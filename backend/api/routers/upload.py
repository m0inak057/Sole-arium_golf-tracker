"""Upload router — ``POST /api/session``.

Creates a new session, persists the uploaded video, enqueues the pipeline,
and returns ``202 Accepted`` with the session_id.
See api-contract.md §1.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, BackgroundTasks

from backend.api.deps import get_settings, get_storage
from backend.api.dto import SessionCreateResponse
from backend.core.config import Settings
from backend.core.logging import get_logger, log_event
from backend.core.session import create_session, create_dual_video_session
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["session"])
logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov"}


def detect_camera_angle_from_filename(filename: str) -> str | None:
    """Detect camera angle from filename patterns.
    
    Args:
        filename: The uploaded filename.
        
    Returns:
        "face_on", "down_the_line", or None if not detectable.
    """
    filename_lower = filename.lower()
    
    # Face-on patterns
    face_on_patterns = [
        "face_on", "face-on", "faceon", "front", "frontal", 
        "fo", "f_o", "face", "front_view"
    ]
    
    # Down-the-line patterns  
    dtl_patterns = [
        "down_the_line", "down-the-line", "downtheline", "dtl", 
        "d_t_l", "side", "lateral", "profile", "side_view"
    ]
    
    for pattern in face_on_patterns:
        if pattern in filename_lower:
            return "face_on"
            
    for pattern in dtl_patterns:
        if pattern in filename_lower:
            return "down_the_line"
            
    return None


def validate_video_file(video: UploadFile, expected_angle: str | None = None) -> tuple[str, str | None]:
    """Validate a video file upload.
    
    Args:
        video: The uploaded video file.
        expected_angle: Expected camera angle if known.
        
    Returns:
        Tuple of (extension, detected_angle).
        
    Raises:
        HTTPException: On validation failures.
    """
    # Validate file extension
    filename = video.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": {
                    "code": "unsupported_file_type",
                    "message": f"File extension must be one of {ALLOWED_EXTENSIONS}.",
                    "details": {"received_extension": ext, "filename": filename},
                }
            },
        )
    
    # Detect camera angle from filename
    detected_angle = detect_camera_angle_from_filename(filename)
    
    return ext, detected_angle


@router.post(
    "/session",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new analysis session",
)
async def create_analysis_session(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Golf swing video (.mp4 or .mov)"),
    gender: str = Form(..., description="Golfer gender: 'male' or 'female'"),
    settings: Settings = Depends(get_settings),
    storage: LocalStorage = Depends(get_storage),
) -> SessionCreateResponse:
    """Accept a video upload + gender, create a session, and enqueue the pipeline.

    Args:
        video: Uploaded video file.
        gender: ``"male"`` or ``"female"``.
        settings: Injected application settings.
        storage: Injected storage adapter.

    Returns:
        ``SessionCreateResponse`` with session_id, status, and created_at.

    Raises:
        HTTPException: On validation failures (400, 413, 415).
    """
    # ── Validate gender ──────────────────────────────────────────────
    gender_lower = gender.strip().lower()
    if gender_lower not in ("male", "female"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "invalid_gender",
                    "message": "gender must be 'male' or 'female'.",
                    "details": {"received": gender},
                }
            },
        )

    # ── Validate file extension ──────────────────────────────────────
    filename = video.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": {
                    "code": "unsupported_file_type",
                    "message": f"File extension must be one of {ALLOWED_EXTENSIONS}.",
                    "details": {"received_extension": ext},
                }
            },
        )

    # ── Read and validate file size ──────────────────────────────────
    content = await video.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "upload_too_large",
                    "message": f"File exceeds the {settings.max_upload_mb} MB limit.",
                    "details": {
                        "max_mb": settings.max_upload_mb,
                        "received_bytes": len(content),
                    },
                }
            },
        )

    # ── Create session ───────────────────────────────────────────────
    session = create_session(gender=gender_lower)  # type: ignore[arg-type]
    storage.save_session(session)

    # ── Persist video ────────────────────────────────────────────────
    await storage.save_upload(session.session_id, content, extension=ext)

    log_event(
        logger,
        "New session created",
        session_id=session.session_id,
        event="session_created",
        gender=gender_lower,
        file_size_bytes=len(content),
    )

    # ── Enqueue pipeline ───────────────────────────────────────────────
    from backend.orchestrator.pipeline import run_pipeline
    
    log_event(
        logger,
        "Enqueuing pipeline in background task",
        session_id=session.session_id,
        event="pipeline_enqueued",
    )
    
    background_tasks.add_task(run_pipeline, session, storage)

    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
    )


@router.post(
    "/session/dual",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new dual-video analysis session",
)
async def create_dual_video_session_endpoint(
    background_tasks: BackgroundTasks,
    face_on_video: UploadFile = File(..., description="Face-on golf swing video (.mp4 or .mov)"),
    down_the_line_video: UploadFile = File(..., description="Down-the-line golf swing video (.mp4 or .mov)"),
    gender: str = Form(..., description="Golfer gender: 'male' or 'female'"),
    settings: Settings = Depends(get_settings),
    storage: LocalStorage = Depends(get_storage),
) -> SessionCreateResponse:
    """Accept two video uploads (face-on + down-the-line) + gender, create a dual-video session.

    Args:
        face_on_video: Face-on camera angle video file.
        down_the_line_video: Down-the-line camera angle video file.
        gender: ``"male"`` or ``"female"``.
        settings: Injected application settings.
        storage: Injected storage adapter.

    Returns:
        ``SessionCreateResponse`` with session_id, status, and created_at.

    Raises:
        HTTPException: On validation failures (400, 413, 415).
    """
    # ── Validate gender ──────────────────────────────────────────────
    gender_lower = gender.strip().lower()
    if gender_lower not in ("male", "female"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "invalid_gender",
                    "message": "gender must be 'male' or 'female'.",
                    "details": {"received": gender},
                }
            },
        )

    # ── Validate both video files ────────────────────────────────────
    face_on_ext, face_on_detected = validate_video_file(face_on_video, "face_on")
    dtl_ext, dtl_detected = validate_video_file(down_the_line_video, "down_the_line")
    
    # ── Read and validate file sizes ─────────────────────────────────
    face_on_content = await face_on_video.read()
    dtl_content = await down_the_line_video.read()
    
    total_size = len(face_on_content) + len(dtl_content)
    max_dual_size = settings.max_upload_bytes * 2  # Allow 2x for dual videos
    
    if len(face_on_content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "face_on_upload_too_large",
                    "message": f"Face-on video exceeds the {settings.max_upload_mb} MB limit.",
                    "details": {
                        "max_mb": settings.max_upload_mb,
                        "received_bytes": len(face_on_content),
                    },
                }
            },
        )
    
    if len(dtl_content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "down_the_line_upload_too_large",
                    "message": f"Down-the-line video exceeds the {settings.max_upload_mb} MB limit.",
                    "details": {
                        "max_mb": settings.max_upload_mb,
                        "received_bytes": len(dtl_content),
                    },
                }
            },
        )

    # ── Create dual video session ────────────────────────────────────
    session = create_dual_video_session(gender=gender_lower)  # type: ignore[arg-type]
    
    # Update dual video status
    if session.dual_video_status:
        session.dual_video_status.face_on_uploaded = True
        session.dual_video_status.down_the_line_uploaded = True
    
    storage.save_session(session)

    # ── Persist both videos ──────────────────────────────────────────
    await storage.save_dual_upload(
        session.session_id, 
        face_on_content, 
        dtl_content,
        extension=face_on_ext  # Assume both have same extension
    )

    log_event(
        logger,
        "New dual-video session created",
        session_id=session.session_id,
        event="dual_session_created",
        gender=gender_lower,
        face_on_size_bytes=len(face_on_content),
        dtl_size_bytes=len(dtl_content),
        total_size_bytes=total_size,
        face_on_detected_angle=face_on_detected,
        dtl_detected_angle=dtl_detected,
    )

    # ── Enqueue dual video pipeline ──────────────────────────────────
    from backend.orchestrator.pipeline import run_pipeline
    
    log_event(
        logger,
        "Enqueuing dual-video pipeline in background task",
        session_id=session.session_id,
        event="dual_pipeline_enqueued",
    )
    
    background_tasks.add_task(run_pipeline, session, storage)

    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
    )


@router.post(
    "/session/single-with-angle",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create a new single-video session with specified camera angle",
)
async def create_single_video_with_angle_session(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="Golf swing video (.mp4 or .mov)"),
    camera_angle: str = Form(..., description="Camera angle: 'face_on' or 'down_the_line'"),
    gender: str = Form(..., description="Golfer gender: 'male' or 'female'"),
    settings: Settings = Depends(get_settings),
    storage: LocalStorage = Depends(get_storage),
) -> SessionCreateResponse:
    """Accept a single video upload with explicit camera angle specification.

    Args:
        video: Uploaded video file.
        camera_angle: ``"face_on"`` or ``"down_the_line"``.
        gender: ``"male"`` or ``"female"``.
        settings: Injected application settings.
        storage: Injected storage adapter.

    Returns:
        ``SessionCreateResponse`` with session_id, status, and created_at.

    Raises:
        HTTPException: On validation failures (400, 413, 415).
    """
    # ── Validate camera angle ────────────────────────────────────────
    camera_angle_lower = camera_angle.strip().lower()
    if camera_angle_lower not in ("face_on", "down_the_line"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "invalid_camera_angle",
                    "message": "camera_angle must be 'face_on' or 'down_the_line'.",
                    "details": {"received": camera_angle},
                }
            },
        )

    # ── Validate gender ──────────────────────────────────────────────
    gender_lower = gender.strip().lower()
    if gender_lower not in ("male", "female"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "invalid_gender",
                    "message": "gender must be 'male' or 'female'.",
                    "details": {"received": gender},
                }
            },
        )

    # ── Validate video file ──────────────────────────────────────────
    ext, detected_angle = validate_video_file(video, camera_angle_lower)

    # ── Read and validate file size ──────────────────────────────────
    content = await video.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": {
                    "code": "upload_too_large",
                    "message": f"File exceeds the {settings.max_upload_mb} MB limit.",
                    "details": {
                        "max_mb": settings.max_upload_mb,
                        "received_bytes": len(content),
                    },
                }
            },
        )

    # ── Create session with angle ────────────────────────────────────
    session = create_session(gender=gender_lower)  # type: ignore[arg-type]
    session.camera_angle = camera_angle_lower  # type: ignore[assignment]
    storage.save_session(session)

    # ── Persist video with angle ─────────────────────────────────────
    await storage.save_upload(session.session_id, content, extension=ext, angle=camera_angle_lower)

    log_event(
        logger,
        "New single-video session created with angle",
        session_id=session.session_id,
        event="single_angle_session_created",
        gender=gender_lower,
        camera_angle=camera_angle_lower,
        file_size_bytes=len(content),
        detected_angle=detected_angle,
    )

    # ── Enqueue pipeline ─────────────────────────────────────────────
    from backend.orchestrator.pipeline import run_pipeline
    
    log_event(
        logger,
        "Enqueuing single-angle pipeline in background task",
        session_id=session.session_id,
        event="single_angle_pipeline_enqueued",
    )
    
    background_tasks.add_task(run_pipeline, session, storage)

    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
    )

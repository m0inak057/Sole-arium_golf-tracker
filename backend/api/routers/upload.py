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
from backend.core.session import create_session
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["session"])
logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov"}


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

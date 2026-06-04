"""Status router — ``GET /api/session/{session_id}/status`` and full session.

Enhanced with dual video support endpoints.

See api-contract.md §1.
"""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.api.dto import (
    SessionStatusResponse,
    DualVideoSessionStatusResponse,
    DualVideoOutputStatus,
    AngleVideoStatus,
    ProcessingProgressResponse,
)
from backend.core.session import SessionJSON, get_progress_pct
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["session"])


@router.get(
    "/session/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Poll session status",
)
async def get_session_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> SessionStatusResponse:
    """Return the current pipeline status for polling.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``SessionStatusResponse`` with status, progress percentage, and failure info.

    Raises:
        HTTPException: 404 if the session does not exist.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "session_not_found",
                    "message": f"No session with id '{session_id}'.",
                    "details": {},
                }
            },
        )

    session = storage.load_session(session_id)
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        progress_pct=get_progress_pct(session.status),
        status_reason=session.status_reason,
        failed=session.status == "failed",
        total_swing_attempts=session.total_swing_attempts,
        all_swing_attempts=session.all_swing_attempts,
    )


@router.get(
    "/session/{session_id}/status/dual",
    response_model=DualVideoSessionStatusResponse,
    summary="Poll dual video session status",
)
async def get_dual_video_session_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> DualVideoSessionStatusResponse:
    """Return comprehensive status for dual video sessions.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``DualVideoSessionStatusResponse`` with detailed dual video status.

    Raises:
        HTTPException: 404 if the session does not exist.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "session_not_found",
                    "message": f"No session with id '{session_id}'.",
                    "details": {},
                }
            },
        )

    session = storage.load_session(session_id)
    
    # Check video availability
    slowmo_face_on = storage.get_video_path(session_id, "slowmo", "face_on")
    slowmo_dtl = storage.get_video_path(session_id, "slowmo", "down_the_line")
    annotated_face_on = storage.get_video_path(session_id, "annotated", "face_on")
    annotated_dtl = storage.get_video_path(session_id, "annotated", "down_the_line")
    
    return DualVideoSessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        progress_pct=get_progress_pct(session.status),
        dual_video_mode=storage.is_dual_video_session(session_id),
        face_on_processing_complete=session.status in ("phase8_done", "complete"),
        down_the_line_processing_complete=session.status in ("phase8_done", "complete"),
        slowmo_face_on_ready=slowmo_face_on is not None,
        slowmo_down_the_line_ready=slowmo_dtl is not None,
        annotated_face_on_ready=annotated_face_on is not None,
        annotated_down_the_line_ready=annotated_dtl is not None,
        slowmo_face_on_path=f"/api/output/{session_id}/slowmo/face-on" if slowmo_face_on else None,
        slowmo_down_the_line_path=f"/api/output/{session_id}/slowmo/down-the-line" if slowmo_dtl else None,
        annotated_face_on_path=f"/api/output/{session_id}/annotated/face-on" if annotated_face_on else None,
        annotated_down_the_line_path=f"/api/output/{session_id}/annotated/down-the-line" if annotated_dtl else None,
        status_reason=session.status_reason,
        failed=session.status == "failed",
        overlay_rendering_failed=session.overlay_rendering_failed,
        total_swing_attempts=session.total_swing_attempts,
        all_swing_attempts=session.all_swing_attempts,
    )


@router.get(
    "/session/{session_id}/status/output",
    response_model=DualVideoOutputStatus,
    summary="Get output video status for all angles and types",
)
async def get_output_status(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> DualVideoOutputStatus:
    """Get comprehensive output status for all video types and angles.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``DualVideoOutputStatus`` with status for all video combinations.

    Raises:
        HTTPException: 404 if the session does not exist.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "session_not_found",
                    "message": f"No session with id '{session_id}'.",
                    "details": {},
                }
            },
        )

    is_dual = storage.is_dual_video_session(session_id)
    
    # Get all video paths
    slowmo_face_on = storage.get_video_path(session_id, "slowmo", "face_on")
    slowmo_dtl = storage.get_video_path(session_id, "slowmo", "down_the_line")
    annotated_face_on = storage.get_video_path(session_id, "annotated", "face_on")
    annotated_dtl = storage.get_video_path(session_id, "annotated", "down_the_line")
    
    # Build status response
    return DualVideoOutputStatus(
        session_id=session_id,
        dual_video_mode=is_dual,
        slowmo={
            "face_on": AngleVideoStatus(
                ready=slowmo_face_on is not None,
                path=f"/api/output/{session_id}/slowmo/face-on" if slowmo_face_on else None,
                file_size_bytes=slowmo_face_on.stat().st_size if slowmo_face_on else None,
            ),
            "down_the_line": AngleVideoStatus(
                ready=slowmo_dtl is not None,
                path=f"/api/output/{session_id}/slowmo/down-the-line" if slowmo_dtl else None,
                file_size_bytes=slowmo_dtl.stat().st_size if slowmo_dtl else None,
            ),
        },
        annotated={
            "face_on": AngleVideoStatus(
                ready=annotated_face_on is not None,
                path=f"/api/output/{session_id}/annotated/face-on" if annotated_face_on else None,
                file_size_bytes=annotated_face_on.stat().st_size if annotated_face_on else None,
            ),
            "down_the_line": AngleVideoStatus(
                ready=annotated_dtl is not None,
                path=f"/api/output/{session_id}/annotated/down-the-line" if annotated_dtl else None,
                file_size_bytes=annotated_dtl.stat().st_size if annotated_dtl else None,
            ),
        },
        metadata_available=any([slowmo_face_on, slowmo_dtl, annotated_face_on, annotated_dtl]),
        metadata_path=f"/api/output/{session_id}/metadata" if any([slowmo_face_on, slowmo_dtl, annotated_face_on, annotated_dtl]) else None,
    )


@router.get(
    "/session/{session_id}/status/progress",
    response_model=ProcessingProgressResponse,
    summary="Get detailed processing progress",
)
async def get_processing_progress(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> ProcessingProgressResponse:
    """Get detailed processing progress for frontend display.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        ``ProcessingProgressResponse`` with detailed progress information.

    Raises:
        HTTPException: 404 if the session does not exist.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "session_not_found",
                    "message": f"No session with id '{session_id}'.",
                    "details": {},
                }
            },
        )

    session = storage.load_session(session_id)
    
    # Calculate elapsed time
    from datetime import datetime, timezone
    created_at = datetime.fromisoformat(session.created_at)
    now = datetime.now(timezone.utc)
    elapsed_seconds = (now - created_at).total_seconds()
    
    # Build phase progress
    phases = {}
    if session.timings:
        timing_fields = [
            ("agent1", "Agent 1: Video Intelligence"),
            ("phase1", "Phase 1: Hit Detection"),
            ("agent2", "Agent 2: Body Calibration"),
            ("phase2", "Phase 2: Keypoints"),
            ("phase3", "Phase 3: Setup Analysis"),
            ("agent3", "Agent 3: Shot Classification"),
            ("phase4", "Phase 4: Biomechanical Metrics"),
            ("agent4", "Agent 4: Threshold Adaptation"),
            ("phase5", "Phase 5: Performance Scoring"),
            ("agent5", "Agent 5: Coaching"),
            ("phase7", "Phase 7: Slow-Motion Rendering"),
            ("phase8", "Phase 8: Annotated Overlay"),
        ]
        
        for timing_key, phase_name in timing_fields:
            timing_ms = getattr(session.timings, f"{timing_key}_ms", None)
            phases[timing_key] = {
                "name": phase_name,
                "duration_ms": timing_ms,
                "complete": timing_ms is not None,
            }
    
    return ProcessingProgressResponse(
        session_id=session.session_id,
        overall_progress_pct=get_progress_pct(session.status),
        current_phase=session.status,
        current_phase_progress_pct=get_progress_pct(session.status),
        phases=phases,
        dual_video_mode=storage.is_dual_video_session(session_id),
        face_on_progress_pct=get_progress_pct(session.status) if storage.is_dual_video_session(session_id) else None,
        down_the_line_progress_pct=get_progress_pct(session.status) if storage.is_dual_video_session(session_id) else None,
        elapsed_seconds=elapsed_seconds,
        status=session.status,
        failed=session.status == "failed",
        error_message=session.status_reason,
    )


@router.get(
    "/session/{session_id}",
    response_model=SessionJSON,
    summary="Get full session JSON",
)
async def get_full_session(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> SessionJSON:
    """Return the full session JSON.  Only call after status is ``complete``.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        The complete ``SessionJSON``.

    Raises:
        HTTPException: 404 if unknown, 409 if not complete yet.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "session_not_found",
                    "message": f"No session with id '{session_id}'.",
                    "details": {},
                }
            },
        )

    session = storage.load_session(session_id)
    if session.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "session_not_complete",
                    "message": "Session is not complete yet. Poll /status instead.",
                    "details": {"current_status": session.status},
                }
            },
        )

    return session

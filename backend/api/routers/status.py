"""Status router — ``GET /api/session/{session_id}/status`` and full session.

See api-contract.md §1.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.api.dto import SessionStatusResponse
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

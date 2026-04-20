"""Coaching router — ``GET /api/coaching/{session_id}``.

Returns the ``coaching_output`` array from the session JSON.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.core.session import CoachingItem
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["coaching"])


@router.get(
    "/coaching/{session_id}",
    response_model=list[CoachingItem],
    summary="Get coaching recommendations",
)
async def get_coaching(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> list[CoachingItem]:
    """Return the coaching output array.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        List of ``CoachingItem``.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session.")

    session = storage.load_session(session_id)
    return session.coaching_output or []

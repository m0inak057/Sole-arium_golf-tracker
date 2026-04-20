"""Phase 5 router — ``GET /api/phase5/score/{session_id}``.

Returns the ``scores`` object from the session JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.core.session import Scores
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["phase5"])


@router.get(
    "/phase5/score/{session_id}",
    response_model=Scores,
    summary="Get Phase 5 performance scores",
)
async def get_phase5_score(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> Scores:
    """Return the scores object from the session JSON.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        The ``Scores`` object.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session.")

    session = storage.load_session(session_id)
    return session.scores or Scores()

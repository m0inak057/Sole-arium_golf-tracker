"""Phase 4 router — ``GET /api/phase4/results/{session_id}``.

Returns the ``metrics`` object from the session JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["phase4"])


@router.get(
    "/phase4/results/{session_id}",
    summary="Get Phase 4 biomechanical metrics",
)
async def get_phase4_results(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> dict[str, Any]:
    """Return the metrics object from the session JSON.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        The ``metrics`` dict.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session.")

    session = storage.load_session(session_id)
    return session.metrics or {}

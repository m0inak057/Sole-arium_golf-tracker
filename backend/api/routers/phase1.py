"""Phase 1 router — ``GET /api/phase1/detection/{session_id}``.

Convenience endpoint per api-contract.md §2.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_storage
from backend.api.dto import Phase1DetectionResponse
from backend.core.storage import LocalStorage

router = APIRouter(prefix="/api", tags=["phase1"])


@router.get(
    "/phase1/detection/{session_id}",
    response_model=Phase1DetectionResponse,
    summary="Get Phase 1 hit detection results",
)
async def get_phase1_detection(
    session_id: str,
    storage: LocalStorage = Depends(get_storage),
) -> Phase1DetectionResponse:
    """Return hit detection results without downloading the full session JSON.

    Args:
        session_id: UUID of the session.
        storage: Injected storage adapter.

    Returns:
        Phase 1 detection fields.
    """
    if not storage.session_exists(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "session_not_found", "message": "Unknown session."}},
        )

    session = storage.load_session(session_id)
    return Phase1DetectionResponse(
        total_swing_attempts=session.total_swing_attempts,
        selected_swing_index=session.selected_swing_index,
        hit_confidence_score=session.hit_confidence_score,
        backswing_start_frame_index=session.backswing_start_frame_index,
        impact_frame_index=session.impact_frame_index,
        follow_through_end_frame_index=session.follow_through_end_frame_index,
    )

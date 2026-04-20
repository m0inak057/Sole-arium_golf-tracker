"""Pydantic models for Phase 1 outputs.

Stub — full implementation in Sprint 1.
"""

from __future__ import annotations

from pydantic import BaseModel


class SwingAttempt(BaseModel):
    attempt_index: int
    score: float
    is_real: bool
    backswing_start_frame_index: int
    impact_frame_index: int
    follow_through_end_frame_index: int
    address_frame_range: list[int]


class HitDetectionResult(BaseModel):
    total_swing_attempts: int
    selected_swing_index: int | None
    hit_confidence_score: float | None
    backswing_start_frame_index: int | None
    impact_frame_index: int | None
    follow_through_end_frame_index: int | None
    address_frame_range: list[int] | None


"""Agent 4 — Threshold Adaptation.

Generates personalised thresholds for the 13 metrics based on inferred skill and setup.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel

from backend.agents.base import BaseAgent


class ThresholdRangeModel(BaseModel):
    green: list[float] | None = None
    amber: list[float] | None = None
    red_below: float | None = None
    red_above: float | None = None
    green_max: float | None = None
    amber_max: float | None = None
    green_min: float | None = None
    amber_min: float | None = None
    green_ratio: list[float] | None = None
    amber_ratio: list[float] | None = None


class Agent4Response(BaseModel):
    """Pydantic model for Agent 4's expected JSON output."""
    inferred_skill_level: Literal["beginner", "intermediate", "advanced", "scratch"]
    active_thresholds: dict[str, ThresholdRangeModel]


class ThresholdAdaptationAgent(BaseAgent):
    """Agent 4 implementation."""

    @property
    def agent_number(self) -> int:
        return 4

    @property
    def response_model(self) -> type[BaseModel]:
        return Agent4Response

    @property
    def system_prompt(self) -> str:
        return (
            "You are Agent 4 in the Golf Trainer AI pipeline. Your job is to classify the\n"
            "prioritize ... Never output prose. Only JSON.\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "inferred_skill_level": "beginner" | "intermediate" | "advanced" | "scratch",\n'
            '  "active_thresholds": { ... }\n'
            "}\n\n"
            "Keys for the active_thresholds dict MUST exactly match:\n"
            '"tempo_ratio", "x_factor", "spine_deviation_max", "hip_sway", "head_sway", "hip_turn",\n'
            '"shoulder_turn", "side_bend", "hips_open", "wrist_lag", "knee_flex_left",\n'
            '"knee_flex_right", "stance_width".\n\n'
            "Threshold shape varies per metric (see schema). For exact bounds, e.g., tempo_ratio is ratio,"
            "sway is green_max/amber_max (in inches) etc. Make logical choices."
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt."""
        return (
            f"Golfer gender: {session_data.get('gender', 'unknown')}\n"
            f"Detected shot type: {session_data.get('detected_shot_type', 'unknown')}\n\n"
            f"Metrics (Phase 4): {session_data.get('metrics', {})}"
        )

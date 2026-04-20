"""Agent 3 — Shot Classification.

Classifies the shot type based on the golfer's setup geometry.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel

from backend.agents.base import BaseAgent


class Agent3Response(BaseModel):
    """Pydantic model for Agent 3's expected JSON output."""
    detected_shot_type: Literal["driver", "long_iron", "mid_iron", "short_iron", "chip_pitch"]
    shot_type_confidence: float
    shot_type_reasoning: str


class ShotClassificationAgent(BaseAgent):
    """Agent 3 implementation."""

    @property
    def agent_number(self) -> int:
        return 3

    @property
    def response_model(self) -> type[BaseModel]:
        return Agent3Response

    @property
    def system_prompt(self) -> str:
        return (
            "You are Agent 3 in the Golf Trainer AI pipeline. Your only job is to classify the\n"
            "shot type the golfer has set up for. Never output prose or markdown. Only one JSON\n"
            "object.\n\n"
            "Allowed shot types:\n"
            "  driver | long_iron | mid_iron | short_iron | chip_pitch\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "detected_shot_type": "<one of the allowed values>",\n'
            '  "shot_type_confidence": <number 0.0 - 1.0>,\n'
            '  "shot_type_reasoning": "<one or two short sentences>"\n'
            "}\n\n"
            "Heuristics:\n"
            "- Driver: widest stance (> shoulder width), ball position forward (toward lead foot,\n"
            "  ratio > 0.65), shallow spine tilt.\n"
            "- Long iron: near-shoulder-width stance, ball slightly forward (0.55 - 0.65).\n"
            "- Mid iron: shoulder-width stance, ball centred (0.45 - 0.55).\n"
            "- Short iron: slightly narrower than shoulder-width, ball centred-to-back (0.40 - 0.50),\n"
            "  more spine tilt.\n"
            "- Chip / pitch: narrow stance (< 0.85 of shoulder width), ball back (< 0.40), open\n"
            "  stance common.\n"
            "- Camera angle matters: ball_position_ratio is unreliable on down-the-line; weight\n"
            "  stance width and spine tilt more heavily in that case."
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt. For Agent 3, metrics come packed in session_data."""
        return (
            f"Camera angle (Agent 1): {session_data.get('camera_angle', 'unknown')}\n"
            f"Calibration (Agent 2): {session_data.get('px_to_inches_scale', 0.0)} in/px\n\n"
            f"Setup metrics (Phase 3):\n"
            f"  stance_width_inches: {session_data.get('stance_width_inches', 'N/A')}\n"
            f"  ball_position: {session_data.get('ball_position', 'N/A')}\n"
            f"  spine_tilt_deg_at_address: {session_data.get('spine_tilt_deg_at_address', 'N/A')}\n\n"
            f"Golfer gender: {session_data.get('gender', 'unknown')}"
        )

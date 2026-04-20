"""Agent 5 — Coaching (acts as Phase 6).

Analyses Phase 5 scores and builds a structured coaching plan with drills.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel

from backend.agents.base import BaseAgent


class CoachingItemModel(BaseModel):
    priority: int
    severity: Literal["high", "medium", "low"]
    title: str
    explanation: str
    drill_suggestion: str = ""


class Agent5Response(BaseModel):
    """Pydantic model for Agent 5's expected JSON output."""
    coaching_output: list[CoachingItemModel]


class CoachingAgent(BaseAgent):
    """Agent 5 implementation."""

    @property
    def agent_number(self) -> int:
        return 5

    @property
    def response_model(self) -> type[BaseModel]:
        return Agent5Response

    @property
    def system_prompt(self) -> str:
        return (
            "You are Agent 5 in the Golf Trainer AI pipeline (The Head Coach).\n"
            "Analyse the scored metrics and overall band, and produce a structured list of\n"
            "2-4 coaching recommendations. Never output prose. Only JSON.\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "coaching_output": [\n'
            '    {\n'
            '      "priority": <int 1-4>,\n'
            '      "severity": "high" | "medium" | "low",\n'
            '      "title": "<short actionable title>",\n'
            '      "explanation": "<explain exactly why this metric hurts their swing>",\n'
            '      "drill_suggestion": "<recommend a specific golf drill to fix this>"\n'
            '    }\n'
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Prioritise 'red' band metrics first.\n"
            "- Explain mechanics clearly without being condescending."
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt."""
        return (
            f"Golfer setup: {session_data.get('gender', 'unknown')} | {session_data.get('detected_shot_type', 'unknown')}\n"
            f"Inferred skill: {session_data.get('inferred_skill_level', 'unknown')}\n\n"
            f"Scores (Phase 5): {session_data.get('scores', {})}\n"
            f"Metrics summary: {session_data.get('metrics', {})}"
        )

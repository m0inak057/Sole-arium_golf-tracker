"""Agent 4 — Threshold Adaptation.

Generates personalised thresholds for the 13 metrics based on inferred skill and setup.
See agent-prompts.md §Agent 4 for the authoritative prompt specification.
"""

from __future__ import annotations

import json
from typing import Any, Literal
from pydantic import BaseModel

from backend.agents.base import BaseAgent
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ThresholdRangeModel(BaseModel):
    """A single threshold entry with flexible range definitions."""

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
            "You are Agent 4 in the Golf Trainer AI pipeline. Your only job is to produce "
            "the active_thresholds used to score this session and infer the golfer's skill level. "
            "Never output prose or markdown. Only one JSON object matching the schema.\n\n"
            "Output JSON schema:\n"
            "{\n"
            '  "inferred_skill_level": "beginner" | "intermediate" | "advanced" | "scratch",\n'
            '  "active_thresholds": {\n'
            '    "tempo_ratio": { ... threshold object ... },\n'
            '    "x_factor": { ... },\n'
            '    "spine_deviation_max": { ... },\n'
            '    ... (all 13 metrics listed below)\n'
            "  }\n"
            "}\n\n"
            "The 13 metrics you must return thresholds for:\n"
            "1. tempo_ratio\n"
            "2. x_factor\n"
            "3. spine_deviation_max\n"
            "4. hip_sway\n"
            "5. head_sway\n"
            "6. hip_turn\n"
            "7. shoulder_turn\n"
            "8. side_bend\n"
            "9. hips_open\n"
            "10. wrist_lag\n"
            "11. knee_flex_left\n"
            "12. knee_flex_right\n"
            "13. stance_width\n\n"
            "SKILL LEVEL INFERENCE RULES:\n"
            "Analyse these signals to classify the golfer:\n"
            "  - Tempo consistency: tight around 3.0 (male) or 4.0 (female) → advanced\n"
            "  - X-factor: high (>40) with low spine deviation → advanced\n"
            "  - Spine deviation: <5 deg → advanced, >8 deg → beginner\n"
            "  - Sway (hip + head): <2 in combined → advanced, >5 in → beginner\n"
            "  - Hip/shoulder turn: controlled, within expected range → higher skill\n"
            "  - Wrist lag: consistent >15 deg → intermediate+, <10 deg → beginner\n\n"
            "Skill classification:\n"
            "  - SCRATCH: excellent tempo (±0.15 of target), X-factor >40, spine <3 deg, "
            "sway <1.5 in, knee flex 25-30, wrist lag 18+\n"
            "  - ADVANCED: tight tempo (±0.25 of target), X-factor >35, spine <5 deg, "
            "sway <2.5 in, wrist lag >15\n"
            "  - INTERMEDIATE: moderate tempo variation (±0.4 of target), X-factor 30-40, "
            "spine <8 deg, sway <4 in, wrist lag 10-15\n"
            "  - BEGINNER: loose tempo (>±0.5 variance), X-factor <30, spine >8 deg, "
            "sway >4 in, wrist lag <10\n\n"
            "THRESHOLD ADAPTATION RULES:\n\n"
            "Base thresholds by shot type:\n"
            "  DRIVER (widest stance, ball forward):\n"
            "    tempo: male [2.8, 3.2], female [3.8, 4.2]\n"
            "    x_factor: [35, 55] (widest)\n"
            "    hip_sway_max: 2.5 in (more sway allowed with big swing)\n"
            "    stance_width: [1.0, 1.15] (wider than shoulder)\n\n"
            "  LONG IRON:\n"
            "    tempo: male [2.8, 3.2], female [3.8, 4.2]\n"
            "    x_factor: [32, 50]\n"
            "    hip_sway_max: 2.2 in\n"
            "    stance_width: [0.95, 1.05]\n\n"
            "  MID IRON (balanced):\n"
            "    tempo: male [2.85, 3.15], female [3.85, 4.15]\n"
            "    x_factor: [30, 48]\n"
            "    hip_sway_max: 1.8 in\n"
            "    stance_width: [0.95, 1.05]\n\n"
            "  SHORT IRON (compact, controlled):\n"
            "    tempo: male [2.9, 3.1], female [3.9, 4.1]\n"
            "    x_factor: [25, 42] (narrower)\n"
            "    hip_sway_max: 1.5 in (minimal sway)\n"
            "    stance_width: [0.90, 1.00]\n\n"
            "  CHIP/PITCH (very compact):\n"
            "    tempo: male [3.5, 4.5], female [4.5, 5.5] (much slower)\n"
            "    x_factor: [15, 30] (minimal rotation)\n"
            "    hip_sway_max: 1.0 in\n"
            "    stance_width: [0.80, 0.95]\n\n"
            "Base thresholds for each metric (apply skill and quality adjustments after):\n\n"
            "  tempo_ratio:\n"
            "    Beginner: green ±0.5 of target, amber ±0.8\n"
            "    Intermediate: green ±0.25 of target, amber ±0.5\n"
            "    Advanced: green ±0.15 of target, amber ±0.3\n"
            "    Scratch: green ±0.1 of target, amber ±0.2\n\n"
            "  x_factor: [see shot type above] × skill scaling\n\n"
            "  spine_deviation_max:\n"
            "    Beginner: green_max 8, amber_max 12\n"
            "    Intermediate: green_max 6, amber_max 10\n"
            "    Advanced: green_max 4, amber_max 7\n"
            "    Scratch: green_max 3, amber_max 5\n\n"
            "  hip_sway: [see shot type above] × skill scaling\n\n"
            "  head_sway:\n"
            "    Beginner: green_max 2.5\n"
            "    Intermediate: green_max 2.0\n"
            "    Advanced: green_max 1.0\n"
            "    Scratch: green_max 0.7\n\n"
            "  hip_turn & shoulder_turn: [subject to shot type]\n"
            "    Driver: hip 45-55, shoulder 85-100 (widest)\n"
            "    Long iron: hip 42-52, shoulder 80-95\n"
            "    Mid iron: hip 40-50, shoulder 75-90\n"
            "    Short iron: hip 38-48, shoulder 70-85 (narrower)\n"
            "    Adjust ±10% per skill level (beginner wider, scratch narrower)\n\n"
            "  side_bend: green [5, 15], amber [0, 20] (apply to all skills)\n\n"
            "  hips_open: green [30, 45], amber [20, 55] (at impact)\n\n"
            "  wrist_lag:\n"
            "    Beginner: green_min 8, amber_min 5\n"
            "    Intermediate: green_min 12, amber_min 8\n"
            "    Advanced: green_min 15, amber_min 12\n"
            "    Scratch: green_min 18, amber_min 15\n\n"
            "  knee_flex_left & knee_flex_right:\n"
            "    All skills: green [20, 30], amber [15, 35]\n"
            "    Beginner: green [18, 32] (slightly wider)\n\n"
            "  stance_width:\n"
            "    green_ratio [0.95, 1.05] (baseline)\n"
            "    amber_ratio [0.85, 1.15]\n"
            "    Adjust per shot type [see above]\n\n"
            "QUALITY AND CONFIDENCE ADJUSTMENTS:\n"
            "  - If video_quality_score < 0.5: widen all ranges by ~15% (measurement noise)\n"
            "  - If shot_type_confidence < 0.6: widen ranges by ~10% (ambiguous shot classification)\n"
            "  - If beginner level: widen all ranges by ~20% (more variability expected)\n"
            "  - If scratch level: narrow all ranges by ~10% (tighter consistency expected)\n\n"
            "CAMERA ANGLE NOTES:\n"
            "  - face_on: measurements generally reliable for hip/shoulder angles\n"
            "  - down_the_line: hip/shoulder angles less reliable; weight sway and spine deviation more\n\n"
            "CRITICAL RULES:\n"
            "  - MUST return all 13 metrics with complete threshold objects\n"
            "  - Do NOT leave metrics out\n"
            "  - Always include red_below and/or red_above when meaningful\n"
            "  - Ensure thresholds are logically consistent (amber wider than green, red beyond amber)\n"
            "  - Prefer ranges [min, max] over single-sided bounds when both apply\n"
            "  - Never use negative numbers for physical measurements\n"
            "  - Return numbers rounded to 1 decimal place (e.g. 2.8, not 2.78234)"
        )

    def build_user_prompt(self, session_data: dict[str, Any]) -> str:
        """Assemble the user prompt from session data.
        
        Formats all Phase 4 metrics with values and units for Agent 4 to:
        1. Infer skill level from observed values
        2. Select appropriate base thresholds per shot type
        3. Apply quality and confidence adjustments
        4. Return complete active_thresholds for all 13 metrics
        """
        gender = session_data.get("gender", "unknown")
        camera_angle = session_data.get("camera_angle", "unknown")
        video_quality_score = session_data.get("video_quality_score", 0.5)
        shot_type = session_data.get("detected_shot_type", "unknown")
        shot_type_confidence = session_data.get("shot_type_confidence", 0.5)

        # Extract metrics for skill inference — format clearly with units
        metrics = session_data.get("metrics", {})
        
        # Build metrics display in the order of the 13 metrics
        metric_order = [
            "tempo_ratio",
            "x_factor",
            "spine_deviation_max",
            "hip_sway",
            "head_sway",
            "hip_turn",
            "shoulder_turn",
            "side_bend",
            "hips_open",
            "wrist_lag",
            "knee_flex_left",
            "knee_flex_right",
            "stance_width",
        ]
        
        metrics_lines = []
        if isinstance(metrics, dict):
            for key in metric_order:
                if key in metrics:
                    m = metrics[key]
                    value = m.get("value") if isinstance(m, dict) else getattr(m, "value", None)
                    unit = m.get("unit") if isinstance(m, dict) else getattr(m, "unit", "")

                    if value is not None:
                        metrics_lines.append(f"  {key}: {value} {unit}".strip())
                    else:
                        metrics_lines.append(f"  {key}: (null)")
                else:
                    metrics_lines.append(f"  {key}: (null)")
        
        metrics_str = "\n".join(metrics_lines) if metrics_lines else "  (no metrics available)"

        return (
            f"GOLFER CONTEXT:\n"
            f"  Gender: {gender}\n"
            f"  Camera angle: {camera_angle}\n"
            f"  Video quality score: {video_quality_score}\n"
            f"  Detected shot type: {shot_type}\n"
            f"  Shot type confidence: {shot_type_confidence}\n\n"
            f"PHASE 4 METRICS (observed this session):\n"
            f"{metrics_str}\n\n"
            f"TASK:\n"
            f"1. Infer this golfer's skill level (beginner/intermediate/advanced/scratch) from the metrics above.\n"
            f"2. Select appropriate base thresholds for the {shot_type} shot type.\n"
            f"3. Apply adjustments for video quality ({video_quality_score}) and shot type confidence ({shot_type_confidence}).\n"
            f"4. Return active_thresholds as a JSON object with ALL 13 metrics above.\n\n"
            f"Each metric must have a threshold object with appropriate fields:\n"
            f"  - Range thresholds: \"green\": [min, max], \"amber\": [min, max]\n"
            f"  - Single-sided bounds: \"green_max\", \"amber_max\", \"green_min\", \"amber_min\"\n"
            f"  - Ratio bounds: \"green_ratio\", \"amber_ratio\" (for stance_width)\n"
            f"  - Explicit red bounds: \"red_below\", \"red_above\"\n\n"
            f"Remember:\n"
            f"  - Thresholds must be internally consistent (amber wider than green, red beyond amber)\n"
            f"  - Widen ranges by ~20% for beginner skill level\n"
            f"  - Widen ranges by ~15% if video_quality_score < 0.5\n"
            f"  - Narrow ranges by ~10% for scratch-level skill\n"
            f"  - Use the observed metrics to validate your skill inference\n"
            f"  - Return ONLY valid JSON matching the schema. No prose, no markdown."
        )

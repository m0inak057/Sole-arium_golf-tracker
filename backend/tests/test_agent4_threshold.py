"""Tests for Agent 4 — Threshold Adaptation.

Tests the Agent 4 prompt building, response validation, and threshold logic.
"""

from __future__ import annotations

import json
import pytest
from pydantic import ValidationError

from backend.agents.threshold_agent import (
    ThresholdAdaptationAgent,
    ThresholdRangeModel,
    Agent4Response,
)


class TestThresholdRangeModel:
    """Test the ThresholdRangeModel Pydantic class."""

    def test_range_based_threshold(self):
        """Test range-based green/amber thresholds."""
        threshold = ThresholdRangeModel(
            green=[30.0, 50.0],
            amber=[25.0, 55.0],
            red_below=25.0,
            red_above=55.0,
        )
        assert threshold.green == [30.0, 50.0]
        assert threshold.amber == [25.0, 55.0]
        assert threshold.red_below == 25.0
        assert threshold.red_above == 55.0

    def test_max_based_threshold(self):
        """Test max-based thresholds (green_max, amber_max)."""
        threshold = ThresholdRangeModel(
            green_max=5.0,
            amber_max=8.0,
            red_above=8.0,
        )
        assert threshold.green_max == 5.0
        assert threshold.amber_max == 8.0
        assert threshold.red_above == 8.0

    def test_min_based_threshold(self):
        """Test min-based thresholds (green_min, amber_min)."""
        threshold = ThresholdRangeModel(
            green_min=15.0,
            amber_min=10.0,
            red_below=10.0,
        )
        assert threshold.green_min == 15.0
        assert threshold.amber_min == 10.0
        assert threshold.red_below == 10.0

    def test_ratio_based_threshold(self):
        """Test ratio-based thresholds (green_ratio, amber_ratio)."""
        threshold = ThresholdRangeModel(
            green_ratio=[0.95, 1.05],
            amber_ratio=[0.85, 1.15],
        )
        assert threshold.green_ratio == [0.95, 1.05]
        assert threshold.amber_ratio == [0.85, 1.15]

    def test_empty_threshold(self):
        """Test that an empty threshold is valid."""
        threshold = ThresholdRangeModel()
        assert threshold.green is None
        assert threshold.amber is None
        assert threshold.red_below is None


class TestAgent4Response:
    """Test the Agent4Response Pydantic model."""

    def test_valid_response(self):
        """Test a valid Agent 4 response structure."""
        response_dict = {
            "inferred_skill_level": "intermediate",
            "active_thresholds": {
                "tempo_ratio": {
                    "green": [2.8, 3.2],
                    "amber": [2.5, 3.5],
                    "red_below": 2.5,
                    "red_above": 3.5,
                },
                "x_factor": {
                    "green": [30, 48],
                    "amber": [25, 55],
                    "red_below": 25,
                    "red_above": 55,
                },
                "spine_deviation_max": {
                    "green_max": 6.0,
                    "amber_max": 10.0,
                    "red_above": 10.0,
                },
                "hip_sway": {
                    "green_max": 2.5,
                    "amber_max": 4.0,
                },
                "head_sway": {
                    "green_max": 2.0,
                    "amber_max": 3.5,
                },
                "hip_turn": {
                    "green": [40, 50],
                    "amber": [35, 55],
                },
                "shoulder_turn": {
                    "green": [75, 90],
                    "amber": [70, 95],
                },
                "side_bend": {
                    "green": [5, 15],
                    "amber": [0, 20],
                },
                "hips_open": {
                    "green": [30, 45],
                    "amber": [20, 55],
                },
                "wrist_lag": {
                    "green_min": 12.0,
                    "amber_min": 8.0,
                },
                "knee_flex_left": {
                    "green": [20, 30],
                    "amber": [15, 35],
                },
                "knee_flex_right": {
                    "green": [20, 30],
                    "amber": [15, 35],
                },
                "stance_width": {
                    "green_ratio": [0.95, 1.05],
                    "amber_ratio": [0.85, 1.15],
                },
            },
        }
        response = Agent4Response(**response_dict)
        assert response.inferred_skill_level == "intermediate"
        assert len(response.active_thresholds) == 13
        assert response.active_thresholds["tempo_ratio"].green == [2.8, 3.2]

    def test_invalid_skill_level(self):
        """Test that invalid skill levels are rejected."""
        with pytest.raises(ValidationError):
            Agent4Response(
                inferred_skill_level="expert",  # Invalid
                active_thresholds={},
            )

    def test_all_skill_levels_valid(self):
        """Test that all allowed skill levels are valid."""
        for skill in ["beginner", "intermediate", "advanced", "scratch"]:
            response = Agent4Response(
                inferred_skill_level=skill,
                active_thresholds={},
            )
            assert response.inferred_skill_level == skill


class TestThresholdAdaptationAgent:
    """Test the ThresholdAdaptationAgent class."""

    def test_agent_number(self):
        """Test that agent_number is 4."""
        agent = ThresholdAdaptationAgent()
        assert agent.agent_number == 4

    def test_response_model(self):
        """Test that response_model is Agent4Response."""
        agent = ThresholdAdaptationAgent()
        assert agent.response_model == Agent4Response

    def test_system_prompt_present(self):
        """Test that system prompt is populated."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 500
        assert "Agent 4" in prompt
        assert "inferred_skill_level" in prompt
        assert "active_thresholds" in prompt

    def test_system_prompt_includes_all_metrics(self):
        """Test that system prompt mentions all 13 metrics."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        metrics = [
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
        for metric in metrics:
            assert metric in prompt, f"{metric} not found in system prompt"

    def test_system_prompt_includes_skill_rules(self):
        """Test that system prompt includes skill classification rules."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "SKILL LEVEL INFERENCE RULES" in prompt
        assert "SCRATCH" in prompt
        assert "ADVANCED" in prompt
        assert "INTERMEDIATE" in prompt
        assert "BEGINNER" in prompt

    def test_system_prompt_includes_shot_types(self):
        """Test that system prompt includes shot type thresholds."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "DRIVER" in prompt
        assert "LONG IRON" in prompt
        assert "MID IRON" in prompt
        assert "SHORT IRON" in prompt
        assert "CHIP/PITCH" in prompt

    def test_system_prompt_includes_adjustments(self):
        """Test that system prompt includes adjustment rules."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "QUALITY AND CONFIDENCE ADJUSTMENTS" in prompt
        assert "video_quality_score" in prompt
        assert "shot_type_confidence" in prompt

    def test_build_user_prompt_basic(self):
        """Test building a basic user prompt."""
        agent = ThresholdAdaptationAgent()
        session_data = {
            "gender": "male",
            "camera_angle": "face_on",
            "video_quality_score": 0.8,
            "detected_shot_type": "driver",
            "shot_type_confidence": 0.85,
            "metrics": {
                "tempo_ratio": {"value": 3.0, "unit": "ratio"},
                "x_factor": {"value": 42.0, "unit": "deg"},
                "spine_deviation_max": {"value": 4.5, "unit": "deg"},
                "hip_sway": {"value": 2.0, "unit": "in"},
                "head_sway": {"value": 1.5, "unit": "in"},
                "hip_turn": {"value": 50.0, "unit": "deg"},
                "shoulder_turn": {"value": 85.0, "unit": "deg"},
                "side_bend": {"value": 10.0, "unit": "deg"},
                "hips_open": {"value": 38.0, "unit": "deg"},
                "wrist_lag": {"value": 18.0, "unit": "deg"},
                "knee_flex_left": {"value": 28.0, "unit": "deg"},
                "knee_flex_right": {"value": 27.0, "unit": "deg"},
                "stance_width": {"value": 1.02, "unit": "ratio"},
            },
        }
        prompt = agent.build_user_prompt(session_data)
        assert "male" in prompt
        assert "face_on" in prompt
        assert "0.8" in prompt
        assert "driver" in prompt
        assert "tempo_ratio: 3.0" in prompt
        assert "x_factor: 42.0" in prompt

    def test_build_user_prompt_with_missing_metrics(self):
        """Test building user prompt with some missing metrics."""
        agent = ThresholdAdaptationAgent()
        session_data = {
            "gender": "female",
            "camera_angle": "down_the_line",
            "video_quality_score": 0.5,
            "detected_shot_type": "mid_iron",
            "shot_type_confidence": 0.7,
            "metrics": {
                "tempo_ratio": {"value": 4.1, "unit": "ratio"},
                "x_factor": {"value": 38.0, "unit": "deg"},
                # Missing other metrics
            },
        }
        prompt = agent.build_user_prompt(session_data)
        assert "female" in prompt
        assert "down_the_line" in prompt
        assert "tempo_ratio: 4.1" in prompt
        assert "x_factor: 38.0" in prompt
        assert "(null)" in prompt  # For missing metrics

    def test_build_user_prompt_with_null_values(self):
        """Test building user prompt with null metric values."""
        agent = ThresholdAdaptationAgent()
        session_data = {
            "gender": "male",
            "camera_angle": "face_on",
            "video_quality_score": 0.6,
            "detected_shot_type": "short_iron",
            "shot_type_confidence": 0.8,
            "metrics": {
                "tempo_ratio": {"value": None, "unit": "ratio"},
                "x_factor": {"value": 35.0, "unit": "deg"},
            },
        }
        prompt = agent.build_user_prompt(session_data)
        assert "tempo_ratio: (null)" in prompt
        assert "x_factor: 35.0" in prompt

    def test_build_user_prompt_includes_task_instructions(self):
        """Test that user prompt includes clear task instructions."""
        agent = ThresholdAdaptationAgent()
        session_data = {
            "gender": "male",
            "camera_angle": "face_on",
            "video_quality_score": 0.7,
            "detected_shot_type": "driver",
            "shot_type_confidence": 0.85,
            "metrics": {},
        }
        prompt = agent.build_user_prompt(session_data)
        assert "TASK:" in prompt
        assert "Infer this golfer's skill level" in prompt
        assert "Select appropriate base thresholds" in prompt
        assert "Apply adjustments" in prompt
        assert "Return active_thresholds" in prompt

    def test_build_user_prompt_metric_ordering(self):
        """Test that metrics are presented in the correct order."""
        agent = ThresholdAdaptationAgent()
        session_data = {
            "gender": "male",
            "camera_angle": "face_on",
            "video_quality_score": 0.7,
            "detected_shot_type": "driver",
            "shot_type_confidence": 0.85,
            "metrics": {
                metric: {"value": i + 1.0, "unit": "unit"}
                for i, metric in enumerate([
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
                ])
            },
        }
        prompt = agent.build_user_prompt(session_data)
        
        # Find positions of metrics in the prompt
        positions = {}
        for metric in session_data["metrics"].keys():
            pos = prompt.find(metric)
            if pos >= 0:
                positions[metric] = pos
        
        # Verify that all metrics appear in the correct order
        metric_list = list(session_data["metrics"].keys())
        for i in range(len(metric_list) - 1):
            assert positions[metric_list[i]] < positions[metric_list[i + 1]], \
                f"{metric_list[i]} should appear before {metric_list[i + 1]}"


class TestSkillInferenceGuidance:
    """Test that system prompt provides adequate skill inference guidance."""

    def test_system_prompt_includes_scratch_criteria(self):
        """Test that system prompt defines scratch-level criteria."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "excellent tempo" in prompt.lower()
        assert "scratch" in prompt.lower()

    def test_system_prompt_includes_beginner_criteria(self):
        """Test that system prompt defines beginner-level criteria."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "loose tempo" in prompt.lower()
        assert "beginner" in prompt.lower()

    def test_system_prompt_includes_gender_specific_guidance(self):
        """Test that system prompt provides gender-specific guidance."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        # Check for male tempo target
        assert "3.0" in prompt
        # Check for female tempo target
        assert "4.0" in prompt


class TestThresholdLogicGuidance:
    """Test that system prompt provides comprehensive threshold logic."""

    def test_system_prompt_explains_metric_width_rules(self):
        """Test that prompt explains when to widen/narrow ranges."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "~20%" in prompt
        assert "beginner" in prompt.lower()
        assert "~15%" in prompt
        assert "video_quality" in prompt.lower()

    def test_system_prompt_includes_critical_rules(self):
        """Test that critical rules are emphasized."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "CRITICAL RULES" in prompt
        assert "all 13 metrics" in prompt
        assert "Do NOT leave metrics out" in prompt
        assert "logically consistent" in prompt

    def test_system_prompt_includes_threshold_types(self):
        """Test that prompt explains all threshold types."""
        agent = ThresholdAdaptationAgent()
        prompt = agent.system_prompt
        assert "[min, max]" in prompt
        assert "green_max" in prompt
        assert "green_min" in prompt
        assert "red_below" in prompt
        assert "red_above" in prompt
        assert "green_ratio" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

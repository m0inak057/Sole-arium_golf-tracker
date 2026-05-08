"""Comprehensive tests for Agent 5 — Coaching (Phase 6).

Tests the coaching agent's LLM prompt generation, response model validation,
causal chain reasoning, and drill suggestion quality.
"""

import pytest
from backend.agents.coaching_agent import (
    CoachingItemModel,
    Agent5Response,
    CoachingAgent,
)


class TestCoachingItemModel:
    """Test the CoachingItemModel Pydantic model."""

    def test_valid_coaching_item(self) -> None:
        """Test creating a valid coaching item."""
        item = CoachingItemModel(
            priority=1,
            severity="high",
            title="Fix your hip sway",
            explanation="Your hip sway of 2.8 inches is causing spine deviation.",
            drill_suggestion="Alignment-stick hip-bump drill",
        )
        assert item.priority == 1
        assert item.severity == "high"
        assert item.title == "Fix your hip sway"
        assert "hip sway" in item.explanation
        assert "drill" in item.drill_suggestion.lower()

    def test_coaching_item_default_drill(self) -> None:
        """Test that drill_suggestion has a default empty string."""
        item = CoachingItemModel(
            priority=2,
            severity="medium",
            title="Improve tempo",
            explanation="Your tempo is inconsistent.",
        )
        assert item.drill_suggestion == ""

    def test_invalid_severity(self) -> None:
        """Test that invalid severity values are rejected."""
        with pytest.raises(ValueError):
            CoachingItemModel(
                priority=1,
                severity="extreme",  # Invalid
                title="Test",
                explanation="Test explanation",
            )

    def test_all_severity_levels(self) -> None:
        """Test that all valid severity levels are accepted."""
        for severity in ["high", "medium", "low"]:
            item = CoachingItemModel(
                priority=1,
                severity=severity,  # type: ignore
                title="Test",
                explanation="Test",
            )
            assert item.severity == severity


class TestAgent5Response:
    """Test the Agent5Response Pydantic model."""

    def test_valid_response(self) -> None:
        """Test creating a valid Agent5Response."""
        response_dict = {
            "coaching_output": [
                {
                    "priority": 1,
                    "severity": "high",
                    "title": "Fix hip sway",
                    "explanation": "Your hip sway is too much.",
                    "drill_suggestion": "Hip-bump drill",
                },
                {
                    "priority": 2,
                    "severity": "medium",
                    "title": "Improve tempo",
                    "explanation": "Your tempo is inconsistent.",
                    "drill_suggestion": "Metronome drill",
                },
            ]
        }
        response = Agent5Response(**response_dict)
        assert len(response.coaching_output) == 2
        assert response.coaching_output[0].priority == 1
        assert response.coaching_output[1].priority == 2

    def test_response_with_minimum_items(self) -> None:
        """Test response with exactly 2 items (minimum)."""
        response_dict = {
            "coaching_output": [
                {
                    "priority": 1,
                    "severity": "high",
                    "title": "Item 1",
                    "explanation": "Explanation 1",
                },
                {
                    "priority": 2,
                    "severity": "medium",
                    "title": "Item 2",
                    "explanation": "Explanation 2",
                },
            ]
        }
        response = Agent5Response(**response_dict)
        assert len(response.coaching_output) == 2

    def test_response_with_maximum_items(self) -> None:
        """Test response with exactly 4 items (maximum)."""
        response_dict = {
            "coaching_output": [
                {
                    "priority": i,
                    "severity": "high" if i == 1 else "medium",
                    "title": f"Item {i}",
                    "explanation": f"Explanation {i}",
                }
                for i in range(1, 5)
            ]
        }
        response = Agent5Response(**response_dict)
        assert len(response.coaching_output) == 4

    def test_empty_coaching_output_invalid(self) -> None:
        """Test that empty coaching_output is invalid."""
        response_dict = {"coaching_output": []}
        with pytest.raises(ValueError):
            Agent5Response(**response_dict)


class TestCoachingAgentBasics:
    """Test basic Agent 5 properties and configuration."""

    def test_agent_number(self) -> None:
        """Test that agent_number is 5."""
        agent = CoachingAgent()
        assert agent.agent_number == 5

    def test_response_model(self) -> None:
        """Test that response_model returns Agent5Response."""
        agent = CoachingAgent()
        assert agent.response_model == Agent5Response

    def test_temperature(self) -> None:
        """Test that temperature is 0.5 (slightly expressive)."""
        agent = CoachingAgent()
        assert agent.temperature == 0.5

    def test_max_tokens(self) -> None:
        """Test that max_tokens is 2000 for detailed coaching."""
        agent = CoachingAgent()
        assert agent.max_tokens == 2000

    def test_system_prompt_length(self) -> None:
        """Test that system_prompt is comprehensive (>2000 characters)."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert len(prompt) > 2000, f"Expected >2000 chars, got {len(prompt)}"

    def test_system_prompt_includes_json_schema(self) -> None:
        """Test that system_prompt includes the JSON schema."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "coaching_output" in prompt
        assert "priority" in prompt
        assert "severity" in prompt
        assert "drill_suggestion" in prompt

    def test_system_prompt_includes_strict_rules(self) -> None:
        """Test that system_prompt includes strict coaching rules."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Exactly one item has priority 1" in prompt
        assert "2 to 4 items total" in prompt
        assert "causal" in prompt.lower()


class TestCoachingSystemPromptContent:
    """Test the comprehensive content of the system prompt."""

    def test_system_prompt_includes_causal_chain_framework(self) -> None:
        """Test that system_prompt has causal chain reasoning section."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "CAUSAL CHAIN REASONING FRAMEWORK" in prompt
        assert "ROOT CAUSE" in prompt
        assert "CONSEQUENCE" in prompt

    def test_system_prompt_includes_metric_interaction_reference(self) -> None:
        """Test that system_prompt documents metric interactions."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "METRIC INTERACTION REFERENCE" in prompt
        assert "hip_sway" in prompt
        assert "spine_deviation" in prompt
        assert "x_factor" in prompt

    def test_system_prompt_includes_common_causal_chains(self) -> None:
        """Test that system_prompt includes example causal chains."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        # CHAIN 1
        assert "Hip Sway → Spine Deviation" in prompt
        # CHAIN 2
        assert "Hip/Shoulder Separation → Reduced X-Factor" in prompt or "Poor Hip/Shoulder Separation" in prompt
        # CHAIN 3
        assert "Tempo" in prompt
        # CHAIN 4
        assert "Head Movement" in prompt or "Head Sway" in prompt

    def test_system_prompt_includes_drill_framework(self) -> None:
        """Test that system_prompt has drill suggestion framework."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "DRILL SUGGESTION FRAMEWORK" in prompt
        assert "Specific" in prompt
        assert "Practical" in prompt
        assert "Actionable" in prompt
        assert "Targeted" in prompt

    def test_system_prompt_includes_drill_examples(self) -> None:
        """Test that system_prompt includes concrete drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        # Check for specific drill names
        assert "Alignment-stick" in prompt
        assert "hip-bump" in prompt or "Hip" in prompt
        assert "Metronome" in prompt
        assert "Wall drill" in prompt

    def test_system_prompt_includes_severity_framework(self) -> None:
        """Test that system_prompt has severity assignment logic."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "SEVERITY ASSIGNMENT FRAMEWORK" in prompt
        assert "HIGH SEVERITY" in prompt
        assert "MEDIUM SEVERITY" in prompt
        assert "LOW SEVERITY" in prompt

    def test_system_prompt_includes_priority_logic(self) -> None:
        """Test that system_prompt explains priority selection."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "PRIORITY SELECTION LOGIC" in prompt
        assert "Priority 1" in prompt
        assert "the ONE focus item" in prompt or "one thing to focus on" in prompt
        assert "Priority 2" in prompt or "Priority 2-4" in prompt

    def test_system_prompt_includes_skill_level_guidance(self) -> None:
        """Test that system_prompt has skill-level specific coaching."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "SKILL-LEVEL SPECIFIC COACHING" in prompt
        assert "BEGINNER" in prompt
        assert "INTERMEDIATE" in prompt
        assert "ADVANCED" in prompt or "SCRATCH" in prompt

    def test_system_prompt_includes_all_13_metrics(self) -> None:
        """Test that system_prompt mentions all 13 core metrics."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        metrics = [
            "tempo_ratio",
            "x_factor",
            "spine_deviation",
            "hip_sway",
            "head_sway",
            "hip_turn",
            "shoulder_turn",
            "side_bend",
            "hips_open",
            "wrist_lag",
            "knee_flex",
            "stance_width",
        ]
        for metric in metrics:
            assert metric in prompt, f"Metric {metric} not found in system prompt"

    def test_system_prompt_includes_number_grounding_rule(self) -> None:
        """Test that system_prompt requires specific numbers in explanations."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Grounding with Numbers" in prompt or "specific numbers" in prompt.lower()
        assert "actual values" in prompt

    def test_system_prompt_prevents_metric_invention(self) -> None:
        """Test that system_prompt forbids inventing metrics."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Do NOT invent metrics" in prompt
        assert "not in the session JSON" in prompt


class TestCoachingUserPromptBuilding:
    """Test the user prompt building method."""

    def test_build_user_prompt_basic(self) -> None:
        """Test basic user prompt building with minimal session data."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metrics": {},
                "scores": {},
            }
        }
        prompt = agent.build_user_prompt(session_data)
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "FULL SESSION JSON" in prompt
        assert "COACHING TASK" in prompt

    def test_build_user_prompt_with_scores(self) -> None:
        """Test user prompt includes score information when available."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metrics": {},
                "scores": {
                    "overall_score": 72.5,
                    "band_overall": "Developing",
                },
            }
        }
        prompt = agent.build_user_prompt(session_data)
        assert "72.5" in prompt
        assert "Developing" in prompt

    def test_build_user_prompt_with_red_metrics(self) -> None:
        """Test user prompt highlights red-band metrics."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metrics": {
                    "hip_sway": {"value": 3.2, "unit": "in"},
                    "tempo_ratio": {"value": 3.8, "unit": "ratio"},
                },
                "scores": {
                    "overall_score": 45.0,
                    "band_overall": "Beginner",
                    "per_metric": {
                        "hip_sway": {"band": "red", "score": 0.0},
                        "tempo_ratio": {"band": "red", "score": 0.0},
                    },
                },
            }
        }
        prompt = agent.build_user_prompt(session_data)
        assert "Red-Band" in prompt
        assert "hip_sway" in prompt
        assert "tempo_ratio" in prompt

    def test_build_user_prompt_with_amber_metrics(self) -> None:
        """Test user prompt highlights amber-band metrics."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metrics": {
                    "head_sway": {"value": 2.1, "unit": "in"},
                },
                "scores": {
                    "per_metric": {
                        "head_sway": {"band": "amber", "score": 0.5},
                    },
                },
            }
        }
        prompt = agent.build_user_prompt(session_data)
        assert "Amber-Band" in prompt
        assert "head_sway" in prompt

    def test_build_user_prompt_with_string_session_json(self) -> None:
        """Test user prompt handles string-serialized session JSON."""
        agent = CoachingAgent()
        session_data = {
            "session_json": '{"metrics": {}, "scores": {}}'
        }
        prompt = agent.build_user_prompt(session_data)
        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_build_user_prompt_includes_task_instructions(self) -> None:
        """Test user prompt includes clear task instructions."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {"metrics": {}, "scores": {}}
        }
        prompt = agent.build_user_prompt(session_data)
        assert "YOUR COACHING TASK" in prompt
        assert "Priority 1" in prompt
        assert "ROOT CAUSE" in prompt
        assert "CONSEQUENCE" in prompt
        assert "high-severity" in prompt or "high severity" in prompt.lower()
        assert "practical, specific drill" in prompt

    def test_build_user_prompt_no_prose_instruction(self) -> None:
        """Test user prompt emphasizes JSON-only output."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {"metrics": {}, "scores": {}}
        }
        prompt = agent.build_user_prompt(session_data)
        assert "ONLY the JSON object" in prompt
        assert "No prose" in prompt
        assert "No markdown" in prompt


class TestCausalChainReasoning:
    """Test the causal chain reasoning content in the system prompt."""

    def test_system_prompt_explains_hip_sway_spine_chain(self) -> None:
        """Test that system_prompt explains hip sway → spine deviation."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Hip Sway → Spine Deviation" in prompt
        # Check for specific explanation
        assert "forcing" in prompt.lower() or "cause" in prompt.lower()

    def test_system_prompt_explains_separation_xfactor_chain(self) -> None:
        """Test that system_prompt explains poor separation → low X-factor."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        # Check for either the section header or detailed explanation
        has_section = "Hip/Shoulder Separation → Reduced X-Factor" in prompt
        has_detail = ("separation" in prompt.lower() and "x_factor" in prompt.lower())
        assert has_section or has_detail

    def test_system_prompt_explains_tempo_consistency_chain(self) -> None:
        """Test that system_prompt explains tempo → inconsistency."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "tempo" in prompt.lower()
        # Check for impact explanation
        assert ("inconsisten" in prompt.lower() or "variability" in prompt.lower())

    def test_system_prompt_explains_head_movement_instability_chain(self) -> None:
        """Test that system_prompt explains head sway → overall instability."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Head Movement" in prompt or "Head Sway" in prompt
        assert "stability" in prompt.lower() or "kinetic chain" in prompt

    def test_system_prompt_explains_wrist_lag_speed_chain(self) -> None:
        """Test that system_prompt explains wrist lag → loss of speed."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Wrist Lag" in prompt
        assert "speed" in prompt.lower() or "release" in prompt.lower()


class TestDrillSuggestions:
    """Test drill suggestion content and quality."""

    def test_system_prompt_includes_tempo_drill_examples(self) -> None:
        """Test that system_prompt provides tempo drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "TEMPO" in prompt
        assert "Metronome" in prompt or "metronome" in prompt.lower()

    def test_system_prompt_includes_hip_sway_drill_examples(self) -> None:
        """Test that system_prompt provides hip sway drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "HIP SWAY" in prompt
        assert "hip-bump" in prompt or "Alignment" in prompt

    def test_system_prompt_includes_head_sway_drill_examples(self) -> None:
        """Test that system_prompt provides head sway drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "HEAD SWAY" in prompt
        assert "chin" in prompt.lower() or "head" in prompt.lower()

    def test_system_prompt_includes_separation_drill_examples(self) -> None:
        """Test that system_prompt provides separation drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "SEPARATION" in prompt or "Hip-lead" in prompt
        assert "separation" in prompt.lower()

    def test_system_prompt_includes_wrist_lag_drill_examples(self) -> None:
        """Test that system_prompt provides wrist lag drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "WRIST LAG" in prompt
        assert "lag preservation" in prompt.lower() or "forward press" in prompt.lower()

    def test_system_prompt_includes_stance_drill_examples(self) -> None:
        """Test that system_prompt provides stance drill examples."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "STANCE" in prompt or "Alignment" in prompt
        assert "alignment sticks" in prompt or "alignment-stick" in prompt.lower()


class TestMetricCoverage:
    """Test that all 13 metrics are covered in coaching guidance."""

    def test_system_prompt_mentions_all_13_core_metrics(self) -> None:
        """Test that all 13 core metrics are mentioned in system prompt."""
        agent = CoachingAgent()
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
            assert metric in prompt, f"Metric {metric} not mentioned in system prompt"

    def test_system_prompt_categorizes_metrics(self) -> None:
        """Test that system_prompt categorizes metrics (primary/secondary/consistency)."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Primary Faults" in prompt or "primary" in prompt.lower()
        assert "Secondary" in prompt
        assert "Consistency" in prompt


class TestRuleEnforcement:
    """Test that system prompt enforces strict coaching rules."""

    def test_system_prompt_enforces_priority_ordering(self) -> None:
        """Test that system_prompt requires priority ordering."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Index 0 has priority 1" in prompt
        assert "ascending" in prompt

    def test_system_prompt_enforces_single_priority_1(self) -> None:
        """Test that system_prompt requires exactly one priority 1 item."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Exactly one item has priority 1" in prompt

    def test_system_prompt_enforces_item_count(self) -> None:
        """Test that system_prompt enforces 2-4 item count."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "2 to 4 items total" in prompt
        assert "Never 1" in prompt or "Never more than 4" in prompt

    def test_system_prompt_requires_causal_chains_for_high_severity(self) -> None:
        """Test that system_prompt requires causal chains for high severity."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "high" in prompt.lower()
        assert "at least" in prompt.lower()
        assert "two" in prompt.lower() or "2" in prompt
        assert "metrics" in prompt.lower()

    def test_system_prompt_prevents_filler_language(self) -> None:
        """Test that system_prompt forbids hedging and filler."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "no hedging" in prompt.lower() or "hedging filler" in prompt

    def test_system_prompt_requires_number_grounding(self) -> None:
        """Test that system_prompt requires specific numbers in explanations."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "numbers" in prompt.lower()
        assert "actual values" in prompt or "specific" in prompt.lower()


class TestToneAndVoice:
    """Test that coaching tone and voice are properly specified."""

    def test_system_prompt_specifies_second_person_voice(self) -> None:
        """Test that system_prompt specifies second person ('Your')."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "second person" in prompt.lower()
        assert "'Your" in prompt or "Your" in prompt

    def test_system_prompt_forbids_emoji(self) -> None:
        """Test that system_prompt forbids emoji."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "No emoji" in prompt or "emoji" in prompt.lower()

    def test_system_prompt_forbids_unjustified_praise(self) -> None:
        """Test that system_prompt forbids praise not earned by numbers."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "No praise" in prompt or "praise" in prompt.lower()
        assert "earned" in prompt.lower() or "numbers" in prompt.lower()

    def test_system_prompt_emphasizes_professional_coach_tone(self) -> None:
        """Test that system_prompt emphasizes professional coaching tone."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "Professional" in prompt
        assert "coach" in prompt.lower()


class TestSkillLevelGuidance:
    """Test skill-level specific coaching guidance."""

    def test_system_prompt_has_beginner_guidance(self) -> None:
        """Test that system_prompt has beginner-level coaching guidance."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "BEGINNER" in prompt
        assert "fundamentals" in prompt.lower()
        assert "tempo" in prompt.lower()

    def test_system_prompt_has_intermediate_guidance(self) -> None:
        """Test that system_prompt has intermediate-level coaching guidance."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "INTERMEDIATE" in prompt
        assert "efficiency" in prompt.lower() or "combination" in prompt.lower()

    def test_system_prompt_has_advanced_guidance(self) -> None:
        """Test that system_prompt has advanced-level coaching guidance."""
        agent = CoachingAgent()
        prompt = agent.system_prompt
        assert "ADVANCED" in prompt or "SCRATCH" in prompt
        assert "consistency" in prompt.lower()
        assert "optimization" in prompt.lower()


class TestCoachingIntegration:
    """Integration tests for complete coaching scenarios."""

    def test_beginner_golfer_coaching_scenario(self) -> None:
        """Test a realistic beginner golfer coaching scenario."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metadata": {"gender": "male", "camera_angle": "face_on"},
                "metrics": {
                    "tempo_ratio": {"value": 4.2, "unit": "ratio"},
                    "hip_sway": {"value": 3.5, "unit": "in"},
                    "x_factor": {"value": 22, "unit": "degrees"},
                    "spine_deviation_max": {"value": 11, "unit": "degrees"},
                    "wrist_lag": {"value": 5, "unit": "degrees"},
                },
                "scores": {
                    "overall_score": 35.0,
                    "band_overall": "Beginner",
                    "per_metric": {
                        "tempo_ratio": {"band": "red", "score": 0.0},
                        "hip_sway": {"band": "red", "score": 0.0},
                        "x_factor": {"band": "red", "score": 0.0},
                    },
                },
            }
        }
        
        system_prompt = agent.system_prompt
        user_prompt = agent.build_user_prompt(session_data)
        
        # Verify system prompt is comprehensive
        assert len(system_prompt) > 2000
        assert "BEGINNER" in system_prompt
        assert "causal" in system_prompt.lower()
        
        # Verify user prompt highlights red metrics
        assert "Red-Band" in user_prompt
        assert "tempo_ratio" in user_prompt
        assert "hip_sway" in user_prompt

    def test_advanced_golfer_coaching_scenario(self) -> None:
        """Test a realistic advanced golfer coaching scenario."""
        agent = CoachingAgent()
        session_data = {
            "session_json": {
                "metadata": {"gender": "male", "camera_angle": "down_the_line"},
                "metrics": {
                    "tempo_ratio": {"value": 3.08, "unit": "ratio"},
                    "x_factor": {"value": 38, "unit": "degrees"},
                    "spine_deviation_max": {"value": 3.5, "unit": "degrees"},
                    "wrist_lag": {"value": 16, "unit": "degrees"},
                },
                "scores": {
                    "overall_score": 82.0,
                    "band_overall": "Proficient",
                    "per_metric": {
                        "tempo_ratio": {"band": "green", "score": 1.0},
                        "x_factor": {"band": "green", "score": 1.0},
                        "wrist_lag": {"band": "amber", "score": 0.5},
                    },
                },
            }
        }
        
        system_prompt = agent.system_prompt
        user_prompt = agent.build_user_prompt(session_data)
        
        # Verify system prompt is comprehensive
        assert "ADVANCED" in system_prompt or "SCRATCH" in system_prompt
        assert "optimization" in system_prompt.lower()
        
        # Verify user prompt reflects advanced player status
        assert "Proficient" in user_prompt
        assert "82" in user_prompt

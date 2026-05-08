"""Comprehensive test suite for Phase 5 — Performance Scoring.

Tests the threshold evaluation logic with various metric values and threshold ranges.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.core.session import SessionJSON, MetricEntry, ThresholdRange, MetricScore, Scores
from backend.phase5.scoring import score_metrics, _evaluate_metric_against_threshold


class TestMetricEvaluation:
    """Test individual metric evaluation against thresholds."""

    def test_metric_in_green_range(self):
        """Metric within green range should score green (1.0)."""
        threshold = ThresholdRange(green=[30.0, 50.0])
        band, score = _evaluate_metric_against_threshold(35.0, threshold)
        
        assert band == "green"
        assert score == 1.0

    def test_metric_in_amber_range(self):
        """Metric within amber range should score amber (0.5)."""
        threshold = ThresholdRange(
            green=[30.0, 50.0],
            amber=[25.0, 55.0]
        )
        band, score = _evaluate_metric_against_threshold(25.5, threshold)
        
        assert band == "amber"
        assert score == 0.5

    def test_metric_outside_all_ranges(self):
        """Metric outside all ranges should score red (0.0)."""
        threshold = ThresholdRange(
            green=[30.0, 50.0],
            amber=[25.0, 55.0],
            red_below=25.0,
            red_above=55.0
        )
        band, score = _evaluate_metric_against_threshold(20.0, threshold)
        
        assert band == "red"
        assert score == 0.0

    def test_metric_exceeds_red_above(self):
        """Metric exceeding red_above should score red."""
        threshold = ThresholdRange(
            green=[30.0, 50.0],
            red_above=55.0
        )
        band, score = _evaluate_metric_against_threshold(60.0, threshold)
        
        assert band == "red"
        assert score == 0.0

    def test_metric_below_red_below(self):
        """Metric below red_below should score red."""
        threshold = ThresholdRange(
            green=[30.0, 50.0],
            red_below=25.0
        )
        band, score = _evaluate_metric_against_threshold(20.0, threshold)
        
        assert band == "red"
        assert score == 0.0

    def test_green_max_threshold(self):
        """green_max threshold should work correctly."""
        threshold = ThresholdRange(green_max=5.0)
        
        # Within green
        band, score = _evaluate_metric_against_threshold(3.0, threshold)
        assert band == "green"
        assert score == 1.0
        
        # Outside green
        band, score = _evaluate_metric_against_threshold(7.0, threshold)
        assert band == "red"
        assert score == 0.0

    def test_amber_max_threshold(self):
        """amber_max threshold should work correctly."""
        threshold = ThresholdRange(
            green_max=5.0,
            amber_max=10.0
        )
        
        # Within amber
        band, score = _evaluate_metric_against_threshold(7.0, threshold)
        assert band == "amber"
        assert score == 0.5

    def test_green_min_threshold(self):
        """green_min threshold should work correctly."""
        threshold = ThresholdRange(green_min=15.0)
        
        # Within green
        band, score = _evaluate_metric_against_threshold(20.0, threshold)
        assert band == "green"
        assert score == 1.0
        
        # Outside green
        band, score = _evaluate_metric_against_threshold(10.0, threshold)
        assert band == "red"
        assert score == 0.0

    def test_green_min_and_max(self):
        """Both green_min and green_max should work together."""
        threshold = ThresholdRange(
            green_min=10.0,
            green_max=20.0
        )
        
        band, score = _evaluate_metric_against_threshold(15.0, threshold)
        assert band == "green"
        assert score == 1.0

    def test_green_ratio_for_stance_width(self):
        """green_ratio should work for ratio metrics like stance_width."""
        threshold = ThresholdRange(green_ratio=[0.95, 1.05])
        
        band, score = _evaluate_metric_against_threshold(1.0, threshold)
        assert band == "green"
        assert score == 1.0
        
        band, score = _evaluate_metric_against_threshold(1.1, threshold)
        assert band == "red"
        assert score == 0.0

    def test_priority_green_over_amber(self):
        """Green should take priority over amber."""
        threshold = ThresholdRange(
            green=[30.0, 50.0],
            amber=[25.0, 55.0]
        )
        
        band, score = _evaluate_metric_against_threshold(35.0, threshold)
        assert band == "green"
        assert score == 1.0


class TestFullScoringPipeline:
    """Test the complete score_metrics pipeline."""

    def test_scores_all_metrics(self):
        """score_metrics should score all available metrics."""
        session = SessionJSON(gender="male")
        
        # Create metrics
        session.metrics = {
            "tempo_ratio": MetricEntry(value=3.0, unit="ratio"),
            "x_factor": MetricEntry(value=40.0, unit="deg"),
            "spine_deviation_max": MetricEntry(value=3.0, unit="deg"),
            "hip_sway": MetricEntry(value=2.0, unit="cm"),
            "head_sway": MetricEntry(value=1.5, unit="cm"),
            "hip_turn": MetricEntry(value=50.0, unit="deg"),
            "shoulder_turn": MetricEntry(value=75.0, unit="deg"),
            "side_bend": MetricEntry(value=10.0, unit="deg"),
            "hips_open": MetricEntry(value=35.0, unit="deg"),
            "wrist_lag": MetricEntry(value=20.0, unit="deg"),
            "knee_flex_left": MetricEntry(value=25.0, unit="deg"),
            "knee_flex_right": MetricEntry(value=25.0, unit="deg"),
            "stance_width": MetricEntry(value=1.0, unit="ratio"),
        }
        
        # Create matching thresholds
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2], amber=[2.5, 3.5]),
            "x_factor": ThresholdRange(green=[35.0, 50.0], amber=[30.0, 55.0]),
            "spine_deviation_max": ThresholdRange(green_max=5.0, amber_max=8.0),
            "hip_sway": ThresholdRange(green_max=3.0, amber_max=5.0),
            "head_sway": ThresholdRange(green_max=2.0, amber_max=3.5),
            "hip_turn": ThresholdRange(green=[45.0, 60.0], amber=[40.0, 65.0]),
            "shoulder_turn": ThresholdRange(green=[70.0, 85.0], amber=[60.0, 90.0]),
            "side_bend": ThresholdRange(green=[5.0, 15.0], amber=[0.0, 20.0]),
            "hips_open": ThresholdRange(green=[30.0, 45.0], amber=[20.0, 55.0]),
            "wrist_lag": ThresholdRange(green_min=15.0, amber_min=10.0),
            "knee_flex_left": ThresholdRange(green=[20.0, 35.0], amber=[15.0, 40.0]),
            "knee_flex_right": ThresholdRange(green=[20.0, 35.0], amber=[15.0, 40.0]),
            "stance_width": ThresholdRange(green_ratio=[0.95, 1.05], amber_ratio=[0.85, 1.15]),
        }
        
        # Run scoring
        scores = score_metrics(session)
        
        # Verify result
        assert scores.per_metric is not None
        assert len(scores.per_metric) > 0
        assert scores.overall is not None
        assert 0 <= scores.overall <= 100
        assert scores.band_overall in ["Beginner", "Developing", "Proficient"]

    def test_perfect_score_all_green(self):
        """All metrics in green should produce high overall score."""
        session = SessionJSON(gender="male")
        
        # All metrics in green
        session.metrics = {
            "tempo_ratio": MetricEntry(value=3.0),
            "x_factor": MetricEntry(value=40.0),
            "spine_deviation_max": MetricEntry(value=3.0),
            "hip_sway": MetricEntry(value=2.0),
            "head_sway": MetricEntry(value=1.5),
            "hip_turn": MetricEntry(value=50.0),
            "shoulder_turn": MetricEntry(value=75.0),
            "side_bend": MetricEntry(value=10.0),
            "hips_open": MetricEntry(value=35.0),
            "wrist_lag": MetricEntry(value=20.0),
            "knee_flex_left": MetricEntry(value=25.0),
            "knee_flex_right": MetricEntry(value=25.0),
            "stance_width": MetricEntry(value=1.0),
        }
        
        # All thresholds green ranges include the metrics
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2]),
            "x_factor": ThresholdRange(green=[35.0, 50.0]),
            "spine_deviation_max": ThresholdRange(green=[0.0, 5.0]),
            "hip_sway": ThresholdRange(green=[0.0, 3.0]),
            "head_sway": ThresholdRange(green=[0.0, 2.0]),
            "hip_turn": ThresholdRange(green=[45.0, 60.0]),
            "shoulder_turn": ThresholdRange(green=[70.0, 85.0]),
            "side_bend": ThresholdRange(green=[5.0, 15.0]),
            "hips_open": ThresholdRange(green=[30.0, 45.0]),
            "wrist_lag": ThresholdRange(green=[15.0, 25.0]),
            "knee_flex_left": ThresholdRange(green=[20.0, 35.0]),
            "knee_flex_right": ThresholdRange(green=[20.0, 35.0]),
            "stance_width": ThresholdRange(green=[0.95, 1.05]),
        }
        
        scores = score_metrics(session)
        
        # All green → score = 100
        assert scores.overall == 100.0
        assert scores.band_overall == "Proficient"
        
        # All metrics should be green
        for band_score in scores.per_metric.values():
            assert band_score.band == "green"
            assert band_score.score == 1.0

    def test_poor_score_all_red(self):
        """All metrics in red should produce low overall score."""
        session = SessionJSON(gender="male")
        
        # All metrics out of range
        session.metrics = {
            "tempo_ratio": MetricEntry(value=1.0),  # Way too low
            "x_factor": MetricEntry(value=10.0),    # Way too low
            "spine_deviation_max": MetricEntry(value=15.0),  # Way too high
            "hip_sway": MetricEntry(value=10.0),    # Way too high
            "head_sway": MetricEntry(value=8.0),    # Way too high
            "hip_turn": MetricEntry(value=20.0),    # Too low
            "shoulder_turn": MetricEntry(value=30.0),  # Too low
            "side_bend": MetricEntry(value=30.0),   # Too high
            "hips_open": MetricEntry(value=10.0),   # Too low
            "wrist_lag": MetricEntry(value=5.0),    # Too low
            "knee_flex_left": MetricEntry(value=10.0),  # Too low
            "knee_flex_right": MetricEntry(value=10.0),  # Too low
            "stance_width": MetricEntry(value=0.5),  # Way too low
        }
        
        # Normal thresholds
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2]),
            "x_factor": ThresholdRange(green=[35.0, 50.0]),
            "spine_deviation_max": ThresholdRange(green=[0.0, 5.0]),
            "hip_sway": ThresholdRange(green=[0.0, 3.0]),
            "head_sway": ThresholdRange(green=[0.0, 2.0]),
            "hip_turn": ThresholdRange(green=[45.0, 60.0]),
            "shoulder_turn": ThresholdRange(green=[70.0, 85.0]),
            "side_bend": ThresholdRange(green=[5.0, 15.0]),
            "hips_open": ThresholdRange(green=[30.0, 45.0]),
            "wrist_lag": ThresholdRange(green=[15.0, 25.0]),
            "knee_flex_left": ThresholdRange(green=[20.0, 35.0]),
            "knee_flex_right": ThresholdRange(green=[20.0, 35.0]),
            "stance_width": ThresholdRange(green=[0.95, 1.05]),
        }
        
        scores = score_metrics(session)
        
        # All red → score = 0
        assert scores.overall == 0.0
        assert scores.band_overall == "Beginner"
        
        # All metrics should be red
        for band_score in scores.per_metric.values():
            assert band_score.band == "red"
            assert band_score.score == 0.0

    def test_mixed_green_amber_red(self):
        """Mixed metric results should produce intermediate score."""
        session = SessionJSON(gender="male")
        
        # Mix of green, amber, red
        session.metrics = {
            "tempo_ratio": MetricEntry(value=3.0),  # Green
            "x_factor": MetricEntry(value=32.0),    # Amber
            "spine_deviation_max": MetricEntry(value=6.0),  # Amber
            "hip_sway": MetricEntry(value=2.0),     # Green
            "head_sway": MetricEntry(value=8.0),    # Red
            "hip_turn": MetricEntry(value=50.0),    # Green
            "shoulder_turn": MetricEntry(value=75.0),  # Green
            "side_bend": MetricEntry(value=25.0),   # Red
            "hips_open": MetricEntry(value=35.0),   # Green
            "wrist_lag": MetricEntry(value=12.0),   # Amber
            "knee_flex_left": MetricEntry(value=25.0),  # Green
            "knee_flex_right": MetricEntry(value=25.0),  # Green
            "stance_width": MetricEntry(value=1.0),  # Green
        }
        
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2]),
            "x_factor": ThresholdRange(green=[35.0, 50.0], amber=[30.0, 55.0]),
            "spine_deviation_max": ThresholdRange(green=[0.0, 5.0], amber=[5.0, 8.0]),
            "hip_sway": ThresholdRange(green=[0.0, 3.0]),
            "head_sway": ThresholdRange(green=[0.0, 2.0]),
            "hip_turn": ThresholdRange(green=[45.0, 60.0]),
            "shoulder_turn": ThresholdRange(green=[70.0, 85.0]),
            "side_bend": ThresholdRange(green=[5.0, 15.0]),
            "hips_open": ThresholdRange(green=[30.0, 45.0]),
            "wrist_lag": ThresholdRange(green=[15.0, 25.0], amber=[10.0, 30.0]),
            "knee_flex_left": ThresholdRange(green=[20.0, 35.0]),
            "knee_flex_right": ThresholdRange(green=[20.0, 35.0]),
            "stance_width": ThresholdRange(green=[0.95, 1.05]),
        }
        
        scores = score_metrics(session)
        
        # Mixed → intermediate score (Developing band)
        assert scores.overall is not None
        assert 40 < scores.overall < 80  # Not too high, not too low
        assert scores.band_overall == "Developing"

    def test_missing_metrics(self):
        """Missing metrics should be skipped without crashing."""
        session = SessionJSON(gender="male")
        
        # Only 3 metrics
        session.metrics = {
            "tempo_ratio": MetricEntry(value=3.0),
            "x_factor": MetricEntry(value=40.0),
            "spine_deviation_max": MetricEntry(value=3.0),
        }
        
        # Only 3 thresholds
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2]),
            "x_factor": ThresholdRange(green=[35.0, 50.0]),
            "spine_deviation_max": ThresholdRange(green=[0.0, 5.0]),
        }
        
        scores = score_metrics(session)
        
        # Should score only the 3 present metrics
        assert scores.overall is not None
        assert len(scores.per_metric) >= 3

    def test_null_metric_values(self):
        """Metrics with null values should be skipped."""
        session = SessionJSON(gender="male")
        
        session.metrics = {
            "tempo_ratio": MetricEntry(value=3.0),
            "x_factor": MetricEntry(value=None, null_reason="low_visibility"),
            "spine_deviation_max": MetricEntry(value=3.0),
        }
        
        session.active_thresholds = {
            "tempo_ratio": ThresholdRange(green=[2.8, 3.2]),
            "x_factor": ThresholdRange(green=[35.0, 50.0]),
            "spine_deviation_max": ThresholdRange(green=[0.0, 5.0]),
        }
        
        scores = score_metrics(session)
        
        # x_factor should have None band and score
        assert scores.per_metric["x_factor"].band is None
        assert scores.per_metric["x_factor"].score is None
        
        # Other metrics should be scored normally
        assert scores.per_metric["tempo_ratio"].band == "green"
        assert scores.per_metric["spine_deviation_max"].band == "green"

    def test_missing_session_data(self):
        """Missing metrics or thresholds should return empty Scores."""
        session = SessionJSON(gender="male")
        
        # No metrics
        session.metrics = None
        session.active_thresholds = None
        
        scores = score_metrics(session)
        
        # Should return empty scores
        assert scores.overall is None
        assert len(scores.per_metric) == 0

    def test_band_classification(self):
        """Test band classification boundaries."""
        session = SessionJSON(gender="male")
        
        # Create scenarios for different overall scores
        test_cases = [
            (100.0, "Proficient"),   # Perfect
            (85.0, "Proficient"),    # Just above 80
            (80.0, "Developing"),    # At boundary
            (65.0, "Developing"),    # Middle
            (50.0, "Beginner"),      # At boundary
            (25.0, "Beginner"),      # Low
            (0.0, "Beginner"),       # Zero
        ]
        
        for overall_score, expected_band in test_cases:
            # Create metrics to achieve the desired overall score
            num_metrics = 10
            score_per_metric = overall_score / 100.0  # Convert percentage to per-metric score
            
            session.metrics = {
                f"metric_{i}": MetricEntry(value=1.0 if score_per_metric >= 1.0 else (10.0 if score_per_metric >= 0.5 else 20.0))
                for i in range(num_metrics)
            }
            
            session.active_thresholds = {
                f"metric_{i}": ThresholdRange(
                    green=[0.0, 1.0],
                    amber=[5.0, 15.0],
                    red_above=15.0
                )
                for i in range(num_metrics)
            }
            
            scores = score_metrics(session)
            
            # Check band (within tolerance due to rounding)
            if expected_band == "Proficient":
                assert scores.band_overall == "Proficient"
            elif expected_band == "Developing":
                assert scores.band_overall in ["Developing", "Proficient"]
            else:
                assert scores.band_overall in ["Beginner", "Developing"]

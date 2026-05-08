"""Comprehensive tests for Phase 4 — Biomechanical Metrics Calculation.

Tests all 13 metrics with:
- Happy path (valid data)
- Edge cases (missing data, null values, degenerate cases)
- Parquet reading and error handling
- Metric value ranges and validation
"""

import math
import tempfile
from pathlib import Path

import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from backend.core.session import SessionJSON, MetricEntry, Resolution
from backend.phase4.measurements import (
    angle_between_vectors_deg,
    line_angle_deg,
    distance_2d,
    get_frame_subset,
    get_frame_landmark,
    check_visibility,
    compute_all_metrics,
    _compute_stance_width,
    _compute_tempo_ratio,
    _compute_hip_sway,
    _compute_head_sway,
    _compute_hip_turn,
    _compute_shoulder_turn,
    _compute_x_factor,
    _compute_spine_deviation_max,
    _compute_side_bend,
    _compute_hips_open,
    _compute_wrist_lag,
    _compute_knee_flex_left,
    _compute_knee_flex_right,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def session_base() -> SessionJSON:
    """Create a base session for testing."""
    return SessionJSON(
        session_id="test_phase4",
        gender="male",
        resolution=Resolution(width=1920, height=1080),
        px_to_inches_scale=0.5,  # 0.5 inches per pixel
        backswing_start_frame_index=10,
        impact_frame_index=50,
        follow_through_end_frame_index=80,
        address_frame_range=[0, 8],
    )


@pytest.fixture
def sample_keypoints_df() -> pd.DataFrame:
    """Create a sample keypoints dataframe with realistic skeleton data."""
    data = []
    
    # Address frames (0-8): Static stance
    for frame in range(0, 9):
        data.extend([
            {"frame_index": frame, "landmark_name": "left_hip", "x": 0.35, "y": 0.6, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_hip", "x": 0.65, "y": 0.6, "z": 0.2, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_shoulder", "x": 0.30, "y": 0.2, "z": 0.0, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_shoulder", "x": 0.70, "y": 0.2, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "nose", "x": 0.50, "y": 0.15, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_ankle", "x": 0.30, "y": 0.9, "z": 0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_ankle", "x": 0.70, "y": 0.9, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_knee", "x": 0.32, "y": 0.7, "z": 0.08, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_knee", "x": 0.68, "y": 0.7, "z": 0.18, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_elbow", "x": 0.25, "y": 0.35, "z": -0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_elbow", "x": 0.75, "y": 0.35, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_wrist", "x": 0.20, "y": 0.4, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_wrist", "x": 0.80, "y": 0.4, "z": 0.2, "visibility": 0.95},
        ])
    
    # Backswing frames (10-35): Rotation and sway
    for frame in range(10, 36):
        # Progressive hip rotation (up to 30°)
        rotation_factor = (frame - 10) / 25.0
        hip_x_offset = 0.1 * rotation_factor
        
        # Progressive sway (up to 0.15 normalized units)
        sway_factor = rotation_factor * 0.5
        
        data.extend([
            {"frame_index": frame, "landmark_name": "left_hip", "x": 0.35 + sway_factor, "y": 0.6, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_hip", "x": 0.65 + sway_factor, "y": 0.6, "z": 0.2, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_shoulder", "x": 0.30 - hip_x_offset, "y": 0.2, "z": 0.0, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_shoulder", "x": 0.70 + hip_x_offset, "y": 0.2, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "nose", "x": 0.50 + sway_factor * 0.5, "y": 0.15, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_ankle", "x": 0.30, "y": 0.9, "z": 0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_ankle", "x": 0.70, "y": 0.9, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_knee", "x": 0.32, "y": 0.7, "z": 0.08, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_knee", "x": 0.68, "y": 0.7, "z": 0.18, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_elbow", "x": 0.25, "y": 0.35, "z": -0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_elbow", "x": 0.75, "y": 0.35, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_wrist", "x": 0.20, "y": 0.4, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_wrist", "x": 0.80, "y": 0.4, "z": 0.2, "visibility": 0.95},
        ])
    
    # Downswing frames (36-50): Acceleration toward impact
    for frame in range(36, 51):
        rotation_factor = 1.0  # Full rotation maintained
        hip_x_offset = 0.1
        
        # Head returns to center during downswing
        head_return_factor = (50 - frame) / 14.0
        
        data.extend([
            {"frame_index": frame, "landmark_name": "left_hip", "x": 0.35, "y": 0.6, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_hip", "x": 0.65, "y": 0.6, "z": 0.2, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_shoulder", "x": 0.30 - hip_x_offset, "y": 0.2, "z": 0.0, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_shoulder", "x": 0.70 + hip_x_offset, "y": 0.2, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "nose", "x": 0.50 + head_return_factor * 0.02, "y": 0.15, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_ankle", "x": 0.30, "y": 0.9, "z": 0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_ankle", "x": 0.70, "y": 0.9, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_knee", "x": 0.32, "y": 0.75, "z": 0.08, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_knee", "x": 0.68, "y": 0.65, "z": 0.18, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_elbow", "x": 0.35, "y": 0.4, "z": -0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_elbow", "x": 0.65, "y": 0.4, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_wrist", "x": 0.40, "y": 0.45, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_wrist", "x": 0.60, "y": 0.45, "z": 0.2, "visibility": 0.95},
        ])
    
    # Follow-through frames (51-80): Recovery
    for frame in range(51, 81):
        data.extend([
            {"frame_index": frame, "landmark_name": "left_hip", "x": 0.40, "y": 0.6, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_hip", "x": 0.60, "y": 0.6, "z": 0.2, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_shoulder", "x": 0.35, "y": 0.2, "z": 0.0, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_shoulder", "x": 0.65, "y": 0.2, "z": 0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "nose", "x": 0.50, "y": 0.15, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_ankle", "x": 0.30, "y": 0.9, "z": 0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_ankle", "x": 0.70, "y": 0.9, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_knee", "x": 0.35, "y": 0.8, "z": 0.08, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_knee", "x": 0.65, "y": 0.8, "z": 0.18, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_elbow", "x": 0.40, "y": 0.4, "z": -0.05, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_elbow", "x": 0.60, "y": 0.4, "z": 0.15, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "left_wrist", "x": 0.45, "y": 0.5, "z": -0.1, "visibility": 0.95},
            {"frame_index": frame, "landmark_name": "right_wrist", "x": 0.55, "y": 0.5, "z": 0.2, "visibility": 0.95},
        ])
    
    return pd.DataFrame(data)


def create_parquet_file(df: pd.DataFrame, path: Path) -> None:
    """Write a dataframe to a Parquet file."""
    table = pa.Table.from_pandas(df)
    pq.write_table(table, str(path))


# ─── Helper Function Tests ────────────────────────────────────────────────────


class TestHelperFunctions:
    """Test helper utility functions."""

    def test_angle_between_vectors_valid(self) -> None:
        """Test angle calculation with valid 3D vectors."""
        # Create a simple 90-degree angle
        p1 = pd.Series({"x": 0.0, "y": 0.0, "z": 0.0})
        p2 = pd.Series({"x": 1.0, "y": 0.0, "z": 0.0})
        p3 = pd.Series({"x": 1.0, "y": 1.0, "z": 0.0})
        
        angle = angle_between_vectors_deg(p1, p2, p3)
        assert angle is not None
        assert 89.0 < angle < 91.0  # Should be ~90 degrees

    def test_angle_between_vectors_degenerate(self) -> None:
        """Test angle calculation with zero-length vector."""
        p1 = pd.Series({"x": 0.0, "y": 0.0, "z": 0.0})
        p2 = pd.Series({"x": 0.0, "y": 0.0, "z": 0.0})  # Degenerate
        p3 = pd.Series({"x": 1.0, "y": 1.0, "z": 0.0})
        
        angle = angle_between_vectors_deg(p1, p2, p3)
        assert angle is None

    def test_line_angle_deg_valid(self) -> None:
        """Test line angle calculation."""
        p1 = pd.Series({"x": 0.0, "y": 0.0})
        p2 = pd.Series({"x": 0.5, "y": 0.5})  # 45 degrees
        
        angle = line_angle_deg(p1, p2)
        assert angle is not None
        assert 44.0 < angle < 46.0

    def test_distance_2d_valid(self) -> None:
        """Test 2D distance calculation."""
        p1 = pd.Series({"x": 0.0, "y": 0.0})
        p2 = pd.Series({"x": 0.5, "y": 0.0})
        
        distance = distance_2d(p1, p2, width=1000, height=1000)
        assert distance is not None
        assert 499.0 < distance < 501.0  # Should be ~500 pixels

    def test_check_visibility_visible(self) -> None:
        """Test visibility check with visible landmark."""
        lm = pd.Series({"visibility": 0.8})
        assert check_visibility(lm, threshold=0.5) is True

    def test_check_visibility_not_visible(self) -> None:
        """Test visibility check with non-visible landmark."""
        lm = pd.Series({"visibility": 0.3})
        assert check_visibility(lm, threshold=0.5) is False

    def test_check_visibility_none(self) -> None:
        """Test visibility check with None landmark."""
        assert check_visibility(None, threshold=0.5) is False


# ─── All 13 Metrics Tests ────────────────────────────────────────────────────


class TestAll13Metrics:
    """Test calculation of all 13 core metrics."""

    def test_metric_1_tempo_ratio_valid(self, session_base: SessionJSON) -> None:
        """Test metric 1: Tempo ratio."""
        metric = _compute_tempo_ratio(session_base)
        assert metric.value is not None
        assert metric.value > 0
        assert metric.unit == "ratio"
        assert metric.primary is True

    def test_metric_1_tempo_ratio_missing_bounds(self) -> None:
        """Test tempo ratio with missing swing bounds."""
        session = SessionJSON(session_id="test")
        metric = _compute_tempo_ratio(session)
        assert metric.value is None
        assert metric.null_reason == "Swing bounds missing"

    def test_metric_2_x_factor_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 2: X-factor."""
        metric = _compute_x_factor(sample_keypoints_df, session_base.backswing_start_frame_index, session_base.impact_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 180
        assert metric.unit == "deg"

    def test_metric_3_spine_deviation_max_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 3: Spine deviation max."""
        metric = _compute_spine_deviation_max(
            sample_keypoints_df,
            session_base.address_frame_range,
            session_base.backswing_start_frame_index,
            session_base.impact_frame_index
        )
        assert metric.value is not None
        assert metric.value >= 0
        assert metric.unit == "deg"

    def test_metric_4_hip_sway_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 4: Hip sway."""
        metric = _compute_hip_sway(sample_keypoints_df, session_base.address_frame_range, session_base.px_to_inches_scale)
        assert metric.value is not None
        assert metric.value >= 0
        assert metric.unit == "inches"
        assert metric.primary is True

    def test_metric_5_head_sway_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 5: Head sway."""
        metric = _compute_head_sway(sample_keypoints_df, session_base.address_frame_range, session_base.px_to_inches_scale)
        assert metric.value is not None
        assert metric.value >= 0
        assert metric.unit == "inches"
        assert metric.primary is True

    def test_metric_6_hip_turn_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 6: Hip turn."""
        metric = _compute_hip_turn(sample_keypoints_df, session_base.address_frame_range, session_base.impact_frame_index)
        assert metric.value is not None
        assert metric.value >= 0
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_7_shoulder_turn_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 7: Shoulder turn."""
        metric = _compute_shoulder_turn(sample_keypoints_df, session_base.address_frame_range, session_base.impact_frame_index)
        assert metric.value is not None
        assert metric.value >= 0
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_8_side_bend_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 8: Side bend."""
        metric = _compute_side_bend(sample_keypoints_df, session_base.backswing_start_frame_index, session_base.impact_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 90
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_9_hips_open_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 9: Hips open at impact."""
        metric = _compute_hips_open(sample_keypoints_df, session_base.impact_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 90
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_10_wrist_lag_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 10: Wrist lag."""
        metric = _compute_wrist_lag(sample_keypoints_df, session_base.impact_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 180
        assert metric.unit == "deg"
        assert metric.primary is False

    def test_metric_11_knee_flex_left_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 11: Knee flex left."""
        metric = _compute_knee_flex_left(sample_keypoints_df, session_base.backswing_start_frame_index, session_base.follow_through_end_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 180
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_12_knee_flex_right_valid(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test metric 12: Knee flex right."""
        metric = _compute_knee_flex_right(sample_keypoints_df, session_base.backswing_start_frame_index, session_base.follow_through_end_frame_index)
        assert metric.value is not None
        assert 0 <= metric.value <= 180
        assert metric.unit == "deg"
        assert metric.primary is True

    def test_metric_13_stance_width_valid(self, session_base: SessionJSON) -> None:
        """Test metric 13: Stance width."""
        session_base.setup_metrics = type('obj', (object,), {'stance_width_px': 300})
        metric = _compute_stance_width(session_base)
        assert metric.value is not None
        assert metric.value > 0
        assert metric.unit == "inches"
        assert metric.primary is True


# ─── Edge Cases and Error Handling ────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_missing_parquet_file(self, session_base: SessionJSON) -> None:
        """Test compute_all_metrics with missing parquet file."""
        metrics = compute_all_metrics(session_base, Path("/nonexistent/path.parquet"))
        assert metrics is not None
        # All metrics should have null_reason
        for metric in metrics.values():
            assert metric.value is None or metric.null_reason == "Keypoint data missing"

    def test_invalid_parquet_format(self, session_base: SessionJSON) -> None:
        """Test compute_all_metrics with corrupted parquet file."""
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            # Write invalid content
            f.write(b"invalid parquet content")
            temp_path = Path(f.name)
        
        try:
            metrics = compute_all_metrics(session_base, temp_path)
            assert metrics is not None
            # All metrics should have null_reason
            for metric in metrics.values():
                if metric.value is None:
                    assert "error" in metric.null_reason.lower() or metric.null_reason == "Keypoint data read error"
        finally:
            temp_path.unlink()

    def test_low_visibility_landmarks_skipped(self, sample_keypoints_df: pd.DataFrame) -> None:
        """Test that landmarks with low visibility are skipped."""
        # Create dataframe with low visibility
        low_vis_df = sample_keypoints_df.copy()
        low_vis_df.loc[low_vis_df["landmark_name"] == "left_hip", "visibility"] = 0.3
        
        # Metrics should handle gracefully (either null or use available data)
        session = SessionJSON(
            session_id="test",
            address_frame_range=[0, 8],
            backswing_start_frame_index=10,
            impact_frame_index=50,
            follow_through_end_frame_index=80,
            px_to_inches_scale=0.5,
        )
        
        # These should not crash
        metric = _compute_hip_sway(low_vis_df, session.address_frame_range, session.px_to_inches_scale)
        assert metric is not None  # Should return MetricEntry (possibly null)


# ─── Integration Tests ───────────────────────────────────────────────────────


class TestPhase4Integration:
    """Integration tests for full Phase 4 workflow."""

    def test_compute_all_metrics_full_workflow(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test compute_all_metrics with complete valid data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pq_path = Path(tmpdir) / "keypoints.parquet"
            create_parquet_file(sample_keypoints_df, pq_path)
            
            # Create a session with setup metrics
            session_base.setup_metrics = type('obj', (object,), {'stance_width_px': 300})
            
            metrics = compute_all_metrics(session_base, pq_path)
            
            # Verify we got all 13 metrics
            assert len(metrics) == 13
            metric_names = {
                "stance_width", "tempo_ratio", "x_factor", "spine_deviation_max",
                "hip_sway", "head_sway", "hip_turn", "shoulder_turn", "side_bend",
                "hips_open", "wrist_lag", "knee_flex_left", "knee_flex_right"
            }
            assert set(metrics.keys()) == metric_names
            
            # Verify each metric has proper structure
            for name, metric in metrics.items():
                assert isinstance(metric, MetricEntry)
                assert metric.unit is not None
                # Value can be None (if calculation failed) or a number
                if metric.value is not None:
                    assert isinstance(metric.value, (int, float))

    def test_all_metrics_have_units(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test that all metrics have proper units."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pq_path = Path(tmpdir) / "keypoints.parquet"
            create_parquet_file(sample_keypoints_df, pq_path)
            session_base.setup_metrics = type('obj', (object,), {'stance_width_px': 300})
            
            metrics = compute_all_metrics(session_base, pq_path)
            
            for name, metric in metrics.items():
                assert metric.unit in ["deg", "inches", "ratio"]

    def test_all_metrics_primary_flag(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test that metrics have correct primary flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pq_path = Path(tmpdir) / "keypoints.parquet"
            create_parquet_file(sample_keypoints_df, pq_path)
            session_base.setup_metrics = type('obj', (object,), {'stance_width_px': 300})
            
            metrics = compute_all_metrics(session_base, pq_path)
            
            # Wrist lag is secondary (primary=False), all others primary
            assert metrics["wrist_lag"].primary is False
            for name, metric in metrics.items():
                if name != "wrist_lag":
                    assert metric.primary is True


# ─── Value Range Tests ───────────────────────────────────────────────────────


class TestMetricValueRanges:
    """Test that metrics produce values within expected ranges."""

    def test_angle_metrics_0_to_180(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test that angle metrics are in [0, 180] degrees."""
        angle_metrics = [
            ("x_factor", _compute_x_factor(sample_keypoints_df, session_base.backswing_start_frame_index, session_base.impact_frame_index)),
            ("spine_deviation_max", _compute_spine_deviation_max(sample_keypoints_df, session_base.address_frame_range, session_base.backswing_start_frame_index, session_base.impact_frame_index)),
            ("hip_turn", _compute_hip_turn(sample_keypoints_df, session_base.address_frame_range, session_base.impact_frame_index)),
            ("shoulder_turn", _compute_shoulder_turn(sample_keypoints_df, session_base.address_frame_range, session_base.impact_frame_index)),
        ]
        
        for name, metric in angle_metrics:
            if metric.value is not None:
                assert 0 <= metric.value <= 180, f"{name} out of range: {metric.value}"

    def test_inches_metrics_positive(self, session_base: SessionJSON, sample_keypoints_df: pd.DataFrame) -> None:
        """Test that inch-based metrics are non-negative."""
        inch_metrics = [
            ("hip_sway", _compute_hip_sway(sample_keypoints_df, session_base.address_frame_range, session_base.px_to_inches_scale)),
            ("head_sway", _compute_head_sway(sample_keypoints_df, session_base.address_frame_range, session_base.px_to_inches_scale)),
        ]
        
        for name, metric in inch_metrics:
            if metric.value is not None:
                assert metric.value >= 0, f"{name} should be non-negative: {metric.value}"

    def test_tempo_ratio_positive(self, session_base: SessionJSON) -> None:
        """Test that tempo ratio is positive."""
        metric = _compute_tempo_ratio(session_base)
        if metric.value is not None:
            assert metric.value > 0

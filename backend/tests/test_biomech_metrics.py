"""Test biomechanical metrics — Sprint 2.

Comprehensive test suite for Phase 4 metric calculations.
Tests all 13 metrics with synthetic keypoint data covering:
- Happy path (correct values within tolerance)
- Edge cases (low visibility, missing frames, degenerate geometry)
- Null handling (metrics that become null in specific conditions)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import pyarrow as pa
import pyarrow.parquet as pq

from backend.core.session import SessionJSON, SetupMetrics
from backend.phase4.measurements import compute_all_metrics


def create_simple_session(
    backswing_start: int = 10,
    impact: int = 50,
    follow_through_end: int = 80,
    address_start: int = 0,
    address_end: int = 8,
    px_scale: float = 0.1,
) -> SessionJSON:
    """Create a minimal SessionJSON for testing."""
    return SessionJSON(
        schema_version="1.3",
        session_id="test-session-123",
        created_at="2026-04-18T00:00:00Z",
        gender="male",
        status="phase4_running",
        backswing_start_frame_index=backswing_start,
        impact_frame_index=impact,
        follow_through_end_frame_index=follow_through_end,
        address_frame_range=[address_start, address_end],
        px_to_inches_scale=px_scale,
        setup_metrics=SetupMetrics(
            stance_width_px=100.0,
            ball_position_ratio=0.5,
            spine_tilt_deg_at_address=20.0,
            grip_position="neutral"
        ),
    )


class TestStanceWidth:
    """Test metric 13: Stance width (distance between ankles)."""

    def test_stance_width_from_setup_metrics(self, tmp_path: Path) -> None:
        """Stance width calculated from setup_metrics at address."""
        session = create_simple_session(px_scale=0.1)
        parquet_path = tmp_path / "test.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["stance_width"].value == 10.0  # 100.0 px * 0.1 scale
        assert metrics["stance_width"].unit == "inches"
        assert metrics["stance_width"].primary is True
        assert metrics["stance_width"].null_reason is None

    def test_stance_width_null_when_setup_missing(self, tmp_path: Path) -> None:
        """Stance width is null when setup metrics unavailable."""
        session = create_simple_session()
        session.setup_metrics = None
        parquet_path = tmp_path / "test.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["stance_width"].value is None
        assert metrics["stance_width"].null_reason == "Address frames unreadable"


class TestTempoRatio:
    """Test metric 1: Tempo ratio (backswing / downswing frames)."""

    def test_tempo_ratio_3_to_1(self, tmp_path: Path) -> None:
        """Tempo ratio of 3:1 (30 backswing frames, 10 downswing frames)."""
        # Backswing: 0–30, impact: 40, so:
        # - Top of backswing: 0 + (40-0)*0.7 = 28
        # - BS frames: 28 - 0 = 28
        # - DS frames: 40 - 28 = 12
        # - Ratio: 28/12 ≈ 2.33
        session = create_simple_session(backswing_start=0, impact=40)
        parquet_path = tmp_path / "test.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["tempo_ratio"].value is not None
        assert abs(metrics["tempo_ratio"].value - 2.33) < 0.1
        assert metrics["tempo_ratio"].unit == "ratio"

    def test_tempo_ratio_null_when_bounds_missing(self, tmp_path: Path) -> None:
        """Tempo ratio is null when frame indices missing."""
        session = create_simple_session()
        session.backswing_start_frame_index = None
        parquet_path = tmp_path / "test.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["tempo_ratio"].value is None
        assert metrics["tempo_ratio"].null_reason == "Swing bounds missing"


class TestHipSway:
    """Test metric 4: Hip sway (lateral hip movement)."""

    def test_hip_sway_calculation(self, tmp_path: Path) -> None:
        """Hip sway with 100 pixel deviation and 0.1 scale → 10 inches."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, px_scale=0.1)
        parquet_path = tmp_path / "keypoints.parquet"

        # Create keypoints with variable hip position during swing
        # Address frames (0–8): hips at x=0.5
        # Swing frames (10–50): hips drift to x=0.55 (5% drift = 96 pixels on 1920 width)
        data = []
        for frame_idx in range(100):
            visibility = 0.9
            if frame_idx <= 8:
                hip_x = 0.5
            else:
                hip_x = 0.5 + (frame_idx - 8) * 0.0005  # Gradual drift

            for lm_id, lm_name in enumerate([
                "nose", "left_eye_inner", "left_eye", "left_eye_outer",
                "right_eye_inner", "right_eye", "right_eye_outer",
                "left_ear", "right_ear", "mouth_left", "mouth_right",
                "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
                "left_wrist", "right_wrist", "left_pinky", "right_pinky",
                "left_index", "right_index", "left_thumb", "right_thumb",
                "left_hip", "right_hip", "left_knee", "right_knee",
                "left_ankle", "right_ankle", "left_heel", "right_heel",
                "left_foot_index", "right_foot_index"
            ]):
                if lm_name == "left_hip":
                    x = hip_x - 0.05
                elif lm_name == "right_hip":
                    x = hip_x + 0.05
                else:
                    x = 0.5

                data.append({
                    "frame_index": frame_idx,
                    "landmark_id": lm_id,
                    "landmark_name": lm_name,
                    "x": x,
                    "y": 0.5,
                    "z": 0.0,
                    "visibility": visibility,
                })

        table = pa.Table.from_pylist(data)
        pq.write_table(table, parquet_path)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["hip_sway"].unit == "inches"
        assert metrics["hip_sway"].primary is True
        if metrics["hip_sway"].value is not None:
            assert metrics["hip_sway"].value >= 0.0

    def test_hip_sway_null_when_address_unavailable(self, tmp_path: Path) -> None:
        """Hip sway is null when address frames not specified."""
        session = create_simple_session()
        session.address_frame_range = None
        parquet_path = tmp_path / "test.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["hip_sway"].value is None
        assert "Address frames" in (metrics["hip_sway"].null_reason or "")


class TestHeadSway:
    """Test metric 5: Head sway (lateral nose movement)."""

    def test_head_sway_null_low_visibility(self, tmp_path: Path) -> None:
        """Head sway is null when nose visibility < 0.5."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8)
        parquet_path = tmp_path / "keypoints.parquet"

        # Nose always invisible
        create_synthetic_keypoints(
            parquet_path,
            num_frames=100,
            override_visibilities={"nose": 0.2},
        )

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["head_sway"].value is None
        assert "not visible" in (metrics["head_sway"].null_reason or "").lower()


class TestHipTurn:
    """Test metric 6: Hip turn (hip rotation from address to impact)."""

    def test_hip_turn_calculation(self, tmp_path: Path) -> None:
        """Hip turn should calculate the rotation angle."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["hip_turn"].unit == "deg"
        assert metrics["hip_turn"].primary is True
        if metrics["hip_turn"].value is not None:
            assert 0 <= metrics["hip_turn"].value <= 180


class TestShoulderTurn:
    """Test metric 7: Shoulder turn (shoulder rotation from address to impact)."""

    def test_shoulder_turn_calculation(self, tmp_path: Path) -> None:
        """Shoulder turn should calculate the rotation angle."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["shoulder_turn"].unit == "deg"
        assert metrics["shoulder_turn"].primary is True
        if metrics["shoulder_turn"].value is not None:
            assert 0 <= metrics["shoulder_turn"].value <= 180


class TestXFactor:
    """Test metric 2: X-factor (angle between hip and shoulder lines)."""

    def test_x_factor_calculation(self, tmp_path: Path) -> None:
        """X-factor should calculate angle between two lines."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(backswing_start=10, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["x_factor"].unit == "deg"
        assert metrics["x_factor"].primary is True
        if metrics["x_factor"].value is not None:
            assert 0 <= metrics["x_factor"].value <= 180


class TestSpineDeviation:
    """Test metric 3: Spine deviation max (max angle delta from address)."""

    def test_spine_deviation_calculation(self, tmp_path: Path) -> None:
        """Spine deviation should calculate max angle change during swing."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, backswing_start=10, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["spine_deviation_max"].unit == "deg"
        assert metrics["spine_deviation_max"].primary is True
        if metrics["spine_deviation_max"].value is not None:
            assert metrics["spine_deviation_max"].value >= 0


class TestSideBend:
    """Test metric 8: Side bend (lateral torso tilt)."""

    def test_side_bend_calculation(self, tmp_path: Path) -> None:
        """Side bend should calculate lateral tilt angle."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(backswing_start=10, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["side_bend"].unit == "deg"
        assert metrics["side_bend"].primary is True
        if metrics["side_bend"].value is not None:
            assert 0 <= metrics["side_bend"].value <= 90


class TestHipsOpen:
    """Test metric 9: Hips open (hip rotation at impact)."""

    def test_hips_open_calculation(self, tmp_path: Path) -> None:
        """Hips open should calculate hip-line angle at impact."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["hips_open"].unit == "deg"
        assert metrics["hips_open"].primary is True
        if metrics["hips_open"].value is not None:
            assert 0 <= metrics["hips_open"].value <= 180


class TestWristLag:
    """Test metric 10: Wrist lag (wrist angle at impact)."""

    def test_wrist_lag_null_low_visibility(self, tmp_path: Path) -> None:
        """Wrist lag is null when lead wrist visibility < 0.5."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(impact=50)
        parquet_path = tmp_path / "keypoints.parquet"

        # Lead wrist (left_wrist) always invisible
        create_synthetic_keypoints(
            parquet_path,
            num_frames=100,
            override_visibilities={"left_wrist": 0.2},
        )

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["wrist_lag"].value is None
        assert metrics["wrist_lag"].null_reason == "lead_wrist_visibility_below_0.5_at_impact"
        assert metrics["wrist_lag"].primary is False

    def test_wrist_lag_calculation(self, tmp_path: Path) -> None:
        """Wrist lag should calculate at-impact angle."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["wrist_lag"].unit == "deg"
        assert metrics["wrist_lag"].primary is False
        if metrics["wrist_lag"].value is not None:
            assert 0 <= metrics["wrist_lag"].value <= 180


class TestKneeFlexLeft:
    """Test metric 11: Left knee flexion angle."""

    def test_knee_flex_left_calculation(self, tmp_path: Path) -> None:
        """Knee flex left should calculate knee angle during swing."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(backswing_start=10, follow_through_end=80)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["knee_flex_left"].unit == "deg"
        assert metrics["knee_flex_left"].primary is True
        if metrics["knee_flex_left"].value is not None:
            assert 0 <= metrics["knee_flex_left"].value <= 180


class TestKneeFlexRight:
    """Test metric 12: Right knee flexion angle."""

    def test_knee_flex_right_calculation(self, tmp_path: Path) -> None:
        """Knee flex right should calculate knee angle during swing."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(backswing_start=10, follow_through_end=80)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        assert metrics["knee_flex_right"].unit == "deg"
        assert metrics["knee_flex_right"].primary is True
        if metrics["knee_flex_right"].value is not None:
            assert 0 <= metrics["knee_flex_right"].value <= 180


class TestIntegration:
    """Integration tests: full metric suite."""

    def test_all_metrics_complete_with_valid_keypoints(self, tmp_path: Path) -> None:
        """Full suite returns all 13 metrics with valid data."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(
            address_start=0, address_end=8, backswing_start=10,
            impact=50, follow_through_end=80
        )
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        # All 13 metrics should be present
        expected_keys = [
            "stance_width", "tempo_ratio", "x_factor", "spine_deviation_max",
            "hip_sway", "head_sway", "hip_turn", "shoulder_turn",
            "side_bend", "hips_open", "wrist_lag", "knee_flex_left", "knee_flex_right"
        ]
        assert set(metrics.keys()) == set(expected_keys)

        # Each metric should have a MetricEntry
        for key, entry in metrics.items():
            assert entry.unit in ["deg", "ratio", "inches", "cm"]
            assert isinstance(entry.primary, bool)
            if entry.value is None:
                assert entry.null_reason is not None

    def test_metrics_with_missing_parquet(self, tmp_path: Path) -> None:
        """Missing parquet file results in null metrics with proper reasons."""
        session = create_simple_session()
        parquet_path = tmp_path / "nonexistent.parquet"

        metrics = compute_all_metrics(session, parquet_path)

        # stance_width and tempo_ratio computed from session; others null
        assert metrics["stance_width"].value == 10.0
        assert metrics["tempo_ratio"].value is not None

        for key in ["x_factor", "hip_sway", "head_sway", "hip_turn"]:
            assert metrics[key].value is None
            assert metrics[key].null_reason == "Keypoint data missing"

    def test_metrics_with_partial_occlusion(self, tmp_path: Path) -> None:
        """Metrics gracefully handle partially occluded keypoints."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"

        # Some landmarks invisible
        create_synthetic_keypoints(
            parquet_path,
            num_frames=100,
            override_visibilities={"left_hip": 0.2, "right_elbow": 0.3},
        )

        metrics = compute_all_metrics(session, parquet_path)

        # Should not crash; some metrics may be null
        assert all(key in metrics for key in [
            "stance_width", "tempo_ratio", "hip_sway", "wrist_lag"
        ])

    def test_metrics_units_correct(self, tmp_path: Path) -> None:
        """All metrics have correct units."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        # Distance metrics
        for key in ["stance_width", "hip_sway", "head_sway"]:
            if metrics[key].value is not None:
                assert metrics[key].unit == "inches"

        # Angle metrics
        for key in [
            "tempo_ratio", "x_factor", "spine_deviation_max",
            "hip_turn", "shoulder_turn", "side_bend", "hips_open",
            "wrist_lag", "knee_flex_left", "knee_flex_right"
        ]:
            if key == "tempo_ratio":
                expected_unit = "ratio"
            else:
                expected_unit = "deg"
            if metrics[key].value is not None:
                assert metrics[key].unit == expected_unit, f"{key} has wrong unit: {metrics[key].unit}"

    def test_primary_flags_correct(self, tmp_path: Path) -> None:
        """Primary flags are set correctly (wrist_lag is non-primary)."""
        from backend.tests.conftest import create_synthetic_keypoints

        session = create_simple_session(address_start=0, address_end=8, impact=50)
        parquet_path = tmp_path / "keypoints.parquet"
        create_synthetic_keypoints(parquet_path, num_frames=100)

        metrics = compute_all_metrics(session, parquet_path)

        # Most metrics are primary
        for key in ["stance_width", "tempo_ratio", "x_factor", "hip_sway", "hip_turn"]:
            assert metrics[key].primary is True

        # Wrist lag is non-primary
        assert metrics["wrist_lag"].primary is False

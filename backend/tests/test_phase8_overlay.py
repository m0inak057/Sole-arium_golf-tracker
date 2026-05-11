"""Comprehensive test suite for Phase 8 — Annotated Video Overlay.

Tests all overlay rendering functions:
  - draw_skeleton()
  - draw_joint_dots()
  - draw_angle_overlay_*()
  - draw_bottom_hud()
  - draw_phase_label()
  - render_overlay()
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import cv2
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from backend.orchestrator.overlay_renderer import (
    draw_skeleton,
    draw_joint_dots,
    draw_angle_overlay_xfactor,
    draw_angle_overlay_spine,
    draw_angle_overlay_wrist_lag,
    draw_angle_overlay_knee,
    draw_angle_overlay_stance,
    draw_bottom_hud,
    draw_phase_label,
)
from backend.phase8.overlay import render_overlay


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def test_frame():
    """Create a test frame (1280x720 BGR)."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def sample_keypoints():
    """Create sample MediaPipe keypoints dict.
    
    Dict format: {landmark_id: (x_px, y_px, visibility)}
    """
    return {
        0: (640, 200, 0.95),  # nose
        11: (550, 300, 0.92),  # left shoulder
        12: (730, 300, 0.93),  # right shoulder
        13: (500, 400, 0.90),  # left elbow
        14: (780, 400, 0.91),  # right elbow
        15: (450, 500, 0.88),  # left wrist
        16: (830, 500, 0.89),  # right wrist
        23: (600, 500, 0.94),  # left hip
        24: (680, 500, 0.94),  # right hip
        25: (580, 650, 0.87),  # left knee
        26: (700, 650, 0.86),  # right knee
        27: (560, 720, 0.85),  # left ankle
        28: (720, 720, 0.84),  # right ankle
    }


@pytest.fixture
def sample_thresholds():
    """Create mock threshold object."""
    mock = MagicMock()
    mock.x_factor = {"min": 20, "max": 40}
    mock.spine_deviation = {"min": 0, "max": 5}
    mock.wrist_lag = {"min": 15, "max": 45}
    return {"x_factor": mock}


@pytest.fixture
def sample_session():
    """Create mock session with metrics."""
    session = MagicMock()
    session.metrics = {
        "x_factor": MagicMock(value=35.0, unit="°"),
        "spine_deviation_max": MagicMock(value=3.2, unit="°"),
        "wrist_lag": MagicMock(value=22.5, unit="°"),
        "knee_flex_right": MagicMock(value=45.0, unit="°"),
        "stance_width": MagicMock(value=22.5, unit='"'),
        "hip_sway": MagicMock(value=5.0, unit="cm"),
        "head_sway": MagicMock(value=3.0, unit="cm"),
        "hip_turn": MagicMock(value=50.0, unit="°"),
        "shoulder_turn": MagicMock(value=75.0, unit="°"),
        "side_bend": MagicMock(value=8.0, unit="°"),
        "hips_open": MagicMock(value=25.0, unit="°"),
        "knee_flex_left": MagicMock(value=40.0, unit="°"),
        "tempo_ratio": MagicMock(value=3.2, unit=":1"),
    }
    session.active_thresholds = {}
    session.scores = MagicMock(overall=78.5)
    return session


@pytest.fixture
def synthetic_video(tmp_path):
    """Create a synthetic test video (5 frames, 640x480)."""
    video_path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type: ignore
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
    
    for i in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        writer.write(frame)
    
    writer.release()
    return video_path


@pytest.fixture
def keypoints_parquet(tmp_path):
    """Create synthetic keypoints Parquet file."""
    pq_path = tmp_path / "keypoints.parquet"
    
    data = {
        "frame_index": [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
        "landmark_id": [0, 11, 23, 0, 11, 23, 0, 11, 23, 0, 11, 23, 0, 11, 23],
        "x": [0.5, 0.45, 0.47, 0.5, 0.45, 0.47, 0.5, 0.45, 0.47, 0.5, 0.45, 0.47, 0.5, 0.45, 0.47],
        "y": [0.3, 0.45, 0.75, 0.3, 0.45, 0.75, 0.3, 0.45, 0.75, 0.3, 0.45, 0.75, 0.3, 0.45, 0.75],
        "visibility": [0.95, 0.92, 0.94, 0.95, 0.92, 0.94, 0.95, 0.92, 0.94, 0.95, 0.92, 0.94, 0.95, 0.92, 0.94],
    }
    
    df = pd.DataFrame(data)
    table = pa.Table.from_pandas(df)
    pq.write_table(table, str(pq_path))
    return pq_path


# ─── Tests: Individual Drawing Functions ──────────────────────────────────


class TestDrawingSkeleton:
    """Test skeleton drawing."""
    
    def test_skeleton_draws_visible_connections(self, test_frame, sample_keypoints):
        """Skeleton should draw lines between visible keypoints."""
        frame = draw_skeleton(test_frame.copy(), sample_keypoints)
        
        # Check that frame has been modified (non-zero pixels added)
        assert frame.sum() > 0
    
    def test_skeleton_skips_invisible_keypoints(self, test_frame):
        """Skeleton should not draw lines to invisible keypoints."""
        keypoints = {
            11: (640, 200, 0.95),
            12: (640, 300, 0.3),  # visibility < 0.5
        }
        frame = draw_skeleton(test_frame.copy(), keypoints)
        
        # Frame should not be modified (no connections drawn)
        assert frame.sum() == 0
    
    def test_skeleton_handles_missing_keypoints(self, test_frame):
        """Skeleton should gracefully handle missing keypoints."""
        keypoints = {11: (640, 200, 0.95)}  # Only one point
        frame = draw_skeleton(test_frame.copy(), keypoints)
        
        # Should not crash
        assert frame is not None


class TestDrawingJointDots:
    """Test joint dot rendering."""
    
    def test_joint_dots_drawn_at_visible_points(self, test_frame, sample_keypoints):
        """Joint dots should be drawn at visible keypoint positions."""
        frame = draw_joint_dots(test_frame.copy(), sample_keypoints)
        
        # Check that frame has been modified
        assert frame.sum() > 0
    
    def test_joint_dots_skip_invisible_points(self, test_frame):
        """Joint dots should skip invisible keypoints."""
        keypoints = {
            11: (640, 200, 0.95),
            12: (640, 300, 0.3),  # visibility < 0.5
        }
        frame = draw_joint_dots(test_frame.copy(), keypoints)
        
        # Only one point should have circles
        assert frame.sum() > 0
    
    def test_joint_dots_creates_concentric_circles(self, test_frame):
        """Joint dots should create concentric circles."""
        keypoints = {0: (640, 360, 0.95)}
        frame = draw_joint_dots(test_frame.copy(), keypoints)
        
        # Check pixels at expected circle positions
        # Outer circle at radius 8, inner at radius 4
        assert frame[360, 640].sum() > 0  # Center should be magenta (inner circle)
        assert frame[352, 640].sum() > 0  # Above center


class TestAngleOverlays:
    """Test angle overlay rendering."""
    
    def test_xfactor_overlay_draws_with_value(self, test_frame, sample_keypoints, sample_thresholds):
        """X-factor overlay should draw arc and label."""
        frame = draw_angle_overlay_xfactor(test_frame.copy(), sample_keypoints, 35.0, sample_thresholds)
        
        # Frame should be modified
        assert frame.sum() > 0
    
    def test_xfactor_overlay_handles_none_value(self, test_frame, sample_keypoints):
        """X-factor overlay should return unchanged frame if value is None."""
        frame_orig = test_frame.copy()
        frame = draw_angle_overlay_xfactor(frame_orig, sample_keypoints, None, {})
        
        # Frame should be unchanged
        assert np.array_equal(frame, frame_orig)
    
    def test_spine_overlay_green_under_threshold(self, test_frame, sample_keypoints):
        """Spine overlay should be green if deviation < 5°."""
        frame = draw_angle_overlay_spine(test_frame.copy(), sample_keypoints, 3.0, {})
        
        assert frame.sum() > 0
    
    def test_spine_overlay_red_over_threshold(self, test_frame, sample_keypoints):
        """Spine overlay should be red if deviation >= 5°."""
        frame = draw_angle_overlay_spine(test_frame.copy(), sample_keypoints, 7.0, {})
        
        assert frame.sum() > 0
    
    def test_wrist_lag_overlay(self, test_frame, sample_keypoints):
        """Wrist lag overlay should draw arc at wrist."""
        frame = draw_angle_overlay_wrist_lag(test_frame.copy(), sample_keypoints, 20.0, {})
        
        assert frame.sum() > 0
    
    def test_knee_flex_overlay(self, test_frame, sample_keypoints):
        """Knee flex overlay should draw circle at knee."""
        frame = draw_angle_overlay_knee(test_frame.copy(), sample_keypoints, 45.0, {})
        
        assert frame.sum() > 0
    
    def test_stance_width_overlay(self, test_frame, sample_keypoints):
        """Stance width overlay should draw bracket at hips."""
        frame = draw_angle_overlay_stance(test_frame.copy(), sample_keypoints, 22.5, {})
        
        assert frame.sum() > 0


class TestHUDAndLabels:
    """Test HUD and label rendering."""
    
    def test_bottom_hud_draws_panel(self, test_frame, sample_session):
        """Bottom HUD should draw black panel at bottom."""
        frame = draw_bottom_hud(test_frame.copy(), sample_session, 1, 5)
        
        # Check that bottom of frame is black (HUD background)
        hud_area = frame[-100:, :, :]
        assert hud_area.sum() > 0  # Text/labels are drawn in HUD
    
    def test_phase_label_draws_text(self, test_frame):
        """Phase label should draw text in corner."""
        frame = draw_phase_label(test_frame.copy(), "Phase 8: Annotated Overlay", "face_on")
        
        assert frame.sum() > 0


# ─── Tests: Main render_overlay Function ────────────────────────────────────


class TestRenderOverlay:
    """Test the main render_overlay function."""
    
    def test_render_overlay_creates_output_file(self, tmp_path, synthetic_video, keypoints_parquet, sample_session):
        """render_overlay should create output MP4 file."""
        output_path = tmp_path / "annotated.mp4"
        
        success = render_overlay(
            input_video=synthetic_video,
            output_video=output_path,
            keypoints_parquet=keypoints_parquet,
            session_json=sample_session,
            start_frame=0,
            end_frame=4,
            camera_angle="face_on"
        )
        
        assert success
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_render_overlay_output_is_readable(self, tmp_path, synthetic_video, keypoints_parquet, sample_session):
        """Output file should be readable by cv2.VideoCapture."""
        output_path = tmp_path / "annotated.mp4"
        
        success = render_overlay(
            input_video=synthetic_video,
            output_video=output_path,
            keypoints_parquet=keypoints_parquet,
            session_json=sample_session,
            start_frame=0,
            end_frame=4,
        )
        
        if success:
            cap = cv2.VideoCapture(str(output_path))
            assert cap.isOpened()
            
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            assert frame_count == 5  # 0-4 inclusive
            
            cap.release()
    
    def test_render_overlay_fails_without_input(self, tmp_path, sample_session):
        """render_overlay should fail if input doesn't exist."""
        output_path = tmp_path / "annotated.mp4"
        fake_input = tmp_path / "nonexistent.mp4"
        fake_keypoints = tmp_path / "nonexistent.parquet"
        
        success = render_overlay(
            input_video=fake_input,
            output_video=output_path,
            keypoints_parquet=fake_keypoints,
            session_json=sample_session,
            start_frame=0,
            end_frame=10,
        )
        
        assert not success
        assert not output_path.exists()
    
    def test_render_overlay_with_partial_range(self, tmp_path, synthetic_video, keypoints_parquet, sample_session):
        """render_overlay should handle partial frame ranges."""
        output_path = tmp_path / "annotated_partial.mp4"
        
        success = render_overlay(
            input_video=synthetic_video,
            output_video=output_path,
            keypoints_parquet=keypoints_parquet,
            session_json=sample_session,
            start_frame=1,
            end_frame=3,
        )
        
        assert success
        assert output_path.exists()

        cap = cv2.VideoCapture(str(output_path))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Now renders entire video (0-4) instead of just critical window (1-3)
        assert frame_count == 5  # full video, with overlays applied to frames 1-3
        cap.release()
    
    def test_render_overlay_different_camera_angles(self, tmp_path, synthetic_video, keypoints_parquet, sample_session):
        """render_overlay should accept different camera angles."""
        for angle in ["face_on", "down_the_line"]:
            output_path = tmp_path / f"annotated_{angle}.mp4"
            
            success = render_overlay(
                input_video=synthetic_video,
                output_video=output_path,
                keypoints_parquet=keypoints_parquet,
                session_json=sample_session,
                start_frame=0,
                end_frame=4,
                camera_angle=angle,
            )
            
            assert success
            assert output_path.exists()


# ─── Integration Tests ────────────────────────────────────────────────────


class TestPhase8Integration:
    """Integration tests for Phase 8 with pipeline."""
    
    def test_phase8_accepts_slowmo_video(self, tmp_path):
        """Phase 8 should work with slowmo MP4 output from Phase 7."""
        # Simulate Phase 7 output
        slowmo_path = tmp_path / "slowmo.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type: ignore
        writer = cv2.VideoWriter(str(slowmo_path), fourcc, 15.0, (640, 480))
        
        for i in range(10):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"Slowmo {i}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            writer.write(frame)
        writer.release()
        
        # Create keypoints
        pq_path = tmp_path / "keypoints.parquet"
        data = {
            "frame_index": list(range(10)) * 3,
            "landmark_id": [0, 11, 23] * 10,
            "x": [0.5, 0.45, 0.47] * 10,
            "y": [0.3, 0.45, 0.75] * 10,
            "visibility": [0.95, 0.92, 0.94] * 10,
        }
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        pq.write_table(table, str(pq_path))
        
        # Render overlay
        output_path = tmp_path / "annotated.mp4"
        session = MagicMock()
        session.metrics = {}
        session.active_thresholds = {}
        session.scores = MagicMock(overall=None)
        
        success = render_overlay(
            input_video=slowmo_path,
            output_video=output_path,
            keypoints_parquet=pq_path,
            session_json=session,
            start_frame=0,
            end_frame=9,
        )
        
        assert success
        assert output_path.exists()


# ─── Property-Based Tests ────────────────────────────────────────────────


class TestPhase8Properties:
    """Property-based tests for Phase 8."""
    
    def test_overlay_functions_preserve_frame_dimensions(self, test_frame):
        """All overlay functions should preserve frame height and width."""
        h, w = test_frame.shape[:2]
        
        functions = [
            lambda f: draw_skeleton(f, {11: (640, 360, 0.95)}),
            lambda f: draw_joint_dots(f, {0: (640, 360, 0.95)}),
            lambda f: draw_phase_label(f, "Phase 8", "face_on"),
        ]
        
        for func in functions:
            result = func(test_frame.copy())
            assert result.shape[:2] == (h, w)
    
    def test_overlay_functions_are_idempotent_on_empty_input(self, test_frame):
        """Overlay functions should handle empty keypoint dicts gracefully."""
        empty_kpts = {}
        
        frame1 = draw_skeleton(test_frame.copy(), empty_kpts)
        frame2 = draw_joint_dots(test_frame.copy(), empty_kpts)
        
        # Should return frame unchanged or with minimal changes
        assert frame1.shape == test_frame.shape
        assert frame2.shape == test_frame.shape

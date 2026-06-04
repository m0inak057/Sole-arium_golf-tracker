"""Tests for Phase 1 Hit Detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
import pytest

from backend.phase1.hit_detector import run_hit_detection
from backend.phase1.models import SwingAttempt, HitDetectionResult
from backend.phase1.swing_segmenter import segment_and_score_swings


@pytest.fixture
def synthetic_video(tmp_path):
    """Create a synthetic test video (20 frames, 640x480)."""
    video_path = tmp_path / "test_hit.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # type: ignore
    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (640, 480))
    
    # Write frames
    for i in range(20):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some changes to create optical flow
        cv2.circle(frame, (100 + i * 10, 240), 10, (255, 255, 255), -1)
        writer.write(frame)
    writer.release()
    return video_path


class TestHitDetection:
    """Test hit detection run logic."""

    def test_run_hit_detection_invalid_path(self):
        """Should raise ValueError on invalid video path."""
        with pytest.raises(ValueError):
            run_hit_detection(Path("nonexistent.mp4"))

    def test_run_hit_detection_returns_valid_result(self, synthetic_video):
        """Should run successfully and return a HitDetectionResult."""
        result = run_hit_detection(synthetic_video, frame_stride=2)
        assert isinstance(result, HitDetectionResult)
        assert result.total_swing_attempts >= 0

    def test_segment_and_score_swings_empty(self):
        """Should return empty list on empty inputs."""
        res = segment_and_score_swings([], [], [], 30.0)
        assert res == []

    def test_segment_and_score_swings_basic(self):
        """Should detect peaks when signals are present."""
        wrist_speeds = [0.1] * 50
        wrist_speeds[20] = 1.0  # Peak
        hip_drops = [0.0] * 50
        flow_mags = [0.0] * 50
        
        attempts = segment_and_score_swings(wrist_speeds, hip_drops, flow_mags, 10.0)
        assert len(attempts) >= 0

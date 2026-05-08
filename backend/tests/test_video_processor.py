"""Test video processor — Sprint 2.

Test cases from testing.md §3 Sprint 2 for Phase 7 — Slow-Motion Rendering.

Acceptance criteria from PRD §8:
- 10-second input video → Output file exists, duration longer than input
- Backswing frame detection → Frame within first 60% of swing
- Valid MP4 output → cv2.VideoCapture opens and reads frames without error
- 0.25× speed applied → Critical section has ~4× frame count vs source
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from backend.phase7.slowmo import render_slowmo
from backend.orchestrator.video_processor import render_slowmo_clip, get_output_video_path


# ─── Fixtures ────────────────────────────────────────────────────────────────


def create_synthetic_test_video(output_path: Path, num_frames: int = 300, fps: float = 30.0) -> Path:
    """Create a synthetic test video.

    Args:
        output_path: Where to write the MP4.
        num_frames: Number of frames to generate.
        fps: Frames per second.

    Returns:
        Path to the created video.
    """
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create a frame with a changing pattern (e.g., moving rectangle)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Draw a rectangle that moves from left to right over time
        x = int((i / num_frames) * width)
        cv2.rectangle(frame, (x, 100), (x + 50, 200), (0, 255, 0), -1)
        # Write frame number in corner
        cv2.putText(frame, f"Frame {i}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(frame)

    writer.release()
    return output_path


def count_video_frames(video_path: Path) -> int:
    """Count total frames in a video.

    Args:
        video_path: Path to the video file.

    Returns:
        Number of frames, or -1 if error.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return -1
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return count


def get_video_duration(video_path: Path) -> float:
    """Get duration of a video in seconds.

    Args:
        video_path: Path to the video file.

    Returns:
        Duration in seconds, or -1 if error.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return -1.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if fps <= 0:
        return -1.0
    return frame_count / fps


# ─── Tests ──────────────────────────────────────────────────────────────────


class TestPhase7SlowMoRendering:
    """Test Phase 7 — Slow-Motion Rendering."""

    def test_render_slowmo_basic(self, tmp_path: Path) -> None:
        """Test basic slowmo rendering with synthetic video.

        Acceptance: Output file exists and can be opened.
        """
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        # Create a synthetic 10-second video at 30 fps (300 frames)
        create_synthetic_test_video(input_vid, num_frames=300, fps=30.0)

        # Render slowmo with critical window from frame 100 to 200
        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=100,
            end_frame=200,
            fps=30.0,
        )

        assert success, "render_slowmo should return True"
        assert output_vid.exists(), "Output video file should be created"

        # Verify output can be opened
        cap = cv2.VideoCapture(str(output_vid))
        assert cap.isOpened(), "Output video should be readable by cv2.VideoCapture"
        cap.release()

    def test_output_longer_than_input(self, tmp_path: Path) -> None:
        """Test that output video is longer than input (0.25× speed in critical window).

        Acceptance (PRD §8): "10-second input video → Output file exists, duration longer than input"
        """
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        # Create a 10-second video (300 frames at 30 fps)
        create_synthetic_test_video(input_vid, num_frames=300, fps=30.0)

        # Critical window: frames 80–220 (140 frames × 4 = 560 output frames)
        # Other frames: 80 + 80 = 160 frames
        # Total output: 560 + 160 = 720 frames
        render_slowmo(
            input_vid,
            output_vid,
            start_frame=80,
            end_frame=220,
            fps=30.0,
        )

        input_frames = count_video_frames(input_vid)
        output_frames = count_video_frames(output_vid)

        assert input_frames > 0, "Input video should have frames"
        assert output_frames > input_frames, "Output video should have more frames than input"

        # Expected: 80 + (140 × 4) + 80 = 720
        expected_frames = 80 + (220 - 80 + 1) * 4 + (300 - 220 - 1)
        # Allow some tolerance (±10 frames)
        assert abs(output_frames - expected_frames) <= 10, (
            f"Output should have ~{expected_frames} frames, got {output_frames}"
        )

    def test_critical_window_4x_frame_count(self, tmp_path: Path) -> None:
        """Test that critical window has 4× frame count.

        Acceptance (PRD §8): "0.25× speed applied → Critical section has ~4× frame count vs source"
        """
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=300, fps=30.0)

        # Critical window: frames 100–150 (51 frames)
        # Expected output frames in critical: 51 × 4 = 204
        render_slowmo(
            input_vid,
            output_vid,
            start_frame=100,
            end_frame=150,
            fps=30.0,
        )

        output_frames = count_video_frames(output_vid)
        critical_frames = (150 - 100 + 1)
        expected_critical_in_output = critical_frames * 4

        # Total should be: pre-critical (100) + critical (204) + post-critical (149)
        expected_total = 100 + expected_critical_in_output + (300 - 150 - 1)
        assert abs(output_frames - expected_total) <= 10, (
            f"Expected ~{expected_total} frames, got {output_frames}"
        )

    def test_output_valid_mp4(self, tmp_path: Path) -> None:
        """Test that output is a valid, readable MP4.

        Acceptance (PRD §8): "Valid MP4 output → cv2.VideoCapture opens and reads frames without error"
        """
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=150, fps=30.0)
        render_slowmo(
            input_vid,
            output_vid,
            start_frame=30,
            end_frame=120,
            fps=30.0,
        )

        cap = cv2.VideoCapture(str(output_vid))
        assert cap.isOpened(), "Output should be openable"

        # Read a few frames to verify integrity
        frame_count = 0
        while frame_count < 5:
            ret, frame = cap.read()
            if not ret:
                break
            assert frame is not None, "Frame should be readable"
            frame_count += 1

        cap.release()
        assert frame_count > 0, "Should be able to read at least one frame"

    def test_edge_case_no_critical_window(self, tmp_path: Path) -> None:
        """Test behavior when critical window is entire video."""
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=100, fps=30.0)

        # Entire video is critical
        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=0,
            end_frame=99,
            fps=30.0,
        )

        assert success, "Should handle entire video as critical window"
        output_frames = count_video_frames(output_vid)
        assert output_frames == 100 * 4, "All frames should be duplicated 4×"

    def test_edge_case_small_critical_window(self, tmp_path: Path) -> None:
        """Test behavior with very small critical window."""
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=100, fps=30.0)

        # Single frame critical window
        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=50,
            end_frame=50,
            fps=30.0,
        )

        assert success, "Should handle single-frame critical window"
        output_frames = count_video_frames(output_vid)
        # 50 + (1 × 4) + 49 = 103
        assert abs(output_frames - 103) <= 1, f"Expected 103 frames, got {output_frames}"

    def test_invalid_frame_range(self, tmp_path: Path) -> None:
        """Test that invalid frame ranges are rejected."""
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=100, fps=30.0)

        # start_frame >= end_frame is invalid
        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=100,
            end_frame=50,
            fps=30.0,
        )

        assert not success, "Should reject invalid frame range"
        assert not output_vid.exists(), "Output should not be created on failure"

    def test_invalid_fps(self, tmp_path: Path) -> None:
        """Test that invalid FPS is rejected."""
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=100, fps=30.0)

        # fps <= 0 is invalid
        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=10,
            end_frame=90,
            fps=0.0,
        )

        assert not success, "Should reject invalid FPS"

    def test_missing_input_file(self, tmp_path: Path) -> None:
        """Test handling of missing input file."""
        input_vid = tmp_path / "nonexistent.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        success = render_slowmo(
            input_vid,
            output_vid,
            start_frame=10,
            end_frame=90,
            fps=30.0,
        )

        assert not success, "Should handle missing input file gracefully"


class TestVideoProcessorWrapper:
    """Test the wrapper functions in video_processor.py."""

    def test_render_slowmo_clip_wrapper(self, tmp_path: Path) -> None:
        """Test render_slowmo_clip wrapper function."""
        input_vid = tmp_path / "input.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        create_synthetic_test_video(input_vid, num_frames=300, fps=30.0)

        result = render_slowmo_clip(
            input_vid,
            output_vid,
            backswing_start=80,
            follow_through_end=220,
            original_fps=30.0,
        )

        assert result == output_vid, "Should return the output path"
        assert output_vid.exists(), "Output should be created"

    def test_render_slowmo_clip_failure_raises(self, tmp_path: Path) -> None:
        """Test that render_slowmo_clip raises ValueError on failure."""
        input_vid = tmp_path / "nonexistent.mp4"
        output_vid = tmp_path / "slowmo.mp4"

        with pytest.raises(ValueError, match="Failed to render slowmo"):
            render_slowmo_clip(
                input_vid,
                output_vid,
                backswing_start=10,
                follow_through_end=90,
                original_fps=30.0,
            )

    def test_get_output_video_path_slowmo(self, tmp_path: Path) -> None:
        """Test get_output_video_path for slowmo."""
        result = get_output_video_path(tmp_path, "slowmo")
        assert result == tmp_path / "slowmo.mp4"

    def test_get_output_video_path_annotated(self, tmp_path: Path) -> None:
        """Test get_output_video_path for annotated."""
        result = get_output_video_path(tmp_path, "annotated")
        assert result == tmp_path / "annotated.mp4"

    def test_get_output_video_path_invalid(self, tmp_path: Path) -> None:
        """Test get_output_video_path with invalid kind."""
        with pytest.raises(ValueError, match="Unknown video kind"):
            get_output_video_path(tmp_path, "invalid")


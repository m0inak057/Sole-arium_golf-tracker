"""Hit detector — Phase 1 core logic.

Processes the entire video to extract frame-level wrist speeds, hip drops,
and optical flow. Hands off to the swing segmenter, then packages the result.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe.python.solutions.pose as mp_pose
import numpy as np

from backend.phase1.models import HitDetectionResult
from backend.phase1.optical_flow_utils import compute_frame_flow_magnitude
from backend.phase1.swing_segmenter import segment_and_score_swings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def run_hit_detection(video_path: Path, frame_stride: int = 2) -> HitDetectionResult:
    """Run the Phase 1 hit detection over the given video.

    Args:
        video_path: Path to the input video.
        frame_stride: Process every Nth frame for speed (default=2 for ~2× speedup).
            Peak indices are rescaled back to original frame space.

    Returns:
        A ``HitDetectionResult`` populated with candidate swing info.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    stride_fps = fps / frame_stride  # effective fps for signal

    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1)

    wrist_speeds: list[float] = []
    hip_drops: list[float] = []
    flow_mags: list[float] = []

    prev_gray: np.ndarray | None = None
    prev_wrist_y: float | None = None

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        # Only process every Nth frame for speed
        if frame_idx % frame_stride == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. Optical flow (compare against previous processed frame)
            if prev_gray is not None:
                flow_mag = compute_frame_flow_magnitude(prev_gray, gray)
            else:
                flow_mag = 0.0
            flow_mags.append(flow_mag)
            prev_gray = gray

            # 2. Keypoints (Wrist speed, Hip drop)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)

            wrist_speed = 0.0
            hip_drop = 0.0

            if result.pose_landmarks:
                lms = result.pose_landmarks.landmark
                curr_wrist_y = (lms[15].y + lms[16].y) / 2.0
                if prev_wrist_y is not None:
                    wrist_speed = abs(curr_wrist_y - prev_wrist_y)
                prev_wrist_y = curr_wrist_y
                hip_drop = (lms[23].y + lms[24].y) / 2.0

            wrist_speeds.append(wrist_speed)
            hip_drops.append(hip_drop)

        frame_idx += 1

    cap.release()
    pose.close()

    # Clean up hip drops — convert to deltas (downward movement only)
    filtered_hip_drops = [0.0]
    for i in range(1, len(hip_drops)):
        # Positive drop is when current y > prev y (moving down)
        delta = hip_drops[i] - hip_drops[i-1]
        filtered_hip_drops.append(delta if delta > 0 else 0.0)

    attempts = segment_and_score_swings(wrist_speeds, filtered_hip_drops, flow_mags, stride_fps)

    # Rescale peak frame indices from stride space back to original frame space
    for a in attempts:
        a.backswing_start_frame_index *= frame_stride
        a.impact_frame_index *= frame_stride
        a.follow_through_end_frame_index *= frame_stride
        a.address_frame_range = [a.address_frame_range[0] * frame_stride,
                                  a.address_frame_range[1] * frame_stride]

    real_attempts = [a for a in attempts if a.is_real]
    if not real_attempts:
        # Fallback to the highest scoring if no "real" found
        if attempts:
            best = max(attempts, key=lambda x: x.score)
        else:
            return HitDetectionResult(
                total_swing_attempts=0,
                selected_swing_index=None,
                hit_confidence_score=None,
                backswing_start_frame_index=None,
                impact_frame_index=None,
                follow_through_end_frame_index=None,
                address_frame_range=None,
                all_attempts=[],
            )
    else:
        best = max(real_attempts, key=lambda x: x.score)

    return HitDetectionResult(
        total_swing_attempts=len(attempts),
        selected_swing_index=best.attempt_index,
        hit_confidence_score=best.score,
        backswing_start_frame_index=best.backswing_start_frame_index,
        impact_frame_index=best.impact_frame_index,
        follow_through_end_frame_index=best.follow_through_end_frame_index,
        address_frame_range=best.address_frame_range,
        all_attempts=real_attempts if real_attempts else [best],
    )



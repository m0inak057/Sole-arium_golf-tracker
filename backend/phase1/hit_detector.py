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


def run_hit_detection(video_path: Path) -> HitDetectionResult:
    """Run the Phase 1 hit detection over the given video.

    Args:
        video_path: Path to the input video.

    Returns:
        A ``HitDetectionResult`` populated with candidate swing info.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    pose = mp_pose.Pose(static_image_mode=False, model_complexity=1)

    wrist_speeds: list[float] = []
    hip_drops: list[float] = []
    flow_mags: list[float] = []

    prev_gray: np.ndarray | None = None
    prev_wrist_y: float | None = None

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 1. Optical flow
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
            # Indices: left_wrist 15, right_wrist 16
            # Use average y-position of wrists for simple speed proxy
            curr_wrist_y = (lms[15].y + lms[16].y) / 2.0
            if prev_wrist_y is not None:
                # Speed as absolute vertical pixel delta (normalized 0-1 coordinate space, so we use direct delta)
                wrist_speed = abs(curr_wrist_y - prev_wrist_y)
            prev_wrist_y = curr_wrist_y

            # Indices: left_hip 23, right_hip 24
            # Hip drop is amount hips move DOWN (higher y value)
            hip_drop = (lms[23].y + lms[24].y) / 2.0
            # To actually make it a drop, we might just look at variance or raw down-movement.
            # Storing raw hip avg y, the segmenter will normalize it.

        wrist_speeds.append(wrist_speed)
        hip_drops.append(hip_drop)

    cap.release()
    pose.close()

    # If hips didn't drop, maybe relative hip movement
    # Let's clean up hip drops so they are derivatives too
    filtered_hip_drops = [0.0]
    for i in range(1, len(hip_drops)):
        # Positive drop is when current y > prev y (moving down)
        delta = hip_drops[i] - hip_drops[i-1]
        filtered_hip_drops.append(delta if delta > 0 else 0.0)

    attempts = segment_and_score_swings(wrist_speeds, filtered_hip_drops, flow_mags, fps)

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
    )


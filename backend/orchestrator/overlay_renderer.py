"""Overlay renderer — annotated video rendering.

All overlay logic lives here.  No drawing code lives anywhere else.
Full implementation in Sprint 3 (Phase 8).
See architecture.md §4 Phase 8 and project-structure.md §overlay.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ── Public rendering functions (Sprint 3) ────────────────────────────────────
# Rendering order is strict: skeleton → dots → overlays → HUD


def draw_skeleton(frame: np.ndarray, keypoints: Any) -> np.ndarray:
    """Draw connected skeleton limb lines on the frame.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data for the current frame.

    Returns:
        Frame with skeleton drawn.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_joint_dots(frame: np.ndarray, keypoints: Any) -> np.ndarray:
    """Draw concentric circles at each keypoint.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data for the current frame.

    Returns:
        Frame with joint dots drawn.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_angle_overlay_xfactor(
    frame: np.ndarray, keypoints: Any, x_factor_deg: float, thresholds: Any
) -> np.ndarray:
    """Draw X-Factor arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data.
        x_factor_deg: Measured X-Factor in degrees.
        thresholds: Active thresholds for colour coding.

    Returns:
        Frame with X-Factor overlay.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_angle_overlay_spine(
    frame: np.ndarray, keypoints: Any, spine_dev_deg: float, thresholds: Any
) -> np.ndarray:
    """Draw spine deviation axis line overlay.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data.
        spine_dev_deg: Spine deviation in degrees.
        thresholds: Active thresholds for colour coding.

    Returns:
        Frame with spine overlay.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_angle_overlay_wrist_lag(
    frame: np.ndarray, keypoints: Any, wrist_lag_deg: float, thresholds: Any
) -> np.ndarray:
    """Draw wrist lag angle arc overlay.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data.
        wrist_lag_deg: Wrist lag in degrees.
        thresholds: Active thresholds.

    Returns:
        Frame with wrist lag overlay.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_angle_overlay_knee(
    frame: np.ndarray, keypoints: Any, knee_flex_deg: float, weight_shift_vec: Any
) -> np.ndarray:
    """Draw knee flex and weight shift overlay.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data.
        knee_flex_deg: Knee flex in degrees.
        weight_shift_vec: Weight transfer direction vector.

    Returns:
        Frame with knee overlay.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_angle_overlay_stance(
    frame: np.ndarray, keypoints: Any, stance_cm: float, shot_type: str
) -> np.ndarray:
    """Draw stance width bracket overlay.

    Args:
        frame: BGR image array.
        keypoints: Keypoint data.
        stance_cm: Stance width in centimetres (converted at render time).
        shot_type: Detected shot type for colour coding.

    Returns:
        Frame with stance bracket overlay.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_bottom_hud(
    frame: np.ndarray, metrics: Any, phase_label: str, progress: float
) -> np.ndarray:
    """Draw the bottom HUD panel (18–20% of frame height).

    Args:
        frame: BGR image array.
        metrics: Current metric values for display.
        phase_label: Current swing phase label string.
        progress: Progress bar value 0.0–1.0.

    Returns:
        Frame with HUD panel drawn.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_phase_label(
    frame: np.ndarray, phase_state: str, swing_number: int
) -> np.ndarray:
    """Draw the swing phase label inside the HUD.

    Args:
        frame: BGR image array.
        phase_state: Current phase (e.g. ``"backswing"``, ``"impact"``).
        swing_number: Current swing number.

    Returns:
        Frame with phase label drawn.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")


def draw_frame_counter(
    frame: np.ndarray, frame_index: int, total_frames: int
) -> np.ndarray:
    """Draw a frame counter on the overlay.

    Args:
        frame: BGR image array.
        frame_index: Current frame index.
        total_frames: Total number of frames.

    Returns:
        Frame with counter drawn.
    """
    raise NotImplementedError("Phase 8 — Sprint 3")

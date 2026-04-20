"""Optical flow utilities for ball motion detection.

Calculates dense optical flow between frames to detect sudden fast movements
indicative of a golf club hitting a ball.
"""

import cv2
import numpy as np


def compute_frame_flow_magnitude(prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
    """Compute the 95th percentile optical flow magnitude between two frames.
    
    This helps filter out slow moving body parts while capturing the
    fast-moving club head / ball at impact.

    Args:
        prev_gray: Previous frame (grayscale).
        curr_gray: Current frame (grayscale).

    Returns:
        A float representing the motion metric.
    """
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
    )
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return float(np.percentile(magnitude, 95))


"""Swing segmenter — identifies swing boundaries Phase 1 core logic.

Analyzes frame-level signals to isolate and score candidate swing attempt segments.
"""

from __future__ import annotations

import numpy as np

from backend.phase1.models import SwingAttempt


def segment_and_score_swings(
    wrist_speeds: list[float],
    hip_drops: list[float],
    flow_mags: list[float],
    fps: float,
) -> list[SwingAttempt]:
    """Find and score candidate swings based on temporal signals.

    Combines the three signals with weights 0.5 (wrist), 0.3 (hip), 0.2 (flow).
    Scores each attempt. Any attempt with score > 0.65 is REAL.

    Args:
        wrist_speeds: Sequence of wrist velocity magnitdues per frame.
        hip_drops: Sequence of vertical hip drops per frame.
        flow_mags: Sequence of optical flow magnitudes per frame.
        fps: The frame rate.

    Returns:
        List of candidate ``SwingAttempt`` objects.
    """
    frame_count = len(wrist_speeds)
    if frame_count == 0:
        return []

    # Normalize signals
    def normalize(sig: list[float]) -> np.ndarray:
        arr = np.array(sig, dtype=float)
        mx = np.max(arr) if len(arr) > 0 and np.max(arr) > 0 else 1.0
        return arr / mx

    norm_wrist = normalize(wrist_speeds)
    norm_hip = normalize(hip_drops)
    norm_flow = normalize(flow_mags)

    # Combined score series
    combined = 0.5 * norm_wrist + 0.3 * norm_hip + 0.2 * norm_flow

    # Very naive peak finding for "impact frame"
    # Find peaks separated by at least 1 second (1 * fps)
    min_dist = int(fps)
    attempts = []
    
    # Smooth a bit to avoid local noisy peaks
    if frame_count > 5:
        smoothed = np.convolve(combined, np.ones(5)/5, mode='same')
    else:
        smoothed = combined

    attempt_idx = 0
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(smoothed, distance=min_dist, height=0.2)

    for peak in peaks:
        score = smoothed[peak]
        
        # Determine temporal windows bounds naively:
        # backswing starts roughly 1.5s before impact
        bs_start = max(0, peak - int(1.5 * fps))
        # follow through ends roughly 0.5s after impact
        ft_end = min(frame_count - 1, peak + int(0.5 * fps))
        
        # address is roughly another 1s before backswing
        address_start = max(0, bs_start - int(1.0 * fps))
        
        attempt = SwingAttempt(
            attempt_index=attempt_idx,
            score=float(score),
            is_real=float(score) > 0.65,
            backswing_start_frame_index=bs_start,
            impact_frame_index=peak,
            follow_through_end_frame_index=ft_end,
            address_frame_range=[address_start, bs_start],
        )
        attempts.append(attempt)
        attempt_idx += 1

    return attempts


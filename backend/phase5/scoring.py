"""Performance scoring — Phase 5 core logic.

Compares Phase 4 metrics against Agent 4 thresholds to produce banded scores.

Scoring logic:
  - GREEN (1.0): Metric within green range
  - AMBER (0.5): Metric within amber range
  - RED (0.0): Metric outside all ranges

Overall score: (sum of per-metric scores / count) * 100
Band mapping: >80 = Proficient, >50 = Developing, ≤50 = Beginner
"""

from __future__ import annotations

from backend.core.session import SessionJSON, MetricScore, Scores, ThresholdRange
from backend.core.logging import get_logger

logger = get_logger(__name__)

# The 13 metrics that Phase 4 produces and Phase 5 scores
METRIC_KEYS = [
    "tempo_ratio",
    "x_factor",
    "spine_deviation_max",
    "hip_sway",
    "head_sway",
    "hip_turn",
    "shoulder_turn",
    "side_bend",
    "hips_open",
    "wrist_lag",
    "knee_flex_left",
    "knee_flex_right",
    "stance_width",
]


def _evaluate_metric_against_threshold(
    value: float, threshold: ThresholdRange
) -> tuple[str, float]:
    """Evaluate a single metric value against its threshold.

    Scoring rules (applied in order):
      1. If green range exists and value is in it → GREEN (1.0)
      2. If amber range exists and value is in it → AMBER (0.5)
      3. If red bounds exist and value violates them → RED (0.0)
      4. Else → RED (0.0)

    Args:
        value: The measured metric value.
        threshold: The ThresholdRange object with green/amber/red bounds.

    Returns:
        Tuple of (band_str, score_val) where band_str is "green"/"amber"/"red"
        and score_val is 1.0/0.5/0.0.
    """
    # Rule 1: Check green range (two-element list [min, max])
    if threshold.green and len(threshold.green) >= 2:
        if threshold.green[0] <= value <= threshold.green[1]:
            return ("green", 1.0)

    # Rule 1b: Check green_min/green_max (single-sided bounds)
    if threshold.green_min is not None and threshold.green_max is not None:
        if threshold.green_min <= value <= threshold.green_max:
            return ("green", 1.0)
    elif threshold.green_min is not None:
        if value >= threshold.green_min:
            return ("green", 1.0)
    elif threshold.green_max is not None:
        if value <= threshold.green_max:
            return ("green", 1.0)

    # Rule 1c: Check green_ratio (for ratio metrics like stance_width)
    if threshold.green_ratio and len(threshold.green_ratio) >= 2:
        if threshold.green_ratio[0] <= value <= threshold.green_ratio[1]:
            return ("green", 1.0)

    # Rule 2: Check amber range (two-element list [min, max])
    if threshold.amber and len(threshold.amber) >= 2:
        if threshold.amber[0] <= value <= threshold.amber[1]:
            return ("amber", 0.5)

    # Rule 2b: Check amber_min/amber_max (single-sided bounds)
    if threshold.amber_min is not None and threshold.amber_max is not None:
        if threshold.amber_min <= value <= threshold.amber_max:
            return ("amber", 0.5)
    elif threshold.amber_min is not None:
        if value >= threshold.amber_min:
            return ("amber", 0.5)
    elif threshold.amber_max is not None:
        if value <= threshold.amber_max:
            return ("amber", 0.5)

    # Rule 2c: Check amber_ratio (for ratio metrics)
    if threshold.amber_ratio and len(threshold.amber_ratio) >= 2:
        if threshold.amber_ratio[0] <= value <= threshold.amber_ratio[1]:
            return ("amber", 0.5)

    # Rule 3: Check red bounds (red_below and red_above are explicit violations)
    if threshold.red_below is not None and value < threshold.red_below:
        return ("red", 0.0)
    if threshold.red_above is not None and value > threshold.red_above:
        return ("red", 0.0)

    # Rule 4: Default to red
    return ("red", 0.0)


def score_metrics(session: SessionJSON) -> Scores:
    """Compare metrics against thresholds to produce scores.

    Workflow:
      1. Validate session has metrics and thresholds
      2. For each metric:
         a. Get metric value from session.metrics
         b. Get threshold from session.active_thresholds
         c. Evaluate value against threshold → (band, score)
         d. Store in per_metric dict
      3. Calculate overall score and band

    Args:
        session: Session with extracted Phase 4 metrics and Agent 4 thresholds.

    Returns:
        A ``Scores`` object with per-metric mapping and overall grade.
    """
    scores = Scores()

    # Validate inputs
    if not getattr(session, "metrics", None) or not getattr(session, "active_thresholds", None):
        logger.warning("Phase 5: Missing metrics or thresholds")
        return scores

    metrics = session.metrics
    thresholds = session.active_thresholds

    if not isinstance(metrics, dict) or not isinstance(thresholds, dict):
        logger.warning("Phase 5: Metrics or thresholds not dict-like")
        return scores

    total_score = 0.0
    count = 0

    # Score each metric
    for key in METRIC_KEYS:
        metric = metrics.get(key)
        threshold = thresholds.get(key)

        # If metric is missing or has no value, mark as unscored
        if not metric or metric.value is None:
            scores.per_metric[key] = MetricScore(band=None, score=None)
            logger.debug(f"Phase 5: Skipping {key} (no value)")
            continue

        # If threshold is missing, mark as unscored (shouldn't happen if Agent 4 ran)
        if not threshold:
            scores.per_metric[key] = MetricScore(band=None, score=None)
            logger.warning(f"Phase 5: No threshold for {key}")
            continue

        # Evaluate metric against threshold
        try:
            band, score_val = _evaluate_metric_against_threshold(metric.value, threshold)
            scores.per_metric[key] = MetricScore(band=band, score=score_val)
            total_score += score_val
            count += 1
            logger.debug(f"Phase 5: {key} = {metric.value} → {band} ({score_val})")
        except Exception as e:
            logger.error(f"Phase 5: Error scoring {key}: {e}")
            scores.per_metric[key] = MetricScore(band=None, score=None)
            continue

    # Calculate overall score and band
    if count > 0:
        overall = (total_score / count) * 100.0
        scores.overall = round(overall, 1)

        # Band classification (per PRD)
        if overall > 80:
            scores.band_overall = "Proficient"
        elif overall > 50:
            scores.band_overall = "Developing"
        else:
            scores.band_overall = "Beginner"

        logger.info(
            f"Phase 5: Overall score {scores.overall:.1f}, "
            f"band {scores.band_overall} ({count} metrics)"
        )
    else:
        logger.warning("Phase 5: No metrics scored")

    return scores

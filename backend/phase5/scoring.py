"""Performance scoring — Phase 5 core logic.

Compares Phase 4 metrics against Agent 4 thresholds to produce banded scores.
"""

from __future__ import annotations

from backend.core.session import SessionJSON, MetricScore, Scores
from backend.core.logging import get_logger

logger = get_logger(__name__)


def score_metrics(session: SessionJSON) -> Scores:
    """Compare metrics against thresholds to produce scores.

    Args:
        session: Session with extracted Phase 4 metrics and Agent 4 thresholds.

    Returns:
        A ``Scores`` object with per-metric mapping and overall grade.
    """
    if not getattr(session, "metrics", None) or not getattr(session, "active_thresholds", None):
        return Scores()

    scores = Scores()
    total_score = 0.0
    count = 0

    for key, threshold in session.active_thresholds.items():
        metric = session.metrics.get(key)
        if not metric or metric.value is None:
            scores.per_metric[key] = MetricScore(band=None, score=None)
            continue

        val = metric.value
        band = "red"
        score_val = 0.0

        # Extremely simple mock scoring heuristic for Sprint 3 fallback
        # Real logic evaluates `val` against bounds
        if threshold.green and len(threshold.green) == 2:
            if threshold.green[0] <= val <= threshold.green[1]:
                band = "green"
                score_val = 1.0
            elif threshold.amber and len(threshold.amber) == 2:
                if threshold.amber[0] <= val <= threshold.amber[1]:
                    band = "amber"
                    score_val = 0.5
        elif threshold.green_max:
            if val <= threshold.green_max:
                band = "green"
                score_val = 1.0
            elif threshold.amber_max and val <= threshold.amber_max:
                band = "amber"
                score_val = 0.5
                
        # ... logic continues mapping ...
        if band == "red":
            band = "red"  # Actually handle red logic

        scores.per_metric[key] = MetricScore(band=band, score=score_val)
        total_score += score_val
        count += 1

    if count > 0:
        overall = (total_score / count) * 100
        scores.overall = round(overall, 1)
        if overall > 80:
            scores.band_overall = "Proficient"
        elif overall > 50:
            scores.band_overall = "Developing"
        else:
            scores.band_overall = "Beginner"

    return scores

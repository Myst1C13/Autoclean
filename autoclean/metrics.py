# src/metrics.py
from __future__ import annotations


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def compute_health_score(
    missing_percent: float,
    duplicate_percent: float,
    outlier_percent: float,
    w_missing: float = 0.55,
    w_dup: float = 0.30,
    w_outlier: float = 0.15,
) -> float:
    """
    Returns a 0–100 "data health" score.
    Higher is better.

    Penalty-based:
      score = 100 - (weighted penalties)
    """
    m = clamp(float(missing_percent or 0.0), 0.0, 100.0)
    d = clamp(float(duplicate_percent or 0.0), 0.0, 100.0)
    o = clamp(float(outlier_percent or 0.0), 0.0, 100.0)

    penalty = (w_missing * m) + (w_dup * d) + (w_outlier * o)
    return round(clamp(100.0 - penalty, 0.0, 100.0), 2)
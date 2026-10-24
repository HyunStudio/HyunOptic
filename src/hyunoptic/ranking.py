"""Tie-aware, prevalence-aware ranking metrics for research QC evaluation.

Independent-reader disagreement is the TARGET, not a clinical disease label.
No diagnostic sensitivity/specificity claims should be inferred from these.
"""
from __future__ import annotations

import math
import numpy as np


def ranking_metrics(scores, absolute_disagreement, *, threshold: float = 0.10) -> dict:
    """Compute average precision (AP) and ROC AUC with proper score tie treatment.

    AP is average precision over DISTINCT score thresholds, not trapezoidal PR AUC.
    ROC AUC gives half credit for positive/negative score ties (Mann-Whitney).
    With no positive cases, AP and ROC AUC are undefined; with no negatives,
    ROC AUC is undefined and AP=1. All percentages describe reader mismatch.
    """
    s = np.asarray(scores, dtype=np.float64)
    d = np.asarray(absolute_disagreement, dtype=np.float64)
    if s.ndim != 1 or d.ndim != 1 or len(s) == 0 or s.shape != d.shape:
        raise ValueError("scores and disagreement must be equally sized nonempty vectors")
    if not np.isfinite(s).all() or not np.isfinite(d).all():
        raise ValueError("scores and disagreements must be finite")
    if np.any(d < 0):
        raise ValueError("absolute disagreement cannot be negative")
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("threshold must be finite and nonnegative")
    y = d > threshold
    n = len(s)
    positives = int(y.sum())
    negatives = n - positives
    sorted_idx = np.argsort(-s, kind="stable")
    sorted_scores = s[sorted_idx]
    sorted_y = y[sorted_idx]
    ap = None
    if positives:
        ends = np.r_[np.flatnonzero(np.diff(sorted_scores) != 0) + 1, n]
        true_positive_cum = np.cumsum(sorted_y)
        previous_recall = 0.0
        ap_value = 0.0
        for stop in ends:
            precision = float(true_positive_cum[stop - 1] / stop)
            recall = float(true_positive_cum[stop - 1] / positives)
            ap_value += precision * (recall - previous_recall)
            previous_recall = recall
        ap = float(ap_value)
    roc = None
    if positives and negatives:
        # Pairwise ranking: tie worth 0.5; full PAPILA < 500^2 operations.
        pos = s[y]
        neg = s[~y]
        roc = float(((pos[:, None] > neg[None, :]).sum()
                    + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (positives * negatives))
    return {
        "n": n,
        "n_high_disagreement": positives,
        "n_other": negatives,
        "prevalence": positives / n,
        "average_precision": ap,
        "roc_auc": roc,
        "number_of_distinct_scores": int(np.unique(s).size),
        "target": f"absolute inter-reader vCDR disagreement > {threshold}",
        "not_glaucoma_diagnosis": True,
    }

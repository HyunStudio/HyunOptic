"""Leakage-separated retrospective evaluation and patient-cluster bootstrap."""
from __future__ import annotations
import math
from dataclasses import asdict, dataclass
import numpy as np

@dataclass(frozen=True)
class ReviewBudgetResult:
    n_cases: int
    budget_fraction: float
    cases_reviewed: int
    discrepancy_threshold: float
    n_discrepant: int
    detected_discrepant: int
    precision_at_budget: float
    recall_at_budget: float | None
    prevalence: float

    def to_dict(self) -> dict:
        return asdict(self)

def evaluate_at_budget(
    candidate_only_scores: np.ndarray | list[float],
    heldout_reader_absolute_vcdr_differences: np.ndarray | list[float],
    *, discrepancy_threshold: float = 0.10, review_fraction: float = 0.20,
) -> ReviewBudgetResult:
    """Evaluate candidate-only scores; heldout differences NEVER enter scoring."""
    scores = np.asarray(candidate_only_scores, dtype=np.float64)
    differences = np.asarray(heldout_reader_absolute_vcdr_differences, dtype=np.float64)
    if scores.ndim != 1 or differences.ndim != 1 or scores.shape != differences.shape or len(scores) == 0:
        raise ValueError("scores and differences must be nonempty equally sized 1D arrays")
    if not np.isfinite(scores).all() or not np.isfinite(differences).all():
        raise ValueError("scores and differences must be finite")
    if np.any(scores < 0) or np.any(differences < 0):
        raise ValueError("scores and absolute differences must be nonnegative")
    if not np.isfinite(discrepancy_threshold) or discrepancy_threshold < 0:
        raise ValueError("discrepancy_threshold must be finite and nonnegative")
    if not np.isfinite(review_fraction) or not 0 < review_fraction <= 1:
        raise ValueError("review_fraction must be in (0,1]")
    positive = differences > discrepancy_threshold
    n = len(scores)
    k = max(1, math.ceil(n * review_fraction))
    indices = np.argsort(-scores, kind="stable")[:k]
    tp = int(np.sum(positive[indices]))
    total_positive = int(np.sum(positive))
    return ReviewBudgetResult(
        n_cases=n, budget_fraction=review_fraction, cases_reviewed=k,
        discrepancy_threshold=discrepancy_threshold,
        n_discrepant=total_positive, detected_discrepant=tp,
        precision_at_budget=tp / k,
        recall_at_budget=tp / total_positive if total_positive else None,
        prevalence=total_positive / n,
    )

def patient_cluster_bootstrap_mean(
    per_eye_values: np.ndarray | list[float],
    patient_ids: list[str] | np.ndarray,
    *, draws: int = 2000, seed: int = 42,
) -> dict:
    """Bootstrap patient-average outcome, resampling patients rather than eyes."""
    values = np.asarray(per_eye_values, dtype=np.float64)
    ids = np.asarray(patient_ids, dtype=str)
    if values.ndim != 1 or ids.ndim != 1 or values.shape != ids.shape:
        raise ValueError("values and patient_ids must be equally sized 1D arrays")
    if not len(values) or not np.isfinite(values).all() or any(not p.strip() for p in ids):
        raise ValueError("values must be finite and patient_ids nonempty")
    if not isinstance(draws, int) or not 100 <= draws <= 100_000:
        raise ValueError("draws must be between 100 and 100000")
    groups, inverse = np.unique(ids, return_inverse=True)
    if len(groups) < 2:
        raise ValueError("at least two distinct patients required for cluster bootstrap")
    means = np.array([values[inverse == k].mean() for k in range(len(groups))])
    rng = np.random.default_rng(seed)
    boot_means = np.empty(draws, dtype=np.float64)
    for start in range(0, draws, 512):
        stop = min(draws, start + 512)
        idx = rng.integers(0, len(groups), size=(stop - start, len(groups)))
        boot_means[start:stop] = means[idx].mean(axis=1)
    lower, upper = np.percentile(boot_means, (2.5, 97.5))
    return {
        "method": "equal_patient_weight_cluster_percentile_bootstrap_v1",
        "n_eyes": int(len(values)), "n_patients": int(len(groups)),
        "patient_weighted_mean": float(means.mean()),
        "lower_95_percentile": float(lower), "upper_95_percentile": float(upper),
        "bootstrap_draws": draws, "seed": seed,
        "interpretation": "Dataset-level patient-weighted mean interval; not individual-patient diagnostic uncertainty.",
    }

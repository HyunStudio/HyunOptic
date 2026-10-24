"""Patient-group label permutation diagnostic for experimental QC benchmarking.

This is an association-only exploratory null. It does NOT prove generalization
and permutation exchangeability across the patient sample is an assumption.
"""
from __future__ import annotations

from collections import defaultdict
import numpy as np

from .evaluation import evaluate_at_budget


def grouped_permutation_null(
    candidate_only_scores: list[float] | np.ndarray,
    independent_reader_abs_differences: list[float] | np.ndarray,
    patient_ids: list[str],
    eye_ids: list[str],
    *,
    threshold: float = 0.10,
    review_fraction: float = 0.20,
    draws: int = 999,
    seed: int = 42,
) -> dict:
    """Permute outcome vectors among same-eye-configuration patients.

    Pair OD and OS outcomes together when available. Stratify incomplete
    groups by eye configuration so that bilateral correlation is retained.
    Avoid using labels to compute candidate ranking or choose hyperparameters.
    """
    scores = np.asarray(candidate_only_scores, dtype=float)
    diffs = np.asarray(independent_reader_abs_differences, dtype=float)
    if scores.ndim != 1 or diffs.ndim != 1 or scores.shape != diffs.shape or not len(scores):
        raise ValueError("scores and differences must be equally sized nonempty vectors")
    if len(patient_ids) != len(scores) or len(eye_ids) != len(scores):
        raise ValueError("patient/eye arrays must match score count")
    if not np.isfinite(scores).all() or not np.isfinite(diffs).all():
        raise ValueError("all metric inputs must be finite")
    if not isinstance(draws, int) or not 99 <= draws <= 100_000:
        raise ValueError("draws must be an integer between 99 and 100000")
    if not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be nonnegative")
    groups: dict[str, dict[str, int]] = defaultdict(dict)
    for i, (patient, eye) in enumerate(zip(patient_ids, eye_ids)):
        if not patient or eye not in {"OD", "OS"}:
            raise ValueError("expected nonempty patient ID and OD/OS eye")
        if eye in groups[patient]:
            raise ValueError("duplicate patient/eye pair")
        groups[patient][eye] = i
    # Key by both shape and laterality so a 1-eye OD is not reassigned to an OS.
    strata: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for pid, eyes in groups.items():
        strata[tuple(sorted(eyes))].append(pid)
    obs = evaluate_at_budget(scores, diffs, discrepancy_threshold=threshold,
                             review_fraction=review_fraction).precision_at_budget
    rng = np.random.default_rng(seed)
    samples = np.empty(draws, dtype=float)
    for d in range(draws):
        shuffled = diffs.copy()
        for signature, pids in strata.items():
            perm = rng.permutation(len(pids))
            for dest_pid, source_index in zip(pids, perm):
                source_pid = pids[int(source_index)]
                for eye in signature:
                    shuffled[groups[dest_pid][eye]] = diffs[groups[source_pid][eye]]
        samples[d] = evaluate_at_budget(scores, shuffled, discrepancy_threshold=threshold,
                                         review_fraction=review_fraction).precision_at_budget
    lower, upper = np.percentile(samples, (2.5, 97.5))
    return {
        "method": "same_eye_configuration_patient_group_permutation_null_v1",
        "n_patients": len(groups),
        "n_exchangeable_strata": len(strata),
        "n_strata_with_at_least_2_patients": sum(len(v) >= 2 for v in strata.values()),
        "draws": draws,
        "seed": seed,
        "observed_precision_at_budget": float(obs),
        "null_mean_precision_at_budget": float(np.mean(samples)),
        "null_interval_2_5_97_5": [float(lower), float(upper)],
        "one_sided_permutation_p_exploratory": float((1 + np.count_nonzero(samples >= obs - 1e-12)) / (draws + 1)),
        "limitations": [
            "Patient groups are assumed exchangeable within each eye configuration.",
            "Null test is exploratory, may lack power in small holdout cohorts.",
            "No effect on clinical disease endpoints or external validity is established.",
            "This comparison is not a pre-registered confirmatory p-value.",
        ],
    }

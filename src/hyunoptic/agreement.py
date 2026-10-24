"""Retrospective inter-reader vCDR agreement with patient-cluster resampling.

Bland-Altman limits of agreement (LOA) require a suitable distribution of
paired measurement differences. Normal-theory LOA are DESCRIPTIVE, not a
confidence interval for individual prediction or proof of clinical agreement.
"""
from __future__ import annotations

import numpy as np


def reader_agreement(
    exp1_vcdr, exp2_vcdr, patient_ids, *, draws: int = 1000, seed: int = 42,
) -> dict:
    """Compute signed reader bias and descriptive LOA with patient-cluster CIs."""
    first = np.asarray(exp1_vcdr, dtype=float)
    second = np.asarray(exp2_vcdr, dtype=float)
    ids = np.asarray(patient_ids, dtype=str)
    if (first.ndim != 1 or second.ndim != 1 or ids.ndim != 1 or
        len(first) < 3 or first.shape != second.shape or first.shape != ids.shape):
        raise ValueError("Need >=3 paired measurements and matching patient IDs")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("Non-finite vCDR measurement")
    if any(not p.strip() for p in ids):
        raise ValueError("Patient IDs must be nonempty")
    if not isinstance(seed, int) or seed < 0 or not isinstance(draws, int) or draws < 100:
        raise ValueError("Invalid cluster-bootstrap settings")
    group_ids = sorted(set(ids))
    if len(group_ids) < 3:
        raise ValueError("Need at least three distinct patients for cluster interval")
    differences = first - second
    def estimates(values):
        bias = float(values.mean())
        sd = float(values.std(ddof=1))
        return [bias, bias - 1.96 * sd, bias + 1.96 * sd]
    observed = estimates(differences)
    groups = [np.flatnonzero(ids == p) for p in group_ids]
    rng = np.random.default_rng(seed)
    boot = np.empty((draws, 3), dtype=float)
    for i in range(draws):
        patient_draw = rng.integers(0, len(groups), size=len(groups))
        indices = np.concatenate([groups[k] for k in patient_draw])
        boot[i] = estimates(differences[indices])
    lo, hi = np.percentile(boot, (2.5, 97.5), axis=0)
    return {
        "method": "descriptive_bland_altman_normal_LOA_patient_cluster_bootstrap",
        "n_images": len(differences),
        "n_patients": len(groups),
        "signed_difference_definition": "vCDR(exp1) - vCDR(exp2)",
        "signed_bias": observed[0],
        "limits_of_agreement_lower": observed[1],
        "limits_of_agreement_upper": observed[2],
        "signed_bias_95_bootstrap_percentile_interval": [float(lo[0]), float(hi[0])],
        "lower_LOA_95_bootstrap_percentile_interval": [float(lo[1]), float(hi[1])],
        "upper_LOA_95_bootstrap_percentile_interval": [float(lo[2]), float(hi[2])],
        "mean_absolute_difference": float(np.mean(np.abs(differences))),
        "median_absolute_difference": float(np.median(np.abs(differences))),
        "draws": draws, "seed": seed,
        "caveats": [
            "LOA are descriptive estimates assuming roughly normal reader differences.",
            "Repeated eyes of one patient may be correlated; resampling is by patient.",
            "Bootstrap intervals are uncertain in small or non-representative cohorts.",
            "Agreement does not establish correct glaucoma diagnosis or treatment safety.",
        ],
    }

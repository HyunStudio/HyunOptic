"""Secondary multi-expert annotation-disagreement endpoints (NO diagnosis).

The candidate QC score is computed separately from the candidate reader's image
and disc/cup masks. This module consumes all expert measurements only AFTER
candidate scoring, for retrospective evaluation targets.
"""
from __future__ import annotations

import itertools
import numpy as np


READERS = tuple(f"expert {i}" for i in range(1, 6))


def five_reader_targets(vcdr_by_reader: dict[str, float], *,
                        threshold: float = 0.10,
                        candidate_reader: str = "expert 1") -> dict:
    """One candidate, four independent expert comparisons, and all ten pairs.

    The 2-of-4 vote is an arbitrary PREDECLARED research target, not a
    statistically independent majority vote or a clinical truth standard.
    """
    if set(vcdr_by_reader) != set(READERS):
        raise ValueError("Expected exactly five original human experts")
    values = {name: float(vcdr_by_reader[name]) for name in READERS}
    if any(not np.isfinite(v) or v < 0 or v > 1 for v in values.values()):
        raise ValueError("vCDR outside [0,1] or nonfinite; inspect source masks")
    if not np.isfinite(threshold) or threshold < 0:
        raise ValueError("Disagreement threshold must be finite and nonnegative")
    if candidate_reader not in READERS:
        raise ValueError("Unknown candidate reader")
    candidate = values[candidate_reader]
    peers = [values[name] for name in READERS if name != candidate_reader]
    deviations = [abs(candidate - peer) for peer in peers]
    all_pairs = [
        abs(values[a] - values[b])
        for a, b in itertools.combinations(READERS, 2)
    ]
    n_high = sum(diff > threshold for diff in deviations)
    return {
        "candidate_reader": candidate_reader,
        "independent_reference_readers": 4,
        "all_unique_expert_pairs": 10,
        "candidate_vs_four_mean_absolute_vcdr": float(np.mean(deviations)),
        "candidate_vs_four_max_absolute_vcdr": float(max(deviations)),
        "candidate_vs_four_n_above_threshold": n_high,
        "candidate_vs_four_at_least_two_high": n_high >= 2,
        "all_ten_pairs_mean_absolute_vcdr": float(np.mean(all_pairs)),
        "all_ten_pairs_max_absolute_vcdr": float(max(all_pairs)),
        "all_five_expert_vcdr_sd": float(np.std(list(values.values()), ddof=1)),
        "interpretation": (
            "Secondary, retrospective five-human-expert disagreement. "
            "Expert 1's candidate QC score must be calculated without "
            "using any of the other four expert annotations. "
            "Two-of-four is not clinical ground truth."
        ),
    }

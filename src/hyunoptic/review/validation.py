"""Offline review evaluation; these descriptive results are not clinical guarantees."""
from __future__ import annotations

import math
from numbers import Real


def order_cases(cases: list[dict]) -> list[dict]:
    """Image-only queue ordering, with reproducible input-order ties, never UUID ties."""
    groups = {'error': 0, 'invalid_geometry': 1, 'disagreement': 2, 'pending': 3}

    def key(row):
        priority = row['priority']
        group = priority['group']
        score = priority.get('score')
        if group == 'disagreement' and (
            isinstance(score, bool) or not isinstance(score, Real)
            or not math.isfinite(score) or not 0 <= score <= 1
        ):
            raise ValueError('Completed disagreement score must be finite in [0,1]')
        return groups.get(group, 3), -score if group == 'disagreement' else 0, row['ordinal']

    return sorted(cases, key=key)


def evaluate_budget(ordered_outcomes: list[bool | None], *, review_fraction: float) -> dict:
    """Budget over ALL ordered cases; missing outcomes stay explicit, never negative.

    `True` is a pre-defined research event, not a diagnosis. Random expectation is
    exact for uniform fixed-size review of this same finite case set. Precision
    and remaining risk use only available outcomes and report their denominators.
    """
    if (isinstance(review_fraction, bool) or not isinstance(review_fraction, Real)
            or not math.isfinite(review_fraction) or not 0 <= review_fraction <= 1):
        raise ValueError('review_fraction must be finite in [0,1]')
    if not ordered_outcomes or any(v is not None and type(v) is not bool for v in ordered_outcomes):
        raise ValueError('outcomes must be a nonempty sequence of bool or None')
    n = len(ordered_outcomes)
    k = math.ceil(n * review_fraction)
    reviewed = [v for v in ordered_outcomes[:k] if v is not None]
    remaining = [v for v in ordered_outcomes[k:] if v is not None]
    total = sum(v is True for v in ordered_outcomes)
    detected = sum(reviewed)
    available = len(reviewed) + len(remaining)
    return dict(n_cases=n, n_outcome_available=available, n_outcome_missing=n-available,
                review_fraction=float(review_fraction), cases_reviewed=k,
                reviewed_outcome_available=len(reviewed), remaining_outcome_available=len(remaining),
                n_positive=total, detected=detected, missed=total-detected,
                precision=detected/len(reviewed) if reviewed else None,
                recall=detected/total if total else None,
                remaining_error_fraction=sum(remaining)/len(remaining) if remaining else None,
                random_expected_detected=k*total/n,
                random_expected_recall=k/n if total else None)

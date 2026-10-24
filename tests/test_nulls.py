import numpy as np
import pytest
from hyunoptic.nulls import grouped_permutation_null


def test_patient_pair_permutation_is_deterministic():
    ids = [f"RET{i:03}" for i in range(8) for _ in ("OD", "OS")]
    eyes = ["OD", "OS"] * 8
    # Both eyes of each patient share a high/low discrepancy label.
    diffs = [0.2 if i < 4 else 0.0 for i in range(8) for _ in range(2)]
    score = [10 - i for i in range(8) for _ in range(2)]
    kw = dict(threshold=0.10, review_fraction=.25, draws=199, seed=9)
    a = grouped_permutation_null(score, diffs, ids, eyes, **kw)
    assert a == grouped_permutation_null(score, diffs, ids, eyes, **kw)
    assert a["observed_precision_at_budget"] == 1
    assert 0 <= a["one_sided_permutation_p_exploratory"] <= 1
    assert a["n_patients"] == 8


def test_missing_one_eye_stratified_and_duplicate_rejected():
    scores = [0.9, 0.8, 0.7, 0.6, 0.5]
    diffs = [0.3, 0, 0.1, 0, 0.2]
    result = grouped_permutation_null(scores, diffs, ["A","A","B","B","C"], 
            ["OD","OS","OD","OS","OD"], draws=99)
    assert result["n_exchangeable_strata"] == 2
    with pytest.raises(ValueError, match="duplicate"):
        grouped_permutation_null([1,2],[0,0],["A","A"],["OD","OD"])


def test_invalid_permutation_arguments():
    with pytest.raises(ValueError):
        grouped_permutation_null([1], [1,2], ["P"], ["OD"])
    with pytest.raises(ValueError):
        grouped_permutation_null([1], [1], ["P"], ["OD"], draws=5)

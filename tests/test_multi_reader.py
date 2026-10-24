"""Scientific invariant tests for five-reader SECONDARY evaluation endpoints."""
import numpy as np
import pytest
from hyunoptic.multi_reader import READERS, five_reader_targets


def test_identical_readers_have_zero_disagreement():
    values = {name: 0.55 for name in READERS}
    r = five_reader_targets(values)
    assert r["independent_reference_readers"] == 4
    assert r["all_unique_expert_pairs"] == 10
    assert r["candidate_vs_four_mean_absolute_vcdr"] == 0
    assert r["all_ten_pairs_mean_absolute_vcdr"] == 0
    assert r["candidate_vs_four_n_above_threshold"] == 0
    assert r["candidate_vs_four_at_least_two_high"] is False


def test_candidate_high_disagreement_two_of_four_is_secondary_not_diagnosis():
    # Two peers > 0.1 away, another peer exactly at 0.1 (strict >), one equal.
    vals = dict(zip(READERS, [0.5, 0.7, 0.3, 0.6, 0.5]))
    r = five_reader_targets(vals, threshold=0.10)
    assert r["candidate_vs_four_n_above_threshold"] >= 2
    assert r["candidate_vs_four_at_least_two_high"] is True
    assert r["all_ten_pairs_mean_absolute_vcdr"] > 0
    assert "clinical ground truth" in r["interpretation"]


def test_pairwise_mean_order_invariant_to_source_dict_order():
    vals = dict(zip(READERS, [0.4, 0.52, 0.51, 0.45, 0.54]))
    a = five_reader_targets(vals)
    b = five_reader_targets(dict(reversed(list(vals.items()))))
    assert a == b


@pytest.mark.parametrize("bad", [
    {"expert 1": 0.5},
    dict(zip(READERS, [0.1, 0.2, 0.3, 0.4, 2.0])),
    dict(zip(READERS, [0.1, 0.2, np.nan, 0.4, 0.5])),
])
def test_invalid_reader_sets_or_vcdrs_rejected(bad):
    with pytest.raises(ValueError):
        five_reader_targets(bad)


def test_threshold_and_candidate_selection():
    vals = dict(zip(READERS, [0.5, 0.65, 0.49, 0.40, 0.53]))
    first = five_reader_targets(vals, candidate_reader="expert 1")
    second = five_reader_targets(vals, candidate_reader="expert 2")
    assert first["candidate_vs_four_mean_absolute_vcdr"] != second["candidate_vs_four_mean_absolute_vcdr"]
    assert first["all_ten_pairs_mean_absolute_vcdr"] == second["all_ten_pairs_mean_absolute_vcdr"]
    with pytest.raises(ValueError):
        five_reader_targets(vals, candidate_reader="expert 6")

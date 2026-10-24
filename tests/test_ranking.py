"""Synthetic tie/imbalance checks for reader-disagreement ranking; no clinical data."""
import pytest
from hyunoptic.ranking import ranking_metrics


def test_perfect_ranking():
    d = ranking_metrics([4, 3, 2, 1], [0.3, 0.2, 0, 0], threshold=.1)
    assert d["average_precision"] == pytest.approx(1)
    assert d["roc_auc"] == pytest.approx(1)
    assert d["n_high_disagreement"] == 2
    assert d["not_glaucoma_diagnosis"]


def test_scores_tied_get_half_roc_credit():
    d = ranking_metrics([.5, .5, .1], [.3, 0, 0], threshold=.1)
    assert d["roc_auc"] == pytest.approx(.75)
    assert d["average_precision"] == pytest.approx(.5)


def test_all_tied_scores_equal_prevalence():
    d = ranking_metrics([2, 2, 2, 2], [.2, 0, .3, 0], threshold=.1)
    assert d["roc_auc"] == pytest.approx(.5)
    assert d["average_precision"] == pytest.approx(.5)


def test_all_negative_undefined():
    d = ranking_metrics([1, 2], [0, .01], threshold=.1)
    assert d["average_precision"] is None
    assert d["roc_auc"] is None
    assert d["prevalence"] == 0


def test_all_positive_ap_one_auc_undefined():
    d = ranking_metrics([1, 2], [.2, .5], threshold=.1)
    assert d["average_precision"] == 1
    assert d["roc_auc"] is None


@pytest.mark.parametrize("s,d", [
    ([], []),
    ([1], [1, 2]),
    ([float("nan")], [0]),
    ([0], [float("inf")]),
    ([0], [-1]),
])
def test_invalid_data(s, d):
    with pytest.raises(ValueError):
        ranking_metrics(s, d)

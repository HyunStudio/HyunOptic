"""Synthetic repeated-eye reader agreement tests; not patient evidence."""
import pytest
from hyunoptic.agreement import reader_agreement


def test_equal_readers_zero_signed_bias_and_limits():
    data = [0.4, 0.5, 0.6, 0.55, 0.7, 0.8]
    patients = ["a", "a", "b", "b", "c", "c"]
    result = reader_agreement(data, data, patients, draws=100, seed=9)
    assert result["signed_bias"] == 0.0
    assert result["limits_of_agreement_lower"] == 0.0
    assert result["limits_of_agreement_upper"] == 0.0
    assert result["n_patients"] == 3
    assert result == reader_agreement(data, data, patients, draws=100, seed=9)


def test_directional_bias_has_sign():
    first = [0.5, 0.7, 0.6, 0.4, 0.45, 0.8]
    second = [0.4, 0.6, 0.5, 0.3, 0.35, 0.7]
    r = reader_agreement(first, second, ["a", "a", "b", "b", "c", "c"], draws=100)
    assert r["signed_bias"] == pytest.approx(.1)
    assert r["mean_absolute_difference"] == pytest.approx(.1)
    assert r["limits_of_agreement_lower"] <= r["signed_bias"] <= r["limits_of_agreement_upper"]


def test_single_patient_has_no_valid_cluster_interval():
    with pytest.raises(ValueError, match="three distinct"):
        reader_agreement([.1, .2, .3], [.2, .3, .4], ["x", "x", "x"], draws=100)


@pytest.mark.parametrize("a,b,ids",[
    ([1,2], [1,2], ["a","b"]),
    ([.1, .2, .3], [.1, .2], ["a", "b", "c"]),
    ([.1, float("nan"), .3], [.1,.2,.3], ["a","b","c"]),
])
def test_invalid_reader_data(a,b,ids):
    with pytest.raises(ValueError):
        reader_agreement(a,b,ids,draws=100)

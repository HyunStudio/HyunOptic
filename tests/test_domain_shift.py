"""The shift feature table depends only on candidate-side information."""
import copy
import pytest
from hyunoptic.domain_shift import camera_feature_shift
from hyunoptic.mask_features import MASK_FEATURES


def fixture():
    scaler = {name: {"mean": 1.0, "sd": 2.0} for name in MASK_FEATURES}
    rows = [
        {"camera": "bosch", "mask_q95": 1.0, "mask_roughness": 3.0,
         "mask_boundary_weakness": 7.1, "heldout_absolute_vcdr_difference": 0.01},
        {"camera": "forus", "mask_q95": 9.0, "mask_roughness": 1.0,
         "mask_boundary_weakness": 1.0, "heldout_absolute_vcdr_difference": 0.20},
        {"camera": "remidio", "mask_q95": 3.0, "mask_roughness": 3.0,
         "mask_boundary_weakness": 1.0, "heldout_absolute_vcdr_difference": 0.15},
    ]
    return scaler, rows


def test_per_camera_diagnostics_and_outlier_fraction():
    scaler, rows = fixture()
    result = camera_feature_shift(rows, scaler)
    assert result["camera_groups"]["all"]["n_images"] == 3
    assert result["camera_groups"]["bosch"]["features"]["mask_boundary_weakness"]["n_abs_z_over_threshold"] == 1
    assert result["camera_groups"]["forus"]["features"]["mask_q95"]["fraction_abs_z_over_threshold"] == 1
    assert result["camera_groups"]["remidio"]["n_images"] == 1
    assert result["method"].startswith("unlabelled")


def test_reference_label_mutation_does_not_change_shift():
    scaler, rows = fixture()
    baseline = camera_feature_shift(rows, scaler)
    altered = copy.deepcopy(rows)
    for row in altered:
        row["heldout_absolute_vcdr_difference"] = 12345
    assert camera_feature_shift(altered, scaler) == baseline


def test_invalid_inputs_rejected():
    scaler, rows = fixture()
    with pytest.raises(ValueError):
        camera_feature_shift([], scaler)
    with pytest.raises(ValueError):
        camera_feature_shift(rows, scaler, z_threshold=0)
    scaler["mask_q95"]["sd"] = 0
    with pytest.raises(ValueError):
        camera_feature_shift(rows, scaler)

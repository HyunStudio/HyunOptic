"""Numerical and supplied-split boundaries discovered by the literature audit."""
from types import SimpleNamespace
import copy

import numpy as np
import pytest
from PIL import Image

from hyunoptic.demo_data import make_papila
from hyunoptic.measure import dice, measure_masks
from hyunoptic.seg.data import build_split_manifest, canonical_sha256, verify_split_manifest


@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf])
def test_nonfinite_masks_are_rejected_before_boolean_conversion(bad):
    disc = np.ones((4, 4))
    cup = np.zeros_like(disc)
    cup[1, 1] = bad
    for a, b in ((disc, cup), (cup, disc)):
        with pytest.raises(ValueError, match='finite'):
            measure_masks(a, b)


@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf])
def test_nonfinite_dice_masks_are_rejected_before_boolean_conversion(bad):
    mask = np.ones((4, 4))
    invalid = mask.copy()
    invalid[1, 1] = bad
    for a, b in ((mask, invalid), (invalid, mask)):
        with pytest.raises(ValueError, match='finite'):
            dice(a, b)


def test_nonzero_integer_mask_convention_is_preserved():
    disc = np.full((4, 4), 255, dtype=np.uint8)
    cup = np.zeros((4, 4), dtype=np.int16)
    cup[1:3, 1:3] = -2
    assert measure_masks(disc, cup).vertical_cdr == .5
    assert dice(disc, cup) == pytest.approx(.4)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_predict_rejects_nonfinite_model_logits(bad):
    torch = pytest.importorskip('torch')
    from hyunoptic.seg.inference import Predictor

    class Logits(torch.nn.Module):
        def forward(self, x):
            out = torch.zeros((len(x), 3, 32, 32))
            out[:, 1, 4:28, 4:28] = 1
            out[:, 2, 12:20, 12:20] = bad
            return out

    predictor = Predictor.__new__(Predictor)
    predictor.bundle = SimpleNamespace(run_id='audit', weights_sha256='0' * 64)
    predictor.model = Logits()
    predictor.size = 32
    pred = predictor.predict(Image.new('RGB', (32, 32)))
    assert pred.status == 'error'
    assert pred.measurement is None
    assert any('finite' in message for message in pred.errors)


def test_finite_prediction_geometry_is_unchanged():
    torch = pytest.importorskip('torch')
    from hyunoptic.seg.inference import Predictor

    class Logits(torch.nn.Module):
        def forward(self, x):
            out = torch.zeros((len(x), 3, 32, 32))
            out[:, 1, 4:28, 4:28] = 1
            out[:, 2, 12:20, 12:20] = 2
            return out

    predictor = Predictor.__new__(Predictor)
    predictor.bundle = SimpleNamespace(run_id='audit', weights_sha256='0' * 64)
    predictor.model = Logits()
    predictor.size = 32
    pred = predictor.predict(Image.new('RGB', (32, 32)))
    assert pred.status == 'ok'
    assert pred.measurement['vertical_cdr'] == pytest.approx(1 / 3)
    assert np.count_nonzero(pred.disc) == 24 * 24
    assert np.count_nonzero(pred.cup) == 8 * 8


@pytest.fixture
def split_payload(tmp_path):
    return build_split_manifest(make_papila(tmp_path / 'P', patients=10))


@pytest.mark.parametrize('change', ['shared_image', 'duplicate_image', 'wrong_patient',
                                  'duplicate_patient', 'missing_partition', 'wrong_type',
                                  'missing_patient', 'unlisted_patient'])
def test_split_verifier_rejects_inconsistent_hashed_partition(split_payload, change):
    body = copy.deepcopy(split_payload['manifest'])
    if change == 'shared_image':
        body['splits']['holdout'].append(body['splits']['development'][0])
    elif change == 'duplicate_image':
        body['splits']['holdout'].append(body['splits']['holdout'][0])
    elif change == 'wrong_patient':
        body['patients']['holdout'][0] = 'RET999'
    elif change == 'duplicate_patient':
        body['patients']['holdout'].append(body['patients']['holdout'][0])
    elif change == 'missing_partition':
        del body['splits']['validation']
    elif change == 'wrong_type':
        body['splits']['holdout'] = 'RET001OD'
    elif change == 'missing_patient':
        body['patients']['holdout'].pop()
    else:
        body['patients']['holdout'].append('RET999')
    with pytest.raises(ValueError):
        verify_split_manifest({'manifest': body, 'sha256': canonical_sha256(body)})


@pytest.mark.parametrize('body', [None, [], {'schema': 'hyunoptic.seg_split/v1'}])
def test_malformed_split_has_actionable_value_error(body):
    with pytest.raises(ValueError):
        verify_split_manifest({'manifest': body, 'sha256': canonical_sha256(body)})

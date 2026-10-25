import numpy as np
import pytest
from evaluate_universities import reference_masks, score, summarize

def test_fairseg_rim_and_cup_encoding():
    raw=np.array([[0,-1,-2],[0,-1,0]],float)
    d,c=reference_masks(raw)
    assert d.sum()==3 and c.sum()==1
    assert d[0,2] and c[0,2] and not c[0,1]

def test_unknown_reference_encoding_refused():
    with pytest.raises(ValueError):reference_masks(np.array([[0,1,2]]))

def test_invalid_prediction_stays_in_dice_not_mae():
    ref=np.array([[0,-1,-2],[0,-1,0]])
    row=score(np.zeros((2,3),np.uint8),ref)
    assert row['model_status']=='invalid_geometry'
    assert row['disc_dice']==0 and row['cup_dice']==0
    assert 'abs_vcdr_error' not in row

def test_perfect_prediction_has_zero_error():
    row=score(np.array([[0,1,2],[0,1,0]],np.uint8),np.array([[0,-1,-2],[0,-1,0]]))
    assert row['disc_dice']==1 and row['cup_dice']==1
    assert row['abs_vcdr_error']==0

def test_unscored_reference_cannot_become_accuracy():
    row=score(np.array([[0,1,2],[0,1,0]],np.uint8),None)
    out=summarize([row])
    assert out['n_images']==1 and out['n_measurable']==1
    assert out['disc_dice']['n']==0 and out['abs_vcdr_error']['n']==0

def test_reference_failure_is_counted():
    row=score(np.array([[0,1,2],[0,1,0]],np.uint8),np.zeros((2,3)))
    out=summarize([row])
    assert out['n_reference_failed']==1 and out['disc_dice']['n']==0

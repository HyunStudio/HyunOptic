"""Training/evaluation Dice must not bypass shared shape/numerical guards."""
import numpy as np
import pytest


@pytest.mark.parametrize('entry',['train','evaluate'])
@pytest.mark.parametrize('bad',[np.nan,np.inf,-np.inf,'broadcast_shape'])
def test_training_and_evaluation_dice_reject_invalid_masks(entry,bad):
    pytest.importorskip('torch')
    from hyunoptic.seg import train,evaluate
    calculate=getattr({'train':train,'evaluate':evaluate}[entry],'dice')
    left=np.ones((3,3));right=np.ones((3,3))
    if isinstance(bad,str):right=np.ones((1,3))
    else:right[1,1]=bad
    with pytest.raises(ValueError):calculate(left,right)


@pytest.mark.parametrize('entry',['train','evaluate'])
def test_training_and_evaluation_dice_preserve_valid_result(entry):
    pytest.importorskip('torch')
    from hyunoptic.seg import train,evaluate
    calculate=getattr({'train':train,'evaluate':evaluate}[entry],'dice')
    assert calculate(np.ones((3,3),bool),np.ones((3,3),bool))==1
    assert calculate(np.zeros((3,3),bool),np.zeros((3,3),bool))==1
    assert calculate(np.ones((3,3),bool),np.eye(3,dtype=bool))==pytest.approx(.5)

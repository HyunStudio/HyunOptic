"""Synthetic checks for opt-in camera photometry; no performance claims."""
import json

import numpy as np
import pytest

torch=pytest.importorskip('torch')

from hyunoptic.seg import preprocess
from hyunoptic.seg.train import _augment,train


def _example():
    image=np.zeros((32,32,3),np.uint8)
    image[4:28,4:28]=[153,51,26]
    image[12:20,12:20]=[204,102,51]
    x=torch.from_numpy(preprocess.normalise(image)[None])
    y=torch.zeros((1,32,32),dtype=torch.long)
    y[:,8:24,8:24]=1
    y[:,12:20,12:20]=2
    return x,y


def test_default_augmentation_preserves_recorded_legacy_behavior():
    # Recorded before adding the new policy, on this synthetic image only.
    x,y=_example(); gen=torch.Generator().manual_seed(88)
    result,labels=_augment(x,y,gen)
    assert result[0,:,0,0].tolist()==pytest.approx([-1.9916796684]*3,abs=1e-6)
    assert result[0,:,16,16].tolist()==pytest.approx([.8709714413,-.5603541136,-1.2760169506],abs=1e-6)
    assert float(result.mean())==pytest.approx(-1.2617939711,abs=1e-6)
    assert int(labels.sum())==363
    assert torch.rand(4,generator=gen).tolist()==pytest.approx([.8892554045,.1977444291,.2396917343,.8600581288],abs=1e-7)


def test_opt_in_photometry_is_bounded_deterministic_and_preserves_geometry_rng():
    x,y=_example()
    baseline_gen=torch.Generator().manual_seed(88)
    baseline,baseline_y=_augment(x,y,baseline_gen)
    gen=torch.Generator().manual_seed(88)
    result,labels=_augment(x,y,gen,photometric_policy='camera_robust_v2',
                          photometric_gen=torch.Generator().manual_seed(1000046))
    repeat,repeat_y=_augment(x,y,torch.Generator().manual_seed(88),
                            photometric_policy='camera_robust_v2',
                            photometric_gen=torch.Generator().manual_seed(1000046))
    assert torch.equal(labels,baseline_y) and torch.equal(labels,repeat_y)
    assert torch.equal(result,repeat) and not torch.allclose(result,baseline)
    assert torch.equal(torch.rand(8,generator=gen),torch.rand(8,generator=baseline_gen))
    raw=result*torch.tensor(preprocess.STD).view(1,3,1,1)+torch.tensor(preprocess.MEAN).view(1,3,1,1)
    assert torch.isfinite(raw).all() and raw.min()>=0 and raw.max()<=1
    assert torch.equal(raw[0,:,0,0],torch.zeros(3))
    assert torch.equal(x,_example()[0]) and torch.equal(y,_example()[1])


def test_unknown_policy_rejected_before_reading_dataset(tmp_path):
    with pytest.raises(ValueError,match='photometric'):
        train(tmp_path/'missing',tmp_path/'unused',photometric_policy='unknown')
    assert not (tmp_path/'unused').exists()


def test_policy_requires_separate_generator():
    with pytest.raises(ValueError,match='generator'):
        _augment(*_example(),torch.Generator().manual_seed(1),photometric_policy='camera_robust_v2')


def test_cli_policy_is_recorded_in_verified_bundle(tmp_path):
    from hyunoptic.demo_data import make_papila
    from hyunoptic.seg.cli import main
    from hyunoptic.seg.bundle import verify_bundle
    source=make_papila(tmp_path/'PAPILA',patients=10)
    output=tmp_path/'bundle'
    assert main(['train','--papila-root',str(source),'--output',str(output),
                 '--image-size','64','--epochs','1','--batch-size','4','--base-channels','4',
                 '--depth','2','--seed','43','--device','cpu','--allow-partial',
                 '--photometric-policy','camera_robust_v2'])==0
    bundle=verify_bundle(output)
    config=json.loads((output/'config.json').read_text(encoding='utf-8'))
    assert config['photometric_policy']=='camera_robust_v2'
    assert config['photometric_generator_seed']==1000046
    assert any('RGB' in value and '0.65' in value for value in config['augmentations'])
    assert any('gamma' in value for value in config['augmentations'])
    assert bundle.manifest['training']['expert2_used'] is False
    assert bundle.manifest['training']['holdout_used_in_training_or_selection'] is False

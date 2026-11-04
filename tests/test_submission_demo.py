"""Public source must prepare an isolated demo without developer model files."""
from pathlib import Path
import json
import runpy

import pytest


def prepare():
    return runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts'/'prepare_submission_demo.py'))['prepare_demo']


def test_demo_refuses_existing_output_without_touching_it(tmp_path):
    output=tmp_path/'existing'
    output.mkdir()
    file=output/'keep.txt'
    file.write_text('previous work')
    with pytest.raises(FileExistsError):prepare()(output,epochs=1)
    assert file.read_text()=='previous work'
    assert list(output.iterdir())==[file]


def test_demo_bad_epoch_count_has_no_filesystem_side_effect(tmp_path):
    output=tmp_path/'new'
    with pytest.raises(ValueError):prepare()(output,epochs=0)
    assert not output.exists()


def test_demo_trains_real_cpu_bundles_and_isolates_workspace(tmp_path,monkeypatch):
    pytest.importorskip('torch')
    from hyunoptic.seg.bundle import verify_bundle
    from hyunoptic.seg.inference import Predictor
    from hyunoptic.papila import discover_cases,load_image
    unrelated=tmp_path/'other-workspace'
    monkeypatch.setenv('HYUNOPTIC_WORKSPACE',str(unrelated))
    output=tmp_path/'demo'
    result=prepare()(output,epochs=1,patients=6,image_size=32)
    assert not unrelated.exists()
    config=json.loads((output/'workspace'/'workspace.json').read_text())
    assert Path(config['models_dir']).resolve()==(output/'models').resolve()
    paths=sorted((output/'models').iterdir())
    assert len(paths)==2
    bundles=[verify_bundle(p) for p in paths]
    assert all(b.synthetic and b.partial for b in bundles)
    assert bundles[0].identity!=bundles[1].identity
    case=discover_cases(output/'PAPILA_SYNTHETIC')[0]
    actual=Predictor(bundles[0]).predict(load_image(case))
    assert actual.status in {'ok','invalid_geometry'}
    assert actual.labels.shape==(384,512)
    assert len(result['models'])==2 and result['synthetic'] is True
    assert (output/'inputs'/'unreadable.png').read_bytes()==b'Intentional unreadable synthetic demo input'

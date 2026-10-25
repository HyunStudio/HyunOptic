"""Bind follow-up evaluations to both prespecified frozen checkpoints."""
import json
import pathlib
from hyunoptic.seg.bundle import verify_bundle

def assert_frozen_identity(bundle, record):
    assert bundle.run_id==record['run_id'], 'Bundle run ID differs from the frozen experiment record.'
    assert bundle.weights_sha256==record['weights_sha256'], 'Bundle weights differ from the frozen experiment record.'

def verify_frozen_bundles(output_folder):
    folder=pathlib.Path(output_folder)
    protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'))
    completion=json.loads((folder/'all_training_complete.json').read_text(encoding='utf-8'))
    assert completion['both_checkpoints_frozen_before_followup_evaluation'] is True
    records=completion['seeds']
    assert len(records)==2 and {r['seed'] for r in records}=={43,44}
    baseline=verify_bundle('models/papila_real_v1_20261025')
    assert_frozen_identity(baseline,{'run_id':protocol['baseline_run_id'],'weights_sha256':protocol['baseline_weights_sha256']})
    bundles={42:baseline}
    for record in records:
        seed=record['seed']
        bundle=verify_bundle(f'models/papila_real_seed{seed}_20261025')
        assert_frozen_identity(bundle,record)
        assert not bundle.synthetic and not bundle.partial
        for key in ('source_content_sha256','split_manifest_sha256'):
            assert bundle.manifest['training'][key]==protocol[key]
        bundles[seed]=bundle
    return bundles

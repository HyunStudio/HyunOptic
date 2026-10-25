import datetime, hashlib, json, math, pathlib, subprocess, sys
import numpy as np
import torch
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.train import train

out = pathlib.Path('reports/seed_stability_20261025')
baseline_path = pathlib.Path('models/papila_real_v1_20261025')
baseline = verify_bundle(baseline_path)
config = json.loads((baseline_path/'config.json').read_text(encoding='utf-8'))
source_files = ['src/hyunoptic/seg/train.py','src/hyunoptic/seg/evaluate.py','src/hyunoptic/seg/inference.py','src/hyunoptic/seg/preprocess.py','src/hyunoptic/seg/model.py','src/hyunoptic/seg/data.py','src/hyunoptic/chaksu.py']
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8'))

protocol_path = out/'protocol.json'
assert not protocol_path.exists(), 'Protocol already exists: do not restart this experiment blindly.'
protocol = {'created_utc':now(),'user_authorization':'Two additional training seeds to assess stability; same split and settings.',
    'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
    'baseline_run_id':baseline.run_id,'baseline_weights_sha256':baseline.weights_sha256,
    'training_seeds':[43,44],'baseline_training_seed':42,'split_seed':42,
    'fixed_config_except_training_seed':config,
    'source_content_sha256':baseline.manifest['training']['source_content_sha256'],
    'split_manifest_sha256':baseline.manifest['training']['split_manifest_sha256'],
    'source_file_sha256':{name:hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in source_files},
    'selection':'For each run, highest validation mean disc/cup Dice; both checkpoints frozen before follow-up evaluation. No holdout/external-based seed selection.',
    'evaluation':'One internal evaluation and one Chaksu external evaluation for each frozen new bundle. All follow-up analyses exploratory; no reuse of baseline inference.',
    'summary':'Show all three runs, mean, sample SD (ddof=1), min/max of run-level metrics; not patient confidence intervals or independent cohorts.',
    'failure_handling':'Retain source annotation errors, invalid predictions and each metric denominator; no source mask repairs.',
    'environment':{'python':sys.version,'torch':torch.__version__,'numpy':np.__version__,'cuda_runtime':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'omp_threads':4,'mkl_threads':4},
    'reproducibility_limit':'CUDA nll_loss2d warns of missing deterministic implementation; fixed seeds do not establish bitwise reproducibility.'}
save(protocol_path,protocol)
save(out/'state.json',{'stage':'training','started_utc':now(),'completed_seeds':[]})
torch.set_num_threads(4)
settings={'image_size':384,'epochs':40,'batch_size':4,'lr':0.001,'weight_decay':0.0001,'base_channels':16,'depth':4,'split_seed':42,'device':'cuda'}
completed=[]
for seed in (43,44):
    target=pathlib.Path(f'models/papila_real_seed{seed}_20261025')
    assert not target.exists(), 'Never overwrite existing model bundle.'
    print(f'Seed {seed}: loading unchanged development/validation data, then 40 epochs.',flush=True)
    def progress(row):
        with (out/f'seed{seed}_training_progress.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(row)+'\n')
        print(json.dumps({'seed':seed,**row}),flush=True)
    train('data/PAPILA',target,seed=seed,progress=progress,**settings)
    bundle=verify_bundle(target)
    trained_config=json.loads((target/'config.json').read_text(encoding='utf-8'))
    expected={**config,'seed':seed}
    assert trained_config==expected, 'Configuration changed beyond training seed.'
    for key in ('source_content_sha256','split_manifest_sha256','n_images','n_patients'):
        assert bundle.manifest['training'][key]==baseline.manifest['training'][key], key
    history=json.loads((target/'history.json').read_text(encoding='utf-8'))
    assert len(history)==40 and all(math.isfinite(row['train_loss']) for row in history)
    assert max(history,key=lambda row:row['val_score'])['epoch']==bundle.manifest['training']['best_epoch']
    record={'seed':seed,'bundle_folder':str(target),'run_id':bundle.run_id,'weights_sha256':bundle.weights_sha256,'best_epoch':bundle.manifest['training']['best_epoch'],'validation_score':bundle.manifest['training']['best_validation_score'],'completed_utc':now()}
    completed.append(record)
    save(out/f'seed{seed}_training_completion.json',record)
    save(out/'state.json',{'stage':'training' if seed==43 else 'both_checkpoints_frozen','completed_seeds':completed,'updated_utc':now()})
    print('FROZEN '+json.dumps(record),flush=True)
assert verify_bundle(baseline_path).weights_sha256==protocol['baseline_weights_sha256']
save(out/'all_training_complete.json',{'completed_utc':now(),'seeds':completed,'both_checkpoints_frozen_before_followup_evaluation':True})
print('Both new checkpoints frozen. Baseline unchanged.',flush=True)

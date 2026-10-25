import datetime,hashlib,json,math,pathlib,subprocess,sys
import torch
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.train import train,CAMERA_ROBUST_AUGMENTATIONS

out=pathlib.Path('reports/remediation_20261025')
target=pathlib.Path('models/papila_camera_robust_seed43_20261025')
baseline=verify_bundle('models/papila_real_seed43_20261025')
config=json.loads((baseline.folder/'config.json').read_text(encoding='utf-8'))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(name,data): (out/name).write_bytes((json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
assert not (out/'protocol.json').exists() and not target.exists(), 'One prespecified run only; no overwrite or outcome-driven retries.'
sources=['src/hyunoptic/seg/train.py','src/hyunoptic/seg/cli.py','src/hyunoptic/seg/model.py','src/hyunoptic/seg/preprocess.py','src/hyunoptic/seg/inference.py','src/hyunoptic/seg/evaluate.py','src/hyunoptic/seg/data.py','src/hyunoptic/chaksu.py']
identities={}
for seed,name in ((42,'papila_real_v1_20261025'),(43,'papila_real_seed43_20261025'),(44,'papila_real_seed44_20261025')):
    b=verify_bundle(pathlib.Path('models')/name);identities[str(seed)]={'run_id':b.run_id,'weights_sha256':b.weights_sha256}
settings={'image_size':384,'epochs':40,'batch_size':4,'lr':.001,'weight_decay':.0001,'base_channels':16,'depth':4,'seed':43,'split_seed':42,'device':'cuda','photometric_policy':'camera_robust_v2'}
protocol={'created_utc':now(),'purpose':'One exploratory photometric-domain remediation run after inspecting previous holdout/external results; no causal or clinical claim.',
 'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'one_run_budget':1,'comparison_training_seed':43,'baseline_identities':identities,
 'baseline_config':config,'training':settings,'new_augmentation_descriptions':CAMERA_ROBUST_AUGMENTATIONS,'photometric_generator_seed':1000046,
 'source_content_sha256':baseline.manifest['training']['source_content_sha256'],'split_manifest_sha256':baseline.manifest['training']['split_manifest_sha256'],
 'source_file_sha256':{name:hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in sources},
 'selection':'Highest validation mean disc/cup Dice only; freeze checkpoint before evaluation. Do not change settings or add runs based on outcomes.',
 'evaluation':'One exploratory internal and external evaluation. Same original masks/postprocessing; keep 25 external reference failures and every model failure/denominator.',
 'success_rule':{'external_model_failures_less_than':16,'external_conditional_vcdr_mae_less_than':.25531008981230335,'external_cup_dice_at_least':.5548701898781451,'internal_tradeoff_disc_drop_greater_than':.02,'internal_tradeoff_cup_drop_greater_than':.02,'internal_tradeoff_failures_greater_than':6},
 'additional_metrics':'Paired vCDR MAE on common measurable cases; separate descriptive research penalty=1 for model-invalid predictions over all reference-valid cases. Penalty is not observed MAE or clinical utility.',
 'diagnostics':'Prior seed43 invalid/high-error/low-error selected cases plus image-only color samples; not performance estimates or proof of root cause.',
 'environment':{'python':sys.version,'torch':torch.__version__,'cuda_runtime':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'omp_threads':4,'mkl_threads':4},
 'limitation':'Fixed-seed single follow-up run on already inspected cohorts; CUDA nll_loss2d nondeterminism warning remains. No stability or superiority inference from one new run.'}
save('protocol.json',protocol)
torch.set_num_threads(4)
def progress(row):
    with (out/'training_progress.jsonl').open('a',encoding='utf-8') as stream: stream.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)
print('Starting the one prespecified camera_robust_v2 run; follow-up holdout not opened.',flush=True)
train('data/PAPILA',target,progress=progress,**settings)
bundle=verify_bundle(target)
expected={**config,'augmentations':CAMERA_ROBUST_AUGMENTATIONS,'photometric_policy':'camera_robust_v2','photometric_generator_seed':1000046}
assert json.loads((target/'config.json').read_text(encoding='utf-8'))==expected
for key in ('source_content_sha256','split_manifest_sha256','n_images','n_patients'):
    assert bundle.manifest['training'][key]==baseline.manifest['training'][key]
history=json.loads((target/'history.json').read_text(encoding='utf-8'))
assert len(history)==40 and all(math.isfinite(r['train_loss']) for r in history)
assert max(history,key=lambda r:r['val_score'])['epoch']==bundle.manifest['training']['best_epoch']
record={'completed_utc':now(),'bundle_folder':str(target),'run_id':bundle.run_id,'weights_sha256':bundle.weights_sha256,'best_epoch':bundle.manifest['training']['best_epoch'],'validation_score':bundle.manifest['training']['best_validation_score']}
save('training_completion.json',record)
print('FROZEN '+json.dumps(record),flush=True)

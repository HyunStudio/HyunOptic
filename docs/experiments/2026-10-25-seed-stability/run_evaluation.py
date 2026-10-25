import datetime, hashlib, json, pathlib, shutil, sys
import torch
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.evaluate import evaluate_chaksu, evaluate_holdout
from hyunoptic.seg.report import validate_report
from frozen_identity import verify_frozen_bundles

out=pathlib.Path('reports/seed_stability_20261025')
seed=int(sys.argv[1]); assert seed in (43,44)
protocol=json.loads((out/'protocol.json').read_text(encoding='utf-8'))
assert (out/'all_training_complete.json').exists(), 'Freeze both checkpoints before any new evaluation.'
for filename,expected in protocol['source_file_sha256'].items():
    assert hashlib.sha256(pathlib.Path(filename).read_bytes()).hexdigest()==expected
bundle=verify_frozen_bundles(out)[seed]
assert not (bundle.folder/'evaluation').exists(), 'No silent repeat evaluation.'
assert not (out/f'seed{seed}_evaluation_complete.json').exists()
torch.set_num_threads(4)
records=[]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
for dataset in ('internal','external'):
    started_utc=now()
    print(f'Seed {seed} {dataset}: exploratory follow-up evaluation starts.',flush=True)
    def progress(k,n):
        if k%20==0 or k==n:
            text=f'Seed {seed} {dataset} {k}/{n}'
            print(text,flush=True)
            (out/f'seed{seed}_evaluation_progress.json').write_text(json.dumps({'seed':seed,'dataset':dataset,'checked':k,'total':n,'updated_utc':now()}),encoding='utf-8')
    folder=(evaluate_holdout(bundle,'data/PAPILA',exploratory_rerun=True,progress=progress)
            if dataset=='internal' else evaluate_chaksu(bundle,'data/Chaksu_Test.zip',progress=progress))
    path=folder/'model_eval_aggregate.json'
    report=json.loads(path.read_text(encoding='utf-8'))
    assert report['exploratory'] is True
    if dataset=='internal':
        report['exploratory_reason']='Follow-up training-seed stability experiment on the same cohort after baseline holdout inspection; first evaluation of this new frozen bundle. No seed or checkpoint selected using holdout results.'
    report['seed_stability_context']={'training_seed':seed,'split_seed':42,'followup_after_baseline_holdout_inspection':True,'protocol_created_utc':protocol['created_utc'],'protocol_sha256':hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest(),'both_new_checkpoints_frozen_before_evaluation':True,'evaluation_started_utc':started_utc}
    validate_report(report,bundle=bundle)
    path.write_bytes((json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
    shutil.copyfile(path,out/f'seed{seed}_{dataset}_aggregate.json')
    record={'seed':seed,'dataset':dataset,'evaluation_folder':str(folder),'run_id':bundle.run_id,'weights_sha256':bundle.weights_sha256,'n_images':report['n_images'],'n_failed':report['n_failed'],'started_utc':started_utc,'completed_utc':now()}
    records.append(record)
    (out/f'seed{seed}_{dataset}_completion.json').write_bytes((json.dumps(record,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({**record,'disc_dice':report['versus_expert1']['disc_dice']['mean'],'cup_dice':report['versus_expert1']['cup_dice']['mean'],'vcdr_mae':report['versus_expert1']['abs_vcdr_error'].get('mean')}),flush=True)
(out/f'seed{seed}_evaluation_complete.json').write_bytes((json.dumps({'seed':seed,'evaluations':records,'completed_utc':now()},indent=2)+'\n').encode('utf-8'))
print(f'Seed {seed} all follow-up evaluations complete.',flush=True)

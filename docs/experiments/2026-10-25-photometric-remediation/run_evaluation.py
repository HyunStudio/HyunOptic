import datetime,hashlib,json,pathlib,shutil
import torch
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.evaluate import evaluate_holdout,evaluate_chaksu
from hyunoptic.seg.report import validate_report

out=pathlib.Path('reports/remediation_20261025')
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,data): path.write_bytes((json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
protocol=load(out/'protocol.json'); frozen=load(out/'training_completion.json')
bundle=verify_bundle(frozen['bundle_folder'])
assert bundle.run_id==frozen['run_id'] and bundle.weights_sha256==frozen['weights_sha256']
assert not (bundle.folder/'evaluation').exists(), 'Exactly one evaluation per dataset; no silent repeat.'
for name,expected in protocol['source_file_sha256'].items(): assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==expected
for seed,name in ((42,'papila_real_v1_20261025'),(43,'papila_real_seed43_20261025'),(44,'papila_real_seed44_20261025')):
    old=verify_bundle(pathlib.Path('models')/name); identity=protocol['baseline_identities'][str(seed)]
    assert old.run_id==identity['run_id'] and old.weights_sha256==identity['weights_sha256']
torch.set_num_threads(4)
records=[]
for dataset in ('internal','external'):
    started=now()
    assert datetime.datetime.fromisoformat(started)>datetime.datetime.fromisoformat(frozen['completed_utc'])
    print(f'{dataset}: frozen photometric model exploratory evaluation starts.',flush=True)
    def progress(k,n):
        if k%20==0 or k==n:
            print(f'{dataset} {k}/{n}',flush=True)
            save(out/'evaluation_progress.json',{'dataset':dataset,'checked':k,'total':n,'updated_utc':now()})
    folder=(evaluate_holdout(bundle,'data/PAPILA',exploratory_rerun=True,progress=progress) if dataset=='internal'
            else evaluate_chaksu(bundle,'data/Chaksu_Test.zip',progress=progress))
    report=load(folder/'model_eval_aggregate.json')
    assert report['exploratory'] is True
    if dataset=='internal': report['exploratory_reason']='One photometric-augmentation remediation run after prior holdout/external inspection; first evaluation of this newly frozen model. No outcome-driven retries.'
    report['remediation_context']={'photometric_policy':'camera_robust_v2','training_seed':43,'split_seed':42,'protocol_created_utc':protocol['created_utc'],'protocol_sha256':hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest(),'evaluation_started_utc':started,'checkpoint_frozen_before_evaluation':True}
    validate_report(report,bundle=bundle);save(folder/'model_eval_aggregate.json',report)
    shutil.copyfile(folder/'model_eval_aggregate.json',out/f'{dataset}_aggregate.json')
    record={'dataset':dataset,'evaluation_folder':str(folder),'run_id':bundle.run_id,'weights_sha256':bundle.weights_sha256,'started_utc':started,'completed_utc':now()}
    save(out/f'{dataset}_completion.json',record);records.append(record)
    print(json.dumps({**record,'n_images':report['n_images'],'n_failed':report['n_failed'],'failure_categories':report['failure_categories'],'disc_dice':report['versus_expert1']['disc_dice'].get('mean'),'cup_dice':report['versus_expert1']['cup_dice'].get('mean'),'vcdr_mae':report['versus_expert1']['abs_vcdr_error'].get('mean')}),flush=True)
save(out/'evaluation_complete.json',{'completed_utc':now(),'evaluations':records})
print('Both follow-up evaluations completed; no additional training runs.',flush=True)

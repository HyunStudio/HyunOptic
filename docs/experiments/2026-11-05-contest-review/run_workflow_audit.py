import json, shutil, time, sys
from pathlib import Path
import torch
from hyunoptic.review.store import ReviewStore
from hyunoptic.review.runner import run_next
from hyunoptic.review.export import export_session, verify_export
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.provenance import source_commit

root=Path(sys.argv[1]).resolve()
root.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(4)
demo=Path(sys.argv[2]).resolve()
def models_at(base):
    result=[]
    for folder in sorted(base.iterdir()):
        b=verify_bundle(folder)
        result.append(dict(folder=str(folder),identity=b.identity,run_id=b.run_id,
                           weights_sha256=b.weights_sha256,data_status=dict(synthetic=True,partial=True)))
    return result
models=models_at(demo/'models')
inputs=[(p.name,p.read_bytes()) for p in sorted((demo/'inputs').glob('*.jpg'))]
out={"source_import":__import__('hyunoptic').__file__,"synthetic_only":True,"checks":[]}
def check(name, expected, actual):
    assert expected==actual,(name,expected,actual)
    out['checks'].append(dict(name=name,expected=expected,actual=actual))
def run(name,items,interrupt=False):
    start=time.perf_counter(); store=ReviewStore(root/name)
    sid=store.create_session(items,models,software_commit=source_commit())
    if interrupt:
        for _ in range(3):assert run_next(store,sid)
        case=store.next_pending(sid);store.claim(case['id'])
        store=ReviewStore(root/name);store.recover(sid)
    while run_next(store,sid):pass
    cases=store.cases(sid)
    good=[c for c in cases if c['status']=='complete']
    c=good[0];store.decide(c['id'],'held',['uncertain'],'Private synthetic audit',c['revision'])
    reopened=ReviewStore(root/name)
    check(name+'_held_reopened',1,sum(c['review_state']=='held' for c in reopened.cases(sid)))
    verification=verify_export(export_session(reopened,sid,root/(name+'.zip')))
    check(name+'_export',True,verification['valid'])
    summary=dict(total=len(cases),complete=len(good),error=sum(c['status']=='error' for c in cases),
                 predictions=sum(len(c['predictions']) for c in cases),seconds=round(time.perf_counter()-start,3))
    out[name]=summary
    return [[p['labels_sha256'] for p in c['predictions']] for c in sorted(good,key=lambda c:c['ordinal'])]
a=run('ordinary',inputs[:2]);b=run('repeat',inputs[:2]);check('repeat_prediction_png_hashes',a,b)
run('demanding',[(f'synthetic_repeat_{i}.jpg',inputs[i%4][1]) for i in range(100)]+[('unreadable.png',b'not an image')],True)
check('demanding_counts',[101,100,1,200],[out['demanding'][k] for k in ['total','complete','error','predictions']])
shutil.copytree(demo/'models',root/'fault_models')
fault_models=models_at(root/'fault_models');store=ReviewStore(root/'fault_store')
sid=store.create_session(inputs[:3],fault_models,software_commit=source_commit())
assert run_next(store,sid);assert run_next(store,sid)
first=next(c for c in store.cases(sid) if c['status']=='complete')
store.decide(first['id'],'held',['uncertain'],'Synthetic fault audit',first['revision'])
(Path(fault_models[0]['folder'])/'weights.pt').write_bytes(b'controlled hash mismatch; never deserialize')
assert run_next(store,sid)
cases=ReviewStore(root/'fault_store').cases(sid)
check('changed_bundle_counts',[2,1,1],[sum(c['status']=='complete' for c in cases),sum(c['status']=='error' for c in cases),sum(c['review_state']=='held' for c in cases)])
check('changed_bundle_export',True,verify_export(export_session(store,sid,root/'fault_export.zip'))['valid'])
out['interpretation']='Synthetic workflow execution; 100 repeated cases are not 100 patients. Recovery uses a controlled unfinished claim, not an OS crash. No accuracy or efficiency claim.'
(root/'workflow_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))

import collections, csv, datetime, hashlib, io, json, math, pathlib, re, shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.report import validate_report
from frozen_identity import verify_frozen_bundles

out=pathlib.Path('reports/seed_stability_20261025')
public_destination=pathlib.Path('docs/experiments/2026-10-25-seed-stability')
public=out/'public_evidence_staging'
protocol=json.loads((out/'protocol.json').read_text(encoding='utf-8'))
assert (out/'all_training_complete.json').exists()
for seed in (43,44): assert (out/f'seed{seed}_evaluation_complete.json').exists()
frozen_bundles=verify_frozen_bundles(out)
assert not public_destination.exists(), 'Never overwrite published experiment evidence.'
assert not public.exists(), 'A previous partial staging directory requires investigation.'
public.mkdir(parents=True)
def save(name,data):
    (public/name).write_bytes((json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))
def load(path): return json.loads(path.read_text(encoding='utf-8'))
rows=[]; histories={}; selected={}; verification=[]; reference_failure_sets=[]
baseline=verify_bundle('models/papila_real_v1_20261025')
for seed in (42,43,44):
    path=pathlib.Path('models/papila_real_v1_20261025' if seed==42 else f'models/papila_real_seed{seed}_20261025')
    bundle=frozen_bundles[seed]; histories[seed]=load(path/'history.json')
    cfg=load(path/'config.json')
    assert cfg=={**protocol['fixed_config_except_training_seed'],'seed':seed}
    assert len(histories[seed])==40
    assert max(histories[seed],key=lambda row:row['val_score'])['epoch']==bundle.manifest['training']['best_epoch']
    assert all(math.isfinite(row['train_loss']) for row in histories[seed])
    for key in ('source_content_sha256','split_manifest_sha256','n_images','n_patients'):
        assert bundle.manifest['training'][key]==baseline.manifest['training'][key]
    selected[seed]={'seed':seed,'run_id':bundle.run_id,'weights_sha256':bundle.weights_sha256,'best_epoch':bundle.manifest['training']['best_epoch'],'validation_score':bundle.manifest['training']['best_validation_score'],'training_seconds':bundle.manifest['runtime']['training_seconds']}
    for filename in ('history.json','config.json','bundle_manifest.json'):
        save(f'seed{seed}_{filename}',load(path/filename))
    for dataset in ('internal','external'):
        completion=load(pathlib.Path('reports/real_20261025')/f'{dataset}_completion.json' if seed==42 else out/f'seed{seed}_{dataset}_completion.json')
        folder=pathlib.Path(completion['evaluation_folder'])
        report=validate_report(load(folder/'model_eval_aggregate.json'),bundle=bundle)
        private=load(folder/'model_eval_private_cases.json')['cases']
        if seed!=42:
            assert report['exploratory'] is True
            assert completion['run_id']==bundle.run_id and completion['weights_sha256']==bundle.weights_sha256
            assert report['seed_stability_context']['protocol_sha256']==hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest()
            assert datetime.datetime.fromisoformat(completion['started_utc'])>datetime.datetime.fromisoformat(load(out/'all_training_complete.json')['completed_utc'])
        assert len(private)==report['n_images']
        failures=collections.Counter(row['failure_category'] for row in private if row['status']!='ok')
        assert dict(failures)==report['failure_categories'] and sum(failures.values())==report['n_failed']
        if dataset=='external': reference_failure_sets.append({row['case_id'] for row in private if row.get('failure_category')=='load_or_geometry_error'})
        for ref,key in (('expert1','versus_expert1'),('expert2','versus_expert2_sensitivity')):
            for metric in ('disc_dice','cup_dice','abs_vcdr_error'):
                values=[row[ref][metric] for row in private if row.get(ref) and metric in row[ref]]
                assert len(values)==report[key][metric]['n']
                if values:
                    assert math.isclose(float(np.mean(values)),report[key][metric]['mean'],abs_tol=1e-12)
                    assert math.isclose(float(np.median(values)),report[key][metric]['median'],abs_tol=1e-12)
            values=[row[ref]['abs_vcdr_error'] for row in private if row.get(ref) and 'abs_vcdr_error' in row[ref]]
            assert sum(v>0.10 for v in values)==report[key]['n_vcdr_error_over_threshold']
            m=report[key]
            rows.append({'seed':seed,'dataset':dataset,'reference':ref,'followup_exploratory':seed!=42 or dataset=='external','selected_epoch':selected[seed]['best_epoch'],'validation_score':selected[seed]['validation_score'],'total_images':report['n_images'],'dice_n':m['cup_dice']['n'],'disc_dice':m['disc_dice'].get('mean'),'cup_dice':m['cup_dice'].get('mean'),'vcdr_n':m['abs_vcdr_error']['n'],'vcdr_mae':m['abs_vcdr_error'].get('mean'),'n_failed':report['n_failed'],'failure_categories':json.dumps(report['failure_categories'],sort_keys=True),'n_vcdr_error_over_0_10':m['n_vcdr_error_over_threshold'],'fraction_vcdr_error_over_0_10':m['fraction_vcdr_error_over_threshold']})
        save(f'seed{seed}_{dataset}_aggregate.json',report)
        verification.append({'seed':seed,'dataset':dataset,'run_id':bundle.run_id,'n_images':len(private),'n_failed':report['n_failed'],'all_aggregate_means_medians_counts_recomputed':True})
assert reference_failure_sets[0]==reference_failure_sets[1]==reference_failure_sets[2]
assert len(reference_failure_sets[0])==25
assert baseline.weights_sha256==protocol['baseline_weights_sha256']
stats=[]
for dataset in ('internal','external'):
    for ref in ('expert1','expert2'):
        group=[r for r in rows if r['dataset']==dataset and r['reference']==ref]
        assert [r['seed'] for r in group]==[42,43,44]
        for metric in ('disc_dice','cup_dice','vcdr_mae'):
            values=np.array([r[metric] for r in group],dtype=float)
            stats.append({'dataset':dataset,'reference':ref,'metric':metric,'n_runs':3,'mean':float(values.mean()),'sample_sd_ddof1':float(values.std(ddof=1)),'minimum':float(values.min()),'maximum':float(values.max()),'range':float(np.ptp(values))})
def write_csv(name,records):
    stream=io.StringIO(newline=''); writer=csv.DictWriter(stream,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    (public/name).write_bytes(stream.getvalue().encode('utf-8-sig'))
write_csv('per_run_metrics.csv',rows); write_csv('seed_variation_summary.csv',stats)
save('protocol.json',protocol)
save('training_completions.json',list(selected.values()))
save('evidence_verification.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':verification,'same_source_and_patient_split_all_three_runs':True,'configs_identical_except_training_seed':True,'reference_failure_case_sets_identical_across_seeds':True,'n_external_reference_failures':25,'baseline_unchanged':True,'note':'Arithmetic/provenance verification, not independent scientific certification. Private case rows are not published.'})
save('results_summary.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'training_seeds':[42,43,44],'fixed_split_seed':42,'selection':list(selected.values()),'per_run':rows,'descriptive_seed_variation':stats,'limits':['Three seeds on one fixed patient split; not three independent cohorts.','Sample SD describes seed variation, not clinical or population uncertainty.','All new follow-up holdout/external results are exploratory after baseline inspection.','Original data, private cases and weights excluded.','CUDA nondeterminism warning remains.']})
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
colors={42:'#0B5CAD',43:'#C45D00',44:'#27815D'}
fig,axes=plt.subplots(1,3,figsize=(15,4.2))
for seed,h in histories.items():
    for ax,key,title in zip(axes,('train_loss','val_disc_dice','val_cup_dice'),('Training loss','Validation disc Dice (384 px)','Validation cup Dice (384 px)')):
        ax.plot([r['epoch'] for r in h],[r[key] for r in h],label=f'Seed {seed}',color=colors[seed]);ax.set(title=title,xlabel='Epoch');ax.grid(alpha=.18)
        if key!='train_loss':
            k=selected[seed]['best_epoch'];ax.scatter([k],[h[k-1][key]],color=colors[seed],s=30,zorder=3)
axes[0].legend(fontsize=9);fig.tight_layout();fig.savefig(public/'training_seed_curves.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(15,4.2))
for ax,metric,title in zip(axes,('disc_dice','cup_dice','vcdr_mae'),('Disc Dice (higher is better)','Cup Dice (higher is better)','vCDR MAE (lower is better)')):
    for i,seed in enumerate((42,43,44)):
        vals=[next(r[metric] for r in rows if r['seed']==seed and r['dataset']==d and r['reference']=='expert1') for d in ('internal','external')]
        bars=ax.bar(np.arange(2)+(i-1)*.23,vals,.23,label=f'Seed {seed}',color=colors[seed]);ax.bar_label(bars,fmt='%.3f',fontsize=8,padding=3)
    ax.set_xticks([0,1],['PAPILA holdout','Chaksu exploratory']);ax.set(title=title,ylim=(0,1.08 if metric!='vcdr_mae' else max(.3,max(r['vcdr_mae'] for r in rows)*1.2)));ax.grid(axis='y',alpha=.18)
axes[0].legend(fontsize=8,loc='lower left');fig.tight_layout();fig.savefig(public/'seed_performance.png',dpi=160);plt.close(fig)
primary=[r for r in rows if r['reference']=='expert1']
table='\n'.join(f"| {r['seed']} | {r['dataset']} | {r['selected_epoch']} | {r['dice_n']} | {r['disc_dice']:.4f} | {r['cup_dice']:.4f} | {r['vcdr_n']} | {r['vcdr_mae']:.4f} | {r['n_failed']} |" for r in primary)
variation='\n'.join(f"| {s['dataset']} | {s['metric']} | {s['mean']:.4f} ± {s['sample_sd_ddof1']:.4f} | {s['minimum']:.4f}–{s['maximum']:.4f} |" for s in stats if s['reference']=='expert1')
readme=f'''# Fixed-split training-seed stability — 2026-10-25

The user requested two additional seeds after the [seed-42 baseline](../2026-10-25-real-data-baseline/README.md). This is a **follow-up exploratory analysis**, including all three runs without choosing a winner from holdout/external performance.

Only training seed changed to 43 and 44. Split seed remains 42; identical patient grouping, source-content hash, 292 development / 98 validation / 98 holdout images, original 384 px U-Net, 40 epochs, batch 4, optimizer, schedule and augmentation. Each checkpoint was selected on validation only, and both new checkpoints were frozen before their follow-up evaluations. No product-code changes.

## Expert-1 original-resolution results

| Seed | Evaluation | Selected epoch | Dice n | Disc Dice | Cup Dice | vCDR n | vCDR MAE | Failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{table}

![Three recorded training runs](training_seed_curves.png)

![Per-seed expert-1 performance](seed_performance.png)

## Descriptive variation over three training seeds

| Evaluation | Metric | Mean ± sample SD | Min–max |
|---|---|---:|---:|
{variation}

Dice and MAE are means over scored images, not pooled-pixel scores. SD uses ddof=1 over the three run-level means. Three seeds on one fixed split measure only training-seed variation; these are not three independent cohorts and the SD is not a patient-population confidence interval. Denominators can differ with invalid predictions; compare them alongside each score. Expert-2 sensitivity and error >0.10 counts are in [per_run_metrics.csv](per_run_metrics.csv) and aggregate JSON.

## Failures and limitations

- All three external runs have the same 25 original-reference loading/containment failures; original masks are unchanged. Additional invalid predictions and undefined vCDR remain counted separately in each aggregate report. Dice includes invalid-geometry predictions where masks exist. No claim of complete 336-image metric coverage.
- Baseline internal evaluation retains its original status; all new internal evaluations explicitly carry exploratory=true and a follow-up reason. All external evaluations are exploratory.
- No checkpoint, seed, setting or annotation was selected/changed using follow-up holdout or external results. Each of the two prespecified new seeds is reported, including failures.
- CUDA nll_loss2d has no deterministic implementation in the recorded environment; fixed seeds do not guarantee identical weights on rerun. No clinical, diagnostic, superiority or untouched external-confirmation claim.
- Different hardware/runtime scheduling may change measured training time; timing is not a speed benchmark.

## Reproducibility and evidence

Sources: [PAPILA v2 (GPL 3.0+)](https://doi.org/10.6084/m9.figshare.14798004.v2), [Kovalyk et al. 2022](https://doi.org/10.1038/s41597-022-01388-1); [Chákṣu v2 (CC BY 4.0)](https://doi.org/10.6084/m9.figshare.20123135.v2), [Kumar et al. 2023](https://doi.org/10.1038/s41597-023-01943-4). See baseline directory for original archive provenance and complete structural-audit failures.

`protocol.json` was saved before additional training and records exact settings, source hashes and environment. Each seed's config, history, bundle manifest, aggregate metrics and weights hash are recorded here. Weights, raw data, split identifiers and private case results remain local. The public bundle manifests describe original local models; this directory cannot be loaded as a model bundle.

`evidence_verification.json` records independent NumPy arithmetic from local private rows, same-source/split/config checks and validation-only selection checks. It is not independent scientific certification. `results_summary.json`, [per_run_metrics.csv](per_run_metrics.csv), [seed_variation_summary.csv](seed_variation_summary.csv) preserve all values. `evidence_manifest.json` hashes every other public file.

### Independent numerical reproduction

In a fresh checkout of protocol code_commit, obtain the official archives under their terms and prepare the environment using the [baseline instructions](../2026-10-25-real-data-baseline/REPRODUCE.txt). For example, for seed 43:

```powershell
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
hyunoptic-seg train --papila-root data/PAPILA --output models/reproduced_seed43 --image-size 384 --epochs 40 --batch-size 4 --lr 0.001 --weight-decay 0.0001 --base-channels 16 --depth 4 --seed 43 --split-seed 42 --device cuda
hyunoptic-seg evaluate --bundle models/reproduced_seed43 --papila-root data/PAPILA --exploratory-rerun
hyunoptic-seg evaluate --bundle models/reproduced_seed43 --chaksu-test-zip data/Chaksu_Test.zip
```

Repeat with --seed 44 and a new `models/reproduced_seed44` folder. Exact weights are subject to the recorded CUDA nondeterminism limitation.

### Actual local orchestration records

[run_training.py](run_training.py), [run_evaluation.py](run_evaluation.py), [frozen_identity.py](frozen_identity.py) and [collect_results.py](collect_results.py) record the orchestration actually used and call existing package APIs. They are audit records with additional **local prerequisites**: the original/recreated baseline bundle at `models/papila_real_v1_20261025`, baseline completion JSONs and private case rows under `reports/real_20261025`, plus the new experiment's protocol/completion files. Those private assets are not distributed, so copying the scripts into a public checkout alone is insufficient. The numerical reproduction commands above do not require them. The runner refuses to replace an existing protocol/model, evaluator refuses repeat evaluation, and collector stages evidence before publishing it.
'''
(public/'README.md').write_bytes(readme.encode('utf-8'))
for filename in ('run_training.py','run_evaluation.py','collect_results.py','frozen_identity.py','check_frozen_identity.py'):
    (public/filename).write_bytes((out/filename).read_bytes().replace(b'\r\n',b'\n'))
(public/'.gitattributes').write_bytes(b'* -text\n')
for path in public.iterdir():
    if path.suffix in {'.json','.md','.csv','.py'}:
        content=path.read_text(encoding='utf-8-sig')
        assert not re.search(r'RET\d{3}(?:OD|OS)|[A-Za-z]:[/\\]+Users[/\\]',content),path.name
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(public.iterdir())}
save('evidence_manifest.json',manifest)
for name,expected in manifest.items():
    assert hashlib.sha256((public/name).read_bytes()).hexdigest()==expected
root=pathlib.Path.cwd().resolve()
assert public.resolve().is_relative_to(root) and public_destination.resolve().is_relative_to(root)
public.rename(public_destination)
public=public_destination
print(json.dumps({'public':str(public),'primary_results':primary,'primary_variation':[s for s in stats if s['reference']=='expert1']},ensure_ascii=True),flush=True)

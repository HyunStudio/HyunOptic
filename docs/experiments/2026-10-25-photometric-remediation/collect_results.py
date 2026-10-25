import collections,csv,datetime,hashlib,io,json,math,pathlib,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from hyunoptic.seg.bundle import verify_bundle
from hyunoptic.seg.report import validate_report

out=pathlib.Path('reports/remediation_20261025')
destination=pathlib.Path('docs/experiments/2026-10-25-photometric-remediation')
public=out/'export_staging'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def save(name,data): (public/name).write_bytes((json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
assert (out/'evaluation_complete.json').exists()
assert not destination.exists() and not public.exists(), 'Never overwrite evidence; investigate partial staging separately.'
protocol=load(out/'protocol.json'); frozen=load(out/'training_completion.json')
new=verify_bundle(frozen['bundle_folder']); baseline=verify_bundle('models/papila_real_seed43_20261025')
assert new.run_id==frozen['run_id'] and new.weights_sha256==frozen['weights_sha256']
for seed,name in ((42,'papila_real_v1_20261025'),(43,'papila_real_seed43_20261025'),(44,'papila_real_seed44_20261025')):
    bundle=verify_bundle(pathlib.Path('models')/name);identity=protocol['baseline_identities'][str(seed)]
    assert bundle.run_id==identity['run_id'] and bundle.weights_sha256==identity['weights_sha256']
for key in ('source_content_sha256','split_manifest_sha256','n_images','n_patients'):
    assert new.manifest['training'][key]==baseline.manifest['training'][key]
old_config=load(baseline.folder/'config.json'); new_config=load(new.folder/'config.json')
assert {k:v for k,v in new_config.items() if k not in ('photometric_policy','photometric_generator_seed','augmentations')}=={k:v for k,v in old_config.items() if k!='augmentations'}
assert new_config['photometric_policy']=='camera_robust_v2' and new_config['photometric_generator_seed']==1000046
histories={}; reports={}; private={}; verification=[]; rows=[]; paired=[]
public.mkdir()
for label,bundle in (('baseline_seed43',baseline),('camera_robust_seed43',new)):
    history=load(bundle.folder/'history.json');histories[label]=history
    assert len(history)==40 and all(math.isfinite(r['train_loss']) for r in history)
    assert max(history,key=lambda r:r['val_score'])['epoch']==bundle.manifest['training']['best_epoch']
    for name in ('config.json','history.json','bundle_manifest.json'): save(label+'_'+name,load(bundle.folder/name))
    for dataset in ('internal','external'):
        completion=load(pathlib.Path('reports/seed_stability_20261025')/f'seed43_{dataset}_completion.json' if label=='baseline_seed43' else out/f'{dataset}_completion.json')
        folder=pathlib.Path(completion['evaluation_folder'])
        report=validate_report(load(folder/'model_eval_aggregate.json'),bundle=bundle)
        cases=load(folder/'model_eval_private_cases.json')['cases']
        assert report['exploratory'] is True
        if label!='baseline_seed43':
            assert completion['run_id']==new.run_id and completion['weights_sha256']==new.weights_sha256
            assert datetime.datetime.fromisoformat(completion['started_utc'])>datetime.datetime.fromisoformat(frozen['completed_utc'])
            assert report['remediation_context']['protocol_sha256']==hashlib.sha256((out/'protocol.json').read_bytes()).hexdigest()
        assert len(cases)==report['n_images']
        failures=collections.Counter(r['failure_category'] for r in cases if r['status']!='ok')
        assert dict(failures)==report['failure_categories'] and sum(failures.values())==report['n_failed']
        private[(label,dataset)]={r['image_id'] if dataset=='internal' else r['case_id']:r for r in cases}
        reports[(label,dataset)]=report
        for ref,key in (('expert1','versus_expert1'),('expert2','versus_expert2_sensitivity')):
            for metric in ('disc_dice','cup_dice','abs_vcdr_error'):
                values=[r[ref][metric] for r in cases if r.get(ref) and metric in r[ref]]
                assert len(values)==report[key][metric]['n']
                if values:
                    assert math.isclose(float(np.mean(values)),report[key][metric]['mean'],abs_tol=1e-12)
                    assert math.isclose(float(np.median(values)),report[key][metric]['median'],abs_tol=1e-12)
            errors=[r[ref]['abs_vcdr_error'] for r in cases if r.get(ref) and 'abs_vcdr_error' in r[ref]]
            assert sum(v>.10 for v in errors)==report[key]['n_vcdr_error_over_threshold']
            m=report[key]; ref_failures=failures.get('load_or_geometry_error',0)
            rows.append({'model':label,'dataset':dataset,'reference':ref,'selected_epoch':bundle.manifest['training']['best_epoch'],'validation_score':bundle.manifest['training']['best_validation_score'],'total_images':report['n_images'],'dice_n':m['cup_dice']['n'],'disc_dice':m['disc_dice'].get('mean'),'cup_dice':m['cup_dice'].get('mean'),'vcdr_n':m['abs_vcdr_error']['n'],'vcdr_mae':m['abs_vcdr_error'].get('mean'),'model_failures':report['n_failed']-ref_failures,'reference_failures':ref_failures,'failure_categories':json.dumps(report['failure_categories'],sort_keys=True),'n_vcdr_error_over_0_10':m['n_vcdr_error_over_threshold'],'fraction_vcdr_error_over_0_10':m['fraction_vcdr_error_over_threshold']})
        verification.append({'model':label,'dataset':dataset,'n_images':len(cases),'aggregate_means_medians_counts_recomputed':True,'n_failed':report['n_failed']})
        save(label+'_'+dataset+'_aggregate.json',report)
for dataset in ('internal','external'):
    old=private[('baseline_seed43',dataset)];current=private[('camera_robust_seed43',dataset)]
    assert set(old)==set(current)
    old_ref_errors={key for key,row in old.items() if row.get('failure_category')=='load_or_geometry_error'}
    new_ref_errors={key for key,row in current.items() if row.get('failure_category')=='load_or_geometry_error'}
    assert old_ref_errors==new_ref_errors
    if dataset=='external': assert len(old_ref_errors)==25
    eligible=sorted(set(old)-old_ref_errors)
    for ref in ('expert1','expert2'):
        common=[key for key in eligible if 'abs_vcdr_error' in old[key].get(ref,{}) and 'abs_vcdr_error' in current[key].get(ref,{})]
        old_values=[old[k][ref]['abs_vcdr_error'] for k in common]; new_values=[current[k][ref]['abs_vcdr_error'] for k in common]
        old_penalty=[old[k].get(ref,{}).get('abs_vcdr_error',1.0) for k in eligible]
        new_penalty=[current[k].get(ref,{}).get('abs_vcdr_error',1.0) for k in eligible]
        paired.append({'dataset':dataset,'reference':ref,'reference_valid_n':len(eligible),'common_measurable_n':len(common),'baseline_common_vcdr_mae':float(np.mean(old_values)) if common else None,'new_common_vcdr_mae':float(np.mean(new_values)) if common else None,'new_minus_baseline_common_vcdr_mae':float(np.mean(np.asarray(new_values)-old_values)) if common else None,'baseline_descriptive_invalid_as_1_penalty':float(np.mean(old_penalty)),'new_descriptive_invalid_as_1_penalty':float(np.mean(new_penalty)),'penalty_is_not_measured_mae_or_clinical_utility':True})
def write_csv(name,data):
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(data[0]),lineterminator='\n');writer.writeheader();writer.writerows(data)
    (public/name).write_bytes(stream.getvalue().encode('utf-8-sig'))
write_csv('comparison_metrics.csv',rows);write_csv('paired_and_penalized_metrics.csv',paired)
primary=[r for r in rows if r['reference']=='expert1']
old_external=next(r for r in primary if r['model']=='baseline_seed43' and r['dataset']=='external')
new_external=next(r for r in primary if r['model']=='camera_robust_seed43' and r['dataset']=='external')
old_internal=next(r for r in primary if r['model']=='baseline_seed43' and r['dataset']=='internal')
new_internal=next(r for r in primary if r['model']=='camera_robust_seed43' and r['dataset']=='internal')
rule=protocol['success_rule']
decision={'predeclared_external_rule_met':bool(new_external['model_failures']<rule['external_model_failures_less_than'] and new_external['vcdr_mae'] is not None and new_external['vcdr_mae']<rule['external_conditional_vcdr_mae_less_than'] and new_external['cup_dice']>=rule['external_cup_dice_at_least']),
          'internal_tradeoff_flag':bool(old_internal['disc_dice']-new_internal['disc_dice']>.02 or old_internal['cup_dice']-new_internal['cup_dice']>.02 or new_internal['model_failures']>6),
          'interpretation':'A prespecified descriptive rule on already inspected cohorts, not significance, stability, causal or clinical proof.'}
save('results_summary.json',{'protocol':protocol,'baseline_run_id':baseline.run_id,'new_run_id':new.run_id,'new_weights_sha256':new.weights_sha256,'comparison':rows,'paired_and_penalized':paired,'decision':decision})
save('protocol.json',protocol);save('training_completion.json',frozen)
save('evidence_verification.json',{'checks':verification,'same_source_patient_split_and_training_seed':True,'configs_differ_only_in_photometric_policy':True,'reference_failure_sets_identical':True,'all_original_three_seed_bundles_unchanged':True,'checkpoint_frozen_before_evaluation':True,'note':'Local arithmetic/provenance checks, not independent scientific certification. Private rows are excluded.'})
for name in ('existing_failure_summary.json','mask_diagnostic_summary.json','colour_diagnostic_summary.json'): save(name,load(out/name))
for name in ('run_training.py','run_evaluation.py','collect_results.py','diagnose_existing.py','diagnose_masks.py','diagnose_colour.py'):
    (public/name).write_bytes((out/name).read_bytes().replace(b'\r\n',b'\n'))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'baseline_seed43':'#0B5CAD','camera_robust_seed43':'#C45D00'}
fig,axes=plt.subplots(1,2,figsize=(12,4.4))
for label,h in histories.items():
    axes[0].plot([r['epoch'] for r in h],[r['train_loss'] for r in h],color=colors[label],label=label)
    axes[1].plot([r['epoch'] for r in h],[r['val_score'] for r in h],color=colors[label],label=label)
axes[0].set(title='Training loss (different augmentation difficulty)',xlabel='Epoch',ylabel='Loss');axes[0].legend(fontsize=8)
axes[1].set(title='Validation mean disc/cup Dice (384 px)',xlabel='Epoch',ylabel='Dice',ylim=(0,1))
for ax in axes: ax.grid(alpha=.18)
fig.tight_layout();fig.savefig(public/'training_comparison.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(1,4,figsize=(16,4.4))
for ax,metric,title in zip(axes,('disc_dice','cup_dice','vcdr_mae','model_failures'),('Disc Dice','Cup Dice','vCDR MAE (conditional)','Model failures')):
    for i,label in enumerate(colors):
        values=[next(r[metric] for r in primary if r['model']==label and r['dataset']==d) for d in ('internal','external')]
        bars=ax.bar(np.arange(2)+(i-.5)*.35,values,.35,label=label,color=colors[label]);ax.bar_label(bars,fmt='%.3f' if metric!='model_failures' else '%d',fontsize=8,padding=3)
    ax.set_xticks([0,1],['Internal','External']);ax.set(title=title);ax.grid(axis='y',alpha=.18)
    if metric in ('disc_dice','cup_dice'): ax.set_ylim(0,1.08)
    else: ax.set_ylim(0,max(.1,max(r[metric] for r in primary))*1.25)
axes[0].legend(fontsize=7,loc='lower left');fig.tight_layout();fig.savefig(public/'performance_comparison.png',dpi=160);plt.close(fig)
table='\n'.join(f"| {r['model']} | {r['dataset']} | {r['dice_n']} | {r['disc_dice']:.4f} | {r['cup_dice']:.4f} | {r['vcdr_n']} | {r['vcdr_mae']:.4f} | {r['model_failures']} | {r['reference_failures']} |" for r in primary)
paired_table='\n'.join(f"| {r['dataset']} | {r['common_measurable_n']} | {r['baseline_common_vcdr_mae']:.4f} | {r['new_common_vcdr_mae']:.4f} | {r['baseline_descriptive_invalid_as_1_penalty']:.4f} | {r['new_descriptive_invalid_as_1_penalty']:.4f} |" for r in paired if r['reference']=='expert1')
readme=f'''# One photometric-remediation follow-up — 2026-10-25

One actual 40-epoch training run tests an image-only photometric-domain hypothesis after the [three-seed experiment](../2026-10-25-seed-stability/README.md). All results are **exploratory**, using already inspected cohorts. The pretraining protocol fixes seed43/split42, all original settings except the explicitly selected `camera_robust_v2` photometry, and a one-run budget. No outcome-driven second attempt, seed selection, postprocess change or source-mask repair.

## Diagnosis and change

The prior seed43 model has 16 external empty-cup failures: six had no raw cup and ten lost raw cup pixels during existing disc-component filtering. On selected high/low-error diagnostic cases, cup-component-only filtering had mixed effects and did not resolve contiguous overextension. These selected cases are not dataset performance estimates.

Image-only samples (32 PAPILA development;16 per external camera) have mean red/green ratios 2.903 / Bosch1.512 / Forus2.390 / Remidio1.359. This suggests a color/exposure mismatch; it does not prove causality. See diagnostic JSON and scripts for exact sampling/masking definitions.

`camera_robust_v2` widens brightness/contrast to 0.7–1.3, adds independent RGB gains0.65–1.35 and gamma0.7–1.5, preserves black pixels and leaves targets unchanged by photometry. Extra draws use a separate generator (seed1000046), preserving the legacy main RNG for shuffle/spatial transforms. The default `baseline_v1` behavior/config remains compatible. Model/loss/inference/postprocessing are unchanged. General photometric-jitter semantics: [official PyTorch documentation](https://docs.pytorch.org/vision/stable/generated/torchvision.transforms.ColorJitter.html); the bounded policy here is explicitly defined by this project.

## Actual original-resolution results, expert1

New selected epoch: **{new.manifest['training']['best_epoch']}**; validation mean disc/cup Dice **{new.manifest['training']['best_validation_score']:.4f}**. Same source/split hashes and development292/validation98/holdout98 images; 146/49/49 patients.

| Model | Evaluation | Dice n | Disc Dice | Cup Dice | vCDR n | vCDR MAE | Model failures | Reference failures |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{table}

Dice/MAE are per-image means. Internal total98 and external total336 are unchanged. Invalid predictions remain in Dice when masks exist; undefined vCDR is excluded from conditional MAE. The same25 external reference failures are retained. Expert2 sensitivity and errors>0.10 are in comparison_metrics.csv and aggregate reports.

![Training and validation curves](training_comparison.png)

![Original-resolution comparison](performance_comparison.png)

## Paired and failure-aware descriptive comparisons

| Evaluation | Common measurable n | Baseline paired MAE | New paired MAE | Baseline invalid=1 penalty | New invalid=1 penalty |
|---|---:|---:|---:|---:|---:|
{paired_table}

Paired MAE uses identical cases for both models, not the whole cohort. The separate penalty assigns1 to model-invalid predictions over all reference-valid cases (98 internal/311 external). This is an arbitrary predeclared research summary, **not measured MAE, clinical utility, or a confidence estimate**. It prevents coverage changes being hidden behind conditional MAE. No private case IDs are published.

## Predeclared decision and limitations

- External rule met: **{decision['predeclared_external_rule_met']}** (fewer than16 model failures, vCDR MAE<0.25531009 and Cup Dice>=0.55487019).
- Internal tradeoff flag: **{decision['internal_tradeoff_flag']}** (disc/cup drop>0.02 or model failures>6).
- These descriptive thresholds were recorded before training; no statistical significance or clinical interpretation is implied. One new run does not establish seed stability, causal benefit or generalization. The seed43 comparator was deliberately chosen after prior failure diagnosis, not as an untouched control. See the original three-seed range for context.
- Human annotations and pixel-span conventions can differ across datasets. Original reference masks, measurement definitions and failure gates were preserved. Full five-reader structural verification remains false; do not claim complete336-image performance.
- GPU nll_loss2d nondeterminism warning remains; fixed seeds do not guarantee bitwise-repeatable weights. No clinical/diagnostic claim.

## Evidence and reproduction

Protocol/code hashes, diagnostic aggregate JSON, each model's config/history/bundle manifest, aggregate results and CSV comparisons are included. New weights SHA256: `{new.weights_sha256}`. Original images, masks, weights, split identifiers and per-case rows remain local. Bundle manifests describe original local models and cannot be loaded from this aggregate-only directory.

Use a fresh checkout of protocol.code_commit and the [baseline environment/source instructions](../2026-10-25-real-data-baseline/REPRODUCE.txt). Obtain [PAPILA v2 (GPL3.0+)](https://doi.org/10.6084/m9.figshare.14798004.v2), [Kovalyk et al.2022](https://doi.org/10.1038/s41597-022-01388-1), and [Chákṣu v2 (CC BY4.0)](https://doi.org/10.6084/m9.figshare.20123135.v2), [Kumar et al.2023](https://doi.org/10.1038/s41597-023-01943-4), under their terms.

```powershell
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
$env:CUBLAS_WORKSPACE_CONFIG=':4096:8'
hyunoptic-seg train --papila-root data/PAPILA --output models/new_photometric_run --image-size 384 --epochs 40 --batch-size 4 --lr 0.001 --weight-decay 0.0001 --base-channels 16 --depth 4 --seed 43 --split-seed 42 --device cuda --photometric-policy camera_robust_v2
hyunoptic-seg evaluate --bundle models/new_photometric_run --papila-root data/PAPILA --exploratory-rerun
hyunoptic-seg evaluate --bundle models/new_photometric_run --chaksu-test-zip data/Chaksu_Test.zip
```

The actual orchestration scripts are audit records requiring the original local bundles, completion files and private evaluation rows. Copying them alone into a public checkout is insufficient; the CLI commands independently reproduce a numerical experiment. The collector independently recomputes arithmetic, verifies unchanged originals and stages evidence before publishing. `evidence_manifest.json` hashes every other public file. These local checks are not independent scientific certification.
'''
(public/'README.md').write_bytes(readme.encode('utf-8'))
(public/'.gitattributes').write_bytes(b'* -text\n')
for path in public.iterdir():
    if path.suffix in ('.md','.json','.csv','.py'):
        assert not re.search(r'RET\d{3}(?:OD|OS)|[A-Za-z]:[/\\]+Users[/\\]',path.read_text(encoding='utf-8-sig')),path.name
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(public.iterdir())}
save('evidence_manifest.json',manifest)
for name,expected in manifest.items(): assert hashlib.sha256((public/name).read_bytes()).hexdigest()==expected
root=pathlib.Path.cwd().resolve()
assert public.resolve().is_relative_to(root) and destination.resolve().is_relative_to(root)
public.rename(destination)
print(json.dumps({'public':str(destination),'primary':primary,'paired':[r for r in paired if r['reference']=='expert1'],'decision':decision}),flush=True)

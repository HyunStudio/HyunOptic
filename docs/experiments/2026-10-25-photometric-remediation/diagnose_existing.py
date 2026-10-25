import collections,json,pathlib,numpy as np
out=pathlib.Path('reports/remediation_20261025')
summary=[]
for seed,folder in ((42,'papila_real_v1_20261025'),(43,'papila_real_seed43_20261025'),(44,'papila_real_seed44_20261025')):
    for path in (pathlib.Path('models')/folder/'evaluation').glob('*/model_eval_private_cases.json'):
        rows=json.loads(path.read_text(encoding='utf-8'))['cases']
        groups=collections.defaultdict(list)
        for row in rows: groups[row.get('camera','internal')].append(row)
        for camera,cases in groups.items():
            errors=collections.Counter()
            for row in cases:
                if row.get('failure_category')=='invalid_geometry': errors.update(row.get('errors',[]))
            valid=[r for r in cases if r.get('expert1') and 'abs_vcdr_error' in r['expert1']]
            summary.append({'seed':seed,'camera':camera,'n':len(cases),'model_failures':sum(errors.values()),'model_error_messages':dict(errors),'vcdr_n':len(valid),'vcdr_mae':float(np.mean([r['expert1']['abs_vcdr_error'] for r in valid])) if valid else None,'reference_vcdr_mean':float(np.mean([r['expert1']['reference_vcdr'] for r in valid])) if valid else None,'disc_dice_mean_among_vcdr_measurable':float(np.mean([r['expert1']['disc_dice'] for r in valid])) if valid else None,'cup_dice_mean_among_vcdr_measurable':float(np.mean([r['expert1']['cup_dice'] for r in valid])) if valid else None})
(out/'existing_failure_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)

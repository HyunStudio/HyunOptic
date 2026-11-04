"""Exploratory image-only photometric stress pilot; outputs contain private artifacts.

Run from repository root. Do not publish output directory; publish only reviewed aggregates.
No model training, calibration, independent clinical evaluation or paper reproduction.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--papila-root', type=Path, default=Path('data/PAPILA'))
    parser.add_argument('--baseline', type=Path, default=Path('models/papila_real_seed43_20261025'))
    parser.add_argument('--comparison', type=Path, default=Path('models/papila_camera_robust_seed43_20261025'))
    parser.add_argument('--output', type=Path, required=True, help='NEW private report directory')
    args = parser.parse_args()
    from hyunoptic.papila import discover_cases, load_image, load_contours
    from hyunoptic.measure import dice, measure_masks, polygon_mask
    from hyunoptic.review.store import ReviewStore
    from hyunoptic.review.runner import run_next
    from hyunoptic.review.export import export_session, verify_export
    from hyunoptic.seg.bundle import verify_bundle

    args.output.mkdir(parents=True, exist_ok=False)
    bundles = [verify_bundle(p) for p in (args.baseline, args.comparison)]
    models = [dict(folder=str(b.folder.resolve()), identity=b.identity, run_id=b.run_id,
                   weights_sha256=b.weights_sha256,
                   data_status={'synthetic': b.synthetic, 'partial': b.partial}) for b in bundles]
    split = json.loads((args.baseline / 'split_manifest.json').read_text())['manifest']
    comparison_split = json.loads((args.comparison / 'split_manifest.json').read_text())['manifest']
    assert split == comparison_split, 'Pilot requires identical development/validation/holdout splits'
    selected, patients = [], set()
    for case in sorted(discover_cases(args.papila_root), key=lambda c: c.image_id):
        if case.image_id in split['splits']['holdout'] and case.patient_id not in patients:
            selected.append(case)
            patients.add(case.patient_id)
        if len(selected) == 4:
            break
    assert len(selected) == 4, 'Need four distinct patients in the frozen holdout'
    protocol = dict(schema='hyunoptic-stress-pilot-v1', selection='first lexicographic holdout image per patient; first four patients',
        n_original_images=4, n_patients=4, independent_test=False, no_training=True,
        conditions={'original': {}, 'brightness_0.6': {'brightness': .6},
                    'contrast_0.6': {'contrast': .6}, 'blur_radius_2': {'gaussian_blur_radius_px': 2}},
        reference='expert1 original-resolution masks, read only after predictions',
        reference_geometry='unchanged by photometric transforms',
        models=[{k: v for k, v in m.items() if k != 'folder'} for m in models],
        metrics=['disc Dice all returned masks', 'cup Dice all returned masks', 'vCDR MAE on measurable pairs',
                 'geometry failures', 'execution failures', 'model disagreement descriptive only'])
    encoded = json.dumps(protocol, sort_keys=True, indent=2).encode()
    (args.output / 'protocol.json').write_bytes(encoded)
    # Freeze protocol before running or inspecting predictions; private selection stays local.
    (args.output / 'private_selection.json').write_text(json.dumps([c.image_id for c in selected]))
    inputs, aliases = [], []
    for index, case in enumerate(selected):
        image = load_image(case).convert('RGB')
        versions = [image, ImageEnhance.Brightness(image).enhance(.6),
                    ImageEnhance.Contrast(image).enhance(.6), image.filter(ImageFilter.GaussianBlur(2))]
        for condition, version in zip(protocol['conditions'], versions):
            data = io.BytesIO()
            version.save(data, format='PNG')
            inputs.append((f'case-{index}-{condition}.png', data.getvalue()))
            aliases.append((case, condition))
    store = ReviewStore(args.output / 'private_review')
    sid = store.create_session(inputs, models)
    start = time.perf_counter()
    while run_next(store, sid):
        pass
    elapsed = time.perf_counter() - start
    accum = {c: [dict(disc=[], cup=[], vcdr=[], geometry_failures=0, execution_failures=0) for _ in models]
             for c in protocol['conditions']}
    agreement_wrong = 0
    measured_errors = {}
    for row, (case, condition) in zip(store.cases(sid), aliases):
        image = load_image(case)
        d, c = load_contours(case, 'exp1')
        disc_ref, cup_ref = polygon_mask(d, image.size), polygon_mask(c, image.size)
        reference = measure_masks(disc_ref, cup_ref).to_dict()
        primary_scores = None
        predictions = {p['model_identity']: p for p in row['predictions']}
        for index, model in enumerate(models):
            item = accum[condition][index]
            pred = predictions.get(model['identity'])
            if pred is None:
                item['execution_failures'] += 1
                continue
            if pred['status'] == 'error' or not pred.get('labels_path'):
                item['execution_failures'] += 1
                continue
            labels = np.asarray(Image.open(pred['labels_path']))
            disc, cup = dice(labels >= 1, disc_ref), dice(labels == 2, cup_ref)
            item['disc'].append(disc)
            item['cup'].append(cup)
            if index == 0:
                primary_scores = (disc, cup)
            if pred['status'] == 'ok':
                error = abs(pred['measurement']['vertical_cdr'] - reference['vertical_cdr'])
                item['vcdr'].append(error)
                measured_errors[(case.image_id, condition, index)] = error
            else:
                item['geometry_failures'] += 1
        if primary_scores and row['priority']['group'] == 'disagreement' and row['priority']['score'] <= .1:
            agreement_wrong += int(primary_scores[0] < .5 or primary_scores[1] < .5)
    result = dict(protocol_sha256=hashlib.sha256(encoded).hexdigest(), n_original_images=4, n_patients=4,
                  n_transformed_cases=len(inputs), n_model_predictions=sum(len(r['predictions']) for r in store.cases(sid)),
                  cpu_seconds=round(elapsed, 2), low_disagreement_large_primary_error_cases=agreement_wrong,
                  conditions={}, limitation='Tiny exploratory reuse of previously evaluated holdout; no efficacy or independent validation claim')
    for condition, values in accum.items():
        result['conditions'][condition] = [dict(model_index=i, n_cases=4,
            n_dice=len(v['disc']), mean_disc_dice=float(np.mean(v['disc'])) if v['disc'] else None,
            mean_cup_dice=float(np.mean(v['cup'])) if v['cup'] else None,
            n_vcdr=len(v['vcdr']), vcdr_mae=float(np.mean(v['vcdr'])) if v['vcdr'] else None,
            geometry_failures=v['geometry_failures'], execution_failures=v['execution_failures']) for i, v in enumerate(values)]
    # Post-hoc denominator diagnostic added after the first pilot; never use the
    # unequal-denominator MAE decrease alone as evidence of robustness improvement.
    paired = {}
    for condition in list(protocol['conditions'])[1:]:
        paired[condition] = []
        for index in range(2):
            values = [(measured_errors[(c.image_id, 'original', index)], measured_errors[(c.image_id, condition, index)])
                      for c in selected if (c.image_id, 'original', index) in measured_errors
                      and (c.image_id, condition, index) in measured_errors]
            paired[condition].append(dict(model_index=index, n_common=len(values),
                original_vcdr_mae=float(np.mean([v[0] for v in values])) if values else None,
                condition_vcdr_mae=float(np.mean([v[1] for v in values])) if values else None))
    result['posthoc_paired_vcdr'] = paired
    result['export_verified'] = verify_export(export_session(store, sid, args.output / 'private-evidence.zip'))['valid']
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

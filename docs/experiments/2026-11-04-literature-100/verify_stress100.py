"""Independently verify frozen real100 masks and metrics; no model execution.

Only PAPILA loading and polygon rasterization are reused. Dice, spans, ratios,
per-condition summaries and all comparisons are calculated here independently.
Public output contains counts and numeric differences, never case identifiers.
"""
import argparse
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from hyunoptic.papila import discover_cases, load_contours, load_image
from hyunoptic.measure import polygon_mask

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--papila-root', type=Path, default=Path('data/PAPILA'))
args = parser.parse_args()
REPO = Path.cwd()
FOLDER = args.report.resolve()
OUTPUT = args.output.resolve()
if OUTPUT.exists():
    raise FileExistsError('Refusing to overwrite verification evidence')
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
TOLERANCE = 1e-12
failures = Counter()
comparisons = Counter()
maximum_differences = Counter()


def check(condition, category):
    comparisons[category] += 1
    if not condition:
        failures[category] += 1


def compare(actual, expected, category):
    comparisons[category] += 1
    if actual is None or expected is None:
        if actual is not None or expected is not None:
            failures[category] += 1
        return
    if isinstance(actual, (bool, str)) or isinstance(expected, (bool, str)):
        if actual != expected:
            failures[category] += 1
        return
    if not math.isfinite(float(actual)) or not math.isfinite(float(expected)):
        failures[category] += 1
        return
    difference = abs(float(actual) - float(expected))
    maximum_differences[category] = max(maximum_differences[category], difference)
    if difference > TOLERANCE:
        failures[category] += 1


def overlap(a, b):
    denominator = np.count_nonzero(a) + np.count_nonzero(b)
    return 2.0 * np.count_nonzero(np.logical_and(a, b)) / denominator if denominator else 1.0


def geometry(mask):
    rows = np.flatnonzero(np.any(mask, axis=1))
    columns = np.flatnonzero(np.any(mask, axis=0))
    if not len(rows):
        return None
    return int(rows[-1] - rows[0] + 1), int(columns[-1] - columns[0] + 1), int(np.count_nonzero(mask))


def mean(values):
    return math.fsum(values) / len(values) if values else None


def main():
    if not (FOLDER / 'summary.json').is_file():
        raise SystemExit('Scoring summary is not ready')
    protocol_bytes = (FOLDER / 'protocol.json').read_bytes()
    protocol = json.loads(protocol_bytes)
    summary = json.loads((FOLDER / 'summary.json').read_text(encoding='utf-8'))
    frozen = json.loads((FOLDER / 'private_predictions.json').read_text(encoding='utf-8'))
    scored = json.loads((FOLDER / 'private_scored_rows.json').read_text(encoding='utf-8'))
    selection = json.loads((FOLDER / 'private_selection.json').read_text(encoding='utf-8'))
    check(hashlib.sha256(protocol_bytes).hexdigest() == summary['protocol_sha256'], 'protocol_sha256')
    check(len(frozen) == len(scored) == 800, 'prediction_count')
    check(len(selection) == len(set(selection)) == 4, 'selection_count')
    cases = {case.image_id: case for case in discover_cases(args.papila_root)}
    check(len({cases[key].patient_id for key in selection}) == 4, 'independent_patient_count')
    references = []
    for key in selection:
        case = cases[key]
        image = load_image(case)
        d, c = load_contours(case, 'exp1')
        disc, cup = polygon_mask(d, image.size), polygon_mask(c, image.size)
        dg, cg = geometry(disc), geometry(cup)
        references.append((disc, cup, cg[0] / dg[0]))
    identity = lambda row: (row['case_index'], row['condition'], row['model_index'])
    frozen_map = {identity(row): row for row in frozen}
    scored_map = {identity(row): row for row in scored}
    expected_keys = {(case, cond['name'], model) for case in range(4)
                     for cond in protocol['conditions'] for model in range(2)}
    check(set(frozen_map) == set(scored_map) == expected_keys, 'cartesian_case_condition_model')
    check(len(frozen_map) == len(frozen) and len(scored_map) == len(scored), 'row_unique_identity')
    recomputed = {}
    mask_files = set()
    statuses = Counter()
    for index, (key, row) in enumerate(frozen_map.items(), 1):
        result = dict(row)
        scored_row = scored_map[key]
        check(all(scored_row.get(field) == value for field, value in row.items()), 'frozen_row_preserved')
        statuses[row['status']] += 1
        if row['labels_file'] is not None:
            name = row['labels_file']
            check(Path(name).name == name, 'mask_filename_local')
            mask_files.add(name)
            payload = (FOLDER / 'private_predictions' / name).read_bytes()
            check(hashlib.sha256(payload).hexdigest() == row['labels_sha256'], 'mask_sha256')
            with Image.open(io.BytesIO(payload)) as image:
                labels = np.array(image)
            disc_ref, cup_ref, reference_vcdr = references[row['case_index']]
            check(labels.dtype == np.uint8 and labels.ndim == 2, 'mask_dtype_rank')
            check(labels.shape == disc_ref.shape, 'original_resolution_geometry')
            check(set(np.unique(labels)).issubset({0, 1, 2}), 'mask_classes')
            disc, cup = labels != 0, labels == 2
            dg, cg = geometry(disc), geometry(cup)
            valid = dg is not None and cg is not None
            check((row['status'] == 'ok') == valid, 'status_geometry_consistency')
            measurement = row['measurement']
            check((measurement is not None) == valid, 'measurement_availability')
            vcdr = cg[0] / dg[0] if valid else None
            if valid:
                values = dict(vertical_cdr=vcdr, horizontal_cdr=cg[1] / dg[1], area_cdr=cg[2] / dg[2],
                              disc_vertical_px=dg[0], disc_horizontal_px=dg[1], disc_area_px=dg[2],
                              cup_vertical_px=cg[0], cup_horizontal_px=cg[1], cup_area_px=cg[2])
                for field, value in values.items():
                    compare(measurement.get(field), value, 'predicted_measurement_fields')
                check(measurement.get('warnings') == [], 'predicted_measurement_warnings')
            result['disc_dice'] = overlap(disc, disc_ref)
            result['cup_dice'] = overlap(cup, cup_ref)
            result['abs_vcdr_error'] = abs(vcdr - reference_vcdr) if valid else None
            for field in ('disc_dice', 'cup_dice', 'abs_vcdr_error'):
                compare(scored_row.get(field), result[field], 'per_prediction_' + field)
        recomputed[key] = result
        if index % 100 == 0:
            print(json.dumps({'verified_predictions': index}), flush=True)
    check(len(mask_files) == 800, 'mask_unique_filename_count')
    check(len(list((FOLDER / 'private_predictions').glob('*.png'))) == len(mask_files), 'mask_directory_count')
    aggregate_map = {(row['condition'], row['model_index']): row for row in summary['conditions']}
    check(len(aggregate_map) == len(summary['conditions']) == 200, 'aggregate_count')
    for cond in protocol['conditions']:
        for model in range(2):
            target = aggregate_map[(cond['name'], model)]
            group = [recomputed[(case, cond['name'], model)] for case in range(4)]
            available = [row for row in group if 'disc_dice' in row]
            errors = [row['abs_vcdr_error'] for row in available if row['abs_vcdr_error'] is not None]
            pairs = [(recomputed[(row['case_index'], 'original', model)].get('abs_vcdr_error'), row['abs_vcdr_error'])
                     for row in available]
            pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
            expected = dict(n_cases=4, n_dice=len(available),
                disc_dice=mean([row['disc_dice'] for row in available]),
                cup_dice=mean([row['cup_dice'] for row in available]),
                geometry_failures=sum(row['status'] == 'invalid_geometry' for row in group),
                execution_failures=sum(row['status'] == 'error' for row in group),
                n_vcdr=len(errors), vcdr_mae=mean(errors), n_common_original_vcdr=len(pairs),
                paired_original_vcdr_mae=mean([a for a, b in pairs]),
                paired_condition_vcdr_mae=mean([b for a, b in pairs]))
            for field, value in expected.items():
                compare(target.get(field), value, 'aggregate_' + field)
            check(target['family'] == cond['family'] and target['value'] == cond['value'], 'condition_metadata')
    for field, expected in dict(n_patients=4, n_original_images=4, n_conditions=100,
                                n_transformed_image_cases=400, n_model_predictions=800,
                                n_masks=len(mask_files), total_geometry_failures=statuses['invalid_geometry'],
                                total_execution_failures=statuses['error']).items():
        compare(summary.get(field), expected, 'summary_counts')
    result = dict(schema='hyunoptic-independent-real100-numeric-verification/v1',
                  verified=not bool(failures), n_predictions=len(frozen), n_masks=len(mask_files),
                  n_selected_patients=4, n_condition_model_aggregates=len(aggregate_map),
                  tolerance=TOLERANCE, comparison_counts=dict(comparisons),
                  maximum_absolute_differences=dict(maximum_differences), failures=dict(failures),
                  reference='PAPILA expert 1; existing contour loading and polygon rasterization reused',
                  independent_calculations='Dice from boolean intersections; inclusive row/column spans; ratios; math.fsum means',
                  no_new_inference_or_training=True,
                  limitation='Independent arithmetic and frozen-artifact integrity check on four reused patients; not clinical validation or paper reproduction.')
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'verified': result['verified'], 'predictions': len(frozen), 'masks': len(mask_files),
                      'aggregate_rows': len(aggregate_map), 'failure_count': sum(failures.values())}), flush=True)
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Independent Chaksu queue-budget arithmetic; no inference or product imports.

Run from repository root. Original saved private Chaksu layout is required.
Use --output to choose an aggregate-only output path.
"""
import argparse
import collections
import json
import math
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('reports/full_validation_20261104/chaksu'))
    parser.add_argument('--output', type=Path, default=Path('reports/full_validation_20261104/final_review/chaksu_queue_arithmetic.json'))
    args = parser.parse_args()
    read = lambda name: json.loads((args.input / name).read_text())
    rows = [json.loads(line) for line in (args.input / 'private_reference_rows.jsonl').read_text().splitlines()]
    byid = {r['case_id']: r for r in rows}
    queue = read('private_queue_frozen_before_references.json')['rows']
    ordered = [byid[q['case_id']] for q in queue]
    assert len(byid) == len(ordered) == 336
    assert len({r['case_id'] for r in ordered}) == 336
    dices = {(r['case_id'], r['model'], r['expert']): r for r in read('private_all_returned_mask_dice.json')}
    metrics = {(r['case_id'], r['model'], r['expert']): r for r in read('private_metrics.json')}
    aggregate = read('aggregate_public_safe.json')
    technical = read('technical_event_posthoc_public_safe.json')
    models = list(aggregate['models'])
    checks = collections.Counter()

    def compare(outcomes, saved):
        n = len(outcomes)
        k = math.ceil(n * saved['review_fraction'])
        positives = sum(v is True for v in outcomes)
        hit = sum(v is True for v in outcomes[:k])
        reviewed_available = sum(v is not None for v in outcomes[:k])
        remaining_available = sum(v is not None for v in outcomes[k:])
        expected = dict(n_cases=n, n_outcome_available=reviewed_available + remaining_available,
                        n_outcome_missing=n - reviewed_available - remaining_available,
                        cases_reviewed=k, reviewed_outcome_available=reviewed_available,
                        remaining_outcome_available=remaining_available,
                        n_positive=positives, detected=hit, missed=positives-hit,
                        reviewed_unknown=k-reviewed_available,
                        remaining_unknown=n-k-remaining_available,
                        precision=hit/reviewed_available if reviewed_available else None,
                        recall=hit/positives if positives else None,
                        remaining_error_fraction=(positives-hit)/remaining_available if remaining_available else None,
                        random_expected_detected=k*positives/n if n else None,
                        random_expected_recall=k/n if n and positives else None)
        for key, value in expected.items():
            actual = saved[key]
            assert actual == value or (isinstance(value, (float, int)) and actual is not None and abs(actual-value) < 1e-12), (key, value, actual)
            checks['budget_fields'] += 1

    def combine(flags):
        return True if any(v is True for v in flags) else None if None in flags else False

    for expert, scopes in aggregate['queue_evaluation'].items():
        for scope, budgets in scopes.items():
            outcomes = []
            for row in ordered:
                flags = []
                for model in models if scope == 'either_model' else [scope]:
                    metric = metrics.get((row['case_id'], model, expert))
                    flags.append(metric['abs_vcdr_error'] > .1 if metric else None)
                outcomes.append(combine(flags))
            for budget in budgets:
                compare(outcomes, budget)
                checks['primary_budget_cells'] += 1

    for subgroup, group in technical['results'].items():
        selected = [r for r in ordered if subgroup == 'all_336' or all(pr['status'] == 'ok' for pr in r['predictions'])]
        assert len(selected) == group['n_images']
        for threshold, experts in group['thresholds'].items():
            for expert, scopes in experts.items():
                for scope, budgets in scopes.items():
                    outcomes = []
                    for row in selected:
                        flags = []
                        for prediction in row['predictions']:
                            if scope != 'either_model' and prediction['model'] != scope:
                                continue
                            metric = dices.get((row['case_id'], prediction['model'], expert))
                            flags.append(True if prediction['status'] in ['error', 'invalid_geometry'] else
                                         min(metric['disc_dice'], metric['cup_dice']) < float(threshold) if metric else None)
                        outcomes.append(combine(flags))
                    for budget in budgets:
                        compare(outcomes, budget)
                        checks['technical_budget_cells'] += 1

    report = dict(passed=True,
                  scope='Independent full Chaksu original-vCDR and posthoc technical queue budget arithmetic from stored private rows; existing frozen order used without new inference.',
                  checks=dict(checks), unknowns_preserved=True,
                  limitations=['Does not independently recompute priority function or Wilson intervals.'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

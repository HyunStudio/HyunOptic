"""Review budgets must keep failures, ties and missing references explicit."""
import pytest

from hyunoptic.review.validation import order_cases, evaluate_budget


def case(ordinal, group, score=None):
    return {'ordinal': ordinal, 'priority': {'group': group, 'score': score}}


def test_queue_order_is_failure_first_descending_and_ordinal_ties():
    rows = [case(5,'disagreement',.2), case(3,'invalid_geometry'), case(9,'error'),
            case(1,'disagreement',.8), case(2,'disagreement',.8), case(0,'pending')]
    assert [r['ordinal'] for r in order_cases(rows)] == [9,3,1,2,5,0]


def test_budget_keeps_failure_events_and_exact_random_expectation():
    result = evaluate_budget([True,False,True,False], review_fraction=.5)
    assert result['n_cases'] == 4 and result['cases_reviewed'] == 2
    assert result['detected'] == 1 and result['missed'] == 1
    assert result['precision'] == .5 and result['recall'] == .5
    assert result['remaining_error_fraction'] == .5
    assert result['random_expected_detected'] == 1


def test_missing_reference_does_not_become_correct_or_change_budget_denominator():
    result = evaluate_budget([None,True,False,True], review_fraction=.5)
    assert result['n_cases'] == 4 and result['n_outcome_available'] == 3
    assert result['n_outcome_missing'] == 1 and result['cases_reviewed'] == 2
    assert result['reviewed_outcome_available'] == 1
    assert result['detected'] == 1 and result['missed'] == 1
    assert result['precision'] == 1 and result['recall'] == .5
    assert result['random_expected_detected'] == 1


def test_zero_and_full_budget_and_zero_events_have_defined_denominators():
    zero = evaluate_budget([True,False], review_fraction=0)
    assert zero['cases_reviewed'] == 0 and zero['precision'] is None
    assert zero['recall'] == 0 and zero['remaining_error_fraction'] == .5
    full = evaluate_budget([True,False], review_fraction=1)
    assert full['remaining_error_fraction'] is None and full['recall'] == 1
    clean = evaluate_budget([False,False], review_fraction=.1)
    assert clean['recall'] is None and clean['random_expected_detected'] == 0


@pytest.mark.parametrize('fraction', [-.1,1.1,float('nan'),float('inf'),True])
def test_reject_invalid_budget(fraction):
    with pytest.raises(ValueError): evaluate_budget([True],review_fraction=fraction)


@pytest.mark.parametrize('events', [[],[1],[float('nan')],['false']])
def test_reject_invalid_outcomes(events):
    with pytest.raises(ValueError): evaluate_budget(events,review_fraction=.1)


@pytest.mark.parametrize('score', [None,float('nan'),float('inf'),-.1,1.1,True])
def test_reject_invalid_completed_disagreement_score(score):
    with pytest.raises(ValueError): order_cases([case(0,'disagreement',score)])

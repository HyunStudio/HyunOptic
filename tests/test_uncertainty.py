import numpy as np
import pytest
from hyunoptic.uncertainty import PerturbationConfig, analyze_vertical_sensitivity
from hyunoptic.evaluation import evaluate_at_budget, patient_cluster_bootstrap_mean

def rect(x1,y1,x2,y2):
    return np.array([[x1,y1],[x2,y1],[x2,y2],[x1,y2]], dtype=float)

DISC=rect(10,10,70,110)
CUP=rect(20,30,60,80)

def test_deterministic_and_finite():
    cfg=PerturbationConfig(draws=800, seed=707)
    a=analyze_vertical_sensitivity(DISC,CUP,cfg)
    assert a.to_dict()==analyze_vertical_sensitivity(DISC,CUP,cfg).to_dict()
    assert a.nominal_continuous_vcdr==pytest.approx(0.5)
    assert a.simulated_percentile_2_5<a.simulated_percentile_97_5
    assert a.q95_absolute_vcdr_change>0
    assert a.delta_method_variance_vcdr>=0

def test_zero_jitter():
    cfg=PerturbationConfig(draws=100,shared_log_sd=0,cup_log_sd=0,disc_log_sd=0)
    a=analyze_vertical_sensitivity(DISC,CUP,cfg)
    assert a.simulated_sd_vcdr==0
    assert a.q95_absolute_vcdr_change==0
    assert a.implied_cup_disc_correlation is None

def test_covariance_common_scaling_cancels_ratio():
    cfg=PerturbationConfig(draws=2000,seed=3,shared_log_sd=.15,cup_log_sd=0,disc_log_sd=0)
    a=analyze_vertical_sensitivity(DISC,CUP,cfg)
    assert a.covariance_cup_disc_vertical>0
    assert a.delta_method_variance_without_covariance>.00001
    assert a.empirical_variance_vcdr<1e-25
    assert a.delta_method_variance_vcdr<1e-12

def test_independent_noise_increases_sensitivity():
    low=analyze_vertical_sensitivity(DISC,CUP,PerturbationConfig(draws=3000,seed=1,shared_log_sd=0,cup_log_sd=.01,disc_log_sd=.01))
    high=analyze_vertical_sensitivity(DISC,CUP,PerturbationConfig(draws=3000,seed=1,shared_log_sd=0,cup_log_sd=.08,disc_log_sd=.08))
    assert high.simulated_sd_vcdr>low.simulated_sd_vcdr
    assert high.q95_absolute_vcdr_change>low.q95_absolute_vcdr_change

def test_candidate_only_public_signature():
    a=analyze_vertical_sensitivity(DISC,CUP)
    assert "heldout" not in str(a.settings)
    assert a.method.startswith("paired_")

@pytest.mark.parametrize("cfg",[
    PerturbationConfig(draws=5),PerturbationConfig(seed=-1),
    PerturbationConfig(cup_log_sd=-.1),PerturbationConfig(shared_log_sd=float("nan"))])
def test_invalid_params(cfg):
    with pytest.raises(ValueError):
        analyze_vertical_sensitivity(DISC,CUP,cfg)

def test_invalid_polygon():
    with pytest.raises(ValueError):
        analyze_vertical_sensitivity(DISC,rect(0,0,10,0))

def test_review_budget_ranking():
    r=evaluate_at_budget([.4,.9,.3,.2,.1],[.01,.20,.10,.12,.03],
                         discrepancy_threshold=.10,review_fraction=.4)
    assert (r.cases_reviewed,r.n_discrepant,r.detected_discrepant)==(2,2,1)
    assert r.precision_at_budget==r.recall_at_budget==.5

def test_review_budget_no_positives():
    r=evaluate_at_budget([1.,0.],[.01,.02],discrepancy_threshold=.2)
    assert r.recall_at_budget is None and r.precision_at_budget==0

def test_review_budget_stable_ties():
    r=evaluate_at_budget([1.,1.,1.],[.2,0,.2],discrepancy_threshold=.1,review_fraction=1/3)
    assert r.cases_reviewed==r.detected_discrepant==1

@pytest.mark.parametrize("scores,differences", [
    ([.2], []), ([float("nan")],[0.]), ([-1.],[0.]), ([],[])])
def test_invalid_budget_inputs(scores,differences):
    with pytest.raises(ValueError):
        evaluate_at_budget(scores,differences)

def test_patient_cluster_bootstrap_bilateral_grouping():
    a=patient_cluster_bootstrap_mean([1,1,3],["P1","P1","P2"],draws=500,seed=4)
    b=patient_cluster_bootstrap_mean([1,3],["P1","P2"],draws=500,seed=4)
    assert a["n_patients"]==2
    assert a["patient_weighted_mean"]==b["patient_weighted_mean"]==2
    assert a==patient_cluster_bootstrap_mean([1,1,3],["P1","P1","P2"],draws=500,seed=4)

def test_patient_bootstrap_requires_two_people():
    with pytest.raises(ValueError, match="two distinct"):
        patient_cluster_bootstrap_mean([1,2],["P1","P1"])

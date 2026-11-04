"""Independent formula tests for Hoebel et al. arXiv:1911.06357, p2.

Related 2019 paper, NOT substitution for a reproduction of SPIE 2020.
Controlled masks/random weights; no medical-data performance claim.
"""
from itertools import combinations
import json,sys,time
from pathlib import Path
import numpy as np
import torch

torch.set_num_threads(2)
torch.manual_seed(20261103)

def metrics(probabilities):
    probabilities=np.asarray(probabilities,dtype=float)
    assert probabilities.shape[0]==10 and np.isfinite(probabilities).all()
    masks=probabilities>=.5
    volumes=masks.reshape(10,-1).sum(1)
    # Literal printed Var(volume)/(E(volume)+1), not the conventional std/mean.
    cv=float(np.var(volumes,ddof=0)/(np.mean(volumes)+1))
    pairs=[]
    for i,j in combinations(range(10),2):
        denominator=int(masks[i].sum()+masks[j].sum())
        if denominator:
            pairs.append(float(2*np.count_nonzero(masks[i]&masks[j])/denominator))
    labelled=probabilities.mean(0)>=.5
    entropy=-np.mean(probabilities*np.log(np.clip(probabilities,1e-12,1)),axis=0)
    return dict(printed_cv=cv,mean_pairwise_dice=float(np.mean(pairs)) if pairs else None,
                pair_count=len(pairs),mean_labelled_entropy=float(entropy[labelled].mean()) if labelled.any() else None)

checks=[]
def run(name,fn):
    try: checks.append(dict(name=name,status='PASS',detail=fn()))
    except Exception as exc: checks.append(dict(name=name,status='FAIL',error=repr(exc)))

reference=np.zeros((8,16,16),bool);reference[1:5,2:6,2:6]=True
wrong=np.zeros_like(reference);wrong[1:5,10:14,10:14]=True
def same():
    a=metrics(np.where(np.repeat(reference[None],10,axis=0),.95,.05))
    b=metrics(np.where(np.repeat(wrong[None],10,axis=0),.95,.05))
    assert a==b and a['printed_cv']==0 and a['mean_pairwise_dice']==1 and a['pair_count']==45
    assert not np.any(reference&wrong)
    return dict(same_uncertainty_for_correct_and_systematically_wrong=True,
                correct_reference_dice=1.,wrong_reference_dice=0.,metrics=a)
def variable():
    values=[]
    for i in range(10):
        mask=np.zeros_like(reference);mask[1:5,2:6,2:6+(i%3)]=True
        values.append(np.where(mask,.95,.05))
    result=metrics(values)
    assert result['printed_cv']>0 and 0<result['mean_pairwise_dice']<1
    return result
def empty():
    result=metrics(np.full((10,8,16,16),.05))
    assert result['mean_pairwise_dice'] is None and result['mean_labelled_entropy'] is None
    return dict(result=result,undefined_empty_aggregates_reported_not_filled_with_success=True)
def dropout():
    net=torch.nn.Sequential(torch.nn.Conv3d(1,4,3,padding=1),torch.nn.ReLU(),torch.nn.Dropout3d(.5),
                            torch.nn.Conv3d(4,1,1),torch.nn.Sigmoid()).train()
    x=torch.randn(1,1,8,16,16)
    with torch.no_grad(): outputs=torch.stack([net(x) for _ in range(10)])
    assert torch.isfinite(outputs).all() and outputs.var(0).sum()>0
    result=metrics(outputs[:,0,0].numpy())
    return dict(random_untrained_model=True,output_shape=list(outputs.shape),metrics=result)

run('identical_correct_vs_identical_wrong_blindspot',same)
run('varying_boundary_variance_and_pairwise_dice',variable)
run('empty_labelled_volume_explicit_undefined',empty)
run('toy_3d_mc_dropout_N10_actual_execution',dropout)
summary=dict(paper='Give me (un)certainty (Hoebel et al. ML4H2019)',source='https://arxiv.org/pdf/1911.06357',
    classification='independent_formula_unit_tests_and_random_weight_dropout_only',
    original_SPIE2020_status='Full text download redirect loop; author checkpoints and code not verified; not reproduced',
    python=sys.version.split()[0],torch=torch.__version__,seed=20261103,checks=checks,
    implementation_choices='population variance as printed in paper; binary threshold >=0.5; empty Dice/labelled aggregate -> null')
(Path(__file__).parent/'hoebel_results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))

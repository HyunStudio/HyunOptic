"""Synthetic-only tests. Does not assert actual patient performance."""
from __future__ import annotations
import numpy as np
import pytest
from PIL import Image
from hyunoptic.features import candidate_features, contour_roughness, boundary_gradient_strength
from hyunoptic.study import patient_splits, run_study, save_study
from hyunoptic.uncertainty import PerturbationConfig

def polygon(x1, y1, x2, y2):
    return np.asarray([[x1,y1],[x2,y1],[x2,y2],[x1,y2]], dtype=float)

def test_roughness_consistent_with_analytic_square():
    r=contour_roughness(polygon(1,1,9,9))
    assert r==pytest.approx(4/np.pi-1)

def test_boundary_gradient_synthetic():
    pixels=np.zeros((64,64), dtype=np.uint8)
    pixels[:,32:]=255
    img=Image.fromarray(pixels)
    crossing=np.asarray([[31,10],[32,10],[31,20],[32,20]],dtype=float)
    flat=np.asarray([[10,10],[11,10],[11,20],[10,20]],dtype=float)
    assert boundary_gradient_strength(img,crossing)>boundary_gradient_strength(img,flat)

def test_candidate_only_features():
    img=Image.new("RGB",(64,64),"gray")
    disc=polygon(5,5,50,50)
    cup=polygon(15,15,35,35)
    values=candidate_features(img,disc,cup,PerturbationConfig(draws=100))
    assert set(values)=={"v02_q95","cup_roughness","cup_boundary_weakness","candidate_vcdr","cup_outside_fraction"}
    assert all(np.isfinite(list(values.values())))
    assert values["cup_boundary_weakness"]==pytest.approx(1.0)

def test_patient_splits_stable_and_disjoint():
    ids=[f"RET{i:03}" for i in range(25)]
    a=patient_splits(ids,seed=9)
    b=patient_splits(ids[::-1],seed=9)
    assert a==b
    assert set(a.values())=={"development","validation","holdout"}
    assert len(a)==25
    assert patient_splits(ids,seed=10)!=a

def test_small_patient_split_rejected():
    with pytest.raises(ValueError):
        patient_splits(["a","b"])

def fake_data(tmp_path, n=15):
    directory=tmp_path/"PAPILA_DBv1"
    images=directory/"FundusImages"
    contours=directory/"ExpertsSegmentations"/"Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    for p in range(n):
        for eye in ("OD","OS"):
            name=f"RET{p:03}{eye}"
            im=Image.new("RGB",(80,80),(80+p*3,80,80))
            im.save(images/f"{name}.jpg")
            def put(exp,struct,pts):
                np.savetxt(contours/f"{name}_{struct}_{exp}.txt",pts)
            disc=polygon(10,10,65,65)
            cup=polygon(25,25,46,46)
            cup_alt=polygon(24,24,46+(p%5)*2,47+(p%4)*2)
            put("exp1","disc",disc)
            put("exp1","cup",cup)
            put("exp2","disc",disc)
            put("exp2","cup",cup_alt)
    return directory

def test_study_is_patient_disjoint_and_deterministic(tmp_path):
    root=fake_data(tmp_path)
    params={"config":PerturbationConfig(draws=70, seed=19),
            "split_seed":13,"bootstrap_draws":100}
    a,rows=run_study(root,**params)
    b,rows_b=run_study(root,**params)
    assert a==b and rows==rows_b
    assert a["version"]=="0.4.0"
    splits={}
    for row in rows:
        splits.setdefault(row["patient_id"],set()).add(row["split"])
    assert all(len(v)==1 for v in splits.values())
    assert set(a["evaluation"])=={"validation","holdout"}
    assert set(a["evaluation"]["holdout"]["scores"])=={
        "v02_q95","cup_roughness","cup_boundary_weakness",
        "candidate_vcdr","combined_candidate_score",
    }
    out=tmp_path/"report.json"
    save_study(a,rows,out,tmp_path/"report.csv")
    assert out.exists() and (tmp_path/"report.csv").exists()

def test_changing_second_expert_does_not_affect_features_or_qc(tmp_path):
    root=fake_data(tmp_path,n=9)
    params={"config":PerturbationConfig(draws=70,seed=20),
            "split_seed":12,"bootstrap_draws":100}
    a, before=run_study(root,**params)
    path=root/"ExpertsSegmentations"/"Contours"/"RET000OD_cup_exp2.txt"
    np.savetxt(path,polygon(18,18,53,53))
    b, after=run_study(root,**params)
    for old,new in zip(before,after):
        for name in ("v02_q95","cup_roughness","cup_boundary_weakness",
                     "candidate_vcdr","cup_outside_fraction","combined_candidate_score"):
            assert old[name]==new[name]
        assert old["split"]==new["split"]
    assert before[0]["heldout_absolute_vcdr_difference"]!=after[0]["heldout_absolute_vcdr_difference"]

def test_train_scaling_unchanged_by_test_image_variation(tmp_path):
    root=fake_data(tmp_path,n=9)
    params={"config":PerturbationConfig(draws=50,seed=3),
            "split_seed":21,"bootstrap_draws":100}
    a,rows=run_study(root,**params)
    # In the artificial images, only holdout image pixel values are changed.
    target=next(r for r in rows if r["split"]=="holdout")
    pic=root/"FundusImages"/(target["image_id"]+".jpg")
    Image.new("RGB",(80,80),"black").save(pic)
    b,_=run_study(root,**params)
    assert a["development_only_unsupervised_scaling"]==b["development_only_unsupervised_scaling"]

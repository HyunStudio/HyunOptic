import json
import numpy as np
from PIL import Image
from hyunoptic.batch import audit_papila,write_audit
from hyunoptic.uncertainty import PerturbationConfig

def test_fake_papila_batch_keeps_candidate_score_independent_of_exp2(tmp_path):
    folder=tmp_path/"PAPILA_DBv1"
    images=folder/"FundusImages"
    contours=folder/"ExpertsSegmentations"/"Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    def poly(top,bottom):
        return np.array([[10,top],[20,top],[20,bottom],[10,bottom]])
    for patient in (1,2):
        for eye in ("OD","OS"):
            name=f"RET{patient:03}{eye}"
            Image.new("RGB",(35,35)).save(images/f"{name}.jpg")
            for expert in ("exp1","exp2"):
                np.savetxt(contours/f"{name}_disc_{expert}.txt",poly(2,22))
                np.savetxt(contours/f"{name}_cup_{expert}.txt",poly(7,11 if expert=="exp1" else 15))
    cfg=PerturbationConfig(draws=100,seed=12)
    summary,rows=audit_papila(tmp_path,config=cfg)
    assert summary["n_analyzed"]==4
    assert summary["patient_bootstrap_absolute_vcdr_difference"]["n_patients"]==2
    assert len({r["candidate_q95_absolute_vcdr_change"] for r in rows})==1
    np.savetxt(contours/"RET001OD_cup_exp2.txt",poly(7,19))
    _,changed=audit_papila(tmp_path,config=cfg)
    assert rows[0]["candidate_q95_absolute_vcdr_change"]==changed[0]["candidate_q95_absolute_vcdr_change"]
    assert rows[0]["heldout_absolute_vcdr_difference"]!=changed[0]["heldout_absolute_vcdr_difference"]
    out=tmp_path/"audit.json"
    csv=tmp_path/"audit.csv"
    write_audit(summary,rows,out,csv)
    assert json.loads(out.read_text())["summary"]["n_analyzed"]==4
    assert csv.exists()

"""Offline synthetic Chaksu ZIP metadata and all-reader audit regression tests."""
from __future__ import annotations
import io
import json
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image
from hyunoptic.chaksu import scan_test_archive
from hyunoptic.external_qc import check_chaksu_archive, save_chaksu_audit
from hyunoptic.external_qc_cli import main as cli

def png_bytes(image):
    b=io.BytesIO(); image.save(b,format="PNG"); return b.getvalue()

def synthetic_test_zip(path, *, root="Test set", camera="Remedio", missing=None):
    image=Image.new("RGB",(32,32),"gray")
    disc=np.zeros((32,32),dtype=np.uint8); disc[3:28,3:28]=255
    cup=np.zeros((32,32),dtype=np.uint8); cup[10:20,10:20]=255
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{root}/1.0_Original_Fundus_Images/{camera}/PAT_001.png",png_bytes(image))
        for i in range(1,6):
            for structure,mask in (("Disc",disc),("Cup",cup)):
                if (i,structure)==missing:
                    continue
                name=f"{root}/3.0_Doctors_Annotations_Binary_OD_OC/Expert {i}/{camera}/{structure}/PAT_001.png"
                z.writestr(name,png_bytes(Image.fromarray(mask)))
    return path

def test_test_set_alias_and_remedio_folder_recognized(tmp_path):
    archive=synthetic_test_zip(tmp_path/"Test.zip")
    cases,inventory=scan_test_archive(archive)
    assert len(cases)==1
    assert cases[0].camera=="remidio"
    assert inventory["image_entries"]==1
    assert inventory["complete_5_reader_cases"]==1
    assert inventory["fingerprint_uses_entry_names_and_uncompressed_sizes"] is True

def test_preflight_reads_all_five_annotators_and_checks_shape(tmp_path):
    archive=synthetic_test_zip(tmp_path/"Test.zip")
    result,private=check_chaksu_archive(archive)
    assert result["n_checked"]==1
    assert result["n_readable_with_all_five_experts"]==1
    assert result["resolution_flags_by_camera"]["remidio"]==1
    assert result["all_published_test_masks_structurally_verified"] is False
    output=tmp_path/"out"
    save_chaksu_audit(result,private,output)
    summary=(output/"audit_aggregate.json").read_text()
    assert "PAT_001" not in summary
    assert "pat_001" in (output/"audit_private_errors.json").read_text().lower()

def test_missing_expert_visible_as_missing_count(tmp_path):
    archive=synthetic_test_zip(tmp_path/"Test.zip",missing=(5,"Cup"))
    summary,_=check_chaksu_archive(archive)
    assert summary["n_cases_with_all_expert_mask_paths"]==0
    assert summary["number_of_missing_annotation_cases"]==1

def test_strict_cli_exit_code_partial(tmp_path):
    archive=synthetic_test_zip(tmp_path/"Test.zip")
    output=tmp_path/"report"
    code=cli(["--chaksu-test-zip",str(archive),"--output-dir",str(output),"--strict"])
    assert code==2
    assert json.loads((output/"audit_aggregate.json").read_text())["partial_audit_or_unverified"]

def test_sampled_audit_always_partial(tmp_path):
    archive=synthetic_test_zip(tmp_path/"Test.zip")
    result,_=check_chaksu_archive(archive,max_cases=1)
    assert result["partial_audit_or_unverified"]

"""Synthetic cross-dataset fixture: no patient files or Chaksu data in repository."""
import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image

from hyunoptic.chaksu import scan_test_archive, load_test_case
from hyunoptic.external import run_external_test, save_external
from hyunoptic.freeze import freeze_papila_model, save_lock, load_lock, validate_model_lock
from hyunoptic.external_cli import main as external_cli
from hyunoptic.mask_features import mask_features, fit_mask_scaler, apply_mask_score, MASK_FEATURES


def rectangle(x1,y1,x2,y2):
    return np.array([[x1,y1], [x2,y1], [x2,y2], [x1,y2]], dtype=float)


def source_fixture(root, count=10):
    images = root / "FundusImages"
    contours = root / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    for p in range(count):
        for eye in ("OD", "OS"):
            name = f"RET{p:03}{eye}"
            image = Image.new("RGB", (48,48), (80+p*2, 80, 80))
            image.save(images / f"{name}.jpg")
            for reader in ("exp1","exp2"):
                np.savetxt(contours / f"{name}_disc_{reader}.txt", rectangle(5,5,40,40))
                top = 13 if reader == "exp1" else 11
                np.savetxt(contours / f"{name}_cup_{reader}.txt", rectangle(14,top,31,32 + p%5))
    return root


def _bytes(img, fmt):
    output = io.BytesIO()
    img.save(output, format=fmt)
    return output.getvalue()


def mask_image(width, height, box):
    # Synthetic opaque zero-background binary TIFF.
    values = np.zeros((height,width), dtype=np.uint8)
    x1,y1,x2,y2 = box
    values[y1:y2+1,x1:x2+1] = 255
    return Image.fromarray(values)


def chaksu_fixture(path, *, cases=3, missing=None, corrupt=None, expert5_shift=0):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for n in range(cases):
            cam = ("Bosch","Forus","Remidio")[n % 3]
            stem = f"IMG_{n:03}"
            photo = Image.new("RGB", (44,48), (80+n*12,90,90))
            zf.writestr(f"Test/1.0_Original_Fundus_Images/{cam}/{stem}.png", _bytes(photo, "PNG"))
            for expert in range(1, 6):
                for structure in ("Disc", "Cup"):
                    identifier = (n, expert, structure)
                    if identifier == missing:
                        continue
                    # Cup for expert 2 sometimes has a distinct measured height.
                    box = (5,5,39,42) if structure == "Disc" else (13,14,28,31 + (expert==2)*4 + (expert==5)*expert5_shift + n%2)
                    sample = mask_image(44,48,box)
                    if identifier == corrupt:
                        sample = mask_image(30,48,box)
                    key = f"Test/3.0_Doctors_Annotations_Binary_OD_OC/Expert {expert}/{cam}/{structure}/{stem}.tif"
                    zf.writestr(key, _bytes(sample, "TIFF"))
    return path


def test_uniform_masks_no_reference_data():
    image = Image.new("RGB",(40,40),"gray")
    disc=np.zeros((40,40),bool)
    cup=np.zeros((40,40),bool)
    disc[5:35,5:35]=True
    cup[13:24,15:25]=True
    data=mask_features(image,disc,cup)
    assert set(MASK_FEATURES).issubset(data)
    assert all(np.isfinite(list(data.values())))
    scaler=fit_mask_scaler([data, data])
    assert apply_mask_score(data,scaler)==pytest.approx(3.0)
    with pytest.raises(ValueError):
        mask_features(image,cup,disc)


def test_freeze_has_no_second_reader_leakage(tmp_path):
    root=source_fixture(tmp_path/"PAPILA_DBv1")
    a=freeze_papila_model(root,draws=60,seed=8,allow_partial=True)
    assert a["model"]["source_is_partial"]
    assert a["model"]["candidate_reader"] == "exp1"
    assert a["model"]["n_development_images"] >= 2
    lock=tmp_path/"lock.json"
    save_lock(a,lock)
    assert load_lock(lock, permit_partial=True)==a
    with pytest.raises(ValueError,match="Partial"):
        load_lock(lock)
    # Changed exp2 reference affects only inventory provenance, not score normalization.
    np.savetxt(root/"ExpertsSegmentations"/"Contours"/"RET000OD_cup_exp2.txt",
               rectangle(10,10,33,33))
    b=freeze_papila_model(root,draws=60,seed=8,allow_partial=True)
    assert a["model"]["scaler"] == b["model"]["scaler"]
    altered=json.loads(lock.read_text())
    altered["model"]["review_fraction"]=.8
    with pytest.raises(ValueError,match="SHA-256"):
        validate_model_lock(altered,permit_partial=True)


def test_test_archive_five_readers_and_no_fused_labels(tmp_path):
    archive=chaksu_fixture(tmp_path/"test.zip")
    cases,inventory=scan_test_archive(archive)
    assert len(cases)==3 and len(cases[0].mask_members)==10
    assert inventory["readable_case_counts_by_camera"]=={"bosch":1,"forus":1,"remidio":1}
    assert not inventory["matches_published_test_file_layout"]
    with zipfile.ZipFile(archive) as zf:
        img,masks=load_test_case(zf,cases[0])
    assert img.size==(44,48) and len(masks)==4
    assert masks[("expert 1","cup")].sum()>0


def test_missing_reader_and_corrupt_size_are_flagged(tmp_path):
    missing=chaksu_fixture(tmp_path/"missing.zip",missing=(0,5,"Cup"))
    cases,manifest=scan_test_archive(missing)
    assert len(cases)==2 and len(manifest["missing_annotation_cases"])==1
    corrupt=chaksu_fixture(tmp_path/"corrupt.zip",corrupt=(0,2,"Cup"))
    cases,_=scan_test_archive(corrupt)
    with zipfile.ZipFile(corrupt) as zf:
        with pytest.raises(ValueError,match="resolution mismatch"):
            load_test_case(zf,cases[0])


def test_external_requires_locked_source_and_complete_test_by_default(tmp_path):
    source=source_fixture(tmp_path/"PAPILA_DBv1")
    lock=tmp_path/"lock.json"
    save_lock(freeze_papila_model(source,draws=60,allow_partial=True),lock)
    archive=chaksu_fixture(tmp_path/"chaksu-test.zip")
    with pytest.raises(ValueError,match="Partial PAPILA"):
        run_external_test(archive,lock)
    summary,rows=run_external_test(archive,lock,allow_partial=True)
    assert len(rows)==3
    assert summary["partial_or_unverified_external"] is True
    assert summary["full_layout_and_readability_verified"] is False
    assert summary["fused_annotations_never_used"]
    assert summary["source_lock_partial"]
    assert summary["results"]["all"]["n"]==3
    assert "candidate_vcdr" in summary["results"]["all"]["scores"]
    folder=tmp_path/"out"
    save_external(summary,rows,folder)
    assert (folder/"external_summary.md").exists()
    assert (folder/"external_aggregate.json").exists()
    assert (folder/"external_private_cases.json").exists()
    aggregate_text = (folder/"external_aggregate.json").read_text()
    assert '"case_id"' not in aggregate_text
    assert "bosch/img_000" not in aggregate_text
    report=(folder/"external_summary.md").read_text()
    assert "NOT clinical accuracy" in report
    with pytest.raises(FileExistsError):
        save_external(summary,rows,folder)


def test_external_cli_round_trip_partial_only(tmp_path):
    papila=source_fixture(tmp_path/"PAPILA_DBv1",count=7)
    lock=tmp_path/"lock.json"
    assert external_cli(["freeze","--papila-root",str(papila),
                         "--output",str(lock),"--allow-partial","--draws","60"])==0
    chaksu=chaksu_fixture(tmp_path/"Test.zip",cases=2)
    out=tmp_path/"results"
    assert external_cli(["test","--model-lock",str(lock),
                         "--chaksu-test-zip",str(chaksu),
                         "--output-dir",str(out),"--allow-partial"])==0
    assert json.loads((out/"external_aggregate.json").read_text())["n_test_images_scored"]==2


def test_v09_secondary_five_reader_outcomes_are_separate_from_candidate_score(tmp_path):
    """Changing expert5 must affect the secondary target, never the expert1 QC score."""
    papila=source_fixture(tmp_path/"papila",count=9)
    lock=tmp_path/"model.json"
    save_lock(freeze_papila_model(papila,draws=60,allow_partial=True),lock)
    first=chaksu_fixture(tmp_path/"first.zip",cases=3,expert5_shift=0)
    second=chaksu_fixture(tmp_path/"second.zip",cases=3,expert5_shift=6)
    a,rows_a=run_external_test(first,lock,allow_partial=True)
    b,rows_b=run_external_test(second,lock,allow_partial=True)
    assert a["version"]==b["version"]=="1.0.0rc1"
    assert "secondary_five_reader_results" in a
    assert a["secondary_five_reader_results"]["all"]["n_images"]==3
    assert rows_a[0]["secondary_five_reader"]["all_unique_expert_pairs"]==10
    for old,new in zip(rows_a,rows_b):
        for field in ("candidate_vcdr","mask_q95","mask_roughness",
                      "mask_boundary_weakness","combined_candidate_score"):
            assert old[field]==new[field]
        assert old["absolute_expert1_expert2_vcdr_difference"]==new["absolute_expert1_expert2_vcdr_difference"]
        assert old["secondary_five_reader"]["all_ten_pairs_mean_absolute_vcdr"] != new["secondary_five_reader"]["all_ten_pairs_mean_absolute_vcdr"]

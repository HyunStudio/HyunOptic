from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from hyunoptic.papila import discover_cases, load_contours, load_image
from hyunoptic.cli import main


def build_sample(tmp_path: Path) -> Path:
    folder = tmp_path / "PAPILA_DBv1"
    images = folder / "FundusImages"
    contours = folder / "ExpertsSegmentations" / "Contours"
    images.mkdir(parents=True)
    contours.mkdir(parents=True)
    pts = {"disc": [[2,2],[14,2],[14,14],[2,14]], "cup": [[6,6],[10,6],[10,10],[6,10]]}
    for eye in ("OD", "OS"):
        Image.new("RGB", (20,20), "white").save(images / f"RET007{eye}.jpg")
        for expert in ("exp1", "exp2"):
            for structure in ("disc", "cup"):
                np.savetxt(contours / f"RET007{eye}_{structure}_{expert}.txt", pts[structure])
    # A duplicate macOS-style file must not alter ingestion.
    np.savetxt(contours / "RET007OD_cup_exp2 2.txt", pts["cup"])
    return folder


def test_case_discovery_load_and_eyes(tmp_path):
    build_sample(tmp_path)
    cases = discover_cases(tmp_path)
    assert [case.image_id for case in cases] == ["RET007OD", "RET007OS"]
    assert cases[0].patient_id == cases[1].patient_id == "RET007"
    assert load_image(cases[0]).size == (20,20)
    disc, cup = load_contours(cases[0], "exp1")
    assert disc.shape == (4,2) and cup.shape == (4,2)


def test_strict_requires_all_annotations(tmp_path):
    root = build_sample(tmp_path)
    (root / "ExpertsSegmentations" / "Contours" / "RET007OD_cup_exp2.txt").unlink()
    assert [case.image_id for case in discover_cases(tmp_path)] == ["RET007OS"]


def test_missing_dataset(tmp_path):
    with pytest.raises(FileNotFoundError, match="FundusImages"):
        discover_cases(tmp_path)


def test_cli_json_and_research_label(tmp_path):
    build_sample(tmp_path)
    output = tmp_path / "report" / "measurement.json"
    assert main(["--papila-root", str(tmp_path), "--image-id", "RET007OD", "--output", str(output)]) == 0
    text = output.read_text()
    assert '"research-only"' in text
    assert '"disc_dice": 1.0' in text


def test_hash_named_official_extract_root_discovered(tmp_path):
    """Publisher ZIP can unpack into a changing, hash-bearing top-level folder."""
    original = build_sample(tmp_path)
    renamed = original.rename(tmp_path / "PAPILA_DBv1_8f90ab293b")
    cases = discover_cases(tmp_path)
    assert [c.image_id for c in cases] == ["RET007OD", "RET007OS"]
    assert all(renamed in c.image_path.parents for c in cases)


def test_multiple_dataset_roots_refused_instead_of_mixed(tmp_path):
    import shutil
    original = build_sample(tmp_path)
    shutil.copytree(original, tmp_path / "PAPILA_db_other")
    with pytest.raises(ValueError, match="Multiple PAPILA datasets"):
        discover_cases(tmp_path)

"""PyTorch segmentation on SYNTHETIC fixtures only (mechanics, not performance)."""
from __future__ import annotations

import json

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")

from hyunoptic.demo_data import make_chaksu, make_papila  # noqa: E402
from hyunoptic.measure import measure_masks  # noqa: E402
from hyunoptic.seg.bundle import BundleError, MANIFEST, WEIGHTS, file_sha256, verify_bundle  # noqa: E402
from hyunoptic.seg.report import validate_report  # noqa: E402
from test_seg_contract import _page, _text  # noqa: E402


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    from hyunoptic.seg.train import train
    base = tmp_path_factory.mktemp("seg")
    root = make_papila(base / "PAPILA", patients=10)
    bundle = train(root, base / "models" / "tiny", image_size=64, epochs=2, batch_size=4,
                   base_channels=4, depth=2, allow_partial=True)
    return base, root, bundle


def test_training_reads_only_expert1_and_writes_verified_bundle(tmp_path, monkeypatch):
    from hyunoptic.seg import data, train as train_mod
    root = make_papila(tmp_path / "P", patients=10)
    seen = []
    original = data.load_contours
    monkeypatch.setattr(data, "load_contours", lambda case, reader: seen.append(reader) or original(case, reader))
    out = train_mod.train(root, tmp_path / "b", image_size=64, epochs=1, batch_size=4, base_channels=4,
                          depth=2, allow_partial=True)
    assert set(seen) == {"exp1"}
    bundle = verify_bundle(out)
    tr = bundle.manifest["training"]
    assert tr["expert2_used"] is False and tr["holdout_used_in_training_or_selection"] is False
    assert bundle.synthetic and bundle.partial
    assert tr["n_images"]["holdout"] > 0 and len(json.loads((out / "history.json").read_text())) == 1
    with pytest.raises(FileExistsError):
        train_mod.train(root, out, image_size=64, epochs=1, allow_partial=True)
    with pytest.raises(ValueError, match="incomplete"):
        train_mod.train(root, tmp_path / "c", image_size=64, epochs=1)


def test_bundle_gate_rejects_tampering_schema_and_non_tensor_weights(trained, tmp_path):
    import shutil
    from hyunoptic.seg.bundle import load_state_dict
    _, _, bundle_dir = trained
    copy = tmp_path / "copy"
    shutil.copytree(bundle_dir, copy)
    (copy / WEIGHTS).write_bytes((copy / WEIGHTS).read_bytes() + b"x")
    with pytest.raises(BundleError, match="SHA-256 mismatch"):
        verify_bundle(copy)
    manifest = json.loads((bundle_dir / MANIFEST).read_text())
    for change in ({"schema": "other/v9"}, {"files": {**manifest["files"], "../evil.pt": "0"}}):
        shutil.rmtree(copy)
        shutil.copytree(bundle_dir, copy)
        (copy / MANIFEST).write_text(json.dumps({**manifest, **change}))
        with pytest.raises(BundleError):
            verify_bundle(copy)
    shutil.rmtree(copy)
    shutil.copytree(bundle_dir, copy)
    torch.save({"weights": "not a tensor"}, copy / WEIGHTS)  # hash re-signed, content still unsafe
    manifest["files"][WEIGHTS] = file_sha256(copy / WEIGHTS)
    (copy / MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="tensor"):
        load_state_dict(verify_bundle(copy))


def test_inference_is_image_only_and_uses_shared_vcdr(trained, tmp_path):
    import shutil
    from hyunoptic.papila import discover_cases
    from hyunoptic.seg.inference import Predictor
    _, source, bundle_dir = trained
    root = tmp_path / "copy"  # edit a copy: the shared fixture must stay byte-identical
    shutil.copytree(source, root)
    predictor = Predictor(verify_bundle(bundle_dir))
    case = discover_cases(root)[0]
    with Image.open(case.image_path) as img:
        image = img.convert("RGB")
    before = predictor.predict(image)
    for p in (root / "ExpertsSegmentations" / "Contours").glob(f"{case.image_id}_*exp2.txt"):
        np.savetxt(p, np.array([[1, 1], [5, 1], [5, 5]]))  # change expert 2
    assert np.array_equal(predictor.predict(image).labels, before.labels)
    assert before.labels.shape == (image.height, image.width)  # original coordinates
    if before.status == "ok":
        assert before.measurement == measure_masks(before.disc, before.cup).to_dict()
    else:
        assert before.measurement is None and before.errors  # no fabricated vCDR


def test_holdout_evaluated_once_and_chaksu_always_exploratory(trained, tmp_path):
    from hyunoptic.seg.evaluate import evaluate_chaksu, evaluate_holdout
    from hyunoptic.seg.report import find_reports
    base, root, bundle_dir = trained
    bundle = verify_bundle(bundle_dir)
    first = evaluate_holdout(bundle, root)
    report = validate_report(json.loads((first / "model_eval_aggregate.json").read_text()))
    assert report["evaluation"] == "internal_papila_holdout" and report["n_images"] > 0
    assert report["exploratory"] is True  # synthetic/partial bundle can never look confirmatory
    aggregate = (first / "model_eval_aggregate.json").read_text()
    assert "RET0" not in aggregate  # identifiers stay in the private file
    assert "RET0" in (first / "model_eval_private_cases.json").read_text()
    with pytest.raises(FileExistsError, match="already evaluated"):
        evaluate_holdout(bundle, root)
    rerun = evaluate_holdout(bundle, root, exploratory_rerun=True)
    assert "Repeat" in json.loads((rerun / "model_eval_aggregate.json").read_text())["exploratory_reason"]
    zip_path = make_chaksu(tmp_path / "Test.zip", per_camera=2)
    ext = json.loads((evaluate_chaksu(bundle, zip_path) / "model_eval_aggregate.json").read_text())
    assert ext["exploratory"] is True and set(ext["by_camera"]) == {"bosch", "forus", "remidio"}
    assert "patient_cluster_bootstrap" not in ext["versus_expert1"]
    assert len(find_reports(bundle_dir)) == 3


def test_evaluation_refuses_changed_source_data(trained, tmp_path):
    import shutil
    from hyunoptic.seg.evaluate import evaluate_holdout
    _, root, bundle_dir = trained
    other = tmp_path / "P2"
    shutil.copytree(root, other)
    next((other / "FundusImages").glob("*.jpg")).write_bytes(b"changed")
    with pytest.raises(ValueError, match="differ"):
        evaluate_holdout(verify_bundle(bundle_dir), other)


def test_model_inference_page_with_bundle(trained, monkeypatch):
    base, root, bundle_dir = trained
    app = _page(monkeypatch, base, "model_inference", papila_root=str(root), models_dir=str(bundle_dir.parent))
    text = _text(app)
    assert "Synthetic-data model" in text and "Weights SHA-256" in text
    assert any(b.label == "Download case report (JSON)" and b.disabled for b in app.get("download_button"))
    app.toggle(key="mi_compare").set_value(True).run()
    assert not app.exception, [str(e.message) for e in app.exception]
    assert "Expert 1 disc · dotted" in _text(app)


def test_model_experiment_page_lists_internal_holdout_first(trained, tmp_path, monkeypatch):
    import shutil
    from hyunoptic.seg.evaluate import evaluate_chaksu, evaluate_holdout
    _, root, bundle_dir = trained
    copy = tmp_path / "models" / "run"
    shutil.copytree(bundle_dir, copy)
    shutil.rmtree(copy / "evaluation", ignore_errors=True)
    app = _page(monkeypatch, tmp_path, "model_experiment", models_dir=str(copy.parent))
    assert "Holdout not evaluated yet" in _text(app) and "Training behaviour" in _text(app)
    bundle = verify_bundle(copy)
    evaluate_chaksu(bundle, make_chaksu(tmp_path / "Test.zip", per_camera=2))
    evaluate_holdout(bundle, root)
    app = _page(monkeypatch, tmp_path, "model_experiment", models_dir=str(copy.parent))
    text = _text(app)
    assert "Internal PAPILA holdout" in text and "Exploratory external" not in text  # primary shown first
    assert "Synthetic-data model" in text


def test_tampered_bundle_is_rejected_visibly(trained, tmp_path, monkeypatch):
    import shutil
    _, _, bundle_dir = trained
    copy = tmp_path / "models" / "bad"
    shutil.copytree(bundle_dir, copy)
    (copy / "config.json").write_text("{}")
    app = _page(monkeypatch, tmp_path, "model_inference", models_dir=str(copy.parent))
    assert "Bundle rejected" in _text(app)


@pytest.mark.parametrize("field,value", [
    ("run_id", "another-run"), ("weights_sha256", "0" * 64),
    ("split_manifest_sha256", "0" * 64),
    ("bundle_data_status", {"synthetic": False, "partial": False, "inventory_complete": True}),
    ("exploratory", False),
])
def test_experiment_rejects_reports_with_wrong_model_or_data_status(trained, tmp_path, monkeypatch, field, value):
    import shutil
    from hyunoptic.seg.evaluate import evaluate_holdout
    _, root, bundle_dir = trained
    copy = tmp_path / "models" / "run"
    shutil.copytree(bundle_dir, copy)
    if (copy / "evaluation").exists():
        shutil.rmtree(copy / "evaluation")
    report_path = evaluate_holdout(verify_bundle(copy), root) / "model_eval_aggregate.json"
    report = json.loads(report_path.read_text())
    report[field] = value
    report_path.write_text(json.dumps(report), encoding="utf-8")
    app = _page(monkeypatch, tmp_path, "model_experiment", models_dir=str(copy.parent))
    assert "Report rejected" in _text(app)
    assert "Median cup Dice" not in _text(app)

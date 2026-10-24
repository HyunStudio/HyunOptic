"""Synthetic metadata fixtures only; a passed gate is NOT scientific validation."""
from __future__ import annotations
import copy
import json
import pytest

from hyunoptic.evidence_gate import review_evidence, save_evidence_review
from hyunoptic.evidence_cli import main as evidence_main
from hyunoptic.freeze import canonical_digest
from hyunoptic.mask_features import MASK_FEATURES, MASK_FEATURE_VERSION
from hyunoptic.uncertainty import PerturbationConfig


def _put(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def evidence_files(tmp_path):
    model = {
        "project": "HyunOptic", "lock_version": "0.7.0",
        "method": MASK_FEATURE_VERSION, "candidate_reader": "exp1",
        "feature_names": list(MASK_FEATURES),
        "source_is_partial": False, "source_complete_inventory": True,
        "source_metadata_fingerprint": "local-metadata-sha",
        "source_content_sha256": "f" * 64,
        "review_fraction": .2, "research_disagreement_threshold": .1,
        "no_outcome_labels_used_in_scaling": True,
        "no_external_data_used_in_scaling": True,
        "perturbation": PerturbationConfig(draws=100).__dict__,
        "scaler": {name: {"mean": 0.2, "sd": 0.1} for name in MASK_FEATURES},
    }
    lock = {"model": model, "sha256": canonical_digest(model)}
    paths = {
        "sources": _put(tmp_path/"sources.json", {
            "project": "HyunOptic",
            "checks": [
                {"dataset": "PAPILA", "matches_independent_public_reference": True},
                {"dataset": "CHAKSU_TEST", "matches_independent_public_reference": True},
            ],
        }),
        "papila_inventory": _put(tmp_path/"inventory.json", {
            "project": "HyunOptic", "matches_full_published_shape": True,
            "observed": {"images": 488, "patients": 244},
            "inventory_sha256_of_paths_and_sizes_only": "local-metadata-sha",
        }),
        "model_lock": _put(tmp_path/"lock.json", lock),
        "source_holdout": _put(tmp_path/"source.json", {
            "project": "HyunOptic", "source_lock_sha256": lock["sha256"],
            "source_content_sha256": "f" * 64,
            "source_inventory_fingerprint": "local-metadata-sha",
            "full_source_holdout_scored": True, "partial_or_unverified": False,
            "n_source_images_discovered": 488, "n_source_patient_groups": 244,
            "n_failed": 0,
            "patient_split_counts": {
                "development": {"n_images": 292},
                "validation": {"n_images": 98},
                "holdout": {"n_images": 98},
            },
            "evaluation": {
                "validation": {"n_images": 98},
                "holdout": {"n_images": 98},
            },
        }),
        "chaksu_audit": _put(tmp_path/"audit.json", {
            "project": "HyunOptic", "all_published_test_masks_structurally_verified": True,
            "n_checked": 336, "n_readable_with_all_five_experts": 336, "n_errors": 0,
        }),
        "external_aggregate": _put(tmp_path/"external.json", {
            "project": "HyunOptic",
            "full_layout_and_readability_verified": True,
            "partial_or_unverified_external": False,
            "n_test_images_scored": 336, "n_failed": 0,
            "source_lock_partial": False,
            "source_lock_sha256": lock["sha256"],
            "fused_annotations_never_used": True,
            "reference_label": "absolute expert1 vs expert2 vCDR disagreement (not diagnosis)",
        }),
    }
    return paths


def test_all_consistent_synthetic_metadata_is_only_package_ready(tmp_path):
    paths = evidence_files(tmp_path)
    doc = review_evidence(**paths)
    assert doc["all_required_artifacts_consistent"] is True
    assert doc["n_passed"] == doc["n_total"]
    assert doc["scientific_validity_established"] is False
    assert doc["clinical_accuracy_established"] is False
    assert "third-party" in " ".join(doc["limitations"])
    out = tmp_path / "gate.json"
    save_evidence_review(doc, out)
    assert json.loads(out.read_text())["all_required_artifacts_consistent"]
    with pytest.raises(FileExistsError):
        save_evidence_review(doc, out)


def test_external_lock_mismatch_fails_and_strict_exits_nonzero(tmp_path):
    paths = evidence_files(tmp_path)
    result = json.loads(paths["external_aggregate"].read_text())
    result["source_lock_sha256"] = "a" * 64
    _put(paths["external_aggregate"], result)
    report = review_evidence(**paths)
    assert not report["all_required_artifacts_consistent"]
    assert not report["checks"]["exact_frozen_lock_matches_external"]["passed"]
    args = []
    for field, value in paths.items():
        args.extend(["--" + field.replace("_", "-"), str(value)])
    args.extend(["--output", str(tmp_path/"gate.json"), "--strict"])
    assert evidence_main(args) == 2


def test_missing_source_preflight_and_partial_rejected(tmp_path):
    paths = evidence_files(tmp_path)
    source = json.loads(paths["sources"].read_text())
    source["checks"] = source["checks"][:1]
    _put(paths["sources"], source)
    audit = json.loads(paths["chaksu_audit"].read_text())
    audit["n_readable_with_all_five_experts"] = 335
    _put(paths["chaksu_audit"], audit)
    aggregate = json.loads(paths["external_aggregate"].read_text())
    aggregate["partial_or_unverified_external"] = True
    _put(paths["external_aggregate"], aggregate)
    result = review_evidence(**paths)
    assert not result["checks"]["archive_identity_metadata"]["passed"]
    assert not result["checks"]["matching_public_reference_archives"]["passed"]
    assert not result["checks"]["full_Chaksu_five_reader_preflight"]["passed"]
    assert not result["checks"]["complete_external_aggregate"]["passed"]


def test_tampered_model_lock_is_rejected(tmp_path):
    paths = evidence_files(tmp_path)
    model = json.loads(paths["model_lock"].read_text())
    model["model"]["review_fraction"] = 0.9
    _put(paths["model_lock"], model)
    with pytest.raises(ValueError, match="SHA-256"):
        review_evidence(**paths)


def test_missing_inputs_are_errors_not_passing(tmp_path):
    paths = evidence_files(tmp_path)
    paths["sources"].unlink()
    with pytest.raises(FileNotFoundError):
        review_evidence(**paths)


def test_missing_source_holdout_cannot_pass_evidence_gate(tmp_path):
    files = evidence_files(tmp_path)
    body = json.loads(files["source_holdout"].read_text())
    body["n_failed"] = 1
    body["partial_or_unverified"] = True
    _put(files["source_holdout"], body)
    result = review_evidence(**files)
    assert not result["checks"]["complete_PAPILA_source_mask_holdout"]["passed"]
    assert not result["all_required_artifacts_consistent"]


def test_source_content_binding_must_match_locked_dataset(tmp_path):
    files = evidence_files(tmp_path)
    body = json.loads(files["source_holdout"].read_text())
    body["source_content_sha256"] = "0" * 64
    _put(files["source_holdout"], body)
    result = review_evidence(**files)
    assert not result["checks"]["same_PAPILA_content_sha256_for_source_evaluation"]["passed"]

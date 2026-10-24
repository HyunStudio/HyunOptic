"""Cross-file evidence bundle gate for release *review*, not clinical validity.

This gate checks internal consistency of outputs from the actual local study
commands. It is NOT an independent audit, signed attestation, IRB approval,
peer review, or evidence of diagnostic/clinical performance.
"""
from __future__ import annotations

import json
from pathlib import Path

from .freeze import load_lock


def _json_file(path: str | Path, label: str) -> dict:
    file = Path(path)
    if not file.is_file():
        raise FileNotFoundError(f"Missing {label} file: {file}")
    content = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return content


def review_evidence(
    *, sources: str | Path, papila_inventory: str | Path,
    model_lock: str | Path, source_holdout: str | Path, chaksu_audit: str | Path,
    external_aggregate: str | Path,
) -> dict:
    """Assess provenance and cross-file consistency without reading patient rows."""
    source = _json_file(sources, "archive identity")
    inventory = _json_file(papila_inventory, "PAPILA inventory")
    audit = _json_file(chaksu_audit, "Chaksu all-expert preflight")
    source_result = _json_file(source_holdout, "PAPILA mask holdout aggregate")
    aggregate = _json_file(external_aggregate, "external aggregate")
    try:
        lock = load_lock(model_lock, permit_partial=True)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed frozen source lock: {exc}") from exc

    checks: dict[str, dict] = {}
    def record(name: str, condition: bool, rationale: str) -> None:
        checks[name] = {"passed": bool(condition), "description": rationale}

    listed = source.get("checks", [])
    by_dataset = {item.get("dataset"): item for item in listed if isinstance(item, dict)}
    record("archive_identity_metadata",
           source.get("project") == "HyunOptic" and
           set(by_dataset) == {"PAPILA", "CHAKSU_TEST"} and len(listed) == 2,
           "Two local archive SHA-256 reports, one per expected source.")
    record("matching_public_reference_archives",
           len(listed) == 2 and all(
               item.get("matches_independent_public_reference") is True
               for item in by_dataset.values()
           ),
           "Exact byte match with third-party reference archives, not publisher signatures.")
    record("full_PAPILA_inventory",
           inventory.get("project") == "HyunOptic" and
           inventory.get("matches_full_published_shape") is True and
           inventory.get("observed", {}).get("images") == 488 and
           inventory.get("observed", {}).get("patients") == 244,
           "244 patients/488 images with dataset structural QA; not clinical truth.")
    body = lock["model"]
    record("frozen_PAPILA_development_only_model",
           not body.get("source_is_partial", True) and
           body.get("source_complete_inventory") is True and
           body.get("no_outcome_labels_used_in_scaling") is True and
           body.get("no_external_data_used_in_scaling") is True,
           "Source-only feature scaling with a validated content-integrity hash.")
    record("same_PAPILA_inventory_fingerprint",
           (body.get("source_metadata_fingerprint") ==
            inventory.get("inventory_sha256_of_paths_and_sizes_only")
            and bool(body.get("source_metadata_fingerprint"))),
           "Model and inventory point to identical file-name/size fingerprint.")
    record("same_PAPILA_content_sha256_for_source_evaluation",
           bool(body.get("source_content_sha256")) and
           body["source_content_sha256"] == source_result.get("source_content_sha256"),
           "Source evaluation uses the exact file contents bound to the frozen model.")
    validation = source_result.get("evaluation", {})
    partitions = source_result.get("patient_split_counts", {})
    record("complete_PAPILA_source_mask_holdout",
           source_result.get("project") == "HyunOptic" and
           source_result.get("full_source_holdout_scored") is True and
           source_result.get("partial_or_unverified") is False and
           source_result.get("n_source_images_discovered") == 488 and
           source_result.get("n_source_patient_groups") == 244 and
           source_result.get("n_failed") == 0 and
           source_result.get("source_lock_sha256") == lock["sha256"] and
           source_result.get("source_inventory_fingerprint") ==
               inventory.get("inventory_sha256_of_paths_and_sizes_only") and
           all(validation.get(split, {}).get("n_images", 0) > 0
               for split in ("validation", "holdout")) and
           sum(partitions.get(split, {}).get("n_images", 0)
               for split in ("development", "validation", "holdout")) == 488,
           "Internal PAPILA source holdout uses same frozen MASK model, patient split, "
           "and provides nonempty held-out comparison on original 488 eyes.")
    record("full_Chaksu_five_reader_preflight",
           audit.get("project") == "HyunOptic" and
           audit.get("all_published_test_masks_structurally_verified") is True and
           audit.get("n_checked") == 336 and
           audit.get("n_readable_with_all_five_experts") == 336 and
           audit.get("n_errors") == 0,
           "All 336 published Test images with 5 expert mask pairs pass structural QA.")
    record("complete_external_aggregate",
           aggregate.get("project") == "HyunOptic" and
           aggregate.get("full_layout_and_readability_verified") is True and
           aggregate.get("partial_or_unverified_external") is False and
           aggregate.get("n_test_images_scored") == 336 and
           aggregate.get("n_failed") == 0 and
           aggregate.get("source_lock_partial") is False,
           "Source-frozen aggregate on the full Chaksu Test cohort.")
    record("exact_frozen_lock_matches_external",
           bool(lock["sha256"]) and
           lock["sha256"] == aggregate.get("source_lock_sha256"),
           "The same frozen model lock is declared in external research output.")
    record("external_disagreement_not_diagnosis",
           aggregate.get("fused_annotations_never_used") is True and
           str(aggregate.get("reference_label", "")).startswith(
               "absolute expert1 vs expert2 vCDR disagreement"
           ),
           "Endpoint concerns inter-reader consistency, not glaucoma diagnosis.")
    complete = all(row["passed"] for row in checks.values())
    return {
        "project": "HyunOptic",
        "gate_version": "1.0.0rc3",
        "purpose": "internal evidence-package readiness for independent scientific review",
        "all_required_artifacts_consistent": complete,
        "scientific_validity_established": False,
        "clinical_accuracy_established": False,
        "source_lock_sha256": lock["sha256"],
        "checks": checks,
        "n_passed": sum(item["passed"] for item in checks.values()),
        "n_total": len(checks),
        "limitations": [
            "Passing structural checks cannot prove that research effects are real or useful.",
            "Reports and JSON may be modified by their owner; this is not signed or independently notarized.",
            "A third-party reference SHA-256 match is not an official publisher signature.",
            "Image/patient independence in Chaksu is unverified; do not calculate naive patient-level CIs.",
            "Review scientific assumptions, observed effect sizes, exclusion patterns and data licenses before publication.",
        ],
    }


def save_evidence_review(result: dict, path: str | Path) -> None:
    output = Path(path)
    if output.exists():
        raise FileExistsError("Refusing to overwrite an earlier evidence review")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8"
    )

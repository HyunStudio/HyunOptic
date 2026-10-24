"""Frozen PAPILA-source -> Chaksu Test external-domain reader-disagreement study.

Original ZIP only, with paired independent reader masks. All source scaling is
frozen before inspection of any Chaksu outcomes.
"""
from __future__ import annotations
import hashlib
import json
import zipfile
from pathlib import Path
import numpy as np
from .chaksu import EXPECTED_TEST, load_test_case, scan_test_archive
from .external_qc import check_chaksu_archive
from .evaluation import evaluate_at_budget
from .freeze import load_lock
from .mask_features import apply_mask_score, mask_features
from .multi_reader import READERS, five_reader_targets
from .measure import measure_masks
from .ranking import ranking_metrics
from .uncertainty import PerturbationConfig

SCORES = ("candidate_vcdr", "mask_q95", "mask_roughness",
          "mask_boundary_weakness", "combined_candidate_score")

def run_external_test(test_zip: str | Path, frozen_lock: str | Path,
                      *, allow_partial: bool = False) -> tuple[dict, list[dict]]:
    """Requires a full original Test.zip by default; partial fixtures marked unverified."""
    payload = load_lock(frozen_lock, permit_partial=allow_partial)
    lock = payload["model"]
    cases, data_manifest = scan_test_archive(test_zip)
    if not allow_partial and not data_manifest["matches_published_test_file_layout"]:
        raise ValueError("Published Chaksu 336-image Test structure not matched; "
                         "no full external claim permitted")
    if not cases:
        raise ValueError("No complete Chaksu Test image/five-reader mask pairs discovered")
    # A correct FILE COUNT is insufficient: verify all five human mask payloads
    # before presenting a fully verified external-domain analysis. This doubles
    # some I/O but avoids an unverified 3rd–5th reader masquerading as validated.
    full_preflight = None
    if not allow_partial:
        full_preflight, _ = check_chaksu_archive(test_zip)
        if not full_preflight["all_published_test_masks_structurally_verified"]:
            raise ValueError(
                "Chaksu five-reader payload preflight failed. "
                "Run hyunoptic-chaksu-audit for private case-level diagnostics."
            )
    cfg = PerturbationConfig(**lock["perturbation"])
    rows, failures = [], []
    with zipfile.ZipFile(test_zip) as zf:
        for case in cases:
            try:
                image, masks = load_test_case(zf, case, readers=READERS)
                # No expert2 measurement, other experts or fused masks enter scoring.
                first_disc, first_cup = masks[("expert 1", "disc")], masks[("expert 1", "cup")]
                features = mask_features(image, first_disc, first_cup, cfg)
                score = apply_mask_score(features, lock["scaler"])
                second = measure_masks(masks[("expert 2", "disc")],
                                       masks[("expert 2", "cup")])
                disagreement = abs(features["candidate_vcdr"] - second.vertical_cdr)
                # Secondary five-reader outcomes are calculated only AFTER the
                # single-reader candidate score is frozen for this case.
                all_reader_vcdr = {
                    reader: measure_masks(masks[(reader, "disc")], masks[(reader, "cup")]).vertical_cdr
                    for reader in READERS
                }
                peer = five_reader_targets(
                    all_reader_vcdr,
                    threshold=lock["research_disagreement_threshold"],
                    candidate_reader="expert 1",
                )
                rows.append({
                    "case_id": case.case_id, "camera": case.camera,
                    **features, "combined_candidate_score": score,
                    "reference_reader": "expert 2",
                    "absolute_expert1_expert2_vcdr_difference": disagreement,
                    "secondary_five_reader": peer,
                })
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                failures.append({"case_id": case.case_id, "error": str(exc)})
    fully_verified = (data_manifest["matches_published_test_file_layout"]
                      and len(rows) == 336 and not failures
                      and not lock["source_is_partial"]
                      and full_preflight is not None
                      and full_preflight["all_published_test_masks_structurally_verified"])
    if not fully_verified and not allow_partial:
        raise ValueError(f"External Test decoding/measurements incomplete "
                         f"({len(failures)} failures, {len(rows)}/336 usable); "
                         "no full external report will be produced")
    if not rows:
        raise ValueError("No decodable test cases")

    metrics: dict[str, dict] = {}
    for group in ("all", *EXPECTED_TEST):
        subset = [r for r in rows if group == "all" or r["camera"] == group]
        if not subset:
            metrics[group] = {"n": 0, "missing": True}
            continue
        target = np.asarray([r["absolute_expert1_expert2_vcdr_difference"] for r in subset])
        metrics[group] = {
            "n": len(subset),
            "n_high_disagreement": int((target > lock["research_disagreement_threshold"]).sum()),
            "scores": {
                name: {
                    "review": evaluate_at_budget([r[name] for r in subset], target,
                        review_fraction=lock["review_fraction"],
                        discrepancy_threshold=lock["research_disagreement_threshold"]).to_dict(),
                    "ranking": ranking_metrics([r[name] for r in subset], target,
                        threshold=lock["research_disagreement_threshold"]),
                } for name in SCORES
            },
        }
    for group in metrics.values():
        if group.get("missing"):
            continue
        baseline = group["scores"]["candidate_vcdr"]
        proposed = group["scores"]["combined_candidate_score"]
        b, p = baseline["review"], proposed["review"]
        bk, pk = baseline["ranking"], proposed["ranking"]
        group["comparison_to_vcdr_descriptive"] = {
            "precision_at_review_budget_delta": p["precision_at_budget"] - b["precision_at_budget"],
            "recall_at_review_budget_delta": None
                if p["recall_at_budget"] is None or b["recall_at_budget"] is None
                else p["recall_at_budget"] - b["recall_at_budget"],
            "average_precision_delta": None
                if pk["average_precision"] is None or bk["average_precision"] is None
                else pk["average_precision"] - bk["average_precision"],
            "roc_auc_delta": None
                if pk["roc_auc"] is None or bk["roc_auc"] is None
                else pk["roc_auc"] - bk["roc_auc"],
            "interpretation": "Descriptive paired-cohort difference only. "
                              "No significance test, population confidence interval, or clinical claim.",
        }
    secondary_evaluation: dict[str, dict] = {}
    for group_name in ("all", *EXPECTED_TEST):
        subset = [r for r in rows if group_name == "all" or r["camera"] == group_name]
        if not subset:
            secondary_evaluation[group_name] = {"n": 0, "missing": True}
            continue
        # Target >=2 disagreements among 4 reference readers; fixed
        # research voting rule, not a glaucoma diagnosis and not independent.
        target = np.array(
            [1.0 if r["secondary_five_reader"]["candidate_vs_four_at_least_two_high"]
             else 0.0 for r in subset], dtype=float
        )
        secondary_evaluation[group_name] = {
            "n_images": len(subset),
            "high_disagreement_with_at_least_two_of_four_peers": int(target.sum()),
            "mean_of_all_ten_unique_reader_pairs_abs_vcdr": float(
                np.mean([r["secondary_five_reader"]["all_ten_pairs_mean_absolute_vcdr"]
                         for r in subset])),
            "scores": {
                name: {
                    "review": evaluate_at_budget(
                        [r[name] for r in subset], target,
                        discrepancy_threshold=0.5,
                        review_fraction=lock["review_fraction"]
                    ).to_dict(),
                    "ranking": ranking_metrics(
                        [r[name] for r in subset], target, threshold=0.5
                    ),
                }
                for name in ("candidate_vcdr", "mask_q95", "combined_candidate_score")
            },
        }
    manifest = {
        "project": "HyunOptic", "version": "0.9.0", "status": "research-only",
        "study": "PAPILA-development-locked candidate mask scoring on external Chaksu Test",
        "external_test_source": "Chaksu original Test.zip, five individual readers in archive",
        "fused_annotations_never_used": True,
        "reference_label": "absolute expert1 vs expert2 vCDR disagreement (not diagnosis)",
        "candidate_score_input": "image and expert 1 disc/cup masks ONLY",
        "source_lock_sha256": payload["sha256"],
        "source_lock_partial": lock["source_is_partial"],
        "test_file_layout": data_manifest,
        "n_test_images_scored": len(rows),
        "n_failed": len(failures),
        "statistical_inference": "Descriptive only: dependence of repeated patient images is not identified.",
        "failures": failures,
        "full_layout_and_readability_verified": fully_verified,
        "all_five_readers_payload_preflight_verified": bool(full_preflight and full_preflight["all_published_test_masks_structurally_verified"]),
        "partial_or_unverified_external": not fully_verified,
        "results": metrics,
        "secondary_five_reader_results": secondary_evaluation,
        "secondary_five_reader_target": "expert1 disagrees >0.10 in vCDR with at least 2 of experts2-5",
        "limitations": [
            "External DOMAIN validation of measurement agreement, NOT clinical glaucoma diagnosis.",
            "Candidate expert 1 and reference expert 2 are only a fixed illustrative pair of five annotators.",
            "No patient-identifiers exist for most Chaksu images; do NOT assume independent patients.",
            "Camera-stratified results can be low-powered and are exploratory.",
            "Secondary four-peer voting is a research-defined disagreement endpoint, NOT consensus medical truth.",
            "This uses a new, uniform mask feature family; prior PAPILA polygon-score performance is not directly comparable.",
            "A source-lock digest is not third-party preregistration; mask shape checks are not proof of clinical correctness.",
            "Do not inspect these results to retune the purported frozen external scoring protocol.",
        ],
    }
    return manifest, rows

def save_external(summary: dict, rows: list[dict], output_dir: str | Path) -> None:
    dest = Path(output_dir)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError("Refusing to overwrite prior external research results")
    dest.mkdir(parents=True, exist_ok=True)
    # Keep case-level results local/private, not GitHub Actions artifacts.
    # Do not leak per-image identifiers through the "aggregate" manifest.
    aggregate = {k: v for k, v in summary.items() if k != "failures"}
    layout = dict(aggregate["test_file_layout"])
    missing_details = layout.pop("missing_annotation_cases", [])
    duplicate_details = layout.pop("ambiguous_duplicate_members", [])
    suspicious_details = layout.pop("suspicious_members", [])
    layout["n_missing_annotation_cases"] = len(missing_details)
    layout["n_duplicate_member_names"] = len(duplicate_details)
    layout["n_suspicious_member_names"] = len(suspicious_details)
    aggregate["test_file_layout"] = layout
    (dest / "external_aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (dest / "external_private_cases.json").write_text(
        json.dumps({"rows": rows, "failures": summary["failures"],
                    "missing_annotation_cases": missing_details,
                    "duplicate_member_names": duplicate_details,
                    "suspicious_member_names": suspicious_details},
                   indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# HyunOptic — Chaksu Test external-domain consistency analysis",
        "",
        "> Research only. NOT clinical accuracy, not glaucoma diagnosis.",
        f"> Complete Test inventory and decoding: **{summary['full_layout_and_readability_verified']}**.",
        f"> Partial/unverified dataset: **{summary['partial_or_unverified_external']}**.",
        "",
        f"- Frozen PAPILA model-lock SHA-256: `{summary['source_lock_sha256']}`",
        f"- Images analyzed: **{summary['n_test_images_scored']}**",
        f"- Failed image-mask pairs: **{summary['n_failed']}**",
        "",
        "## High reader-disagreement ranking at a fixed 20% review budget",
        "",
        "| Camera | Images | High disagreement | Score | Precision@budget | Recall@budget | AP | ROC AUC |",
        "|---|---:|---:|---|---:|---:|---:|---:|",
    ]
    for group, data in summary["results"].items():
        if data.get("missing"):
            continue
        for name in ("candidate_vcdr", "mask_q95", "combined_candidate_score"):
            pair = data["scores"][name]
            r, k = pair["review"], pair["ranking"]
            fmt = lambda x: "N/A" if x is None else f"{x:.3f}"
            lines.append(
                f"| {group} | {data['n']} | {data['n_high_disagreement']} | {name} | "
                f"{fmt(r['precision_at_budget'])} | {fmt(r['recall_at_budget'])} | "
                f"{fmt(k['average_precision'])} | {fmt(k['roc_auc'])} |"
            )
    lines.extend(["", "## Descriptive comparison against vCDR ranking", "",
                  "The difference below is on the SAME scored images. A positive value is",
                  "not proof of real-world benefit or statistical significance.", "",
                  "| Camera | Delta precision@budget (combined - vCDR) |",
                  "|---|---:|"])
    for group_name, value in summary["results"].items():
        if not value.get("missing"):
            delta = value["comparison_to_vcdr_descriptive"]["precision_at_review_budget_delta"]
            lines.append(f"| {group_name} | {delta:+.3f} |")
    lines.append("")
    lines.extend(["", "## Secondary analysis: all five independent experts", "",
                  "Candidate QC scores still use ONLY expert 1 + photo. This analysis",
                  "compares that score to a separately computed 2-of-4 reader",
                  "disagreement target. These readers are correlated and no",
                  "majority medical diagnosis or clinical correctness is implied.",
                  "",
                  "| Camera | n images | 2-of-4 high disagreement | Score | Precision@budget | AP |",
                  "|---|---:|---:|---|---:|---:|"])
    secondary = summary["secondary_five_reader_results"]
    for camera, result in secondary.items():
        if result.get("missing"):
            continue
        for name in ("candidate_vcdr", "combined_candidate_score"):
            record = result["scores"][name]
            ap = record["ranking"]["average_precision"]
            fmt_ap = "N/A" if ap is None else f"{ap:.3f}"
            lines.append(
                f"| {camera} | {result['n_images']} | "
                f"{result['high_disagreement_with_at_least_two_of_four_peers']} | "
                f"{name} | {record['review']['precision_at_budget']:.3f} | {fmt_ap} |"
            )
    lines.extend(["", "## Interpretation", ""])
    lines += ["- " + limitation for limitation in summary["limitations"]]
    lines.extend(["", "Scores are descriptive and hypothesis-generating. "
                  "No accuracy improvement is asserted without the actual results, "
                  "quality review, and appropriate statistical comparisons.", ""])
    (dest / "external_summary.md").write_text("\n".join(lines), encoding="utf-8")

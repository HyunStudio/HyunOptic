"""Locked PAPILA mask-based internal evaluation for the EXACT feature family
later used on Chaksu. Development split is used for unlabeled scaler fitting
by freeze.py and NEVER scored against expert2 in this evaluation.

Reference reader is opened only after exp1 candidate scoring, to prevent leakage.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np

from .evaluation import evaluate_at_budget
from .freeze import load_lock
from .inventory import inspect_papila
from .mask_features import apply_mask_score, mask_features
from .measure import measure_masks, polygon_mask
from .papila import discover_cases, load_contours, load_image
from .ranking import ranking_metrics
from .study import _patient_bootstrap_difference, patient_splits
from .source_fingerprint import papila_content_sha256
from .uncertainty import PerturbationConfig

SCORE_NAMES = (
    "candidate_vcdr", "mask_q95", "mask_roughness",
    "mask_boundary_weakness", "combined_candidate_score",
)


def evaluate_source(
    root: str | Path, frozen_lock: str | Path, *, allow_partial: bool = False,
    bootstrap_draws: int = 1000,
) -> tuple[dict, list[dict]]:
    """Evaluate only source validation/holdout eyes using locked mask features.

    Same frozen score and vCDR definition as the external Chaksu Test evaluator.
    All patient grouping and evaluator settings are taken from the source lock.
    """
    payload = load_lock(frozen_lock, permit_partial=allow_partial)
    model = payload["model"]
    inventory = inspect_papila(root)
    if inventory["inventory_sha256_of_paths_and_sizes_only"] != model["source_metadata_fingerprint"]:
        raise ValueError("PAPILA source files differ from those used for the frozen model")
    if not allow_partial and not inventory["matches_full_published_shape"]:
        raise ValueError("Full original PAPILA inventory is required for source validation")
    content_hash = model.get("source_content_sha256")
    if not content_hash:
        raise ValueError(
            "Frozen PAPILA model lacks source content SHA-256; regenerate lock "
            "with the current software before source holdout analysis."
        )
    if papila_content_sha256(root) != content_hash:
        raise ValueError(
            "PAPILA source CONTENT differs from the frozen model; "
            "a same-sized change is not accepted."
        )
    cases = discover_cases(root)
    assignments = patient_splits([c.patient_id for c in cases], seed=model["split_seed"])
    groups = {
        split: [case for case in cases if assignments[case.patient_id] == split]
        for split in ("development", "validation", "holdout")
    }
    if not groups["validation"] or not groups["holdout"]:
        raise ValueError("Empty validation or holdout source partition")
    if len(groups["development"]) != model["n_development_images"]:
        raise ValueError("Frozen development case count does not match same-patient split")
    cfg = PerturbationConfig(**model["perturbation"])
    rows, failures = [], []
    for split in ("validation", "holdout"):
        for case in groups[split]:
            try:
                image = load_image(case)
                disc1, cup1 = load_contours(case, "exp1")
                d1 = polygon_mask(disc1, image.size)
                c1 = polygon_mask(cup1, image.size)
                # Candidate scoring has *no* second-expert inputs.
                feat = mask_features(image, d1, c1, cfg)
                score = apply_mask_score(feat, model["scaler"])
                # Retrospective comparison happens only AFTER frozen scoring.
                disc2, cup2 = load_contours(case, "exp2")
                m2 = measure_masks(
                    polygon_mask(disc2, image.size),
                    polygon_mask(cup2, image.size),
                )
                diff = abs(feat["candidate_vcdr"] - m2.vertical_cdr)
                rows.append({
                    "image_id": case.image_id, "patient_id": case.patient_id,
                    "eye": case.eye, "split": split, **feat,
                    "combined_candidate_score": score,
                    "absolute_reader_vcdr_disagreement": diff,
                    # Alias for existing patient-cluster paired-bootstrap util.
                    "heldout_absolute_vcdr_difference": diff,
                })
            except (OSError, ValueError, RuntimeError) as exc:
                failures.append({"image_id": case.image_id, "reason": str(exc)})
    full = (
        inventory["matches_full_published_shape"]
        and not model["source_is_partial"]
        and len(cases) == 488
        and len(rows) == len(groups["validation"]) + len(groups["holdout"])
        and not failures
        and not allow_partial
    )
    if not full and not allow_partial:
        raise ValueError(
            f"Source validation incomplete: {len(failures)} failed eyes; "
            "refusing a complete source report. Inspect local PAPILA annotations."
        )
    statistics = {}
    for split in ("validation", "holdout"):
        subset = [r for r in rows if r["split"] == split]
        if not subset:
            raise ValueError(f"No usable {split} cases")
        target = [r["absolute_reader_vcdr_disagreement"] for r in subset]
        scores = {
            name: {
                "review": evaluate_at_budget(
                    [r[name] for r in subset], target,
                    discrepancy_threshold=model["research_disagreement_threshold"],
                    review_fraction=model["review_fraction"],
                ).to_dict(),
                "ranking": ranking_metrics(
                    [r[name] for r in subset], target,
                    threshold=model["research_disagreement_threshold"],
                ),
            }
            for name in SCORE_NAMES
        }
        primary = scores["combined_candidate_score"]
        baseline = scores["candidate_vcdr"]
        delta_precision = (
            primary["review"]["precision_at_budget"] -
            baseline["review"]["precision_at_budget"]
        )
        statistics[split] = {
            "n_images": len(subset),
            "n_patients": len({r["patient_id"] for r in subset}),
            "n_high_disagreement": int(sum(
                value > model["research_disagreement_threshold"] for value in target
            )),
            "scores": scores,
            "combined_minus_vcdr_precision_at_budget": float(delta_precision),
        }
    holdout = [r for r in rows if r["split"] == "holdout"]
    ci = _patient_bootstrap_difference(
        holdout, baseline="candidate_vcdr", candidate="combined_candidate_score",
        threshold=model["research_disagreement_threshold"],
        fraction=model["review_fraction"],
        seed=model["split_seed"],
        draws=bootstrap_draws,
    )
    return {
        "project": "HyunOptic", "version": "1.0.0rc3",
        "study_type": "PAPILA source-only heldout MASK feature benchmarking",
        "research_only": True, "not_external_validation": True,
        "not_clinical_diagnosis": True,
        "candidate_expert": "exp1", "reference_expert": "exp2",
        "source_lock_sha256": payload["sha256"],
        "source_inventory_fingerprint": model["source_metadata_fingerprint"],
        "source_content_sha256": content_hash,
        "model_scoring_method": model["method"],
        "source_complete_inventory": inventory["matches_full_published_shape"],
        "source_partial": model["source_is_partial"],
        "full_source_holdout_scored": full,
        "partial_or_unverified": not full,
        "n_source_images_discovered": len(cases),
        "n_source_patient_groups": len(set(assignments)),
        "n_evaluated_images": len(rows),
        "n_failed": len(failures),
        "failures": failures,  # Never export to aggregate report.
        "patient_split_counts": {
            split: {"n_images": len(group),
                    "n_patients": len({c.patient_id for c in group})}
            for split, group in groups.items()
        },
        "evaluation": statistics,
        "paired_patient_bootstrap_holdout": ci,
        "negative_control_warning": (
            "mask_q95 is a rescaled candidate vCDR with fixed perturbations; "
            "not an independent calibrated uncertainty estimate."
        ),
        "limitations": [
            "Internal source holdout does not establish cross-camera or cross-hospital generalization.",
            "Reader difference is neither disease truth nor diagnostic accuracy.",
            "A patient bootstrap supports only exploratory within-cohort precision differences.",
            "Scores and evaluation settings are frozen from the provided source lock.",
            "Do not use internal holdout results to repeatedly tune weights or research thresholds.",
            "Unit tests use synthetic data; no real PAPILA cohort measurements are claimed.",
        ],
    }, rows


def save_source_evaluation(summary: dict, cases: list[dict], output_dir: str | Path) -> None:
    """Separate aggregate research evidence from patient/eye-indexed local data."""
    target = Path(output_dir)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError("Refusing to replace prior source research outputs")
    target.mkdir(parents=True, exist_ok=True)
    public = {key: value for key, value in summary.items() if key != "failures"}
    (target / "source_aggregate.json").write_text(
        json.dumps(public, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (target / "source_private_cases.json").write_text(
        json.dumps({"cases": cases, "failures": summary["failures"]},
                   indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    def fmt(value) -> str:
        return "N/A" if value is None else f"{value:.4f}"
    lines = [
        "# HyunOptic — PAPILA Source MASK Validation and Holdout",
        "",
        "> Internal research only. NOT independent external or clinical validation.",
        f"> Complete original PAPILA source evaluated: **{summary['full_source_holdout_scored']}**.",
        f"> Dataset partial/unverified: **{summary['partial_or_unverified']}**.",
        "",
        f"- Locked model SHA-256: `{summary['source_lock_sha256']}`",
        f"- Images analyzed in validation + holdout: **{summary['n_evaluated_images']}**",
        f"- Failed analyzed images: **{summary['n_failed']}**",
        "",
        "| Split | Score | Images | Patients | High disagreement | Precision@20% | Recall@20% | AP | ROC-AUC |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split, group in summary["evaluation"].items():
        for name in ("candidate_vcdr", "mask_q95", "combined_candidate_score"):
            metrics = group["scores"][name]
            lines.append(
                f"| {split} | {name} | {group['n_images']} | {group['n_patients']} | "
                f"{group['n_high_disagreement']} | "
                f"{fmt(metrics['review']['precision_at_budget'])} | "
                f"{fmt(metrics['review']['recall_at_budget'])} | "
                f"{fmt(metrics['ranking']['average_precision'])} | "
                f"{fmt(metrics['ranking']['roc_auc'])} |"
            )
    interval = summary["paired_patient_bootstrap_holdout"]
    lines.extend(["", "## Exploratory patient-cluster bootstrap", ""])
    if interval.get("available") is True:
        low, high = interval["delta_95_percentile_interval"]
        lines.append(
            f"Combined minus candidate-vCDR precision@budget: bootstrap mean "
            f"**{interval['delta_mean_bootstrap']:+.4f}**; "
            f"95% percentile interval **[{low:+.4f}, {high:+.4f}]**."
        )
    else:
        lines.append("Paired bootstrap unavailable for this cohort.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {entry}" for entry in summary["limitations"])
    lines.append("")
    (target / "source_summary.md").write_text("\n".join(lines), encoding="utf-8")

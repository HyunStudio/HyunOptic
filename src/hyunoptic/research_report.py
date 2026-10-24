"""Generate a cautious, data-derived Markdown research summary from a local study.

No sample data or performance values are invented. Patient-level cases are
not included in the portfolio summary. No causal or clinical claims.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def render_research_summary(manifest: dict, study_summary: dict) -> str:
    if manifest.get("project") != "HyunOptic" or study_summary.get("project") != "HyunOptic":
        raise ValueError("Expected HyunOptic run and study summaries")
    if study_summary.get("not_external_validation") is not True:
        raise ValueError("Only exploratory internal evaluation is supported")
    if not all(k in study_summary["evaluation"] for k in ("validation", "holdout")):
        raise ValueError("Missing internal evaluation partitions")
    lines = [
        "# HyunOptic — Exploratory PAPILA Measurement-Reliability Report",
        "",
        "> **Research only. Not for diagnosis, patient care or medical-device claims.**",
        "> Expert agreement is not disease truth. This internal holdout is **not external validation**.",
        "",
        "## Provenance and evaluation population",
        "",
        f"- Source: locally obtained PAPILA; expected full-archive shape matched: **{bool(manifest.get('full_published_inventory_shape_match'))}**.",
        f"- Partial/unverified sample: **{bool(manifest.get('partial_or_unverified_input'))}**.",
        f"- Images analyzed: **{manifest['n_images_with_results']}**; unique patients: **{manifest['n_patients_with_results']}**.",
        f"- Excluded by study analysis: **{manifest['n_skipped_by_study']}**.",
        f"- Protocol digest: `{manifest['study_protocol_sha256']}`",
        f"- Study JSON SHA-256: `{manifest['study_json_sha256']}`",
        "",
        "## Fixed-budget internal comparison",
        "",
        "Outcome: retrospective absolute vCDR disagreement against another expert.",
        "Candidate ranking uses only first-reader contours/image. Review quota and",
        "disagreement threshold are **research settings**, not clinical cutoffs.",
        "",
        "| Partition | Score | Images | Cases flagged | High-disagreement cases | Precision@budget | Recall@budget |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for partition in ("validation", "holdout"):
        group = study_summary["evaluation"][partition]
        for score_name in ("candidate_vcdr", "v02_q95", "combined_candidate_score"):
            data = group["scores"][score_name]
            recall = "N/A (no positive cases)" if data["recall_at_budget"] is None else f"{data['recall_at_budget']:.3f}"
            lines.append(
                f"| {partition} | {score_name} | {group['n_images']} | "
                f"{data['cases_reviewed']} | {data['n_discrepant']} | "
                f"{data['precision_at_budget']:.3f} | {recall} |"
            )
    bootstrap = study_summary.get("paired_holdout_bootstrap", {})
    lines.extend(["", "## Patient-group sensitivity of the comparison", ""])
    if bootstrap.get("available") is True:
        interval = bootstrap["delta_95_percentile_interval"]
        lines.extend([
            f"- Paired bootstrap delta in precision@budget (combined minus v02_q95): "
            f"**{bootstrap['delta_mean_bootstrap']:+.3f}**.",
            f"- Exploratory 95% percentile interval: **[{interval[0]:+.3f}, {interval[1]:+.3f}]**.",
            "- This is a resampling interval from the same internal holdout, not clinical confidence.",
        ])
    else:
        lines.append("- Paired bootstrap unavailable for this cohort.")
    lines.extend(["", "## Exploratory permutation-null diagnostics", ""])
    nulls = study_summary.get("permutation_null_holdout_exploratory", {})
    for name in ("v02_q95", "combined_candidate_score"):
        d = nulls.get(name)
        if d is not None:
            lines.append(
                f"- {name}: observed precision **{d['observed_precision_at_budget']:.3f}**, "
                f"permuted null mean **{d['null_mean_precision_at_budget']:.3f}**, "
                f"exploratory one-sided tail value **{d['one_sided_permutation_p_exploratory']:.3f}** "
                f"({d['draws']} draws, unadjusted)."
            )
    lines.extend([
        "",
        "## Interpretation boundaries",
        "",
        "1. **No clinical glaucoma detection, prognosis, or patient-safety utility is established.**",
        "2. Repeat uses of the internal holdout for design decisions invalidate confirmatory inference.",
        "3. Scores from hypothetical geometric perturbations are not calibrated reader-error probabilities.",
        "4. Camera, cohort and institution transfer require separately locked external testing.",
        "5. Negative or inconclusive performance is a valid and reportable research outcome.",
        "6. Prior methods already study CDR, inter-reader agreement and uncertainty; novelty remains unproven.",
        "",
        "## Next study",
        "",
        "Reproduce reference-reader comparisons on legally obtained data, audit exclusions,",
        "then lock one primary metric and scoring configuration before Chákṣu external evaluation.",
        "",
        "### References",
        "",
        "- PAPILA dataset descriptor: https://doi.org/10.1038/s41597-022-01388-1",
        "- Official PAPILA data: https://figshare.com/articles/dataset/PAPILA/14798004",
        "",
    ])
    return "\n".join(lines)


def write_research_summary(manifest: dict, study_summary: dict, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_research_summary(manifest, study_summary), encoding="utf-8")

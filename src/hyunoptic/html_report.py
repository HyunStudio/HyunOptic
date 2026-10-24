"""Self-contained, aggregate-only HTML research report (plan item F08).

The report reads only aggregate JSON outputs from the other HyunOptic commands.
Per-case rows, failure identifiers and file names are never rendered, and the
page states that no clinical or scientific validity is established.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from . import __version__

SCORES = ("candidate_vcdr", "mask_q95", "combined_candidate_score")
SCORE_LABELS = {
    "candidate_vcdr": "Candidate vCDR (baseline)",
    "mask_q95": "Mask Q95 sensitivity (negative control)",
    "combined_candidate_score": "Combined candidate QC score",
}
# Keys that may hold per-case identifiers in non-aggregate outputs.
_PRIVATE_KEYS = {"failures", "cases", "rows", "unusable_image_ids",
                 "duplicate_like_contour_names", "unexpected_text_filenames",
                 "missing_annotation_cases", "ambiguous_duplicate_members",
                 "suspicious_members"}

_CSS = """
:root{--bg:#ffffff;--fg:#111111;--muted:#444444;--line:#767676;--pass:#0b6b2e;
--fail:#a3150b;--warn-bg:#fff4ce;--warn-fg:#3d2c00;--head:#eef1f4}
@media (prefers-color-scheme: dark){:root{--bg:#121212;--fg:#f2f2f2;--muted:#c8c8c8;
--line:#9a9a9a;--pass:#6fdc8c;--fail:#ff8a80;--warn-bg:#3d2c00;--warn-fg:#ffe7a3;--head:#22272e}}
html{font-size:100%}
body{background:var(--bg);color:var(--fg);font:1rem/1.6 system-ui,-apple-system,"Segoe UI",
Roboto,sans-serif;margin:0 auto;max-width:72rem;padding:1rem}
h1{font-size:1.75rem;margin:.5rem 0}h2{font-size:1.35rem;margin-top:2rem;
border-bottom:2px solid var(--line)}h3{font-size:1.1rem}
.banner{background:var(--warn-bg);color:var(--warn-fg);border:2px solid currentColor;
padding:.75rem 1rem;font-weight:600}
.meta,.note{color:var(--muted)}
.table-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;margin:.5rem 0 1rem}
caption{text-align:left;font-weight:600;padding:.25rem 0}
th,td{border:1px solid var(--line);padding:.35rem .5rem;text-align:left;vertical-align:top}
thead th{background:var(--head)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.pass{color:var(--pass);font-weight:700}.fail{color:var(--fail);font-weight:700}
code{word-break:break-all}
:focus-visible{outline:3px solid var(--fg);outline-offset:2px}
"""


def _clean(data: dict | None) -> dict | None:
    """Drop keys that could carry per-case identifiers, recursively."""
    if data is None:
        return None
    def walk(value):
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items() if k not in _PRIVATE_KEYS}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value
    return walk(data)


def _num(value, digits: int = 3, signed: bool = False) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:+.{digits}f}" if signed else f"{value:.{digits}f}"
    return escape(str(value))


def _status(flag) -> str:
    """Text plus colour, so status never relies on colour alone."""
    if flag is True:
        return '<span class="pass">PASS</span>'
    if flag is False:
        return '<span class="fail">FAIL</span>'
    return "N/A"


def _table(caption: str, header: list[str], rows: list[list[str]],
           numeric: set[int] = frozenset()) -> str:
    head = "".join(f'<th scope="col">{escape(h)}</th>' for h in header)
    body = []
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i == 0:
                cells.append(f'<th scope="row">{cell}</th>')
            else:
                cls = ' class="num"' if i in numeric else ""
                cells.append(f"<td{cls}>{cell}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (f'<div class="table-wrap"><table><caption>{escape(caption)}</caption>'
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>")


def _list(items) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{escape(str(i))}</li>" for i in items) + "</ul>"


def _metric_rows(group_label: str, group: dict) -> list[list[str]]:
    rows = []
    for name in SCORES:
        if name not in group.get("scores", {}):
            continue
        review = group["scores"][name]["review"]
        rank = group["scores"][name]["ranking"]
        rows.append([
            escape(group_label), escape(SCORE_LABELS[name]),
            _num(review.get("precision_at_budget")), _num(review.get("recall_at_budget")),
            _num(rank.get("average_precision")), _num(rank.get("roc_auc")),
        ])
    return rows


def _inventory_section(inventory: dict) -> str:
    observed = inventory.get("observed", {})
    expected = inventory.get("published_expectation", {})
    rows = [
        ["Patients", _num(observed.get("patients")), _num(expected.get("patients"))],
        ["Images (eyes)", _num(observed.get("images")), _num(expected.get("eyes"))],
        ["Canonical contour files", _num(observed.get("canonical_contours")),
         _num(expected.get("contour_files"))],
        ["Unusable images", _num(observed.get("unusable_images")), "0"],
        ["Image dimension mismatches", _num(observed.get("image_dimension_mismatches")), "0"],
    ]
    return ("<h2 id=\"inventory\">PAPILA data inventory</h2>"
            f"<p>Matches complete published dataset shape: "
            f"{_status(inventory.get('matches_full_published_shape'))}</p>"
            + _table("PAPILA inventory counts", ["Item", "Observed", "Published"], rows, {1, 2}))


def _source_section(source: dict) -> str:
    parts = ["<h2 id=\"source\">PAPILA patient-disjoint source holdout (internal)</h2>",
             f"<p>Complete original source scored: "
             f"{_status(source.get('full_source_holdout_scored'))} · "
             f"Images evaluated: {_num(source.get('n_evaluated_images'))} · "
             f"Failed: {_num(source.get('n_failed'))}</p>"]
    splits = source.get("patient_split_counts", {})
    if splits:
        parts.append(_table(
            "Patient-level split (both eyes of a patient stay in one split)",
            ["Split", "Images", "Patients"],
            [[escape(k), _num(v.get("n_images")), _num(v.get("n_patients"))]
             for k, v in splits.items()], {1, 2}))
    rows = []
    for split, group in source.get("evaluation", {}).items():
        rows.extend(_metric_rows(
            f"{split} (n={group.get('n_images')}, high={group.get('n_high_disagreement')})",
            group))
    if rows:
        parts.append(_table(
            "Ranking of high expert1-vs-expert2 vCDR disagreement at the frozen review budget",
            ["Split", "Score", "Precision@budget", "Recall@budget", "AP", "ROC-AUC"],
            rows, {2, 3, 4, 5}))
    ci = source.get("paired_patient_bootstrap_holdout", {})
    if ci.get("available") is True:
        low, high = ci.get("delta_95_percentile_interval", [None, None])
        parts.append(
            "<p>Exploratory patient-cluster bootstrap, holdout precision@budget "
            f"(combined − vCDR): mean {_num(ci.get('delta_mean_bootstrap'), 4, True)}, "
            f"95% percentile interval [{_num(low, 4, True)}, {_num(high, 4, True)}].</p>")
    else:
        parts.append("<p>Paired patient-cluster bootstrap unavailable for this cohort.</p>")
    if source.get("negative_control_warning"):
        parts.append(f'<p class="note">{escape(source["negative_control_warning"])}</p>')
    parts.append("<h3>Limitations</h3>" + _list(source.get("limitations")))
    return "".join(parts)


def _audit_section(audit: dict) -> str:
    rows = [[escape(cam), _num(audit.get("readable_by_camera", {}).get(cam)),
             _num(audit.get("decode_errors_by_camera", {}).get(cam)),
             _num(audit.get("resolution_flags_by_camera", {}).get(cam))]
            for cam in audit.get("readable_by_camera", {})]
    return ("<h2 id=\"audit\">Chákṣu Test all-five-reader preflight</h2>"
            f"<p>All published Test masks structurally verified: "
            f"{_status(audit.get('all_published_test_masks_structurally_verified'))} · "
            f"Checked: {_num(audit.get('n_checked'))} · Errors: {_num(audit.get('n_errors'))}</p>"
            + _table("Readable cases by camera", ["Camera", "Readable (5 experts)",
                                                 "Decode errors", "Resolution flags"],
                     rows, {1, 2, 3}))


def _external_section(external: dict) -> str:
    parts = ["<h2 id=\"external\">Chákṣu Test external-domain analysis</h2>",
             f"<p>Complete Test layout and decoding verified: "
             f"{_status(external.get('full_layout_and_readability_verified'))} · "
             f"Images scored: {_num(external.get('n_test_images_scored'))} · "
             f"Failed: {_num(external.get('n_failed'))}</p>"]
    rows, deltas = [], []
    for camera, group in external.get("results", {}).items():
        if group.get("missing"):
            continue
        rows.extend(_metric_rows(
            f"{camera} (n={group.get('n')}, high={group.get('n_high_disagreement')})", group))
        cmp = group.get("comparison_to_vcdr_descriptive")
        if cmp:
            deltas.append([escape(camera),
                           _num(cmp.get("precision_at_review_budget_delta"), 3, True),
                           _num(cmp.get("recall_at_review_budget_delta"), 3, True),
                           _num(cmp.get("average_precision_delta"), 3, True),
                           _num(cmp.get("roc_auc_delta"), 3, True)])
    if rows:
        parts.append(_table(
            "Primary endpoint: expert1-vs-expert2 vCDR disagreement, overall and by camera",
            ["Camera", "Score", "Precision@budget", "Recall@budget", "AP", "ROC-AUC"],
            rows, {2, 3, 4, 5}))
    if deltas:
        parts.append(_table(
            "Descriptive same-image difference: combined score minus vCDR baseline",
            ["Camera", "Δ precision", "Δ recall", "Δ AP", "Δ ROC-AUC"], deltas, {1, 2, 3, 4}))
        parts.append('<p class="note">No significance test or patient-independent '
                     "interval is implied; Chákṣu patient identity is largely unknown.</p>")
    secondary = []
    for camera, group in external.get("secondary_five_reader_results", {}).items():
        if group.get("missing"):
            continue
        secondary.extend(_metric_rows(
            f"{camera} (n={group.get('n_images')}, "
            f"high={group.get('high_disagreement_with_at_least_two_of_four_peers')})", group))
    if secondary:
        parts.append(_table(
            "Secondary endpoint: expert 1 differs by >0.10 vCDR from at least 2 of experts 2–5",
            ["Camera", "Score", "Precision@budget", "Recall@budget", "AP", "ROC-AUC"],
            secondary, {2, 3, 4, 5}))
    parts.append("<h3>Limitations</h3>" + _list(external.get("limitations")))
    return "".join(parts)


def _evidence_section(evidence: dict) -> str:
    rows = [[escape(name), _status(item.get("passed")), escape(item.get("description", ""))]
            for name, item in evidence.get("checks", {}).items()]
    return ("<h2 id=\"evidence\">Evidence-package consistency gate</h2>"
            f"<p>Checks passed: {_num(evidence.get('n_passed'))} / {_num(evidence.get('n_total'))} · "
            f"Package consistent: {_status(evidence.get('all_required_artifacts_consistent'))}</p>"
            "<p><strong>Scientific validity established: No. Clinical accuracy established: "
            "No.</strong> A passing gate only means the files are mutually consistent.</p>"
            + _table("Evidence gate checks", ["Check", "Status", "Meaning"], rows)
            + "<h3>Limitations</h3>" + _list(evidence.get("limitations")))


def _pipeline_section(manifest: dict) -> str:
    rows = [[escape(step.get("name", "")), escape(step.get("status", "")),
             escape(step.get("detail", ""))]
            for step in manifest.get("steps", [])]
    return ("<h2 id=\"pipeline\">Pipeline steps</h2>"
            + _table("Steps executed by hyunoptic-pipeline", ["Step", "Status", "Detail"], rows))


def build_html_report(*, inventory: dict | None = None, source: dict | None = None,
                      audit: dict | None = None, external: dict | None = None,
                      evidence: dict | None = None, pipeline: dict | None = None,
                      generated_at: str | None = None) -> str:
    """Render whichever aggregate inputs are available; missing ones are labelled."""
    inventory, source, audit, external, evidence, pipeline = map(
        _clean, (inventory, source, audit, external, evidence, pipeline))
    stamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    partial = any(
        flag for flag in (
            inventory is not None and not inventory.get("matches_full_published_shape"),
            source is not None and source.get("partial_or_unverified", True),
            audit is not None and audit.get("partial_audit_or_unverified", True),
            external is not None and external.get("partial_or_unverified_external", True),
        )
    )
    sections, missing = [], []
    for label, data, render in (
        ("PAPILA inventory", inventory, _inventory_section),
        ("PAPILA source holdout", source, _source_section),
        ("Chákṣu preflight", audit, _audit_section),
        ("Chákṣu external analysis", external, _external_section),
        ("Evidence gate", evidence, _evidence_section),
    ):
        if data is None:
            missing.append(label)
        else:
            sections.append(render(data))
    if pipeline is not None:
        sections.append(_pipeline_section(pipeline))
    lock = (source or {}).get("source_lock_sha256") or (external or {}).get("source_lock_sha256")
    status = ('<p class="banner" role="alert">At least one input is PARTIAL or UNVERIFIED '
              "(synthetic fixture, subset or incomplete archive). Do NOT cite these numbers "
              "as validation evidence.</p>") if partial else ""
    missing_html = (f"<p><strong>Not included (not run or not supplied):</strong> "
                    f"{escape(', '.join(missing))}.</p>") if missing else ""
    lock_html = (f"<p>Frozen PAPILA model-lock SHA-256: <code>{escape(str(lock))}</code></p>"
                 if lock else "")
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<title>HyunOptic Research Report</title>"
        f"<style>{_CSS}</style></head><body><main>"
        "<h1>HyunOptic — Optic Nerve Measurement Reliability Report</h1>"
        f"<p class=\"meta\">HyunOptic {escape(__version__)} · generated {escape(stamp)} · "
        "aggregate outputs only (no per-case rows, file names or images)</p>"
        "<p class=\"banner\" role=\"note\">Research/education only. NOT for clinical use, "
        "glaucoma diagnosis or patient care. Endpoints measure disagreement between expert "
        "readers, not disease. Scientific validity and clinical accuracy are not established "
        "by this report.</p>"
        f"{status}{lock_html}{missing_html}{''.join(sections)}"
        "</main></body></html>\n"
    )


def _load(path: Path | None) -> dict | None:
    if path is None:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("project") != "HyunOptic":
        raise ValueError(f"{path} is not a HyunOptic JSON report")
    return data


def write_html_report(output: str | Path, **inputs) -> Path:
    target = Path(output)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing report: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_html_report(**inputs), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build an aggregate-only HTML research report (research only, not diagnosis)")
    p.add_argument("--papila-inventory", type=Path)
    p.add_argument("--source-aggregate", type=Path, help="source_aggregate.json")
    p.add_argument("--chaksu-audit", type=Path, help="audit_aggregate.json")
    p.add_argument("--external-aggregate", type=Path, help="external_aggregate.json")
    p.add_argument("--evidence-review", type=Path, help="evidence_review.json")
    p.add_argument("--output", type=Path, default=Path("reports/hyunoptic_report.html"))
    a = p.parse_args(argv)
    inputs = {"inventory": a.papila_inventory, "source": a.source_aggregate,
              "audit": a.chaksu_audit, "external": a.external_aggregate,
              "evidence": a.evidence_review}
    if all(v is None for v in inputs.values()):
        p.error("Pass at least one aggregate JSON")
    try:
        path = write_html_report(a.output, **{k: _load(v) for k, v in inputs.items()})
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.error(str(exc))
    print(f"HTML report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

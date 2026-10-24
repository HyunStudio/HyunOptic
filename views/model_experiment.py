"""Model Experiment (read-only): frozen evaluator reports for a trained segmentation bundle."""
from __future__ import annotations

import json

import streamlit as st

from hyunoptic.seg.bundle import HISTORY, BundleError, find_bundles, verify_bundle
from hyunoptic.seg.report import find_reports, validate_report
from hyunoptic.ui import charts
from hyunoptic.ui.components import badge, empty, fmt, html, kpi, kpi_row, note, page_title, section, table
from hyunoptic.ui.state import workspace

page_title("Model Experiment", "Frozen evaluation of the PyTorch segmentation baseline (separate from the QC study).",
           [badge("Segmentation study", "info"), badge("Research only", "warn")])
ws = workspace()
folders = find_bundles(ws.models_dir)
if not folders:
    empty("No model experiment yet", f"No trained bundle in “{ws.models_dir}”. Train and evaluate offline with "
          "`hyunoptic-seg`; nothing is shown until the evaluator has written a report.", "chart")
    st.stop()
labels = {str(f): f.name for f in folders}
chosen = st.selectbox("Model run", list(labels), format_func=lambda k: labels[k], key="me_bundle")
try:
    bundle = verify_bundle(chosen)
except BundleError as exc:
    note(f"<b>Bundle rejected.</b> {exc}", "bad")
    st.stop()
m, tr = bundle.manifest, bundle.manifest["training"]
if bundle.synthetic:
    note("<b>Synthetic-data model.</b> Every number below demonstrates the pipeline only and is not a real-data "
         "result.", "bad")
elif bundle.partial:
    note("<b>Partial data.</b> Trained on an incomplete dataset; results are exploratory.", "warn")

with st.container(border=True):
    section("Training behaviour", f"{bundle.run_id} · selection rule: {tr['selection_rule']}")
    history = json.loads((bundle.folder / HISTORY).read_text(encoding="utf-8"))
    c1, c2 = st.columns(2)
    dice_chart, loss_chart = charts.training_curves(history)
    c1.altair_chart(dice_chart, width="stretch")
    c2.altair_chart(loss_chart, width="stretch")
    st.caption(f"Best validation epoch {tr['best_epoch']} of {tr['epochs']} (score {fmt(tr['best_validation_score'])}). "
               f"Development {tr['n_images']['development']} images / {tr['n_patients']['development']} patients · "
               f"validation {tr['n_images']['validation']} / {tr['n_patients']['validation']}. "
               "Validation scores guided checkpoint selection and are not held-out estimates.")

reports = []
for path in find_reports(bundle.folder):
    try:
        reports.append((path.parent.name, validate_report(json.loads(path.read_text(encoding="utf-8")))))
    except (ValueError, OSError) as exc:
        note(f"<b>Report rejected</b> ({path.parent.name}): {exc}", "bad")
if not reports:
    empty("Holdout not evaluated yet",
          "Run  hyunoptic-seg evaluate --bundle <folder> --papila-root <PAPILA>  once. No placeholder metrics are "
          "shown before the frozen evaluator writes its report.", "lock")
    st.stop()

# Primary endpoint first: internal holdout, then exploratory reports.
reports.sort(key=lambda r: (r[1]["evaluation"] != "internal_papila_holdout", r[1]["exploratory"], r[0]))
names = [n for n, _ in reports]
pick = st.segmented_control("Report", names, default=names[0], key="me_report") or names[0]
report = dict(reports)[pick]
internal = report["evaluation"] == "internal_papila_holdout"
html(badge("Internal PAPILA holdout" if internal else "Exploratory external · Chákṣu", "info" if internal else "warn")
     + (" " + badge("Exploratory", "warn") if report["exploratory"] else "")
     + (f" <span style='color:#66768A;font-size:.85rem'>{report['exploratory_reason']}</span>"
        if report.get("exploratory_reason") else ""))
st.write("")
e1 = report["versus_expert1"]
kpi_row([
    kpi("image", "Images", f"{report['n_images']:,}",
        f"{report.get('n_patients', 'n/a')} patients" if internal else "Patients not identifiable"),
    kpi("check" if not report["n_failed"] else "alert", "Failed predictions", f"{report['n_failed']:,}",
        ", ".join(f"{k}: {v}" for k, v in report["failure_categories"].items()) or "None",
        "ok" if not report["n_failed"] else "warn"),
    kpi("target", "Median cup Dice", fmt(e1["cup_dice"].get("median")), "vs expert 1 (primary endpoint)"),
    kpi("target", "Median disc Dice", fmt(e1["disc_dice"].get("median")), "vs expert 1"),
    kpi("trend", "vCDR error > 0.10", fmt(e1.get("fraction_vcdr_error_over_threshold")),
        f"{e1['n_vcdr_error_over_threshold']} images · research threshold"),
])
st.write("")
left, right = st.columns([1.3, 1], gap="medium")
with left:
    with st.container(border=True):
        section("Dice distribution vs expert 1", "Aggregate histogram from the evaluator (no per-image data)")
        hists = {s: e1[k]["histogram"] for s, k in (("Disc", "disc_dice"), ("Cup", "cup_dice")) if "histogram" in e1[k]}
        if hists:
            st.altair_chart(charts.binned_structures(hists), width="stretch")
        rows = []
        for label, key in (("Disc Dice", "disc_dice"), ("Cup Dice", "cup_dice"), ("|vCDR error|", "abs_vcdr_error")):
            d = e1[key]
            rows.append([label, str(d.get("n", 0)), fmt(d.get("mean")), fmt(d.get("min")), fmt(d.get("q25")),
                         fmt(d.get("median")), fmt(d.get("q75")), fmt(d.get("max"))])
        table(["Metric", "n", "Mean", "Min", "Q25", "Median", "Q75", "Max"], rows, numeric={1, 2, 3, 4, 5, 6, 7})
with right:
    with st.container(border=True):
        section("Patient-grouped intervals", "Both eyes resampled together · cohort-level only")
        boot = e1.get("patient_cluster_bootstrap")
        if not boot:
            empty("No intervals", report.get("patient_linkage", "Patient linkage unavailable for this dataset."))
        else:
            table(["Mean of", "Estimate", "95% interval", "Patients"],
                  [[k.replace("_", " "), fmt(v.get("patient_weighted_mean")),
                    f"{fmt(v.get('lower_95_percentile'))} – {fmt(v.get('upper_95_percentile'))}",
                    str(v.get("n_patients", "—"))] if v.get("available", True) else [k, "N/A", v.get("reason", ""), "—"]
                   for k, v in boot.items()], numeric={1, 3})
    with st.container(border=True):
        section("Reader sensitivity", "Same frozen predictions against each expert")
        e2 = report.get("versus_expert2_sensitivity", {})
        rows = [["Model vs expert 1 (primary)", fmt(e1["disc_dice"].get("median")), fmt(e1["cup_dice"].get("median")),
                 fmt(e1["abs_vcdr_error"].get("median"))],
                ["Model vs expert 2", fmt(e2.get("disc_dice", {}).get("median")), fmt(e2.get("cup_dice", {}).get("median")),
                 fmt(e2.get("abs_vcdr_error", {}).get("median"))]]
        ctx = report.get("reader_context_expert1_vs_expert2")
        if ctx:
            rows.append(["Expert 1 vs expert 2 (context)", fmt(ctx["disc_dice"].get("median")),
                         fmt(ctx["cup_dice"].get("median")), fmt(ctx["abs_vcdr_difference"].get("median"))])
        table(["Comparison", "Median disc Dice", "Median cup Dice", "Median |ΔvCDR|"], rows, numeric={1, 2, 3})
        st.caption("Inter-expert agreement is context, not a performance ceiling; experts are references, not truth.")

if report.get("by_camera"):
    with st.container(border=True):
        section("By camera (exploratory)", "Chákṣu Test vs expert 1")
        table(["Camera", "Images", "Median disc Dice", "Median cup Dice", "Median |vCDR error|", "Share > 0.10"],
              [[cam.title(), str(v["cup_dice"].get("n", 0)), fmt(v["disc_dice"].get("median")),
                fmt(v["cup_dice"].get("median")), fmt(v["abs_vcdr_error"].get("median")),
                fmt(v.get("fraction_vcdr_error_over_threshold"))] for cam, v in report["by_camera"].items()],
              numeric={1, 2, 3, 4, 5})
st.write("")
note("<b>Limitations.</b> " + " ".join(report.get("limitations", [])))

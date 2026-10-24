"""External Validation: the PAPILA-frozen score on the Chákṣu Test set, by camera."""
import json

import pandas as pd
import streamlit as st

from hyunoptic.ui import charts
from hyunoptic.ui.components import disclaimer, empty, fmt, kpi, kpi_row, page_title, score_legend, section, table
from hyunoptic.ui.results import METRICS, partitions
from hyunoptic.ui.state import active_run, load_json_upload, partial_banner
from hyunoptic.ui.workspace import run_from_uploads

page_title("External Validation",
           "The PAPILA-frozen score applied unchanged to the Chákṣu Test set and its three cameras.")
run = active_run()
if run is None or run.external is None:
    empty("No external results",
          "Connect the original Chákṣu Test.zip and run Batch Analysis (or hyunoptic-external test), or open "
          "an existing external_aggregate.json below. Nothing is shown until real outputs exist.", "chart")
    uploaded = st.file_uploader("Open external_aggregate.json", type=["json"])
    if uploaded is None:
        st.stop()
    try:
        data = load_json_upload(uploaded)
        if not str(data.get("reference_label", "")).startswith("absolute expert1"):
            raise ValueError("Unexpected research endpoint")
        run = run_from_uploads(external=data)
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"Cannot read report: {exc}")
        st.stop()

ext = run.external
partial_banner(run)
scored, failed = ext.get("n_test_images_scored", 0), ext.get("n_failed", 0)
lock_sha = ext.get("source_lock_sha256")
expected = run.lock_sha or (run.source or {}).get("source_lock_sha256")
match = None if not expected else lock_sha == expected
verified = ext.get("full_layout_and_readability_verified") is True
kpi_row([
    kpi("database", "Scored images", f"{scored:,}", "Chákṣu Test · expert 1 masks + image only"),
    kpi("alert" if failed else "check", "Failed cases", f"{failed:,}",
        f"{failed / max(1, scored + failed):.1%} of attempted", "bad" if failed else "ok"),
    kpi("check" if verified else "alert", "Full layout verified", "Yes" if verified else "No",
        "336 images · all five readers" if verified else "Partial or unverified Test set",
        "ok" if verified else "warn"),
    kpi("lock", "Source lock match", {True: "Match", False: "Mismatch", None: "N/A"}[match],
        (lock_sha or "")[:16] + "…" if lock_sha else "No lock recorded",
        {True: "ok", False: "bad", None: ""}[match]),
])
st.write("")

show_q95 = st.toggle("Include mask Q95 negative control", value=False, key="ext_q95")
scores = ["combined_candidate_score", "candidate_vcdr"] + (["mask_q95"] if show_q95 else [])


def metric_panels(secondary: bool) -> None:
    parts = [p for p in partitions(run, secondary=secondary) if p.dataset == "Chákṣu"]
    if not parts:
        empty("No camera groups", "This report has no evaluable camera groups.")
        return
    score_legend(scores)
    for col, metric in zip(st.columns(4), METRICS):
        with col:
            data = pd.DataFrame([{"Camera": p.label.replace("Chákṣu (all)", "Overall"), "score": s,
                                  "value": p.metric(s, metric)}
                                 for p in parts for s in scores if p.metric(s, metric) is not None])
            if data.empty:
                st.caption(f"{metric}: undefined")
                continue
            st.altair_chart(charts.grouped_bars(data, group="Camera", value="value", scores=scores,
                                                title=metric, height=210, legend=False),
                            width="stretch")
    rows = [[p.label, f"{p.n_images:,}", f"{p.n_high:,}"]
            + [fmt(p.delta(m), signed=True) for m in METRICS] for p in parts]
    with st.expander("Table view and descriptive differences (combined − vCDR)"):
        table(["Camera", "Images", "High disagreement", "Δ precision", "Δ recall", "Δ AP", "Δ ROC-AUC"],
              rows, numeric={1, 2, 3, 4, 5, 6})
        st.caption("Same-image descriptive differences. No significance test; Chákṣu patient identity is "
                   "largely unknown, so images are not independent patients.")


with st.container(border=True):
    section("Primary: Expert 1 vs Expert 2 Disagreement",
            "Ranking images where |vCDR expert 1 − expert 2| > 0.10, overall and per camera")
    metric_panels(secondary=False)
with st.container(border=True):
    section("Secondary: Five-Expert Disagreement",
            "Expert 1 differs by > 0.10 vCDR from at least 2 of experts 2–5 (research rule, not consensus truth)")
    if ext.get("secondary_five_reader_results"):
        metric_panels(secondary=True)
    else:
        empty("Not in this report", "Secondary five-reader results were added in v0.9.")

with st.container(border=True):
    section("Candidate-only Feature Shift",
            "Feature distributions on Chákṣu cameras versus PAPILA (validation + holdout); no labels involved")
    ext_rows, src_rows = run.external_rows or [], run.source_rows or []
    features = {"mask_q95": "Mask Q95", "mask_roughness": "Cup roughness",
                "mask_boundary_weakness": "Boundary weakness"}
    if ext_rows:
        cols = st.columns(3)
        for col, (name, label) in zip(cols, features.items()):
            records = [{"group": "PAPILA", "Dataset": "PAPILA", "value": r[name]} for r in src_rows if name in r]
            records += [{"group": "Overall", "Dataset": "Chákṣu", "value": r[name]} for r in ext_rows]
            records += [{"group": r["camera"].title(), "Dataset": "Chákṣu", "value": r[name]} for r in ext_rows]
            with col:
                st.altair_chart(charts.feature_boxes(pd.DataFrame(records), name, title=label),
                                width="stretch")
        st.caption("Boxes show min–max whiskers, quartiles and median. A shift is a warning sign, not proof "
                   "of error, and must not be used to retune the frozen model.")
    else:
        shift = ext.get("camera_feature_shift_candidate_only", {}).get("camera_groups", {})
        if shift:
            rows = [[cam.title(), f"{g.get('n_images', 0):,}"]
                    + [fmt(g.get("features", {}).get(f, {}).get("mean_source_standardized"), 2) for f in features]
                    for cam, g in shift.items()]
            table(["Camera", "Images"] + [f"{v} (mean z)" for v in features.values()], rows,
                  numeric={1, 2, 3, 4})
            st.caption("Mean feature value in PAPILA-development standard deviations.")
        else:
            empty("No shift diagnostics", "This report predates the camera shift diagnostics.")
st.write("")
disclaimer()

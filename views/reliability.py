"""Reliability Analysis: how well candidate-only scores rank expert disagreement."""
import pandas as pd
import streamlit as st

from hyunoptic.ui import charts
from hyunoptic.ui.components import badge, empty, fmt, kpi, kpi_row, page_title, section, table
from hyunoptic.ui.results import METRICS, SCORES, partitions
from hyunoptic.ui.state import partial_banner, require_run

page_title("Reliability Analysis",
           "Do candidate-only QC scores prioritise images where two experts disagree?",
           [badge("Candidate-QC study", "neutral"), badge("Research only", "info"), badge("Not diagnostic", "warn")])
run = require_run("Reliability Analysis")
if run is None:
    st.stop()
partial_banner(run)
parts = partitions(run)
if not parts:
    empty("No evaluated partitions", "This run has no source-holdout or external results yet.", "chart")
    st.stop()

by_key = {p.key: p for p in parts}
default = "papila_holdout" if "papila_holdout" in by_key else parts[0].key
focus_key = st.segmented_control("Partition", list(by_key), default=default,
                                 format_func=lambda k: by_key[k].label, key="rel_focus") or default
focus = by_key[focus_key]
budget = (run.lock or {}).get("model", {}).get("review_fraction", 0.2)


def delta_text(metric: str) -> str:
    d = focus.delta(metric)
    if d is None:
        return "Δ vs vCDR: N/A"
    arrow = "▲" if d > 0 else ("▼" if d < 0 else "■")
    return f"{arrow} {d:+.3f} vs vCDR baseline"


diffs = focus.differences
ci = (run.source or {}).get("paired_patient_bootstrap_holdout", {}) if focus_key == "papila_holdout" else {}
ci_text, ci_sub = "N/A", "Patient bootstrap only for PAPILA holdout"
if ci.get("available"):
    lo, hi = ci["delta_95_percentile_interval"]
    ci_text, ci_sub = f"{lo:+.3f} – {hi:+.3f}", "Δ precision (combined − vCDR), 95% percentile"
kpi_row([
    kpi("target", f"Precision@{budget:.0%}", fmt(focus.metric("combined_candidate_score", "Precision@budget")),
        "Combined QC score", delta=delta_text("Precision@budget")),
    kpi("chart", f"Recall@{budget:.0%}", fmt(focus.metric("combined_candidate_score", "Recall@budget")),
        "Combined QC score", delta=delta_text("Recall@budget")),
    kpi("file", "Average precision", fmt(focus.metric("combined_candidate_score", "Average precision")),
        "Precision–recall AUC", delta=delta_text("Average precision")),
    kpi("trend", "ROC-AUC", fmt(focus.metric("combined_candidate_score", "ROC-AUC")),
        "Ranking of high disagreement", delta=delta_text("ROC-AUC")),
    kpi("users", "Mean |ΔvCDR|", fmt(float(diffs.mean())) if diffs.size else "N/A",
        f"Expert 1 vs 2 · {focus.n_high} of {focus.n_images} > 0.10"),
    kpi("interval", "Bootstrap interval", ci_text, ci_sub, small=True),
])
st.caption(f"Focus: {focus.label}. Endpoint: |vCDR expert 1 − expert 2| > 0.10 (research threshold). "
           "Deltas are descriptive, not significance tests.")
st.write("")

left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True):
        section("Precision–Recall Curve", f"{focus.label} · review images in descending score order")
        if focus.rows and focus.labels().any():
            curves = {s: charts.pr_points(focus.score_values(s), focus.labels()) for s in SCORES}
            st.altair_chart(charts.precision_recall(curves, prevalence=float(focus.labels().mean())),
                            width="stretch")
            st.caption("Dashed grey line: chance level (share of high-disagreement images).")
        else:
            empty("Curve unavailable", "Needs local per-image results with at least one high-disagreement "
                  "image (private case files stay on this computer).")
with right:
    with st.container(border=True):
        head, pick = st.columns([2, 1], vertical_alignment="center")
        with head:
            section("Metric Comparison by Partition", "Same frozen scores on every partition")
        with pick:
            metric = st.selectbox("Metric", list(METRICS), index=2, key="rel_metric",
                                  label_visibility="collapsed")
        data = pd.DataFrame([{"Partition": p.label, "score": s, "value": p.metric(s, metric)}
                             for p in parts for s in SCORES if p.metric(s, metric) is not None])
        if data.empty:
            empty("No values", f"{metric} is undefined for these partitions.")
        else:
            st.altair_chart(charts.grouped_bars(data, group="Partition", value="value", scores=list(SCORES),
                                                height=300), width="stretch")

left, right = st.columns([1, 1.25], gap="medium")
with left:
    with st.container(border=True):
        section("Reader Disagreement Distribution", f"{focus.label} · absolute vCDR difference between experts")
        if diffs.size:
            st.altair_chart(charts.histogram(diffs, threshold=0.10), width="stretch")
            st.caption(f"Mean {diffs.mean():.3f} · median {pd.Series(diffs).median():.3f} · "
                       f"95th percentile {pd.Series(diffs).quantile(.95):.3f} · n = {diffs.size}")
        else:
            empty("No per-image differences", "Local per-image results are not available for this partition.")
with right:
    with st.container(border=True):
        section("Metrics by Partition", "Combined QC score; baseline values in parentheses")
        rows = []
        for p in parts:
            def pair(m, p=p):
                return f"{fmt(p.metric('combined_candidate_score', m))} ({fmt(p.metric('candidate_vcdr', m))})"
            d = p.differences
            rows.append([p.label, f"{p.n_images:,}", f"{p.n_high:,}", pair("Precision@budget"),
                         pair("Recall@budget"), pair("Average precision"), pair("ROC-AUC"),
                         fmt(float(d.mean())) if d.size else "N/A"])
        table(["Partition", "Images", "High", f"P@{budget:.0%}", f"R@{budget:.0%}", "AP", "ROC-AUC", "Mean |Δ|"],
              rows, numeric={1, 2, 3, 4, 5, 6, 7},
              highlight={i for i, p in enumerate(parts) if p.key == focus_key})
        st.caption("Chákṣu patients are largely unidentifiable, so no patient-level intervals are given there.")

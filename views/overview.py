"""Research Overview: dataset status, analysis progress and key results at a glance."""
import streamlit as st

from hyunoptic.ui.components import empty, fmt, html, kpi, kpi_row, note, page_title, section, step, table
from hyunoptic.ui.results import STEP_TITLES, STEP_TONE, partitions
from hyunoptic.ui.review import review_workspace
from hyunoptic.ui.state import active_run, available_datasets, datasets

page_title("Research Overview", "Dataset status, analysis progress, and key results at a glance.")
papila, chaksu = datasets()
connected = [s for s in (papila, chaksu) if s.connected]
run = active_run()

if run is None:
    status, status_sub, tone = "Not run", "Start a run in Batch Analysis", "warn"
elif run.evidence and run.evidence.get("all_required_artifacts_consistent"):
    status, status_sub, tone = "Package consistent", "All evidence checks passed · not clinical validation", "ok"
elif run.partial:
    status, status_sub, tone = "Partial", "Subset or synthetic data · not evidence", "warn"
else:
    status, status_sub, tone = "Complete", "Model locked · evidence gate pending", "ok"

experts = " · ".join(f"{s.n_experts}" for s in (papila, chaksu) if s.connected) or "—"
kpi_row([
    kpi("database", "Datasets connected", f"{len(connected)} of 2",
        " · ".join(s.name for s in connected) or "Connect on the Datasets page"),
    kpi("image", "Total images", f"{sum(s.n_images for s in connected):,}",
        " · ".join(f"{s.n_images:,} ({s.name})" for s in connected) or "No local data"),
    kpi("users", "Expert readers", experts,
        " · ".join(f"{s.name}" for s in connected) or "PAPILA 2 · Chákṣu 5 when connected"),
    kpi("trend", "Analysis status", status, status_sub, tone),
])
st.write("")
if available_datasets() == ["Synthetic demo"]:
    note("No dataset is connected yet, so the viewer shows synthetic demo geometry (not patient data). "
         "Add your local PAPILA folder and Chákṣu <code>Test.zip</code> on the <b>Datasets</b> page.")
    st.write("")

review_workspace("ov", default_mode="Side by side", compact=True)

st.write("")
left, right = st.columns([1, 1.4], gap="medium")
with left:
    with st.container(border=True):
        section("Latest analysis run", run.label if run else "")
        if run is None or not run.manifest:
            empty("No run yet", "Batch Analysis runs inventory → freeze → source holdout → external test → "
                  "evidence gate → report in one go.", "chart")
        else:
            html("".join(step(STEP_TONE.get(s["status"], ""), STEP_TITLES.get(s["name"], s["name"]),
                              s.get("detail", "")[:110], s["status"]) for s in run.manifest.get("steps", [])))
with right:
    with st.container(border=True):
        section("Key results", "Combined QC score vs vCDR baseline at the frozen review budget "
                "(reader-disagreement ranking, not diagnosis)")
        parts = partitions(run) if run else []
        if not parts:
            empty("No results to show", "Results appear here after a run produces source-holdout or "
                  "external aggregates.", "chart")
        else:
            rows = [[p.label, f"{p.n_images:,}", f"{p.n_high:,}",
                     fmt(p.metric("combined_candidate_score", "Average precision")),
                     fmt(p.metric("candidate_vcdr", "Average precision")),
                     fmt(p.delta("Average precision"), signed=True)] for p in parts]
            table(["Partition", "Images", "High disagreement", "AP combined", "AP vCDR", "Δ AP"],
                  rows, numeric={1, 2, 3, 4, 5})
            if run.partial:
                st.caption("⚠ Partial or unverified run — do not cite these numbers.")

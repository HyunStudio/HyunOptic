"""Model Settings: inspect the frozen model lock of the active run (read-only)."""
import streamlit as st

from hyunoptic.mask_features import MASK_FEATURES
from hyunoptic.ui.components import badge, empty, fmt, hash_card, html, kpi, kpi_row, note, page_title, section, table
from hyunoptic.ui.state import require_run, workspace

page_title("Model Settings", "The frozen candidate-only scoring model. Locks are read-only by design.",
           [badge("Frozen", "info")])
run = require_run("Model Settings")
if run is None:
    st.stop()
if not run.lock:
    empty("No model lock in this run", "The freeze step did not complete for the selected run.")
    st.stop()
model = run.lock["model"]
kpi_row([
    kpi("lock", "Method", model.get("method", "—"), f"Lock version {model.get('lock_version', '—')}", small=True),
    kpi("users", "Development images", f"{model.get('n_development_images', 0):,}",
        "Expert 1 only; no outcome labels"),
    kpi("target", "Review budget", f"{model.get('review_fraction', 0):.0%}", "Fixed before evaluation"),
    kpi("alert", "Disagreement threshold", fmt(model.get("research_disagreement_threshold"), 2),
        "Research setting, not clinical"),
])
st.write("")
left, right = st.columns([1.4, 1], gap="medium")
with left:
    with st.container(border=True):
        section("Feature scaler", "Mean and SD fitted on PAPILA development patients; score = 3 + mean(clipped z)")
        table(["Feature", "Mean", "SD"],
              [[n, fmt(model["scaler"][n]["mean"], 5), fmt(model["scaler"][n]["sd"], 5)] for n in MASK_FEATURES],
              numeric={1, 2})
    with st.container(border=True):
        section("Perturbation settings", "Assumed log-normal boundary scaling used by the Q95 feature")
        p = model.get("perturbation", {})
        table(["Setting", "Value"], [[k, str(v)] for k, v in p.items()])
with right:
    with st.container(border=True):
        section("Lock identity")
        html(hash_card("lock", "Model lock SHA-256", run.lock.get("sha256"), [
            ("Split", model.get("split_method", "—")), ("Split seed", str(model.get("split_seed", "—"))),
            ("Candidate reader", model.get("candidate_reader", "—")),
            ("Complete source", "Yes" if model.get("source_complete_inventory") else "No (partial)")]))
        st.write("")
        html(hash_card("file", "Source content SHA-256", model.get("source_content_sha256"),
                       [("Target", model.get("target_definition", "—"))]))
    ws = workspace()
    note(f"New runs use seed <b>{ws.seed}</b>, <b>{ws.draws}</b> perturbation draws and <b>{ws.bootstrap_draws}"
         "</b> bootstrap draws (change them in Batch Analysis). Editing a lock is deliberately impossible: "
         "re-freezing after seeing results would break the protocol.")

"""Read-only external-domain research metrics; never generates clinical claims."""
from __future__ import annotations
import json
import streamlit as st

st.set_page_config(page_title="HyunOptic | External Dataset", page_icon="🌐", layout="wide")
st.title("HyunOptic — Chákṣu External-Domain Evaluation")
st.caption("v0.7 · PAPILA source-frozen → Chákṣu Test · research only")
st.warning("Inter-reader disagreement is NOT glaucoma diagnosis or clinical validation.")

uploaded = st.file_uploader("Open local external_aggregate.json", type=["json"])
if uploaded is None:
    st.info("No external results loaded. Freeze a PAPILA model, then analyze original Chákṣu Test.zip.")
    st.stop()

try:
    summary = json.load(uploaded)
    if summary.get("project") != "HyunOptic" or summary.get("version") != "0.7.0":
        raise ValueError("Expected a HyunOptic v0.7 external report")
    if summary.get("reference_label", "").startswith("absolute expert1") is not True:
        raise ValueError("Unexpected research endpoint")
    groups = summary["results"]
except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
    st.error(f"Cannot interpret the report: {exc}")
    st.stop()

if summary.get("partial_or_unverified_external", True):
    st.error("The uploaded report comes from a partial or unverified test set. Do NOT cite as external-validation evidence.")

col1,col2,col3 = st.columns(3)
col1.metric("Scored images", int(summary["n_test_images_scored"]))
col2.metric("Failed annotations", int(summary["n_failed"]))
col3.metric("Full published Test verified", "Yes" if summary["full_layout_and_readability_verified"] else "No")
st.caption("Score source was frozen on the PAPILA development subset before Chákṣu analysis.")
st.code(summary["source_lock_sha256"], language=None)

data = []
for camera, group in groups.items():
    if group.get("missing"):
        continue
    for score in ("candidate_vcdr", "mask_q95", "combined_candidate_score"):
        item = group["scores"][score]
        review = item["review"]
        rank = item["ranking"]
        data.append({
            "Camera": camera,
            "QC score": score,
            "Images": int(group["n"]),
            "High expert-disagreement": int(group["n_high_disagreement"]),
            "Precision@20%": round(review["precision_at_budget"], 4),
            "Recall@20%": None if review["recall_at_budget"] is None else round(review["recall_at_budget"], 4),
            "Average precision": None if rank["average_precision"] is None else round(rank["average_precision"], 4),
            "ROC AUC": None if rank["roc_auc"] is None else round(rank["roc_auc"], 4),
        })
st.subheader("Fixed protocol: Overall and by camera")
st.dataframe(data, use_container_width=True, hide_index=True)
st.caption("AP and ROC AUC refer only to expert1–expert2 vCDR disagreement, not diagnostic outcomes.")
with st.expander("Method limitations"):
    for issue in summary.get("limitations", []):
        st.write("- " + issue)

"""Read-only external-domain research metrics; never generates clinical claims."""
from __future__ import annotations
import json
import streamlit as st

st.set_page_config(page_title="HyunOptic | External Dataset", page_icon="🌐", layout="wide")
st.title("HyunOptic — Chákṣu External-Domain Evaluation")
st.caption("v0.8 · PAPILA source-frozen → Chákṣu Test · research only")
st.warning("Inter-reader disagreement is NOT glaucoma diagnosis or clinical validation.")

uploaded = st.file_uploader("Open local external_aggregate.json", type=["json"])
if uploaded is None:
    st.info("No external results loaded. Freeze a PAPILA model, then analyze original Chákṣu Test.zip.")
    st.stop()

try:
    summary = json.load(uploaded)
    if summary.get("project") != "HyunOptic" or summary.get("version") not in ("0.7.0", "0.8.0", "0.9.0"):
        raise ValueError("Expected a HyunOptic v0.7–v0.9 external report")
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
if summary.get("version") in ("0.8.0", "0.9.0"):
    st.subheader("Descriptive difference from vCDR-only ranking")
    st.caption("Paired image-level descriptive comparison ONLY; no patient-independent statistical inference.")
    for camera, group in groups.items():
        delta = group.get("comparison_to_vcdr_descriptive", {})
        if "precision_at_review_budget_delta" in delta:
            st.write(f"**{camera}**: precision@budget difference = {delta['precision_at_review_budget_delta']:+.3f}")
with st.expander("Method limitations"):
    for issue in summary.get("limitations", []):
        st.write("- " + issue)

if summary.get("version") == "0.9.0":
    st.divider()
    st.subheader("Secondary: Five-expert measurement disagreement")
    st.info(
        "This SECONDARY analysis tests whether the candidate first expert disagrees "
        "with at least 2 of 4 other experts by more than the research vCDR threshold. "
        "It is NOT a glaucoma diagnosis or expert-voted clinical ground truth."
    )
    peers = summary.get("secondary_five_reader_results", {})
    peer_rows = []
    for cam, details in peers.items():
        if details.get("missing"):
            continue
        for name in ("candidate_vcdr", "combined_candidate_score"):
            evaluation = details["scores"][name]
            peer_rows.append({
                "Camera": cam,
                "Score": name,
                "Images": details["n_images"],
                "At least 2 of 4 peers disagree": details["high_disagreement_with_at_least_two_of_four_peers"],
                "Precision@review": round(evaluation["review"]["precision_at_budget"], 4),
                "Average precision": None if evaluation["ranking"]["average_precision"] is None
                                     else round(evaluation["ranking"]["average_precision"], 4),
            })
    st.dataframe(peer_rows, use_container_width=True, hide_index=True)
    st.caption("No patient-level confidence interval or clinical performance inference is claimed.")

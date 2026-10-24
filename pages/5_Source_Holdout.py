"""Read-only PAPILA internal mask holdout dashboard.

Contains NO synthetic performance numbers or clinical diagnosis claims.
Requires locally generated source_aggregate.json.
"""
from __future__ import annotations
import json
import streamlit as st

st.set_page_config(page_title="HyunOptic | Source Holdout", page_icon="📋", layout="wide")
st.title("HyunOptic — PAPILA Source MASK Holdout")
st.warning(
    "Internal expert measurement-consistency analysis only. Not external "
    "validation, glaucoma diagnosis or clinical acceptance evidence."
)
file = st.file_uploader(
    "Open source_aggregate.json from hyunoptic-source-check",
    type=["json"],
)
if file is None:
    st.info(
        "No source evaluation loaded. Freeze the PAPILA development-only model, "
        "then run hyunoptic-source-check on that SAME dataset."
    )
    st.stop()
try:
    body = json.load(file)
    if body.get("project") != "HyunOptic" or body.get("version") != "1.0.0rc3":
        raise ValueError("Expected a HyunOptic rc3 source holdout report")
    if body.get("not_external_validation") is not True:
        raise ValueError("Missing internal-research disclaimer")
    cohorts = body["evaluation"]
except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
    st.error(f"Invalid source validation report: {exc}")
    st.stop()

if body.get("partial_or_unverified", True):
    st.error("Partial/unverified source input: do not publish as a full-PAPILA research result.")

a, b, c = st.columns(3)
a.metric("Discovered source eyes", int(body["n_source_images_discovered"]))
b.metric("Analyzed validation + holdout eyes", int(body["n_evaluated_images"]))
c.metric("Failed evaluated eyes", int(body["n_failed"]))

table = []
for split, group in cohorts.items():
    for name in ("candidate_vcdr", "mask_q95", "combined_candidate_score"):
        rank = group["scores"][name]["ranking"]
        review = group["scores"][name]["review"]
        table.append({
            "Partition": split,
            "Score": name,
            "Eyes": group["n_images"],
            "Patients": group["n_patients"],
            "High disagreement": group["n_high_disagreement"],
            "Precision@budget": round(review["precision_at_budget"], 4),
            "Recall@budget": None if review["recall_at_budget"] is None
                             else round(review["recall_at_budget"], 4),
            "Average precision": None if rank["average_precision"] is None
                                 else round(rank["average_precision"], 4),
            "ROC AUC": None if rank["roc_auc"] is None
                       else round(rank["roc_auc"], 4),
        })
st.subheader("Same mask features to be used on Chákṣu")
st.dataframe(table, use_container_width=True, hide_index=True)
st.caption("The second reader is a retrospective disagreement target, not medical ground truth.")
with st.expander("Paired patient-bootstrap — combined score minus plain vCDR"):
    st.json(body["paired_patient_bootstrap_holdout"])
with st.expander("Reproducibility"):
    st.code(body["source_lock_sha256"], language=None)
    st.code(body["source_content_sha256"], language=None)
    st.json(body["patient_split_counts"])
    for caution in body.get("limitations", []):
        st.write("- " + caution)

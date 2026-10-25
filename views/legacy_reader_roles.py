"""Read-only v0.6 bidirectional reader audit viewer.

No measured results exist until the user supplies a local JSON report.
"""
import json
import streamlit as st

st.title("HyunOptic — Reader-Role Sensitivity")
st.caption("v0.6 · exploratory internal reliability analysis")
st.warning("Research only. Agreement between experts does not establish glaucoma diagnosis or clinical correctness.")

source = st.file_uploader(
    "Open the reader_symmetry.json produced by hyunoptic-reader-check",
    type=["json"],
)
if source is None:
    st.info("No reader-role audit loaded. Run hyunoptic-reader-check on a locally obtained PAPILA archive.")
    st.stop()

try:
    payload = json.load(source)
    body = payload["summary"]
    if (body.get("project") != "HyunOptic" or body.get("version") != "0.6.0"
        or body.get("not_external_validation") is not True):
        raise ValueError("Expected internal reader-role sensitivity v0.6 report")
    evaluation = body["evaluation"]
except (ValueError, KeyError, TypeError, json.JSONDecodeError) as err:
    st.error(f"Invalid report: {err}")
    st.stop()

a, b, c = st.columns(3)
a.metric("Analyzed images", int(body["n_images_analyzed"]))
b.metric("Patients", int(body["n_patients_analyzed"]))
c.metric("Skipped cases", int(body["n_images_skipped"]))
if body.get("partial_or_unverified_input", True):
    st.warning("Dataset inventory was partial or unverified; do not present as a full PAPILA result.")

split = st.radio("Evaluation subset", ["validation", "holdout"], horizontal=True, index=1)
table = []
for reader in ("exp1", "exp2"):
    for name in ("candidate_vcdr", "v02_q95", "combined_candidate_score"):
        values = evaluation[split][reader]["scores"][name]
        r, k = values["review"], values["ranking"]
        table.append({
            "Candidate reader": reader,
            "Score": name,
            "N images": int(r["n_cases"]),
            "High-disagreement": int(r["n_discrepant"]),
            "Precision@budget": round(r["precision_at_budget"], 4),
            "Recall@budget": None if r["recall_at_budget"] is None else round(r["recall_at_budget"], 4),
            "Average precision": None if k["average_precision"] is None else round(k["average_precision"], 4),
            "ROC AUC": None if k["roc_auc"] is None else round(k["roc_auc"], 4),
        })
st.subheader("Same images, reversed expert roles")
st.dataframe(table, width="stretch", hide_index=True)
st.caption("AP/ROC AUC refer to inter-reader disagreement, NOT glaucoma diagnosis.")
st.subheader("Reader-role ranking stability")
for name, info in evaluation[split]["reader_role_agreement"].items():
    st.write(f"**{name}** — top-budget overlap "
             f"{info['top_k_overlap_count']}/{info['reviewed_per_direction']} "
             f"({info['top_k_overlap_fraction']:.1%})")
with st.expander("Descriptive Bland–Altman agreement"):
    agreement = evaluation[split].get("bland_altman_inter_reader")
    if agreement and agreement.get("available") is not False:
        st.write({
            "Signed bias exp1 − exp2": agreement["signed_bias"],
            "Lower normal-theory LOA": agreement["limits_of_agreement_lower"],
            "Upper normal-theory LOA": agreement["limits_of_agreement_upper"],
            "Patients": agreement["n_patients"],
            "Images": agreement["n_images"],
        })
        st.caption("Repeated bilateral eyes may be correlated; interval resampling is by patient. "
                   "Normal-theory LOA are descriptive and not clinically accepted limits.")
    else:
        st.info("Agreement interval unavailable for this split (insufficient independent patients).")
with st.expander("Protocol and cautions"):
    st.code(body["protocol_sha256"], language=None)
    st.json(body["protocol_settings"])
    for limitation in body.get("caveats", []):
        st.write("- " + limitation)

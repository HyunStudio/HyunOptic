"""Read-only dataset inventory viewer. No patient images or clinical records."""
from __future__ import annotations
import json
import streamlit as st

st.set_page_config(page_title="HyunOptic | Dataset Quality", page_icon="🧪", layout="wide")
st.title("HyunOptic — PAPILA Dataset Integrity")
st.caption("v0.4 · Research-only inventory viewer")
st.warning("Dataset completeness and coordinate checks do not establish clinical correctness.")

file = st.file_uploader("Open inventory JSON generated locally by hyunoptic-inventory", type=["json"])
if file is None:
    st.info("No inventory loaded. Run hyunoptic-inventory on your local PAPILA folder.")
    st.stop()
try:
    doc = json.load(file)
    if doc.get("project") != "HyunOptic" or doc.get("source", "").split(";")[0] != "PAPILA local inventory":
        raise ValueError("Expected HyunOptic PAPILA inventory JSON")
    obs = doc["observed"]
    expected = doc["published_expectation"]
    cases = doc["cases"]
except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
    st.error(f"Invalid inventory: {exc}")
    st.stop()

st.subheader("Observed vs published archive")
cols = st.columns(4)
cols[0].metric("Patients", f"{obs['patients']} / {expected['patients']}")
cols[1].metric("Images", f"{obs['images']} / {expected['eyes']}")
cols[2].metric("Canonical contours", f"{obs['canonical_contours']} / {expected['contour_files']}")
cols[3].metric("Unusable image pairs", str(obs["unusable_images"]))
st.write("**Exact full published shape match:**", bool(doc["matches_full_published_shape"]))
st.caption("A match in file counts does not confirm content authenticity; this page does not read raw images.")

quality = [
    {
        "image ID": item.get("image_id", ""),
        "eye": item.get("eye", ""),
        "contour files": int(item.get("annotation_files_present", 0)),
        "errors": "; ".join(item.get("errors", [])),
        "warnings": "; ".join(item.get("warnings", [])),
    }
    for item in cases if item.get("errors") or item.get("warnings")
]
if quality:
    st.subheader("Cases requiring inspection")
    st.dataframe(quality, use_container_width=True, hide_index=True)
else:
    st.success("No reported case-level structural issues in this inventory.")
with st.expander("Duplicate and unrecognized annotation filenames"):
    st.write("**Duplicate-like TXT files**", doc.get("duplicate_like_contour_names", []))
    st.write("**Unexpected TXT filenames**", doc.get("unexpected_text_filenames", []))
with st.expander("Reproducibility fingerprint and limitations"):
    st.code(str(doc.get("inventory_sha256_of_paths_and_sizes_only")), language=None)
    st.warning("Fingerprint covers file PATHS and FILE SIZES only; it is NOT a file-content hash.")
    for limitation in doc.get("limitations", []):
        st.write("- " + str(limitation))

"""HyunOptic MVP Streamlit viewer; local research data only."""
from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import streamlit as st

from hyunoptic.measure import compare_readers, measure_contours
from hyunoptic.papila import discover_cases, load_contours, load_image
from hyunoptic.viz import optic_crop, overlay_contours

st.set_page_config(page_title="HyunOptic — Research Prototype", page_icon="🔬", layout="wide")
st.title("HyunOptic")
st.caption("Quantitative optic nerve measurement · Research-only prototype v0.1")
st.warning("Research/education only — NOT a glaucoma diagnostic tool or a medical device.")


def example() -> tuple[Image.Image, dict]:
    """Artificial geometry, never represented as an actual retinal image or patient."""
    w = h = 640
    img = Image.new("RGB", (w, h), "#151f29")
    draw = ImageDraw.Draw(img)
    draw.ellipse((100, 100, 540, 540), fill="#384654")
    draw.ellipse((175, 120, 470, 510), fill="#c79869")
    draw.ellipse((258, 220, 405, 408), fill="#e5bd8a")
    def ellipse_points(cx, cy, rx, ry, shift=0):
        theta = np.linspace(0, 2 * np.pi, 80, endpoint=False)
        return np.column_stack((cx + shift + rx * np.cos(theta), cy + ry * np.sin(theta)))
    first_d = ellipse_points(322, 316, 153, 197)
    first_c = ellipse_points(333, 311, 78, 97)
    second_d = ellipse_points(322, 316, 150, 194, 3)
    second_c = ellipse_points(333, 311, 82, 92, 2)
    return img, {"exp1": (first_d, first_c), "exp2": (second_d, second_c)}


@st.cache_data(show_spinner=False)
def cached_cases(path_str: str):
    return discover_cases(path_str)


with st.sidebar:
    st.header("Dataset")
    data_source = st.radio("Input source", ["Synthetic demo", "Local PAPILA folder"], index=0)
    if data_source == "Local PAPILA folder":
        root = st.text_input("PAPILA directory", value="data/PAPILA_DBv1")
        st.caption("Dataset remains on your computer; this app does not upload it.")
    selected_expert = st.selectbox("Overlay annotation", ["exp1", "exp2"])
    zoom = st.toggle("Crop around optic disc", value=True)

if data_source == "Synthetic demo":
    img, pair = example()
    case_name = "SYNTHETIC (NOT PATIENT DATA)"
else:
    try:
        cases = cached_cases(str(Path(root).expanduser().resolve()))
        if not cases:
            st.error("No complete PAPILA image/annotation pairs found. Check your directory layout.")
            st.stop()
        ids = [c.image_id for c in cases]
        selected_id = st.selectbox("PAPILA case", ids)
        case = cases[ids.index(selected_id)]
        img = load_image(case)
        pair = {expert: load_contours(case, expert) for expert in ("exp1", "exp2")}
        case_name = case.image_id
    except (OSError, ValueError) as exc:
        st.error(f"Could not load PAPILA data: {exc}")
        st.stop()

size = img.size
try:
    result = compare_readers(*pair["exp1"], *pair["exp2"], size)
    selected_disc, selected_cup = pair[selected_expert]
    view = overlay_contours(img, selected_disc, selected_cup, line_width=max(2, img.width // 500))
    if zoom:
        view = optic_crop(view, selected_disc)
except ValueError as exc:
    st.error(f"Annotation geometry error: {exc}")
    st.stop()

st.subheader(f"Image: {case_name}")
m = result[selected_expert]
for col, (name, value) in zip(st.columns(4), [
    ("Vertical CDR", m["vertical_cdr"]), ("Horizontal CDR", m["horizontal_cdr"]),
    ("Area CDR", m["area_cdr"]), ("Reader |ΔvCDR|", result["absolute_vcdr_difference"]),
]):
    col.metric(name, f"{value:.3f}")

left, right = st.columns([3, 2])
with left:
    st.image(view, caption="Cyan: disc contour · Coral: cup contour; contours belong to selected reader", use_container_width=True)
with right:
    st.subheader("Independent reader agreement")
    st.write({"disc Dice": round(result["disc_dice"], 4), "cup Dice": round(result["cup_dice"], 4)})
    st.dataframe([
        {"reader": label, "vCDR": round(result[label]["vertical_cdr"], 4),
         "hCDR": round(result[label]["horizontal_cdr"], 4),
         "aCDR": round(result[label]["area_cdr"], 4)}
        for label in ("exp1", "exp2")
    ], use_container_width=True, hide_index=True)
    for expert in ("exp1", "exp2"):
        for warning in result[expert]["warnings"]:
            st.warning(f"{expert}: {warning}")
    st.caption("This retrospective agreement is NOT a reference-free uncertainty score or diagnostic result.")

payload = {"project": "HyunOptic", "status": "research-only", "image_id": case_name,
           "image_size": list(size), "reader_comparison": result}
st.download_button("Download measurement JSON", data=json.dumps(payload, indent=2),
                   file_name=f"hyunoptic_{case_name}.json", mime="application/json")
byte_buf = io.BytesIO()
view.save(byte_buf, format="PNG")
st.download_button("Download displayed overlay PNG", data=byte_buf.getvalue(),
                   file_name=f"hyunoptic_{case_name}_overlay.png", mime="image/png")

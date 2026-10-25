"""Model Inference (experimental): image-only optic disc/cup prediction from a verified local bundle."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st
from PIL import Image

from hyunoptic.measure import dice, measure_masks
from hyunoptic.seg import RESEARCH_THRESHOLD, torch_available
from hyunoptic.seg.bundle import BundleError, find_bundles, verify_bundle
from hyunoptic.ui.components import (badge, empty, fmt, html, kpi, kpi_row, kv, line_legend, note, page_title,
                                     section, stat, table)
from hyunoptic.ui.state import _mtime, available_datasets, case_data, cases, dataset_location, save_workspace, workspace

DOCS = "https://github.com/HyunStudio/HyunOptic/blob/main/docs/V10_RUNBOOK.md#8-experimental-pytorch-segmentation"
page_title("Model Inference", "Image-only optic disc and cup prediction from a verified local model.",
           [badge("Research only · experimental", "warn")])
note("Runs on this computer only. Images, masks and identifiers are not sent anywhere. Predictions are research "
     "outputs, not a diagnosis or glaucoma risk score.")
st.write("")

ws = workspace()
with st.expander("Model folder", icon=":material/folder_open:"):
    folder = st.text_input("Folder containing trained bundles", ws.models_dir, key="mi_models_dir",
                           help="Each bundle is a folder made by `hyunoptic-seg train`.")
    if st.button("Save folder", key="mi_save") and folder.strip() != ws.models_dir:
        ws.models_dir = folder.strip()
        save_workspace(ws)
        st.rerun()

if not torch_available():
    empty("PyTorch is not installed — inference is unavailable",
          "Install the optional extra with  pip install -e \".[ml]\"  and restart. Every other page works "
          "without it.", "info")
    st.stop()
folders = find_bundles(ws.models_dir)
if not folders:
    empty("No verified local model loaded. Inference is unavailable.",
          f"Train a bundle offline with `hyunoptic-seg train` into “{ws.models_dir}/<name>”. The app never "
          "trains or downloads models.", "lock")
    st.link_button("Training and evaluation instructions", DOCS, icon=":material/menu_book:")
    st.stop()

labels = {str(f): f.name for f in folders}
chosen = st.selectbox("Approved local run", list(labels), format_func=lambda k: labels[k], key="mi_bundle")
try:
    bundle = verify_bundle(chosen)
except BundleError as exc:
    note(f"<b>Bundle rejected.</b> {escape(str(exc))}", "bad")
    st.stop()

m = bundle.manifest
tr = m["training"]
kpi_row([
    kpi("lock", "Run", bundle.run_id, f"{m['architecture']['name']} · {m['preprocessing']['image_size']} px", small=True),
    kpi("fingerprint", "Weights SHA-256", bundle.weights_sha256[:12] + "…", "Verified against manifest", "ok", small=True),
    kpi("database", "Training data", f"{tr['dataset']} · {tr['reader']}",
        f"{tr['n_images']['development']} dev · {tr['n_images']['validation']} val images", small=True),
    kpi("target", "Selection (validation)", fmt(tr["best_validation_score"]),
        f"Best epoch {tr['best_epoch']} · not a held-out result", small=True),
])
if bundle.synthetic:
    note("<b>Synthetic-data model.</b> Trained on generated demo images: this demonstrates mechanics and layout "
         "only. It is not a trained-model result on real data.", "bad")
elif bundle.partial:
    note("<b>Partial / exploratory model.</b> Trained on an incomplete dataset; outputs are exploratory.", "warn")
st.write("")

left, right = st.columns([1, 2.6], gap="medium")
with left:
    with st.container(border=True):
        section("Input", "Local image or case")
        sources = [d for d in available_datasets() if d != "Synthetic demo"] + ["Local image file"]
        source = st.radio("Source", sources, key="mi_source")
        refs_available, image, case_id, readers = False, None, None, []
        if source == "Local image file":
            upload = st.file_uploader("Fundus image (stays on this computer)", type=["png", "jpg", "jpeg", "tif", "tiff"],
                                      key="mi_upload")
            if upload is not None:
                try:
                    image = Image.open(upload).convert("RGB")
                    case_id = Path(upload.name).stem
                except (OSError, ValueError) as exc:
                    st.error(f"Cannot open image: {exc}")
        else:
            loc = dataset_location(source)
            refs = cases(source, loc, _mtime(loc))
            ids = [r.case_id for r in refs]
            case_id = st.selectbox("Image", ids, key=f"mi_case_{source}")
            ref = refs[ids.index(case_id)]
            image, readers = case_data(ref, loc, _mtime(loc))
            refs_available = bool(readers)
        st.divider()
        show_disc = st.checkbox("Predicted disc", True, key="mi_disc")
        show_cup = st.checkbox("Predicted cup", True, key="mi_cup")
        zoom = st.toggle("Zoom to predicted disc", True, key="mi_zoom")

if image is None:
    with right:
        empty("Choose an image", "Select a dataset case or a local image file to run image-only inference.")
    st.stop()

from hyunoptic.ui.model_ui import crop_box, draw_prediction, image_sha256, predict, split_role  # noqa: E402

with st.spinner("Running image-only inference…"):
    try:
        pred = predict(str(bundle.folder), bundle.weights_sha256, image_sha256(image), image)
    except (BundleError, ValueError, RuntimeError, OSError) as exc:
        pred = None
        error = str(exc)
role = split_role(bundle, case_id) if source == "PAPILA" else None
thickness = st.session_state.get("pref_thickness", 2)

with right:
    with st.container(border=True):
        head, tag = st.columns([3, 1.4], vertical_alignment="center")
        with head:
            section("Source and prediction", f"{source} · {case_id}")
        with tag:
            if role:
                html(badge({"development": "Used in training", "validation": "Used for checkpoint selection",
                            "holdout": "Internal holdout image"}[role],
                           {"holdout": "info"}.get(role, "warn")))
        if pred is None:
            note(f"<b>Prediction failed.</b> {escape(error)}", "bad")
            st.image(image, caption="Source image (no prediction)", width="stretch")
        else:
            overlay, legend = draw_prediction(image, pred.disc, pred.cup, show_disc=show_disc, show_cup=show_cup,
                                              thickness=thickness)
            box = crop_box(pred.disc, image) if zoom else None
            c1, c2 = st.columns(2)
            c1.image(image.crop(box) if box else image, caption="Source image", width="stretch")
            c2.image(overlay.crop(box) if box else overlay, caption="Model prediction (image-only)", width="stretch")
            html(line_legend(legend))
            if role in ("development", "validation"):
                st.caption("This image was seen during training or checkpoint selection; its prediction says "
                           "nothing about generalisation.")
    if pred is not None:
        with st.container(border=True):
            section("Predicted measurements", "Shared measurement library · descriptive, not a risk score")
            if pred.status != "ok":
                note("<b>No measurement.</b> " + escape("; ".join(pred.errors) or pred.status)
                     + " — the image is kept, but no vCDR is shown.", "warn")
            else:
                mm = pred.measurement
                cards = [stat("Predicted vCDR", fmt(mm["vertical_cdr"], 3), "Cup ÷ disc height"),
                         stat("Predicted hCDR", fmt(mm["horizontal_cdr"], 3), "Cup ÷ disc width"),
                         stat("Area ratio", fmt(mm["area_cdr"], 3), "Cup area ÷ disc area"),
                         stat("Disc / cup area", "", "", extra=kv([("Disc px", f"{mm['disc_area_px']:,}"),
                                                                  ("Cup px", f"{mm['cup_area_px']:,}")]))]
                for col, card in zip(st.columns(4), cards):
                    with col:
                        html(card)
                for w in mm.get("warnings", []):
                    st.warning(w)

        with st.container(border=True):
            section("Expert comparison", "Separate panel · expert annotations are references, never model inputs")
            if not refs_available:
                st.info("No local expert annotations for this image, so comparison is disabled. Inference does not "
                        "need them.")
            elif st.toggle("Show expert comparison", False, key="mi_compare"):
                chosen_experts = st.multiselect("Experts", [r.label for r in readers],
                                                default=[r.label for r in readers[:2]], key=f"mi_experts_{len(readers)}")
                pairs = [(i, r) for i, r in enumerate(readers) if r.label in chosen_experts]
                comp, legend = draw_prediction(image, pred.disc, pred.cup, show_disc=show_disc, show_cup=show_cup,
                                               experts=pairs, thickness=thickness)
                box = crop_box(pred.disc, image) or None
                pic, info = st.columns([1, 1.25])
                pic.image(comp.crop(box) if box else comp, caption="Model (solid/dashed) vs experts (dotted)",
                          width="stretch")
                with info:
                    html(line_legend(legend))
                rows = []
                for _, r in pairs:
                    ref_m = measure_masks(r.disc, r.cup)
                    pv = pred.measurement["vertical_cdr"] if pred.measurement else None
                    err = None if pv is None else abs(pv - ref_m.vertical_cdr)
                    rows.append([r.label, fmt(dice(pred.disc, r.disc)), fmt(dice(pred.cup, r.cup)),
                                 fmt(ref_m.vertical_cdr),
                                 "N/A" if err is None else
                                 f"{err:.3f} ({'>' if err > RESEARCH_THRESHOLD else '≤'} 0.10)"])
                with info:
                    table(["Reference", "Disc Dice", "Cup Dice", "Expert vCDR", "ΔvCDR vs model"],
                          rows, numeric={1, 2, 3, 4})
                    st.caption("Per-image comparison for inspection only. Benchmark metrics come from the frozen "
                               "evaluator on the Model Experiment page, never from browsing.")
            else:
                st.caption("Hidden by default so expert outlines are not mistaken for the model's output.")

        with st.expander("Provenance", icon=":material/fingerprint:"):
            st.json({"run_id": bundle.run_id, "created_utc": m["created_utc"], "software_version": m["software_version"],
                     "weights_sha256": bundle.weights_sha256, "architecture": m["architecture"],
                     "preprocessing": m["preprocessing"], "postprocessing": m["postprocessing"],
                     "training": {k: tr[k] for k in ("dataset", "reader", "split_manifest_sha256", "selection_rule",
                                                      "best_epoch", "holdout_used_in_training_or_selection")},
                     "data_status": m["data_status"], "prediction_preprocessing": pred.preprocessing,
                     "permitted_use": m["permitted_use"]}, expanded=1)

        with st.container(border=True):
            section("Export", "Local research report for this image")
            ack = st.checkbox("I understand this file contains case-level data (image ID and measurements) and that "
                              "dataset terms may restrict sharing it.", key="mi_ack")
            payload = {"project": "HyunOptic", "report": "single-image model inference (research only)",
                       "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "source": source, "image_id": case_id, "image_role_in_model": role,
                       "run_id": bundle.run_id, "weights_sha256": bundle.weights_sha256,
                       "data_status": m["data_status"], "status": pred.status, "errors": pred.errors,
                       "predicted_measurement": pred.measurement,
                       "note": "Not a diagnosis. Expert annotations are references, not disease truth."}
            st.download_button("Download case report (JSON)", json.dumps(payload, indent=2, default=float),
                               file_name=f"hyunoptic_model_{case_id}.json", mime="application/json",
                               disabled=not ack, icon=":material/download:", key="mi_export")

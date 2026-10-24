"""PAPILA Source Holdout: the frozen mask score on patient-disjoint validation/holdout."""
import json

import streamlit as st

from hyunoptic.ui.components import (badge, empty, fmt, hash_card, html, kpi, kpi_row, note, page_title,
                                     section, table)
from hyunoptic.ui.results import SCORES
from hyunoptic.ui.state import active_run, load_json_upload, partial_banner
SHORT = {"combined_candidate_score": "Combined QC", "candidate_vcdr": "vCDR baseline",
         "mask_q95": "Mask Q95 (control)"}
from hyunoptic.ui.workspace import run_from_uploads

page_title("PAPILA Source Holdout",
           "The same frozen mask score evaluated on PAPILA patients never used to fit it.")
run = active_run()
if run is None or run.source is None:
    empty("No source-holdout results",
          "Run Batch Analysis (or hyunoptic-source-check) to evaluate the frozen model on PAPILA validation "
          "and holdout patients, or open an existing source_aggregate.json below. No numbers are shown "
          "until real outputs exist.", "chart")
    uploaded = st.file_uploader("Open source_aggregate.json", type=["json"])
    if uploaded is None:
        st.stop()
    try:
        run = run_from_uploads(source=load_json_upload(uploaded))
    except (ValueError, json.JSONDecodeError) as exc:
        st.error(f"Cannot read report: {exc}")
        st.stop()

src = run.source
partial_banner(run)
splits = src.get("patient_split_counts", {})
evaluation = src.get("evaluation", {})
lock_sha = src.get("source_lock_sha256", "")
complete = src.get("full_source_holdout_scored") is True


def split_card(name: str, icon_name: str) -> str:
    s = splits.get(name, {})
    return kpi(icon_name, f"{name.title()} eyes", f"{s.get('n_images', 0):,}",
               f"{s.get('n_patients', 0):,} patients · PAPILA")


kpi_row([
    split_card("validation", "users"),
    split_card("holdout", "database"),
    kpi("shield", "Source lock SHA-256", (lock_sha[:12] + "…") if lock_sha else "N/A",
        f"Lock in this run matches: {fmt(run.lock_sha == lock_sha) if run.lock else 'n/a'}", small=True),
    kpi("check" if complete else "alert", "Partial / verified status", "Verified" if complete else "Partial",
        "Complete 488-eye source scored" if complete else "Subset, synthetic or incomplete source",
        "ok" if complete else "warn"),
])
st.write("")
main, side = st.columns([2.45, 1.05], gap="medium")
with main:
    with st.container(border=True):
        budget = (run.lock or {}).get("model", {}).get("review_fraction", 0.2)
        section("Source Holdout Results",
                f"Ranking high expert-1 vs expert-2 vCDR disagreement (> 0.10) at a {budget:.0%} review budget")
        rows, highlight = [], set()
        for score in SCORES:
            for split in ("validation", "holdout"):
                g = evaluation.get(split)
                if not g:
                    continue
                m = g["scores"].get(score, {})
                share = g["n_high_disagreement"] / g["n_images"] if g.get("n_images") else None
                if score == "combined_candidate_score":
                    highlight.add(len(rows))
                first = split == "validation" or "validation" not in evaluation
                rows.append([SHORT[score] if first else "", split.title(), f"{g['n_images']:,}", f"{g['n_patients']:,}",
                             f"{g['n_high_disagreement']} ({share:.1%})" if share is not None else "N/A",
                             fmt(m.get("review", {}).get("precision_at_budget")),
                             fmt(m.get("review", {}).get("recall_at_budget")),
                             fmt(m.get("ranking", {}).get("average_precision")),
                             fmt(m.get("ranking", {}).get("roc_auc"))])
        table(["Method", "Split", "Images", "Patients", "High (share)", f"P@{budget:.0%}",
               f"R@{budget:.0%}", "AP", "ROC-AUC"], rows, numeric={2, 3, 4, 5, 6, 7, 8},
              highlight=highlight)
        if src.get("negative_control_warning"):
            st.caption(src["negative_control_warning"])
    with st.container(border=True):
        section("Reproducibility", "Hashes binding this evaluation to exact inputs and the frozen model")
        model = (run.lock or {}).get("model", {})
        c1, c2, c3 = st.columns(3)
        with c1:
            html(hash_card("file", "Dataset content hash", src.get("source_content_sha256"),
                           [("Algorithm", "SHA-256"), ("Scope", "Image + contour file bytes")]))
        with c2:
            html(hash_card("database", "Inventory fingerprint", src.get("source_inventory_fingerprint"),
                           [("Algorithm", "SHA-256"), ("Scope", "File names + sizes")]))
        with c3:
            html(hash_card("lock", "Model lock", lock_sha,
                           [("Method", model.get("method", src.get("model_scoring_method", "—"))),
                            ("Split seed", str(model.get("split_seed", "—")))]))
with side:
    with st.container(border=True):
        section("Patient Bootstrap", "Holdout precision@budget, combined score − vCDR baseline")
        ci = src.get("paired_patient_bootstrap_holdout", {})
        if ci.get("available"):
            lo, hi = ci["delta_95_percentile_interval"]
            crosses = lo <= 0 <= hi
            html(f'<div class="hz-stat"><div class="hd"><span>Mean Δ (bootstrap)</span>'
                 f'{badge("Interval includes 0" if crosses else "Interval excludes 0", "neutral" if crosses else "info")}'
                 f'</div><div class="v">{ci["delta_mean_bootstrap"]:+.3f}</div>'
                 f'<div class="c">95% percentile interval</div><div class="v" style="font-size:1.4rem">'
                 f"{lo:+.3f} to {hi:+.3f}</div></div>")
            st.caption("Exploratory patient-cluster bootstrap (both eyes resampled together). "
                       "Not a significance test or clinical effect.")
        else:
            empty("Bootstrap unavailable", ci.get("reason", "Not enough holdout patients for a paired bootstrap."))
    with st.container(border=True):
        section("Dataset Split Summary", "Patient-level 60/20/20 split; both eyes stay together")
        total = sum(s.get("n_images", 0) for s in splits.values()) or 1
        for name in ("development", "validation", "holdout"):
            s = splits.get(name, {})
            share = s.get("n_images", 0) / total
            html(f'<div class="hz-stat" style="margin-bottom:.5rem"><div class="hd"><span>{name.title()}</span>'
                 f'{badge(f"{share:.0%}", "info")}</div><div class="c">{s.get("n_images", 0):,} images · '
                 f'{s.get("n_patients", 0):,} patients</div></div>')
        st.caption("Development fits the frozen scaler (expert 1 only); expert 2 is read only after scoring.")
st.write("")
note("Internal holdout only: this does not show cross-camera or cross-hospital generalisation, and reader "
     "disagreement is not disease truth.")

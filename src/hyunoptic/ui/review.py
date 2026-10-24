"""Image review workspace shared by the Overview and Image Review pages."""
from __future__ import annotations

import streamlit as st

from .. import __version__
from ..mask_features import apply_mask_score, mask_features
from ..uncertainty import PerturbationConfig
from .components import badge, fmt, gauge, html, kv, line_legend, section, stat
from .images import SYNTHETIC, adjust, case_metrics, crop_to_disc, render_overlay
from .state import _mtime, active_run, available_datasets, case_data, case_thumb, cases, dataset_location
from .theme import EXPERT_COLORS

THRESHOLD = 0.10  # frozen research disagreement threshold, not a clinical cut-off
MODES = ["Single view", "Side by side", "Expert comparison"]


def _selection(names: list[str]) -> dict:
    sel = st.session_state.setdefault("selection", {"dataset": names[0], "index": 0})
    if sel["dataset"] not in names:
        sel.update(dataset=names[0], index=0)
    return sel


def _refs(dataset: str):
    loc = dataset_location(dataset)
    return cases(dataset, loc, _mtime(loc)), loc


def _set_index(i: int) -> None:
    st.session_state["selection"]["index"] = i


@st.cache_data(show_spinner=False, max_entries=48)
def _metrics(ref, loc: str, stamp: float, a: int, b: int | None, lock: dict | None) -> dict:
    image, readers = case_data(ref, loc, stamp)
    result = case_metrics(image, readers, a, b)
    if lock and result["features"] is not None:
        model = lock["model"]
        cfg = PerturbationConfig(**model["perturbation"])
        feats = mask_features(image, readers[a].disc, readers[a].cup, cfg)
        result["features"] = feats
        result["frozen_score"] = apply_mask_score(feats, model["scaler"])
        result["lock_sha"] = lock["sha256"]
    return result


def _image_selection(prefix: str, names: list[str]):
    sel = _selection(names)
    section("Image Selection")
    st.session_state[f"{prefix}_ds"] = sel["dataset"]

    def on_dataset():
        st.session_state["selection"] = {"dataset": st.session_state[f"{prefix}_ds"], "index": 0}

    st.selectbox("Dataset", names, key=f"{prefix}_ds", on_change=on_dataset)
    refs, loc = _refs(sel["dataset"])
    if not refs:
        st.warning("No readable images in this dataset.")
        return None, None, None
    i = min(sel["index"], len(refs) - 1)
    groups = list(dict.fromkeys(r.group for r in refs))
    group_label = {"PAPILA": "Patient", "Chákṣu": "Camera"}.get(sel["dataset"], "Set")
    st.session_state[f"{prefix}_grp"] = refs[i].group

    def on_group():
        g = st.session_state[f"{prefix}_grp"]
        _set_index(next(k for k, r in enumerate(refs) if r.group == g))

    st.selectbox(group_label, groups, key=f"{prefix}_grp", on_change=on_group)
    in_group = [k for k, r in enumerate(refs) if r.group == refs[i].group]
    st.session_state[f"{prefix}_img"] = refs[i].case_id

    def on_image():
        cid = st.session_state[f"{prefix}_img"]
        _set_index(next(k for k, r in enumerate(refs) if r.case_id == cid))

    st.selectbox("Image", [refs[k].case_id for k in in_group], key=f"{prefix}_img", on_change=on_image)
    prev, pos, nxt = st.columns([1, 2, 1], vertical_alignment="center")
    prev.button("", icon=":material/chevron_left:", key=f"{prefix}_prev", disabled=i == 0,
                on_click=_set_index, args=(i - 1,), help="Previous image", width="stretch")
    pos.markdown(f"<div style='text-align:center'>{i + 1:,} / {len(refs):,}</div>", unsafe_allow_html=True)
    nxt.button("", icon=":material/chevron_right:", key=f"{prefix}_next", disabled=i >= len(refs) - 1,
               on_click=_set_index, args=(i + 1,), help="Next image", width="stretch")
    strip = list(range(i, min(len(refs), i + 4)))
    for col, k in zip(st.columns(4), strip):
        with col:
            st.image(case_thumb(refs[k], loc, _mtime(loc)), width="stretch")
            st.button("●" if k == i else str(k + 1), key=f"{prefix}_th{k}", on_click=_set_index, args=(k,),
                      width="stretch", type="primary" if k == i else "secondary",
                      help=refs[k].case_id)
    return refs[i], loc, sel["dataset"]


def _overlay_options(prefix: str, n_readers: int) -> tuple[bool, bool, list[int]]:
    section("Overlay Options")
    show_disc = st.checkbox("Disc contour", value=True, key=f"{prefix}_disc")
    show_cup = st.checkbox("Cup contour", value=True, key=f"{prefix}_cup")
    experts = []
    for k in range(5):
        left, right = st.columns([4, 1])
        with left:
            on = st.checkbox(f"Expert {k + 1}", value=k < 2, key=f"{prefix}_e{k}",
                             disabled=k >= n_readers,
                             help=None if k < n_readers else "Not annotated in this dataset")
        with right:
            right.markdown(f'<span class="hz-swatch" style="border-color:{EXPERT_COLORS[k]}"></span>',
                           unsafe_allow_html=True)
        if on and k < n_readers:
            experts.append(k)
    return show_disc, show_cup, experts


def _adjustments(prefix: str) -> tuple[int, int]:
    section("Image Adjustments", "Display only — measurements always use original pixels.")
    bri = st.slider("Brightness", -100, 100, 0, key=f"{prefix}_bri")
    con = st.slider("Contrast", -100, 100, 0, key=f"{prefix}_con")

    def reset():
        st.session_state[f"{prefix}_bri"] = 0
        st.session_state[f"{prefix}_con"] = 0

    st.button("Reset", icon=":material/restart_alt:", key=f"{prefix}_reset", on_click=reset)
    return bri, con


def _summary(prefix: str, m: dict, dataset: str) -> None:
    head, tabs = st.columns([2, 3], vertical_alignment="center")
    with head:
        section("Measurement Summary", f"{m['a']}" + (f" vs {m['b']}" if "b" in m else "")
                + " · current image")
    with tabs:
        tab = st.segmented_control("Metric group", ["vCDR", "Area ratio", "Contour metrics", "Quality"],
                                   default="vCDR", key=f"{prefix}_tab", label_visibility="collapsed")
    a = m["measure_a"]
    cards = []
    has_b = "b" in m
    diff = m.get("abs_vcdr_difference")
    diff_badge = ("" if diff is None else badge("> 0.10 threshold", "warn") if diff > THRESHOLD
                  else badge("≤ 0.10 threshold", "ok"))
    if tab in (None, "vCDR"):
        cards = [
            stat("Vertical CDR", fmt(a["vertical_cdr"], 2), f"{m['a']} (cup ÷ disc height)",
                 extra=gauge(a["vertical_cdr"], 0, 1, [0, .25, .5, .75, 1])),
            stat("Reader |ΔvCDR|", fmt(diff, 3) if has_b else "N/A",
                 f"{m['a']} vs {m['b']}" if has_b else "Select a second expert",
                 diff_badge, gauge(diff, 0, .3, [0, .1, .2, .3], threshold=THRESHOLD) if has_b else ""),
            stat("Horizontal CDR", fmt(a["horizontal_cdr"], 2), f"{m['a']}",
                 extra=gauge(a["horizontal_cdr"], 0, 1, [0, .25, .5, .75, 1])),
            stat("Disc / Cup area (px)", "", "", extra=kv([
                ("Disc", f"{a['disc_area_px']:,}"), ("Cup", f"{a['cup_area_px']:,}"),
                ("Area ratio", fmt(a["area_cdr"], 2))])),
        ]
    elif tab == "Area ratio":
        b = m.get("measure_b") or {}
        cards = [
            stat("Area CDR", fmt(a["area_cdr"], 3), m["a"], extra=gauge(a["area_cdr"], 0, 1, [0, .5, 1])),
            stat("Area CDR", fmt(b.get("area_cdr"), 3), m.get("b", "No second expert"),
                 extra=gauge(b.get("area_cdr"), 0, 1, [0, .5, 1])),
            stat("Disc height / width (px)", f"{a['disc_vertical_px']} / {a['disc_horizontal_px']}", m["a"]),
            stat("Cup height / width (px)", f"{a['cup_vertical_px']} / {a['cup_horizontal_px']}", m["a"]),
        ]
    elif tab == "Contour metrics":
        spread = max(m["all_reader_vcdr"]) - min(m["all_reader_vcdr"])
        cards = [
            stat("Disc Dice", fmt(m.get("disc_dice"), 3), f"{m['a']} vs {m.get('b', '—')}",
                 extra=gauge(m.get("disc_dice"), 0, 1, [0, .5, 1])),
            stat("Cup Dice", fmt(m.get("cup_dice"), 3), f"{m['a']} vs {m.get('b', '—')}",
                 extra=gauge(m.get("cup_dice"), 0, 1, [0, .5, 1])),
            stat("vCDR spread, all experts", fmt(spread, 3),
                 f"max − min over {len(m['all_reader_vcdr'])} experts"),
            stat("Cup outline roughness", fmt((m["features"] or {}).get("mask_roughness"), 3),
                 f"{m['a']} · isoperimetric excess (0 = circle)"),
        ]
    else:
        f = m["features"] or {}
        frozen = m.get("frozen_score")
        cards = [
            stat("Combined QC score", fmt(frozen, 2) if frozen is not None else "No lock",
                 f"Frozen lock {m['lock_sha'][:10]}…" if frozen is not None
                 else "Run an analysis to freeze a model", badge("candidate-only", "info")),
            stat("Mask Q95 |ΔvCDR|", fmt(f.get("mask_q95"), 4), "Perturbation sensitivity (negative control)"),
            stat("Boundary weakness", fmt(f.get("mask_boundary_weakness"), 3), "1 − mean cup-edge gradient"),
            stat("Cup roughness", fmt(f.get("mask_roughness"), 3), "Isoperimetric excess"),
        ]
        if m.get("feature_error"):
            st.warning(f"Candidate features unavailable: {m['feature_error']}")
    for col, card in zip(st.columns(4), cards):
        with col:
            html(card)
    caption = ("Inter-reader values compare two experts retrospectively. Badges refer to the frozen 0.10 "
               "research threshold, not a clinical cut-off. vCDR is not a diagnosis.")
    if dataset == SYNTHETIC:
        caption = "Synthetic geometry (not patient data). " + caption
    st.caption(caption)


def review_workspace(prefix: str, *, default_mode: str, compact: bool) -> None:
    names = available_datasets()
    main, side = st.columns([3.1, 1.15], gap="medium")
    with side:
        with st.container(border=True):
            ref, loc, dataset = _image_selection(prefix, names)
            if ref is None:
                return
            image, readers = case_data(ref, loc, _mtime(loc))
            show_disc, show_cup, experts = _overlay_options(prefix, len(readers))
            st.divider()
            bri, con = _adjustments(prefix)
    if not experts:
        experts = [0]
    run = active_run()
    a = experts[0]
    b = experts[1] if len(experts) > 1 else (1 if a != 1 and len(readers) > 1 else None)
    metrics = _metrics(ref, loc, _mtime(loc), a, b, run.lock if run else None)
    with main:
        with st.container(border=True):
            head, modes = st.columns([2, 2.2], vertical_alignment="center")
            with head:
                section("Quick Image Review" if compact else "Image Review",
                        "Inspect optic disc and cup annotations." if compact
                        else "Compare expert annotations on the original image.")
            with modes:
                mode = st.segmented_control("View", MODES, default=default_mode, key=f"{prefix}_mode",
                                            label_visibility="collapsed") or default_mode
            zoom = st.toggle("Zoom to optic disc", value=True, key=f"{prefix}_zoom")
            base = adjust(image, bri, con)
            overlay, legend = render_overlay(
                base, readers, experts=experts, show_disc=show_disc, show_cup=show_cup,
                compare=mode == "Expert comparison",
                high_contrast=st.session_state.get("pref_high_contrast", False),
                dashed_cup=st.session_state.get("pref_dashed_cup", False),
                thickness=st.session_state.get("pref_thickness", 2))
            if zoom:
                base, overlay = crop_to_disc(base, readers), crop_to_disc(overlay, readers)
            title = f"{ref.dataset} · {ref.case_id}"
            if mode == "Single view":
                st.image(overlay, caption=f"Annotation overlay — {title}", width="stretch")
            else:
                left, right = st.columns(2)
                left.image(base, caption=f"Original image — {title}", width="stretch")
                right.image(overlay, caption=("Expert comparison overlay" if mode == "Expert comparison"
                                              else "Annotation overlay"), width="stretch")
            html(line_legend(legend))
        with st.container(border=True):
            _summary(prefix, metrics, dataset)


def sensitivity_panel(prefix: str) -> None:
    """v0.2 candidate-only perturbation sensitivity plus JSON/PNG export for the selected image."""
    import io
    import json

    from ..uncertainty import analyze_vertical_sensitivity

    sel = st.session_state.get("selection")
    if not sel:
        return
    refs, loc = _refs(sel["dataset"])
    if not refs:
        return
    ref = refs[min(sel["index"], len(refs) - 1)]
    image, readers = case_data(ref, loc, _mtime(loc))
    expert = next((k for k in range(len(readers)) if st.session_state.get(f"{prefix}_e{k}")), 0)
    reader = readers[expert]
    with st.container(border=True):
        section("Candidate-only measurement sensitivity",
                f"{reader.label} contours only · hypothetical boundary perturbations, NOT calibrated "
                "clinical uncertainty")
        c = st.columns(5)
        draws = c[0].slider("Monte Carlo draws", 100, 3000, 500, 100, key=f"{prefix}_draws")
        shared = c[1].slider("Shared log-SD", 0.0, 0.15, 0.02, 0.005, key=f"{prefix}_shared")
        cup_sd = c[2].slider("Cup log-SD", 0.0, 0.15, 0.03, 0.005, key=f"{prefix}_cupsd")
        disc_sd = c[3].slider("Disc log-SD", 0.0, 0.15, 0.03, 0.005, key=f"{prefix}_discsd")
        seed = c[4].number_input("Random seed", 0, 999_999, 42, key=f"{prefix}_seed")
        try:
            result = analyze_vertical_sensitivity(
                reader.disc_xy, reader.cup_xy,
                PerturbationConfig(draws=int(draws), seed=int(seed), shared_log_sd=float(shared),
                                   cup_log_sd=float(cup_sd), disc_log_sd=float(disc_sd)))
        except ValueError as exc:
            st.error(f"Sensitivity unavailable: {exc}")
            return
        cards = [
            stat("Q95 |ΔvCDR|", fmt(result.q95_absolute_vcdr_change, 4), "Under perturbation"),
            stat("Simulated vCDR SD", fmt(result.simulated_sd_vcdr, 4), "Empirical"),
            stat("2.5–97.5% range", f"{result.simulated_percentile_2_5:.3f}–{result.simulated_percentile_97_5:.3f}",
                 "Simulated, not a clinical CI"),
            stat("Cov(cup, disc) px²", fmt(result.covariance_cup_disc_vertical, 3), "Induced by assumed shared term"),
        ]
        for col, card in zip(st.columns(4), cards):
            with col:
                html(card)
        with st.expander("Covariance-aware error propagation"):
            st.write({
                "continuous-coordinate nominal vCDR": round(result.nominal_continuous_vcdr, 6),
                "empirical variance": round(result.empirical_variance_vcdr, 9),
                "delta-method variance (with covariance)": round(result.delta_method_variance_vcdr, 9),
                "delta-method variance (without covariance)": round(result.delta_method_variance_without_covariance, 9),
                "implied correlation": result.implied_cup_disc_correlation,
            })
        if ref.dataset == "Chákṣu":
            st.caption("Chákṣu outlines are traced from binary masks, so this sensitivity is approximate.")
        metrics = case_metrics(image, readers, expert, 1 if expert != 1 and len(readers) > 1 else None)
        payload = {"project": "HyunOptic", "version": __version__, "status": "research-only",
                   "dataset": ref.dataset, "image_id": ref.case_id, "image_size": list(image.size),
                   "candidate_reader": reader.label, "measurements": metrics,
                   "candidate_only_sensitivity": result.to_dict()}
        overlay, _ = render_overlay(image, readers, experts=[expert])
        png = io.BytesIO()
        overlay.save(png, format="PNG")
        d1, d2 = st.columns(2)
        d1.download_button("Download measurement JSON", json.dumps(payload, indent=2, default=float),
                           file_name=f"hyunoptic_{ref.case_id}.json", mime="application/json",
                           icon=":material/download:", key=f"{prefix}_json")
        d2.download_button("Download overlay PNG", png.getvalue(), file_name=f"hyunoptic_{ref.case_id}_overlay.png",
                           mime="image/png", icon=":material/download:", key=f"{prefix}_png")

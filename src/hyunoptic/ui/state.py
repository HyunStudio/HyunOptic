"""Cached data access and the shared page shell (top bar, sidebar card, run picker)."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import streamlit as st

from .. import __version__
from .components import html
from .icons import LOGO, icon
from .images import SYNTHETIC, CaseRef, list_cases, load_case, thumbnail
from .theme import inject_theme
from .workspace import (DatasetStatus, RunData, Workspace, chaksu_status, find_runs,
                        load_run, papila_status)

REPO_URL = "https://github.com/HyunStudio/HyunOptic"


def _mtime(path: str) -> float:
    try:
        return Path(path).expanduser().stat().st_mtime if path else 0.0
    except OSError:
        return 0.0


def workspace() -> Workspace:
    if "workspace" not in st.session_state:
        st.session_state["workspace"] = Workspace.load()
    return st.session_state["workspace"]


def save_workspace(ws: Workspace) -> None:
    ws.save()
    st.session_state["workspace"] = ws
    st.cache_data.clear()


@st.cache_data(show_spinner=False)
def _papila(root: str, stamp: float) -> DatasetStatus:
    return papila_status(root)


@st.cache_data(show_spinner=False)
def _chaksu(archive: str, stamp: float) -> DatasetStatus:
    return chaksu_status(archive)


def datasets() -> tuple[DatasetStatus, DatasetStatus]:
    ws = workspace()
    return _papila(ws.papila_root, _mtime(ws.papila_root)), _chaksu(ws.chaksu_zip, _mtime(ws.chaksu_zip))


def dataset_location(name: str) -> str:
    ws = workspace()
    return {"PAPILA": ws.papila_root, "Chákṣu": ws.chaksu_zip}.get(name, "")


@st.cache_data(show_spinner=False)
def cases(dataset: str, location: str, stamp: float) -> list[CaseRef]:
    return list_cases(dataset, location)


@st.cache_data(show_spinner=False, max_entries=24)
def case_data(ref: CaseRef, location: str, stamp: float):
    return load_case(ref, location)


@st.cache_data(show_spinner=False, max_entries=200)
def case_thumb(ref: CaseRef, location: str, stamp: float):
    image, _ = load_case(ref, location)
    return thumbnail(image)


def available_datasets() -> list[str]:
    papila, chaksu = datasets()
    names = [s.name for s in (papila, chaksu) if s.connected]
    return names + [SYNTHETIC]


@st.cache_data(show_spinner=False)
def _run(folder: str, stamp: float) -> RunData:
    return load_run(folder)


def runs() -> list[Path]:
    return find_runs(workspace().reports_dir)


def active_run() -> RunData | None:
    """The analysis run chosen in the sidebar (most recent by default)."""
    folders = runs()
    if not folders:
        return None
    chosen = st.session_state.get("active_run")
    folder = next((f for f in folders if str(f) == chosen), folders[0])
    return _run(str(folder), (folder / "pipeline_manifest.json").stat().st_mtime)


def _chip(dot: str, title: str, sub: str, extra: str = "") -> str:
    return (f'<div class="hz-chip {extra}"><span class="hz-dot {dot}"></span><div><b>{escape(title)}</b>'
            f"<small>{escape(sub)}</small></div></div>")


def _dataset_chip(status: DatasetStatus) -> str:
    if status.connected:
        noun = "images" + (" · demo" if status.synthetic else "")
        return _chip("warn" if status.synthetic else "on", status.name, f"{status.n_images:,} {noun}")
    if status.configured:
        return _chip("bad", status.name, "Path error")
    return _chip("", status.name, "Not connected")


def _search() -> None:
    query = st.session_state.get("hz_search", "").strip().upper()
    if not query:
        return
    for name in available_datasets():
        refs = cases(name, dataset_location(name), _mtime(dataset_location(name)))
        for i, ref in enumerate(refs):
            if query in ref.case_id.upper() or query == ref.group.upper():
                st.session_state["selection"] = {"dataset": name, "index": i}
                st.session_state["search_hit"] = f"{ref.dataset} · {ref.case_id}"
                st.session_state["goto_review"] = True
                return
    st.session_state["search_hit"] = f"No image or patient matches “{query}”."


def shell() -> None:
    """Theme, top bar and sidebar card shared by every page."""
    text_size = st.session_state.get("pref_text_size", "Standard")
    inject_theme(text_size)
    papila, chaksu = datasets()
    brand, search, chips, mode, prefs = st.columns([2.5, 2.4, 2.9, 1.45, 0.5], vertical_alignment="center")
    with brand:
        html(f'<div class="hz-brand">{LOGO}<div><b>HyunOptic</b><small>Ophthalmic Research Workspace</small>'
             f"</div></div>")
    with search:
        st.text_input("Search", key="hz_search", placeholder="Search image or patient ID",
                      label_visibility="collapsed", on_change=_search)
    with chips:
        c1, c2 = st.columns(2)
        with c1:
            html(_dataset_chip(papila))
        with c2:
            html(_dataset_chip(chaksu))
    with mode:
        html(_chip("on", "Research Mode", "Not for clinical use", "mode"))
    with prefs:
        with st.popover("", icon=":material/settings:", help="Display & accessibility"):
            st.select_slider("Text size", options=["Standard", "Large", "Extra large"], key="pref_text_size")
            st.toggle("High-contrast contour colours", key="pref_high_contrast",
                      help="Yellow disc / blue cup, distinguishable with common colour-vision deficiencies")
            st.toggle("Dashed cup outline", key="pref_dashed_cup",
                      help="Disc stays solid so outlines differ without relying on colour")
            st.slider("Contour line thickness", 1, 5, key="pref_thickness")
    if st.session_state.pop("goto_review", False):
        st.switch_page("views/image_review.py")
    hit = st.session_state.pop("search_hit", None)
    if hit and hit.startswith("No "):
        st.toast(hit)
    _sidebar()


def _sidebar() -> None:
    folders = runs()
    with st.sidebar:
        if folders:
            labels = {str(f): f.name for f in folders}
            current = st.session_state.get("active_run")
            if current not in labels:
                st.session_state["active_run"] = str(folders[0])
            st.selectbox("Analysis run", list(labels), key="active_run",
                         format_func=lambda k: labels[k],
                         help="Folders created by hyunoptic-pipeline under the reports directory")
        html(f'<div class="hz-side"><b>HyunOptic v{escape(__version__)}</b><br>'
             f'<span class="hz-badge info" style="margin-top:.35rem">Research Only</span>'
             "<p>Optic nerve measurement reliability for research and education.</p>"
             f'<hr style="margin:.6rem 0;border:0;border-top:1px solid #E1E7EF">'
             f'<a href="{REPO_URL}#readme" target="_blank">📄 Documentation</a>'
             f'<a href="{REPO_URL}" target="_blank">🐙 GitHub repository</a>'
             f'<a href="{REPO_URL}/issues" target="_blank">💬 Report an issue</a></div>')


def init_prefs() -> None:
    for key, value in (("pref_text_size", "Standard"), ("pref_high_contrast", False),
                       ("pref_dashed_cup", False), ("pref_thickness", 2)):
        st.session_state.setdefault(key, value)
    # Keep values when a page without these widgets is shown (Streamlit drops
    # widget state for widgets that were not rendered in the previous run).
    for key in ("pref_text_size", "pref_high_contrast", "pref_dashed_cup", "pref_thickness",
                "active_run"):
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def require_run(page: str) -> RunData | None:
    run = active_run()
    if run is None:
        from .components import empty
        empty("No analysis run yet",
              f"{page} shows results from a HyunOptic analysis run. Connect datasets on the Datasets page, "
              "then start a run from Batch Analysis (or run hyunoptic-pipeline). Nothing is shown "
              "until real outputs exist.", "chart")
    return run


def partial_banner(run: RunData) -> None:
    if run.partial:
        from .components import note
        note("<b>Partial or unverified inputs.</b> This run used a subset, synthetic fixture or an "
             "incomplete archive. Do not cite these numbers as validation evidence.", "warn")


def load_json_upload(uploaded) -> dict:
    data = json.load(uploaded)
    if not isinstance(data, dict) or data.get("project") != "HyunOptic":
        raise ValueError("Not a HyunOptic JSON report")
    return data

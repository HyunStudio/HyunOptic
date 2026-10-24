"""Batch Analysis: run the full frozen research chain into a new run folder."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from hyunoptic.pipeline import run_pipeline
from hyunoptic.ui.results import STEP_TITLES, STEP_TONE as TONE
from hyunoptic.ui.components import badge, html, note, page_title, section, step
from hyunoptic.ui.state import datasets, save_workspace, workspace

page_title("Batch Analysis", "Run inventory → freeze → source holdout → external test → evidence gate → report.",
           [badge("Writes a new folder", "info")])
ws = workspace()
papila, chaksu = datasets()

left, right = st.columns([1.3, 1], gap="medium")
with left:
    with st.container(border=True):
        section("Inputs", "Locations are set on the Datasets page")
        html(step("ok" if papila.connected else "bad", "PAPILA folder",
                  f"{papila.n_images:,} images · {ws.papila_root}" if papila.connected
                  else (papila.error or "Not configured — required")))
        html(step("ok" if chaksu.connected else "", "Chákṣu Test.zip (optional)",
                  f"{chaksu.n_images:,} images" if chaksu.connected else "Not configured — external steps skipped"))
        html(step("ok" if ws.papila_zip else "", "PAPILA.zip (optional)",
                  ws.papila_zip or "Not set — archive SHA-256 for PAPILA skipped"))
    with st.container(border=True):
        section("Run settings", "Frozen protocol defaults; change only for documented sensitivity runs")
        name = st.text_input("Run folder name", key="ba_name", value=f"run_{datetime.now():%Y%m%d_%H%M}",
                             help=f"Created inside {ws.reports_dir}/ — must be new")
        c1, c2, c3 = st.columns(3)
        seed = c1.number_input("Split seed", 0, 10**6, ws.seed)
        draws = c2.number_input("Perturbation draws", 100, 100_000, ws.draws, step=100)
        boots = c3.number_input("Bootstrap draws", 100, 100_000, ws.bootstrap_draws, step=100)
        verify = st.checkbox("Decode every PAPILA JPEG during inventory (slower)")
        partial = st.checkbox("Allow partial data (synthetic fixtures or subsets ONLY)",
                              value=papila.synthetic,
                              help="Results are labelled partial/unverified and cannot be cited as evidence")
        reports_dir = st.text_input("Reports directory", ws.reports_dir)
        start = st.button("Start analysis", type="primary", icon=":material/play_arrow:", key="ba_start",
                          disabled=not papila.connected or not name.strip(), width="stretch")

with right:
    with st.container(border=True):
        section("Progress", "Each step reports passed, incomplete, failed or skipped")
        board = st.empty()
        if start:
            if (int(seed), int(draws), int(boots), reports_dir) != (ws.seed, ws.draws, ws.bootstrap_draws,
                                                                     ws.reports_dir):
                ws.seed, ws.draws, ws.bootstrap_draws, ws.reports_dir = int(seed), int(draws), int(boots), reports_dir
                save_workspace(ws)
            done: list[tuple[str, str, str]] = []

            def progress(step_name, status, detail):
                done.append((step_name, status, detail))
                board.markdown("".join(step(TONE[s], STEP_TITLES.get(n, n), d[:140], s) for n, s, d in done),
                               unsafe_allow_html=True)

            out = Path(reports_dir).expanduser() / name.strip()
            try:
                with st.spinner("Running… large datasets can take several minutes."):
                    manifest = run_pipeline(
                        ws.papila_root, out, chaksu_test_zip=ws.chaksu_zip or None,
                        papila_zip=ws.papila_zip or None, allow_partial=partial, verify_pixels=verify,
                        seed=int(seed), draws=int(draws), bootstrap_draws=int(boots), progress=progress)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.cache_data.clear()
                st.session_state["active_run"] = str(out)
                if manifest["all_executed_steps_passed"]:
                    note(f"<b>Finished.</b> Run “{name}” is now the active run in the sidebar.")
                else:
                    note("<b>A step failed.</b> See the messages above; outputs before the failure are kept.", "bad")
        else:
            board.caption("Not started. Results stay on this computer.")
    note("Per-image files (<code>inventory.json</code>, <code>*private*</code>) stay local. "
         "Passing every step is not scientific or clinical validation.")

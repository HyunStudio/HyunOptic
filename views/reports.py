"""Reports & Evidence: preview, regenerate and export aggregate-only research outputs."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from hyunoptic.html_report import write_html_report
from hyunoptic.pipeline import AGGREGATE_FILES
from hyunoptic.ui.components import badge, empty, html, note, page_title, section, step, table
from hyunoptic.ui.icons import icon
from hyunoptic.ui.state import partial_banner, require_run
from hyunoptic.ui.workspace import append_history, read_history

page_title("Reports & Evidence",
           "Preview, regenerate and export aggregate-only reports for research documentation.")
run = require_run("Reports")
if run is None:
    st.stop()
partial_banner(run)
folder: Path = run.folder


def files() -> list[Path]:
    paths = [folder / rel for rel in AGGREGATE_FILES if (folder / rel).is_file()]
    paths += sorted(p for p in folder.glob("report_*.html") if p.is_file())
    return paths


KIND = {".md": "Summary", ".html": "Report", ".json": "Data"}


def card(col, icon_name: str, title: str, desc: str, path: Path | None) -> None:
    present = path is not None and path.is_file()
    with col:
        with st.container(border=True):
            html(f'<div style="display:flex;gap:.8rem"><div class="hz-kpi" style="border:0;padding:0;'
                 f'min-height:0"><div class="ic">{icon(icon_name)}</div></div><div><b>{escape(title)}</b> '
                 f'{badge("Available" if present else "Not generated", "ok" if present else "neutral")}'
                 f'<div style="color:#3B4A5E;font-size:.88rem">{escape(desc)}</div></div></div>')
            if present:
                st.download_button("Download", path.read_bytes(), file_name=path.name, key=f"dl_{title}",
                                   icon=":material/download:", width="stretch")


c = st.columns(4)
card(c[0], "file", "Source summary", "PAPILA validation/holdout results",
     folder / "source_holdout/source_summary.md")
card(c[1], "chart", "External summary", "Chákṣu Test results by camera", folder / "external/external_summary.md")
card(c[2], "shield", "Evidence review", "Cross-file consistency gate", folder / "evidence_review.json")
card(c[3], "file", "HTML report", "Self-contained aggregate report", folder / "report.html")
st.write("")

main, side = st.columns([2.4, 1.1], gap="medium")
with main:
    with st.container(border=True):
        head, act = st.columns([3, 1.2], vertical_alignment="center")
        with head:
            section("Generated Reports", f"Aggregate-only files in run “{run.label}”")
        with act:
            if st.button("Generate report", type="primary", icon=":material/note_add:", width="stretch"):
                inventory = None
                inv_path = folder / "inventory.json"
                if inv_path.is_file():
                    inventory = json.loads(inv_path.read_text(encoding="utf-8"))
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                out = write_html_report(folder / f"report_{stamp}.html", inventory=inventory, source=run.source,
                                        audit=run.audit, external=run.external, evidence=run.evidence,
                                        pipeline=run.manifest)
                append_history("export", run=run.label, name=out.name, type="HTML report",
                               size=out.stat().st_size)
                st.toast(f"Created {out.name}")
        listing = files()
        rows = []
        for p in listing:
            info = p.stat()
            rows.append([str(p.relative_to(folder)), KIND.get(p.suffix, "File"), f"{info.st_size / 1024:,.1f} KB",
                         datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M")])
        table(["File", "Type", "Size", "Modified"], rows, numeric={2})
        st.caption("inventory.json and files named *private* hold per-image rows; they are never listed or "
                   "exported here.")
        if listing:
            choice = st.selectbox("Preview", [str(p.relative_to(folder)) for p in listing], key="rep_preview")
            path = folder / choice
            if path.suffix == ".md":
                with st.container(height=420):
                    st.markdown(path.read_text(encoding="utf-8"))
            elif path.suffix == ".html":
                components.html(path.read_text(encoding="utf-8"), height=520, scrolling=True)
            else:
                st.json(json.loads(path.read_text(encoding="utf-8")), expanded=1)
            st.download_button(f"Download {path.name}", path.read_bytes(), file_name=path.name,
                               icon=":material/download:", key="rep_dl")

with side:
    with st.container(border=True):
        section("Evidence Package Readiness", "Six artifacts the evidence gate requires")
        checks = []

        def add(title, desc, present, ok):
            checks.append(("ok" if ok else ("warn" if present else ""), title,
                           desc if present else "Missing", "ready" if ok else ("review" if present else "")))
            return ok

        srcs = run.sources or {}
        listed = {c.get("dataset"): c for c in srcs.get("checks", [])}
        ready = all([
            add("Sources", "Archive SHA-256 for PAPILA and Chákṣu", bool(run.sources),
                set(listed) == {"PAPILA", "CHAKSU_TEST"} and all(
                    c.get("matches_independent_public_reference") for c in listed.values())),
            add("PAPILA inventory", "Image counts and structure", run.inventory_counts is not None,
                run.inventory_complete is True),
            add("Model lock", "Frozen development-only scaler", run.lock is not None,
                bool(run.lock) and not run.lock["model"].get("source_is_partial", True)),
            add("Source holdout", "Validation + holdout evaluation", run.source is not None,
                bool(run.source) and run.source.get("full_source_holdout_scored") is True),
            add("Chákṣu audit", "All five readers, 336 images", run.audit is not None,
                bool(run.audit) and run.audit.get("all_published_test_masks_structurally_verified") is True),
            add("External aggregate", "Frozen score on the full Test set", run.external is not None,
                bool(run.external) and run.external.get("partial_or_unverified_external") is False),
        ])
        html("".join(step(*c) for c in checks))
        if ready:
            note("<b>All six artifacts are complete.</b> Run the Evidence Check to confirm they are mutually "
                 "consistent. Consistency is not scientific or clinical validation.")
        else:
            note("<b>Not ready.</b> Missing or partial artifacts are marked above. An export is still possible "
                 "but is labelled partial.", "warn")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in files():
                zf.write(p, f"{run.label}/{p.relative_to(folder)}")
            zf.writestr(f"{run.label}/README.txt",
                        "HyunOptic aggregate evidence package. Research only; NOT clinical validation.\n"
                        f"Complete package: {ready}. Per-image files are deliberately excluded.\n")
        name = f"hyunoptic_evidence_{run.label}{'' if ready else '_PARTIAL'}.zip"
        if st.download_button("Generate evidence package", buffer.getvalue(), file_name=name,
                              mime="application/zip", type="primary", icon=":material/download:",
                              width="stretch"):
            append_history("export", run=run.label, name=name, type="Evidence package",
                           size=len(buffer.getvalue()))

st.write("")
with st.container(border=True):
    section("Recent Exports", "Stored locally in the workspace folder")
    exports = read_history("export", limit=10)
    if exports:
        table(["Time (UTC)", "Run", "File", "Type", "Size"],
              [[e["time_utc"], e.get("run", ""), e.get("name", ""), e.get("type", ""),
                f"{e.get('size', 0) / 1024:,.1f} KB"] for e in exports], numeric={4})
    else:
        empty("No exports yet", "Generated reports and evidence packages will be listed here.")

"""Datasets & Integrity: connect local datasets and run integrity checks."""
from __future__ import annotations

import time
from pathlib import Path
import zipfile
from html import escape

import streamlit as st

from hyunoptic.chaksu import scan_test_archive
from hyunoptic.external_qc import check_chaksu_archive
from hyunoptic.inventory import inspect_papila
from hyunoptic.source_integrity import verify_archive
from hyunoptic.ui.components import badge, html, kv, note, page_title, section, step, table
from hyunoptic.ui.icons import icon
from hyunoptic.ui.state import datasets, save_workspace, workspace
from hyunoptic.ui.workspace import append_history, read_history

page_title("Datasets & Integrity",
           "Connect local datasets and verify data integrity, structure and annotations. Nothing is uploaded.")
ws = workspace()
papila, chaksu = datasets()
history = read_history("integrity", limit=50)


def last(dataset: str, check: str) -> dict | None:
    return next((h for h in history if h.get("dataset") == dataset and h.get("check") == check), None)


def short(path: str) -> str:
    """Last two path parts; the full path is shown in the Location editor."""
    if not path:
        return "Not set"
    parts = Path(path).parts
    return path if len(parts) <= 3 else "…/" + "/".join(parts[-2:])


def card(status, path_label: str, zip_value: str, key: str) -> None:
    tone = {"Connected": "ok", "Error": "bad"}.get(status.state, "neutral")
    sha = last(status.name, "Archive SHA-256")
    structure = last(status.name, "Full integrity check")
    with st.container(border=True):
        top, act = st.columns([2.6, 1.4], vertical_alignment="center")
        with top:
            html(f'<div style="display:flex;gap:1rem;align-items:center"><div class="hz-kpi" style="border:0;'
                 f'padding:0;min-height:0"><div class="ic">{icon("database", 30)}</div></div><div>'
                 f'<b style="font-size:1.3rem">{escape(status.name)}</b> {badge(status.state, tone)}'
                 + (f" {badge('Synthetic demo data', 'warn')}" if status.synthetic else "")
                 + f'<div style="font-size:1.9rem;font-weight:700">{status.n_images:,} '
                 f'<span style="font-size:1rem;font-weight:400;color:#3B4A5E">images</span></div></div></div>')
        with act:
            with st.popover("Edit", icon=":material/folder_open:", width="stretch", help="Change dataset location"):
                if status.name == "PAPILA":
                    root = st.text_input("Extracted PAPILA folder", ws.papila_root, key=f"{key}_root",
                                         help="Folder containing FundusImages/ and ExpertsSegmentations/")
                    zp = st.text_input("PAPILA.zip (optional, for SHA-256)", ws.papila_zip, key=f"{key}_zip")
                    if st.button("Save", key=f"{key}_save", type="primary"):
                        ws.papila_root, ws.papila_zip = root.strip(), zp.strip()
                        save_workspace(ws)
                        st.rerun()
                else:
                    zp = st.text_input("Original Chákṣu Test.zip", ws.chaksu_zip, key=f"{key}_zip")
                    if st.button("Save", key=f"{key}_save", type="primary"):
                        ws.chaksu_zip = zp.strip()
                        save_workspace(ws)
                        st.rerun()
        rows = [(path_label, short(status.location))]
        if zip_value or status.name == "PAPILA":
            rows.append(("Archive", short(zip_value)))
        rows += [
            ("Archive SHA-256", (sha["sha256"][:12] + "…") if sha and sha.get("sha256") else "Not checked"),
            ("Reference match", sha["result"] if sha else "—"),
            ("Last verified (UTC)", structure["time_utc"] if structure else "Never"),
        ]
        html(kv(rows))
        if status.error:
            st.error(status.error)


left, right = st.columns([2.45, 1.05], gap="medium")
with left:
    c1, c2 = st.columns(2)
    with c1:
        card(papila, "Folder", ws.papila_zip, "pap")
    with c2:
        card(chaksu, "Test.zip", "", "chk")
    with st.container(border=True):
        section("Dataset List", "Only datasets with an implemented adapter and protocol role are listed.")

        def checked(name, check):
            entry = last(name, check)
            return entry["result"] if entry else "Not checked"

        table(["Dataset", "Role", "Images", "Patients", "Expert annotations", "Checksum", "Structure", "Status"], [
            ["PAPILA", papila.role, f"{papila.n_images:,}",
             f"{papila.n_patients:,}" if papila.n_patients is not None else "—",
             "2 experts (contours)", checked("PAPILA", "Archive SHA-256"),
             checked("PAPILA", "Full integrity check"), papila.state],
            ["Chákṣu Test", chaksu.role, f"{chaksu.n_images:,}", "Not identifiable",
             "5 experts (binary masks)", checked("Chákṣu", "Archive SHA-256"),
             checked("Chákṣu", "Full integrity check"), chaksu.state],
        ], numeric={2, 3})
        if chaksu.connected and chaksu.groups:
            st.caption("Chákṣu cameras: " + " · ".join(f"{k.title()} {v}" for k, v in chaksu.groups.items())
                       + " (published Test: Bosch 41 · Forus 31 · Remidio 264).")
        if papila.connected:
            st.caption(f"PAPILA: {papila.n_patients} patients, both eyes kept in one split "
                       "(published: 244 patients · 488 images).")
    with st.container(border=True):
        section("Recent Verification History", "Stored locally in the workspace folder.")
        if not history:
            st.caption("No integrity checks have been run yet.")
        else:
            table(["Time (UTC)", "Dataset", "Check", "Result", "Details"],
                  [[h["time_utc"], h["dataset"], h["check"], h["result"], h.get("details", "")]
                   for h in history[:12]])

with right:
    with st.container(border=True):
        section("Integrity Check", "Run structural validation for the selected dataset.")
        choices = [s.name for s in (papila, chaksu) if s.configured]
        if not choices:
            st.info("Set a dataset location first (Location button on a dataset card).")
            st.stop()
        name = st.selectbox("Dataset", choices, key="ic_dataset")
        pixels = False
        if name == "PAPILA":
            pixels = st.checkbox("Decode every JPEG (slower)", key="ic_pixels")
        go = st.button("Run Integrity Check", type="primary", icon=":material/play_arrow:",
                       width="stretch")
        if go:
            results = []

            def timed(title, fn):
                start = time.perf_counter()
                try:
                    tone, detail, extra = fn()
                except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
                    tone, detail, extra = "bad", f"{type(exc).__name__}: {exc}", {}
                results.append((tone, title, detail, f"{time.perf_counter() - start:.1f}s"))
                return tone, detail, extra

            archive = ws.papila_zip if name == "PAPILA" else ws.chaksu_zip
            dataset_key = "PAPILA" if name == "PAPILA" else "CHAKSU_TEST"
            with st.spinner("Checking…"):
                if archive:
                    def sha():
                        r = verify_archive(archive, dataset_key)
                        ok = r["matches_independent_public_reference"]
                        return ("ok" if ok else "warn",
                                f"{r['computed_sha256'][:16]}… · reference {'match' if ok else 'mismatch'}",
                                {"sha256": r["computed_sha256"], "match": ok})
                    tone, detail, extra = timed("Archive SHA-256", sha)
                    append_history("integrity", dataset=name, check="Archive SHA-256",
                                   result="Match" if extra.get("match") else
                                   ("Mismatch" if tone != "bad" else "Error"),
                                   details=detail, sha256=extra.get("sha256"))
                else:
                    results.append(("", "Archive SHA-256", "No archive path set — skipped", ""))
                if name == "PAPILA":
                    holder = {}

                    def layout():
                        inv = inspect_papila(ws.papila_root, verify_pixels=pixels)
                        holder["inv"] = inv
                        o = inv["observed"]
                        ok = o["images"] == 488 and o["patients"] == 244 and o["canonical_contours"] == 1952
                        return ("ok" if ok else "warn",
                                f"{o['patients']} patients · {o['images']} images · {o['canonical_contours']} "
                                "contours (published 244 · 488 · 1952)", {})
                    timed("Folder layout & counts", layout)

                    def readability():
                        o = holder["inv"]["observed"]
                        bad = o["unusable_images"] + o["duplicate_like_contours"] + o["unexpected_txt_files"]
                        return ("ok" if bad == 0 else "warn",
                                f"{o['unusable_images']} unusable images · {o['duplicate_like_contours']} "
                                f"duplicate-like contours · {o['unexpected_txt_files']} unexpected files", {})
                    if "inv" in holder:
                        timed("Annotation readability", readability)

                        def dims():
                            n = holder["inv"]["observed"]["image_dimension_mismatches"]
                            return ("ok" if n == 0 else "warn", f"{n} images differ from 2576×1934", {})
                        timed("Image dimensions", dims)
                    complete = bool(holder.get("inv", {}).get("matches_full_published_shape"))
                else:
                    holder = {}

                    def layout():
                        _, manifest = scan_test_archive(ws.chaksu_zip)
                        ok = manifest["matches_published_test_file_layout"]
                        return ("ok" if ok else "warn",
                                f"{manifest['image_entries']} Test images indexed · published layout "
                                f"{'matched' if ok else 'not matched'}", {})
                    timed("Folder layout", layout)

                    def masks():
                        report, _ = check_chaksu_archive(ws.chaksu_zip)
                        holder["audit"] = report
                        return ("ok" if report["all_published_test_masks_structurally_verified"] else "warn",
                                f"{report['n_readable_with_all_five_experts']} of {report['n_checked']} readable "
                                f"with all 5 experts · {report['n_errors']} errors", {})
                    timed("Expert mask check (5 readers)", masks)
                    complete = bool(holder.get("audit", {}).get("all_published_test_masks_structurally_verified"))
            worst = "bad" if any(r[0] == "bad" for r in results) else (
                "warn" if any(r[0] == "warn" for r in results) else "ok")
            summary = {"ok": "Passed", "warn": "Issues found", "bad": "Error"}[worst]
            append_history("integrity", dataset=name, check="Full integrity check", result=summary,
                           details="; ".join(f"{r[1]}: {r[2]}" for r in results)[:300],
                           complete_published_dataset=complete)
            st.session_state["ic_last"] = {"dataset": name, "steps": results, "summary": summary,
                                           "worst": worst, "complete": complete}
            st.rerun()  # refresh the cards and history with the new entries
        last_run = st.session_state.get("ic_last")
        if last_run and last_run["dataset"] == name:
            html("".join(step(*r) for r in last_run["steps"]))
            text = {"ok": "All checks passed.", "warn": "Checks ran; issues need review.",
                    "bad": "A check failed to run."}[last_run["worst"]]
            sub = ("Matches the complete published dataset." if last_run["complete"]
                   else "Not the complete published dataset (subset, synthetic or modified).")
            note(f"<b>{escape(last_run['summary'])}</b> — {escape(text)}<br>{escape(sub)}",
                 {"ok": "", "warn": "warn", "bad": "bad"}[last_run["worst"]])
        else:
            st.caption("Results and timings appear here. Structural checks are not proof of clinical "
                       "annotation correctness.")

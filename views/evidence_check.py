"""Evidence Check: run the cross-file consistency gate on the active run."""
from __future__ import annotations

import streamlit as st

from hyunoptic.evidence_gate import review_evidence
from hyunoptic.ui.components import badge, empty, html, kpi, kpi_row, note, page_title, section, step
from hyunoptic.ui.state import require_run

page_title("Evidence Check", "Are the six research artifacts present and mutually consistent?",
           [badge("Not certification", "warn")])
run = require_run("Evidence Check")
if run is None:
    st.stop()
folder = run.folder
paths = {
    "sources": folder / "sources.json", "papila_inventory": folder / "inventory.json",
    "model_lock": folder / "model_lock.json",
    "source_holdout": folder / "source_holdout/source_aggregate.json",
    "chaksu_audit": folder / "chaksu_audit/audit_aggregate.json",
    "external_aggregate": folder / "external/external_aggregate.json",
}
missing = [k for k, p in paths.items() if not p.is_file()]
report = run.evidence
if missing:
    empty("Gate cannot run", "Missing artifacts: " + ", ".join(m.replace("_", " ") for m in missing)
          + ". Connect both datasets and archives, then start a new Batch Analysis run.", "alert")
    st.stop()
if report is None or st.button("Re-check now", icon=":material/refresh:"):
    try:
        report = review_evidence(**paths)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        st.error(f"Gate error: {exc}")
        st.stop()
consistent = report["all_required_artifacts_consistent"]
kpi_row([
    kpi("check" if consistent else "alert", "Package consistent", "Yes" if consistent else "No",
        "All required checks" if consistent else "See failed checks", "ok" if consistent else "warn"),
    kpi("shield", "Checks passed", f"{report['n_passed']} / {report['n_total']}", report.get("gate_version", "")),
    kpi("info", "Scientific validity", "Not established", "A gate cannot establish it", "warn"),
    kpi("info", "Clinical accuracy", "Not established", "Research only", "warn"),
])
st.write("")
with st.container(border=True):
    section("Checks", report.get("purpose", ""))
    html("".join(step("ok" if c["passed"] else "bad", name.replace("_", " "), c["description"],
                      "PASS" if c["passed"] else "FAIL") for name, c in report["checks"].items()))
note("<b>Limitations.</b> " + " ".join(report.get("limitations", [])))

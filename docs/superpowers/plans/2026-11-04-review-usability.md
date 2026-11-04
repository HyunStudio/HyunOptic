# Review Workflow Usability Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for independent implementation tasks and requesting-code-review before integration.

**Goal:** Implement the reviewed design with verified integrity, safer UI and reviewable submission evidence.
**Architecture:** Split metadata listing from verified case detail, keep strict actions/snapshots, share a provenance resolver and retain Streamlit UI.
**Tech stack:** Python, SQLite, Streamlit, Pillow/NumPy, optional PyTorch.
**Spec:** `docs/superpowers/specs/2026-11-04-review-usability-design.md`.

## Global constraints

Local-only; no patient data in public evidence; preserve prior artifacts/models/default policy; no invented human/event claims; no license grants/branch deletion. Existing checkout is dedicated to HyunOptic and clean; create a feature branch here as in previous authorized work.

## Review focus

- Session switch must revoke deletion consent; test equal-size sessions.
- Wrong working directory/outer Git repo must never produce false application provenance.
- Fast lists must not weaken selected-case, save or export verification.
- Filter/order changes and stale saves must not skip or falsely review a case.
- Narrow/zoomed views must retain model identity, errors and keyboard reachability.

## Tasks

- [ ] Store: RED tests; add list_case_metadata and verified_case with persisted priority and safe legacy fallback; benchmark 20/200 synthetic inputs; review independently.
- [ ] Provenance: RED tests; add best-effort source-root resolver; test Git missing/timeout/nonrepo/wrong cwd; root wires UI; review independently.
- [ ] UI: RED tests for session-scoped delete, terminal imports, save-next; add comparison columns/full-size view, local labels, metadata list + verified selection, responsive header; run focused UI regressions.
- [ ] Submission: simplify README and narrative, add personal motivation and truthful step comparison, current demo plan/captions/evidence, source-date disclosure; retain human worksheet and license boundaries.
- [ ] Integration: full suite, isolated installed package checks, actual browser desktop/narrow/zoom flow and export, independent full diff review; freeze results and validate hashes.
- [ ] Publish: matching commit via PR, all CI green, merge and verify main tree/clean checkout.

Ruling: Implement now as pre-event work, rather than retaining known defects for potential scoring. The user explicitly authorized execution after design; do not add another approval stop.

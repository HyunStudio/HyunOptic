# Submission Review Workflow Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans; check each deliverable with meaningful tests.

**Goal:** Deliver a working local research review workflow and correct the four reproduced defects.
**Architecture:** Existing CPU Predictor and verified bundles feed a persistent SQLite ReviewStore. An independent runner processes one pending case at a time; deterministic priority and static exports never use reference annotations.
**Tech Stack:** Python 3.10+, SQLite, Pillow, NumPy, Streamlit; PyTorch remains optional/lazy.
**Spec:** `docs/superpowers/specs/2026-11-03-ai-builders-review-workflow-design.md`.

## Global constraints and rulings

- User authorizes completion now. All 2026-11-03 implementation is pre-event work, never claimed as event-period contributions.
- Work on `codex/submission-review-workflow`, preserving main and four local real-data bundles.
- No raw research data, masks, weights, patient IDs, personal registration information in public commits.
- No diagnostic claims, measured review-efficiency claims, or fabricated independent evaluation.
- Runtime artifacts belong under HYUNOPTIC_WORKSPACE, never committed.
- Ruling: implement in the existing dedicated review checkout on a separate branch, avoiding extra workspace relocation and virtualenv duplication.
- Ruling: model pairs are chosen explicitly; synthetic fixtures prove mechanics, never real-data accuracy.

## Review focus

- Same-weight bundle replacement must invalidate both inference caches.
- Replacing nested dataset content must invalidate cached images/annotations.
- Interrupted writes and stale reviewer revisions must preserve prior decisions.
- Missing model/data and partially failed runs must remain visible and resumable.
- Export must exclude private inputs and detect missing/tampered payloads.

## Task 1: regression fixes
- [x] Add failing regressions for nested source changes, full bundle identity, unsupported bundle contracts, multi-frame TIFF.
- [x] Implement supported bundle schema validation and identity, source fingerprint, safe image loader.
- [x] Update UI callsites and run focused + legacy contract tests.

## Task 2: persistent review domain
- [x] Add failing tests for import limits, copying, revision conflicts, interruption, evidence identity and ranking.
- [x] Implement `review/store.py`, `review/priority.py`, `review/inputs.py`.
- [x] Verify no ground truth reaches priority and no review is carried to a new prediction set.

### Shared interface (Task 2 owns)

`ReviewStore(root: Path)` creates root and DB. All public rows are dictionaries.
`create_session(inputs: list[tuple[str, bytes]], models: list[dict], modality='color_fundus', software_commit='unknown') -> str`.
Model dictionaries: `folder`, `identity`, `run_id`, `weights_sha256`; two distinct models required.
`sessions() -> list[dict]`, `session(session_id) -> dict` with models list.
`cases(session_id) -> list[dict]`: id, original_name(local only), input_path, pixel_sha256, status(pending/processing/complete/error), error, predictions(list), review_state, revision, reasons, note, prediction_set_hash, priority(dict).
`claim(case_id)`, `record_prediction(case_id, model_identity, prediction: dict, labels: ndarray | None)`, `finish(case_id, error: str | None=None)`, `recover(session_id)`.
prediction fields: status, measurement, errors, preprocessing, run_id, weights_sha256.
`decide(case_id, state, reasons, note, expected_revision)` supports unreviewed/reviewed/held and requires complete prediction_set_hash; held needs reason, other needs note.
`events(session_id)`, `delete_session(session_id)`; store.root available. `record_prediction` returns no value.
`priority(predictions)` implemented from prediction dicts with labels_path; `cases` attaches priority: group, score(nullable), reasons(list), vcdr_delta(nullable).

## Task 3: runner and export (depends on shared interface)
- [x] Tests first: real adapter with fake predictors, per-case recovery, export privacy and tamper rejection.
- [x] `review/runner.py`: `run_next(store, session_id, predictor_factory=None) -> bool`; reverify chosen bundle identity, process one case, preserve per-model errors; default factory lazy Predictor. No CLI side effects.
- [x] `review/export.py`: `export_session(store, session_id, target: Path) -> Path` creates ZIP; `verify_export(path: Path) -> dict`. Payloads JSON/CSV/JSONL/static HTML; no original names/paths/images/notes/actor by default; strict path/member verification. CLI via `python -m hyunoptic.review.export ZIP` verifies.

## Task 4: application integration and submission package
- [x] AppTest tests for empty state and loaded review, save/restore, export.
- [x] Add `views/model_review_queue.py`, navigation, explicit model pair and modality choice, import, bounded processing, review controls, full source overlay, ZIP download and delete.
- [x] Reuse accessibility options; preserve source full view and explain research scope/retention.
- [x] Add truthful baseline/event/AI/access/validation/demo documentation; smoke full synthetic run and real local pair; capture actual results.

## Task 5: verification and delivery
- [x] Run whole suite and evidence verification; compile, CLI checks, diff check.
- [x] Independent review of integrated branch; fix substantiated issues and rerun affected checks.
- [ ] Commit and publish feature branch/PR after final checks; no competition submission or public video publication is performed automatically.

## Progress

- Tasks 1–4 implemented. Final integrated suite: 274 passed, 2 existing CUDA warnings, 382.37 seconds. Independent review fixes verified with 23 scoped tests. 100-case synthetic batch and actual two-model/two-image local integration passed. Existing evidence verified on disk and in staged Git blobs. Publishing is tracked by the branch/PR record.
- Ruling: bounded synchronous processing uses explicit steps (default five images); automatic background execution is outside the single-user local scope. Cost: large batches require repeated continue actions.
- Ruling: independent ranking effectiveness remains unestablished, so the feature is described as model comparison and descriptive priority. Cost: no supported efficiency-improvement claim.
- Ruling: actual public video and event submission remain publication steps; the package supplies a script and checklist, without inventing a video URL. Cost: submitter still needs to record/review the final demonstration.

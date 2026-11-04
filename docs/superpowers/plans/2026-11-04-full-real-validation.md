# Full real-data validation plan

> **For agentic workers:** Use executing-plans for the PAPILA audit and dispatching-parallel-agents for independent external-data work. Track completed evidence below.

**Goal:** Replace the four-patient robustness pilot with full available holdout coverage, fresh external inference and independently checked failure-aware metrics.

**Architecture:** Freeze protocols and model/data identities. PAPILA and Chaksu save image-only predictions before reference scoring; RIM's first pass pre-audits references and its explicit follow-up saves all masks before re-scoring. Publish aggregate evidence and reproducible harnesses, keeping source assets and identifiers private.

**Tech Stack:** Python 3.12, existing PyTorch Predictor on CPU, NumPy, Pillow, verified local research datasets.

**Spec:** User requests sufficient paper-informed and actual-data testing; earlier 100-paper catalogue and four-patient pilot establish scope, not clinical sufficiency.

## Global constraints

- No retraining, target-label tuning, mask repair, default-policy promotion, raw-data redistribution or original-paper performance claims.
- PAPILA is a reused holdout (49 patients, 98 eyes); transformations are correlated repeats, not new patients.
- Chaksu is a reused external Test cohort (336 images); all five readers scored independently, unknown patient linkage prevents patient-level confidence intervals.
- New datasets require official access/terms and original reference masks; access failures remain visible.
- Literature connections motivate checks, not 100 independent algorithm reproductions.
- Preserve previous frozen reports, bundles, source data and social-media drafts.

## Review focus

1. Full cartesian coverage and every execution/geometry/reference failure retained.
2. Correlated eyes and transformations are clustered by patient; paired comparisons use common measurable cases.
3. One corrupt reader does not discard other valid original readers.
4. Ranking is frozen before labels; unknown reference outcomes are neither negative nor silently excluded from the queue.
5. Public aggregates contain no patient identifiers or source assets; official source limitations and source hashes remain reproducible.

## Tasks

- [x] Freeze and execute PAPILA 98 eyes × 13 conditions × 2 frozen models (2,548 predictions); score both readers, patient-weighted uncertainty and paired changes; save masks privately.
- [x] Fresh Chaksu 336 images × 2 models (672 predictions), five-reader and camera-stratified evaluation with actual mask disagreement ranking.
- [x] Check official access for a new external dataset; evaluate all 174 RIM-ONE DL hospital-Test images and perform the separately declared artifact-checking repeat.
- [x] Independently recompute saved-mask arithmetic, coverage and aggregates; investigate any discrepancy and regression-test confirmed product bugs before fixes.
- [x] Publish reviewed aggregates, protocols, limitations, source provenance and harnesses under a new evidence manifest; verify previous evidence unchanged.
- [x] Run appropriate software checks and final independent review; publication is gated by the remote PR checks and merge.

## Execution ledger

- Baseline: main `9cd674e3ee54d903410a24071f6a4de99fb38cdf`; clean dedicated checkout, new `codex/full-real-validation-20261104` branch.
- Ruling: full-data stress uses 13 fixed conditions (original plus photometric/compression/resolution perturbations), rather than extending all 100 pilot conditions. The 128-pixel downsample can be substantial; strengths are not presented as clinically calibrated severity. This expands patient coverage while avoiding counting transformations as clinical diversity.
- Ruling: read-only metadata/content hashing before inference is integrity verification; expert contours/masks are interpreted only after the prediction phase.
- Ruling: RIM-ONE DL supplies cropped ROI images. Two complete passes cover 174 images and 348 unique image-model pairs, not 696 subjects. The first pass pre-audited references and saved metrics only; an explicitly exploratory second pass saved all 348 masks before re-scoring, enabling independent pixel arithmetic. First-pass pixel identity cannot be checked.
- Ruling: Chaksu's original frozen endpoint is conditional vCDR error. The all-mask Dice addendum was frozen before reference inspection; a separate technical segmentation-event supplement was declared after partial reference scoring and remains post hoc, without changing the original endpoint, queue or model.
- Product defect ledger: five observed failing reader-isolation cases, one missing-reference-image omission case and two CRC corruption cases were corrected. Eight new regressions and the original suite pass together: 388 passed, two existing CUDA warnings, 646.75 seconds. Prior frozen evidence remains valid (61 payloads, six manifests).
- PAPILA final proof: all 2,548 masks, both-reader scores, 52 aggregates, 312 patient-bootstrap comparisons and 234 budget outputs passed independent arithmetic/integrity checks. All 196 original predictions and 1,176 old metrics reproduced exactly. The verifier's initial split-envelope parser error was corrected and disclosed without changing experiment artifacts.
- External proof: 672 Chaksu masks and 3,284 Dice-row aggregates checked, plus fresh 30-image/300-reference-raster pixel QA and all queue arithmetic; old common 311 statuses/metrics exactly match. RIM all 348 saved masks and 348 PNG/TXT pairs checked; first/second metrics/statuses match, all-event endpoint saturated and no queue benefit claimed.
- Publication proof: product source commit `a3d8040` equals tested Windows bytes after Git CRLF normalization; Python ASTs match. Frozen evidence retains raw bytes. No product source behavior changed after the 388-test run.
- Final whole-branch review: no open Critical/Important/Minor finding; fresh-directory setup and queue-table scope clarifications corrected. The remaining remote publication gate is represented by the PR checks rather than a claim that local testing already proves remote CI success.

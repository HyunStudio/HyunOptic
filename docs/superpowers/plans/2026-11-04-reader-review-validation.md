# Reader sensitivity and review-budget validation

> Execute inline using superpowers:executing-plans. User approved the proposed experiments and subsequent bug remediation on 2026-11-04; continue without an additional approval round.

**Goal:** Evaluate frozen baseline-43 and photometric-43 models against both PAPILA readers and compare the existing image-only review ordering with random review.

**Architecture:** Keep trained bundles and earlier evidence immutable. A new reproducible experiment writes private masks/identifiers under ignored reports and exports only aggregate evidence. Shared pure review-ordering and budget calculations are verified on hand-derived cases, then used by the experiment and UI where appropriate.

**Spec:** The preceding user-approved proposal: reader sensitivity, fixed review-budget error detection, and external exploratory follow-up; fix demonstrated bugs without changing trained models or tuning on test outcomes.

**Constraints:** Existing feature branch codex/submission-review-workflow, clean starting HEAD 05040ba. Continue in this established checkout to retain private datasets and model environment. No new dependencies, new training, clinical claims, patient imagery publication or author contact. Preserve all failures and original denominators. References never enter prediction or priority. Both eyes remain clustered by patient. Actual clinical workflow benefit is outside this offline evaluation.

## Tasks

- [x] 1. Test-first shared ordering/budget utilities. Error before invalid geometry before descending mask disagreement, stable ties by ordinal, no reference access. Exact random expected detections k*positives/n; no-positive recall null, no remaining cases risk null, missing outcomes excluded explicitly. Budget fractions 0, .1, .2, 1. Invalid score/budget/outcome inputs rejected. UI uses the same ordering.
- [x] 2. Freeze an execution protocol before predictions. Evaluate all 98 holdout images/49 patients, two frozen models, no transforms. Verify bundle, source fingerprint and identical split before execution. Save each prediction before loading reader references. Report each reader separately, paired reader changes, reader warning/failure counts, common-case vCDR, patient-cluster intervals, research threshold min(Dice)<.5 with .4/.6 sensitivity. Review targets include model failures; also report valid-prediction-only error detection to expose failure-first effects.
- [x] 3. Reanalyse previously saved Chaksu evaluations for expert sensitivity if compatible private per-image rows exist. Do not present reanalysis as new external inference or use vCDR differences as mask disagreement. Report limitations if mask artifacts needed for the same queue evaluation are unavailable.
- [x] 4. Investigate observed issues with regression reproduction before fixes. Verify relevant and whole product suite; independent final review of changed code and numerical/evidence boundaries. Publish new aggregate report with SHA256 manifest in a new dated folder. Commit on current feature branch; no main merge.

## Review focus

Missing outcomes must not become false negatives or silently disappear. Successful geometry is not segmentation correctness. Failed predictions must not improve risk by disappearing. Budget ties must match UI. Two eyes are not independent patients. Shared-mask hash validation must use the decoded bytes that were checked. No random-baseline simulation interval is a patient uncertainty interval.

## Execution ledger

Starting state: clean branch at 05040ba. Ruling: reuse current feature checkout, not a second checkout — existing authorized development context contains ignored data and verified bundles; no other dirty work was present.


Completed: 196 new predictions for 98 eyes/49 patients; 336 preserved external records per model reanalysed. TDD verified UUID tie bug, verified-byte race/suppression, and NumPy scalar serialization. Final suite 308 passed, 2 existing CUDA warnings in 213.21 seconds. Independent review: 990 internal aggregate comparisons, 36 external scalar comparisons; all 196 mask hashes and 1456 numeric checks independently verified with difference zero. Ruling: external review ranking not fabricated from vCDR-only saved rows; mask artifacts were unavailable, so external results are reader-sensitivity reanalysis only. Cost: no new external mask-ranking conclusion. First aggregate-write failure retained; recovery performed no new inference. Reviewer reporting concerns resolved in README (image vs patient estimands; failure history).

# Validation record — 2026-11-03

The new feature is research software. These checks establish workflow behavior; they do not establish clinical reliability, transfer accuracy or reduced review time.

## Actual local model integration

Windows, Python 3.12.10, PyTorch 2.13.0+cu126; the review runner performs CPU inference. The existing seed-43 baseline and photometric follow-up were verified using full bundle identities. Two locally available PAPILA images and one deliberately unreadable input were imported.

| Observation | Actual result |
| --- | --- |
| Input cases | 3 |
| Completed cases | 2 |
| Error cases | 1, unreadable input retained |
| Stored model predictions | 4 |
| Held review persisted across reopening store | Yes |
| Evidence ZIP verification | Passed, 6 payloads plus manifest |
| Processing wall time for the two real images | 24.21 seconds on this machine |

This was an execution smoke check using existing models, not new training or an accuracy assessment. It is not a speed guarantee or a participant study. Input identifiers, images, masks and local files remain private under ignored `reports/submission_20261103/`; no patient imagery accompanies this report.

## Software verification

The baseline suite passed 207 tests before these changes. The final integrated suite on the completed implementation passed **274 tests in 382.37 seconds**, with two existing PyTorch CUDA nondeterministic-kernel warnings. No test failed. New tests cover nested input changes, full bundle identity, unsupported contracts, single-frame limits, store transactions and revisions, artifact tampering, runner recovery, safe ZIP verification, and Streamlit review interaction.

- A synthetic 100-case batch retained 99 completed cases, one unreadable input, 198 model outputs and a held decision through interruption and reopening. Predictors in this test are explicit synthetic adapters; this is not 100-image real-model performance evidence.
- Independent scoped re-review passed 23 store/UI tests, including a threaded active-recovery race reproduction which now rejects the stale worker and preserves the newer held decision.
- `compileall`, staged/working-tree whitespace checks and the new export verifier CLI smoke check passed.
- All four preserved real-data bundles passed stricter verification without modifying their bytes.

Independent review found an active-recovery overwrite race, derived previews on changed source pixels and silently dropped stale form submissions. Regression tests were first observed failing, then fixes added processing ownership tokens, suppressed invalid evidence, and pinned the displayed revision with an explicit conflict response.

Frozen university evidence verification passed for 25 files and both preserved runners, both on disk and in staged Git blobs. These historical evidence files were not changed. Remote CI results, if any, are separate from the local results recorded here.

## Supported limits

Model disagreement ranking has not undergone a new independent dataset evaluation. No error-detection recall or user-time benefit is claimed. The queue can miss cases where both models agree incorrectly. The existing model transfer studies remain prior evidence with their original denominators and limitations.

Application accessibility features are present, but a formal accessibility audit and a study involving visually impaired users have not been completed. No public demonstration video or Devpost submission is implied by passing software tests.

## Subsequent issue remediation — 2026-11-03

ReviewStore now derives new successful predictions' measurements from the stored class map, downgrades empty masks, withholds failed measurements and validates error metadata. Ten regression checks failed before the correction and pass afterward. The final expanded suite passed **284 tests, 2 existing CUDA warnings, 323.06 seconds**. Existing frozen study results were not rewritten. See the [issue remediation report](../experiments/2026-11-03-issue-remediation/README.md) for the separately isolated DDU/CalDiff patches and their limited, nonclinical checks.

## Reader sensitivity and review evaluation — 2026-11-04

The final suite passed **308 tests, 2 existing CUDA warnings, 213.21 seconds** after new regression failures were reproduced and fixed. Review-priority ties now use input ordinals rather than random case UUIDs. Mask decoding uses the same bytes whose SHA256 was checked; a subsequent integrity error from priority verification withholds predictions and invalidates review evidence. Disagreement scores return native Python floats so ordinary threshold counts can be serialized to JSON. New review-budget helpers retain all-case budgets, missing-outcome counts and exact uniform-random expected detections.

An exploratory rerun generated 196 frozen-model predictions for all 98 previously evaluated PAPILA holdout images from 49 patients. Both-reader metrics, patient-cluster intervals, fixed review budgets and a separate reanalysis of preserved Chaksu records are in the [new report](../experiments/2026-11-04-reader-review-validation/README.md). All 196 stored mask digests and 1,456 independently calculated numeric comparisons passed (maximum difference 0.0). Independent review checked 990 aggregate comparisons and 36 external reanalysis values. The initial new experiment aggregate write failed on a NumPy int64 and was recovered from retained predictions without new inference; this harness failure is explicitly preserved in the report. No clinical utility, independent generalization, calibrated uncertainty or review-time improvement is established.

## Submission-readiness audit — 2026-11-04

The expanded final local suite passed **326 tests, 2 existing CUDA warnings, 207.80 seconds** after demonstrated preview replacement, upload-limit and unreadable-input UI regressions were corrected. An isolated clean-source clone reused installed dependencies and prepared two actual CPU-trained synthetic models. The actual browser workflow and separately verified downloaded ZIP passed. Ordinary/repeated runs, a controlled interrupted 100-case repeated-image batch and copied-bundle hash failure matched expected outcomes. The repeated batch is not a new patient cohort or clinical test. [Detailed evidence, expected/actual values, actual captures and exact independent-review scope](../experiments/2026-11-04-submission-readiness/README.md).

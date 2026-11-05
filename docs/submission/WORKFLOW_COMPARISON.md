# The same review task, with and without HyunOptic

This is a concrete comparison of steps and records, **not a timed experiment or participant study**. No completion-time, error-reduction, clinical or reviewer-efficiency result is claimed. The manual method can be automated or improved; its tools are not inherently incapable of traceability.

## Fixed task and inputs

Use one permitted source image, its two **existing** prediction masks from identified models, their model/input hashes and supported measurement protocol. Inspect both boundaries against the same source, mark the case held with a reason, resume it after closing the tools, then assemble and independently verify a privacy-filtered evidence ZIP. Neither method includes training time. HyunOptic normally produces predictions from two local bundles; that inference step is additional preparation, not a shortcut credited against this manual comparison. It is not a general importer for arbitrary prediction masks.

| Task | Defined manual method | HyunOptic workflow |
| --- | --- | --- |
| Identify the evidence | Record the source identifier, model identifiers and SHA-256 hashes; check files against that record. | Verified local bundles and retained inputs carry identity. Selected detail and consequential actions validate the relevant evidence; export validates the full snapshot. A metadata list alone is not a fresh integrity audit. |
| Inspect the image | Open the source plus both masks in an image viewer, align their coordinates and create overlays. Check which model produced each mask. | Open the selected case and inspect the source and the two identified model overlays. Aligned comparison/full-size views were observed in the November 5 browser acceptance; source/model identities remain attached. |
| Decide and record | Enter case ID, state, reason and optional private note in a spreadsheet; keep rows linked to the right files and model versions. | Save reviewed or held state with a reason. A human makes the decision; the software does not certify anatomy. Save + next stored the held decision and advanced to the next case in the November 5 browser check. |
| Resume | Reopen the viewer/files and spreadsheet; check that the selected row still corresponds to the same evidence and latest decision. | Reopen the stored session and case. Decisions persist; revision checks reject stale saves. If processing was interrupted, explicitly recover unfinished cases before continuing. |
| Package | Create a shareable spreadsheet/table copy, omit private fields and originals/masks, collect provenance and hash records, and create a ZIP. Inspect its contents for unwanted private material. | Build the default evidence ZIP from the verified session. Originals, masks, filenames, paths and private notes are excluded by default. A downloaded ZIP is a separate retained copy. |
| Verify | Recompute payload SHA-256 values and compare the complete payload set, lengths and records to the intended snapshot. Resolve differences. | Run `python -m hyunoptic.review.export path/to/evidence.zip` separately, and inspect the intended states and provenance. Verification checks consistency, not scientific truth or anonymity. |

The integrated benefit is fewer separately maintained links between evidence, decisions and export records. Whether this improves a person's speed, correctness or workload is unmeasured. Integrity checks in either method do not replace human inspection, establish independent patient counts or validate a model in a new domain.

## Evidence boundary

The [historical browser audit](../experiments/2026-11-04-submission-readiness/README.md) demonstrated synthetic processing, hold/reopen and export/verification at its own source version. The [404-test distribution audit](../experiments/2026-11-04-submission-code-audit/README.md) is the completed software baseline. The [current browser acceptance](../experiments/2026-11-05-final-acceptance/README.md) records actual aligned layout, save-next, reload, keyboard save and ZIP download. The [earlier software audit](../experiments/2026-11-04-review-usability/README.md) retains its own metadata/detail benchmarks; native 200% zoom remains unverified.

A future human comparison would need a stated task, identical evidence, participant/sequence details and observed results. Engineering latency benchmarks on 20/200 synthetic inputs measure software operations only and cannot be reported as human time savings. This document does not claim such a study has happened.

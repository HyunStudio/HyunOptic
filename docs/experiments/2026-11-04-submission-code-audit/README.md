# Submission Git, distribution and lifecycle audit — 2026-11-04

This audit starts from main `35ee360b9edbca97b52b88b04a1e674783fcf909`. It supplements the [previous browser/source check](../2026-11-04-final-submission-polish/README.md); it does not repeat clinical evaluation, browser automation or video publication. All work is pre-event.

## Reproduced defects and corrections

| Boundary | Observed defect | Correction |
| --- | --- | --- |
| Image import | A small malformed PNG raised Pillow `SyntaxError`; a malformed TIFF raised `TypeError`. Either rolled back a batch containing a valid neighbor. | Normalize known decoder errors to `ValueError`; keep the valid input pending and the malformed input visibly failed. |
| Deletion/export | Export paused after verification, session deleted through a second store connection, export resumed: a valid managed ZIP reappeared for a nonexistent session. | Check session existence and publish while holding the same SQLite writer lock used by deletion; remove the temporary ZIP after rejection. |
| Provenance | The installed 1.2.0 CLI wrote version 0.2.0 in its image-level report. | Read the shared package version. Historical reports are not rewritten. |
| Evaluation labeling | Synthetic=true / partial=false produced a non-exploratory holdout report rejected by its own reader. | Synthetic or partial status always forces exploratory; preserve repeat reasons and real/full controls. |

Fourteen regression cases were added. The six import/export/version cases and the synthetic-only evaluation case were observed failing before their fixes; seven other evaluation combinations served as controls. An initial CLI test used an invalid draw count (10), was corrected to 30, and then failed on the intended version assertion before production correction. No test execution is counted as new patient/model-performance evidence.

## Verification and scope

See `verification.json` for measured suite/install/demo outcomes, `git_audit.json` for the baseline remote-head/asset inventory, and `independent_review.json` for review scope. These files are covered by `manifest.json`; this explanatory README is not frozen.

The base wheel was built from an anonymous clean clone and installed non-editably in a new Python 3.12 virtual environment with `include-system-site-packages=false`. All 15 console entry points printed help without PyTorch or Streamlit, and the base synthetic CLI reproduced the version defect. The corrected wheel was built from the clean clone plus the reviewed source changes. All 71 packaged Python modules were compared with the tested source using LF normalization. Corrected CLI execution outside the source directory used `site-packages`, not editable source.

The inspected baseline contained 484 tracked files. All 11 then-live remote heads were already ancestors of main; no omitted contribution required merging and no branch was deleted. No accidental weights/private database/source image payload was found in reachable Git objects. The intended synthetic browser evidence ZIP contains seven text-report entries. The demonstration MP4 remains the intended approximately 4.5 MB submission asset.

The bounded decoder probes included 4,500 synthetic PNG/JPEG/TIFF mutations. This is a limited robustness probe, not a security certification or exhaustive parser test. Explicit external export copies retain their existing lifecycle; managed export deletion is the tested contract. Previously downloaded copies cannot be recalled.

No real images, model weights, private session databases, patient identifiers or raw workstation paths are published here. Frozen research evidence, model/default policy and severe external-transfer limitations remain unchanged. Passing software checks does not establish clinical reliability or organizer acceptance.

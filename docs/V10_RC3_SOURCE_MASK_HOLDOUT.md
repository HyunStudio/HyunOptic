# HyunOptic v1.0.0rc3 — PAPILA Source MASK Holdout Before Chákṣu External Test

**Date:** 24 October 2026 · **Stage:** software evaluation infrastructure, NOT completed real-data research.

## Scientific gap fixed

Earlier versions learned a frozen, *unlabeled* score standardization from PAPILA first-reader development images and applied that scoring family to Chákṣu Test. However, the PAPILA internal validation and holdout metrics previously used an **older polygon-contour feature family**, which is NOT comparable to the new shared-mask feature family. This left a gap: did the exact score proposed for external transfer work at all on its own source cohort?

rc3 adds a new pre-external **PAPILA source mask heldout benchmark**, using precisely the same features and frozen model settings as Chákṣu external Test:
- first expert's original fundus image and disc/cup polygons, converted to masks at original image size;
- vCDR, fixed-scale Q95 negative control, mask boundary roughness, mask boundary weakness;
- the *existing* source-development mean/SD and fixed equal-weight combined score;
- second expert contours loaded and measured **only after candidate scoring**, on **validation and holdout** images, never source-development images.

PAPILA development, validation and holdout still use fixed patient-level 60/20/20 partitions; both eyes of a participant remain in one partition. No holdout labels are used to fit the scoring function.

## Data integrity added

The old PAPILA metadata fingerprint used paths and file byte sizes, which cannot detect a same-length change inside an annotation. rc3 computes an additional **streaming SHA-256 fingerprint of the CONTENTS** of each direct fundus image and contour file and binds it into the newly frozen model.

A later source holdout run refuses the dataset if the content digest changes, even when a contour is replaced with the same-sized file. The digest:
- is computed locally, reading raw image and contour bytes in chunks;
- does not upload images or open private clinical spreadsheets;
- is deterministic across Windows/Linux for identical file bytes;
- is **not** an official publisher signature or proof of annotation validity.

**Older frozen PAPILA model locks lack this checksum, so re-freeze from original source with rc3 before running the new source holdout.** Chákṣu's original external protocol remains defined by a locked model source, and research settings are not retuned.

## Research-only endpoints

For source *validation* and *holdout* groups, separately:
- retrospective `abs(vCDR_exp1 - vCDR_exp2) > 0.10`, research threshold only;
- fixed precision and recall at a 20% annotation-review budget;
- average precision and ROC-AUC for **reader disagreement**, not disease status;
- same-image precision@budget difference: frozen combined candidate score minus simple vCDR;
- exploratory **paired patient-group bootstrap percentile interval** for that difference on the source holdout (patient grouping is known in PAPILA).

The Q95 perturbation baseline remains a scaled version of vCDR for fixed perturbation parameters. Statistical results must include negative differences and undefined metrics without imputing positives.

## Running the exact source → external chain

First review source licensing, obtain official PAPILA images/contours and the original Chákṣu Test.zip locally. Keep original data outside your public repository.

```powershell
git pull
python -m pip install -e ".[ui,dev]"
pytest -q

# 1. New immutable source lock, with actual CONTENT fingerprint.
hyunoptic-external freeze --papila-root "D:\\datasets\\PAPILA" --output "reports\\rc3\\papila_mask_lock.json"

# 2. Evaluate that SAME frozen mask scoring family on PAPILA's untouched
#    patient-disjoint validation and holdout groups, BEFORE external testing.
hyunoptic-source-check --papila-root "D:\\datasets\\PAPILA" `
  --model-lock "reports\\rc3\\papila_mask_lock.json" `
  --output-dir "reports\\rc3\\source_holdout"

# 3. Preflight all five Chákṣu expert masks in Test.zip.
hyunoptic-chaksu-audit --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" `
  --output-dir "reports\\rc3\\chaksu_audit" --strict

# 4. Evaluate original Chákṣu Test with exactly the same source lock.
hyunoptic-external test --model-lock "reports\\rc3\\papila_mask_lock.json" `
  --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" `
  --output-dir "reports\\rc3\\external"
```

Run `streamlit run app.py`, then select the new **Source Holdout** page and open `reports/rc3/source_holdout/source_aggregate.json`. The older **External Validation** page reads external aggregate JSON as before.

Run the full archive SHA-256 provenance tool and PAPILA inventory separately, then the updated evidence gate with **six** inputs:

```powershell
hyunoptic-evidence `
  --sources "reports\\rc3\\sources.json" `
  --papila-inventory "reports\\rc3\\papila_inventory.json" `
  --model-lock "reports\\rc3\\papila_mask_lock.json" `
  --source-holdout "reports\\rc3\\source_holdout\\source_aggregate.json" `
  --chaksu-audit "reports\\rc3\\chaksu_audit\\audit_aggregate.json" `
  --external-aggregate "reports\\rc3\\external\\external_aggregate.json" `
  --output "reports\\rc3\\evidence_review.json" --strict
```

The `sources.json` and `papila_inventory.json` files above must be generated first by `hyunoptic-verify-sources` and `hyunoptic-inventory`, respectively, as documented in [rc2](V10_RC2_EVIDENCE_REVIEW.md).

## Outputs and sharing

`hyunoptic-source-check` writes:
- `source_aggregate.json`: patient-aggregated split counts, heldout metrics, fixed model digest, bootstrap result, warnings, without case identifiers.
- `source_private_cases.json`: per-image candidate scores, reference disagreements and original image/patient IDs. **Do not publish without reviewing dataset terms and ethics.**
- `source_summary.md`: manuscript-style aggregate table for each split, with explicit research disclaimer.

Source and external results must not be portrayed as independent *clinical* disease prediction. The source heldout is still from one dataset; Chákṣu external Test uses a different image population and acquisition devices, but subject-level linkage in Chákṣu is not fully known. No clinical diagnosis claim is supported.

## Acceptance boundaries

- Synthetic unit tests and CI demonstrate software behavior, **not** that the original 488 PAPILA eyes and 336 Chákṣu Test images have been successfully processed.
- A matching SHA-256 digest proves input bytes stayed the same within an experiment, not that source annotations are correct.
- Source holdout rank improvement must not be used to retune the combined score and call the identical holdout confirmatory.
- An externally locked method can fail on a new device or cohort; report this clearly if it occurs.
- For academic writing, compare performance to established segmentation QC literature before claiming novelty or clinically meaningful benefit.

## Original dataset links

- PAPILA source: https://figshare.com/articles/dataset/PAPILA/14798004
- Chákṣu external: https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135

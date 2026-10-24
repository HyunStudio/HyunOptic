# HyunOptic v1.0.0rc2 — Evidence-Package Readiness Review

**24 October 2026 | Status: software verification only.** This release candidate does NOT establish original PAPILA/Chákṣu dataset scientific results, superior annotation reliability, clinical utility, or glaucoma diagnostic accuracy.

## Why this additional gate exists

The source data are large (PAPILA original ZIP approximately 563 MB; Chákṣu Test archive much larger), and source identity, source lock, annotation inventory, and the external research output are currently checked by separate tools. A valid individual JSON file is insufficient to tell whether all experiment artifacts refer to compatible original data and the same frozen model.

`hyunoptic-evidence` now verifies the **consistency of five local JSON artifacts** without processing fundus images, personal health records, or individual eye measurements. It returns a clear *incomplete* status when any artifact is missing or fails.

This is a **checklist automation** and a tamper-detection aid, **not an independently signed certification, clinical validation, or proof that the scientific hypothesis is correct**. A user can fabricate compatible JSON files: code cannot prove scientific validity by itself.

## Five required inputs

| Input | Local generator | Necessary properties |
|---|---|---|
| Archive provenance | `hyunoptic-verify-sources` | Local archive SHA-256 equals independently indexed public reference for PAPILA AND Chákṣu Test |
| PAPILA inventory | `hyunoptic-inventory` | 244 patients, 488 eyes and structural full-inventory match |
| Frozen scoring model | `hyunoptic-external freeze` | Original-source model lock with intact content SHA-256, not a partial sample; source development features only |
| Chákṣu preflight | `hyunoptic-chaksu-audit` | 336 Test images successfully checked against all five expert masks with zero structural errors |
| External study aggregate | `hyunoptic-external test` | 336 scored Test images, no skipped cases, same model-lock hash, no fused annotations, reader disagreement endpoint |

An additional check compares the PAPILA filename/size fingerprint in the inventory and the frozen model. The fingerprint does **not** cryptographically attest to all uncompressed patient data, and there is no independently signed audit.

The SHA-256 references are from [fundus-atlas](https://github.com/staskh/fundus-atlas), an independent public dataset index, not signatures published by the data custodians. A new legitimate dataset revision may differ; compare official version numbers before concluding an integrity problem. The strict package gate intentionally requires a matching indexed version.

## Windows commands after obtaining the official datasets

```powershell
git pull
python -m pip install -e ".[ui,dev]"

# 1. Locally hash source archives. Neither archive is uploaded.
hyunoptic-verify-sources --papila-zip "D:\\datasets\\PAPILA.zip" --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output "reports\\rc2\\sources.json" --require-reference-match

# 2. Verify original, locally extracted PAPILA.
hyunoptic-inventory --papila-root "D:\\datasets\\PAPILA" --output "reports\\rc2\\papila_inventory.json" --strict-full --verify-pixels

# 3. Freeze source-only scoring from PAPILA development split.
hyunoptic-external freeze --papila-root "D:\\datasets\\PAPILA" --output "reports\\rc2\\papila_lock.json"

# 4. Check all five original Chákṣu human masks per Test image.
hyunoptic-chaksu-audit --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\rc2\\chaksu_audit" --strict

# 5. Run external reader-consistency study without retuning the source lock.
hyunoptic-external test --model-lock "reports\\rc2\\papila_lock.json" --chaksu-test-zip "D:\\datasets\\Chaksu\\Test.zip" --output-dir "reports\\rc2\\external"

# 6. Audit all five research-provenance artifacts together.
hyunoptic-evidence --sources "reports\\rc2\\sources.json" --papila-inventory "reports\\rc2\\papila_inventory.json" --model-lock "reports\\rc2\\papila_lock.json" --chaksu-audit "reports\\rc2\\chaksu_audit\\audit_aggregate.json" --external-aggregate "reports\\rc2\\external\\external_aggregate.json" --output "reports\\rc2\\evidence_review.json" --strict
```

The final gate writes `evidence_review.json`. Exit status `0` means all metadata cross-checks passed. Exit `2` means a missing or inconsistent prerequisite **when `--strict` is enabled**. It does **not** mean the independent scientific results were positive. Missing/invalid input files can also cause a parser error.

## New repeated-patient warning from Chákṣu filenames

An independent public Chákṣu archive reader documents Bosch filenames such as `P11_image_1` and `P11_image_2` as potentially multiple images of the same subject. The ZIP scanner now reports *counts only*:

- `images_with_partially_decodable_patient_id`
- `known_repeat_patient_groups`
- `images_in_known_repeat_groups`

Other filenames can omit patient linkage, so **zero counted repeats does NOT guarantee independent observations**. Do not calculate or publish naive per-image independent patient confidence intervals on Chákṣu based on this weak information.

Source: https://github.com/staskh/fundus-atlas/blob/main/src/datasets/chaksu.py

## Sign-off limits

The gate explicitly and permanently sets:
- `scientific_validity_established = false`
- `clinical_accuracy_established = false`

The gate can help assemble a complete reproducibility package, but it cannot decide whether a fixed-score difference is statistically robust, novel, useful or generalizable. Those require **real patient data results and independent methodological review**. It also cannot prove a JSON document genuinely came from a particular execution.

**Next scientific milestone:** Obtain the official archives under distributor terms; execute the independent inventory + source lock + Chákṣu preflight + original external evaluation; review case exclusions, device heterogeneity, effect magnitudes and domain shifts; publish an honest negative result if appropriate.

## Sources

- [PAPILA official download](https://figshare.com/articles/dataset/PAPILA/14798004)
- [Chákṣu official download](https://figshare.com/articles/dataset/Ch_k_u_A_glaucoma_specific_fundus_image_database/20123135)
- [Original PAPILA descriptor](https://doi.org/10.1038/s41597-022-01388-1)
- [Original Chákṣu descriptor](https://doi.org/10.1038/s41597-023-01943-4)

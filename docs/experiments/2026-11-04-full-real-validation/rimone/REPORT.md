# RIM-ONE DL: frozen external segmentation evaluation

**Both frozen models showed severe failure on the dataset-supplied cropped-ROI domain.** Baseline invalid geometry was 160/174 and camera-robust invalid geometry 132/174; baseline measurable-only vCDR MAE must be read with its 14/174 coverage. No tuning or model promotion followed.

Completed the full official hospital-heldout test partition: **174 distinct image files, 118 normal and 56 glaucoma**. The random variant and hospital training partition were not evaluated or counted as extra samples. In the original pass both pre-existing PAPILA-trained models ran once, frozen, without training, tuning or manually generated crops.

This is exploratory external segmentation testing, **not a reproduction of the RIM-ONE DL classification benchmark** and not comparable to its RIM-only-trained leaderboard. No glaucoma classification AUC, sensitivity or accuracy is claimed.

## Results

| Frozen model | Selected / valid references | Disc Dice, mean | Cup Dice, mean | vCDR MAE | Measurable vCDR / valid / selected | Prediction status counts |
|---|---:|---:|---:|---:|---:|---|
| papila_real_seed43_20261025 | 174 / 174 | 0.012226 | 0.001826 | 0.218528 | 14 / 174 / 174 | {'invalid_geometry': 160, 'ok': 14} |
| papila_camera_robust_seed43_20261025 | 174 / 174 | 0.018380 | 0.006450 | 0.237220 | 42 / 174 / 174 | {'ok': 42, 'invalid_geometry': 132} |

All Dice values are macro averages at each supplied image's original pixel resolution, including empty or invalid prediction masks. A missing prediction is scored as empty for Dice; no failure is silently dropped. vCDR is an axis-aligned pixel-span ratio; it is reported only where both disc and cup can be measured, with the measurable denominator shown explicitly. Full descriptive distributions and deterministic image bootstrap intervals are in aggregate.json; these intervals do not account for patient clustering.

## Reference and scope limits

- All 174 selected images had validly shaped, nonempty, binary official disc and cup PNG masks. There were zero missing/shape/binary reference failures.
- One official reference has 46 cup pixels outside its disc. The raw masks were retained and the warning recorded separately; no reference repair or exclusion was applied. A descriptive no-warning vCDR sensitivity result is saved separately in independent_numeric_verification.json.
- The official dataset images are already square crops around the optic nerve head, rather than whole-fundus photographs. This changes optic-disc scale and field of view relative to PAPILA. The harness applies only the existing image-only bundle preprocessing; it does not derive a crop from the reference.
- The paper describes removal of duplicates/test-retests and one image per patient and eye. An authoritative patient-to-image linkage table was not verified, so the denominator is 174 images, not 174 independently verified patients. Patient-level confidence intervals are not available.
- The official masks represent one glaucoma expert reference per image, so this dataset cannot estimate independent inter-reader uncertainty.
- This evaluates technical segmentation transfer under a material image-domain change. It establishes neither clinical utility nor safety for medical decisions.

## Provenance and permitted use

Official repository: https://github.com/miag-ull/rim-one-dl ; archived source commit: 5f56b8c9957656282c2d00d40fc420a850bd1fe4. Official author-linked assets were obtained from https://bit.ly/rim-one-dl-images and https://bit.ly/rim-one-dl-reference-segmentations . No mirrors or alternate datasets were used.

Official terms allow free research/educational use without asking the authors, and prohibit redistribution and unauthorized commercial use. Data, IDs, masks, model weights and individual results remain local in ignored directories. Do not publish those artifacts.

Citation: Fumero Batista FJ et al. RIM-ONE DL: A Unified Retinal Image Database for Assessing Glaucoma Using Deep Learning. Image Analysis & Stereology 39(3):161–167 (2020). https://doi.org/10.5566/ias.2346 ; official paper: https://www.ias-iss.org/ojs/IAS/article/download/2346/1128/6451 .

Images archive: 222,561,134 bytes; SHA-256 85aed5f95c794f52d11b6ed953032108a66576ffcff4b587365df467491b603d. Reference archive: 1,608,386 bytes; SHA-256 edc363b1f0deabc8ed7a356250a9e1fb21825bf06f7337889fd1e764e1947901.

## Reproducibility and checks

The first pass included a complete reference pre-audit and frozen manifest before inference. It was not blind to reference labels. Both models and their image-only processing were already frozen, and no tuning followed. The supplemental pass was explicitly exploratory after those results were known.

Protocol frozen at 2026-11-04T07:31:14.355125+00:00; model identities, archive hashes, all selected image/mask payload hashes, and harness/source hashes were fixed before inference. Inference started at 2026-11-04T07:32:06.753345+00:00. Both checkpoints were verified and loaded with the existing restricted weights_only loader. CPU threads were fixed to two.

Independent verification recomputed macro means from saved individual records, checked complete one-to-one accounting of all 174 images per model, verified finite bounded Dice values, and confirmed protocol timing and vCDR denominators. This is independent arithmetic/accounting verification, not an independent inference implementation or raw predicted-mask recomputation.

Local commands from repository root:

```powershell
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py prepare
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py run
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/audit_references.py
.venv/Scripts/python.exe reports/full_validation_20261104/new_external/verify_numeric.py
```

prepare/run deliberately refuse to overwrite an existing frozen protocol or silently rerun predictions. Existing outputs must be preserved; any authorized rerun requires a separately identified output/protocol.

Artifact index: protocol.json (frozen evaluation rules/identities); provenance.json and images_confirm_download.json (source/HTTP/size/hash records); access_attempts.json (initial access responses and article-page timeout); input_manifest.json and *_individual.jsonl (private IDs, never publish); reference_failures.json and independent_reference_audit.json (reference accounting); *_aggregate.json / aggregate.json (safe aggregate metrics); independent_numeric_verification.json (arithmetic audit). evaluate_rimone.py is the standalone harness; official conversion files are archived only for format provenance, with the supplied PNG masks used directly.

## Supplemental artifact verification

### Fresh independent full-cohort review

A separate reviewer recalculated all 348 saved prediction masks, both models' overall and normal/glaucoma subgroup statistics, bootstrap summaries and review budgets. All checks passed; available first/second-pass statuses, errors and metrics matched exactly. First-pass pixel identity remains untestable because those masks were not saved.

The separate coordinate audit extended the first-three check below to **all 348 disc/cup PNG/TXT pairs**. Every TXT center agreed with PNG foreground, checked corners were background, and all **5,568 contour points** were within one pixel of the mask boundary. This supports polarity/coordinate interpretation without asserting complete interpolation equivalence. See [independent verification](rim_independent_verification.json) and [source review](rim_source_scope_review.json).

Conditional vCDR means on 14 baseline eyes and 42 comparison eyes cannot rank the models. On exactly **two common measurable eyes**, MAE was 0.15833 versus 0.14890; this tiny descriptive subset cannot establish superiority. [Common-case comparison](rim_paired_comparison.json). Both models retain severe transfer failure on the supplied ROI domain.

The artifact index describes the local execution record; individual rows, coordinates, masks, image IDs and QA montage remain private. [Fresh-directory setup and copyback instructions](PUBLIC_REPRODUCTION.md) preserve frozen harness bytes.

### Original supplemental execution

A separately frozen exploratory follow-up protocol was created at 2026-11-04T07:42:34.484532+00:00, after original GT results had already been inspected. It repeated the complete 174-image evaluation with both unchanged models (348 additional inferences), persisting **348 original-resolution label PNGs plus SHA-256 hashes**. All 348 prediction artifacts were complete before computing the image-only queue, and all 174 priorities were frozen before the supplemental script first loaded reference rasters. No training, tuning, winner selection, new crop or original-output replacement occurred.

The two passes total **696 actual inferences over 348 unique image–model pairs and 174 images**. Replication does not add subjects. Independent boolean-pixel Dice and inclusive row-span vCDR calculations from saved PNGs reproduced the original individual statuses, errors and metrics for all 348 pairs: **0 discrepancies** at 1e-12 numeric tolerance. The raw label PNGs are private and must not be redistributed. This verifies the artifact-to-metric calculation; the same frozen inference implementation produced both passes.

Reference polarity/mapping was independently checked for the first 3 lexicographic test images (6 PNG/TXT pairs). Every TXT center lay in 255 foreground and all four corners in 0 background; each of the 16 official contour points was within 1 pixel of the corresponding PNG boundary using the official x/y-minus1 convention. Disc/Cup files were kept distinct and aligned to the supplied source image. This supports correct polarity and coordinates without claiming full TXT interpolation/rasterizer equivalence.

### Predeclared technical queue stress test

The supplemental protocol froze baseline technical research events as baseline error/invalid geometry OR min(discDice,cupDice) below 0.4, 0.5, or 0.6, with review budgets 10%, 20%, 50%. These are segmentation audit thresholds, not clinical outcome definitions. A missing reference remains unknown when baseline is otherwise valid; it is never counted negative. Existing review.priority and order_cases consumed only the two saved model predictions before reference scoring.

Image-only priority groups: {'invalid_geometry': 172, 'disagreement': 2}.

| Subgroup | Threshold | Images | Available outcomes | Positive events | Review budgets: detected / random expectation |
|---|---:|---:|---:|---:|---|
| All images | 0.4 | 174 | 174 | 174 | 10%: 18 / 18.000; 20%: 35 / 35.000; 50%: 87 / 87.000 |
| All images | 0.5 | 174 | 174 | 174 | 10%: 18 / 18.000; 20%: 35 / 35.000; 50%: 87 / 87.000 |
| All images | 0.6 | 174 | 174 | 174 | 10%: 18 / 18.000; 20%: 35 / 35.000; 50%: 87 / 87.000 |
| Both models geometrically valid | 0.4 | 2 | 2 | 2 | 10%: 1 / 1.000; 20%: 1 / 1.000; 50%: 1 / 1.000 |
| Both models geometrically valid | 0.5 | 2 | 2 | 2 | 10%: 1 / 1.000; 20%: 1 / 1.000; 50%: 1 / 1.000 |
| Both models geometrically valid | 0.6 | 2 | 2 | 2 | 10%: 1 / 1.000; 20%: 1 / 1.000; 50%: 1 / 1.000 |

All 174 images satisfy every predeclared event threshold, including images where both models produced nonempty geometry. The endpoint is saturated: failure-first review has no incremental detection benefit over random review at these budgets. With no event-negative images, this dataset cannot establish research-event discrimination, specificity, AUROC, or clinical triage benefit. The small both-models-ok subgroup is explicitly counted separately and does not rescue the transfer result.

Supplemental artifacts: supplemental_verification/protocol.json; aggregate.json; predictions_complete.json; priorities_before_gt.json; scoring_started.json; first_vs_supplement_discrepancies.json; per-model predictions.json and independent_scores.json; private original-resolution label PNGs. supplemental_run.py contains the complete freeze/inference/queue/independent-pixel-scoring procedure. The private first-three-image QA montage is supplemental_verification/private_visual_qa_first3.png and is not a publication artifact.

A final standalone verifier (`final_verify_saved_masks.py`) passed all 348 saved raster/hash/shape/metric checks and all 174 actual priority checks, including prediction-metadata hashes, queue hash, frozen source hashes, and phase timestamps. See `supplemental_verification/independent_final_artifact_verification.json` and `final_phase_attestation.json`.

Private visual QA of the first three lexicographic images showed plausible aligned expert contours around the enlarged optic-disc ROI; the models produced tiny, misplaced fragments or empty geometry. This agrees with the negative quantitative result and the independent PNG/TXT polarity checks. The montage remains private; no images are included in this report.

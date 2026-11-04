# Fresh frozen-model Chaksu Test evaluation

All 336 images received two fresh image-only predictions: **672/672 original-resolution masks returned and verified**. Real model: 318 valid measurements and 18 invalid geometries; camera-robust model: 316 valid measurements and 20 invalid geometries. There were zero image-load/inference exceptions and zero missing prediction masks. All 38 invalid prediction geometries were empty predicted cups. No masks or references were repaired.

This is exploratory reuse of an already inspected Chaksu Test set and the same frozen models. It is neither untouched external confirmation, an author benchmark replication, nor clinical validation.

## Dice for every returned mask

This leading descriptive analysis includes invalid-geometry prediction masks. Each expert has its own valid-reference denominator. The original protocol’s successful-prediction-only Dice remains a conditional analysis in aggregate_public_safe.json; it must not replace these all-returned-mask results. The all-returned-mask analysis was added by timestamped addendum during image-only inference, before any reference outcome was opened.

| Expert | Valid references | Real disc Dice | Robust disc Dice | Real cup Dice | Robust cup Dice | Paired cup change, robust−real [image-IID 95% interval] |
|---|---:|---:|---:|---:|---:|---|
| expert 1 | 321 | 0.8678 | 0.8474 | 0.5734 | 0.5935 | +0.0200 [+0.0007, +0.0388] |
| expert 2 | 334 | 0.8391 | 0.8352 | 0.5578 | 0.5673 | +0.0095 [-0.0103, +0.0291] |
| expert 3 | 331 | 0.8522 | 0.8394 | 0.5431 | 0.5630 | +0.0199 [-0.0003, +0.0392] |
| expert 4 | 331 | 0.8363 | 0.8312 | 0.5629 | 0.5651 | +0.0022 [-0.0172, +0.0220] |
| expert 5 | 325 | 0.8363 | 0.8335 | 0.5477 | 0.5755 | +0.0278 [+0.0071, +0.0478] |

All-returned-mask Dice comprises 3,284 model–expert rows. Camera-specific results (Bosch 41, Forus 31, Remidio 264) and paired common-case differences are in supplement_public_safe.json. There is no pooling of five correlated experts as independent datasets.

## Reference failures and vCDR

Strict reference checks rejected 38 expert–image pairs across 25 images. Valid reference counts were 321, 334, 331, 331 and 325 for experts 1–5. These are reference failures, separate from prediction geometry failures over all 336 images. A bad expert never erased another expert or prevented a new prediction.

The protocol’s vCDR event is absolute error >0.10. An invalid prediction measurement or invalid reference is unknown for that model’s vCDR outcome. MAE therefore conditions on both a valid prediction measurement and a valid expert reference.

| Expert | Real vCDR n | Real MAE | Robust vCDR n | Robust MAE |
|---|---:|---:|---:|---:|
| expert 1 | 304 | 0.2553 | 302 | 0.1141 |
| expert 2 | 316 | 0.2329 | 314 | 0.1167 |
| expert 3 | 313 | 0.2580 | 311 | 0.1247 |
| expert 4 | 314 | 0.2332 | 311 | 0.1098 |
| expert 5 | 308 | 0.2770 | 306 | 0.1334 |

## Frozen app queue and original vCDR outcome

Actual app priority() and order_cases() ran on all 336 images before any reference bytes were opened. The queue has 29 invalid-geometry cases first and 307 disagreement cases; original input order resolves ties. Budgets are 34, 68 and 168 cases. For the either-model outcome, a known positive remains positive even if the other model is unknown; otherwise any unknown stays unknown.

| Expert | Available / missing | Known positives | 10% detected / reviewed unknown | 20% detected / reviewed unknown | 50% detected / reviewed unknown |
|---|---:|---:|---:|---:|---:|
| expert 1 | 305 / 31 | 269 | 15 / 19 | 46 / 21 | 135 / 26 |
| expert 2 | 318 / 18 | 281 | 18 / 16 | 50 / 16 | 139 / 17 |
| expert 3 | 312 / 24 | 281 | 15 / 19 | 47 / 20 | 142 / 23 |
| expert 4 | 315 / 21 | 273 | 17 / 17 | 49 / 18 | 137 / 21 |
| expert 5 | 306 / 30 | 279 | 12 / 22 | 44 / 22 | 135 / 26 |

These are detections among known outcomes; unknowns are not negatives. Full denominators, remaining known-event fractions, intervals and exact finite-cohort random expectations are reported for each model and either model in aggregate_public_safe.json.

## Post hoc technical-event supplement

A separately timestamped POST HOC exploratory addendum was written after partial reference inspection. It does not replace the original vCDR endpoint. The technical event is prediction error/invalid geometry, or min(disc Dice, cup Dice) below 0.4, 0.5 or 0.6. Prediction failures are positive without needing references; a valid prediction with an invalid expert reference stays unknown. All three thresholds and 10%, 20%, 50% budgets are reported without optimization or tuning.

The both-models-valid subgroup has 307 images. It filters the same frozen queue without reordering, with subgroup budgets 31, 62 and 154.

The table below reports **either-model events over all 336 images**, not the 307-image subgroup. The subgroup results are reported separately in the linked JSON.

| Threshold | Expert | Known positives | Available / missing | 10% detected | 20% detected | 50% detected |
|---:|---|---:|---:|---:|---:|---:|
| 0.4 | expert 1 | 72 | 322 / 14 | 32 | 59 | 67 |
| 0.4 | expert 2 | 82 | 334 / 2 | 34 | 63 | 76 |
| 0.4 | expert 3 | 85 | 331 / 5 | 34 | 62 | 77 |
| 0.4 | expert 4 | 80 | 332 / 4 | 34 | 62 | 75 |
| 0.4 | expert 5 | 84 | 326 / 10 | 32 | 61 | 76 |
| 0.5 | expert 1 | 109 | 322 / 14 | 32 | 63 | 89 |
| 0.5 | expert 2 | 118 | 334 / 2 | 34 | 67 | 98 |
| 0.5 | expert 3 | 138 | 331 / 5 | 34 | 66 | 104 |
| 0.5 | expert 4 | 115 | 332 / 4 | 34 | 65 | 93 |
| 0.5 | expert 5 | 132 | 326 / 10 | 32 | 65 | 101 |
| 0.6 | expert 1 | 174 | 322 / 14 | 32 | 64 | 118 |
| 0.6 | expert 2 | 199 | 334 / 2 | 34 | 68 | 135 |
| 0.6 | expert 3 | 205 | 331 / 5 | 34 | 67 | 129 |
| 0.6 | expert 4 | 200 | 332 / 4 | 34 | 67 | 131 |
| 0.6 | expert 5 | 203 | 326 / 10 | 32 | 66 | 130 |

Full technical-event model-specific and either-model results, explicit unknown counts and both-models-valid subgroup results are in technical_event_posthoc_public_safe.json.

## Historical common-case reproducibility

On the original 311 images where all five references passed, both model statuses and every available historical expert 1/2 disc Dice, cup Dice, reference vCDR and absolute vCDR error reproduced exactly: zero status or metric differences. Historical masks were not preserved, so this is metric agreement rather than proof of label identity. The 25 historically blocked images had no old inference. Old 16/19 prediction failures among 311 cannot be compared directly with new 18/20 among 336 as deterioration. Details and source-file hashes are in historical_commoncase_public_safe.json.

## Timing, provenance and limits

- Original protocol frozen before inference: 2026-11-04T07:30:50.935106+00:00.
- All-returned-mask addendum: 2026-11-04T07:34:42.598468+00:00 (before references).
- All predictions and app queue frozen: 2026-11-04T07:50:50.465106+00:00.
- Technical-event POST HOC addendum: 2026-11-04T08:03:52.804568+00:00.
- Original protocol and harness bytes remain unchanged. CPU threads=2; no predictor, GPU, weight or measurement changes were made by this evaluation.
- Parent changed production Chaksu indexing during this run. The process already held the original module. The original executed-source hash is retained; current _read_member and load_test_case ASTs exactly match baseline 9cd674e without line attributes. Current default strict scan has identical 336 case IDs, camera counts and archive metadata fingerprint. This is a specific semantic proof, not a blanket source-change waiver.
- Explicit pixel intersections/counts and inclusive vertical spans compute the metrics independently of product metric helpers; successful predicted vCDR agrees with the app measurement to 1e-12.
- Mean/delta intervals use 2,000 image-IID bootstrap draws, seed 20261104; event-rate intervals use Wilson 95%. Incomplete patient linkage and known repeated images violate IID assumptions. These are descriptive sensitivity intervals, not patient-level or population confidence guarantees. No patient bootstrap was used.
- Five expert annotations are references, not disease truth; vCDR error and technical failure events are not diagnostic accuracy.

## Portable reproduction and publication handoff

Run the private harness from the repository root with the project Python environment. Its output directory is Path(__file__).resolve().parent, so copy the unchanged harness into a new empty ignored reports directory; do not copy an existing protocol.json, because a new run freezes its own protocol. Inputs resolve relative to the working directory: data/Chaksu_Test.zip and models/<the two frozen bundle names>. Do not infer a repository root from the script’s parent chain. The harness refuses an existing protocol.json; use a new empty output directory for a genuinely new run. Keep the already executed original directory unchanged.

Run verify_and_supplement.py and historical_commoncase_check.py from the same directory after the original run. The supplementary hash/AST audit records the documented production indexing change. Do not rerun inference merely to regenerate the report.

The public bundle contains reviewed aggregates, a protocol excerpt, dated analysis addenda and own-authored harnesses. The enclosing experiment manifest verifies their final bytes. The raw protocol/layout, individual rows, exact per-image failures, masks, source ZIP and weights remain private.


## Fresh independent review

The separate reviewer reproduced all 3,284 Dice-row aggregate calculations and paired bootstrap summaries. A fixed first-ten-per-camera sample additionally verified 60 prediction masks, 300 original reference rasters, 143 valid and seven unavailable reader references, and 286 pixel-Dice comparisons with no discrepancies. This is a 30-image raw-pixel audit, not a claim that all 3,284 pixel scores were independently recomputed. See [verification](chaksu_fresh_verification.json). Use the [public reproduction guide](PUBLIC_REPRODUCTION.md), which clarifies fresh output directories and protocol timing.

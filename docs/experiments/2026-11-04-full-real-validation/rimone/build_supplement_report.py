"""Append completed supplemental verification to public-safe report; no image IDs."""
import json,pathlib
p=pathlib.Path(__file__).resolve().parent;s=p/'supplemental_verification';a=json.loads((s/'aggregate.json').read_text(encoding='utf-8'));protocol=json.loads((s/'protocol.json').read_text(encoding='utf-8'));coord=json.loads((p/'private_png_txt_coordinate_check.json').read_text(encoding='utf-8'));main=(p/'REPORT.md').read_text(encoding='utf-8')
main=main.replace('Completed the full official hospital-heldout test partition:', '**Both frozen models showed severe failure on the dataset-supplied cropped-ROI domain.** Baseline invalid geometry was160/174 and camera-robust invalid geometry132/174; baseline measurable-only vCDR MAE must be read with its14/174 coverage. No tuning or model promotion followed.\n\nCompleted the full official hospital-heldout test partition:')
main=main.replace('Both pre-existing PAPILA-trained models ran once, frozen,', 'In the original pass both pre-existing PAPILA-trained models ran once, frozen,')
maxdistance=max(r['masks'][part]['contour_point_distance_to_png_foreground_boundary_px']['max'] for r in coord['checks'] for part in ['disc','cup'])
lines=['','## Supplemental artifact verification','',
f"A separately frozen exploratory follow-up protocol was created at {protocol['created_utc']}, after original GT results had already been inspected. It repeated the complete174-image evaluation with both unchanged models (348additional inferences), persisting **348original-resolution label PNGs plus SHA-256 hashes**. All348prediction artifacts were complete before computing the image-only queue, and all174priorities were frozen before the supplemental script first loaded reference rasters. No training, tuning, winner selection, new crop or original-output replacement occurred.",
'',
f"The two passes total **696actual inferences over348unique image–model pairs and174images**. Replication does not add subjects. Independent boolean-pixel Dice and inclusive row-span vCDR calculations from saved PNGs reproduced the original individual statuses, errors and metrics for all348pairs: **{a['n_comparison_discrepancies']}discrepancies** at1e-12 numeric tolerance. The raw label PNGs are private and must not be redistributed. This verifies the artifact-to-metric calculation; the same frozen inference implementation produced both passes.",
'',
f"Reference polarity/mapping was independently checked for the first3lexicographic test images (6PNG/TXT pairs). Every TXT center lay in255foreground and all four corners in0background; each of the16official contour points was within{maxdistance:g}pixel of the corresponding PNG boundary using the official x/y-minus1 convention. Disc/Cup files were kept distinct and aligned to the supplied source image. This supports correct polarity and coordinates without claiming full TXT interpolation/rasterizer equivalence.",
'',
'### Predeclared technical queue stress test','',
'The supplemental protocol froze baseline technical research events as baseline error/invalid geometry OR min(discDice,cupDice) below0.4,0.5,or0.6, with review budgets10%,20%,50%. These are segmentation audit thresholds, not clinical outcome definitions. A missing reference remains unknown when baseline is otherwise valid; it is never counted negative. Existing review.priority and order_cases consumed only the two saved model predictions before reference scoring.',
'',
f"Image-only priority groups: {a['image_only_priority_counts']}.",
'',
'| Subgroup | Threshold | Images | Available outcomes | Positive events | Review budgets: detected / random expectation |',
'|---|---:|---:|---:|---:|---|']
for r in a['research_queue_evaluation']:
 bs=r['budgets'];available=bs[0]['n_outcome_available'] if bs else 0;positive=bs[0]['n_positive'] if bs else 0
 desc='; '.join(f"{int(b['review_fraction']*100)}%: {b['detected']} / {b['random_expected_detected']:.3f}" for b in bs)
 lines.append(f"| {r['subgroup']} | {r['threshold']} | {r['n_images']} | {available} | {positive} | {desc} |")
lines+=['',
'All174images satisfy every predeclared event threshold, including images where both models produced nonempty geometry. The endpoint is saturated: failure-first review has no incremental detection benefit over random review at these budgets. With no event-negative images, this dataset cannot establish research-event discrimination, specificity, AUROC, or clinical triage benefit. The small both-models-ok subgroup is explicitly counted separately and does not rescue the transfer result.',
'',
'Supplemental artifacts: supplemental_verification/protocol.json; aggregate.json; predictions_complete.json; priorities_before_gt.json; scoring_started.json; first_vs_supplement_discrepancies.json; per-model predictions.json and independent_scores.json; private original-resolution label PNGs. supplemental_run.py contains the complete freeze/inference/queue/independent-pixel-scoring procedure. The private first3-image QA montage is supplemental_verification/private_visual_qa_first3.png and is not a publication artifact.',
'']
(p/'REPORT.md').write_text(main+'\n'.join(lines),encoding='utf-8')
print(p/'REPORT.md')


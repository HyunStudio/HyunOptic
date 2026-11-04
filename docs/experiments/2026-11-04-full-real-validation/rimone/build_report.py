"""Build a public-safe aggregate narrative; contains no image IDs or masks."""
import pathlib,json
p=pathlib.Path(__file__).resolve().parent
protocol=json.loads((p/'protocol.json').read_text());a=json.loads((p/'aggregate.json').read_text());ref=json.loads((p/'independent_reference_audit.json').read_text());v=json.loads((p/'independent_numeric_verification.json').read_text())
lines=['# RIM-ONE DL: frozen external segmentation evaluation','',
'Completed the full official hospital-heldout test partition: **174 distinct image files, 118 normal and 56 glaucoma**. The random variant and hospital training partition were not evaluated or counted as extra samples. Both pre-existing PAPILA-trained models ran once, frozen, without training, tuning or manually generated crops.','',
'This is exploratory external segmentation testing, **not a reproduction of the RIM-ONE DL classification benchmark** and not comparable to its RIM-only-trained leaderboard. No glaucoma classification AUC, sensitivity or accuracy is claimed.','',
'## Results','',
'| Frozen model | Selected / valid references | Disc Dice, mean | Cup Dice, mean | vCDR MAE | Measurable vCDR / valid / selected | Prediction status counts |','|---|---:|---:|---:|---:|---:|---|']
for m in a['models']:
 lines.append(f"| {m['model']} | {m['n_selected']} / {m['n_reference_valid']} | {m['disc_dice']['mean']:.6f} | {m['cup_dice']['mean']:.6f} | {format(m['vcdr_abs_error']['mean'], '.6f') if m['vcdr_abs_error']['mean'] is not None else 'unmeasurable'} | {m['vcdr_measurable']} / {m['vcdr_reference_valid_denominator']} / {m['vcdr_selected_denominator']} | {m['prediction_status_counts']} |")
lines+=['',
'All Dice values are macro averages at each supplied image\'s original pixel resolution, including empty or invalid prediction masks. A missing prediction is scored as empty for Dice; no failure is silently dropped. vCDR is an axis-aligned pixel-span ratio; it is reported only where both disc and cup can be measured, with the measurable denominator shown explicitly. Full descriptive distributions and deterministic image bootstrap intervals are in aggregate.json; these intervals do not account for patient clustering.','',
'## Reference and scope limits','',
'- All 174 selected images had validly shaped, nonempty, binary official disc and cup PNG masks. There were zero missing/shape/binary reference failures.',
'- One official reference has 46 cup pixels outside its disc. The raw masks were retained and the warning recorded separately; no reference repair or exclusion was applied. A descriptive no-warning vCDR sensitivity result is saved separately in independent_numeric_verification.json.',
'- The official dataset images are already square crops around the optic nerve head, rather than whole-fundus photographs. This changes optic-disc scale and field of view relative to PAPILA. The harness applies only the existing image-only bundle preprocessing; it does not derive a crop from the reference.',
'- The paper describes removal of duplicates/test-retests and one image per patient and eye. An authoritative patient-to-image linkage table was not verified, so the denominator is 174 images, not 174 independently verified patients. Patient-level confidence intervals are not available.',
'- This evaluates technical segmentation transfer under a material image-domain change. It establishes neither clinical utility nor safety for medical decisions.','',
'## Provenance and permitted use','',
'Official repository: https://github.com/miag-ull/rim-one-dl ; archived source commit: 5f56b8c9957656282c2d00d40fc420a850bd1fe4. Official author-linked assets were obtained from https://bit.ly/rim-one-dl-images and https://bit.ly/rim-one-dl-reference-segmentations . No mirrors or alternate datasets were used.',
'',
'Official terms allow free research/educational use without asking the authors, and prohibit redistribution and unauthorized commercial use. Data, IDs, masks, model weights and individual results remain local in ignored directories. Do not publish those artifacts.',
'',
'Citation: Fumero Batista FJ et al. RIM-ONE DL: A Unified Retinal Image Database for Assessing Glaucoma Using Deep Learning. Image Analysis & Stereology 39(3):161–167 (2020). https://doi.org/10.5566/ias.2346 ; official paper: https://www.ias-iss.org/ojs/IAS/article/download/2346/1128/6451 .',
'',
'Images archive: 222,561,134 bytes; SHA-256 85aed5f95c794f52d11b6ed953032108a66576ffcff4b587365df467491b603d. Reference archive: 1,608,386 bytes; SHA-256 edc363b1f0deabc8ed7a356250a9e1fb21825bf06f7337889fd1e764e1947901.',
'',
'## Reproducibility and checks','',
f"Protocol frozen at {protocol['created_utc']}; model identities, archive hashes, all selected image/mask payload hashes, and harness/source hashes were fixed before inference. Inference started at {json.loads((p/'inference_started.json').read_text())['started_utc']}. Both checkpoints were verified and loaded with the existing restricted weights_only loader. CPU threads were fixed to two.",
'',
'Independent verification recomputed macro means from saved individual records, checked complete one-to-one accounting of all 174 images per model, verified finite bounded Dice values, and confirmed protocol timing and vCDR denominators. This is independent arithmetic/accounting verification, not an independent inference implementation or raw predicted-mask recomputation.',
'',
'Local commands from repository root:',
'```powershell',
'.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py prepare',
'.venv/Scripts/python.exe reports/full_validation_20261104/new_external/evaluate_rimone.py run',
'.venv/Scripts/python.exe reports/full_validation_20261104/new_external/audit_references.py',
'.venv/Scripts/python.exe reports/full_validation_20261104/new_external/verify_numeric.py',
'```',
'',
'prepare/run deliberately refuse to overwrite an existing frozen protocol or silently rerun predictions. Existing outputs must be preserved; any authorized rerun requires a separately identified output/protocol.',
'',
'Artifact index: protocol.json (frozen evaluation rules/identities); provenance.json and images_confirm_download.json (source/HTTP/size/hash records); access_attempts.json (initial access responses and article-page timeout); input_manifest.json and *_individual.jsonl (private IDs, never publish); reference_failures.json and independent_reference_audit.json (reference accounting); *_aggregate.json / aggregate.json (safe aggregate metrics); independent_numeric_verification.json (arithmetic audit). evaluate_rimone.py is the standalone harness; official conversion files are archived only for format provenance, with the supplied PNG masks used directly.',
'']
(p/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8');print(p/'REPORT.md')


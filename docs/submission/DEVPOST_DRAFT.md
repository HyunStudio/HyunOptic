# HyunOptic — traceable review of ophthalmic AI predictions

**Prepared description; not a submitted entry.** Contributor: HyunGi Hwang, independent researcher and M.S. student in Computer Science, University of Colorado Boulder. [Submission fields](SUBMISSION.md).

## Inspiration and user need

An ophthalmic model can return a cup-to-disc measurement while segmenting the wrong structure. Our real-data tests found exactly this: on 174 new external RIM-ONE DL hospital-Test images, both models failed severely, including some geometrically measurable outputs. A researcher needs to inspect predictions, retain unresolved cases and recover the evidence behind each decision. HyunOptic provides that local review workflow. It is research software, not a diagnostic or patient-care tool.

## What it does and why it helps

Choose two verified local segmentation bundles, import permitted images and process bounded batches. Inspect the full image alongside both overlays, record reviewed or held decisions with reasons, reopen the session and export a verifiable evidence ZIP. Unsupported inputs and model failures stay visible. Interrupted work can be recovered; stale decisions cannot overwrite newer revisions.

The comparison is a defined manual method: open the source image and two prediction files, consult separate model identifiers, maintain case status/reasons in a spreadsheet, then assemble and check an export. HyunOptic joins those steps in a persistent session: previews carry model identity, saved reasons reopen with the case, and the export binds decisions to input/model hashes and revisions. These are documented workflow capabilities, not a timed comparison or a claim about all spreadsheet tools. We have not measured time savings or conducted a participant study.

## AI choices and limits

A small PyTorch U-Net provides image-only disc/cup segmentation. Two distinct frozen models make differing boundaries inspectable without requiring additional models or an LLM. Local CPU execution avoids sending research images or notes to an API; the public preparation command actually trains two small synthetic models, so reviewers can run the mechanics without private weights. Bundle integrity checks establish identity and supported contracts, not domain validity.

Reference annotations never enter prediction or priority. Ordering by execution failure, invalid geometry and disagreement helps organize inspection; it is not calibrated uncertainty, disease risk or a proven error detector. Both models may agree and be wrong. Whole-fundus training does not validate cropped optic-nerve-head inputs, other cameras, SLO or OCT. Measurable geometry does not establish anatomical accuracy. [Model/data access](MODEL_AND_DATA_ACCESS.md).

## What actually worked

An actual browser audit processed four synthetic images into eight predictions while retaining one unreadable input. A held/uncertain decision survived refresh; the downloaded ZIP passed separate six-payload verification. A repeated ordinary run reproduced prediction PNG digests. A demanding run recovered a deliberately unfinished claim across 100 repeated synthetic cases, retaining 200 predictions and an input error. A copied-bundle hash failure preserved earlier completed cases and the held decision. These checks establish review mechanics, not segmentation accuracy; 100 repeated cases are not 100 patients. [Expected and observed outcomes](../experiments/2026-11-04-submission-readiness/README.md).

That historical browser audit passed 326 software tests. The subsequent integrated real-data audit passed 388, including eight regressions for three evaluator defects: expert-reference failures could block predictions, missing expert files excluded images, and ZIP corruption aborted evaluation. The preceding source passed 390 tests (two existing CUDA warnings). The [latest Git/distribution audit](../experiments/2026-11-04-submission-code-audit/README.md) passed 404 tests in development and 404 against an isolated CPU-installed wheel. Four reproduced import/export/provenance/labeling defects were corrected with 14 regression cases; default synthetic preparation and installed-package review/export/deletion also passed. Two domain-guidance regressions failed before correction, then passed. A [fresh browser check](../experiments/2026-11-04-final-submission-polish/README.md) used an API-preseeded session, processed eight predictions, preserved a held decision after full reload and independently verified the six-payload downloaded ZIP. It also checked persistent cropped-ROI guidance and accuracy-unverified measurement labels. Historical totals are not added together.

## What the real-data assessment found

The [full November 4 report](../experiments/2026-11-04-full-real-validation/README.md) accounts for 3,916 inference calls: PAPILA 2,548 (98 eyes/49 patients, 13 conditions, two models), Chákṣu 672 (336 images, five expert references), and RIM-ONE DL 696 (174 new images, two complete two-model passes). The 608 source image records are not verified independent patients.

PAPILA retained 2,382 measurable predictions and 166 invalid geometries. Baseline Cup Dice fell from 0.6883 to 0.3581 under grayscale; invalid geometry rose from 6/98 to 42/98. Grayscale photographs do not validate SLO transfer. Chákṣu retained every returned prediction and isolated reference failures per expert.

RIM-ONE DL supplied cropped inputs: baseline/photometric Cup Dice was 0.0018/0.0065 across all 174 images, with 160/174 and 132/174 invalid geometries. Only two images were measurable under both models. The saturated queue endpoint equalled random expectation, establishing no triage benefit. Independent artifact checks are linked in the report. Reused Test cohorts and repeated passes are not untouched confirmation, clinical benefit or reproduction of 100 papers' original benchmarks.

## Development, privacy and demonstration

OpenAI Codex assisted design, implementation, tests, review and documentation. Observed failing regressions preceded fixes; AI review remains fallible. Person-specific checking of an AI contribution and the resulting keep/change/reject decision remains for the submitter to record honestly. [AI disclosure](AI_DISCLOSURE.md), [personal worksheet](HUMAN_REVIEW.md).

Default exports omit originals, masks, filenames, local paths and private notes; hashes do not guarantee anonymity. Local storage is not encrypted by the app. No patient images or third-party research weights appear in the public demo.

The [public 3:38 video](https://youtu.be/xbs47mX0d5g) uses authentic application captures from the explicitly recorded earlier version, synthetic models/data, edited timing and disclosed AI narration. [Source](https://github.com/HyunStudio/HyunOptic), [setup](README.md), [video provenance](VIDEO_PUBLICATION.md). All work through November 4 is pre-event; preserve the actual event-start commit and disclose genuine later additions in [development history](EVENT_CHANGES.md). Personal review, roster/eligibility confirmation and actual Devpost submission remain pending.

# HyunOptic — traceable review of ophthalmic AI predictions

**Prepared description for personal final review; not a submitted entry.** Paste the body after checking it against the final frozen version. Contributor information supplied by the author: HyunGi Hwang, independent researcher and M.S. student in Computer Science at the University of Colorado Boulder. [Copy-ready fields and prepared video](SUBMISSION.md).

## Inspiration and problem

An image model can produce a cup-to-disc measurement while identifying the wrong structure. In independent ophthalmic research, inspecting a number alone can hide that failure. HyunOptic helps a researcher inspect full images and two model overlays, preserve unresolved cases and retain the evidence behind a review decision. The tool is research-only and does not diagnose glaucoma or approve patient care.

## What it does

Select two verified local segmentation bundles and import permitted images. The application copies inputs locally with explicit retention notice, processes bounded batches, and keeps unsupported inputs and model failures visible. Cases can be ordered by execution failure, invalid measurements and model disagreement. Inspect full image context, record reviewed/held decisions with reasons, resume interrupted work and export a verifiable evidence package. Concurrent stale decisions are rejected instead of silently overwriting a newer record.

Compared with manually opening predictions and keeping notes in a spreadsheet, the implemented workflow joins model/input identities, decision revisions and export checks in one persistent session. This is a feature comparison, not measured time savings. We have not conducted a user study or established that disagreement ranking reliably detects errors.

## AI and implementation choices

The product uses a small PyTorch U-Net with fixed image-only preprocessing and verified bundle contracts. Two distinct frozen models make differing predictions inspectable; additional models or an LLM are not required for the task. CPU execution and synthetic public-source preparation make the demonstration reproducible without private developer weights. Reference masks never enter prediction or priority. Disagreement is descriptive, not calibrated uncertainty, diagnostic risk or correctness certification.

OpenAI Codex assisted planning, implementation, tests, review and documentation. Concrete checks exposed mismatched upload limits, preview file replacement between verification and decoding, and unhelpful raw decoder errors. Failing regressions preceded fixes, followed by the full suite. Automated review is fallible and is not evidence of human clinical approval. See [AI disclosure](AI_DISCLOSURE.md); the submitter's specific final personal check remains to be recorded truthfully.

## What actually worked

In an actual browser run, four synthetic images produced eight predictions from two actual CPU-trained models, alongside one retained unreadable input. A held/uncertain review persisted after refresh. The downloaded evidence ZIP passed a separate six-payload verification. A repeated run produced identical prediction PNG digests. A separate 100-case repeated-image batch recovered a deliberately unfinished claim and retained 200 predictions plus one input error. A copied model hash failure preserved completed cases and the held decision.

The final local suite passed 326 tests with two existing CUDA nondeterminism warnings. The public-source audit reused installed dependencies with clean-clone source, so it does not establish a fresh Windows install. CI covers separate dependency installation and platform checks. [Detailed execution evidence](../experiments/2026-11-04-submission-readiness/README.md).

## Research context and limits

Earlier real-data transfer failures motivated this workflow; synthetic demo success does not resolve them. The November 4 exploratory reader/review experiment used 98 PAPILA eyes from 49 patients and 196 predictions from two frozen models. For expert 1, reviewing 20 of 98 images selected 12 of 18 predefined research events and missed six; uniform-random expected detections were 3.6735. This reused cohort, annotation sensitivity and heuristic ranking do not establish independent generalization, clinical benefit or user-time savings. [Full denominators, definitions and reader sensitivity](../experiments/2026-11-04-reader-review-validation/README.md).

Default ZIP exports omit original images, masks, filenames, local paths and private notes, but hashes do not guarantee anonymity. Local data is not encrypted by the application. No patient images or third-party research weights appear in the public demo. Hosted deployment, clinical use, formal accessibility testing and independent participant evaluation remain outside this release's evidence.

## Development boundary and links

All work through November 4 is existing/pre-event work, including this audit. Preserve the actual event-start commit and list only real subsequent changes in [development disclosure](EVENT_CHANGES.md).

- Source: https://github.com/HyunStudio/HyunOptic — use the final verified commit/branch link.
- Setup: [submission README](README.md).
- Video: https://youtu.be/xbs47mX0d5g — publicly published narrated/captioned demonstration with actual application captures, edited timing, synthetic inputs/models and disclosed AI narration. [Original MP4](media/hyunoptic-demo.mp4) and [publication verification](VIDEO_PUBLICATION.md) remain available.
- Team/eligibility and personal final check: **pending submitter confirmation**.

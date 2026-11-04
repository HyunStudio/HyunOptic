# HyunOptic — traceable review of ophthalmic AI predictions

**Prepared description, not a submitted entry.** HyunGi Hwang — independent researcher and M.S. student in Computer Science, University of Colorado Boulder. [Submission fields](SUBMISSION.md).

## Inspiration

I was born with congenital cataracts, underwent surgeries including lens removal, developed glaucoma in childhood, and am registered as visually impaired under South Korea’s criteria. Frequent hospital visits as a child shaped my interest in medicine. Studying computer science gave me a way to pursue independent medical imaging research. This experience motivates my independent research.

A model can return a cup-to-disc measurement while locating the wrong structure. Our external tests found severe failures even among some geometrically measurable outputs. I wanted a concrete research workflow: inspect the source and two predictions, keep unresolved cases visible, resume later and retain the evidence behind each decision.

## What it does

HyunOptic runs locally with two verified PyTorch segmentation bundles. Researchers import permitted images, process bounded batches, compare the source and model overlays, and save reviewed or held decisions with reasons. Sessions persist across reloads. Revision checks guard against stale saves; interrupted processing can be recovered. An evidence ZIP binds decisions to inputs, model identities and revisions, and has a separate integrity verifier.

The [manual comparison](WORKFLOW_COMPARISON.md) uses the same task: an image viewer, two existing prediction masks, model/hash records, a spreadsheet and a ZIP tool. HyunOptic integrates those records and checks. A person must still inspect the boundaries and decide what to record. We have not measured human time savings, review accuracy or clinical benefit.

## AI and its limits

Two small frozen U-Net models expose differing boundaries without an LLM or remote inference API. The public preparation command actually trains two CPU models on synthetic data; private research weights are not needed for the mechanics demo. Reference annotations never enter prediction or priority. Execution failures, invalid geometry and disagreement organize inspection; they are not calibrated uncertainty, disease risk or a proven error detector. Two models can agree and both be wrong.

Whole-fundus training does not validate cropped optic-nerve-head inputs, other cameras, SLO or OCT. Measurable geometry is not anatomical validation. [Model/data access and limitations](MODEL_AND_DATA_ACCESS.md).

## What the evidence shows

The [completed software audit](../experiments/2026-11-04-submission-code-audit/README.md) passed the same 404-test suite in development and an isolated CPU-installed wheel. Earlier authentic browser checks processed four synthetic images/eight predictions, retained an unreadable input, preserved a held decision after reload and independently verified the downloaded six-payload ZIP. These establish workflow mechanics at their recorded source versions. The subsequent [usability audit](../experiments/2026-11-04-review-usability/README.md) passed 442 tests against the final installed CPU wheel and 80 final targeted development checks. Metadata listing on 200 repeated synthetic cases had sample p95 0.066 seconds; selected verification was 0.093 seconds. These are different software operations, not measured human-time savings. Current browser/responsive acceptance and refreshed video remain incomplete after browser control stopped.

The [full real-data assessment](../experiments/2026-11-04-full-real-validation/README.md) records 3,916 inference calls across 98 PAPILA eyes/49 patients, 336 Chákṣu images and 174 RIM-ONE DL images, including perturbations and repeats. The 608 source image records are not verified independent patients. On the cropped RIM-ONE DL inputs, baseline/photometric Cup Dice was 0.0018/0.0065; invalid geometry occurred in 160/174 and 132/174 images. Only two images were measurable under both models. The saturated queue endpoint equalled random expectation: no triage benefit was established. Reused cohorts and repeated passes are not untouched confirmation.

## Development and demonstration

OpenAI Codex assisted design, implementation, testing, review and documentation. The [A4 personal worksheet](HUMAN_REVIEW.md) remains uncompleted: automated checks and AI review cannot stand in for an actual person's finding and keep/change/reject decision. [AI disclosure](AI_DISCLOSURE.md).

Default exports exclude originals, masks, filenames, local paths and private notes. Hashes do not guarantee anonymity; app storage is not encrypted. No patient images or private research weights appear in the public demo.

The [historical 3:38 video](https://youtu.be/xbs47mX0d5g) uses authentic earlier-version captures, edited timing, synthetic models/images and AI narration. It does not depict the new usability changes. The [refresh storyboard and draft captions](DEMO_REFRESH_PLAN.md) are a plan, not newly recorded or published media. [Source](https://github.com/HyunStudio/HyunOptic), [setup](README.md), [rights](REPOSITORY_RIGHTS.md).

All work through November 4 is pre-event. Genuine later work must be recorded separately in [development history](EVENT_CHANGES.md). Personal review, roster/eligibility confirmation and actual submission remain pending. HyunOptic is research/education software and must not guide diagnosis or patient care.
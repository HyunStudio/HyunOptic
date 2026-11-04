# Rubric-to-evidence map

**Latest software audit (2026-11-04):** [Git/distribution and lifecycle audit](../experiments/2026-11-04-submission-code-audit/README.md) — 404 tests passed in the development environment and 404 against a non-editable wheel in a new CPU-only environment. Four reproduced defects were corrected with 14 regression cases. Default two-seed/80-epoch synthetic preparation, installed-package processing, held-state reload, ZIP verification and managed deletion passed. These are software checks; earlier browser and real-data evidence retains its original scope.


Checked against the [official rubric](https://global-ai-builders-challenge.devpost.com/resources) on 2026-11-04. This maps all 25 checkpoints to available evidence and honest limits; it assigns no score. Judges normally use the video and description; installing the app and an outside tester are optional. Required entry materials are tracked in the [checklist](CHECKLIST.md).

| Checkpoint | Evidence and supported interpretation | Limit / remaining action |
| --- | --- | --- |
| V1: need | [Real transfer audit](../experiments/2026-11-04-full-real-validation/README.md): wrong anatomy can still yield measurements. | Research inspection need; no clinician-demand study. |
| V1: use example | [Description](DEVPOST_DRAFT.md), [video](https://youtu.be/xbs47mX0d5g): inspect two overlays, hold uncertainty, reopen and export. | Synthetic demonstration. |
| V2: comparison basis | [Description](DEVPOST_DRAFT.md) defines a manual image/prediction-file plus spreadsheet method and its steps. | Documented task comparison, not a universal claim about existing tools. |
| V2: concrete advantage | [Workflow audit](../experiments/2026-11-04-submission-readiness/README.md): persisted reasons/model identity and verified export join the manual steps. | No measured speed, error reduction or user benefit estimate. |
| V3: feasible access | [Setup](README.md), [access](MODEL_AND_DATA_ACCESS.md): CPU, local storage, synthetic public recipe; permitted research bundles optional. | Dependency download required; private weights/data not redistributed. |
| A1: model choice | [Description](DEVPOST_DRAFT.md): image segmentation for overlays; two frozen models expose differing boundaries. | No claim these models are accurate across domains. |
| A1: supporting evidence | [CPU workflow audit](../experiments/2026-11-04-submission-readiness/README.md): actual local models complete review without an inference API or private weights in the synthetic route. | Supports local feasibility, not superiority over other architectures. |
| A2: design rationale | [AI disclosure](AI_DISCLOSURE.md): image-only preprocessing, fixed contracts, reference isolation and local processing. | Disagreement is descriptive; bundle identity is not accuracy. |
| A2: demonstrated contribution | [Video](https://youtu.be/xbs47mX0d5g): two actual frozen models produce different overlays for the same image, supporting a persisted uncertain/held review. | Comparative inspection, not reliable error detection. |
| A3: actual quality assessment | [Full report](../experiments/2026-11-04-full-real-validation/README.md): reference methods, denominators, 3,916 calls and independent checks. | Reused cohorts; repeated conditions/passes are correlated. |
| A3: appropriate reliance | [Description](DEVPOST_DRAFT.md): severe cropped-ROI failure, measurable-but-wrong outputs and no RIM queue benefit. | Research inspection only; no clinical or ranking validation. |
| A4: person checks AI work | [Personal worksheet](HUMAN_REVIEW.md) names specific AI-assisted contributions to inspect. | Pending actual person's action; AI review/tests cannot fill this checkpoint. |
| A4: human finding and decision | Same worksheet requests the observed result and keep/change/reject rationale. | Pending truthful person-specific record; no approval invented. |
| R1: complete process | [Browser audit](../experiments/2026-11-04-submission-readiness/README.md): create → actual prediction → hold → reload → independently verified download. | Public video is edited authentic captures of an identified earlier version. |
| R2: ordinary case one | Browser run expected/observed: four complete images, eight predictions, retained unreadable input, held decision and verified ZIP. | Checks workflow requirements, not anatomical truth. |
| R2: ordinary case two | Same report: separate two-input run, four predictions; held state survives reopened store. | Different synthetic execution; no independent patient sample. |
| R2: repeat | Same report: repeated two-input run has identical four prediction PNG digests. | Checked CPU run only; no CUDA determinism promise. |
| R2: demanding case | Same report: 100 repeated-image cases, 200 predictions, controlled recovery, held state and verified export. | Deliberately unfinished claim, not OS-crash testing. |
| R3: input failure | Same report and [video](https://youtu.be/xbs47mX0d5g): unreadable file remains visible; other work continues. | Supported formats and limits in [setup](README.md). |
| R3: model failure | Same report: copied-bundle hash mismatch visibly fails remaining work, preserving two completed cases and held decision. | Controlled copied-model failure. |
| D1: task emphasis | [Video](https://youtu.be/xbs47mX0d5g) and [workflow](README.md): create/process, select case, review, export; counts and errors remain visible. | Final source has additional domain guidance; video provenance is explicit. |
| D2: consistency | Actual capture sequence in [video provenance](VIDEO_PUBLICATION.md): repeated tables, controls, model labels and status/reason presentation. | No formal usability/accessibility certification. |
| D3: reduced effort | Persisted session and held reasons reopen without re-entering records; [browser audit](../experiments/2026-11-04-submission-readiness/README.md) verifies refresh. | Specific avoided re-entry; no measured time savings. |
| D4: find information | [Video](https://youtu.be/xbs47mX0d5g): queue ordering, case detail and export group distinct tasks. | Priority is not a correctness ranking. |
| D4: see relationships | Same video: full-image context and both labeled model overlays connect differing boundaries to measurements and held reasons. | Geometrically measurable remains accuracy-unverified. |

Final-source validation: **390 tests passed**, with two existing CUDA warnings. The [latest source/browser audit](../experiments/2026-11-04-final-submission-polish/README.md) verifies persistent ROI/domain limits, accuracy-unverified labels, processing, held-state reload and independently checked ZIP download from an API-preseeded session. It supplements the earlier complete browser workflow; it does not repeat browser creation, medical evaluation or video production.

The [description](DEVPOST_DRAFT.md) carries comparison, AI reasoning and concise results so judges need not reconstruct claims from raw artifacts. [Readiness](READINESS.md) separates completed engineering/evidence from actual human and event obligations. No item here establishes eligibility or predicts an award.

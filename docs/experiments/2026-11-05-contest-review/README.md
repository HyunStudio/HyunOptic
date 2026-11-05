# Competition-readiness precision review — 2026-11-05

**Decision: the research-review software and demonstration are technically prepared for entry; submission eligibility and completion remain conditional.** No blocking defect was found in the inspected main workflow. This is not organizer approval, a clinical-performance claim, an expected contest score or a completed entry.

Reviewed baseline: `d75ad096b094dae9b201f467f1aed8ad95f731d8`. Application code remains unchanged during this review; corrections concern submission links, current evidence pointers and explicit provenance limits. [Verification receipt](verification.json), [current workflow results](workflow_audit.json), [document checks](document_checks.json).

## Entry requirements versus quality checks

The [official rules](https://global-ai-builders-challenge.devpost.com/rules) and [published rubric](https://global-ai-builders-challenge.devpost.com/resources) were rechecked November 5. The required description, public code, 2–4 minute video, roster and AI/development disclosures are prepared. The [current public movie](https://youtu.be/C5KE1KaHWGI) is 167.401 seconds on the host; [publication receipts](../../submission/VIDEO_PUBLICATION_20261105.md) record English captions, playback to the end and anonymous oEmbed. Local source/model/data access has a runnable synthetic route with no private weights or API account.

The event starts **November 21, 2026, 17:00 KST** and closes **November 29, 08:00 KST**. This entire review is pre-event. Existing work must be disclosed and genuine event-period contributions recorded separately. Before actual entry, the author must confirm eligibility, complete the actual roster and rights/disclosures, freeze the intended source version and check the real Devpost preview/embed. None of these personal or platform actions is fabricated here.

Native 200% browser zoom is **unverified**, a remaining usability check rather than an additional eligibility gate stated by the event. The [A4 personal worksheet](../../submission/HUMAN_REVIEW.md) remains blank: the rubric allocates up to six quality points to actual person-specific checking and its supported decision. AI-agent review cannot fill it. A hosted app, outside tester, paid AI service, more papers or a new model architecture are not mandatory under the reviewed rules.

## Fresh execution on the reviewed source

The full suite was rerun; exact count, warnings and duration are in [verification](verification.json). An independent code reviewer also reported **133 targeted tests passed** across store/runner/export integrity, provenance, CPU training/inference and UI boundaries. These overlap the full suite and are not 133 additional distinct test cases.

Two already prepared, actually CPU-trained synthetic bundles from November 5 were reused. No new training or patient evaluation is claimed. The [current driver](run_workflow_audit.py), adapted from the preserved November 4 driver, obtains the actual creation commit instead of hard-coding that historical commit.

| Scenario | Expected | Observed |
| --- | --- | --- |
| Ordinary two-image session | Two complete, four predictions, held decision survives reopening, ZIP verifies | Matched |
| Repeat ordinary session | Same four prediction PNG digests, preserved decision and verified ZIP | Matched |
| Controlled interruption and demanding session | 100 completed repeated-image cases, one unreadable input, 200 predictions, held decision and verified ZIP retained | Matched |
| Copied model file changed | First two completed cases and held decision retained; third case errors; ZIP verifies | Matched |

All ten explicit expected/observed checks passed. The demanding case repeats four synthetic images: it is not 100 patients. Recovery follows an intentionally unfinished claim, not an OS crash. Runtime observations are machine-specific and do not measure human time saved or clinical benefit. The prior [actual browser import-to-download](../2026-11-05-final-acceptance/README.md) retains its own source and scope; this rerun is a programmatic workflow check, not a new browser recording.

Reproduce in a **new** output directory after the public two-model preparation:

```powershell
python scripts/prepare_submission_demo.py --output demo_data/contest-review
python docs/experiments/2026-11-05-contest-review/run_workflow_audit.py reports/contest-review demo_data/contest-review
python -m hyunoptic.review.export reports/contest-review/demanding.zip
python scripts/verify_experiment_evidence.py
```

## Corrections and residual limits

- The copy-ready Devpost description contained **15 repository-relative links**. An external-origin portability check failed; all links now use absolute public URLs and the same check passes. The actual Devpost editor still needs its submission-time preview check.
- The personal worksheet and rubric map pointed to the older movie. They now point to the current public demonstration; historical reports and frozen media remain unchanged.
- The manual-comparison and development disclosure documents contained stale pending-layout/publication wording. They now agree with the observed November 5 results.
- Session `software_commit` is creation-time source metadata. It does not attest to each prediction's execution source when a session resumes under different code. This limitation is now explicit in [setup](../../submission/README.md). Keep the checkout and dependencies fixed for reproducible studies. No cross-version execution-attestation feature is claimed.

The supported product value is comparing model outputs with source context, retaining unresolved decisions and linking decisions to verified evidence. External RIM-ONE DL transfer failures and the absence of demonstrated queue benefit remain disclosed. Clinical accuracy, human workload reduction and award competitiveness require their own evidence; test totals or institution names cannot establish them.

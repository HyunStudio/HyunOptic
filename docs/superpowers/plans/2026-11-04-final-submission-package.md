# Final submission package implementation plan

> **For agentic workers:** Execute inline using the established submission-readiness design and verification workflow.

**Goal:** Finish and publish the reviewable software/media package instead of leaving a local video draft and unmerged default repository.

**Architecture:** Keep the already verified application behavior. Capture actual additional browser interactions, produce an accessible narrated/captioned 2–4 minute demonstration from authentic captures with explicit edited timing and synthetic disclosure, and publish the video, transcript, immutable source links and submission fields together. Integrate verified changes into the default repository after final checks. Human attestations and event-period work must remain truthful.

**Tech stack:** Existing Streamlit/PyTorch app, CUA browser captures, offline Windows speech synthesis, isolated FFmpeg tooling, Markdown and GitHub.

**Spec:** Existing `2026-11-04-submission-readiness-audit.md` and `docs/submission/READINESS.md`, plus user's instruction to finish to final submission standard.

## Tasks

- [x] Captured 21 authentic browser screenshots of actual create/process/compare/held/full-reload/reopen/export actions. Downloaded synthetic ZIP independently verifies six payloads; no patient data.
- [x] Final narrated MP4 is 217.507 seconds, H.264/AAC, 1280×960. Full decode, twelve chapter caption bounds and audio levels checked; decoded chapter contact sheet inspected. SRT uses disclosed approximate word-proportional timing; transcript/thumbnail/capture provenance and 30-payload manifest prepared for public Git publication.
- [x] Copy-ready fields, package landing page, supported-host upload text and specific personal review worksheet prepared. Official Devpost help confirms supported-host URL requirement; GitHub MP4 is not a substitute. User asked to select YouTube/Vimeo account or upload personally while independent work continues.
- [x] Media/evidence/112 local links verified; public authoring rebuild produced a byte-identical MP4. Independent final review found no Critical/Important issue. All four final PR and main CI jobs passed. PR7 merged at a185467e0c86a010a8b64d3fc8c30638551847ea; main's local full suite passed 326 tests, two existing CUDA warnings, 197.35 seconds. Frozen tag submission-prep-20261104 points at that merge. No destructive cleanup or Devpost submission.
- [x] Author subsequently selected their YouTube account for public upload and confirmed login. Published https://youtu.be/xbs47mX0d5g with English SRT, thumbnail, disclosures and public visibility; hosted playback and anonymous oEmbed HTTP200 checked. Exact verification limits in docs/submission/VIDEO_PUBLICATION.md. Personal review and actual entry remain pending.

## Boundaries

Event has not started. No fabricated event contributions, person-specific checking, eligibility approval or final legal attestations. AI narration is disclosed. No novelty/clinical/efficiency claim is invented. GitHub MP4 access is separate from Devpost's accepted embedded video-provider field; verify what is observable, and preserve the portable file if an account-specific upload remains necessary.

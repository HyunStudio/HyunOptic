# Actual browser and current-source acceptance — 2026-11-05

The current Review Queue workflow was exercised through the actual browser, including a real file chooser and downloaded ZIP. A small-screen header defect was reproduced and fixed. This audit supersedes the open browser/import and local-video items in the [November 4 usability audit](../2026-11-04-review-usability/README.md); that historical evidence remains frozen. It does **not** close native 200% zoom, personal review or actual Devpost entry.

## Source and verification

Baseline `5c9f698bd97c3707d2e4b9052c0e7870e3815916`; product fix `ea4e76811c931134bc77a7684a1cf21bbc32492a`. Captures used the baseline with the [recorded CSS patch](capture-source.diff), committed unchanged afterward. The session's creation HEAD therefore correctly records the baseline. No model algorithm, training default or reported medical performance changed.

The full development suite passed **442 tests**, with four warnings in **222.07 seconds**: two existing CUDA nondeterminism warnings and two intentional malformed-TIFF warnings. Targeted UI verification passed **22 tests**. [Machine-readable verification](verification.json) records the independently installed wheel and final integrity checks. These tests verify software behavior, not medical accuracy.

At 390×844, status cards originally squeezed beside the brand to approximately 93 pixels each. The CSS now gives them a full-width row below the brand at widths up to 900 pixels. Real DOM measurements show 111.66-pixel cards, the correct row placement and no page horizontal overflow after an application restart. [Before](captures/01-narrow-before.png), [after](captures/03-narrow-fixed.png), [measurements](layout-checks.json).

## Actual workflow results

The public synthetic preparation ran two CPU models for 80 epochs each. Primary seed 43: `seg-20261104-212850-3231ffb2`; comparison seed 42: `seg-20261104-212808-47e91de2`. IDs use UTC; this report uses November 5 KST. Models were prepared before capture.

| Action | Observed outcome |
| --- | --- |
| Actual file chooser → retention confirmation → create | Four synthetic JPEGs and one intentionally unreadable PNG; new session |
| Process inputs | Four complete, one input error, eight actual predictions |
| Aligned comparison | Source and both predictions aligned at y=444, each 263 pixels wide at the tested desktop viewport |
| Hold + uncertain → Save and next | Saved decision and advanced to the next case in the actual priority ordering |
| Reload → reopen held case | Held/uncertain retained |
| Keyboard Tab navigation → Return on Save | Review controls reachable with visible focus; saved revision 2 |
| Inspect unreadable case | One terminal explanation, no misleading inference retry or review form |
| Build → actual Download verified ZIP | Independent verifier accepted six payloads, five cases and eight predictions |

[Workflow receipt](workflow-receipt.json), [keyboard trail](keyboard-trail.json), [terminal-error checks](unsupported-check.json). The [exact downloaded ZIP](../../submission/media-20261105/synthetic-review-evidence.zip) is 5,304 bytes, SHA256 `0461aa10b61efd421022f63ab51b7379df79ee82230b5b05c97122c3fd947af2`. Original names, paths, images, masks and private notes are excluded. All data and models in these captures are synthetic.

## Responsive and accessibility scope

Actual 1280×720, 768×1024 and 390×844 viewports were inspected. Tablet header/comparison and phone full-size primary view were checked. Keyboard verification covers the Review Queue controls and saving, not a full application or WCAG certification. **Native 200% browser zoom remains unverified:** the attempted IAB shortcuts changed none of inner width, device scale or visual viewport scale, and Chrome tab creation was rejected. A narrow viewport is not substituted for native zoom. A manual check was requested; no result is invented.

## Refreshed demonstration and remaining steps

The [new 2:47 local demonstration](../../submission/media-20261105/README.md) contains 13 authentic UI captures plus a clearly identified generated verifier card, edited timing and AI narration. Full decode, cue text/timing, hashes, selected encoded frames and export contents were independently checked. It is not continuous recording, patient evidence or a human review. The old public video and bytes remain historical. New YouTube publication awaits the requested action-time terms confirmation.

Before claiming all planned acceptance complete, finish native 200% zoom and inspect the new hosted video once publication is authorized. The author must personally complete eligibility/roster/rights and any A4 review record; current work is pre-event. Actual Devpost submission is not claimed. No clinical utility, time-saving study or contest score is asserted.

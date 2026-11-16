# Fresh Windows checkout and Chrome acceptance — 2026-11-16

The public checkout started at [`06b327c`](https://github.com/HyunStudio/HyunOptic/commit/06b327caec94dc1a650b6579fcbcdf7e9acd9de9). The final app code tested for this audit is [`aac351d`](https://github.com/HyunStudio/HyunOptic/commit/aac351dfbe41dc21cbf7ca9dcd3f2faae641dc39). Validation took place in a separate Windows checkout on a local disk and an independent Python 3.12.10 environment. The network-drive copy and its installed launcher were outside this execution.

## Reproduction

1. Clone the tested source and create a new virtual environment. Follow the [Windows setup](../../submission/README.md#run-the-submitted-code). The first editable installation was interrupted while acquiring isolated build dependencies. The completed run installed `setuptools` and `wheel` first, then used `pip install --no-build-isolation -e ".[ui,dev,ml]"` with the pip cache disabled. `pip check` passed. Streamlit 1.67.0 and PyTorch 2.15.0 were installed.
2. Run `python scripts/prepare_submission_demo.py --output demo_data/submission`. The command trained both small synthetic models for 80 epochs each. Start Streamlit using the workspace path printed by the script. This run used loopback port 18516 and opened Review Queue.
3. Create a local session with the two generated bundles and five generated inputs. Process one batch and inspect the source image and two model overlays. Four inputs completed with eight prediction records. One intentionally unreadable image appeared as an input error. Save Case 001 as held with reason `uncertain`; refresh the page and reselect the session and case to see the decision and reason.
4. Build the ZIP and download it with the browser. Run `python -m hyunoptic.review.export <downloaded-zip>` in a separate process. The [actual Chrome download](synthetic-review-evidence.zip) passed with schema `hyunoptic-review-export-v1` and six verified payloads. Its review record includes one held/uncertain case. The archive omits source filenames, image files, masks and private-note fields. Its session was created at [`495c6e1`](https://github.com/HyunStudio/HyunOptic/commit/495c6e1ef97d12c4cf5dd9884e3f555924d9dec5). ZIP creation and native Chrome download were repeated against that existing session on `aac351d`. The session field identifies the creation source.

## Display and keyboard checks

- In desktop and narrow viewport checks at 1280 and 390 CSS pixels, document and main-page scroll widths matched their client widths. The queue's data grid has its own controls.
- Windows Chrome showed its own 200% page-zoom setting on a 1920-pixel-wide window. A JSON-rendered vCDR value was clipped in the comparison columns. The corrected view showed both values in full as wrapping text to four displayed decimal places. ZIP measurement precision is unaffected.
- Tab reached the save, ZIP construction and download buttons at 200%. Enter built and downloaded the ZIP in native Chrome. The download button remained available afterward. The integrated-browser automation reported a download failure on later attempts, which is why the final archive was collected through native Chrome.
- The local suite passed 444 tests. Pillow emitted two warnings for intentionally malformed TIFF fixtures. The code commit passed all four jobs in [GitHub Actions run 43874124059](https://github.com/HyunStudio/HyunOptic/actions/runs/43874124059). See [PR #16](https://github.com/HyunStudio/HyunOptic/pull/16) for the current checks.

## Submission scope

This is a software acceptance check with synthetic inputs. Existing real-data evaluations retain their own [methods and limits](../2026-11-04-full-real-validation/README.md). The [public demo](https://youtu.be/C5KE1KaHWGI) shows the same review flow from [its November 5 capture source](../../submission/media-20261105/README.md). Its comparison numbers appear in the older presentation and its download predates the no-rerun change. This work was performed before the event. Personal review, rules verification for the final entry and Devpost submission remain with the entrant.

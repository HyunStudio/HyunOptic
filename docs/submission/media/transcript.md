# HyunOptic demonstration transcript

Actual app captures; edited timing; synthetic images/models; Microsoft Zira synthetic narration. Subtitle cue timings are approximate word-proportional timings; the full chapter text is also burned into the video.

## The problem: a number can hide a wrong prediction

HyunOptic is a local research workspace for reviewing ophthalmic AI predictions. A model can produce a measurable cup to disc ratio while locating the wrong structure. The task here is to inspect that evidence, preserve unresolved decisions, and export a traceable record.

## Start with two verified local models

This demonstration uses only synthetic images and two real CPU trained PyTorch models. Seed forty three is the primary model, and seed forty two is the comparison. The public preparation command creates both models and an isolated workspace without private research weights or an API key.

## Create a session and retain failed inputs

I select four synthetic images and one intentionally unreadable input, then confirm local retention. The session copies images to this computer. The application allows thirty megabytes per file. The unreadable case stays visible instead of disappearing from the total.

## Run a bounded processing step

Clicking Process next images runs actual image only inference with verified model bundles. The completed session contains four processed images, eight model predictions, and one input error. Processing is synchronous and bounded. This edited sequence is not a real time speed benchmark.

## Inspect the full source image

The queue orders execution failures, invalid measurements, and model disagreement for inspection. Opening a completed case shows the complete source image. Full context matters because a plausible measurement alone does not establish that the model found the correct anatomy.

## Compare actual model overlays

These are the two actual model overlays on the same synthetic image. Both predictions produce measurements, but the boundaries differ. Disagreement is a descriptive ordering signal, not calibrated confidence or diagnostic risk. Both models can also agree on a wrong structure.

## Record an unresolved decision

The review state can remain unreviewed, become reviewed, or be held. Here I select held and the reason uncertain, then save. A held decision requires a reason. The software record does not certify anatomical correctness, clinical approval, or independent human review.

## Reopen without losing the decision

After reloading the browser, I reopen the stored session and the same case. Held and uncertain remain recorded. Revision checks prevent a stale tab from silently replacing a newer decision. The application also supports recovery of unfinished processing while retaining completed results.

## Export evidence with explicit privacy limits

I build the evidence ZIP and download the verified package. A separate command line check accepted all six payloads. Default exports exclude original images, masks, filenames, local paths and private notes. Hashes do not guarantee anonymity, and the local database is not encrypted by the application.

## Check repeatability and failure behavior

Separate execution checks matched repeated prediction digests and preserved two hundred predictions after a controlled interruption of one hundred repeated synthetic cases. A changed copied model bundle failed without erasing prior decisions. Repeated cases are not independent patients, and this was not an operating system crash.

## Software evidence is separate from clinical evidence

The local suite passed three hundred twenty six tests. Linux, Windows, and actual PyTorch CPU training checks also passed in continuous integration. Earlier real data transfer failures motivate this workflow. Synthetic execution does not establish clinical accuracy, ranking efficiency, or measured time savings.

## Reproduce the workflow and inspect its limits

The repository includes source, setup instructions, aggregate research results and AI disclosures. All work shown was prepared before the hackathon. This is an AI operated demonstration with synthetic narration and edited screenshot timing. HyunOptic remains research only and must not guide diagnosis or patient care.

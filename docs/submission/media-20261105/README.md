# Current-source demonstration — 2026-11-05

[MP4](hyunoptic-current-demo.mp4) · [English captions](hyunoptic-current-demo.en.srt) · [Transcript](transcript.md) · [Validation](validation.json) · [Actual capture provenance](capture-provenance.json)

Measured duration **167.371 seconds (2:47)**, H.264/AAC, 1280×960, 12 fps. Thirteen actual browser captures and one separately generated verifier-summary card are assembled with edited timing. This is not continuous screen recording. AI operated the UI; Microsoft Zira Desktop supplies synthesized narration. Subtitle boundaries follow measured per-cue audio plus deliberate reading pauses, not word alignment. No person-specific human review is claimed.

The source is `ea4e76811c931134bc77a7684a1cf21bbc32492a`. Captures were made on base `5c9f698bd97c3707d2e4b9052c0e7870e3815916` with the exact responsive CSS patch later committed unchanged as `ea4e768`; the [acceptance audit](../../experiments/2026-11-05-final-acceptance/README.md) preserves that patch. Session creation metadata correctly retains its creation HEAD. All visible inputs and trained models are synthetic; no clinical accuracy, human time saving or event-period contribution is demonstrated.

The [workflow receipt](workflow-receipt.json) describes the actual browser-created session: four completed inputs, one unreadable input, eight predictions and held/uncertain revision 2 after reload and keyboard save. [This ZIP](synthetic-review-evidence.zip) is the actual browser download, independently verified. It excludes original images, masks, names, paths and private notes. Hash integrity does not establish medical correctness or general anonymity.

## Rebuild a new variant

Windows, Python 3.12 recommended, Microsoft Zira Desktop voice, Windows Arial fonts, PowerShell, Pillow and imageio-ffmpeg are required. The builder can alternatively take an explicit trusted `--ffmpeg` executable. Install media dependencies in a separate environment with `python -m pip install Pillow imageio-ffmpeg`; they are not runtime app dependencies.

Copy `build_demo.py`, `chapters.json`, `workflow-receipt.json`, `synthetic-review-evidence.zip`, `capture-provenance.json` and the `captures` folder to a **new** output folder outside this frozen package. From a dependency-equipped Python environment run:

```powershell
python <new-output-folder>/build_demo.py --source-commit ea4e76811c931134bc77a7684a1cf21bbc32492a --work <new-private-build-folder>
```

The script deliberately refuses to overwrite an existing MP4. Speech/encoder versions can change output bytes; the manifest verifies this preserved build rather than promising byte-identical resynthesis. Source captures remain authentic to their recorded commit; rebuilding does not create a new UI execution. The historical `../media/` package remains unchanged.

## Publication status

Local video, captions, full-decode checks and independent artifact review are complete. A new YouTube upload is pending the action-time confirmation requested for its submission/terms notice. The older public URL remains historical and is not this movie. Native 200% browser zoom acceptance is also still unverified. See the current acceptance audit before claiming submission readiness.

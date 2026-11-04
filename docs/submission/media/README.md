# Prepared demonstration media

[Public YouTube demonstration](https://youtu.be/xbs47mX0d5g) — published on the author-selected Hyun_Studio channel, with English SRT and the prepared thumbnail. [Publication verification](../VIDEO_PUBLICATION.md).

[Play/download MP4](hyunoptic-demo.mp4) · [SRT](hyunoptic-demo.en.srt) · [Transcript](transcript.md) · [Thumbnail](thumbnail.jpg)

Duration 217.507 seconds (3:38); H.264/AAC, 1280×960, 15 fps. Full audio/video decode and caption bounds passed. [Validation](validation.json), [timeline and capture provenance](timeline.json), [SHA256/byte manifest](manifest.json).

The video uses actual browser screenshots of real application execution. It is assembled with edited timing, rather than continuous footage. Models were prepared before capture. Inputs/models are synthetic, the operator is an AI assistant, and Microsoft Zira Desktop provides synthetic narration. No patient data or third-party research weights are distributed. Subtitle cues use approximate word-proportional timings; complete chapter narration is also burned into the picture.

The source application is frozen at the commit named in validation.json. The [synthetic browser evidence ZIP](synthetic-browser-evidence.zip) was downloaded through the shown UI and independently verified. Its synthetic IDs are not patient identifiers.

To verify the complete public media payloads from the repository root:

```powershell
python -c "from pathlib import Path; from scripts.verify_experiment_evidence import verify_folder; print(verify_folder(Path('docs/submission/media')))"
python -m hyunoptic.review.export docs/submission/media/synthetic-browser-evidence.zip
```

Optional authoring reproduction on Windows, with Pillow, the installed Microsoft Zira Desktop voice, and a trusted FFmpeg installation:

```powershell
python docs/submission/media/build_video.py --output reports/rebuilt_media --work reports/rebuilt_media_work --ffmpeg C:/path/to/ffmpeg.exe
```

New output/work directories are required. Source captures are preserved under `captures/`; regenerated narration/encoding may vary by operating-system voice and FFmpeg versions. This command regenerates media from authentic saved captures; it does not pretend to rerun the browser or the model experiment.

The public MP4 and supported-host YouTube publication are complete. Use https://youtu.be/xbs47mX0d5g in the Devpost video field and check the actual entry before submission; personal final review remains pending.

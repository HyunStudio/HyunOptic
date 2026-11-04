"""Author the final, disclosed narrated demo from authentic browser captures."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,textwrap,wave
from PIL import Image,ImageDraw,ImageFont
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--captures',type=Path,default=Path(__file__).resolve().parent/'captures')
parser.add_argument('--output',type=Path,required=True,help='A new media output folder')
parser.add_argument('--work',type=Path,required=True,help='A new ignored work folder')
parser.add_argument('--ffmpeg',type=Path,required=True,help='Path to an installed trusted FFmpeg binary')
args=parser.parse_args()
captures_root=args.captures.resolve()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
work=args.work.resolve();work.mkdir(parents=True,exist_ok=False)
ffmpeg=str(args.ffmpeg.resolve())
chapters=[
('The problem: a number can hide a wrong prediction',[0],
 'HyunOptic is a local research workspace for reviewing ophthalmic AI predictions. A model can produce a measurable cup to disc ratio while locating the wrong structure. The task here is to inspect that evidence, preserve unresolved decisions, and export a traceable record.'),
('Start with two verified local models',[0,1],
 'This demonstration uses only synthetic images and two real CPU trained PyTorch models. Seed forty three is the primary model, and seed forty two is the comparison. The public preparation command creates both models and an isolated workspace without private research weights or an API key.'),
('Create a session and retain failed inputs',[2,3],
 'I select four synthetic images and one intentionally unreadable input, then confirm local retention. The session copies images to this computer. The application allows thirty megabytes per file. The unreadable case stays visible instead of disappearing from the total.'),
('Run a bounded processing step',[4,5,6],
 'Clicking Process next images runs actual image only inference with verified model bundles. The completed session contains four processed images, eight model predictions, and one input error. Processing is synchronous and bounded. This edited sequence is not a real time speed benchmark.'),
('Inspect the full source image',[7,8,9],
 'The queue orders execution failures, invalid measurements, and model disagreement for inspection. Opening a completed case shows the complete source image. Full context matters because a plausible measurement alone does not establish that the model found the correct anatomy.'),
('Compare actual model overlays',[10,11],
 'These are the two actual model overlays on the same synthetic image. Both predictions produce measurements, but the boundaries differ. Disagreement is a descriptive ordering signal, not calibrated confidence or diagnostic risk. Both models can also agree on a wrong structure.'),
('Record an unresolved decision',[12,13,14,15],
 'The review state can remain unreviewed, become reviewed, or be held. Here I select held and the reason uncertain, then save. A held decision requires a reason. The software record does not certify anatomical correctness, clinical approval, or independent human review.'),
('Reopen without losing the decision',[16,17],
 'After reloading the browser, I reopen the stored session and the same case. Held and uncertain remain recorded. Revision checks prevent a stale tab from silently replacing a newer decision. The application also supports recovery of unfinished processing while retaining completed results.'),
('Export evidence with explicit privacy limits',[18,19,20],
 'I build the evidence ZIP and download the verified package. A separate command line check accepted all six payloads. Default exports exclude original images, masks, filenames, local paths and private notes. Hashes do not guarantee anonymity, and the local database is not encrypted by the application.'),
('Check repeatability and failure behavior',[6,17],
 'Separate execution checks matched repeated prediction digests and preserved two hundred predictions after a controlled interruption of one hundred repeated synthetic cases. A changed copied model bundle failed without erasing prior decisions. Repeated cases are not independent patients, and this was not an operating system crash.'),
('Software evidence is separate from clinical evidence',[10,11],
 'The local suite passed three hundred twenty six tests. Linux, Windows, and actual PyTorch CPU training checks also passed in continuous integration. Earlier real data transfer failures motivate this workflow. Synthetic execution does not establish clinical accuracy, ranking efficiency, or measured time savings.'),
('Reproduce the workflow and inspect its limits',[0,17,19],
 'The repository includes source, setup instructions, aggregate research results and AI disclosures. All work shown was prepared before the hackathon. This is an AI operated demonstration with synthetic narration and edited screenshot timing. HyunOptic remains research only and must not guide diagnosis or patient care.')]

fonts=[ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24),ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30),ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)]
captures=json.loads((captures_root/'capture-index.json').read_text())
audio_script=work/'narrate.ps1'
audio_script.write_text("""param([string]$TextFile,[string]$AudioFile)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice('Microsoft Zira Desktop')
$speaker.Rate = 1
$speaker.SetOutputToWaveFile($AudioFile)
$speaker.Speak([IO.File]::ReadAllText($TextFile))
$speaker.Dispose()
""",encoding='utf-8')
timeline=[];position=0;concat=[]
for n,(title,indices,narration) in enumerate(chapters):
    textfile=work/f'{n:02}.txt';textfile.write_text(narration,encoding='utf-8')
    audiofile=work/f'{n:02}.wav'
    subprocess.run(['powershell','-NoProfile','-File',str(audio_script),str(textfile),str(audiofile)],check=True,capture_output=True)
    with wave.open(str(audiofile)) as w: spoken=w.getnframes()/w.getframerate()
    duration=max(12,spoken+1.0)
    lines=textwrap.wrap(narration,width=102)
    for k,index in enumerate(indices):
        source=captures_root/captures[index]['file']
        canvas=Image.new('RGB',(1280,960),'#101c2b')
        with Image.open(source) as im:canvas.paste(im.resize((1280,720)),(0,0))
        d=ImageDraw.Draw(canvas)
        d.text((26,732),'ACTUAL APP CAPTURES | EDITED TIMING | SYNTHETIC DATA / MODELS | AI NARRATION',font=fonts[2],fill='#73e1df')
        assert d.textbbox((26,763),title,font=fonts[1])[2]<1280
        d.text((26,763),title,font=fonts[1],fill='white')
        for j,line in enumerate(lines):
            bbox=d.textbbox((26,808+j*29),line,font=fonts[0])
            assert bbox[2]<1280 and bbox[3]<960,(n,line,bbox)
            d.text((26,808+j*29),line,font=fonts[0],fill='#e8edf4')
        name=f'{n:02}-{k:02}.png';canvas.save(work/name)
        concat.append(f"file '{name}'\nduration {duration/len(indices):.6f}\n")
    timeline.append(dict(chapter=n+1,title=title,start=round(position,6),duration=round(duration,6),narration=narration,
                         captures=[captures[i]['file'] for i in indices],spoken_seconds=round(spoken,6)))
    position+=duration
concat.append(f"file '{len(chapters)-1:02}-{len(chapters[-1][1])-1:02}.png'\n")
assert 120<=position<=240,position
(work/'frames.txt').write_text(''.join(concat),encoding='utf-8')
audio_concat=[]
for n,t in enumerate(timeline):
    pad=work/f'{n:02}-padded.wav'
    subprocess.run([ffmpeg,'-y','-i',str(work/f'{n:02}.wav'),'-af','apad','-t',str(t['duration']),str(pad)],check=True,capture_output=True)
    audio_concat.append(f"file '{pad.name}'\n")
(work/'audio.txt').write_text(''.join(audio_concat),encoding='utf-8')
subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i','audio.txt','narration.wav'],cwd=work,check=True,capture_output=True)
video=out/'hyunoptic-demo.mp4'
encode=subprocess.run([ffmpeg,'-y','-f','concat','-safe','0','-i','frames.txt','-i','narration.wav',
    '-t',str(position),'-vf','fps=15','-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p',
    '-c:a','aac','-b:a','128k','-movflags','+faststart',str(video)],cwd=work,capture_output=True,text=True)
(work/'encode.log').write_text(encode.stderr,encoding='utf-8');assert encode.returncode==0
decoded=subprocess.run([ffmpeg,'-i',str(video),'-f','null','-'],capture_output=True,text=True)
(work/'decode.log').write_text(decoded.stderr,encoding='utf-8');assert decoded.returncode==0
def timestamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'
subtitles=[]
for t in timeline:
    words=t['narration'].split();chunks=[words[i:i+12] for i in range(0,len(words),12)];offset=0
    for chunk in chunks:
        start=t['start']+t['spoken_seconds']*offset/len(words)
        offset+=len(chunk);end=t['start']+t['spoken_seconds']*offset/len(words)
        subtitles.append(f"{len(subtitles)+1}\n{timestamp(start)} --> {timestamp(end)}\n"+textwrap.fill(' '.join(chunk),width=62)+'\n')
(out/'hyunoptic-demo.en.srt').write_text('\n'.join(subtitles),encoding='utf-8')
(out/'transcript.md').write_text('# HyunOptic demonstration transcript\n\nActual app captures; edited timing; synthetic images/models; Microsoft Zira synthetic narration. Subtitle cue timings are approximate word-proportional timings; the full chapter text is also burned into the video.\n\n'+'\n\n'.join(f"## {t['title']}\n\n{t['narration']}" for t in timeline)+'\n',encoding='utf-8')
(out/'timeline.json').write_text(json.dumps({'duration_seconds':round(position,6),'chapters':timeline,'capture_provenance':captures},indent=2)+'\n',encoding='utf-8')
shutil.copyfile(captures_root/captures[10]['file'],out/'thumbnail.jpg')
validation=dict(duration_seconds=round(position,6),dimensions=[1280,960],frames_per_second=15,video_codec='h264',audio_codec='aac',
                full_decode_passed=True,caption_bounds_checked=True,actual_source_capture_count=len(captures),
                synthetic_narration_voice='Microsoft Zira Desktop',continuous_screen_recording=False,
                subtitle_timing='Approximate word-proportional timings; complete chapter text burned in',
                source_code_commit='491d6f39f162ed048c9015cc2ac83f9e636e6999',
                reviewed_by_human=False,patient_data_included=False)
(out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
print(json.dumps(validation,indent=2),flush=True)


"""Build the disclosed 2026-11-05 demo from actual captures and timed TTS cues.

Windows + Microsoft Zira Desktop; Pillow and optional imageio-ffmpeg required.
Never overwrite a published movie. All narration is AI-generated speech.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import textwrap
import wave
from PIL import Image,ImageDraw,ImageFont


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def wrap(draw,text,font,width):
    lines=[];line=''
    for word in text.split():
        trial=(line+' '+word).strip()
        if line and draw.textlength(trial,font=font)>width:lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    return lines


def stamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit',required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--ffmpeg',type=Path)
    args=parser.parse_args()
    import re
    if not re.fullmatch('[0-9a-f]{40}',args.source_commit):parser.error('Expected full source commit')
    out=Path(__file__).resolve().parent;work=args.work.resolve()
    if (out/'hyunoptic-current-demo.mp4').exists():parser.error('Published movie already exists; use a new version directory')
    work.mkdir(parents=True,exist_ok=True)
    if args.ffmpeg:ffmpeg=str(args.ffmpeg.resolve())
    else:
        import imageio_ffmpeg
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    windows=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    title_font=ImageFont.truetype(str(windows/'arialbd.ttf'),32)
    caption_font=ImageFont.truetype(str(windows/'arial.ttf'),28)
    small_font=ImageFont.truetype(str(windows/'arial.ttf'),17)
    card_font=ImageFont.truetype(str(windows/'arial.ttf'),30)
    receipt=json.loads((out/'workflow-receipt.json').read_text(encoding='utf-8'))
    card=Image.new('RGB',(1280,720),'#101c2b');draw=ImageDraw.Draw(card)
    draw.text((48,45),'Independent check of the downloaded ZIP',font=title_font,fill='white')
    draw.text((48,102),'RECORDED VERIFIER OUTPUT | SYNTHETIC WORKFLOW',font=small_font,fill='#79e0d4')
    rows=[('Archive integrity','VALID' if receipt['valid'] else 'INVALID'),('Payload files',str(receipt['payloads'])),
          ('Input cases',f"{receipt['complete']} complete / {receipt['input_errors']} error"),
          ('Model predictions',str(receipt['predictions'])),('Held decision',f"uncertain; revision {receipt['held_revision']}"),
          ('Original filename excluded',str(receipt['filename_excluded']))]
    for n,(label,value) in enumerate(rows):
        y=158+n*64;draw.text((48,y),label,font=card_font,fill='#bfcedb');draw.text((700,y),value,font=card_font,fill='white')
    draw.text((48,585),'SHA-256: '+receipt['sha256'],font=small_font,fill='#79e0d4')
    draw.text((48,650),'Summary card from the actual result; this is not an application screenshot.',font=small_font,fill='white')
    card.save(out/'captures/verifier-result.png')
    chapters=json.loads((out/'chapters.json').read_text(encoding='utf-8'))
    overrides={1:['04-import-and-retention.png']*3+['05-session-created.png'],
               5:['18-phone-fullsize.png','03-narrow-fixed.png','03-narrow-fixed.png','18-phone-fullsize.png'],
               6:['14-export-ready.png']+['verifier-result.png']*3}
    cues=[]
    for chapter_no,chapter in enumerate(chapters):
        for index,text in enumerate(chapter['cues']):
            capture=overrides.get(chapter_no,[chapter['captures'][min(len(chapter['captures'])-1,i*len(chapter['captures'])//len(chapter['cues']))] for i in range(len(chapter['cues']))])[index]
            cues.append(dict(title=chapter['title'],text=text,capture=capture,audio=str(work/f'cue-{len(cues):02}.wav')))
    (work/'tts-cues.json').write_text(json.dumps(cues,ensure_ascii=False),encoding='utf-8')
    ps=work/'narrate.ps1'
    ps.write_text("""param([string]$CueFile)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$ttsCues = ConvertFrom-Json ([IO.File]::ReadAllText($CueFile))
foreach ($ttsCue in $ttsCues) {
  $ttsSpeaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
  $ttsSpeaker.SelectVoice('Microsoft Zira Desktop')
  $ttsSpeaker.Rate = 0
  $ttsSpeaker.SetOutputToWaveFile($ttsCue.audio)
  $ttsSpeaker.Speak($ttsCue.text)
  $ttsSpeaker.Dispose()
}
""",encoding='utf-8')
    subprocess.run(['powershell','-NoProfile','-File',str(ps),str(work/'tts-cues.json')],check=True,capture_output=True)
    position=0;frames=[];audios=[];srt=[]
    for index,cue in enumerate(cues):
        with wave.open(cue['audio']) as audio:spoken=audio.getnframes()/audio.getframerate()
        duration=max(4.5,spoken+.3)
        canvas=Image.new('RGB',(1280,960),'#101c2b')
        source=out/'captures'/cue['capture']
        with Image.open(source) as image:
            image=image.convert('RGB');image.thumbnail((1280,720),Image.Resampling.LANCZOS)
            canvas.paste(image,((1280-image.width)//2,(720-image.height)//2))
        draw=ImageDraw.Draw(canvas)
        kind='RECORDED VERIFIER SUMMARY' if cue['capture']=='verifier-result.png' else 'ACTUAL APP CAPTURE'
        disclosure=kind+' | EDITED TIMING | SYNTHETIC DATA/MODELS | AI NARRATION'
        assert draw.textlength(disclosure,font=small_font)<1228
        draw.text((26,734),disclosure,font=small_font,fill='#79e0d4')
        assert draw.textlength(cue['title'],font=title_font)<1228
        draw.text((26,768),cue['title'],font=title_font,fill='white')
        lines=wrap(draw,cue['text'],caption_font,1228)
        assert len(lines)<=3,(cue['text'],lines)
        for n,line in enumerate(lines):draw.text((26,817+n*35),line,font=caption_font,fill='#e7eef5')
        footer='Tested source '+args.source_commit+' | pre-event: 2026-11-05 | research only'
        assert draw.textlength(footer,font=small_font)<1228
        draw.text((26,936),footer,font=small_font,fill='#bfcedb')
        frame=work/f'frame-{index:02}.png';canvas.save(frame)
        padded=work/f'audio-{index:02}.wav'
        subprocess.run([ffmpeg,'-v','error','-y','-i',cue['audio'],'-af','apad','-t',str(duration),'-ar','48000','-ac','1',str(padded)],check=True,capture_output=True)
        frames.append(f"file '{frame.name}'\nduration {duration:.6f}\n")
        audios.append(f"file '{padded.name}'\n")
        start=position;position+=duration
        text='\n'.join(textwrap.wrap(cue['text'],width=72))
        srt.append(f'{index+1}\n{stamp(start)} --> {stamp(position)}\n{text}\n')
        cue.update(start=start,end=position,spoken_seconds=spoken,duration=duration,source_sha256=sha(source))
        cue.pop('audio')
    assert 120<=position<=240,position
    frames.append(f"file 'frame-{len(cues)-1:02}.png'\n")
    (work/'frames.txt').write_text(''.join(frames),encoding='utf-8')
    (work/'audio.txt').write_text(''.join(audios),encoding='utf-8')
    subprocess.run([ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','audio.txt','narration.wav'],cwd=work,check=True,capture_output=True)
    movie=out/'hyunoptic-current-demo.mp4'
    subprocess.run([ffmpeg,'-v','error','-y','-f','concat','-safe','0','-i','frames.txt','-i','narration.wav','-t',str(position),'-vf','fps=12','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(movie)],cwd=work,check=True,capture_output=True)
    subprocess.run([ffmpeg,'-v','error','-i',str(movie),'-f','null','-'],check=True,capture_output=True)
    (out/'hyunoptic-current-demo.en.srt').write_text('\n'.join(srt),encoding='utf-8')
    (out/'transcript.md').write_text('# Current HyunOptic demonstration\n\nActual app captures; edited timing; synthetic inputs/models; AI operation and Microsoft Zira narration. Each cue was synthesized separately, and subtitle boundaries use its measured, padded audio interval. No person-specific A4 review is claimed.\n\n'+'\n\n'.join('## '+c['title']+'\n\n'+' '.join(c['cues']) for c in chapters)+'\n',encoding='utf-8')
    (out/'timeline.json').write_text(json.dumps({'duration_seconds':position,'cues':cues},indent=2)+'\n',encoding='utf-8')
    validation=dict(duration_seconds=position,dimensions=[1280,960],frames_per_second=12,video_codec='h264',audio_codec='aac',full_decode_passed=True,caption_bounds_checked=True,subtitle_timing='Measured per-cue TTS audio intervals including deliberate reading pauses; not word-aligned',voice='Microsoft Zira Desktop',continuous_screen_recording=False,actual_capture_count=13,generated_verifier_cards=1,source_code_commit=args.source_commit,source_capture_basis='5c9f698 plus recorded CSS patch subsequently committed unchanged',reviewed_by_human=False,patient_data_included=False,sha256=sha(movie),bytes=movie.stat().st_size)
    (out/'validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(validation,indent=2),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())

"""Compose reviewed cuts, restrained zooms, audio cleanup and retimed captions."""
import json,subprocess,tempfile,threading,time,uuid,math
from pathlib import Path
import avtools
from captions import retime_captions,export_captions
from render import keep_ranges,video_args
from jobs import JobCancelled

def probe_streams(path):
    result=subprocess.run([avtools.ffprobe_path(),'-v','error','-show_streams','-show_format','-of','json',str(path)],capture_output=True,timeout=30)
    if result.returncode:raise ValueError('ویدیوی منبع قابل خواندن نیست.')
    obj=json.loads(result.stdout);video=next((s for s in obj['streams'] if s['codec_type']=='video'),None)
    audio=next((s for s in obj['streams'] if s['codec_type']=='audio'),None)
    duration=float(obj['format']['duration'])
    if not math.isfinite(duration) or duration<=0:raise ValueError('مدت ویدیو معتبر نیست.')
    return {'video':video,'audio':audio,'duration':duration}

def _split_keep(keep,zooms):
    out=[]
    for start,end in keep:
        boundaries=sorted({start,end,*[t for z in zooms for t in (z['start'],z['end']) if start<t<end]})
        for a,b in zip(boundaries,boundaries[1:]):
            zoom=next((z for z in zooms if z['start']<=a+.001 and z['end']>=b-.001),None)
            if b-a>.01:out.append((a,b,zoom))
    return out

def _filter(chunks,width,height,ass_file,denoise):
    parts=[];vlabels=[];alabels=[];elapsed=0
    for i,(a,b,zoom) in enumerate(chunks):
        spatial=''
        if zoom:
            scale=zoom['scale'];x=zoom['center_x'];y=zoom['center_y']
            spatial=f",crop=w='trunc(iw/{scale}/2)*2':h='trunc(ih/{scale}/2)*2':x='min(max(iw*{x}-ow/2,0),iw-ow)':y='min(max(ih*{y}-oh/2,0),ih-oh)'"
        # Allocate frames from cumulative output time, not rounded chunk durations.
        # This bounds A/V drift to one frame even after hundreds of fractional cuts.
        frames=round((elapsed+b-a)*30)-round(elapsed*30);elapsed+=b-a
        if frames:
            parts.append(f'[0:v:0]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS{spatial},scale={width}:{height},fps=30:start_time=0,tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame={frames},setsar=1[v{i}]')
            vlabels.append(f'[v{i}]')
        parts.append(f'[0:a:0]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]')
        alabels.append(f'[a{i}]')
    parts.append(''.join(vlabels)+f'concat=n={len(vlabels)}:v=1:a=0[vcat]')
    parts.append(''.join(alabels)+f'concat=n={len(chunks)}:v=0:a=1[acat]')
    if ass_file:
        escaped=str(ass_file).replace('\\','/').replace(':','\\:').replace("'","\\'")
        parts.append(f"[vcat]ass=filename='{escaped}'[vout]")
    else:parts.append('[vcat]null[vout]')
    audio='highpass=f=65,afftdn=nf=-30,acompressor=threshold=-20dB:ratio=1.6:attack=20:release=250,loudnorm=I=-16:TP=-1.5:LRA=11' if denoise else 'anull'
    parts.append('[acat]'+audio+'[aout]')
    return ';'.join(parts)

def render_educational(ctx,media,transcript,plan,kind,nvenc=None,before_register=None):
    rd=ctx.services['renders'];info=probe_streams(media['path'])
    if not info['video'] or not info['audio']:raise ValueError('ویدیو و صدای قابل استفاده لازم است.')
    keep=keep_ranges(plan['cuts'],info['duration'])
    if not keep:raise ValueError('برش‌ها تمام ویدیو را حذف کرده‌اند.')
    width=int(info['video']['width'])//2*2;height=int(info['video']['height'])//2*2
    chunks=_split_keep(keep,plan['zooms']);duration=sum(b-a for a,b in keep)
    label=rd.next_label(media['id'],kind);outdir=rd.root/media['id'];outdir.mkdir(parents=True,exist_ok=True)
    output=outdir/(label.replace(' ','_')+'_AUTO_'+uuid.uuid4().hex[:8]+'.mp4')
    sidecars=[output.with_suffix('.'+fmt) for fmt in ('srt','vtt','ass')]
    cues=retime_captions(transcript['segments'],keep)
    for fmt,target in zip(('srt','vtt','ass'),sidecars):target.write_text(export_captions(cues,fmt),encoding='utf-8')
    ass_file=output.with_suffix('.ass') if plan['options'].get('subtitles') and cues else None
    if nvenc is None:nvenc=avtools.nvenc_available()
    graph=_filter(chunks,width,height,ass_file,plan['options'].get('denoise',False))
    script=output.with_suffix('.filter.txt');script.write_text(graph,encoding='utf-8')
    command=[avtools.ffmpeg_path(),'-y','-hide_banner','-nostats','-i',media['path'],'-/filter_complex',str(script),
        '-map','[vout]','-map','[aout]',*video_args(kind,nvenc),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','-progress','pipe:1',str(output)]
    stop=threading.Event();cancelled=[];error_file=tempfile.TemporaryFile()
    proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=error_file)
    def monitor():
        deadline=time.monotonic()+max(120,min(86400,info['duration']*5+90))
        while not stop.wait(.3) and proc.poll() is None:
            if ctx.cancelled():cancelled.append(True);proc.kill();return
            if time.monotonic()>deadline:proc.kill();return
    watcher=threading.Thread(target=monitor,daemon=True);watcher.start()
    try:
        for line in proc.stdout:
            if line.startswith(b'out_time_us='):
                try:ctx.progress(60+min(38,float(line.split(b'=')[1])/1e6/duration*38))
                except ValueError:pass
        code=proc.wait();error_file.seek(0);error=error_file.read().decode('utf-8','replace')[-1200:]
        if cancelled:raise JobCancelled()
        if code:raise RuntimeError('رندر یکپارچه ناموفق بود: '+error)
        actual=probe_streams(output)
        if not actual['video'] or not actual['audio'] or abs(actual['duration']-duration)>.25:raise RuntimeError('مدت یا تراک خروجی رندر معتبر نیست.')
        if ctx.cancelled():raise JobCancelled()
        if before_register:before_register()
    except BaseException:
        if proc.poll() is None:proc.kill();proc.wait()
        for target in [output,*sidecars]:target.unlink(missing_ok=True)
        raise
    finally:
        stop.set();watcher.join(timeout=1);proc.stdout.close();error_file.close();script.unlink(missing_ok=True)
    encoder='h264_nvenc' if nvenc else 'libx264'
    row=rd.add(media['id'],label,kind,output,output.stat().st_size,len(plan['cuts']),round(duration,3),encoder,ctx.id)
    output.with_suffix('.edit.json').write_text(json.dumps({'plan_id':plan.get('id'),'cuts':plan['cuts'],'zooms':plan['zooms'],'options':plan['options'],'source_sha':media['sha256'],'transcript_revision':transcript['revision']},ensure_ascii=False,indent=2),encoding='utf-8')
    ctx.log('خروجی '+label+' آماده شد؛ '+str(len(cues))+' زیرنویس با زمان‌بندی نسخهٔ تدوین‌شده.')
    return {'render_id':row['id'],'label':label,'duration':round(duration,3),'encoder':encoder,'captions':len(cues),'subtitle_formats':['srt','vtt','ass']}

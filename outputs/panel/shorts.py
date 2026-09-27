"""Short/Reel candidate detection from transcripts + real 9:16 rendering.

Candidates come from real transcript content only (no invention). The 9:16
render composites the clip over a blurred background so screen tutorials are
never blind-cropped.
"""
import json, subprocess, uuid
from pathlib import Path
import avtools
from jobs import DependencyMissing, JobCancelled

def shorts_candidates(segments,duration=None,count=3,min_len=40,target=35.0):
    """Heuristic candidate clips: informative, sentence-like, spread out."""
    usable=[s for s in segments if len((s.get('text') or '').strip())>=min_len]
    scored=[]
    for i,s in enumerate(usable):
        text=s['text'].strip()
        score=len(text)*2
        if text[-1] in '.!؟?…': score+=40
        if i==0: score+=25
        if any(k in text for k in ('چطور','چگونه','اشتباه','راه‌حل','آسان','سریع','نکته','مهم')): score+=30
        scored.append((score,i,s))
    scored.sort(key=lambda x:-x[0])
    picked=[]
    for score,i,s in scored:
        if len(picked)>=count: break
        if any(abs(s['start']-p['start'])<20 for p in picked): continue
        picked.append(s)
    picked.sort(key=lambda s:s['start'])
    out=[]
    for s in picked:
        end=s['end']
        for nxt in segments[segments.index(s)+1:] if s in segments else []:
            if end>=s['start']+target: break
            if nxt['end']>end: end=nxt['end']
        end=max(end,s['start']+min(20.0,target))
        out.append({'start':round(s['start'],2),'end':round(end,2),
                    'duration':round(end-s['start'],2),
                    'text':s['text'].strip(),
                    'reason':'متن فشرده و جمله‌بندی کامل' if s['text'].strip()[-1:] in '.!؟?' else 'قطعه پرمحتوای transcript',
                    'hook':s['text'].strip()[:60]})
    return out

def render_short_handler(ctx):
    """Job handler: 9:16 clip (blurred background + centered video) with AAC audio."""
    mlib=ctx.services['media']; rd=ctx.services['renders']
    if not avtools.ffmpeg_path(): raise DependencyMissing(avtools.ffmpeg_missing())
    m=mlib.get(ctx.payload.get('media_id'))
    if not m: raise ValueError('رسانه پیدا نشد.')
    s=float(ctx.payload.get('start') or 0); e=float(ctx.payload.get('end') or 0)
    if e<=s: raise ValueError('بازه زمانی کاندیدا معتبر نیست.')
    has_video=True
    outdir=rd.root/m['id']; outdir.mkdir(parents=True,exist_ok=True)
    label=rd.next_label(m['id'],'short')
    out=outdir/f"SHORT_{uuid.uuid4().hex[:8]}.mp4"
    ctx.log(f"رندر عمودی {label} از {s:.1f} تا {e:.1f} ثانیه")
    ff=avtools.ffmpeg_path()
    cmd=[ff,'-y','-hide_banner','-nostats','-ss',f'{s:.3f}','-to',f'{e:.3f}','-i',m['path'],
         '-filter_complex',
         '[0:v]split[fg][bg];'
         '[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=24[bgb];'
         '[fg]scale=1080:-2[fgs];'
         '[bgb][fgs]overlay=(W-w)/2:(H-h)/2[vout];'
         '[0:a]aformat=sample_rates=44100:channel_layouts=stereo[aout]',
         '-map','[vout]','-map','[aout]','-c:v','libx264','-preset','veryfast','-crf','23',
         '-c:a','aac','-b:a','128k','-movflags','+faststart']
    if ctx.payload.get('progress'):
        cmd+=['-progress','pipe:1']
    ctx.progress(10)
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if ctx.payload.get('progress'):
        dur=e-s
        for line in proc.stdout:
            text=line.decode('ascii','replace').strip()
            if text.startswith('out_time_ms=') or text.startswith('out_time_us='):
                try:
                    done=float(text.split('=',1)[1])/1_000_000
                    if dur>0: ctx.progress(10+done/dur*88)
                except ValueError: pass
            if ctx.cancelled():
                proc.kill(); raise JobCancelled()
    code=proc.wait()
    if code!=0:
        err=proc.stderr.read().decode('utf-8','replace')[-400:]
        out.unlink(missing_ok=True)
        raise RuntimeError('رندر عمودی ناموفق بود: '+err)
    if not out.exists() or out.stat().st_size==0: raise RuntimeError('خروجی عمودی ساخته نشد.')
    row=rd.add(m['id'],label,'short',out,out.stat().st_size,0,round(e-s,2),'libx264 · 9:16',ctx.id)
    ctx.log('نسخه عمودی آماده شد.')
    return {'render_id':row['id'],'label':label,'duration':round(e-s,2),'size':row['size']}

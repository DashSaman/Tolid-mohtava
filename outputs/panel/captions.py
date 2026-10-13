"""Caption retiming around cuts, using OpenCut-AI's MIT subtitle serializers."""
import math,re
from vendor import opencut_subtitles as upstream

def retime_captions(segments,keep):
    cues=[];offset=0
    for range_index,(start,end) in enumerate(keep):
        for segment in segments:
            words=segment.get('words') or []
            units=[{'start':w['start'],'end':w['end'],'text':w.get('word','').strip()} for w in words] if words else [segment]
            for unit in units:
                a=max(start,float(unit['start']));b=min(end,float(unit['end']))
                text=(unit.get('text') or '').strip()
                if b>a+.02 and text:cues.append({'start':round(offset+a-start,3),'end':round(offset+b-start,3),'text':text,'range':range_index})
        offset+=end-start
    # Keep cue text short; don't bridge a reading pause or a hard cut.
    out=[]
    for cue in cues:
        if out and cue['range']==out[-1]['range'] and cue['start']-out[-1]['end']<.22 and cue['end']-out[-1]['start']<4 and len(out[-1]['text'])+len(cue['text'])<70:
            out[-1]['text']+=' '+cue['text'];out[-1]['end']=cue['end']
        else:out.append(dict(cue))
    return [{k:v for k,v in cue.items() if k!='range'} for cue in out]

def export_captions(cues,fmt):
    if fmt not in ('srt','vtt','ass'):raise ValueError('قالب زیرنویس معتبر نیست.')
    quantum=100 if fmt=='ass' else 1000
    clean=[]
    for c in cues:
        if not all(isinstance(c[k],(int,float)) and math.isfinite(c[k]) for k in ('start','end')):raise ValueError('زمان زیرنویس معتبر نیست.')
        a=round(max(0,c['start'])*quantum)/quantum;b=round(c['end']*quantum)/quantum
        if b<=a:continue
        text=re.sub(r'[\x00-\x08\x0b-\x1f]','',c['text'])
        # ASS control overrides must not be injected by source text.
        if fmt=='ass':text=text.replace('\\','／').replace('{','｛').replace('}','｝')
        clean.append({'start':a,'end':b,'text':text})
    if fmt=='srt':return upstream.segments_to_srt(clean)
    if fmt=='vtt':return upstream.segments_to_vtt(clean)
    return upstream.segments_to_ass(clean,{'font_name':'DejaVu Sans','font_size':38,'bold':0})

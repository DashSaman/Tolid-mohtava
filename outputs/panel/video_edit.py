"""Validated educational edit decisions. AI suggests; source evidence sets the bounds."""
import hashlib,json,math,re

WAIT=('منتظر','صبر','نصب می','راه‌اندازی','بارگذاری','لود','ذخیره می','ریستارت','reboot','restart','wait','install')
def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def educational_silence_cuts(silences,segments,duration,activity=()):
    cuts=[];budget=duration*.2
    for start,end,length in silences:
        if not all(finite(v) for v in (start,end,length)) or length<2:continue
        if any(a<end and b>start for a,b in activity):continue
        before=[s for s in segments if start-12<=s['end']<=start+.2]
        if any(any(w in s['text'].lower() for w in WAIT) for s in before):continue
        a=max(0,start+.3);b=min(duration,end-.3)
        for segment in segments:
            if segment['start']<b and segment['end']>a:
                # Whisper speech and acoustic silence can disagree; preserve the speech.
                a=max(a,segment['end']+.18)
        b=min(b,a+max(0,budget-sum(e-s for s,e in cuts)))
        if b-a>=.5:cuts.append((round(a,3),round(b,3)))
    return cuts

def _norm(text):
    text=str(text).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹يک','0123456789یک'))
    return re.sub(r'\s+',' ',text).strip()

def semantic_decisions(proposals,segments,duration,existing_cuts=()):
    decisions=[];used=set();preserved=set();budget=duration*.2
    for p in proposals if isinstance(proposals,list) else []:
        if not isinstance(p,dict):continue
        i,j=p.get('segment'),p.get('duplicate_of');confidence=p.get('confidence',0)
        if type(i)!=int or type(j)!=int or i==j or not 0<=i<len(segments) or not 0<=j<len(segments):continue
        if not finite(confidence) or confidence<.9 or confidence>1 or i in used or i in preserved or j in used:continue
        a,b=segments[i],segments[j];ta,tb=_norm(a['text']),_norm(b['text'])
        # A changed command or negation can be a tiny textual difference but a new step.
        if len(ta)<18 or ta!=tb:continue
        if re.findall(r'\d+(?:\.\d+)*',ta)!=re.findall(r'\d+(?:\.\d+)*',tb):continue
        if abs(a['start']-b['start'])>120 or any(w in a['text'] for w in ('تکرار می‌کن','مثال دیگر','دوباره تست','مقایسه')):continue
        start=max(0,a['start']-.08);end=min(duration,a['end']+.08)
        if not all(finite(v) for v in (start,end)) or end<=start:continue
        current=[*existing_cuts,*[(d['start'],d['end']) for d in decisions]]
        if any(s<b['end'] and e>b['start'] for s,e in [*current,(start,end)]):continue
        if any(start<segments[k]['end'] and end>segments[k]['start'] for k in preserved):continue
        if sum(d['end']-d['start'] for d in decisions)+end-start>budget:continue
        decisions.append({'start':round(start,3),'end':round(end,3),'reason_code':'repeat','confidence':confidence,
                          'reason':'برداشت تکراری؛ جملهٔ همسان در بخش '+str(j+1)+' حفظ می‌شود.','segment':i,'duplicate_of':j})
        used.add(i);preserved.add(j)
    return decisions

def validate_zooms(regions,duration):
    out=[]
    for r in regions if isinstance(regions,list) else []:
        if not isinstance(r,dict):continue
        box=r.get('box');start,end,confidence=r.get('start'),r.get('end'),r.get('confidence',0)
        if not isinstance(box,list) or len(box)!=4 or not all(finite(v) for v in [start,end,confidence,*box]):continue
        x,y,w,h=box
        if not 0<=start<end<=duration or end-start>12 or confidence<.9 or confidence>1:continue
        if x<0 or y<0 or w<.1 or h<.1 or x+w>1 or y+h>1:continue
        if any(start<z['end'] and end>z['start'] for z in out):continue
        scale=min(1.3,1/(w+.15),1/(h+.15))
        if scale<1.08:continue
        out.append({'start':round(start,3),'end':round(end,3),'box':box,'confidence':confidence,'scale':round(scale,3),
                    'center_x':x+w/2,'center_y':y+h/2,'reason':str(r.get('reason','ناحیهٔ تنظیمات'))[:160]})
    return sorted(out,key=lambda r:r['start'])[:12]

def plan_fingerprint(raw_sha,revision,cuts,options,zooms):
    data={'raw':raw_sha,'revision':revision,'cuts':cuts,'options':options,'zooms':zooms}
    return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

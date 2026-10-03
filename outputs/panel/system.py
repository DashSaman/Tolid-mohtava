"""System health and storage introspection. Only real, local observations."""
import ctypes, json, os, platform, subprocess, sys, threading, time
from pathlib import Path
import avtools
import transcribe

_gpu_cache={'probed_at':None,'result':None}
_kinds_fa={'ok':'سالم','limited':'محدود','off':'قطع','setup':'نیازمند تنظیم','credential':'نیازمند Credential'}

def status_fa(kind): return _kinds_fa.get(kind,kind)

def ffmpeg_version():
    ff=avtools.ffmpeg_path()
    if not ff: return None
    try:
        out=subprocess.run([ff,'-hide_banner','-version'],capture_output=True,timeout=20)
        return out.stdout.decode('utf-8','replace').splitlines()[0].strip()
    except Exception:
        return None

def gpu_detected():
    try:
        out=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version',
                            '--format=csv,noheader'],capture_output=True,timeout=15)
        if out.returncode==0:
            line=out.stdout.decode('utf-8','replace').splitlines()[0]
            parts=[p.strip() for p in line.split(',')]
            return {'name':parts[0] if parts else None,'memory':parts[1] if len(parts)>1 else None,
                    'driver':parts[2] if len(parts)>2 else None}
    except Exception:
        pass
    return None

def gpu_probe(model_size='tiny'):
    """Deep GPU check: real tiny-model inference. Cached; runs once per request."""
    if _gpu_cache['result'] and time.time()-_gpu_cache['probed_at']<600:
        return _gpu_cache['result']
    result={'status':'off','detail':''}
    try:
        if not transcribe.engine_available():
            result['detail']='faster-whisper نصب نیست'
        elif not transcribe.detect_device()=='cuda':
            result['detail']='هیچ GPU سازگاری پیدا نشد'
        else:
            transcribe._ensure_cuda_dlls()
            from faster_whisper import WhisperModel
            model=WhisperModel(model_size,device='cuda',compute_type='float16')
            t0=time.time()
            seg,_=model.transcribe(_silent_wav(),language='fa')
            list(seg)
            result={'status':'ok','detail':f'استنتاج CUDA موفق (~{time.time()-t0:.1f}s)'}
    except Exception as e:
        result={'status':'limited','detail':str(e)[:300]}
    _gpu_cache['probed_at']=time.time(); _gpu_cache['result']=result
    return result

def _silent_wav():
    import tempfile, wave, struct
    p=os.path.join(tempfile.gettempdir(),'panel-silence.wav')
    if not os.path.exists(p):
        with wave.open(p,'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
            w.writeframes(b'\x00\x00'*16000)
    return p

def health_payload(db_path,queue_counts,workers):
    ff=avtools.ffmpeg_path()
    whisper_ok=transcribe.engine_available()
    try:
        import faster_whisper
        wv=getattr(faster_whisper,'__version__','?')
    except Exception:
        wv=None
    db=Path(db_path)
    gpu=gpu_detected()
    return [
      {'name':'پایتون','status':'ok','detail':platform.python_version()+' · '+platform.platform()},
      {'name':'تبدیل‌کنندهٔ ویدیو (FFmpeg)','status':'ok' if ff else 'setup','detail':ffmpeg_version() or avtools.ffmpeg_missing()},
      {'name':'بررسی رسانه (FFprobe)','status':'ok' if avtools.ffprobe_path() else 'setup','detail':avtools.ffprobe_path() or ''},
      {'name':'تبدیل گفتار (Whisper)','status':'ok' if whisper_ok else 'setup',
       'detail':('v'+wv) if wv else 'نصب نشده؛ متن دستی یا نصب بسته'},
      {'name':'پردازندهٔ گرافیکی (GPU)','status':'limited' if gpu else 'off',
       'detail':(gpu['name']+' · '+gpu['driver']) if gpu else 'GPU مخصوص پیدا نشد؛ پردازش روی CPU انجام می‌شود'},
      {'name':'رمزگذاری ویدیو (NVENC)','status':'ok' if avtools.nvenc_available() else 'limited',
       'detail':'رندر نهایی با NVENC' if avtools.nvenc_available() else 'رندر نهایی با CPU انجام می‌شود'},
      {'name':'پایگاه داده','status':'ok' if db.exists() else 'setup','detail':str(db)+' · '+(db.stat().st_size//1024 if db.exists() else 0).__str__()+' KB'},
      {'name':'صف کارها','status':'ok','detail':f'{workers} worker · '+' · '.join(f'{k}: {v}' for k,v in queue_counts.items())},
      {'name':'مدل زبانی محلی (LLM)','status':'credential','detail':'هیچ اتصال مدل زبانی پیکربندی نشده است'},
      {'name':'سرویس‌های سئو','status':'credential','detail':'DispatchSEO در GrowthOS ارجاع شده؛ اتصال زنده تأیید نشده'},
      {'name':'انتشار در شبکه‌ها','status':'credential','detail':'OAuth لازم است؛ فعلاً فقط بسته dry-run'},
    ]

def drives():
    """Real local drives: letter, label, free/total bytes, type."""
    out=[]
    try:
        bitmask=ctypes.windll.kernel32.GetLogicalDrives()
    except Exception:
        return out
    for i in range(26):
        if not (bitmask>>i)&1: continue
        letter=chr(ord('A')+i)+':\\'
        free=total=None; label=''; dtype=''
        try:
            vol=ctypes.create_unicode_buffer(261); fs=ctypes.create_unicode_buffer(261)
            if ctypes.windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(letter),vol,261,None,None,None,fs,261):
                label=vol.value
            sfree=ctypes.c_ulonglong(); stotal=ctypes.c_ulonglong()
            if ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(letter),None,ctypes.byref(stotal),ctypes.byref(sfree)):
                free,total=sfree.value,stotal.value
            t=ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(letter))
            dtype={2:'removable',3:'fixed',4:'network',5:'cdrom'}.get(t,'unknown')
        except Exception:
            continue
        if total:
            out.append({'letter':letter,'label':label,'free':free,'total':total,'type':dtype})
    return out

def dir_size(path):
    total=0
    p=Path(path)
    if not p.is_dir(): return 0
    for f in p.rglob('*'):
        try:
            if f.is_file(): total+=f.stat().st_size
        except OSError: pass
    return total

"""Locate FFmpeg/FFprobe on this machine. No download, no install here."""
import os, shutil
from pathlib import Path

def _winget_ffmpeg():
    base=Path.home()/'AppData/Local/Microsoft/WinGet/Packages'
    if not base.is_dir(): return None
    for hit in sorted(base.glob('Gyan.FFmpeg*/**/bin/ffmpeg.exe')):
        return hit
    return None

def ffmpeg_path():
    p=os.environ.get('TEHNET_FFMPEG')
    if p and Path(p).is_file(): return p
    found=shutil.which('ffmpeg')
    if found: return found
    w=_winget_ffmpeg()
    return str(w) if w else None

def ffprobe_path():
    ff=ffmpeg_path()
    if ff:
        cand=Path(ff).with_name('ffprobe.exe')
        if cand.is_file(): return str(cand)
    found=shutil.which('ffprobe')
    return found

def nvenc_available():
    """True only if the ffmpeg binary lists h264_nvenc. Honest capability check."""
    ff=ffmpeg_path()
    if not ff: return False
    import subprocess
    try:
        out=subprocess.run([ff,'-hide_banner','-encoders'],capture_output=True,timeout=30)
        return b'h264_nvenc' in out.stdout
    except Exception:
        return False

def ffmpeg_missing():
    return 'FFmpeg نصب نیست؛ این بخش از پردازش رسانه در دسترس نیست.'

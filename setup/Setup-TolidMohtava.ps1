# Setup-TolidMohtava.ps1 — idempotent Windows bootstrap for a fresh clone.
# Safe to re-run: installs only what's missing, never deletes data or secrets.
# Usage:  powershell -ExecutionPolicy Bypass -File setup\Setup-TolidMohtava.ps1
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location $root
$log=Join-Path $root 'work\setup.log'; New-Item -ItemType Directory -Force -Path (Split-Path $log)|Out-Null
function Info($m){ "$([DateTime]::Now.ToString('s'))  $m" | Tee-Object -FilePath $log -Append }
function Have($c){ Get-Command $c -ErrorAction SilentlyContinue }

Info "== Tolid-mohtava bootstrap (idempotent) =="

# 1) Python
if(-not (Have python) -and (Have py)){ Info "python alias missing; py launcher present (OK)" }
elseif(-not (Have python)){
  Info "Installing Python 3.12 via winget..."; winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements | Out-Null
}
$cand=@(); if(Have py){$cand+='py'}
if(Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"){$cand+="$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"}
if(Have python){$cand+='python'}
if(-not $cand){ throw 'Python still missing — install manually and re-run' }
$py=$cand[0]
Info "Python: $py (& $($py) --version)"

# 2) FFmpeg (winget if absent; panel can also auto-locate)
if(-not (Have ffmpeg)){
  Info 'Installing FFmpeg via winget...'; winget install --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements | Out-Null
  Info ('FFmpeg: ' + $(if(Have ffmpeg){'installed'}else{'absent — panel will auto-locate winget path or set TEHNET_FFMPEG'}))
} else { Info 'FFmpeg: present' }

# 3) Python deps (panel is stdlib-only; these enable GPU whisper + edge-tts sample)
& $py -m pip install --quiet --disable-pip-version-check faster-whisper==1.2.1 2>$null
& $py -m pip install --quiet --disable-pip-version-check nvidia-cublas-cu12 nvidia-cudnn-cu12 2>$null
& $py -m pip install --quiet --disable-pip-version-check google-ads==25.1.0 2>$null
Info 'pip deps ensured (faster-whisper==1.2.1, google-ads==25.1.0 for Keyword Planner; CUDA wheels optional→CPU fallback)'

# 4) Directories
foreach($d in @('outputs\panel\data','outputs\panel\data\media','outputs\panel\data\renders','work')){ New-Item -ItemType Directory -Force -Path (Join-Path $root $d)|Out-Null }
Info 'directories ensured'

# 5) Database initialization (server creates schema on first run; just validate import)
& $py -c "import sys; sys.path.insert(0,'outputs/panel'); import server" 2>$null
if($LASTEXITCODE -ne 0){ & $py -c "import sys; sys.path.insert(0,'outputs/panel'); import store, jobs, media" }
Info 'panel modules import OK'

# 6) Config template
if(-not (Test-Path '.env')){ Copy-Item '.env.example' '.env'; Info '.env created from template (fill credentials later; NEVER commit it)' } else { Info '.env already exists (kept)' }

# 7) AI runtime expectation
Info 'AI runtime expectation: LM Studio server on http://127.0.0.1:1234 with qwen2.5-7b-instruct (fallback: meta-llama-3-8b-instruct). Start: lms server start; lms load qwen2.5-7b-instruct --gpu max'
try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:1234/v1/models' -TimeoutSec 3 -UseBasicParsing; Info ('LM Studio reachable: '+$r.StatusCode) } catch { Info 'LM Studio not reachable (optional until content generation; panel will report honestly)' }

# 8) Verify installation
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Verify-Installation.ps1')
Info 'bootstrap done. Start panel: Open-Panel.cmd  (http://127.0.0.1:8766)'

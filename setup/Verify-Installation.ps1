# Verify-Installation.ps1 — machine migration / health verification.
# Exit codes: 0 READY · 1 READY_WITH_OPTIONAL_WARNINGS · 2 BLOCKED
$ErrorActionPreference='SilentlyContinue'
$root=Split-Path -Parent $PSScriptRoot; Set-Location $root
$cand = @()
if(Get-Command py -ErrorAction SilentlyContinue){ $cand += 'py' }
if(Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"){ $cand += "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }
if(Get-Command python -ErrorAction SilentlyContinue){ $cand += 'python' }
$py = $cand[0]
$warn=0; $block=0
function Check($name,$ok,$level,$detail){
  $tag = if($ok){'OK '} elseif($level -eq 'warn'){$script:warn++;'WARN'} else {$script:block++;'BLOCK'}
  Write-Host ("[{0}] {1} {2}" -f $tag,$name,$detail)
}

Check 'Python'      ((& $py --version) -match '3\.(\d+)')'warn' (& $py --version)
Check 'Git'         ((git --version)) 'warn' ''
Check 'FFmpeg'      ((ffmpeg -version | Select-Object -First 1)) 'warn' '(panel auto-locates winget path if not on PATH)'
& $py -c "import faster_whisper; print(faster_whisper.__version__)" 2>$null
Check 'faster-whisper' ($LASTEXITCODE -eq 0) 'warn' 'pip install faster-whisper'
Check 'GPU(nvidia-smi)' ((nvidia-smi --query-gpu=name --format=csv,noheader)) 'warn' '(CPU fallback automatic)'
& $py -c "import sys; sys.path.insert(0,'outputs/panel'); import avtools; print(avtools.nvenc_available())" 2>$null
Check 'NVENC'       ($LASTEXITCODE -eq 0) 'warn' 'CPU render fallback automatic'
Check 'LM Studio'   ((& $py -c "import urllib.request;print(json.load(urllib.request.urlopen('http://127.0.0.1:1234/v1/models',timeout=3))['data'][0]['id'])" 2>$null)) 'warn' '(start: lms server start; lms load qwen2.5-7b-instruct --gpu max)'
& $py -c "import sys; sys.path.insert(0,'outputs/panel'); import server" *> $null
Check 'Panel modules' ($LASTEXITCODE -eq 0) 'block' 'server.py + full handler registry'
Check 'Data dir writable' ((Test-Path 'outputs\panel\data') -or ((New-Item -ItemType Directory -Force -Path 'outputs\panel\data') -ne $null)) 'block' ''
Check 'DB init'     ((& $py -c "import sys; sys.path.insert(0,'outputs/panel'); from store import Store; s=Store('outputs/panel/data/content.sqlite'); print('schema-ok')")) 'block' ''
& $py -m unittest tests.test_store tests.test_jobs *> $null
$testsOk = if($LASTEXITCODE -eq 0){'pass'}else{'fail'}
Check 'Unit tests smoke' ($testsOk -eq 'pass') 'warn' $testsOk
Check 'My Passport' ((Get-Volume | Where-Object {$_.FileSystemLabel -like '*Passport*'} | Select-Object -First 1 -ExpandProperty DriveLetter)) 'warn' '(archive optional; never auto-delete)'

if($block){ Write-Host 'RESULT: BLOCKED' -ForegroundColor Red; exit 2 }
if($warn){ Write-Host 'RESULT: READY_WITH_OPTIONAL_WARNINGS' -ForegroundColor Yellow; exit 1 }
Write-Host 'RESULT: READY' -ForegroundColor Green; exit 0

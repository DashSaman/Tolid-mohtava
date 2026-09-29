# Backup-TolidMohtava.ps1 — safe project backup (DB + config + media index).
# Usage: powershell -ExecutionPolicy Bypass -File setup\Backup-TolidMohtava.ps1 [-IncludeMedia] [-Out D:\backups]
param([switch]$IncludeMedia,[string]$Out='')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot; Set-Location $root
if(-not $Out){ $Out=Join-Path $root 'outputs\backups' }
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'; $dir=Join-Path $Out "tolid-$stamp"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

# python resolution (avoid WindowsApps stub)
$cand=@()
if(Get-Command py -ErrorAction SilentlyContinue){ $cand+='py' }
if(Test-Path "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"){ $cand+="$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }
if(Get-Command python -ErrorAction SilentlyContinue){ $cand+='python' }
if(-not $cand){ throw 'Python not found - run setup\Setup-TolidMohtava.ps1 first' }
$py=$cand[0]

# 1) CONSISTENT sqlite backup (WAL-safe, works while panel is running)
$db=Join-Path $root 'outputs\panel\data\content.sqlite'
$dst=Join-Path $dir 'content.sqlite'
if(Test-Path $db){
  & $py -c ("import sqlite3;s=sqlite3.connect(r'{0}');d=sqlite3.connect(r'{1}');s.backup(d);d.close();s.close()".Replace('{0}',$db).Replace('{1}',$dst))
  if($LASTEXITCODE -ne 0 -or -not (Test-Path $dst)){ throw 'sqlite backup failed' }
} else { throw "database not found: $db" }

# 2) environment manifest + media index (no \n literals in -c!)
Copy-Item (Join-Path $root 'setup\ENVIRONMENT.json') $dir -Force
& $py -c "import json,pathlib;[json.dump({'name':f.name,'bytes':f.stat().st_size},open(r'$dir\media-index.json','a',encoding='utf-8')) for f in []]" 2>$null
& $py -c "import json,pathlib;fs=[{'name':f.name,'bytes':f.stat().st_size} for f in pathlib.Path(r'outputs/panel/data/media').glob('*') if f.is_file()];json.dump(fs,open(r'$dir\media-index.json','w',encoding='utf-8'),ensure_ascii=False)" 2>$null

# 3) optional RAW media (large)
if($IncludeMedia){ Copy-Item (Join-Path $root 'outputs\panel\data\media') (Join-Path $dir 'media') -Recurse -Force }

# 4) .env (kept OUT of Git; stored alongside backup with clear name)
if(Test-Path (Join-Path $root '.env')){ Copy-Item (Join-Path $root '.env') (Join-Path $dir 'env.KEEP-PRIVATE.txt') -Force }

Write-Host "Backup ready: $dir"
Write-Host ("media: " + $(if($IncludeMedia){'RAW included'}else{'index only (use -IncludeMedia for RAW)'}))

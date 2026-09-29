# Backup-TolidMohtava.ps1 — safe project backup (DB + config template state + indexes).
# Usage: powershell -ExecutionPolicy Bypass -File setup\Backup-TolidMohtava.ps1 [-IncludeMedia] [-Out D:\backups]
param([switch]$IncludeMedia,[string]$Out='')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot; Set-Location $root
if(-not $Out){ $Out=Join-Path $root 'outputs\backups' }
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'; $dir=Join-Path $Out "tolid-$stamp"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$py = if(Get-Command python -ErrorAction SilentlyContinue){'python'} else {'py -3'}

# 1) SQLite consistent backup via API (server may be running)
& $py outputs\panel\backup.py 2>$null
$db=Join-Path $root 'outputs\panel\data\content.sqlite'
if(Test-Path $db){ Copy-Item $db (Join-Path $dir 'content.sqlite') }
Copy-Item (Join-Path $root 'setup\ENVIRONMENT.json') $dir
if(Test-Path '.env'){ Copy-Item '.env' (Join-Path $dir 'env.EXCLUDED-FROM-GIT-keep-safe.txt') }
# 2) media index + optional RAW
& $py -c "import json,sys,os; sys.path.insert(0,'outputs/panel');`nfrom media import MediaLibrary;`n" 2>$null
Get-ChildItem 'outputs\panel\data\media' -File -ErrorAction SilentlyContinue | Select-Object Name,Length | ConvertTo-Json | Out-File (Join-Path $dir 'media-index.json')
if($IncludeMedia){ Copy-Item 'outputs\panel\data\media' (Join-Path $dir 'media') -Recurse }
Write-Host "Backup ready: $dir (media: $(if($IncludeMedia){'included'}else{'index only — rerun with -IncludeMedia for RAW'})"

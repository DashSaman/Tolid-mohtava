# Restore-TolidMohtava.ps1 — restore a Backup-TolidMohtava folder into THIS clone.
# NEVER silently overwrites: existing DB is timestamped aside first.
# Usage: powershell -ExecutionPolicy Bypass -File setup\Restore-TolidMohtava.ps1 -From D:\backups\tolid-...  [-WithMedia]
param([Parameter(Mandatory=$true)][string]$From,[switch]$WithMedia)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot; Set-Location $root
$srcDb=Join-Path $From 'content.sqlite'
if(-not (Test-Path $srcDb)){ throw "content.sqlite not found in $From" }
$dataDir=Join-Path $root 'outputs\panel\data'; New-Item -ItemType Directory -Force -Path $dataDir|Out-Null
$dst=Join-Path $dataDir 'content.sqlite'
if(Test-Path $dst){
  $aside=Join-Path $dataDir ("content.pre-restore-{0}.sqlite" -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
  Copy-Item $dst $aside; Write-Host "existing DB kept aside: $aside"
}
Copy-Item $srcDb $dst
if($WithMedia -and (Test-Path (Join-Path $From 'media'))){
  Copy-Item (Join-Path $From 'media') (Join-Path $dataDir 'media') -Recurse -Force
  Write-Host 'media restored (checksums recomputable via panel Storage page)'
}
Write-Host 'restore done — run setup\Verify-Installation.ps1 then Open-Panel.cmd. Secrets (.env) must be re-entered by you.'

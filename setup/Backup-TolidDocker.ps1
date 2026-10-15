param([string]$Destination='D:\Tolid-Mohtava\backups')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir=Join-Path $Destination $stamp
if(Test-Path -LiteralPath $backupDir) { throw 'Backup destination already exists; no overwrite.' }
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
$dockerPath='C:\Program Files\Docker\Docker\resources\bin\docker.exe'
if(!(Test-Path -LiteralPath $dockerPath)) { $dockerPath=(Get-Command docker -ErrorAction Stop).Source }
$remoteFile="/tmp/tolid-backup-$stamp.sqlite"
$code="import sqlite3; s=sqlite3.connect('file:/app/outputs/panel/data/content.sqlite?mode=ro',uri=True,timeout=30); d=sqlite3.connect('$remoteFile'); s.backup(d); assert d.execute('pragma integrity_check').fetchone()[0]=='ok'; d.close(); s.close(); print('backup integrity: ok')"
& $dockerPath compose exec -T tolid-web python -c $code
if($LASTEXITCODE -ne 0) { throw 'SQLite snapshot failed.' }
$localFile=Join-Path $backupDir 'content.sqlite'
& $dockerPath compose cp "tolid-web:$remoteFile" $localFile
if($LASTEXITCODE -ne 0) { throw 'Snapshot copy failed.' }
$hashAlgorithm=[Security.Cryptography.SHA256]::Create()
$fileStream=[IO.File]::OpenRead($localFile)
try { $digest=[BitConverter]::ToString($hashAlgorithm.ComputeHash($fileStream)).Replace('-','') }
finally { $fileStream.Dispose();$hashAlgorithm.Dispose() }
[IO.File]::WriteAllText((Join-Path $backupDir 'SHA256.txt'),"$digest  content.sqlite`r`n",(New-Object Text.UTF8Encoding($false)))
Write-Host "Backup verified: $backupDir"
Write-Host 'Original media and renders remain on D:. Use the archive workflow for an independent media copy.'

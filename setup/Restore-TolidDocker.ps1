param([Parameter(Mandatory=$true)][string]$Backup)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$source=(Resolve-Path -LiteralPath $Backup).Path
if(!(Test-Path -LiteralPath $source -PathType Leaf)) { throw 'Backup file is missing.' }
Write-Host 'Restore replaces panel database state. Current media files are preserved.'
if((Read-Host 'Type RESTORE to continue') -cne 'RESTORE') { throw 'Restore cancelled.' }
& "$PSScriptRoot\Backup-TolidDocker.ps1"
if($LASTEXITCODE -ne 0) { throw 'Pre-restore backup failed; database not changed.' }
$dockerPath='C:\Program Files\Docker\Docker\resources\bin\docker.exe'
if(!(Test-Path -LiteralPath $dockerPath)) { $dockerPath=(Get-Command docker -ErrorAction Stop).Source }
$backupParent=Split-Path -Parent $source
$backupName=Split-Path -Leaf $source
$restoreCode=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'restore_database.py'))
& $dockerPath compose stop tolid-web
if($LASTEXITCODE -ne 0) { throw 'Could not stop the panel; restore not attempted.' }
try {
    & $dockerPath compose run --rm --no-deps --user '10001:10001' -v "${backupParent}:/restore-input:ro" --entrypoint python tolid-web -c $restoreCode "/restore-input/$backupName" '/app/outputs/panel/data/content.sqlite'
    if($LASTEXITCODE -ne 0) { throw 'Restore failed; inspect the error and the pre-restore backup.' }
} finally { & "$PSScriptRoot\Start-TolidDocker.ps1" -NoBrowser }

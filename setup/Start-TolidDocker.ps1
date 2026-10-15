param([switch]$NoBrowser)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$dockerPath='C:\Program Files\Docker\Docker\resources\bin\docker.exe'
if(!(Test-Path -LiteralPath $dockerPath)) { $dockerPath=(Get-Command docker -ErrorAction Stop).Source }
& $dockerPath info *> $null
if($LASTEXITCODE -ne 0) {
    Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
    for($attempt=0;$attempt -lt 60;$attempt++) {
        Start-Sleep -Seconds 3
        & $dockerPath info *> $null
        if($LASTEXITCODE -eq 0) { break }
    }
    if($LASTEXITCODE -ne 0) { throw 'Docker did not become ready. Open Docker Desktop and try again.' }
}
$composeArgs=@('compose','-f','compose.yaml')
$archivePath='E:\Tolid-Mohtava-Archive'
if(Test-Path -LiteralPath '.env') {
    $archiveEntry=Get-Content -LiteralPath '.env' | Where-Object { $_ -match '^TOLID_ARCHIVE_DIR=' } | Select-Object -Last 1
    if($archiveEntry) { $archivePath=$archiveEntry.Split('=',2)[1].Trim() }
}
if(Test-Path -LiteralPath $archivePath) { $composeArgs+=@('-f','compose.archive.yaml') }
& $dockerPath @composeArgs up -d --no-build
if($LASTEXITCODE -ne 0) { throw 'Panel start failed. See the Docker error above.' }
$ready=$false
for($attempt=0;$attempt -lt 40;$attempt++) {
    try { $response=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:18767/api/health' -TimeoutSec 8; if($response.StatusCode -eq 200) { $ready=$true;break } } catch {}
    Start-Sleep -Seconds 2
}
if(!$ready) { throw 'The panel did not become healthy. Run Status-Tolid-Docker.cmd.' }
Write-Host 'Panel ready: http://127.0.0.1:18767'
if(!$NoBrowser) { Start-Process 'http://127.0.0.1:18767' }

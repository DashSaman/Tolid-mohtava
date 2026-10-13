$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
Write-Host 'Enable YouTube Data API v3 in your Google Cloud project.'
Write-Host 'Create an OAuth Web client. Authorized redirect URI:'
Write-Host 'http://127.0.0.1:18767/oauth/callback'
Write-Host 'For a Testing OAuth app, add your channel account as a test user.'
$clientId=(Read-Host 'OAuth Client ID').Trim()
if($clientId -notmatch '^[A-Za-z0-9.-]+\.apps\.googleusercontent\.com$') { throw 'Invalid Client ID.' }
$secretEntry=Read-Host 'OAuth Client Secret (hidden)' -AsSecureString
$secretPointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretEntry)
try { $clientSecret=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer) }
if($clientSecret -notmatch '^[A-Za-z0-9_-]{10,}$') { throw 'Invalid Client Secret.' }
$secretPath=Join-Path $projectRoot 'runtime\secrets\tolid.env'
if(!(Test-Path -LiteralPath $secretPath)) { throw 'Existing panel secret file is missing; authentication settings were not changed.' }
$lines=@(Get-Content -LiteralPath $secretPath | Where-Object { $_ -notmatch '^(YOUTUBE_CLIENT_ID|YOUTUBE_CLIENT_SECRET|OAUTH_REDIRECT_BASE)=' })
$lines+=@("YOUTUBE_CLIENT_ID=$clientId","YOUTUBE_CLIENT_SECRET=$clientSecret",'OAUTH_REDIRECT_BASE=http://127.0.0.1:18767')
[IO.File]::WriteAllLines($secretPath,$lines,(New-Object Text.UTF8Encoding($false)))
$clientSecret=$null;$lines=$null
Write-Host 'Saved locally. Restarting this panel only.'
& "$PSScriptRoot\Start-TolidDocker.ps1" -NoBrowser
if($LASTEXITCODE -ne 0) { throw 'Panel restart failed.' }
Start-Process 'http://127.0.0.1:18767/#/integrations'
Write-Host 'Sign in to the panel, then click Connect account on the YouTube card.'

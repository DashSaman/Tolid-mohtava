@echo off
rem Tolid-Mohtava — Docker start (normal launch path). Only this compose project.
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
docker info >nul 2>&1 || (echo Docker engine not running - starting Docker Desktop... & start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe" )
:wait
docker info >nul 2>&1 || (timeout /t 3 >nul & goto wait)
docker compose up -d
echo Waiting for health...
:health
curl -s -o nul -m 3 http://127.0.0.1:18767/api/health && goto ok
timeout /t 3 >nul
goto health
:ok
echo.
echo TOLID LOCAL: http://127.0.0.1:18767
docker compose ps --format "table {{.Name}}\t{{.Status}}"
for /f "tokens=*" %%i in ('docker compose exec -T tolid-tailscale tailscale ip -4 2^>nul') do echo TOLID REMOTE (tailnet): http://%%i:8766
start "" http://127.0.0.1:18767
pause

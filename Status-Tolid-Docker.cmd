@echo off
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
curl -s -o nul -m 3 -w "LOCAL http://127.0.0.1:18767 -> HTTP %%{http_code}\n" http://127.0.0.1:18767/api/health
for /f "tokens=*" %%i in ('docker compose exec -T tolid-tailscale tailscale ip -4 2^>nul') do echo REMOTE (tailnet): http://%%i:8766
docker compose exec -T tolid-tailscale tailscale status 2>nul | findstr /i "tolid" 
pause

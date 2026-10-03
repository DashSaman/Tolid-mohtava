@echo off
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
docker compose stop
docker compose ps --format "table {{.Name}}\t{{.Status}}"
pause

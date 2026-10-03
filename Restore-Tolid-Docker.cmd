@echo off
rem Tolid-Mohtava — RESTORE a DB backup INTO the Docker named volume.
rem Usage: Restore-Tolid-Docker.cmd backups\content-XXXX.sqlite
rem Stops only tolid-web, seeds the volume, verifies integrity, starts again.
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
if "%~1"=="" (echo Usage: Restore-Tolid-Docker.cmd ^<backup.sqlite^> & pause & exit /b 1)
if not exist "%~1" (echo Backup file not found: %~1 & pause & exit /b 1)
echo Stopping tolid-web...
docker compose stop tolid-web
echo Seeding volume from: %~1
docker compose up -d --no-deps tolid-web
timeout /t 5 >nul
docker cp "%~1" tolid-mohtava-tolid-web-1:/app/outputs/panel/data/content.sqlite || goto :err
docker compose restart tolid-web
timeout /t 12 >nul
docker compose exec -T tolid-web python -c "import sqlite3;d=sqlite3.connect('file:/app/outputs/panel/data/content.sqlite?mode=ro',uri=True);r=d.execute('PRAGMA integrity_check').fetchone()[0];p=d.execute('select count(*) from content').fetchone()[0];print('integrity:',r,'projects:',p);exit(0 if r=='ok' else 1)" || goto :err
echo RESTORE OK.
pause & exit /b 0
:err
echo RESTORE FAILED - volume may hold partial data; re-run with a verified backup.
pause & exit /b 1

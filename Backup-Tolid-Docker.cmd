@echo off
rem Tolid-Mohtava — DB backup FROM the Docker named volume (safe while stack runs).
rem Uses the SQLite backup API inside the Linux container; NEVER open the live DB from Windows.
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
if not exist backups mkdir backups
for /f "tokens=1-3 delims=/:. " %%a in ("%date% %time%") do set STAMP=%%a%%b%%c-%%d%%e
docker compose exec -T tolid-web python -c "import sqlite3;s=sqlite3.connect('file:/app/outputs/panel/data/content.sqlite?mode=ro',uri=True,timeout=30);d=sqlite3.connect('/tmp/backup.sqlite');s.backup(d);d.close();print('backup-ok')" || goto :err
docker compose cp tolid-web:/tmp/backup.sqlite "backups\content-%STAMP%.sqlite" || goto :err
docker compose exec -T tolid-web python -c "import os;os.remove('/tmp/backup.sqlite')"
for %%f in ("backups\content-%STAMP%.sqlite") do echo BACKUP: backups\content-%STAMP%.sqlite (%%~zf bytes)
echo Verify: docker compose exec tolid-web python -c "import sqlite3;print(sqlite3.connect('/tmp/x').execute('x'))" -- or restore-check via Restore-Tolid-Docker.cmd
pause & exit /b 0
:err
echo BACKUP FAILED - see messages above.
pause & exit /b 1

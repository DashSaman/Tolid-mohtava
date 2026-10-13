@echo off
rem Tolid-Mohtava — DB backup FROM the Docker named volume (safe while stack runs).
rem Uses the SQLite backup API inside the Linux container; NEVER open the live DB from Windows.
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\Backup-TolidDocker.ps1" || goto :err
pause & exit /b 0
:err
echo BACKUP FAILED - see messages above.
pause & exit /b 1

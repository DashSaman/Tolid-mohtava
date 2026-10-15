@echo off
if "%~1"=="" (echo Usage: Restore-Tolid-Docker.cmd ^<backup.sqlite^> & pause & exit /b 1)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\Restore-TolidDocker.ps1" -Backup "%~1"
if errorlevel 1 (echo Restore failed. & pause & exit /b 1)
pause

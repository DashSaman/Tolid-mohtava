@echo off
rem Tolid-Mohtava — Docker start (normal launch path). Only this compose project.
cd /d "%~dp0"
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\Start-TolidDocker.ps1"
if errorlevel 1 echo START FAILED - see the message above.
pause

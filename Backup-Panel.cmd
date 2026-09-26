@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 outputs\panel\backup.py
) else (
  python outputs\panel\backup.py
)
if errorlevel 1 pause

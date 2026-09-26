@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 scripts\start_panel.py
) else (
  python scripts\start_panel.py
)
if errorlevel 1 pause

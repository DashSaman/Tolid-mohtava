@echo off
rem Tehran Network / MyTel local content panel launcher.
rem Starts the local server (127.0.0.1) and opens the panel in the default browser.
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"

if not defined PYEXE (
  echo Python 3.10+ found nowhere on this machine.
  echo Install Python from https://www.python.org/downloads/ and run this file again.
  pause
  exit /b 1
)

%PYEXE% scripts\start_panel.py
if errorlevel 1 pause

@echo off
rem Tolid-Mohtava — secure remote access via Tailscale (private tailnet only).
rem 1) starts/verifies the local panel  2) detects the ACTUAL port (8766/8767/8768)
rem 3) requires ADMIN auth to be enabled  4) configures `tailscale serve` to it
rem 5) prints/opens the private https URL. No public exposure, no port forwarding.
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"

if not defined PYEXE (
  echo Python not found. Install Python then run setup\Setup-TolidMohtava.ps1
  pause
  exit /b 1
)

%PYEXE% scripts\remote_access.py
echo.
pause

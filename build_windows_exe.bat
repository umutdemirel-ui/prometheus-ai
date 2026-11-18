@echo off
setlocal
cd /d "%~dp0"
title PROMETHEUS AI // Masaustu EXE Derleyici
echo ======================================================
echo   PROMETHEUS AI - Windows Masaustu Uygulamasi (.exe)
echo ======================================================

set "PY_CMD="
where python >nul 2>nul && set "PY_CMD=python"
if "%PY_CMD%"=="" (
    where py >nul 2>nul && set "PY_CMD=py -3"
)
if "%PY_CMD%"=="" (
    echo [HATA] Python 3 bulunamadi!
    pause
    exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    %PY_CMD% -m venv "%~dp0.venv"
)

"%~dp0.venv\Scripts\python.exe" -m pip install --quiet -r "%~dp0requirements.txt" -r "%~dp0requirements-desktop.txt"
"%~dp0.venv\Scripts\python.exe" "%~dp0build_desktop.py"

echo.
echo Hazir! Masaustu uygulamaniz: %~dp0dist\PrometheusAI.exe
pause

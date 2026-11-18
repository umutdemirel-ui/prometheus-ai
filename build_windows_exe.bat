@echo off
title PROMETHEUS AI // Masaustu EXE Derleyici
echo ======================================================
echo   PROMETHEUS AI - Windows Masaustu Uygulamasi (.exe)
echo ======================================================

if not exist ".venv" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt -r requirements-desktop.txt
python build_desktop.py

echo.
echo Hazir! Masaustu uygulamaniz: dist\PrometheusAI.exe
pause

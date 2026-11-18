@echo off
setlocal
cd /d "%~dp0"
title PROMETHEUS AI // Baslatiliyor...
echo ======================================================
echo   PROMETHEUS AI - Tam Yetkili & Ucretsiz Asistan
echo ======================================================

set "PY_CMD="
where python >nul 2>nul && set "PY_CMD=python"
if "%PY_CMD%"=="" (
    where py >nul 2>nul && set "PY_CMD=py -3"
)
if "%PY_CMD%"=="" (
    echo [HATA] Python 3 bulunamadi! Lutfen python.org uzerinden Python 3.11+ kurun.
    pause
    exit /b 1
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [1/3] Sanal ortam olusturuluyor...
    %PY_CMD% -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [HATA] Sanal ortam olusturulamadi!
        pause
        exit /b 1
    )
)

echo [2/3] Gerekli kutuphaneler kontrol ediliyor...
"%~dp0.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install --quiet -r "%~dp0requirements.txt"

echo [3/3] Prometheus Masaustu Uygulamasi baslatiliyor...
"%~dp0.venv\Scripts\python.exe" "%~dp0run.py" --desktop
if errorlevel 1 (
    echo [HATA] Prometheus baslatilirken bir hata olustu.
    pause
)

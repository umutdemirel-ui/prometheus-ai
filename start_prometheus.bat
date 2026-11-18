@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title PROMETHEUS AI // Baslatiliyor...
echo ======================================================
echo   PROMETHEUS AI - Tam Yetkili & Ucretsiz Asistan
echo ======================================================

call :find_python
if "!PY_EXE!"=="" (
    echo.
    echo [BILGI] Sistemde Python 3 bulunamadi. Otomatik kurulum deneniyor ^(winget^)...
    where winget >nul 2>nul
    if !errorlevel! equ 0 (
        winget install -e --id Python.Python.3.11 --scope CurrentUser --accept-package-agreements --accept-source-agreements
        call :find_python
    )
)

if "!PY_EXE!"=="" (
    echo.
    echo [HATA] Python 3.11+ bulunamadi!
    echo Lutfen https://www.python.org/downloads/ adresinden Python kurup
    echo kurulumda "Add python.exe to PATH" kutusunu isaretleyin.
    pause
    exit /b 1
)

echo [OK] Python bulundu: "!PY_EXE!"

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [1/3] Sanal ortam olusturuluyor...
    "!PY_EXE!" -m venv "%~dp0.venv"
    if not exist "%~dp0.venv\Scripts\python.exe" (
        echo [HATA] Sanal ortam olusturulamadi!
        pause
        exit /b 1
    )
)

echo [2/3] Gerekli kutuphaneler kontrol ediliyor...
"%~dp0.venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%~dp0.venv\Scripts\python.exe" -m pip install --quiet -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [HATA] Kutuphaneler yuklenemedi! Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

echo [3/3] Prometheus Masaustu Uygulamasi baslatiliyor...
"%~dp0.venv\Scripts\python.exe" "%~dp0run.py" --desktop
if errorlevel 1 (
    echo [HATA] Prometheus baslatilirken bir hata olustu.
    pause
)
exit /b 0

:find_python
set "PY_EXE="
where py >nul 2>nul
if !errorlevel! equ 0 (
    py -3 -c "import sys" >nul 2>nul
    if !errorlevel! equ 0 (
        for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%I"
    )
)
if "!PY_EXE!"=="" (
    python -c "import sys; assert 'WindowsApps' not in sys.executable" >nul 2>nul
    if !errorlevel! equ 0 (
        for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "PY_EXE=%%I"
    )
)
if "!PY_EXE!"=="" (
    for %%D in ("%LocalAppData%\Programs\Python" "%ProgramFiles%" "C:\") do (
        if exist "%%~D" (
            for /d %%P in ("%%~D\Python3*") do (
                if exist "%%~P\python.exe" (
                    "%%~P\python.exe" -c "import sys" >nul 2>nul
                    if !errorlevel! equ 0 set "PY_EXE=%%~P\python.exe"
                )
            )
        )
    )
)
goto :eof

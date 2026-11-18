@echo off
title PROMETHEUS AI // Başlatılıyor...
echo ======================================================
echo   PROMETHEUS AI - Tam Yetkili & Ucretsiz Asistan
echo ======================================================

if not exist ".venv" (
    echo [1/3] Sanal ortam olusturuluyor...
    python -m venv .venv
)

echo [2/3] Gerekli kutuphaneler kontrol ediliyor...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo [3/3] Prometheus Masaustu Uygulamasi baslatiliyor...
python run.py --desktop
pause

#!/usr/bin/env bash
set -e

echo "======================================================"
echo "  PROMETHEUS AI - Tam Yetkili & Ücretsiz Asistan"
echo "======================================================"

if [ ! -d ".venv" ]; then
  echo "[1/3] Sanal ortam oluşturuluyor..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "[2/3] Gerekli kütüphaneler kuruluyor..."
pip install -q -r requirements.txt

echo "[3/3] Prometheus HUD başlatılıyor..."
python run.py "$@"

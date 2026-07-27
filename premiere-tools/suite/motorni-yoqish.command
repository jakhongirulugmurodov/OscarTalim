#!/bin/bash
# Podcast Suite motori — Mac uchun ishga tushirgich (ikki marta bosing)
cd "$(dirname "$0")/engine"

if ! command -v python3 >/dev/null; then
  echo "[XATO] Python topilmadi — https://www.python.org/downloads/ dan o'rnating"
  read -r; exit 1
fi

python3 -c "import numpy" 2>/dev/null || {
  echo "numpy o'rnatilmoqda — bir martalik..."
  python3 -m pip install numpy
}

command -v ffmpeg >/dev/null || {
  echo "[OGOHLANTIRISH] ffmpeg topilmadi — terminalda: brew install ffmpeg"
}

python3 server.py

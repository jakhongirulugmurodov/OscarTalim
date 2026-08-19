#!/bin/bash
# Podcast Suite motori — Mac uchun ishga tushirgich (ikki marta bosing).
# Kerak bo'lsa numpy va ffmpeg'ni o'zi o'rnatadi.
cd "$(dirname "$0")" || exit 1
BASE="$PWD"
export PATH="$BASE/bin:$PATH"

echo "===== Podcast Suite — motor ====="

# --- Python ---
if ! command -v python3 >/dev/null; then
  echo "[XATO] Python topilmadi."
  echo "  https://www.python.org/downloads/ dan o'rnating va shu faylni qayta bosing."
  read -r -p "Yopish uchun Enter..."; exit 1
fi

# --- numpy ---
python3 -c "import numpy" 2>/dev/null || {
  echo "numpy o'rnatilmoqda (bir martalik)..."
  python3 -m pip install --quiet numpy 2>/dev/null ||
    python3 -m pip install --user --quiet numpy || {
      echo "[XATO] numpy o'rnatilmadi."
      read -r -p "Yopish uchun Enter..."; exit 1; }
}

# --- ffmpeg + ffprobe ---
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  echo "ffmpeg topilmadi — yuklab olinmoqda (bir martalik, ~40 MB)..."
  mkdir -p "$BASE/bin"
  if [ "$(uname -m)" = "arm64" ]; then
    FF_URL="https://www.osxexperts.net/ffmpeg711arm.zip"
    FP_URL="https://www.osxexperts.net/ffprobe711arm.zip"
  else
    FF_URL="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    FP_URL="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
  fi
  (
    cd "$BASE/bin" || exit 1
    curl -L --progress-bar -o ff.zip "$FF_URL" && unzip -oq ff.zip && rm -f ff.zip
    curl -L --progress-bar -o fp.zip "$FP_URL" && unzip -oq fp.zip && rm -f fp.zip
    rm -rf __MACOSX
    xattr -dr com.apple.quarantine ffmpeg ffprobe 2>/dev/null
    chmod +x ffmpeg ffprobe 2>/dev/null
  )
  if ! "$BASE/bin/ffmpeg" -version >/dev/null 2>&1; then
    echo "[XATO] ffmpeg ishga tushmadi."
    echo "  Homebrew bo'lsa shuni sinang:  brew install ffmpeg"
    read -r -p "Yopish uchun Enter..."; exit 1
  fi
  echo "ffmpeg tayyor ✓"
fi

echo
python3 engine/server.py
read -r -p "Motor to'xtadi. Yopish uchun Enter..."

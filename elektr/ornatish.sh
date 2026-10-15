#!/bin/bash
# Elektr balansi serverini Mac'ga o'rnatadi:
#   1) .venv + Playwright
#   2) bir marta qo'lda kabinetga kirish (sessiya saqlanadi)
#   3) launchd: Mac yoqilib, siz kirganingizda server o'zi ishga tushadi
# Qayta ishga tushirish xavfsiz. O'chirish: ./ornatish.sh --ochir
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
NOM="uz.oscartalim.elektr"
PLIST="$HOME/Library/LaunchAgents/$NOM.plist"
LOG="$HOME/.elektr/server.log"

if [ "${1:-}" = "--ochir" ]; then
  launchctl bootout "gui/$(id -u)/$NOM" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Server o'chirildi. Sessiya va natijalar: ~/.elektr (qo'lda o'chiring)."
  exit 0
fi

echo "1/3 Python muhiti..."
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q --upgrade pip playwright
if [ ! -d "/Applications/Google Chrome.app" ]; then
  echo "    Google Chrome yo'q — Playwright Chromium yuklanadi"
  "$DIR/.venv/bin/python" -m playwright install chromium
fi

if [ "${1:-}" != "--kirishsiz" ]; then
  echo "2/3 Kabinetga kirish (brauzer oynasi ochiladi)..."
  "$DIR/.venv/bin/python" "$DIR/tekshir.py" kirish
fi

echo "3/3 Avtomatik ishga tushish (launchd)..."
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.elektr"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$NOM</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DIR/.venv/bin/python</string>
    <string>$DIR/server.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>ELEKTR_DAVR</key><string>${ELEKTR_DAVR:-6}</string>
    <key>ELEKTR_HOST</key><string>${ELEKTR_HOST:-127.0.0.1}</string>
    <key>ELEKTR_KALIT</key><string>${ELEKTR_KALIT:-}</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF
chmod 600 "$PLIST"
launchctl bootout "gui/$(id -u)/$NOM" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

sleep 2
echo "Tayyor: http://127.0.0.1:8765"
open "http://127.0.0.1:8765${ELEKTR_KALIT:+/?k=$ELEKTR_KALIT}"

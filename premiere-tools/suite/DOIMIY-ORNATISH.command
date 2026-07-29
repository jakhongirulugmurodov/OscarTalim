#!/bin/bash
# Podcast Suite — doimiy o'rnatish (Mac).
#
# Ikki narsani hal qiladi:
#   1. Panel Premiere'ga doimiy o'rnatiladi — endi har safar UXP Developer
#      Tools'dan Load qilish shart emas, Window > UXP Plugins da doim turadi.
#   2. Motor kompyuter yonganda o'zi ishga tushadi — Terminal ochish shart emas.
#
# Ikki marta bosing. Qayta ishga tushirsangiz, eskisini yangilaydi.

set -u
cd "$(dirname "$0")" || exit 1
BASE="$PWD"
PANEL="$BASE/panel"
MANIFEST="$PANEL/manifest.json"

echo "===== Podcast Suite — doimiy o'rnatish ====="

if [ ! -f "$MANIFEST" ]; then
  echo "[XATO] panel/manifest.json topilmadi. Bu fayl PodcastSuite papkasida turishi kerak."
  read -r -p "Yopish uchun Enter..."; exit 1
fi

# --- manifestdan id va versiyani olamiz (papka nomi shu ikkisidan yasaladi) ---
read -r PLUGIN_ID PLUGIN_VER <<EOF
$(python3 -c "
import json
m = json.load(open('$MANIFEST'))
print(m['id'], m['version'])
")
EOF

if [ -z "${PLUGIN_ID:-}" ]; then
  echo "[XATO] manifest.json o'qib bo'lmadi."
  read -r -p "Yopish uchun Enter..."; exit 1
fi

# --- 1. Panelni Premiere ko'radigan papkaga ko'chirish ---
EXTERNAL="$HOME/Library/Application Support/Adobe/UXP/Plugins/External"
TARGET="$EXTERNAL/${PLUGIN_ID}_${PLUGIN_VER}"

echo "▶ Panel o'rnatilmoqda..."
mkdir -p "$EXTERNAL"
# Eski versiyalarni tozalaymiz — ro'yxatda ikkilanish bo'lmasin
find "$EXTERNAL" -maxdepth 1 -type d -name "${PLUGIN_ID}_*" -exec rm -rf {} + 2>/dev/null
mkdir -p "$TARGET"
cp -R "$PANEL/." "$TARGET/"
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null
echo "  → $TARGET"

# --- 2. Motorni tizimga ro'yxatdan o'tkazish (login'da o'zi yonadi) ---
echo "▶ Motor avtomatik ishga tushirishga qo'yilmoqda..."
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/uz.oscartalim.podcastsuite.motor.plist"
PY=$(command -v python3)
mkdir -p "$AGENTS"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>uz.oscartalim.podcastsuite.motor</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$BASE/engine/server.py</string>
  </array>
  <key>WorkingDirectory</key><string>$BASE</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$BASE/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$BASE/motor.log</string>
  <key>StandardErrorPath</key><string>$BASE/motor.log</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" 2>/dev/null || {
  echo "  (launchctl load ishlamadi — motorni qo'lda yoqasiz)"
}

# --- 3. Tekshiruv ---
echo "▶ Motor tekshirilmoqda..."
for i in $(seq 1 15); do
  sleep 1
  curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1 && break
done

HEALTH=$(curl -s --max-time 3 http://127.0.0.1:8765/health 2>/dev/null)
echo
if [ -n "$HEALTH" ]; then
  echo "✅ Motor ishlayapti: $HEALTH"
  case "$HEALTH" in
    *'"ffmpeg": false'*)
      echo "⚠️  ffmpeg topilmadi — «motorni-yoqish.command» ni bir marta ishga tushiring,"
      echo "    u ffmpeg'ni yuklab oladi, keyin shu faylni qayta bosing." ;;
  esac
else
  echo "⚠️  Motor javob bermadi. Sabab: $BASE/motor.log"
  tail -5 "$BASE/motor.log" 2>/dev/null
fi

echo
echo "✅ Panel o'rnatildi. Premiere Pro'ni YOPIB QAYTA OCHING, so'ng:"
echo "   Window > UXP Plugins > Podcast Suite"
echo
echo "Endi UXP Developer Tools ham, Terminal ham kerak emas."
read -r -p "Yopish uchun Enter..."

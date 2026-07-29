#!/bin/bash
# Podcast Suite — motorni doimiy qilish + panelni o'rnatishga urinish (Mac).
#
# 1. Motor kompyuter yonganda o'zi ishga tushadi (Terminal kerak emas).
# 2. Agar yonida to'g'ri qadoqlangan .ccx bo'lsa, panelni Adobe'ning o'z
#    o'rnatuvchisi (UPIA) orqali doimiy o'rnatadi.
#
# .ccx ni UXP Developer Tools yasaydi: plugin qatorida ••• > Package.
# Qo'lda zip qilingan .ccx ishlamaydi — Adobe imzoni tekshiradi.

set -u
cd "$(dirname "$0")" || exit 1
BASE="$PWD"

echo "===== Podcast Suite — doimiy o'rnatish ====="

# ---------- 1. Motor: login'da o'zi yonsin ----------
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

LABEL="uz.oscartalim.podcastsuite.motor"
GUI="gui/$(id -u)"
launchctl bootout "$GUI/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null
launchctl bootstrap "$GUI" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null
launchctl kickstart -k "$GUI/$LABEL" 2>/dev/null

for i in $(seq 1 15); do
  sleep 1
  curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1 && break
done
HEALTH=$(curl -s --max-time 3 http://127.0.0.1:8765/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
  echo "  ✅ Motor ishlayapti: $HEALTH"
  case "$HEALTH" in
    *'"ffmpeg": false'*)
      echo "  ⚠️  ffmpeg yo'q — «motorni-yoqish.command» ni bir marta ishlating." ;;
  esac
else
  echo "  ⚠️  Motor javob bermadi. Sabab: $BASE/motor.log"
  tail -5 "$BASE/motor.log" 2>/dev/null
fi

# ---------- 2. Panel: Adobe o'rnatuvchisi orqali ----------
echo
echo "▶ Panel o'rnatilmoqda..."

UPIA="/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent"
# UDT «Package» yasagan .ccx ni qidiramiz (qo'lda zip qilingani emas)
CCX=$(ls -t "$BASE"/*.ccx ~/Desktop/*.ccx ~/Downloads/*.ccx 2>/dev/null \
      | grep -iv "PodcastSuite.ccx$" | head -1)

if [ -z "$CCX" ]; then
  echo "  ℹ️  Qadoqlangan .ccx topilmadi — panel hozircha UDT orqali yuklanadi."
  NEED_PACKAGE=1
elif [ ! -x "$UPIA" ]; then
  echo "  ℹ️  Adobe o'rnatuvchisi topilmadi — .ccx ni ikki marta bosib o'rnating:"
  echo "     $CCX"
  NEED_PACKAGE=0
else
  echo "  .ccx: $CCX"
  if "$UPIA" --install "$CCX"; then
    echo "  ✅ Panel o'rnatildi!"
    NEED_PACKAGE=0
  else
    echo "  ⚠️  O'rnatuvchi rad etdi — pastdagi yo'riqnomaga qarang."
    NEED_PACKAGE=1
  fi
fi

echo
if [ "${NEED_PACKAGE:-1}" = "1" ]; then
  cat <<'GUIDE'
── Panelni DOIMIY qilish uchun (bir martalik, 2 daqiqa) ──
1. UXP Developer Tools'ni oching
2. Podcast Suite qatorida:  •••  >  Package
3. Saqlash joyi so'raganda — Desktop'ni tanlang
4. Yasalgan .ccx faylni IKKI MARTA BOSING (Creative Cloud o'rnatadi)
5. Premiere'ni yopib qayta oching

Shundan keyin panel doim shu yerda turadi:
   Window > UXP Plugins > Podcast Suite

Agar 4-qadamda xato chiqsa — shu faylni qayta ishga tushiring, u .ccx ni
Adobe o'rnatuvchisi orqali o'zi o'rnatib ko'radi.
GUIDE
else
  echo "✅ Tayyor. Premiere'ni yopib qayta oching:"
  echo "   Window > UXP Plugins > Podcast Suite"
fi

echo
read -r -p "Yopish uchun Enter..."

#!/bin/bash
# Podcast Suite — panelni Premiere'ga DOIMIY o'rnatish (Mac).
#
# Shundan keyin Premiere'ni qayta ochganda ham panel joyida turadi —
# UXP Developer Tools'da har safar Reload bosish shart bo'lmaydi.
#
# Oldindan: UDT'da Podcast Suite qatorida  •••  >  Package  qiling va
# .ccx faylni Desktop'ga saqlang. So'ng shu faylni ishga tushiring.

set -u
cd "$(dirname "$0")" || exit 1
BASE="$PWD"
PLUGIN_ID="uz.oscartalim.podcastsuite"

echo "===== Panelni doimiy o'rnatish ====="

# --- .ccx ni qidiramiz (eng yangisi) ---
CCX=$(ls -t ~/Desktop/*.ccx ~/Downloads/*.ccx "$BASE"/*.ccx 2>/dev/null | head -1)

if [ -z "$CCX" ]; then
  cat <<'GUIDE'
[.ccx topilmadi]

Avval uni yasash kerak (bir martalik, 1 daqiqa):
  1. UXP Developer Tools'ni oching
  2. Podcast Suite qatorida:  •••  >  Package
  3. Saqlash joyi — Desktop
  4. So'ng shu faylni qayta ishga tushiring

GUIDE
  read -r -p "Yopish uchun Enter..."; exit 1
fi

echo "▶ Topildi: $CCX"

UPIA="/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent"

if [ -x "$UPIA" ]; then
  echo "▶ Adobe o'rnatuvchisi orqali o'rnatilmoqda..."
  # Eski nusxa bo'lsa olib tashlaymiz — ikkilanish bo'lmasin
  "$UPIA" --remove "$PLUGIN_ID" >/dev/null 2>&1
  if "$UPIA" --install "$CCX"; then
    OK=1
  else
    OK=0
  fi
else
  echo "▶ Adobe o'rnatuvchisi topilmadi — .ccx ochilmoqda..."
  open "$CCX" && OK=1 || OK=0
fi

# --- Natijani tekshiramiz ---
EXTERNAL="$HOME/Library/Application Support/Adobe/UXP/Plugins/External"
sleep 2
FOUND=$(ls -d "$EXTERNAL/${PLUGIN_ID}"_* 2>/dev/null | head -1)

echo
if [ -n "$FOUND" ]; then
  echo "✅ O'rnatildi: $FOUND"
  echo
  echo "Endi:"
  echo "  1. UXP Developer Tools'da qator bo'lsa — Unload qiling (ikkilanmasin)"
  echo "  2. Premiere Pro'ni yopib qayta oching"
  echo "  3. Window > UXP Plugins > Podcast Suite"
  echo
  echo "Bundan keyin panel doim shu yerda turadi. «Yangilash» tugmasi esa"
  echo "o'rnatilgan nusxani ham yangilaydi — qayta o'rnatish shart emas."
elif [ "$OK" = "1" ]; then
  echo "ℹ️  O'rnatish boshlandi — Creative Cloud oynasida «Install» ni tasdiqlang,"
  echo "    so'ng shu faylni qayta ishga tushirib natijani tekshiring."
else
  echo "⚠️  O'rnatib bo'lmadi."
  echo "    Sabab odatda: .ccx UDT'ning «Package» funksiyasi bilan yasalmagan."
  echo "    UDT > ••• > Package qilib, qayta urinib ko'ring."
  echo
  echo "    Ishlamasa ham qo'rqinchli emas: UDT > Reload orqali ishlatavering."
fi

echo
read -r -p "Yopish uchun Enter..."

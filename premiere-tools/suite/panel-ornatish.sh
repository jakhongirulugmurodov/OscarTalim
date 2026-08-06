#!/bin/bash
# Panelni Premiere'ga doimiy o'rnatish — umumiy qism.
#
# Uchta skript (ORNATISH, YANGILASH, PANELNI-DOIMIY-QILISH) shu bitta
# faylni chaqiradi. Sabab oddiy: o'rnatish mantig'i bir joyda tursin,
# aks holda birini tuzatib, ikkinchisi eski holda qolib ketadi.
#
# Nima uchun .ccx orqali:
# Adobe'ning UXP papkasidagi fayllarni qo'lda almashtirib ko'rdik va
# plugin Premiere ro'yxatidan butunlay yo'qoldi — o'sha papkani Adobe
# o'zi boshqaradi. Shuning uchun paketni Adobe'ning o'z o'rnatuvchisiga
# (UPIA) beramiz va papkaga tegmaymiz.

panel_ornat() {
  local SUITE="$1"
  local PLUGIN_ID="uz.oscartalim.podcastsuite"
  local CCX="$SUITE/PodcastSuite.ccx"
  local UPIA="/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent"
  local EXTERNAL="$HOME/Library/Application Support/Adobe/UXP/Plugins/External"

  echo "▶ Panel paketi yasalmoqda..."
  if ! python3 "$SUITE/ccx-yasash.py"; then
    echo "  [XATO] paket yasalmadi"
    return 1
  fi

  # Premiere ochiq bo'lsa, o'rnatilgan panel eski nusxada qolib ketadi.
  # Buni oldindan aytamiz — keyin «nega o'zgarmadi?» degan savol chiqmasin.
  if pgrep -x "Adobe Premiere Pro" >/dev/null 2>&1; then
    echo "  ⚠️  Premiere ochiq. O'rnatgandan keyin uni yopib qayta oching."
  fi

  if [ -x "$UPIA" ]; then
    echo "▶ Adobe o'rnatuvchisi orqali o'rnatilmoqda..."
    "$UPIA" --remove "$PLUGIN_ID" >/dev/null 2>&1
    "$UPIA" --install "$CCX" 2>&1 | sed 's/^/    /'
  else
    echo "▶ Adobe o'rnatuvchisi topilmadi — paket ochilmoqda..."
    open "$CCX"
    echo "    Creative Cloud oynasida «Install» ni tasdiqlang."
    sleep 8
  fi

  # Haqiqatan o'rnatildimi — papkaning o'zidan tekshiramiz.
  # «O'rnatildi» deb yozib qo'yish oson, lekin tekshirilmagan xabar
  # foydalanuvchini adashtiradi.
  sleep 2
  local FOUND
  FOUND=$(ls -d "$EXTERNAL/${PLUGIN_ID}"_* 2>/dev/null | head -1)
  if [ -n "$FOUND" ]; then
    echo "  ✅ O'rnatildi: $(basename "$FOUND")"
    return 0
  fi

  echo "  ⚠️  O'rnatilganini tasdiqlab bo'lmadi."
  echo
  echo "  Zaxira yo'l (UXP Developer Tools orqali):"
  echo "    1. UXP Developer Tools > Add Plugin"
  echo "    2. Cmd+Shift+G bosib shu yo'lni qo'ying:"
  echo "         $SUITE/panel/manifest.json"
  echo "    3. «Load & Watch» ni bosing"
  return 1
}

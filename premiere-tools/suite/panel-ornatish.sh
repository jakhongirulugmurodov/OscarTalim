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

  # Kutilayotgan versiya — tekshiruv AYNAN shuni qidiradi.
  # Ilgari har qanday versiya mos kelaverardi va eski papka turgan
  # bo'lsa, o'rnatish muvaffaqiyatsiz bo'lsa ham «o'rnatildi» deb
  # yozilardi. Bu eng yomon xato turi: dastur yolg'on xabar beradi.
  local VER
  VER=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['version'])" \
        "$SUITE/panel/manifest.json" 2>/dev/null)
  if [ -z "$VER" ]; then
    echo "  [XATO] manifest'dan versiya o'qilmadi"
    return 1
  fi

  if [ -x "$UPIA" ]; then
    echo "▶ Adobe o'rnatuvchisi orqali o'rnatilmoqda..."
    "$UPIA" --remove "$PLUGIN_ID" >/dev/null 2>&1
    local CHIQISH
    CHIQISH=$("$UPIA" --install "$CCX" 2>&1)
    echo "$CHIQISH" | sed 's/^/    /'
    if echo "$CHIQISH" | grep -qi "failed\|error\|status = -"; then
      echo
      echo "  ❌ Adobe paketni QABUL QILMADI."
      echo "     Sabab: imzolanmagan paket. Adobe faqat imzolangan"
      echo "     .ccx ni o'rnatadi, imzoni esa UXP Developer Tools qo'yadi."
      echo
      echo "  Hozircha ishlatish uchun (2 daqiqa, ishlashi kafolatlangan):"
      echo "    1. UXP Developer Tools > Add Plugin"
      echo "    2. Cmd+Shift+G > shu yo'lni qo'ying:"
      echo "         $SUITE/panel/manifest.json"
      echo "    3. «Load & Watch» ni bosing"
      echo
      echo "  Doimiy qilish uchun o'sha yerda: ••• > Package > Desktop,"
      echo "  so'ng PANELNI-DOIMIY-QILISH.command ni bosing."
      return 1
    fi
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
  local DIR="$EXTERNAL/${PLUGIN_ID}_${VER}"
  if [ -f "$DIR/main.js" ]; then
    # Papka bor — endi ICHIDAGI kod haqiqatan yangimi, shuni tekshiramiz.
    # Papka nomi to'g'ri bo'lib, ichi eski qolishi mumkin.
    local KUTILGAN ORNATILGAN
    KUTILGAN=$(grep -o 'PANEL_BUILD = "[^"]*"' "$SUITE/panel/main.js" | head -1)
    ORNATILGAN=$(grep -o 'PANEL_BUILD = "[^"]*"' "$DIR/main.js" | head -1)
    if [ "$KUTILGAN" = "$ORNATILGAN" ]; then
      echo "  ✅ O'rnatildi: ${PLUGIN_ID}_${VER} ($ORNATILGAN)"
      return 0
    fi
    echo "  ⚠️  Papka bor, lekin ichida ESKI kod: $ORNATILGAN"
    echo "      Kutilgan: $KUTILGAN"
    return 1
  fi

  # Eski versiya qolib ketgan bo'lsa — buni ochiq aytamiz, aks holda
  # foydalanuvchi Premiere'da eski panelni ko'rib chalkashadi.
  local ESKI
  ESKI=$(ls -d "$EXTERNAL/${PLUGIN_ID}"_* 2>/dev/null | head -1)
  if [ -n "$ESKI" ]; then
    echo "  ⚠️  Yangi versiya o'rnatilmadi. Eski nusxa turibdi:"
    echo "      $(basename "$ESKI")"
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

#!/bin/bash
# Podcast Suite — panelni Premiere'ga DOIMIY o'rnatish (Mac).
#
# Shundan keyin Premiere'ni qayta ochganda ham panel joyida turadi —
# UXP Developer Tools'da har safar Reload bosish shart bo'lmaydi.
#
# Paket shu skriptning o'zida yasaladi — UDT'da qo'lda «Package» qilish
# endi shart emas.
#
# Odatda buni alohida ishga tushirish kerak emas: ORNATISH.command
# panelni allaqachon o'rnatadi. Bu fayl panel ro'yxatdan tushib qolgan
# yoki qayta o'rnatish kerak bo'lgan holat uchun.

set -u
cd "$(dirname "$0")" || exit 1
BASE="$PWD"
PLUGIN_ID="uz.oscartalim.podcastsuite"

echo "===== Panelni doimiy o'rnatish ====="

# Paketni o'zimiz yasaymiz — UDT'da qo'lda «Package» qilish shart emas.
# shellcheck source=panel-ornatish.sh
. "$BASE/panel-ornatish.sh"

if panel_ornat "$BASE"; then
  echo
  echo "Endi:"
  echo "  1. UXP Developer Tools'da qator bo'lsa — Unload qiling (ikkilanmasin)"
  echo "  2. Premiere Pro'ni yopib qayta oching"
  echo "  3. Window > UXP Plugins > Podcast Suite"
fi
read -r -p "Yopish uchun Enter..."

#!/bin/bash
# Podcast Suite — yangilash (Mac). Ikki marta bosing.
#
# Panel ichidagi «Yangilash» tugmasi ishlamay qolsa yoki motor eski kod
# bilan qolib ketsa, shu faylni ishga tushiring: kodni tortadi, o'rnatilgan
# panel nusxasini yangilaydi va motorni yangi kod bilan qayta ishga tushiradi.

set -u
ROOT="$HOME/PodcastSuite"
SUITE="$ROOT/premiere-tools/suite"
LABEL="uz.oscartalim.podcastsuite.motor"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
GUI="gui/$(id -u)"

echo "===== Podcast Suite — yangilash ====="

if [ ! -d "$ROOT/.git" ]; then
  echo "[XATO] $ROOT topilmadi. Avval ORNATISH.command ni ishga tushiring."
  read -r -p "Yopish uchun Enter..."; exit 1
fi

echo "▶ Kod tortilmoqda..."
git -C "$ROOT" pull --ff-only || {
  echo "  [XATO] git pull bo'lmadi."
  read -r -p "Yopish uchun Enter..."; exit 1; }

# O'rnatilgan panel nusxasi (.ccx orqali) — git unga tegmaydi, qo'lda ko'chiramiz
DEST=$(ls -d "$HOME/Library/Application Support/Adobe/UXP/Plugins/External"/uz.oscartalim.podcastsuite_* 2>/dev/null | head -1)
if [ -n "$DEST" ]; then
  cp -f "$SUITE/panel/"* "$DEST/" 2>/dev/null && echo "▶ Panel yangilandi"
fi

echo "▶ Motor qayta ishga tushmoqda..."
# Portni ushlab turgan har qanday eski jarayonni to'xtatamiz — aks holda
# yangi motor portni band ko'rib o'chadi va eskisi javob beraveradi.
lsof -ti tcp:8765 2>/dev/null | xargs -r kill 2>/dev/null
sleep 1
# kickstart -k — jarayonni majburan qayta yoqadi; unload/load yangi macOS'da
# ba'zan jimgina o'tib ketadi va eski jarayon ishlab turaveradi.
launchctl kickstart -k "$GUI/$LABEL" 2>/dev/null || {
  launchctl bootout "$GUI/$LABEL" 2>/dev/null
  launchctl bootstrap "$GUI" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null
}

for i in $(seq 1 20); do
  sleep 1
  curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1 && break
done

echo
HEALTH=$(curl -s --max-time 3 http://127.0.0.1:8765/health)
if [ -n "$HEALTH" ]; then
  echo "✅ Motor: $HEALTH"
else
  echo "⚠️  Motor javob bermadi. Sabab: $SUITE/motor.log"
  tail -5 "$SUITE/motor.log" 2>/dev/null
fi

cat <<'GUIDE'

Premiere'da yangi panelni ko'rish uchun:
  panelni yoping (☰ > Close panel), so'ng
  Window > UXP Plugins > Podcast Suite

GUIDE
read -r -p "Yopish uchun Enter..."

#!/bin/bash
# Podcast Suite — eng qisqa boshlash yo'li.
#
# Terminalda bitta qator:
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/jakhongirulugmurodov/OscarTalim/refs/heads/claude/cloud-premier-plugin-check-yy2nse/premiere-tools/suite/BOSHLASH.sh)"
#
# Bu skript dasturni yuklab oladi va to'liq o'rnatuvchini ishga tushiradi.
# Hech qanday fayl yuklab olish, ochish, ko'chirish shart emas.
#
# «bash -c "$(curl ...)"» shakli ataylab tanlangan: «curl | bash» da
# skriptning o'zi stdin bo'lib qoladi va o'rnatuvchi savol berganda
# javobni skript matnidan «o'qib» yuboradi. Bu shaklda stdin terminalda
# qoladi.

set -u
REPO="https://github.com/jakhongirulugmurodov/OscarTalim.git"
BRANCH="claude/cloud-premier-plugin-check-yy2nse"
ROOT="$HOME/PodcastSuite"

echo "===== Podcast Suite ====="

if ! command -v git >/dev/null; then
  echo "[XATO] git yo'q. Terminalda «xcode-select --install» ni bajaring,"
  echo "       o'rnatilgach shu buyruqni qayta qo'ying."
  exit 1
fi

if [ -d "$ROOT/.git" ]; then
  echo "▶ Mavjud nusxa yangilanmoqda..."
  git -C "$ROOT" fetch --quiet origin "$BRANCH" \
    && git -C "$ROOT" checkout --quiet "$BRANCH" \
    && git -C "$ROOT" reset --hard --quiet "origin/$BRANCH" || {
      echo "[XATO] yangilab bo'lmadi. $ROOT ni o'chirib, qayta urinib ko'ring."
      exit 1; }
else
  echo "▶ Dastur yuklab olinmoqda..."
  git clone --quiet --branch "$BRANCH" --single-branch "$REPO" "$ROOT" || {
    echo "[XATO] yuklab bo'lmadi — internetni tekshiring."
    exit 1; }
fi

ORNATUVCHI="$ROOT/premiere-tools/suite/ORNATISH.command"
if [ ! -f "$ORNATUVCHI" ]; then
  echo "[XATO] o'rnatuvchi topilmadi: $ORNATUVCHI"
  exit 1
fi

echo "▶ O'rnatuvchi ishga tushmoqda..."
echo
exec bash "$ORNATUVCHI"

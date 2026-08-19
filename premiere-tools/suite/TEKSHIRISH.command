#!/bin/bash
# Podcast Suite — plagin holatini tekshirish (Mac).
#
# Nima uchun kerak: imzolanmagan .ccx ni Adobe rad etadi (-267), lekin
# UXP papkasiga plaginni QO'LDA qo'yish mumkinmi — buni bilish uchun
# o'sha papka aynan qanday tuzilganini ko'rish kerak. Ayniqsa: imzo
# fayli bormi va plagin ro'yxati qayerda saqlanadi.
#
# Skript hech narsani o'zgartirmaydi — faqat o'qiydi va yozib beradi.
# Chiqish matni buferga ham nusxalanadi.

set -u
UXP="$HOME/Library/Application Support/Adobe/UXP"
ID="uz.oscartalim.podcastsuite"
OUT=$(mktemp /tmp/podcastsuite-tekshiruv.XXXXXX.txt)

{
echo "===== PODCAST SUITE — HOLAT ====="
echo "Sana: $(date '+%Y-%m-%d %H:%M')"
echo "macOS: $(sw_vers -productVersion 2>/dev/null)  ·  $(uname -m)"
echo

echo "--- 1. Motor ---"
H=$(curl -s --max-time 3 http://127.0.0.1:8765/health 2>/dev/null)
[ -n "$H" ] && echo "$H" || echo "javob bermadi (o'chiq)"
echo

echo "--- 2. Kod nusxasi ---"
ROOT="$HOME/PodcastSuite"
if [ -d "$ROOT/.git" ]; then
  echo "$(git -C "$ROOT" log -1 --format='%h %cd %s' --date=short 2>/dev/null)"
  echo "shox: $(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  grep -o 'PANEL_BUILD = "[^"]*"' "$ROOT/premiere-tools/suite/panel/main.js" 2>/dev/null
else
  echo "$ROOT topilmadi"
fi
echo

echo "--- 3. UXP papkasi bormi ---"
if [ -d "$UXP" ]; then
  ls -1 "$UXP" | sed 's/^/  /'
else
  echo "  YO'Q: $UXP"
fi
echo

echo "--- 4. O'rnatilgan plaginlar (External) ---"
EXT="$UXP/Plugins/External"
if [ -d "$EXT" ]; then
  for d in "$EXT"/*/; do
    [ -d "$d" ] || continue
    echo "  [$(basename "$d")]"
    # Har bir fayl: nomi va o'lchami. Imzo fayli shu yerda ko'rinadi.
    find "$d" -type f 2>/dev/null | head -40 | while read -r f; do
      printf '     %8s  %s\n' "$(stat -f%z "$f" 2>/dev/null)" "${f#"$d"}"
    done
    N=$(find "$d" -type f 2>/dev/null | wc -l | tr -d ' ')
    [ "$N" -gt 40 ] && echo "     ... jami $N fayl"
    B=$(grep -o 'PANEL_BUILD = "[^"]*"' "$d/main.js" 2>/dev/null | head -1)
    [ -n "$B" ] && echo "     → $B"
  done
  [ -z "$(ls -A "$EXT" 2>/dev/null)" ] && echo "  (bo'sh)"
else
  echo "  YO'Q: $EXT"
fi
echo

echo "--- 5. Plaginlar ro'yxati qayerda saqlanadi ---"
# Ro'yxat fayli topilsa, imzosiz o'rnatish yo'li ochiladi: papkani
# qo'yib, shu faylga yozuv qo'shish kifoya bo'lishi mumkin.
find "$UXP" -maxdepth 3 -name "*.json" 2>/dev/null | head -20 | while read -r j; do
  echo "  $j  ($(stat -f%z "$j" 2>/dev/null) bayt)"
  if grep -qi "podcastsuite\|pluginId\|plugins" "$j" 2>/dev/null; then
    echo "    ↓ ichi:"
    head -c 1200 "$j" | sed 's/^/      /'
    echo
  fi
done
echo

echo "--- 6. Adobe o'rnatuvchisi ---"
UPIA="/Library/Application Support/Adobe/Adobe Desktop Common/RemoteComponents/UPI/UnifiedPluginInstallerAgent/UnifiedPluginInstallerAgent.app/Contents/MacOS/UnifiedPluginInstallerAgent"
[ -x "$UPIA" ] && echo "  bor: $UPIA" || echo "  YO'Q"
echo
echo "--- 7. UXP Developer Tools ---"
# Quvurdan keyin «||» sed'ning holatini ko'radi va hech qachon
# ishlamaydi — shuning uchun natijani avval o'zgaruvchiga olamiz.
UDT=$(ls -d /Applications/*UXP* /Applications/Adobe*UXP* 2>/dev/null)
if [ -n "$UDT" ]; then echo "$UDT" | sed 's/^/  /'; else echo "  o'rnatilmagan"; fi
echo
echo "===== TUGADI ====="
} > "$OUT" 2>&1

cat "$OUT"
pbcopy < "$OUT" 2>/dev/null && echo && echo "(matn buferga nusxalandi — Claude'ga qo'ying)"
echo "Fayl: $OUT"
read -r -p "Yopish uchun Enter..."

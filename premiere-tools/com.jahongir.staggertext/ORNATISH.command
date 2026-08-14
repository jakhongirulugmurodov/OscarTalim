#!/bin/bash
# Stagger Text panelini bir bosishda o'rnatish.
#
# Nima qiladi:
#   1. CSInterface.js placeholder bo'lsa — Adobe'dan haqiqiysini yuklaydi
#   2. Papkani Adobe'ning CEP extensions joyiga nusxalaydi
#   3. PlayerDebugMode yoqadi (imzosiz panelga ruxsat)
# Har qadam tekshiriladi — «o'rnatildi» yolg'on chiqmasin.

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/Library/Application Support/Adobe/CEP/extensions/com.jahongir.staggertext"
CSI="$SRC/client/js/CSInterface.js"
URL="https://raw.githubusercontent.com/Adobe-CEP/CEP-Resources/master/CEP_11.x/CSInterface.js"

echo "Stagger Text — o'rnatish"
echo

# --- 1. CSInterface.js ---
if grep -q "__csinterface_yoq" "$CSI" 2>/dev/null; then
  echo "▶ CSInterface.js Adobe'dan yuklanmoqda..."
  if curl -fsSL "$URL" -o "$CSI.yangi" \
     && grep -q "CSInterface" "$CSI.yangi"; then
    mv "$CSI.yangi" "$CSI"
    echo "  ✅ Yuklandi"
  else
    rm -f "$CSI.yangi"
    echo "  ❌ Yuklab bo'lmadi (internet?). INSTALL.md dagi 1-qadamni"
    echo "     qo'lda bajaring, so'ng shu skriptni qayta ishga tushiring."
    exit 1
  fi
else
  echo "▶ CSInterface.js allaqachon haqiqiy ✅"
fi

# --- 2. Panelni joyiga qo'yish ---
echo "▶ Panel nusxalanmoqda..."
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
if cp -R "$SRC" "$DEST" && [ -f "$DEST/CSXS/manifest.xml" ]; then
  echo "  ✅ $DEST"
else
  echo "  ❌ Nusxalab bo'lmadi"
  exit 1
fi

# --- 3. PlayerDebugMode ---
echo "▶ PlayerDebugMode yoqilmoqda (imzosiz panelga ruxsat)..."
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
# CEP 12 li yangi Premiere'lar uchun ham — ortiqcha bo'lsa zarari yo'q
defaults write com.adobe.CSXS.12 PlayerDebugMode 1 2>/dev/null
killall cfprefsd 2>/dev/null
echo "  ✅"

echo
if pgrep -x "Adobe Premiere Pro" >/dev/null 2>&1; then
  echo "⚠️  Premiere hozir ochiq — uni YOPIB, qayta oching."
fi
echo "Keyin:  Window > Extensions > Stagger Text"

#!/bin/bash
# Podcast Suite — bir martalik o'rnatish (Mac).
#
# Shu bitta faylni ikki marta bosing. U hammasini o'zi qiladi:
#   1. Dasturni GitHub'dan ~/PodcastSuite ga klon qiladi (yoki yangilaydi)
#   2. numpy va ffmpeg'ni o'rnatadi
#   3. Motorni login'da o'zi yonadigan qilib qo'yadi
#   4. Panelni UDT'ga qo'shish uchun kerakli yo'lni ko'rsatadi
#
# Shundan keyin yangilanishlar panel ichidagi «Yangilash» tugmasi orqali
# keladi — boshqa hech qanday fayl yuklab olish shart emas.

set -u
REPO="https://github.com/jakhongirulugmurodov/OscarTalim.git"
BRANCH="claude/cloud-premier-plugin-check-yy2nse"
ROOT="$HOME/PodcastSuite"
SUITE="$ROOT/premiere-tools/suite"

echo "===== Podcast Suite — o'rnatish ====="

# ---------- 0. git bormi ----------
if ! command -v git >/dev/null; then
  echo "[XATO] git topilmadi. Terminalda quyidagini bajaring, so'ng shu faylni qayta bosing:"
  echo "   xcode-select --install"
  read -r -p "Yopish uchun Enter..."; exit 1
fi

# ---------- 1. Klon yoki yangilash ----------
# Skriptning o'zi ham repo ichida yotadi. git pull uni almashtirsa, ishlab
# turgan bash eski nusxani ushlab qolaveradi va foydalanuvchi yangi kodni
# ko'rmaydi. Shuning uchun pull'dan keyin o'zimizni tekshiramiz.
OZI="$0"
SUM_OLDIN=$(shasum "$OZI" 2>/dev/null | cut -d' ' -f1)

if [ -d "$ROOT/.git" ]; then
  echo "▶ Mavjud nusxa yangilanmoqda: $ROOT"
  git -C "$ROOT" fetch --quiet origin "$BRANCH" && \
  git -C "$ROOT" checkout --quiet "$BRANCH" && \
  git -C "$ROOT" pull --ff-only --quiet origin "$BRANCH" || {
    echo "  [XATO] yangilash bo'lmadi. $ROOT ni o'chirib, qayta urinib ko'ring."
    read -r -p "Yopish uchun Enter..."; exit 1; }
else
  echo "▶ Dastur yuklab olinmoqda..."
  git clone --quiet --branch "$BRANCH" --single-branch "$REPO" "$ROOT" || {
    echo "  [XATO] yuklab bo'lmadi — internetni tekshiring."
    read -r -p "Yopish uchun Enter..."; exit 1; }
fi
echo "  → $ROOT"

SUM_KEYIN=$(shasum "$OZI" 2>/dev/null | cut -d' ' -f1)
if [ -n "$SUM_OLDIN" ] && [ "$SUM_OLDIN" != "$SUM_KEYIN" ] && [ -z "${SUITE_QAYTA:-}" ]; then
  echo "▶ O'rnatuvchining o'zi yangilandi — yangi nusxa bilan qayta boshlanmoqda..."
  echo
  SUITE_QAYTA=1 exec bash "$OZI"
fi

# ---------- 2. numpy ----------
if ! command -v python3 >/dev/null; then
  echo "[XATO] Python topilmadi — https://www.python.org/downloads/ dan o'rnating."
  read -r -p "Yopish uchun Enter..."; exit 1
fi
python3 -c "import numpy" 2>/dev/null || {
  echo "▶ numpy o'rnatilmoqda..."
  python3 -m pip install --quiet numpy 2>/dev/null || \
  python3 -m pip install --user --quiet numpy; }

# ---------- 3. ffmpeg ----------
if ! command -v ffmpeg >/dev/null || ! command -v ffprobe >/dev/null; then
  if [ ! -x "$SUITE/bin/ffmpeg" ]; then
    echo "▶ ffmpeg yuklanmoqda (bir martalik, ~40 MB)..."
    mkdir -p "$SUITE/bin"
    if [ "$(uname -m)" = "arm64" ]; then
      FF="https://www.osxexperts.net/ffmpeg711arm.zip"
      FP="https://www.osxexperts.net/ffprobe711arm.zip"
    else
      FF="https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
      FP="https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"
    fi
    (cd "$SUITE/bin" && \
     curl -L --progress-bar -o ff.zip "$FF" && unzip -oq ff.zip && rm -f ff.zip && \
     curl -L --progress-bar -o fp.zip "$FP" && unzip -oq fp.zip && rm -f fp.zip && \
     rm -rf __MACOSX && xattr -dr com.apple.quarantine ffmpeg ffprobe 2>/dev/null; \
     chmod +x ffmpeg ffprobe 2>/dev/null)
  fi
fi

# ---------- 3b. whisper.cpp (Captions moduli uchun) ----------
#
# Uch xil yo'l bor, eng osonidan boshlaymiz:
#   1. Homebrew bo'lsa — bitta buyruq;
#   2. bo'lmasa — manbadan quramiz. Buning uchun kompilyator (Xcode Command
#      Line Tools — git bilan birga keladi) va cmake kerak;
#   3. cmake yo'q bo'lsa — uni cmake.org dan tayyor holda olamiz. Admin
#      paroli ham, Homebrew ham shart emas: papkaga ochib, o'sha yerdan
#      ishlatamiz va ishimiz bitgach o'chirib tashlaymiz.

whisper_qur() {    # $1 — cmake yo'li
  local CM="$1"
  rm -rf "$SUITE/whisper-src"
  git clone -q --depth 1 https://github.com/ggerganov/whisper.cpp \
        "$SUITE/whisper-src" || return 1
  # Avval Metal bilan (Apple chipida bir necha barobar tez). Metal
  # shaderlarini qurish uchun to'liq Xcode kerak bo'lishi mumkin —
  # bo'lmasa, protsessor rejimida qayta urinamiz.
  # BUILD_SHARED_LIBS=OFF — muhim: aks holda whisper-cli o'zi bilan birga
  # libwhisper.dylib va ggml kutubxonalarini qurilish papkasida qoldiradi,
  # biz esa o'sha papkani o'chiramiz va dastur ishga tushmay qoladi.
  local FLAGS=""
  for FLAGS in "" "-DGGML_METAL=OFF"; do
    rm -rf "$SUITE/whisper-src/build"
    if "$CM" -S "$SUITE/whisper-src" -B "$SUITE/whisper-src/build" \
             -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
             -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON \
             $FLAGS >>"$SUITE/qurilish.log" 2>&1 && \
       "$CM" --build "$SUITE/whisper-src/build" -j --target whisper-cli \
             >>"$SUITE/qurilish.log" 2>&1 && \
       [ -x "$SUITE/whisper-src/build/bin/whisper-cli" ]; then
      mkdir -p "$SUITE/bin"
      cp "$SUITE/whisper-src/build/bin/whisper-cli" "$SUITE/bin/"
      # Manbani o'chirishdan oldin tekshiramiz: dastur yakka o'zi ishlaydimi
      rm -rf "$SUITE/whisper-src"
      if "$SUITE/bin/whisper-cli" --help >/dev/null 2>&1; then
        [ -n "$FLAGS" ] && echo "  (Metal ishlamadi — protsessor rejimida qurildi)"
        return 0
      fi
      echo "  [XATO] qurilgan dastur ishga tushmadi — qayta urinilmoqda" \
        >>"$SUITE/qurilish.log"
      rm -f "$SUITE/bin/whisper-cli"
      git clone -q --depth 1 https://github.com/ggerganov/whisper.cpp \
            "$SUITE/whisper-src" || return 1
    fi
  done
  return 1
}

# Bor-yo'g'ini emas, ishlashini tekshiramiz: nuqson bilan qurilgan nusxa
# fayl sifatida turaveradi, lekin ishga tushmaydi.
whisper_ishlaydimi() {
  for W in "$SUITE/bin/whisper-cli" \
           "$(command -v whisper-cli || true)" \
           "$(command -v whisper-cpp || true)"; do
    [ -n "$W" ] && [ -x "$W" ] && "$W" --help >/dev/null 2>&1 && return 0
  done
  return 1
}

if ! whisper_ishlaydimi; then
  rm -f "$SUITE/bin/whisper-cli"        # nosoz nusxa yo'lni to'sib turmasin
  echo "▶ whisper.cpp o'rnatilmoqda (subtitr uchun)..."
  : > "$SUITE/qurilish.log"

  if command -v brew >/dev/null; then
    brew install whisper-cpp 2>&1 | tail -2
  elif ! xcode-select -p >/dev/null 2>&1; then
    echo "  [XATO] Xcode Command Line Tools yo'q."
    echo "  Terminalda «xcode-select --install» ni qo'ying, o'rnatilgach"
    echo "  shu faylni qayta bosing."
  else
    CMAKE_BIN="$(command -v cmake || true)"
    if [ -z "$CMAKE_BIN" ]; then
      echo "  cmake yuklab olinmoqda (~80 MB, faqat qurish uchun)..."
      # Versiya ataylab qotirilgan: cmake 4.x eski CMakeLists fayllarini rad
      # etadi, 3.31 esa whisper.cpp bilan ishlashi tekshirilgan.
      TGZ="cmake-3.31.6-macos-universal.tar.gz"
      BASE="https://cmake.org/files/v3.31/"
      rm -rf "$SUITE/qurilma"; mkdir -p "$SUITE/qurilma"
      if curl -L --progress-bar -o "$SUITE/qurilma/cmake.tar.gz" "$BASE$TGZ" && \
         tar -xzf "$SUITE/qurilma/cmake.tar.gz" -C "$SUITE/qurilma"; then
        CMAKE_BIN=$(find "$SUITE/qurilma" -type f -path "*/Contents/bin/cmake" | head -1)
        xattr -dr com.apple.quarantine "$SUITE/qurilma" 2>/dev/null
      fi
    fi

    if [ -n "$CMAKE_BIN" ] && [ -x "$CMAKE_BIN" ]; then
      echo "  Manbadan qurilmoqda — 3-10 daqiqa, kutib turing..."
      whisper_qur "$CMAKE_BIN" && echo "  whisper.cpp tayyor ✓" \
        || echo "  [XATO] qurib bo'lmadi — tafsilot: $SUITE/qurilish.log"
    else
      echo "  [XATO] cmake ni yuklab bo'lmadi — internetni tekshiring."
    fi
    rm -rf "$SUITE/qurilma"     # 80 MB ni ushlab turishning hojati yo'q
  fi
fi

# Natijani aytamiz — «o'rnatildimi?» degan savol qolmasin
if whisper_ishlaydimi; then
  echo "  whisper.cpp: bor ✓ (Captions ishlaydi)"
else
  echo "  whisper.cpp: YO'Q — Captions tabi yopiq turadi, qolgani ishlaydi"
fi

# ---------- 4. Motor: login'da o'zi yonsin ----------
echo "▶ Motor sozlanmoqda..."
AGENTS="$HOME/Library/LaunchAgents"
PLIST="$AGENTS/uz.oscartalim.podcastsuite.motor.plist"
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
    <string>$(command -v python3)</string>
    <string>$SUITE/engine/server.py</string>
  </array>
  <key>WorkingDirectory</key><string>$SUITE</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>$SUITE/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$SUITE/motor.log</string>
  <key>StandardErrorPath</key><string>$SUITE/motor.log</string>
</dict>
</plist>
PLISTEOF
# Yangi macOS'da bootstrap/kickstart ishonchli ishlaydi; unload/load esa
# ba'zan jimgina o'tib ketadi va eski jarayon ishlab turaveradi.
LABEL="uz.oscartalim.podcastsuite.motor"
GUI="gui/$(id -u)"
launchctl bootout "$GUI/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null
launchctl bootstrap "$GUI" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null
launchctl kickstart -k "$GUI/$LABEL" 2>/dev/null

for i in $(seq 1 20); do
  sleep 1
  curl -s --max-time 2 http://127.0.0.1:8765/health >/dev/null 2>&1 && break
done
HEALTH=$(curl -s --max-time 3 http://127.0.0.1:8765/health 2>/dev/null)

# ---------- 5. Xulosa ----------
echo
if [ -n "$HEALTH" ]; then
  echo "✅ Motor ishlayapti: $HEALTH"
else
  echo "⚠️  Motor javob bermadi. Sabab: $SUITE/motor.log"
  tail -5 "$SUITE/motor.log" 2>/dev/null
fi

MANIFEST="$SUITE/panel/manifest.json"
printf '%s' "$MANIFEST" | pbcopy 2>/dev/null && COPIED=" (nusxalandi ✓)" || COPIED=""

cat <<GUIDE

── Panelni Premiere'ga ulash (bir martalik) ──
1. UXP Developer Tools'ni oching
2. Eski «Podcast Suite» qatori bo'lsa: ••• > Remove
3. «Add Plugin» > ochilgan oynada Cmd+Shift+G bosing va shu yo'lni qo'ying$COPIED:
     $MANIFEST
4. Qator paydo bo'lgach: «Load & Watch» ni bosing
   (Watch — kod yangilanganda panel o'zi qayta yuklanadi)

Shundan keyin yangilanish shunday bo'ladi: panelda «Yangilash» tugmasi
paydo bo'ladi — bosasiz, tamom. Fayl yuklab olish, ko'chirish yo'q.
GUIDE
read -r -p "Yopish uchun Enter..."

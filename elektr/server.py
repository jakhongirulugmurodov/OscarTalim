#!/usr/bin/env python3
"""
Elektr balansi — Mac'da ishlaydigan kichik server.

    python3 server.py

Brauzerda http://127.0.0.1:8765 — oxirgi balans va «Hozir tekshirish» tugmasi.
Server ishga tushganda bir marta, keyin har ELEKTR_DAVR soatda tekshiradi va
natijani macOS bildirishnomasida ko'rsatadi.

Muhit o'zgaruvchilari (ixtiyoriy):
    ELEKTR_PORT     standart 8765
    ELEKTR_HOST     standart 127.0.0.1. Telefondan (Wi-Fi) ochish uchun 0.0.0.0
                    — bunda ELEKTR_KALIT majburiy: http://<mac-ip>:8765/?k=KALIT
    ELEKTR_KALIT    tarmoqdan kirish uchun maxfiy so'z
    ELEKTR_DAVR     necha soatda bir tekshirish (standart 6, 0 — o'chiq)
"""
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BU_PAPKA = Path(__file__).resolve().parent
sys.path.insert(0, str(BU_PAPKA))
import tekshir  # noqa: E402

PORT = int(os.environ.get("ELEKTR_PORT", "8765"))
HOST = os.environ.get("ELEKTR_HOST", "127.0.0.1")
KALIT = os.environ.get("ELEKTR_KALIT", "")
DAVR = float(os.environ.get("ELEKTR_DAVR", "6"))

if HOST not in ("127.0.0.1", "localhost") and not KALIT:
    sys.exit("ELEKTR_HOST tarmoqqa ochilgan — ELEKTR_KALIT ham bering.")

qulf = threading.Lock()


def oxirgi():
    try:
        return json.loads(tekshir.NATIJA.read_text())
    except Exception:
        return {"holat": "hali_yoq"}


def bildirish(natija):
    if sys.platform != "darwin":
        return
    h = natija.get("holat")
    if h == "ok":
        matn = f"{natija['summa']:,.0f} so'm".replace(",", " ")
    elif h == "kirish_kerak":
        matn = "Sessiya tugadi — qayta kiring: python3 tekshir.py kirish"
    else:
        matn = "Balansni olib bo'lmadi — sahifani oching"
    skript = f'display notification {json.dumps(matn)} with title "⚡ Elektr balansi"'
    subprocess.run(["osascript", "-e", skript], check=False)


def tekshiruv(xabar=True):
    """Alohida jarayonda — Playwright server oqimlariga aralashmasin."""
    with qulf:
        try:
            subprocess.run([sys.executable, str(BU_PAPKA / "tekshir.py")],
                           capture_output=True, timeout=180, check=False)
            natija = oxirgi()
        except subprocess.TimeoutExpired:
            natija = {"holat": "xato", "xato": "3 daqiqada javob kelmadi",
                      "vaqt": time.strftime("%Y-%m-%d %H:%M")}
    if xabar:
        bildirish(natija)
    return natija


def jadval():
    while True:
        try:
            tekshiruv()
        except Exception as e:
            print("Tekshiruv xatosi:", e, file=sys.stderr)
        if DAVR <= 0:
            return
        time.sleep(DAVR * 3600)


SAHIFA = (BU_PAPKA / "sahifa.html").read_text()


class Ishlovchi(BaseHTTPRequestHandler):
    def _ruxsat(self):
        if not KALIT:
            return True
        k = parse_qs(urlparse(self.path).query).get("k", [""])[0]
        return k == KALIT or self.headers.get("X-Kalit") == KALIT

    def _yubor(self, kod, tana, tur="application/json; charset=utf-8"):
        tana = tana.encode() if isinstance(tana, str) else tana
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(tana)))
        self.end_headers()
        self.wfile.write(tana)

    def do_GET(self):
        if not self._ruxsat():
            return self._yubor(403, '{"xato":"kalit"}')
        yol = urlparse(self.path).path
        if yol == "/":
            return self._yubor(200, SAHIFA, "text/html; charset=utf-8")
        if yol == "/api/holat":
            return self._yubor(200, json.dumps(oxirgi(), ensure_ascii=False))
        self._yubor(404, '{"xato":"topilmadi"}')

    def do_POST(self):
        if not self._ruxsat():
            return self._yubor(403, '{"xato":"kalit"}')
        if urlparse(self.path).path == "/api/tekshir":
            natija = tekshiruv(xabar=False)
            return self._yubor(200, json.dumps(natija, ensure_ascii=False))
        self._yubor(404, '{"xato":"topilmadi"}')

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    threading.Thread(target=jadval, daemon=True).start()
    print(f"⚡ http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Ishlovchi).serve_forever()

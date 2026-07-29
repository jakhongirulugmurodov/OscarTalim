#!/usr/bin/env python3
"""Podcast Suite motori — UXP panel bilan gaplashadigan lokal server.

Ishga tushirish:
    python3 server.py

Panel http://127.0.0.1:8765 ga so'rov yuboradi. Server faqat shu
kompyuterning o'zidan (127.0.0.1) so'rov qabul qiladi — tashqariga ochilmaydi.

Endpointlar:
    GET  /health  -> motor ishlayaptimi (panel shu bilan tekshiradi)
    POST /sync    -> {"files": [...], "name": "...", "minutes": 20}
                     Sinxronlab, XML yozadi va natijani JSON qilib qaytaradi.
"""

import json
import os
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# autosync.py ni topish: repo tuzilishi (../../autosync) yoki tayyor paket (../autosync)
_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.join(_here, "..", "..", "autosync"),
              os.path.join(_here, "..", "autosync")):
    if os.path.isfile(os.path.join(_cand, "autosync.py")):
        sys.path.insert(0, _cand)
        break
from autosync import run_sync, FFMPEG, FFPROBE

HOST, PORT = "127.0.0.1", 8765
VERSION = "0.1.0"

# Natijalar paket ichidagi «natijalar» papkasiga tushadi — vaqtinchalik tizim
# papkasida yo'qolib ketmasin, foydalanuvchi Finder'dan topa olsin.
RESULTS_DIR = os.path.join(_here, "..", "natijalar")


def default_output():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H-%M")
    return os.path.abspath(os.path.join(RESULTS_DIR, "sync_" + stamp + ".xml"))


# ------------------------------------------------------------- yangilanish

def repo_root():
    """Papka git klonimi? Bo'lsa — ildizini qaytaradi."""
    path = os.path.abspath(_here)
    for _ in range(6):
        if os.path.isdir(os.path.join(path, ".git")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return None


def git(root, *args, timeout=60):
    out = subprocess.run(["git", "-C", root, *args],
                         capture_output=True, text=True, timeout=timeout)
    return out.returncode, (out.stdout + out.stderr).strip()


def version_info():
    """Hozirgi versiya va yangilanish bor-yo'qligi."""
    root = repo_root()
    if not root:
        return {"git": False,
                "note": "Papka git klon emas — yangilanish tugmasi ishlamaydi"}

    _, current = git(root, "log", "-1", "--format=%h %cd", "--date=short")
    code, _ = git(root, "fetch", "--quiet", "origin")
    behind = 0
    if code == 0:
        _, branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        c, count = git(root, "rev-list", "--count", f"HEAD..origin/{branch}")
        if c == 0 and count.isdigit():
            behind = int(count)
    return {"git": True, "current": current, "updates": behind}


def do_update():
    root = repo_root()
    if not root:
        return {"ok": False, "error": "Papka git klon emas. Yangilash uchun "
                                      "ORNATISH.command orqali o'rnating."}
    code, out = git(root, "pull", "--ff-only", timeout=180)
    if code != 0:
        return {"ok": False, "error": "git pull xatosi: " + out[-400:]}
    _, current = git(root, "log", "-1", "--format=%h %cd", "--date=short")
    return {"ok": True, "current": current, "log": out[-400:]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {})

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "version": VERSION, "modules": ["sync"],
                             "ffmpeg": bool(FFMPEG and FFPROBE)})
        elif self.path == "/version":
            try:
                self._send(200, version_info())
            except Exception as e:
                self._send(200, {"git": False, "note": str(e)})
        else:
            self._send(404, {"error": "Bunday endpoint yo'q"})

    def do_POST(self):
        if self.path == "/update":
            result = do_update()
            self._send(200, result)
            if result.get("ok"):
                # Yangi kod bilan qayta yonishi uchun chiqamiz — launchd
                # (DOIMIY-ORNATISH.command o'rnatgan) motorni o'zi ko'taradi.
                threading.Timer(0.5, lambda: os._exit(0)).start()
            return
        if self.path != "/sync":
            return self._send(404, {"error": "Bunday endpoint yo'q"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")

            files = req.get("files") or []
            if len(files) < 2:
                return self._send(400, {"error": "Kamida 2 ta fayl kerak"})
            missing = [f for f in files if not os.path.isfile(f)]
            if missing:
                return self._send(400, {"error": f"Fayl topilmadi: {missing[0]}"})

            output = req.get("output") or default_output()
            logs = []
            result = run_sync(
                files, output=output,
                name=req.get("name") or "AutoSync Sequence",
                minutes=float(req.get("minutes", 20)),
                log=lambda m: (logs.append(m), print(m)))
            result["logs"] = logs
            self._send(200, result)
        except RuntimeError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            self._send(500, {"error": f"Kutilmagan xato: {e}"})

    def log_message(self, *args):
        pass  # standart HTTP loglari shovqin qilmasin


def main():
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Podcast Suite motori ishga tushdi: http://{HOST}:{PORT}")
    print("Premiere Pro'dagi panel endi motorni ko'ra oladi.")
    print("To'xtatish: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMotor to'xtatildi.")


if __name__ == "__main__":
    main()

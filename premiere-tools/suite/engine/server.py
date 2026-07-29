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
import shutil
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
        sys.path.insert(0, os.path.abspath(_cand))
        break
from autosync import run_sync, FFMPEG, FFPROBE
from cut import run_cut

HOST, PORT = "127.0.0.1", 8765
VERSION = "0.1.0"
PLUGIN_ID = "uz.oscartalim.podcastsuite"

# Natijalar paket ichidagi «natijalar» papkasiga tushadi — vaqtinchalik tizim
# papkasida yo'qolib ketmasin, foydalanuvchi Finder'dan topa olsin.
RESULTS_DIR = os.path.join(_here, "..", "natijalar")


def default_output(files=None, kind="Sync"):
    """Natija fayl qayerga saqlansin.

    Eng qulayi — materiallar turgan papka: montajchi uni izlab yurmaydi va
    loyiha ko'chirilsa XML ham birga ketadi. Papkaga yozib bo'lmasa (masalan
    tashqi disk faqat o'qish uchun ulangan), paket ichidagi «natijalar» ga
    tushadi.
    """
    stamp = time.strftime("%Y-%m-%d_%H-%M")
    fname = f"PodcastSuite_{kind}_{stamp}.xml"

    if files:
        media_dir = os.path.dirname(os.path.abspath(files[0]))
        if os.path.isdir(media_dir) and os.access(media_dir, os.W_OK):
            return os.path.join(media_dir, fname)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    return os.path.abspath(os.path.join(RESULTS_DIR, fname))


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


def installed_panel_dirs():
    """Doimiy o'rnatilgan panel nusxalari (Adobe boshqaradigan papkada).

    Panel .ccx orqali o'rnatilgan bo'lsa, uning fayllari alohida joyda
    yotadi va git pull ularga tegmaydi. Shu papkalarni topamiz.
    """
    base = os.path.expanduser(
        "~/Library/Application Support/Adobe/UXP/Plugins/External")
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, d) for d in os.listdir(base)
            if d.startswith(PLUGIN_ID + "_")
            and os.path.isfile(os.path.join(base, d, "manifest.json"))]


def sync_installed_panel():
    """Yangi panel fayllarini o'rnatilgan nusxaga ham ko'chiradi."""
    src = os.path.join(_here, "..", "panel")
    if not os.path.isdir(src):
        return []
    updated = []
    for target in installed_panel_dirs():
        try:
            for name in os.listdir(src):
                s = os.path.join(src, name)
                if os.path.isfile(s):
                    shutil.copy2(s, os.path.join(target, name))
            updated.append(os.path.basename(target))
        except OSError as e:
            print(f"Panel nusxasini yangilab bo'lmadi ({target}): {e}")
    return updated


def do_update():
    root = repo_root()
    if not root:
        return {"ok": False, "error": "Papka git klon emas. Yangilash uchun "
                                      "ORNATISH.command orqali o'rnating."}
    code, out = git(root, "pull", "--ff-only", timeout=180)
    if code != 0:
        return {"ok": False, "error": "git pull xatosi: " + out[-400:]}
    _, current = git(root, "log", "-1", "--format=%h %cd", "--date=short")
    return {"ok": True, "current": current, "log": out[-400:],
            "panel_updated": sync_installed_panel()}


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
            self._send(200, {"ok": True, "version": VERSION,
                             "modules": ["sync", "cut"],
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
        if self.path not in ("/sync", "/cut"):
            return self._send(404, {"error": "Bunday endpoint yo'q"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")

            files = req.get("files") or []
            least = 1 if self.path == "/cut" else 2
            if len(files) < least:
                return self._send(400, {"error": f"Kamida {least} ta fayl kerak"})
            missing = [f for f in files if not os.path.isfile(f)]
            if missing:
                return self._send(400, {"error": f"Fayl topilmadi: {missing[0]}"})

            kind = "Cut" if self.path == "/cut" else "Sync"
            output = req.get("output") or default_output(files, kind)
            logs = []
            record = lambda m: (logs.append(m), print(m))

            if self.path == "/cut":
                result = run_cut(
                    files, output=output,
                    name=req.get("name") or "Podcast Suite — Cut",
                    threshold=float(req.get("threshold", 0.18)),
                    min_pause=float(req.get("min_pause", 0.7)),
                    padding=float(req.get("padding", 0.12)),
                    log=record)
            else:
                result = run_sync(
                    files, output=output,
                    name=req.get("name") or "Podcast Suite — Sync",
                    log=record)
            result["logs"] = logs
            self._send(200, result)
        except RuntimeError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            self._send(500, {"error": f"Kutilmagan xato: {e}"})

    def log_message(self, *args):
        pass  # standart HTTP loglari shovqin qilmasin


def main():
    print(f"Podcast Suite motori — {os.path.abspath(__file__)}")
    print(f"Modullar: sync, cut · ffmpeg: {bool(FFMPEG and FFPROBE)}")
    try:
        server = HTTPServer((HOST, PORT), Handler)
    except OSError as e:
        # Eng chalkash holat: eski motor portni ushlab turadi, yangisi
        # jimgina o'lib ketadi va panel eski modullarni ko'rsatib turaveradi.
        print(f"[XATO] {HOST}:{PORT} band — eski motor ishlab turibdi ({e}).")
        print("Uni to'xtatish: lsof -ti tcp:8765 | xargs kill")
        sys.exit(1)
    print(f"Ishga tushdi: http://{HOST}:{PORT}")
    print("Premiere Pro'dagi panel endi motorni ko'ra oladi.")
    print("To'xtatish: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMotor to'xtatildi.")


if __name__ == "__main__":
    main()

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
import sys
import tempfile
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
        else:
            self._send(404, {"error": "Bunday endpoint yo'q"})

    def do_POST(self):
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

            output = req.get("output") or os.path.join(
                tempfile.gettempdir(), "podcast-suite-sync.xml")
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

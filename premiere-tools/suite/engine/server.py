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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# autosync.py ni topish: repo tuzilishi (../../autosync) yoki tayyor paket (../autosync)
_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.join(_here, "..", "..", "autosync"),
              os.path.join(_here, "..", "autosync")):
    if os.path.isfile(os.path.join(_cand, "autosync.py")):
        sys.path.insert(0, os.path.abspath(_cand))
        break
from autosync import run_sync, FFMPEG, FFPROBE
from cut import run_cut
from switch import run_switch
from captions import (run_captions, search_archive, find_whisper,
                      have_model, MODELS)
from intro import (run_intro, build_intro, load_transcript,
                   transcript_on_timeline)
from shorts import run_shorts, build_shorts
from matn import run_matn, shriftlar, oldin_korish
from harakat import run_harakat
from gemini import run_import, subtitr_yasash

HOST, PORT = "127.0.0.1", 8765
VERSION = "0.2.0"
PLUGIN_ID = "uz.oscartalim.podcastsuite"

# Natijalar paket ichidagi «natijalar» papkasiga tushadi — vaqtinchalik tizim
# papkasida yo'qolib ketmasin, foydalanuvchi Finder'dan topa olsin.
RESULTS_DIR = os.path.join(_here, "..", "natijalar")

# Ish jarayonining holati. Uzun ishlarda (model yuklash, transkripsiya)
# javob oxirida kelgani uchun panel jim turardi va «osilib qoldi» degan
# taassurot berardi. Endi panel shu holatni har ikki soniyada o'qiydi va
# qaysi bosqich ketayotganini, foizini, qancha vaqt qolganini ko'rsatadi.
PROGRESS = {
    "busy": False, "job": "", "lines": [], "started": 0.0,
    "steps": [],          # [{"label": ..., "weight": ...}] — rejadagi bosqichlar
    "step": -1,           # hozirgi bosqich indeksi
    "stage": "",          # hozirgi bosqich nomi
    "percent": None,      # shu bosqichning foizi (bilinmasa — None)
    "detail": "",         # jonli tafsilot: «340 MB / 1.5 GB»
    "stage_started": 0.0,  # bosqich boshlangan payt — qolgan vaqt shundan
}

# Har ish uchun bosqichlar rejasi. Panel shu ro'yxatni ko'rsatib turadi:
# qaysi biri tugagan, qaysi biri ketayapti, qaysilari navbatda.
JOB_STEPS = {
    "Captions": [{"label": "Ovoz ajratilmoqda", "short": "Ovoz", "weight": 6},
                 {"label": "Model tayyorlanmoqda", "short": "Model", "weight": 4},
                 {"label": "Matnga aylantirilmoqda", "short": "Matn", "weight": 85},
                 {"label": "Subtitr yig'ilmoqda", "short": "Subtitr", "weight": 5}],
    "Sync":     [{"label": "Ovoz tahlil qilinmoqda", "short": "Tahlil", "weight": 70},
                 {"label": "Sinxron hisoblanmoqda", "short": "Sinxron", "weight": 25},
                 {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 5}],
    "Cut":      [{"label": "Ovoz tahlil qilinmoqda", "short": "Tahlil", "weight": 70},
                 {"label": "Pauzalar qidirilmoqda", "short": "Pauzalar", "weight": 25},
                 {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 5}],
    "Intro":    [{"label": "Ovoz tahlil qilinmoqda", "short": "Tahlil", "weight": 75},
                 {"label": "Lahzalar qidirilmoqda", "short": "Lahzalar", "weight": 25}],
    "IntroYasash": [{"label": "Fayllar o'qilmoqda", "short": "Fayllar", "weight": 40},
                    {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 60}],
    "Shorts":   [{"label": "Ovoz tahlil qilinmoqda", "short": "Tahlil", "weight": 75},
                 {"label": "Bo'laklar qidirilmoqda", "short": "Bo'laklar", "weight": 25}],
    "ShortsYasash": [{"label": "Fayllar o'qilmoqda", "short": "Fayllar", "weight": 35},
                     {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 65}],
    "Matn":     [{"label": "Matnlar yasalmoqda", "short": "Matn", "weight": 90},
                 {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 10}],
    "Switch":   [{"label": "Ovoz tahlil qilinmoqda", "short": "Tahlil", "weight": 65},
                 {"label": "Kadrlar rejalanmoqda", "short": "Kadrlar", "weight": 30},
                 {"label": "Timeline yozilmoqda", "short": "Timeline", "weight": 5}],
}


def progress_start(job):
    PROGRESS.update(busy=True, job=job, lines=[], started=time.time(),
                    steps=[dict(s) for s in JOB_STEPS.get(job, [])],
                    step=-1, stage="", percent=None, detail="",
                    stage_started=time.time())


def progress_note(text):
    PROGRESS["lines"].append(text)
    if len(PROGRESS["lines"]) > 400:
        del PROGRESS["lines"][:100]


def progress_update(stage=None, percent=None, detail=None):
    """Modullar shu funksiya orqali «qayerdaman» deb aytadi.

    Bosqich nomi o'zgarsa — rejadagi o'rnini topib, sanoqni yangilaymiz.
    Nomi ro'yxatda bo'lmasa ham yozilaveradi: panel baribir ko'rsatadi.
    """
    if stage and stage != PROGRESS["stage"]:
        PROGRESS["stage"] = stage
        PROGRESS["stage_started"] = time.time()
        PROGRESS["percent"] = None
        PROGRESS["detail"] = ""
        for i, s in enumerate(PROGRESS["steps"]):
            if s["label"] == stage:
                PROGRESS["step"] = i
                break
        else:
            PROGRESS["step"] = min(PROGRESS["step"] + 1,
                                   len(PROGRESS["steps"]) - 1)
    if percent is not None:
        PROGRESS["percent"] = max(0.0, min(100.0, float(percent)))
    if detail is not None:
        PROGRESS["detail"] = detail


def progress_snapshot():
    """Panel uchun to'liq manzara — umumiy foiz shu yerda hisoblanadi."""
    steps = PROGRESS["steps"]
    total = sum(s["weight"] for s in steps) or 100
    done = sum(s["weight"] for s in steps[:max(PROGRESS["step"], 0)])
    cur = steps[PROGRESS["step"]]["weight"] if 0 <= PROGRESS["step"] < len(steps) else 0
    pct = PROGRESS["percent"]
    overall = (done + cur * (pct or 0) / 100.0) / total * 100.0 if steps else None
    now = time.time()
    return {
        "busy": PROGRESS["busy"], "job": PROGRESS["job"],
        "lines": PROGRESS["lines"],
        "steps": [{"label": s["label"], "short": s.get("short", s["label"]),
                   "weight": s["weight"]} for s in steps],
        "step": PROGRESS["step"], "stage": PROGRESS["stage"],
        "percent": pct, "detail": PROGRESS["detail"],
        "overall": round(overall, 1) if steps else None,
        "elapsed": (now - PROGRESS["started"]) if PROGRESS["started"] else 0,
        "stage_elapsed": (now - PROGRESS["stage_started"])
                         if PROGRESS["stage_started"] else 0,
    }


def panel_build():
    """Diskdagi panel kodining versiyasi (main.js ichidagi PANEL_BUILD).

    Panel o'zining versiyasini shu bilan solishtiradi: farq bo'lsa — demak
    Premiere xotirasida eski nusxa ishlab turibdi va uni qayta yuklash kerak.
    Aynan shu holat bir necha marta «tuzatilgan xato yana chiqdi» degan
    chalkashlikka olib keldi.
    """
    path = os.path.join(_here, "..", "panel", "main.js")
    try:
        with open(path, encoding="utf-8") as fh:
            head = fh.read(4000)
    except OSError:
        return ""
    import re as _re
    m = _re.search(r'PANEL_BUILD\s*=\s*"([^"]*)"', head)
    return m.group(1) if m else ""


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
    """Doimiy o'rnatilgan panel eskirganini xabar qiladi.

    Bu papka Adobe o'rnatuvchisiga tegishli. Fayllarni to'g'ridan-to'g'ri
    almashtirib ko'rdik va plugin Premiere ro'yxatidan yo'qoldi, shuning
    uchun endi tegmaymiz: o'rnatilgan nusxa mavjud bo'lsa, uni qayta
    qadoqlash kerakligini aytamiz, xolos.
    """
    stale = [os.path.basename(d) for d in installed_panel_dirs()]
    if stale:
        print("Diqqat: doimiy o'rnatilgan panel eski kodda qoldi — "
              "yangilash uchun UDT > Package > .ccx ni qayta o'rnating.")
    return stale


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
                             "modules": ["sync", "cut", "switch", "captions",
                                         "intro", "shorts", "matn", "harakat", "gemini"],
                             "whisper": bool(find_whisper()),
                             "panel_build": panel_build(),
                             # qaysi model tayyor — panel yuklab olish
                             "models": {k: have_model(k) for k in MODELS},
                             "ffmpeg": bool(FFMPEG and FFPROBE)})
        elif self.path.startswith("/search"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            try:
                self._send(200, {"hits": search_archive(q)})
            except Exception as e:
                self._send(500, {"error": str(e)})
        elif self.path == "/shriftlar":
            # Panelda shrift tanlash uchun. ffmpeg'da fontconfig yo'q,
            # shuning uchun ro'yxatni motor fayl tizimidan o'zi yig'adi.
            try:
                self._send(200, {"shriftlar": shriftlar()})
            except Exception as e:
                self._send(500, {"error": str(e)})
        elif self.path == "/progress":
            self._send(200, progress_snapshot())
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
        if self.path == "/log-saqlash":
            # Panel log'ini faylga yozamiz: uzun tashxis matnini ekrandan
            # o'qib olish qiyin, faylni esa ochib nusxalash oson.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                os.makedirs(RESULTS_DIR, exist_ok=True)
                path = os.path.abspath(os.path.join(
                    RESULTS_DIR,
                    "panel-log_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".txt"))
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(req.get("text") or "")
                return self._send(200, {"ok": True, "path": path})
            except Exception as e:
                return self._send(500, {"error": str(e)})

        if self.path == "/subtitr":
            # Arxivdagi transkriptdan SRT. Whisper ishlatilmaydi —
            # transkript bir marta olib kirilgan bo'lsa yetadi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                out = req.get("output") or os.path.join(
                    os.path.abspath(RESULTS_DIR),
                    "subtitr_" + time.strftime("%Y-%m-%d_%H-%M") + ".srt")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                lines = []
                natija = subtitr_yasash(req.get("files") or [],
                                        timeline=req.get("timeline"),
                                        output=out, log=lines.append)
                natija["log"] = lines
                return self._send(200, natija)
            except Exception as e:
                return self._send(400, {"error": str(e)})

        if self.path == "/transkript-import":
            # Gemini transkriptini (SRT/JSON) suite arxiviga olib kiradi.
            # Shundan keyin Intro, Captions va matndan tanlash uni o'zi
            # topadi — chunki hammasi bitta arxivdan qidiradi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                fayl = req.get("fayl") or ""
                manba = req.get("manba") or ""
                if not fayl or not manba:
                    return self._send(400, {"error":
                        "Transkript fayli va video fayl ko'rsatilishi shart"})
                lines = []
                natija = run_import(fayl, manba, nomi=req.get("nomi"),
                                    log=lines.append)
                natija["log"] = lines
                return self._send(200, natija)
            except Exception as e:
                return self._send(400, {"error": str(e)})

        if self.path == "/harakat":
            # Kadrga harakat rejasi. Og'ir ish yo'q — faqat manba
            # o'lchamini o'qiydi, shuning uchun bir zumda javob beradi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                clips = req.get("clips") or []
                w = int(req.get("width") or 0)
                h = int(req.get("height") or 0)
                if not w or not h:
                    return self._send(400, {"error":
                        "Sequence o'lchami o'qilmadi"})
                lines = []
                reja = run_harakat(clips, w, h,
                                   oraliq=float(req.get("oraliq") or 15),
                                   kuch=float(req.get("kuch") or 5),
                                   rejim=str(req.get("rejim") or "kesim"),
                                   daraja=str(req.get("daraja") or "orta"),
                                   log=lines.append)
                reja["log"] = lines
                return self._send(200, reja)
            except Exception as e:
                return self._send(500, {"error": str(e)})

        if self.path == "/transkript":
            # Saqlangan transkriptni timeline vaqtida qaytaradi.
            # Ovoz qayta o'qilmaydi — faqat arxiv va joylashuv kerak,
            # shuning uchun bir zumda ishlaydi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                files = req.get("files") or []
                seq = req.get("timeline")
                if seq:
                    files = list(dict.fromkeys(c["path"] for c in seq))
                if not files:
                    return self._send(400, {"error": "Fayl ko'rsatilmagan"})

                data = load_transcript(files)
                if not data:
                    return self._send(404, {"error":
                        "Bu yozuv uchun transkript topilmadi. Captions "
                        "tabida «To'liq transkripsiya» ni bir marta "
                        "ishlating — keyin matndan tanlash ochiladi."})

                # Yengil klip ma'lumoti: audio o'qilmaydi, faqat joylashuv
                if seq:
                    joy = {}
                    for it in seq:
                        joy.setdefault(os.path.abspath(it["path"]), []).append(
                            {"start": float(it["start"]), "in": float(it["in"]),
                             "out": float(it["out"])})
                    clips = [{"path": p, "name": os.path.basename(p),
                              "placements": v} for p, v in joy.items()]
                else:
                    clips = [{"path": os.path.abspath(f),
                              "name": os.path.basename(f),
                              "placements": [{"start": 0.0, "in": 0.0,
                                              "out": 10 ** 9}]}
                             for f in files]

                lines = transcript_on_timeline(data, clips)
                lines.sort(key=lambda x: x["start"])
                return self._send(200, {
                    "title": data.get("title") or "",
                    "from_sequence": bool(data.get("from_sequence")),
                    "lines": [{"start": round(float(l["start"]), 2),
                               "end": round(float(l["end"]), 2),
                               "text": l.get("text", "")}
                              for l in lines if l.get("text")],
                })
            except Exception as e:
                return self._send(500, {"error": str(e)})

        if self.path == "/matn-oldin":
            # Panelda «shunday ko'rinadi» rasmi. Kichraytirilgan PNG base64
            # bo'lib qaytadi: UXP panelga fayl yo'li bilan rasm ko'rsatish
            # ishonchsiz, data-URI esa har doim ishlaydi.
            try:
                import base64
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                w = int(req.get("width") or 1080)
                h = int(req.get("height") or 1920)
                # Ko'rish uchun 540 px kenglik yetarli (uslub aynan saqlanadi)
                k = 540.0 / max(w, 1)
                pw, ph = max(2, int(w * k) // 2 * 2), max(2, int(h * k) // 2 * 2)
                os.makedirs(RESULTS_DIR, exist_ok=True)
                png = os.path.abspath(os.path.join(RESULTS_DIR, "_matn-oldin.png"))
                oldin_korish(req.get("matn") or "", png, pw, ph,
                             uslub=req.get("uslub") or {},
                             kadr=req.get("kadr"))
                with open(png, "rb") as fh:
                    data = base64.b64encode(fh.read()).decode("ascii")
                return self._send(200, {"png": "data:image/png;base64," + data,
                                        "width": pw, "height": ph})
            except Exception as e:
                return self._send(400, {"error": str(e)})

        if self.path == "/matn":
            # Matnlarni render qilib, timeline'ga qo'yadigan XML yozadi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                bloklar = req.get("bloklar") or []
                if not bloklar:
                    return self._send(400, {"error": "Bironta matn yozilmagan"})
                logs = []
                progress_start("Matn")
                record = lambda m: (logs.append(m), progress_note(m), print(m))
                output = req.get("output") or default_output(None, "Matn")
                result = run_matn(
                    bloklar, output=output,
                    name=req.get("name") or "Podcast Suite — Matn",
                    width=int(req.get("width") or 1920),
                    height=int(req.get("height") or 1080),
                    fps=float(req.get("fps") or 25.0),
                    uslub=req.get("uslub") or {},
                    fallback=RESULTS_DIR, log=record, progress=progress_update)
                result["logs"] = logs
                return self._send(200, result)
            except RuntimeError as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:
                return self._send(500, {"error": str(e)})
            finally:
                PROGRESS["busy"] = False

        if self.path in ("/intro-yasash", "/shorts-yasash"):
            # Ikkinchi bosqich: tanlangan lahzalardan sequence. Qayta tahlil
            # qilinmaydi — birinchi bosqichdagi joylashuv ishlatiladi.
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                moments = req.get("moments") or []
                arrangement = req.get("arrangement") or []
                if not moments or not arrangement:
                    return self._send(400, {"error": "Hech narsa tanlanmagan"})
                is_shorts = self.path == "/shorts-yasash"
                logs = []
                progress_start("ShortsYasash" if is_shorts else "IntroYasash")
                record = lambda m: (logs.append(m), progress_note(m), print(m))
                paths = [a["path"] for a in arrangement]
                review = bool(req.get("review"))
                if is_shorts:
                    output = req.get("output") or default_output(paths, "Shorts")
                    result = build_shorts(
                        arrangement, moments, output=output,
                        fallback=RESULTS_DIR, log=record,
                        progress=progress_update)
                else:
                    output = req.get("output") or default_output(
                        paths, "Intro-nomzodlar" if review else "Intro")
                    result = build_intro(
                        arrangement, moments, output=output, review=review,
                        name=req.get("name") or ("Podcast Suite — Intro nomzodlar"
                                                 if review else
                                                 "Podcast Suite — Intro"),
                        fallback=RESULTS_DIR, log=record,
                        progress=progress_update)
                    result["review"] = review
                result["logs"] = logs
                return self._send(200, result)
            except RuntimeError as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:
                return self._send(500, {"error": f"Kutilmagan xato: {e}"})
            finally:
                PROGRESS["busy"] = False

        if self.path not in ("/sync", "/cut", "/switch", "/captions", "/intro",
                             "/shorts"):
            return self._send(404, {"error": "Bunday endpoint yo'q"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")

            files = req.get("files") or []
            seq_timeline = (req.get("timeline")
                            if self.path in ("/cut", "/switch", "/intro",
                                             "/shorts")
                            else None)
            if seq_timeline:
                files = list(dict.fromkeys(c["path"] for c in seq_timeline))
            least = 1 if self.path in ("/cut", "/captions", "/intro",
                                       "/shorts") else 2
            if len(files) < least:
                return self._send(400, {"error": f"Kamida {least} ta fayl kerak"})
            missing = [f for f in files if not os.path.isfile(f)]
            if missing:
                return self._send(400, {"error": f"Fayl topilmadi: {missing[0]}"})

            kind = {"/cut": "Cut", "/switch": "Switch",
                    "/captions": "Captions", "/intro": "Intro",
                    "/shorts": "Shorts"}.get(self.path, "Sync")
            output = req.get("output") or default_output(files, kind)
            logs = []
            progress_start(kind)
            record = lambda m: (logs.append(m), progress_note(m), print(m))
            step = progress_update

            if self.path == "/shorts":
                result = run_shorts(
                    files, timeline=seq_timeline,
                    markers=req.get("markers"),
                    limit=int(req.get("limit", 8)),
                    faqat_markerlar=bool(req.get("faqat_markerlar")),
                    log=record, progress=step)
            elif self.path == "/intro":
                result = run_intro(
                    files, timeline=seq_timeline,
                    markers=req.get("markers"),
                    limit=int(req.get("limit", 18)),
                    log=record, progress=step)
            elif self.path == "/captions":
                # Sequence berilgan bo'lsa — shu bitta ovoz manbasining
                # montajda ishlatilgan bo'laklarini ajratamiz.
                spans = [{"start": c["start"], "in": c["in"], "out": c["out"]}
                         for c in (req.get("timeline") or [])
                         if c.get("path") == files[0]]
                result = run_captions(
                    files[0], output=output,
                    model=req.get("model") or "balans",
                    language=req.get("language") or "uz",
                    sample_seconds=req.get("sample_seconds"),
                    title=req.get("title"), spans=spans,
                    fallback=RESULTS_DIR, log=record, progress=step)
            elif self.path == "/switch":
                result = run_switch(
                    files, output=output,
                    name=req.get("name") or "Podcast Suite — Switch",
                    roles=req.get("roles"), speakers=req.get("speakers"),
                    audio_master=req.get("audio_master"),
                    min_shot=float(req.get("min_shot", 2.5)),
                    max_shot=float(req.get("max_shot", 25.0)),
                    timeline=seq_timeline, fallback=RESULTS_DIR, log=record,
                    progress=step)
            elif self.path == "/cut":
                result = run_cut(
                    files, output=output,
                    name=req.get("name") or "Podcast Suite — Cut",
                    # threshold berilmasa «auto» — chegara yozuvning o'z
                    # ovoz darajasidan olinadi (panel qat'iylikni yuboradi)
                    threshold=req.get("threshold") or "auto",
                    strictness=req.get("strictness") or "orta",
                    min_pause=float(req.get("min_pause", 0.7)),
                    padding=float(req.get("padding", 0.12)),
                    min_keep=float(req.get("min_keep", 0.30)),
                    seq_format=req.get("seq_format") or None,
                    timeline=seq_timeline, fallback=RESULTS_DIR, log=record,
                    progress=step,
                    # Panel montajni joyida qirqadigan bo'lsa, XML yozilmaydi
                    xml_yozish=not req.get("faqat_pauzalar"))
            else:
                result = run_sync(
                    files, output=output,
                    name=req.get("name") or "Podcast Suite — Sync",
                    fallback=RESULTS_DIR, log=record, progress=step)
            result["logs"] = logs
            self._send(200, result)
        except RuntimeError as e:
            self._send(400, {"error": str(e)})
        except Exception as e:
            self._send(500, {"error": f"Kutilmagan xato: {e}"})
        finally:
            PROGRESS["busy"] = False

    def log_message(self, *args):
        pass  # standart HTTP loglari shovqin qilmasin


def main():
    print(f"Podcast Suite motori — {os.path.abspath(__file__)}")
    print(f"Modullar: sync, cut, switch, captions · "
          f"ffmpeg: {bool(FFMPEG and FFPROBE)} · whisper: {bool(find_whisper())}")
    try:
        # Ko'p oqimli: uzun transkripsiya ketayotganda ham panel holatni
        # (/health, /progress) so'ray oladi — aks holda navbatda qotib turardi.
        server = ThreadingHTTPServer((HOST, PORT), Handler)
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

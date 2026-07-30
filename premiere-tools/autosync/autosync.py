#!/usr/bin/env python3
"""AutoSync — podcast/multicam kliplarni audio orqali sinxronlash vositasi.

Foydalanish:
    python3 autosync.py cam1.mp4 cam2.mp4 cam3.mp4 recorder.wav -o synced.xml

Natija: Premiere Pro'ga import qilinadigan FCP7 XML (File > Import > synced.xml).
Har bir fayl alohida video/audio trekka, audio bo'yicha to'g'ri joyga surilgan
holda qo'yiladi — xuddi "Create Multi-Camera Source Sequence" dagidek, lekin
avtomatik va tashqi rekorder fayllari bilan ham ishlaydi.

Talablar: Python 3.8+, numpy, ffmpeg/ffprobe (PATH da bo'lishi kerak).
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
from urllib.request import pathname2url
from xml.sax.saxutils import escape

import numpy as np

ANALYSIS_SR = 8000   # audio o'qish chastotasi (past = tez, tahlilga yetarli)
ENV_RATE = 200       # envelope namunalari/sekund → 5 ms aniqlik (kadrdan mayda)
MIN_CONFIDENCE = 2.5  # shundan past bo'lsa siljish ishonchsiz deb belgilanadi


def _find_tool(name):
    """ffmpeg/ffprobe ni topish — PATH bo'sh bo'lsa ham ishlashi uchun.

    Motor qaysi papkadan yoqilganidan qat'i nazar topilsin: paket ichidagi
    bin/, Homebrew joylari va foydalanuvchining odatdagi papkalari qaraladi.
    """
    found = shutil.which(name)
    if found:
        return found

    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(here, "..", "bin", name),      # paket: autosync/../bin
        os.path.join(here, "..", "suite", "bin", name),
        os.path.join(here, "bin", name),
        "/opt/homebrew/bin/" + name,                # Apple Silicon Homebrew
        "/usr/local/bin/" + name,                   # Intel Homebrew / qo'lda
        "/opt/local/bin/" + name,                   # MacPorts
    ]
    # Har qanday joydagi PodcastSuite/bin — foydalanuvchi qayerga ochgan bo'lsa ham
    for folder in ("Desktop", "Downloads", "Documents", ""):
        candidates.append(os.path.join(home, folder, "PodcastSuite", "bin", name))
    candidates += glob.glob(os.path.join(home, "*", "PodcastSuite", "bin", name))

    for path in candidates:
        path = os.path.abspath(path)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


FFMPEG = _find_tool("ffmpeg")
FFPROBE = _find_tool("ffprobe")

FFMPEG_YOQ = (
    "ffmpeg topilmadi. Motorni «motorni-yoqish.command» orqali ishga tushiring "
    "— u ffmpeg'ni o'zi yuklab oladi. Yoki terminalda: brew install ffmpeg"
)


# ---------------------------------------------------------------- media info

def stream_rotation(stream):
    """Video oqimining ekranda ko'rsatish burchagi (0/90/180/270).

    Telefonda tik (reels) olingan video ko'pincha 1920x1080 bo'lib yoziladi
    va yoniga «90 daraja burib ko'rsat» belgisi qo'yiladi. Shu belgini
    o'qimasak, fayl gorizontal ko'rinadi — sequence ham gorizontal
    yasaladi, vertikal kadr esa yon tomonga cho'zilib qoladi.

    Yangi fayllarda belgi `side_data_list` ichida (display matrix), eskisida
    `tags.rotate` da bo'ladi — ikkalasi ham qaraladi.
    """
    for side in stream.get("side_data_list") or []:
        if "rotation" in side:
            try:
                return int(round(float(side["rotation"]))) % 360
            except (TypeError, ValueError):
                pass
    tag = (stream.get("tags") or {}).get("rotate")
    if tag is not None:
        try:
            return int(round(float(tag))) % 360
        except (TypeError, ValueError):
            pass
    return 0


def ffprobe(path):
    """Fayl haqida ma'lumot: davomiylik, fps, o'lcham, audio bor-yo'qligi.

    `width`/`height` — EKRANDAGI o'lcham (burilish hisobga olingan holda),
    ya'ni odam ko'radigan kadr. Faylga qanday yozilgani `raw_width`/
    `raw_height` da qoladi.
    """
    if not FFPROBE:
        raise RuntimeError(FFMPEG_YOQ)
    cmd = [
        FFPROBE, "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe xatosi ({path}): {out.stderr.strip()}")
    data = json.loads(out.stdout)

    if not data.get("streams") or "duration" not in data.get("format", {}):
        raise RuntimeError(
            f"{os.path.basename(path)}: fayl buzuq yoki media emas "
            "(davomiyligi o'qilmadi)")

    info = {
        "path": os.path.abspath(path),
        "name": os.path.basename(path),
        "duration": float(data["format"]["duration"]),
        "has_video": False,
        "has_audio": False,
        "fps": None,
        "width": None,
        "height": None,
        "raw_width": None,
        "raw_height": None,
        "rotation": 0,
        "audio_rate": 48000,
        "audio_channels": 2,
    }
    for s in data["streams"]:
        if s["codec_type"] == "video" and not info["has_video"]:
            num, _, den = s.get("avg_frame_rate", "0/1").partition("/")
            if float(den or 1) > 0 and float(num) > 0:
                info["fps"] = float(num) / float(den or 1)
            info["has_video"] = True
            w, h = s.get("width"), s.get("height")
            rot = stream_rotation(s)
            info["raw_width"], info["raw_height"] = w, h
            info["rotation"] = rot
            # 90/270 da tomonlar almashadi: yozilgani 1920x1080, ko'rinishi
            # 1080x1920. Sequence ko'rinadigan o'lcham bo'yicha yasaladi.
            if rot in (90, 270) and w and h:
                w, h = h, w
            info["width"], info["height"] = w, h
        elif s["codec_type"] == "audio" and not info["has_audio"]:
            info["has_audio"] = True
            info["audio_rate"] = int(s.get("sample_rate", 48000))
            info["audio_channels"] = int(s.get("channels", 2))
    return info


def extract_envelope(path, duration=None, progress=None):
    """Audioning energiya «izi» (envelope) — to'liq fayl bo'yicha.

    Butun audioni xotiraga yig'ish o'rniga oqim bo'lib o'qiladi va har
    5 ms uchun bitta RMS qiymat saqlanadi. Shu tufayli 1 soatlik yozuv ham
    bir necha megabaytga sig'adi — fayl uzunligiga cheklov qo'yish shart emas.
    """
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)

    bin_size = ANALYSIS_SR // ENV_RATE
    cmd = [FFMPEG, "-v", "error", "-i", path, "-map", "a:0", "-ac", "1",
           "-ar", str(ANALYSIS_SR), "-f", "f32le", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Uzun fayl bir necha daqiqa o'qiladi — bu Sync/Cut/Switch ishining eng
    # og'ir qismi. Necha bayt o'qilganini bilamiz, demak foizni ham bilamiz.
    say = progress or (lambda **k: None)
    expect = (duration or 0) * ANALYSIS_SR * 4      # f32le: 4 bayt/namuna
    parts, leftover, got = [], b"", 0
    read_bytes = bin_size * 4 * 20000
    while True:
        data = proc.stdout.read(read_bytes)
        if not data:
            break
        got += len(data)
        if expect:
            say(percent=min(99.0, got / expect * 100))
        data = leftover + data
        usable = (len(data) // 4 // bin_size) * bin_size
        leftover = data[usable * 4:]
        if usable:
            block = np.frombuffer(data[:usable * 4], dtype=np.float32)
            block = block.astype(np.float64).reshape(-1, bin_size)
            parts.append(np.sqrt((block * block).mean(axis=1)))
    proc.stdout.close()
    err = proc.stderr.read().decode(errors="replace").strip()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg xatosi ({os.path.basename(path)}): {err}")
    if not parts:
        raise RuntimeError(f"{os.path.basename(path)}: audio o'qib bo'lmadi")

    env = np.concatenate(parts)
    # Logarifmik siqish: turli mikrofon va masofalardagi yozuvlar solishtirsa
    # bo'ladigan bo'lsin (baland tovushlar tahlilni bosib ketmasin).
    env = np.log1p(env / (np.median(env) + 1e-9))
    env -= env.mean()
    std = env.std()
    if std > 0:
        env /= std
    return env


def sub_progress(say, index, total):
    """Bitta fayl ichidagi foizni «i-fayl / jami» foiziga aylantiradi.

    Shunda panelda bitta uzluksiz bar ko'rinadi: 3 fayldan ikkinchisining
    yarmi — 50%, 4 fayldan uchinchisining oxiri — 75%.
    """
    def inner(percent=None, **kw):
        if percent is not None and total:
            say(percent=(index + percent / 100.0) / total * 100)
    return inner


# ------------------------------------------------------------- offset topish

def find_offset(ref, sig):
    """sig yozuvi ref'dan necha soniya KEYIN boshlanganini topadi.

    Envelope'lar kross-korrelyatsiyasi. Musbat natija = sig keyinroq
    boshlangan. Ishonch — cho'qqining eng kuchli raqibiga nisbati: mos
    kelmagan yozuvlarda bu ko'rsatkich 1 ga yaqin bo'lib qoladi, shuning
    uchun u eski «median» o'lchovidan ancha ishonchli.
    Qaytadi: (soniya, ishonch).
    """
    n = len(ref) + len(sig) - 1
    nfft = 1 << (n - 1).bit_length()
    corr = np.fft.irfft(np.fft.rfft(ref, nfft) * np.conj(np.fft.rfft(sig, nfft)),
                        nfft)

    peak_idx = int(np.argmax(corr))
    peak = float(corr[peak_idx])
    lag = peak_idx if peak_idx <= nfft // 2 else peak_idx - nfft
    if peak <= 0:
        return lag / ENV_RATE, 0.0

    # Cho'qqi atrofidagi ±1 soniyani chiqarib tashlab, eng kuchli raqibni topamiz
    guard = ENV_RATE
    rival = corr.copy()
    rival[max(0, peak_idx - guard):peak_idx + guard + 1] = 0
    if peak_idx < guard:                      # aylanma chetlar
        rival[nfft - (guard - peak_idx):] = 0
    if peak_idx + guard >= nfft:
        rival[:peak_idx + guard - nfft + 1] = 0

    second = float(np.max(rival))
    confidence = peak / second if second > 0 else float("inf")
    return lag / ENV_RATE, confidence


def write_xml(xml, output, fallback=None, log=print):
    """XML'ni yozadi; joy yozishga yopiq bo'lsa — zaxira papkaga.

    macOS tashqi disklarga yozishni bloklashi mumkin (Operation not
    permitted), shuning uchun butun ish shu sababdan bekor bo'lib
    ketmasin: natijani zaxira papkaga saqlab, yo'lini aytamiz.
    """
    output = os.path.abspath(output)
    try:
        with open(output, "w", encoding="utf-8") as fh:
            fh.write(xml)
        return output
    except OSError as e:
        if not fallback:
            raise RuntimeError(f"Faylni yozib bo'lmadi ({output}): {e}")
        log(f"OGOHLANTIRISH: {os.path.dirname(output)} ga yozib bo'lmadi "
            f"({e.strerror}) — natija zaxira papkaga saqlandi")
        os.makedirs(fallback, exist_ok=True)
        alt = os.path.abspath(os.path.join(fallback, os.path.basename(output)))
        with open(alt, "w", encoding="utf-8") as fh:
            fh.write(xml)
        return alt


# ----------------------------------------------------------- XML generatsiya

def fps_to_timebase(fps):
    """29.97 -> (30, TRUE); 25 -> (25, FALSE) va h.k."""
    if fps is None:
        return 25, "FALSE"
    for real, base in ((23.976, 24), (29.97, 30), (59.94, 60)):
        if abs(fps - real) < 0.01:
            return base, "TRUE"
    return int(round(fps)), "FALSE"


# ------------------------------------------------- ovoz darajasi chegaralari
#
# Qat'iy son («0.12 dan past — jimlik») har yozuvga to'g'ri kelmaydi:
# mikrofon yaqin turgan yoki xonasi shovqinli yozuvda u butunlay boshqa
# joyga tushadi. Shuning uchun chegara har yozuvning O'Z darajalaridan
# hisoblanadi. Cut, Intro va Shorts — uchovi ham shu yerdan oladi.

def otsu_split(values, bins=256):
    """Ikki to'da orasidagi eng chuqur «vodiy» (Otsu usuli).

    Yozuvda ikki xil daraja bor: jimlik/shovqin va gap. Ularning orasidagi
    chegarani qidiramiz — qaysi nuqtada bo'linsa, ikki to'da bir-biridan
    eng uzoq ajraladi. Rasm qayta ishlashdagi klassik usul; bu yerda ham
    vazifa aynan shu: bitta sonli chegara topish.
    """
    hist, edges = np.histogram(values, bins=bins, range=(0.0, 1.0))
    w = hist.astype(np.float64)
    total = w.sum()
    if total <= 0:
        return None
    centers = (edges[:-1] + edges[1:]) / 2.0
    w0 = np.cumsum(w)[:-1]                     # chegaradan pastdagilar
    w1 = total - w0
    m0 = np.cumsum(w * centers)[:-1]
    m_all = float((w * centers).sum())
    ok = (w0 > 0) & (w1 > 0)
    if not ok.any():
        return None
    mu0 = m0 / np.where(w0 > 0, w0, 1.0)
    mu1 = (m_all - m0) / np.where(w1 > 0, w1, 1.0)
    between = w0 * w1 * (mu0 - mu1) ** 2
    between[~ok] = -1.0
    return float(edges[int(np.argmax(between)) + 1])


def level_range(loud):
    """Yozuvning shovqin darajasi va gap darajasi (p10 va p92)."""
    return float(np.percentile(loud, 10)), float(np.percentile(loud, 92))


def quiet_threshold(loud, log=None):
    """Jimlik chegarasi — bo'lak CHEGARALARINI topish uchun.

    Bu Cut'dagi «gap bormi?» chegarasidan pastroq turadi va ataylab
    shunday: Intro/Shorts bu bilan bo'lak qayerdan boshlanib qayerda
    tugashini hal qiladi. Baland chegara olsak, bo'lak gap o'rtasidan,
    bo'g'inlar orasidagi mayda tanaffusdan kesilib qolardi.

    Shovqin darajasi bilan gap darajasi orasidagi vodiyning pastki
    uchdan biri olinadi: shovqindan yuqori, lekin gapga tegmaydi.
    """
    floor, speech = level_range(loud)
    span = speech - floor
    if span < 0.02:
        return 0.12                            # eski qat'iy qiymat
    valley = otsu_split(loud)
    if valley is None or not (floor < valley < speech):
        valley = floor + 0.45 * span
    thr = floor + 0.35 * (valley - floor)
    thr = min(max(thr, floor + 0.02), floor + 0.30 * span)
    if log:
        log(f"  jimlik chegarasi: {thr:.3f} (shovqin {floor:.2f}, "
            f"gap {speech:.2f})")
    return thr


def shape_name(width, height):
    """Kadr shakli — logda odam tilida ko'rinsin."""
    if not width or not height:
        return "noma'lum"
    if height > width:
        return "vertikal"
    if height == width:
        return "kvadrat"
    return "gorizontal"


def _clip_weight(clip):
    """Klip timeline'da necha soniya turadi — format ovoz berishida vazni."""
    places = clip.get("placements")
    if places:
        return sum(max(0.0, float(p["out"]) - float(p["in"])) for p in places)
    return float(clip.get("duration") or 0.0)


def sequence_format(clips, log=print, prefer=None):
    """Sequence o'lchami va fps'ini manbalarning O'ZIGA qarab tanlaydi.

    Ilgari har modul «ro'yxatdagi birinchi videoli fayl»ni olardi. Bu ikki
    joyda yiqilardi: reels (vertikal) yozuv gorizontal sequence'ga tushib
    qolardi, aralash materialda esa formatni fayllar tartibi hal qilardi.

    Endi ovoz beriladi: har format timeline'da necha soniya turgan bo'lsa,
    shuncha vazn oladi va eng ko'p vaqt egallagani yutadi. Sozlamadan
    hech narsa kiritish shart emas — reels tashlansangiz, sequence ham
    vertikal bo'ladi.

    `prefer` — {"width": .., "height": ..}: Premiere'dagi ochiq sequence'ning
    o'z o'lchami. Montaj tayyor sequence'dan olinayotgan bo'lsa, formatni
    siz allaqachon tanlagansiz — biz uni buzmaymiz.

    Qaytadi: {"fps", "timebase", "ntsc", "width", "height", "mixed"}.
    """
    videos = [c for c in clips
              if c.get("has_video") and c.get("width") and c.get("height")]
    if not videos:
        log("Sequence: videoli fayl yo'q — 1920x1080, 25fps")
        return {"fps": 25.0, "timebase": 25, "ntsc": "FALSE",
                "width": 1920, "height": 1080, "mixed": False}

    tally = {}
    for c in videos:
        key = (int(c["width"]), int(c["height"]),
               round(float(c["fps"] or 25.0), 3))
        tally[key] = tally.get(key, 0.0) + _clip_weight(c)

    # Teng bo'lsa — kattaroq kadr yutsin (kichigini kattaga cho'zgandan
    # ko'ra, kattasini kichikka sig'dirgan afzal).
    width, height, fps = max(tally.items(),
                             key=lambda kv: (kv[1], kv[0][0] * kv[0][1]))[0]
    timebase, ntsc = fps_to_timebase(fps)

    # Ochiq sequence'dan olinayotgan bo'lsa — uning o'lchamini saqlaymiz.
    # fps manbadan qoladi: kadr chegaralari shu bo'yicha hisoblangan.
    if prefer:
        try:
            pw, ph = int(prefer.get("width") or 0), int(prefer.get("height") or 0)
        except (TypeError, ValueError):
            pw = ph = 0
        if pw > 0 and ph > 0 and (pw, ph) != (width, height):
            log(f"Sequence: {pw}x{ph} ({shape_name(pw, ph)}) — Premiere'dagi "
                f"ochiq sequence'dan (manba {width}x{height})")
            return {"fps": float(fps), "timebase": timebase, "ntsc": ntsc,
                    "width": pw, "height": ph, "mixed": len(tally) > 1}

    shapes = {shape_name(w, h) for w, h, _ in tally}
    rotated = [c["name"] for c in videos if c.get("rotation")]
    log(f"Sequence: {width}x{height} ({shape_name(width, height)}), "
        f"{timebase}fps (ntsc={ntsc}) — manbadan avtomatik")
    if rotated:
        log(f"  burilgan (telefon/reels) fayl: {', '.join(rotated[:3])}"
            + (" ..." if len(rotated) > 3 else ""))
    if len(shapes) > 1:
        log("  OGOHLANTIRISH: manbalar aralash (" + ", ".join(sorted(shapes))
            + ") — ko'p vaqt egallagani tanlandi, qolganlari kadrga "
              "moslanadi (Premiere'da Auto Reframe yordam beradi)")

    return {"fps": float(fps), "timebase": timebase, "ntsc": ntsc,
            "width": int(width), "height": int(height),
            "mixed": len(tally) > 1}


def rate_xml(timebase, ntsc, indent):
    pad = " " * indent
    return (f"{pad}<rate>\n{pad}\t<timebase>{timebase}</timebase>\n"
            f"{pad}\t<ntsc>{ntsc}</ntsc>\n{pad}</rate>")


def file_xml(clip, file_id, timebase, ntsc, full=True):
    """<file> bloki. Bir fayl ikkinchi marta ishlatilsa faqat id yoziladi."""
    if not full:
        return f'\t\t\t\t\t\t<file id="{file_id}"/>'
    url = "file://localhost" + pathname2url(clip["path"])
    lines = [f'\t\t\t\t\t\t<file id="{file_id}">',
             f"\t\t\t\t\t\t\t<name>{escape(clip['name'])}</name>",
             f"\t\t\t\t\t\t\t<pathurl>{escape(url)}</pathurl>",
             rate_xml(timebase, ntsc, 7).replace(" " * 7, "\t" * 7),
             f"\t\t\t\t\t\t\t<duration>{clip['dur_frames']}</duration>",
             "\t\t\t\t\t\t\t<media>"]
    if clip["has_video"]:
        lines += ["\t\t\t\t\t\t\t\t<video>",
                  "\t\t\t\t\t\t\t\t\t<samplecharacteristics>",
                  rate_xml(timebase, ntsc, 10).replace(" " * 10, "\t" * 10),
                  f"\t\t\t\t\t\t\t\t\t\t<width>{clip['width']}</width>",
                  f"\t\t\t\t\t\t\t\t\t\t<height>{clip['height']}</height>",
                  "\t\t\t\t\t\t\t\t\t</samplecharacteristics>",
                  "\t\t\t\t\t\t\t\t</video>"]
    if clip["has_audio"]:
        lines += ["\t\t\t\t\t\t\t\t<audio>",
                  "\t\t\t\t\t\t\t\t\t<samplecharacteristics>",
                  f"\t\t\t\t\t\t\t\t\t\t<samplerate>{clip['audio_rate']}</samplerate>",
                  "\t\t\t\t\t\t\t\t\t\t<depth>16</depth>",
                  "\t\t\t\t\t\t\t\t\t</samplecharacteristics>",
                  f"\t\t\t\t\t\t\t\t\t<channelcount>{clip['audio_channels']}</channelcount>",
                  "\t\t\t\t\t\t\t\t</audio>"]
    lines += ["\t\t\t\t\t\t\t</media>", "\t\t\t\t\t\t</file>"]
    return "\n".join(lines)


def clipitem_xml(clip, idx, media_type, timebase, ntsc, first_use, seg,
                 seg_no=0, file_id=None):
    """Timeline'dagi bitta bo'lak.

    `seg` — {start, in, out} (freymlarda): klip timeline'ning qayeriga
    tushishi va manba faylning qaysi qismidan olinishi. Sinxronlashda bitta
    bo'lak bo'ladi, kesishda esa pauzalar olib tashlangani uchun bir nechta.
    """
    cid = f"clipitem-{media_type}-{idx}-{seg_no}"
    file_id = file_id or f"file-{idx}"
    length = seg["out"] - seg["in"]
    lines = [f'\t\t\t\t\t<clipitem id="{cid}">',
             f"\t\t\t\t\t\t<name>{escape(clip['name'])}</name>",
             "\t\t\t\t\t\t<enabled>TRUE</enabled>",
             f"\t\t\t\t\t\t<duration>{clip['dur_frames']}</duration>",
             rate_xml(timebase, ntsc, 6).replace(" " * 6, "\t" * 6),
             f"\t\t\t\t\t\t<start>{seg['start']}</start>",
             f"\t\t\t\t\t\t<end>{seg['start'] + length}</end>",
             f"\t\t\t\t\t\t<in>{seg['in']}</in>",
             f"\t\t\t\t\t\t<out>{seg['out']}</out>",
             file_xml(clip, file_id, timebase, ntsc, full=first_use)]
    if media_type == "audio":
        lines += ["\t\t\t\t\t\t<sourcetrack>",
                  "\t\t\t\t\t\t\t<mediatype>audio</mediatype>",
                  "\t\t\t\t\t\t\t<trackindex>1</trackindex>",
                  "\t\t\t\t\t\t</sourcetrack>"]
    lines.append("\t\t\t\t\t</clipitem>")
    return "\n".join(lines)


def build_xml(clips, seq_name, timebase, ntsc, width, height,
              single_video_track=False, markers=None, file_ids=None):
    """Sequence XML. Har klipda `segments` bo'lmasa — butun fayl bitta bo'lak.

    `single_video_track` — Switch uchun: hamma kamera bo'laklari bitta
    «programma» trekiga ketma-ket teriladi (ular vaqt bo'yicha kesishmaydi),
    audio esa har fayl uchun alohida trekda qoladi.

    `markers` — sequence markerlari: [{"frame": ..., "name": ...}]. Intro
    nomzodlarini ko'rib chiqishda har bo'lak nomi bilan belgilanadi.

    `file_ids` — {fayl yo'li: "file-N"}. Bitta XML'da bir nechta sequence
    bo'lganda (Shorts) fayl id'lari barqaror bo'lishi SHART: har sequence
    o'z tartibi bilan raqamlasa, ikkinchi sequence'ning «file-1» i boshqa
    faylga tegib, Premiere xato media ulab qo'yadi.
    """
    for clip in clips:
        if not clip.get("segments"):
            clip["segments"] = [{"start": clip["start_frame"], "in": 0,
                                 "out": clip["dur_frames"]}]

    total = max(s["start"] + (s["out"] - s["in"])
                for c in clips for s in c["segments"])

    video_tracks, audio_tracks, program = [], [], []
    for i, clip in enumerate(clips, start=1):
        segs = clip["segments"]
        # Ovoz manbasi videodan boshqacha bo'lishi mumkin: kamera almashsa ham
        # ovoz bitta yaxshi yozuvdan kelishi kerak, shuning uchun audio
        # bo'laklari alohida berilishi mumkin (`audio_segments`).
        asegs = clip.get("audio_segments", segs)
        show_video = clip["has_video"] and clip.get("emit_video", True) and segs
        play_audio = clip["has_audio"] and clip.get("emit_audio", True) and asegs

        # <file> to'liq tavsifi birinchi ishlatilgan joyda yoziladi.
        # file_ids berilgan bo'lsa — id yo'l bo'yicha, tartib bo'yicha emas.
        fid = (file_ids or {}).get(clip["path"])
        if show_video:
            items = [clipitem_xml(clip, i, "video", timebase, ntsc, n == 0, s, n,
                                  file_id=fid)
                     for n, s in enumerate(segs)]
            if single_video_track:
                program += [(s["start"], item) for s, item in zip(segs, items)]
            else:
                video_tracks.append("\t\t\t\t<track>\n" + "\n".join(items)
                                    + "\n\t\t\t\t</track>")
        if play_audio:
            items = [clipitem_xml(clip, i, "audio", timebase, ntsc,
                                  n == 0 and not show_video, s, n, file_id=fid)
                     for n, s in enumerate(asegs)]
            audio_tracks.append("\t\t\t\t<track>\n" + "\n".join(items)
                                + "\n\t\t\t\t</track>")

    if single_video_track and program:
        program.sort(key=lambda x: x[0])
        video_tracks = ["\t\t\t\t<track>\n"
                        + "\n".join(item for _, item in program)
                        + "\n\t\t\t\t</track>"]

    marker_xml = ""
    for mk in (markers or []):
        marker_xml += (f"\t\t<marker>\n"
                       f"\t\t\t<name>{escape(str(mk.get('name', '')))}</name>\n"
                       f"\t\t\t<comment>{escape(str(mk.get('comment', '')))}</comment>\n"
                       f"\t\t\t<in>{int(mk['frame'])}</in>\n"
                       f"\t\t\t<out>-1</out>\n"
                       f"\t\t</marker>\n")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE xmeml>
<xmeml version="4">
\t<sequence id="sequence-1">
\t\t<name>{escape(seq_name)}</name>
\t\t<duration>{total}</duration>
{rate_xml(timebase, ntsc, 2).replace("  ", chr(9) * 2, 1).replace(" " * 2, chr(9) * 2)}
\t\t<media>
\t\t\t<video>
\t\t\t\t<format>
\t\t\t\t\t<samplecharacteristics>
{rate_xml(timebase, ntsc, 6).replace(" " * 6, chr(9) * 6)}
\t\t\t\t\t\t<width>{width}</width>
\t\t\t\t\t\t<height>{height}</height>
\t\t\t\t\t\t<pixelaspectratio>square</pixelaspectratio>
\t\t\t\t\t</samplecharacteristics>
\t\t\t\t</format>
{chr(10).join(video_tracks)}
\t\t\t</video>
\t\t\t<audio>
{chr(10).join(audio_tracks)}
\t\t\t</audio>
\t\t</media>
\t\t<timecode>
{rate_xml(timebase, ntsc, 3).replace(" " * 3, chr(9) * 3)}
\t\t\t<string>00:00:00:00</string>
\t\t\t<frame>0</frame>
\t\t\t<displayformat>NDF</displayformat>
\t\t</timecode>
{marker_xml}\t</sequence>
</xmeml>
"""


# --------------------------------------------------------------------- main

def sequence_block(xml_doc):
    """To'liq XML'dan faqat <sequence>…</sequence> qismini ajratadi."""
    a = xml_doc.index("<sequence")
    b = xml_doc.index("</sequence>") + len("</sequence>")
    return xml_doc[a:b]


def wrap_project(project_name, sequence_blocks):
    """Bir nechta sequence'ni bitta XML'ga yig'adi (Premiere bin qilib oladi).

    Shorts moduli uchun: har bo'lak alohida sequence bo'lishi kerak, aks
    holda ularni alohida eksport qilib bo'lmaydi.
    """
    inner = "\n".join("\t\t" + b.replace("\n", "\n\t") for b in sequence_blocks)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            "<!DOCTYPE xmeml>\n"
            '<xmeml version="4">\n'
            "\t<project>\n"
            f"\t\t<name>{escape(project_name)}</name>\n"
            "\t\t<children>\n"
            f"{inner}\n"
            "\t\t</children>\n"
            "\t</project>\n"
            "</xmeml>\n")


# ------------------------------------------- kliplarni timeline'ga joylash
#
# Cut, Switch va Intro uchun bir xil ish: fayllarni o'qib, ularni umumiy
# timeline'ga joylashtirish. Ikki yo'l bor — Premiere'dagi tayyor sequence
# bo'yicha, yoki fayllarni o'zaro sinxronlab. Kod bir joyda turishi kerak:
# aks holda bitta modulda tuzatilgan xato boshqasida qolib ketadi.

def prepare_clips(files, timeline=None, log=print, progress=None):
    """Fayllar -> envelope + timeline'dagi joylashuv.

    Qaytadi: clips ro'yxati. Har birida `placements` bor:
    [{"start": timeline'dagi joyi, "in": fayl ichidagi boshi, "out": oxiri}].
    """
    say = progress or (lambda **k: None)
    clips = []
    for i, f in enumerate(files):
        say(stage="Ovoz tahlil qilinmoqda", percent=i / max(len(files), 1) * 100,
            detail=f"{i + 1}/{len(files)}: {os.path.basename(f)}")
        info = ffprobe(f)
        if not info["has_audio"]:
            # Audiosiz kamera. Ilgari butunlay tashlab yuborilardi va
            # natija «faqat ovoz» bo'lib chiqardi — buni foydalanuvchi
            # faqat Premiere'da ochganda bilardi.
            #
            # Tayyor sequence'dan ishlayotgan bo'lsak, klipning joyi
            # allaqachon ma'lum: tahlilga qo'shmaymiz (jim envelope),
            # lekin timeline'ga qo'yamiz. Fayllardan ishlayotganda esa
            # uni sinxronlash mumkin emas — qayerga qo'yishni bilmaymiz.
            if info["has_video"] and timeline:
                info["envelope"] = np.zeros(
                    max(1, int(round(info["duration"] * ENV_RATE))))
                info["ovozsiz"] = True
                clips.append(info)
                log(f"  {info['name']}: audio yo'q — tahlilga kirmaydi, "
                    "lekin kadr sifatida qoladi")
            else:
                log(f"  OGOHLANTIRISH: {info['name']} da audio yo'q — "
                    "o'tkazildi (sinxronlash uchun ovoz kerak). Tayyor "
                    "sequence'dan olsangiz, kadr saqlanadi.")
            continue
        info["envelope"] = extract_envelope(
            f, info["duration"], progress=sub_progress(say, i, len(files)))
        clips.append(info)
        log(f"  {info['name']}: {info['duration']:.1f}s")
    say(percent=100)
    if not clips:
        raise RuntimeError("Audioli fayl topilmadi.")

    if timeline:
        by_path = {c["path"]: c for c in clips}
        for c in clips:
            c["placements"] = []
            c["confidence"], c["reliable"] = None, True
        for item in timeline:
            clip = by_path.get(item["path"])
            if clip:
                clip["placements"].append(
                    {"start": float(item["start"]), "in": float(item["in"]),
                     "out": float(item["out"])})
        clips = [c for c in clips if c["placements"]]
        for c in clips:
            c["rel_offset"] = min(p["start"] - p["in"] for p in c["placements"])
        log(f"Sequence'dan {sum(len(c['placements']) for c in clips)} ta klip olindi")
        return clips

    say(stage="Sinxron hisoblanmoqda", percent=0)
    ref = max(clips, key=lambda c: len(c["envelope"]))
    for i, clip in enumerate(clips):
        say(percent=i / len(clips) * 100)
        if clip is ref or len(clips) == 1:
            clip["offset_sec"] = 0.0
            clip["confidence"], clip["reliable"] = None, True
            continue
        offset, conf = find_offset(ref["envelope"], clip["envelope"])
        clip["confidence"] = conf
        clip["reliable"] = conf >= MIN_CONFIDENCE
        clip["offset_sec"] = offset if clip["reliable"] else 0.0
        if not clip["reliable"]:
            log(f"  OGOHLANTIRISH: {clip['name']} — mos joy topilmadi "
                f"(ishonch {conf:.1f}x), boshiga qo'yildi")
    base = min(c["offset_sec"] for c in clips)
    for clip in clips:
        clip["rel_offset"] = clip["offset_sec"] - base
        clip["placements"] = [{"start": clip["rel_offset"], "in": 0.0,
                               "out": clip["duration"]}]
    return clips


def timeline_length(clips):
    """Joylashtirilgan kliplarning umumiy uzunligi (soniya)."""
    return max(p["start"] + (p["out"] - p["in"])
               for c in clips for p in c["placements"])


def cut_to_segments(clips, keeps, fps, log=print):
    """Saqlanadigan (boshi, oxiri) oraliqlarni klip segmentlariga aylantiradi.

    Butun hisob freymlarda ketadi: soniyalarni har bo'lakda alohida
    yumaloqlash kesiklar orasida bir freymli bo'shliq yoki ustma-ustlik
    qoldiradi, Premiere esa bunday sequence'ni buzuq deb qabul qiladi.
    """
    keeps_f, cursor_f = [], 0
    for a, b in keeps:
        a_f, b_f = int(round(a * fps)), int(round(b * fps))
        if b_f > a_f:
            keeps_f.append((a_f, b_f, cursor_f))
            cursor_f += b_f - a_f

    for clip in clips:
        clip["dur_frames"] = int(round(clip["duration"] * fps))
        clip["start_frame"] = int(round(clip["rel_offset"] * fps))
        clip["segments"] = []
        for place in clip["placements"]:
            p_start = int(round(place["start"] * fps))
            p_in = int(round(place["in"] * fps))
            p_out = int(round(place["out"] * fps))
            for a_f, b_f, tl_f in keeps_f:
                clip_a = max(a_f, p_start)
                clip_b = min(b_f, p_start + (p_out - p_in))
                if clip_b > clip_a:
                    src_in = p_in + (clip_a - p_start)
                    clip["segments"].append({
                        "start": tl_f + (clip_a - a_f),
                        "in": src_in,
                        "out": src_in + (clip_b - clip_a),
                    })
        if not clip["segments"]:
            log(f"  {clip['name']}: bu bo'laklarda ishlatilmadi")
    return [c for c in clips if c["segments"]]


def run_sync(files, output="synced.xml", name="AutoSync Sequence",
             minutes=None, fallback=None, log=print, progress=None):
    """To'liq sinxronlash oqimi: tahlil -> siljishlar -> XML.

    CLI ham, panel motori (server.py) ham shu funksiyani chaqiradi.
    `minutes` endi ishlatilmaydi — tahlil har doim to'liq fayl bo'yicha
    ketadi (eski chaqiruvlar buzilmasligi uchun parametr saqlab qolindi).
    Natija: JSON'ga tayyor dict (kliplar, siljishlar, XML yo'li).
    """
    say = progress or (lambda **k: None)
    log("Fayllar tahlil qilinmoqda...")
    clips = []
    for i, f in enumerate(files):
        say(stage="Ovoz tahlil qilinmoqda", percent=i / len(files) * 100,
            detail=f"{i + 1}/{len(files)}: {os.path.basename(f)}")
        info = ffprobe(f)
        if not info["has_audio"]:
            log(f"  OGOHLANTIRISH: {info['name']} da audio yo'q — o'tkazib yuborildi")
            continue
        info["envelope"] = extract_envelope(
            f, info["duration"], progress=sub_progress(say, i, len(files)))
        clips.append(info)
        kind = "video" if info["has_video"] else "audio"
        log(f"  {info['name']}: {info['duration']:.1f}s ({kind})")

    if len(clips) < 2:
        raise RuntimeError("Sinxronlash uchun audioli kamida 2 ta fayl kerak.")

    # Eng uzun yozuv — tayanch (reference)
    ref = max(clips, key=lambda c: len(c["envelope"]))
    log(f"Tayanch fayl: {ref['name']}")

    say(stage="Sinxron hisoblanmoqda", percent=0,
        detail=f"tayanch: {ref['name']}")
    for done, clip in enumerate(clips):
        say(percent=done / len(clips) * 100)
        if clip is ref:
            clip["offset_sec"], clip["confidence"] = 0.0, None
            clip["reliable"] = True
            continue
        offset, conf = find_offset(ref["envelope"], clip["envelope"])
        clip["confidence"] = conf
        clip["reliable"] = conf >= MIN_CONFIDENCE
        # Ishonchsiz natijani timeline'ga qo'yish — noto'g'ri joyga qo'yish
        # demak. Bunday fayl 0 nuqtada qoladi va aniq belgilanadi.
        clip["offset_sec"] = offset if clip["reliable"] else 0.0

    # Eng erta boshlangan fayl timeline'da 0 nuqtada tursin
    base = min(c["offset_sec"] for c in clips)

    # Sequence parametrlari — manbaning o'ziga qarab (vertikal/gorizontal)
    fmt = sequence_format(clips, log=log)
    fps, timebase, ntsc = fmt["fps"], fmt["timebase"], fmt["ntsc"]
    width, height = fmt["width"], fmt["height"]

    for clip in clips:
        rel = clip["offset_sec"] - base
        clip["rel_offset"] = rel
        clip["start_frame"] = int(round(rel * fps))
        clip["dur_frames"] = int(round(clip["duration"] * fps))
        if clip is ref:
            log(f"  {clip['name']}: +{rel:.3f}s (tayanch)")
        elif clip["reliable"]:
            log(f"  {clip['name']}: +{rel:.3f}s (ishonch {clip['confidence']:.1f}x)")
        else:
            log(f"  OGOHLANTIRISH: {clip['name']} — mos joy topilmadi "
                f"(ishonch {clip['confidence']:.1f}x). Boshiga qo'yildi, "
                "qo'lda tekshiring: boshqa yozuvdan bo'lishi mumkin.")

    say(stage="Timeline yozilmoqda", percent=50, detail=os.path.basename(output))
    xml = build_xml(clips, name, timebase, ntsc, width, height)
    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    log(f"Tayyor: {output}")

    return {
        "output": output,
        "sequence": {"name": name, "timebase": timebase, "ntsc": ntsc,
                     "width": width, "height": height},
        "clips": [{
            "name": c["name"], "path": c["path"],
            "duration": c["duration"],
            "offset_sec": round(c["rel_offset"], 4),
            "confidence": None if c["confidence"] is None
                          else round(c["confidence"], 1),
            "reliable": c["reliable"],
            "is_reference": c is ref,
            "has_video": c["has_video"],
        } for c in clips],
    }


def main():
    ap = argparse.ArgumentParser(
        description="Multicam/podcast fayllarini audio orqali sinxronlab, "
                    "Premiere Pro uchun XML sequence yasaydi.")
    ap.add_argument("files", nargs="+", help="Video/audio fayllar (2 ta va undan ko'p)")
    ap.add_argument("-o", "--output", default="synced.xml", help="Natija XML fayli")
    ap.add_argument("--name", default="AutoSync Sequence", help="Sequence nomi")
    ap.add_argument("--minutes", type=float, default=20,
                    help="Tahlil uchun boshidan necha minut olinadi (0 = to'liq)")
    args = ap.parse_args()

    if len(args.files) < 2:
        ap.error("Kamida 2 ta fayl kerak")
    try:
        run_sync(args.files, output=args.output, name=args.name,
                 minutes=args.minutes)
    except RuntimeError as e:
        sys.exit(str(e))
    print("Premiere Pro'da: File > Import > shu XML faylni tanlang.")


if __name__ == "__main__":
    main()

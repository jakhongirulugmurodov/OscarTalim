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

ANALYSIS_SR = 8000  # audio tahlil uchun namuna chastotasi (past = tez, yetarli aniq)


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

def ffprobe(path):
    """Fayl haqida ma'lumot: davomiylik, fps, o'lcham, audio bor-yo'qligi."""
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

    info = {
        "path": os.path.abspath(path),
        "name": os.path.basename(path),
        "duration": float(data["format"]["duration"]),
        "has_video": False,
        "has_audio": False,
        "fps": None,
        "width": None,
        "height": None,
        "audio_rate": 48000,
        "audio_channels": 2,
    }
    for s in data["streams"]:
        if s["codec_type"] == "video" and not info["has_video"]:
            num, _, den = s.get("avg_frame_rate", "0/1").partition("/")
            if float(den or 1) > 0 and float(num) > 0:
                info["fps"] = float(num) / float(den or 1)
            info["has_video"] = True
            info["width"] = s.get("width")
            info["height"] = s.get("height")
        elif s["codec_type"] == "audio" and not info["has_audio"]:
            info["has_audio"] = True
            info["audio_rate"] = int(s.get("sample_rate", 48000))
            info["audio_channels"] = int(s.get("channels", 2))
    return info


def extract_audio(path, max_seconds):
    """Audioni mono float32 ko'rinishida o'qib olish (tahlil uchun)."""
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)
    cmd = [FFMPEG, "-v", "error", "-i", path]
    if max_seconds:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-map", "a:0", "-ac", "1", "-ar", str(ANALYSIS_SR), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffmpeg xatosi ({path}): {out.stderr.decode().strip()}")
    audio = np.frombuffer(out.stdout, dtype=np.float32).astype(np.float64)
    if audio.size == 0:
        raise RuntimeError(f"{path}: audio o'qib bo'lmadi")
    audio -= audio.mean()
    peak = np.abs(audio).max()
    if peak > 0:
        audio /= peak
    return audio


# ------------------------------------------------------------- offset topish

def find_offset(ref, sig):
    """sig yozuvi ref'dan necha soniya KEYIN boshlanganini topadi.

    FFT orqali kross-korrelyatsiya: ref[t] ~ sig[t - lag] bo'lgan lag topiladi.
    Musbat natija = sig keyinroq boshlangan. Qaytadi: (soniya, ishonch).
    """
    n = len(ref) + len(sig) - 1
    nfft = 1 << (n - 1).bit_length()
    R = np.fft.rfft(ref, nfft)
    S = np.fft.rfft(sig, nfft)
    corr = np.fft.irfft(R * np.conj(S), nfft)

    peak_idx = int(np.argmax(corr))
    lag = peak_idx if peak_idx <= nfft // 2 else peak_idx - nfft

    peak = corr[peak_idx]
    noise = np.median(np.abs(corr)) + 1e-12
    confidence = float(peak / noise)
    return lag / ANALYSIS_SR, confidence


# ----------------------------------------------------------- XML generatsiya

def fps_to_timebase(fps):
    """29.97 -> (30, TRUE); 25 -> (25, FALSE) va h.k."""
    if fps is None:
        return 25, "FALSE"
    for real, base in ((23.976, 24), (29.97, 30), (59.94, 60)):
        if abs(fps - real) < 0.01:
            return base, "TRUE"
    return int(round(fps)), "FALSE"


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


def clipitem_xml(clip, idx, media_type, timebase, ntsc, first_use):
    cid = f"clipitem-{media_type}-{idx}"
    file_id = f"file-{idx}"
    lines = [f'\t\t\t\t\t<clipitem id="{cid}">',
             f"\t\t\t\t\t\t<name>{escape(clip['name'])}</name>",
             "\t\t\t\t\t\t<enabled>TRUE</enabled>",
             f"\t\t\t\t\t\t<duration>{clip['dur_frames']}</duration>",
             rate_xml(timebase, ntsc, 6).replace(" " * 6, "\t" * 6),
             f"\t\t\t\t\t\t<start>{clip['start_frame']}</start>",
             f"\t\t\t\t\t\t<end>{clip['start_frame'] + clip['dur_frames']}</end>",
             "\t\t\t\t\t\t<in>0</in>",
             f"\t\t\t\t\t\t<out>{clip['dur_frames']}</out>",
             file_xml(clip, file_id, timebase, ntsc, full=first_use)]
    if media_type == "audio":
        lines += ["\t\t\t\t\t\t<sourcetrack>",
                  "\t\t\t\t\t\t\t<mediatype>audio</mediatype>",
                  "\t\t\t\t\t\t\t<trackindex>1</trackindex>",
                  "\t\t\t\t\t\t</sourcetrack>"]
    lines.append("\t\t\t\t\t</clipitem>")
    return "\n".join(lines)


def build_xml(clips, seq_name, timebase, ntsc, width, height):
    total = max(c["start_frame"] + c["dur_frames"] for c in clips)

    video_tracks, audio_tracks = [], []
    for i, clip in enumerate(clips, start=1):
        # <file> to'liq tavsifi birinchi ishlatilgan joyda yoziladi
        if clip["has_video"]:
            video_tracks.append(
                "\t\t\t\t<track>\n"
                + clipitem_xml(clip, i, "video", timebase, ntsc, True)
                + "\n\t\t\t\t</track>")
        if clip["has_audio"]:
            audio_tracks.append(
                "\t\t\t\t<track>\n"
                + clipitem_xml(clip, i, "audio", timebase, ntsc,
                               not clip["has_video"])
                + "\n\t\t\t\t</track>")

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
\t</sequence>
</xmeml>
"""


# --------------------------------------------------------------------- main

def run_sync(files, output="synced.xml", name="AutoSync Sequence",
             minutes=20.0, log=print):
    """To'liq sinxronlash oqimi: tahlil -> siljishlar -> XML.

    CLI ham, panel motori (server.py) ham shu funksiyani chaqiradi.
    Natija: JSON'ga tayyor dict (kliplar, siljishlar, XML yo'li).
    """
    max_sec = minutes * 60 if minutes and minutes > 0 else None

    log("Fayllar tahlil qilinmoqda...")
    clips = []
    for f in files:
        info = ffprobe(f)
        if not info["has_audio"]:
            log(f"  OGOHLANTIRISH: {info['name']} da audio yo'q — o'tkazib yuborildi")
            continue
        info["analysis_audio"] = extract_audio(f, max_sec)
        clips.append(info)
        kind = "video" if info["has_video"] else "audio"
        log(f"  {info['name']}: {info['duration']:.1f}s ({kind})")

    if len(clips) < 2:
        raise RuntimeError("Sinxronlash uchun audioli kamida 2 ta fayl kerak.")

    # Eng uzun audio — tayanch (reference)
    ref = max(clips, key=lambda c: len(c["analysis_audio"]))
    log(f"Tayanch fayl: {ref['name']}")

    for clip in clips:
        if clip is ref:
            clip["offset_sec"], clip["confidence"] = 0.0, None
            continue
        clip["offset_sec"], clip["confidence"] = find_offset(
            ref["analysis_audio"], clip["analysis_audio"])

    # Eng erta boshlangan fayl timeline'da 0 nuqtada tursin
    base = min(c["offset_sec"] for c in clips)

    # Sequence parametrlari — videoli tayanchdan, bo'lmasa birinchi videodan
    video_clip = next((c for c in [ref] + clips if c["has_video"]), None)
    fps = video_clip["fps"] if video_clip else 25.0
    timebase, ntsc = fps_to_timebase(fps)
    width = video_clip["width"] if video_clip else 1920
    height = video_clip["height"] if video_clip else 1080
    log(f"Sequence: {timebase}fps (ntsc={ntsc}), {width}x{height}")

    for clip in clips:
        rel = clip["offset_sec"] - base
        clip["rel_offset"] = rel
        clip["start_frame"] = int(round(rel * fps))
        clip["dur_frames"] = int(round(clip["duration"] * fps))
        conf = "tayanch" if clip is ref else f"{clip['confidence']:.0f}x"
        log(f"  {clip['name']}: +{rel:.3f}s ({conf})")
        if clip is not ref and clip["confidence"] < 15:
            log(f"  OGOHLANTIRISH: {clip['name']} ishonch past — "
                "audio bir-biriga o'xshamasligi mumkin, natijani tekshiring")

    xml = build_xml(clips, name, timebase, ntsc, width, height)
    output = os.path.abspath(output)
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(xml)
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

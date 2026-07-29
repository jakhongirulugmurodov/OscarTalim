#!/usr/bin/env python3
"""Cut — podcastdagi pauzalarni topib, kesilgan sequence yasaydi.

Foydalanish (terminaldan):
    python3 cut.py cam1.mp4 cam2.mp4 recorder.wav -o kesilgan.xml

Mantiq: fayllar avval Sync moduli bilan bir-biriga moslanadi, so'ng umumiy
timeline bo'yicha HAMMA mikrofon bir vaqtda jim bo'lgan joylar qidiriladi.
Bittasi gapirayotgan bo'lsa — bu pauza emas. Topilgan pauzalar olib
tashlanib, qolgan bo'laklar ketma-ket ulanadi; hamma trek bir xil kesilgani
uchun sinxronlik saqlanadi.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (ENV_RATE, build_xml, extract_envelope, ffprobe,
                      find_offset, fps_to_timebase, MIN_CONFIDENCE)

# Standart sozlamalar — panel ularni o'zgartira oladi
DEFAULT_THRESHOLD = 0.18   # jimlik chegarasi (0..1, normallashtirilgan energiya)
DEFAULT_MIN_PAUSE = 0.7    # shundan qisqa pauzalar tegilmaydi (soniya)
DEFAULT_PADDING = 0.12     # gap chetlaridan qoldiriladigan zaxira (soniya)


def speech_mask(clips, total_bins, threshold):
    """Har bin uchun: shu lahzada kimdir gapiryaptimi?

    Har fayl o'z siljishi bilan umumiy timeline'ga joylashtiriladi va
    energiyalarning eng kattasi olinadi — ya'ni bittasi gapirsa yetarli.
    """
    loudest = np.zeros(total_bins)
    for clip in clips:
        env = clip["envelope"]
        # envelope log-normallashtirilgan; 0..1 oralig'iga keltiramiz
        e = env - env.min()
        peak = np.percentile(e, 99) or 1.0
        e = np.clip(e / peak, 0, 1)

        start = int(round(clip["rel_offset"] * ENV_RATE))
        end = min(total_bins, start + len(e))
        if end > start:
            loudest[start:end] = np.maximum(loudest[start:end], e[:end - start])
    return loudest >= threshold


def find_pauses(mask, min_pause, padding):
    """Jim bo'lgan uzun oraliqlar → kesiladigan bo'laklar ro'yxati.

    Chetlariga `padding` qoldiriladi: gapning boshi va oxiri kesilib
    ketmasin, montaj tabiiy eshitilsin.
    """
    pad_bins = int(round(padding * ENV_RATE))
    min_bins = int(round(min_pause * ENV_RATE))

    pauses = []
    silent = ~mask
    idx = 0
    n = len(mask)
    while idx < n:
        if not silent[idx]:
            idx += 1
            continue
        start = idx
        while idx < n and silent[idx]:
            idx += 1
        end = idx
        # chetlarni bo'shatamiz
        start += pad_bins
        end -= pad_bins
        if end - start >= min_bins:
            pauses.append((start / ENV_RATE, end / ENV_RATE))
    return pauses


def keep_segments(pauses, total_sec):
    """Pauzalar orasidagi saqlanadigan bo'laklar."""
    keeps, cursor = [], 0.0
    for a, b in pauses:
        if a > cursor:
            keeps.append((cursor, a))
        cursor = b
    if cursor < total_sec:
        keeps.append((cursor, total_sec))
    return keeps


def run_cut(files, output="kesilgan.xml", name="Podcast Suite — Cut",
            threshold=DEFAULT_THRESHOLD, min_pause=DEFAULT_MIN_PAUSE,
            padding=DEFAULT_PADDING, log=print):
    """Sinxronlash + pauzalarni kesish. Natija: JSON'ga tayyor dict."""
    log("Fayllar tahlil qilinmoqda...")
    clips = []
    for f in files:
        info = ffprobe(f)
        if not info["has_audio"]:
            log(f"  OGOHLANTIRISH: {info['name']} da audio yo'q — o'tkazildi")
            continue
        info["envelope"] = extract_envelope(f)
        clips.append(info)
        log(f"  {info['name']}: {info['duration']:.1f}s")

    if not clips:
        raise RuntimeError("Audioli fayl topilmadi.")

    # --- 1. Sinxronlash (bitta fayl bo'lsa — shart emas) ---
    ref = max(clips, key=lambda c: len(c["envelope"]))
    for clip in clips:
        if clip is ref or len(clips) == 1:
            clip["offset_sec"], clip["confidence"], clip["reliable"] = 0.0, None, True
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

    total_sec = max(c["rel_offset"] + c["duration"] for c in clips)
    total_bins = int(round(total_sec * ENV_RATE)) + 1

    # --- 2. Pauzalarni topish ---
    mask = speech_mask(clips, total_bins, threshold)
    pauses = find_pauses(mask, min_pause, padding)
    saved = sum(b - a for a, b in pauses)
    log(f"Pauzalar: {len(pauses)} ta, jami {saved:.1f}s "
        f"({saved / total_sec * 100:.0f}%) qisqaradi")

    keeps = keep_segments(pauses, total_sec)
    if not keeps:
        raise RuntimeError("Kesishdan keyin hech narsa qolmadi — "
                           "jimlik chegarasini pasaytiring.")

    # --- 3. Sequence parametrlari ---
    video_clip = next((c for c in clips if c["has_video"]), None)
    fps = video_clip["fps"] if video_clip else 25.0
    timebase, ntsc = fps_to_timebase(fps)
    width = video_clip["width"] if video_clip else 1920
    height = video_clip["height"] if video_clip else 1080

    # --- 4. Har klipni saqlanadigan bo'laklarga bo'lamiz ---
    # Butun hisob freymlarda ketadi: soniyalarni har bo'lakda alohida
    # yumaloqlash kesiklar orasida bir freymli bo'shliq/ustma-ustlik
    # qoldiradi, Premiere esa bunday sequence'ni buzuq deb qabul qiladi.
    keeps_f, cursor_f = [], 0
    for a, b in keeps:
        a_f, b_f = int(round(a * fps)), int(round(b * fps))
        if b_f > a_f:
            keeps_f.append((a_f, b_f, cursor_f))
            cursor_f += b_f - a_f

    for clip in clips:
        clip["dur_frames"] = int(round(clip["duration"] * fps))
        clip["start_frame"] = int(round(clip["rel_offset"] * fps))
        off_f = clip["start_frame"]
        clip["segments"] = []
        for a_f, b_f, tl_f in keeps_f:
            # bo'lakning shu klipga tegishli qismi
            clip_a = max(a_f, off_f)
            clip_b = min(b_f, off_f + clip["dur_frames"])
            if clip_b > clip_a:
                src_in = clip_a - off_f
                clip["segments"].append({
                    "start": tl_f + (clip_a - a_f),
                    "in": src_in,
                    "out": src_in + (clip_b - clip_a),
                })
        if not clip["segments"]:
            log(f"  {clip['name']}: butunlay kesildi — o'tkazib yuborildi")

    clips = [c for c in clips if c["segments"]]
    if not clips:
        raise RuntimeError("Kesishdan keyin klip qolmadi.")

    xml = build_xml(clips, name, timebase, ntsc, width, height)
    output = os.path.abspath(output)
    with open(output, "w", encoding="utf-8") as fh:
        fh.write(xml)
    log(f"Tayyor: {output}")

    return {
        "output": output,
        "pauses": [{"start": round(a, 3), "end": round(b, 3),
                    "length": round(b - a, 3)} for a, b in pauses],
        "total_sec": round(total_sec, 2),
        "saved_sec": round(saved, 2),
        "new_length_sec": round(total_sec - saved, 2),
        "clips": [{"name": c["name"], "path": c["path"],
                   "segments": len(c["segments"]),
                   "offset_sec": round(c["rel_offset"], 4),
                   "reliable": c["reliable"]} for c in clips],
    }


def main():
    ap = argparse.ArgumentParser(
        description="Podcastdagi pauzalarni kesib, yangi sequence yasaydi.")
    ap.add_argument("files", nargs="+", help="Video/audio fayllar")
    ap.add_argument("-o", "--output", default="kesilgan.xml")
    ap.add_argument("--name", default="Podcast Suite — Cut")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help="jimlik chegarasi 0..1 (kichik = kamroq kesadi)")
    ap.add_argument("--min-pause", type=float, default=DEFAULT_MIN_PAUSE,
                    help="shundan qisqa pauzalarga tegilmaydi (soniya)")
    ap.add_argument("--padding", type=float, default=DEFAULT_PADDING,
                    help="gap chetlarida qoldiriladigan zaxira (soniya)")
    args = ap.parse_args()

    try:
        r = run_cut(args.files, output=args.output, name=args.name,
                    threshold=args.threshold, min_pause=args.min_pause,
                    padding=args.padding)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"{r['total_sec']:.0f}s → {r['new_length_sec']:.0f}s")
    print("Premiere Pro'da: File > Import > shu XML faylni tanlang.")


if __name__ == "__main__":
    main()

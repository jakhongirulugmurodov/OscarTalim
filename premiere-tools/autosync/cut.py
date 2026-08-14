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
from autosync import (ENV_RATE, build_xml, cut_to_segments, fps_to_timebase,
                      level_range, otsu_split, prepare_clips, sequence_format,
                      timeline_length, write_xml)

# Standart sozlamalar — panel ularni o'zgartira oladi
DEFAULT_THRESHOLD = "auto"  # chegara yozuvning o'zidan olinadi (pastga qarang)
MANUAL_THRESHOLD = 0.18     # «auto» ishlamasa ishlatiladigan eski qiymat
DEFAULT_MIN_PAUSE = 0.7    # shundan qisqa pauzalar tegilmaydi (soniya)
DEFAULT_PADDING = 0.12     # gap chetlaridan qoldiriladigan zaxira (soniya)


# Qat'iylik: chegarani jimlik tomonga yoki gap tomonga suradi.
# «qattiq» — faqat baland, aniq gap qoladi; past tondagi ovozlar kesiladi.
STRICTNESS = {"yumshoq": 0.7, "orta": 1.0, "qattiq": 1.45}
DEFAULT_STRICTNESS = "orta"


def loudness_lane(clips, total_bins):
    """Timeline bo'ylab eng baland ovoz darajasi (0..1).

    Har klip timeline'dagi o'z joyiga qo'yiladi va energiyalarning eng
    kattasi olinadi — ya'ni bittasi gapirsa, bu pauza emas. Timeline'da
    klip bir necha marta turgan bo'lsa (montaj bo'lingan bo'lsa), har
    bo'lagi alohida hisobga olinadi.
    """
    loudest = np.zeros(total_bins)
    for clip in clips:
        env = clip["envelope"]
        # envelope log-normallashtirilgan; 0..1 oralig'iga keltiramiz.
        # Tayanch sifatida eng past NAMUNA emas, past FOIZ olinadi: bir
        # soatlik yozuvda eng past nuqta tasodifiy chetlashish bo'ladi va
        # butun shkalani surib yuboradi.
        e = env - np.percentile(env, 2)
        peak = np.percentile(e, 99) or 1.0
        e = np.clip(e / peak, 0, 1)

        for place in clip["placements"]:
            src_a = int(round(place["in"] * ENV_RATE))
            src_b = min(len(e), int(round(place["out"] * ENV_RATE)))
            start = int(round(place["start"] * ENV_RATE))
            piece = e[src_a:src_b]
            end = min(total_bins, start + len(piece))
            if end > start:
                loudest[start:end] = np.maximum(loudest[start:end],
                                                piece[:end - start])
    return loudest


def auto_threshold(loud, strictness=DEFAULT_STRICTNESS, log=print):
    """Jimlik chegarasini yozuvning O'ZIGA qarab tanlaydi.

    Nega kerak: qat'iy 0.18 har yozuvga to'g'ri kelmaydi. Mikrofon yaqin
    turgan, xonasi jim yozuvda u juda past qolib ketadi — past tondagi
    shovqin, nafas, stul g'ichirlashi ham «gap» deb hisoblanadi va
    kesilmay qoladi. Aynan siz aytgan muammo shu.

    Ish tartibi:
      1. Yozuvning o'z shovqin darajasi (past foiz) va gap darajasi
         (yuqori foiz) o'lchanadi;
      2. Ular orasidagi eng chuqur vodiy Otsu bilan topiladi;
      3. Natija shu ikki daraja orasida ushlab turiladi — na juda past,
         na hamma gapni yeb qo'yadigan darajada baland;
      4. Qat'iylik chegarani shu oraliqda suradi: «qattiq» — gap tomonga,
         ya'ni faqat baland, aniq gapirilgan joylar qoladi.
    """
    floor, speech = level_range(loud)          # shovqin va gap darajalari
    span = speech - floor
    if span < 0.02:
        # Daraja bir tekis — ajratadigan narsa yo'q (doimiy shovqin/musiqa)
        log(f"  chegara: {MANUAL_THRESHOLD:.2f} (daraja bir tekis, "
            "avtomatik tanlab bo'lmadi)")
        return MANUAL_THRESHOLD

    t = otsu_split(loud)
    if t is None:
        t = floor + 0.35 * span
    # Vodiy tasodifan chetga tushib qolmasin
    t = min(max(t, floor + 0.12 * span), floor + 0.75 * span)

    frac = (t - floor) / span
    frac = min(0.90, max(0.08, frac * STRICTNESS.get(strictness, 1.0)))
    thr = floor + frac * span
    log(f"  chegara: {thr:.2f} (avtomatik — shovqin {floor:.2f}, "
        f"gap {speech:.2f}, qat'iylik «{strictness}»)")
    return thr


def resolve_threshold(loud, threshold, strictness=DEFAULT_STRICTNESS,
                      log=print):
    """Berilgan chegarani sonli qiymatga aylantiradi.

    `threshold` "auto"/bo'sh bo'lsa — yozuvdan hisoblanadi; son bo'lsa
    qo'lda kiritilgan qiymat aynan ishlatiladi (eski xatti-harakat).
    """
    if threshold is None or (isinstance(threshold, str)
                             and threshold.strip().lower() in ("", "auto")):
        return auto_threshold(loud, strictness, log=log)
    try:
        return float(threshold)
    except (TypeError, ValueError):
        return auto_threshold(loud, strictness, log=log)


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
            padding=DEFAULT_PADDING, strictness=DEFAULT_STRICTNESS,
            timeline=None, seq_format=None, fallback=None, log=print,
            progress=None, xml_yozish=True):
    """Pauzalarni kesish.

    Ikki rejim bor:
      * `timeline` berilsa — Premiere'dagi tayyor sequence'ning joylashuvi
        ishlatiladi (qayta sinxronlamaymiz, sizning montajingizga tegmaymiz);
      * berilmasa — fayllar avval o'zaro sinxronlanadi, keyin kesiladi.
    """
    from_timeline = bool(timeline)
    if from_timeline:
        files = list(dict.fromkeys(c["path"] for c in timeline))

    say = progress or (lambda **k: None)
    log("Fayllar tahlil qilinmoqda...")
    clips = prepare_clips(files, timeline, log=log, progress=say)

    total_sec = timeline_length(clips)
    total_bins = int(round(total_sec * ENV_RATE)) + 1

    # --- 2. Pauzalarni topish ---
    say(stage="Pauzalar qidirilmoqda", percent=None,
        detail=f"{total_sec / 60:.0f} daqiqalik montaj")
    loud = loudness_lane(clips, total_bins)
    threshold = resolve_threshold(loud, threshold, strictness, log=log)
    pauses = find_pauses(loud >= threshold, min_pause, padding)
    saved = sum(b - a for a, b in pauses)
    log(f"Pauzalar: {len(pauses)} ta, jami {saved:.1f}s "
        f"({saved / total_sec * 100:.0f}%) qisqaradi")

    keeps = keep_segments(pauses, total_sec)
    if not keeps:
        raise RuntimeError("Kesishdan keyin hech narsa qolmadi — "
                           "jimlik chegarasini pasaytiring.")

    # --- 3. Sequence parametrlari (o'lcham manbadan avtomatik olinadi) ---
    fmt = sequence_format(clips, log=log,
                          prefer=seq_format if from_timeline else None)
    fps, timebase, ntsc = fmt["fps"], fmt["timebase"], fmt["ntsc"]
    width, height = fmt["width"], fmt["height"]

    # --- 4. Har klipni saqlanadigan bo'laklarga bo'lamiz ---
    # Butun hisob freymlarda ketadi: soniyalarni har bo'lakda alohida
    # yumaloqlash kesiklar orasida bir freymli bo'shliq/ustma-ustlik
    # qoldiradi, Premiere esa bunday sequence'ni buzuq deb qabul qiladi.
    clips = cut_to_segments(clips, keeps, fps, log)
    if not clips:
        raise RuntimeError("Kesishdan keyin klip qolmadi.")

    if xml_yozish:
        say(stage="Timeline yozilmoqda", percent=50)
        # Montaj tayyor sequence'dan olingan bo'lsa, kadrlar qaysi qavatda
        # turgan bo'lsa o'sha yerda qolsin. Fayllar qo'lda tanlangan bo'lsa
        # qavat tushunchasi yo'q — eski yo'l qoladi.
        xml = build_xml(clips, name, timebase, ntsc, width, height,
                        keep_tracks=bool(timeline))
        output = write_xml(xml, output, fallback, log)
        log(f"Tayyor: {output}")
    else:
        # Panel montajning O'ZINI qirqadi — XML kerak emas. Uni baribir
        # yozsak, har ishga tushganda loyihaga keraksiz fayl qo'shiladi
        # va Project panelida dublikatlar to'planib boradi.
        output = None
        log(f"{len(pauses)} pauza topildi — montajning o'zi qirqiladi")
    say(percent=100, detail="tayyor")

    return {
        "output": output,
        "pauses": [{"start": round(a, 3), "end": round(b, 3),
                    "length": round(b - a, 3)} for a, b in pauses],
        "total_sec": round(total_sec, 2),
        "saved_sec": round(saved, 2),
        "threshold": round(float(threshold), 3),
        "strictness": strictness,
        "format": {"width": width, "height": height,
                   "shape": "vertikal" if height > width else
                            ("kvadrat" if height == width else "gorizontal"),
                   "fps": round(float(fps), 3), "mixed": fmt["mixed"]},
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
    ap.add_argument("--threshold", default=DEFAULT_THRESHOLD,
                    help="jimlik chegarasi 0..1, yoki «auto» (standart)")
    ap.add_argument("--strictness", default=DEFAULT_STRICTNESS,
                    choices=sorted(STRICTNESS),
                    help="«auto» chegarasi qanchalik qattiq bo'lsin")
    ap.add_argument("--min-pause", type=float, default=DEFAULT_MIN_PAUSE,
                    help="shundan qisqa pauzalarga tegilmaydi (soniya)")
    ap.add_argument("--padding", type=float, default=DEFAULT_PADDING,
                    help="gap chetlarida qoldiriladigan zaxira (soniya)")
    args = ap.parse_args()

    try:
        r = run_cut(args.files, output=args.output, name=args.name,
                    threshold=args.threshold, min_pause=args.min_pause,
                    padding=args.padding, strictness=args.strictness)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"{r['total_sec']:.0f}s → {r['new_length_sec']:.0f}s")
    print("Premiere Pro'da: File > Import > shu XML faylni tanlang.")


if __name__ == "__main__":
    main()

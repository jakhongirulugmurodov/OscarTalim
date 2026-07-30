#!/usr/bin/env python3
"""Vaqtlar — ro'yxat bo'yicha kadrlarni qirqib, alohida sequence qiladi.

Foydalanish (terminaldan):
    python3 ranges.py yozuv.mp4 -t "1:30-1:44, 2:39-2:45, 1:02:30-1:02:31"
    python3 ranges.py yozuv.mp4 -f vaqtlar.txt --bitta

Bu modulda hech qanday taxmin yo'q: qaysi kadrlar kerakligini siz aytasiz,
modul faqat qirqadi. Shuning uchun u tez ishlaydi — ovoz tahlil qilinmaydi,
faqat fayl ma'lumoti o'qiladi.

Vaqtlar montaj (sequence) vaqtida tushuniladi — ya'ni Premiere'da ko'rib
turgan raqamlaringiz. Ochiq sequence berilsa, modul ularni har klipning o'z
faylidagi joyiga o'zi ko'chiradi.

Qabul qilinadigan yozuvlar (aralash bo'lsa ham):
    1:30 - 1:44        mm:ss
    4:18- 4:21         bo'shliqsiz
    1:02:30 - 1:02:31  h:mm:ss
    90-104             soniyalar
    00:01:30;12        Premiere timecode (freym ; bilan) — freym tashlanadi
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (build_xml, cut_to_segments, ffprobe, fps_to_timebase,
                      sequence_block, timeline_length, wrap_project, write_xml)

# «1:30 - 1:44» dan «1:02:30–1:02:31» gacha: ajratgich tire, en-dash, «to»
SEP = r"(?:\s*(?:-|–|—|to|\.\.)\s*)"
TIME = r"\d{1,2}(?::\d{1,2}){0,2}(?:[.,]\d+)?(?:;\d+)?"
PAIR = re.compile(rf"({TIME}){SEP}({TIME})")


def to_seconds(text):
    """«1:02:30» → 3750.0 · «4:21» → 261.0 · «90» → 90.0

    Ikki bo'lak — daqiqa:soniya, uch bo'lak — soat:daqiqa:soniya. Premiere
    timecode'idagi freym (`;12` yoki oxirgi `:12`) ataylab tashlanadi:
    ro'yxat qo'lda yozilganda freym aniqligi baribir bo'lmaydi.
    """
    t = text.strip().replace(",", ".")
    t = t.split(";")[0]                      # 00:01:30;12 → 00:01:30
    parts = t.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 1:
        return nums[0]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] * 3600 + nums[1] * 60 + nums[2]


def parse_ranges(text):
    """Matndan oraliqlarni ajratadi. Qaytadi: [{start, end, raw}]."""
    out = []
    for m in PAIR.finditer(text or ""):
        a, b = to_seconds(m.group(1)), to_seconds(m.group(2))
        if a is None or b is None:
            continue
        if b <= a:                            # teskari yozilgan bo'lsa — almashtiramiz
            a, b = b, a
        if b - a <= 0:
            continue
        out.append({"start": round(a, 3), "end": round(b, 3),
                    "raw": m.group(0).strip()})
    out.sort(key=lambda r: r["start"])
    return out


def tc(sec):
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run_ranges(files, ranges, timeline=None, split=True, pad=0.0,
               output="kadrlar.xml", prefix="Kadr", name="Podcast Suite — Kadrlar",
               fallback=None, log=print, progress=None):
    """Berilgan oraliqlarni qirqib, sequence(lar) yasaydi.

    split=True  — har oraliq alohida sequence (alohida eksport uchun)
    split=False — hammasi bitta sequence'da, ketma-ket (ko'rib chiqish uchun)
    """
    say = progress or (lambda **k: None)
    if not ranges:
        raise RuntimeError("Vaqtlar ro'yxati bo'sh.")
    if timeline:
        files = list(dict.fromkeys(c["path"] for c in timeline))
    if not files:
        raise RuntimeError("Fayl berilmadi.")

    say(stage="Fayllar o'qilmoqda", percent=None)
    base = []
    for i, path in enumerate(files):
        say(percent=i / max(len(files), 1) * 100,
            detail=f"{i + 1}/{len(files)}: {os.path.basename(path)}")
        info = ffprobe(path)
        info["confidence"], info["reliable"] = None, True
        if timeline:
            info["placements"] = [
                {"start": float(c["start"]), "in": float(c["in"]),
                 "out": float(c["out"])}
                for c in timeline if c["path"] == info["path"]]
            if not info["placements"]:
                continue
            info["rel_offset"] = min(p["start"] - p["in"]
                                     for p in info["placements"])
        else:
            # Sequence berilmasa: fayllar noldan boshlanadi deb olamiz
            info["placements"] = [{"start": 0.0, "in": 0.0,
                                   "out": info["duration"]}]
            info["rel_offset"] = 0.0
        base.append(info)
    if not base:
        raise RuntimeError("Fayllar sequence bilan mos kelmadi.")

    total_sec = timeline_length(base)
    video_clip = next((c for c in base if c["has_video"]), None)
    fps = video_clip["fps"] if video_clip else 25.0
    timebase, ntsc = fps_to_timebase(fps)
    width = video_clip["width"] if video_clip else 1920
    height = video_clip["height"] if video_clip else 1080
    file_ids = {c["path"]: f"file-{i}" for i, c in enumerate(base, start=1)}

    # Oraliqlarni tekshiramiz: montaj tashqarisiga chiqib ketganini aytamiz
    good, skipped = [], []
    for r in ranges:
        a = max(0.0, float(r["start"]) - pad)
        b = min(total_sec, float(r["end"]) + pad)
        if b - a < 0.04 or a >= total_sec:      # bir freymdan qisqa yoki tashqarida
            skipped.append(r)
            continue
        good.append({**r, "cut_start": round(a, 3), "cut_end": round(b, 3)})
    if skipped:
        log(f"OGOHLANTIRISH: {len(skipped)} oraliq montajdan tashqarida "
            f"(montaj uzunligi {tc(total_sec)}): "
            + ", ".join(s.get("raw") or tc(s["start"]) for s in skipped[:4]))
    if not good:
        raise RuntimeError(
            f"Birorta oraliq montajga tushmadi. Montaj uzunligi {tc(total_sec)} "
            "— vaqtlar shu sequence'ning vaqtlarimi?")

    say(stage="Timeline yozilmoqda", percent=0)
    made = []
    if split:
        blocks = []
        for n, r in enumerate(good, start=1):
            say(percent=n / len(good) * 100, detail=f"{n}/{len(good)}")
            clips = [dict(c) for c in base]
            used = cut_to_segments(clips, [(r["cut_start"], r["cut_end"])], fps,
                                   log=lambda *a: None)
            if not used:
                skipped.append(r)
                continue
            length = r["cut_end"] - r["cut_start"]
            seq_name = f"{prefix} {n} · {tc(r['start'])} · {length:.0f}s"
            blocks.append(sequence_block(
                build_xml(used, seq_name, timebase, ntsc, width, height,
                          file_ids=file_ids)))
            made.append({"name": seq_name, "start": r["start"], "end": r["end"],
                         "length": round(length, 2)})
        if not blocks:
            raise RuntimeError("Tanlangan joylarda klip topilmadi.")
        xml = wrap_project(name, blocks)
    else:
        clips = [dict(c) for c in base]
        keeps = [(r["cut_start"], r["cut_end"]) for r in good]
        used = cut_to_segments(clips, keeps, fps, log=log)
        if not used:
            raise RuntimeError("Tanlangan joylarda klip topilmadi.")
        # Bitta sequence'da markerlar bilan: qaysi bo'lak qayerdan olingani
        markers, cursor = [], 0.0
        for n, r in enumerate(good, start=1):
            markers.append({"frame": int(round(cursor * fps)),
                            "name": f"{n} · {tc(r['start'])}"})
            cursor += r["cut_end"] - r["cut_start"]
            made.append({"name": f"{n} · {tc(r['start'])}",
                         "start": r["start"], "end": r["end"],
                         "length": round(r["cut_end"] - r["cut_start"], 2)})
        xml = build_xml(used, name, timebase, ntsc, width, height,
                        markers=markers, file_ids=file_ids)

    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    total = sum(m["length"] for m in made)
    log(f"{len(made)} kadr, jami {total:.0f}s ({tc(total)}) — {output}")
    return {"output": output, "count": len(made), "length_sec": round(total, 2),
            "split": bool(split), "made": made,
            "skipped": [s.get("raw") or tc(s["start"]) for s in skipped]}


def main():
    ap = argparse.ArgumentParser(
        description="Vaqtlar ro'yxati bo'yicha kadrlarni alohida qirqadi.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("-t", "--times", default="", help="oraliqlar ro'yxati")
    ap.add_argument("-f", "--file", help="oraliqlar yozilgan matn fayli")
    ap.add_argument("--pad", type=float, default=0.0,
                    help="har chetiga qo'shiladigan zaxira (soniya)")
    ap.add_argument("--bitta", action="store_true",
                    help="hammasini bitta sequence'da ketma-ket qilish")
    ap.add_argument("-o", "--output", default="kadrlar.xml")
    args = ap.parse_args()

    text = args.times
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text += "\n" + fh.read()
    ranges = parse_ranges(text)
    if not ranges:
        sys.exit("Oraliq topilmadi. Namuna: 1:30-1:44, 2:39-2:45")
    print(f"{len(ranges)} oraliq o'qildi:")
    for r in ranges:
        print(f"   {tc(r['start'])} → {tc(r['end'])}  "
              f"({r['end'] - r['start']:.0f}s)")

    try:
        out = run_ranges(args.files, ranges, split=not args.bitta,
                         pad=args.pad, output=args.output)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"\n{out['count']} kadr → {out['output']}")


if __name__ == "__main__":
    main()

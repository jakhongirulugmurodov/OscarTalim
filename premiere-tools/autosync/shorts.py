#!/usr/bin/env python3
"""Shorts — podcastdan qisqa (reels/Shorts) bo'laklar ajratadi.

Foydalanish (terminaldan):
    python3 shorts.py yozuv.mp4                    # nomzod bo'laklarni ko'rish
    python3 shorts.py yozuv.mp4 --auto 3 -o shorts.xml

Intro'dan farqi ikkita:

  1. Uzunlik. Intro uchun 5-10 soniyalik lahza kerak, Shorts uchun esa
     tugallangan fikr: 20-60 soniya. Shuning uchun topilgan cho'qqi atrofi
     jimliklar bo'yicha kengaytiriladi — gap o'rtasidan boshlanmaydi va
     yarim gapda tugamaydi.

  2. Har bo'lak ALOHIDA sequence bo'ladi (bittasida hammasi emas), chunki
     ularni alohida eksport qilish kerak.

Vertikal (9:16) kadr haqida halol gap: kadrni to'g'ri qayta ramkalash uchun
odam yuzini kuzatish kerak, buni esa Premiere'ning o'zi «Auto Reframe» bilan
bizdan yaxshi qiladi (Adobe'ning yuz kuzatuvi ishlatiladi). Shuning uchun
modul eng qiyin ishni — QAYSI 40 soniyani olish kerakligini — hal qiladi,
qayta ramkalashni esa bir bosishda Premiere'ga topshiradi.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (ENV_RATE, build_xml, cut_to_segments, ffprobe,
                      fps_to_timebase, prepare_clips, quiet_threshold,
                      sequence_block, sequence_format, timeline_length,
                      wrap_project, write_xml)
from intro import (find_moments, lane_energy, load_transcript, smooth,
                   transcript_on_timeline)

MIN_SHORT = 20.0      # bundan qisqasi tugallangan fikr bo'lmaydi
MAX_SHORT = 60.0      # ko'p platformada shu chegara
GAP_SEC = 0.45        # shu uzunlikdagi jimlik — gap tugadi degan belgi


def quiet_mask(clips, total_bins, log=None):
    """Timeline bo'ylab jimlik xaritasi — bo'lak chegaralari uchun.

    Chegara yozuvning o'z darajalaridan olinadi. Qat'iy son ishlatilganda
    shovqinli xonada bironta ham jimlik nuqtasi topilmasdi — natijada
    bo'laklarni qayerdan kesishni bilmay, Shorts bo'sh qaytardi.
    """
    lanes = [lane_energy(c, total_bins) for c in clips]
    loudest = np.maximum.reduce(lanes) if lanes else np.zeros(total_bins)
    sm = smooth(loudest, 0.25)
    return sm < quiet_threshold(sm, log=log)


def gap_points(quiet, min_gap=GAP_SEC):
    """Jimlik oraliqlarining o'rtasi — kesish uchun eng xavfsiz nuqtalar."""
    pts, i, n = [], 0, len(quiet)
    need = int(round(min_gap * ENV_RATE))
    while i < n:
        if not quiet[i]:
            i += 1
            continue
        a = i
        while i < n and quiet[i]:
            i += 1
        if i - a >= need:
            pts.append((a + i) / 2 / ENV_RATE)
    return pts


def expand_to_short(center, gaps, total_sec):
    """Cho'qqi atrofini tugallangan bo'lakka kengaytiradi.

    Chegaralar jimlik nuqtalaridan olinadi: oldingi eng yaqin jimlik —
    boshi, keyingi — oxiri. Uzunlik MIN_SHORT..MAX_SHORT ga tushmasa,
    keyingi jimliklarga o'tib boradi.
    """
    before = [g for g in gaps if g <= center]
    after = [g for g in gaps if g > center]

    start = before[-1] if before else max(0.0, center - MIN_SHORT / 2)
    end = after[0] if after else min(total_sec, center + MIN_SHORT / 2)

    # Qisqa bo'lsa — ikki tomonga kengaytiramiz, gap chegarasida to'xtab
    bi, ai = len(before) - 2, 1
    while end - start < MIN_SHORT and (bi >= 0 or ai < len(after)):
        # qaysi tomon arzonroq bo'lsa — o'sha tomonga
        grow_back = before[bi] if bi >= 0 else None
        grow_fwd = after[ai] if ai < len(after) else None
        if grow_fwd is not None and (grow_back is None
                                     or (grow_fwd - end) <= (start - grow_back)):
            if grow_fwd - start <= MAX_SHORT:
                end = grow_fwd
            ai += 1
        elif grow_back is not None:
            if end - grow_back <= MAX_SHORT:
                start = grow_back
            bi -= 1
        else:
            break

    if end - start > MAX_SHORT:
        # Cho'qqi o'rtada qolsin
        half = MAX_SHORT / 2
        start = max(start, center - half)
        end = min(end, start + MAX_SHORT)
    return max(0.0, start - 0.2), min(total_sec, end + 0.3)


def run_shorts(files, timeline=None, markers=None, limit=8, log=print,
               progress=None):
    """Nomzod bo'laklarni topadi (XML yozmaydi)."""
    say = progress or (lambda **k: None)
    if timeline:
        files = list(dict.fromkeys(c["path"] for c in timeline))

    log("Fayllar tahlil qilinmoqda...")
    clips = prepare_clips(files, timeline, log=log, progress=say)
    total_sec = timeline_length(clips)
    total_bins = int(round(total_sec * ENV_RATE)) + 1

    say(stage="Bo'laklar qidirilmoqda", percent=None,
        detail=f"{total_sec / 60:.0f} daqiqalik yozuv")

    data = load_transcript([c["path"] for c in clips])
    lines = transcript_on_timeline(data, clips) if data else []

    # Poydevor — Intro bilan bir xil: kuchli lahzalar. Ularning atrofini
    # tugallangan bo'lakka kengaytiramiz.
    seeds = find_moments(clips, total_sec, lines, markers,
                         limit=limit * 3, log=log)
    quiet = quiet_mask(clips, total_bins, log=log)
    gaps = gap_points(quiet)
    log(f"  {len(gaps)} ta jimlik nuqtasi (kesish uchun)")

    shorts = []
    for m in seeds:
        center = (float(m["start"]) + float(m["end"])) / 2
        s0, s1 = expand_to_short(center, gaps, total_sec)
        if s1 - s0 < MIN_SHORT * 0.7:
            continue
        if any(s0 < sh["end"] and s1 > sh["start"] for sh in shorts):
            continue                       # ustma-ust bo'laklar kerak emas
        text = " ".join(ln["text"] for ln in lines
                        if ln["start"] < s1 and ln["end"] > s0)[:260]
        shorts.append({
            "start": round(s0, 2), "end": round(s1, 2),
            "length": round(s1 - s0, 2),
            "kind": m["kind"], "why": m["why"], "score": m["score"],
            "text": text, "seed": round(center, 2),
        })
        if len(shorts) >= limit:
            break

    for i, sh in enumerate(sorted(shorts, key=lambda x: -x["score"]), start=1):
        sh["rank"] = i
    shorts.sort(key=lambda sh: sh["start"])
    if shorts:
        log(f"{len(shorts)} bo'lak topildi "
            f"({MIN_SHORT:.0f}-{MAX_SHORT:.0f}s, o'rtacha "
            f"{np.mean([s['length'] for s in shorts]):.0f}s)")
    elif total_sec < MIN_SHORT * 2:
        log(f"Bo'lak topilmadi — yozuv qisqa ({total_sec:.0f}s). "
            f"Bir bo'lak uchun kamida {MIN_SHORT:.0f}s kerak.")
    elif not seeds:
        log("Bo'lak topilmadi: kuchli lahza topilmadi — yozuvda ovoz "
            "darajasi deyarli o'zgarmaydi.")
        log("Nima qilish mumkin: qiziq joylarga timeline'da marker "
            "qo'ying (M tugmasi) — ular to'g'ridan-to'g'ri bo'lakka aylanadi.")
    else:
        log(f"Bo'lak topilmadi: {len(seeds)} ta lahza bor, lekin atrofida "
            f"kesish uchun jimlik yo'q ({len(gaps)} ta nuqta topildi). "
            "Yozuv juda zich — pauzasiz gapirilgan bo'lishi mumkin.")
    say(percent=100, detail=f"{len(shorts)} bo'lak")

    return {
        "shorts": shorts,
        "total_sec": round(total_sec, 2),
        "has_text": bool(lines),
        "arrangement": [{"path": c["path"], "name": c["name"],
                         "rel_offset": round(c["rel_offset"], 4),
                         "placements": c["placements"]} for c in clips],
    }


def build_shorts(arrangement, shorts, output="shorts.xml",
                 prefix="Short", fallback=None, log=print, progress=None):
    """Har tanlangan bo'lak uchun alohida sequence yasaydi."""
    say = progress or (lambda **k: None)
    if not shorts:
        raise RuntimeError("Hech qanday bo'lak tanlanmagan.")

    say(stage="Fayllar o'qilmoqda", percent=None)
    base = []
    for i, item in enumerate(arrangement):
        say(percent=i / max(len(arrangement), 1) * 100)
        info = ffprobe(item["path"])
        info["placements"] = item["placements"]
        info["rel_offset"] = float(item.get("rel_offset", 0.0))
        info["confidence"], info["reliable"] = None, True
        base.append(info)

    fmt = sequence_format(base, log=log)
    fps, timebase, ntsc = fmt["fps"], fmt["timebase"], fmt["ntsc"]
    width, height = fmt["width"], fmt["height"]

    # Fayl id'lari hamma sequence bo'ylab bir xil bo'lishi kerak: bo'lakda
    # ba'zi kamera ishlatilmasa, tartib siljib, id boshqa faylga tegib qoladi.
    file_ids = {c["path"]: f"file-{i}" for i, c in enumerate(base, start=1)}

    blocks = []
    for n, sh in enumerate(sorted(shorts, key=lambda s: s["start"]), start=1):
        say(stage="Timeline yozilmoqda",
            percent=n / len(shorts) * 100, detail=f"{n}/{len(shorts)}")
        # Har sequence uchun kliplarning yangi nusxasi: cut_to_segments
        # ularning segments maydonini o'zgartiradi.
        clips = [dict(c) for c in base]
        keeps = [(float(sh["start"]), float(sh["end"]))]
        used = cut_to_segments(clips, keeps, fps, log=lambda *a: None)
        if not used:
            continue
        mm, ss = divmod(int(float(sh["start"])), 60)
        name = f"{prefix} {n} · {mm:02d}:{ss:02d} · {sh['length']:.0f}s"
        blocks.append(sequence_block(
            build_xml(used, name, timebase, ntsc, width, height,
                      file_ids=file_ids)))

    if not blocks:
        raise RuntimeError("Tanlangan joylarda klip topilmadi.")

    xml = wrap_project("Podcast Suite — Shorts", blocks)
    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    total = sum(float(s["end"]) - float(s["start"]) for s in shorts)
    log(f"{len(blocks)} ta bo'lak, jami {total:.0f}s — {output}")
    if height > width:
        log("Manba allaqachon vertikal — sequence ham vertikal yasaldi, "
            "qayta ramkalash shart emas.")
    else:
        log("Premiere'da: har sequence'ni tanlab, o'ng tugma > Auto Reframe "
            "Sequence > 9:16 — Adobe yuzni o'zi kuzatib, vertikal qiladi.")
    return {"output": output, "shorts": len(blocks),
            "length_sec": round(total, 2),
            "names": [b.split("<name>")[1].split("</name>")[0] for b in blocks]}


def main():
    ap = argparse.ArgumentParser(
        description="Podcastdan qisqa (reels) bo'laklar ajratadi.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--auto", type=int, metavar="N", default=0,
                    help="eng kuchli N bo'lakdan darhol sequence yasash")
    ap.add_argument("-o", "--output", default="shorts.xml")
    args = ap.parse_args()

    try:
        r = run_shorts(args.files, limit=args.limit)
    except RuntimeError as e:
        sys.exit(str(e))

    for sh in r["shorts"]:
        mm, ss = divmod(int(sh["start"]), 60)
        print(f"{sh['rank']:>3}. {mm:02d}:{ss:02d}  {sh['length']:>5.1f}s  "
              f"{sh['kind']:<8} {sh['why']}")
        if sh["text"]:
            print(f"      «{sh['text'][:90]}»")

    if args.auto:
        chosen = [s for s in r["shorts"] if s["rank"] <= args.auto]
        out = build_shorts(r["arrangement"], chosen, output=args.output)
        print(f"\n{out['shorts']} sequence → {out['output']}")
        for nm in out["names"]:
            print("   ", nm)


if __name__ == "__main__":
    main()

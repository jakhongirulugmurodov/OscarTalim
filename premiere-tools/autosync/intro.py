#!/usr/bin/env python3
"""Intro — podcastning eng kuchli lahzalarini topib, boshiga intro yig'adi.

Foydalanish (terminaldan):
    python3 intro.py yozuv.mp4 --limit 15          # nomzodlarni ko'rish
    python3 intro.py yozuv.mp4 --auto -o intro.xml  # eng kuchli 5 tasidan yasash

Bu modulning boshqalardan farqi bor: «eng yaxshi kadr» — did masalasi, uni
mashina hal qila olmaydi. Lekin 50 daqiqalik yozuvni qayta ko'rib chiqish —
mana shu vaqtni yeydi. Shuning uchun ish ikkiga bo'lingan:

    1) mashina nomzodlarni topadi va nima uchun tanlaganini aytadi;
    2) tanlovni odam qiladi, keyin modul faqat tanlanganidan sequence yasaydi.

Nimaga qarab topadi (kuchi bo'yicha):
    * markerlar   — timeline'ga siz qo'ygan belgilar, hech qanday taxminsiz
    * ta'kid      — spiker o'zining odatiy darajasidan baland gapirgan joy
    * kulgi       — keskin ko'tarilish + bir nechta mikrofonda bir vaqtda
    * matn        — transkript bo'lsa: savol, raqam, kuchli so'zlar, tez temp

Transkripsiya shart emas, lekin bo'lsa — tanlash osonlashadi, chunki har
nomzodning gapi ro'yxatda yozilib turadi va eshitib ko'rish shart bo'lmaydi.
"""

import argparse
import glob
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (ENV_RATE, build_xml, cut_to_segments, ffprobe,
                      fps_to_timebase, prepare_clips, quiet_threshold,
                      sequence_format, timeline_length, write_xml)

# Nomzod uzunligi: undan qisqasi tushunarsiz, uzunidan intro cho'zilib ketadi
MIN_MOMENT = 3.5
MAX_MOMENT = 12.0
MIN_GAP = 20.0        # nomzodlar orasidagi eng kichik masofa (soniya)
SMOOTH_SEC = 0.4      # energiyani silliqlash — bitta «tars» ovoz aldab qo'ymasin
BASELINE_SEC = 90.0   # «odatdagi darajasi» shu oynaning medianasi

# Matndagi belgilar — qat'iy qoida emas, ehtimollik. Ro'yxat ataylab qisqa:
# uzun ro'yxat har gapga ball berib, tanlovni ma'nosiz qiladi.
KUCHLI_SOZLAR = (
    "eng", "juda", "aslida", "hech qachon", "birinchi marta", "hayron",
    "qiziq", "sir", "muammo", "million", "milliard", "foiz", "rostdan",
    "haqiqatan", "bilasizmi", "tasavvur qiling", "kutmagan", "shok",
    "sirasini aytganda", "to'g'risi", "afsus", "baxt", "qo'rquv",
)


def smooth(x, sec):
    """Oddiy yuguruvchi o'rtacha — o'lchamni saqlab qoladi."""
    n = max(1, int(round(sec * ENV_RATE)))
    if n <= 1:
        return x
    pad = np.pad(x, (n // 2, n - n // 2 - 1), mode="edge")
    return np.convolve(pad, np.ones(n) / n, mode="valid")


def lane_energy(clip, total_bins):
    """Bitta faylning energiyasi timeline bo'yicha (0..1)."""
    env = clip["envelope"]
    e = env - env.min()
    peak = np.percentile(e, 99) or 1.0
    e = np.clip(e / peak, 0, 1)

    lane = np.zeros(total_bins)
    for place in clip["placements"]:
        src_a = int(round(place["in"] * ENV_RATE))
        src_b = min(len(e), int(round(place["out"] * ENV_RATE)))
        start = int(round(place["start"] * ENV_RATE))
        piece = e[src_a:src_b]
        end = min(total_bins, start + len(piece))
        if end > start:
            lane[start:end] = np.maximum(lane[start:end], piece[:end - start])
    return lane


def rolling_baseline(x, sec=BASELINE_SEC):
    """Har nuqta uchun «odatdagi daraja» — uzun oynadagi mediana.

    Mutlaq balandlik yaramaydi: baland gapiradigan odam butun yozuv bo'ylab
    baland bo'ladi. Bizni qiziqtirgani — o'zining me'yoridan chiqqan joy.
    Mediana bo'laklab hisoblanadi (har nuqtada emas), keyin cho'zib olinadi:
    50 daqiqalik yozuvda ham bir sekundda tugaydi.
    """
    win = max(1, int(round(sec * ENV_RATE)))
    if len(x) <= win:
        return np.full(len(x), float(np.median(x)))
    blocks = int(np.ceil(len(x) / win))
    meds = np.array([np.median(x[i * win:(i + 1) * win]) for i in range(blocks)])
    centers = np.arange(blocks) * win + win / 2
    return np.interp(np.arange(len(x)), centers, meds)


def find_bursts(score, min_len_sec=0.8, thresh=0.55):
    """Ball chizig'idagi cho'qqilar → (boshi, oxiri, cho'qqi qiymati)."""
    hot = score >= thresh
    out, i, n = [], 0, len(hot)
    min_bins = int(round(min_len_sec * ENV_RATE))
    while i < n:
        if not hot[i]:
            i += 1
            continue
        a = i
        while i < n and hot[i]:
            i += 1
        if i - a >= min_bins:
            out.append((a / ENV_RATE, i / ENV_RATE,
                        float(score[a:i].max()), int(a + np.argmax(score[a:i]))))
    return out


# Nutqmi yoki musiqa/shovqinmi — bo'g'in tebranishi bo'yicha.
#
# Gapirishda energiya sekundda 3-6 marta ko'tarilib-tushadi (bo'g'inlar),
# barqaror musiqada esa deyarli tekis, bir marta taqqan shovqinda — bitta
# cho'qqi. Shu farq envelope'ning 2-8 Hz oralig'idagi quvvat ulushida
# ko'rinadi. O'lchovda: haqiqiy nutq 0.43-0.63, oq shovqin 0.33, yo'talish
# 0.15, barqaror musiqa 0.00 chiqdi.
SPEECH_DROP = 0.12    # bundan past — nomzod umuman olinmaydi
SPEECH_WEAK = 0.28    # bu oraliqda — ball pasaytiriladi, lekin qoldiriladi


def speechiness(env_window):
    """0..1: shu oynadagi energiya nutqqa qanchalik o'xshaydi.

    Ikki ehtiyot chorasi bor, ikkovi ham sinovda kerak bo'ldi:
      * chetlari kesiladi — oyna boshidagi «jimlikdan ovozga» sakrash
        o'zi keng chastotali portlash beradi va barqaror musiqani ham
        nutqqa o'xshatib qo'yadi;
      * Hann oynasi qo'llanadi — kesilgan chetlar yana sakrash yasamasin.
    """
    x = np.asarray(env_window, dtype=float)
    trim = int(0.4 * ENV_RATE)
    if len(x) > 2 * trim + ENV_RATE:
        x = x[trim:len(x) - trim]
    if len(x) < ENV_RATE:
        return 1.0          # bir soniyadan qisqa oyna — hukm chiqarmaymiz
    if x.std() < 0.01:
        return 0.0          # butunlay tekis: baland, lekin gap emas
    x = (x - x.mean()) * np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x)) ** 2
    freq = np.fft.rfftfreq(len(x), 1.0 / ENV_RATE)
    band = spec[(freq >= 2) & (freq <= 8)].sum()
    total = spec[(freq >= 0.3) & (freq <= 20)].sum() + 1e-12
    return float(band / total)


# --------------------------------------------------------------- transkript

def archive_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "suite", "transkriptlar"))


def load_transcript(paths):
    """Shu fayllar uchun saqlangan transkriptni topadi (eng yangisini).

    Transkript sequence'dan olingan bo'lsa, vaqtlari montaj vaqtida —
    ular bizning timeline'imizga to'g'ridan-to'g'ri tushadi. Xom fayldan
    olingan bo'lsa, vaqtlarni klip joylashuvi bo'yicha ko'chiramiz.
    """
    want = {os.path.abspath(p) for p in paths}
    want_names = {os.path.basename(p) for p in paths}
    best = None
    for f in sorted(glob.glob(os.path.join(archive_dir(), "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        src = data.get("source") or ""
        if os.path.abspath(src) in want or os.path.basename(src) in want_names:
            if best is None or os.path.getmtime(f) > os.path.getmtime(best[0]):
                best = (f, data)
    return best[1] if best else None


def transcript_on_timeline(data, clips):
    """Transkript qatorlarini timeline vaqtiga keltiradi."""
    lines = [dict(ln) for ln in data.get("lines", []) if ln.get("text")]
    if data.get("from_sequence"):
        return lines            # allaqachon montaj vaqtida

    src = os.path.abspath(data.get("source") or "")
    clip = next((c for c in clips if c["path"] == src
                 or c["name"] == os.path.basename(src)), None)
    if not clip:
        return lines
    out = []
    for ln in lines:
        for place in clip["placements"]:
            if place["in"] <= ln["start"] < place["out"]:
                shift = place["start"] - place["in"]
                out.append({**ln, "start": ln["start"] + shift,
                            "end": min(ln["end"], place["out"]) + shift})
                break
    return out


def text_score(text):
    """Gapning «qiziqarlilik» belgilari → (ball, sabab)."""
    t = (text or "").lower()
    score, why = 0.0, []
    if "?" in t:
        score += 0.35
        why.append("savol")
    if "!" in t:
        score += 0.2
        why.append("hayajon")
    if re.search(r"\d", t):
        score += 0.15
        why.append("raqam")
    hits = [w for w in KUCHLI_SOZLAR if w in t]
    if hits:
        score += min(0.4, 0.15 * len(hits))
        why.append("kuchli so'z: " + hits[0])
    return score, why


# ----------------------------------------------------------------- nomzodlar

def snap_bounds(center, lines, quiet, total_sec):
    """Nomzod chegaralarini gap boshi/oxiriga (yoki jimlikka) tekislaydi.

    Gapning o'rtasidan boshlangan intro parchasi tushunarsiz bo'ladi.
    Transkript bo'lsa — gap chegaralari bo'yicha, bo'lmasa — eng yaqin
    jimlik bo'yicha.
    """
    # Cho'qqi atrofidagi qatorlar: eng «gapga to'q» bo'lganini olamiz, aks
    # holda cho'qqiga tasodifan tekkan bo'sh gap tanlanib qolishi mumkin.
    near = [ln for ln in lines
            if ln["start"] - 1.5 <= center <= ln["end"] + 1.5]
    if near:
        near.sort(key=lambda ln: -text_score(ln["text"])[0])
        for ln in near[:1]:
            a, b = ln["start"], ln["end"]
            # qo'shni qatorlarni ham qo'shib, kamida MIN_MOMENT ga yetkazamiz
            for nxt in lines:
                if b - a >= MIN_MOMENT:
                    break
                if abs(nxt["start"] - b) < 0.9:
                    b = nxt["end"]
            return max(0.0, a - 0.25), min(total_sec, b + 0.35)

    # Transkriptsiz: chap va o'ngdagi eng yaqin jimlikni qidiramiz
    c = int(round(center * ENV_RATE))
    lo = c
    while lo > 0 and (c - lo) < int(MAX_MOMENT / 2 * ENV_RATE):
        if quiet[lo]:
            break
        lo -= 1
    hi = c
    while hi < len(quiet) - 1 and (hi - c) < int(MAX_MOMENT / 2 * ENV_RATE):
        if quiet[hi]:
            break
        hi += 1
    a, b = lo / ENV_RATE, hi / ENV_RATE
    if b - a < MIN_MOMENT:                      # jimlik topilmadi — markazdan olamiz
        a, b = center - MIN_MOMENT / 2, center + MIN_MOMENT / 2
    return max(0.0, a), min(total_sec, b)


def find_moments(clips, total_sec, lines, markers=None, limit=18, log=print):
    """Nomzodlarni topadi. Qaytadi: vaqt bo'yicha tartiblangan ro'yxat."""
    total_bins = int(round(total_sec * ENV_RATE)) + 1
    lanes = [lane_energy(c, total_bins) for c in clips]
    loudest = np.maximum.reduce(lanes) if lanes else np.zeros(total_bins)
    # Jimlik chegarasi yozuvning o'zidan olinadi: qat'iy son shovqinli
    # xonada hech qachon ishlamaydi — bir dona ham chegara topilmaydi.
    sm_loud = smooth(loudest, 0.25)
    quiet = sm_loud < quiet_threshold(sm_loud, log=log)

    # 1) Ta'kid: o'z me'yoridan baland gapirgan joylar
    emphasis = np.zeros(total_bins)
    for lane in lanes:
        sm = smooth(lane, SMOOTH_SEC)
        base = rolling_baseline(sm)
        emphasis = np.maximum(emphasis, np.clip((sm - base) / 0.35, 0, 1))

    # 2) Keskin ko'tarilish (kulgi, hayajon) — silliqlangan chiziqning o'sishi
    rise = np.zeros(total_bins)
    step = max(1, int(0.4 * ENV_RATE))
    for lane in lanes:
        sm = smooth(lane, 0.25)
        d = np.zeros_like(sm)
        d[step:] = sm[step:] - sm[:-step]
        rise = np.maximum(rise, np.clip(d / 0.45, 0, 1))

    # 3) Bir vaqtda bir nechta mikrofon — birga kulish belgisi.
    #    Faqat mikrofonlar bir-biridan farq qilsa ishonchli: bitta xonada
    #    hamma mikrofon hammani yozadi va bu belgi ma'nosiz bo'lib qoladi.
    together = np.zeros(total_bins)
    # Jim yo'laklar (audiosiz kamera) hisobga olinmaydi: ularning
    # o'zgarishi nol, korrelyatsiya esa NaN chiqadi va butun o'lchovni
    # buzadi.
    tirik = [smooth(l, SMOOTH_SEC) for l in lanes]
    tirik = [l for l in tirik if float(np.std(l)) > 1e-9]
    if len(tirik) >= 2:
        stack = np.vstack(tirik)
        corr = np.corrcoef(stack)
        distinct = np.nanmin(corr[np.triu_indices(len(tirik), 1)]) < 0.9
        if distinct:
            hot = (stack > 0.5).sum(axis=0)
            together = np.clip((hot - 1) / max(1, len(tirik) - 1), 0, 1)
        else:
            log("  (mikrofonlar bir-biriga juda o'xshash — «birga kulgi» "
                "belgisi ishlatilmadi)")

    score = 0.55 * emphasis + 0.3 * rise + 0.15 * together
    sm_score = smooth(score, 0.3)

    # Qat'iy 0.45 chegara bir tekis gapiradigan spikerda BO'SH ro'yxat
    # qaytaradi: yozuvda lahzalar bor, lekin ovoz keskin ko'tarilmaydi.
    # Foydalanuvchi uchun bu «modul ishlamadi» degani. Shuning uchun
    # yetarli nomzod topilmasa, sezgirlik bosqichma-bosqich oshiriladi —
    # nomzodlar baribir kuchi bo'yicha tartiblanadi, ya'ni eng yaxshisi
    # tepada qoladi.
    want = max(3, limit // 3)
    used = 0.45
    bursts = find_bursts(sm_score, thresh=used)
    for lower in (0.35, 0.28, 0.22, 0.16):
        if len(bursts) >= want:
            break
        weaker = find_bursts(sm_score, thresh=lower)
        if len(weaker) > len(bursts):
            bursts, used = weaker, lower
    log(f"  {len(bursts)} ta energiya cho'qqisi topildi"
        + (f" (yozuv bir tekis — sezgirlik oshirildi: {used})"
           if used < 0.45 else ""))

    # 4) Matn ballari — gap darajasida
    line_score = {}
    for ln in lines:
        s, why = text_score(ln["text"])
        if s > 0:
            line_score[round(ln["start"], 2)] = (s, why, ln)

    cands, dropped = [], 0
    for a, b, peak, peak_bin in bursts:
        center = peak_bin / ENV_RATE
        s0, s1 = snap_bounds(center, lines, quiet, total_sec)
        if s1 - s0 > MAX_MOMENT:
            s1 = s0 + MAX_MOMENT
        text = " ".join(ln["text"] for ln in lines
                        if ln["start"] < s1 and ln["end"] > s0)[:220]
        tscore, twhy = text_score(text)

        kind = "ta'kid"
        if together[peak_bin] > 0.6 and rise[peak_bin] > 0.4:
            kind = "kulgi"
        elif rise[peak_bin] > 0.6:
            kind = "hayajon"
        if "savol" in twhy:
            kind = "savol"

        # Musiqa, qarsak, stul qichirlashi — energiya baland, lekin gap emas
        sp = speechiness(loudest[int(s0 * ENV_RATE):int(s1 * ENV_RATE)])
        if sp < SPEECH_DROP:
            dropped += 1
            continue

        why = [kind]
        if tscore > 0:
            why += twhy
        penalty = 1.0
        if sp < SPEECH_WEAK:
            penalty = 0.6
            why.append("ovoz noaniq")
        cands.append({
            "start": round(s0, 2), "end": round(s1, 2),
            "length": round(s1 - s0, 2),
            "kind": kind, "why": ", ".join(dict.fromkeys(why)),
            "score": round((peak + tscore) * penalty, 3),
            "text": text,
        })

    if dropped:
        log(f"  {dropped} ta cho'qqi nutq emas deb chiqarildi "
            "(musiqa, qarsak, shovqin)")

    # 5) Foydalanuvchi markerlari — taxmin emas, shuning uchun eng yuqorida
    for m in (markers or []):
        t = float(m.get("start", m) if isinstance(m, dict) else m)
        s0, s1 = snap_bounds(t, lines, quiet, total_sec)
        text = " ".join(ln["text"] for ln in lines
                        if ln["start"] < s1 and ln["end"] > s0)[:220]
        cands.append({
            "start": round(s0, 2), "end": round(min(s1, s0 + MAX_MOMENT), 2),
            "length": round(min(s1 - s0, MAX_MOMENT), 2),
            "kind": "marker", "why": "siz belgilagan joy",
            "score": 99.0, "text": text,
        })

    # 6) Yaqin nomzodlarni birlashtiramiz va kuchsizini tashlaymiz
    cands.sort(key=lambda c: -c["score"])
    picked = []
    for c in cands:
        if any(abs(c["start"] - p["start"]) < MIN_GAP for p in picked):
            continue
        picked.append(c)
        if len(picked) >= limit:
            break

    for i, c in enumerate(sorted(picked, key=lambda x: -x["score"]), start=1):
        c["rank"] = i
    picked.sort(key=lambda c: c["start"])
    return picked


# -------------------------------------------------------------------- oqim

def run_intro(files, timeline=None, markers=None, limit=18, log=print,
              progress=None):
    """Nomzodlarni topish bosqichi — XML yozmaydi."""
    say = progress or (lambda **k: None)
    if timeline:
        files = list(dict.fromkeys(c["path"] for c in timeline))

    log("Fayllar tahlil qilinmoqda...")
    clips = prepare_clips(files, timeline, log=log, progress=say)
    total_sec = timeline_length(clips)

    say(stage="Lahzalar qidirilmoqda", percent=None,
        detail=f"{total_sec / 60:.0f} daqiqalik yozuv")
    data = load_transcript([c["path"] for c in clips])
    lines = transcript_on_timeline(data, clips) if data else []
    if lines:
        log(f"Transkript ishlatilmoqda: {data.get('title')} "
            f"({len(lines)} qator)")
    else:
        log("Transkript topilmadi — faqat ovoz bo'yicha qidiriladi "
            "(Captions bilan transkripsiya qilsangiz, tanlash osonlashadi)")

    moments = find_moments(clips, total_sec, lines, markers, limit, log)
    if moments:
        log(f"{len(moments)} nomzod tanlandi — panelda belgilab, intro yasaysiz")
    else:
        # Bo'sh ro'yxat «modul ishlamadi» degan taassurot qoldiradi.
        # Aynan sabab va aniq keyingi qadam aytilsin.
        log("Nomzod topilmadi. Sabab: yozuvda ovoz darajasi deyarli "
            "o'zgarmaydi — «ta'kid» va «kulgi» belgilari shunga qarab "
            "topiladi.")
        log("Nima qilish mumkin: timeline'ga o'zingiz marker qo'ying "
            "(M tugmasi) — markerlar taxminsiz ishlatiladi va ro'yxatning "
            "eng tepasida turadi.")
    say(percent=100, detail=f"{len(moments)} nomzod")

    return {
        "moments": moments,
        "total_sec": round(total_sec, 2),
        "has_text": bool(lines),
        "arrangement": [{"path": c["path"], "name": c["name"],
                         "rel_offset": round(c["rel_offset"], 4),
                         "placements": c["placements"]} for c in clips],
    }


def build_intro(arrangement, moments, output="intro.xml",
                name="Podcast Suite — Intro", review=False, fallback=None,
                log=print, progress=None):
    """Tanlangan lahzalardan sequence yasaydi (qayta tahlil qilmaydi).

    `review=True` — «ko'rib chiqish» rejimi: hamma nomzod ketma-ket teriladi
    va har biri marker bilan raqamlanadi. 50 daqiqalik timeline'ni titkilash
    o'rniga ikki daqiqada hammasini eshitib, keyin panelda belgilash mumkin.
    Transkript yo'q bo'lganda bu yagona tez yo'l.
    """
    say = progress or (lambda **k: None)
    if not moments:
        raise RuntimeError("Hech qanday lahza tanlanmagan.")

    say(stage="Fayllar o'qilmoqda", percent=None)
    clips = []
    for i, item in enumerate(arrangement):
        say(percent=i / max(len(arrangement), 1) * 100)
        info = ffprobe(item["path"])
        info["placements"] = item["placements"]
        info["rel_offset"] = float(item.get("rel_offset", 0.0))
        info["confidence"], info["reliable"] = None, True
        clips.append(info)

    fmt = sequence_format(clips, log=log)
    fps, timebase, ntsc = fmt["fps"], fmt["timebase"], fmt["ntsc"]
    width, height = fmt["width"], fmt["height"]

    keeps = [(float(m["start"]), float(m["end"])) for m in moments]
    keeps = [(a, b) for a, b in keeps if b > a]
    say(stage="Timeline yozilmoqda", percent=40)
    clips = cut_to_segments(clips, keeps, fps, log)
    if not clips:
        raise RuntimeError("Tanlangan joylarda klip topilmadi.")

    # Ko'rib chiqish rejimida har bo'lak boshiga marker: «3 · kulgi 12:04»
    markers = None
    if review:
        markers, cursor = [], 0.0
        for i, m in enumerate(moments, start=1):
            mm, ss = divmod(int(float(m["start"])), 60)
            markers.append({
                "frame": int(round(cursor * fps)),
                "name": f"{i} · {m.get('kind', 'lahza')} {mm:02d}:{ss:02d}",
                "comment": (m.get("text") or m.get("why") or "")[:120],
            })
            cursor += float(m["end"]) - float(m["start"])

    xml = build_xml(clips, name, timebase, ntsc, width, height,
                    markers=markers)
    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    length = sum(b - a for a, b in keeps)
    log(f"Intro: {len(keeps)} lahza, {length:.1f}s — {output}")
    return {"output": output, "moments": len(keeps),
            "length_sec": round(length, 2),
            "clips": [{"name": c["name"], "segments": len(c["segments"])}
                      for c in clips]}


def main():
    ap = argparse.ArgumentParser(
        description="Podcastning eng kuchli lahzalarini topadi.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--limit", type=int, default=18)
    ap.add_argument("--auto", type=int, metavar="N", default=0,
                    help="eng kuchli N lahzadan darhol intro yasash")
    ap.add_argument("-o", "--output", default="intro.xml")
    args = ap.parse_args()

    try:
        r = run_intro(args.files, limit=args.limit)
    except RuntimeError as e:
        sys.exit(str(e))

    for m in r["moments"]:
        mm, ss = divmod(int(m["start"]), 60)
        print(f"{m['rank']:>3}. {mm:02d}:{ss:02d}  {m['length']:>5.1f}s  "
              f"{m['kind']:<8} {m['why']}")
        if m["text"]:
            print(f"      «{m['text'][:90]}»")

    if args.auto:
        chosen = sorted([m for m in r["moments"] if m["rank"] <= args.auto],
                        key=lambda m: m["start"])
        out = build_intro(r["arrangement"], chosen, output=args.output)
        print(f"\n{out['moments']} lahza · {out['length_sec']}s → {out['output']}")


if __name__ == "__main__":
    main()

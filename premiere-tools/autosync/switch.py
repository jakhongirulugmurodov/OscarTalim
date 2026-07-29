#!/usr/bin/env python3
"""Switch — kim gapirsa, o'sha kameraga o'tadigan montaj rejasi.

Foydalanish (terminaldan):
    python3 switch.py behruz.mp4 mehmon.mp4 keng.mp4 \
        --roles speaker,speaker,wide -o switch.xml

Mantiq: har spikerning mikrofoni o'z darajasiga nisbatan baholanadi (mutlaq
balandlik emas — mikrofonlar turlicha sozlangan bo'lishi mumkin). Eng faoli
o'sha lahzadagi spiker; uning kamerasi programmaga chiqadi. Ustiga rejissyor
qoidalari qo'yiladi: kadr juda qisqa bo'lmasin, bir kadr juda uzoq turmasin,
ikki kishi birga gapirsa keng planga o'tilsin.
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (ENV_RATE, build_xml, extract_envelope, ffprobe,
                      find_offset, fps_to_timebase, write_xml, MIN_CONFIDENCE, sub_progress)

# Kamera vazifalari
SPEAKER, WIDE, ALT, INSERT = "speaker", "wide", "alt", "insert"
AUDIO = "audio"     # faqat ovoz manbasi (kamera sifatida ishlatilmaydi)

# Rejissyor qoidalari (panel ularni o'zgartira oladi)
DEFAULT_MIN_SHOT = 2.5     # eng qisqa kadr, soniya
DEFAULT_MAX_SHOT = 25.0    # bir kadr shundan uzoq tursa — muqobilga chiqamiz
DEFAULT_MARGIN = 1.35      # spiker deb tan olish uchun raqibidan shuncha kuchli
DEFAULT_SILENCE = 0.12     # shundan past — bu mikrofonda gap yo'q
DEFAULT_SMOOTH = 0.5       # ovoz izini silliqlash oynasi, soniya


def normalized(env):
    """Envelope'ni 0..1 ga keltirish — mikrofonlar bir-biriga solishtirilsin."""
    e = env - env.min()
    peak = np.percentile(e, 99) or 1.0
    return np.clip(e / peak, 0, 1)


def place_on_timeline(clip, total_bins):
    """Klip audiosini umumiy timeline'ga qo'yish (joylashuvlari bo'yicha)."""
    lane = np.zeros(total_bins)
    e = normalized(clip["envelope"])
    for place in clip["placements"]:
        src_a = int(round(place["in"] * ENV_RATE))
        src_b = min(len(e), int(round(place["out"] * ENV_RATE)))
        start = int(round(place["start"] * ENV_RATE))
        piece = e[src_a:src_b]
        end = min(total_bins, start + len(piece))
        if end > start:
            lane[start:end] = np.maximum(lane[start:end], piece[:end - start])
    return lane


def smooth(x, seconds):
    """Ovoz izini silliqlash — nutq tabiatan uzuq-yuluq bo'ladi."""
    w = max(1, int(round(seconds * ENV_RATE)))
    if w < 2:
        return x
    return np.convolve(x, np.ones(w) / w, mode="same")


def active_speaker(lanes, margin, silence, smoothing=DEFAULT_SMOOTH):
    """Har bin uchun: qaysi spiker faol (-1 = hech kim, -2 = bir nechta).

    Mutlaq balandlik emas, nisbiy farq qaraladi: bir mikrofonda qo'shnining
    ovozi ham eshitiladi, shuning uchun eng kuchlisi ikkinchisidan `margin`
    barobar baland bo'lsagina u spiker deb tan olinadi.

    Qaror har 5 ms uchun alohida qabul qilinsa natija shovqinli bo'ladi
    (o'lchovda 82%), chunki nutqda bo'g'inlar orasida tabiiy jimliklar bor.
    Shuning uchun izlar avval yarim soniyalik oynada silliqlanadi — shunda
    aniqlik 99% dan oshadi.
    """
    if not lanes:
        return np.array([], dtype=int)
    if smoothing > 0:
        lanes = [smooth(l, smoothing) for l in lanes]
    stack = np.vstack(lanes)                    # [spiker][bin]
    best = np.argmax(stack, axis=0)
    top = stack.max(axis=0)

    second = np.sort(stack, axis=0)[-2] if len(lanes) > 1 else np.zeros_like(top)
    result = np.where(top >= silence, best, -1)
    if len(lanes) > 1:
        # Ikkitasi yaqin bo'lsa — birga gapirishyapti
        together = (top >= silence) & (second * margin > top)
        result = np.where(together, -2, result)
    return result


def plan_shots(active, cams, min_shot, max_shot, fps=25.0, log=print):
    """Faollikdan kamera rejasini tuzish: [(start_bin, end_bin, cam_index)].

    cams — kameralar ro'yxati, har birida `role` va spiker uchun `speaker_idx`.
    """
    # Kadr chegaralari keyinroq freymlarga yumaloqlanadi, shuning uchun aniq
    # chegarada turgan kadr bir freymga qisqarib ketishi mumkin — bir freymlik
    # zaxira qo'shamiz, shunda «eng qisqa kadr» qoidasi haqiqatan bajariladi.
    bins_per_frame = max(1, int(round(ENV_RATE / max(fps, 1))))
    min_bins = int(np.ceil(min_shot * ENV_RATE)) + bins_per_frame
    max_bins = int(round(max_shot * ENV_RATE))

    # Ekranga faqat videosi bor fayllar chiqa oladi. Rekorder (audio-only)
    # fayl spiker deb belgilangan bo'lsa ham kadr bo'la olmaydi — aks holda
    # programmada teshik qolib ketadi.
    def usable(c):
        return c["has_video"] and c["role"] != AUDIO

    speaker_cams = {}          # spiker raqami -> shu spikerning kameralari
    for i, cam in enumerate(cams):
        if not usable(cam) or cam.get("speaker_idx") is None:
            continue
        if cam["role"] in (SPEAKER, ALT):
            speaker_cams.setdefault(cam["speaker_idx"], []).append(i)
    wides = [i for i, c in enumerate(cams) if c["role"] == WIDE and usable(c)]
    inserts = [i for i, c in enumerate(cams) if c["role"] == INSERT and usable(c)]
    on_screen = [i for i, c in enumerate(cams) if usable(c)]
    fallback = wides or inserts or on_screen[:1] or [0]

    def cams_for(state, current):
        """Shu holatda qaysi kameralar mos keladi (birinchisi — afzal)."""
        if state == -2:                        # birga gapirishyapti
            return wides or ([current] if current is not None else fallback)
        if state == -1:                        # jimlik
            return wides or ([current] if current is not None else fallback)
        return speaker_cams.get(state) or wides or fallback

    shots = []
    current, start = None, 0
    used_count = {}

    for i in range(len(active) + 1):
        state = active[i] if i < len(active) else None
        want = cams_for(state, current) if state is not None else None
        end_of_input = i == len(active)

        # Hozirgi kadr hali mos kelayaptimi?
        keeps = (not end_of_input) and current is not None and current in want
        length = i - start
        too_long = current is not None and length >= max_bins

        if keeps and not too_long:
            continue

        if current is not None and (end_of_input or not keeps or too_long):
            if end_of_input or length >= min_bins or not shots:
                shots.append([start, i, current])
                used_count[current] = used_count.get(current, 0) + 1
                start = i
            else:
                # Juda qisqa: yangi kadrni ochmaymiz, hozirgisini cho'zamiz
                continue

        if end_of_input:
            break

        options = want or fallback
        if too_long and current is not None:
            # Bir kadr cho'zilib ketdi — muqobil kadrga chiqamiz
            others = [c for c in options if c != current]
            if not others:
                others = [c for c in (wides + inserts) if c != current]
            if others:
                options = others
        # Kam ishlatilganini afzal ko'ramiz — kameralar navbatlashsin
        current = min(options, key=lambda c: (c == shots[-1][2] if shots else False,
                                              used_count.get(c, 0)))
        if current is None:
            current = options[0]

    # Qo'shni bir xil kadrlarni birlashtiramiz
    merged = []
    for s in shots:
        if merged and merged[-1][2] == s[2] and merged[-1][1] == s[0]:
            merged[-1][1] = s[1]
        else:
            merged.append(list(s))
    return merged


def run_switch(files, roles=None, speakers=None, output="switch.xml",
               name="Podcast Suite — Switch", min_shot=DEFAULT_MIN_SHOT,
               max_shot=DEFAULT_MAX_SHOT, margin=DEFAULT_MARGIN,
               silence=DEFAULT_SILENCE, audio_master=None, timeline=None,
               fallback=None, log=print, progress=None):
    """Kamera almashtirish rejasini tuzib, sequence yasaydi.

    roles        — har fayl uchun vazifa: speaker / wide / alt / insert
    speakers     — spiker kamerasi qaysi spikerga tegishli (alt kadrlar uchun ham)
    audio_master — ovozi butun timeline bo'ylab ishlatiladigan fayl yo'li.
                   Bu kamera bo'lishi ham mumkin: u ekranga chiqaveradi,
                   ovozi esa kadr almashsa ham uzluksiz qolaveradi.
    """
    from_timeline = bool(timeline)
    if from_timeline:
        files = list(dict.fromkeys(c["path"] for c in timeline))

    say = progress or (lambda **k: None)
    log("Fayllar tahlil qilinmoqda...")
    clips = []
    for idx, f in enumerate(files):
        say(stage="Ovoz tahlil qilinmoqda", percent=idx / len(files) * 100,
            detail=f"{idx + 1}/{len(files)}: {os.path.basename(f)}")
        info = ffprobe(f)
        if not info["has_audio"]:
            log(f"  OGOHLANTIRISH: {info['name']} da audio yo'q — o'tkazildi")
            continue
        info["envelope"] = extract_envelope(
            f, info["duration"], progress=sub_progress(say, idx, len(files)))
        info["role"] = (roles[idx] if roles and idx < len(roles) else SPEAKER)
        info["speaker_idx"] = (speakers[idx] if speakers and idx < len(speakers)
                               else None)
        clips.append(info)
        log(f"  {info['name']}: {info['duration']:.1f}s ({info['role']})")

    if not clips:
        raise RuntimeError("Audioli fayl topilmadi.")

    # --- Joylashuv: sequence'dan yoki sinxronlab ---
    if from_timeline:
        by_path = {c["path"]: c for c in clips}
        for c in clips:
            c["placements"] = []
        for item in timeline:
            clip = by_path.get(item["path"])
            if clip:
                clip["placements"].append(
                    {"start": float(item["start"]), "in": float(item["in"]),
                     "out": float(item["out"])})
        clips = [c for c in clips if c["placements"]]
        log(f"Sequence'dan {sum(len(c['placements']) for c in clips)} klip olindi")
    else:
        ref = max(clips, key=lambda c: len(c["envelope"]))
        for clip in clips:
            if clip is ref or len(clips) == 1:
                clip["offset_sec"] = 0.0
            else:
                offset, conf = find_offset(ref["envelope"], clip["envelope"])
                if conf < MIN_CONFIDENCE:
                    log(f"  OGOHLANTIRISH: {clip['name']} — mos joy topilmadi "
                        f"(ishonch {conf:.1f}x), boshiga qo'yildi")
                    offset = 0.0
                clip["offset_sec"] = offset
        base = min(c["offset_sec"] for c in clips)
        for clip in clips:
            clip["placements"] = [{"start": clip["offset_sec"] - base,
                                   "in": 0.0, "out": clip["duration"]}]

    total_sec = max(p["start"] + (p["out"] - p["in"])
                    for c in clips for p in c["placements"])
    total_bins = int(round(total_sec * ENV_RATE)) + 1

    # --- Kim gapiryapti ---
    # Har spikerning "ovoz yo'lagi": o'z kamerasi (yoki alt kadri) audiosidan
    speaker_ids = sorted({c["speaker_idx"] for c in clips
                          if c["role"] in (SPEAKER, ALT)
                          and c["speaker_idx"] is not None})
    if not speaker_ids:
        # Vazifa berilmagan bo'lsa: har spiker kamerasi o'z spikeri
        n = 0
        for c in clips:
            if c["role"] == SPEAKER:
                c["speaker_idx"] = n
                n += 1
        speaker_ids = list(range(n))

    lanes = []
    for sid in speaker_ids:
        own = [c for c in clips if c["speaker_idx"] == sid and c["role"] == SPEAKER]
        if not own:
            own = [c for c in clips if c["speaker_idx"] == sid]
        lane = np.zeros(total_bins)
        for c in own:
            lane = np.maximum(lane, place_on_timeline(c, total_bins))
        lanes.append(lane)

    active = active_speaker(lanes, margin, silence)

    # --- Sequence parametrlari (kadr rejasi freymlarni bilishi kerak) ---
    video_clip = next((c for c in clips if c["has_video"]), None)
    fps = video_clip["fps"] if video_clip else 25.0
    timebase, ntsc = fps_to_timebase(fps)
    width = video_clip["width"] if video_clip else 1920
    height = video_clip["height"] if video_clip else 1080

    # --- Kamera rejasi ---
    say(stage="Kadrlar rejalanmoqda", percent=None,
        detail=f"{len(clips)} kamera")
    shots = plan_shots(active, clips, min_shot, max_shot, fps, log)
    if not shots:
        raise RuntimeError("Kamera rejasi tuzilmadi — vazifalarni tekshiring.")

    together = int(np.sum(active == -2)) / ENV_RATE
    quiet = int(np.sum(active == -1)) / ENV_RATE
    log(f"Kadrlar: {len(shots)} ta · birga gapirish {together:.0f}s · "
        f"jimlik {quiet:.0f}s")

    # --- Kadrlarni klip bo'laklariga aylantiramiz ---
    for c in clips:
        c["dur_frames"] = int(round(c["duration"] * fps))
        c["start_frame"] = int(round(c["placements"][0]["start"] * fps))
        c["segments"] = []
        c["shot_count"] = 0

    def covering(cam_idx, at):
        """Shu kamera `at` lahzada mavjudmi? Mavjud bo'lsa joylashuvi."""
        for place in clips[cam_idx]["placements"]:
            if place["start"] <= at < place["start"] + (place["out"] - place["in"]):
                return place
        return None

    def any_covering(at, prefer):
        """`at` lahzada mavjud bo'lgan istalgan kamera (afzali — `prefer`)."""
        order = [prefer] + [i for i in range(len(clips)) if i != prefer]
        for i in order:
            if clips[i]["role"] == AUDIO or not clips[i]["has_video"]:
                continue
            place = covering(i, at)
            if place:
                return i, place
        return None, None

    # Kadrni bo'laklarga aylantiramiz. Tanlangan kamera o'sha vaqtda
    # yozilmagan bo'lishi mumkin (masalan qisqaroq fayl) — u holda
    # programmada teshik qolib ketmasin: o'sha lahzada mavjud boshqa
    # kameraga o'tamiz.
    step = 1.0 / fps
    filled = 0.0
    for start_bin, end_bin, cam_idx in shots:
        a, b = start_bin / ENV_RATE, end_bin / ENV_RATE
        cursor = a
        while cursor < b - step / 2:
            use_idx, place = cam_idx, covering(cam_idx, cursor)
            if place is None:
                use_idx, place = any_covering(cursor, cam_idx)
                if place is None:      # hech bir kamera yo'q — o'tkazamiz
                    cursor += step
                    continue
                filled += 0.0          # quyida aniq uzunlik qo'shiladi
            p_end = place["start"] + (place["out"] - place["in"])
            hi = min(b, p_end)
            if hi - cursor <= step / 2:
                cursor += step
                continue
            clip = clips[use_idx]
            src_in = place["in"] + (cursor - place["start"])
            clip["segments"].append({
                "start": int(round(cursor * fps)),
                "in": int(round(src_in * fps)),
                "out": int(round((src_in + (hi - cursor)) * fps)),
            })
            clip["shot_count"] += 1
            if use_idx != cam_idx:
                filled += hi - cursor
            cursor = hi
    if filled > 0.5:
        log(f"  {filled:.0f}s da tanlangan kamera yozuvi yo'q edi — "
            "boshqa kamera bilan to'ldirildi")

    # --- Ovoz manbasi ---
    # Odatda bitta yaxshi yozuv bo'ladi (rekorder yoki bitta kamera), qolgan
    # kameralarda esa o'zining past sifatli mikrofoni. Kamera almashganda ovoz
    # ham almashib ketmasin: belgilangan manba butun timeline bo'ylab uzluksiz
    # ketadi, boshqalarining audiosi umuman chiqarilmaydi.
    masters = [c for c in clips if c["path"] == os.path.abspath(audio_master or "")]
    if not masters:
        masters = [c for c in clips if c["role"] == AUDIO]
    if masters:
        master = masters[0]
        for c in clips:
            c["emit_audio"] = c is master
        # AUDIO vazifasidagi fayl faqat ovoz beradi; kamera bo'lsa — ekranda
        # ham qolaveradi, ovozi esa alohida, uzluksiz trek bo'lib ketadi.
        if master["role"] == AUDIO:
            master["emit_video"] = False
        master["audio_segments"] = [
            {"start": int(round(p["start"] * fps)),
             "in": int(round(p["in"] * fps)),
             "out": int(round(p["out"] * fps))}
            for p in master["placements"]]
        log(f"Ovoz manbasi: {master['name']} (butun davomiylik bo'ylab)")

    used = [c for c in clips
            if c["segments"] or (c.get("emit_audio") and c.get("audio_segments"))]
    if not used:
        raise RuntimeError("Hech qaysi kamera ishlatilmadi.")
    for c in clips:
        if not c["segments"] and c["role"] != AUDIO:
            log(f"  Diqqat: {c['name']} umuman ishlatilmadi")

    say(stage="Timeline yozilmoqda", percent=50)
    xml = build_xml(used, name, timebase, ntsc, width, height,
                    single_video_track=True)
    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    log(f"Tayyor: {output}")

    return {
        "output": output,
        "shots": len(shots),
        "total_sec": round(total_sec, 2),
        "together_sec": round(together, 1),
        "quiet_sec": round(quiet, 1),
        "clips": [{"name": c["name"], "path": c["path"], "role": c["role"],
                   "speaker_idx": c["speaker_idx"], "shots": c["shot_count"],
                   "screen_sec": round(sum((s["out"] - s["in"]) for s in c["segments"]) / fps, 1)}
                  for c in clips],
    }


def main():
    ap = argparse.ArgumentParser(
        description="Kim gapirsa o'sha kameraga o'tadigan montaj yasaydi.")
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--output", default="switch.xml")
    ap.add_argument("--name", default="Podcast Suite — Switch")
    ap.add_argument("--roles", help="vergul bilan: speaker,speaker,wide,alt")
    ap.add_argument("--speakers", help="vergul bilan: 0,1,,0 (alt kadr uchun ham)")
    ap.add_argument("--min-shot", type=float, default=DEFAULT_MIN_SHOT)
    ap.add_argument("--max-shot", type=float, default=DEFAULT_MAX_SHOT)
    args = ap.parse_args()

    roles = args.roles.split(",") if args.roles else None
    speakers = ([int(x) if x.strip() != "" else None
                 for x in args.speakers.split(",")] if args.speakers else None)
    try:
        r = run_switch(args.files, roles=roles, speakers=speakers,
                       output=args.output, name=args.name,
                       min_shot=args.min_shot, max_shot=args.max_shot)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"{r['shots']} kadr")
    for c in r["clips"]:
        print(f"  {c['name']:<22} {c['role']:<8} {c['shots']:>3} kadr  "
              f"{c['screen_sec']:>7.1f}s ekranda")


if __name__ == "__main__":
    main()

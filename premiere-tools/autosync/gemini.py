#!/usr/bin/env python3
"""Gemini transkriptini suite arxiviga olib kiradi.

Nima uchun bu shunchalik kichik: transcriber.py chiqaradigan segment
formati suite ichidagi format bilan AYNAN bir xil — {start, end, text},
soniyalarda. Shuning uchun bu yerda quvur qurilmaydi, faqat fayl
o'qiladi va arxivga to'g'ri nom bilan yoziladi.

Arxivga tushgandan keyin uchta narsa o'zi ishlaydi:
    · Captions  — SRT yasash
    · Intro     — lahzalarni matn bo'yicha tanlash
    · Shorts    — matndan tanlash

Kirish sifatida ikki xil fayl qabul qilinadi:
    .srt  — transcriber.py ning odatiy chiqishi
    .json — segment ro'yxati yoki to'liq transkript obyekti

Muhim: transkript QAYSI video faylga tegishli ekani ko'rsatilishi shart.
Suite arxivdan transkriptni aynan shu yo'l bo'yicha topadi — noto'g'ri
bog'lansa, boshqa epizodning matni ishlatilib ketadi.
"""

import json
import os
import re

SRT_VAQT = re.compile(
    r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def _soniya(soat, daq, son, mill):
    return (int(soat) * 3600 + int(daq) * 60 + int(son)
            + int(mill.ljust(3, "0")) / 1000.0)


def srt_oqish(path):
    """SRT faylni {start, end, text} ro'yxatiga aylantiradi."""
    with open(path, encoding="utf-8-sig") as fh:
        xom = fh.read()

    segmentlar = []
    # Bloklar bo'sh qator bilan ajratiladi. Ba'zi dasturlar \r\n yozadi,
    # ba'zilari blok raqamini tashlab ketadi — ikkalasiga ham tayyormiz.
    for blok in re.split(r"\n\s*\n", xom.replace("\r\n", "\n").strip()):
        m = SRT_VAQT.search(blok)
        if not m:
            continue
        matn_qatorlari = []
        korildi = False
        for q in blok.split("\n"):
            if SRT_VAQT.search(q):
                korildi = True
                continue
            if korildi:
                matn_qatorlari.append(q)
        matn = " ".join(x.strip() for x in matn_qatorlari).strip()
        if not matn:
            continue
        segmentlar.append({
            "start": _soniya(*m.groups()[:4]),
            "end": _soniya(*m.groups()[4:]),
            "text": matn,
        })
    return segmentlar


def json_oqish(path):
    """JSON faylni segment ro'yxatiga aylantiradi.

    Ikki shakl qabul qilinadi: sof ro'yxat va {"lines": [...]} obyekti.
    """
    with open(path, encoding="utf-8-sig") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("lines") or data.get("segments") or []
    if not isinstance(data, list):
        raise ValueError("JSON ichida segment ro'yxati topilmadi")
    return [x for x in data if isinstance(x, dict) and "text" in x]


def tozalash(segmentlar):
    """Vaqtlarni tekshiradi va tartibga soladi.

    Gemini ba'zan chegaradosh segmentlarni ustma-ust qo'yib yuboradi
    yoki end < start qilib qaytaradi. Bunday qatorlar keyin timeline'ga
    ko'chirilganda chalkashlik chiqaradi, shuning uchun shu yerda
    to'g'irlanadi.
    """
    toza = []
    for s in segmentlar:
        try:
            a = float(s.get("start", 0))
            b = float(s.get("end", 0))
        except (TypeError, ValueError):
            continue
        matn = str(s.get("text", "")).strip()
        if not matn or a < 0:
            continue
        if b <= a:
            # Uzunligi yo'q segment — matn uzunligiga qarab taxmin
            b = a + max(0.6, len(matn) * 0.06)
        toza.append({"start": round(a, 3), "end": round(b, 3), "text": matn})

    toza.sort(key=lambda x: x["start"])
    for i in range(len(toza) - 1):
        if toza[i]["end"] > toza[i + 1]["start"]:
            toza[i]["end"] = toza[i + 1]["start"]
    return [s for s in toza if s["end"] > s["start"]]


def olib_kirish(fayl, manba, nomi=None, log=print):
    """Gemini transkriptini o'qib, suite arxivi formatiga keltiradi.

    fayl  — .srt yoki .json
    manba — transkript tegishli bo'lgan video/audio fayl yo'li
    """
    if not os.path.isfile(fayl):
        raise ValueError(f"Transkript fayli topilmadi: {fayl}")
    manba = os.path.abspath(manba)
    if not os.path.isfile(manba):
        raise ValueError(f"Video fayl topilmadi: {manba}")

    kengaytma = os.path.splitext(fayl)[1].lower()
    if kengaytma == ".srt":
        xom = srt_oqish(fayl)
    elif kengaytma in (".json", ".txt"):
        xom = json_oqish(fayl)
    else:
        raise ValueError("Faqat .srt yoki .json qabul qilinadi")

    lines = tozalash(xom)
    if not lines:
        raise ValueError("Transkriptda birorta ham qator topilmadi")

    sozlar = sum(len(l["text"].split()) for l in lines)
    davomiylik = lines[-1]["end"]
    log(f"{len(lines)} qator, ~{sozlar} so'z, {davomiylik / 60:.1f} daqiqa")

    return {
        "title": nomi or os.path.splitext(os.path.basename(manba))[0],
        "source": manba,
        "language": "uz",
        "model": "gemini",
        "duration": round(davomiylik, 2),
        "sample": False,
        "from_sequence": False,
        "lines": lines,
        "words": [],           # Gemini so'z darajasida vaqt bermaydi
        "preview": " ".join(l["text"] for l in lines[:6])[:400],
    }


def run_import(fayl, manba, nomi=None, log=print, progress=None):
    """Server chaqiradigan kirish nuqtasi."""
    if progress:
        progress(stage="Transkript o'qilmoqda", percent=20)
    data = olib_kirish(fayl, manba, nomi=nomi, log=log)

    # Arxivga saqlash — captions moduli bilan bir xil joyga, chunki
    # load_transcript aynan o'sha papkadan qidiradi.
    from captions import save_transcript
    if progress:
        progress(stage="Arxivga yozilmoqda", percent=80)
    yol = save_transcript(data, data["title"], log=log)

    if progress:
        progress(stage="Tayyor", percent=100)
    return {"path": yol, "title": data["title"], "source": data["source"],
            "line_count": len(data["lines"]),
            "word_count": sum(len(l["text"].split()) for l in data["lines"]),
            "duration": data["duration"],
            "preview": data["preview"]}

#!/usr/bin/env python3
"""Harakat rejasi — kadr hech qachon uzoq vaqt qotib turmasin.

Muammo: statik kameradan olingan podkastda kadr o'nlab daqiqa qimirlamaydi.
Tomoshabin zerikadi va videoni tashlab ketadi. YouTube'dagi silliq
ko'rinish esa oddiy narsadan chiqadi — kadr doimo sekin harakatda
bo'ladi va har bir plan boshqacha qirqilgan bo'ladi.

Bu modul ana shu rejani tuzadi: qaysi klipda, qaysi soniyada Motion >
Scale qanday bo'lishi kerak. Rejani Premiere'ning o'zida panel qo'llaydi.

Ikki qoida bor:

1. HAR N SONIYADA O'ZGARISH. Kadr N soniyadan ortiq qotib turmaydi.
   N ni foydalanuvchi tanlaydi (10 / 15 / 30 / 60 soniya).

2. HAR PLAN BOSHQACHA. Ketma-ket kliplar bir xil qirqilmaydi — biri
   kengroq, keyingisi tigroq boshlanadi. Aks holda kesish sezilmaydi.

Eng muhimi — SIFAT. Zoom faqat manba sequence'dan kattaroq bo'lsa
sifat yo'qotmaydi: 4K manba 1080p montajda 200% gacha bemalol
kattalashadi. Manbada joy bo'lmasa, bu modul harakatni QO'SHMAYDI va
sababini aytadi — xira kadrdan ko'ra qimirlamagan kadr yaxshi.
"""

import os

from autosync import ffprobe

# Harakat sezilmas darajada sekin bo'lishi kerak. Tajriba shuni
# ko'rsatadi: 8-10 soniyada 4-6% — tomoshabin harakatni sezmaydi, lekin
# kadr «tirik» bo'lib qoladi. Tezroq qilinsa aksincha ta'sir qiladi:
# ko'z charchaydi va bu havaskorlik belgisi bo'lib ko'rinadi.
KUCH = 5.0              # foizda: kadr shuncha kattalashib-kichrayadi
ENG_QISQA_HARAKAT = 6.0  # bundan qisqa oraliqda harakat qilinmaydi
ENG_QISQA_KLIP = 1.2     # bundan qisqa klip umuman tegilmaydi
HARAKAT_ULUSHI = 0.62    # bo'lakning shuncha qismida suriladi, qolgani — tinch
ZAXIRA = 0.99            # manba chegarasiga tegib ketmaslik uchun


def manba_olchami(path, kesh):
    """Faylning ekrandagi o'lchami (burilish hisobga olingan)."""
    key = os.path.abspath(path)
    if key not in kesh:
        try:
            info = ffprobe(key)
            kesh[key] = (info.get("width"), info.get("height"))
        except Exception:
            kesh[key] = (None, None)
    return kesh[key]


def zoom_chegarasi(sw, sh, seq_w, seq_h):
    """Sifat yo'qotmasdan necha barobar kattalashtirsa bo'ladi.

    Manba 3840x2160, montaj 1920x1080 bo'lsa — 2.0, ya'ni 200% gacha
    har bir ekran nuqtasiga kamida bitta manba nuqtasi to'g'ri keladi.
    Manba montaj bilan teng bo'lsa — 1.0, ya'ni joy yo'q.
    """
    if not sw or not sh or not seq_w or not seq_h:
        return 1.0
    return max(1.0, min(sw / float(seq_w), sh / float(seq_h)) * ZAXIRA)


def klip_rejasi(uzunlik, oraliq, kuch, teskari):
    """Bitta klip uchun keyframe ro'yxati.

    Qaytadi: [{"t": klip boshidan soniya, "d": qo'shimcha foiz}]
    «d» — asosiy o'lchamga QO'SHILADIGAN foiz (0 = tegilmagan holat).
    Panel uni klipning hozirgi Scale qiymatiga qo'shadi, shuning uchun
    9:16 ga o'tkazilgan (Scale allaqachon 178%) montaj ham buziladi.
    """
    if uzunlik < ENG_QISQA_KLIP:
        return []
    # Klip qisqa bo'lsa — harakat emas, shunchaki boshqacha qirqim.
    # Uzun klip esa bo'laklarga bo'linadi va har bo'lakda yo'nalish
    # almashadi: kadr sekin yaqinlashadi, keyin sekin uzoqlashadi.
    if uzunlik < ENG_QISQA_HARAKAT:
        return [{"t": 0.0, "d": round(kuch if teskari else 0.0, 2)}]

    bolak = max(ENG_QISQA_HARAKAT, float(oraliq))
    n = max(1, int(round(uzunlik / bolak)))
    qadam = uzunlik / n

    # Ikki narsa harakatni «mexanik» bo'lishdan saqlaydi:
    #
    # 1. TO'XTAB TURISH. Kadr bo'lakning boshida sekin suriladi, keyin
    #    qolgan vaqtda turadi. Doimiy tebranish arra tishiga o'xshaydi
    #    va sun'iy ko'rinadi — haqiqiy montajchi ham surib, keyin qo'yib
    #    yuboradi.
    # 2. TENG BO'LMAGAN KUCH. Har bo'lakda masofa biroz boshqacha.
    #    Aynan bir xil takrorlanish ko'zga tashlanadi.
    keys = []
    oldingi = kuch if teskari else 0.0
    keys.append({"t": 0.0, "d": round(oldingi, 2)})
    for i in range(n):
        t0 = i * qadam
        t1 = min((i + 1) * qadam, uzunlik)
        yuqorida = (i % 2 == 0) != bool(teskari)
        # oltin nisbat bilan 75-100% oralig'ida takrorlanmas o'zgarish
        aralash = 0.75 + 0.25 * ((i * 0.6180339887) % 1.0)
        nishon = round(kuch * aralash, 2) if yuqorida else 0.0
        surish = t0 + (t1 - t0) * HARAKAT_ULUSHI
        if surish <= t0 + 0.4:
            continue
        # Bo'lak boshiga oldingi qiymatni qo'yamiz — shu ikki keyframe
        # orasida kadr TINCH TURADI. Busiz harakatlar bir-biriga ulanib
        # ketadi va kadr to'xtovsiz «suzadi».
        if t0 > keys[-1]["t"] + 0.4:
            keys.append({"t": round(t0, 3), "d": round(oldingi, 2)})
        keys.append({"t": round(surish, 3), "d": round(nishon, 2)})
        oldingi = nishon
    if keys[-1]["t"] < uzunlik - 0.4:
        keys.append({"t": round(uzunlik, 3), "d": round(oldingi, 2)})
    return keys


def harakat_rejasi(clips, seq_w, seq_h, oraliq=15.0, kuch=KUCH, log=print):
    """Butun timeline uchun reja.

    clips: [{"path", "start", "in", "out"}] — video kliplar, timeline
    tartibida. seq_w/seq_h — montaj o'lchami.
    """
    kesh = {}
    rejalar, joysiz = [], []
    # Navbat (kengroq → tigroq → kengroq) timeline tartibida almashishi
    # kerak, panel esa kliplarni trek bo'yicha yuboradi. Shuning uchun
    # bu yerda vaqt bo'yicha saralaymiz, asl o'rnini «idx» da saqlab.
    tartib = sorted(range(len(clips)), key=lambda k: float(clips[k]["start"]))
    for i, asl in enumerate(tartib):
        c = clips[asl]
        uzunlik = float(c["out"]) - float(c["in"])
        if uzunlik <= 0:
            continue
        sw, sh = manba_olchami(c["path"], kesh)
        chegara = zoom_chegarasi(sw, sh, seq_w, seq_h)
        # Mavjud joy foizda: 1.35 → 35% kattalashtirsa bo'ladi
        joy = (chegara - 1.0) * 100.0
        bu_kuch = min(kuch, joy)

        if bu_kuch < 1.0:
            joysiz.append({"path": os.path.basename(c["path"]),
                           "start": round(float(c["start"]), 2),
                           "manba": f"{sw}x{sh}" if sw else "noma'lum"})
            continue

        keys = klip_rejasi(uzunlik, oraliq, bu_kuch, teskari=(i % 2 == 1))
        if not keys:
            continue
        rejalar.append({
            "idx": asl,
            "start": round(float(c["start"]), 3),
            "in": round(float(c["in"]), 3),
            "uzunlik": round(uzunlik, 3),
            "path": c["path"],
            "nomi": os.path.basename(c["path"]),
            "max_k": round(chegara, 4),
            "kuch": round(bu_kuch, 2),
            "keys": keys,
            "harakat": len(keys) > 1,
        })

    harakatli = sum(1 for r in rejalar if r["harakat"])
    log(f"{len(rejalar)} klipga reja tuzildi "
        f"({harakatli} tasida harakat, {len(rejalar) - harakatli} tasida "
        f"faqat boshqacha qirqim)")
    if joysiz:
        log(f"{len(joysiz)} klipga tegilmadi — manba montajdan katta emas, "
            f"kattalashtirsak rasm xiralashadi")
    return {"rejalar": rejalar, "joysiz": joysiz,
            "oraliq": oraliq, "kuch": kuch,
            "stat": {"jami": len(rejalar), "harakatli": harakatli,
                     "joysiz": len(joysiz)}}


def run_harakat(clips, seq_w, seq_h, oraliq=15.0, kuch=KUCH, log=print,
                progress=None):
    """Server chaqiradigan kirish nuqtasi."""
    if progress:
        progress(stage="Manbalar tekshirilmoqda", percent=10)
    if not clips:
        raise ValueError("Klip yo'q — avval «Ochiq sequence'ni olish» ni bosing")
    reja = harakat_rejasi(clips, seq_w, seq_h, oraliq=oraliq, kuch=kuch, log=log)
    if progress:
        progress(stage="Reja tayyor", percent=100)
    return reja

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

SIFAT ikki xil hisoblanadi.

Manba montajdan KATTA bo'lsa (4K manba, 1080p montaj) — zoom 1:1
chegarasigacha ruxsat etiladi, ya'ni sifat umuman yo'qolmaydi.

Manba montajdan KICHIK bo'lsa (gorizontal manbadan vertikal 9:16
montaj) — kadr allaqachon ~178% ga kattalashtirilgan bo'ladi. Bunday
holatda «1:1 dan oshmasin» degan qoida hech qachon bajarilmaydi va
modul umuman ishlamay qolardi. Holbuki 178% dan 183% ga o'tish sifatni
atigi 3% ga o'zgartiradi — buni ko'z ilg'amaydi. Shuning uchun harakat
qo'shiladi, faqat kuchi pasaytiriladi va bu log'da aytiladi.
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

# Manba montajdan KICHIK bo'lganda ham harakat qo'shiladi, faqat kuchi
# pasaytiriladi. Sabab: vertikal montajda (gorizontal manbadan 9:16
# yasalganda) kadr allaqachon ~178% ga kattalashtirilgan bo'ladi va
# «1:1 dan oshmasin» degan qoida hech qachon bajarilmaydi — ya'ni
# modul umuman ishlamay qoladi. Holbuki 178% dan 183% ga o'tish sifatni
# atigi 3% ga o'zgartiradi, buni ko'z ilg'amaydi. Umuman qimirlamagan
# kadrdan ko'ra shu yaxshiroq.
ZAXIRASIZ_KUCH = 3.0

# Ikki xil ish, ikki xil kuch.
#
# «Sekin harakat» — kadr 15 soniyada 5% suriladi. Bu ataylab sezilmas:
# tomoshabin harakatni payqamaydi, lekin kadr «tirik» bo'lib qoladi.
#
# «Kesimda» — har plan boshqa masofadan boshlanadi. Bu KO'RINISHI kerak,
# aks holda kesim sezilmaydi va butun ishning ma'nosi qolmaydi. Shuning
# uchun kuch bir necha barobar katta.
KUCHLAR = {
    "kesim": {"yumshoq": 8.0, "orta": 14.0, "kuchli": 22.0},
    "sekin": {"yumshoq": 3.0, "orta": 5.0, "kuchli": 8.0},
}
# Manba montajdan kichik bo'lganda ham foydalanuvchi tanlagan kuch
# qoladi — faqat aqldan tashqari qiymatlar kesiladi. Sabab: bu yerda
# «sifat yo'qoladi/yo'qolmaydi» degan chegara yo'q, bosqichma-bosqich
# yumshaydi xolos. Shuning uchun jimgina pasaytirmaymiz, balki
# natijada kadr manbadan NECHA BAROBAR kattalashishini aytamiz —
# qaror foydalanuvchiniki.
TOR_KESIM_CHEK = 25.0

# Ketma-ket kliplar QANCHALIK farq qilishi. Har son «kuch» ga
# ko'paytiriladi. Ro'yxat shunday tanlanganki, yonma-yon turgan ikki
# son hech qachon yaqin bo'lmaydi — eng kichik farq 0.45 × kuch.
KESIM_ULUSHLARI = (0.0, 1.0, 0.45, 0.9, 0.25, 0.7)


def kesim_ulushi(i):
    """i-klip uchun qirqim ulushi (0..1)."""
    return KESIM_ULUSHLARI[i % len(KESIM_ULUSHLARI)]


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


def harakat_rejasi(clips, seq_w, seq_h, oraliq=15.0, kuch=KUCH, log=print,
                   rejim="kesim", daraja="orta"):
    """Butun timeline uchun reja.

    clips: [{"path", "start", "in", "out"}] — video kliplar, timeline
    tartibida. seq_w/seq_h — montaj o'lchami.
    """
    kesh = {}
    rejalar, joysiz, tor_manba = [], [], []
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

        if not sw or not sh:
            # Faylni umuman o'qib bo'lmadi — tegmaymiz
            joysiz.append({"path": os.path.basename(c["path"]),
                           "start": round(float(c["start"]), 2),
                           "manba": "o'qilmadi"})
            continue

        tordan = joy < 1.0
        if tordan:
            tor_manba.append(f"{sw}x{sh}")

        # Har rejim o'z kuchini oladi. Kesim rejimida kuch bir necha
        # barobar katta — chunki u KO'RINISHI kerak.
        kesim_k = KUCHLAR["kesim"].get(daraja, 14.0)
        sekin_k = KUCHLAR["sekin"].get(daraja, 5.0)
        if tordan:
            kesim_k = min(kesim_k, TOR_KESIM_CHEK)
            sekin_k = min(sekin_k, ZAXIRASIZ_KUCH)
        else:
            kesim_k = min(kesim_k, joy)
            sekin_k = min(sekin_k, joy)

        keys = []
        if rejim in ("kesim", "ikkala"):
            # Bitta qiymat — butun klip shu masofada turadi. Keyframe
            # kerak emas, ya'ni Premiere API'sining keyframe qismiga
            # umuman bog'liq emas.
            asos_d = round(kesim_k * kesim_ulushi(i), 2)
            keys = [{"t": 0.0, "d": asos_d}]
        if rejim in ("sekin", "ikkala"):
            sekin = klip_rejasi(uzunlik, oraliq, sekin_k, teskari=(i % 2 == 1))
            if rejim == "ikkala" and keys:
                # Qirqim ustiga sekin harakat qo'shiladi
                asos_d = keys[0]["d"]
                keys = [{"t": k["t"], "d": round(asos_d + k["d"], 2)}
                        for k in sekin] or keys
            else:
                keys = sekin
        if not keys:
            continue
        bu_kuch = kesim_k if rejim != "sekin" else sekin_k
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
            "tor": tordan,
        })

    harakatli = sum(1 for r in rejalar if r["harakat"])
    torlar = sum(1 for r in rejalar if r.get("tor"))
    nomi = {"kesim": "har kesimda boshqa qirqim",
            "sekin": "sekin harakat",
            "ikkala": "qirqim + sekin harakat"}.get(rejim, rejim)
    log(f"Rejim: {nomi}")
    if rejalar:
        qiymatlar = sorted({r["keys"][0]["d"] for r in rejalar[:12]})
        log(f"{len(rejalar)} klipga reja tuzildi. Qirqim qiymatlari: "
            + ", ".join(f"+{q:.0f}%" for q in qiymatlar))
    if torlar and rejalar:
        olcham = tor_manba[0] if tor_manba else "?"
        # Kadr manbadan necha barobar kattalashayotganini aniq aytamiz:
        # «sifat tushadi» degan mavhum gapdan ko'ra raqam foydali.
        try:
            sw, sh = [int(x) for x in olcham.split("x")]
            hozir = max(seq_w / float(sw), seq_h / float(sh))
        except Exception:
            hozir = 1.0
        eng = max(r["keys"][0]["d"] for r in rejalar)
        log(f"Manba montajdan kichik ({olcham} → {seq_w}x{seq_h}). Kadr "
            f"hozir manbadan {hozir:.2f} barobar kattalashtirilgan, "
            f"eng tig qirqimda {hozir * (1 + eng / 100):.2f} barobar "
            f"bo'ladi.")
    if joysiz:
        log(f"{len(joysiz)} klipning o'lchami o'qilmadi — tegilmadi")
    return {"rejalar": rejalar, "joysiz": joysiz,
            "oraliq": oraliq, "kuch": kuch,
            "stat": {"jami": len(rejalar), "harakatli": harakatli,
                     "tor": torlar, "joysiz": len(joysiz)}}


def run_harakat(clips, seq_w, seq_h, oraliq=15.0, kuch=KUCH, log=print,
                progress=None, rejim="kesim", daraja="orta"):
    """Server chaqiradigan kirish nuqtasi."""
    if progress:
        progress(stage="Manbalar tekshirilmoqda", percent=10)
    if not clips:
        raise ValueError("Klip yo'q — avval «Ochiq sequence'ni olish» ni bosing")
    reja = harakat_rejasi(clips, seq_w, seq_h, oraliq=oraliq, kuch=kuch,
                          log=log, rejim=rejim, daraja=daraja)
    if progress:
        progress(stage="Reja tayyor", percent=100)
    return reja

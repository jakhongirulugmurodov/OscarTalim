#!/usr/bin/env python3
"""Matn — yozilgan matnlarni silliq animatsiya bilan kadr ustiga qo'yadi.

Foydalanish (terminaldan):
    python3 matn.py --matn "Jahongir Ulug'murodov|prodyuser" --vaqt 12.5 \\
                    --davomiylik 5 -o matnlar.xml

Nima qiladi: har matn uchun SHAFFOF fonli qisqa video yasaydi (faqat matn
ko'rinadi, orqasi bo'sh) va ularni timeline'dagi kerakli joyga qo'yadigan
XML yozadi. Premiere'da bu kliplarni video trekka tashlasangiz, ostidagi
kadr ko'rinib turadi.

Animatsiya haqida ataylab qilingan tanlov
-----------------------------------------
Tomoshabin matnning CHIQQANINI sezmasligi kerak — «yo'q edi, bor bo'ldi».
Shuning uchun:

  * masofa kichik (28 px), sakrash yo'q;
  * tezlik sekinlashib boradi (ease-out): boshida tez, oxirida deyarli
    to'xtagan — ko'z chegarani ilg'amaydi, harakat «qo'nadi»;
  * chiqqandan keyin piksel ham qimirlamaydi (o'lchab tekshirilgan);
  * kattalashish, aylanish, sakrash, so'z-ma-so'z chiqish YO'Q.

O'qilishi uchun matn ostiga yumshoq soya va nozik kontur qo'yiladi: shu
ikkisi matnni har qanday kadr ustida o'qiladigan qiladi, lekin ko'zga
tashlanmaydi.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import (FFMPEG, FFMPEG_YOQ, build_xml, fps_to_timebase,
                      write_xml)

# --- Animatsiya vaqtlari (soniya) ---------------------------------------
# Sinovda o'lchangan: 0.55s da harakat to'xtaydi, keyin mutlaqo qimirlamaydi.
KIRISH = 0.55         # ochilish + ko'tarilish
CHIQISH = 0.45        # so'nish
SILJISH = 28          # necha piksel pastdan ko'tariladi

# --- Joylashuv: kadr balandligining necha ulushida turadi ----------------
JOYLAR = {
    "past": 0.78,     # eng ko'p ishlatiladigan — lower third
    "orta": 0.50,
    "tepa": 0.14,
}

# --- Uslub standartlari --------------------------------------------------
STANDART = {
    "shrift": None,        # topilganidan birinchisi
    "olcham": 58,          # 1080x1920 uchun; boshqa o'lchamda moslanadi
    "rang": "#FFFFFF",
    "qalin": True,
    "joy": "past",
    "kontur": 5,           # matn atrofidagi qora chiziq (0 = yo'q)
    "soya": 3,             # pastga soya (0 = yo'q)
    "qator_oraligi": 14,
}

# macOS'da shriftlar shu papkalarda turadi. ffmpeg'imizda fontconfig yo'q,
# shuning uchun shrift NOMI emas, FAYLI kerak — papkalarni o'zimiz qidiramiz.
SHRIFT_PAPKALARI = (
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/Library/Fonts",
    os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts",                       # Linux (sinov uchun)
)

# Podcast sarlavhasi uchun yaxshi ko'rinadigan va o'zbekcha harflarni
# qo'llaydigan shriftlar — ro'yxatning boshida shular tursin.
TAVSIYA = ("Helvetica", "HelveticaNeue", "Arial", "AvenirNext", "Avenir",
           "SFProDisplay", "SFNS", "Futura", "GillSans", "Optima",
           "Verdana", "Tahoma", "TrebuchetMS", "Georgia", "Palatino",
           "DejaVuSans", "Times New Roman")


# Qalinlik/uslub belgilari — oila nomiga kirmasligi kerak, aks holda
# «FreeSans» va «FreeSansBold» ikki xil oila bo'lib ko'rinadi.
OGIRLIK = ("bold", "semibold", "demibold", "heavy", "black", "medium",
           "regular", "roman", "book", "mt", "ms")


def _nom(path):
    """Fayl nomidan oila nomi: «HelveticaNeue-Bold.ttf» → «Helvetica Neue»."""
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.split(r"[-_]", base)[0]
    base = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base).strip() or base
    sozlar = base.split()
    while len(sozlar) > 1 and sozlar[-1].lower() in OGIRLIK:
        sozlar.pop()
    return " ".join(sozlar) or base


def shriftlar():
    """Kompyuterdagi shriftlar ro'yxati (nomi + fayli + qalin varianti).

    ffmpeg'da fontconfig yo'q, shuning uchun «Helvetica» deb yozib
    bo'lmaydi — aniq fayl yo'li kerak. Shu sababli papkalarni o'zimiz
    ko'rib chiqamiz va har oila uchun oddiy/qalin faylini juftlaymiz.
    """
    oila = {}
    for papka in SHRIFT_PAPKALARI:
        if not os.path.isdir(papka):
            continue
        for root, _dirs, files in os.walk(papka):
            for f in sorted(files):
                if not f.lower().endswith((".ttf", ".otf", ".ttc")):
                    continue
                path = os.path.join(root, f)
                nom = _nom(path)
                low = f.lower()
                # Kursiv/ingichka variantlar ro'yxatni chalkashtiradi
                if any(k in low for k in ("italic", "oblique", "thin",
                                          "light", "ultralight")):
                    continue
                rec = oila.setdefault(nom, {"nom": nom, "oddiy": None,
                                            "qalin": None})
                if "bold" in low or "semibold" in low or "heavy" in low:
                    rec["qalin"] = rec["qalin"] or path
                else:
                    rec["oddiy"] = rec["oddiy"] or path

    out = [r for r in oila.values() if r["oddiy"] or r["qalin"]]

    def tartib(r):
        siqiq = r["nom"].replace(" ", "")
        for i, t in enumerate(TAVSIYA):
            if siqiq.lower() == t.replace(" ", "").lower():
                return (0, i, r["nom"])
        return (1, 0, r["nom"])

    out.sort(key=tartib)
    for r in out:
        r["tavsiya"] = tartib(r)[0] == 0
    return out


def shrift_fayli(nom, qalin=True):
    """Shrift nomidan aniq fayl yo'li. Topilmasa — birinchi mavjudi."""
    hammasi = shriftlar()
    if not hammasi:
        raise RuntimeError(
            "Kompyuterda shrift fayli topilmadi. Odatda bunday bo'lmaydi — "
            "motorni qayta ishga tushiring.")
    tanlangan = None
    if nom:
        siqiq = str(nom).replace(" ", "").lower()
        for r in hammasi:
            if r["nom"].replace(" ", "").lower() == siqiq:
                tanlangan = r
                break
    tanlangan = tanlangan or hammasi[0]
    if qalin:
        return tanlangan["qalin"] or tanlangan["oddiy"]
    return tanlangan["oddiy"] or tanlangan["qalin"]


# ------------------------------------------------------------ render qismi

def _rang(hex_str, alpha=None):
    """«#FFCC00» → ffmpeg rangi. alpha berilsa «0xFFCC00@0.7» ko'rinishida."""
    s = str(hex_str or "#FFFFFF").strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        s = "FFFFFF"
    return f"0x{s.upper()}" + (f"@{alpha}" if alpha is not None else "")


def _ifoda(davomiylik):
    """Ochilish/so'nish va ko'tarilish ifodalari (ffmpeg expression).

    Ko'tarilish ease-out cubic: 1-(1-p)^3. Boshida tez, oxirida to'xtagan —
    aynan shuning uchun harakat sezilmaydi.
    """
    d = float(davomiylik)
    chiqish_boshi = max(d - CHIQISH, KIRISH)
    ease = f"(1-pow(1-min(1\\,t/{KIRISH})\\,3))"
    alpha = (f"if(lt(t,{KIRISH}), t/{KIRISH},"
             f" if(gt(t,{chiqish_boshi}), max(0,({d}-t)/{CHIQISH}), 1))")
    return ease, alpha


def _olcham(baza, width, height):
    """Shrift o'lchamini kadrga moslaydi — kadrning TOR tomoni bo'yicha.

    Nega tor tomoni: matn eniga sig'ishi kerak. Balandlikka bog'lasak,
    vertikal (1080x1920) kadrda o'lcham ikki barobar oshib ketadi va
    oddiy ism ham sig'may, uch qatorga bo'linib ketadi — sinovda aynan
    shunday bo'ldi. Tor tomonga bog'laganda 1920x1080 ham, 1080x1920 ham
    bir xil o'lchamda chiqadi: montajchi kutgani ham shu.

    Tayanch — 1080: «O'rtacha 58» degani ikkala kadrda ham 58 px.
    """
    return max(12, int(round(float(baza) * (min(width, height) / 1080.0))))


# Matn kadrning shuncha ulushidan chiqmasligi kerak
ENG_KENG = 0.88
ENG_BALAND = 0.42


def drawtext_zanjiri(qatorlar, fayl, olcham, oraliq, joy, u, tmp_dir,
                     y_qoshimcha="", alpha=None):
    """Har qator uchun ALOHIDA drawtext — shunda har biri markazda turadi.

    Nega kerak: drawtext ko'p qatorli matnni bitta blok qilib chizadi va
    faqat blokni markazlashtiradi, qatorlarni esa chapga tekislaydi.
    Natijada markazga qo'yilgan matnning chap cheti tekis, o'ng cheti
    tishli bo'lib qoladi — ko'z buni «biror narsa noto'g'ri» deb oladi.
    Har qatorni alohida chizsak, har biri o'z eni bo'yicha markazlashadi.
    """
    filtrlar = []
    for i, qator in enumerate(qatorlar):
        if not qator.strip():
            continue
        txt = os.path.join(tmp_dir, f"q{i}.txt")
        with open(txt, "w", encoding="utf-8") as fh:
            fh.write(qator)
        y = f"h*{joy}+{i * (olcham + oraliq)}"
        if y_qoshimcha:
            y += y_qoshimcha
        qismlar = [
            f"fontfile={fayl}", f"textfile={txt}",
            f"fontcolor={_rang(u.get('rang'))}", f"fontsize={olcham}",
            "x=(w-tw)/2", f"y={y}",
        ]
        if alpha:
            qismlar.append(f"alpha='{alpha}'")
        if int(u.get("kontur", 0) or 0) > 0:
            qismlar += [f"borderw={int(u['kontur'])}", "bordercolor=black@0.7"]
        if int(u.get("soya", 0) or 0) > 0:
            qismlar += ["shadowx=0", f"shadowy={int(u['soya'])}",
                        "shadowcolor=black@0.5"]
        filtrlar.append("drawtext=" + ":".join(qismlar))
    return ",".join(filtrlar) if filtrlar else "null"


def _matn_olchovi(text, u, olcham, width, height):
    """Matn shu o'lchamda necha piksel joy egallaydi (eni, bo'yi).

    Muhim tafsilot: o'lchash KENG bo'sh joyda ketadi. Aks holda kadrga
    sig'magan matn chetidan kesiladi va o'lchov «aynan kadr eni» bo'lib
    chiqadi — qancha oshib ketgani bilinmaydi, moslash esa ishlamaydi.

    Shrift metrikasini o'zimiz o'qimaymiz: bitta kadr chizib, alfa
    kanalining chegaralari o'lchanadi. Bu har qanday shrift va har qanday
    harf uchun to'g'ri ishlaydi (o'zbekcha gʻ, oʻ ham).
    """
    import tempfile
    import numpy as np

    KENG, BALAND = 6000, 2000        # matn bemalol sig'adigan bo'sh joy
    fayl = shrift_fayli(u.get("shrift"), bool(u.get("qalin", True)))
    with tempfile.TemporaryDirectory() as tmp:
        txt = os.path.join(tmp, "t.txt")
        with open(txt, "w", encoding="utf-8") as fh:
            fh.write(text)
        qismlar = [
            f"fontfile={fayl}", f"textfile={txt}",
            "fontcolor=white", f"fontsize={olcham}",
            f"line_spacing={_olcham(u.get('qator_oraligi', 14), width, height)}",
            "x=(w-tw)/2", "y=(h-th)/2",
        ]
        if int(u.get("kontur", 0) or 0) > 0:
            qismlar += [f"borderw={int(u['kontur'])}", "bordercolor=black"]
        raw = os.path.join(tmp, "f.raw")
        cmd = [FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i",
               f"color=c=black@0.0:s={KENG}x{BALAND},format=yuva420p",
               "-vf", "drawtext=" + ":".join(qismlar),
               "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", raw]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            return 0, 0                    # o'lchay olmadik — tegmaymiz
        a = np.fromfile(raw, dtype=np.uint8)
        if a.size < KENG * BALAND * 4:
            return 0, 0
        al = a[:KENG * BALAND * 4].reshape(BALAND, KENG, 4)[:, :, 3]
        xs = np.where(al.max(axis=0) > 8)[0]
        ys = np.where(al.max(axis=1) > 8)[0]
        if not len(xs) or not len(ys):
            return 0, 0
        return int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def moslangan_olcham(text, width, height, u, log=print):
    """Matn kadrdan chiqib ketmasligi uchun o'lchamni kamaytiradi.

    Uzun ism yoki iqtibos yozilganda matn kadr chetiga urilib, yarmi
    ko'rinmay qolardi — tomoshabin uchun bu eng ko'zga tashlanadigan xato.

    Matn eni shrift o'lchamiga TO'G'RI proporsional, shuning uchun bir
    marta o'lchab, kerakli o'lchamni to'g'ridan-to'g'ri hisoblaymiz —
    urinib ko'rish shart emas.
    """
    soralgan = _olcham(u.get("olcham", 58), width, height)
    olchov = 60                                   # tayanch o'lcham
    tw, th = _matn_olchovi(text, u, olchov, width, height)
    if tw <= 0 or th <= 0:
        return soralgan

    sigadigan_w = olchov * (ENG_KENG * width) / tw
    sigadigan_h = olchov * (ENG_BALAND * height) / th
    olcham = int(min(soralgan, sigadigan_w, sigadigan_h))
    olcham = max(12, olcham)
    if olcham < soralgan:
        log(f"    matn kadrga sig'sin deb o'lcham {soralgan} → {olcham} px")
    return olcham


MAX_QATOR = 4          # bundan ko'pi ekranni to'sib qo'yadi


def qatorlarga_bolish(text, width, height, u, log=print):
    """Uzun matnni kadr eniga qarab qatorlarga bo'ladi.

    Nega kerak: uzun iqtibos bitta qatorga sig'masa, faqat o'lchamni
    kichraytirsak matn o'qib bo'lmaydigan darajaga tushib ketadi (sinovda
    27 px gacha). To'g'ri yechim — qatorga bo'lish: o'lcham saqlanadi,
    matn esa ikki-uch qatorda tinch turadi.

    Foydalanuvchi o'zi Enter bosgan joylar saqlanadi — faqat juda uzun
    qatorlar bo'linadi.
    """
    soralgan = _olcham(u.get("olcham", 58), width, height)
    sigadi = ENG_KENG * width

    # Avval bir oz kichraytirib ko'ramiz, keyin bo'lamiz. Aks holda ism
    # ham ikkiga bo'linib ketadi — «Jahongir / Ulugʻmurodov» degani esa
    # oddiy kichraytirishdan yomonroq ko'rinadi. Chegarasi: o'lchamning
    # eng ko'pi bilan 28% ini yo'qotamiz, undan ortig'i o'qishga xalaqit
    # beradi va o'shanda qatorga bo'lish afzal.
    SIQISH = 0.72
    bolish_chegarasi = sigadi / SIQISH

    natija = []
    for para in str(text).split("\n"):
        sozlar = para.split()
        if not sozlar:
            natija.append("")
            continue
        tw, _th = _matn_olchovi(para, u, soralgan, width, height)
        if tw <= 0 or tw <= bolish_chegarasi:
            natija.append(para)      # kichraytirish yetadi — bo'lmaymiz
            continue
        # Bitta o'lchovdan o'rtacha belgi eni chiqadi — shu bilan har
        # qatorga nechta belgi sig'ishini bilamiz (aniq emas, lekin
        # keyin o'lcham baribir tekshiriladi).
        belgi_en = tw / max(1, len(para))
        budjet = max(6, int(sigadi / belgi_en))
        qator = ""
        for soz in sozlar:
            sinov = (qator + " " + soz).strip()
            if not qator or len(sinov) <= budjet:
                qator = sinov
            else:
                natija.append(qator)
                qator = soz
        if qator:
            natija.append(qator)

    if len(natija) > MAX_QATOR:
        log(f"    matn {len(natija)} qator chiqdi — o'lcham kichraytiriladi")
    yangi = "\n".join(natija)
    if yangi != text:
        log(f"    matn {len(natija)} qatorga bo'lindi")
    return yangi


def render_matn(text, out_path, width, height, fps, davomiylik,
                uslub=None, log=print):
    """Bitta matn uchun shaffof fonli video yasaydi."""
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)
    u = dict(STANDART, **(uslub or {}))

    text = (text or "").strip()
    if not text:
        raise RuntimeError("Matn bo'sh.")

    text = qatorlarga_bolish(text, width, height, u, log=log)
    fayl = shrift_fayli(u.get("shrift"), bool(u.get("qalin", True)))
    olcham = moslangan_olcham(text, width, height, u, log=log)
    oraliq = _olcham(u.get("qator_oraligi", 14), width, height)
    joy = JOYLAR.get(u.get("joy", "past"), JOYLAR["past"])
    ease, alpha = _ifoda(davomiylik)

    # Matn buyruq satriga emas, faylga yoziladi: o'zbekchada apostrof ko'p,
    # uni har xil qochirishlar bilan o'tkazish xatoga olib keladi.
    tmp = tempfile.mkdtemp(prefix="matn-")
    try:
        vf = drawtext_zanjiri(text.split("\n"), fayl, olcham, oraliq, joy, u,
                              tmp, y_qoshimcha=f"-{SILJISH}*{ease}",
                              alpha=alpha)
        cmd = [
            FFMPEG, "-v", "error", "-y",
            "-f", "lavfi", "-i",
            f"color=c=black@0.0:s={width}x{height}:r={fps}:d={davomiylik:.3f},"
            "format=yuva420p",
            "-vf", vf,
            # QuickTime Animation — alfa (shaffoflik) bilan, yo'qotishsiz va
            # ProRes 4444 dan ~4 barobar kichik (o'lchangan: 5 MB / 22 MB).
            "-c:v", "qtrle", "-pix_fmt", "argb",
            out_path,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        raise RuntimeError(f"Matn yasalmadi: {r.stderr.strip()[:300]}")
    return out_path


def oldin_korish(text, out_png, width, height, uslub=None, kadr=None):
    """Bitta PNG — panelda «shunday ko'rinadi» deb ko'rsatish uchun.

    Shaffof emas, tekshirish uchun kulrang fon beriladi: oq matn oq fonda
    ko'rinmay qolmasin.
    """
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)
    u = dict(STANDART, **(uslub or {}))
    text = qatorlarga_bolish((text or "").strip() or " ", width, height, u,
                             log=lambda *a: None)
    fayl = shrift_fayli(u.get("shrift"), bool(u.get("qalin", True)))
    olcham = moslangan_olcham(text, width, height, u, log=lambda *a: None)
    oraliq = _olcham(u.get("qator_oraligi", 14), width, height)
    joy = JOYLAR.get(u.get("joy", "past"), JOYLAR["past"])

    tmp = tempfile.mkdtemp(prefix="matn-oldin-")
    try:
        vf = drawtext_zanjiri(text.split("\n"), fayl, olcham, oraliq, joy, u, tmp)
        fon = kadr if (kadr and os.path.isfile(kadr)) else None
        cmd = [FFMPEG, "-v", "error", "-y"]
        if fon:
            cmd += ["-i", fon, "-vf", f"scale={width}:{height}," + vf]
        else:
            cmd += ["-f", "lavfi", "-i", f"color=c=0x3A3B42:s={width}x{height}",
                    "-vf", vf]
        cmd += ["-frames:v", "1", out_png]
        r = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if r.returncode != 0:
        raise RuntimeError(f"Ko'rish rasmi yasalmadi: {r.stderr.strip()[:300]}")
    return out_png


# ------------------------------------------------------------------- XML

def kesishadimi(bloklar):
    """Matnlar vaqt bo'yicha ustma-ust tushadimi?

    Bitta video trekda ikki klip ustma-ust tursa, Premiere XML'ni buzuq
    deb qabul qiladi. Shuning uchun kesishgan holatda har matn o'z
    trekiga chiqariladi.
    """
    tartib = sorted(bloklar, key=lambda x: x["start"])
    for oldingi, keyingi in zip(tartib, tartib[1:]):
        if oldingi["start"] + oldingi["davomiylik"] > keyingi["start"] + 1e-6:
            return True
    return False


def matn_kliplari(bloklar, timebase, width, height):
    """Render qilingan .mov fayllarni build_xml kutgan ko'rinishga keltiradi."""
    clips = []
    for b in sorted(bloklar, key=lambda x: x["start"]):
        clips.append({
            "name": b["name"], "path": b["path"],
            "has_video": True, "has_audio": False,
            "width": width, "height": height,
            "fps": timebase, "duration": b["davomiylik"],
            "audio_rate": 48000, "audio_channels": 2,
            "dur_frames": b["frames"],
            "start_frame": b["start_frame"],
            "segments": [{"start": b["start_frame"], "in": 0,
                          "out": b["frames"]}],
        })
    return clips


# ------------------------------------------------------------------ oqim

def run_matn(bloklar, output="matnlar.xml", name="Podcast Suite — Matn",
             width=1920, height=1080, fps=25.0, uslub=None, outdir=None,
             fallback=None, log=print, progress=None):
    """Matnlarni render qilib, timeline'ga qo'yadigan XML yozadi.

    `bloklar` — [{"matn": "...", "start": 12.5, "davomiylik": 5.0,
                  "uslub": {...ixtiyoriy...}}]
    """
    say = progress or (lambda **k: None)
    bloklar = [b for b in (bloklar or []) if str(b.get("matn", "")).strip()]
    if not bloklar:
        raise RuntimeError("Bironta ham matn yozilmagan.")

    outdir = outdir or os.path.join(os.path.dirname(os.path.abspath(output)),
                                    "matn-kliplari")
    os.makedirs(outdir, exist_ok=True)
    timebase, ntsc = fps_to_timebase(fps)

    log(f"{len(bloklar)} ta matn · {width}x{height} · {timebase}fps")
    tayyor = []
    for i, b in enumerate(sorted(bloklar, key=lambda x: float(x.get("start", 0))),
                          start=1):
        matn = str(b["matn"]).strip()
        start = max(0.0, float(b.get("start", 0)))
        dav = max(KIRISH + CHIQISH + 0.4, float(b.get("davomiylik", 5.0)))
        say(stage="Matnlar yasalmoqda", percent=(i - 1) / len(bloklar) * 100,
            detail=f"{i}/{len(bloklar)}: {matn.splitlines()[0][:28]}")

        nom = f"Matn {i:02d}.mov"
        path = os.path.join(outdir, nom)
        render_matn(matn, path, width, height, timebase, dav,
                    uslub=dict(uslub or {}, **(b.get("uslub") or {})), log=log)
        frames = int(round(dav * timebase))
        tayyor.append({
            "path": path, "name": nom, "matn": matn,
            "start": start, "davomiylik": round(dav, 3),
            "start_frame": int(round(start * timebase)), "frames": frames,
        })
        mm, ss = divmod(int(start), 60)
        log(f"  {i:02d}. {mm:02d}:{ss:02d} · {dav:.1f}s · "
            f"«{matn.splitlines()[0][:40]}»")

    say(stage="Timeline yozilmoqda", percent=95)
    # Kesishmasa — hammasi bitta trekda (toza timeline). Kesishsa — har
    # matn o'z trekiga chiqadi, aks holda Premiere XML'ni buzuq deb biladi.
    ustma_ust = kesishadimi(tayyor)
    if ustma_ust:
        log("  ba'zi matnlar vaqt bo'yicha ustma-ust — har biri alohida "
            "trekka qo'yildi")
    clips = matn_kliplari(tayyor, timebase, width, height)
    xml = build_xml(clips, name, timebase, ntsc, width, height,
                    single_video_track=not ustma_ust)
    output = write_xml(xml, output, fallback, log)
    say(percent=100, detail="tayyor")
    log(f"Tayyor: {output}")
    log(f"Kliplar: {outdir}")

    return {
        "output": output, "outdir": outdir,
        "count": len(tayyor),
        "clips": [{"name": t["name"], "path": t["path"], "matn": t["matn"],
                   "start": t["start"], "davomiylik": t["davomiylik"]}
                  for t in tayyor],
        "format": {"width": width, "height": height, "fps": round(fps, 3)},
    }


def main():
    ap = argparse.ArgumentParser(
        description="Matnlarni silliq animatsiya bilan kadr ustiga qo'yadi.")
    ap.add_argument("--matn", action="append", default=[],
                    help="matn (yangi qator uchun |), bir necha marta berish mumkin")
    ap.add_argument("--vaqt", action="append", type=float, default=[],
                    help="har matnning boshlanish vaqti (soniya)")
    ap.add_argument("--davomiylik", type=float, default=5.0)
    ap.add_argument("--olcham", default="1920x1080")
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--shrift", default=None)
    ap.add_argument("--joy", default="past", choices=sorted(JOYLAR))
    ap.add_argument("--shriftlar", action="store_true",
                    help="kompyuterdagi shriftlar ro'yxatini ko'rsatadi")
    ap.add_argument("-o", "--output", default="matnlar.xml")
    args = ap.parse_args()

    if args.shriftlar:
        for r in shriftlar():
            belgi = "*" if r["tavsiya"] else " "
            print(f" {belgi} {r['nom']}")
        return

    w, _, h = args.olcham.partition("x")
    bloklar = [{"matn": m.replace("|", "\n"),
                "start": args.vaqt[i] if i < len(args.vaqt) else i * 8.0,
                "davomiylik": args.davomiylik}
               for i, m in enumerate(args.matn)]
    try:
        r = run_matn(bloklar, output=args.output, width=int(w), height=int(h),
                     fps=args.fps, uslub={"shrift": args.shrift,
                                          "joy": args.joy})
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"{r['count']} matn → {r['output']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Elektr balansini HET shaxsiy kabinetidan (cabinet.het.uz) olish.

Nega brauzer orqali: kabinetning ochiq API'si yo'q, ichki so'rovlari esa
istalgan payt o'zgarishi mumkin. Shuning uchun haqiqiy brauzer (Playwright)
sahifani o'zingiz ko'rgandek ochadi, sessiya esa alohida profilda saqlanadi.
Parol hech qayerga yozilmaydi: siz bir marta qo'lda kirasiz, keyin skript
o'sha sessiyadan foydalanadi. Sessiya tugasa — «kirish_kerak» holati qaytadi.

Rejimlar:
    python3 tekshir.py kirish   # brauzer oynasi ochiladi, qo'lda kirasiz
    python3 tekshir.py          # yashirin tekshiruv, natija JSON ko'rinishida

Muhit o'zgaruvchilari (hammasi ixtiyoriy):
    ELEKTR_URL      kabinet manzili (standart: https://cabinet.het.uz/)
    ELEKTR_PAPKA    profil va natijalar papkasi (standart: ~/.elektr)
    ELEKTR_KANAL    brauzer: chrome (standart) | msedge | chromium
"""
import json
import os
import re
import sys
import time
from pathlib import Path

PAPKA = Path(os.environ.get("ELEKTR_PAPKA") or Path.home() / ".elektr")
PROFIL = PAPKA / "profil"
NATIJA = PAPKA / "natija.json"
JAVOBLAR = PAPKA / "oxirgi_javoblar.json"
URL = os.environ.get("ELEKTR_URL", "https://cabinet.het.uz/")
KANAL = os.environ.get("ELEKTR_KANAL", "chrome")

# Balans/qarz maydonlarini tanish uchun kalit so'zlar (o'zbek, ingliz, rus).
KALITLAR = ("balans", "balance", "saldo", "qarz", "debt", "dolg",
            "баланс", "сальдо", "долг", "задолж", "qoldiq")
SON = re.compile(r"[-−–]?\s?\d{1,3}(?:[   ,]\d{3})*(?:[.,]\d{1,2})?|[-−–]?\d+(?:[.,]\d{1,2})?")


def _son(matn):
    """'−125 400,50' → -125400.5"""
    s = str(matn).strip().replace("−", "-").replace("–", "-")
    s = re.sub(r"[   ]", "", s)
    if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
        s = s.replace(",", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def jsondan_top(obj, yol=""):
    """JSON ichidan nomida kalit so'z bor sonli maydonlarni topadi."""
    topilgan = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            ichki = f"{yol}.{k}" if yol else str(k)
            if isinstance(v, (dict, list)):
                topilgan += jsondan_top(v, ichki)
            elif any(s in str(k).lower() for s in KALITLAR):
                son = v if isinstance(v, (int, float)) and not isinstance(v, bool) else _son(v)
                if son is not None:
                    topilgan.append({"maydon": ichki, "summa": float(son)})
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            topilgan += jsondan_top(v, f"{yol}[{i}]")
    return topilgan


def matndan_top(matn):
    """Sahifa matnidan kalit so'z bor qatordagi summani topadi."""
    qatorlar = [q.strip() for q in matn.splitlines() if q.strip()]
    for i, q in enumerate(qatorlar):
        if not any(s in q.lower() for s in KALITLAR):
            continue
        # Summa shu qatorda yoki keyingi qatorda bo'lishi mumkin.
        for nomzod in (q, " ".join(qatorlar[i:i + 2])):
            for m in SON.finditer(nomzod):
                son = _son(m.group())
                if son is not None and (abs(son) >= 100 or son == 0):
                    return {"maydon": q[:80], "summa": son}
    return None


def _brauzer(p, yashirin):
    PROFIL.mkdir(parents=True, exist_ok=True)
    sozlama = dict(user_data_dir=str(PROFIL), headless=yashirin,
                   locale="uz-UZ", viewport={"width": 1280, "height": 900})
    if KANAL and KANAL != "chromium":
        try:
            return p.chromium.launch_persistent_context(channel=KANAL, **sozlama)
        except Exception:
            pass  # Chrome o'rnatilmagan — Playwright'ning o'z Chromium'i
    return p.chromium.launch_persistent_context(**sozlama)


def _kirish_sahifasimi(sahifa):
    try:
        return sahifa.locator("input[type=password]:visible").count() > 0
    except Exception:
        return False


def kirish():
    """Ko'rinadigan brauzer ochadi; siz kirasiz, sessiya profilda qoladi."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = _brauzer(p, yashirin=False)
        sahifa = ctx.pages[0] if ctx.pages else ctx.new_page()
        sahifa.goto(URL)
        print("Brauzerda kabinetga kiring (hisob raqam + parol / SMS kod).")
        print("Balans ko'rinadigan sahifaga yetgach, shu yerda Enter bosing.")
        input()
        ctx.close()
    print("Sessiya saqlandi:", PROFIL)


def tekshir():
    from playwright.sync_api import sync_playwright
    javoblar = []

    def ushla(javob):
        if "json" not in (javob.headers.get("content-type") or ""):
            return
        try:
            javoblar.append({"url": javob.url, "data": javob.json()})
        except Exception:
            pass

    natija = {"vaqt": time.strftime("%Y-%m-%d %H:%M"), "url": URL}
    try:
        with sync_playwright() as p:
            ctx = _brauzer(p, yashirin=True)
            sahifa = ctx.pages[0] if ctx.pages else ctx.new_page()
            sahifa.on("response", ushla)
            sahifa.goto(URL, wait_until="networkidle", timeout=60000)
            sahifa.wait_for_timeout(2500)  # kech yuklanadigan raqamlar uchun
            if _kirish_sahifasimi(sahifa):
                natija["holat"] = "kirish_kerak"
            else:
                matn = sahifa.inner_text("body")
                topilgan = []
                for j in javoblar:
                    for t in jsondan_top(j["data"]):
                        topilgan.append({**t, "manba": j["url"]})
                if topilgan:
                    natija.update(holat="ok", **topilgan[0])
                    natija["boshqa"] = topilgan[1:6]
                else:
                    t = matndan_top(matn)
                    if t:
                        natija.update(holat="ok", manba="sahifa matni", **t)
                    else:
                        natija.update(holat="topilmadi", matn=matn[:1500])
            ctx.close()
    except Exception as e:
        natija.update(holat="xato", xato=f"{type(e).__name__}: {e}"[:500])

    PAPKA.mkdir(parents=True, exist_ok=True)
    NATIJA.write_text(json.dumps(natija, ensure_ascii=False, indent=2))
    # Kabinet qaytargan JSON'lar — keyinchalik to'g'ridan-to'g'ri API'ga
    # o'tish yoki maydonni aniqlashtirish uchun.
    JAVOBLAR.write_text(json.dumps(javoblar[-30:], ensure_ascii=False, indent=2)[:2_000_000])
    return natija


if __name__ == "__main__":
    if sys.argv[1:] == ["kirish"]:
        kirish()
    else:
        print(json.dumps(tekshir(), ensure_ascii=False, indent=2))

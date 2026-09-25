#!/usr/bin/env python3
"""
Sehrli Javon — kitob do'koni uchun Telegram bot.

Maqsad: sotilmay qolgan va ombordagi kitoblarni sotish.

Xaridor uchun:
  • Ro'yxatdan o'tish: Google (Gmail) akkaunt yoki ism-familiya, keyin yosh.
  • Katalog — janrlar bo'yicha; har bir kitob sahifasida narx, ombordagi
    soni, aksiya, sovg'a, reyting, sotilgan soni va «Bilasizmi?» fakti.
  • 🔥 Aksiyalar, 🎯 yoshiga mos tavsiyalar, 🎲 tasodifiy kitob, qidiruv
    (shunchaki kitob yoki muallif nomini yozish kifoya).
  • Sovg'alar: kitobning o'z sovg'asi, xarid summasiga va kitoblar soniga
    qarab qo'shimcha sovg'a.
  • Promokod — 10% dan 50% gacha. Har bir kitobga eng katta chegirma
    qo'llanadi (aksiya yoki promokod), ikkalasi qo'shilib ketmaydi.
  • Rasmiylashtirish: telefon → lokatsiya yoki manzil → to'lov turi (naqd,
    karta, Click/Payme) → tasdiqlash → buyurtma raqami, sahifasi va holati.
  • Sotib olingan kitobni 1–5 yulduz bilan baholash va sharh qoldirish.

Admin uchun (ADMIN_IDS): /admin — umumiy hisobot, marketing tahlili (HTML
grafiklar, hisobot.py), buyurtmalarni ✅ tasdiqlash / ❌ rad etish, mijozlar,
reklama havolalari (/havola — mijoz qayerdan kelganini sanaydi), ombor,
sotilmayotgan kitoblar (bir bosishda aksiya + hammaga e'lon), promokodlar.

Faqat standart kutubxona. Ma'lumotlar bitta JSON faylda (STATE_FILE),
boshlang'ich katalog — katalog.json.

Rejimlar:
    python3 bot.py              # doimiy (o'z serveringiz bo'lsa): long polling
    python3 bot.py --for 270    # N soniya ishlab, chiqib ketadi (GitHub Actions)
    python3 bot.py --once       # navbatdagi xabarlarni bir marta qayta ishlaydi
    python3 bot.py --setup      # bot nomi, tavsifi, buyruqlar ro'yxati

Muhit o'zgaruvchilari:
    BOT_TOKEN      BotFather bergan token
    ADMIN_IDS      admin(lar) Telegram ID si, vergul bilan
    STATE_FILE     holat fayli (ixtiyoriy, standart: kitob-bot/holat.json)
    KATALOG_FILE   katalog (ixtiyoriy, standart: kitob-bot/katalog.json)
"""

import hashlib
import html
import json
import os
import random
import re
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hisobot  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(HERE, "holat.json")
KATALOG = os.environ.get("KATALOG_FILE") or os.path.join(HERE, "katalog.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

PROMO_MIN, PROMO_MAX = 10, 50
SAHIFA = 6                       # ro'yxatda bir sahifadagi kitoblar
TOSHKENT = 5 * 3600              # UTC+5

KAT = {}                         # katalog.json (janrlar, sovg'alar, do'kon)

# Pastki menyu tugmalari
B_KATALOG = "📚 Katalog"
B_AKSIYA = "🔥 Aksiyalar"
B_SIZ = "🎯 Siz uchun"
B_TASODIF = "🎲 Tasodifiy kitob"
B_SAVAT = "🛒 Savat"
B_XARID = "📦 Xaridlarim"
B_PROMO = "🎟 Promokod"
B_PROFIL = "👤 Profil"
B_BEKOR = "❌ Bekor qilish"
B_OLIB = "🏪 Do'kondan olib ketaman"
B_TEL = "📱 Raqamimni yuborish"

B_LOK = "📍 Lokatsiyani yuborish"

HOLAT = {
    "yangi": "🆕 Ko'rib chiqilmoqda",
    "tasdiqlandi": "👍 Tasdiqlandi",
    "yuborildi": "🚚 Yo'lda",
    "yetkazildi": "✅ Yetkazildi",
    "bekor": "❌ Bekor qilindi",
}
# qaysi holatdan qaysilariga o'tish mumkin
OTISH = {
    "yangi": ("tasdiqlandi", "bekor"),
    "tasdiqlandi": ("yuborildi", "yetkazildi", "bekor"),
    "yuborildi": ("yetkazildi", "bekor"),
    "yetkazildi": (),
    "bekor": (),
}
# admin tugmalari (holatga o'tkazish)
TUGMA = {
    "tasdiqlandi": "✅ Tasdiqlash",
    "yuborildi": "🚚 Yuborildi",
    "yetkazildi": "📬 Yetkazildi",
    "bekor": "❌ Rad etish",
}
TOLOV = {
    "naqd": "💵 Naqd pul",
    "karta": "💳 Karta (qabul qilganda)",
    "click": "📲 Click / Payme",
}


# ---------------------------------------------------------------- Telegram API
def _multipart(data, fayl):
    """fayl = (maydon, nomi, baytlar, mime) — Telegram'ga fayl yuklash uchun."""
    chegara = "----sehrlijavon%x" % random.getrandbits(64)
    qism = []
    for k, v in data.items():
        qism.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                     % (chegara, k, v)).encode())
    maydon, nomi, bayt, mime = fayl
    qism.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                 'Content-Type: %s\r\n\r\n' % (chegara, maydon, nomi, mime)).encode())
    qism.append(bayt + b"\r\n--" + chegara.encode() + b"--\r\n")
    return b"".join(qism), "multipart/form-data; boundary=" + chegara


def call(method, _fayl=None, **params):
    data = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        data[k] = v
    if _fayl:
        tana, turi = _multipart(data, _fayl)
        so_rov = Request(API + method, data=tana, headers={"Content-Type": turi})
    else:
        so_rov = Request(API + method, data=urlencode(data).encode())
    try:
        with urlopen(so_rov, timeout=70) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            body = json.load(e)
        except ValueError:
            body = {"description": str(e)}
        if "not modified" not in str(body.get("description")):
            print("telegram xatosi:", method, body.get("description"), file=sys.stderr)
        return {"ok": False, **body}
    except (URLError, OSError, ValueError) as e:
        print("tarmoq xatosi:", method, e, file=sys.stderr)
        return {"ok": False}


def _preview(url):
    if url:
        return {"url": url, "show_above_text": True, "prefer_large_media": True}
    return {"is_disabled": True}


def send(chat, text, kb=None, rasm=None):
    return call("sendMessage", chat_id=chat, text=text, parse_mode="HTML",
                reply_markup=kb, link_preview_options=_preview(rasm))


def edit(chat, mid, text, kb=None, rasm=None):
    """Xabarni joyida yangilaydi; iloji bo'lmasa (eski xabar) — yangisini yuboradi."""
    if mid:
        r = call("editMessageText", chat_id=chat, message_id=mid, text=text,
                 parse_mode="HTML", reply_markup=kb or {"inline_keyboard": []},
                 link_preview_options=_preview(rasm))
        if r.get("ok") or "not modified" in str(r.get("description")):
            return r
    return send(chat, text, kb, rasm)


def answer(cb_id, text=None, alert=False):
    return call("answerCallbackQuery", callback_query_id=cb_id, text=text,
                show_alert=alert or None)


def ikb(rows):
    return {"inline_keyboard": [r for r in rows if r]}


def btn(text, data):
    return {"text": text, "callback_data": data}


def menyu():
    return {
        "keyboard": [
            [{"text": B_KATALOG}, {"text": B_AKSIYA}],
            [{"text": B_SIZ}, {"text": B_TASODIF}],
            [{"text": B_SAVAT}, {"text": B_XARID}],
            [{"text": B_PROMO}, {"text": B_PROFIL}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": "Kitob yoki muallif nomini yozing…",
    }


def bekor_kb(*qator):
    rows = [[{"text": t}] for t in qator if t]
    return {"keyboard": rows + [[{"text": B_BEKOR}]], "resize_keyboard": True}


# ---------------------------------------------------------------- yordamchilar
def e(s):
    return html.escape(str(s), quote=False)


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def yulduz(o):
    t = int(round(o))
    return "★" * t + "☆" * (5 - t)


def sana(ts):
    return time.strftime("%d.%m.%Y %H:%M", time.gmtime(ts + TOSHKENT))


def bugun():
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + TOSHKENT))


def norm(s):
    s = (s or "").lower()
    for ch in "ʻʼ‘’`´":
        s = s.replace(ch, "'")
    return s


def chegirma(narx, foiz):
    """Chegirmali narx, 100 so'mgacha yaxlitlab."""
    return (int(narx) * (100 - int(foiz)) + 5000) // 10000 * 100


def qisqa(s, n=26):
    return s if len(s) <= n else s[:n - 1] + "…"


def toliq_ism(u):
    return ("%s %s" % (u.get("ism") or "", u.get("familiya") or "")).strip() \
        or u.get("tg_ism") or "Kitobxon"


# ---------------------------------------------------------------- saqlash
def yukla():
    """Holat fayli + katalog. Katalogdagi yangi kitob/promokodlar qo'shiladi,
    mavjud kitoblarning matnlari yangilanadi (narx, soni, aksiya, sovg'a
    esa bot ichida boshqariladi va tegilmaydi)."""
    global KAT
    with open(KATALOG, encoding="utf-8") as f:
        KAT = json.load(f)
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    for k, v in (("users", {}), ("kitoblar", {}), ("promo", {}),
                 ("buyurtmalar", {}), ("keyingi", 1)):
        db.setdefault(k, v)
    for b in KAT.get("kitoblar", []):
        eski = db["kitoblar"].get(b["id"])
        if eski is None:
            yangi = dict(b)
            yangi.update(sotildi=0, baholar={}, sharhlar=[])
            db["kitoblar"][b["id"]] = yangi
        else:
            for k in ("nomi", "muallif", "janr", "yosh", "tavsif", "qiziq", "rasm"):
                if k in b:
                    eski[k] = b[k]
    for p in KAT.get("promokodlar", []):
        kod = p["kod"].upper()
        if kod in db["promo"]:
            continue
        if not PROMO_MIN <= int(p["foiz"]) <= PROMO_MAX:
            print("promokod %s o'tkazib yuborildi: foiz %s%%–%s%% oralig'ida bo'lishi kerak"
                  % (kod, PROMO_MIN, PROMO_MAX), file=sys.stderr)
            continue
        db["promo"][kod] = {"foiz": int(p["foiz"]), "qoldi": p.get("qoldi"),
                            "muddat": p.get("muddat"), "faol": True, "ishlatganlar": []}
    return db


def saqla(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def foydalanuvchi(db, chat, frm):
    u = db["users"].get(chat)
    if u is None:
        u = {"id": chat, "royxat": False, "savat": {}, "qadam": None,
             "promo": None, "sana": int(time.time())}
        db["users"][chat] = u
    tg = ("%s %s" % (frm.get("first_name") or "", frm.get("last_name") or "")).strip()
    u["tg_ism"] = tg
    u["tg_fam"] = frm.get("last_name") or ""
    u["tg_nom"] = frm.get("first_name") or ""
    u["username"] = frm.get("username") or ""
    u.pop("blok", None)
    return u


# ---------------------------------------------------------------- kitob hisob-kitobi
def narxi(b):
    return chegirma(b["narx"], b.get("aksiya") or 0)


def reyting(b):
    v = list((b.get("baholar") or {}).values())
    return (sum(v) / len(v), len(v)) if v else (0.0, 0)


def yosh_mos(u, b):
    return (u.get("yosh") or 0) >= (b.get("yosh") or 0)


def promo_tekshir(db, kod, chat):
    """(ok, xabar, foiz)"""
    kod = (kod or "").strip().upper()
    p = db["promo"].get(kod)
    if not p:
        return False, "Bunday promokod topilmadi.", 0
    if not p.get("faol"):
        return False, "Bu promokod hozir faol emas.", 0
    if p.get("qoldi") is not None and p["qoldi"] <= 0:
        return False, "Bu promokodning soni tugagan.", 0
    if p.get("muddat") and p["muddat"] < bugun():
        return False, "Bu promokodning muddati o'tgan.", 0
    if chat in p.get("ishlatganlar", []):
        return False, "Siz bu promokodni avval ishlatgansiz — har bir promokod bir marta.", 0
    return True, "", max(PROMO_MIN, min(PROMO_MAX, int(p["foiz"])))


def hisob(db, u):
    """Savat hisobi. Tugagan kitoblar o'chiriladi, miqdor ombordagidan
    oshsa — kamaytiriladi (o'zgargan bo'lsa, ozgardi=True)."""
    kitoblar = db["kitoblar"]
    savat = u.setdefault("savat", {})
    pfoiz, pkod, ozgardi = 0, u.get("promo"), False
    if pkod:
        ok, _, pfoiz = promo_tekshir(db, pkod, u["id"])
        if not ok:
            u["promo"], pkod, pfoiz = None, None, 0
    qatorlar = []
    for bid, q in list(savat.items()):
        b = kitoblar.get(bid)
        if not b or b.get("soni", 0) <= 0:
            del savat[bid]
            ozgardi = True
            continue
        if q > b["soni"]:
            q = savat[bid] = b["soni"]
            ozgardi = True
        af = b.get("aksiya") or 0
        f = max(af, pfoiz)
        manba = None if f == 0 else ("aksiya" if af >= pfoiz else "promo")
        birlik = chegirma(b["narx"], f)
        qatorlar.append({"id": bid, "nomi": b["nomi"], "soni": q, "narx": b["narx"],
                         "birlik": birlik, "foiz": f, "manba": manba, "jami": birlik * q,
                         "sovga": b.get("sovga")})
    asl = sum(x["narx"] * x["soni"] for x in qatorlar)
    jami = sum(x["jami"] for x in qatorlar)
    dona = sum(x["soni"] for x in qatorlar)

    sovgalar = [x["sovga"] for x in qatorlar if x["sovga"]]
    keyingi = None
    sv = KAT.get("sovgalar", {})
    pogonalar = sorted(sv.get("summa", []), key=lambda s: s["dan"])
    erishilgan = [s for s in pogonalar if jami >= s["dan"]]
    if erishilgan and qatorlar:
        sovgalar.append(erishilgan[-1]["sovga"])
    qolgan = [s for s in pogonalar if jami < s["dan"]]
    if qolgan and qatorlar:
        keyingi = (qolgan[0]["dan"] - jami, qolgan[0]["sovga"])
    sn = sv.get("soni")
    if sn and dona >= sn["dan"]:
        sovgalar.append(sn["sovga"])
    return {"qatorlar": qatorlar, "asl": asl, "jami": jami, "dona": dona,
            "promo": pkod, "pfoiz": pfoiz, "sovgalar": sovgalar,
            "keyingi": keyingi, "ozgardi": ozgardi}


def savat_izi(u):
    s = json.dumps([sorted(u.get("savat", {}).items()), u.get("promo")])
    return hashlib.md5(s.encode()).hexdigest()[:8]


def xarid_qilganmi(db, chat, bid):
    for o in db["buyurtmalar"].values():
        if o["chat"] == chat and o["holat"] != "bekor" \
                and any(x["id"] == bid for x in o["qatorlar"]):
            return True
    return False


# ---------------------------------------------------------------- ro'yxatdan o'tish
SALOM = (
    "📚✨ <b>Sehrli Javon</b>ga xush kelibsiz!\n\n"
    "Bu yerda har bir kitob o'z egasini kutib turibdi — ba'zilari aksiyada, "
    "ba'zilari sovg'a bilan. Avval tanishib olaylik.\n\n"
    "Qanday ro'yxatdan o'tasiz?"
)


def reg_boshla(chat, u):
    u["qadam"] = None
    send(chat, SALOM, ikb([
        [btn("📧 Google akkaunt (Gmail) orqali", "reg:gmail")],
        [btn("✍️ Ism va familiya orqali", "reg:ism")],
    ]))


def reg_qadam(db, chat, u, text):
    q = u.get("qadam")
    if q == "email":
        t = text.strip().lower()
        if not re.fullmatch(r"[a-z0-9._%+\-]{1,64}@[a-z0-9.\-]+\.[a-z]{2,}", t):
            send(chat, "🤔 Bu e-pochtaga o'xshamayapti. Google akkauntingiz manzilini "
                       "to'liq yozing, masalan: <code>aziz.karimov@gmail.com</code>")
            return
        u["email"], u["usul"] = t, "gmail"
        u["ism"] = u.get("tg_nom") or t.split("@")[0]
        u["familiya"] = u.get("tg_fam") or ""
        u["qadam"] = "yosh"
        send(chat, "✅ Google akkaunt: <b>%s</b>\n\n🎂 Yoshingiz nechada? "
                   "<i>(raqam bilan, masalan: 17)</i>" % e(t))
        return
    if q == "ism":
        qism = text.split()
        soz = r"[^\W\d_]+(?:['ʻʼ‘’`\-][^\W\d_]+)*"
        if len(qism) < 2 or len(qism) > 4 or \
                not all(re.fullmatch(soz, p) and 2 <= len(p) <= 30 for p in qism):
            send(chat, "✍️ Ism va familiyangizni harflar bilan, bo'sh joy bilan "
                       "ajratib yozing. Masalan: <code>Aziz Karimov</code>")
            return
        qism = [p[0].upper() + p[1:] for p in qism]
        u["ism"], u["familiya"], u["usul"] = qism[0], " ".join(qism[1:]), "ism"
        u["qadam"] = "yosh"
        send(chat, "Tanishganimdan xursandman, <b>%s</b>! 😊\n\n🎂 Yoshingiz nechada? "
                   "<i>(raqam bilan, masalan: 17)</i>" % e(u["ism"]))
        return
    if q == "yosh":
        t = text.strip()
        if not t.isdigit() or not 5 <= int(t) <= 100:
            send(chat, "🎂 Yoshingizni 5 dan 100 gacha bo'lgan raqam bilan yozing, masalan: <code>17</code>")
            return
        u["yosh"], u["royxat"], u["qadam"] = int(t), True, None
        u.setdefault("royxat_sana", int(time.time()))
        matn = ("🎉 Tayyor, <b>%s</b>! Endi javonlarni birga titkilaymiz.\n\n"
                "👇 Pastdagi menyudan tanlang yoki shunchaki kitob/muallif nomini yozing."
                % e(toliq_ism(u)))
        xp = KAT.get("dokon", {}).get("xush_promo")
        if xp and promo_tekshir(db, xp, u["id"])[0]:
            p = db["promo"][xp]
            matn += ("\n\n🎁 Tanishuv sovg'asi: <code>%s</code> promokodi — birinchi xaridga "
                     "<b>%d%%</b> chegirma!" % (xp, p["foiz"]))
        send(chat, matn, menyu())
        bid = u.pop("ochish", None)
        if bid and bid in db["kitoblar"]:
            kitob_sahifa(db, chat, u, None, bid, "-", 0)


# ---------------------------------------------------------------- katalog
def kitob_royxati(db, u, kalit):
    """(sarlavha, kitoblar)"""
    hammasi = list(db["kitoblar"].values())
    janrlar = KAT.get("janrlar", {})
    bor = lambda b: (b.get("soni", 0) <= 0, )
    if kalit == "*all":
        s, r = "📚 Barcha kitoblar", sorted(hammasi, key=lambda b: bor(b) + (b["nomi"],))
    elif kalit == "*aksiya":
        s = "🔥 Aksiya va sovg'ali kitoblar"
        r = [b for b in hammasi if (b.get("aksiya") or b.get("sovga")) and b.get("soni", 0) > 0]
        r.sort(key=lambda b: -(b.get("aksiya") or 0))
    elif kalit == "*top":
        s = "⭐ Eng yuqori baholangan"
        r = sorted(hammasi, key=lambda b: bor(b) + (-reyting(b)[0], -b.get("sotildi", 0)))
    elif kalit == "*siz":
        s = "🎯 %s, siz uchun tanladik" % e(u.get("ism") or "Kitobxon")
        r = [b for b in hammasi if yosh_mos(u, b) and b.get("soni", 0) > 0]
        bola = (u.get("yosh") or 99) < 13

        def ball(b):
            rt, n = reyting(b)
            return -((3 if bola and b.get("janr") == "bolalar" else 0)
                     + (b.get("aksiya") or 0) / 10 + (1 if b.get("sovga") else 0)
                     + (rt if n else 3.5) / 2)
        r.sort(key=ball)
    elif kalit in janrlar:
        s = janrlar[kalit]
        r = sorted([b for b in hammasi if b.get("janr") == kalit],
                   key=lambda b: bor(b) + (-(b.get("aksiya") or 0), b["nomi"]))
    else:
        return None, []
    return s, r


def janrlar_kb(db):
    rows = []
    for k, nom in KAT.get("janrlar", {}).items():
        n = sum(1 for b in db["kitoblar"].values() if b.get("janr") == k and b.get("soni", 0) > 0)
        if n:
            rows.append([btn("%s (%d)" % (nom, n), "j:%s:0" % k)])
    rows.append([btn("🔥 Aksiyalar", "j:*aksiya:0"), btn("⭐ Eng yaxshilar", "j:*top:0")])
    rows.append([btn("📚 Hammasi", "j:*all:0")])
    return ikb(rows)


def katalog(db, chat, mid=None):
    jami = sum(b.get("soni", 0) for b in db["kitoblar"].values())
    edit(chat, mid, "📚 <b>Katalog</b>\n\nJavonlarimizda <b>%d</b> dona kitob. "
                    "Qaysi janrdan boshlaymiz?" % jami, janrlar_kb(db))


def royxat_sahifa(db, chat, u, mid, kalit, sahifa):
    sarlavha, kitoblar = kitob_royxati(db, u, kalit)
    if sarlavha is None:
        return katalog(db, chat, mid)
    if not kitoblar:
        return edit(chat, mid, "%s\n\nHozircha bu yerda kitob yo'q. 🙂" % sarlavha,
                    ikb([[btn("⬅️ Janrlar", "cat")]]))
    soni = (len(kitoblar) + SAHIFA - 1) // SAHIFA
    sahifa = max(0, min(sahifa, soni - 1))
    rows = []
    for b in kitoblar[sahifa * SAHIFA:(sahifa + 1) * SAHIFA]:
        belgi = "❌" if b.get("soni", 0) <= 0 else ("🔥" if b.get("aksiya") else
                                                    ("🎁" if b.get("sovga") else "📖"))
        rows.append([btn("%s %s · %s" % (belgi, qisqa(b["nomi"]), som(narxi(b))),
                         "k:%s:%s:%d" % (b["id"], kalit, sahifa))])
    if soni > 1:
        rows.append([btn("◀️", "j:%s:%d" % (kalit, (sahifa - 1) % soni)),
                     btn("%d / %d" % (sahifa + 1, soni), "nop"),
                     btn("▶️", "j:%s:%d" % (kalit, (sahifa + 1) % soni))])
    rows.append([btn("⬅️ Janrlar", "cat"), btn("🛒 Savat", "cart")])
    izoh = "\n\n🔥 — aksiya · 🎁 — sovg'a bilan · ❌ — tugagan"
    if kalit == "*aksiya":
        izoh += sovga_qoidalari()
    edit(chat, mid, "<b>%s</b>%s" % (sarlavha, izoh), ikb(rows))


def sovga_qoidalari():
    sv = KAT.get("sovgalar", {})
    q = ["\n\n🎁 <b>Qo'shimcha sovg'alar:</b>"]
    for s in sorted(sv.get("summa", []), key=lambda s: s["dan"]):
        q.append("• %s dan xarid — %s" % (som(s["dan"]), e(s["sovga"])))
    if sv.get("soni"):
        q.append("• %d va undan ortiq kitob — %s" % (sv["soni"]["dan"], e(sv["soni"]["sovga"])))
    return "\n".join(q) if len(q) > 1 else ""


def kitob_matn(db, u, b):
    janr = KAT.get("janrlar", {}).get(b.get("janr"), "")
    af = b.get("aksiya") or 0
    q = ["📖 <b>%s</b>" % e(b["nomi"]), "✍️ %s" % e(b["muallif"])]
    teg = [e(janr)] if janr else []
    if b.get("yosh"):
        teg.append("%d+" % b["yosh"])
    if teg:
        q.append("🏷 " + " · ".join(teg))
    q.append("")
    if af:
        q.append("💰 <s>%s</s>  <b>%s</b>  🔥 −%d%%" % (som(b["narx"]), som(narxi(b)), af))
    else:
        q.append("💰 <b>%s</b>" % som(b["narx"]))
    if b.get("sovga"):
        q.append("🎁 Sovg'a: %s" % e(b["sovga"]))
    s = b.get("soni", 0)
    if s <= 0:
        q.append("📦 ❌ Hozircha tugagan")
    elif s <= 3:
        q.append("📦 ⚡ Oxirgi <b>%d</b> dona qoldi!" % s)
    else:
        q.append("📦 Omborda: %d dona" % s)
    rt, n = reyting(b)
    q.append("⭐ %s %.1f (%d baho) · 🛍 Sotilgan: %d dona" % (yulduz(rt), rt, n, b.get("sotildi", 0))
             if n else "⭐ Hali baholanmagan · 🛍 Sotilgan: %d dona" % b.get("sotildi", 0))
    if b.get("tavsif"):
        q += ["", "<i>%s</i>" % e(b["tavsif"])]
    if b.get("qiziq"):
        q += ["", "💡 <b>Bilasizmi?</b> %s" % e(b["qiziq"])]
    if not yosh_mos(u, b):
        q += ["", "🔞 Bu kitob %d+ yoshdagilar uchun." % b["yosh"]]
    return "\n".join(q)


def kitob_sahifa(db, chat, u, mid, bid, kalit, sahifa):
    b = db["kitoblar"].get(bid)
    if not b:
        return edit(chat, mid, "Bu kitob endi mavjud emas.", ikb([[btn("⬅️ Janrlar", "cat")]]))
    ctx = "%s:%s:%d" % (bid, kalit, sahifa)
    rows = []
    savatda = u.get("savat", {}).get(bid, 0)
    if b.get("soni", 0) > 0 and yosh_mos(u, b):
        rows.append([btn("🛒 Savatga qo'shish" + (" (%d)" % savatda if savatda else ""), "+:" + ctx)])
    _, n = reyting(b)
    rows.append([btn("💬 Baholar va sharhlar (%d)" % n, "sh:" + ctx)])
    if kalit != b.get("janr") and b.get("janr") in KAT.get("janrlar", {}):
        rows.append([btn("📚 Shu janrdagi boshqa kitoblar", "j:%s:0" % b["janr"])])
    orqa = btn("⬅️ Orqaga", "j:%s:%d" % (kalit, sahifa)) if kalit != "-" else btn("⬅️ Katalog", "cat")
    rows.append([orqa, btn("🛒 Savat" + (" ✓" if u.get("savat") else ""), "cart")])
    edit(chat, mid, kitob_matn(db, u, b), ikb(rows), b.get("rasm"))


def sharhlar_sahifa(db, chat, mid, bid, kalit, sahifa):
    b = db["kitoblar"].get(bid)
    if not b:
        return
    rt, n = reyting(b)
    q = ["💬 <b>%s</b> — baholar" % e(b["nomi"]), ""]
    if n:
        q.append("%s <b>%.1f</b> / 5  (%d baho)" % (yulduz(rt), rt, n))
        v = list(b["baholar"].values())
        for y in range(5, 0, -1):
            c = v.count(y)
            q.append("%d★ %s %d" % (y, "▓" * round(10 * c / n) + "░" * (10 - round(10 * c / n)), c))
        sh = [s for s in b.get("sharhlar", []) if s.get("matn")][-5:]
        if sh:
            q += ["", "<b>So'nggi sharhlar:</b>"]
            for s in reversed(sh):
                q.append("%s <b>%s</b>: %s" % ("★" * s["baho"], e(s["ism"]), e(s["matn"])))
    else:
        q.append("Hali hech kim baholamagan. Birinchi bo'lib sotib oling va baholang! 😉")
    q += ["", "<i>Baholash faqat kitobni sotib olganlar uchun — «📦 Xaridlarim» bo'limida.</i>"]
    edit(chat, mid, "\n".join(q), ikb([[btn("⬅️ Kitobga qaytish", "k:%s:%s:%d" % (bid, kalit, sahifa))]]))


def tasodifiy(db, chat, u, mid=None):
    r = [b for b in db["kitoblar"].values() if b.get("soni", 0) > 0 and yosh_mos(u, b)]
    if not r:
        return send(chat, "Hozircha omborda sizga mos kitob qolmadi. 😔")
    # ombori to'lib yotgan kitoblar ko'proq chiqadi
    b = random.choices(r, weights=[1 + b.get("soni", 0) / (1 + b.get("sotildi", 0)) for b in r])[0]
    rows = []
    if b.get("soni", 0) > 0:
        rows.append([btn("🛒 Savatga qo'shish", "+:%s:~:0" % b["id"])])
    rows.append([btn("🎲 Yana bittasi", "rnd"), btn("🛒 Savat", "cart")])
    edit(chat, mid, "🎲 <b>Taqdir sizga shu kitobni tanladi:</b>\n\n" + kitob_matn(db, u, b),
         ikb(rows), b.get("rasm"))


def qidir(db, chat, u, text):
    t = norm(text).strip()
    if len(t) < 2:
        return send(chat, "Pastdagi menyudan tanlang 👇", menyu())
    topildi = [b for b in db["kitoblar"].values()
               if t in norm(b["nomi"]) or t in norm(b["muallif"])][:8]
    if not topildi:
        return send(chat, "🔍 «%s» bo'yicha kitob topilmadi.\n\nKatalogni ko'rib chiqing yoki "
                          "boshqa so'z bilan qidiring." % e(text[:50]), janrlar_kb(db))
    rows = [[btn("%s %s · %s" % ("🔥" if b.get("aksiya") else "📖", qisqa(b["nomi"]), som(narxi(b))),
                 "k:%s:-:0" % b["id"])] for b in topildi]
    send(chat, "🔍 Topildi: %d ta" % len(topildi), ikb(rows))


# ---------------------------------------------------------------- savat
def savat_matn(h, tahrir=True):
    q = ["🛒 <b>Savat</b>", ""]
    for i, x in enumerate(h["qatorlar"], 1):
        s = "%d. <b>%s</b> × %d = %s" % (i, e(x["nomi"]), x["soni"], som(x["jami"]))
        if x["foiz"]:
            s += "\n    <s>%s</s> −%d%% %s" % (som(x["narx"] * x["soni"]), x["foiz"],
                                           "🔥 aksiya" if x["manba"] == "aksiya" else "🎟 promokod")
        q.append(s)
    q.append("")
    if h["asl"] != h["jami"]:
        q.append("Narxi: <s>%s</s>" % som(h["asl"]))
        q.append("Tejaysiz: <b>%s</b> 🎉" % som(h["asl"] - h["jami"]))
    if h["promo"]:
        q.append("🎟 Promokod: <code>%s</code> (−%d%%)" % (h["promo"], h["pfoiz"]))
    q.append("💳 <b>To'lov: %s</b>" % som(h["jami"]))
    if h["sovgalar"]:
        q += ["", "🎁 <b>Sovg'alaringiz:</b>"] + ["• " + e(s) for s in h["sovgalar"]]
    if h["keyingi"] and tahrir:
        q += ["", "💡 Yana <b>%s</b>lik kitob olsangiz — %s sovg'a!" % (som(h["keyingi"][0]), e(h["keyingi"][1]))]
    if h["promo"] and tahrir:
        q += ["", "<i>Har bir kitobga eng katta chegirma qo'llanadi — aksiya yoki promokod.</i>"]
    return "\n".join(q)


def savat(db, chat, u, mid=None):
    h = hisob(db, u)
    if not h["qatorlar"]:
        return edit(chat, mid, "🛒 Savatingiz bo'sh.\n\nKatalogdan yoqqan kitobni tanlang — "
                               "🔥 aksiyadagilarni ham ko'rib chiqing!",
                    ikb([[btn("📚 Katalog", "cat"), btn("🔥 Aksiyalar", "j:*aksiya:0")]]))
    rows = [[btn("➖", "c-:" + x["id"]), btn("❌ " + qisqa(x["nomi"], 18), "cx:" + x["id"]),
             btn("➕", "c+:" + x["id"])] for x in h["qatorlar"]]
    rows.append([btn("❎ Promokodni olib tashlash", "cpx") if h["promo"]
                 else btn("🎟 Promokod kiritish", "cpromo")])
    rows.append([btn("✅ Buyurtma berish — " + som(h["jami"]), "buy")])
    rows.append([btn("📚 Davom etish", "cat"), btn("🗑 Tozalash", "cclr")])
    matn = savat_matn(h)
    if h["ozgardi"]:
        matn = "⚠️ <i>Ombordagi miqdor o'zgargani uchun savat yangilandi.</i>\n\n" + matn
    edit(chat, mid, matn, ikb(rows))


def savatga(db, u, bid):
    """(ok, xabar)"""
    b = db["kitoblar"].get(bid)
    if not b:
        return False, "Bu kitob endi mavjud emas."
    if not yosh_mos(u, b):
        return False, "🔞 Bu kitob %d+ yoshdagilar uchun." % b["yosh"]
    if b.get("soni", 0) <= 0:
        return False, "😔 Bu kitob tugagan."
    s = u.setdefault("savat", {})
    if s.get(bid, 0) >= b["soni"]:
        return False, "Omborda faqat %d dona bor — hammasi savatingizda." % b["soni"]
    s[bid] = s.get(bid, 0) + 1
    return True, "🛒 Savatga qo'shildi (%d dona)" % s[bid]


# ---------------------------------------------------------------- buyurtma
def buyurtma_boshla(db, chat, u):
    h = hisob(db, u)
    if not h["qatorlar"]:
        return send(chat, "🛒 Savatingiz bo'sh.", menyu())
    u["qadam"] = "tel"
    kb = {"keyboard": [[{"text": B_TEL, "request_contact": True}]]
          + ([[{"text": u["tel"]}]] if u.get("tel") else []) + [[{"text": B_BEKOR}]],
          "resize_keyboard": True}
    send(chat, "📝 <b>Buyurtmani rasmiylashtirish</b>\n👤 Qabul qiluvchi: <b>%s</b>\n\n"
               "📱 <b>1/3.</b> Telefon raqamingizni yuboring — kuryer siz bilan shu raqam orqali "
               "bog'lanadi.\n\nPastdagi tugmani bosing yoki raqamni yozing: <code>+998901234567</code>"
               % e(toliq_ism(u)), kb)


def tel_qadam(chat, u, text, contact, frm):
    if contact:
        if contact.get("user_id") and str(contact["user_id"]) != str(frm.get("id")):
            return send(chat, "Iltimos, o'zingizning raqamingizni yuboring (tugma orqali).")
        tel = re.sub(r"\D", "", contact.get("phone_number", ""))
    else:
        tel = re.sub(r"[\s\-()]", "", text or "").lstrip("+")
        if len(tel) == 9 and tel.isdigit():
            tel = "998" + tel
    if not (tel.isdigit() and 9 <= len(tel) <= 15):
        return send(chat, "🤔 Raqam noto'g'ri ko'rinadi. Masalan: <code>+998901234567</code>")
    u["tel"] = "+" + tel
    u["qadam"] = "manzil"
    eski = u.get("manzil") if u.get("manzil") and not u.get("lokatsiya") and u["manzil"] != B_OLIB else None
    kb = {"keyboard": [[{"text": B_LOK, "request_location": True}], [{"text": B_OLIB}]]
          + ([[{"text": eski}]] if eski else []) + [[{"text": B_BEKOR}]],
          "resize_keyboard": True}
    send(chat, "📍 <b>2/3.</b> Lokatsiyangizni yuboring (pastdagi tugma) yoki manzilni yozing "
               "(shahar, ko'cha, uy, mo'ljal).\n\n🚚 %s\n🏪 %s" % (
                   e(KAT.get("dokon", {}).get("yetkazish", "")),
                   e(KAT.get("dokon", {}).get("olib_ketish", ""))), kb)


def xarita(lok):
    return "https://maps.google.com/?q=%.6f,%.6f" % (lok["lat"], lok["lon"])


def manzil_qadam(db, chat, u, text, lokatsiya=None):
    t = (text or "").strip()
    if lokatsiya and "latitude" in lokatsiya:
        u["lokatsiya"] = {"lat": float(lokatsiya["latitude"]), "lon": float(lokatsiya["longitude"])}
        u["manzil"] = "📍 Xaritadagi nuqta"
    elif t == B_OLIB or len(t) >= 8:
        u["lokatsiya"] = None
        u["manzil"] = t[:300]
    else:
        return send(chat, "📍 Lokatsiyani tugma orqali yuboring, manzilni batafsilroq yozing "
                          "(kamida 8 belgi) yoki «%s» tugmasini bosing." % B_OLIB)
    u["qadam"] = None
    send(chat, "✅ Manzil saqlandi.", menyu())
    tolov_sorov(chat, u)


def tolov_sorov(chat, u, mid=None):
    edit(chat, mid, "💳 <b>3/3.</b> To'lov turini tanlang:\n\n<i>%s</i>" % e(
        KAT.get("dokon", {}).get("tolov", "")),
         ikb([[btn(v, "pay:" + k)] for k, v in TOLOV.items()]))


def manzil_satr(o, html_=True):
    s = e(o.get("manzil") or "")
    if o.get("lokatsiya") and html_:
        s += ' — <a href="%s">xaritada ochish</a>' % xarita(o["lokatsiya"])
    return s


def tasdiq_sahifa(db, chat, u, mid=None):
    h = hisob(db, u)
    if not h["qatorlar"]:
        return edit(chat, mid, "🛒 Savatingiz bo'sh.")
    matn = (savat_matn(h, tahrir=False) + "\n\n👤 %s\n📱 %s\n📍 %s\n%s" % (
        e(toliq_ism(u)), e(u["tel"]), manzil_satr(u), TOLOV.get(u.get("tolov"), "")))
    edit(chat, mid, "📝 <b>Buyurtmani tasdiqlang</b>\n\n" + matn, ikb([
        [btn("✅ Tasdiqlayman", "ok:" + savat_izi(u))],
        [btn("✏️ Savatni o'zgartirish", "cart"), btn("❌ Bekor", "cancelbuy")],
    ]))


def buyurtma_tasdiq(db, chat, u, mid, iz):
    if not u.get("tel") or not u.get("manzil"):
        return buyurtma_boshla(db, chat, u)
    if u.get("tolov") not in TOLOV:
        return tolov_sorov(chat, u)
    if iz != savat_izi(u):
        send(chat, "⚠️ Savat o'zgargan — yangilangan buyurtmani qayta tekshiring.")
        return tasdiq_sahifa(db, chat, u)
    h = hisob(db, u)
    if not h["qatorlar"]:
        return edit(chat, mid, "🛒 Savatingiz bo'sh — buyurtma allaqachon berilgan bo'lishi mumkin. "
                               "«📦 Xaridlarim»ni tekshiring.")
    if h["ozgardi"]:
        send(chat, "⚠️ Ayrim kitoblar omborda kamaydi — savat yangilandi. Qayta tekshiring.")
        return tasdiq_sahifa(db, chat, u)

    kam = []
    for x in h["qatorlar"]:
        b = db["kitoblar"][x["id"]]
        b["soni"] -= x["soni"]
        b["sotildi"] = b.get("sotildi", 0) + x["soni"]
        if b["soni"] <= 2:
            kam.append("%s — %d dona" % (b["nomi"], b["soni"]))
    if h["promo"]:
        p = db["promo"][h["promo"]]
        p.setdefault("ishlatganlar", []).append(chat)
        if p.get("qoldi") is not None:
            p["qoldi"] -= 1
    n = db["keyingi"]
    db["keyingi"] = n + 1
    o = {"id": n, "chat": chat, "ism": toliq_ism(u), "username": u.get("username"),
         "email": u.get("email"), "yosh": u.get("yosh"), "tel": u["tel"], "manzil": u["manzil"],
         "qatorlar": h["qatorlar"], "asl": h["asl"], "jami": h["jami"], "promo": h["promo"],
         "pfoiz": h["pfoiz"], "sovgalar": h["sovgalar"], "holat": "yangi",
         "tolov": u["tolov"], "lokatsiya": u.get("lokatsiya"), "manba": u.get("manba"),
         "sana": int(time.time()), "tarix": [["yangi", int(time.time())]]}
    db["buyurtmalar"][str(n)] = o
    u["savat"], u["promo"] = {}, None

    edit(chat, mid, "🎉 <b>Buyurtma rasmiylashtirildi!</b>\n\n🧾 Buyurtma raqami: <b>#%d</b>\n"
                    "💳 %s — %s\n\nAdmin tasdiqlashi bilan sizga xabar beramiz. Holatini "
                    "«📦 Xaridlarim» bo'limida kuzatib borishingiz mumkin." % (n, som(o["jami"]), TOLOV[o["tolov"]]),
         ikb([[btn("📄 Buyurtma sahifasi", "o:%d" % n)]]))
    tavsiya = tavsiyalar(db, u, o)
    if tavsiya:
        send(chat, "📚 <b>Sizga yana yoqishi mumkin:</b>", ikb(
            [[btn("📖 %s · %s" % (qisqa(b["nomi"]), som(narxi(b))), "k:%s:-:0" % b["id"])] for b in tavsiya]))
    for a in ADMINS:
        send(a, admin_buyurtma_matn(o) + ("\n\n⚠️ <b>Kam qoldi:</b>\n" + "\n".join(map(e, kam)) if kam else ""),
             admin_buyurtma_kb(o))
        if o["lokatsiya"]:
            call("sendLocation", chat_id=a, latitude=o["lokatsiya"]["lat"], longitude=o["lokatsiya"]["lon"])


def tavsiyalar(db, u, o):
    olingan = {x["id"] for x in o["qatorlar"]}
    janrlar = {db["kitoblar"][i].get("janr") for i in olingan if i in db["kitoblar"]}
    r = [b for b in db["kitoblar"].values() if b["id"] not in olingan and b.get("soni", 0) > 0
         and yosh_mos(u, b) and b.get("janr") in janrlar]
    r.sort(key=lambda b: -(b.get("aksiya") or 0))
    return r[:2]


def buyurtma_matn(o, admin=False):
    q = ["📄 <b>Buyurtma #%d</b>" % o["id"], "🗓 %s" % sana(o["sana"]),
         "Holati: <b>%s</b>" % HOLAT[o["holat"]], ""]
    for i, x in enumerate(o["qatorlar"], 1):
        s = "%d. %s × %d = %s" % (i, e(x["nomi"]), x["soni"], som(x["jami"]))
        if x["foiz"]:
            s += " (−%d%%)" % x["foiz"]
        q.append(s)
    q.append("")
    if o["asl"] != o["jami"]:
        q.append("Tejaldi: %s" % som(o["asl"] - o["jami"]))
    if o.get("promo"):
        q.append("🎟 Promokod: %s (−%d%%)" % (o["promo"], o["pfoiz"]))
    q.append("💳 <b>Jami: %s</b>" % som(o["jami"]))
    if o.get("sovgalar"):
        q.append("🎁 Sovg'alar: " + ", ".join(map(e, o["sovgalar"])))
    q += ["", "📱 %s" % e(o["tel"]), "📍 %s" % manzil_satr(o)]
    if o.get("tolov"):
        q.append(TOLOV.get(o["tolov"], ""))
    if admin:
        q.insert(1, "👤 %s%s · %s yosh%s%s" % (
            e(o["ism"]), (" (@%s)" % e(o["username"])) if o.get("username") else "",
            o.get("yosh") or "?", ("\n📧 " + e(o["email"])) if o.get("email") else "",
            ("\n📣 Manba: " + e(o["manba"])) if o.get("manba") else ""))
    return "\n".join(q)


def admin_buyurtma_matn(o):
    return "🛎 <b>Yangi buyurtma!</b>\n\n" + buyurtma_matn(o, admin=True) if o["holat"] == "yangi" \
        else buyurtma_matn(o, admin=True)


def admin_buyurtma_kb(o):
    return ikb([[btn(TUGMA[h], "a:s:%d:%s" % (o["id"], h)) for h in OTISH[o["holat"]]]]
               + [[btn("⬅️ Buyurtmalar", "a:o")]])


def holat_ozgartir(db, n, yangi, kim):
    """(ok, xabar)"""
    o = db["buyurtmalar"].get(str(n))
    if not o:
        return False, "Buyurtma topilmadi."
    if yangi not in OTISH.get(o["holat"], ()):
        return False, "Bu buyurtma holati allaqachon: %s" % HOLAT[o["holat"]]
    o["holat"] = yangi
    o.setdefault("tarix", []).append([yangi, int(time.time())])
    if yangi == "bekor":
        for x in o["qatorlar"]:
            b = db["kitoblar"].get(x["id"])
            if b:
                b["soni"] = b.get("soni", 0) + x["soni"]
                b["sotildi"] = max(0, b.get("sotildi", 0) - x["soni"])
        p = db["promo"].get(o.get("promo") or "")
        if p:
            if o["chat"] in p.get("ishlatganlar", []):
                p["ishlatganlar"].remove(o["chat"])
            if p.get("qoldi") is not None:
                p["qoldi"] += 1
    if kim == "admin":
        send(o["chat"], "📦 Buyurtma <b>#%d</b> holati: <b>%s</b>" % (n, HOLAT[yangi]),
             ikb([[btn("📄 Buyurtma sahifasi", "o:%d" % n)]]))
    else:
        for a in ADMINS:
            send(a, "❌ Mijoz buyurtma <b>#%d</b> ni bekor qildi. Kitoblar omborga qaytarildi." % n)
    return True, HOLAT[yangi]


def xaridlarim(db, chat, u, mid=None):
    mening = sorted((o for o in db["buyurtmalar"].values() if o["chat"] == chat),
                    key=lambda o: -o["id"])[:15]
    if not mening:
        return edit(chat, mid, "📦 Hali xaridlaringiz yo'q.\n\nBirinchi kitobingizni tanlang — "
                               "tanishuv promokodi sizni kutyapti! 😉",
                    ikb([[btn("📚 Katalog", "cat")]]))
    rows = [[btn("#%d · %s · %s" % (o["id"], som(o["jami"]), HOLAT[o["holat"]]), "o:%d" % o["id"])]
            for o in mening]
    edit(chat, mid, "📦 <b>Xaridlarim</b>\n\nBuyurtmani tanlang — sahifasida holatini ko'rasiz "
                    "va kitoblarni ⭐ baholaysiz.", ikb(rows))


def buyurtma_sahifa(db, chat, u, mid, n):
    o = db["buyurtmalar"].get(str(n))
    if not o or o["chat"] != chat:
        return edit(chat, mid, "Buyurtma topilmadi.")
    rows = []
    if o["holat"] != "bekor":
        for x in o["qatorlar"]:
            b = db["kitoblar"].get(x["id"])
            if b:
                mb = (b.get("baholar") or {}).get(chat)
                rows.append([btn(("⭐ %d — " % mb if mb else "⭐ Baholash: ") + qisqa(x["nomi"], 24),
                                 "r:%s:%d" % (x["id"], n))])
    if o["holat"] == "yangi":
        rows.append([btn("❌ Buyurtmani bekor qilish", "oc:%d" % n)])
    rows.append([btn("⬅️ Xaridlarim", "ol")])
    edit(chat, mid, buyurtma_matn(o), ikb(rows))


# ---------------------------------------------------------------- admin
def admin_panel(db, chat, mid=None):
    st = hisobot.statistika(db, KAT)
    qiymat = sum(b.get("soni", 0) * narxi(b) for b in db["kitoblar"].values())
    matn = ("🛠 <b>Admin panel</b>\n\n"
            "💰 Jami tushum: <b>%s</b> (bugun: %s)\n🧾 Buyurtmalar: %d · kutmoqda: <b>%d</b>\n"
            "👥 Mijozlar: %d / %d\n📦 Omborda: %d dona (≈ %s)\n\n"
            "<b>Buyruqlar:</b>\n"
            "<code>/qoldiq b01 25</code> — ombordagi soni\n"
            "<code>/narx b01 49000</code> — narx\n"
            "<code>/aksiya b01 25</code> — aksiya %% (0 — olib tashlash)\n"
            "<code>/sovga b01 🔖 Xatcho'p</code> — sovg'a (<code>-</code> — olib tashlash)\n"
            "<code>/promo KOD 30 [soni] [2026-12-31]</code> — promokod (10–50%%)\n"
            "<code>/promo_ochir KOD</code>\n"
            "<code>/yangi_kitob nomi | muallif | janr | narx | soni | yosh | tavsif</code>\n"
            "<code>/havola instagram</code> — reklama havolasi (qayerdan kelganini sanaydi)\n"
            "<code>/xabar matn</code> — hammaga e'lon\n\n"
            "Janr kalitlari: %s"
            % (som(st["tushum"]), som(st["tushum_bugun"]), st["buyurtmalar"], st["yangi_buyurtma"],
               st["mijozlar"], st["maqsad"], st["ombor"], som(qiymat),
               ", ".join("<code>%s</code>" % k for k in KAT.get("janrlar", {}))))
    edit(chat, mid, matn, ikb([
        [btn("📊 Umumiy hisobot", "a:r"), btn("📈 Marketing tahlil", "a:mk")],
        [btn("🧾 Buyurtmalar" + (" (%d)" % st["yangi_buyurtma"] if st["yangi_buyurtma"] else ""), "a:o"),
         btn("👥 Mijozlar", "a:m:0")],
        [btn("📦 Ombor", "a:w"), btn("🐢 Sotilmayotganlar", "a:slow")],
        [btn("🎟 Promokodlar", "a:p")],
    ]))


def admin_hisobot(db, chat, mid):
    edit(chat, mid, hisobot.matn_hisobot(hisobot.statistika(db, KAT)),
         ikb([[btn("📈 Marketing tahlil (grafiklar)", "a:mk")], [btn("⬅️ Panel", "a:home")]]))


def admin_marketing(db, chat):
    st = hisobot.statistika(db, KAT)
    sahifa = hisobot.html_hisobot(st, KAT.get("dokon", {}).get("nomi", "Sehrli Javon"))
    nom = "marketing-%s.html" % st["bugun"]
    r = call("sendDocument", chat_id=chat, _fayl=("document", nom, sahifa.encode("utf-8"), "text/html"),
             caption="📈 Marketing tahlili — faylni oching (brauzerda ko'rinadi).\n"
                     "Tushum: %s · Mijozlar: %d / %d · Konversiya: %d%%"
                     % (som(st["tushum"]), st["mijozlar"], st["maqsad"], st["konversiya"]))
    if not r.get("ok"):
        send(chat, "Faylni yuborib bo'lmadi, birozdan keyin qayta urinib ko'ring.")


def admin_mijozlar(db, chat, mid, sahifa):
    xarid = {}
    for o in db["buyurtmalar"].values():
        if o["holat"] != "bekor":
            x = xarid.setdefault(o["chat"], [0, 0])
            x[0] += 1
            x[1] += o["jami"]
    royxat = sorted((u for u in db["users"].values() if u.get("royxat")),
                    key=lambda u: (-xarid.get(u["id"], [0, 0])[1], -(u.get("royxat_sana") or 0)))
    n = 15
    soni = max(1, (len(royxat) + n - 1) // n)
    sahifa = max(0, min(sahifa, soni - 1))
    q = ["👥 <b>Mijozlar</b>: %d ta (xarid qilgan: %d)" % (len(royxat), len(xarid)),
         "<i>Ko'p xarid qilganlar tepada</i>", ""]
    for i, u in enumerate(royxat[sahifa * n:(sahifa + 1) * n], sahifa * n + 1):
        b, j = xarid.get(u["id"], [0, 0])
        q.append("%d. <b>%s</b>, %s yosh%s%s\n    🧾 %d · %s%s" % (
            i, e(toliq_ism(u)), u.get("yosh") or "?",
            (" · @" + e(u["username"])) if u.get("username") else "",
            (" · " + e(u["tel"])) if u.get("tel") else "", b, som(j),
            (" · 📣 " + e(u["manba"])) if u.get("manba") else ""))
    if not royxat:
        q.append("Hali ro'yxatdan o'tgan mijoz yo'q.")
    rows = []
    if soni > 1:
        rows.append([btn("◀️", "a:m:%d" % ((sahifa - 1) % soni)), btn("%d / %d" % (sahifa + 1, soni), "nop"),
                     btn("▶️", "a:m:%d" % ((sahifa + 1) % soni))])
    rows.append([btn("⬅️ Panel", "a:home")])
    edit(chat, mid, "\n".join(q), ikb(rows))


def admin_buyurtmalar(db, chat, mid):
    ob = sorted(db["buyurtmalar"].values(),
                key=lambda o: (o["holat"] in ("yetkazildi", "bekor"), o["holat"] != "yangi", -o["id"]))[:20]
    if not ob:
        return edit(chat, mid, "Hali buyurtma yo'q.", ikb([[btn("⬅️ Panel", "a:home")]]))
    rows = []
    for o in ob:
        r = [btn("#%d · %s · %s · %s" % (o["id"], qisqa(o["ism"], 12), hisobot.qisqa_som(o["jami"]),
                                          HOLAT[o["holat"]][:1]), "a:d:%d" % o["id"])]
        if o["holat"] == "yangi":                     # doskadagi ✓ / ✗
            r += [btn("✅", "a:s:%d:tasdiqlandi:l" % o["id"]), btn("❌", "a:s:%d:bekor:l" % o["id"])]
        rows.append(r)
    rows.append([btn("⬅️ Panel", "a:home")])
    edit(chat, mid, "🧾 <b>Buyurtmalar</b>\nYangilari tepada: ✅ — tasdiqlash, ❌ — rad etish. "
                    "Batafsil — buyurtma ustiga bosing.", ikb(rows))


def admin_ombor(db, chat, mid):
    q = ["📦 <b>Ombor</b>", ""]
    for b in sorted(db["kitoblar"].values(), key=lambda b: b["id"]):
        q.append("<code>%s</code> %s — %d dona · %s%s%s" % (
            b["id"], e(qisqa(b["nomi"], 24)), b.get("soni", 0), som(b["narx"]),
            " 🔥−%d%%" % b["aksiya"] if b.get("aksiya") else "", " 🎁" if b.get("sovga") else ""))
    edit(chat, mid, "\n".join(q), ikb([[btn("⬅️ Panel", "a:home")]]))


def admin_sekin(db, chat, mid):
    r = [b for b in db["kitoblar"].values() if b.get("soni", 0) > 0]
    r.sort(key=lambda b: (b.get("sotildi", 0) / (b.get("sotildi", 0) + b["soni"]), -b["soni"]))
    q = ["🐢 <b>Sotilmayotgan kitoblar</b>", "<i>Omborda ko'p, sotuvi kam — aksiya qo'ying, "
         "keyin hammaga e'lon qiling.</i>", ""]
    rows = []
    for b in r[:8]:
        q.append("<code>%s</code> %s — omborda %d, sotilgan %d%s" % (
            b["id"], e(qisqa(b["nomi"], 24)), b["soni"], b.get("sotildi", 0),
            " (hozir −%d%%)" % b["aksiya"] if b.get("aksiya") else ""))
        rows.append([btn("🔥 %s: −20%%" % qisqa(b["nomi"], 14), "a:ak:%s:20" % b["id"]),
                     btn("−30%", "a:ak:%s:30" % b["id"]), btn("📣", "a:bc:%s" % b["id"])])
    rows.append([btn("⬅️ Panel", "a:home")])
    edit(chat, mid, "\n".join(q) if r else "Omborda kitob yo'q.", ikb(rows))


def admin_promolar(db, chat, mid):
    q = ["🎟 <b>Promokodlar</b>", ""]
    for k, p in sorted(db["promo"].items()):
        q.append("<code>%s</code> −%d%% · %s · qoldi: %s · ishlatildi: %d%s" % (
            k, p["foiz"], "✅" if p.get("faol") else "⛔",
            "∞" if p.get("qoldi") is None else p["qoldi"], len(p.get("ishlatganlar", [])),
            " · %s gacha" % p["muddat"] if p.get("muddat") else ""))
    edit(chat, mid, "\n".join(q), ikb([[btn("⬅️ Panel", "a:home")]]))


def elon(db, matn, kb=None):
    n = 0
    for chat, u in list(db["users"].items()):
        if not u.get("royxat") or u.get("blok"):
            continue
        r = send(chat, matn, kb)
        if r.get("ok"):
            n += 1
        elif r.get("error_code") == 403:
            u["blok"] = True                     # botni bloklagan
        time.sleep(0.05)                         # Telegram cheklovi: ~30 xabar/soniya
    return n


def kitob_elon(db, bid):
    b = db["kitoblar"][bid]
    matn = "🔥 <b>Aksiya!</b>\n\n📖 <b>%s</b> — %s\n" % (e(b["nomi"]), e(b["muallif"]))
    if b.get("aksiya"):
        matn += "<s>%s</s> → <b>%s</b> (−%d%%)\n" % (som(b["narx"]), som(narxi(b)), b["aksiya"])
    else:
        matn += "<b>%s</b>\n" % som(b["narx"])
    if b.get("sovga"):
        matn += "🎁 Sovg'a: %s\n" % e(b["sovga"])
    if b.get("soni", 0) <= 5:
        matn += "⚡ Atigi %d dona qoldi!\n" % b["soni"]
    return elon(db, matn, ikb([[btn("👀 Ko'rish", "k:%s:-:0" % bid)]]))


def admin_buyruq(db, chat, cmd, arg):
    """Admin buyrug'i bo'lsa — bajaradi va True qaytaradi."""
    kit = db["kitoblar"]

    def kitob(a):
        b = kit.get(a.lower())
        if not b:
            send(chat, "Kitob topilmadi: <code>%s</code>. /admin → 📦 Ombor — ID lar ro'yxati." % e(a))
        return b

    p = arg.split()
    if cmd == "/admin":
        admin_panel(db, chat)
    elif cmd in ("/qoldiq", "/narx", "/aksiya"):
        if len(p) != 2 or not p[1].isdigit():
            send(chat, "Foydalanish: <code>%s b01 25</code>" % cmd)
            return True
        b = kitob(p[0])
        if not b:
            return True
        v = int(p[1])
        if cmd == "/qoldiq":
            b["soni"] = v
        elif cmd == "/narx":
            if v < 1000:
                send(chat, "Narx kamida 1000 so'm bo'lsin.")
                return True
            b["narx"] = v
        else:
            if v > 90:
                send(chat, "Aksiya 0–90% oralig'ida bo'lsin.")
                return True
            b["aksiya"] = v
        send(chat, "✅ Saqlandi:\n\n" + kitob_matn(db, {"yosh": 99}, b),
             ikb([[btn("📣 Hammaga e'lon qilish", "a:bc:%s" % b["id"])]]) if cmd == "/aksiya" and v else None)
    elif cmd == "/sovga":
        if len(p) < 2:
            send(chat, "Foydalanish: <code>/sovga b01 🔖 Xatcho'p</code> yoki <code>/sovga b01 -</code>")
            return True
        b = kitob(p[0])
        if b:
            matn = arg.split(None, 1)[1].strip()
            b["sovga"] = None if matn == "-" else matn[:60]
            send(chat, "✅ Sovg'a: %s" % e(b["sovga"] or "yo'q"))
    elif cmd == "/promo":
        if len(p) < 2 or not re.fullmatch(r"[A-Za-z0-9]{3,20}", p[0]) or not p[1].isdigit():
            send(chat, "Foydalanish: <code>/promo KOD 30 [soni] [YYYY-MM-DD]</code>\n"
                       "KOD — 3–20 ta lotin harf/raqam, foiz — %d dan %d gacha." % (PROMO_MIN, PROMO_MAX))
            return True
        foiz = int(p[1])
        if not PROMO_MIN <= foiz <= PROMO_MAX:
            send(chat, "❗ Promokod foizi %d%% dan %d%% gacha bo'lishi kerak." % (PROMO_MIN, PROMO_MAX))
            return True
        qoldi, muddat = None, None
        for x in p[2:]:
            if x.isdigit():
                qoldi = int(x)
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", x):
                muddat = x
            else:
                send(chat, "Tushunmadim: <code>%s</code> — soni (raqam) yoki muddat (YYYY-MM-DD) bo'lsin." % e(x))
                return True
        kod = p[0].upper()
        eski = db["promo"].get(kod, {})
        db["promo"][kod] = {"foiz": foiz, "qoldi": qoldi, "muddat": muddat, "faol": True,
                            "ishlatganlar": eski.get("ishlatganlar", [])}
        send(chat, "✅ Promokod <code>%s</code>: −%d%%, soni: %s%s" % (
            kod, foiz, "cheksiz" if qoldi is None else qoldi, ", %s gacha" % muddat if muddat else ""))
    elif cmd == "/promo_ochir":
        kod = arg.strip().upper()
        if kod in db["promo"]:
            db["promo"][kod]["faol"] = False
            send(chat, "⛔ <code>%s</code> o'chirildi." % e(kod))
        else:
            send(chat, "Bunday promokod yo'q.")
    elif cmd == "/yangi_kitob":
        q = [x.strip() for x in arg.split("|")]
        janrlar = KAT.get("janrlar", {})
        if len(q) < 5 or not q[3].isdigit() or not q[4].isdigit() or q[2] not in janrlar \
                or (len(q) > 5 and q[5] and not q[5].isdigit()):
            send(chat, "Foydalanish:\n<code>/yangi_kitob Nomi | Muallif | janr | 45000 | 10 | 12 | Tavsif</code>\n\n"
                       "janr: %s\nyosh va tavsif ixtiyoriy." % ", ".join("<code>%s</code>" % k for k in janrlar))
            return True
        i = 1
        while "b%02d" % i in kit:
            i += 1
        bid = "b%02d" % i
        kit[bid] = {"id": bid, "nomi": q[0], "muallif": q[1], "janr": q[2], "narx": int(q[3]),
                    "soni": int(q[4]), "yosh": int(q[5]) if len(q) > 5 and q[5] else 0,
                    "aksiya": 0, "sovga": None, "tavsif": q[6] if len(q) > 6 else "",
                    "qiziq": "", "sotildi": 0, "baholar": {}, "sharhlar": []}
        send(chat, "✅ Kitob qo'shildi (<code>%s</code>):\n\n" % bid + kitob_matn(db, {"yosh": 99}, kit[bid]))
    elif cmd == "/havola":
        m = arg.strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{2,30}", m):
            send(chat, "Foydalanish: <code>/havola instagram</code>\nNom — lotin harf, raqam, _ (2–30 belgi).\n\n"
                       "Havolani reklamaga, varaqaga yoki QR kodga qo'ying — bot shu havoladan "
                       "kelganlarni alohida sanaydi (📈 Marketing tahlil → «qayerdan keldi»).")
            return True
        link = "https://t.me/%s?start=r_%s" % (bot_nomi(), m)
        xp = KAT.get("dokon", {}).get("xush_promo")
        send(chat, "🔗 <b>%s</b> uchun havola:\n<code>%s</code>\n\n"
                   "Shu havola orqali kirgan har bir yangi mijoz ro'yxatdan o'tgach %s oladi."
                   % (e(m), link, ("<code>%s</code> promokodini" % xp) if xp else "salomlashuv xabarini"))
    elif cmd == "/xabar":
        if not arg.strip():
            send(chat, "Foydalanish: <code>/xabar Yangi kitoblar keldi!</code>")
            return True
        send(chat, "📣 Yuborildi: %d ta mijozga" % elon(db, e(arg.strip())))
    else:
        return False
    return True


_BOT_NOMI = []


def bot_nomi():
    if not _BOT_NOMI:
        n = call("getMe").get("result", {}).get("username")
        if not n:
            return "SehrliJavonBot"
        _BOT_NOMI.append(n)
    return _BOT_NOMI[0]


def admin_tugma(db, chat, mid, p, cb_id):
    """p — callback_data qismlari: a:..."""
    if p[1] == "home":
        admin_panel(db, chat, mid)
    elif p[1] == "o":
        admin_buyurtmalar(db, chat, mid)
    elif p[1] == "w":
        admin_ombor(db, chat, mid)
    elif p[1] == "p":
        admin_promolar(db, chat, mid)
    elif p[1] == "slow":
        admin_sekin(db, chat, mid)
    elif p[1] == "r":
        admin_hisobot(db, chat, mid)
    elif p[1] == "mk":
        answer(cb_id, "📈 Tayyorlanmoqda…")
        admin_marketing(db, chat)
        return True
    elif p[1] == "m" and len(p) == 3:
        admin_mijozlar(db, chat, mid, int(p[2]))
    elif p[1] == "d" and len(p) == 3:
        o = db["buyurtmalar"].get(p[2])
        if o:
            edit(chat, mid, buyurtma_matn(o, admin=True), admin_buyurtma_kb(o))
    elif p[1] == "s" and len(p) in (4, 5):
        ok, x = holat_ozgartir(db, int(p[2]), p[3], "admin")
        answer(cb_id, x, alert=not ok)
        o = db["buyurtmalar"].get(p[2])
        if len(p) == 5:
            admin_buyurtmalar(db, chat, mid)
        elif o:
            edit(chat, mid, buyurtma_matn(o, admin=True), admin_buyurtma_kb(o))
        return True
    elif p[1] == "ak" and len(p) == 4:
        b = db["kitoblar"].get(p[2])
        if b:
            b["aksiya"] = int(p[3])
            answer(cb_id, "🔥 %s: −%s%%" % (b["nomi"], p[3]))
            admin_sekin(db, chat, mid)
            return True
    elif p[1] == "bc" and len(p) == 3:
        if p[2] in db["kitoblar"]:
            answer(cb_id, "📣 Yuborilmoqda…")
            send(chat, "📣 E'lon yuborildi: %d ta mijozga" % kitob_elon(db, p[2]))
            return True
    return False


# ---------------------------------------------------------------- xabarlar
YORDAM = (
    "ℹ️ <b>Sehrli Javon — qanday ishlaydi?</b>\n\n"
    "📚 <b>Katalog</b> — janrlar bo'yicha kitoblar\n"
    "🔥 <b>Aksiyalar</b> — chegirmali va sovg'ali kitoblar\n"
    "🎯 <b>Siz uchun</b> — yoshingizga mos tavsiyalar\n"
    "🎲 <b>Tasodifiy kitob</b> — taqdirga ishoning 😉\n"
    "🔍 <b>Qidiruv</b> — kitob yoki muallif nomini yozing\n"
    "🎟 <b>Promokod</b> — 10% dan 50% gacha chegirma\n"
    "📦 <b>Xaridlarim</b> — buyurtmalar holati va ⭐ baholash\n\n"
    "Istalgan paytda: /bekor — amalni bekor qilish."
)


def handle_message(db, msg):
    if msg["chat"].get("type") != "private":
        return
    chat = str(msg["chat"]["id"])
    frm = msg.get("from", {})
    u = foydalanuvchi(db, chat, frm)
    text = (msg.get("text") or "").strip()
    contact = msg.get("contact")
    cmd, arg = "", ""
    if text.startswith("/"):
        bol = text.split(None, 1)
        cmd, arg = bol[0].split("@")[0].lower(), (bol[1] if len(bol) > 1 else "")

    if cmd == "/start":
        u["qadam"] = None
        if arg.startswith("k_"):
            u["ochish"] = arg[2:]
        elif arg.startswith("r_") and not u.get("manba") and re.fullmatch(r"r_[a-z0-9_]{2,30}", arg):
            u["manba"] = arg[2:]                 # reklama manbasi (birinchi kelgani)
        if not u.get("royxat"):
            return reg_boshla(chat, u)
        send(chat, "📚✨ Yana xush kelibsiz, <b>%s</b>! Javonlarda sizni yangi kitoblar kutyapti."
                   % e(toliq_ism(u)), menyu())
        bid = u.pop("ochish", None)
        if bid in db["kitoblar"]:
            kitob_sahifa(db, chat, u, None, bid, "-", 0)
        return
    if cmd == "/men":
        return send(chat, "Telegram ID ingiz: <code>%s</code>" % chat)
    if cmd in ("/help", "/yordam"):
        return send(chat, YORDAM, menyu() if u.get("royxat") else None)
    if cmd and chat in ADMINS and admin_buyruq(db, chat, cmd, arg):
        return
    if cmd == "/bekor" or text == B_BEKOR:
        u["qadam"] = None
        if not u.get("royxat"):
            return reg_boshla(chat, u)
        return send(chat, "Bekor qilindi.", menyu())

    q = u.get("qadam") or ""
    if q in ("email", "ism", "yosh"):
        return reg_qadam(db, chat, u, text)
    if not u.get("royxat"):
        send(chat, "Avval ro'yxatdan o'tib olaylik 🙂")
        return reg_boshla(chat, u)

    if q == "tel":
        return tel_qadam(chat, u, text, contact, frm)
    if q == "manzil":
        return manzil_qadam(db, chat, u, text, msg.get("location"))
    if q == "promo" and text and not cmd and text not in MENYU_TUGMALARI:
        u["qadam"] = None
        ok, xato, foiz = promo_tekshir(db, text, chat)
        if not ok:
            u["qadam"] = "promo"
            return send(chat, "❌ %s\n\nBoshqa kodni yozing yoki /bekor." % xato)
        u["promo"] = text.strip().upper()
        send(chat, "✅ Promokod qabul qilindi: <b>−%d%%</b>\n"
                   "<i>Har bir kitobga eng katta chegirma qo'llanadi — aksiya yoki promokod.</i>" % foiz,
             menyu())
        return savat(db, chat, u)
    if q.startswith("sharh:") and text and not cmd and text not in MENYU_TUGMALARI:
        u["qadam"] = None
        bid = q.split(":", 1)[1]
        b = db["kitoblar"].get(bid)
        if b:
            for s in b.setdefault("sharhlar", []):
                if s["chat"] == chat:
                    s["matn"] = text[:500]
            send(chat, "💬 Rahmat! Sharhingiz boshqa kitobxonlarga yordam beradi.", menyu())
        return
    if q:
        u["qadam"] = None                    # menyu tugmasi bosildi — amal bekor

    if contact or msg.get("location"):
        return send(chat, "Raqam va lokatsiyani buyurtma berayotganda so'rayman 🙂", menyu())
    if text == B_KATALOG or cmd == "/katalog":
        return katalog(db, chat)
    if text == B_AKSIYA or cmd == "/aksiyalar":
        return royxat_sahifa(db, chat, u, None, "*aksiya", 0)
    if text == B_SIZ:
        return royxat_sahifa(db, chat, u, None, "*siz", 0)
    if text == B_TASODIF:
        return tasodifiy(db, chat, u)
    if text == B_SAVAT or cmd == "/savat":
        return savat(db, chat, u)
    if text == B_XARID or cmd == "/xaridlarim":
        return xaridlarim(db, chat, u)
    if text == B_PROMO or cmd == "/promokod":
        u["qadam"] = "promo"
        joriy = ("\n\nHozirgi promokodingiz: <code>%s</code>" % u["promo"]) if u.get("promo") else ""
        return send(chat, "🎟 Promokodni yozing (chegirma 10%% dan 50%% gacha):%s" % joriy, bekor_kb())
    if text == B_PROFIL:
        ob = [o for o in db["buyurtmalar"].values() if o["chat"] == chat and o["holat"] != "bekor"]
        return send(chat, "👤 <b>Profil</b>\n\n%s\n%s🎂 %s yosh\n%s\n"
                          "🧾 Buyurtmalar: %d\n💳 Xaridlar: %s\n🎉 Tejaldi: %s" % (
                              e(toliq_ism(u)),
                              ("📧 %s\n" % e(u["email"])) if u.get("email") else "",
                              u.get("yosh"), ("📱 %s\n" % e(u["tel"])) if u.get("tel") else "",
                              len(ob), som(sum(o["jami"] for o in ob)),
                              som(sum(o["asl"] - o["jami"] for o in ob))),
                    ikb([[btn("✏️ Ma'lumotlarni o'zgartirish", "reg:edit")]]))
    if cmd:
        return send(chat, "Bunday buyruq yo'q. /yordam", menyu())
    if text:
        return qidir(db, chat, u, text)
    send(chat, "Pastdagi menyudan tanlang 👇", menyu())


MENYU_TUGMALARI = {B_KATALOG, B_AKSIYA, B_SIZ, B_TASODIF, B_SAVAT, B_XARID, B_PROMO, B_PROFIL}


def handle_callback(db, cq):
    msg = cq.get("message") or {}
    if (msg.get("chat") or {}).get("type") != "private":
        return answer(cq["id"])
    chat = str(msg["chat"]["id"])
    mid = msg.get("message_id")
    u = foydalanuvchi(db, chat, cq.get("from", {}))
    p = (cq.get("data") or "").split(":")
    t, cb = p[0], cq["id"]
    javob = None                              # tugma ustida chiqadigan qisqa xabar

    if t == "reg":
        if p[1] == "gmail":
            u["qadam"] = "email"
            send(chat, "📧 Google akkauntingiz manzilini yozing:\n<i>masalan: aziz.karimov@gmail.com</i>",
                 {"remove_keyboard": True})
        elif p[1] == "ism":
            u["qadam"] = "ism"
            send(chat, "✍️ Ism va familiyangizni yozing:\n<i>masalan: Aziz Karimov</i>",
                 {"remove_keyboard": True})
        elif p[1] == "edit":
            u["royxat"] = False
            reg_boshla(chat, u)
        return answer(cb)
    if t == "nop":
        return answer(cb)
    if t == "a":
        if chat not in ADMINS:
            return answer(cb, "Faqat admin uchun.", True)
        if not admin_tugma(db, chat, mid, p, cb):
            answer(cb)
        return
    if not u.get("royxat"):
        answer(cb, "Avval ro'yxatdan o'ting 🙂")
        return reg_boshla(chat, u)

    if t == "cat":
        katalog(db, chat, mid)
    elif t == "j" and len(p) == 3:
        royxat_sahifa(db, chat, u, mid, p[1], int(p[2]))
    elif t == "k" and len(p) == 4:
        kitob_sahifa(db, chat, u, mid, p[1], p[2], int(p[3]))
    elif t == "+" and len(p) == 4:
        ok, javob = savatga(db, u, p[1])
        if p[2] != "~":                            # tasodifiy kartochka o'zgarmaydi
            kitob_sahifa(db, chat, u, mid, p[1], p[2], int(p[3]))
        return answer(cb, javob, alert=not ok)
    elif t == "sh" and len(p) == 4:
        sharhlar_sahifa(db, chat, mid, p[1], p[2], int(p[3]))
    elif t == "rnd":
        tasodifiy(db, chat, u, mid)
    elif t == "cart":
        savat(db, chat, u, mid)
    elif t in ("c+", "c-", "cx") and len(p) == 2:
        s = u.setdefault("savat", {})
        if t == "c+":
            ok, javob = savatga(db, u, p[1])
            if not ok:
                answer(cb, javob, alert=True)
                return savat(db, chat, u, mid)
        elif p[1] in s:
            s[p[1]] -= 1
            if t == "cx" or s[p[1]] <= 0:
                del s[p[1]]
                javob = "Savatdan olib tashlandi"
        savat(db, chat, u, mid)
    elif t == "cclr":
        u["savat"] = {}
        savat(db, chat, u, mid)
        javob = "Savat tozalandi"
    elif t == "cpromo":
        u["qadam"] = "promo"
        send(chat, "🎟 Promokodni yozing (chegirma 10% dan 50% gacha):", bekor_kb())
    elif t == "cpx":
        u["promo"] = None
        savat(db, chat, u, mid)
    elif t == "buy":
        buyurtma_boshla(db, chat, u)
    elif t == "pay" and len(p) == 2 and p[1] in TOLOV:
        if not u.get("tel") or not u.get("manzil"):
            answer(cb)
            return buyurtma_boshla(db, chat, u)
        u["tolov"] = p[1]
        edit(chat, mid, "💳 To'lov turi: <b>%s</b>" % TOLOV[p[1]])
        tasdiq_sahifa(db, chat, u)
    elif t == "ok" and len(p) == 2:
        buyurtma_tasdiq(db, chat, u, mid, p[1])
    elif t == "cancelbuy":
        edit(chat, mid, "Buyurtma bekor qilindi. Kitoblar savatda turibdi. 🛒",
             ikb([[btn("🛒 Savat", "cart")]]))
    elif t == "ol":
        xaridlarim(db, chat, u, mid)
    elif t == "o" and len(p) == 2:
        buyurtma_sahifa(db, chat, u, mid, int(p[1]))
    elif t == "oc" and len(p) == 2:
        edit(chat, mid, "Buyurtma <b>#%s</b> ni bekor qilasizmi?" % e(p[1]), ikb([
            [btn("Ha, bekor qilaman", "ocy:" + p[1]), btn("Yo'q", "o:" + p[1])]]))
    elif t == "ocy" and len(p) == 2:
        o = db["buyurtmalar"].get(p[1])
        if o and o["chat"] == chat and o["holat"] != "yangi":
            answer(cb, "Buyurtma allaqachon %s — bekor qilish uchun adminga yozing."
                   % HOLAT[o["holat"]].split(" ", 1)[1].lower(), alert=True)
            return buyurtma_sahifa(db, chat, u, mid, int(p[1]))
        if o and o["chat"] == chat:
            ok, javob = holat_ozgartir(db, int(p[1]), "bekor", "mijoz")
            if not ok:
                answer(cb, javob, alert=True)
                return buyurtma_sahifa(db, chat, u, mid, int(p[1]))
        buyurtma_sahifa(db, chat, u, mid, int(p[1]))
    elif t == "r" and len(p) == 3:
        b = db["kitoblar"].get(p[1])
        if not b or not xarid_qilganmi(db, chat, p[1]):
            return answer(cb, "Faqat sotib olgan kitobingizni baholay olasiz.", True)
        edit(chat, mid, "⭐ <b>%s</b> sizga qanchalik yoqdi?" % e(b["nomi"]), ikb([
            [btn("⭐" * i, "rs:%s:%d:%s" % (p[1], i, p[2])) for i in (1, 2, 3)],
            [btn("⭐" * i, "rs:%s:%d:%s" % (p[1], i, p[2])) for i in (4, 5)],
            [btn("⬅️ Orqaga", "o:" + p[2])]]))
    elif t == "rs" and len(p) == 4:
        b = db["kitoblar"].get(p[1])
        s = int(p[2]) if p[2].isdigit() else 0
        if not b or not 1 <= s <= 5 or not xarid_qilganmi(db, chat, p[1]):
            return answer(cb, "Faqat sotib olgan kitobingizni baholay olasiz.", True)
        b.setdefault("baholar", {})[chat] = s
        sh = b.setdefault("sharhlar", [])
        eski = next((x for x in sh if x["chat"] == chat), None)
        if eski:
            eski["baho"] = s
        else:
            sh.append({"chat": chat, "ism": u.get("ism") or "Kitobxon", "baho": s,
                       "matn": "", "sana": int(time.time())})
        u["qadam"] = "sharh:" + p[1]
        edit(chat, mid, "%s Rahmat! <b>%s</b> — %d yulduz.\n\n💬 Bir-ikki og'iz sharh yozasizmi? "
                        "Boshqa kitobxonlarga tanlashda yordam beradi." % ("⭐" * s, e(b["nomi"]), s),
             ikb([[btn("O'tkazib yuborish", "rskip:" + p[3])]]))
        javob = "Baholandi: %d ⭐" % s
    elif t == "rskip" and len(p) == 2:
        u["qadam"] = None
        buyurtma_sahifa(db, chat, u, mid, int(p[1]))
    answer(cb, javob)


def process(db, updates):
    last = None
    for upd in updates:
        last = upd["update_id"]
        try:
            if upd.get("message"):
                handle_message(db, upd["message"])
            elif upd.get("callback_query"):
                handle_callback(db, upd["callback_query"])
        except Exception as ex:                    # bitta xato botni to'xtatmasin
            import traceback
            traceback.print_exc()
            print("xato:", ex, file=sys.stderr)
            if upd.get("callback_query"):
                answer(upd["callback_query"]["id"], "Xatolik yuz berdi, qayta urinib ko'ring.")
    return last


# ---------------------------------------------------------------- ishga tushirish
def setup():
    nom = KAT.get("dokon", {}).get("nomi", "Sehrli Javon")
    natija = [
        call("deleteWebhook"),
        call("setMyName", name=nom + " 📚"),
        call("setMyCommands", commands=[
            {"command": "start", "description": "Boshlash"},
            {"command": "katalog", "description": "Kitoblar katalogi"},
            {"command": "aksiyalar", "description": "Aksiya va sovg'alar"},
            {"command": "savat", "description": "Savat"},
            {"command": "xaridlarim", "description": "Buyurtmalarim va baholash"},
            {"command": "promokod", "description": "Promokod kiritish"},
            {"command": "yordam", "description": "Yordam"},
            {"command": "bekor", "description": "Amalni bekor qilish"},
        ]),
        call("setMyDescription", description=(
            "📚✨ Sehrli Javon — kitoblar do'koni.\n\n🔥 Aksiyalar va sovg'alar\n"
            "🎟 10–50% promokodlar\n🎯 Yoshingizga mos tavsiyalar\n⭐ Kitobxonlar baholari\n\n"
            "Boshlash uchun «Start» ni bosing!")),
        call("setMyShortDescription", short_description=
             "Kitoblar do'koni: aksiyalar, sovg'alar, 10–50% promokodlar 📚✨"),
    ]
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("natija:", [r.get("ok") for r in natija])
    return all(r.get("ok") for r in natija[:1] + natija[2:])   # nom — ixtiyoriy (limit bor)


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    db = yukla()
    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    turlar = ["message", "callback_query"]
    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=turlar)
        last = process(db, r.get("result", []))
        saqla(db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0, limit=1)
        print("qayta ishlandi: %d ta" % len(r.get("result", [])))
        return

    muddat = None
    if "--for" in argv:
        i = argv.index("--for")
        muddat = time.time() + int(argv[i + 1] if len(argv) > i + 1 else 270)
    offset = None
    print("Bot ishga tushdi. Mijozlar: %d, kitoblar: %d" % (len(db["users"]), len(db["kitoblar"])))
    while True:
        kutish = 50
        if muddat is not None:
            kutish = int(muddat - time.time()) - 5
            if kutish < 1:
                break
            kutish = min(kutish, 50)
        r = call("getUpdates", offset=offset, timeout=kutish, allowed_updates=turlar)
        if not r.get("ok"):
            time.sleep(3)
            continue
        last = process(db, r.get("result", []))
        if last is not None:
            offset = last + 1
            saqla(db)
    if offset is not None:
        call("getUpdates", offset=offset, timeout=0, limit=1)   # «shulargacha ko'rdim»
    saqla(db)


if __name__ == "__main__":
    main(sys.argv[1:])

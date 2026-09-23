#!/usr/bin/env python3
"""
Kitob.uz — Juma aksiyasi Telegram boti.

Vazifasi:
  1. Odamlarni har juma bo'ladigan aksiyaga jalb qilish.
  2. Botdan foydalanishdan oldin ro'yxatdan o'tish: telefon raqami,
     ism-familiya, tug'ilgan sana (kun.oy.yil) va qiziqadigan kitob turlari.
  3. Aksiya boshlanishidan oldin (standart — 3 kun) har bir ro'yxatdan
     o'tganga eslatma: uning qiziqishiga mos chegirmadagi kitoblar bilan.
     Aksiya boshlanganda yana bitta qisqa xabar.
  4. Aksiyada kitoblarga 10% dan 30% gacha chegirma (bot boshqasiga ruxsat
     bermaydi).
  5. Xodim paneli — dasturchisiz boshqarish: kitob qo'shish/o'chirish,
     chegirmani o'zgartirish, aksiya vaqti va eslatma muddati, xabar
     yuborish, kelgan mijozni belgilash, tahlil va Excel (CSV) jadval.

Faqat standart kutubxona. Ma'lumotlar bitta JSON faylda.

Rejimlar:
    python3 bot.py              # doimiy (server bo'lsa): long polling + jadval
    python3 bot.py --once       # GitHub Actions: xabarlarni qayta ishlaydi,
                                #   eslatma vaqti kelgan bo'lsa yuboradi
    python3 bot.py --setup      # buyruqlar va tavsif

Muhit o'zgaruvchilari:
    BOT_TOKEN      BotFather bergan token
    ADMIN_IDS      egalarning Telegram ID lari, vergul bilan
    XODIM_KODI     xodim bo'lish kodi: xodim botga `/xodim KOD` yozadi
    STATE_FILE     ma'lumotlar fayli (ixtiyoriy)
    DOKON_NOMI     do'kon nomi (standart: Kitob.uz)
"""

import csv
import html
import io
import json
import os
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
XODIM_KODI = os.environ.get("XODIM_KODI", "").strip()
DOKON = os.environ.get("DOKON_NOMI", "").strip() or "Kitob.uz"
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "kitob.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

TZ = timezone(timedelta(hours=5))          # Toshkent vaqti
MIN_CHEGIRMA, MAX_CHEGIRMA = 10, 30
CHEGIRMALAR = [10, 15, 20, 25, 30]
KUNLAR = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
         "sentabr", "oktabr", "noyabr", "dekabr"]

JANRLAR = [
    ("badiiy", "📖 Badiiy adabiyot"),
    ("diniy", "🕌 Diniy kitoblar"),
    ("rivoj", "🧠 Psixologiya va shaxsiy rivojlanish"),
    ("biznes", "💼 Biznes va moliya"),
    ("tarix", "🏛 Tarix va biografiya"),
    ("ilmiy", "🔬 Ilmiy-ommabop"),
    ("bolalar", "🧸 Bolalar adabiyoti"),
    ("talim", "🎓 Darslik va til o'rganish"),
    ("detektiv", "🕵️ Detektiv va fantastika"),
]
JANR = dict(JANRLAR)

# mijoz menyusi
B_AKSIYA = "🔥 Juma aksiyasi"
B_KITOBLAR = "📚 Chegirmadagi kitoblar"
B_PROFIL = "👤 Profilim"
B_TAKLIF = "🎁 Do'stni taklif qilish"
B_PANEL = "🛠 Xodim paneli"
# xodim menyusi
B_TAHLIL = "📊 Tahlil"
B_CSV = "📥 Excel jadval"
B_RO_KITOB = "📚 Kitoblar"
B_QOSH = "➕ Kitob qo'shish"
B_SOZLA = "⚙️ Aksiya sozlamalari"
B_XABAR = "📣 Xabar yuborish"
B_KELDI = "🧾 Kelganini belgilash"
B_MIJOZ = "👥 Mijoz ko'rinishi"
B_TEL = "📱 Raqamni yuborish"

STANDART_AKSIYA = {
    "kun": 4,                 # 0 — dushanba ... 4 — juma
    "boshlanish": "10:00",
    "tugash": "20:00",
    "eslatma_soat": 72,       # boshlanishidan necha soat oldin (72 = 3 kun)
    "faol": True,
    "izoh": "",
}

_bot_username = None


# ---------------------------------------------------------------- Telegram API
def call(method, **params):
    data = urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                      for k, v in params.items() if v is not None}).encode()
    try:
        with urlopen(Request(API + method, data=data), timeout=70) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            body = json.load(e)
        except ValueError:
            body = {"description": str(e)}
        print("telegram xatosi:", method, body.get("description"), file=sys.stderr)
        return {"ok": False, **body}
    except URLError as e:
        print("tarmoq xatosi:", e, file=sys.stderr)
        return {"ok": False}


def send(chat_id, text, markup=None):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
                reply_markup=markup, disable_web_page_preview="true")


def edit(chat_id, message_id, text, markup=None):
    return call("editMessageText", chat_id=chat_id, message_id=message_id, text=text,
                parse_mode="HTML", reply_markup=markup or {"inline_keyboard": []})


def send_file(chat_id, name, data, caption=""):
    """sendDocument — multipart/form-data, faqat standart kutubxona bilan."""
    chegara = uuid.uuid4().hex
    qism = []
    for k, v in (("chat_id", str(chat_id)), ("caption", caption)):
        qism.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                     % (chegara, k, v)).encode())
    qism.append(("--%s\r\nContent-Disposition: form-data; name=\"document\"; "
                 "filename=\"%s\"\r\nContent-Type: text/csv\r\n\r\n" % (chegara, name)).encode())
    qism.append(data)
    qism.append(("\r\n--%s--\r\n" % chegara).encode())
    req = Request(API + "sendDocument", data=b"".join(qism),
                  headers={"Content-Type": "multipart/form-data; boundary=" + chegara})
    try:
        with urlopen(req, timeout=70) as r:
            return json.load(r)
    except (HTTPError, URLError) as e:
        print("fayl yuborishda xato:", e, file=sys.stderr)
        return {"ok": False}


def bot_username():
    global _bot_username
    if _bot_username is None:
        _bot_username = (call("getMe").get("result") or {}).get("username", "")
    return _bot_username


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    db.setdefault("xodimlar", [])
    db.setdefault("kitoblar", [])
    db.setdefault("yuborilgan", {})
    db.setdefault("keyingi_id", 1)
    aksiya = db.setdefault("aksiya", {})
    for k, v in STANDART_AKSIYA.items():
        aksiya.setdefault(k, v)
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- yordamchilar
def e(s):
    return html.escape(str(s or ""))


def hozir():
    return datetime.now(TZ)


def som(n):
    return "{:,}".format(int(round(n))).replace(",", " ") + " so'm"


def sana_matn(d):
    return "%d-%s, %s" % (d.day, OYLAR[d.month - 1], KUNLAR[d.weekday()])


def muddat_matn(soat):
    if soat % 24 == 0:
        return "%d kun" % (soat // 24)
    return "%d soat" % soat


def vaqt(s):
    h, m = s.split(":")
    return int(h), int(m)


def aksiya_boshi(db, d):
    h, m = vaqt(db["aksiya"]["boshlanish"])
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


def aksiya_oxiri(db, d):
    h, m = vaqt(db["aksiya"]["tugash"])
    return datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)


def keyingi_aksiya(db, now=None):
    """Hali tugamagan eng yaqin aksiya sanasi (bugun bo'lsa ham)."""
    now = now or hozir()
    d = now.date()
    d += timedelta(days=(db["aksiya"]["kun"] - d.weekday()) % 7)
    if now >= aksiya_oxiri(db, d):
        d += timedelta(days=7)
    return d


def oxirgi_aksiya(db, now=None):
    """Bugun aksiya kuni bo'lsa — bugun, aks holda o'tgan aksiya sanasi."""
    now = now or hozir()
    d = now.date()
    return d - timedelta(days=(d.weekday() - db["aksiya"]["kun"]) % 7)


def yosh(tugilgan, bugun=None):
    t = date.fromisoformat(tugilgan)
    bugun = bugun or hozir().date()
    return bugun.year - t.year - ((bugun.month, bugun.day) < (t.month, t.day))


def telefon_toza(s):
    raqam = re.sub(r"\D", "", s or "")
    if len(raqam) == 9:
        raqam = "998" + raqam
    if len(raqam) == 12 and raqam.startswith("998"):
        return "+" + raqam
    if 10 <= len(raqam) <= 15 and (s or "").strip().startswith("+"):
        return "+" + raqam
    return None


def sana_toza(s):
    s = (s or "").strip()
    m = re.fullmatch(r"(\d{1,2})[./\- ](\d{1,2})[./\- ](\d{4})", s)
    try:
        if m:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        else:
            d = date.fromisoformat(s)
    except ValueError:
        return None
    if not 5 <= yosh(d.isoformat()) <= 100:
        return None
    return d


def ism_toza(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    qism = s.split(" ")
    if len(qism) < 2 or len(s) > 60:
        return None
    if not all(re.fullmatch(r"[^\W\d_][\w'ʻʼ`‘’\-]*", q) for q in qism):
        return None
    return " ".join(q[:1].upper() + q[1:] for q in qism)


def narx_toza(s):
    raqam = re.sub(r"[\s,.']|so'?m", "", (s or "").lower())
    return int(raqam) if raqam.isdigit() and 0 < int(raqam) < 10**9 else None


def xodimmi(db, chat):
    return chat in ADMINS or chat in db["xodimlar"]


def royxatdan_otgan(u):
    return bool(u and u.get("royxat"))


def mijozlar(db):
    return [u for u in db["users"].values() if royxatdan_otgan(u)]


def shaxsiy_kod(db):
    band = {u.get("kod") for u in db["users"].values()}
    n = 1000 + len(band)
    while "K%d" % n in band:
        n += 1
    return "K%d" % n


def kitob_qator(k):
    yangi = k["narx"] * (100 - k["chegirma"]) / 100
    return "• <b>%s</b> — <s>%s</s> → <b>%s</b> (−%d%%)" % (
        e(k["nom"]), som(k["narx"]), som(yangi), k["chegirma"])


def mos_kitoblar(db, u, n=6):
    """Mijoz qiziqishiga mos kitoblar oldinda, keyin eng katta chegirmalar."""
    q = set(u.get("qiziqish") or [])
    return sorted(db["kitoblar"],
                  key=lambda k: (k["janr"] not in q, -k["chegirma"]))[:n]


# ---------------------------------------------------------------- klaviaturalar
def mijoz_menyu(db, chat):
    rows = [[{"text": B_AKSIYA}, {"text": B_KITOBLAR}],
            [{"text": B_PROFIL}, {"text": B_TAKLIF}]]
    if xodimmi(db, chat):
        rows.append([{"text": B_PANEL}])
    return {"keyboard": rows, "resize_keyboard": True}


def xodim_menyu():
    return {"keyboard": [[{"text": B_TAHLIL}, {"text": B_CSV}],
                         [{"text": B_RO_KITOB}, {"text": B_QOSH}],
                         [{"text": B_SOZLA}, {"text": B_XABAR}],
                         [{"text": B_KELDI}, {"text": B_MIJOZ}]],
            "resize_keyboard": True}


def tel_klav():
    return {"keyboard": [[{"text": B_TEL, "request_contact": True}]],
            "resize_keyboard": True, "one_time_keyboard": True}


def janr_klav(tanlangan, prefix="q", tayyor=True):
    rows = [[{"text": ("✅ " if k in tanlangan else "") + nom, "callback_data": "%s:%s" % (prefix, k)}]
            for k, nom in JANRLAR]
    if tayyor:
        rows.append([{"text": "➡️ Tayyor", "callback_data": prefix + ":tayyor"}])
    return {"inline_keyboard": rows}


def chegirma_klav(prefix):
    return {"inline_keyboard": [[{"text": "−%d%%" % c, "callback_data": "%s:%d" % (prefix, c)}
                                 for c in CHEGIRMALAR]]}


def rsvp_klav(d):
    return {"inline_keyboard": [
        [{"text": "✅ Boraman", "callback_data": "rsvp:" + d.isoformat()}],
        [{"text": "📚 Barcha chegirmadagi kitoblar", "callback_data": "kitoblar"}],
    ]}


# ---------------------------------------------------------------- matnlar
def aksiya_matn(db, u=None, sarlavha=None):
    a = db["aksiya"]
    d = keyingi_aksiya(db)
    qator = [sarlavha or "🔥 <b>%s — Juma aksiyasi</b>" % e(DOKON), "",
             "📅 %s, %s–%s" % (sana_matn(d), a["boshlanish"], a["tugash"]),
             "💸 Kitoblarga <b>%d%% dan %d%% gacha</b> chegirma!" % (MIN_CHEGIRMA, MAX_CHEGIRMA)]
    if not a["faol"]:
        qator = ["⏸ Juma aksiyasi hozircha to'xtatilgan. Qayta boshlanganda xabar beramiz."]
        return "\n".join(qator)
    kitoblar = mos_kitoblar(db, u or {})
    if kitoblar:
        q = set((u or {}).get("qiziqish") or [])
        mos = q and any(k["janr"] in q for k in kitoblar)
        qator += ["", "<b>%s:</b>" % ("Sizga mos kitoblar" if mos else "Chegirmadagi kitoblar")]
        qator += [kitob_qator(k) for k in kitoblar]
        if len(db["kitoblar"]) > len(kitoblar):
            qator.append("… va yana %d ta kitob" % (len(db["kitoblar"]) - len(kitoblar)))
    if a["izoh"]:
        qator += ["", e(a["izoh"])]
    if u and u.get("kod"):
        qator += ["", "🎫 Shaxsiy kodingiz: <b>%s</b> — kassada ayting." % u["kod"]]
    return "\n".join(qator)


def profil_matn(u):
    q = ", ".join(JANR.get(k, k) for k in u.get("qiziqish") or []) or "—"
    t = date.fromisoformat(u["tugilgan"])
    return ("👤 <b>%s</b>\n📱 %s\n🎂 %s (%d yosh)\n📚 %s\n🎫 Shaxsiy kod: <b>%s</b>"
            % (e(u["ism"]), e(u["telefon"]), t.strftime("%d.%m.%Y"), yosh(u["tugilgan"]),
               e(q), u.get("kod", "—")))


# ---------------------------------------------------------------- ro'yxatdan o'tish
def royxat_boshla(chat, u):
    u["holat"] = "tel"
    send(chat, "Assalomu alaykum! 👋\n\n<b>%s</b> har juma kitoblarga <b>%d%% dan %d%% gacha</b> "
               "chegirma qiladi. Aksiyadan oldin sizga eslatib, qiziqishingizga mos kitoblarni "
               "yuboramiz.\n\nBotdan foydalanish uchun qisqa ro'yxatdan o'ting (4 qadam).\n\n"
               "<b>1/4.</b> Telefon raqamingizni yuboring — pastdagi tugmani bosing "
               "yoki yozing: <code>+998901234567</code>" % (e(DOKON), MIN_CHEGIRMA, MAX_CHEGIRMA),
         tel_klav())


def royxat_qadam(db, chat, u, msg, text):
    h = u.get("holat")
    if h == "tel":
        kontakt = msg.get("contact")
        if kontakt and kontakt.get("user_id") not in (None, msg.get("from", {}).get("id")):
            send(chat, "Iltimos, <b>o'zingizning</b> raqamingizni yuboring.", tel_klav())
            return
        tel = telefon_toza(kontakt["phone_number"] if kontakt else text)
        if not tel:
            send(chat, "Raqam noto'g'ri. Masalan: <code>+998901234567</code>", tel_klav())
            return
        boshqa = next((x for x in mijozlar(db) if x.get("telefon") == tel and x["id"] != chat), None)
        if boshqa:
            send(chat, "Bu raqam boshqa hisobda ro'yxatdan o'tgan. Boshqa raqam yuboring "
                       "yoki do'kon xodimiga murojaat qiling.", tel_klav())
            return
        u["telefon"] = tel
        u["holat"] = "ism"
        send(chat, "<b>2/4.</b> Ism va familiyangizni yozing.\nMasalan: <i>Aziza Karimova</i>",
             {"remove_keyboard": True})
    elif h == "ism":
        ism = ism_toza(text)
        if not ism:
            send(chat, "Ism va familiyani bo'sh joy bilan yozing, raqamsiz. "
                       "Masalan: <i>Aziza Karimova</i>")
            return
        u["ism"] = ism
        u["holat"] = "sana"
        send(chat, "<b>3/4.</b> Tug'ilgan sanangiz (kun.oy.yil).\nMasalan: <code>15.03.1998</code>")
    elif h == "sana":
        d = sana_toza(text)
        if not d:
            send(chat, "Sanani <code>kun.oy.yil</code> ko'rinishida yozing. "
                       "Masalan: <code>15.03.1998</code>")
            return
        u["tugilgan"] = d.isoformat()
        u["holat"] = "qiziqish"
        u["qiziqish"] = []
        send(chat, "<b>4/4.</b> Qanday kitoblarga qiziqasiz? Bir nechtasini tanlashingiz mumkin, "
                   "keyin <b>➡️ Tayyor</b> ni bosing.", janr_klav([]))
    elif h == "qiziqish":
        send(chat, "Yuqoridagi ro'yxatdan kitob turlarini tanlab, <b>➡️ Tayyor</b> ni bosing.",
             janr_klav(u.get("qiziqish") or []))


def royxat_tugat(db, chat, u):
    yangi = not u.get("royxat")
    u["holat"] = None
    u.setdefault("royxat", int(time.time()))
    u.setdefault("kod", shaxsiy_kod(db))
    matn = ("🎉 <b>Ro'yxatdan o'tdingiz!</b>\n\n" if yangi else "✅ Saqlandi.\n\n") + profil_matn(u)
    if yangi:
        matn += ("\n\nAksiyadan <b>%s</b> oldin eslatamiz. Hozircha aksiya haqida "
                 "<b>%s</b> tugmasida o'qing." % (muddat_matn(db["aksiya"]["eslatma_soat"]), B_AKSIYA))
        taklif = db["users"].get(u.get("taklif_qilgan") or "")
        if taklif and royxatdan_otgan(taklif):
            send(taklif["id"], "🎁 Do'stingiz <b>%s</b> sizning havolangiz orqali ro'yxatdan o'tdi. "
                               "Rahmat!" % e(u["ism"]))
    send(chat, matn, mijoz_menyu(db, chat))


# ---------------------------------------------------------------- xodim paneli
def tahlil_matn(db):
    now = hozir()
    hamma = list(db["users"].values())
    mij = mijozlar(db)
    n = len(mij)
    foiz = lambda a, b: (100 * a // b) if b else 0
    hafta = now.timestamp() - 7 * 86400
    kel = keyingi_aksiya(db, now)
    q = ["📊 <b>Tahlil</b> — %s" % now.strftime("%d.%m.%Y %H:%M"), "",
         "Botni ochgan: <b>%d</b>" % len(hamma),
         "Ro'yxatdan o'tgan: <b>%d</b> (%d%%)" % (n, foiz(n, len(hamma))),
         "Oxirgi 7 kunda yangi: <b>+%d</b>" % sum(1 for u in mij if u["royxat"] >= hafta),
         "Botni bloklagan: %d" % sum(1 for u in mij if u.get("bloklagan")),
         "Do'st taklifi bilan kelgan: %d" % sum(1 for u in mij if u.get("taklif_qilgan")),
         "", "<b>Keyingi aksiya: %s</b>" % sana_matn(kel)]
    ek = "eslatma:" + kel.isoformat()
    q.append("Eslatma: " + ("yuborildi (%d ta)" % db["yuborilgan"][ek] if ek in db["yuborilgan"]
                            else "%s da yuboriladi" % (aksiya_boshi(db, kel) - timedelta(
                                hours=db["aksiya"]["eslatma_soat"])).strftime("%d.%m %H:%M")))
    q.append("«Boraman» bosganlar: <b>%d</b>" % sum(1 for u in mij if kel.isoformat() in (u.get("rsvp") or [])))

    tarix = []
    d = oxirgi_aksiya(db, now)
    if d == kel:
        d -= timedelta(days=7)
    for _ in range(4):
        s = d.isoformat()
        b = sum(1 for u in mij if s in (u.get("rsvp") or []))
        k = sum(1 for u in mij if s in (u.get("keldi") or []))
        kb = sum(1 for u in mij if s in (u.get("keldi") or []) and s in (u.get("rsvp") or []))
        if b or k:
            tarix.append("%s: boraman %d → keldi %d (shundan boraman degan %d)" %
                         (d.strftime("%d.%m"), b, k, kb))
        d -= timedelta(days=7)
    if tarix:
        q += ["", "<b>O'tgan aksiyalar:</b>"] + tarix

    if n:
        q += ["", "<b>Qiziqishlar:</b>"]
        sanoq = sorted(((sum(1 for u in mij if k in (u.get("qiziqish") or [])), nom)
                        for k, nom in JANRLAR), reverse=True)
        for c, nom in sanoq:
            q.append("%s — %d (%d%%)" % (nom, c, foiz(c, n)))
        q += ["", "<b>Yosh:</b>"]
        guruh = [("18 gacha", 0, 17), ("18–24", 18, 24), ("25–34", 25, 34),
                 ("35–44", 35, 44), ("45–54", 45, 54), ("55+", 55, 200)]
        yoshlar = [yosh(u["tugilgan"], now.date()) for u in mij]
        for nom, a, b in guruh:
            c = sum(1 for y in yoshlar if a <= y <= b)
            if c:
                q.append("%s — %d (%d%%)" % (nom, c, foiz(c, n)))
        tk = []
        for u in mij:
            t = date.fromisoformat(u["tugilgan"])
            for i in range(7):
                kun = now.date() + timedelta(days=i)
                if (t.month, t.day) == (kun.month, kun.day):
                    tk.append("%s — %s (%s)" % (e(u["ism"]), kun.strftime("%d.%m"), e(u["telefon"])))
        if tk:
            q += ["", "🎂 <b>7 kun ichida tug'ilgan kun:</b>"] + tk
        taklif = {}
        for u in mij:
            if u.get("taklif_qilgan"):
                taklif[u["taklif_qilgan"]] = taklif.get(u["taklif_qilgan"], 0) + 1
        if taklif:
            q += ["", "<b>Eng ko'p taklif qilganlar:</b>"]
            for uid, c in sorted(taklif.items(), key=lambda x: -x[1])[:5]:
                q.append("%s — %d kishi" % (e(db["users"].get(uid, {}).get("ism", uid)), c))
    kit = db["kitoblar"]
    q += ["", "<b>Chegirmadagi kitoblar:</b> %d ta" % len(kit)]
    if kit:
        q.append("O'rtacha chegirma: %d%%" % (sum(k["chegirma"] for k in kit) // len(kit)))
    return "\n".join(q)


def csv_fayl(db):
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(["Kod", "Ism familiya", "Telefon", "Tug'ilgan sana", "Tug'ilgan yil", "Yosh",
                "Qiziqishlar", "Ro'yxatdan o'tgan", "Taklif qilgan", "Boraman (aksiyalar)",
                "Kelgan (aksiyalar)", "Botni bloklagan"])
    for u in sorted(mijozlar(db), key=lambda u: u["royxat"]):
        t = date.fromisoformat(u["tugilgan"])
        w.writerow([u.get("kod"), u["ism"], u["telefon"], t.strftime("%d.%m.%Y"), t.year,
                    yosh(u["tugilgan"]), ", ".join(JANR.get(k, k) for k in u.get("qiziqish") or []),
                    datetime.fromtimestamp(u["royxat"], TZ).strftime("%d.%m.%Y %H:%M"),
                    db["users"].get(u.get("taklif_qilgan") or "", {}).get("ism", ""),
                    len(u.get("rsvp") or []), len(u.get("keldi") or []),
                    "ha" if u.get("bloklagan") else ""])
    return ("﻿" + f.getvalue()).encode("utf-8")      # BOM — Excel o'zbekcha harflarni to'g'ri ochadi


def kitoblar_klav(db):
    rows = [[{"text": "%s  −%d%%" % (k["nom"][:30], k["chegirma"]), "callback_data": "kb:%d" % k["id"]}]
            for k in db["kitoblar"]]
    if db["kitoblar"]:
        rows.append([{"text": "🗑 Hammasini o'chirish (yangi hafta)", "callback_data": "ktoza"}])
    return {"inline_keyboard": rows}


def kitoblar_royxat(db):
    if not db["kitoblar"]:
        return "Chegirmadagi kitoblar yo'q. <b>%s</b> tugmasi bilan qo'shing." % B_QOSH
    return ("📚 <b>Chegirmadagi kitoblar (%d):</b>\n\n" % len(db["kitoblar"])
            + "\n".join("%s  <i>%s</i>" % (kitob_qator(k), e(JANR.get(k["janr"], "")))
                        for k in db["kitoblar"])
            + "\n\nO'zgartirish yoki o'chirish uchun kitobni bosing.")


def kitob_karta(k):
    return ("📖 <b>%s</b>\nTuri: %s\nNarxi: %s\nChegirma: <b>%d%%</b> → %s\n\n"
            "Chegirmani o'zgartirish yoki o'chirish:" %
            (e(k["nom"]), JANR.get(k["janr"], "—"), som(k["narx"]), k["chegirma"],
             som(k["narx"] * (100 - k["chegirma"]) / 100)))


def kitob_karta_klav(k):
    rows = chegirma_klav("kc:%d" % k["id"])["inline_keyboard"]
    rows.append([{"text": "🗑 O'chirish", "callback_data": "kdel:%d" % k["id"]}])
    return {"inline_keyboard": rows}


def sozlama_matn(db):
    a = db["aksiya"]
    kel = keyingi_aksiya(db)
    return ("⚙️ <b>Aksiya sozlamalari</b>\n\n"
            "Holati: %s\nKuni: har %s\nVaqti: %s–%s\n"
            "Eslatma: boshlanishidan <b>%s</b> oldin\nKeyingi aksiya: %s\n"
            "Chegirma chegarasi: %d%%–%d%%\nQo'shimcha matn: %s" %
            ("▶️ faol" if a["faol"] else "⏸ to'xtatilgan", KUNLAR[a["kun"]],
             a["boshlanish"], a["tugash"], muddat_matn(a["eslatma_soat"]), sana_matn(kel),
             MIN_CHEGIRMA, MAX_CHEGIRMA, e(a["izoh"]) or "—"))


def sozlama_klav(db):
    a = db["aksiya"]
    es = [(3, "3 soat"), (24, "1 kun"), (48, "2 kun"), (72, "3 kun")]
    return {"inline_keyboard": [
        [{"text": ("✅ " if a["eslatma_soat"] == h else "") + t, "callback_data": "es:%d" % h}
         for h, t in es],
        [{"text": "🕙 Vaqtni o'zgartirish", "callback_data": "svaqt"},
         {"text": "📝 Qo'shimcha matn", "callback_data": "sizoh"}],
        [{"text": "⏸ To'xtatish" if a["faol"] else "▶️ Yoqish", "callback_data": "sfaol"},
         {"text": "👁 Eslatmani ko'rish", "callback_data": "skor"}],
    ]}


def xabar_klav(db):
    mij = [u for u in mijozlar(db) if not u.get("bloklagan")]
    rows = [[{"text": "👥 Hammaga (%d)" % len(mij), "callback_data": "xb:hamma"}]]
    for k, nom in JANRLAR:
        c = sum(1 for u in mij if k in (u.get("qiziqish") or []))
        if c:
            rows.append([{"text": "%s (%d)" % (nom, c), "callback_data": "xb:" + k}])
    rows.append([{"text": "✖️ Bekor qilish", "callback_data": "xb:bekor"}])
    return {"inline_keyboard": rows}


def mijoz_top(db, s):
    s = s.strip().upper()
    tel = telefon_toza(s)
    for u in mijozlar(db):
        if u.get("kod") == s or (tel and u.get("telefon") == tel):
            return u
    return None


def xodim_holat(db, chat, u, text):
    """Xodim biror qiymat kiritayotgan bo'lsa (kitob nomi, narx...). True — qayta ishlandi."""
    h = u.get("holat")
    tmp = u.setdefault("tmp", {})
    if h == "k_nom":
        if not text or len(text) > 120:
            send(chat, "Kitob nomini yozing (120 belgigacha).")
            return True
        tmp["nom"] = text
        u["holat"] = "k_janr"
        send(chat, "Kitob turi:", janr_klav([], prefix="kj", tayyor=False))
        return True
    if h == "k_narx":
        narx = narx_toza(text)
        if not narx:
            send(chat, "Narxni raqam bilan yozing. Masalan: <code>85000</code>")
            return True
        tmp["narx"] = narx
        u["holat"] = "k_chegirma"
        send(chat, "Chegirma (%d%%–%d%%) — tugmani bosing yoki raqam yozing:" %
             (MIN_CHEGIRMA, MAX_CHEGIRMA), chegirma_klav("kn"))
        return True
    if h == "k_chegirma":
        c = narx_toza(text.rstrip("%"))
        if c is None or not MIN_CHEGIRMA <= c <= MAX_CHEGIRMA:
            send(chat, "Chegirma %d%% dan %d%% gacha bo'lishi kerak." % (MIN_CHEGIRMA, MAX_CHEGIRMA),
                 chegirma_klav("kn"))
            return True
        kitob_saqla(db, chat, u, c)
        return True
    if h == "s_vaqt":
        m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*[-–—]\s*(\d{1,2})[:.](\d{2})\s*", text)
        if not m or not (0 <= int(m[1]) < 24 and 0 <= int(m[3]) < 24 and int(m[2]) < 60
                         and int(m[4]) < 60) or (int(m[1]), int(m[2])) >= (int(m[3]), int(m[4])):
            send(chat, "Masalan: <code>10:00-20:00</code>")
            return True
        db["aksiya"]["boshlanish"] = "%02d:%s" % (int(m[1]), m[2])
        db["aksiya"]["tugash"] = "%02d:%s" % (int(m[3]), m[4])
        u["holat"] = None
        send(chat, sozlama_matn(db), sozlama_klav(db))
        return True
    if h == "s_izoh":
        db["aksiya"]["izoh"] = "" if text in ("-", "—") else text[:500]
        u["holat"] = None
        send(chat, sozlama_matn(db), sozlama_klav(db))
        return True
    if h == "x_matn":
        if not text:
            send(chat, "Xabar matnini yozing.")
            return True
        tmp["xabar"] = text[:3500]
        u["holat"] = None
        send(chat, "Kimga yuboramiz?\n\n<i>%s</i>" % e(tmp["xabar"]), xabar_klav(db))
        return True
    if h == "keldi":
        m = mijoz_top(db, text)
        if not m:
            send(chat, "Topilmadi. Shaxsiy kod (<code>K1001</code>) yoki telefon raqamini yozing.")
            return True
        d = oxirgi_aksiya(db).isoformat()
        keldi = m.setdefault("keldi", [])
        if d in keldi:
            send(chat, "ℹ️ %s allaqachon belgilangan (%s)." % (e(m["ism"]), d))
            return True
        keldi.append(d)
        send(chat, "✅ <b>%s</b> (%s) — %s aksiyasiga keldi.\n%s\n\nKeyingi kod yoki raqamni "
                   "yozing, tugatish uchun menyudagi tugmani bosing." %
             (e(m["ism"]), m.get("kod"), d,
              "«Boraman» degan edi." if d in (m.get("rsvp") or []) else "«Boraman» bosmagan edi."))
        return True
    return False


def kitob_saqla(db, chat, u, chegirma):
    tmp = u.get("tmp") or {}
    if not all(k in tmp for k in ("nom", "janr", "narx")):
        u["holat"] = None
        send(chat, "Ma'lumot to'liq emas, qaytadan boshlang: " + B_QOSH, xodim_menyu())
        return
    k = {"id": db["keyingi_id"], "nom": tmp["nom"], "janr": tmp["janr"],
         "narx": tmp["narx"], "chegirma": chegirma}
    db["keyingi_id"] += 1
    db["kitoblar"].append(k)
    u["holat"] = None
    u["tmp"] = {}
    send(chat, "✅ Qo'shildi:\n" + kitob_qator(k) + "\n\nYana qo'shish: " + B_QOSH, xodim_menyu())


def xodim_tugma(db, chat, u, text):
    """Xodim menyusidagi tugmalar. True — qayta ishlandi."""
    if text in (B_PANEL, "/panel"):
        u["holat"] = None
        send(chat, "🛠 <b>Xodim paneli</b>", xodim_menyu())
    elif text == B_TAHLIL:
        send(chat, tahlil_matn(db))
    elif text == B_CSV:
        r = send_file(chat, "mijozlar_%s.csv" % hozir().strftime("%Y-%m-%d"), csv_fayl(db),
                      "Mijozlar ro'yxati (%d). Excel'da oching." % len(mijozlar(db)))
        if not r.get("ok"):
            send(chat, "Faylni yuborib bo'lmadi, birozdan keyin qayta urinib ko'ring.")
    elif text == B_RO_KITOB:
        send(chat, kitoblar_royxat(db), kitoblar_klav(db))
    elif text == B_QOSH:
        u["holat"] = "k_nom"
        u["tmp"] = {}
        send(chat, "Kitob nomini yozing (muallifi bilan). Masalan: <i>O'tkan kunlar — "
                   "Abdulla Qodiriy</i>")
    elif text == B_SOZLA:
        u["holat"] = None
        send(chat, sozlama_matn(db), sozlama_klav(db))
    elif text == B_XABAR:
        u["holat"] = "x_matn"
        send(chat, "Mijozlarga yuboriladigan xabar matnini yozing.")
    elif text == B_KELDI:
        u["holat"] = "keldi"
        send(chat, "Aksiyaga kelgan mijozning shaxsiy kodini (<code>K1001</code>) yoki telefon "
                   "raqamini yozing. Bir nechtasini ketma-ket yozish mumkin.")
    elif text == B_MIJOZ:
        u["holat"] = None
        if royxatdan_otgan(u):
            send(chat, "Mijoz menyusi. Panelga qaytish: " + B_PANEL, mijoz_menyu(db, chat))
        else:
            royxat_boshla(chat, u)
    else:
        return False
    return True


# ---------------------------------------------------------------- xabarlar
def handle(msg, db):
    if msg["chat"].get("type") != "private":
        return
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    frm = msg.get("from", {})
    u = db["users"].setdefault(chat, {"id": chat, "boshlagan": int(time.time())})
    u["username"] = frm.get("username", "")
    u.pop("bloklagan", None)

    if text.startswith("/start"):
        arg = text.split(maxsplit=1)[1] if " " in text else ""
        if arg.startswith("ref_") and not royxatdan_otgan(u) and arg[4:] != chat:
            u["taklif_qilgan"] = arg[4:]
        if royxatdan_otgan(u):
            u["holat"] = None
            send(chat, aksiya_matn(db, u), mijoz_menyu(db, chat))
        elif not u.get("holat"):
            royxat_boshla(chat, u)
        else:
            royxat_qadam(db, chat, u, {}, "")
        return

    if text.startswith("/xodim"):
        kod = text.split(maxsplit=1)[1].strip() if " " in text else ""
        if xodimmi(db, chat):
            send(chat, "🛠 <b>Xodim paneli</b>", xodim_menyu())
        elif XODIM_KODI and kod == XODIM_KODI:
            db["xodimlar"].append(chat)
            send(chat, "✅ Siz xodim sifatida qo'shildingiz.", xodim_menyu())
            for a in ADMINS:
                send(a, "ℹ️ Yangi xodim: %s (@%s, ID %s)" %
                     (e(frm.get("first_name")), e(u["username"]), chat))
        else:
            send(chat, "Kod noto'g'ri.")
        return

    if text.startswith("/men"):
        send(chat, "Telegram ID: <code>%s</code>" % chat)
        return

    if xodimmi(db, chat):
        if text.startswith("/xodimlar") and chat in ADMINS:
            ro = [f"{x} — {e(db['users'].get(x, {}).get('username') or '')}" for x in db["xodimlar"]]
            send(chat, "Xodimlar:\n%s\n\nO'chirish: <code>/ochir ID</code>" % ("\n".join(ro) or "—"))
            return
        if text.startswith("/ochir") and chat in ADMINS:
            x = text.split(maxsplit=1)[1].strip() if " " in text else ""
            if x in db["xodimlar"]:
                db["xodimlar"].remove(x)
                send(chat, "O'chirildi: " + x)
            else:
                send(chat, "Bunday xodim yo'q.")
            return
        if xodim_tugma(db, chat, u, text):
            return
        if u.get("holat") in ("k_nom", "k_narx", "k_chegirma", "s_vaqt", "s_izoh", "x_matn", "keldi"):
            if xodim_holat(db, chat, u, text):
                return

    if not royxatdan_otgan(u):
        if xodimmi(db, chat) and not u.get("holat"):
            send(chat, "🛠 <b>Xodim paneli</b>\nMijoz sifatida ro'yxatdan o'tish: " + B_MIJOZ,
                 xodim_menyu())
        elif not u.get("holat"):
            royxat_boshla(chat, u)
        else:
            royxat_qadam(db, chat, u, msg, text)
        return

    if text in (B_AKSIYA, "/aksiya"):
        send(chat, aksiya_matn(db, u), rsvp_klav(keyingi_aksiya(db)) if db["aksiya"]["faol"] else None)
    elif text in (B_KITOBLAR, "/kitoblar"):
        kitoblar_mijozga(db, chat, u)
    elif text in (B_PROFIL, "/profil"):
        send(chat, profil_matn(u), {"inline_keyboard": [
            [{"text": "✏️ Qiziqishlarni o'zgartirish", "callback_data": "qiz"}],
            [{"text": "🔄 Qaytadan ro'yxatdan o'tish", "callback_data": "qayta"}]]})
    elif text in (B_TAKLIF, "/taklif"):
        havola = "https://t.me/%s?start=ref_%s" % (bot_username(), chat)
        send(chat, "🎁 Do'stlaringizni ham juma aksiyasiga taklif qiling! Shu havolani yuboring:\n\n"
                   "%s\n\nKim orqali kelganini ko'rib boramiz." % havola)
    else:
        send(chat, "Pastdagi tugmalardan foydalaning 👇", mijoz_menyu(db, chat))


def kitoblar_mijozga(db, chat, u):
    if not db["kitoblar"]:
        send(chat, "Chegirmadagi kitoblar ro'yxati tez orada e'lon qilinadi. "
                   "Aksiyadan oldin sizga yuboramiz 📚")
        return
    q = set(u.get("qiziqish") or [])
    kitoblar = sorted(db["kitoblar"], key=lambda k: (k["janr"] not in q, -k["chegirma"]))
    send(chat, "📚 <b>Juma aksiyasida chegirmadagi kitoblar:</b>\n\n" +
         "\n".join(kitob_qator(k) + ("  ⭐" if k["janr"] in q else "") for k in kitoblar) +
         ("\n\n⭐ — sizning qiziqishingizga mos" if any(k["janr"] in q for k in kitoblar) else ""))


def handle_callback(cb, db):
    chat = str(cb["message"]["chat"]["id"])
    mid = cb["message"]["message_id"]
    data = cb.get("data") or ""
    u = db["users"].setdefault(chat, {"id": chat, "boshlagan": int(time.time())})
    javob = ""

    if data.startswith("q:") and u.get("holat") in ("qiziqish", "qiz"):
        k = data[2:]
        q = u.setdefault("qiziqish", [])
        if k == "tayyor":
            if not q:
                javob = "Kamida bittasini tanlang"
            else:
                edit(chat, mid, "📚 Qiziqishlar: " + e(", ".join(JANR[x] for x in q)))
                royxat_tugat(db, chat, u)
        elif k in JANR:
            q.remove(k) if k in q else q.append(k)
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup=janr_klav(q))
    elif data == "qiz" and royxatdan_otgan(u):
        u["holat"] = "qiz"
        send(chat, "Qiziqishlaringizni belgilang va <b>➡️ Tayyor</b> ni bosing.",
             janr_klav(u.get("qiziqish") or []))
    elif data == "qayta" and royxatdan_otgan(u):
        for k in ("royxat", "telefon", "ism", "tugilgan", "qiziqish"):
            u.pop(k, None)
        royxat_boshla(chat, u)
    elif data.startswith("rsvp:") and royxatdan_otgan(u):
        d = data[5:]
        r = u.setdefault("rsvp", [])
        if d not in r:
            r.append(d)
        javob = "Kutib qolamiz! 📚"
        call("editMessageReplyMarkup", chat_id=chat, message_id=mid, reply_markup={"inline_keyboard": [
            [{"text": "✅ Boraman — belgilandi", "callback_data": "rsvp:" + d}],
            [{"text": "📚 Barcha chegirmadagi kitoblar", "callback_data": "kitoblar"}]]})
    elif data == "kitoblar" and royxatdan_otgan(u):
        kitoblar_mijozga(db, chat, u)
    elif xodimmi(db, chat):
        javob = xodim_callback(db, chat, mid, u, data)

    call("answerCallbackQuery", callback_query_id=cb["id"], text=javob or None)


def xodim_callback(db, chat, mid, u, data):
    a = db["aksiya"]
    tmp = u.setdefault("tmp", {})
    if data.startswith("kj:") and u.get("holat") == "k_janr" and data[3:] in JANR:
        tmp["janr"] = data[3:]
        u["holat"] = "k_narx"
        edit(chat, mid, "Turi: " + JANR[tmp["janr"]])
        send(chat, "Kitobning <b>chegirmasiz</b> narxi (so'm). Masalan: <code>85000</code>")
    elif data.startswith("kn:") and u.get("holat") == "k_chegirma":
        edit(chat, mid, "Chegirma: %s%%" % data[3:])
        kitob_saqla(db, chat, u, int(data[3:]))
    elif data.startswith("kb:"):
        k = next((k for k in db["kitoblar"] if str(k["id"]) == data[3:]), None)
        if not k:
            return "Kitob topilmadi"
        send(chat, kitob_karta(k), kitob_karta_klav(k))
    elif data.startswith("kc:"):
        _, kid, c = data.split(":")
        k = next((k for k in db["kitoblar"] if str(k["id"]) == kid), None)
        if not k:
            return "Kitob topilmadi"
        k["chegirma"] = max(MIN_CHEGIRMA, min(MAX_CHEGIRMA, int(c)))
        edit(chat, mid, kitob_karta(k), kitob_karta_klav(k))
        return "Chegirma: %d%%" % k["chegirma"]
    elif data.startswith("kdel:"):
        db["kitoblar"] = [k for k in db["kitoblar"] if str(k["id"]) != data[5:]]
        edit(chat, mid, "🗑 O'chirildi.")
    elif data == "ktoza":
        edit(chat, mid, "Hamma kitoblarni o'chirasizmi?", {"inline_keyboard": [
            [{"text": "Ha, o'chirish", "callback_data": "ktoza!"},
             {"text": "Yo'q", "callback_data": "bekor"}]]})
    elif data == "ktoza!":
        n = len(db["kitoblar"])
        db["kitoblar"] = []
        edit(chat, mid, "🗑 %d ta kitob o'chirildi. Yangi haftaning kitoblarini qo'shing: %s" % (n, B_QOSH))
    elif data == "bekor":
        edit(chat, mid, "Bekor qilindi.")
    elif data.startswith("es:"):
        a["eslatma_soat"] = int(data[3:])
        edit(chat, mid, sozlama_matn(db), sozlama_klav(db))
    elif data == "sfaol":
        a["faol"] = not a["faol"]
        edit(chat, mid, sozlama_matn(db), sozlama_klav(db))
    elif data == "svaqt":
        u["holat"] = "s_vaqt"
        send(chat, "Aksiya vaqtini yozing: <code>10:00-20:00</code>")
    elif data == "sizoh":
        u["holat"] = "s_izoh"
        send(chat, "Eslatmaga qo'shiladigan matn (manzil, sovg'a, shartlar...). "
                   "O'chirish uchun <code>-</code> yozing.")
    elif data == "skor":
        send(chat, eslatma_matn(db, u if royxatdan_otgan(u) else {}), rsvp_klav(keyingi_aksiya(db)))
    elif data.startswith("xb:"):
        kim = data[3:]
        matn = tmp.pop("xabar", None)
        if kim == "bekor" or not matn:
            edit(chat, mid, "Bekor qilindi.")
            return ""
        qabul = [x for x in mijozlar(db) if kim == "hamma" or kim in (x.get("qiziqish") or [])]
        edit(chat, mid, "Yuborilmoqda...")
        n = tarqat(db, qabul, lambda x: (matn, None))
        edit(chat, mid, "📣 Yuborildi: %d / %d\n\n<i>%s</i>" % (n, len(qabul), e(matn)))
    return ""


# ---------------------------------------------------------------- jadval (eslatmalar)
def eslatma_matn(db, u):
    return aksiya_matn(db, u, "⏰ <b>%s aksiyasiga %s qoldi!</b>" % (
        e(DOKON), muddat_matn(db["aksiya"]["eslatma_soat"])))


def tarqat(db, qabul, xabar):
    """Har bir mijozga xabar yuboradi. Botni bloklaganlarni belgilaydi."""
    n = 0
    for u in qabul:
        if u.get("bloklagan"):
            continue
        matn, klav = xabar(u)
        r = send(u["id"], matn, klav)
        if r.get("ok"):
            n += 1
        elif r.get("error_code") == 403:
            u["bloklagan"] = True
        elif r.get("error_code") == 429:
            time.sleep((r.get("parameters") or {}).get("retry_after", 1))
            if send(u["id"], matn, klav).get("ok"):
                n += 1
        time.sleep(0.05)          # Telegram cheklovi: ~30 xabar/soniya
    return n


def jadval(db, now=None):
    """Vaqti kelgan eslatmalarni yuboradi. Har 5 daqiqada chaqiriladi."""
    now = now or hozir()
    a = db["aksiya"]
    yub = db["yuborilgan"]
    if a["faol"]:
        d = keyingi_aksiya(db, now)
        bosh = aksiya_boshi(db, d)
        k = "eslatma:" + d.isoformat()
        if bosh - timedelta(hours=a["eslatma_soat"]) <= now < bosh and k not in yub:
            yub[k] = tarqat(db, mijozlar(db), lambda u: (eslatma_matn(db, u), rsvp_klav(d)))
            print("eslatma yuborildi:", yub[k])
        k = "boshlandi:" + d.isoformat()
        if bosh <= now < aksiya_oxiri(db, d) and k not in yub:
            yub[k] = tarqat(db, mijozlar(db), lambda u: (
                "🔥 <b>Juma aksiyasi boshlandi!</b> Bugun %s gacha kitoblarga %d%%–%d%% chegirma.\n"
                "🎫 Kodingiz: <b>%s</b>" % (a["tugash"], MIN_CHEGIRMA, MAX_CHEGIRMA, u.get("kod")),
                {"inline_keyboard": [[{"text": "📚 Chegirmadagi kitoblar", "callback_data": "kitoblar"}]]}))
            print("boshlandi xabari:", yub[k])

    # tug'ilgan kun tabrigi — soat 9:00 dan keyin, yiliga bir marta
    if now.hour >= 9:
        for u in mijozlar(db):
            t = date.fromisoformat(u["tugilgan"])
            k = "tk:%s:%d" % (u["id"], now.year)
            if (t.month, t.day) == (now.month, now.day) and k not in yub:
                yub[k] = 1
                tarqat(db, [u], lambda u: (
                    "🎂 <b>Tug'ilgan kuningiz bilan, %s!</b>\n\n%s jamoasi sizga ilm va baxt "
                    "tilaydi. Juma aksiyasida sizni kutamiz! 📚" % (e(u["ism"].split()[0]), e(DOKON)),
                    None))


# ---------------------------------------------------------------- ishga tushirish
def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        try:
            if upd.get("message"):
                handle(upd["message"], db)
            elif upd.get("callback_query") and upd["callback_query"].get("message"):
                handle_callback(upd["callback_query"], db)
        except Exception as ex:                          # bitta xato botni to'xtatmasin
            print("xato:", repr(ex), file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Boshlash"},
        {"command": "aksiya", "description": "Juma aksiyasi"},
        {"command": "kitoblar", "description": "Chegirmadagi kitoblar"},
        {"command": "profil", "description": "Profilim"},
        {"command": "taklif", "description": "Do'stni taklif qilish"},
    ])
    r2 = call("setMyDescription", description=(
        "%s — har juma kitoblarga %d%% dan %d%% gacha chegirma! Ro'yxatdan o'ting — aksiyadan "
        "oldin qiziqishingizga mos kitoblarni yuboramiz." % (DOKON, MIN_CHEGIRMA, MAX_CHEGIRMA)))
    r3 = call("setMyShortDescription", short_description=(
        "Har juma kitoblarga %d–%d%% chegirma" % (MIN_CHEGIRMA, MAX_CHEGIRMA)))
    print("bot: @%s" % bot_username())
    print("buyruqlar:", r1.get("ok"), "| tavsif:", r2.get("ok"), r3.get("ok"))
    return all(x.get("ok") for x in (r1, r2, r3))


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    allowed = ["message", "callback_query"]
    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=allowed)
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        jadval(db)
        save(db)
        print("qayta ishlandi: %d ta, mijozlar: %d" % (len(r.get("result", [])), len(mijozlar(db))))
        return

    setup()
    offset = 0
    print("Bot ishga tushdi. Mijozlar:", len(mijozlar(db)))
    while True:
        r = call("getUpdates", offset=offset, timeout=50, allowed_updates=allowed)
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
        jadval(db)
        save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""
Kitoblar olami — kitob do'konining Telegram boti.

Vazifasi:
  1. Ro'yxatdan o'tish: ism, familiya, yosh va qiziqadigan janrlar.
  2. Tavsiya: yoshi va qiziqishiga mos kitoblarni ko'rsatadi.
  3. Katalog, savatcha va onlayn buyurtma: telefon + manzil, keyin
     Telegram to'lovi (Click/Payme, PAYMENT_TOKEN bo'lsa) yoki
     yetkazib berganda naqd to'lash.
  4. Juma aksiyasi: har juma bo'ladigan aksiyani bot 1 hafta oldin
     (o'tgan juma kuni) hammaga e'lon qiladi, aksiya kuni yana eslatadi.
     Keyingi juma uchun aksiya kiritilmagan bo'lsa, adminlarga eslatadi.

Kitoblar ro'yxati — kitoblar.json (id, nomi, muallif, janr, yosh, narx,
tavsif, ixtiyoriy rasm havolasi).

Rejimlar:
    python3 bot.py              # doimiy (server bo'lsa): long polling
    python3 bot.py --once       # GitHub Actions: kelgan xabarlarni qayta
                                #   ishlaydi, aksiyani tekshiradi, chiqadi
    python3 bot.py --setup      # buyruqlar va tavsif

Muhit o'zgaruvchilari:
    BOT_TOKEN        BotFather bergan token
    PAYMENT_TOKEN    BotFather → Payments'dan olingan to'lov tokeni (ixtiyoriy)
    ADMIN_IDS        adminlarning Telegram ID lari, vergul bilan
    STATE_FILE       holat fayli (ixtiyoriy, standart: state.json)
    BOOKS_FILE       kitoblar ro'yxati (ixtiyoriy, standart: kitoblar.json)
    ELON_SOATI       aksiya e'lon qilinadigan soat, Toshkent vaqti (standart 10)
"""

import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from html import escape as _escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
PAY_TOKEN = os.environ.get("PAYMENT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(HERE, "state.json")
BOOKS_FILE = os.environ.get("BOOKS_FILE") or os.path.join(HERE, "kitoblar.json")
ELON_SOATI = int(os.environ.get("ELON_SOATI") or 10)
API = "https://api.telegram.org/bot%s/" % TOKEN
TZ = timezone(timedelta(hours=5))          # Toshkent
JUMA = 4                                   # date.weekday(): dushanba=0 … juma=4

JANRLAR = [
    ("badiiy", "📖 Badiiy adabiyot"),
    ("sarguzasht", "🧭 Sarguzasht"),
    ("fantastika", "🚀 Fantastika"),
    ("detektiv", "🕵️ Detektiv"),
    ("tarix", "🏛 Tarix"),
    ("ilmiy", "🔬 Ilmiy-ommabop"),
    ("rivojlanish", "🌱 O'zini rivojlantirish"),
    ("bolalar", "🧸 Bolalar uchun"),
    ("diniy", "🕌 Diniy-ma'rifiy"),
]
JANR_NOMI = dict(JANRLAR)

BTN_TAVSIYA = "📚 Men uchun kitoblar"
BTN_KATALOG = "🔎 Katalog"
BTN_SAVAT = "🛒 Savatcha"
BTN_AKSIYA = "🎉 Juma aksiyasi"
BTN_PROFIL = "👤 Profil"
BTN_BEKOR = "❌ Bekor qilish"

SAHIFA = 5                                 # bir safar nechta kitob ko'rsatiladi
OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
         "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]

TAVSIF = ("Kitoblar olami — kitob do'koni boti. Yoshingiz va qiziqishingizga "
          "mos kitoblarni tavsiya qiladi, onlayn buyurtma qabul qiladi va har "
          "juma bo'ladigan aksiyani bir hafta oldin e'lon qiladi.")


# ---------------------------------------------------------------- Telegram API
def call(method, **params):
    data = urlencode({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
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
                reply_markup=markup, disable_web_page_preview=True)


def menu():
    return {
        "keyboard": [
            [{"text": BTN_TAVSIYA}, {"text": BTN_KATALOG}],
            [{"text": BTN_SAVAT}, {"text": BTN_AKSIYA}],
            [{"text": BTN_PROFIL}],
        ],
        "resize_keyboard": True,
    }


def inline(rows):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}


NO_KB = {"remove_keyboard": True}


def escape(s):
    return _escape(s, quote=False)


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    db.setdefault("orders", [])
    db.setdefault("aksiyalar", {})         # "2026-10-02": {foiz, matn, elon, bugun}
    db.setdefault("eslatildi", [])         # admin eslatmasi yuborilgan jumalar
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def load_books():
    with open(BOOKS_FILE, encoding="utf-8") as f:
        return {b["id"]: b for b in json.load(f)}


BOOKS = {}


# ---------------------------------------------------------------- yordamchilar
def bugun():
    return datetime.now(TZ).date()


def sana(d):
    return "%d-%s" % (d.day, OYLAR[d.month - 1])


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def bugungi_aksiya(db):
    """Bugun aksiya kuni bo'lsa — chegirma foizi, aks holda 0."""
    a = db["aksiyalar"].get(bugun().isoformat())
    return int(a.get("foiz") or 0) if a else 0


def narx(book, db):
    foiz = bugungi_aksiya(db)
    return book["narx"] * (100 - foiz) // 100


def mos_kitoblar(u):
    """Yoshga mos kitoblar; qiziqishga ko'proq mos kelganlari oldinda."""
    yosh = u.get("yosh") or 0
    qiz = set(u.get("qiziqish") or [])
    mos = [b for b in BOOKS.values() if b["yosh"][0] <= yosh <= b["yosh"][1]]
    mos.sort(key=lambda b: -len(qiz & set(b["janr"])))
    return mos


def kitob_matni(b, db):
    janrlar = ", ".join(JANR_NOMI.get(j, j) for j in b["janr"])
    yangi = narx(b, db)
    if yangi < b["narx"]:
        pul = "<s>%s</s> → <b>%s</b> 🎉" % (som(b["narx"]), som(yangi))
    else:
        pul = "<b>%s</b>" % som(b["narx"])
    return ("<b>%s</b>\n✍️ %s\n🏷 %s · 👥 %d+ yosh\n\n%s\n\n💰 %s" % (
        escape(b["nomi"]), escape(b["muallif"]), janrlar, b["yosh"][0],
        escape(b.get("tavsif", "")), pul))


def kitob_yubor(chat, b, db):
    kb = inline([[("🛒 Savatchaga qo'shish", "add:" + b["id"])]])
    if b.get("rasm"):
        r = call("sendPhoto", chat_id=chat, photo=b["rasm"], caption=kitob_matni(b, db),
                 parse_mode="HTML", reply_markup=kb)
        if r.get("ok"):
            return
    send(chat, kitob_matni(b, db), kb)


def royxat_yubor(chat, books, db, offset, keyingi):
    """books[offset:offset+SAHIFA] ni yuboradi; qolsa — "Yana" tugmasi."""
    qism = books[offset:offset + SAHIFA]
    for b in qism:
        kitob_yubor(chat, b, db)
    if offset + SAHIFA < len(books):
        send(chat, "Yana %d ta kitob bor." % (len(books) - offset - SAHIFA),
             inline([[("⬇️ Yana ko'rsatish", keyingi % (offset + SAHIFA))]]))


def is_registered(u):
    return bool(u and u.get("royxatdan"))


def broadcast(db, body, markup=None):
    sent = 0
    for uid, u in db["users"].items():
        if is_registered(u) and send(uid, body, markup).get("ok"):
            sent += 1
        time.sleep(0.05)                   # Telegram cheklovi: ~30 xabar/soniya
    return sent


def adminlarga(text, markup=None):
    for a in ADMINS:
        send(a, text, markup)


# ---------------------------------------------------------------- ro'yxatdan o'tish
def janr_klaviatura(tanlangan):
    rows, row = [], []
    for key, nom in JANRLAR:
        row.append((("✅ " if key in tanlangan else "") + nom, "janr:" + key))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([("➡️ Tayyor", "janr_ok")])
    return inline(rows)


def royxat_boshla(chat, u):
    u["qadam"] = "ism"
    u["qiziqish"] = []
    send(chat, "📚 <b>Kitoblar olami</b>ga xush kelibsiz!\n\n"
               "Sizga mos kitoblarni tanlab berishim uchun qisqa ro'yxatdan o'tamiz.\n\n"
               "1/4. <b>Ismingiz</b>ni yozing:", NO_KB)


def royxat_qadam(chat, u, text):
    qadam = u.get("qadam")
    if qadam in ("ism", "familiya"):
        if not (2 <= len(text) <= 40) or any(c.isdigit() for c in text) or text.startswith("/"):
            send(chat, "Iltimos, to'g'ri yozing (2–40 harf, raqamsiz).")
            return
        if qadam == "ism":
            u["ism"] = text
            u["qadam"] = "familiya"
            send(chat, "2/4. <b>Familiyangiz</b>ni yozing:")
        else:
            u["familiya"] = text
            u["qadam"] = "yosh"
            send(chat, "3/4. <b>Yoshingiz</b> nechada? Faqat raqam, masalan: 17")
        return
    if qadam == "yosh":
        if not text.isdigit() or not (5 <= int(text) <= 100):
            send(chat, "Yoshni raqam bilan yozing (5 dan 100 gacha), masalan: 17")
            return
        u["yosh"] = int(text)
        u["qadam"] = "qiziqish"
        send(chat, "4/4. Qanday kitoblarga <b>qiziqasiz</b>? Bir nechtasini tanlashingiz "
                   "mumkin, keyin «Tayyor»ni bosing.", janr_klaviatura(u["qiziqish"]))
        return
    if qadam == "qiziqish":
        send(chat, "Yuqoridagi tugmalardan janr tanlab, «➡️ Tayyor»ni bosing.")


def royxat_tugat(chat, u, db):
    u["qadam"] = None
    u["royxatdan"] = True
    u.setdefault("since", int(time.time()))
    janrlar = ", ".join(JANR_NOMI[j] for j in u["qiziqish"])
    send(chat, "✅ Ro'yxatdan o'tdingiz, <b>%s</b>!\n\n👤 %s %s, %d yosh\n❤️ %s\n\n"
               "Har juma bo'ladigan aksiya haqida bir hafta oldin xabar beraman. "
               "Mana sizga mos kitoblar 👇" % (
                   escape(u["ism"]), escape(u["ism"]), escape(u["familiya"]), u["yosh"], janrlar),
         menu())
    royxat_yubor(chat, mos_kitoblar(u), db, 0, "tavsiya:%d")


# ---------------------------------------------------------------- savatcha va buyurtma
def savat_matni(u, db):
    savat = {k: v for k, v in (u.get("savat") or {}).items() if k in BOOKS}
    if not savat:
        return None, 0
    lines, jami = [], 0
    for bid, soni in savat.items():
        b = BOOKS[bid]
        summa = narx(b, db) * soni
        jami += summa
        lines.append("• %s — %d × %s = %s" % (escape(b["nomi"]), soni, som(narx(b, db)), som(summa)))
    foiz = bugungi_aksiya(db)
    izoh = "\n🎉 Bugun juma aksiyasi: −%d%% chegirma hisoblandi." % foiz if foiz else ""
    return "🛒 <b>Savatcha</b>\n\n%s\n\n<b>Jami: %s</b>%s" % ("\n".join(lines), som(jami), izoh), jami


def savat_korsat(chat, u, db):
    matn, _ = savat_matni(u, db)
    if not matn:
        send(chat, "Savatcha bo'sh. «%s» yoki «%s» bo'limidan kitob tanlang." % (BTN_TAVSIYA, BTN_KATALOG))
        return
    rows = [[("➖ " + BOOKS[bid]["nomi"][:28], "del:" + bid)] for bid in u["savat"] if bid in BOOKS]
    rows.append([("🗑 Tozalash", "savat_tozala"), ("✅ Rasmiylashtirish", "savat_ok")])
    send(chat, matn, inline(rows))


def buyurtma_boshla(chat, u, db):
    if not savat_matni(u, db)[0]:
        send(chat, "Savatcha bo'sh.", menu())
        return
    u["qadam"] = "telefon"
    send(chat, "📞 Telefon raqamingizni yuboring — pastdagi tugmani bosing yoki "
               "raqamni yozing (masalan, +998 90 123 45 67):", {
                   "keyboard": [[{"text": "📱 Raqamni yuborish", "request_contact": True}],
                                [{"text": BTN_BEKOR}]],
                   "resize_keyboard": True, "one_time_keyboard": True})


def buyurtma_qadam(chat, u, db, msg, text):
    if text == BTN_BEKOR:
        u["qadam"] = None
        send(chat, "Buyurtma bekor qilindi. Savatcha saqlanib qoldi.", menu())
        return
    if u["qadam"] == "telefon":
        tel = (msg.get("contact") or {}).get("phone_number") or text
        raqam = "".join(c for c in tel if c.isdigit())
        if not (9 <= len(raqam) <= 15):
            send(chat, "Telefon raqamini to'g'ri yuboring, masalan: +998 90 123 45 67")
            return
        u["telefon"] = "+" + raqam if len(raqam) > 9 else "+998" + raqam
        u["qadam"] = "manzil"
        send(chat, "📍 Yetkazib berish manzilini yozing (shahar, ko'cha, uy):",
             {"keyboard": [[{"text": BTN_BEKOR}]], "resize_keyboard": True})
        return
    if u["qadam"] == "manzil":
        if len(text) < 5:
            send(chat, "Manzilni to'liqroq yozing (shahar, ko'cha, uy).")
            return
        u["manzil"] = text
        u["qadam"] = None
        matn, jami = savat_matni(u, db)
        order = {
            "id": len(db["orders"]) + 1,
            "chat": chat,
            "ism": "%s %s" % (u.get("ism", ""), u.get("familiya", "")),
            "telefon": u["telefon"],
            "manzil": u["manzil"],
            "kitoblar": dict(u["savat"]),
            "jami": jami,
            "holat": "kutilmoqda",
            "vaqt": int(time.time()),
        }
        db["orders"].append(order)
        tugmalar = [[("💵 Yetkazib berganda to'layman", "naqd:%d" % order["id"])]]
        if PAY_TOKEN:
            tugmalar.insert(0, [("💳 Onlayn to'lash (Click/Payme)", "pay:%d" % order["id"])])
        send(chat, "Buyurtma №%d\n\n%s\n\n📞 %s\n📍 %s" % (
            order["id"], matn, escape(u["telefon"]), escape(u["manzil"])), menu())
        send(chat, "To'lov usulini tanlang:", inline(tugmalar))


def buyurtma_tasdiq(chat, u, order, usul):
    order["holat"] = "tasdiqlandi" if usul == "naqd" else "to'landi"
    order["tolov"] = usul
    u["savat"] = {}
    send(chat, "✅ Buyurtma №%d qabul qilindi! Tez orada operatorimiz %s raqamiga "
               "qo'ng'iroq qiladi. Rahmat! 📚" % (order["id"], escape(order["telefon"])), menu())
    kitoblar = "\n".join("• %s × %d" % (escape(BOOKS[k]["nomi"]) if k in BOOKS else k, v)
                         for k, v in order["kitoblar"].items())
    adminlarga("🆕 <b>Buyurtma №%d</b> (%s)\n\n%s\n\n💰 %s\n👤 %s\n📞 %s\n📍 %s\n\n"
               "Yetkazilgach: <code>/yetkazildi %d</code>" % (
                   order["id"], "naqd" if usul == "naqd" else "onlayn to'landi ✅", kitoblar,
                   som(order["jami"]), escape(order["ism"]), escape(order["telefon"]),
                   escape(order["manzil"]), order["id"]))


def find_order(db, oid):
    try:
        oid = int(oid)
    except (TypeError, ValueError):
        return None
    return next((o for o in db["orders"] if o["id"] == oid), None)


# ---------------------------------------------------------------- juma aksiyasi
def keyingi_juma(d, ichida=False):
    """d dan keyingi juma (ichida=True bo'lsa, d ning o'zi juma bo'lsa ham qaytaradi)."""
    kun = (JUMA - d.weekday()) % 7
    if kun == 0 and not ichida:
        kun = 7
    return d + timedelta(days=kun)


def aksiya_matni(kun, a, tur):
    d = date.fromisoformat(kun)
    foiz = ("\n\n🔥 Barcha kitoblarga <b>−%d%%</b> chegirma!" % a["foiz"]) if a.get("foiz") else ""
    if tur == "elon":
        bosh = "📣 <b>Kelasi juma — %s — aksiya!</b>" % sana(d)
        oxir = "\n\nBir hafta bor — kerakli kitoblarni hozirdan savatchaga yig'ib qo'ying 😉"
    else:
        bosh = "🎉 <b>Bugun juma aksiyasi!</b>"
        oxir = "\n\nChegirma faqat bugun amal qiladi. «%s» tugmasini bosing 👇" % BTN_TAVSIYA
    return "%s\n\n%s%s%s" % (bosh, escape(a.get("matn", "")), foiz, oxir)


def aksiya_tekshir(db):
    """Har ishga tushganda: vaqti kelgan e'lon va eslatmalarni yuboradi."""
    now = datetime.now(TZ)
    today = now.date()
    if now.hour < ELON_SOATI:
        return
    for kun, a in sorted(db["aksiyalar"].items()):
        d = date.fromisoformat(kun)
        if d < today:
            continue
        if not a.get("elon") and today >= d - timedelta(days=7):
            a["elon"] = True
            n = broadcast(db, aksiya_matni(kun, a, "elon"))
            adminlarga("📣 %s aksiyasi e'lon qilindi: %d kishiga." % (sana(d), n))
        if not a.get("bugun") and today == d:
            a["bugun"] = True
            broadcast(db, aksiya_matni(kun, a, "bugun"), menu())
    # E'lon vaqti yaqinlashgan, lekin aksiya kiritilmagan juma — adminlarga eslatma
    juma = keyingi_juma(today + timedelta(days=7), ichida=True)
    if (juma - today).days <= 9 and juma.isoformat() not in db["aksiyalar"] \
            and juma.isoformat() not in db["eslatildi"]:
        db["eslatildi"].append(juma.isoformat())
        adminlarga("⚠️ %s (juma) uchun aksiya hali kiritilmagan. E'lon %s kuni chiqishi kerak.\n\n"
                   "Kiritish: <code>/aksiya %s 20 Aksiya matni</code>" % (
                       sana(juma), sana(juma - timedelta(days=7)), juma.isoformat()))


def aksiya_korsat(chat, db):
    today = bugun()
    kelasi = [(k, a) for k, a in sorted(db["aksiyalar"].items())
              if date.fromisoformat(k) >= today and a.get("elon")]
    if not kelasi:
        send(chat, "🎉 Har juma — <b>Kitoblar olami</b>da aksiya!\n\n"
                   "Keyingi aksiya haqida bir hafta oldin shu yerda xabar beraman.")
        return
    kun, a = kelasi[0]
    send(chat, aksiya_matni(kun, a, "bugun" if kun == today.isoformat() else "elon"))


def aksiya_qosh(chat, db, args):
    """/aksiya 2026-10-02 20 Matn  (sana DD.MM.YYYY ham bo'ladi; foiz ixtiyoriy)."""
    qism = args.split(maxsplit=1)
    if not qism:
        send(chat, "Foydalanish:\n<code>/aksiya 2026-10-02 20 Barcha kitoblarga chegirma!</code>\n"
                   "(sana — juma kuni; 20 — chegirma foizi, ixtiyoriy)")
        return
    try:
        if "." in qism[0]:
            d = datetime.strptime(qism[0], "%d.%m.%Y").date()
        else:
            d = date.fromisoformat(qism[0])
    except ValueError:
        send(chat, "Sanani <code>2026-10-02</code> yoki <code>02.10.2026</code> ko'rinishida yozing.")
        return
    if d.weekday() != JUMA:
        send(chat, "%s — juma emas. Eng yaqin juma: <code>%s</code>" % (
            sana(d), keyingi_juma(d, ichida=True).isoformat()))
        return
    if d < bugun():
        send(chat, "Bu sana o'tib ketgan.")
        return
    rest = qism[1].strip() if len(qism) > 1 else ""
    foiz = 0
    bosh = rest.split(maxsplit=1)
    if bosh and bosh[0].rstrip("%").isdigit():
        foiz = int(bosh[0].rstrip("%"))
        rest = bosh[1] if len(bosh) > 1 else ""
    if not (0 <= foiz <= 90):
        send(chat, "Chegirma 0–90% oralig'ida bo'lsin.")
        return
    eski = db["aksiyalar"].get(d.isoformat(), {})
    db["aksiyalar"][d.isoformat()] = {"foiz": foiz, "matn": rest or "Kitoblar olamida katta aksiya!",
                                      "elon": eski.get("elon", False), "bugun": eski.get("bugun", False)}
    elon_kuni = d - timedelta(days=7)
    send(chat, "✅ Aksiya saqlandi: %s, −%d%%.\nE'lon: %s soat %d:00 dan keyin (yoki kechikkan "
               "bo'lsa — darhol).\n\nKo'rinishi:\n\n%s" % (
                   sana(d), foiz, sana(max(elon_kuni, bugun())), ELON_SOATI,
                   aksiya_matni(d.isoformat(), db["aksiyalar"][d.isoformat()], "elon")))
    aksiya_tekshir(db)


# ---------------------------------------------------------------- admin
ADMIN_YORDAM = (
    "<b>Admin buyruqlari</b>\n"
    "/aksiya 2026-10-02 20 Matn — juma aksiyasini kiritish\n"
    "/aksiyalar — kiritilgan aksiyalar\n"
    "/aksiya_ochir 2026-10-02 — aksiyani o'chirish\n"
    "/buyurtmalar — oxirgi buyurtmalar\n"
    "/yetkazildi 5 — buyurtma yetkazildi (mijozga xabar boradi)\n"
    "/xabar Matn — hamma foydalanuvchiga xabar\n"
    "/statistika — foydalanuvchilar soni"
)


def admin_buyruq(chat, text, db):
    cmd, _, args = text.partition(" ")
    cmd = cmd.split("@")[0]
    args = args.strip()
    if cmd == "/admin":
        send(chat, ADMIN_YORDAM)
    elif cmd == "/aksiya" and args:
        aksiya_qosh(chat, db, args)
    elif cmd == "/aksiyalar":
        rows = ["%s — −%d%% %s%s" % (k, a.get("foiz", 0), escape(a.get("matn", "")[:40]),
                                     " (e'lon qilingan)" if a.get("elon") else "")
                for k, a in sorted(db["aksiyalar"].items()) if k >= bugun().isoformat()]
        send(chat, "Kelgusi aksiyalar:\n" + ("\n".join(rows) or "—"))
    elif cmd == "/aksiya_ochir":
        send(chat, "O'chirildi." if db["aksiyalar"].pop(args, None) else "Bunday sana yo'q.")
    elif cmd == "/buyurtmalar":
        rows = ["№%d %s — %s, %s, %s" % (o["id"], time.strftime("%d.%m", time.gmtime(o["vaqt"] + 5 * 3600)),
                                         escape(o["ism"]), som(o["jami"]), o["holat"])
                for o in db["orders"][-15:]]
        send(chat, "Oxirgi buyurtmalar:\n" + ("\n".join(rows) or "—"))
    elif cmd == "/yetkazildi":
        o = find_order(db, args)
        if not o:
            send(chat, "Buyurtma topilmadi. Masalan: <code>/yetkazildi 5</code>")
            return True
        o["holat"] = "yetkazildi"
        send(o["chat"], "📦 Buyurtma №%d yetkazildi. Maroqli mutolaa! 📚" % o["id"])
        send(chat, "№%d — yetkazildi." % o["id"])
    elif cmd == "/xabar" and args:
        send(chat, "Yuborildi: %d ta" % broadcast(db, escape(args)))
    elif cmd == "/statistika":
        users = [u for u in db["users"].values() if is_registered(u)]
        janr = {}
        for u in users:
            for j in u.get("qiziqish", []):
                janr[j] = janr.get(j, 0) + 1
        top = "\n".join("%s — %d" % (JANR_NOMI.get(j, j), n)
                        for j, n in sorted(janr.items(), key=lambda x: -x[1]))
        send(chat, "👥 Ro'yxatdan o'tganlar: %d\n🧾 Buyurtmalar: %d\n\nQiziqishlar:\n%s" % (
            len(users), len(db["orders"]), top or "—"))
    else:
        return False
    return True


# ---------------------------------------------------------------- xabarlar
def handle_message(msg, db):
    if msg["chat"].get("type") != "private":
        return
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    u = db["users"].setdefault(chat, {"id": chat})
    u["username"] = msg.get("from", {}).get("username", "")

    if msg.get("successful_payment"):
        pay = msg["successful_payment"]
        o = find_order(db, pay.get("invoice_payload", "").partition(":")[2])
        if o:
            o["tolov_id"] = pay.get("provider_payment_charge_id")
            buyurtma_tasdiq(chat, u, o, "onlayn")
        return

    if text.startswith("/start") or (text == "/qayta"):
        if is_registered(u) and text != "/qayta":
            send(chat, "Qaytganingizdan xursandmiz, <b>%s</b>! 📚" % escape(u.get("ism", "")), menu())
        else:
            royxat_boshla(chat, u)
        return

    if chat in ADMINS and text.startswith("/") and admin_buyruq(chat, text, db):
        return

    if u.get("qadam") in ("ism", "familiya", "yosh", "qiziqish"):
        royxat_qadam(chat, u, text)
        return
    if not is_registered(u):
        royxat_boshla(chat, u)
        return
    if u.get("qadam") in ("telefon", "manzil"):
        buyurtma_qadam(chat, u, db, msg, text)
        return

    if text in (BTN_TAVSIYA, "/tavsiya"):
        books = mos_kitoblar(u)
        if not books:
            send(chat, "Hozircha yoshingizga mos kitob topilmadi — katalogni ko'ring.", menu())
            return
        send(chat, "📚 Sizga mos kitoblar:")
        royxat_yubor(chat, books, db, 0, "tavsiya:%d")
    elif text in (BTN_KATALOG, "/katalog"):
        rows = [[(nom, "kat:%s:0" % key)] for key, nom in JANRLAR]
        send(chat, "Qaysi janr?", inline(rows))
    elif text in (BTN_SAVAT, "/savat"):
        savat_korsat(chat, u, db)
    elif text in (BTN_AKSIYA, "/aksiya"):
        aksiya_korsat(chat, db)
    elif text in (BTN_PROFIL, "/profil"):
        janrlar = ", ".join(JANR_NOMI.get(j, j) for j in u.get("qiziqish", [])) or "—"
        buyurtmalar = sum(1 for o in db["orders"] if o["chat"] == chat)
        send(chat, "👤 <b>%s %s</b>\n🎂 %d yosh\n❤️ %s\n🧾 Buyurtmalar: %d" % (
            escape(u.get("ism", "")), escape(u.get("familiya", "")), u.get("yosh", 0),
            janrlar, buyurtmalar),
             inline([[("✏️ Ma'lumotlarni o'zgartirish", "qayta")]]))
    else:
        topilgan = [b for b in BOOKS.values()
                    if len(text) >= 3 and (text.lower() in b["nomi"].lower()
                                           or text.lower() in b["muallif"].lower())]
        if topilgan:
            for b in topilgan[:SAHIFA]:
                kitob_yubor(chat, b, db)
        else:
            send(chat, "Kitob nomi yoki muallifini yozing — qidirib beraman. "
                       "Yoki pastdagi tugmalardan foydalaning 👇", menu())


def handle_callback(cq, db):
    chat = str(cq["message"]["chat"]["id"])
    mid = cq["message"]["message_id"]
    data = cq.get("data", "")
    u = db["users"].setdefault(chat, {"id": chat})
    javob = None

    if data.startswith("janr:") and u.get("qadam") == "qiziqish":
        key = data[5:]
        if key in JANR_NOMI:
            tanlangan = u.setdefault("qiziqish", [])
            if key in tanlangan:
                tanlangan.remove(key)
            else:
                tanlangan.append(key)
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid,
                 reply_markup=janr_klaviatura(tanlangan))
    elif data == "janr_ok" and u.get("qadam") == "qiziqish":
        if not u.get("qiziqish"):
            javob = "Kamida bitta janr tanlang"
        else:
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid,
                 reply_markup={"inline_keyboard": []})
            royxat_tugat(chat, u, db)
    elif data == "qayta":
        royxat_boshla(chat, u)
    elif not is_registered(u):
        javob = "Avval ro'yxatdan o'ting: /start"
    elif data.startswith("add:"):
        bid = data[4:]
        if bid in BOOKS:
            savat = u.setdefault("savat", {})
            savat[bid] = savat.get(bid, 0) + 1
            javob = "✅ Savatchaga qo'shildi (%d ta)" % savat[bid]
    elif data.startswith("del:"):
        savat = u.get("savat") or {}
        bid = data[4:]
        if savat.get(bid, 0) > 1:
            savat[bid] -= 1
        else:
            savat.pop(bid, None)
        call("deleteMessage", chat_id=chat, message_id=mid)
        savat_korsat(chat, u, db)
    elif data == "savat_tozala":
        u["savat"] = {}
        call("editMessageText", chat_id=chat, message_id=mid, text="🗑 Savatcha tozalandi.")
    elif data == "savat_ok":
        buyurtma_boshla(chat, u, db)
    elif data.startswith("tavsiya:"):
        royxat_yubor(chat, mos_kitoblar(u), db, int(data[8:]), "tavsiya:%d")
    elif data.startswith("kat:"):
        _, key, off = data.split(":")
        books = [b for b in BOOKS.values() if key in b["janr"]]
        if int(off) == 0:
            send(chat, "%s — %d ta kitob:" % (JANR_NOMI.get(key, key), len(books)))
        royxat_yubor(chat, books, db, int(off), "kat:%s:%%d" % key)
    elif data.startswith(("pay:", "naqd:")):
        usul, _, oid = data.partition(":")
        o = find_order(db, oid)
        if not o or o["chat"] != chat or o["holat"] != "kutilmoqda":
            javob = "Bu buyurtma allaqachon rasmiylashtirilgan"
        elif usul == "naqd":
            call("editMessageReplyMarkup", chat_id=chat, message_id=mid,
                 reply_markup={"inline_keyboard": []})
            buyurtma_tasdiq(chat, u, o, "naqd")
        else:
            r = call("sendInvoice", chat_id=chat, title="Kitoblar olami — №%d" % o["id"],
                     description="%d ta kitob" % sum(o["kitoblar"].values()),
                     payload="order:%d" % o["id"], provider_token=PAY_TOKEN, currency="UZS",
                     prices=[{"label": "Kitoblar", "amount": o["jami"] * 100}])
            if not r.get("ok"):
                javob = "Onlayn to'lov hozir ishlamayapti — naqd usulni tanlang"
    call("answerCallbackQuery", callback_query_id=cq["id"], text=javob)


def handle_pre_checkout(q, db):
    o = find_order(db, q.get("invoice_payload", "").partition(":")[2])
    ok = bool(o and o["holat"] == "kutilmoqda" and q.get("total_amount") == o["jami"] * 100)
    call("answerPreCheckoutQuery", pre_checkout_query_id=q["id"], ok=json.dumps(ok),
         error_message=None if ok else "Buyurtma eskirgan. Iltimos, qaytadan rasmiylashtiring.")


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        try:
            if upd.get("message"):
                handle_message(upd["message"], db)
            elif upd.get("callback_query") and upd["callback_query"].get("message"):
                handle_callback(upd["callback_query"], db)
            elif upd.get("pre_checkout_query"):
                handle_pre_checkout(upd["pre_checkout_query"], db)
        except Exception as e:                          # bitta xato botni to'xtatmasin
            print("xato:", repr(e), file=sys.stderr)
    return last


UPDATES = ["message", "callback_query", "pre_checkout_query"]


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Boshlash / ro'yxatdan o'tish"},
        {"command": "tavsiya", "description": "Menga mos kitoblar"},
        {"command": "katalog", "description": "Janrlar bo'yicha katalog"},
        {"command": "savat", "description": "Savatcha va buyurtma"},
        {"command": "aksiya", "description": "Juma aksiyasi"},
        {"command": "profil", "description": "Mening ma'lumotlarim"},
    ])
    r2 = call("setMyDescription", description=TAVSIF)
    r3 = call("setMyShortDescription", short_description="Kitob do'koni: tavsiya, onlayn buyurtma, juma aksiyalari")
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("buyruqlar:", r1.get("ok"), "| tavsif:", r2.get("ok"), r3.get("ok"))
    return all(x.get("ok") for x in (r1, r2, r3))


def main(argv):
    global BOOKS
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    BOOKS = load_books()
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=UPDATES)
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        aksiya_tekshir(db)
        save(db)
        print("qayta ishlandi: %d ta, foydalanuvchilar: %d" % (len(r.get("result", [])), len(db["users"])))
        return

    setup()
    offset = 0
    print("Bot ishga tushdi. Foydalanuvchilar:", len(db["users"]))
    while True:
        r = call("getUpdates", offset=offset, timeout=50, allowed_updates=UPDATES)
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
        aksiya_tekshir(db)
        save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

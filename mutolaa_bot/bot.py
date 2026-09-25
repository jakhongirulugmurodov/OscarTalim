#!/usr/bin/env python3
"""
«Mutolaa» kitob uyi — Telegram bot.

Kitobxon uchun:
  • ro'yxatdan o'tish: ism, familiya, yosh, telefon, sevimli janrlar + so'rovnoma
  • katalog: har bir kitobning narxi, qancha sotilgani va qancha qolgani
  • 🔥 juma aksiyasi — har juma bitta kitob maxsus narxda
  • 🏆 haftaning eng ko'p sotilgan kitoblari
  • buyurtma berish, 🎁 har xaridga sovg'a (xatcho'p, stiker...), kitobxon darajasi
  • qidiruv, do'stni taklif qilish havolasi

Avtomatik:
  • payshanba 19:00 — «ertaga aksiya» eslatmasi
  • juma 09:00 — haftalik xabar (top kitoblar + bugungi aksiya) hammaga va kanalga;
    aksiya belgilanmagan bo'lsa, eng ko'p qoldig'i bor kitob avtomatik tanlanadi
  • har kuni 23:00 — baza zaxirasi adminga

Admin: /admin buyrug'i barcha imkoniyatlarni ko'rsatadi.

Ishga tushirish:
    python3 bot.py                  # doimiy (server)
    python3 bot.py --muddat 7000    # 7000 soniya ishlab to'xtaydi (GitHub Actions)

Muhit o'zgaruvchilari — README.md ga qarang.
"""

import csv
import html
import io
import json
import os
import queue
import re
import signal
import sqlite3
import sys
import threading
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import tg                     # noqa: E402
from baza import Baza         # noqa: E402


def env(k, d=""):
    return os.environ.get(k, "").strip() or d


# ================================================================ DO'KON MA'LUMOTLARI
DOKON = env("DOKON_NOMI", "Mutolaa")
MANZIL = env("DOKON_MANZIL", "Toshkent shahri")
TELEFON = env("DOKON_TELEFON", "+998 90 000 00 00")
ISH_VAQTI = env("DOKON_ISH_VAQTI", "Har kuni 10:00 – 21:00")
XARITA = env("DOKON_XARITA")                 # Google/Yandex xarita havolasi
INSTAGRAM = env("DOKON_INSTAGRAM")           # masalan: mutolaa.uz
KANAL = env("KANAL_ID")                      # @kanal — haftalik xabar kanalga ham chiqadi
ADMINS = [int(x) for x in re.findall(r"-?\d+", env("ADMIN_IDS"))]
BUYURTMA_CHAT = env("BUYURTMA_CHAT_ID")      # buyurtmalar tushadigan guruh (ixtiyoriy)
DB_PATH = env("DB_PATH", os.path.join(HERE, "data", "mutolaa.db"))

TZ = timezone(timedelta(hours=5))            # Toshkent vaqti
AKSIYA_SOAT = 9                              # juma, haftalik xabar
ESLATMA_SOAT = 19                            # payshanba, «ertaga aksiya»
ZAXIRA_SOAT = 23                             # har kuni, baza zaxirasi
AKSIYA_CHEGIRMA = 0.20                       # avtomatik tanlashda chegirma

JANRLAR = {
    "badiiy": "📖 Badiiy adabiyot",
    "tarix": "🏛 Tarix",
    "diniy": "🕌 Diniy-ma'rifiy",
    "falsafa": "🧠 Falsafa",
    "psixologiya": "💭 Psixologiya",
    "biznes": "💼 Biznes va moliya",
    "rivojlanish": "🚀 Shaxsiy rivojlanish",
    "ilmiy": "🔬 Ilmiy-ommabop",
    "jahon": "🌍 Jahon klassikasi",
    "detektiv": "🕵️ Detektiv va sarguzasht",
    "sheriyat": "🪶 She'riyat",
    "bolalar": "🧸 Bolalar adabiyoti",
}
YOSHLAR = ["17 gacha", "18–24", "25–34", "35–44", "45+"]
SOROVLAR = [
    ("oqish", "📖 Oyiga nechta kitob o'qiysiz?",
     ["1 tadan kam", "1–2 ta", "3–5 ta", "5 tadan ko'p"]),
    ("manba", "🔎 Bizni qayerdan topdingiz?",
     ["Instagram", "Telegram kanal", "Do'stlardan", "Do'konda ko'rdim", "Boshqa"]),
    ("olish", "🛍 Kitobni qanday olishni afzal ko'rasiz?",
     ["🏬 Do'kondan borib", "🚚 Yetkazib berish", "Farqi yo'q"]),
]
MANBALAR = {"instagram": "Instagram", "ig": "Instagram", "insta": "Instagram",
            "telegram": "Telegram", "tg": "Telegram", "kanal": "Telegram"}
DARAJALAR = [(0, "🌱 Yangi kitobxon"), (1, "📖 Kitobxon"), (3, "📚 Faol kitobxon"),
             (6, "🦉 Kitob ustasi"), (12, "👑 Mutolaa afsonasi")]
BOSHLANGICH_SOVGALAR = [("🔖 Xatcho'p", 500), ("✨ Stikerlar to'plami", 500),
                        ("💌 Iqtibosli kartochka", 300)]

M_AKSIYA = "🔥 Juma aksiyasi"
M_KATALOG = "📚 Katalog"
M_TOP = "🏆 Top kitoblar"
M_QIDIR = "🔎 Qidirish"
M_SOVGA = "🎁 Sovg'alarim"
M_PROFIL = "👤 Profilim"
M_DOKON = "📍 Do'kon haqida"
MENYU_TUGMALARI = {M_AKSIYA, M_KATALOG, M_TOP, M_QIDIR, M_SOVGA, M_PROFIL, M_DOKON}

BOSQICHLAR = ["ism", "familiya", "yosh", "telefon", "janr"] + ["s%d" % i for i in range(len(SOROVLAR))]
SAHIFA = 8
MEDAL = ["🥇", "🥈", "🥉", "4.", "5.", "6.", "7.", "8.", "9.", "10."]
OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
         "sentabr", "oktabr", "noyabr", "dekabr"]

db = None                    # Baza — main() da ochiladi
BOT = ""                     # botning @username i — getMe dan
navbat = queue.Queue()       # ommaviy xabarlar navbati
TOXTA = threading.Event()


# ================================================================ yordamchilar
def e(s):
    return html.escape(str(s), quote=False)


def ism_togrimi(t):
    """Faqat harflar, bo'sh joy, chiziqcha va apostrof; kamida 2 ta harf."""
    return (2 <= len(t) <= 40 and t[0].isalpha() and sum(c.isalpha() for c in t) >= 2
            and all(c.isalpha() or c in " -'ʻʼ‘’`." for c in t))


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def hozir():
    return datetime.now(TZ)


def bugun():
    return hozir().date()


def sana_matn(d):
    return "%d-%s" % (d.day, OYLAR[d.month - 1])


def keyingi_juma(d):
    return d + timedelta(days=(4 - d.weekday()) % 7)


def bar(ulush, n=10):
    k = max(0, min(n, round(ulush * n)))
    return "▰" * k + "▱" * (n - k)


def raqam(s):
    d = re.sub(r"\D", "", s or "")
    return int(d) if d else None


def tekis(s):
    """Qidiruv uchun: kichik harf, turli apostroflarni bittaga keltiradi."""
    return re.sub(r"[ʻʼ‘’`´]", "'", (s or "").casefold())


def btn(text, data):
    return {"text": text, "callback_data": data}


def ikb(rows):
    return {"inline_keyboard": rows}


def menyu():
    return {"keyboard": [[{"text": M_AKSIYA}, {"text": M_KATALOG}],
                         [{"text": M_TOP}, {"text": M_QIDIR}],
                         [{"text": M_SOVGA}, {"text": M_PROFIL}],
                         [{"text": M_DOKON}]],
            "resize_keyboard": True, "is_persistent": True}


def tmp_ol(u):
    try:
        return json.loads(u["tmp"] or "{}")
    except ValueError:
        return {}


def janrlar(u):
    return [g for g in (u["genres"] or "").split(",") if g in JANRLAR]


def janr_top(s):
    """«tarix», «Tarix», «🏛 Tarix» → «tarix». Topilmasa None."""
    s = tekis(s).strip()
    if not s:
        return None
    if s in JANRLAR:
        return s
    for k, v in JANRLAR.items():
        nom = tekis(v.split(" ", 1)[1])
        if s == nom or s in nom or nom in s:
            return k
    return None


def ism(u):
    return (u["first_name"] or "kitobxon") if u else "kitobxon"


def daraja(n):
    joriy, keyingi = DARAJALAR[0], None
    for d in DARAJALAR:
        if n >= d[0]:
            joriy = d
        elif keyingi is None:
            keyingi = d
    return joriy, keyingi


def havola(param=""):
    return "https://t.me/%s%s" % (BOT, ("?start=" + param) if param else "")


def adminlarga(text, kb=None):
    for a in ADMINS:
        tg.send(a, text, kb)


def admin(uid):
    return uid in ADMINS


def xato_log():
    traceback.print_exc()


# ================================================================ aksiya
def aksiya():
    """Joriy yoki kelgusi juma aksiyasi (dict) yoki None."""
    a = db.get("aksiya")
    if not a:
        return None
    sana = date.fromisoformat(a["sana"])
    if sana < bugun():
        return None
    b = db.book(a["book_id"])
    if not b or not b["active"]:
        return None
    return {"kitob": b, "narx": a["narx"], "sana": sana, "bugun": sana == bugun()}


def narx_bugun(b):
    """(narx, aksiyami) — bugun aksiya bo'lsa aksiya narxi."""
    a = aksiya()
    if a and a["bugun"] and a["kitob"]["id"] == b["id"]:
        return a["narx"], True
    return b["price"], False


def foiz(eski, yangi):
    return round(100 - yangi * 100 / eski) if eski else 0


def aksiyani_tayyorla(sana):
    """Juma kuni aksiya belgilanmagan bo'lsa — eng ko'p qolgan kitobni tanlaydi."""
    a = aksiya()
    if a and a["sana"] == sana:
        return a
    b = db.one("SELECT * FROM books WHERE active=1 AND stock>0 ORDER BY stock DESC, sold, id LIMIT 1")
    if not b:
        return None
    narx = max(1000, int(b["price"] * (1 - AKSIYA_CHEGIRMA)) // 1000 * 1000)
    db.put("aksiya", {"book_id": b["id"], "narx": narx, "sana": sana.isoformat()})
    adminlarga("🤖 Bu juma uchun aksiya belgilanmagan edi — avtomatik tanlandi:\n"
               "📖 <b>%s</b> (#%d)\n💰 %s → <b>%s</b>\n\nO'zgartirish: <code>/aksiya_qoy %d NARX</code>"
               % (e(b["title"]), b["id"], som(b["price"]), som(narx), b["id"]))
    return aksiya()


# ================================================================ kitob kartochkasi
def qoldiq_matn(b):
    jami = b["sold"] + b["stock"]
    s = "✅ Sotildi: <b>%d</b> ta   📦 Qoldi: <b>%d</b> ta" % (b["sold"], b["stock"])
    if jami:
        s += "\n%s %d%% sotildi" % (bar(b["sold"] / jami), round(100 * b["sold"] / jami))
    if b["stock"] == 0:
        s += "\n❌ Hozircha tugagan"
    elif b["stock"] <= 5:
        s += "\n⚡ Oxirgi nusxalar!"
    return s


def kitob_matn(b, tavsif_chegara=700):
    narx, chegirma = narx_bugun(b)
    q = ["📖 <b>%s</b>" % e(b["title"])]
    if b["author"]:
        q.append("✍️ %s" % e(b["author"]))
    if b["genre"] in JANRLAR:
        q.append(JANRLAR[b["genre"]])
    if b["about"]:
        t = b["about"] if len(b["about"]) <= tavsif_chegara else b["about"][:tavsif_chegara] + "…"
        q += ["", "<i>%s</i>" % e(t)]
    q.append("")
    if chegirma:
        q.append("🔥 <b>JUMA AKSIYASI — faqat bugun!</b>")
        q.append("💰 <s>%s</s> → <b>%s</b> (−%d%%)" % (som(b["price"]), som(narx), foiz(b["price"], narx)))
    else:
        q.append("💰 Narxi: <b>%s</b>" % som(narx))
    q.append(qoldiq_matn(b))
    return "\n".join(q)


def kitob_kb(b, orqa=""):
    rows = []
    if b["stock"] > 0:
        rows.append([btn("🛒 Buyurtma berish", "buy:%d" % b["id"])])
    if BOT:
        matn = "📚 %s — %s do'konida" % (b["title"], DOKON)
        rows.append([{"text": "📤 Do'stga ulashish",
                      "url": "https://t.me/share/url?url=%s&text=%s"
                             % (quote(havola("b%d" % b["id"])), quote(matn))}])
    if orqa:
        rows.append([btn("⬅️ Orqaga", orqa)])
    return ikb(rows)


def kitob_yubor(uid, bid, orqa="", mid=None):
    b = db.book(bid)
    if not b or not b["active"]:
        return tg.send(uid, "Bu kitob katalogda topilmadi.")
    kb = kitob_kb(b, orqa)
    if b["photo"]:
        r = tg.send_photo(uid, b["photo"], kitob_matn(b, 350), kb)
        if r.get("ok"):
            return r
    if mid:
        return tg.edit(uid, mid, kitob_matn(b), kb)
    return tg.send(uid, kitob_matn(b), kb)


# ================================================================ katalog
def katalog_view():
    books = db.books()
    soni = {}
    for b in books:
        soni[b["genre"]] = soni.get(b["genre"], 0) + 1
    rows, row = [], []
    for k, v in JANRLAR.items():
        if soni.get(k):
            row.append(btn("%s (%d)" % (v, soni[k]), "g:%s:0" % k))
            if len(row) == 2:
                rows.append(row)
                row = []
    if row:
        rows.append(row)
    rows.append([btn("📄 Hammasi (%d)" % len(books), "g:all:0"), btn("🔥 Ko'p sotilgan", "g:top:0")])
    rows.append([btn("📃 To'liq ro'yxat", "royxat")])
    matn = ("📚 <b>%s katalogi</b>\n\n📕 %d nomdagi kitob · 📦 %d dona mavjud\n\nJanrni tanlang 👇"
            % (e(DOKON), len(books), sum(b["stock"] for b in books)))
    return matn, ikb(rows)


def royxat_view(key, sahifa):
    if key == "all":
        books, sarlavha = db.books(), "📄 <b>Barcha kitoblar</b>"
    elif key == "top":
        books = sorted(db.books(), key=lambda b: (-b["sold"], b["title"]))
        sarlavha = "🔥 <b>Eng ko'p sotilgan kitoblar</b>"
    else:
        books, sarlavha = db.books(key), "<b>%s</b>" % JANRLAR.get(key, key)
    sahifalar = max(1, (len(books) + SAHIFA - 1) // SAHIFA)
    sahifa = max(0, min(sahifa, sahifalar - 1))
    qism = books[sahifa * SAHIFA:(sahifa + 1) * SAHIFA]
    q = ["%s — %d ta kitob" % (sarlavha, len(books))]
    if sahifalar > 1:
        q[0] += " (%d/%d)" % (sahifa + 1, sahifalar)
    q.append("")
    rows = []
    orqa = "g:%s:%d" % (key, sahifa)
    for i, b in enumerate(qism, sahifa * SAHIFA + 1):
        narx, chegirma = narx_bugun(b)
        q.append("%d. <b>%s</b>%s" % (i, e(b["title"]), (" — " + e(b["author"])) if b["author"] else ""))
        q.append("     %s%s · 📦 %s · ✅ %d sotildi"
                 % ("🔥 " if chegirma else "💰 ", som(narx),
                    ("%d ta qoldi" % b["stock"]) if b["stock"] else "tugagan", b["sold"]))
        rows.append([btn("%d. %s" % (i, b["title"][:40]), "b:%d:%s" % (b["id"], orqa))])
    if not qism:
        q.append("Hozircha bu bo'limda kitob yo'q.")
    nav = []
    if sahifa > 0:
        nav.append(btn("◀️", "g:%s:%d" % (key, sahifa - 1)))
    if sahifa < sahifalar - 1:
        nav.append(btn("▶️", "g:%s:%d" % (key, sahifa + 1)))
    if nav:
        rows.append(nav)
    rows.append([btn("⬅️ Janrlar", "cat")])
    return "\n".join(q), ikb(rows)


def toliq_royxat(uid):
    """Barcha kitoblar — janrlar bo'yicha, bir necha xabarda."""
    books = db.books()
    q = ["📃 <b>%s — to'liq ro'yxat</b> (%d ta)" % (e(DOKON), len(books))]
    for k, v in list(JANRLAR.items()) + [("", "📦 Boshqa")]:
        guruh = [b for b in books if (b["genre"] == k if k else b["genre"] not in JANRLAR)]
        if not guruh:
            continue
        q += ["", "<b>%s</b>" % v]
        for b in guruh:
            q.append("• %s%s — %s · 📦 %d · ✅ %d" % (
                e(b["title"]), (" (%s)" % e(b["author"])) if b["author"] else "",
                som(narx_bugun(b)[0]), b["stock"], b["sold"]))
    q += ["", "Kitob nomini yozing — batafsil ma'lumot va buyurtma tugmasi chiqadi."]
    boloklar(uid, q)


def boloklar(uid, qatorlar, kb=None):
    """Uzun matnni 4096 belgidan oshirmay bo'lib yuboradi."""
    blok = ""
    for s in qatorlar:
        if len(blok) + len(s) + 1 > 3900:
            tg.send(uid, blok)
            blok = ""
        blok += s + "\n"
    if blok:
        tg.send(uid, blok, kb)


# ================================================================ bo'limlar
def aksiya_korsat(uid):
    a = aksiya()
    if a and a["bugun"]:
        return kitob_yubor(uid, a["kitob"]["id"])
    kun = keyingi_juma(bugun())
    if kun == bugun():                      # juma, lekin aksiya hali e'lon qilinmagan
        kun_matn = "bugun soat %d:00 da" % AKSIYA_SOAT
    else:
        qolgan = (kun - bugun()).days
        kun_matn = "%s, juma kuni (%s) soat %d:00 da" % (
            sana_matn(kun), "ertaga" if qolgan == 1 else "%d kundan so'ng" % qolgan, AKSIYA_SOAT)
    q = ["🔥 <b>Juma aksiyasi</b>", "",
         "Har juma bitta kitob odatdagidan <b>ancha arzon</b> narxda sotiladi. "
         "Soni cheklangan — tugaguncha yoki kun oxirigacha.", "",
         "📅 Keyingi aksiya %s e'lon qilinadi." % kun_matn]
    if a and a["kitob"]["genre"] in JANRLAR:
        q.append("🤫 Kichik maslahat: bu safar «%s» janridan!" % JANRLAR[a["kitob"]["genre"]].split(" ", 1)[1])
    q += ["", "🔔 Bot bildirishnomalarini o'chirmang — birinchilardan bo'lib bilasiz."]
    tg.send(uid, "\n".join(q))


def top_matn():
    rows = db.top(time.time() - 7 * 86400, 10)
    sarlavha = "🏆 <b>Haftaning eng ko'p sotilgan kitoblari</b>"
    if not rows:
        rows = db.q("SELECT *, sold AS n FROM books WHERE active=1 AND sold>0 ORDER BY sold DESC LIMIT 10")
        sarlavha = "🏆 <b>Eng ko'p sotilgan kitoblar</b>"
    if not rows:
        return "🏆 Hali sotuvlar yo'q — birinchi xaridor siz bo'ling! 📚", ikb([[btn("📚 Katalog", "cat")]])
    q = [sarlavha, ""]
    kb = []
    for i, b in enumerate(rows):
        q.append("%s <b>%s</b>%s" % (MEDAL[i], e(b["title"]), (" — " + e(b["author"])) if b["author"] else ""))
        q.append("      🔥 %d ta sotildi · 📦 %d ta qoldi" % (b["n"], b["stock"]))
        kb.append([btn("%s %s" % (MEDAL[i], b["title"][:40]), "b:%d:t" % b["id"])])
    return "\n".join(q), ikb(kb)


def top_korsat(uid):
    tg.send(uid, *top_matn())


def qidir_sora(uid):
    tg.send(uid, "🔎 Kitob nomi yoki muallifini yozing — topib beraman.\n"
                 "Masalan: <i>Muqaddima</i> yoki <i>Qodiriy</i>")


def qidir(uid, matn):
    so = [w for w in tekis(matn).split() if w]
    if not so or len(matn.strip()) < 2:
        return tg.send(uid, "Kamida 2 ta harf yozing 🙂", menyu())
    topildi = [b for b in db.books() if all(w in tekis(b["title"] + " " + b["author"]) for w in so)]
    if len(topildi) == 1:
        return kitob_yubor(uid, topildi[0]["id"])
    if topildi:
        q = ["🔎 <b>«%s»</b> bo'yicha %d ta kitob:" % (e(matn), len(topildi)), ""]
        kb = []
        for b in topildi[:15]:
            q.append("• <b>%s</b> — %s · 📦 %d" % (e(b["title"]), som(narx_bugun(b)[0]), b["stock"]))
            kb.append([btn(b["title"][:50], "b:%d:" % b["id"])])
        return tg.send(uid, "\n".join(q), ikb(kb))
    u = db.user(uid)
    t = tmp_ol(u)
    t["qidiruv"] = matn[:100]
    db.upd_user(uid, tmp=json.dumps(t, ensure_ascii=False))
    tg.send(uid, "😔 «%s» hozircha do'konimizda yo'q.\n\n"
                 "Xohlasangiz, so'rov qoldiring — kitobni olib kelsak, sizga birinchi bo'lib xabar beramiz."
            % e(matn), ikb([[btn("📝 So'rov qoldirish", "req")]]))


def sovgalar(uid):
    rows = db.bought(uid)
    n = sum(r["qty"] for r in rows)
    (_, nom), keyingi = daraja(n)
    q = ["🎁 <b>Sovg'alarim</b>", "", "Darajangiz: <b>%s</b>" % nom, "Sotib olingan kitoblar: <b>%d</b> ta" % n]
    if keyingi:
        q.append("Keyingi daraja — %s: yana %d ta kitob" % (keyingi[1], keyingi[0] - n))
    q.append("")
    sovga = [r for r in rows if r["gift"]]
    if sovga:
        q.append("<b>Olgan sovg'alaringiz:</b>")
        for r in sovga[:20]:
            q.append("%s — «%s» bilan, %s" % (e(r["gift"]), e(r["title"]),
                                             datetime.fromtimestamp(r["done_at"], TZ).strftime("%d.%m.%Y")))
    else:
        q.append("Hozircha sovg'a yo'q. Har bir xaridga kichik sovg'a beramiz — "
                 "🔖 xatcho'p, ✨ stikerlar va boshqalar!")
    tg.send(uid, "\n".join(q))


def profil(uid):
    u = db.user(uid)
    n = sum(r["qty"] for r in db.bought(uid))
    js = ", ".join(JANRLAR[g].split(" ", 1)[1] for g in janrlar(u)) or "—"
    q = ["👤 <b>Profilim</b>", "",
         "🙂 %s %s" % (e(u["first_name"]), e(u["last_name"])),
         "📞 %s" % e(u["phone"]),
         "🎂 Yosh: %s" % e(u["age"]),
         "🏷 Janrlar: %s" % e(js),
         "📚 Xaridlar: %d ta · %s" % (n, daraja(n)[0][1]),
         "", "👥 Siz taklif qilgan do'stlar: <b>%d</b>" % db.invited_count(uid)]
    if BOT:
        q += ["Taklif havolangiz:", "<code>%s</code>" % havola("r%d" % uid),
              "Eng faol kitobxonlarni sovg'alar bilan taqdirlaymiz 🎁"]
    tg.send(uid, "\n".join(q), ikb([[btn("🏷 Janrlarni o'zgartirish", "pj")],
                                    [btn("✏️ Ma'lumotlarni yangilash", "pr")]]))


def dokon(uid):
    q = ["📍 <b>%s kitob uyi</b>" % e(DOKON), "",
         "🏠 %s" % e(MANZIL), "🕰 %s" % e(ISH_VAQTI), "📞 %s" % e(TELEFON)]
    if INSTAGRAM:
        q.append('📸 <a href="https://instagram.com/%s">Instagram</a>' % e(INSTAGRAM.lstrip("@")))
    if KANAL.startswith("@"):
        q.append('📢 <a href="https://t.me/%s">Telegram kanal</a>' % e(KANAL[1:]))
    q += ["", "📚 Kitob — eng yaxshi sovg'a. Har xaridga — bizdan kichik sovg'a 🎁"]
    kb = ikb([[{"text": "🗺 Xaritada ochish", "url": XARITA}]]) if XARITA else None
    tg.send(uid, "\n".join(q), kb)


def yordam(uid):
    tg.send(uid, "📚 <b>%s — yordam</b>\n\n"
                 "%s — bugungi yoki keyingi aksiya\n%s — janrlar bo'yicha kitoblar\n"
                 "%s — haftaning eng ko'p sotilganlari\n%s — kitob izlash\n"
                 "%s — xaridlaringiz va sovg'alar\n%s — ma'lumotlaringiz, taklif havolasi\n\n"
                 "💡 Istalgan payt kitob nomini yozing — topib beraman.\n📞 Savollar: %s"
            % (e(DOKON), M_AKSIYA, M_KATALOG, M_TOP, M_QIDIR, M_SOVGA, M_PROFIL, e(TELEFON)), menyu())


BOLIMLAR = {M_AKSIYA: aksiya_korsat, M_KATALOG: lambda uid: tg.send(uid, *katalog_view()),
            M_TOP: top_korsat, M_QIDIR: qidir_sora, M_SOVGA: sovgalar, M_PROFIL: profil,
            M_DOKON: dokon}
BUYRUQLAR = {"/aksiya": aksiya_korsat, "/katalog": BOLIMLAR[M_KATALOG], "/top": top_korsat,
             "/sovgalar": sovgalar, "/profil": profil, "/dokon": dokon, "/yordam": yordam,
             "/help": yordam}


# ================================================================ ro'yxatdan o'tish
SALOM = ("📚 <b>{dokon} kitob uyiga xush kelibsiz!</b>\n\n"
         "Bu yerda sizni kutmoqda:\n"
         "🔥 har juma — bitta kitob maxsus aksiya narxida\n"
         "🏆 haftaning eng ko'p o'qilayotgan kitoblari\n"
         "📦 har bir kitob: qancha sotildi, qanchasi qoldi\n"
         "🎁 har bir xaridga — kichik sovg'a: xatcho'p, stikerlar\n\n"
         "Keling, avval tanishib olaylik — bor-yo'g'i 1 daqiqa ☕️")


def janr_kb(tanlangan):
    rows, row = [], []
    for k, v in JANRLAR.items():
        row.append(btn(("✅ " if k in tanlangan else "") + v, "jt:" + k))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([btn("Tayyor ➡️", "jd")])
    return ikb(rows)


def qadam_belgi(qadam):
    return "<i>%d/%d</i>  " % (BOSQICHLAR.index(qadam) + 1, len(BOSQICHLAR))


def sora(uid, qadam):
    u = db.user(uid)
    t = tmp_ol(u)
    if qadam in ("ism", "familiya"):
        taklif = t.get("tg_first" if qadam == "ism" else "tg_last") or ""
        kb = ({"keyboard": [[{"text": taklif[:40]}]], "resize_keyboard": True, "one_time_keyboard": True}
              if taklif else {"remove_keyboard": True})
        tg.send(uid, qadam_belgi(qadam) + ("✍️ <b>Ismingiz?</b>" if qadam == "ism"
                                           else "✍️ <b>Familiyangiz?</b>"), kb)
    elif qadam == "yosh":
        tg.send(uid, qadam_belgi(qadam) + "🎂 <b>Yoshingiz?</b>\nTanlang yoki raqam bilan yozing.",
                {"keyboard": [[{"text": y} for y in YOSHLAR[:3]], [{"text": y} for y in YOSHLAR[3:]]],
                 "resize_keyboard": True, "one_time_keyboard": True})
    elif qadam == "telefon":
        tg.send(uid, qadam_belgi(qadam) + "📱 <b>Telefon raqamingiz?</b>\n"
                     "Pastdagi tugmani bosing — raqam avtomatik yuboriladi. "
                     "Buyurtma berganingizda aynan shu raqamga qo'ng'iroq qilamiz.",
                {"keyboard": [[{"text": "📱 Raqamni yuborish", "request_contact": True}]],
                 "resize_keyboard": True, "one_time_keyboard": True})
    elif qadam == "janr":
        tg.send(uid, qadam_belgi(qadam) + "📚 <b>Qaysi janrdagi kitoblarni yoqtirasiz?</b>\n"
                     "Bir nechtasini tanlang — sizga mos kitoblar haqida birinchi bo'lib aytamiz.",
                janr_kb(janrlar(u)))
    elif qadam.startswith("s"):
        i = int(qadam[1:])
        _, savol, variantlar = SOROVLAR[i]
        tg.send(uid, qadam_belgi(qadam) + "<b>%s</b>" % savol,
                ikb([[btn(v, "s:%d:%d" % (i, j))] for j, v in enumerate(variantlar)]))


def keyingi(uid, joriy):
    i = BOSQICHLAR.index(joriy) + 1
    if i < len(BOSQICHLAR):
        db.upd_user(uid, step=BOSQICHLAR[i])
        sora(uid, BOSQICHLAR[i])
    else:
        yakunla(uid)


def yosh_oraliq(s):
    s = s.strip()
    if s in YOSHLAR:
        return s
    n = raqam(s) if re.fullmatch(r"\d{1,2}", s) else None
    if n is None or not 5 <= n <= 99:
        return None
    return "17 gacha" if n < 18 else "18–24" if n < 25 else "25–34" if n < 35 else "35–44" if n < 45 else "45+"


def telefon_norm(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) == 9:
        d = "998" + d
    if len(d) == 12 and d.startswith("998"):
        return "+" + d
    if 10 <= len(d) <= 15 and (s or "").strip().startswith("+"):
        return "+" + d
    return None


def royxat_matn(u, m, text):
    uid, qadam = u["id"], u["step"]
    if qadam in ("ism", "familiya"):
        t = " ".join(text.split())
        if not ism_togrimi(t):
            return tg.send(uid, "Iltimos, %s harflar bilan yozing (2–40 belgi)."
                           % ("ismingizni" if qadam == "ism" else "familiyangizni"))
        db.upd_user(uid, **{"first_name" if qadam == "ism" else "last_name": t[0].upper() + t[1:]})
        return keyingi(uid, qadam)
    if qadam == "yosh":
        y = yosh_oraliq(text)
        if not y:
            return sora(uid, "yosh")
        db.upd_user(uid, age=y)
        return keyingi(uid, qadam)
    if qadam == "telefon":
        c = m.get("contact")
        if c and c.get("user_id") and c["user_id"] != uid:
            return tg.send(uid, "Iltimos, <b>o'zingizning</b> raqamingizni yuboring 🙂")
        tel = telefon_norm(c["phone_number"] if c else text)
        if not tel:
            return tg.send(uid, "Raqamni tugma orqali yuboring yoki <code>+998 90 123 45 67</code> "
                                "ko'rinishida yozing.",
                           {"keyboard": [[{"text": "📱 Raqamni yuborish", "request_contact": True}]],
                            "resize_keyboard": True, "one_time_keyboard": True})
        db.upd_user(uid, phone=tel)
        tg.send(uid, "✅ Raqam qabul qilindi: %s" % tel, {"remove_keyboard": True})
        return keyingi(uid, qadam)
    # janr va so'rovnoma — tugmalar orqali
    tg.send(uid, "👆 Iltimos, yuqoridagi tugmalardan tanlang.")
    sora(uid, qadam)


def yakunla(uid):
    u = db.user(uid)
    t = tmp_ol(u)
    keyin = t.pop("keyin", None)
    birinchi = not u["registered_at"]
    f = {"step": None, "tmp": json.dumps(t, ensure_ascii=False)}
    if birinchi:
        f["registered_at"] = int(time.time())
    db.upd_user(uid, **f)
    if not birinchi:
        return tg.send(uid, "✅ Ma'lumotlaringiz yangilandi!", menyu())
    tg.send(uid, "🎉 <b>Tabriklaymiz, %s!</b>\nSiz endi %s kitobxonlari safidasiz.\n\n"
                 "📌 Har juma soat %d:00 da — aksiya kitobi\n"
                 "🏆 Har hafta — eng ko'p sotilgan kitoblar\n"
                 "🎁 Har bir xaridga — sovg'a\n\n"
                 "💡 Kitob nomini yozsangiz — darhol topib beraman. Yoki pastdagi menyudan foydalaning 👇"
            % (e(ism(u)), e(DOKON), AKSIYA_SOAT), menyu())
    if u["invited_by"]:
        tg.send(u["invited_by"], "🎉 Do'stingiz <b>%s</b> sizning taklifingiz bilan qo'shildi! "
                                 "Jami taklif qilganlaringiz: %d"
                % (e(ism(u)), db.invited_count(u["invited_by"])))
    if keyin:
        chuqur_havola(uid, keyin)


def chuqur_havola(uid, arg):
    if arg == "aksiya":
        aksiya_korsat(uid)
    elif arg == "katalog":
        tg.send(uid, *katalog_view())
    elif arg == "top":
        top_korsat(uid)
    elif re.fullmatch(r"b\d+", arg):
        kitob_yubor(uid, int(arg[1:]))


def start(u, arg):
    uid = u["id"]
    arg = (arg or "").strip().lower()
    if arg in MANBALAR and not u["ref"]:
        db.upd_user(uid, ref=MANBALAR[arg])
    if re.fullmatch(r"r\d+", arg) and not u["registered_at"] and not u["invited_by"]:
        kim = int(arg[1:])
        if kim != uid and db.user(kim):
            db.upd_user(uid, invited_by=kim, ref=u["ref"] or "Do'st taklifi")
    if u["registered_at"]:
        tg.send(uid, "📚 <b>%s</b>ga xush kelibsiz, %s!" % (e(DOKON), e(ism(u))), menyu())
        return chuqur_havola(uid, arg)
    t = tmp_ol(u)
    if arg and arg not in MANBALAR and not arg.startswith("r"):
        t["keyin"] = arg
    db.upd_user(uid, tmp=json.dumps(t, ensure_ascii=False), step=u["step"] or "ism")
    tg.send(uid, SALOM.format(dokon=e(DOKON)))
    sora(uid, u["step"] or "ism")


# ================================================================ buyurtma
def buyurtma_matn(o, u=None):
    u = u or (db.user(o["user_id"]) if o["user_id"] else None)
    q = ["🛒 <b>Buyurtma #%d</b>%s" % (o["id"], " (do'konda)" if o["via"] == "dokon" else "")]
    if u:
        q.append("👤 %s %s%s" % (e(u["first_name"]), e(u["last_name"]),
                                 (" (@%s)" % e(u["username"])) if u["username"] else ""))
        q.append("📞 %s" % e(u["phone"]))
        s = json.loads(u["survey"] or "{}")
        if s.get("olish"):
            q.append("🛍 %s" % e(s["olish"]))
    q.append("📖 %s%s × %d" % (e(o["title"]), (" — " + e(o["author"])) if o["author"] else "", o["qty"]))
    q.append("💰 %s" % som(o["price"] * o["qty"]))
    q.append("📦 Omborda qoldi: %d ta" % o["stock"])
    holat = {"yangi": "🕐 Kutilmoqda", "sotildi": "✅ Sotildi", "bekor": "❌ Bekor qilindi"}[o["status"]]
    q.append("\n" + holat + ("  ·  🎁 %s" % e(o["gift"]) if o["gift"] else ""))
    return "\n".join(q)


def buyurtma_kb(o):
    if o["status"] != "yangi":
        return None
    return ikb([[btn("✅ Sotildi", "adm:ok:%d" % o["id"]), btn("❌ Bekor", "adm:x:%d" % o["id"])]])


def sotildi_xabari(o):
    """Kitobxonga: xarid uchun rahmat + sovg'a + daraja."""
    if not o["user_id"]:
        return
    n = sum(r["qty"] for r in db.bought(o["user_id"]))
    (_, nom), kel = daraja(n)
    q = ["🎉 <b>Xaridingiz uchun rahmat!</b>", "", "📖 %s" % e(o["title"])]
    if o["gift"]:
        q.append("🎁 Sovg'angiz: <b>%s</b> — kitob bilan birga beriladi!" % e(o["gift"]))
    q += ["", "Darajangiz: <b>%s</b> (%d ta kitob)" % (nom, n)]
    if kel:
        q.append("Keyingi daraja — %s: yana %d ta kitob" % (kel[1], kel[0] - n))
    q += ["", "Yoqimli mutolaa! 📚 Kitob haqida fikringizni bizga yozib qoldiring."]
    tg.send(o["user_id"], "\n".join(q))


def kam_qoldi(o):
    if 0 <= o["stock"] <= 5:
        adminlarga("⚠️ <b>%s</b> — omborda %d ta qoldi." % (e(o["title"]), o["stock"]))


# ================================================================ tugmalar (callback)
def tugma(cb):
    d = cb.get("data") or ""
    uid = cb["from"]["id"]
    m = cb.get("message") or {}
    chat, mid = (m.get("chat") or {}).get("id"), m.get("message_id")
    if d.startswith("adm:"):
        return admin_tugma(cb, d, chat, mid)
    if chat != uid:
        return None
    u = db.user(uid)
    if not u:
        return "Avval /start bosing", True

    if d.startswith("jt:"):
        k = d[3:]
        tan = janrlar(u)
        tan = [g for g in tan if g != k] if k in tan else tan + [k]
        db.upd_user(uid, genres=",".join(tan))
        tg.edit_kb(uid, mid, janr_kb(tan))
        return None
    if d == "jd":
        tan = janrlar(u)
        if not tan:
            return "Kamida bitta janr tanlang 🙂", True
        nomlar = ", ".join(JANRLAR[g].split(" ", 1)[1] for g in tan)
        if u["step"] == "janr":
            tg.edit(uid, mid, "📚 Janrlar: <b>%s</b> ✅" % e(nomlar))
            keyingi(uid, "janr")
        else:
            tg.edit(uid, mid, "✅ Janrlaringiz saqlandi: <b>%s</b>" % e(nomlar))
        return None
    if d.startswith("s:"):
        _, i, j = d.split(":")
        i, j = int(i), int(j)
        if u["step"] != "s%d" % i:
            return "Bu savolga javob berilgan ✅"
        kalit, savol, variantlar = SOROVLAR[i]
        s = json.loads(u["survey"] or "{}")
        s[kalit] = variantlar[j]
        db.upd_user(uid, survey=json.dumps(s, ensure_ascii=False))
        tg.edit(uid, mid, "<b>%s</b>\n✅ %s" % (savol, e(variantlar[j])))
        keyingi(uid, "s%d" % i)
        return None

    if not u["registered_at"]:
        sora(uid, u["step"] or "ism")
        return "Avval ro'yxatdan o'tishni yakunlang 🙂"

    if d == "cat":
        tg.edit(uid, mid, *katalog_view())
    elif d.startswith("g:"):
        _, key, sahifa = d.split(":")
        tg.edit(uid, mid, *royxat_view(key, int(sahifa)))
    elif d == "t":
        tg.edit(uid, mid, *top_matn())
    elif d.startswith("b:"):
        _, bid, orqa = d.split(":", 2)
        kitob_yubor(uid, int(bid), orqa, mid)
    elif d == "royxat":
        toliq_royxat(uid)
    elif d.startswith("buy:"):
        return buyurtma_sora(u, int(d[4:]))
    elif d.startswith("ok:"):
        return buyurtma_tasdiq(u, int(d[3:]), mid)
    elif d == "no":
        tg.edit(uid, mid, "Buyurtma bekor qilindi. Boshqa kitob tanlash uchun — %s" % M_KATALOG)
    elif d == "req":
        t = tmp_ol(u)
        nom = t.pop("qidiruv", "")
        if not nom:
            return "So'rov allaqachon yuborilgan ✅"
        db.upd_user(uid, tmp=json.dumps(t, ensure_ascii=False))
        sor = db.get("kitob_sorovlari", [])
        sor.append({"kitob": nom, "user": uid, "vaqt": int(time.time())})
        db.put("kitob_sorovlari", sor[-500:])
        tg.edit(uid, mid, "📝 So'rovingiz qabul qilindi: «%s». Kitob kelsa, xabar beramiz!" % e(nom))
        adminlarga("📝 <b>Kitob so'rovi:</b> «%s»\n👤 %s %s, %s"
                   % (e(nom), e(u["first_name"]), e(u["last_name"]), e(u["phone"])))
    elif d == "pj":
        tg.send(uid, "🏷 Qaysi janrlar sizga yoqadi?", janr_kb(janrlar(u)))
    elif d == "pr":
        db.upd_user(uid, step="ism")
        sora(uid, "ism")
    return None


def buyurtma_sora(u, bid):
    b = db.book(bid)
    if not b or not b["active"]:
        return "Kitob topilmadi", True
    if b["stock"] <= 0:
        return "Afsuski, bu kitob tugagan 😔", True
    if db.pending_order(u["id"], bid):
        return "Bu kitobga buyurtmangiz qabul qilingan — operatorimiz siz bilan bog'lanadi 📞", True
    narx, chegirma = narx_bugun(b)
    tg.send(u["id"], "🛒 <b>Buyurtmani tasdiqlang</b>\n\n📖 %s%s\n💰 %s%s\n📞 %s\n\n"
                     "Tasdiqlasangiz, operatorimiz shu raqamga qo'ng'iroq qilib, "
                     "olib ketish yoki yetkazib berishni kelishib oladi."
            % (e(b["title"]), (" — " + e(b["author"])) if b["author"] else "", som(narx),
               "  🔥 aksiya narxi" if chegirma else "", e(u["phone"])),
            ikb([[btn("✅ Tasdiqlash", "ok:%d" % bid), btn("❌ Bekor qilish", "no")]]))
    return None


def buyurtma_tasdiq(u, bid, mid):
    b = db.book(bid)
    if not b or b["stock"] <= 0:
        tg.edit(u["id"], mid, "Afsuski, bu kitob hozirgina tugab qoldi 😔")
        return None
    if db.pending_order(u["id"], bid):
        return "Buyurtmangiz allaqachon qabul qilingan ✅"
    narx, _ = narx_bugun(b)
    o = db.order(db.new_order(u["id"], bid, narx))
    tg.edit(u["id"], mid, "✅ <b>Buyurtma #%d qabul qilindi!</b>\n\n📖 %s — %s\n\n"
                          "Operatorimiz tez orada %s raqamiga qo'ng'iroq qiladi.\n"
                          "🎁 Kitob bilan birga sovg'a ham olasiz!"
            % (o["id"], e(b["title"]), som(narx), e(u["phone"])))
    for chat in ([BUYURTMA_CHAT] if BUYURTMA_CHAT else ADMINS):
        tg.send(chat, "🆕 " + buyurtma_matn(o, u), buyurtma_kb(o))
    return None


def admin_tugma(cb, d, chat, mid):
    if not admin(cb["from"]["id"]):
        return "Bu tugma faqat admin uchun", True
    _, amal, oid = d.split(":")
    if amal == "ok":
        o, xato = db.sell_order(int(oid))
    else:
        o, xato = db.cancel_order(int(oid))
    if o and chat and mid:
        tg.edit(chat, mid, buyurtma_matn(o) + "\n👮 %s" % e(cb["from"].get("first_name", "")),
                buyurtma_kb(o))
    if xato:
        return xato, True
    if amal == "ok":
        sotildi_xabari(o)
        kam_qoldi(o)
        return "✅ Sotildi" + (" · sovg'a: " + o["gift"] if o["gift"] else "")
    if o["user_id"]:
        tg.send(o["user_id"], "❌ Buyurtma #%d («%s») bekor qilindi.\nSavollar bo'lsa: %s"
                % (o["id"], e(o["title"]), e(TELEFON)))
    return "Bekor qilindi"


# ================================================================ ommaviy xabarlar
def tarqatuvchi():
    """Alohida oqim: navbatdagi ommaviy xabarlarni Telegram cheklovi ichida yuboradi."""
    while True:
        nom, xabarlar = navbat.get()
        try:
            ok, bloklar = 0, []
            for cid, matn, kb, rasm in xabarlar:
                r = tg.send_photo(cid, rasm, matn, kb) if rasm else tg.send(cid, matn, kb)
                if r.get("ok"):
                    ok += 1
                elif r.get("error_code") == 403:
                    bloklar.append(cid)
                time.sleep(0.04)             # ~25 xabar/soniya
            if bloklar:
                b = Baza(DB_PATH)
                b.mark_blocked(bloklar)
                b.close()
            adminlarga("📣 «%s» yuborildi: <b>%d</b> / %d%s"
                       % (e(nom), ok, len(xabarlar),
                          (" · botni bloklaganlar: %d" % len(bloklar)) if bloklar else ""))
        except Exception:
            xato_log()
        finally:
            navbat.task_done()


def tarqat(nom, xabarlar):
    navbat.put((nom, xabarlar))
    return len(xabarlar)


def haftalik_matn(u, a, top):
    q = (["📚 <b>Assalomu alaykum, %s!</b>" % e(ism(u)), "%s — haftalik kitob xabarnomasi" % e(DOKON)]
         if u else ["📚 <b>%s — haftalik kitob xabarnomasi</b>" % e(DOKON)])
    if top:
        q += ["", "🏆 <b>Haftaning eng ko'p sotilgan kitoblari:</b>"]
        for i, b in enumerate(top[:5]):
            q.append("%s %s — %d ta" % (MEDAL[i], e(b["title"]), b["n"]))
    if a:
        b = a["kitob"]
        q += ["", "🔥 <b>%s JUMA AKSIYASI</b>" % ("BUGUNGI" if a["bugun"] else sana_matn(a["sana"]).upper()),
              "📖 <b>%s</b>%s" % (e(b["title"]), (" — " + e(b["author"])) if b["author"] else ""),
              "💰 <s>%s</s> → <b>%s</b> (−%d%%)" % (som(b["price"]), som(a["narx"]), foiz(b["price"], a["narx"])),
              "📦 Faqat <b>%d ta</b> qoldi!" % b["stock"]]
        if a["bugun"]:
            q.append("⏰ Aksiya faqat bugun, 23:59 gacha")
        if u and b["genre"] in janrlar(u):
            q.append("💡 Bu kitob siz yoqtirgan «%s» janridan!" % JANRLAR[b["genre"]].split(" ", 1)[1])
    q += ["", "🎁 Har bir xaridga — sovg'a: xatcho'p yoki stikerlar!"]
    return "\n".join(q)


def haftalik_yubor(faqat=None):
    a = aksiyani_tayyorla(bugun()) if bugun().weekday() == 4 else aksiya()
    top = db.top(time.time() - 7 * 86400, 5)
    kb = ikb([[btn("🛒 Buyurtma berish", "buy:%d" % a["kitob"]["id"])], [btn("📚 Katalog", "catn")]]
             if a else [[btn("📚 Katalogni ochish", "catn")]])
    rasm = a["kitob"]["photo"] if a else ""
    users = [db.user(faqat)] if faqat else db.audience()
    xabarlar = []
    for u in users:
        if not u:
            continue
        t = haftalik_matn(u, a, top)
        xabarlar.append((u["id"], t, kb, rasm if rasm and len(t) <= 1024 else ""))
    if faqat:
        for cid, t, k, r in xabarlar:
            (tg.send_photo(cid, r, t, k) if r else tg.send(cid, t, k))
        return len(xabarlar)
    if KANAL:
        t = haftalik_matn(None, a, top)
        kkb = ikb([[{"text": "🛒 Botda buyurtma berish", "url": havola("aksiya")}]])
        (tg.send_photo(KANAL, rasm, t, kkb) if rasm and len(t) <= 1024 else tg.send(KANAL, t, kkb))
    return tarqat("Haftalik xabar", xabarlar)


def ertaga_eslatma():
    a = aksiya()
    maslahat = ""
    if a and a["sana"] == bugun() + timedelta(days=1) and a["kitob"]["genre"] in JANRLAR:
        maslahat = "🤫 Kichik maslahat: bu safar «%s» janridan!\n\n" % JANRLAR[a["kitob"]["genre"]].split(" ", 1)[1]
    xabarlar = [(u["id"], "⏳ <b>%s, ertaga — juma!</b>\n\n"
                          "Ertaga soat %d:00 da haftaning aksiya kitobini e'lon qilamiz. "
                          "Narxi — odatdagidan ancha arzon, soni esa cheklangan.\n\n%s"
                          "🔔 Bildirishnomalarni yoqib qo'ying — birinchilardan bo'lib olasiz!"
                 % (e(ism(u)), AKSIYA_SOAT, maslahat), None, "") for u in db.audience()]
    return tarqat("Ertaga aksiya eslatmasi", xabarlar)


def zaxira_yubor(chat):
    nom = "mutolaa-%s.db" % hozir().strftime("%Y-%m-%d-%H%M")
    return tg.send_document(chat, nom, db.backup_bytes(),
                            "💾 Baza zaxirasi. Tiklash: shu faylni /tikla izohi bilan yuboring.")


def jadval():
    """Har aylanishda chaqiriladi: vaqti kelgan avtomatik ishlarni bajaradi."""
    n = hozir()
    s = n.date().isoformat()
    if n.weekday() == 4 and AKSIYA_SOAT <= n.hour < 21 and db.get("haftalik_sana") != s:
        db.put("haftalik_sana", s)
        haftalik_yubor()
    if n.weekday() == 3 and ESLATMA_SOAT <= n.hour < 22 and db.get("eslatma_sana") != s:
        db.put("eslatma_sana", s)
        ertaga_eslatma()
    if n.hour >= ZAXIRA_SOAT and ADMINS and db.get("zaxira_sana") != s:
        db.put("zaxira_sana", s)
        zaxira_yubor(ADMINS[0])


# ================================================================ admin
def a_admin(uid, arg):
    tg.send(uid, statistika_matn(qisqa=True) + "\n\n" + ADMIN_YORDAM)


ADMIN_YORDAM = """🛠 <b>Admin buyruqlari</b>

📊 /statistika — auditoriya, so'rovnoma, savdo
🛒 /buyurtmalar — kutilayotgan buyurtmalar
📦 /qoldiq — barcha kitoblar: qoldi / sotildi
📝 /sorovlar — kitobxonlar so'ragan kitoblar

<b>Katalog</b>
<code>/kitob_qosh Nomi | Muallif | janr | narx | soni</code>
<code>/narx 5 120000</code> · <code>/soni 5 40</code> · <code>/ochir 5</code>
Rasm: kitob rasmini <code>/rasm 5</code> izohi bilan yuboring
CSV/Excel ro'yxat: <b>.csv</b> faylni yuboring (nomi;muallif;janr;narx;soni;tavsif)
/janrlar — janr kalitlari

<b>Aksiya va sotuv</b>
<code>/aksiya_qoy 5 239000</code> — shu (yoki keyingi) juma aksiyasi
<code>/aksiya_qoy 5 239000 keyingi</code> — bir hafta keyingisi
/aksiya_bekor
<code>/sotuv 5</code> · <code>/sotuv 5 2 +998901234567</code> — do'kondagi sotuv
/sovga_qoldiq · <code>/sovga_qosh 🔖 Xatcho'p | 200</code>

<b>Xabarlar</b>
<code>/xabar matn</code> — hammaga (rasm bilan ham bo'ladi)
<code>/xabar_janr tarix matn</code> — janr bo'yicha
/haftalik_test — haftalik xabarni o'zingizga ko'rish
/haftalik — haftalik xabarni hozir hammaga
/instagram — Instagram uchun tayyor matn

<b>Ma'lumot</b>
/eksport — kitobxonlar, sotuvlar, katalog (CSV)
/zaxira — baza nusxasi · tiklash: faylni <code>/tikla</code> izohi bilan yuboring"""


def taqsimot(sanoq, jami, n=8):
    q = []
    for k, v in sorted(sanoq.items(), key=lambda x: -x[1])[:n]:
        q.append("  %s — %d (%d%%)" % (e(k or "—"), v, round(100 * v / jami) if jami else 0))
    return q


def statistika_matn(qisqa=False):
    users = db.q("SELECT * FROM users")
    reg = [u for u in users if u["registered_at"]]
    kun0 = int(datetime.combine(bugun(), datetime.min.time(), TZ).timestamp())
    hafta0 = time.time() - 7 * 86400
    faol = [u for u in reg if not u["blocked"]]
    savdo = lambda since: db.one("SELECT COALESCE(SUM(qty),0) n, COALESCE(SUM(qty*price),0) s FROM orders "
                                 "WHERE status='sotildi' AND done_at>=?", int(since))
    h, j, k = savdo(hafta0), savdo(0), savdo(kun0)
    kut = db.one("SELECT COUNT(*) n FROM orders WHERE status='yangi'")["n"]
    ombor = db.one("SELECT COUNT(*) n, COALESCE(SUM(stock),0) s FROM books WHERE active=1")
    q = ["📊 <b>%s — statistika</b>" % e(DOKON), "",
         "👥 Botga kirgan: <b>%d</b> · ro'yxatdan o'tgan: <b>%d</b>" % (len(users), len(reg)),
         "🆕 Bugun: +%d · 7 kunda: +%d" % (sum(1 for u in reg if u["registered_at"] >= kun0),
                                          sum(1 for u in reg if u["registered_at"] >= hafta0)),
         "🚫 Botni bloklagan: %d · faol: %d" % (len(reg) - len(faol), len(faol)), "",
         "🛒 Bugun: %d ta · %s" % (k["n"], som(k["s"])),
         "🛒 7 kunda: %d ta · %s" % (h["n"], som(h["s"])),
         "🛒 Jami: %d ta · %s" % (j["n"], som(j["s"])),
         "🕐 Kutilayotgan buyurtmalar: %d" % kut,
         "📦 Omborda: %d nom, %d dona" % (ombor["n"], ombor["s"])]
    if qisqa:
        return "\n".join(q)
    yosh, janr, ref = {}, {}, {}
    sorov = [{} for _ in SOROVLAR]
    for u in reg:
        yosh[u["age"]] = yosh.get(u["age"], 0) + 1
        ref[u["ref"] or "To'g'ridan-to'g'ri"] = ref.get(u["ref"] or "To'g'ridan-to'g'ri", 0) + 1
        for g in janrlar(u):
            nom = JANRLAR[g]
            janr[nom] = janr.get(nom, 0) + 1
        s = json.loads(u["survey"] or "{}")
        for i, (kalit, _, _) in enumerate(SOROVLAR):
            if s.get(kalit):
                sorov[i][s[kalit]] = sorov[i].get(s[kalit], 0) + 1
    n = len(reg)
    q += ["", "🎂 <b>Yosh</b>"] + taqsimot(yosh, n)
    q += ["", "🏷 <b>Qiziqishlar (janr)</b>"] + taqsimot(janr, n, 12)
    q += ["", "🔗 <b>Havola manbasi</b>"] + taqsimot(ref, n)
    for i, (_, savol, _) in enumerate(SOROVLAR):
        q += ["", "<b>%s</b>" % savol] + taqsimot(sorov[i], n)
    taklif = db.q("SELECT invited_by, COUNT(*) n FROM users WHERE invited_by IS NOT NULL "
                  "AND registered_at IS NOT NULL GROUP BY invited_by ORDER BY n DESC LIMIT 5")
    if taklif:
        q += ["", "👥 <b>Eng ko'p do'st taklif qilganlar</b>"]
        for r in taklif:
            u = db.user(r["invited_by"])
            q.append("  %s %s (%s) — %d" % (e(u["first_name"]), e(u["last_name"]), e(u["phone"]), r["n"]))
    q += ["", "🎁 <b>Sovg'alar qoldig'i</b>"] + ["  %s — %d" % (e(g["name"]), g["stock"]) for g in db.gifts()]
    return "\n".join(q)


def a_statistika(uid, arg):
    boloklar(uid, statistika_matn().split("\n"))


def a_buyurtmalar(uid, arg):
    rows = db.q("SELECT id FROM orders WHERE status='yangi' ORDER BY id LIMIT 20")
    if not rows:
        return tg.send(uid, "🕐 Kutilayotgan buyurtma yo'q.")
    for r in rows:
        o = db.order(r["id"])
        tg.send(uid, buyurtma_matn(o), buyurtma_kb(o))


def a_qoldiq(uid, arg):
    q = ["📦 <b>Qoldiq</b> (#ID · nomi — qoldi / sotildi · narx)", ""]
    for b in db.q("SELECT * FROM books WHERE active=1 ORDER BY stock, title"):
        q.append("#%d %s — 📦 %d / ✅ %d · %s" % (b["id"], e(b["title"]), b["stock"], b["sold"], som(b["price"])))
    boloklar(uid, q)


def a_sorovlar(uid, arg):
    sor = db.get("kitob_sorovlari", [])
    if not sor:
        return tg.send(uid, "Hozircha kitob so'rovlari yo'q.")
    sanoq = {}
    for s in sor:
        k = s["kitob"].strip().casefold()
        sanoq[k] = sanoq.get(k, 0) + 1
    boloklar(uid, ["📝 <b>Kitobxonlar so'ragan kitoblar</b> (oxirgi %d ta)" % len(sor), ""]
             + ["• %s — %d marta" % (e(k), v) for k, v in sorted(sanoq.items(), key=lambda x: -x[1])[:50]])


def a_janrlar(uid, arg):
    tg.send(uid, "🏷 <b>Janr kalitlari</b>\n\n" + "\n".join("<code>%s</code> — %s" % kv for kv in JANRLAR.items()))


def a_kitob_qosh(uid, arg):
    p = [x.strip() for x in (arg or "").split("|")]
    if len(p) < 5:
        return tg.send(uid, "Namuna: <code>/kitob_qosh Muqaddima | Ibn Xaldun | tarix | 300000 | 100</code>\n"
                            "(oxiriga <code>| tavsif</code> ham qo'shsa bo'ladi)")
    jk, narx, soni = janr_top(p[2]), raqam(p[3]), raqam(p[4])
    if not p[0] or jk is None or narx is None or soni is None:
        return tg.send(uid, "Janr, narx yoki son noto'g'ri. Janrlar: /janrlar")
    bid, yangi = db.add_book(p[0], p[1], jk, narx, soni, p[5] if len(p) > 5 else "")
    tg.send(uid, "%s #%d\n\n%s" % ("✅ Qo'shildi" if yangi else "♻️ Yangilandi", bid, kitob_matn(db.book(bid))))


def _id_va_son(uid, arg, namuna):
    p = (arg or "").split()
    b = db.book(raqam(p[0])) if p else None
    n = raqam(p[1]) if len(p) > 1 else None
    if not b or n is None:
        tg.send(uid, "Namuna: <code>%s</code> (ID — /qoldiq dan)" % namuna)
        return None, None
    return b, n


def a_narx(uid, arg):
    b, n = _id_va_son(uid, arg, "/narx 5 120000")
    if b:
        db.run("UPDATE books SET price=? WHERE id=?", n, b["id"])
        tg.send(uid, "✅ «%s» narxi: %s" % (e(b["title"]), som(n)))


def a_soni(uid, arg):
    b, n = _id_va_son(uid, arg, "/soni 5 40")
    if b:
        db.run("UPDATE books SET stock=? WHERE id=?", n, b["id"])
        tg.send(uid, "✅ «%s» qoldig'i: %d ta" % (e(b["title"]), n))


def a_ochir(uid, arg):
    b = db.book(raqam(arg))
    if not b:
        return tg.send(uid, "Namuna: <code>/ochir 5</code>")
    db.run("UPDATE books SET active=0 WHERE id=?", b["id"])
    tg.send(uid, "🗑 «%s» katalogdan olindi. Qaytarish: CSV orqali yoki /kitob_qosh bilan qayta kiriting."
            % e(b["title"]))


def a_aksiya_qoy(uid, arg):
    p = (arg or "").split()
    b = db.book(raqam(p[0])) if p else None
    narx = raqam(p[1]) if len(p) > 1 else None
    if not b or not narx:
        a = aksiya()
        joriy = ("\n\nHozirgi: «%s» — %s, %s" % (e(a["kitob"]["title"]), som(a["narx"]), sana_matn(a["sana"]))
                 if a else "")
        return tg.send(uid, "Namuna: <code>/aksiya_qoy 5 239000</code>%s" % joriy)
    sana = keyingi_juma(bugun())
    if len(p) > 2 and p[2].lower().startswith("keyin"):
        sana += timedelta(days=7)
    db.put("aksiya", {"book_id": b["id"], "narx": narx, "sana": sana.isoformat()})
    tg.send(uid, "🔥 Aksiya belgilandi: <b>%s</b>\n📅 %s, juma%s\n💰 %s → <b>%s</b> (−%d%%)\n📦 Omborda: %d ta\n\n"
                 "Haftalik xabar juma soat %d:00 da avtomatik yuboriladi. Oldindan ko'rish: /haftalik_test"
            % (e(b["title"]), sana_matn(sana), " (bugun)" if sana == bugun() else "",
               som(b["price"]), som(narx), foiz(b["price"], narx), b["stock"], AKSIYA_SOAT))


def a_aksiya_bekor(uid, arg):
    db.put("aksiya", None)
    tg.send(uid, "Aksiya bekor qilindi. Juma kuni belgilanmagan bo'lsa, bot avtomatik tanlaydi.")


def a_sotuv(uid, arg):
    p = (arg or "").split()
    b = db.book(raqam(p[0])) if p else None
    if not b:
        return tg.send(uid, "Namuna: <code>/sotuv 5</code>, <code>/sotuv 5 2</code> yoki "
                            "<code>/sotuv 5 1 +998901234567</code> (xaridor botda bo'lsa — sovg'a unga yoziladi)")
    qolgan, qty = p[1:], 1
    if qolgan and 0 < len(re.sub(r"\D", "", qolgan[0])) < 4:
        qty, qolgan = max(1, raqam(qolgan[0])), qolgan[1:]
    tel = telefon_norm(" ".join(qolgan)) if qolgan else None
    if qolgan and not tel:
        return tg.send(uid, "Telefon raqami noto'g'ri. Namuna: <code>/sotuv 5 1 +998901234567</code>")
    u = db.user_by_phone(tel) if tel else None
    o, xato = db.sell_direct(b["id"], qty, narx_bugun(b)[0], u["id"] if u else None)
    if xato:
        return tg.send(uid, "❌ " + xato)
    tg.send(uid, buyurtma_matn(o) + ("\n\n🎁 Xaridorga sovg'a bering: <b>%s</b>" % e(o["gift"]) if o["gift"] else "")
            + ("" if u or not tel else "\n\nℹ️ Bu raqam botda ro'yxatdan o'tmagan."))
    if u:
        sotildi_xabari(o)
    kam_qoldi(o)


def a_sovgalar(uid, arg):
    g = db.gifts()
    tg.send(uid, "🎁 <b>Sovg'alar</b>\n\n" + ("\n".join("%s — %d ta" % (e(x["name"]), x["stock"]) for x in g) or "—")
            + "\n\nQo'shish: <code>/sovga_qosh 🔖 Xatcho'p | 200</code>")


def a_sovga_qosh(uid, arg):
    p = [x.strip() for x in (arg or "").split("|")]
    if len(p) < 2 or not p[0] or raqam(p[1]) is None:
        return tg.send(uid, "Namuna: <code>/sovga_qosh 🔖 Xatcho'p | 200</code>")
    db.add_gift(p[0], raqam(p[1]))
    a_sovgalar(uid, "")


def a_xabar(uid, arg, rasm="", janr=None):
    if not arg:
        return tg.send(uid, "Namuna: <code>/xabar Yangi kitoblar keldi!</code>\n"
                            "Rasm bilan: rasmni <code>/xabar matn</code> izohi bilan yuboring.")
    users = db.audience(janr)
    kb = ikb([[btn("📚 Katalog", "catn")]])
    n = tarqat("Xabar" + (" (%s)" % janr if janr else ""),
               [(u["id"], e(arg), kb, rasm) for u in users])
    tg.send(uid, "📣 Navbatga qo'yildi: %d ta kitobxon. Tugagach hisobot keladi." % n)


def a_xabar_janr(uid, arg, rasm=""):
    p = (arg or "").split(maxsplit=1)
    jk = janr_top(p[0]) if p else None
    if not jk or len(p) < 2:
        return tg.send(uid, "Namuna: <code>/xabar_janr tarix Yangi tarixiy kitoblar keldi!</code>\nJanrlar: /janrlar")
    a_xabar(uid, p[1], rasm, jk)


def a_haftalik(uid, arg):
    n = haftalik_yubor()
    tg.send(uid, "📣 Haftalik xabar navbatga qo'yildi: %d ta kitobxon." % n)


def a_haftalik_test(uid, arg):
    haftalik_yubor(faqat=uid)


def a_instagram(uid, arg):
    a = aksiya()
    q = ["📚 Har juma — bitta kitob maxsus narxda! 🔥", ""]
    if a:
        b = a["kitob"]
        q += ["Bu haftaning aksiya kitobi: «%s»%s" % (b["title"], (" — " + b["author"]) if b["author"] else ""),
              "💰 %s o'rniga — %s" % (som(b["price"]), som(a["narx"])),
              "📦 Atigi %d ta qoldi!" % b["stock"], ""]
    q += ["🎁 Har bir xaridga sovg'a: xatcho'p va stikerlar",
          "🏆 Haftaning eng ko'p o'qilayotgan kitoblari va barcha kitoblar ro'yxati — botimizda",
          "", "👉 Telegram botimiz: %s" % havola("instagram"),
          "(havola bio'da)", "", "#kitob #kitobxon #mutolaa #aksiya #kitoblar"]
    tg.send(uid, "📸 <b>Instagram uchun tayyor matn</b> (nusxa olib qo'ying):\n\n<code>%s</code>\n\n"
                 "Havoladan kelganlar statistikada «Instagram» deb ko'rinadi."
            % e("\n".join(q)))


def _csv(sarlavha, qatorlar):
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(sarlavha)
    w.writerows(qatorlar)
    return f.getvalue().encode("utf-8-sig")        # Excel o'zbekcha harflarni to'g'ri ochadi


def a_eksport(uid, arg):
    kun = hozir().strftime("%Y-%m-%d")
    fmt = lambda t: datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d %H:%M") if t else ""
    xarid = {r["user_id"]: r["n"] for r in db.q("SELECT user_id, SUM(qty) n FROM orders "
                                                "WHERE status='sotildi' AND user_id IS NOT NULL GROUP BY user_id")}
    qat = []
    for u in db.q("SELECT * FROM users WHERE registered_at IS NOT NULL ORDER BY registered_at"):
        s = json.loads(u["survey"] or "{}")
        qat.append([u["id"], u["first_name"], u["last_name"], u["username"], u["age"], u["phone"],
                    ", ".join(JANRLAR[g].split(" ", 1)[1] for g in janrlar(u))]
                   + [s.get(k, "") for k, _, _ in SOROVLAR]
                   + [u["ref"], fmt(u["registered_at"]), xarid.get(u["id"], 0), "ha" if u["blocked"] else ""])
    tg.send_document(uid, "kitobxonlar-%s.csv" % kun, _csv(
        ["telegram_id", "ism", "familiya", "username", "yosh", "telefon", "janrlar"]
        + [k for k, _, _ in SOROVLAR] + ["havola", "royxatdan_otgan", "xaridlar", "bloklagan"], qat),
        "👥 Kitobxonlar: %d ta" % len(qat))
    sot = db.q("SELECT o.*, b.title, u.first_name, u.last_name, u.phone FROM orders o "
               "JOIN books b ON b.id=o.book_id LEFT JOIN users u ON u.id=o.user_id ORDER BY o.id")
    tg.send_document(uid, "sotuvlar-%s.csv" % kun, _csv(
        ["id", "kitob", "soni", "narx", "jami", "holat", "qayerda", "sovga", "xaridor", "telefon", "vaqt"],
        [[o["id"], o["title"], o["qty"], o["price"], o["qty"] * o["price"], o["status"], o["via"], o["gift"],
          ("%s %s" % (o["first_name"] or "", o["last_name"] or "")).strip(), o["phone"] or "",
          fmt(o["done_at"] or o["created_at"])] for o in sot]), "🛒 Buyurtma va sotuvlar: %d ta" % len(sot))
    tg.send_document(uid, "katalog-%s.csv" % kun, _csv(
        ["nomi", "muallif", "janr", "narx", "soni", "tavsif", "sotildi", "id"],
        [[b["title"], b["author"], b["genre"], b["price"], b["stock"], b["about"], b["sold"], b["id"]]
         for b in db.books()]),
        "📚 Katalog. Excel'da o'zgartirib, shu faylni qayta yuborsangiz — katalog yangilanadi.")


def a_zaxira(uid, arg):
    zaxira_yubor(uid)


def csv_import(uid, data):
    matn = None
    for kod in ("utf-8-sig", "cp1251"):
        try:
            matn = data.decode(kod)
            break
        except UnicodeDecodeError:
            pass
    if matn is None:
        return tg.send(uid, "Faylni o'qib bo'lmadi. CSV (UTF-8) ko'rinishida saqlang.")
    birinchi = matn.split("\n", 1)[0]
    ajrat = max(";,\t", key=birinchi.count)
    qatorlar = list(csv.reader(io.StringIO(matn), delimiter=ajrat))
    boshi = 1
    if qatorlar and qatorlar[0] and "nom" in qatorlar[0][0].casefold():
        qatorlar, boshi = qatorlar[1:], 2
    yangi = yangilandi = 0
    xatolar = []
    with db.tx():
        for i, q in enumerate(qatorlar, boshi):
            q = [x.strip() for x in q]
            if not any(q):
                continue
            if len(q) < 5:
                xatolar.append(i)
                continue
            jk, narx, soni = janr_top(q[2]), raqam(q[3]), raqam(q[4])
            if not q[0] or jk is None or narx is None or soni is None:
                xatolar.append(i)
                continue
            _, y = db.add_book(q[0], q[1], jk, narx, soni, q[5] if len(q) > 5 else "")
            yangi += y
            yangilandi += not y
    tg.send(uid, "📥 <b>Katalog yangilandi</b>\n➕ Yangi: %d\n♻️ Yangilangan: %d%s"
            % (yangi, yangilandi, ("\n⚠️ O'qilmagan qatorlar: %s\n(janr — /janrlar, narx va soni — raqam)"
                                   % ", ".join(map(str, xatolar[:30]))) if xatolar else ""))


def tikla(uid, data):
    global db
    tmp = DB_PATH + ".tiklash"
    with open(tmp, "wb") as f:
        f.write(data)
    try:
        c = sqlite3.connect(tmp)
        n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        c.execute("SELECT COUNT(*) FROM books").fetchone()
        c.close()
    except sqlite3.Error:
        os.remove(tmp)
        return tg.send(uid, "❌ Bu fayl bot bazasi emas.")
    navbat.join()                          # ommaviy xabar tugashini kutamiz
    db.close()
    os.replace(tmp, DB_PATH)
    db = Baza(DB_PATH)
    tg.send(uid, "✅ Baza tiklandi. Kitobxonlar: %d" % n)


ADMIN_BUYRUQLAR = {
    "/admin": a_admin, "/statistika": a_statistika, "/buyurtmalar": a_buyurtmalar, "/qoldiq": a_qoldiq,
    "/sorovlar": a_sorovlar, "/janrlar": a_janrlar, "/kitob_qosh": a_kitob_qosh, "/narx": a_narx,
    "/soni": a_soni, "/ochir": a_ochir, "/aksiya_qoy": a_aksiya_qoy, "/aksiya_bekor": a_aksiya_bekor,
    "/sotuv": a_sotuv, "/sovga_qoldiq": a_sovgalar, "/sovga_qosh": a_sovga_qosh, "/xabar": a_xabar,
    "/xabar_janr": a_xabar_janr, "/haftalik": a_haftalik, "/haftalik_test": a_haftalik_test,
    "/instagram": a_instagram, "/eksport": a_eksport, "/zaxira": a_zaxira,
}


def admin_fayl(uid, m, cmd, arg):
    """Admin rasm yoki fayl yubordi: /rasm, /xabar (rasm bilan), CSV katalog, /tikla."""
    if m.get("photo"):
        fid = m["photo"][-1]["file_id"]
        if cmd == "/rasm":
            b = db.book(raqam(arg))
            if not b:
                return tg.send(uid, "Izohga kitob ID sini yozing: <code>/rasm 5</code>")
            db.run("UPDATE books SET photo=? WHERE id=?", fid, b["id"])
            return kitob_yubor(uid, b["id"])
        if cmd == "/xabar":
            return a_xabar(uid, arg, fid)
        if cmd == "/xabar_janr":
            return a_xabar_janr(uid, arg, fid)
        return tg.send(uid, "Rasm izohiga <code>/rasm ID</code> yoki <code>/xabar matn</code> yozing.")
    doc = m["document"]
    nom = (doc.get("file_name") or "").lower()
    data = tg.download(doc["file_id"])
    if data is None:
        return tg.send(uid, "Faylni yuklab bo'lmadi (20 MB dan kichik bo'lsin).")
    if cmd == "/tikla":
        return tikla(uid, data)
    if nom.endswith((".csv", ".txt")):
        return csv_import(uid, data)
    tg.send(uid, "Katalog uchun <b>.csv</b> fayl yuboring (Excel → Saqlash → CSV UTF-8).\n"
                 "Baza zaxirasini tiklash uchun izohga <code>/tikla</code> yozing.")


# ================================================================ xabarlar
def xabar(m):
    if (m.get("chat") or {}).get("type") != "private":
        return
    uid = m["chat"]["id"]
    frm = m.get("from") or {}
    db.add_user(uid, frm.get("username"))
    u = db.user(uid)
    if u["blocked"] or (frm.get("username") or "") != u["username"]:
        db.upd_user(uid, blocked=0, username=frm.get("username") or "")
    matn = (m.get("text") or m.get("caption") or "").strip()
    cmd, arg = "", ""
    if matn.startswith("/"):
        p = matn.split(maxsplit=1)
        cmd, arg = p[0].split("@")[0].lower(), (p[1] if len(p) > 1 else "")

    if cmd == "/start":
        if not u["registered_at"]:
            t = tmp_ol(u)
            t.update(tg_first=frm.get("first_name") or "", tg_last=frm.get("last_name") or "")
            db.upd_user(uid, tmp=json.dumps(t, ensure_ascii=False))
            u = db.user(uid)
        return start(u, arg)
    if admin(uid):
        if m.get("photo") or m.get("document"):
            return admin_fayl(uid, m, cmd, arg)
        if cmd in ADMIN_BUYRUQLAR:
            return ADMIN_BUYRUQLAR[cmd](uid, arg)

    if not u["registered_at"]:
        if not u["step"]:
            return start(u, "")
        return royxat_matn(u, m, m.get("text") or "")
    if u["step"]:
        if matn in MENYU_TUGMALARI or cmd:           # ma'lumot yangilash to'xtatildi
            db.upd_user(uid, step=None)
        else:
            return royxat_matn(u, m, m.get("text") or "")

    if matn in BOLIMLAR:
        return BOLIMLAR[matn](uid)
    if cmd in BUYRUQLAR:
        return BUYRUQLAR[cmd](uid)
    if cmd:
        return yordam(uid)
    if m.get("text"):
        return qidir(uid, matn)
    tg.send(uid, "Kitob nomini yozing yoki pastdagi menyudan foydalaning 👇", menyu())


def yangilanish(upd):
    if upd.get("message"):
        xabar(upd["message"])
    elif upd.get("callback_query"):
        cb = upd["callback_query"]
        if cb.get("data") == "catn":                  # ommaviy xabardagi «Katalog» tugmasi
            u = db.user(cb["from"]["id"])
            tg.answer(cb["id"])
            if u and u["registered_at"]:
                tg.send(u["id"], *katalog_view())
            return
        try:
            res = tugma(cb)
        except Exception:
            tg.answer(cb["id"], "Xatolik yuz berdi, qayta urinib ko'ring", True)
            raise
        if isinstance(res, tuple):
            tg.answer(cb["id"], *res)
        else:
            tg.answer(cb["id"], res)


# ================================================================ ishga tushirish
def boshlangich_malumot():
    if db.one("SELECT COUNT(*) n FROM books")["n"] == 0:
        with open(os.path.join(HERE, "kitoblar.csv"), "rb") as f:
            csv_import_jim(f.read())
        for nom, n in BOSHLANGICH_SOVGALAR:
            db.add_gift(nom, n)
        if db.one("SELECT COUNT(*) n FROM users")["n"] == 0:
            adminlarga("ℹ️ Bot yangi (bo'sh) baza bilan ishga tushdi, namuna katalog yuklandi.\n"
                       "Agar bu kutilmagan bo'lsa — oxirgi zaxira faylini <code>/tikla</code> izohi bilan yuboring.")


def csv_import_jim(data):
    matn = data.decode("utf-8-sig")
    for q in list(csv.reader(io.StringIO(matn), delimiter=";"))[1:]:
        if len(q) >= 5 and janr_top(q[2]):
            db.add_book(q[0].strip(), q[1].strip(), janr_top(q[2]), raqam(q[3]), raqam(q[4]),
                        q[5].strip() if len(q) > 5 else "")


def sozla():
    global BOT
    BOT = (tg.call("getMe").get("result") or {}).get("username", "")
    tg.call("deleteWebhook")
    foydalanuvchi = [
        {"command": "start", "description": "Bosh menyu"},
        {"command": "aksiya", "description": "🔥 Juma aksiyasi"},
        {"command": "katalog", "description": "📚 Barcha kitoblar"},
        {"command": "top", "description": "🏆 Haftaning top kitoblari"},
        {"command": "sovgalar", "description": "🎁 Xaridlar va sovg'alar"},
        {"command": "profil", "description": "👤 Profilim"},
        {"command": "dokon", "description": "📍 Manzil va aloqa"},
    ]
    tg.call("setMyCommands", commands=foydalanuvchi)
    for a in ADMINS:
        tg.call("setMyCommands", scope={"type": "chat", "chat_id": a}, commands=foydalanuvchi + [
            {"command": "admin", "description": "🛠 Admin panel"},
            {"command": "statistika", "description": "📊 Statistika"},
            {"command": "buyurtmalar", "description": "🛒 Kutilayotgan buyurtmalar"},
            {"command": "qoldiq", "description": "📦 Qoldiq"},
            {"command": "haftalik_test", "description": "👀 Haftalik xabarni ko'rish"},
            {"command": "eksport", "description": "📥 CSV eksport"},
        ])
    tg.call("setMyDescription", description=(
        "📚 %s kitob uyi\n\n🔥 Har juma — bitta kitob maxsus aksiya narxida\n"
        "🏆 Haftaning eng ko'p sotilgan kitoblari\n📦 Har kitob: qancha sotildi, qancha qoldi\n"
        "🎁 Har xaridga — sovg'a\n\n«Start» ni bosing 👇" % DOKON))
    tg.call("setMyShortDescription", short_description=(
        "%s kitob uyi: juma aksiyalari, top kitoblar, har xaridga sovg'a 🎁" % DOKON))
    print("bot: @%s | adminlar: %s | baza: %s" % (BOT or "?", ADMINS or "yo'q", DB_PATH))


def main(argv):
    global db
    if not tg.TOKEN:
        sys.exit("BOT_TOKEN muhit o'zgaruvchisini kiriting.")
    db = Baza(DB_PATH)
    boshlangich_malumot()
    sozla()
    muddat = float(argv[argv.index("--muddat") + 1]) if "--muddat" in argv else 0
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: TOXTA.set())
    threading.Thread(target=tarqatuvchi, daemon=True).start()

    boshlandi = time.time()
    offset = None
    print("Bot ishga tushdi. Kitobxonlar:", db.one("SELECT COUNT(*) n FROM users")["n"])
    while not TOXTA.is_set() and not (muddat and time.time() - boshlandi > muddat):
        try:
            jadval()
        except Exception:
            xato_log()
        r = tg.call("getUpdates", offset=offset, timeout=25,
                    allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            if r.get("error_code") == 409:
                print("Boshqa nusxa ishlayapti — kutaman", file=sys.stderr)
            time.sleep(5)
            continue
        for upd in r.get("result", []):
            offset = upd["update_id"] + 1
            try:
                yangilanish(upd)
            except Exception:
                xato_log()
    if offset:
        tg.call("getUpdates", offset=offset, timeout=0)   # «shulargacha ko'rdim»
    print("To'xtayapman: navbatdagi ommaviy xabarlar tugashini kutaman...")
    navbat.join()
    db.close()


if __name__ == "__main__":
    main(sys.argv[1:])

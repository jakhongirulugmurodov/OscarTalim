#!/usr/bin/env python3
"""
Kitob olami — Telegram bot (kitob do'koni).

Vazifasi:
  1. Ro'yxatdan o'tish: /start → «📝 Ro'yxatdan o'tish» → ism, familiya,
     telefon, yosh, qiziqqan kitob janri.
  2. Juma aksiyasi: har juma bitta kitob tannarxidan ozgina arzonga
     (ozgina zarariga) sotiladi. Aksiyani do'kon egasi bot ichida qo'shadi.
  3. Eslatmalar (Toshkent vaqti bilan, soat ESLATMA_SOAT dan keyin):
       - do'kon egasiga — aksiyadan 4 hafta oldin (kitobni tayyorlash uchun)
         va 4 hafta keyingi juma bo'sh bo'lsa, «aksiya qo'ying» deb;
       - do'kon egasiga — mijozlarga e'lon ketishidan bir kun oldin;
       - mijozlarga — 1 hafta oldin, bir kun oldin va juma kuni ertalab.
     Mijozlar aksiyani faqat 1 hafta qolganda biladi — undan oldin bot
     hech kimga ko'rsatmaydi.

Do'kon egasi (ADMIN_IDS) uchun buyruqlar:
    ➕ Aksiya qo'shish   — sana, kitob, janr, narxlar so'raladi
    📋 Aksiyalar          — rejalashtirilgan aksiyalar, tannarx va zarar
    👥 Mijozlar           — ro'yxatdan o'tganlar
    /ochir 3              — 3-aksiyani o'chirish
    /xabar matn           — barcha mijozlarga xabar
    /men                  — o'z Telegram ID ingizni bilish

Rejimlar:
    python3 bot.py              # doimiy (server bo'lsa): long polling
    python3 bot.py --once       # GitHub Actions: xabarlar + eslatmalar
    python3 bot.py --setup      # buyruqlar va tavsif

Muhit o'zgaruvchilari:
    BOT_TOKEN      BotFather bergan token
    ADMIN_IDS      do'kon egasining Telegram ID lari, vergul bilan
    STATE_FILE     kitob.json manzili (ixtiyoriy)
    ESLATMA_SOAT   eslatmalar yuboriladigan soat, Toshkent vaqti (standart 10)
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from html import escape
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "kitob.json")
ESLATMA_SOAT = int(os.environ.get("ESLATMA_SOAT") or 10)
API = "https://api.telegram.org/bot%s/" % TOKEN
TOSHKENT = timezone(timedelta(hours=5))

EGA_OLDIN = 28          # do'kon egasi aksiyani necha kun oldin bilishi kerak
MIJOZ_OLDIN = 7         # mijozlar necha kun oldin biladi

BTN_ROYXAT = "📝 Ro'yxatdan o'tish"
BTN_AKSIYA = "🔥 Juma aksiyasi"
BTN_MEN = "👤 Ma'lumotlarim"
BTN_QAYTA = "✏️ Ma'lumotni o'zgartirish"
BTN_BEKOR = "❌ Bekor qilish"
BTN_TELEFON = "📱 Raqamimni yuborish"
BTN_QOSH = "➕ Aksiya qo'shish"
BTN_ROYXAT_AKSIYA = "📋 Aksiyalar"
BTN_MIJOZLAR = "👥 Mijozlar"
BTN_HA = "✅ Ha, saqlash"
BTN_YOQ = "❌ Yo'q"
HAMMA = "📚 Hamma uchun"

JANRLAR = [
    "💪 Motivatsion",
    "🎬 Kino asosidagi kitoblar",
    "💕 Romanlar",
    "🕌 Diniy va tarixiy",
    "🧠 Psixologiya",
    "💼 Biznes",
    "🧸 Bolalar kitoblari",
    "📖 Badiiy adabiyot",
]

OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
         "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]

SALOM = (
    "Assalomu alaykum! <b>Kitob olami</b>ga xush kelibsiz 📚\n\n"
    "Har <b>juma</b> kuni bitta kitobni tannarxidan ham arzonga sotamiz — "
    "masalan, «Muqaddima» yoki «Saodat asri qissalari».\n\n"
    "Ro'yxatdan o'ting — juma aksiyasini bir hafta oldin sizga "
    "birinchilardan bo'lib aytamiz 👇"
)
TAVSIF = ("Kitob olami — har juma bitta kitob tannarxidan arzon. "
          "Ro'yxatdan o'ting va juma aksiyasini bir hafta oldin biling.")


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


def send(chat_id, text, keyboard=None):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
                disable_web_page_preview="true", reply_markup=keyboard)


def send_long(chat_id, lines, keyboard=None):
    """Telegram bitta xabarga 4096 belgidan ko'p sig'dirmaydi — bo'lib yuboramiz."""
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) > 3800:
            send(chat_id, chunk)
            chunk = ""
        chunk += line + "\n"
    send(chat_id, chunk or "—", keyboard)


def kb(rows):
    return {"keyboard": [[b if isinstance(b, dict) else {"text": b} for b in row]
                         for row in rows],
            "resize_keyboard": True}


def menyu(chat, db):
    if not royxatda(db, chat):
        rows = [[BTN_ROYXAT], [BTN_AKSIYA]]
    else:
        rows = [[BTN_AKSIYA], [BTN_MEN, BTN_QAYTA]]
    if chat in ADMINS:
        rows += [[BTN_QOSH, BTN_ROYXAT_AKSIYA], [BTN_MIJOZLAR]]
    return kb(rows)


def ustunlar(items, n=2):
    return [items[i:i + n] for i in range(0, len(items), n)]


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    db.setdefault("promos", [])
    db.setdefault("sent", {})
    db.setdefault("seq", 0)
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def royxatda(db, chat):
    return bool(db["users"].get(chat, {}).get("royxat"))


# ---------------------------------------------------------------- yordamchilar
def bugun():
    return datetime.now(TOSHKENT).date()


def sana_matn(d):
    return "%d-%s" % (d.day, OYLAR[d.month - 1])


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def son(text):
    """«120 000», «120.000 so'm», «120000» → 120000."""
    raqam = re.sub(r"[^\d]", "", text or "")
    return int(raqam) if raqam else None


def telefon_tozala(text):
    raqam = re.sub(r"[^\d]", "", text or "")
    if len(raqam) == 9:                       # 901234567
        raqam = "998" + raqam
    if len(raqam) < 9 or len(raqam) > 15:
        return None
    return "+" + raqam


def jumalar(soni=8):
    """Bugundan keyingi jumalar (bugun juma bo'lsa, u ham kiradi)."""
    d = bugun()
    d += timedelta(days=(4 - d.weekday()) % 7)
    return [d + timedelta(weeks=i) for i in range(soni)]


def sana_oqi(text):
    text = (text or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    m = re.match(r"^(\d{1,2})[- ]([a-z']+)", text.lower())   # «2-oktabr»
    if m and m.group(2) in OYLAR:
        oy = OYLAR.index(m.group(2)) + 1
        d = bugun()
        yil = d.year + (1 if (oy, int(m.group(1))) < (d.month, d.day) else 0)
        try:
            return date(yil, oy, int(m.group(1)))
        except ValueError:
            return None
    return None


def kelgusi(db):
    """Bugundan boshlab kelgusi aksiyalar, sana bo'yicha tartiblangan."""
    b = bugun().isoformat()
    return sorted((p for p in db["promos"] if p["sana"] >= b), key=lambda p: p["sana"])


def zarar(p):
    return p["tannarx"] - p["narx"]


def aksiya_matn(p, u=None):
    """Mijozga ko'rsatiladigan aksiya matni (tannarx ko'rsatilmaydi)."""
    d = date.fromisoformat(p["sana"])
    qoldi = (d - bugun()).days
    if qoldi == 0:
        qachon = "🔥 <b>BUGUN — juma aksiyasi!</b>"
    elif qoldi == 1:
        qachon = "⏰ <b>Ertaga — juma aksiyasi!</b>"
    else:
        qachon = "📢 <b>%s, juma — aksiya</b> (%d kun qoldi)" % (sana_matn(d), qoldi)
    lines = [qachon, "", "📖 <b>%s</b>" % escape(p["kitob"])]
    if p.get("odatiy") and p["odatiy"] > p["narx"]:
        lines.append("Narxi: <s>%s</s> → <b>%s</b>" % (som(p["odatiy"]), som(p["narx"])))
    else:
        lines.append("Narxi: <b>%s</b>" % som(p["narx"]))
    lines.append("Bu narx kitobning tannarxidan ham past — faqat shu juma kuni.")
    if u and p.get("janr") and p["janr"] != HAMMA and u.get("qiziqish") == p["janr"]:
        lines.append("\n💚 Bu siz yoqtirgan janrdan: %s" % escape(p["janr"]))
    if u and u.get("ism"):
        lines.insert(0, "Hurmatli %s!\n" % escape(u["ism"]))
    return "\n".join(lines)


# ---------------------------------------------------------------- ro'yxatdan o'tish
def royxat_qadam(chat, u, msg, text, db):
    qadam = u.get("qadam")
    q = u.setdefault("vaqtincha", {})

    if qadam == "ism":
        if not text or len(text) > 50 or text.startswith("/"):
            send(chat, "Ismingizni yozing (masalan: <i>Aziz</i>).")
            return
        q["ism"] = text
        u["qadam"] = "familiya"
        send(chat, "Familiyangizni yozing:", kb([[BTN_BEKOR]]))
        return

    if qadam == "familiya":
        if not text or len(text) > 50 or text.startswith("/"):
            send(chat, "Familiyangizni yozing (masalan: <i>Karimov</i>).")
            return
        q["familiya"] = text
        u["qadam"] = "telefon"
        send(chat, "Telefon raqamingizni yuboring — pastdagi tugmani bosing "
                   "yoki yozing (masalan: <i>+998 90 123 45 67</i>):",
             kb([[{"text": BTN_TELEFON, "request_contact": True}], [BTN_BEKOR]]))
        return

    if qadam == "telefon":
        contact = msg.get("contact")
        raqam = telefon_tozala(contact["phone_number"] if contact else text)
        if not raqam:
            send(chat, "Raqam noto'g'ri. Masalan: <i>+998 90 123 45 67</i> — "
                       "yoki «%s» tugmasini bosing." % BTN_TELEFON)
            return
        q["telefon"] = raqam
        u["qadam"] = "yosh"
        send(chat, "Yoshingiz nechada?", kb([[BTN_BEKOR]]))
        return

    if qadam == "yosh":
        yosh = son(text)
        if yosh is None or not 5 <= yosh <= 100:
            send(chat, "Yoshingizni raqam bilan yozing (masalan: <i>24</i>).")
            return
        q["yosh"] = yosh
        u["qadam"] = "qiziqish"
        send(chat, "Qaysi kitoblarni yoqtirasiz? Tanlang yoki o'zingiz yozing:",
             kb(ustunlar(JANRLAR) + [[BTN_BEKOR]]))
        return

    if qadam == "qiziqish":
        if not text or len(text) > 60 or text.startswith("/"):
            send(chat, "Janrni tanlang yoki qisqacha yozing.")
            return
        q["qiziqish"] = text
        yangi = not u.get("royxat")
        u.update(q)
        u["royxat"] = u.get("royxat") or int(time.time())
        u.pop("vaqtincha", None)
        u.pop("qadam", None)
        send(chat, "✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n%s\n\n"
                   "Juma aksiyasini bir hafta oldin shu yerga yozamiz. "
                   "Botni o'chirib qo'ymang 🙂" % profil(u), menyu(chat, db))
        if yangi:
            for a in ADMINS:
                send(a, "🆕 Yangi mijoz (%d-chi):\n%s" % (
                    sum(1 for x in db["users"].values() if x.get("royxat")), profil(u)))
        return


def profil(u):
    return ("👤 %s %s\n📱 %s\n🎂 %s yosh\n📚 %s" % (
        escape(u.get("ism", "")), escape(u.get("familiya", "")),
        escape(u.get("telefon", "")), u.get("yosh", "?"),
        escape(u.get("qiziqish", ""))))


# ---------------------------------------------------------------- aksiya qo'shish (do'kon egasi)
def bosh_jumalar(db):
    band = {p["sana"] for p in db["promos"]}
    return [d for d in jumalar(10) if d.isoformat() not in band]


def aksiya_qadam(chat, u, text, db):
    qadam = u["qadam"]
    q = u.setdefault("vaqtincha", {})

    if qadam == "a_sana":
        d = sana_oqi(text.split(" ")[0].replace("📅", "").strip()) if text else None
        if not d:
            m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", text or "")
            d = date.fromisoformat(m.group(1)) if m else None
        if not d:
            send(chat, "Sanani tugmadan tanlang yoki yozing: <i>2026-10-02</i> yoki <i>02.10.2026</i>.")
            return
        if d.weekday() != 4:
            send(chat, "%s — juma emas. Juma kunini tanlang." % sana_matn(d))
            return
        if d < bugun():
            send(chat, "Bu sana o'tib ketgan.")
            return
        if any(p["sana"] == d.isoformat() for p in db["promos"]):
            send(chat, "Bu jumaga aksiya bor. Avval uni o'chiring (📋 Aksiyalar).")
            return
        q["sana"] = d.isoformat()
        u["qadam"] = "a_kitob"
        qoldi = (d - bugun()).days
        ogoh = ""
        if qoldi < EGA_OLDIN:
            ogoh = ("\n⚠️ Aksiyagacha %d kun qoldi — odatda 4 hafta oldin "
                    "rejalashtirgan ma'qul." % qoldi)
        send(chat, "📅 %s, juma.%s\n\nKitob nomini yozing (masalan: <i>Muqaddima</i>):"
             % (sana_matn(d), ogoh), kb([[BTN_BEKOR]]))
        return

    if qadam == "a_kitob":
        if not text or len(text) > 120 or text.startswith("/"):
            send(chat, "Kitob nomini yozing.")
            return
        q["kitob"] = text
        u["qadam"] = "a_janr"
        send(chat, "Kitob janri? (shu janrni yoqtirganlarga alohida belgi qo'yamiz)",
             kb([[HAMMA]] + ustunlar(JANRLAR) + [[BTN_BEKOR]]))
        return

    if qadam == "a_janr":
        if not text:
            return
        q["janr"] = text
        u["qadam"] = "a_odatiy"
        send(chat, "Kitobning <b>odatiy</b> (do'kondagi) narxi qancha? "
                   "Masalan: <i>150000</i>. Bilmasangiz «0» yozing.", kb([[BTN_BEKOR]]))
        return

    if qadam == "a_odatiy":
        n = son(text)
        if n is None:
            send(chat, "Narxni raqam bilan yozing, masalan: <i>150000</i>.")
            return
        q["odatiy"] = n
        u["qadam"] = "a_tannarx"
        send(chat, "Kitobning <b>tannarxi</b> (o'zingizga necha pulga tushadi)? "
                   "Buni mijozlar ko'rmaydi.")
        return

    if qadam == "a_tannarx":
        n = son(text)
        if not n:
            send(chat, "Tannarxni raqam bilan yozing, masalan: <i>120000</i>.")
            return
        q["tannarx"] = n
        u["qadam"] = "a_narx"
        tavsiya = int(round(n * 0.95, -3)) or n - 1
        send(chat, "Juma kuni qanchaga sotamiz? U <b>tannarxdan ozgina past</b> "
                   "bo'lishi kerak. Masalan: <i>%d</i> (tannarxdan ~5%% past)." % tavsiya)
        return

    if qadam == "a_narx":
        n = son(text)
        if not n:
            send(chat, "Narxni raqam bilan yozing.")
            return
        if n >= q["tannarx"]:
            send(chat, "Aksiya narxi tannarxdan (%s) <b>past</b> bo'lishi kerak — "
                       "juma aksiyasi ozgina zarariga qilinadi. Qaytadan yozing:"
                 % som(q["tannarx"]))
            return
        q["narx"] = n
        u["qadam"] = "a_tasdiq"
        z = q["tannarx"] - n
        foiz = 100.0 * z / q["tannarx"]
        ogoh = ("\n⚠️ Zarar %.0f%% — bu «ozgina» emas. Ishonchingiz komilmi?" % foiz
                if foiz > 15 else "")
        send(chat, "Tekshiring:\n\n📅 %s, juma\n📖 %s\n📚 %s\n"
                   "Odatiy narx: %s\nTannarx: %s\nAksiya narxi: <b>%s</b>\n"
                   "Bitta kitobdan zarar: %s (%.1f%%)%s\n\nSaqlaymizmi?"
             % (sana_matn(date.fromisoformat(q["sana"])), escape(q["kitob"]),
                escape(q["janr"]), som(q["odatiy"]) if q["odatiy"] else "—",
                som(q["tannarx"]), som(n), som(z), foiz, ogoh),
             kb([[BTN_HA, BTN_YOQ]]))
        return

    if qadam == "a_tasdiq":
        u.pop("qadam", None)
        if text != BTN_HA:
            u.pop("vaqtincha", None)
            send(chat, "Bekor qilindi.", menyu(chat, db))
            return
        db["seq"] += 1
        p = dict(q, id=db["seq"], qoshgan=chat, vaqt=int(time.time()))
        db["promos"].append(p)
        u.pop("vaqtincha", None)
        qoldi = (date.fromisoformat(p["sana"]) - bugun()).days
        if qoldi <= EGA_OLDIN:
            db["sent"]["%d:ega" % p["id"]] = int(time.time())
        mijoz_kuni = date.fromisoformat(p["sana"]) - timedelta(days=MIJOZ_OLDIN)
        if qoldi <= MIJOZ_OLDIN:
            keyin = "Mijozlarga e'lon keyingi tekshiruvda (bir necha daqiqada) yuboriladi."
        else:
            keyin = "Mijozlarga %s kuni e'lon qilinadi." % sana_matn(mijoz_kuni)
        send(chat, "✅ Aksiya #%d saqlandi.\n%s" % (p["id"], keyin), menyu(chat, db))
        return


def aksiyalar_royxati(chat, db):
    ps = kelgusi(db)
    if not ps:
        send(chat, "Rejalashtirilgan aksiya yo'q. «%s» tugmasini bosing." % BTN_QOSH,
             menyu(chat, db))
        return
    lines = ["<b>Rejalashtirilgan aksiyalar</b>\n"]
    for p in ps:
        d = date.fromisoformat(p["sana"])
        qoldi = (d - bugun()).days
        holat = ("mijozlar biladi" if qoldi <= MIJOZ_OLDIN
                 else "mijozlarga %d kundan keyin e'lon" % (qoldi - MIJOZ_OLDIN))
        lines.append("#%d · 📅 %s (%d kun) — <b>%s</b>\n   %s → %s, zarar %s/dona · %s"
                     % (p["id"], sana_matn(d), qoldi, escape(p["kitob"]),
                        som(p["tannarx"]), som(p["narx"]), som(zarar(p)), holat))
    bosh = [d for d in bosh_jumalar(db) if (d - bugun()).days <= EGA_OLDIN + 7]
    if bosh:
        lines.append("\n⚠️ Aksiyasiz jumalar: " + ", ".join(sana_matn(d) for d in bosh))
    lines.append("\nO'chirish: <code>/ochir 3</code>")
    send_long(chat, lines, menyu(chat, db))


def mijozlar(chat, db):
    us = [u for u in db["users"].values() if u.get("royxat")]
    if not us:
        send(chat, "Hali hech kim ro'yxatdan o'tmagan.", menyu(chat, db))
        return
    janr = {}
    for u in us:
        janr[u.get("qiziqish", "?")] = janr.get(u.get("qiziqish", "?"), 0) + 1
    lines = ["<b>Mijozlar: %d ta</b>" % len(us)]
    bloklagan = sum(1 for u in us if u.get("bloklagan"))
    if bloklagan:
        lines.append("(botni o'chirganlar: %d)" % bloklagan)
    lines.append("\n<b>Qiziqishlar:</b>")
    for k, v in sorted(janr.items(), key=lambda x: -x[1]):
        lines.append("  %s — %d" % (escape(k), v))
    lines.append("\n<b>Ro'yxat:</b>")
    for i, u in enumerate(sorted(us, key=lambda x: x["royxat"]), 1):
        lines.append("%d. %s %s, %s yosh, %s — %s" % (
            i, escape(u.get("ism", "")), escape(u.get("familiya", "")), u.get("yosh", "?"),
            escape(u.get("telefon", "")), escape(u.get("qiziqish", ""))))
    send_long(chat, lines, menyu(chat, db))


def hammaga(db, matn_fn):
    """Ro'yxatdan o'tgan har bir mijozga matn_fn(u) ni yuboradi."""
    yuborildi = 0
    for chat, u in db["users"].items():
        if not u.get("royxat") or u.get("bloklagan"):
            continue
        r = send(chat, matn_fn(u), menyu(chat, db))
        if r.get("ok"):
            yuborildi += 1
        elif r.get("error_code") == 403:          # botni o'chirib qo'ygan
            u["bloklagan"] = int(time.time())
        time.sleep(0.05)                           # Telegram cheklovi: ~30 xabar/soniya
    return yuborildi


# ---------------------------------------------------------------- eslatmalar
def eslatmalar(db):
    """Har ishga tushganda chaqiriladi; har eslatma faqat bir marta ketadi."""
    if datetime.now(TOSHKENT).hour < ESLATMA_SOAT:
        return
    b = bugun()
    sent = db["sent"]

    for p in kelgusi(db):
        d = date.fromisoformat(p["sana"])
        qoldi = (d - b).days
        pid = p["id"]

        # Do'kon egasi — 4 hafta oldin: kitobni tayyorlash vaqti.
        if qoldi <= EGA_OLDIN and "%d:ega" % pid not in sent:
            for a in ADMINS:
                send(a, "📦 <b>Aksiyaga %d kun qoldi</b> (%s, juma)\n\n📖 %s\n"
                        "Aksiya narxi: %s, tannarx: %s\n\n"
                        "Kitobni yetarlicha buyurtma qilib qo'ying. Mijozlarga "
                        "%s kuni e'lon qilinadi."
                     % (qoldi, sana_matn(d), escape(p["kitob"]), som(p["narx"]),
                        som(p["tannarx"]), sana_matn(d - timedelta(days=MIJOZ_OLDIN))))
            sent["%d:ega" % pid] = int(time.time())

        # Do'kon egasi — mijozlarga e'lon ketishidan bir kun oldin.
        if qoldi == MIJOZ_OLDIN + 1 and "%d:ega8" % pid not in sent:
            for a in ADMINS:
                send(a, "🔔 Ertaga mijozlarga «%s» aksiyasi e'lon qilinadi. "
                        "Kitob omborda yetarlimi?" % escape(p["kitob"]))
            sent["%d:ega8" % pid] = int(time.time())

        # Mijozlar — 7 kun, 1 kun oldin va juma kuni. Kech qo'shilgan aksiyada
        # faqat eng yaqin eslatma ketadi, oldingilari o'tkazib yuboriladi.
        if qoldi <= MIJOZ_OLDIN:
            bosqich = 0 if qoldi == 0 else 1 if qoldi == 1 else MIJOZ_OLDIN
            kalit = "%d:m%d" % (pid, bosqich)
            if kalit not in sent:
                for k in (MIJOZ_OLDIN, 1, 0):
                    if k >= bosqich:
                        sent.setdefault("%d:m%d" % (pid, k), int(time.time()))
                n = hammaga(db, lambda u, p=p: aksiya_matn(p, u))
                for a in ADMINS:
                    send(a, "📨 «%s» eslatmasi %d ta mijozga yuborildi." % (escape(p["kitob"]), n))

    # 4 hafta keyingi juma aksiyasiz bo'lsa — do'kon egasiga aytamiz.
    band = {p["sana"] for p in db["promos"]}
    for d in jumalar(6):
        qoldi = (d - b).days
        kalit = "bosh:" + d.isoformat()
        if qoldi <= EGA_OLDIN and d.isoformat() not in band and kalit not in sent:
            for a in ADMINS:
                send(a, "📅 <b>%s, juma</b> uchun aksiya hali yo'q (%d kun qoldi).\n"
                        "«%s» tugmasi bilan kitob tanlang." % (sana_matn(d), qoldi, BTN_QOSH))
            sent[kalit] = int(time.time())


# ---------------------------------------------------------------- xabarlarni qayta ishlash
def handle(msg, db):
    if msg["chat"].get("type") != "private":
        return
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {})
    u = db["users"].setdefault(chat, {"id": chat, "since": int(time.time())})
    u["username"] = user.get("username", "")
    u.pop("bloklagan", None)               # yozdi — demak botni o'chirmagan

    if text == BTN_BEKOR or text.startswith("/start") or text == "/bekor":
        u.pop("qadam", None)
        u.pop("vaqtincha", None)
        if text.startswith("/start") and royxatda(db, chat):
            send(chat, "Assalomu alaykum, %s! Juma aksiyasini bir hafta oldin "
                       "shu yerga yozamiz 📚" % escape(u.get("ism", "")), menyu(chat, db))
        elif text.startswith("/start"):
            send(chat, SALOM, menyu(chat, db))
        else:
            send(chat, "Bekor qilindi.", menyu(chat, db))
        return

    if text == "/men":
        send(chat, "Sizning Telegram ID: <code>%s</code>" % chat)
        return

    qadam = u.get("qadam")
    if qadam and qadam.startswith("a_"):
        if chat in ADMINS:
            aksiya_qadam(chat, u, text, db)
            return
        qadam = u.pop("qadam", None)
    if qadam:
        royxat_qadam(chat, u, msg, text, db)
        return

    if text in (BTN_ROYXAT, BTN_QAYTA) or text == "/royxat":
        u["qadam"] = "ism"
        u["vaqtincha"] = {}
        send(chat, "Ismingizni yozing:", kb([[BTN_BEKOR]]))
        return

    if text == BTN_MEN:
        if royxatda(db, chat):
            send(chat, profil(u), menyu(chat, db))
        else:
            send(chat, "Siz hali ro'yxatdan o'tmagansiz.", menyu(chat, db))
        return

    if text == BTN_AKSIYA or text == "/aksiya":
        yaqin = [p for p in kelgusi(db)
                 if (date.fromisoformat(p["sana"]) - bugun()).days <= MIJOZ_OLDIN]
        if yaqin:
            send(chat, aksiya_matn(yaqin[0], u), menyu(chat, db))
        else:
            send(chat, "Keyingi juma aksiyasi haqida bir hafta oldin xabar beramiz."
                       + ("" if royxatda(db, chat) else " Buning uchun ro'yxatdan o'ting 👇"),
                 menyu(chat, db))
        return

    # ---- do'kon egasi
    if chat in ADMINS:
        if text == BTN_QOSH or text == "/qosh":
            u["qadam"] = "a_sana"
            u["vaqtincha"] = {}
            tugmalar = ["📅 %s (%s)" % (sana_matn(d), d.isoformat()) for d in bosh_jumalar(db)[:8]]
            send(chat, "Qaysi juma? Tanlang yoki yozing (<i>2026-10-02</i>):",
                 kb(ustunlar(tugmalar) + [[BTN_BEKOR]]))
            return
        if text == BTN_ROYXAT_AKSIYA or text == "/aksiyalar":
            aksiyalar_royxati(chat, db)
            return
        if text == BTN_MIJOZLAR or text == "/mijozlar":
            mijozlar(chat, db)
            return
        if text.startswith("/ochir"):
            n = son(text)
            p = next((p for p in db["promos"] if p["id"] == n), None)
            if not p:
                send(chat, "Aksiya topilmadi. Raqamini «📋 Aksiyalar»dan oling: "
                           "<code>/ochir 3</code>")
                return
            db["promos"].remove(p)
            send(chat, "🗑 #%d «%s» o'chirildi." % (p["id"], escape(p["kitob"])),
                 menyu(chat, db))
            return
        if text.startswith("/xabar"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                send(chat, "Foydalanish: <code>/xabar Yangi kitoblar keldi!</code>")
                return
            body = escape(parts[1])
            send(chat, "Yuborildi: %d ta" % hammaga(db, lambda u: body))
            return

    send(chat, "Pastdagi tugmalardan foydalaning 👇", menyu(chat, db))


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        msg = upd.get("message") or upd.get("edited_message")
        if msg:
            try:
                handle(msg, db)
            except Exception as e:                      # bitta xato botni to'xtatmasin
                print("xato:", repr(e), file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Boshlash"},
        {"command": "royxat", "description": "Ro'yxatdan o'tish"},
        {"command": "aksiya", "description": "Juma aksiyasi"},
        {"command": "men", "description": "Mening Telegram ID im"},
    ])
    r2 = call("setMyDescription", description=TAVSIF)
    r3 = call("setMyShortDescription", short_description="Har juma bitta kitob tannarxidan arzon")
    r4 = call("setChatMenuButton", menu_button={"type": "commands"})
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("buyruqlar:", r1.get("ok"), "| tavsif:", r2.get("ok"), r3.get("ok"),
          "| menyu:", r4.get("ok"))
    if not ADMINS:
        print("ogohlantirish: ADMIN_IDS bo'sh — do'kon egasi eslatma olmaydi.")
    return all(x.get("ok") for x in (r1, r2, r3, r4))


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        eslatmalar(db)
        save(db)
        print("qayta ishlandi: %d ta, mijozlar: %d, aksiyalar: %d" % (
            len(r.get("result", [])),
            sum(1 for u in db["users"].values() if u.get("royxat")), len(kelgusi(db))))
        return

    setup()
    offset = 0
    print("Kitob olami boti ishga tushdi.")
    while True:
        r = call("getUpdates", offset=offset, timeout=50, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
        eslatmalar(db)
        save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""
Juma aksiyasi — kitob do'koni uchun Telegram bot.

Vazifasi:
  1. Mijozni ro'yxatga oladi: ism, familiya, telefon, qiziqqan janrlari.
  2. Admin har hafta juma aksiyasidagi kitobni (rasm + matn) kiritadi —
     bot uni ro'yxatdagi hammaga bir hafta oldin yuboradi.
  3. Payshanba kechqurun "ertaga" va juma ertalab "bugun" deb o'zi eslatadi.
  4. Mijoz "🛒 Band qilish" tugmasini bosadi — adminga ismi va telefoni
     keladi; kitoblar soni (SONI) tugasa, band qilish yopiladi.
  5. Admin istalgan payt ro'yxatni CSV fayl qilib oladi.

Instagram va Telegram kanaldan kelganlarni ajratish uchun havolaga belgi
qo'shing: t.me/<bot>?start=insta, t.me/<bot>?start=tg — /statistika da
qayerdan qancha odam kelgani ko'rinadi.

Rejimlar:
    python3 bot.py                  # doimiy (server bo'lsa)
    python3 bot.py --muddat 3300    # shuncha soniya ishlab, to'xtaydi
                                    #   (GitHub Actions uchun)

Muhit o'zgaruvchilari:
    BOT_TOKEN     BotFather bergan token
    ADMIN_IDS     adminlarning Telegram ID lari, vergul bilan
    STATE_FILE    ma'lumotlar fayli (ixtiyoriy, standart: kitob_bot/data.json)
    NARX_ESKI     asl narx, so'm (standart 300000)
    NARX_YANGI    aksiya narxi, so'm (standart 239000)
    SONI          aksiyadagi kitoblar soni (standart 100)

Admin buyruqlari:
    /aksiya [YYYY-MM-DD]  keyingi juma aksiyasini kiritish (rasm + matn)
    /eslatma <matn>       ro'yxatdagi hammaga xabar
    /royxat               mijozlar ro'yxati (CSV)
    /statistika           janrlar, manbalar, bandlar soni
"""

import csv
import html
import io
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data.json")
NARX_ESKI = int(os.environ.get("NARX_ESKI") or 300000)
NARX_YANGI = int(os.environ.get("NARX_YANGI") or 239000)
SONI = int(os.environ.get("SONI") or 100)
API = "https://api.telegram.org/bot%s/" % TOKEN
TOSHKENT = timezone(timedelta(hours=5))

JANRLAR = [
    "Diniy-ma'rifiy", "Tarix", "Falsafa", "Badiiy adabiyot",
    "Jahon klassikasi", "Shaxsiy rivojlanish", "Psixologiya",
    "Biznes va moliya", "Bolalar adabiyoti", "Ilmiy-ommabop",
]

BTN_AKSIYA = "📚 Shu juma aksiyasi"
BTN_TAHRIR = "✏️ Ma'lumotlarimni o'zgartirish"
BTN_TEL = "📱 Raqamni yuborish"


def som(n):
    return "{:,}".format(n).replace(",", " ")


SALOM = (
    "Assalomu alaykum! 📚\n\n"
    "Har <b>juma</b> kuni bitta kitobni <b>zarariga</b> sotamiz:\n"
    "<s>%s so'm</s> o'rniga <b>%s so'm</b>, atigi <b>%d dona</b>.\n\n"
    "Qaysi kitob aksiyada bo'lishini ro'yxatdan o'tganlarga "
    "<b>bir hafta oldin</b> aytamiz — kitob tugab qolmasidan band qilib "
    "ulgurasiz.\n\n"
    "Ro'yxatdan o'tish 30 soniya oladi. Ismingizni yozing:"
) % (som(NARX_ESKI), som(NARX_YANGI), SONI)
TAVSIF = ("Har juma bitta kitob %s so'm o'rniga %s so'm. Qaysi kitob "
          "bo'lishini bir hafta oldin shu bot orqali bilasiz."
          % (som(NARX_ESKI), som(NARX_YANGI)))


# ---------------------------------------------------------------- Telegram API
def call(method, files=None, **params):
    fields = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
              for k, v in params.items() if v is not None}
    if files:                                   # multipart: fayl yuborish
        chegara = uuid.uuid4().hex
        qism = []
        for k, v in fields.items():
            qism.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                         % (chegara, k, v)).encode())
        for k, (nomi, data) in files.items():
            qism.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                         'Content-Type: application/octet-stream\r\n\r\n'
                         % (chegara, k, nomi)).encode() + data + b"\r\n")
        qism.append(("--%s--\r\n" % chegara).encode())
        req = Request(API + method, data=b"".join(qism),
                      headers={"Content-Type": "multipart/form-data; boundary=" + chegara})
    else:
        req = Request(API + method, data=urlencode(fields).encode())
    try:
        with urlopen(req, timeout=70) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            body = json.load(e)
        except ValueError:
            body = {"description": str(e), "error_code": e.code}
        print("telegram xatosi:", method, body.get("description"), file=sys.stderr)
        return {"ok": False, **body}
    except (URLError, OSError) as e:
        print("tarmoq xatosi:", e, file=sys.stderr)
        return {"ok": False}


def send(chat_id, text, keyboard=None):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
                reply_markup=keyboard, disable_web_page_preview=True)


def menyu():
    return {"keyboard": [[{"text": BTN_AKSIYA}], [{"text": BTN_TAHRIR}]],
            "resize_keyboard": True}


YOPIQ = {"remove_keyboard": True}


def janr_tugmalari(tanlangan):
    rows, row = [], []
    for i, j in enumerate(JANRLAR):
        row.append({"text": ("✅ " if j in tanlangan else "") + j, "callback_data": "j:%d" % i})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "Tayyor ➡️", "callback_data": "j:ok"}])
    return {"inline_keyboard": rows}


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    db.setdefault("aksiya", None)
    db.setdefault("qoralama", None)
    db.setdefault("navbat", [])
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- vaqt
def hozir():
    return datetime.now(TOSHKENT)


def keyingi_juma():
    bugun = hozir().date()
    kun = (4 - bugun.weekday()) % 7 or 7        # 4 = juma; bugun juma bo'lsa — keyingisi
    return (bugun + timedelta(days=kun)).isoformat()


def sana_matn(iso):
    oylar = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
             "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
    d = datetime.strptime(iso, "%Y-%m-%d")
    return "%d-%s" % (d.day, oylar[d.month - 1])


# ---------------------------------------------------------------- aksiya
def aksiya_matni(a, sarlavha):
    qoldi = max(0, SONI - len(a.get("bandlar", [])))
    return (
        "%s\n\n%s\n\n"
        "💰 <s>%s so'm</s> → <b>%s so'm</b>\n"
        "📅 Juma, %s\n"
        "📦 Jami %d dona, qoldi: <b>%d</b>"
    ) % (sarlavha, html.escape(a["matn"]), som(NARX_ESKI), som(NARX_YANGI),
         sana_matn(a["sana"]), SONI, qoldi)


SARLAVHA = {
    "elon": "📢 <b>Keyingi juma aksiyasi!</b>",
    "ertaga": "⏰ <b>Ertaga — juma aksiyasi!</b>",
    "bugun": "🔥 <b>Bugun — juma aksiyasi!</b>",
    "korish": "📚 <b>Juma aksiyasi</b>",
}


def aksiya_yubor(chat, a, tur):
    matn = aksiya_matni(a, SARLAVHA[tur])
    tugma = {"inline_keyboard": [[{"text": "🛒 Band qilish", "callback_data": "band"}]]}
    if a.get("rasm"):
        return call("sendPhoto", chat_id=chat, photo=a["rasm"], caption=matn,
                    parse_mode="HTML", reply_markup=tugma)
    return send(chat, matn, tugma)


def faol_aksiya(db):
    a = db.get("aksiya")
    if a and a["sana"] >= hozir().date().isoformat():
        return a
    return None


def navbatga(db, tur, matn=None):
    """Ro'yxatdan o'tgan hammaga yuboriladigan xabarni navbatga qo'yadi.
    Navbat bosqichma-bosqich yuboriladi — bot shu payt ham javob beradi."""
    odamlar = [c for c, u in db["users"].items()
               if u.get("tayyor") and not u.get("bloklagan")]
    if odamlar:
        db["navbat"].append({"tur": tur, "matn": matn, "kimga": odamlar})
    return len(odamlar)


def navbatni_yubor(db, necha=20):
    """Navbatdan bir nechta xabar yuboradi. Qolgani bor-yo'qligini qaytaradi."""
    while db["navbat"] and necha > 0:
        ish = db["navbat"][0]
        if not ish["kimga"]:
            db["navbat"].pop(0)
            continue
        chat = ish["kimga"][0]
        if ish["tur"] == "matn":
            r = send(chat, ish["matn"])
        else:
            a = db.get("aksiya")
            r = aksiya_yubor(chat, a, ish["tur"]) if a else {"ok": True}
        if r.get("error_code") == 429:           # juda tez — Telegram kutishni so'radi
            time.sleep((r.get("parameters") or {}).get("retry_after", 5))
            return True
        if r.get("error_code") in (400, 403) and chat in db["users"]:
            db["users"][chat]["bloklagan"] = True
        ish["kimga"].pop(0)
        necha -= 1
        time.sleep(0.04)                          # ~25 xabar/soniya
    return bool(db["navbat"])


def eslatmalar(db):
    """Payshanba 19:00 — "ertaga", juma 09:00 — "bugun" (Toshkent vaqti)."""
    a = db.get("aksiya")
    if not a:
        return
    t = hozir()
    ertaga = (t.date() + timedelta(days=1)).isoformat()
    if a["sana"] == ertaga and t.hour >= 19 and not a.get("ertaga"):
        a["ertaga"] = True
        navbatga(db, "ertaga")
    if a["sana"] == t.date().isoformat() and t.hour >= 9 and not a.get("bugun"):
        a["bugun"] = True
        navbatga(db, "bugun")


# ---------------------------------------------------------------- ro'yxat
def telefon(matn):
    raqam = "".join(ch for ch in matn if ch.isdigit())
    if len(raqam) == 9:
        raqam = "998" + raqam
    if len(raqam) != 12 or not raqam.startswith("998"):
        return None
    return "+" + raqam


def keyingi_qadam(chat, u):
    q = u.get("qadam")
    if q == "ism":
        send(chat, "Ismingizni yozing:", YOPIQ)
    elif q == "familiya":
        send(chat, "Familiyangizni yozing:")
    elif q == "tel":
        send(chat, "Telefon raqamingizni yuboring — pastdagi tugmani bosing "
                   "yoki yozing (masalan, 90 123 45 67):",
             {"keyboard": [[{"text": BTN_TEL, "request_contact": True}]],
              "resize_keyboard": True, "one_time_keyboard": True})
    elif q == "janr":
        send(chat, "Rahmat! Endi qaysi janrdagi kitoblar sizga qiziq? "
                   "Bir nechtasini tanlashingiz mumkin:", YOPIQ)
        send(chat, "👇 Tanlang, keyin <b>Tayyor</b> ni bosing",
             janr_tugmalari(u.get("janr", [])))


def royxat_tugadi(db, chat, u):
    u["qadam"] = None
    yangi = not u.get("tayyor")
    u["tayyor"] = True
    u.setdefault("sana", hozir().strftime("%Y-%m-%d %H:%M"))
    send(chat, "✅ <b>Ro'yxatdan o'tdingiz!</b>\n\n"
               "👤 %s %s\n📱 %s\n📖 %s\n\n"
               "Har hafta juma aksiyasidagi kitobni sizga bir hafta oldin "
               "shu yerda yuboramiz. Bildirishnomalarni yoqib qo'ying 🔔"
         % (html.escape(u["ism"]), html.escape(u["familiya"]), u["tel"],
            html.escape(", ".join(u.get("janr") or ["—"]))), menyu())
    a = faol_aksiya(db)
    if yangi and a:
        aksiya_yubor(chat, a, "korish")


def handle(msg, db):
    chat = str(msg["chat"]["id"])
    if msg["chat"].get("type") != "private":
        return
    text = (msg.get("text") or msg.get("caption") or "").strip()
    frm = msg.get("from", {})
    admin = chat in ADMINS
    users = db["users"]

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        u = users.setdefault(chat, {"id": chat})
        u["username"] = frm.get("username", "")
        u.pop("bloklagan", None)
        if len(parts) > 1 and not u.get("manba"):
            u["manba"] = parts[1].strip()[:32]
        if u.get("tayyor"):
            send(chat, "Siz ro'yxatdasiz ✅", menyu())
            a = faol_aksiya(db)
            if a:
                aksiya_yubor(chat, a, "korish")
            return
        u["qadam"] = "ism"
        send(chat, SALOM, YOPIQ)
        return

    if text.startswith("/men"):
        send(chat, "Sizning Telegram ID: <code>%s</code>" % chat)
        return

    # ---------------- admin
    if admin and admin_buyruq(msg, text, chat, db):
        return

    u = users.get(chat)
    if u is None:
        u = users[chat] = {"id": chat, "username": frm.get("username", ""), "qadam": "ism"}
        send(chat, SALOM, YOPIQ)
        return

    if text == BTN_TAHRIR or text.startswith("/tahrir"):
        u["qadam"] = "ism"
        keyingi_qadam(chat, u)
        return

    q = u.get("qadam")
    if q == "ism" or q == "familiya":
        if not text or text.startswith("/") or len(text) > 40:
            send(chat, "Iltimos, matn qilib yozing (40 harfgacha).")
            return
        u[q] = text
        u["qadam"] = "familiya" if q == "ism" else "tel"
        keyingi_qadam(chat, u)
        return
    if q == "tel":
        c = msg.get("contact")
        raqam = telefon(c["phone_number"] if c else text)
        if not raqam:
            send(chat, "Raqam noto'g'ri ko'rinadi. Masalan: <b>90 123 45 67</b> "
                       "yoki <b>+998 90 123 45 67</b>")
            return
        u["tel"] = raqam
        u["qadam"] = "janr"
        keyingi_qadam(chat, u)
        return
    if q == "janr":
        send(chat, "Janrlarni yuqoridagi tugmalardan tanlang va <b>Tayyor</b> ni bosing 👆")
        return

    if text == BTN_AKSIYA or text.startswith("/aksiya"):
        a = faol_aksiya(db)
        if a:
            aksiya_yubor(chat, a, "korish")
        else:
            send(chat, "Keyingi juma aksiyasi hali e'lon qilinmadi. "
                       "E'lon qilishimiz bilan shu yerga yuboramiz 🔔", menyu())
        return

    send(chat, "Pastdagi tugmalardan foydalaning 👇", menyu())


def admin_buyruq(msg, text, chat, db):
    """Admin xabari bo'lsa, qayta ishlab True qaytaradi."""
    users = db["users"]
    q = db.get("qoralama")

    if q and q.get("admin") == chat and q.get("kutish"):
        if text.startswith("/bekor"):
            db["qoralama"] = None
            send(chat, "Bekor qilindi.")
            return True
        if not text.startswith("/"):
            rasm = msg["photo"][-1]["file_id"] if msg.get("photo") else None
            if not text:
                send(chat, "Kitob haqida matn ham kerak (rasm tagiga yozing).")
                return True
            if rasm and len(aksiya_matni({"matn": text, "sana": q["sana"]}, SARLAVHA["ertaga"])) > 1024:
                send(chat, "Rasm tagidagi matn juda uzun — qisqartiring (taxminan 800 belgigacha).")
                return True
            q.update(kutish=False, matn=text, rasm=rasm)
            aksiya_yubor(chat, q, "elon")
            n = sum(1 for u in users.values() if u.get("tayyor") and not u.get("bloklagan"))
            send(chat, "Yuqoridagidek ko'rinadi. <b>%d</b> kishiga yuboraymi?" % n,
                 {"inline_keyboard": [[{"text": "📣 Hammaga yuborish", "callback_data": "a:ha"},
                                       {"text": "❌ Bekor", "callback_data": "a:yoq"}]]})
            return True

    if text.startswith("/aksiya"):
        parts = text.split()
        sana = keyingi_juma()
        if len(parts) > 1:
            try:
                sana = datetime.strptime(parts[1], "%Y-%m-%d").date().isoformat()
            except ValueError:
                send(chat, "Sana formati: <code>/aksiya 2026-10-02</code>")
                return True
        db["qoralama"] = {"admin": chat, "sana": sana, "kutish": True}
        send(chat, "Juma, <b>%s</b> aksiyasi.\n\nKitob <b>rasmini</b> yuboring, tagiga "
                   "nomi va qisqacha tavsifini yozing (yoki faqat matn). "
                   "Narx va sana o'zi qo'shiladi.\n\nBekor qilish: /bekor"
             % sana_matn(sana), YOPIQ)
        return True

    if text.startswith("/eslatma"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Foydalanish: <code>/eslatma Matn</code>")
            return True
        n = navbatga(db, "matn", html.escape(parts[1]))
        send(chat, "Navbatga qo'yildi: %d kishi. Asta-sekin yuboriladi." % n)
        return True

    if text.startswith("/royxat"):
        buf = io.StringIO()
        w = csv.writer(buf)
        a = db.get("aksiya") or {}
        bandlar = set(a.get("bandlar", []))
        w.writerow(["Ism", "Familiya", "Telefon", "Janrlar", "Username",
                    "Manba", "Sana", "Band qilgan", "Botni bloklagan"])
        for u in users.values():
            if not u.get("tayyor"):
                continue
            w.writerow([u.get("ism", ""), u.get("familiya", ""), u.get("tel", ""),
                        "; ".join(u.get("janr", [])),
                        ("@" + u["username"]) if u.get("username") else "",
                        u.get("manba", ""), u.get("sana", ""),
                        "ha" if u["id"] in bandlar else "",
                        "ha" if u.get("bloklagan") else ""])
        nomi = "mijozlar_%s.csv" % hozir().strftime("%Y-%m-%d")
        # ﻿ — Excel o'zbekcha harflarni to'g'ri ochishi uchun
        call("sendDocument", chat_id=chat,
             files={"document": (nomi, ("﻿" + buf.getvalue()).encode("utf-8"))})
        return True

    if text.startswith("/statistika"):
        tayyor = [u for u in users.values() if u.get("tayyor")]
        janr, manba = {}, {}
        for u in tayyor:
            for j in u.get("janr", []):
                janr[j] = janr.get(j, 0) + 1
            m = u.get("manba") or "belgisiz"
            manba[m] = manba.get(m, 0) + 1
        a = faol_aksiya(db)
        qator = ["<b>Ro'yxatdan o'tgan:</b> %d (boshlab tashlagan: %d)"
                 % (len(tayyor), len(users) - len(tayyor)),
                 "<b>Botni bloklagan:</b> %d" % sum(1 for u in tayyor if u.get("bloklagan")),
                 "", "<b>Janrlar:</b>"]
        qator += ["%s — %d" % (k, v) for k, v in sorted(janr.items(), key=lambda x: -x[1])]
        qator += ["", "<b>Qayerdan kelgan:</b>"]
        qator += ["%s — %d" % (html.escape(k), v) for k, v in sorted(manba.items(), key=lambda x: -x[1])]
        if a:
            qator += ["", "<b>Aksiya (%s):</b> band qilingan %d / %d"
                      % (sana_matn(a["sana"]), len(a.get("bandlar", [])), SONI)]
        if db["navbat"]:
            qator += ["", "Yuborilmoqda: yana %d ta xabar" % sum(len(i["kimga"]) for i in db["navbat"])]
        send(chat, "\n".join(qator))
        return True

    return False


def handle_callback(cb, db):
    chat = str(cb["from"]["id"])
    data = cb.get("data", "")
    m = cb.get("message") or {}
    u = db["users"].get(chat)
    javob = None

    if data.startswith("j:") and u and u.get("qadam") == "janr":
        if data == "j:ok":
            if not u.get("janr"):
                javob = "Kamida bitta janr tanlang"
            else:
                call("editMessageReplyMarkup", chat_id=chat, message_id=m.get("message_id"),
                     reply_markup={"inline_keyboard": []})
                royxat_tugadi(db, chat, u)
        else:
            j = JANRLAR[int(data[2:])]
            tanlangan = u.setdefault("janr", [])
            tanlangan.remove(j) if j in tanlangan else tanlangan.append(j)
            call("editMessageReplyMarkup", chat_id=chat, message_id=m.get("message_id"),
                 reply_markup=janr_tugmalari(tanlangan))

    elif data == "band":
        a = faol_aksiya(db)
        if not u or not u.get("tayyor"):
            javob = "Avval ro'yxatdan o'ting: /start"
        elif not a:
            javob = "Bu aksiya tugagan. Keyingisini kuting 🔔"
        elif chat in a.setdefault("bandlar", []):
            javob = "Siz allaqachon band qilgansiz ✅"
        elif len(a["bandlar"]) >= SONI:
            javob = "Afsus, %d ta kitobning hammasi band qilindi 😔" % SONI
        else:
            a["bandlar"].append(chat)
            send(chat, "✅ <b>Band qilindi!</b> Sizning navbatingiz: %d.\n"
                       "Juma kuni operatorimiz <b>%s</b> raqamiga qo'ng'iroq qiladi."
                 % (len(a["bandlar"]), u["tel"]))
            for ad in ADMINS:
                send(ad, "🛒 Band #%d: %s %s, %s%s"
                     % (len(a["bandlar"]), html.escape(u.get("ism", "")),
                        html.escape(u.get("familiya", "")), u["tel"],
                        (" @" + u["username"]) if u.get("username") else ""))

    elif data.startswith("a:") and chat in ADMINS:
        q = db.get("qoralama")
        call("editMessageReplyMarkup", chat_id=chat, message_id=m.get("message_id"),
             reply_markup={"inline_keyboard": []})
        if data == "a:ha" and q and not q.get("kutish"):
            bugun = hozir().date()
            sana = datetime.strptime(q["sana"], "%Y-%m-%d").date()
            db["aksiya"] = {"sana": q["sana"], "matn": q["matn"], "rasm": q.get("rasm"),
                            "bandlar": [],
                            # juda yaqin bo'lsa, ortiqcha eslatma yubormaymiz
                            "ertaga": (sana - bugun).days <= 1,
                            "bugun": sana == bugun}
            db["qoralama"] = None
            n = navbatga(db, "elon")
            send(chat, "📣 Aksiya saqlandi va %d kishiga yuborilmoqda.\n"
                       "Payshanba 19:00 va juma 09:00 da o'zim eslataman." % n, menyu())
        else:
            db["qoralama"] = None
            send(chat, "Bekor qilindi.", menyu())

    call("answerCallbackQuery", callback_query_id=cb["id"], text=javob)


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        try:
            if upd.get("callback_query"):
                handle_callback(upd["callback_query"], db)
            elif upd.get("message"):
                handle(upd["message"], db)
        except Exception as e:                      # bitta xato botni to'xtatmasin
            print("xato:", repr(e), file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Ro'yxatdan o'tish"},
        {"command": "aksiya", "description": "Shu juma aksiyasi"},
        {"command": "tahrir", "description": "Ma'lumotlarimni o'zgartirish"},
    ])
    for ad in ADMINS:
        call("setMyCommands", scope={"type": "chat", "chat_id": int(ad)}, commands=[
            {"command": "aksiya", "description": "Juma aksiyasini kiritish"},
            {"command": "eslatma", "description": "Hammaga xabar"},
            {"command": "royxat", "description": "Mijozlar ro'yxati (CSV)"},
            {"command": "statistika", "description": "Statistika"},
            {"command": "bekor", "description": "Bekor qilish"},
        ])
    r2 = call("setMyDescription", description=TAVSIF)
    r3 = call("setMyShortDescription", short_description=TAVSIF[:120])
    me = call("getMe").get("result", {})
    print("bot: @%s | buyruqlar: %s | tavsif: %s" % (me.get("username", "?"), r1.get("ok"),
                                                     r2.get("ok") and r3.get("ok")))


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    if not ADMINS:
        print("Diqqat: ADMIN_IDS berilmagan — /aksiya ishlamaydi.", file=sys.stderr)
    muddat = None
    if "--muddat" in argv:
        muddat = time.time() + int(argv[argv.index("--muddat") + 1])

    db = load()
    setup()
    offset = db.get("offset", 0)
    saqlangan = time.time()
    print("Bot ishga tushdi. Mijozlar:", sum(1 for u in db["users"].values() if u.get("tayyor")))
    while muddat is None or time.time() < muddat:
        eslatmalar(db)
        band = navbatni_yubor(db)
        kutish = 0 if band else 25
        if muddat is not None:
            kutish = max(0, min(kutish, int(muddat - time.time())))
        r = call("getUpdates", offset=offset, timeout=kutish,
                 allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            time.sleep(3)
            continue
        last = process(r.get("result", []), db)
        if last is not None:
            offset = db["offset"] = last + 1
        if last is not None or time.time() - saqlangan > 60:
            save(db)
            saqlangan = time.time()
    # Telegram'ga "shulargacha o'qidim" deb tasdiqlab chiqamiz
    call("getUpdates", offset=offset, timeout=0)
    save(db)
    print("To'xtadi. Mijozlar:", sum(1 for u in db["users"].values() if u.get("tayyor")))


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""
AI Kutubxona — Telegram bot.

Vazifasi uchta:
  1. Mini App'ga kirish nuqtasi (/start -> tugma -> dastur ochiladi)
  2. Kutubxonachi eslatmasi — /eslatma buyrug'i (GitHub Actions'dan ham)
  3. Muddat eslatmasi — kitobni o'qish muddati tugagan foydalanuvchilarga
     avtomatik xabar yuboradi ("SMS" o'rniga Telegram xabari)

Ro'yxatdan o'tish va kitob olish bot ichida emas, Mini App ichida bo'ladi —
u yerda ism, telefon va Face ID bor, ma'lumot to'g'ridan-to'g'ri Firebase'ga
yoziladi. Bot faqat chat_id larni saqlaydi (kutubxonachi e'loni uchun) va
Firestore'dagi ochiq "libReminders" navbatini o'qib, muddati o'tganlarga xabar beradi.

Muddat eslatmasi Firestore REST API orqali, HECH QANDAY kalit yoki hisobsiz
o'qiladi — buning uchun firestore.rules'da libReminders o'qish uchun ochiq
qilib qo'yilgan (faqat kitob nomi va muddat, ism/telefon YO'Q). Xabar
yuborilgach, faqat "reminded" maydoni true qilib qo'yiladi (buni ham hamma
qila oladi — qoidalarda shunga ruxsat berilgan, cheklangan yozuv).

Rejimlar:
    python3 kutubxona_bot.py                # doimiy (server bo'lsa): long polling
    python3 kutubxona_bot.py --once         # GitHub Actions: kelgan xabarlarga javob
    python3 kutubxona_bot.py --tekshir      # muddati o'tgan kitoblarga eslatma
    python3 kutubxona_bot.py --setup        # menyu tugmasi, buyruqlar, tavsif
    python3 kutubxona_bot.py --broadcast "matn"   # hammaga e'lon

Muhit o'zgaruvchilari:
    BOT_TOKEN      BotFather bergan token
    APP_URL        https://<foydalanuvchi>.github.io/OscarTalim/kutubxona/
    ADMIN_IDS      kutubxonachining Telegram ID lari, vergul bilan (ixtiyoriy)
    STATE_FILE     users.json manzili (ixtiyoriy)
    FIREBASE_PROJECT   Firestore loyiha ID si (standart: oscartalim-sinf-80da0)
"""

import json
import os
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
APP_URL = os.environ.get("APP_URL", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "kutubxona_users.json")
PROJECT = os.environ.get("FIREBASE_PROJECT", "oscartalim-sinf-80da0").strip()
API = "https://api.telegram.org/bot%s/" % TOKEN
FS = "https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents" % PROJECT

SALOM = (
    "Salom! Bu — *AI Kutubxona* boti.\n\n"
    "Pastdagi tugmani bos:\n"
    "• ismingni va telefon raqamingni yozasan\n"
    "• Face ID / barmoq izi bilan tasdiqlaysan\n"
    "• kitoblarni tanlab o'qishni boshlaysan\n\n"
    "Kitobni o'qish muddati tugasa — shu botdan eslatma keladi."
)
TAVSIF = ("AI Kutubxona — PDF kitoblar, bir necha tilda (o'zbek, rus, ingliz, nemis, "
          "xitoy, arab). O'qish tezligi bo'yicha reyting bor.")


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
    return call("sendMessage", chat_id=chat_id, text=text,
                parse_mode="Markdown", reply_markup=keyboard)


def app_button(text="📚 Kutubxonani ochish"):
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": APP_URL}}]]}


# ---------------------------------------------------------------- saqlash (chat ro'yxati)
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- buyruqlar
def broadcast(db, body):
    sent = 0
    for uid in db:
        if send(uid, body, app_button()).get("ok"):
            sent += 1
        time.sleep(0.05)          # Telegram cheklovi: ~30 xabar/soniya
    return sent


def handle(msg, db):
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {})
    if msg["chat"].get("type") != "private":
        return                    # guruhlarda javob bermaymiz

    if text.startswith("/start"):
        db[chat] = {
            "id": chat,
            "name": ((user.get("first_name") or "") + " " + (user.get("last_name") or "")).strip(),
            "username": user.get("username", ""),
            "since": db.get(chat, {}).get("since", int(time.time())),
        }
        send(chat, SALOM, app_button())
        return

    if text.startswith("/men"):
        send(chat, "Sizning Telegram ID: `%s`" % chat)
        return

    if text.startswith("/eslatma"):
        if chat not in ADMINS:
            send(chat, "Bu buyruq faqat kutubxonachi uchun.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Foydalanish: `/eslatma Yangi kitoblar qo'shildi!`")
            return
        send(chat, "Yuborildi: %d ta" % broadcast(db, parts[1]))
        return

    if text.startswith("/kim"):
        if chat not in ADMINS:
            return
        lines = ["%s (@%s)" % (u.get("name", "?"), u.get("username") or "-") for u in db.values()]
        send(chat, "Botga yozilganlar (%d):\n%s" % (len(lines), "\n".join(lines) or "-"))
        return

    send(chat, "Dasturni ochish uchun tugmani bos 👇", app_button())


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        msg = upd.get("message") or upd.get("edited_message")
        if msg:
            try:
                handle(msg, db)
            except Exception as e:                      # bitta xato botni to'xtatmasin
                print("xato:", e, file=sys.stderr)
    return last


def setup():
    """Bir marta: Telegram'dagi pastki menyu tugmasi, buyruqlar, tavsif."""
    r1 = call("setChatMenuButton", menu_button={"type": "web_app", "text": "Kutubxona",
                                                "web_app": {"url": APP_URL}})
    r2 = call("setMyCommands", commands=[
        {"command": "start", "description": "Dasturni ochish"},
        {"command": "men", "description": "Mening Telegram ID im"},
    ])
    r3 = call("setMyDescription", description=TAVSIF)
    r4 = call("setMyShortDescription", short_description="AI Kutubxona — PDF kitoblar, reyting bilan")
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("menyu tugmasi:", r1.get("ok"), "| buyruqlar:", r2.get("ok"),
          "| tavsif:", r3.get("ok"), r4.get("ok"))
    return all(x.get("ok") for x in (r1, r2, r3, r4))


# ---------------------------------------------------------------- Firestore REST (kalitsiz)
def fs_unwrap(fields):
    """Firestore REST field({type: value}) formatini oddiy dict'ga o'giradi."""
    out = {}
    for k, v in (fields or {}).items():
        if "stringValue" in v:
            out[k] = v["stringValue"]
        elif "integerValue" in v:
            out[k] = int(v["integerValue"])
        elif "booleanValue" in v:
            out[k] = v["booleanValue"]
        elif "nullValue" in v:
            out[k] = None
        else:
            out[k] = v
    return out


def fs_request(method, url, body=None):
    req = Request(url, method=method,
                  data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except HTTPError as e:
        txt = e.read().decode()
        try:
            return e.code, json.loads(txt)
        except ValueError:
            return e.code, {"raw": txt[:300]}
    except URLError as e:
        print("Firestore tarmoq xatosi:", e, file=sys.stderr)
        return 0, {}


def overdue_reminders():
    """dueAtMs <= hozir bo'lgan libReminders hujjatlarini qaytaradi (reminded holidan
    qat'i nazar — reminded==True bo'lganlari keyin filtrlanadi, chunki tenglik +
    oraliq filtrni birga ishlatish composite index talab qiladi)."""
    now_ms = int(time.time() * 1000)
    body = {
        "structuredQuery": {
            "from": [{"collectionId": "libReminders"}],
            "where": {"fieldFilter": {
                "field": {"fieldPath": "dueAtMs"},
                "op": "LESS_THAN_OR_EQUAL",
                "value": {"integerValue": str(now_ms)},
            }},
            "limit": 300,
        }
    }
    status, rows = fs_request("POST", FS + ":runQuery", body)
    if status != 200 or not isinstance(rows, list):
        print("Firestore so'rovi muvaffaqiyatsiz:", status, str(rows)[:300], file=sys.stderr)
        return []
    out = []
    for row in rows:
        doc = row.get("document")
        if not doc:
            continue
        d = fs_unwrap(doc.get("fields"))
        d["_id"] = doc["name"].rsplit("/", 1)[-1]
        if not d.get("reminded"):
            out.append(d)
    return out


def mark_reminded(doc_id):
    url = FS + "/libReminders/%s?updateMask.fieldPaths=reminded&updateMask.fieldPaths=remindedAt" % doc_id
    now_ms = int(time.time() * 1000)
    body = {"fields": {"reminded": {"booleanValue": True}, "remindedAt": {"integerValue": str(now_ms)}}}
    status, _ = fs_request("PATCH", url, body)
    return status == 200


def tekshir_muddatlar():
    reminders = overdue_reminders()
    sent = 0
    for r in reminders:
        chat_id = r.get("chatId")
        title = r.get("bookTitle", "kitob")
        if not chat_id:
            # Telegram orqali ulanmagan foydalanuvchi — eslatma yubora olmaymiz,
            # lekin qayta-qayta urinmaslik uchun baribir belgilaymiz.
            mark_reminded(r["_id"])
            continue
        text = (
            "⏰ *%s* kitobini o'qish muddati tugadi!\n\n"
            "Ilovada \"✅ Tugatdim\" tugmasini bosing, yoki yana bir muddat davom eting."
        ) % title
        ok = send(str(chat_id), text, app_button("📖 Kutubxonaga o'tish")).get("ok")
        if ok:
            sent += 1
        mark_reminded(r["_id"])
        time.sleep(0.05)
    print("eslatma tekshirildi: %d ta topildi, %d ta yuborildi" % (len(reminders), sent))
    return sent


def main(argv):
    if not TOKEN or not APP_URL:
        sys.exit("BOT_TOKEN va APP_URL o'zgaruvchilarini kiriting.")

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--broadcast" in argv:
        i = argv.index("--broadcast")
        body = argv[i + 1] if len(argv) > i + 1 else ""
        if not body.strip():
            sys.exit("Matn bo'sh.")
        db = load()
        print("Yuborildi: %d ta" % broadcast(db, body))
        return

    did_something = False

    if "--once" in argv:
        db = load()
        r = call("getUpdates", timeout=0, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        save(db)
        print("xabarlar qayta ishlandi: %d ta, foydalanuvchilar: %d" % (len(r.get("result", [])), len(db)))
        did_something = True

    if "--tekshir" in argv:
        tekshir_muddatlar()
        did_something = True

    if did_something:
        return

    # doimiy rejim (o'z serveringiz bo'lsa)
    setup()
    db = load()
    offset = 0
    last_check = 0
    print("Bot ishga tushdi. Foydalanuvchilar:", len(db))
    while True:
        r = call("getUpdates", offset=offset, timeout=60, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
            save(db)
        if time.time() - last_check > 900:        # har 15 daqiqada muddatlarni tekshir
            tekshir_muddatlar()
            last_check = time.time()


if __name__ == "__main__":
    main(sys.argv[1:])

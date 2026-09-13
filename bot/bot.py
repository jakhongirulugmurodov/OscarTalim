#!/usr/bin/env python3
"""
AI kursi — Telegram bot.

Vazifasi uchta:
  1. Mini App'ga kirish nuqtasi (/start → tugma → dastur ochiladi)
  2. Sinf kodini havola orqali uzatish (t.me/BOT?start=AI13)
  3. Eslatmalar — GitHub Actions sahifasidan yoki /eslatma buyrug'i bilan

Ro'yxatdan o'tish bot ichida emas, Mini App ichida bo'ladi: u yerda ism,
guruh, rasm va Face ID bor va ma'lumot to'g'ridan-to'g'ri Firebase'ga yoziladi.
Bot faqat chat_id larni saqlaydi — eslatma yuborish uchun shu yetadi.

Rejimlar:
    python3 bot.py                      # doimiy (server bo'lsa): long polling
    python3 bot.py --once               # GitHub Actions: kelgan xabarlarni
                                        #   qayta ishlab chiqib ketadi
    python3 bot.py --setup              # menyu tugmasi, buyruqlar, tavsif
    python3 bot.py --broadcast "matn"   # hammaga eslatma

Muhit o'zgaruvchilari:
    BOT_TOKEN   BotFather bergan token
    APP_URL     https://<foydalanuvchi>.github.io/OscarTalim/sinf/
    ADMIN_IDS   muallimning Telegram ID lari, vergul bilan (ixtiyoriy)
    STATE_FILE  users.json manzili (ixtiyoriy)
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
    os.path.dirname(os.path.abspath(__file__)), "users.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

SALOM = (
    "Salom! Bu — *AI kursi · 13 dars* dasturi.\n\n"
    "Pastdagi tugmani bos:\n"
    "• ismingni yozasan va rasmga tushasan\n"
    "• muallim tasdiqlaydi\n"
    "• o'tilgan darslar, vazifalar va reyting ochiladi\n\n"
    "Ball o'yindan emas, *ishdan* chiqadi. Jonli o'yin — qo'shimcha."
)
TAVSIF = ("AI kursi · 13 dars. O'quvchilar dasturi: darslar, vazifalar, "
          "jonli duel va reyting. Pastdagi «AI kursi» tugmasini bosing.")


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


def app_button(code=None):
    url = APP_URL + (("?code=" + code) if code else "")
    return {"inline_keyboard": [[{"text": "📚 Dasturni ochish", "web_app": {"url": url}}]]}


# ---------------------------------------------------------------- saqlash
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
    for uid, u in db.items():
        if send(uid, body, app_button(u.get("code"))).get("ok"):
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
        parts = text.split(maxsplit=1)
        code = parts[1].strip().upper() if len(parts) > 1 else db.get(chat, {}).get("code")
        db[chat] = {
            "id": chat,
            "name": ((user.get("first_name") or "") + " " + (user.get("last_name") or "")).strip(),
            "username": user.get("username", ""),
            "code": code or "",
            "since": db.get(chat, {}).get("since", int(time.time())),
        }
        send(chat, SALOM, app_button(code))
        return

    if text.startswith("/kod"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Sinf kodini yozing: `/kod AI13`")
            return
        code = parts[1].strip().upper()
        db.setdefault(chat, {"id": chat})["code"] = code
        send(chat, "Sinf kodi saqlandi: *%s*" % code, app_button(code))
        return

    if text.startswith("/men"):
        send(chat, "Sizning Telegram ID: `%s`" % chat)
        return

    if text.startswith("/eslatma"):
        if chat not in ADMINS:
            send(chat, "Bu buyruq faqat muallim uchun.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Foydalanish: `/eslatma Dars 30 daqiqadan keyin`")
            return
        send(chat, "Yuborildi: %d ta" % broadcast(db, parts[1]))
        return

    if text.startswith("/kim"):
        if chat not in ADMINS:
            return
        lines = ["%s — %s" % (u.get("name", "?"), u.get("code") or "kodsiz")
                 for u in db.values()]
        send(chat, "Botga yozilganlar (%d):\n%s" % (len(lines), "\n".join(lines) or "—"))
        return

    send(chat, "Dasturni ochish uchun tugmani bos 👇", app_button(db.get(chat, {}).get("code")))


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
    r1 = call("setChatMenuButton", menu_button={"type": "web_app", "text": "AI kursi",
                                                "web_app": {"url": APP_URL}})
    r2 = call("setMyCommands", commands=[
        {"command": "start", "description": "Dasturni ochish"},
        {"command": "kod", "description": "Sinf kodini kiritish"},
        {"command": "men", "description": "Mening Telegram ID im"},
    ])
    r3 = call("setMyDescription", description=TAVSIF)
    r4 = call("setMyShortDescription", short_description="AI kursi · 13 dars — o'quvchilar dasturi")
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("menyu tugmasi:", r1.get("ok"), "| buyruqlar:", r2.get("ok"),
          "| tavsif:", r3.get("ok"), r4.get("ok"))
    return all(x.get("ok") for x in (r1, r2, r3, r4))


def main(argv):
    if not TOKEN or not APP_URL:
        sys.exit("BOT_TOKEN va APP_URL o'zgaruvchilarini kiriting.")
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--broadcast" in argv:
        i = argv.index("--broadcast")
        body = argv[i + 1] if len(argv) > i + 1 else ""
        if not body.strip():
            sys.exit("Matn bo'sh.")
        print("Yuborildi: %d ta" % broadcast(db, body))
        return

    if "--once" in argv:
        # GitHub Actions: navbatdagi xabarlarni olamiz, javob beramiz,
        # keyin Telegram'ga "shulargacha ko'rdim" deb tasdiqlaymiz.
        r = call("getUpdates", timeout=0, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        save(db)
        print("qayta ishlandi: %d ta, foydalanuvchilar: %d" % (len(r.get("result", [])), len(db)))
        return

    # doimiy rejim (o'z serveringiz bo'lsa)
    setup()
    offset = 0
    print("Bot ishga tushdi. Foydalanuvchilar:", len(db))
    while True:
        r = call("getUpdates", offset=offset, timeout=60, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
            save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

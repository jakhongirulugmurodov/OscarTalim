#!/usr/bin/env python3
"""
AI kursi — Telegram bot.

Vazifasi uchta:
  1. Mini App'ga kirish nuqtasi (/start → tugma → dastur ochiladi)
  2. Sinf kodini havola orqali uzatish (t.me/BOT?start=AI13)
  3. Eslatmalar (dars boshlanishi, streak, uy ishi) — muallim buyrug'i bilan

Ro'yxatdan o'tish bot ichida emas, Mini App ichida bo'ladi: u yerda ism,
guruh, rasm va Face ID bor va ma'lumot to'g'ridan-to'g'ri Firebase'ga yoziladi.
Bot faqat chat_id larni saqlaydi — eslatma yuborish uchun shu yetadi.

Ishga tushirish:
    export BOT_TOKEN="BotFather bergan token"
    export APP_URL="https://<foydalanuvchi>.github.io/OscarTalim/sinf/"
    export ADMIN_IDS="123456789"          # muallimning Telegram ID si
    python3 bot.py
"""

import json
import os
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
APP_URL = os.environ.get("APP_URL", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

SALOM = (
    "Salom! Bu — *AI kursi · 13 dars* dasturi.\n\n"
    "Pastdagi tugmani bos:\n"
    "• ismingni yozasan va rasmga tushasan\n"
    "• muallim tasdiqlaydi\n"
    "• o'tilgan darslar, vazifalar va reyting ochiladi\n\n"
    "Ball o'yindan emas, *ishdan* chiqadi. Jonli o'yin — qo'shimcha."
)


# ---------------------------------------------------------------- Telegram API
def call(method, **params):
    data = urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                      for k, v in params.items() if v is not None}).encode()
    try:
        with urlopen(Request(API + method, data=data), timeout=70) as r:
            return json.load(r)
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
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- buyruqlar
def handle(msg, db):
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {})

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
        save(db)
        send(chat, SALOM, app_button(code))
        return

    if text.startswith("/kod"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Sinf kodini yozing: `/kod AI13`")
            return
        code = parts[1].strip().upper()
        db.setdefault(chat, {"id": chat})["code"] = code
        save(db)
        send(chat, "Sinf kodi saqlandi: *%s*" % code, app_button(code))
        return

    if text.startswith("/eslatma"):
        if chat not in ADMINS:
            send(chat, "Bu buyruq faqat muallim uchun.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Foydalanish: `/eslatma Dars 30 daqiqadan keyin`")
            return
        body, sent = parts[1], 0
        for uid, u in db.items():
            if send(uid, body, app_button(u.get("code"))).get("ok"):
                sent += 1
            time.sleep(0.05)          # Telegram cheklovi: ~30 xabar/soniya
        send(chat, "Yuborildi: %d ta" % sent)
        return

    if text.startswith("/kim"):
        if chat not in ADMINS:
            return
        lines = ["%s — %s" % (u.get("name", "?"), u.get("code") or "kodsiz")
                 for u in db.values()]
        send(chat, "Botga yozilganlar (%d):\n%s" % (len(lines), "\n".join(lines) or "—"))
        return

    send(chat, "Dasturni ochish uchun tugmani bos 👇", app_button(db.get(chat, {}).get("code")))


def main():
    if not TOKEN or not APP_URL:
        sys.exit("BOT_TOKEN va APP_URL o'zgaruvchilarini kiriting.")

    # Telegram'dagi pastki menyu tugmasi
    call("setChatMenuButton", menu_button={"type": "web_app", "text": "AI kursi",
                                           "web_app": {"url": APP_URL}})
    call("setMyCommands", commands=[
        {"command": "start", "description": "Dasturni ochish"},
        {"command": "kod", "description": "Sinf kodini kiritish"},
    ])

    db, offset = load(), 0
    print("Bot ishga tushdi. Foydalanuvchilar:", len(db))
    while True:
        r = call("getUpdates", offset=offset, timeout=60)
        for upd in r.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("edited_message")
            if msg:
                try:
                    handle(msg, db)
                except Exception as e:                      # bitta xato botni to'xtatmasin
                    print("xato:", e, file=sys.stderr)


if __name__ == "__main__":
    main()

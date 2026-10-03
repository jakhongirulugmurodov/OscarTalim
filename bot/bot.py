#!/usr/bin/env python3
"""
AI kursi — Telegram bot.

Vazifasi:
  1. Mini App'ga kirish nuqtasi (/start → tugma → dastur ochiladi)
  2. Sinf kodini havola orqali uzatish (t.me/BOT?start=AI13)
  3. Eslatmalar — GitHub Actions sahifasidan yoki /eslatma buyrug'i bilan
  4. TestCorrect — foydalanuvchi test savoli+javobini (matn yoki rasm)
     yuboradi, Gemini to'g'ri/noto'g'riligini va xatoni bosqichma-bosqich
     tushuntiradi; xohlasa, mavzu bo'yicha javoblari bilan test ham tuzib
     beradi (bot/gemini.py, GEMINI_API_KEY kerak).

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
    BOT_TOKEN        BotFather bergan token
    APP_URL          https://<foydalanuvchi>.github.io/OscarTalim/sinf/
    ADMIN_IDS        muallimning Telegram ID lari, vergul bilan (ixtiyoriy)
    STATE_FILE       users.json manzili (ixtiyoriy)
    GEMINI_API_KEY   TestCorrect uchun (https://aistudio.google.com/apikey)
"""

import json
import os
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

import gemini

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
APP_URL = os.environ.get("APP_URL", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "users.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

BTN_DASTUR = "📚 Dasturni ochish"
BTN_TEKSHIR = "🧪 Javobni tekshirish"
BTN_YARAT = "🧾 Test yaratish"

SALOM = (
    "Salom! Bu — *AI kursi* va *TestCorrect* dasturi.\n\n"
    "📚 *Dasturni ochish* — ismingni yozasan, muallim tasdiqlaydi, "
    "o'tilgan darslar va reyting ochiladi.\n\n"
    "🧪 *Javobni tekshirish* — istalgan fandan test savoli va o'z "
    "javobingni (rasm yoki matn qilib) yubor — to'g'ri-noto'g'riligini "
    "va xato bo'lsa, qayerda adashganingni bosqichma-bosqich aytib beraman.\n\n"
    "🧾 *Test yaratish* — mavzuni yoz, javoblari bilan test tuzib beraman.\n\n"
    "Qaysi tilda yozsang, o'sha tilda javob beraman."
)
TAVSIF = ("AI kursi va TestCorrect. Darslar, reyting va jonli duel; "
          "istalgan fandan test javobini tekshirish va test tuzish — "
          "rasm yoki matn orqali, har qanday tilda.")


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


def keyboard(code=None):
    url = APP_URL + (("?code=" + code) if code else "")
    return {
        "keyboard": [
            [{"text": BTN_DASTUR, "web_app": {"url": url}}],
            [{"text": BTN_TEKSHIR}, {"text": BTN_YARAT}],
        ],
        "resize_keyboard": True,
    }


def fayl_yukla(file_id):
    """Telegramdagi faylni (masalan, javob rasmi) baytlarga yuklab oladi."""
    meta = call("getFile", file_id=file_id)
    yol = (meta.get("result") or {}).get("file_path")
    if not yol:
        return None, None
    try:
        with urlopen("https://api.telegram.org/file/bot%s/%s" % (TOKEN, yol), timeout=60) as r:
            data = r.read()
    except (URLError, HTTPError) as e:
        print("fayl yuklashda xato:", e, file=sys.stderr)
        return None, None
    kengaytma = yol.rsplit(".", 1)[-1].lower() if "." in yol else "jpg"
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp"}.get(kengaytma, "image/jpeg")
    return data, mime


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
        if send(uid, body, keyboard(u.get("code"))).get("ok"):
            sent += 1
        time.sleep(0.05)          # Telegram cheklovi: ~30 xabar/soniya
    return sent


def handle(msg, db):
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or msg.get("caption") or "").strip()
    photo = msg.get("photo")
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
        send(chat, SALOM, keyboard(code))
        return

    if text.startswith("/kod"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send(chat, "Sinf kodini yozing: `/kod AI13`")
            return
        code = parts[1].strip().upper()
        db.setdefault(chat, {"id": chat})["code"] = code
        send(chat, "Sinf kodi saqlandi: *%s*" % code, keyboard(code))
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

    entry = db.setdefault(chat, {"id": chat})

    if text == BTN_YARAT or text.startswith("/yarat"):
        entry["kutilmoqda"] = "yarat"
        send(chat, "Qaysi fan/mavzu bo'yicha test kerak? Masalan: "
                    "\"Biologiya, hujayra, 5 ta savol\". Javoblari bilan tuzib beraman.")
        return

    if text == BTN_TEKSHIR or text.startswith("/tekshir"):
        entry["kutilmoqda"] = None
        send(chat, "Test savoli va o'z javobingizni yuboring — rasm (masalan, "
                    "daftar surati) yoki matn qilib. Darhol tekshirib beraman.")
        return

    if entry.get("kutilmoqda") == "yarat":
        entry["kutilmoqda"] = None
        if not text:
            send(chat, "Mavzuni matn qilib yozing, masalan: \"Tarix, Amir Temur, 5 ta savol\".")
            return
        natija = gemini.test_yarat(text)
        send(chat, natija or "Uzr, hozir test tuzib bo'lmadi. Birozdan keyin qayta urinib ko'ring.")
        return

    if photo or text:
        rasm = mime = None
        if photo:
            rasm, mime = fayl_yukla(photo[-1]["file_id"])
        natija = gemini.javobni_tekshir(savol_matn=text or None, rasm=rasm,
                                         rasm_mime=mime or "image/jpeg")
        send(chat, natija or "Uzr, hozir tekshirib bo'lmadi (rasm noaniq yoki "
                              "server band). Birozdan keyin qayta yuborib ko'ring.")
        return

    send(chat, "Dasturni ochish yoki savolingizni yuborish uchun pastdagi "
                "tugmalardan foydalaning 👇", keyboard(entry.get("code")))


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
        {"command": "tekshir", "description": "Test javobini tekshirish"},
        {"command": "yarat", "description": "Test yaratish"},
        {"command": "kod", "description": "Sinf kodini kiritish"},
        {"command": "men", "description": "Mening Telegram ID im"},
    ])
    r3 = call("setMyDescription", description=TAVSIF)
    r4 = call("setMyShortDescription", short_description="AI kursi va TestCorrect — o'quvchilar dasturi")
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

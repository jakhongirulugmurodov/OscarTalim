#!/usr/bin/env python3
"""
Zumar kitob do'koni — Telegram bot.

Vazifasi:
  1. Ro'yxatdan o'tkazish: ism-familiya, yosh, telefon raqam.
  2. MUQADDIMA kitobi: narxi (99 000 so'm), qoldig'i — qolgan bo'lsa
     nechta qolganini, qolmagan bo'lsa «qolmadi» deydi.
  3. Buyurtma: kitob olgan har bir xaridorga bonus — stikerlar to'plami
     va keyingi safar do'konga kelganda ishlatiladigan chegirma kodi.
  4. Haftada 1 marta aksiya — hamma obunachilarga avtomatik yuboriladi.
  5. Auditoriya: Instagram / Telegram kanal havolalari va do'st taklif
     qilish (taklif qilgan odamga bonus ball).
  6. «Boshqa kitob kerak» — xaridorlar so'ragan kitoblar ro'yxati,
     do'kon qaysi kitobni olib kelishni shundan biladi.

Rejimlar:
    python3 bot.py                      # doimiy (server bo'lsa): long polling
    python3 bot.py --once               # GitHub Actions: kelgan xabarlarni
                                        #   qayta ishlab chiqib ketadi
    python3 bot.py --setup              # buyruqlar va tavsif
    python3 bot.py --aksiya ["matn"]    # aksiyani hozir hammaga yuborish

Muhit o'zgaruvchilari:
    BOT_TOKEN        BotFather bergan token
    ADMIN_IDS        do'kon egasi/sotuvchi Telegram ID lari, vergul bilan
    INSTAGRAM_URL    https://instagram.com/... (ixtiyoriy)
    KANAL_URL        https://t.me/... (ixtiyoriy)
    MANZIL           do'kon manzili (ixtiyoriy)
    STATE_FILE       zumar.json manzili (ixtiyoriy)
"""

import html
import json
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
INSTAGRAM = os.environ.get("INSTAGRAM_URL", "").strip()
KANAL = os.environ.get("KANAL_URL", "").strip()
MANZIL = os.environ.get("MANZIL", "").strip() or "Zumar kitob do'koni"
STORE = os.environ.get("STATE_FILE") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zumar.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

TOSHKENT = timezone(timedelta(hours=5))
AKSIYA_KUNI = 4          # 0 = dushanba ... 4 = juma
AKSIYA_SOATI = 10        # Toshkent vaqti bilan

KITOB = "MUQADDIMA"
NARX = 99000
BOSHLANGICH_QOLDIQ = 100
CHEGIRMA = 10            # keyingi xarid uchun bonus kod, foizda
TAKLIF_BALL = 5000       # do'st taklif qilib, u xarid qilsa — so'm hisobida

BTN_KITOB = "📖 MUQADDIMA — 99 000 so'm"
BTN_OLISH = "🛒 Sotib olish"
BTN_BONUS = "🎁 Bonuslarim"
BTN_AKSIYA = "🔥 Haftalik aksiya"
BTN_BOSHQA = "📚 Boshqa kitob kerak"
BTN_BIZ = "📢 Instagram / Telegram"
BTN_BEKOR = "❌ Bekor qilish"
BTN_TELEFON = "📱 Raqamni yuborish"
MENYU = {BTN_KITOB, BTN_OLISH, BTN_BONUS, BTN_AKSIYA, BTN_BOSHQA, BTN_BIZ}

# Admin /aksiya bilan o'z matnini qo'ymasa, shular navbat bilan yuboriladi.
AKSIYALAR = [
    "🔥 <b>Haftalik aksiya!</b>\nShu hafta MUQADDIMA olgan har bir xaridorga "
    "stikerlar to'plami + qo'shimcha xatcho'p sovg'a!",
    "🔥 <b>Haftalik aksiya!</b>\nDo'stingiz bilan keling: 2 ta MUQADDIMA olsangiz, "
    "ikkinchisiga 10% chegirma.",
    "🔥 <b>Haftalik aksiya!</b>\nBotdagi bonus kodingizni ko'rsating — "
    "shu hafta u ikki barobar kuchli: 20% chegirma.",
    "🔥 <b>Haftalik aksiya!</b>\nInstagram sahifamizdagi so'nggi postga izoh "
    "qoldiring — har hafta 1 kishiga MUQADDIMA sovg'a!",
]


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


def e(s):
    return html.escape(str(s or ""), quote=False)


def som(n):
    return "{:,}".format(n).replace(",", " ") + " so'm"


def menyu():
    return {
        "keyboard": [
            [{"text": BTN_KITOB}],
            [{"text": BTN_OLISH}, {"text": BTN_BONUS}],
            [{"text": BTN_AKSIYA}, {"text": BTN_BOSHQA}],
            [{"text": BTN_BIZ}],
        ],
        "resize_keyboard": True,
    }


def tugmalar(*qatorlar):
    return {"keyboard": [[{"text": t} for t in q] for q in qatorlar],
            "resize_keyboard": True, "one_time_keyboard": True}


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    db.setdefault("orders", [])
    db.setdefault("sorovlar", [])
    db.setdefault("qoldiq", BOSHLANGICH_QOLDIQ)
    db.setdefault("aksiya", {"matn": "", "oxirgi_hafta": "", "navbat": 0})
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


def adminlarga(text):
    for a in ADMINS:
        send(a, text)


# ---------------------------------------------------------------- matnlar
def qoldiq_matn(db):
    q = db["qoldiq"]
    if q <= 0:
        return ("📖 <b>%s</b>\n💰 Narxi: %s\n\n❌ <b>Qolmadi.</b> Hozircha sotuvda yo'q — "
                "yangi partiya kelganda birinchi bo'lib xabar beramiz." % (KITOB, som(NARX)))
    return ("📖 <b>%s</b> — Ibn Xaldun\n💰 Narxi: <b>%s</b>\n✅ Do'konda <b>%d dona</b> qoldi.\n\n"
            "🎁 Har bir xaridga stikerlar to'plami va keyingi xarid uchun %d%% "
            "chegirma kodi sovg'a!" % (KITOB, som(NARX), q, CHEGIRMA))


def biz_matn(u):
    qatorlar = ["📢 <b>Bizni kuzating</b> — yangi kitoblar, aksiyalar va sovg'alar birinchi "
                "u yerda e'lon qilinadi:"]
    if INSTAGRAM:
        qatorlar.append("📸 Instagram: " + e(INSTAGRAM))
    if KANAL:
        qatorlar.append("✈️ Telegram kanal: " + e(KANAL))
    qatorlar.append("📍 " + e(MANZIL))
    me = call("getMe").get("result", {}).get("username")
    if me:
        qatorlar.append("\n🤝 <b>Do'stingizni taklif qiling!</b> Shu havola orqali kirgan "
                        "do'stingiz kitob olsa, sizga %s bonus:\nhttps://t.me/%s?start=%s"
                        % (som(TAKLIF_BALL), me, u["id"]))
    return "\n".join(qatorlar)


def aksiya_matn(db):
    a = db["aksiya"]
    return a["matn"] or AKSIYALAR[a["navbat"] % len(AKSIYALAR)]


# ---------------------------------------------------------------- aksiya
def broadcast(db, body):
    sent = 0
    for uid, u in db["users"].items():
        if u.get("bosqich") == "tayyor" and not u.get("bloklagan"):
            r = send(uid, body, menyu())
            if r.get("ok"):
                sent += 1
            elif r.get("error_code") == 403:
                u["bloklagan"] = True
            time.sleep(0.05)      # Telegram cheklovi: ~30 xabar/soniya
    return sent


def haftalik_aksiya(db, majburiy=False):
    """Har hafta AKSIYA_KUNI, AKSIYA_SOATI dan keyin bir marta yuboradi."""
    hozir = datetime.now(TOSHKENT)
    yil, hafta, _ = hozir.isocalendar()
    kalit = "%d-W%02d" % (yil, hafta)
    a = db["aksiya"]
    if not majburiy:
        if a["oxirgi_hafta"] == kalit:
            return None
        if hozir.weekday() < AKSIYA_KUNI or (hozir.weekday() == AKSIYA_KUNI
                                              and hozir.hour < AKSIYA_SOATI):
            return None
    n = broadcast(db, aksiya_matn(db))
    a["oxirgi_hafta"] = kalit
    if not a["matn"]:
        a["navbat"] += 1
    a["matn"] = ""                # admin matni bir hafta amal qiladi
    adminlarga("🔥 Haftalik aksiya %d kishiga yuborildi." % n)
    return n


# ---------------------------------------------------------------- xarid
def bonus_kod():
    return "ZUMAR-" + "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
                              for _ in range(5))


def buyurtma(db, u, soni):
    if db["qoldiq"] <= 0:
        return send(u["id"], qoldiq_matn(db), menyu())
    if soni > db["qoldiq"]:
        return send(u["id"], "Kechirasiz, do'konda faqat <b>%d dona</b> qoldi. "
                    "Nechta olasiz?" % db["qoldiq"], soni_tugmalari())
    db["qoldiq"] -= soni
    kod = bonus_kod()
    o = {"id": len(db["orders"]) + 1, "user": u["id"], "soni": soni,
         "summa": soni * NARX, "kod": kod, "vaqt": int(time.time()), "holat": "yangi"}
    db["orders"].append(o)
    u.setdefault("kodlar", []).append(kod)
    u["xaridlar"] = u.get("xaridlar", 0) + soni

    # Taklif qilgan do'stga birinchi xariddan keyin bonus
    t = u.get("taklif")
    if t and not u.get("taklif_berildi") and t in db["users"]:
        db["users"][t]["ball"] = db["users"][t].get("ball", 0) + TAKLIF_BALL
        u["taklif_berildi"] = True
        send(t, "🎉 Siz taklif qilgan do'stingiz kitob oldi! Sizga <b>%s</b> bonus "
                "qo'shildi. Keyingi xaridda ishlating." % som(TAKLIF_BALL))

    send(u["id"],
         "✅ <b>Buyurtma #%d qabul qilindi!</b>\n\n📖 %s × %d = <b>%s</b>\n\n"
         "🎁 <b>Sovg'alaringiz:</b>\n"
         "• Stikerlar to'plami — kitob bilan birga beriladi\n"
         "• Keyingi xarid uchun <b>%d%% chegirma</b> kodi: <code>%s</code>\n\n"
         "Kodni keyingi safar Zumar kitob do'koniga kelganingizda ko'rsating. "
         "Tez orada siz bilan bog'lanamiz: %s"
         % (o["id"], KITOB, soni, som(o["summa"]), CHEGIRMA, kod, e(u.get("tel"))),
         menyu())
    adminlarga("🛒 <b>Yangi buyurtma #%d</b>\n%s, %s yosh\n📱 %s\n📖 %s × %d = %s\n"
               "🎁 Stiker + kod %s\n📦 Qoldiq: %d dona"
               % (o["id"], e(u.get("ism")), e(u.get("yosh")), e(u.get("tel")),
                  KITOB, soni, som(o["summa"]), kod, db["qoldiq"]))
    if db["qoldiq"] == 0:
        adminlarga("⚠️ %s tugadi! Yangi partiya yoki boshqa kitob olib kelish vaqti." % KITOB)
    return None


def soni_tugmalari():
    return tugmalar(["1", "2", "3"], [BTN_BEKOR])


# ---------------------------------------------------------------- admin
def admin(chat, text, db):
    cmd, _, arg = text.partition(" ")
    arg = arg.strip()
    if cmd == "/qoldiq":
        if arg.isdigit():
            eski = db["qoldiq"]
            db["qoldiq"] = int(arg)
            send(chat, "📦 Qoldiq: %d dona" % db["qoldiq"])
            if eski <= 0 < db["qoldiq"]:
                n = broadcast(db, "📖 <b>%s yana sotuvda!</b>\n\n%s" % (KITOB, qoldiq_matn(db)))
                send(chat, "Kutganlarga xabar berildi: %d ta" % n)
        else:
            send(chat, "📦 Qoldiq: %d dona\nO'zgartirish: <code>/qoldiq 100</code>" % db["qoldiq"])
        return True
    if cmd == "/aksiya":
        if not arg:
            send(chat, "Joriy aksiya:\n\n%s\n\nO'zgartirish: <code>/aksiya matn</code>\n"
                       "Hozir yuborish: <code>/aksiya_yubor</code>" % aksiya_matn(db))
        else:
            db["aksiya"]["matn"] = "🔥 <b>Haftalik aksiya!</b>\n" + e(arg)
            send(chat, "Saqlandi. Juma kuni soat %d:00 da hammaga yuboriladi "
                       "(hozir yuborish: /aksiya_yubor)." % AKSIYA_SOATI)
        return True
    if cmd == "/aksiya_yubor":
        send(chat, "Yuborildi: %d ta" % haftalik_aksiya(db, majburiy=True))
        return True
    if cmd == "/xabar":
        if not arg:
            send(chat, "Foydalanish: <code>/xabar Yangi kitoblar keldi!</code>")
        else:
            send(chat, "Yuborildi: %d ta" % broadcast(db, e(arg)))
        return True
    if cmd == "/buyurtmalar":
        qator = []
        for o in db["orders"][-20:]:
            u = db["users"].get(o["user"], {})
            qator.append("#%d %s — %s, %d dona, %s [%s]" % (
                o["id"], e(u.get("ism")), e(u.get("tel")), o["soni"], som(o["summa"]), o["holat"]))
        send(chat, "🛒 Oxirgi buyurtmalar:\n" + ("\n".join(qator) or "—") +
             "\n\nBerildi: <code>/berildi 5</code> · Bekor: <code>/bekor 5</code>")
        return True
    if cmd in ("/berildi", "/bekor"):
        o = next((o for o in db["orders"] if str(o["id"]) == arg), None)
        if not o:
            send(chat, "Buyurtma topilmadi. Masalan: <code>%s 5</code>" % cmd)
        elif o["holat"] != "yangi":
            send(chat, "#%d allaqachon: %s" % (o["id"], o["holat"]))
        elif cmd == "/berildi":
            o["holat"] = "berildi"
            send(chat, "✅ #%d berildi." % o["id"])
            send(o["user"], "📖 Kitobingiz va stikerlaringiz berildi! Yoqimli mutolaa. "
                            "Keyingi safar bonus kodingiz bilan keling 🎁")
        else:
            o["holat"] = "bekor"
            db["qoldiq"] += o["soni"]
            send(chat, "❌ #%d bekor qilindi, qoldiq: %d" % (o["id"], db["qoldiq"]))
        return True
    if cmd == "/sorovlar":
        send(chat, "📚 Xaridorlar so'ragan kitoblar:\n" +
             ("\n".join("• " + e(s["kitob"]) for s in db["sorovlar"][-30:]) or "—"))
        return True
    if cmd == "/statistika":
        users = [u for u in db["users"].values() if u.get("bosqich") == "tayyor"]
        faol = [o for o in db["orders"] if o["holat"] != "bekor"]
        send(chat, "📊 <b>Statistika</b>\n👥 Ro'yxatdan o'tganlar: %d\n🛒 Buyurtmalar: %d\n"
                   "📖 Sotilgan: %d dona\n💰 Tushum: %s\n📦 Qoldiq: %d dona\n🤝 Taklif bilan "
                   "kelganlar: %d" % (len(users), len(faol), sum(o["soni"] for o in faol),
                                      som(sum(o["summa"] for o in faol)), db["qoldiq"],
                                      sum(1 for u in users if u.get("taklif"))))
        return True
    if cmd == "/kod":
        kod = arg.upper()
        egasi = next((u for u in db["users"].values() if kod in u.get("kodlar", [])), None)
        if not egasi:
            send(chat, "❌ Bunday kod yo'q yoki ishlatilgan.")
        else:
            egasi["kodlar"].remove(kod)
            send(chat, "✅ Kod to'g'ri: %s — %d%% chegirma bering." % (e(egasi.get("ism")), CHEGIRMA))
        return True
    if cmd == "/ball":
        raqam = "".join(ch for ch in arg if ch.isdigit())[-9:]
        egasi = next((u for u in db["users"].values()
                      if raqam and (u.get("tel") or "").endswith(raqam)), None)
        if not egasi:
            send(chat, "Foydalanish: <code>/ball 901234567</code> — xaridor raqami bo'yicha")
        else:
            send(chat, "💰 %s: %s bonus. Hisobdan chiqarildi." % (e(egasi.get("ism")),
                                                                  som(egasi.get("ball", 0))))
            send(egasi["id"], "💰 %s bonusingiz xaridda ishlatildi. Rahmat!" % som(egasi.get("ball", 0)))
            egasi["ball"] = 0
        return True
    if cmd == "/admin":
        send(chat, "<b>Admin buyruqlari</b>\n/statistika · /buyurtmalar\n/berildi N · /bekor N\n"
                   "/qoldiq [N]\n/aksiya [matn] · /aksiya_yubor\n/xabar matn\n"
                   "/kod ZUMAR-XXXXX — bonus kodni tekshirish\n/ball 901234567 — bonus ballni ishlatish\n/sorovlar — so'ralgan kitoblar")
        return True
    return False


# ---------------------------------------------------------------- xabarlar
def handle(msg, db):
    if msg["chat"].get("type") != "private":
        return
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    users = db["users"]

    if chat in ADMINS and text.startswith("/") and admin(chat, text, db):
        return

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        u = users.get(chat)
        if u and u.get("bosqich") == "tayyor":
            send(chat, "Qaytganingizdan xursandmiz, %s! 📚" % e(u.get("ism")), menyu())
            return
        users[chat] = {"id": chat, "bosqich": "ism", "since": int(time.time())}
        if len(parts) > 1 and parts[1] in users and parts[1] != chat:
            users[chat]["taklif"] = parts[1]
        send(chat, "Assalomu alaykum! <b>Zumar kitob do'koni</b> botiga xush kelibsiz 📚\n\n"
                   "Ro'yxatdan o'tsangiz — kitob qoldig'i, aksiyalar va sovg'alar haqida "
                   "birinchi bo'lib bilasiz.\n\n✍️ <b>Ism va familiyangizni</b> yozing:",
             {"remove_keyboard": True})
        return

    u = users.get(chat)
    if not u:
        send(chat, "Boshlash uchun /start ni bosing.")
        return

    # --- ro'yxatdan o'tish
    b = u.get("bosqich")
    if b == "ism":
        if len(text.split()) < 2 or text.startswith("/") or len(text) > 60:
            send(chat, "Iltimos, ism va familiyangizni to'liq yozing. Masalan: <i>Aziz Karimov</i>")
            return
        u["ism"] = text
        u["bosqich"] = "yosh"
        send(chat, "Rahmat, %s! 🎂 <b>Yoshingiz</b> nechada?" % e(text.split()[0]))
        return
    if b == "yosh":
        if not text.isdigit() or not 6 <= int(text) <= 100:
            send(chat, "Yoshingizni raqam bilan yozing. Masalan: <i>21</i>")
            return
        u["yosh"] = int(text)
        u["bosqich"] = "tel"
        send(chat, "📱 <b>Telefon raqamingizni</b> yuboring — pastdagi tugmani bosing "
                   "yoki yozing (+998 90 123 45 67):",
             {"keyboard": [[{"text": BTN_TELEFON, "request_contact": True}]],
              "resize_keyboard": True, "one_time_keyboard": True})
        return
    if b == "tel":
        c = msg.get("contact")
        tel = c.get("phone_number") if c else "".join(ch for ch in text if ch.isdigit() or ch == "+")
        if len([ch for ch in tel if ch.isdigit()]) < 9:
            send(chat, "Raqam noto'g'ri ko'rinadi. Masalan: <i>+998 90 123 45 67</i>")
            return
        u["tel"] = tel if tel.startswith("+") else "+" + tel
        u["bosqich"] = "tayyor"
        send(chat, "✅ Ro'yxatdan o'tdingiz!\n\n" + qoldiq_matn(db), menyu())
        adminlarga("👤 Yangi obunachi: %s, %s yosh, %s" % (e(u["ism"]), u["yosh"], e(u["tel"])))
        return

    # --- kutilayotgan javoblar
    kutish = u.pop("kutish", None)
    if text == BTN_BEKOR:
        send(chat, "Bekor qilindi.", menyu())
        return
    if kutish == "soni":
        if text.isdigit() and 1 <= int(text) <= 20:
            buyurtma(db, u, int(text))
        else:
            u["kutish"] = "soni"
            send(chat, "Nechta kitob olasiz? Raqam bilan yozing (1–20).", soni_tugmalari())
        return
    if kutish == "boshqa" and text and not text.startswith("/") and text not in MENYU:
        db["sorovlar"].append({"user": chat, "kitob": text[:200], "vaqt": int(time.time())})
        send(chat, "📝 Yozib oldik! Shu kitobni olib kelsak, sizga birinchi bo'lib xabar "
                   "beramiz.", menyu())
        adminlarga("📚 Kitob so'rovi: <b>%s</b>\n— %s, %s" % (e(text[:200]), e(u["ism"]), e(u["tel"])))
        return

    # --- menyu
    if text in (BTN_KITOB, "/kitob", "/qoldiq"):
        send(chat, qoldiq_matn(db), menyu())
    elif text in (BTN_OLISH, "/olish"):
        if db["qoldiq"] <= 0:
            send(chat, qoldiq_matn(db), menyu())
        else:
            u["kutish"] = "soni"
            send(chat, "🛒 <b>%s</b> — %s\nNechta olasiz?" % (KITOB, som(NARX)), soni_tugmalari())
    elif text in (BTN_BONUS, "/bonus"):
        kodlar = u.get("kodlar", [])
        send(chat, "🎁 <b>Bonuslaringiz</b>\n📖 Olingan kitoblar: %d\n💰 Bonus ball: %s\n"
                   "🎟 Chegirma kodlari (%d%%): %s\n\nKodni do'konda sotuvchiga ko'rsating."
             % (u.get("xaridlar", 0), som(u.get("ball", 0)), CHEGIRMA,
                ", ".join("<code>%s</code>" % k for k in kodlar) or "hali yo'q — kitob oling!"),
             menyu())
    elif text in (BTN_AKSIYA, "/aksiya"):
        send(chat, aksiya_matn(db) + "\n\n📅 Har juma yangi aksiya — kuzatib boring!", menyu())
    elif text in (BTN_BOSHQA, "/boshqa"):
        u["kutish"] = "boshqa"
        send(chat, "📚 Qaysi kitob kerak? Nomini (va muallifini) yozing — olib kelishga "
                   "harakat qilamiz.", tugmalar([BTN_BEKOR]))
    elif text in (BTN_BIZ, "/biz"):
        send(chat, biz_matn(u), menyu())
    elif text.startswith("/men"):
        send(chat, "Telegram ID: <code>%s</code>" % chat)
    else:
        send(chat, "Pastdagi tugmalardan birini tanlang 👇", menyu())


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        msg = upd.get("message")
        if msg:
            try:
                handle(msg, db)
            except Exception as ex:                     # bitta xato botni to'xtatmasin
                print("xato:", ex, file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Boshlash"},
        {"command": "kitob", "description": "MUQADDIMA — narx va qoldiq"},
        {"command": "olish", "description": "Sotib olish"},
        {"command": "bonus", "description": "Bonuslarim"},
        {"command": "aksiya", "description": "Haftalik aksiya"},
        {"command": "boshqa", "description": "Boshqa kitob so'rash"},
        {"command": "biz", "description": "Instagram va Telegram"},
    ])
    r2 = call("setMyDescription", description=(
        "Zumar kitob do'koni. MUQADDIMA — 99 000 so'm. Har xaridga stikerlar va "
        "keyingi xarid uchun chegirma kodi, har juma yangi aksiya."))
    r3 = call("setMyShortDescription", short_description="Zumar kitob do'koni — kitoblar, bonuslar, aksiyalar")
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    return all(x.get("ok") for x in (r1, r2, r3))


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--aksiya" in argv:
        i = argv.index("--aksiya")
        if len(argv) > i + 1 and argv[i + 1].strip():
            db["aksiya"]["matn"] = "🔥 <b>Haftalik aksiya!</b>\n" + e(argv[i + 1])
        print("Yuborildi: %d ta" % haftalik_aksiya(db, majburiy=True))
        save(db)
        return

    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        haftalik_aksiya(db)
        save(db)
        print("qayta ishlandi: %d ta, obunachilar: %d, qoldiq: %d"
              % (len(r.get("result", [])), len(db["users"]), db["qoldiq"]))
        return

    setup()
    offset = 0
    print("Bot ishga tushdi. Obunachilar:", len(db["users"]))
    while True:
        r = call("getUpdates", offset=offset, timeout=60, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
        haftalik_aksiya(db)
        save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""
Kitob do'koni — Telegram bot.

Mijoz uchun:
  1. Ro'yxatdan o'tish: ism-familiya → telefon → sevimli janrlar →
     sevimli kitob/muallif → qisqa so'rovnoma. Oxirida — ro'yxat sovg'asi.
  2. «Kitob bormi?» — nomi yoki muallifini yozadi. Bor bo'lsa: narxi,
     chegirmasi, nechta qolgani. Yo'q bo'lsa: keyingi hafta keladimi yoki
     yo'qmi, keladigan kitoblar ro'yxati; kelganda botning o'zi xabar beradi.
  3. Yangi kelgan kitoblar, keyingi hafta keladiganlar, aksiyalar
     (juma kuni — qo'shimcha chegirma), sovg'alarim, do'kon haqida.

Do'kon egasi (ADMIN_IDS) uchun — /yordam:
  /xarid  — xaridni yozib qo'yadi, mijozga «sovg'aga ega bo'ldingiz» xabari boradi
  /yangi  — yangi kitob keldi: katalogga qo'shiladi, hammaga xabar boradi
  /keladi — keyingi hafta keladigan kitob
  /stat   — qaysi janr yoqadi, nimalar qidirilyapti, nima yetishmayapti

Do'kon ma'lumotlari va boshlang'ich katalog — dokon.json. Mijozlar, xaridlar,
qidiruvlar va katalogdagi o'zgarishlar — STATE_FILE (baza.json).

Rejimlar:
    python3 bot.py              # doimiy (server bo'lsa): long polling, javob darhol
    python3 bot.py --once       # GitHub Actions: kelgan xabarlarni qayta ishlaydi
    python3 bot.py --setup      # buyruqlar va tavsif
    python3 bot.py --juma       # hammaga juma aksiyasi haqida xabar
    python3 bot.py --broadcast "matn"
    python3 bot.py --katalog    # katalogni dokon.json dan qaytadan yuklaydi

Muhit o'zgaruvchilari:
    BOT_TOKEN    BotFather bergan token
    ADMIN_IDS    do'kon egasi/sotuvchilarning Telegram ID lari, vergul bilan
    STATE_FILE   baza.json manzili (ixtiyoriy)
"""

import html
import json
import os
import random
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.environ.get("STATE_FILE") or os.path.join(HERE, "baza.json")
API = "https://api.telegram.org/bot%s/" % TOKEN
TOSHKENT = timezone(timedelta(hours=5))

with open(os.path.join(HERE, "dokon.json"), encoding="utf-8") as _f:
    CFG = json.load(_f)
DOKON = CFG["dokon"]
JANRLAR = CFG["janrlar"]
SOROV = CFG["sorovnoma"]

BTN_QIDIR = "🔎 Kitob bormi?"
BTN_YANGI = "🆕 Yangi kelganlar"
BTN_KEYINGI = "📅 Keyingi hafta"
BTN_AKSIYA = "🔥 Aksiyalar"
BTN_SOVGA = "🎁 Sovg'alarim"
BTN_DOKON = "🏪 Do'kon haqida"
BTN_TAYYOR = "✅ Tayyor"
BTN_OTKAZ = "➡️ O'tkazib yuborish"


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


def send(chat_id, text, kb=None):
    # Telegram bitta xabarga 4096 belgi beradi — uzun matnni qatorlab bo'lamiz
    bolaklar, joriy = [], ""
    for qator in text.split("\n"):
        if joriy and len(joriy) + len(qator) > 3900:
            bolaklar.append(joriy)
            joriy = ""
        joriy += ("\n" if joriy else "") + qator
    bolaklar.append(joriy)
    r = {"ok": False}
    for i, b in enumerate(bolaklar):
        r = call("sendMessage", chat_id=chat_id, text=b, parse_mode="HTML",
                 disable_web_page_preview="true",
                 reply_markup=kb if i == len(bolaklar) - 1 else None)
    return r


def menyu():
    return {"keyboard": [[{"text": BTN_QIDIR}, {"text": BTN_YANGI}],
                         [{"text": BTN_KEYINGI}, {"text": BTN_AKSIYA}],
                         [{"text": BTN_SOVGA}, {"text": BTN_DOKON}]],
            "resize_keyboard": True}


def tugmalar(variantlar, ustun=2, qoshimcha=None):
    qator = [[{"text": v} for v in variantlar[i:i + ustun]]
             for i in range(0, len(variantlar), ustun)]
    if qoshimcha:
        qator.append([{"text": qoshimcha}])
    return {"keyboard": qator, "resize_keyboard": True}


YOPIQ = {"remove_keyboard": True}


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("mijozlar", {})
    db.setdefault("qidiruv", [])
    db.setdefault("kutish", [])
    db.setdefault("xaridlar", [])
    if "katalog" not in db:
        katalog_yukla(db)
    return db


def katalog_yukla(db):
    kitoblar = [dict(k, keldi=0) for k in CFG["kitoblar"]]
    db["katalog"] = {"kitoblar": kitoblar,
                     "keyingi_hafta": list(CFG["keyingi_hafta"]),
                     "keyingi_id": max([k["id"] for k in kitoblar] or [0]) + 1}


def save(db):
    db["qidiruv"] = db["qidiruv"][-3000:]
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- yordamchilar
def e(s):
    return html.escape(str(s or ""), quote=False)


def hozir():
    return datetime.now(TOSHKENT)


def juma():
    return hozir().weekday() == 4


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def norm(s):
    s = (s or "").lower()
    s = re.sub(r"[ʻʼ’‘`´']", "'", s)
    s = re.sub(r"[^\w' ]+", " ", s)
    return " ".join(s.split())


def mos(sorov, kitob):
    """So'rovdagi har bir so'z kitob nomi yoki muallifida bormi."""
    joy = norm(kitob.get("nomi", "") + " " + kitob.get("muallif", ""))
    sozlar = [w for w in norm(sorov).split() if len(w) >= 2]
    return bool(sozlar) and all(w in joy for w in sozlar)


def raqam(s):
    """Telefonni +998XXXXXXXXX ko'rinishiga keltiradi; noto'g'ri bo'lsa None."""
    d = re.sub(r"\D", "", s or "")
    if len(d) == 9:
        d = "998" + d
    return "+" + d if 11 <= len(d) <= 13 else None


def chegirma(k):
    foiz = int(k.get("chegirma") or 0)
    if juma():
        foiz += int(CFG.get("juma_qoshimcha") or 0)
    return min(foiz, 90)


def narx_matn(k):
    foiz = chegirma(k)
    if not foiz:
        return "💰 Narxi: <b>%s</b>" % som(k["narx"])
    yangi = int(k["narx"] * (100 - foiz) / 10000 + 0.5) * 100
    return "💰 Narxi: <s>%s</s> → <b>%s</b> (−%d%%)" % (som(k["narx"]), som(yangi), foiz)


def kitob_matn(k, holat=True):
    qator = ["📖 <b>%s</b> — %s" % (e(k["nomi"]), e(k.get("muallif"))),
             "🏷 %s" % e(k.get("janr"))]
    if k.get("narx"):
        qator.append(narx_matn(k))
    if holat:
        soni = int(k.get("soni") or 0)
        if soni > 3:
            qator.append("✅ Bor")
        elif soni > 0:
            qator.append("✅ Bor — oxirgi %d dona qoldi" % soni)
        else:
            qator.append("❌ Hozir tugagan")
    return "\n".join(qator)


def sovga_kodi():
    return "KT-%04d" % random.randint(0, 9999)


def mijoz_ism(m):
    return m.get("ism") or m.get("tg_ism") or "Hurmatli mijoz"


def juma_eslatma():
    q = CFG.get("juma_qoshimcha") or 0
    if juma():
        return "🎉 <b>Bugun juma!</b> Barcha kitoblarga qo'shimcha −%d%% chegirma." % q
    return ("🗓 Eng katta aksiyalar — <b>har juma kuni</b>: barcha kitoblarga "
            "qo'shimcha −%d%%. Juma kuni kutamiz!" % q)


# ---------------------------------------------------------------- matnlar
def dokon_matn():
    d = DOKON
    qator = ["🏪 <b>%s</b>" % e(d["nomi"])]
    if d.get("shior"):
        qator.append("<i>%s</i>" % e(d["shior"]))
    qator += ["", e(d.get("tavsif")), "",
              "📍 %s" % e(d.get("manzil"))]
    if d.get("moljal"):
        qator.append("🧭 Mo'ljal: %s" % e(d["moljal"]))
    qator += ["🕘 %s" % e(d.get("ish_vaqti")),
              "📞 %s" % e(d.get("telefon"))]
    if d.get("yetkazib_berish"):
        qator.append("🚚 %s" % e(d["yetkazib_berish"]))
    if d.get("instagram"):
        qator.append("📸 %s" % e(d["instagram"]))
    qator += ["", juma_eslatma()]
    return "\n".join(qator)


def yangi_kelganlar(db):
    kitoblar = [k for k in db["katalog"]["kitoblar"] if int(k.get("soni") or 0) > 0]
    kitoblar.sort(key=lambda k: (k.get("keldi") or 0, k["id"]), reverse=True)
    if not kitoblar:
        return "Hozircha yangi kitob yo'q."
    return ("🆕 <b>Do'konimizdagi eng yangi kitoblar</b>\n\n" +
            "\n\n".join(kitob_matn(k) for k in kitoblar[:8]))


def keyingi_hafta(db):
    ruy = db["katalog"]["keyingi_hafta"]
    if not ruy:
        return "📅 Keyingi hafta keladigan kitoblar ro'yxati hali tayyor emas."
    return ("📅 <b>Keyingi hafta keladigan kitoblar</b>\n\n" +
            "\n".join("• <b>%s</b> — %s (%s)" % (e(k["nomi"]), e(k.get("muallif")),
                                                 e(k.get("janr"))) for k in ruy) +
            "\n\nKerakli kitobni oldindan band qilish uchun: 📞 %s" % e(DOKON.get("telefon")))


def aksiyalar(db):
    kitoblar = [k for k in db["katalog"]["kitoblar"]
                if int(k.get("soni") or 0) > 0 and chegirma(k) > 0]
    kitoblar.sort(key=chegirma, reverse=True)
    bosh = "🔥 <b>Aksiyalar</b>\n\n" + juma_eslatma()
    if not kitoblar:
        return bosh
    return bosh + "\n\n" + "\n\n".join(kitob_matn(k) for k in kitoblar[:10])


def sovgalarim(m):
    sov = m.get("sovgalar") or []
    if not sov:
        return ("🎁 Hozircha sovg'angiz yo'q.\n\nDo'konimizdan xarid qiling — har bir "
                "xariddan keyin shu yerga sovg'a keladi.")
    qator = ["🎁 <b>Sovg'alaringiz</b>\n"]
    for s in reversed(sov[-10:]):
        belgi = "☑️ ishlatilgan" if s.get("ishlatildi") else "🟢 faol"
        qator.append("• %s\n   Kod: <code>%s</code> — %s" % (e(s["matn"]), s["kod"], belgi))
    qator.append("\nKodni kassada ko'rsating.")
    return "\n".join(qator)


# ---------------------------------------------------------------- qidiruv
def qidir(db, chat, sorov):
    kat = db["katalog"]
    topildi = [k for k in kat["kitoblar"] if mos(sorov, k)]
    bor = [k for k in topildi if int(k.get("soni") or 0) > 0]
    keladi = [k for k in kat["keyingi_hafta"] if mos(sorov, k)]
    db["qidiruv"].append({"q": sorov[:100], "chat": chat, "t": int(time.time()),
                          "bor": bool(bor)})

    if bor:
        javob = "✅ <b>Ha, bor!</b>\n\n" + "\n\n".join(kitob_matn(k) for k in bor[:5])
        javob += "\n\n📍 %s\n📞 %s" % (e(DOKON.get("manzil")), e(DOKON.get("telefon")))
        if not juma():
            javob += "\n\n" + juma_eslatma()
        return javob

    if topildi:
        javob = "❌ <b>Afsus, hozir tugagan:</b>\n\n" + "\n\n".join(
            kitob_matn(k, holat=False) for k in topildi[:3])
    else:
        javob = "❌ <b>«%s» hozir do'konimizda yo'q.</b>" % e(sorov)

    if keladi:
        javob += ("\n\n📅 <b>Xushxabar: keyingi hafta keladi!</b>\n" +
                  "\n".join("• %s — %s" % (e(k["nomi"]), e(k.get("muallif"))) for k in keladi))
    else:
        ruy = kat["keyingi_hafta"]
        if ruy:
            javob += "\n\n📅 Keyingi hafta shu kitoblar keladi:\n" + "\n".join(
                "• %s — %s" % (e(k["nomi"]), e(k.get("muallif"))) for k in ruy[:8])

    if not any(w["chat"] == chat and norm(w["q"]) == norm(sorov) for w in db["kutish"]):
        db["kutish"].append({"chat": chat, "q": sorov[:100], "t": int(time.time())})
    javob += "\n\n🔔 So'rovingiz yozib olindi — kitob kelishi bilan shu yerga xabar beramiz."
    return javob


def kutganlarga_xabar(db, kitob):
    """Kitob kelganda uni so'ragan mijozlarga xabar beradi."""
    qolgan, yuborildi = [], 0
    for w in db["kutish"]:
        if mos(w["q"], kitob):
            send(w["chat"], "🔔 <b>Siz so'ragan kitob keldi!</b>\n\n" + kitob_matn(kitob) +
                 "\n\n📍 %s" % e(DOKON.get("manzil")))
            yuborildi += 1
            time.sleep(0.05)
        else:
            qolgan.append(w)
    db["kutish"] = qolgan
    return yuborildi


# ---------------------------------------------------------------- ro'yxatdan o'tish
def savol_ber(chat, m):
    qadam = m.get("qadam")
    if qadam == "ism":
        send(chat, "✍️ <b>Ism va familiyangizni</b> yozing:\n<i>Masalan: Aziza Karimova</i>",
             YOPIQ)
    elif qadam == "tel":
        send(chat, "📞 <b>Telefon raqamingizni</b> yuboring — pastdagi tugmani bosing "
                   "yoki raqamni yozing (masalan, 90 123 45 67):",
             {"keyboard": [[{"text": "📱 Raqamni yuborish", "request_contact": True}]],
              "resize_keyboard": True, "one_time_keyboard": True})
    elif qadam == "janr":
        send(chat, "📚 Qaysi <b>janrdagi</b> kitoblarni yoqtirasiz?\n\nBir nechtasini "
                   "tanlashingiz mumkin, keyin «%s» ni bosing." % BTN_TAYYOR,
             tugmalar(JANRLAR, 2, BTN_TAYYOR))
    elif qadam == "sevimli":
        send(chat, "❤️ Eng yaxshi ko'rgan <b>kitobingiz yoki muallifingiz</b> kim?",
             tugmalar([BTN_OTKAZ], 1))
    elif qadam and qadam.startswith("s"):
        i = int(qadam[1:])
        send(chat, "📝 <b>So'rovnoma (%d/%d)</b>\n\n%s" % (i + 1, len(SOROV), e(SOROV[i]["savol"])),
             tugmalar(SOROV[i]["variantlar"], 2))


def royxat(chat, m, text, contact, db):
    """Ro'yxatdan o'tish bosqichlari. True — xabar shu yerda ishlandi."""
    qadam = m.get("qadam")

    if qadam == "ism":
        if not re.search(r"[^\W\d_]{2,}", text) or len(text) > 60 or text.startswith("/"):
            send(chat, "Iltimos, ism va familiyangizni harflar bilan yozing.")
            return True
        m["ism"] = " ".join(text.split()).title()
        m["qadam"] = "tel"

    elif qadam == "tel":
        tel = raqam(contact.get("phone_number")) if contact else raqam(text)
        if not tel:
            send(chat, "Raqam noto'g'ri ko'rinadi. Masalan: <code>+998 90 123 45 67</code>")
            return True
        m["tel"] = tel
        m["janrlar"] = []
        m["qadam"] = "janr"

    elif qadam == "janr":
        if text == BTN_TAYYOR:
            if not m.get("janrlar"):
                send(chat, "Kamida bitta janrni tanlang 👇")
                return True
            m["qadam"] = "sevimli"
        else:
            for bolak in text.split(","):
                bolak = bolak.strip()
                if not bolak:
                    continue
                janr = next((j for j in JANRLAR if norm(j) == norm(bolak)), bolak[:40])
                if janr not in m["janrlar"]:
                    m["janrlar"].append(janr)
            send(chat, "Tanlandi: <b>%s</b>\nYana tanlang yoki «%s» ni bosing."
                 % (e(", ".join(m["janrlar"])), BTN_TAYYOR))
            return True

    elif qadam == "sevimli":
        m["sevimli"] = "" if text == BTN_OTKAZ else text[:150]
        m["qadam"] = "s0"
        m["sorovnoma"] = {}

    elif qadam and qadam.startswith("s"):
        i = int(qadam[1:])
        if not text:
            return True
        m["sorovnoma"][SOROV[i]["savol"]] = text[:100]
        if i + 1 < len(SOROV):
            m["qadam"] = "s%d" % (i + 1)
        else:
            tugat(chat, m, db)
            return True
    else:
        return False

    savol_ber(chat, m)
    return True


def tugat(chat, m, db):
    m["qadam"] = None
    m["royxatda"] = True
    m["royxat_vaqti"] = int(time.time())
    sov = CFG.get("royxat_sovgasi")
    matn = "🎉 <b>Rahmat, %s! Siz ro'yxatdan o'tdingiz.</b>" % e(m["ism"])
    if sov:
        kod = sovga_kodi()
        m.setdefault("sovgalar", []).append(
            {"matn": sov, "kod": kod, "vaqt": int(time.time()), "ishlatildi": False})
        matn += ("\n\n🎁 Sizga sovg'a: <b>%s</b>\nKod: <code>%s</code> — kassada ko'rsating."
                 % (e(sov), kod))
    matn += ("\n\nEndi siz yoqtirgan janrdagi yangi kitoblar, chegirmalar va juma "
             "aksiyalari haqida birinchi bo'lib bilasiz.\n\nKerakli kitob bormi-yo'qmi "
             "bilish uchun shunchaki nomini yozing 👇")
    send(chat, matn, menyu())
    for a in ADMINS:
        send(a, "🆕 Yangi mijoz: <b>%s</b>, %s\nJanrlar: %s\nSevimli: %s"
             % (e(m["ism"]), e(m["tel"]), e(", ".join(m.get("janrlar") or [])),
                e(m.get("sevimli") or "—")))


# ---------------------------------------------------------------- admin
YORDAM = """<b>Do'kon egasi buyruqlari</b>

<b>Xarid va sovg'a</b>
/xarid 901234567 350000 — xarid; mijozga sovg'a xabari boradi
/sovga 901234567 Bepul xatcho'p — qo'lda sovg'a
/ishlat KT-1234 — sovg'a kodi kassada ishlatildi

<b>Kitoblar</b>
/kitoblar — katalog (id, soni)
/yangi Nomi | Muallif | Janr | Narx | Chegirma% | Soni — yangi kitob keldi, hammaga xabar
/keladi Nomi | Muallif | Janr — keyingi hafta keladi
/keladi_tozala — keyingi hafta ro'yxatini tozalash
/soni 5 10 — 5-kitobdan 10 dona bor
/narx 5 70000 · /chegirma 5 15 · /ochir 5

<b>Mijozlar</b>
/stat — janrlar, so'rovnoma, qidiruvlar, yetishmayotgan kitoblar
/mijozlar — ro'yxat va telefonlar
/tarqat Matn — hammaga xabar
/juma — hozir juma aksiyasi xabarini yuborish"""


def mijoz_top(db, tel):
    tel = raqam(tel)
    if not tel:
        return None, None
    for cid, m in db["mijozlar"].items():
        if m.get("tel") and m["tel"][-9:] == tel[-9:]:
            return cid, m
    return None, None


def tel_ajrat(matn):
    """«90 123 45 67 320000 izoh» → ("90 123 45 67", "320000 izoh").
    Raqam bo'shliq bilan yozilgan bo'lsa ham, 9 ta raqam yig'ilguncha oladi."""
    sozlar = matn.split()
    raqamlar = ""
    for i, s in enumerate(sozlar):
        if not re.fullmatch(r"\+?[\d\-()]+", s):
            break
        raqamlar += re.sub(r"\D", "", s)
        if len(raqamlar) >= 9:
            return " ".join(sozlar[:i + 1]), " ".join(sozlar[i + 1:])
    return "", matn


def kitob_top(db, kid):
    try:
        kid = int(kid)
    except (TypeError, ValueError):
        return None
    return next((k for k in db["katalog"]["kitoblar"] if k["id"] == kid), None)


def son(s):
    try:
        return int(re.sub(r"[^\d]", "", s or "") or "x")
    except ValueError:
        return None


def tarqat(db, matn, janr=None):
    """Ro'yxatdagi hamma mijozga xabar; janr berilsa, o'sha janr yoqadiganlarga belgi."""
    yuborildi = 0
    for cid, m in db["mijozlar"].items():
        if not m.get("royxatda"):
            continue
        t = matn
        if janr and janr in (m.get("janrlar") or []):
            t = "💚 <b>Siz yoqtirgan janrdan!</b>\n" + t
        if send(cid, t, menyu()).get("ok"):
            yuborildi += 1
        time.sleep(0.05)          # Telegram cheklovi: ~30 xabar/soniya
    return yuborildi


def juma_xabari(db):
    kitoblar = [k for k in db["katalog"]["kitoblar"] if int(k.get("soni") or 0) > 0]
    kitoblar.sort(key=chegirma, reverse=True)
    matn = ("🎉 <b>Bugun juma — aksiya kuni!</b>\n\nBarcha kitoblarga qo'shimcha "
            "<b>−%d%%</b> chegirma. Eng foydalilari:\n\n" % (CFG.get("juma_qoshimcha") or 0)
            + "\n\n".join(kitob_matn(k) for k in kitoblar[:8])
            + "\n\n📍 %s\n🕘 %s" % (e(DOKON.get("manzil")), e(DOKON.get("ish_vaqti"))))
    return tarqat(db, matn)


def statistika(db):
    mij = [m for m in db["mijozlar"].values() if m.get("royxatda")]
    hafta = time.time() - 7 * 86400
    oy = time.time() - 30 * 86400
    qator = ["📊 <b>Statistika</b>",
             "Mijozlar: <b>%d</b> (shu hafta +%d)"
             % (len(mij), sum(1 for m in mij if (m.get("royxat_vaqti") or 0) > hafta))]

    xar = [x for x in db["xaridlar"] if x["t"] > oy]
    qator.append("Xaridlar (30 kun): %d ta, %s" % (len(xar), som(sum(x["summa"] for x in xar))))

    janr = Counter(j for m in mij for j in (m.get("janrlar") or []))
    if janr:
        qator.append("\n📚 <b>Yoqtirilgan janrlar</b>")
        qator += ["%s — %d" % (e(j), n) for j, n in janr.most_common(10)]

    for s in SOROV:
        c = Counter((m.get("sorovnoma") or {}).get(s["savol"]) for m in mij)
        c.pop(None, None)
        if c:
            qator.append("\n📝 <b>%s</b>" % e(s["savol"]))
            qator += ["%s — %d" % (e(v), n) for v, n in c.most_common()]

    qid = [q for q in db["qidiruv"] if q["t"] > oy]
    kop = Counter(norm(q["q"]) for q in qid)
    if kop:
        qator.append("\n🔎 <b>Eng ko'p qidirilgan (30 kun)</b>")
        qator += ["%s — %d" % (e(q), n) for q, n in kop.most_common(10)]
    yoq = Counter(norm(q["q"]) for q in qid if not q["bor"])
    if yoq:
        qator.append("\n❗️ <b>So'ralgan, lekin yo'q — buyurtma qiling</b>")
        qator += ["%s — %d" % (e(q), n) for q, n in yoq.most_common(10)]
    qator.append("\nKitob kelishini kutayotganlar: %d ta so'rov" % len(db["kutish"]))
    return "\n".join(qator)


def admin(chat, text, db):
    """Admin buyrug'i bo'lsa, bajaradi va True qaytaradi."""
    buyruq, _, qolgan = text.partition(" ")
    buyruq = buyruq.split("@")[0].lower()
    qolgan = qolgan.strip()
    kat = db["katalog"]

    if buyruq in ("/yordam", "/admin"):
        send(chat, YORDAM)

    elif buyruq == "/xarid":
        tel, qolgan = tel_ajrat(qolgan)
        q = [tel] + qolgan.split(maxsplit=1)
        summa = son(q[1]) if len(q) > 1 else None
        if not tel or summa is None:
            send(chat, "Foydalanish: <code>/xarid 901234567 350000 [izoh]</code>")
            return True
        cid, m = mijoz_top(db, q[0])
        db["xaridlar"].append({"tel": raqam(q[0]), "summa": summa, "chat": cid,
                               "izoh": q[2] if len(q) > 2 else "", "t": int(time.time())})
        if not m:
            send(chat, "Xarid yozildi. Bu raqam botda ro'yxatdan o'tmagan — sovg'a xabari "
                       "yuborilmadi. Mijozga botni tavsiya qiling 🙂")
            return True
        sov = next(r["sovga"] for r in sorted(CFG["sovga_qoidalari"], key=lambda r: -r["dan"])
                   if summa >= r["dan"])
        kod = sovga_kodi()
        m.setdefault("sovgalar", []).append(
            {"matn": sov, "kod": kod, "vaqt": int(time.time()), "ishlatildi": False})
        m["xaridlar"] = m.get("xaridlar", 0) + 1
        send(cid, "🎉 <b>Xaridingiz uchun rahmat, %s!</b>\n\nSiz <b>%s</b>ga xarid qildingiz "
                  "va sovg'aga ega bo'ldingiz:\n\n🎁 <b>%s</b>\nKod: <code>%s</code>\n\n"
                  "Keyingi safar kassada kodni ko'rsating.\n\n%s"
             % (e(mijoz_ism(m)), som(summa), e(sov), kod, juma_eslatma()), menyu())
        send(chat, "✅ %s ga sovg'a yuborildi: %s (%s)" % (e(mijoz_ism(m)), e(sov), kod))

    elif buyruq == "/sovga":
        tel, matn = tel_ajrat(qolgan)
        q = [tel, matn]
        if not tel or not matn:
            send(chat, "Foydalanish: <code>/sovga 901234567 Bepul xatcho'p</code>")
            return True
        cid, m = mijoz_top(db, q[0])
        if not m:
            send(chat, "Bu raqamli mijoz topilmadi.")
            return True
        kod = sovga_kodi()
        m.setdefault("sovgalar", []).append(
            {"matn": q[1], "kod": kod, "vaqt": int(time.time()), "ishlatildi": False})
        send(cid, "🎁 <b>%s, sizga sovg'a!</b>\n\n%s\nKod: <code>%s</code> — kassada ko'rsating."
             % (e(mijoz_ism(m)), e(q[1]), kod), menyu())
        send(chat, "✅ Yuborildi: %s (%s)" % (e(mijoz_ism(m)), kod))

    elif buyruq == "/ishlat":
        kod = qolgan.upper()
        for m in db["mijozlar"].values():
            for s in m.get("sovgalar") or []:
                if s["kod"] == kod:
                    if s.get("ishlatildi"):
                        send(chat, "⚠️ Bu kod avval ishlatilgan.")
                    else:
                        s["ishlatildi"] = True
                        send(chat, "✅ %s — %s: %s" % (kod, e(mijoz_ism(m)), e(s["matn"])))
                    return True
        send(chat, "Bunday kod topilmadi.")

    elif buyruq == "/kitoblar":
        qator = ["%d. %s — %s | %s | %s dona" % (k["id"], e(k["nomi"]), e(k.get("muallif")),
                                                 som(k.get("narx") or 0), k.get("soni", 0))
                 + (" | −%d%%" % k["chegirma"] if k.get("chegirma") else "")
                 for k in kat["kitoblar"]]
        send(chat, "\n".join(qator) or "Katalog bo'sh.")

    elif buyruq == "/yangi":
        q = [x.strip() for x in qolgan.split("|")]
        if len(q) < 4 or not q[0] or son(q[3]) is None:
            send(chat, "Foydalanish:\n<code>/yangi Nomi | Muallif | Janr | Narx | Chegirma | Soni</code>\n"
                       "Chegirma va soni ixtiyoriy.")
            return True
        k = next((k for k in kat["kitoblar"] if norm(k["nomi"]) == norm(q[0])), None)
        soni = son(q[5]) if len(q) > 5 else None
        if k is None:
            k = {"id": kat["keyingi_id"], "nomi": q[0], "soni": 0}
            kat["keyingi_id"] += 1
            kat["kitoblar"].append(k)
        k.update(muallif=q[1], janr=q[2], narx=son(q[3]), keldi=int(time.time()),
                 chegirma=(son(q[4]) or 0) if len(q) > 4 else k.get("chegirma", 0))
        k["soni"] = int(k.get("soni") or 0) + (soni if soni is not None else 1)
        kat["keyingi_hafta"] = [x for x in kat["keyingi_hafta"] if norm(x["nomi"]) != norm(k["nomi"])]
        kutgan = kutganlarga_xabar(db, k)
        n = tarqat(db, "🆕 <b>Do'konimizga yangi kitob keldi!</b>\n\n" + kitob_matn(k) +
                   "\n\n" + juma_eslatma(), janr=k["janr"])
        send(chat, "✅ Qo'shildi (id %d). Xabar: %d mijozga, kutganlar: %d" % (k["id"], n, kutgan))

    elif buyruq == "/keladi":
        q = [x.strip() for x in qolgan.split("|")]
        if not q[0]:
            send(chat, "Foydalanish: <code>/keladi Nomi | Muallif | Janr</code>")
            return True
        kat["keyingi_hafta"].append({"nomi": q[0], "muallif": q[1] if len(q) > 1 else "",
                                     "janr": q[2] if len(q) > 2 else ""})
        send(chat, "✅ Keyingi hafta ro'yxatiga qo'shildi (%d ta)." % len(kat["keyingi_hafta"]))

    elif buyruq == "/keladi_tozala":
        kat["keyingi_hafta"] = []
        send(chat, "✅ Keyingi hafta ro'yxati tozalandi.")

    elif buyruq in ("/soni", "/narx", "/chegirma", "/ochir"):
        q = qolgan.split()
        k = kitob_top(db, q[0]) if q else None
        if not k:
            send(chat, "Kitob id sini yozing. Ro'yxat: /kitoblar")
            return True
        if buyruq == "/ochir":
            kat["kitoblar"].remove(k)
            send(chat, "🗑 O'chirildi: %s" % e(k["nomi"]))
            return True
        qiymat = son(q[1]) if len(q) > 1 else None
        if qiymat is None:
            send(chat, "Qiymatni yozing, masalan: <code>%s %d 10</code>" % (buyruq, k["id"]))
            return True
        eski = int(k.get("soni") or 0)
        k[buyruq[1:]] = qiymat
        xabar = ""
        if buyruq == "/soni" and eski == 0 and qiymat > 0:
            xabar = " Kutganlarga xabar: %d" % kutganlarga_xabar(db, k)
        send(chat, "✅ %s: %s = %d.%s" % (e(k["nomi"]), buyruq[1:], qiymat, xabar))

    elif buyruq == "/stat":
        send(chat, statistika(db))

    elif buyruq == "/mijozlar":
        mij = sorted((m for m in db["mijozlar"].values() if m.get("royxatda")),
                     key=lambda m: -(m.get("royxat_vaqti") or 0))
        qator = ["%s — %s — %s" % (e(m.get("ism")), e(m.get("tel")),
                                   e(", ".join(m.get("janrlar") or [])))
                 for m in mij[:60]]
        send(chat, "👥 Mijozlar (%d):\n%s" % (len(mij), "\n".join(qator) or "—"))

    elif buyruq == "/tarqat":
        if not qolgan:
            send(chat, "Foydalanish: <code>/tarqat Matn</code>")
            return True
        send(chat, "Yuborildi: %d ta" % tarqat(db, e(qolgan)))

    elif buyruq == "/juma":
        send(chat, "Yuborildi: %d ta" % juma_xabari(db))

    else:
        return False
    return True


# ---------------------------------------------------------------- asosiy
def handle(msg, db):
    if msg["chat"].get("type") != "private":
        return                    # guruhlarda javob bermaymiz
    chat = str(msg["chat"]["id"])
    text = (msg.get("text") or "").strip()
    contact = msg.get("contact")
    user = msg.get("from", {})

    if text.startswith("/men"):
        send(chat, "Sizning Telegram ID: <code>%s</code>" % chat)
        return
    if chat in ADMINS and text.startswith("/") and admin(chat, text, db):
        return

    m = db["mijozlar"].setdefault(chat, {"id": chat, "boshlandi": int(time.time())})
    m["tg_ism"] = ((user.get("first_name") or "") + " " + (user.get("last_name") or "")).strip()
    m["username"] = user.get("username", "")

    if text.startswith("/start") or (not m.get("royxatda") and not m.get("qadam")):
        if m.get("royxatda"):
            send(chat, "Qaytganingizdan xursandmiz, <b>%s</b>! 📚\n\nKerakli kitob nomini "
                       "yozing yoki pastdagi tugmalardan foydalaning." % e(mijoz_ism(m)), menyu())
            return
        send(chat, "Assalomu alaykum! 👋\n\n" + dokon_matn() +
             "\n\nKeling, tanishib olaylik — bu bir daqiqa oladi. Keyin sizga yoqadigan "
             "kitoblar, chegirmalar va sovg'alar haqida birinchi bo'lib xabar beramiz.")
        m["qadam"] = "ism"
        savol_ber(chat, m)
        return

    if m.get("qadam") and royxat(chat, m, text, contact, db):
        return

    if text.startswith("/bekor"):
        m["qadam"] = None
        send(chat, "Bosh menyu 👇", menyu())
    elif text == BTN_QIDIR or text.startswith("/qidir"):
        send(chat, "🔎 Kitob nomi yoki muallifini yozing:\n<i>Masalan: O'tkan kunlar</i>")
    elif text == BTN_YANGI or text.startswith("/yangi"):
        send(chat, yangi_kelganlar(db), menyu())
    elif text == BTN_KEYINGI or text.startswith("/keyingi"):
        send(chat, keyingi_hafta(db), menyu())
    elif text == BTN_AKSIYA or text.startswith("/aksiya"):
        send(chat, aksiyalar(db), menyu())
    elif text == BTN_SOVGA or text.startswith("/sovga"):
        send(chat, sovgalarim(m), menyu())
    elif text == BTN_DOKON or text.startswith("/dokon"):
        send(chat, dokon_matn(), menyu())
    elif text and not text.startswith("/"):
        send(chat, qidir(db, chat, text), menyu())
    else:
        send(chat, "Kerakli kitob nomini yozing yoki pastdagi tugmalardan "
                   "foydalaning 👇", menyu())


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        msg = upd.get("message") or upd.get("edited_message")
        if msg:
            try:
                handle(msg, db)
            except Exception as ex:                     # bitta xato botni to'xtatmasin
                print("xato:", repr(ex), file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Boshlash / ro'yxatdan o'tish"},
        {"command": "qidir", "description": "Kitob bormi?"},
        {"command": "yangi", "description": "Yangi kelgan kitoblar"},
        {"command": "keyingi", "description": "Keyingi hafta keladigan kitoblar"},
        {"command": "aksiya", "description": "Aksiyalar (juma — eng ko'p)"},
        {"command": "sovga", "description": "Sovg'alarim"},
        {"command": "dokon", "description": "Do'kon haqida"},
    ])
    r2 = call("setMyDescription", description=(
        "%s — %s\n\nKitob bormi-yo'qmi va narxini biling, yangi kitoblar va juma "
        "aksiyalaridan birinchi bo'lib xabardor bo'ling, har xariddan sovg'a oling."
        % (DOKON["nomi"], DOKON.get("shior", "")))[:512])
    r3 = call("setMyShortDescription", short_description=(
        "%s: kitoblar, narxlar, aksiyalar va sovg'alar" % DOKON["nomi"])[:120])
    me = call("getMe").get("result", {})
    print("bot: @%s" % me.get("username", "?"))
    print("buyruqlar:", r1.get("ok"), "| tavsif:", r2.get("ok"), r3.get("ok"))
    return all(x.get("ok") for x in (r1, r2, r3))


def main(argv):
    if not TOKEN:
        sys.exit("BOT_TOKEN o'zgaruvchisini kiriting.")
    db = load()

    if "--setup" in argv:
        sys.exit(0 if setup() else 1)

    if "--katalog" in argv:
        katalog_yukla(db)
        save(db)
        print("Katalog dokon.json dan yuklandi: %d ta kitob" % len(db["katalog"]["kitoblar"]))
        return

    if "--juma" in argv:
        print("Juma xabari: %d ta" % juma_xabari(db))
        return

    if "--broadcast" in argv:
        i = argv.index("--broadcast")
        body = argv[i + 1] if len(argv) > i + 1 else ""
        if not body.strip():
            sys.exit("Matn bo'sh.")
        print("Yuborildi: %d ta" % tarqat(db, e(body)))
        return

    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        save(db)
        print("qayta ishlandi: %d ta, mijozlar: %d" % (len(r.get("result", [])), len(db["mijozlar"])))
        return

    setup()
    offset = 0
    print("Bot ishga tushdi. Mijozlar:", len(db["mijozlar"]))
    while True:
        r = call("getUpdates", offset=offset, timeout=60, allowed_updates=["message"])
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
            save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

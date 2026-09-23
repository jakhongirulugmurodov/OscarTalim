#!/usr/bin/env python3
"""
Kitob do'koni — Telegram bot.

Mijoz uchun:
  1. Ro'yxatdan o'tish: ism-familiya, telefon raqam, yoqtirgan janrlar
  2. So'rovnoma (dokon.json → "sorovnoma")
  3. Kitob qidirish: bor bo'lsa — narxi va chegirmasi; yo'q bo'lsa —
     keyingi hafta qaysi kitoblar kelishi va "kelganda xabar bering" tugmasi
  4. Yangi kitoblar, chegirmalar, Juma aksiyalari, keyingi hafta keladiganlar
  5. Sovg'alar: xarid qilgandan keyin bot sovg'a haqida xabar yuboradi
  6. Do'kon haqida: manzil, ish vaqti, telefon, xarita

Do'kon egasi (ADMIN_IDS) uchun — /admin buyrug'ida to'liq ro'yxat:
  /kitob, /chegirma, /juma, /keladi, /xarid, /sovga, /kod, /xabar, /stat

Rejimlar:
    python3 bot.py                      # doimiy (server bo'lsa): long polling
    python3 bot.py --once               # GitHub Actions: kelgan xabarlarni
                                        #   qayta ishlab chiqib ketadi
    python3 bot.py --setup              # buyruqlar va tavsif
    python3 bot.py --juma               # Juma aksiyalarini hammaga yuborish
    python3 bot.py --broadcast "matn"   # hammaga xabar

Muhit o'zgaruvchilari:
    BOT_TOKEN     BotFather bergan token
    ADMIN_IDS     do'kon egasi/sotuvchilarning Telegram ID lari, vergul bilan
    STATE_FILE    holat fayli (ixtiyoriy, standart: kitob_bot/state.json)
    DOKON_FILE    do'kon sozlamalari (ixtiyoriy, standart: kitob_bot/dokon.json)
"""

import difflib
import html
import json
import os
import random
import re
import string
import sys
import time
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMINS = {x.strip() for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
STORE = os.environ.get("STATE_FILE") or os.path.join(HERE, "state.json")
DOKON_FILE = os.environ.get("DOKON_FILE") or os.path.join(HERE, "dokon.json")
API = "https://api.telegram.org/bot%s/" % TOKEN

with open(DOKON_FILE, encoding="utf-8") as _f:
    CFG = json.load(_f)
DOKON = CFG["dokon"]
JANRLAR = CFG["janrlar"]
SOROV = CFG["sorovnoma"]

BTN_QIDIR = "🔎 Китоб излаш"
BTN_YANGI = "🆕 Янги китоблар"
BTN_CHEGIRMA = "🏷 Чегирмалар"
BTN_JUMA = "🎉 Жума акциялари"
BTN_KELADI = "📅 Кейинги ҳафта"
BTN_SOVGA = "🎁 Совғаларим"
BTN_DOKON = "🏪 Дўкон ҳақида"
BTN_SOROV = "📝 Сўровнома"
BTN_JANR = "📚 Жанрларим"

YANGI_KUN = 14          # necha kun ichida qo'shilgan kitob "yangi" hisoblanadi


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


# ---------------------------------------------------------------- saqlash
def load():
    try:
        with open(STORE, encoding="utf-8") as f:
            db = json.load(f)
    except (OSError, ValueError):
        db = {}
    db.setdefault("users", {})
    if "kitoblar" not in db:                  # birinchi ishga tushish: dokon.json'dan
        db["kitoblar"] = {}
        now = int(time.time())
        for k in CFG.get("kitoblar", []):
            db["kitoblar"][norm(k["nom"])] = dict(k, chegirma=0, juma=0, qoshildi=now - 86400 * 30)
    if "keladi" not in db:
        db["keladi"] = list(CFG.get("keladi", []))
    return db


def save(db):
    os.makedirs(os.path.dirname(os.path.abspath(STORE)), exist_ok=True)
    tmp = STORE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STORE)


# ---------------------------------------------------------------- yordamchi
_KIRIL = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяўқғҳ",
                  ["a", "b", "v", "g", "d", "e", "yo", "j", "z", "i", "y", "k", "l", "m",
                   "n", "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sh",
                   "", "i", "", "e", "yu", "ya", "o", "k", "g", "h"]))


def norm(s):
    """Qidiruv uchun: kirill/lotin farqi, tutuq belgisi, q/k, x/h farqlari yo'qoladi."""
    s = "".join(_KIRIL.get(ch, ch) for ch in str(s).lower())
    s = s.replace("q", "k").replace("x", "h")
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return " ".join(s.split())


def tel_norm(s):
    d = re.sub(r"\D", "", str(s))
    return d[-9:] if len(d) >= 9 else d


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " сўм"


def narx_matn(k):
    ch = k.get("juma") or k.get("chegirma") or 0
    if ch:
        yangi = round(k["narx"] * (100 - ch) / 100 / 1000) * 1000
        return "<s>%s</s> → <b>%s</b> (−%d%%)" % (som(k["narx"]), som(yangi), ch)
    return "<b>%s</b>" % som(k["narx"])


def kitob_qator(k, narx=True):
    s = "📖 <b>%s</b> — %s" % (e(k["nom"]), e(k.get("muallif")))
    if narx and "narx" in k:
        s += "\n     " + narx_matn(k)
    return s


def admin(chat):
    return chat in ADMINS


def menu(u):
    rows = [[{"text": BTN_QIDIR}],
            [{"text": BTN_YANGI}, {"text": BTN_CHEGIRMA}],
            [{"text": BTN_JUMA}, {"text": BTN_KELADI}],
            [{"text": BTN_SOVGA}, {"text": BTN_DOKON}]]
    if not u.get("sorov_tugadi"):
        rows.append([{"text": BTN_SOROV}, {"text": BTN_JANR}])
    else:
        rows.append([{"text": BTN_JANR}])
    return {"keyboard": rows, "resize_keyboard": True}


def args(text):
    """'/buyruq a | b | c' → ['a', 'b', 'c']"""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return []
    return [x.strip() for x in parts[1].split("|")]


def kitob_top(db, soz):
    """Nomi yoki muallifi bo'yicha kitoblarni topadi (avval aniq, keyin o'xshash)."""
    q = norm(soz)
    if not q:
        return []
    kitoblar = list(db["kitoblar"].values())
    topildi = [k for k in kitoblar
               if all(t in norm(k["nom"] + " " + k.get("muallif", "")) for t in q.split())]
    if topildi:
        return topildi
    nomlar = {norm(k["nom"]): k for k in kitoblar}
    return [nomlar[n] for n in difflib.get_close_matches(q, list(nomlar), n=3, cutoff=0.6)]


def keladi_top(db, soz):
    q = norm(soz)
    return [k for k in db["keladi"]
            if q and (q in norm(k["nom"] + " " + k.get("muallif", ""))
                      or difflib.SequenceMatcher(None, q, norm(k["nom"])).ratio() > 0.7)]


def keladi_matn(db):
    if not db["keladi"]:
        return "Кейинги ҳафта келадиган китоблар рўйхати ҳали тайёр эмас."
    lines = ["📅 <b>Кейинги ҳафта келадиган китоблар:</b>", ""]
    for k in db["keladi"]:
        lines.append("📦 <b>%s</b> — %s%s" % (e(k["nom"]), e(k.get("muallif")),
                                             (" (%s)" % e(k["sana"])) if k.get("sana") else ""))
    return "\n".join(lines)


def reg_tugadimi(u):
    return bool(u.get("ism") and u.get("tel") and u.get("janr_tugadi"))


# ---------------------------------------------------------------- ro'yxatdan o'tish
def janr_klaviatura(u):
    tanlangan = set(u.get("janrlar", []))
    rows, row = [], []
    for i, j in enumerate(JANRLAR):
        row.append({"text": ("✅ " if j in tanlangan else "") + j, "callback_data": "j:%d" % i})
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "✔️ Тайёр", "callback_data": "j:ok"}])
    return {"inline_keyboard": rows}


def janr_sora(chat, u):
    send(chat, "📚 Қайси жанрдаги китобларни яхши кўрасиз? Бир нечтасини танланг, "
               "кейин <b>«Тайёр»</b>ни босинг.\n\nШу жанрларда янги китоб ёки "
               "чегирма бўлса, сизга биринчилардан бўлиб хабар берамиз.",
         janr_klaviatura(u))


def sorov_sora(chat, u, i):
    if i >= len(SOROV):
        u["sorov_tugadi"] = True
        u["qadam"] = None
        send(chat, "🙏 Раҳмат! Жавобларингиз дўконимизни яхшилашга ёрдам беради.", menu(u))
        return
    u["qadam"] = "sorov"
    q = SOROV[i]
    kb = [[{"text": j, "callback_data": "s:%d:%d" % (i, a)}] for a, j in enumerate(q["javoblar"])]
    kb.append([{"text": "⏭ Кейинроқ", "callback_data": "s:skip"}])
    send(chat, "📝 <b>Сўровнома (%d/%d)</b>\n\n%s" % (i + 1, len(SOROV), e(q["savol"])),
         {"inline_keyboard": kb})


def roxatdan_otdi(chat, u, db):
    """Janrlar tanlangandan keyin: xush kelibsiz sovg'asi va so'rovnoma."""
    matn = ("🎉 <b>%s</b>, рўйхатдан ўтдингиз!\n\nЭнди китоб излашингиз, янги китоблар, "
            "чегирмалар ва жума акциялари ҳақида биринчилардан бўлиб билишингиз мумкин."
            % e(u["ism"]))
    if CFG.get("xush_kelibsiz_sovga") and not u.get("sovgalar"):
        s = sovga_ber(u, CFG["xush_kelibsiz_sovga"])
        matn += ("\n\n🎁 Сизга совғамиз: <b>%s</b>\nКод: <code>%s</code> — кассада айтинг."
                 % (e(s["matn"]), s["kod"]))
    send(chat, matn, menu(u))
    if SOROV and not u.get("sorov_tugadi"):
        sorov_sora(chat, u, 0)


# ---------------------------------------------------------------- sovg'alar
def sovga_ber(u, matn):
    kod = "KB" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
    s = {"matn": matn, "kod": kod, "sana": time.strftime("%d.%m.%Y"), "ishlatildi": False}
    u.setdefault("sovgalar", []).append(s)
    return s


def foydalanuvchi_tel(db, tel):
    t = tel_norm(tel)
    if not t:
        return None, None
    for chat, u in db["users"].items():
        if tel_norm(u.get("tel", "")) == t:
            return chat, u
    return None, None


# ---------------------------------------------------------------- tarqatish
def tarqat(db, text, kimga=None):
    """kimga(u) → True bo'lsa yuboradi. Yuborilganlar sonini qaytaradi."""
    n = 0
    for chat, u in db["users"].items():
        if not reg_tugadimi(u) or (kimga and not kimga(u)):
            continue
        if send(chat, text).get("ok"):
            n += 1
        time.sleep(0.05)              # Telegram cheklovi: ~30 xabar/soniya
    return n


def janr_egalari(janr):
    return lambda u: not u.get("janrlar") or janr in u.get("janrlar", [])


def juma_matn(db):
    ak = [k for k in db["kitoblar"].values() if k.get("juma")]
    if not ak:
        return None
    lines = ["🎉 <b>ЖУМА АКЦИЯСИ!</b>", "",
             "Бугун, жума куни, «%s»да қуйидаги китобларга махсус чегирма:" % e(DOKON["nom"]), ""]
    lines += [kitob_qator(k) for k in ak]
    lines += ["", "📍 %s" % e(DOKON["manzil"]), "🕘 %s" % e(DOKON["ish_vaqti"]),
              "", "Акция фақат бугун амал қилади — шошилинг! 📚"]
    return "\n".join(lines)


# ---------------------------------------------------------------- mijoz bo'limlari
def qidir(chat, u, db, soz):
    u["oxirgi_qidiruv"] = soz
    top = kitob_top(db, soz)
    bor = [k for k in top if k.get("soni", 0) > 0]
    if bor:
        lines = ["✅ <b>Бор!</b>", ""]
        for k in bor:
            lines.append(kitob_qator(k))
            lines.append("     Жанр: %s · Омборда: %d дона" % (e(k.get("janr")), k["soni"]))
        lines += ["", "📍 %s\n📞 %s" % (e(DOKON["manzil"]), e(DOKON["telefon"]))]
        send(chat, "\n".join(lines), menu(u))
        return

    kelyapti = keladi_top(db, soz)
    if kelyapti:
        k = kelyapti[0]
        send(chat, "⏳ <b>%s</b> ҳозир йўқ, лекин <b>%s</b> келади!\n\n"
                   "Келганда сизга хабар берайликми?" % (e(k["nom"]), e(k.get("sana") or "яқинда")),
             {"inline_keyboard": [[{"text": "🔔 Келганда хабар беринг", "callback_data": "w"}]]})
        return

    if top:
        matn = "😔 <b>%s</b> ҳозир тугаган." % e(top[0]["nom"])
    else:
        matn = "😔 Афсуски, «%s» ҳозир дўконимизда йўқ." % e(soz)
    send(chat, matn + "\n\n" + keladi_matn(db) +
         "\n\nСиз излаган китоб келса, дарҳол хабар берамиз 👇",
         {"inline_keyboard": [[{"text": "🔔 Келганда хабар беринг", "callback_data": "w"}]]})


def yangi_kitoblar(chat, u, db):
    chegara = time.time() - YANGI_KUN * 86400
    ks = sorted((k for k in db["kitoblar"].values()
                 if k.get("qoshildi", 0) >= chegara and k.get("soni", 0) > 0),
                key=lambda k: -k.get("qoshildi", 0))
    if not ks:
        send(chat, "Сўнгги кунларда янги китоб келмади. Кейинги ҳафта келадиганлар:\n\n"
                   + keladi_matn(db), menu(u))
        return
    send(chat, "🆕 <b>Янги келган китоблар:</b>\n\n" + "\n".join(kitob_qator(k) for k in ks[:20]),
         menu(u))


def chegirmalar(chat, u, db):
    ks = [k for k in db["kitoblar"].values() if k.get("chegirma") and k.get("soni", 0) > 0]
    if not ks:
        send(chat, "Ҳозир чегирмадаги китоб йўқ. Жума кунлари акциялар бўлади — "
                   "кузатиб боринг! 🎉", menu(u))
        return
    send(chat, "🏷 <b>Чегирмадаги китоблар:</b>\n\n" + "\n".join(kitob_qator(k) for k in ks), menu(u))


def juma_bolim(chat, u, db):
    m = juma_matn(db)
    if m:
        send(chat, m, menu(u))
    else:
        send(chat, "🎉 <b>Жума акциялари</b>\n\nҲар жума куни танланган китобларга махсус "
                   "чегирма қиламиз. Бу жумадаги акция рўйхати ҳали эълон қилинмади — "
                   "жума куни эрталаб ботга хабар келади.", menu(u))


def sovgalarim(chat, u):
    ss = [s for s in u.get("sovgalar", []) if not s.get("ishlatildi")]
    if not ss:
        send(chat, "🎁 Ҳозир фаол совғангиз йўқ.\n\nДўконимиздан китоб харид қилинг — "
                   "ҳар бир харид учун совға оласиз! Ҳар %d-харидда эса катта совға 😉"
             % CFG.get("har_nechinchi_xarid", 5), menu(u))
        return
    lines = ["🎁 <b>Сизнинг совғаларингиз:</b>", ""]
    for s in ss:
        lines.append("• %s\n   Код: <code>%s</code> (%s)" % (e(s["matn"]), s["kod"], s["sana"]))
    lines += ["", "Совғадан фойдаланиш учун кассада кодни айтинг."]
    send(chat, "\n".join(lines), menu(u))


def dokon_haqida(chat, u):
    d = DOKON
    lines = ["🏪 <b>%s</b>" % e(d["nom"])]
    if d.get("shior"):
        lines.append("<i>%s</i>" % e(d["shior"]))
    lines += ["", e(d.get("haqida")), "",
              "📍 <b>Манзил:</b> %s" % e(d["manzil"]),
              "🕘 <b>Иш вақти:</b> %s" % e(d["ish_vaqti"]),
              "📞 <b>Телефон:</b> %s" % e(d["telefon"])]
    if d.get("instagram"):
        lines.append("📸 <b>Инстаграм:</b> %s" % e(d["instagram"]))
    if d.get("telegram_kanal"):
        lines.append("📢 <b>Канал:</b> %s" % e(d["telegram_kanal"]))
    lines += ["", "🎉 Жума кунлари — махсус акциялар!",
              "🎁 Ҳар бир харид учун — совға!"]
    send(chat, "\n".join(lines), menu(u))
    if d.get("lat") is not None and d.get("lon") is not None:
        call("sendLocation", chat_id=chat, latitude=d["lat"], longitude=d["lon"])


# ---------------------------------------------------------------- admin
ADMIN_YORDAM = """<b>Дўкон эгаси буйруқлари</b>

<b>Каталог</b>
/kitob Ном | Муаллиф | Жанр | Нарх | Сони — китоб қўшиш ёки янгилаш. Янги китоб бўлса, шу жанрни яхши кўрадиганларга ва кутаётганларга хабар кетади.
/soni Ном | Сони — омбордаги сонни ўзгартириш
/ochir Ном — китобни каталогдан олиб ташлаш
/katalog — бутун каталог

<b>Чегирма ва акция</b>
/chegirma Ном | 20 — 20% чегирма (шу жанр мухлисларига хабар кетади). 0 — чегирмани олиб ташлаш
/juma Ном | 30 — жума акциясига қўшиш (жума куни эрталаб ҳаммага юборилади)
/juma_tozala — жума рўйхатини тозалаш
/juma_yubor — жума акциясини ҳозироқ ҳаммага юбориш

<b>Кейинги ҳафта</b>
/keladi Ном | Муаллиф | Жанр | Қачон — келадиган китоб
/keladi_tozala — рўйхатни тозалаш

<b>Харид ва совға</b>
/xarid +998901234567 | Китоб номи — харидни ёзиш: мижозга совға хабари кетади, омбордан 1 дона айрилади
/sovga +998901234567 | Совға матни — махсус совға юбориш
/kod KBXXXXX — совға кодини текшириш ва «ишлатилди» деб белгилаш

<b>Бошқа</b>
/xabar Матн — барча мижозларга хабар
/stat — мижозлар, жанрлар ва сўровнома натижалари
/men — Телеграм ID'ингиз"""


def kitob_ber(db, nom):
    top = db["kitoblar"].get(norm(nom))
    if top:
        return top
    t = kitob_top(db, nom)
    return t[0] if len(t) == 1 else None


def xabar_yangi_kitob(db, k):
    """Yangi kitob kelganda: kutganlarga alohida, janr muxlislariga umumiy xabar."""
    kn = norm(k["nom"])
    n = 0
    for chat, u in db["users"].items():
        if not reg_tugadimi(u):
            continue
        kutgan = [w for w in u.get("kutish", [])
                  if norm(w) and (norm(w) in kn or kn in norm(w)
                                  or difflib.SequenceMatcher(None, norm(w), kn).ratio() > 0.7)]
        if kutgan:
            u["kutish"] = [w for w in u["kutish"] if w not in kutgan]
            matn = ("🔔 <b>Сиз кутган китоб келди!</b>\n\n%s\n\nДўконга келинг ёки "
                    "қўнғироқ қилинг: %s" % (kitob_qator(k), e(DOKON["telefon"])))
        elif k.get("janr") in u.get("janrlar", []):
            matn = ("🆕 <b>Дўконимизга янги китоб келди!</b>\n\n%s\n\nСиз яхши кўрадиган "
                    "«%s» жанрида 📚" % (kitob_qator(k), e(k["janr"])))
        else:
            continue
        if send(chat, matn).get("ok"):
            n += 1
        time.sleep(0.05)
    return n


def admin_buyruq(chat, text, db):
    cmd = text.split()[0].split("@")[0].lower()
    a = args(text)

    if cmd == "/admin":
        send(chat, ADMIN_YORDAM)

    elif cmd == "/kitob":
        if len(a) < 4:
            send(chat, "Намуна: <code>/kitob Ўтган кунлар | Абдулла Қодирий | Тарихий | 65000 | 10</code>")
            return
        try:
            narx = int(re.sub(r"\D", "", a[3]))
            soni = int(re.sub(r"\D", "", a[4])) if len(a) > 4 and a[4] else 1
        except ValueError:
            send(chat, "Нарх ва сон рақам бўлиши керак.")
            return
        eski = db["kitoblar"].get(norm(a[0]))
        yangi_keldi = not eski or (eski.get("soni", 0) == 0 and soni > 0)
        k = dict(eski or {}, nom=a[0], muallif=a[1], janr=a[2], narx=narx, soni=soni)
        k.setdefault("chegirma", 0)
        k.setdefault("juma", 0)
        if yangi_keldi:
            k["qoshildi"] = int(time.time())
        db["kitoblar"][norm(a[0])] = k
        db["keladi"] = [x for x in db["keladi"] if norm(x["nom"]) != norm(a[0])]
        javob = "✅ Сақланди:\n" + kitob_qator(k)
        if a[2] not in JANRLAR:
            javob += "\n\n⚠️ «%s» жанри рўйхатда йўқ. Жанрлар: %s" % (e(a[2]), e(", ".join(JANRLAR)))
        if yangi_keldi and soni > 0:
            javob += "\n\n📨 Хабар юборилди: %d та мижозга" % xabar_yangi_kitob(db, k)
        send(chat, javob)

    elif cmd == "/soni":
        k = kitob_ber(db, a[0]) if a else None
        if not k or len(a) < 2:
            send(chat, "Намуна: <code>/soni Ўтган кунлар | 5</code> (китоб номи аниқ бўлсин)")
            return
        eski = k.get("soni", 0)
        k["soni"] = int(re.sub(r"\D", "", a[1]) or 0)
        javob = "✅ «%s»: %d дона" % (e(k["nom"]), k["soni"])
        if eski == 0 and k["soni"] > 0:
            k["qoshildi"] = int(time.time())
            javob += "\n📨 Хабар юборилди: %d та мижозга" % xabar_yangi_kitob(db, k)
        send(chat, javob)

    elif cmd == "/ochir":
        k = kitob_ber(db, a[0]) if a else None
        if not k:
            send(chat, "Китоб топилмади.")
            return
        db["kitoblar"].pop(norm(k["nom"]), None)
        send(chat, "🗑 «%s» каталогдан олиб ташланди." % e(k["nom"]))

    elif cmd == "/katalog":
        ks = sorted(db["kitoblar"].values(), key=lambda k: k.get("janr", ""))
        lines = ["%s — %s, %s, %s дона%s%s" % (e(k["nom"]), e(k.get("muallif")), som(k["narx"]),
                                                k.get("soni", 0),
                                                ", −%d%%" % k["chegirma"] if k.get("chegirma") else "",
                                                ", жума −%d%%" % k["juma"] if k.get("juma") else "")
                 for k in ks]
        matn = "📚 <b>Каталог (%d):</b>\n\n" % len(ks) + "\n".join(lines)
        for i in range(0, len(matn), 4000):
            send(chat, matn[i:i + 4000])

    elif cmd in ("/chegirma", "/juma"):
        k = kitob_ber(db, a[0]) if a else None
        if not k or len(a) < 2:
            send(chat, "Намуна: <code>%s Алкимёгар | 20</code> (китоб номи аниқ бўлсин)" % cmd)
            return
        foiz = max(0, min(90, int(re.sub(r"\D", "", a[1]) or 0)))
        if cmd == "/juma":
            k["juma"] = foiz
            send(chat, "🎉 Жума акцияси: «%s» −%d%%. Жума куни эрталаб ҳаммага юборилади "
                       "(ҳозир юбориш учун /juma_yubor)." % (e(k["nom"]), foiz))
            return
        k["chegirma"] = foiz
        if not foiz:
            send(chat, "Чегирма олиб ташланди: «%s»." % e(k["nom"]))
            return
        n = tarqat(db, "🏷 <b>ЧЕГИРМА!</b>\n\n%s\n\nДўконимизга келинг: %s"
                   % (kitob_qator(k), e(DOKON["manzil"])), janr_egalari(k.get("janr")))
        send(chat, "✅ «%s» −%d%%. Хабар юборилди: %d та мижозга." % (e(k["nom"]), foiz, n))

    elif cmd == "/juma_tozala":
        for k in db["kitoblar"].values():
            k["juma"] = 0
        send(chat, "Жума акцияси рўйхати тозаланди.")

    elif cmd == "/juma_yubor":
        m = juma_matn(db)
        if not m:
            send(chat, "Жума акциясида китоб йўқ. Аввал: <code>/juma Ном | 30</code>")
            return
        send(chat, "📨 Юборилди: %d та мижозга" % tarqat(db, m))

    elif cmd == "/keladi":
        if not a or not a[0]:
            send(chat, "Намуна: <code>/keladi Сапиенс | Юваль Ной Харари | Илмий-оммабоп | душанба</code>")
            return
        db["keladi"] = [x for x in db["keladi"] if norm(x["nom"]) != norm(a[0])]
        db["keladi"].append({"nom": a[0], "muallif": a[1] if len(a) > 1 else "",
                             "janr": a[2] if len(a) > 2 else "", "sana": a[3] if len(a) > 3 else ""})
        send(chat, "✅ Қўшилди.\n\n" + keladi_matn(db))

    elif cmd == "/keladi_tozala":
        db["keladi"] = []
        send(chat, "Кейинги ҳафта рўйхати тозаланди.")

    elif cmd in ("/xarid", "/sovga"):
        if not a or not a[0]:
            send(chat, "Намуна: <code>%s +998901234567 | %s</code>"
                 % (cmd, "Ўтган кунлар" if cmd == "/xarid" else "Кейинги харидга 10% чегирма"))
            return
        uid, u = foydalanuvchi_tel(db, a[0])
        if not u:
            send(chat, "❗ Бу рақам ботда рўйхатдан ўтмаган. Мижозга ботга киришни таклиф қилинг.")
            return
        izoh = ""
        if cmd == "/sovga":
            if len(a) < 2 or not a[1]:
                send(chat, "Совға матнини ёзинг.")
                return
            matn = a[1]
            sarlavha = "🎁 <b>Сизга совға!</b>"
        else:
            u["xaridlar"] = u.get("xaridlar", 0) + 1
            k = kitob_ber(db, a[1]) if len(a) > 1 and a[1] else None
            if k and k.get("soni", 0) > 0:
                k["soni"] -= 1
                izoh = " («%s»: омборда %d қолди)" % (e(k["nom"]), k["soni"])
            har = CFG.get("har_nechinchi_xarid") or 0
            if har and u["xaridlar"] % har == 0:
                matn = CFG["katta_sovga"]
                sarlavha = "🏆 <b>Бу сизнинг %d-харидингиз — катта совға!</b>" % u["xaridlar"]
            else:
                matn = random.choice(CFG["sovgalar"])
                sarlavha = "🎁 <b>Харидингиз учун раҳмат! Сиз совғага эга бўлдингиз!</b>"
        s = sovga_ber(u, matn)
        r = send(uid, "%s\n\n%s\n\nКод: <code>%s</code>\nКейинги сафар кассада шу кодни айтинг. "
                      "Барча совғалар: «%s»." % (sarlavha, e(matn), s["kod"], BTN_SOVGA), menu(u))
        send(chat, "%s %s — %s: «%s», код <code>%s</code>%s"
             % ("✅" if r.get("ok") else "⚠️ (етказилмади)", e(u.get("ism")), e(u.get("tel")),
                e(matn), s["kod"], izoh))

    elif cmd == "/kod":
        kod = (a[0] if a else "").upper().replace(" ", "")
        for uid, u in db["users"].items():
            for s in u.get("sovgalar", []):
                if s["kod"] == kod:
                    if s.get("ishlatildi"):
                        send(chat, "⚠️ Бу код аввал ишлатилган (%s)." % e(s.get("ishlatildi")))
                        return
                    s["ishlatildi"] = time.strftime("%d.%m.%Y %H:%M")
                    send(chat, "✅ Код тўғри: <b>%s</b>\nМижоз: %s, %s\nЭнди «ишлатилди» деб белгиланди."
                         % (e(s["matn"]), e(u.get("ism")), e(u.get("tel"))))
                    send(uid, "✅ Совғангиздан фойдаландингиз: <b>%s</b>. Харидингиз учун раҳмат!"
                         % e(s["matn"]))
                    return
        send(chat, "❌ Бундай код топилмади.")

    elif cmd == "/xabar":
        body = text.split(maxsplit=1)[1].strip() if len(text.split(maxsplit=1)) > 1 else ""
        if not body:
            send(chat, "Намуна: <code>/xabar Эртага дўконимиз 10:00 дан очилади</code>")
            return
        send(chat, "📨 Юборилди: %d та мижозга" % tarqat(db, e(body)))

    elif cmd == "/stat":
        us = [u for u in db["users"].values() if reg_tugadimi(u)]
        lines = ["📊 <b>Статистика</b>", "",
                 "Ботга кирганлар: %d" % len(db["users"]),
                 "Рўйхатдан ўтганлар: %d" % len(us),
                 "Жами харидлар: %d" % sum(u.get("xaridlar", 0) for u in us),
                 "", "<b>Жанрлар:</b>"]
        for j in sorted(JANRLAR, key=lambda j: -sum(j in u.get("janrlar", []) for u in us)):
            lines.append("  %s — %d" % (e(j), sum(j in u.get("janrlar", []) for u in us)))
        for i, q in enumerate(SOROV):
            lines += ["", "<b>%s</b>" % e(q["savol"])]
            for a_i, j in enumerate(q["javoblar"]):
                n = sum(1 for u in us if u.get("sorov", {}).get(str(i)) == a_i)
                lines.append("  %s — %d" % (e(j), n))
        send(chat, "\n".join(lines))

    else:
        return False
    return True


ADMIN_CMDS = {"/admin", "/kitob", "/soni", "/ochir", "/katalog", "/chegirma", "/juma",
              "/juma_tozala", "/juma_yubor", "/keladi", "/keladi_tozala", "/xarid",
              "/sovga", "/kod", "/xabar", "/stat"}


# ---------------------------------------------------------------- xabarlar
def handle(msg, db):
    chat = str(msg["chat"]["id"])
    if msg["chat"].get("type") != "private":
        return                    # guruhlarda javob bermaymiz
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {})
    u = db["users"].setdefault(chat, {"id": chat, "since": int(time.time())})
    u["username"] = user.get("username", "")

    if text.startswith("/start"):
        if reg_tugadimi(u):
            send(chat, "Хуш келибсиз, <b>%s</b>! 📚 Қуйидаги тугмалардан фойдаланинг 👇"
                 % e(u["ism"]), menu(u))
            return
        u["qadam"] = "ism"
        send(chat, "Ассалому алайкум! 👋\n\n<b>«%s»</b> ботига хуш келибсиз!\n<i>%s</i>\n\n"
                   "Бу ерда сиз:\n🔎 керакли китоб бор-йўқлигини ва нархини биласиз\n"
                   "🆕 янги китоблар ва 🏷 чегирмалар ҳақида биринчи бўлиб эшитасиз\n"
                   "🎉 жума акцияларидан хабардор бўласиз\n🎁 ҳар бир харид учун совға оласиз\n\n"
                   "Келинг, танишиб оламиз. <b>Исм ва фамилиянгизни</b> ёзинг:"
             % (e(DOKON["nom"]), e(DOKON.get("shior"))), {"remove_keyboard": True})
        return

    if text.startswith("/men"):
        send(chat, "Сизнинг Телеграм ID: <code>%s</code>" % chat)
        return

    if text.startswith("/") and text.split()[0].split("@")[0].lower() in ADMIN_CMDS:
        if admin(chat):
            admin_buyruq(chat, text, db)
        else:
            send(chat, "Бу буйруқ фақат дўкон ходимлари учун.")
        return

    # --- ro'yxatdan o'tish bosqichlari
    qadam = u.get("qadam")
    if qadam is None and not reg_tugadimi(u):
        qadam = u["qadam"] = ("ism" if not u.get("ism") else "tel" if not u.get("tel") else "janr")

    if qadam == "ism":
        if len(text) < 3 or text.startswith("/"):
            send(chat, "Исм ва фамилиянгизни ёзинг, масалан: <i>Алишер Навоий</i>")
            return
        u["ism"] = text[:60]
        u["qadam"] = "tel"
        send(chat, "Танишганимдан хурсандман, <b>%s</b>! 😊\n\nЭнди <b>телефон рақамингизни</b> "
                   "юборинг — пастдаги тугмани босинг ёки ёзинг (масалан, +998 90 123 45 67)."
             % e(u["ism"]),
             {"keyboard": [[{"text": "📱 Рақамни юбориш", "request_contact": True}]],
              "resize_keyboard": True, "one_time_keyboard": True})
        return

    if qadam == "tel":
        contact = msg.get("contact")
        raqam = contact.get("phone_number") if contact else text
        if len(re.sub(r"\D", "", raqam or "")) < 9:
            send(chat, "Телефон рақамни тўлиқ ёзинг ёки «📱 Рақамни юбориш» тугмасини босинг.")
            return
        u["tel"] = "+" + re.sub(r"\D", "", raqam) if len(re.sub(r"\D", "", raqam)) > 9 \
            else "+998" + re.sub(r"\D", "", raqam)
        u["qadam"] = "janr"
        send(chat, "✅ Рақамингиз сақланди.", {"remove_keyboard": True})
        janr_sora(chat, u)
        return

    if qadam == "janr":
        janr_sora(chat, u)
        return

    # --- asosiy menyu
    if text == BTN_QIDIR:
        u["qadam"] = "qidir"
        send(chat, "🔎 Китоб номини ёки муаллифини ёзинг (кирилл ёки лотинда):")
    elif text == BTN_YANGI:
        yangi_kitoblar(chat, u, db)
    elif text == BTN_CHEGIRMA:
        chegirmalar(chat, u, db)
    elif text == BTN_JUMA:
        juma_bolim(chat, u, db)
    elif text == BTN_KELADI:
        send(chat, keladi_matn(db), menu(u))
    elif text == BTN_SOVGA:
        sovgalarim(chat, u)
    elif text == BTN_DOKON:
        dokon_haqida(chat, u)
    elif text == BTN_SOROV:
        sorov_sora(chat, u, 0)
    elif text == BTN_JANR:
        u["qadam"] = None
        janr_sora(chat, u)
    elif text and not text.startswith("/"):
        # tugma bosmay yozilgan har qanday matn — kitob qidiruvi
        u["qadam"] = None
        qidir(chat, u, db, text)
    else:
        send(chat, "Қуйидаги тугмалардан фойдаланинг 👇", menu(u))


def handle_callback(cq, db):
    chat = str(cq["from"]["id"])
    data = cq.get("data", "")
    msg = cq.get("message") or {}
    u = db["users"].setdefault(chat, {"id": chat, "since": int(time.time())})
    javob = None

    if data.startswith("j:"):
        if data == "j:ok":
            if not u.get("janrlar"):
                javob = "Камида битта жанр танланг"
            else:
                call("editMessageReplyMarkup", chat_id=chat, message_id=msg.get("message_id"),
                     reply_markup={"inline_keyboard": []})
                birinchi = not u.get("janr_tugadi")
                u["janr_tugadi"] = True
                u["qadam"] = None
                if birinchi:
                    roxatdan_otdi(chat, u, db)
                else:
                    send(chat, "✅ Жанрларингиз сақланди: %s" % e(", ".join(u["janrlar"])), menu(u))
        else:
            i = int(data[2:])
            if 0 <= i < len(JANRLAR):
                js = u.setdefault("janrlar", [])
                js.remove(JANRLAR[i]) if JANRLAR[i] in js else js.append(JANRLAR[i])
                call("editMessageReplyMarkup", chat_id=chat, message_id=msg.get("message_id"),
                     reply_markup=janr_klaviatura(u))

    elif data.startswith("s:"):
        call("editMessageReplyMarkup", chat_id=chat, message_id=msg.get("message_id"),
             reply_markup={"inline_keyboard": []})
        if data == "s:skip":
            u["qadam"] = None
            send(chat, "Майли, сўровномани кейинроқ «%s» тугмаси орқали тўлдиришингиз мумкин."
                 % BTN_SOROV, menu(u))
        else:
            _, i, a = data.split(":")
            u.setdefault("sorov", {})[i] = int(a)
            javob = "✅ " + SOROV[int(i)]["javoblar"][int(a)]
            sorov_sora(chat, u, int(i) + 1)

    elif data == "w":
        soz = u.get("oxirgi_qidiruv")
        if soz:
            kutish = u.setdefault("kutish", [])
            if soz not in kutish:
                kutish.append(soz)
            javob = "🔔 Келганда хабар берамиз!"
            send(chat, "🔔 «%s» дўконимизга келиши билан сизга хабар берамиз." % e(soz), menu(u))

    call("answerCallbackQuery", callback_query_id=cq["id"], text=javob)


def process(updates, db):
    last = None
    for upd in updates:
        last = upd["update_id"]
        try:
            if upd.get("message"):
                handle(upd["message"], db)
            elif upd.get("callback_query"):
                handle_callback(upd["callback_query"], db)
        except Exception as ex:                          # bitta xato botni to'xtatmasin
            print("xato:", repr(ex), file=sys.stderr)
    return last


def setup():
    r1 = call("setMyCommands", commands=[
        {"command": "start", "description": "Бош меню"},
        {"command": "men", "description": "Телеграм ID'им"},
    ])
    r2 = call("setMyDescription", description=(
        "«%s» боти: китоб бор-йўқлигини ва нархини билинг, янги китоблар, чегирмалар ва "
        "жума акциялари ҳақида биринчи бўлиб эшитинг, ҳар бир харид учун совға олинг!"
        % DOKON["nom"])[:512])
    r3 = call("setMyShortDescription",
              short_description=("%s — китоб излаш, чегирмалар, совғалар" % DOKON["nom"])[:120])
    for a in ADMINS:              # do'kon egasiga admin buyruqlari ham ko'rinsin
        call("setMyCommands", scope={"type": "chat", "chat_id": int(a)}, commands=[
            {"command": "start", "description": "Бош меню"},
            {"command": "admin", "description": "Барча буйруқлар"},
            {"command": "xarid", "description": "Харид → мижозга совға"},
            {"command": "kitob", "description": "Китоб қўшиш/янгилаш"},
            {"command": "chegirma", "description": "Чегирма эълон қилиш"},
            {"command": "juma", "description": "Жума акциясига қўшиш"},
            {"command": "keladi", "description": "Кейинги ҳафта келадиган китоб"},
            {"command": "kod", "description": "Совға кодини текшириш"},
            {"command": "stat", "description": "Статистика"},
        ])
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

    if "--juma" in argv:
        m = juma_matn(db)
        print("Juma aksiyasi:", "yuborildi %d ta" % tarqat(db, m) if m else "ro'yxat bo'sh")
        return

    if "--broadcast" in argv:
        i = argv.index("--broadcast")
        body = argv[i + 1] if len(argv) > i + 1 else ""
        if not body.strip():
            sys.exit("Matn bo'sh.")
        print("Yuborildi: %d ta" % tarqat(db, e(body)))
        return

    upd_turlari = ["message", "callback_query"]
    if "--once" in argv:
        r = call("getUpdates", timeout=0, allowed_updates=upd_turlari)
        last = process(r.get("result", []), db)
        if last is not None:
            call("getUpdates", offset=last + 1, timeout=0)
        save(db)
        print("qayta ishlandi: %d ta, mijozlar: %d" % (len(r.get("result", [])), len(db["users"])))
        return

    # doimiy rejim (o'z serveringiz bo'lsa)
    setup()
    offset = 0
    print("Bot ishga tushdi. Mijozlar:", len(db["users"]))
    while True:
        r = call("getUpdates", offset=offset, timeout=60, allowed_updates=upd_turlari)
        last = process(r.get("result", []), db)
        if last is not None:
            offset = last + 1
            save(db)


if __name__ == "__main__":
    main(sys.argv[1:])

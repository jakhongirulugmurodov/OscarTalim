#!/usr/bin/env python3
"""Sehrli Javon botining sinovlari — Telegram'siz, soxta API bilan.

    python3 sehrli_javon/test_bot.py
"""

import io
import os
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot  # noqa: E402

MIJOZ, ADMIN = "1001", "9009"


class _Html(HTMLParser):
    RUXSAT = {"b", "i", "s", "u", "code", "pre", "a"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stek = []

    def handle_starttag(self, tag, attrs):
        assert tag in self.RUXSAT, "ruxsat etilmagan teg: " + tag
        self.stek.append(tag)

    def handle_endtag(self, tag):
        assert self.stek and self.stek.pop() == tag, "yopilmagan teg: " + tag


def html_tekshir(matn):
    """Telegram HTML: faqat ruxsat etilgan teglar, hammasi yopilgan, <= 4096 belgi."""
    assert len(matn) <= 4096, "xabar juda uzun"
    matn_ = re.sub(r'<a href="https://[^"<>]*">|</a>', "", matn)
    assert "<" not in matn_.replace("<b>", "").replace("</b>", "").replace("<i>", "") \
        .replace("</i>", "").replace("<s>", "").replace("</s>", "").replace("<code>", "") \
        .replace("</code>", ""), "escape qilinmagan '<': " + matn[:200]
    p = _Html()
    p.feed(matn)
    p.close()
    assert not p.stek, "yopilmagan teglar: %s" % p.stek


class Soxta:
    """bot.call o'rniga: yuborilgan hamma narsani yozib boradi."""

    def __init__(self):
        self.log = []

    def __call__(self, method, **p):
        if "text" in p and method in ("sendMessage", "editMessageText"):
            html_tekshir(p["text"])
        if method == "sendPhoto":
            html_tekshir(p["caption"])
            assert len(p["caption"]) <= 1024, "rasm izohi juda uzun"
            self.log.append((method, p))
            return {"ok": True, "result": {"photo": [{"file_id": "kichik"}, {"file_id": "LOGO123"}]}}
        self.log.append((method, p))
        return {"ok": True, "result": {}}

    def matnlar(self):
        return [p.get("text") or p.get("caption", "") for m, p in self.log
                if m in ("sendMessage", "editMessageText", "sendPhoto")]

    def oxirgi(self):
        return self.matnlar()[-1]

    def tugmalar(self):
        for m, p in reversed(self.log):
            kb = p.get("reply_markup")
            if m in ("sendMessage", "editMessageText", "sendPhoto") and kb and "inline_keyboard" in kb:
                return [b["callback_data"] for row in kb["inline_keyboard"] for b in row]
        return []

    def toast(self):
        for m, p in reversed(self.log):
            if m == "answerCallbackQuery":
                return p.get("text") or ""
        return ""


class Sinov(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        bot.STORE = os.path.join(self.tmp, "holat.json")
        bot.ADMINS = {ADMIN}
        self.api = Soxta()
        bot.call = self.api
        self.db = bot.yukla()
        self.uid = 0
        self.xato = io.StringIO()               # process() xatolarni yutadi — ushlab qolamiz
        self._stderr, sys.stderr = sys.stderr, self.xato

    def tearDown(self):
        sys.stderr = self._stderr
        self.assertNotIn("Traceback", self.xato.getvalue(), self.xato.getvalue())

    # -- yordamchilar
    def yoz(self, text, chat=MIJOZ, contact=None):
        self.uid += 1
        msg = {"chat": {"id": int(chat), "type": "private"},
               "from": {"id": int(chat), "first_name": "Aziz", "last_name": "Karimov"},
               "text": text}
        if contact:
            msg["contact"] = contact
            msg.pop("text")
        bot.process(self.db, [{"update_id": self.uid, "message": msg}])

    def bos(self, data, chat=MIJOZ, text=""):
        self.uid += 1
        bot.process(self.db, [{"update_id": self.uid, "callback_query": {
            "id": "cb%d" % self.uid, "data": data, "from": {"id": int(chat), "first_name": "Aziz"},
            "message": {"message_id": 5, "chat": {"id": int(chat), "type": "private"}, "text": text}}}])

    def rasmiylashtir(self, tel="901234567", manzil=None, tolov="naqd", tasdiq=True):
        self.bos("buy")
        self.yoz(tel)
        self.yoz(manzil or bot.B_OLIB)
        self.assertIn("pay:" + tolov, self.api.tugmalar())
        self.bos("pay:" + tolov)
        iz = [d for d in self.api.tugmalar() if d.startswith("ok:")]
        self.assertEqual(len(iz), 1)
        if tasdiq:
            self.bos(iz[0])
        return iz[0]

    def royxat(self, yosh="20", chat=MIJOZ):
        self.yoz("/start", chat)
        self.bos("reg:ism", chat)
        self.yoz("aziz karimov", chat)
        self.yoz(yosh, chat)

    # -- sinovlar
    def test_royxat_ism_va_yosh(self):
        self.yoz("/start")
        self.assertIn("reg:gmail", self.api.tugmalar())
        self.yoz("salom")                                   # ro'yxatsiz — qaytadan taklif
        self.assertIn("reg:ism", self.api.tugmalar())
        self.bos("reg:ism")
        self.yoz("Aziz")                                    # familiyasiz
        self.assertIn("Ism va familiya", self.api.oxirgi())
        self.yoz("aziz karimov")
        self.yoz("3")                                       # yosh noto'g'ri
        self.assertIn("5 dan 100", self.api.oxirgi())
        self.yoz("abc")
        self.yoz("20")
        u = self.db["users"][MIJOZ]
        self.assertTrue(u["royxat"])
        self.assertEqual((u["ism"], u["familiya"], u["yosh"]), ("Aziz", "Karimov", 20))
        self.assertIn("SALOM10", self.api.oxirgi())

    def test_logo(self):
        self.yoz("/start")
        birinchi = [p for m, p in self.api.log if m == "sendPhoto"][-1]
        self.assertEqual(birinchi["_fayl"][1], "logo.png")
        self.assertTrue(birinchi["_fayl"][2].startswith(b"\x89PNG"))
        self.assertEqual(self.db["logo_id"], "LOGO123")
        self.yoz("/start", "2002")                          # ikkinchi marta — qayta yuklanmaydi
        ikkinchi = [p for m, p in self.api.log if m == "sendPhoto"][-1]
        self.assertEqual(ikkinchi.get("photo"), "LOGO123")
        self.assertNotIn("_fayl", ikkinchi)

    def test_royxat_gmail(self):
        self.yoz("/start")
        self.bos("reg:gmail")
        self.yoz("bu-email-emas")
        self.assertIn("e-pochtaga o'xshamayapti", self.api.oxirgi())
        self.yoz("Aziz.Karimov@Gmail.com")
        self.yoz("25")
        u = self.db["users"][MIJOZ]
        self.assertEqual(u["email"], "aziz.karimov@gmail.com")
        self.assertEqual(u["usul"], "gmail")
        self.assertTrue(u["royxat"])

    def test_katalog_va_kitob_sahifasi(self):
        self.royxat()
        self.yoz(bot.B_KATALOG)
        self.assertIn("j:uzbek:0", self.api.tugmalar())
        self.bos("j:uzbek:0")
        self.assertTrue(any(d.startswith("k:b01:uzbek") for d in self.api.tugmalar()))
        self.bos("k:b02:uzbek:0")
        m = self.api.oxirgi()
        self.assertIn("Kecha va kunduz", m)
        self.assertIn("40 800 so'm", m)                     # 48 000 − 15%
        self.assertIn("Bilasizmi", m)
        for k in ("*aksiya", "*top", "*all", "*siz"):
            self.bos("j:%s:0" % k)
        self.bos("j:*all:1")                                # 2-sahifa
        self.bos("rnd")
        self.assertIn("Taqdir", self.api.oxirgi())

    def test_qidiruv(self):
        self.royxat()
        self.yoz("qodiriy")
        self.assertIn("k:b01:-:0", self.api.tugmalar())
        self.yoz("bunaqa kitob yo'q")
        self.assertIn("topilmadi", self.api.oxirgi())

    def test_yosh_cheklovi(self):
        self.royxat(yosh="10")
        self.bos("+:b04:uzbek:0")                           # Shaytanat 18+
        self.assertIn("18+", self.api.toast())
        self.assertEqual(self.db["users"][MIJOZ]["savat"], {})
        self.yoz(bot.B_SIZ)
        self.assertNotIn("k:b04:*siz:0", self.api.tugmalar())

    def test_ombordan_ortiq_olib_bolmaydi(self):
        self.royxat()
        self.db["kitoblar"]["b12"]["soni"] = 2
        for _ in range(3):
            self.bos("+:b12:ilm:0")
        self.assertEqual(self.db["users"][MIJOZ]["savat"]["b12"], 2)
        self.assertIn("faqat 2 dona", self.api.toast())

    def test_promokod_chegaralari(self):
        self.royxat()
        self.yoz(bot.B_PROMO)
        self.yoz("YOQKOD")
        self.assertIn("topilmadi", self.api.oxirgi())
        self.yoz("/bekor")
        # admin 10–50% dan tashqarini qabul qilmaydi
        self.yoz("/promo KATTA 60", ADMIN)
        self.assertNotIn("KATTA", self.db["promo"])
        self.yoz("/promo KICHIK 5", ADMIN)
        self.assertNotIn("KICHIK", self.db["promo"])
        self.yoz("/promo YOZ30 30 1", ADMIN)
        self.assertEqual(self.db["promo"]["YOZ30"]["foiz"], 30)
        self.yoz("/promo ESKI40 40 2000-01-01", ADMIN)
        self.yoz(bot.B_PROMO)
        self.yoz("eski40")
        self.assertIn("muddati", self.api.oxirgi())
        self.yoz("yoz30")
        self.assertEqual(self.db["users"][MIJOZ]["promo"], "YOZ30")

    def test_toliq_xarid_sovga_baho(self):
        self.royxat()
        self.bos("+:b01:uzbek:0")                           # 55 000, aksiyasiz
        self.bos("+:b01:uzbek:0")
        self.bos("+:b05:jahon:0")                           # 42 000, −25%
        self.yoz(bot.B_PROMO)
        self.yoz("DOST20")                                  # 20%
        h = bot.hisob(self.db, self.db["users"][MIJOZ])
        # b01: 20% promokod → 44 000 × 2; b05: aksiya 25% (kattaroq) → 31 500
        self.assertEqual(h["jami"], 44000 * 2 + 31500)
        self.assertIn("🔖 Xatcho'plar to'plami", h["sovgalar"])       # 3 dona
        self.assertNotIn("☕ Kitobxon krujkasi", h["sovgalar"])       # 119 500 < 150 000
        self.bos("cart")
        self.bos("buy")
        self.yoz("123")                                     # noto'g'ri raqam
        self.assertIn("noto'g'ri", self.api.oxirgi())
        self.yoz(None, contact={"phone_number": "998901234567", "user_id": int(MIJOZ)})
        self.yoz("qisqa")
        self.assertIn("batafsilroq", self.api.oxirgi())
        self.yoz("Toshkent, Chilonzor 5-kvartal, 12-uy")
        self.bos("ok:eskiiz")                               # to'lov tanlanmagan — so'raladi
        self.assertEqual(self.db["buyurtmalar"], {})
        self.assertIn("pay:click", self.api.tugmalar())
        self.bos("pay:click")
        izlar = [d for d in self.api.tugmalar() if d.startswith("ok:")]
        self.assertEqual(len(izlar), 1)
        self.bos(izlar[0])
        o = self.db["buyurtmalar"]["1"]
        self.assertEqual(o["jami"], 119500)
        self.assertEqual(o["tel"], "+998901234567")
        self.assertEqual(o["tolov"], "click")
        self.assertTrue(any("rasmiylashtirildi" in m and "#1" in m for m in self.api.matnlar()))
        self.assertEqual(self.db["kitoblar"]["b01"]["soni"], 22)
        self.assertEqual(self.db["kitoblar"]["b01"]["sotildi"], 2)
        self.assertEqual(self.db["users"][MIJOZ]["savat"], {})
        self.assertIn(MIJOZ, self.db["promo"]["DOST20"]["ishlatganlar"])
        self.assertEqual(self.db["promo"]["DOST20"]["qoldi"], 99)
        # adminga xabar ketdi
        self.assertTrue(any(p.get("chat_id") == ADMIN and "Yangi buyurtma" in p.get("text", "")
                            for m, p in self.api.log if m == "sendMessage"))
        # ikkinchi marta bosish — ikkinchi buyurtma bo'lmaydi
        self.bos(izlar[0])
        self.assertEqual(len(self.db["buyurtmalar"]), 1)
        # promokod qayta ishlamaydi
        self.yoz(bot.B_PROMO)
        self.yoz("DOST20")
        self.assertIn("avval ishlatgansiz", self.api.oxirgi())
        self.yoz("/bekor")
        # buyurtma sahifasi va baholash
        self.yoz(bot.B_XARID)
        self.assertIn("o:1", self.api.tugmalar())
        self.bos("o:1")
        self.assertIn("r:b01:1", self.api.tugmalar())
        self.bos("r:b06:1")                                 # sotib olinmagan kitob
        self.assertIn("Faqat sotib olgan", self.api.toast())
        self.bos("r:b01:1")
        self.bos("rs:b01:5:1")
        self.yoz("Juda zo'r kitob, hammaga tavsiya qilaman!")
        b = self.db["kitoblar"]["b01"]
        self.assertEqual(b["baholar"][MIJOZ], 5)
        self.assertEqual(b["sharhlar"][0]["matn"], "Juda zo'r kitob, hammaga tavsiya qilaman!")
        self.bos("sh:b01:uzbek:0")
        self.assertIn("Juda zo'r", self.api.oxirgi())
        self.bos("k:b01:uzbek:0")
        self.assertIn("5.0 (1 baho)", self.api.oxirgi())

    def test_sovga_summa_boyicha(self):
        self.royxat()
        for _ in range(3):
            self.bos("+:b13:fantastika:0")                  # 85 500 × 3 = 256 500
        h = bot.hisob(self.db, self.db["users"][MIJOZ])
        self.assertIn("☕ Kitobxon krujkasi", h["sovgalar"])
        self.assertEqual(h["keyingi"][1], "🎒 Kitob sumkasi + ☕ kitobxon krujkasi")

    def test_savat_ozgarsa_tasdiq_rad(self):
        self.royxat()
        self.bos("+:b01:uzbek:0")
        iz = self.rasmiylashtir(tel="+998 90 123 45 67", tasdiq=False)
        self.bos("+:b03:bolalar:0")                         # tasdiqdan oldin savat o'zgardi
        self.bos(iz)
        self.assertEqual(self.db["buyurtmalar"], {})
        yangi = [d for d in self.api.tugmalar() if d.startswith("ok:")][0]
        self.assertNotEqual(iz, yangi)
        self.bos(yangi)
        self.assertEqual(len(self.db["buyurtmalar"]), 1)

    def test_bekor_qilish_omborga_qaytaradi(self):
        self.royxat()
        self.bos("+:b07:bolalar:0")
        self.yoz(bot.B_PROMO)
        self.yoz("OMBOR50")
        self.rasmiylashtir()
        self.assertEqual(self.db["kitoblar"]["b07"]["soni"], 49)
        self.assertEqual(self.db["buyurtmalar"]["1"]["tel"], "+998901234567")
        self.bos("oc:1")
        self.bos("ocy:1")
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "bekor")
        self.assertEqual(self.db["kitoblar"]["b07"]["soni"], 50)
        self.assertEqual(self.db["promo"]["OMBOR50"]["qoldi"], 20)
        self.assertNotIn(MIJOZ, self.db["promo"]["OMBOR50"]["ishlatganlar"])
        self.bos("ocy:1")                                   # qayta bekor — o'zgarmaydi
        self.assertEqual(self.db["kitoblar"]["b07"]["soni"], 50)

    def test_admin(self):
        self.royxat()
        self.bos("a:home")                                  # mijoz admin emas
        self.assertIn("Faqat admin", self.api.toast())
        self.royxat(chat=ADMIN)
        self.yoz("/admin", ADMIN)
        self.assertIn("Admin panel", self.api.oxirgi())
        self.yoz("/qoldiq b01 3", ADMIN)
        self.assertEqual(self.db["kitoblar"]["b01"]["soni"], 3)
        self.yoz("/narx b01 60000", ADMIN)
        self.yoz("/aksiya b01 50", ADMIN)
        self.assertEqual(bot.narxi(self.db["kitoblar"]["b01"]), 30000)
        self.yoz("/sovga b01 🎁 Daftar", ADMIN)
        self.assertEqual(self.db["kitoblar"]["b01"]["sovga"], "🎁 Daftar")
        self.yoz("/yangi_kitob Yangi kitob | Muallif | ilm | 40000 | 7 | 12 | Zo'r kitob", ADMIN)
        self.assertEqual(self.db["kitoblar"]["b16"]["soni"], 7)
        self.yoz("/yangi_kitob noto'g'ri | janr | yoq | x | y", ADMIN)
        self.assertNotIn("b17", self.db["kitoblar"])
        for d in ("a:o", "a:w", "a:p", "a:slow", "a:ak:b06:30"):
            self.bos(d, ADMIN)
        self.assertEqual(self.db["kitoblar"]["b06"]["aksiya"], 30)
        self.bos("a:bc:b06", ADMIN)
        self.assertTrue(any(p.get("chat_id") == MIJOZ and "Aksiya" in p.get("text", "")
                            for m, p in self.api.log if m == "sendMessage"))
        # buyurtma holatini o'zgartirish
        self.bos("+:b01:uzbek:0")
        self.rasmiylashtir()
        self.bos("a:s:1:yuborildi", ADMIN)                 # avval tasdiqlash kerak
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "yangi")
        self.bos("a:s:1:tasdiqlandi", ADMIN)
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "tasdiqlandi")
        self.bos("oc:1")
        self.bos("ocy:1")                                   # tasdiqlangani mijoz bekor qila olmaydi
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "tasdiqlandi")
        self.bos("a:s:1:yuborildi", ADMIN)
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "yuborildi")
        self.bos("a:s:1:yangi", ADMIN)                      # orqaga qaytib bo'lmaydi
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "yuborildi")
        self.bos("a:s:1:yetkazildi", ADMIN)
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "yetkazildi")
        self.yoz("/xabar Yangi kitoblar keldi!", ADMIN)
        self.assertIn("Yuborildi", self.api.oxirgi())

    def test_saqlash_va_qayta_yuklash(self):
        self.royxat()
        self.bos("+:b01:uzbek:0")
        bot.saqla(self.db)
        db2 = bot.yukla()
        self.assertEqual(db2["users"][MIJOZ]["savat"], {"b01": 1})
        self.assertEqual(len(db2["kitoblar"]), len(self.db["kitoblar"]))

    def test_html_injeksiya(self):
        self.yoz("/start")
        self.bos("reg:ism")
        self.yoz("Ali <b>Valiyev")
        self.yoz("Ali Vali<i>")
        self.bos("reg:gmail")
        self.yoz("a<b>@gmail.com")
        self.yoz("ali@gmail.com")
        self.yoz("20")
        self.yoz("<b>qidiruv")
        self.yoz(bot.B_PROMO)
        self.yoz("<i>kod")

    def test_lokatsiya_va_tolov(self):
        self.royxat()
        self.bos("+:b01:uzbek:0")
        self.bos("pay:naqd")                                # telefonsiz — boshidan so'raladi
        self.assertEqual(self.db["users"][MIJOZ]["qadam"], "tel")
        self.yoz("901234567")
        self.uid += 1
        bot.process(self.db, [{"update_id": self.uid, "message": {
            "chat": {"id": int(MIJOZ), "type": "private"}, "from": {"id": int(MIJOZ), "first_name": "Aziz"},
            "location": {"latitude": 41.311081, "longitude": 69.240562}}}])
        self.bos("pay:karta")
        self.assertIn("xaritada ochish", self.api.oxirgi())
        self.bos([d for d in self.api.tugmalar() if d.startswith("ok:")][0])
        o = self.db["buyurtmalar"]["1"]
        self.assertEqual(o["lokatsiya"], {"lat": 41.311081, "lon": 69.240562})
        self.assertEqual(o["tolov"], "karta")
        self.assertTrue(any(m == "sendLocation" and p["chat_id"] == ADMIN for m, p in self.api.log))
        # keyingi buyurtmada matnli manzil lokatsiyani almashtiradi
        self.bos("+:b03:bolalar:0")
        self.rasmiylashtir(manzil="Samarqand, Registon ko'chasi 1")
        self.assertIsNone(self.db["buyurtmalar"]["2"]["lokatsiya"])

    def test_manba_havola(self):
        self.yoz("/havola Instagram!", ADMIN)
        self.assertIn("Foydalanish", self.api.oxirgi())
        self.yoz("/havola instagram", ADMIN)
        self.assertIn("?start=r_instagram", self.api.oxirgi())
        self.yoz("/start r_instagram")
        self.yoz("/start r_boshqa")                          # birinchi manba saqlanadi
        self.assertEqual(self.db["users"][MIJOZ]["manba"], "instagram")
        self.bos("reg:ism")
        self.yoz("Aziz Karimov")
        self.yoz("20")
        self.bos("+:b05:jahon:0")
        self.rasmiylashtir()
        st = bot.hisobot.statistika(self.db, bot.KAT)
        m = dict(st["manbalar"])
        self.assertEqual(m["instagram"]["xaridor"], 1)
        self.assertEqual(m["instagram"]["tushum"], 31500)

    def test_admin_royxatdan_tasdiqlash_va_hisobotlar(self):
        self.royxat()
        for bid in ("b01", "b05"):
            self.bos("+:%s:x:0" % bid)
            self.rasmiylashtir()
        self.bos("a:o", ADMIN)
        t = self.api.tugmalar()
        self.assertIn("a:s:1:tasdiqlandi:l", t)
        self.assertIn("a:s:2:bekor:l", t)
        self.bos("a:s:1:tasdiqlandi:l", ADMIN)
        self.bos("a:s:2:bekor:l", ADMIN)
        self.assertEqual(self.db["buyurtmalar"]["1"]["holat"], "tasdiqlandi")
        self.assertEqual(self.db["buyurtmalar"]["2"]["holat"], "bekor")
        self.assertEqual(self.db["kitoblar"]["b05"]["soni"], 40)            # omborga qaytdi
        self.assertNotIn("a:s:1:tasdiqlandi:l", self.api.tugmalar())      # ro'yxat yangilandi
        self.assertTrue(any(p.get("chat_id") == MIJOZ and "Tasdiqlandi" in p.get("text", "")
                            for m, p in self.api.log if m == "sendMessage"))
        self.bos("a:m:0", ADMIN)
        self.assertIn("Aziz Karimov", self.api.oxirgi())
        self.bos("a:r", ADMIN)
        m = self.api.oxirgi()
        self.assertIn("55 000 so'm", m)                                   # faqat tasdiqlangani
        self.assertIn("1 / 1000", m)
        self.bos("a:mk", ADMIN)
        fayl = [p for m, p in self.api.log if m == "sendDocument"][-1]
        self.assertEqual(fayl["chat_id"], ADMIN)
        maydon, nom, bayt, mime = fayl["_fayl"]
        self.assertTrue(nom.endswith(".html"))
        self.assertIn(b"marketing tahlili", bayt)
        self.assertIn(b"<svg", bayt)

    def test_multipart(self):
        tana, turi = bot._multipart({"chat_id": "5", "caption": "salom"},
                                    ("document", "a.html", b"<p>x</p>", "text/html"))
        chegara = turi.split("boundary=")[1].encode()
        self.assertTrue(tana.startswith(b"--" + chegara))
        self.assertTrue(tana.endswith(b"--" + chegara + b"--\r\n"))
        self.assertIn(b'name="document"; filename="a.html"', tana)
        self.assertIn(b"<p>x</p>", tana)

    def test_bosh_hisobot(self):
        st = bot.hisobot.statistika(self.db, bot.KAT)
        self.assertEqual(st["tushum"], 0)
        html_tekshir(bot.hisobot.matn_hisobot(st))
        self.assertIn("<svg", bot.hisobot.html_hisobot(st))
        misol = bot.hisobot._misol()
        self.assertGreater(misol["tushum"], 0)
        bot.hisobot.html_hisobot(misol)

    def test_guruhda_jim(self):
        bot.process(self.db, [{"update_id": 1, "message": {
            "chat": {"id": -5, "type": "group"}, "from": {"id": 1}, "text": "/start"}}])
        self.assertEqual(self.api.matnlar(), [])

    def test_callback_data_64_baytdan_oshmaydi(self):
        self.royxat()
        for k in list(bot.KAT["janrlar"]) + ["*aksiya", "*top", "*all", "*siz"]:
            self.bos("j:%s:0" % k)
        for bid in self.db["kitoblar"]:
            self.bos("k:%s:fantastika:9" % bid)
        for m, p in self.api.log:
            kb = p.get("reply_markup") or {}
            for row in kb.get("inline_keyboard", []):
                for b in row:
                    self.assertLessEqual(len(b["callback_data"].encode()), 64)


if __name__ == "__main__":
    unittest.main(verbosity=1)

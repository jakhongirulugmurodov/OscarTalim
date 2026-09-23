"""Kitob boti sinovlari: Telegram o'rniga soxta `call`. Ishga tushirish:
    python3 -m unittest kitob_bot/test_bot.py
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime

os.environ.update(BOT_TOKEN="x", ADMIN_IDS="1", XODIM_KODI="sir",
                  STATE_FILE=os.path.join(tempfile.mkdtemp(), "k.json"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bot  # noqa: E402

YUBORILGAN = []


def soxta_call(method, **p):
    YUBORILGAN.append((method, p))
    if method == "getMe":
        return {"ok": True, "result": {"username": "kitobuz_bot"}}
    return {"ok": True, "result": {}}


bot.call = soxta_call
bot.send_file = lambda chat, name, data, caption="": YUBORILGAN.append(("file", data)) or {"ok": True}
bot.time.sleep = lambda s: None


def xabar(chat, text="", **qo):
    return {"chat": {"id": int(chat), "type": "private"}, "from": {"id": int(chat)}, "text": text, **qo}


def tugma(chat, data):
    return {"id": "c", "data": data, "message": {"chat": {"id": int(chat)}, "message_id": 5}}


def oxirgi():
    return [p.get("text") for m, p in YUBORILGAN if m == "sendMessage"][-1]


class Sinov(unittest.TestCase):
    def setUp(self):
        if os.path.exists(bot.STORE):
            os.remove(bot.STORE)
        self.db = bot.load()
        YUBORILGAN.clear()

    def royxat(self, chat="100", tel="90 123 45 67", ism="aziza karimova"):
        db = self.db
        bot.handle(xabar(chat, "/start"), db)
        bot.handle(xabar(chat, "Salom"), db)                 # ro'yxatsiz — o'tkazilmaydi
        self.assertIn("noto'g'ri", oxirgi())
        bot.handle(xabar(chat, tel), db)
        bot.handle(xabar(chat, "Aziza"), db)                 # familiyasiz
        self.assertIn("familiya", oxirgi())
        bot.handle(xabar(chat, ism), db)
        bot.handle(xabar(chat, "31.02.1998"), db)            # noto'g'ri sana
        self.assertIn("kun.oy.yil", oxirgi())
        bot.handle(xabar(chat, "15.03.1998"), db)
        bot.handle_callback(tugma(chat, "q:tayyor"), db)     # hech narsa tanlanmagan
        self.assertFalse(bot.royxatdan_otgan(db["users"][chat]))
        bot.handle_callback(tugma(chat, "q:badiiy"), db)
        bot.handle_callback(tugma(chat, "q:tarix"), db)
        bot.handle_callback(tugma(chat, "q:tayyor"), db)
        return db["users"][chat]

    def test_royxat(self):
        u = self.royxat()
        self.assertTrue(bot.royxatdan_otgan(u))
        self.assertEqual(u["telefon"], "+998901234567")
        self.assertEqual(u["ism"], "Aziza Karimova")
        self.assertEqual(u["tugilgan"], "1998-03-15")
        self.assertEqual(u["qiziqish"], ["badiiy", "tarix"])
        self.assertTrue(u["kod"].startswith("K"))

    def test_kontakt(self):
        db = self.db
        bot.handle(xabar("200", "/start"), db)
        bot.handle(xabar("200", contact={"phone_number": "998911112233", "user_id": 999}), db)
        self.assertIn("o'zingizning", oxirgi())
        bot.handle(xabar("200", contact={"phone_number": "998911112233", "user_id": 200}), db)
        self.assertEqual(db["users"]["200"]["telefon"], "+998911112233")

    def test_xodim_kitob_va_eslatma(self):
        db = self.db
        u = self.royxat()
        bot.handle(xabar("300", "/xodim notogri"), db)
        self.assertNotIn("300", db["xodimlar"])
        bot.handle(xabar("300", "/xodim sir"), db)
        self.assertIn("300", db["xodimlar"])
        # kitob qo'shish
        bot.handle(xabar("300", bot.B_QOSH), db)
        bot.handle(xabar("300", "O'tkan kunlar — Abdulla Qodiriy"), db)
        bot.handle_callback(tugma("300", "kj:badiiy"), db)
        bot.handle(xabar("300", "85 000"), db)
        bot.handle(xabar("300", "50"), db)                     # 30% dan ko'p — rad
        self.assertEqual(db["kitoblar"], [])
        bot.handle(xabar("300", "25%"), db)
        self.assertEqual(db["kitoblar"][0]["chegirma"], 25)
        bot.handle(xabar("300", bot.B_QOSH), db)
        bot.handle(xabar("300", "Sapiens"), db)
        bot.handle_callback(tugma("300", "kj:ilmiy"), db)
        bot.handle(xabar("300", "120000"), db)
        bot.handle_callback(tugma("300", "kn:10"), db)
        self.assertEqual(len(db["kitoblar"]), 2)
        bot.handle_callback(tugma("300", "kc:2:30"), db)
        self.assertEqual(db["kitoblar"][1]["chegirma"], 30)

        # 2026-09-22 seshanba 09:00 — hali erta (eslatma 25-sentabr 10:00 dan 72 soat oldin)
        YUBORILGAN.clear()
        bot.jadval(db, datetime(2026, 9, 22, 9, 0, tzinfo=bot.TZ))
        self.assertEqual(YUBORILGAN, [])
        bot.jadval(db, datetime(2026, 9, 22, 10, 5, tzinfo=bot.TZ))
        msgs = [p for m, p in YUBORILGAN if m == "sendMessage"]
        self.assertEqual(len(msgs), 1)
        self.assertIn("3 kun qoldi", msgs[0]["text"])
        self.assertIn("Sizga mos", msgs[0]["text"])
        self.assertTrue(msgs[0]["text"].index("O&#x27;tkan") < msgs[0]["text"].index("Sapiens"))
        YUBORILGAN.clear()
        bot.jadval(db, datetime(2026, 9, 22, 10, 10, tzinfo=bot.TZ))   # takror yuborilmaydi
        self.assertEqual(YUBORILGAN, [])
        bot.jadval(db, datetime(2026, 9, 25, 10, 1, tzinfo=bot.TZ))
        self.assertIn("boshlandi", oxirgi())

        # boraman + kelganini belgilash + tahlil + csv
        bot.handle_callback(tugma("100", "rsvp:2026-09-25"), db)
        self.assertEqual(u["rsvp"], ["2026-09-25"])
        bot.oxirgi_aksiya = lambda db, now=None: datetime(2026, 9, 25).date()
        bot.handle(xabar("300", bot.B_KELDI), db)
        bot.handle(xabar("300", u["kod"].lower()), db)
        self.assertEqual(u["keldi"], ["2026-09-25"])
        bot.handle(xabar("300", bot.B_TAHLIL), db)
        self.assertIn("Ro'yxatdan o'tgan: <b>1</b>", oxirgi())
        bot.handle(xabar("300", bot.B_CSV), db)
        fayl = [p for m, p in YUBORILGAN if m == "file"][0].decode("utf-8-sig")
        self.assertIn("Aziza Karimova;+998901234567;15.03.1998;1998", fayl)

        # eslatma muddatini 3 soatga o'zgartirish
        bot.handle_callback(tugma("300", "es:3"), db)
        self.assertEqual(db["aksiya"]["eslatma_soat"], 3)
        bot.save(db)


class Vaqt(unittest.TestCase):
    def test_keyingi_aksiya(self):
        db = bot.load()
        self.assertEqual(str(bot.keyingi_aksiya(db, datetime(2026, 9, 23, 12, tzinfo=bot.TZ))), "2026-09-25")
        self.assertEqual(str(bot.keyingi_aksiya(db, datetime(2026, 9, 25, 19, tzinfo=bot.TZ))), "2026-09-25")
        self.assertEqual(str(bot.keyingi_aksiya(db, datetime(2026, 9, 25, 21, tzinfo=bot.TZ))), "2026-10-02")


if __name__ == "__main__":
    unittest.main()

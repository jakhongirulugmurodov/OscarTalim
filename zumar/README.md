# Zumar kitob do'koni — bot va auditoriya rejasi

## Muammo

- Zumar kitob do'koniga Instagram va Telegram'da auditoriya yig'ish kerak.
- Do'konda **MUQADDIMA** kitobidan **100 dona** bor — sotish kerak.
- Keyin boshqa kitoblarni olib kelish kerak.

## Yechim

- **Narx:** MUQADDIMA — **99 000 so'm** (psixologik narx: «100 mingdan arzon»).
- **Telegram bot** (`zumar/bot.py`) — xaridorlar bazasi, sotuv va qayta keltirish.

## Bot nima qiladi

| Qadam | Bot |
|---|---|
| /start | Ism-familiya → yosh → telefon raqam so'raydi (raqam tugma bilan yuboriladi) |
| 📖 MUQADDIMA | Narxi va qoldig'i: «98 dona qoldi» yoki **«Qolmadi»** |
| 🛒 Sotib olish | Nechta — buyurtma; qoldiq kamayadi, sotuvchiga xabar boradi |
| 🎁 Bonus | Har xaridga **stikerlar to'plami** + keyingi xarid uchun **10% chegirma kodi** (`ZUMAR-XXXXX`) — odam yana do'konga kelishi uchun |
| 🔥 Aksiya | **Haftada 1 marta** (juma, 10:00) hammaga avtomatik aksiya yuboriladi |
| 📚 Boshqa kitob | Xaridor qaysi kitob kerakligini yozadi → keyin nimani olib kelishni shu ro'yxatdan bilasiz |
| 📢 Instagram / Telegram | Sahifa havolalari + do'st taklif qilish havolasi (do'st xarid qilsa, 5 000 so'm bonus) |

MUQADDIMA tugasa, sotuvchiga «tugadi» xabari keladi. `/qoldiq 50` bilan yangi
partiya qo'shilsa, bot hammaga «yana sotuvda» deb yozadi.

### Admin buyruqlari (faqat `ADMIN_IDS` dagilar uchun)

`/admin` — ro'yxat · `/statistika` · `/buyurtmalar` · `/berildi 5` · `/bekor 5` ·
`/qoldiq 100` · `/aksiya matn` · `/aksiya_yubor` · `/xabar matn` ·
`/kod ZUMAR-XXXXX` (chegirma kodini tekshirib, o'chiradi) · `/ball 901234567` ·
`/sorovlar` (so'ralgan kitoblar)

## Ishga tushirish

1. Telegram'da @BotFather → `/newbot` → token oling.
2. GitHub: **Settings → Secrets and variables → Actions**
   - Secret `ZUMAR_BOT_TOKEN` — token
   - Variable `ZUMAR_ADMIN_IDS` — Telegram ID ingiz (botga `/men` yozsangiz aytadi)
   - Variable `ZUMAR_INSTAGRAM`, `ZUMAR_KANAL`, `ZUMAR_MANZIL` — ixtiyoriy
3. **Actions → Zumar bot → Run workflow → `sozlash`** (bir marta).
4. Tamom: bot har 5 daqiqada javob beradi. Jadval faqat `main` shoxchasida ishlaydi.

Doimiy server bo'lsa: `BOT_TOKEN=... ADMIN_IDS=... python3 zumar/bot.py` — darhol javob beradi.

## Auditoriya yig'ish rejasi (Instagram + Telegram)

1. **Botni hamma joyga qo'ying:** Instagram bio, Telegram kanal, do'kondagi
   kassa yoniga QR-kod («Skanerlang — bonus oling»).
2. **Instagram:** haftada 3 ta Reels — MUQADDIMA'dan 1 ta qisqa iqtibos,
   «kitob ochish» videosi, xaridor fikri. Har postda: «Narxi 99 000 — bot orqali
   buyurtma bering, stikerlar sovg'a».
3. **Telegram kanal:** har kuni 1 ta iqtibos + juma kuni aksiya. Bot ham shu
   aksiyani yuboradi.
4. **Qoldiqni ko'rsating:** «100 dan 63 dona qoldi» — shoshilish hissi sotuvni tezlatadi.
5. **Do'st taklifi:** botdagi taklif havolasi — har bir xaridor yangi xaridor olib keladi.
6. **Keyingi kitob:** `/sorovlar` da eng ko'p so'ralgan kitobni olib keling va
   `/xabar` bilan hammaga e'lon qiling.

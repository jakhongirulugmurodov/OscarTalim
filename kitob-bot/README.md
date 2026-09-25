# 📚✨ Sehrli Javon — kitob do'koni boti

Sotilmay qolgan va ombordagi kitoblarni sotish uchun Telegram bot.
Faqat Python standart kutubxonasi ishlatilgan, qo'shimcha o'rnatish kerak emas.

## Xaridor nimani ko'radi

| Bo'lim | Nima qiladi |
|---|---|
| **Ro'yxatdan o'tish** | `/start` → **Google akkaunt (Gmail)** yoki **ism va familiya** → **yosh** |
| 📚 **Katalog** | 6 ta janr, har bir kitobning o'z sahifasi: narx, omborda nechta qolgani, aksiya, sovg'a, ⭐ reyting, nechta sotilgani, «💡 Bilasizmi?» fakti |
| 🔥 **Aksiyalar** | chegirmali va sovg'ali kitoblar + qo'shimcha sovg'a qoidalari |
| 🎯 **Siz uchun** | yoshiga mos tavsiyalar (bolalarga — bolalar kitoblari birinchi) |
| 🎲 **Tasodifiy kitob** | omborda ko'p turib qolgan kitoblar ko'proq chiqadi |
| 🔍 **Qidiruv** | kitob yoki muallif nomini yozish kifoya |
| 🎟 **Promokod** | 10% dan 50% gacha; har bir kishi bitta kodni bir marta ishlatadi |
| 🛒 **Savat** | ➖ ➕ ❌, chegirma va sovg'alar hisobi, «yana X so'mlik olsangiz — sovg'a» maslahati |
| 📝 **Rasmiylashtirish** | qabul qiluvchi ismi → 📱 telefon → 📍 **lokatsiya** (yoki manzil / do'kondan olib ketish) → 💳 **to'lov turi**: naqd, karta, Click/Payme → «Buyurtma rasmiylashtirildi, raqami #N» |
| 📦 **Xaridlarim** | har bir buyurtmaning sahifasi: holati, kitoblar, summa, sovg'alar; sotib olingan kitobni **1–5 ⭐ baholash** va sharh yozish |

**Chegirma qoidasi:** har bir kitobga eng katta chegirma qo'llanadi — aksiya
yoki promokod (ikkalasi qo'shilib ketmaydi, zarar bo'lmasligi uchun).

**Sovg'alar** (`katalog.json` → `sovgalar`):
- kitobning o'z sovg'asi (masalan, «Kichkina shahzoda» → 🎨 bo'yash kitobchasi);
- 150 000 so'mdan — ☕ krujka, 300 000 so'mdan — 🎒 sumka + krujka;
- 3 va undan ortiq kitob — 🔖 xatcho'plar to'plami.

**Kamchiliksiz ishlashi uchun tekshirilgan:** ombordagidan ortiq sotib bo'lmaydi;
18+ kitob yosh kichiklarga sotilmaydi; tasdiqlash oldidan savat o'zgarsa —
qayta ko'rsatiladi; «Tasdiqlash»ni ikki marta bosish ikki buyurtma qilmaydi;
bekor qilingan buyurtmaning kitoblari omborga, promokodi egasiga qaytadi;
faqat sotib olgan kishi baholay oladi; ism/manzilga yozilgan HTML buzmaydi.

## Admin (do'kon egasi)

`ADMIN_IDS` dagi odam uchun. Har bir yangi buyurtma adminga **✅ Tasdiqlash /
❌ Rad etish** tugmalari bilan keladi (lokatsiya bo'lsa — xarita nuqtasi ham).
Keyin: 🚚 Yuborildi → 📬 Yetkazildi. Mijozga holat o'zi boradi. Tasdiqlangan
buyurtmani mijoz o'zi bekor qila olmaydi.

`/admin` — panel (jami tushum, bugungi tushum, kutayotgan buyurtmalar, mijozlar / maqsad), va:
- 📊 **Umumiy hisobot** — tushum (bugun / 7 / 30 kun), o'rtacha chek, 1000 mijoz
  maqsadiga progress, voronka (ochgan → ro'yxat → xarid), 14 kunlik sotuv va
  yangi mijozlar mini-grafigi, top kitoblar, mijozlar qayerdan kelgani.
- 📈 **Marketing tahlil** — bot HTML fayl yuboradi, telefonda yoki kompyuterda
  ochiladi: ko'rsatkich doiralari, kunlik sotuv grafigi, yangi mijozlar grafigi,
  voronka, yosh guruhlari, manbalar, top va sotilmayotgan kitoblar, promokodlar,
  to'lov turlari.
- 🧾 **Buyurtmalar** — yangilari tepada, har birining yonida ✅ / ❌.
- 👥 **Mijozlar** — ism, yosh, telefon, nechta buyurtma, qancha xarid, manba.
- 🐢 **Sotilmayotganlar** — omborda ko'p, sotuvi kam kitoblar. Bir bosishda
  −20% / −30% aksiya qo'yasiz va 📣 hamma mijozlarga e'lon yuborasiz.
- 🧾 Buyurtmalar, 📦 Ombor, 🎟 Promokodlar.

| Buyruq | Misol |
|---|---|
| ombordagi soni | `/qoldiq b01 25` |
| narx | `/narx b01 49000` |
| aksiya (0 — olib tashlash) | `/aksiya b01 25` |
| sovg'a (`-` — olib tashlash) | `/sovga b01 🔖 Xatcho'p` |
| promokod (10–50%, soni va muddat ixtiyoriy) | `/promo YOZ30 30 100 2026-12-31` |
| promokodni o'chirish | `/promo_ochir YOZ30` |
| yangi kitob | `/yangi_kitob Nomi \| Muallif \| janr \| 45000 \| 10 \| 12 \| Tavsif` |
| reklama havolasi (manbani sanaydi) | `/havola instagram` → `t.me/<bot>?start=r_instagram` |
| hammaga e'lon | `/xabar Yangi kitoblar keldi!` |

**Reklama havolalari.** Har bir reklama joyi uchun alohida havola oling
(`/havola instagram`, `/havola varaqa`, `/havola kanal`) — varaqaga QR qilib
bosish mumkin. Shu havoladan kirgan yangi mijoz ro'yxatdan o'tgach 10% tanishuv
promokodini (`SALOM10`) oladi, marketing tahlilida esa har bir manbadan nechta
odam kelgani, nechtasi xarid qilgani va qancha tushum bergani ko'rinadi.

## Ishga tushirish

1. **@BotFather** → `/newbot` → nomi: `Sehrli Javon`, username: masalan
   `SehrliJavonBot` (band bo'lsa — boshqasi) → **token**.
2. Repo → **Settings → Secrets and variables → Actions**:
   - secret `KITOB_BOT_TOKEN` — token;
   - variable `KITOB_ADMIN_IDS` — sizning Telegram ID ingiz (botga `/men` deb yozsangiz aytadi).
3. **Actions → Kitob bot → Run workflow → rejim: `sozlash`** — bot tavsifi va
   buyruqlar ro'yxati o'rnatiladi.
4. Tamom: workflow har 5 daqiqada ishga tushib, ~4,5 daqiqa xabarlarni jonli
   kutadi. (GitHub jadvalni ba'zan kechiktiradi, shunda bot bir necha daqiqa
   jim turishi mumkin — to'liq uzluksiz bo'lishi uchun serverda ishlating.)

**O'z serveringizda** (VPS, uy kompyuteri):

```bash
BOT_TOKEN=123:ABC ADMIN_IDS=111222333 python3 kitob-bot/bot.py --setup
BOT_TOKEN=123:ABC ADMIN_IDS=111222333 python3 kitob-bot/bot.py
```

Bitta token bilan bir vaqtda faqat bitta nusxa ishlashi kerak (yoki Actions,
yoki server).

## Kitoblarni o'zgartirish

`katalog.json` — boshlang'ich katalog: janrlar, kitoblar, promokodlar,
sovg'a qoidalari, do'kon ma'lumotlari. Yangi kitob/promokod qo'shsangiz,
keyingi ishga tushishda botga qo'shiladi. Mavjud kitobning **narxi, soni,
aksiyasi, sovg'asi** esa bot ichida boshqariladi (yuqoridagi buyruqlar) —
chunki sotuv davomida ular o'zgarib boradi. Rasm qo'shish uchun kitobga
`"rasm": "https://..."` maydonini yozing — kitob sahifasining tepasida chiqadi.

## Sinovlar

```bash
python3 kitob-bot/test_bot.py
```

Telegram'siz, soxta API bilan (21 ta): ro'yxatdan o'tish, katalog, yosh cheklovi,
ombor chegarasi, promokod chegaralari, to'liq xarid, lokatsiya va to'lov turi,
sovg'alar, baholash, bekor qilish, admin ✅/❌, hisobotlar, reklama manbalari,
fayl yuborish, HTML xavfsizligi.

Marketing sahifasini namuna ma'lumot bilan ko'rish:
`python3 kitob-bot/hisobot.py > misol.html` va brauzerda oching.

## Bilib qo'ying

- **Google akkaunt** — bot Gmail manzilini so'raydi va mijoz profiliga
  bog'laydi. Haqiqiy «Google bilan kirish» (OAuth) uchun doimiy veb-server
  kerak; bu bot serversiz ishlagani uchun manzil tasdiqlanmaydi.
- **To'lov** — mijoz naqd, karta yoki Click/Payme'ni tanlaydi, pul esa
  kitobni qabul qilganda (yoki admin yuborgan havola orqali) to'lanadi. Bot
  ichida avtomatik onlayn to'lov uchun Click/Payme bilan shartnoma va provayder
  tokeni kerak — keyin qo'shish mumkin.

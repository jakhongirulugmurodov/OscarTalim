# 📚 Kitoblar olami — Telegram bot

Kitob do'koni boti. Faqat Python standart kutubxonasi — hech narsa o'rnatish shart emas.

## Nima qiladi

| | |
|---|---|
| **Ro'yxatdan o'tish** | `/start` → ism → familiya → yosh → qiziqadigan janrlar (bir nechtasini tanlash mumkin) |
| **Tavsiya** | Yoshiga mos, qiziqishiga eng ko'p mos keladigan kitoblar oldinda, 5 tadan |
| **Katalog va qidiruv** | Janr bo'yicha ro'yxat; kitob nomi yoki muallifni yozsa — qidiradi |
| **Onlayn buyurtma** | Savatcha → telefon → **🏬 do'kondan olib ketish** yoki 🚚 yetkazib berish → to'lov: 💳 onlayn (Click/Payme) yoki 💵 naqd |
| **Olish kodi** | Har bir buyurtmaga 6 xonali kod beriladi (masalan, `460614`). Mijoz do'konga kelib kodni ko'rsatadi, admin uni botga yozadi — bot buyurtmani ko'rsatadi, «📦 Kitoblar berildi» bosilgach kod yaroqsiz bo'ladi. Mijoz kodini «👤 Profil»dan istalgan payt ko'radi |
| **Juma aksiyasi** | Admin aksiyani kiritadi va chegirmaga tushadigan kitoblarni tanlaydi → bot aksiyani **1 hafta oldin** (o'tgan juma soat 10:00 da) hammaga e'lon qiladi, aksiya kuni yana eslatadi va chegirmani o'sha kitoblarga avtomatik qo'llaydi. Keyingi juma uchun aksiya kiritilmagan bo'lsa, adminlarga oldindan eslatadi |

## ⚙️ Admin panel (faqat adminlarga ko'rinadi)

`ADMIN_IDS` dagi odamlarda pastki menyuda qo'shimcha **⚙️ Admin panel** tugmasi chiqadi.
Oddiy mijozlar bu tugmani ham, buyruqlarni ham ko'rmaydi; bossa ham ishlamaydi.

| Tugma | Nima qiladi |
|---|---|
| 🏷 Juma chegirmasidagi kitoblar | Kelgusi har bir juma: chegirma foizi, qaysi kitoblar tushadi (eski → yangi narx), e'lon holati. «✏️ Kitoblarni tanlash» — ✅ belgilab tanlanadi |
| 🔑 Kodni tekshirish | Mijoz ko'rsatgan kodni yozing (tugmasiz ham — 6 raqamni shunchaki yuborsangiz bo'ladi). Kod noto'g'ri yoki ishlatilgan bo'lsa, bot ogohlantiradi; naqd buyurtmada «pul oling» deb eslatadi |
| 🧾 Berilmagan buyurtmalar | Kodlari bilan, hali olib ketilmagan buyurtmalar |
| 📊 Statistika | Mijozlar soni, buyurtmalar, eng ko'p qiziqilgan janrlar |

Buyruqlar:

```
/aksiya 2026-10-02 20 Matn       — juma aksiyasi (sana, chegirma %, matn)
/juma                            — juma chegirmasidagi kitoblar
/aksiya_ochir 2026-10-02         — aksiyani o'chirish
/kod 460614                      — kodni tekshirish
/berildi 5                       — №5 buyurtma berildi
/buyurtmalar                     — berilmagan buyurtmalar
/xabar Matn                      — hammaga xabar
/statistika                      — statistika
```

## Ishga tushirish

1. **@BotFather** → `/newbot` → nomi «Kitoblar olami» → tokenni oling.
2. Onlayn to'lov uchun: BotFather → bot → *Payments* → Click yoki Payme → to'lov tokeni.
   Token bo'lmasa, faqat naqd to'lov chiqadi.
3. O'z Telegram ID ingizni biling (masalan, @userinfobot orqali).
4. GitHub → Settings → Secrets and variables → Actions:
   - secret `KITOBLAR_BOT_TOKEN`
   - secret `KITOBLAR_PAYMENT_TOKEN` (ixtiyoriy)
   - variable `KITOBLAR_ADMIN_IDS` — `123456789` (bir nechta bo'lsa vergul bilan)
5. Actions → **Kitoblar olami bot** → *Run workflow* → `sozlash` (buyruqlar va tavsif bir marta).
   Keyin bot har 5 daqiqada o'zi ishlaydi (workflow `main` shoxchasida bo'lishi kerak).

O'z serveringizda doimiy ishlatish (javob darhol keladi):

```bash
BOT_TOKEN=... ADMIN_IDS=... python3 kitoblar_olami/bot.py
```

## Kitoblar ro'yxati

`kitoblar.json` — har bir kitob:

```json
{"id": "sherlok", "nomi": "...", "muallif": "...", "janr": ["detektiv"],
 "yosh": [12, 99], "narx": 55000, "tavsif": "...", "rasm": "https://... (ixtiyoriy)"}
```

Janr kalitlari: `badiiy`, `sarguzasht`, `fantastika`, `detektiv`, `tarix`, `ilmiy`,
`rivojlanish`, `bolalar`, `diniy`. **Narxlar namuna uchun** — do'konning haqiqiy
narxlari va kitoblarini kiriting.

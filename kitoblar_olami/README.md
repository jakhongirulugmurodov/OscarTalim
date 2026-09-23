# 📚 Kitoblar olami — Telegram bot

Kitob do'koni boti. Faqat Python standart kutubxonasi — hech narsa o'rnatish shart emas.

## Nima qiladi

| | |
|---|---|
| **Ro'yxatdan o'tish** | `/start` → ism → familiya → yosh → qiziqadigan janrlar (bir nechtasini tanlash mumkin) |
| **Tavsiya** | Yoshiga mos, qiziqishiga eng ko'p mos keladigan kitoblar oldinda, 5 tadan |
| **Katalog va qidiruv** | Janr bo'yicha ro'yxat; kitob nomi yoki muallifni yozsa — qidiradi |
| **Onlayn buyurtma** | Savatcha → telefon → manzil → to'lov: 💳 onlayn (Click/Payme) yoki 💵 yetkazib berganda naqd. Buyurtma adminlarga keladi |
| **Juma aksiyasi** | Admin aksiyani kiritadi → bot uni **1 hafta oldin** (o'tgan juma soat 10:00 da) hammaga e'lon qiladi, aksiya kuni yana eslatadi va chegirmani narxlarga avtomatik qo'llaydi. Keyingi juma uchun aksiya kiritilmagan bo'lsa, adminlarga oldindan eslatadi |

## Admin buyruqlari

```
/admin                           — buyruqlar ro'yxati
/aksiya 2026-10-02 20 Matn       — juma aksiyasi (sana, chegirma %, matn)
/aksiyalar                       — kelgusi aksiyalar
/aksiya_ochir 2026-10-02         — aksiyani o'chirish
/buyurtmalar                     — oxirgi 15 buyurtma
/yetkazildi 5                    — №5 yetkazildi (mijozga xabar boradi)
/xabar Matn                      — hammaga xabar
/statistika                      — foydalanuvchilar va qiziqishlar
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

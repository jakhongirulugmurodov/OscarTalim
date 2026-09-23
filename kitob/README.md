# Kitob olami — Telegram bot

Kitob do'koni uchun bot: mijozlar ro'yxatdan o'tadi, har juma bitta kitob
**tannarxidan ozgina arzonga** (ozgina zarariga) sotiladi, bot esa hammaga
o'z vaqtida eslatib turadi.

## Mijoz nima ko'radi

1. `/start` → pastda **📝 Ro'yxatdan o'tish** tugmasi.
2. Ketma-ket so'raladi: **ism → familiya → telefon** (tugma bilan yoki
   yozib) **→ yosh → qiziqqan janr** (Motivatsion, Kino asosidagi
   kitoblar, Romanlar, Diniy va tarixiy, … yoki o'zi yozadi).
3. Tayyor. Keyin menyu: **🔥 Juma aksiyasi**, **👤 Ma'lumotlarim**,
   **✏️ Ma'lumotni o'zgartirish**.

## Eslatmalar jadvali

| Qachon | Kimga | Nima |
|---|---|---|
| Aksiyadan **4 hafta** oldin | do'kon egasi | «Aksiyaga 28 kun qoldi — kitobni buyurtma qiling» |
| 4 hafta keyingi juma **bo'sh** bo'lsa | do'kon egasi | «Bu jumaga aksiya yo'q — kitob tanlang» |
| E'londan bir kun oldin (8 kun) | do'kon egasi | «Ertaga mijozlarga e'lon ketadi, omborni tekshiring» |
| Aksiyadan **1 hafta** oldin | barcha mijozlar | Kitob nomi, eski narx → aksiya narxi |
| Payshanba (1 kun oldin) | barcha mijozlar | «Ertaga — juma aksiyasi!» |
| Juma ertalab | barcha mijozlar | «Bugun — juma aksiyasi!» |

Mijozlar aksiyani **faqat 1 hafta qolganda** biladi — undan oldin bot hech
kimga ko'rsatmaydi. Eslatmalar Toshkent vaqti bilan soat 10:00 dan keyin
ketadi, har biri faqat bir marta. Aksiya janri mijozning qiziqishiga mos
kelsa, xabarga «💚 Bu siz yoqtirgan janrdan» qo'shiladi.

## Do'kon egasi nima qiladi

Egasining Telegram ID si `KITOB_ADMIN_IDS` da bo'lsa, menyuda qo'shimcha
tugmalar chiqadi:

- **➕ Aksiya qo'shish** — juma (tugmalardan tanlanadi), kitob nomi, janr,
  odatiy narx, **tannarx**, aksiya narxi. Aksiya narxi tannarxdan past
  bo'lmasa, bot qabul qilmaydi; zarar 15% dan oshsa, ogohlantiradi.
  Tannarxni mijozlar ko'rmaydi.
- **📋 Aksiyalar** — rejadagi aksiyalar, har biridan zarar, aksiyasiz jumalar.
- **👥 Mijozlar** — ro'yxatdan o'tganlar soni, janrlar bo'yicha, telefonlar.
- `/ochir 3` — 3-aksiyani o'chirish.
- `/xabar matn` — barcha mijozlarga xabar (masalan, yangi kitoblar keldi).

## Ishga tushirish (bir marta)

1. **@BotFather** → `/newbot` → nomi «Kitob olami» → token.
2. GitHub: **Settings → Secrets and variables → Actions**:
   - *Secrets* → `KITOB_BOT_TOKEN` = token;
   - *Variables* → `KITOB_ADMIN_IDS` = do'kon egasining Telegram ID si
     (botga `/men` deb yozsangiz aytadi; bir nechta bo'lsa — vergul bilan).
3. **Actions → Kitob olami bot → Run workflow → rejim: `sozlash`**.

Shundan keyin workflow har 5 daqiqada ishlaydi (faqat `main` shoxchada).
Ma'lumotlar (mijozlar, aksiyalar) Actions keshida `state/kitob.json`
faylida saqlanadi.

O'z serveringizda ishlatish:

```sh
BOT_TOKEN=... ADMIN_IDS=123456 python3 kitob/bot.py
```

# Juma aksiyasi — kitob boti

Har juma bitta kitob **300 000 so'm o'rniga 239 000 so'm**, 100 dona.
Bot mijozlarni ro'yxatga oladi va aksiyadagi kitobni **bir hafta oldin** aytadi.

## Mijoz nima ko'radi

1. `/start` → aksiya haqida qisqacha → **ism → familiya → telefon**
   (tugma bilan yoki yozib) → **janrlar** (bir nechtasini tanlash mumkin).
2. Admin aksiyani e'lon qilganda — kitob rasmi, narxi, sanasi va
   **🛒 Band qilish** tugmasi keladi.
3. Payshanba 19:00 da "Ertaga!", juma 09:00 da "Bugun!" eslatmasi (o'zi).
4. Band qilsa, adminga ismi va telefoni keladi. 100 ta tugagach band qilish yopiladi.

## Admin buyruqlari

| Buyruq | Nima qiladi |
|---|---|
| `/aksiya` | Keyingi juma aksiyasi: kitob rasmini yuborasiz, tagiga nomi va tavsifi. Ko'rib chiqasiz → **📣 Hammaga yuborish** |
| `/aksiya 2026-10-02` | Boshqa sanadagi juma uchun |
| `/eslatma <matn>` | Ro'yxatdagi hammaga xabar |
| `/royxat` | Mijozlar ro'yxati — Excel'da ochiladigan CSV fayl |
| `/statistika` | Nechta odam, qaysi janr, qayerdan kelgan, nechta band |
| `/men` | O'zingizning Telegram ID ingiz |

Narx va sana matnga o'zi qo'shiladi — faqat kitob nomi va tavsifini yozing.

## Instagram va Telegram uchun havolalar

Qayerdan qancha odam kelganini bilish uchun har joyga alohida havola qo'ying:

- Instagram bio / stories: `https://t.me/<bot_nomi>?start=insta`
- Telegram kanal: `https://t.me/<bot_nomi>?start=tg`

`/statistika` da "insta — 820, tg — 340" kabi ko'rinadi.

## Ishga tushirish (bir marta)

1. **@BotFather** → `/newbot` → token oling.
2. GitHub: **Settings → Secrets and variables → Actions**
   - **Secrets** → `KITOB_BOT_TOKEN` = token
   - **Variables** → `KITOB_ADMIN_IDS` = admin Telegram ID lari, vergul bilan
     (ID ni bilish uchun: botni vaqtincha ishga tushirib, `/men` deb yozing)
   - ixtiyoriy: `NARX_ESKI`, `NARX_YANGI`, `SONI`
3. Bu kod `main` shoxchasiga tushgach, **Actions → Kitob bot → Run workflow**.
   Keyin u har 15 daqiqada o'zi navbatga turadi va deyarli to'xtovsiz ishlaydi.

Server bo'lsa: `BOT_TOKEN=... ADMIN_IDS=... python3 kitob_bot/bot.py` —
faqat standart Python kutubxonasi, o'rnatish kerak emas.

## Bilish kerak

- Ma'lumotlar GitHub Actions keshida saqlanadi. Muhim ro'yxatni vaqti-vaqti
  bilan `/royxat` bilan yuklab oling — zaxira bo'ladi.
- Katta auditoriya bilan (aksiya kuni minglab odam) o'z serveri yoki VPS
  ishonchliroq: GitHub bot ishga tushishlari orasida 10–30 soniya uzilish bo'ladi.

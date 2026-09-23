# Kitob.uz — Juma aksiyasi boti

Har juma bo'ladigan aksiyaga odamlarni jalb qiluvchi Telegram bot.
Kitoblarga **10% dan 30% gacha** chegirma — bot boshqa foizga ruxsat bermaydi.

## Mijoz nimani ko'radi

1. **Ro'yxatdan o'tish** (majburiy — usiz bot hech narsa ko'rsatmaydi):
   1. telefon raqami (tugma bilan yoki yozib: `+998901234567`);
   2. ism va familiya;
   3. tug'ilgan sana — `15.03.1998` (yil ham, sana ham shundan olinadi);
   4. qiziqadigan kitob turlari — bir nechtasini tanlash mumkin.

   Oxirida mijozga **shaxsiy kod** beriladi (`K1001`) — kassada aytadi.
2. **Eslatma** — aksiya boshlanishidan **3 kun oldin** (juma 10:00 bo'lsa,
   seshanba 10:00 da) har bir mijozga: uning qiziqishiga mos chegirmadagi
   kitoblar oldinda, **✅ Boraman** tugmasi bilan.
3. Aksiya boshlanganda — yana bitta qisqa xabar.
4. Menyu: 🔥 Juma aksiyasi · 📚 Chegirmadagi kitoblar · 👤 Profilim ·
   🎁 Do'stni taklif qilish (shaxsiy havola — kim kimni olib kelgani
   tahlilda ko'rinadi).
5. Tug'ilgan kunida bot tabriklaydi.

## Xodim paneli (dasturchisiz boshqarish)

Xodim botga `/xodim KOD` yozadi (KOD — `KITOB_XODIM_KODI`). Egalar
(`KITOB_ADMIN_IDS`) avtomatik xodim; ular `/xodimlar` va `/ochir ID`
bilan xodimlarni ko'radi va o'chiradi.

| Tugma | Nima qiladi |
|---|---|
| 📊 Tahlil | Botni ochgan / ro'yxatdan o'tgan, 7 kunda yangi, qiziqishlar va yosh bo'yicha taqsimot, keyingi aksiyaga «Boraman» deganlar, o'tgan 4 aksiya: boraman → keldi, 7 kun ichidagi tug'ilgan kunlar, eng ko'p taklif qilganlar |
| 📥 Excel jadval | Barcha mijozlar CSV faylda (Excel'da ochiladi) |
| 📚 Kitoblar | Chegirmadagi kitoblar; bosib chegirmani o'zgartirish yoki o'chirish; yangi hafta uchun hammasini tozalash |
| ➕ Kitob qo'shish | Nomi → turi → narxi → chegirma (10–30%) |
| ⚙️ Aksiya sozlamalari | Eslatma muddati (3 soat / 1 / 2 / 3 kun), vaqt (`10:00-20:00`), qo'shimcha matn (manzil, sovg'a), to'xtatish/yoqish, eslatmani oldindan ko'rish |
| 📣 Xabar yuborish | Hammaga yoki faqat biror kitob turiga qiziquvchilarga |
| 🧾 Kelganini belgilash | Kassada mijoz kodini yoki telefonini yozish — kim haqiqatan kelgani hisoblanadi |

## Ishga tushirish (GitHub Actions, server kerak emas)

1. **@BotFather** → `/newbot` → token.
2. Repo → **Settings → Secrets and variables → Actions**:
   - secret `KITOB_BOT_TOKEN` — token;
   - secret `KITOB_XODIM_KODI` — xodimlar uchun maxfiy so'z;
   - variable `KITOB_ADMIN_IDS` — sizning Telegram ID ingiz (botga `/men` yozsangiz aytadi);
   - variable `KITOB_DOKON_NOMI` — ixtiyoriy.
3. **Actions → Kitob boti → Run workflow → rejim: `sozlash`** — buyruqlar va tavsif.

Bot har 5 daqiqada ishga tushadi, shuning uchun javob 5–15 daqiqa kechikishi
mumkin (GitHub jadvali shunday). Jadval faqat `main` shoxchasida ishlaydi.
Tez javob kerak bo'lsa, istalgan serverda `python3 kitob_bot/bot.py` —
doimiy rejim.

Ma'lumotlar GitHub Actions keshida saqlanadi. Vaqti-vaqti bilan
**📥 Excel jadval** bilan zaxira oling.

## Sinov

```
python3 -m unittest kitob_bot/test_bot.py
```

# Kitob olami — Telegram bot

Kitob do'koni uchun bot: mijozlar ro'yxatdan o'tadi, har juma bitta kitob
**tannarxidan ozgina arzonga** (ozgina zarariga) sotiladi, bot esa hammaga
o'z vaqtida eslatib turadi.

## Mijoz nima ko'radi

1. Botni ochganda o'rtada kitoblar rasmi (`rasmlar/salom.png`) va ostida
   «**Assalomu alaykum! Kitoblar olamiga xush kelibsiz**» turadi; bot
   rasmi doirachada — `rasmlar/avatar.png`.
   START → salomlashish va pastda **📝 Ro'yxatdan o'tish** tugmasi.
2. Ketma-ket so'raladi: **ism → familiya → telefon** (tugma bilan yoki
   yozib) **→ yosh → qiziqqan janr** (Motivatsion, Kino asosidagi
   kitoblar, Romanlar, Diniy va tarixiy, … yoki o'zi yozadi).
3. Tayyor. Keyin menyu: **🔥 Juma aksiyasi**, **📦 Buyurtmalarim**,
   **👤 Ma'lumotlarim**, **✏️ Ma'lumotni o'zgartirish**.

## Buyurtma

Aksiya xabari (kitob muqovasi rasmi, eski narx → aksiya narxi, «Qoldi: N ta»)
ostida **🛒 Buyurtma berish** tugmasi bor:

1. Ro'yxatdan o'tmagan bo'lsa — avval ro'yxatdan o'tadi, keyin davom etadi.
2. **Nechta?** — 1 dan 5 gacha (qolgan kitobdan ko'p emas).
3. `TOLOV_KARTA` berilgan bo'lsa — kartaga o'tkazib **chek rasmini** yuboradi
   yoki «💵 Olganda to'layman» ni tanlaydi.
4. Tekshiradi → **✅ Buyurtmani tasdiqlash** → «Buyurtma #1001 rasmiylashtirildi».
5. Do'kon egasiga buyurtma (chek rasmi bilan) **✅ Qabul / ❌ Rad** tugmalari
   bilan keladi. Bosgach, mijozga javob boradi. Rad etilgan buyurtmaning
   kitoblari yana sotuvga qaytadi.

Kitoblar tugasa, e'londa «tugadi» deb yoziladi va payshanba/juma eslatmasi
yuborilmaydi.

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

- **➕ Aksiya qo'shish** — juma (tugmalardan tanlanadi), kitob nomi,
  muqova rasmi, janr, odatiy narx, **tannarx**, aksiya narxi, nechta kitob.
  - Aksiya narxi tannarxdan past bo'lmasa, bot qabul qilmaydi.
  - Bot tannarxdan 1 000 so'm kamini taklif qiladi: tannarx **340 000** →
    aksiya **339 000** (bir tugma).
  - Zarar 5% dan oshsa, ogohlantiradi. Tannarxni mijozlar ko'rmaydi.
- **📋 Aksiyalar** — rejadagi aksiyalar, har biridan zarar, nechta buyurtma
  olingani, aksiyasiz jumalar.
- **📦 Buyurtmalar** — kutilayotgan buyurtmalar ✅/❌ tugmalari bilan.
- **📊 Marketing** — mijozlar soni (bu hafta nechta yangi), buyurtmalar,
  sotilgan kitoblar, tushum, aksiya xarajati (jami zarar), bitta mijozga
  xarajat, buyurtma bergan va qayta kelgan mijozlar, 8 haftalik
  «Mijoz / Sotuv» grafigi, oxirgi aksiyalar natijasi, mijozlar yoqtirgan janrlar.
- **👥 Mijozlar** — ro'yxatdan o'tganlar soni, janrlar bo'yicha, telefonlar.
- `/ochir 3` — 3-aksiyani o'chirish.
- `/xabar matn` — barcha mijozlarga xabar (masalan, yangi kitoblar keldi).

## Ishga tushirish (bir marta)

1. **@BotFather** → `/newbot` → nomi «Kitob olami» → token.
2. GitHub: **Settings → Secrets and variables → Actions**:
   - *Secrets* → `KITOB_BOT_TOKEN` = token;
   - *Variables* → `KITOB_ADMIN_IDS` = do'kon egasining Telegram ID si
     (botga `/men` deb yozsangiz aytadi; bir nechta bo'lsa — vergul bilan);
   - *Variables* → `KITOB_TOLOV_KARTA` = karta raqami (ixtiyoriy; bo'lmasa,
     mijoz kitobni olganda to'laydi).
3. **Actions → Kitob olami bot → Run workflow → rejim: `sozlash`**.
4. Rasmlar (faqat @BotFather orqali qo'yiladi, Bot API'da bunday usul yo'q):
   - **o'rtadagi rasm**: @BotFather → `/mybots` → botni tanlang →
     **Edit Bot** → **Edit Description Picture** → `kitob/rasmlar/salom-640.jpg` (640×360);
   - **doirachadagi rasm**: @BotFather → `/setuserpic` → botni tanlang →
     `kitob/rasmlar/avatar.jpg`.

   Rasm ostidagi matn (`TAVSIF`) 3-qadamdagi `sozlash` bilan qo'yiladi.

## Rasmlar

`kitob/rasmlar/` ichida: `salom.png` (1280×720, botni ochganda o'rtada
turadigan rasm) va `avatar.png` (640×640, doirachadagi bot rasmi). Ular `salom.html` va `avatar.html` dan
chiziladi. Kitob nomlarini yoki ranglarni o'zgartirsangiz, qayta chizing:

```sh
cd kitob/rasmlar && node chiz.mjs     # playwright kerak
```

Keyin yangi rasmni @BotFather orqali qayta qo'ying (yuqoridagi 4-qadam).

Shundan keyin workflow har 5 daqiqada ishlaydi (faqat `main` shoxchada).
Ma'lumotlar (mijozlar, aksiyalar) Actions keshida `state/kitob.json`
faylida saqlanadi.

O'z serveringizda ishlatish:

```sh
BOT_TOKEN=... ADMIN_IDS=123456 python3 kitob/bot.py
```

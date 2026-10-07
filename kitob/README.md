# Kitob olami — Telegram bot

Telegram'da: **Mybooks** — [@My_books_07bot](https://t.me/My_books_07bot).

Kitob do'koni uchun bot: mijozlar ro'yxatdan o'tadi, har juma bitta kitob
**odatiy narxidan arzonga** sotiladi — lekin tannarxdan arzon emas, do'kon
zarar ko'rmaydi, bot esa hammaga
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

Mijoz `/ochir_meni` deb yozsa, uning ism, familiya, telefon, yosh,
qiziqish va chek rasmlari o'chiriladi, eslatmalar to'xtaydi.

## Band qilish (bron) — yarim pul oldindan

Aksiya xabarida (kitob muqovasi, eski narx → aksiya narxi, «Aksiyada 100 ta
kitob — qoldi: N ta») **📌 Band qilish — yarim pulini to'lab** tugmasi bor:

1. Ro'yxatdan o'tmagan bo'lsa — avval ro'yxatdan o'tadi, keyin davom etadi.
2. **Nechta?** — 1 dan 5 gacha (qolgan kitobdan ko'p emas).
3. Bot jami va **oldindan to'lov (yarmi)** ni aytadi, masalan 2 × 360 000 =
   720 000 → oldindan **360 000**, juma kuni 360 000.
4. `TOLOV_KARTA` bo'lsa — kartaga yarim pulni o'tkazib, **chek rasmini**
   yuboradi (chek bo'lmasa, bron qilinmaydi). Karta berilmagan bo'lsa —
   yarim pulni do'konga kelib to'laydi.
5. Tekshiradi → **✅ Band qilishni tasdiqlash** → «Bron #1001 qabul qilindi».
6. Do'kon egasiga bron chek rasmi bilan **✅ To'lov keldi / ❌ Rad** tugmalari
   bilan keladi. «To'lov keldi» → mijozga «Kitob siz uchun band».
   Rad etilgan bronning kitoblari yana sotuvga qaytadi.

Band qilganlarga **shaxsiy eslatma** boradi — payshanba (1 kun oldin) va
juma ertalab: qaysi kitob, nechta, qancha oldindan to'langan va olganda
qancha to'lanadi. Ular umumiy aksiya e'lonini qayta olmaydi.

100 ta kitob band qilinsa, bot «😔 Kitob qolmadi — keyingi juma aksiyasida
(9-oktabr) kitob olasiz!» deb yozadi, band qilish tugmasi yo'qoladi va
payshanba/juma umumiy eslatmasi yuborilmaydi.

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

Egasining Telegram ID si `KITOB_OLAMI_ADMIN_IDS` da bo'lsa, menyuda qo'shimcha
tugmalar chiqadi:

- **➕ Aksiya qo'shish** — juma (tugmalardan tanlanadi), kitob nomi,
  muqova rasmi, janr, odatiy narx, **tannarx**, aksiya narxi. Har juma
  **100 ta** kitob aksiyaga qo'yiladi (boshqa son kerak bo'lsa — workflow'da
  `AKSIYA_SONI`); 100 tasi buyurtma qilinsa, «tugadi» deb yoziladi.
  - Aksiya narxi odatiy narxdan **arzon**, lekin tannarxdan **arzon emas**
    bo'lishi shart — aks holda bot qabul qilmaydi.
  - Bot odatiy narxdan ~10% arzonini taklif qiladi (tannarxdan past
    tushmaydi): odatiy **400 000**, tannarx **340 000** → aksiya **360 000**.
  - Chegirma 30% dan oshsa, ogohlantiradi. Tannarxni mijozlar ko'rmaydi.
- **📋 Aksiyalar** — rejadagi aksiyalar, chegirma va har biridan foyda, nechta buyurtma
  olingani, aksiyasiz jumalar.
- **📦 Buyurtmalar** — to'lovi tekshirilayotgan bronlar ✅/❌ tugmalari bilan.
- **📊 Marketing** — mijozlar soni (bu hafta nechta yangi), buyurtmalar,
  sotilgan kitoblar, tushum, foyda, mijozlarga berilgan chegirma, buyurtma bergan va qayta kelgan mijozlar, 8 haftalik
  «Mijoz / Sotuv» grafigi, oxirgi aksiyalar natijasi, mijozlar yoqtirgan janrlar.
- **👥 Mijozlar** — ro'yxatdan o'tganlar soni, janrlar bo'yicha, telefonlar.
- `/ochir 3` — 3-aksiyani o'chirish.
- `/xabar matn` — barcha mijozlarga xabar (masalan, yangi kitoblar keldi).

## Ishga tushirish (bir marta)

1. **@BotFather** → `/newbot` → nomi «Kitob olami» → token.
2. GitHub: **Settings → Secrets and variables → Actions**:
   - *Secrets* → `KITOB_OLAMI_BOT_TOKEN` = token;
   - *Variables* → `KITOB_OLAMI_ADMIN_IDS` = do'kon egasining Telegram ID si
     (botga `/men` deb yozsangiz aytadi; bir nechta bo'lsa — vergul bilan);
   - *Variables* → `KITOB_OLAMI_TOLOV_KARTA` = oldindan to'lov kartasi raqami
     (bo'lmasa, mijoz yarim pulni do'konga kelib to'laydi).
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

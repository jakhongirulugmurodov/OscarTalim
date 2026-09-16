# AI Kutubxona

PDF kitoblar kutubxonasi: bir necha tilda (o'zbek, rus, ingliz, nemis, xitoy,
arab), o'qish tezligi bo'yicha reyting va muddati o'tganda avtomatik
eslatma bilan. Telegram Mini App sifatida ham, oddiy web-sahifa sifatida
ham ishlaydi — xuddi shu repodagi [`sinf`](../sinf/) va
[`anjuman`](../anjuman/) kabi.

## Qanday ishlaydi

- **Ro'yxatdan o'tish** — ilovaga kirishdan oldin shart: to'liq ism,
  telefon raqam, so'ng **Face ID / barmoq izi** bilan tasdiqlash (xuddi
  `sinf`dagi kabi — qurilmadan "egasini so'rash", serverda yuz taqqoslash
  emas).
- **Katalog** — kitoblarni tilga qarab filtrlaysiz (🇺🇿🇷🇺🇬🇧🇩🇪🇨🇳🇸🇦), qidirasiz,
  bosasiz — tavsif va mavjud tillar ochiladi.
- **O'qishni boshlash** — bir tilni tanlaysiz, PDF havolasi yangi oynada
  ochiladi va **14 kunlik** hisoblagich boshlanadi (bu son dastur ichida
  `PERIOD_DAYS` konstantasi — xohlasangiz o'zgartiring).
- **"Tugatdim"** tugmasi — o'qib bo'lgach bosiladi, necha kunda
  o'qilgani hisoblanadi va statistikaga qo'shiladi.
- **Reyting** — kamida bitta kitobni tugatgan o'quvchilar orasida, **eng
  kam o'rtacha muddatda o'qiganlar tepada**. Yangi ro'yxatdan o'tgan yoki
  hali hech narsa tugatmagan odam reytingda yo'q — bu ataylab shunday:
  "tezroq o'qi" mukofotlanadi, "hech narsa olma" emas.
- **Eslatma** — kitobni o'qish muddati tugasa, agar dastur **Telegram
  ichida** ochilgan bo'lsa, botdan avtomatik xabar keladi ("SMS" o'rniga —
  quyida sababi bor).

## Nega SMS emas, Telegram

Haqiqiy SMS (Eskiz.uz kabi O'zbekiston provayderi orqali) alohida hisob,
API kalit va pul talab qiladi. Telegram bot esa **shu repodagi bosqichda
allaqachon bor infratuzilma bilan, bepul va serversiz** ishlaydi (GitHub
Actions orqali, xuddi `sinf` botiga o'xshab). Shuning uchun birinchi
bosqichda shu tanlandi.

Agar keyinchalik haqiqiy SMS kerak bo'lsa: `bot/kutubxona_bot.py` dagi
`send()` funksiyasi o'rniga (yoki qo'shimcha ravishda) Eskiz.uz REST API'ga
so'rov yuboradigan funksiya qo'shiladi — qolgan hamma narsa (muddatlarni
kuzatish, qaysi foydalanuvchiga qachon yuborish) o'zgarishsiz qoladi.

## Ochish

**https://jakhongirulugmurodov.github.io/OscarTalim/kutubxona/**

Yoki Telegram orqali: `t.me/<bot_username>` → "Kutubxonani ochish" (bot
sozlangandan keyin, pastga qarang).

Mahalliy sinash uchun:

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/kutubxona/
```

`FB_CONFIG` bo'sh (`null`) qolsa — dastur **mahalliy rejim**da ishlaydi:
hamma narsa shu qurilmaning `localStorage`ida, sinov uchun qulay.
Nusxada u allaqachon to'ldirilgan — chunki bu ilova **`sinf` bilan bitta
Firebase loyihasini bo'lishadi** (API kaliti maxfiy emas, Firebase'da
xavfsizlik `firestore.rules` orqali ta'minlanadi, config orqali emas).

## Firebase — nima qilish kerak

Alohida loyiha yaratish shart emas: `sinf` uchun Firebase allaqachon
sozlangan bo'lsa, bu ilova ham darhol ishlaydi (config bir xil,
`docs/kutubxona/index.html` ichida `FB_CONFIG`).

Faqat **xavfsizlik qoidalarini** yangilash kerak — `firestore.rules`
faylida `libBooks`, `libUsers`, `libBorrows`, `libReminders`,
`libConfig` uchun qoidalar allaqachon qo'shilgan, ularni deploy qilish
kifoya:

**Repo → Actions → Firebase sozlash → Run workflow →**
`faqat_qoidalar: true` qo'yib ishga tushiring (google_auth maydoniga
oldin ishlatilgan havolani yoki yangisini bering — README'si:
[`../sinf/README.md`](../sinf/README.md#firebaseni-ulash)).

Yoki qo'lda: [console.firebase.google.com](https://console.firebase.google.com) →
loyiha → **Firestore Database → Rules** → shu repodagi `firestore.rules`
faylining to'liq mazmunini joylashtiring → Publish.

### Kutubxonachi (admin) bosh kaliti

Kitob qo'shish/o'chirish huquqi — `sinf`dagi bosh kalit patterni bilan
bir xil: **Profil → 🛠 Kutubxonachi** bo'limida birinchi marta istalgan
kalitni kiritgan odam o'sha kalitni belgilaydi (`libConfig/admin`
hujjatiga yoziladi, mijoz uni keyin o'qiy olmaydi — faqat solishtirish
uchun ishlatiladi). Boshqa kutubxonachilar xuddi o'sha kalitni bilishi
kerak.

## Telegram bot

Bot **GitHub Actions'da** ishlaydi, `sinf` botidan **alohida** (turli
bot = turli shaxs, turli mavzu). Har 15 daqiqada: (1) kelgan xabarlarga
javob beradi, (2) muddati o'tgan kitoblar uchun eslatma yuboradi.

Bir marta sozlash:

1. **@BotFather** → `/newbot` → token.
2. Repo → **Settings → Secrets and variables → Actions → New repository
   secret**: nomi `LIBRARY_BOT_TOKEN`, qiymati — token.
3. (Ixtiyoriy) o'sha yerda **Variables** → `LIBRARY_ADMIN_IDS` — o'z
   Telegram ID ingiz (botga `/men` deb yozsangiz aytadi). Shunda
   `/eslatma` va `/kim` buyruqlari sizga ochiladi.
4. **Actions → Kutubxona bot → Run workflow → rejim: `sozlash`** — menyu
   tugmasi, buyruqlar va tavsif o'rnatiladi.

E'lon yuborish (masalan "yangi kitoblar qo'shildi"): **Run workflow →
rejim: `eslatma`**, matnni yozing — botga yozgan hamma foydalanuvchiga
boradi. Yoki Telegram'da `/eslatma matn`.

Muddat eslatmasi qo'lda tekshirish uchun kutish shart emas — **Run
workflow → rejim: `xabarlar`** darhol ishga tushiradi (u ham xabarlarni,
ham muddatlarni tekshiradi).

Bot buyruqlari: `/start`, `/men`, `/eslatma <matn>` (kutubxonachi),
`/kim` (kutubxonachi).

O'z serveringiz bo'lsa, doimiy rejim ham bor (15 daqiqada bir marta
muddatlarni o'zi tekshiradi):

```bash
export BOT_TOKEN="..." APP_URL="https://<foydalanuvchi>.github.io/OscarTalim/kutubxona/"
python3 bot/kutubxona_bot.py
```

### Muddat eslatmasi qanday ishlaydi (texnik)

Bot Firestore'ni **hech qanday kalit yoki autentifikatsiyasiz**, oddiy
REST so'rov bilan o'qiydi — `libReminders` to'plami maxsus shu maqsadda
**ochiq o'qish uchun** qilib qo'yilgan (`firestore.rules`). U yerda
faqat: kitob nomi, muddat (`dueAtMs`) va Telegram ID (`chatId`) bor —
**ism va telefon YO'Q**. Xabar yuborilgach, bot faqat `reminded`
maydonini `true` qilib qo'yadi — buni ham istalgan kishi (hatto
kirmagan holda) qila oladi, chunki qoidalarda faqat shu bitta maydonga
cheklangan yozuvga ruxsat berilgan.

## Xavfsizlik: nima himoyalangan, nima emas

Himoyalangan:

- **Kutubxonachi bo'lish** faqat bosh kalit bilan — `sinf`dagi bilan bir
  xil pattern.
- **Telefon raqam va Telegram ID** — `libUsers/{uid}/private/contact`da,
  faqat egasi o'qiydi.
- **Boshqa foydalanuvchining kitob tarixini o'qib/yozib bo'lmaydi** —
  `libBorrows` faqat egasiga ochiq.
- Foydalanuvchi kiritgan har qanday matn ekranga qochirib chiqariladi
  (`escapeHtml`).

Hozircha bor cheklovlar (`sinf`dagi bilan bir xil mantiqda qabul
qilingan):

- **`libReminders` ochiq o'qiladi** — istalgan kishi u yerdagi Telegram
  ID, kitob nomi va muddatni ko'ra oladi (ism/telefon yo'q). Bu — bot
  server kodisiz (Cloud Functions'siz) ishlashi uchun ataylab qilingan
  murosaga.
- **Statistika (`finishedCount`, `totalDays`) mijoz tomonidan yoziladi**
  — `sinf`dagi ball tizimi kabi. Qat'iy hisob kerak bo'lsa, Cloud
  Functions orqali yozish kerak.
- **Telegram ID faqat Mini App ichida ochilganda olinadi**
  (`initDataUnsafe`, server tomonda tekshirilmagan — `sinf`dagi bilan
  bir xil cheklov). Oddiy brauzerda ochilsa, eslatma yubora olmaydi —
  Profil bo'limida shu haqda ogohlantirish bor.

## Fayllar

```
docs/kutubxona/
├── index.html            # butun dastur (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg, icon-maskable.svg
└── README.md
bot/
├── kutubxona_bot.py       # Telegram bot (faqat standart kutubxona)
.github/workflows/
└── kutubxona-bot.yml      # bot GitHub Actions'da: har 15 daqiqada + qo'lda
```

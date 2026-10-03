# 📚 «Mutolaa» kitob uyi — Telegram bot

Kitob do'koni uchun tayyor bot: auditoriya yig'adi, qoldiq kitoblarni
(masalan, 100 ta «Muqaddima») juma aksiyasi orqali sotadi va kitobxonlarni
muntazam xabardor qilib turadi. Faqat Python standart kutubxonasi — hech
narsa o'rnatish shart emas.

## Kitobxon nimani ko'radi

| Bo'lim | Nima bor |
|---|---|
| **Ro'yxatdan o'tish** (8 qadam, ~1 daqiqa) | ism, familiya, yosh, telefon (tugma bilan), sevimli janrlar, 3 savollik so'rovnoma: oyiga nechta kitob o'qiydi, bizni qayerdan topdi, kitobni qanday olishni xohlaydi |
| 🔥 **Juma aksiyasi** | juma kuni — aksiya kitobi: ~~300 000~~ → **239 000 so'm**, qancha qolgani, «Buyurtma berish». Boshqa kunlari — keyingi aksiyagacha necha kun qolgani va janr bo'yicha kichik maslahat |
| 📚 **Katalog** | janrlar → kitoblar ro'yxati → kitob kartochkasi: narx, **✅ qancha sotildi, 📦 qancha qoldi**, sotilish foizi `▰▰▰▱▱▱`, buyurtma va «Do'stga ulashish» tugmasi. «To'liq ro'yxat» — barcha kitoblar bitta ro'yxatda |
| 🏆 **Top kitoblar** | haftaning eng ko'p sotilgan 10 ta kitobi |
| 🔎 **Qidirish** | istalgan payt kitob nomi yoki muallifini yozish kifoya. Topilmasa — «So'rov qoldirish» (admin qaysi kitoblarga talab borligini ko'radi) |
| 🎁 **Sovg'alarim** | olingan sovg'alar (xatcho'p, stikerlar...) va kitobxon darajasi: 🌱 → 📖 → 📚 → 🦉 → 👑 |
| 👤 **Profilim** | ma'lumotlar, janrlarni o'zgartirish, shaxsiy **taklif havolasi** (do'st kelsa, xabar keladi) |
| 📍 **Do'kon haqida** | manzil, ish vaqti, telefon, xarita, Instagram, kanal |

## Avtomatik ishlar (Toshkent vaqti)

| Qachon | Nima |
|---|---|
| **Payshanba 19:00** | «Ertaga — juma! Soat 9:00 da aksiya kitobi e'lon qilinadi» eslatmasi |
| **Juma 09:00** | Haftalik xabar hammaga: ismi bilan salom, haftaning top-5 kitobi, bugungi aksiya (narx, qoldiq), kitob kitobxon yoqtirgan janrdan bo'lsa — «💡 siz yoqtirgan janrdan!». `KANAL_ID` berilsa — kanalga ham |
| Juma, aksiya belgilanmagan bo'lsa | Bot o'zi eng ko'p qoldig'i bor kitobni −20% bilan tanlaydi va adminga aytadi |
| **Har kuni 23:00** | Baza zaxirasi (fayl) birinchi adminga |

Juma kuni bot orqali berilgan buyurtmalar avtomatik aksiya narxida yoziladi.

## Buyurtma va sovg'a qanday ishlaydi

1. Kitobxon «🛒 Buyurtma berish» → «✅ Tasdiqlash».
2. Admin(lar)ga (yoki `BUYURTMA_CHAT_ID` guruhiga) xabar keladi: ism, telefon,
   kitob, narx, qanday olishni xohlashi — **[✅ Sotildi] [❌ Bekor]** tugmalari bilan.
3. Operator qo'ng'iroq qiladi. Kitob berilganda «✅ Sotildi» bosiladi:
   qoldiq kamayadi, «sotildi» ko'payadi, omborda bor sovg'alardan biri
   (xatcho'p, stikerlar, kartochka) avtomatik biriktiriladi va kitobxonga
   «Rahmat! Sovg'angiz: 🔖 Xatcho'p» xabari boradi.
4. Qoldiq 5 tadan kamaysa — adminga ogohlantirish.

Do'konning o'zida sotilgan kitoblar ham hisobga kirishi uchun: `/sotuv 5`
(yoki `/sotuv 5 2 +998901234567` — xaridor botda bo'lsa, sovg'a va rahmat
xabari unga yoziladi).

## Admin buyruqlari

`/admin` — hammasi bitta joyda. Asosiylari:

| Buyruq | Nima qiladi |
|---|---|
| `/statistika` | kitobxonlar soni, bugun/hafta qo'shilganlar, yosh, janr qiziqishlari, so'rovnoma javoblari, Instagram/Telegram havolasidan kelganlar, eng ko'p do'st taklif qilganlar, savdo (bugun / 7 kun / jami), sovg'alar qoldig'i |
| `/buyurtmalar` | kutilayotgan buyurtmalar tugmalari bilan |
| `/qoldiq` | har kitob: ID, qoldi, sotildi, narx |
| `/aksiya_qoy 1 239000` | shu juma aksiyasi (`... keyingi` — bir hafta keyin) |
| `/haftalik_test` | juma xabarini oldindan o'zingizga ko'rish |
| `/kitob_qosh Nomi \| Muallif \| janr \| narx \| soni` | kitob qo'shish (bor bo'lsa — yangilanadi) |
| `/narx 5 120000`, `/soni 5 40`, `/ochir 5` | tahrirlash |
| rasm + izoh `/rasm 5` | kitob muqovasi (kartochka rasmli chiqadi) |
| **.csv fayl yuborish** | butun katalogni yuklash/yangilash |
| `/xabar matn` (rasm bilan ham) | hammaga xabar |
| `/xabar_janr tarix matn` | faqat shu janrni yoqtirganlarga |
| `/sovga_qosh 🔖 Xatcho'p \| 200`, `/sovga_qoldiq` | sovg'alar ombori |
| `/sorovlar` | kitobxonlar so'ragan, lekin do'konda yo'q kitoblar |
| `/instagram` | Instagram post uchun tayyor matn + bot havolasi |
| `/eksport` | 3 ta CSV (Excel): kitobxonlar, sotuvlar, katalog |
| `/zaxira`, fayl + izoh `/tikla` | baza nusxasi va uni tiklash |

### Katalogni Excel orqali yuklash

Namuna — [`kitoblar.csv`](kitoblar.csv) (bot birinchi ishga tushganda shu
namuna katalogni yuklaydi — o'zingiznikiga almashtiring):

```
nomi;muallif;janr;narx;soni;tavsif
Muqaddima;Ibn Xaldun;tarix;300000;100;Tarix falsafasi ...
```

Excel'da to'ldiring → «Saqlash» → **CSV UTF-8** → faylni botga yuboring.
Nomi va muallifi bir xil kitob yangilanadi (narx, soni), yangilari
qo'shiladi. Eng oson yo'l: `/eksport` dan kelgan `katalog-....csv` ni
o'zgartirib, qayta yuborish. Janr kalitlari: `/janrlar`
(badiiy, tarix, diniy, falsafa, psixologiya, biznes, rivojlanish, ilmiy,
jahon, detektiv, sheriyat, bolalar — nomini to'liq yozsa ham bo'ladi).

## 15k Telegram + 100k Instagram auditoriyani botga olib kelish

- **Telegram kanal**: bot havolasi — `https://t.me/BOT?start=kanal`.
  Juma xabari kanalga ham avtomatik chiqadi («Botda buyurtma berish» tugmasi bilan).
- **Instagram**: bio va storiesga `https://t.me/BOT?start=instagram`
  (`/instagram` tayyor matn beradi). Kim qaysi havoladan kelgani `/statistika` da.
- **Aksiya havolasi**: `https://t.me/BOT?start=aksiya` — ro'yxatdan o'tgach
  darhol aksiya kitobini ko'rsatadi.
- **Kitob havolasi**: `https://t.me/BOT?start=b5` — to'g'ridan-to'g'ri 5-kitob.
- **Do'stni taklif**: har kitobxonning `?start=r<ID>` havolasi bor; eng faollari `/statistika` da.

## Ishga tushirish

### 1. Bot tokeni
Telegram'da [@BotFather](https://t.me/BotFather) → `/newbot` → nom (masalan
«Mutolaa kitob uyi») va username (masalan `mutolaa_kitob_bot`) → token.
O'z Telegram ID ingizni bilish uchun [@userinfobot](https://t.me/userinfobot).

### 2-a. GitHub Actions'da (server kerak emas)

1. Repo → **Settings → Secrets and variables → Actions**:
   - *Secrets*: `MUTOLAA_BOT_TOKEN` (token), `MUTOLAA_DB_KEY` (istalgan uzun parol — bazani shifrlaydi, **yo'qotmang**).
   - *Variables*: `MUTOLAA_ADMIN_IDS` (masalan `123456789,987654321`),
     ixtiyoriy: `MUTOLAA_KANAL_ID` (`@kanal`), `MUTOLAA_BUYURTMA_CHAT_ID`,
     `DOKON_NOMI`, `DOKON_MANZIL`, `DOKON_TELEFON`, `DOKON_ISH_VAQTI`,
     `DOKON_XARITA`, `DOKON_INSTAGRAM`.
2. `mutolaa-bot.yml` `main` shoxchasida bo'lishi kerak (jadval faqat shu yerda ishlaydi).
3. **Actions → Mutolaa kitob bot → Run workflow** — bot ishga tushadi,
   keyin har soatda o'zi davom ettiradi.

Workflow bir ishga tushishda ~2 soat ishlaydi; keyingisi navbatda turadi,
shuning uchun bot uzluksiz javob beradi. Baza shifrlangan holda Actions
keshida saqlanadi. Ochiq (public) repoda Actions daqiqalari bepul; yopiq
(private) repoda oylik limit bot uchun yetmaydi — unda serverdan foydalaning.

### 2-b. Serverda (VPS) — eng ishonchli yo'l

```bash
git clone https://github.com/jakhongirulugmurodov/OscarTalim /opt/OscarTalim
# mutolaa-bot.service ichida BOT_TOKEN, ADMIN_IDS va boshqalarni to'ldiring
sudo cp /opt/OscarTalim/mutolaa_bot/mutolaa-bot.service /etc/systemd/system/
sudo systemctl enable --now mutolaa-bot
```

Yoki shunchaki: `BOT_TOKEN=... ADMIN_IDS=... python3 mutolaa_bot/bot.py`

### 3. Kanal va guruh (ixtiyoriy)
- Botni kanalingizga **admin** qilib qo'shing va `KANAL_ID=@kanal` bering.
- Buyurtmalar bir nechta operatorga tushishi uchun guruh oching, botni qo'shing,
  guruh ID sini (`-100...`) `BUYURTMA_CHAT_ID` ga yozing. «Sotildi» tugmasini
  faqat `ADMIN_IDS` dagilar bosa oladi.

### 4. Birinchi sozlash
1. Botga `/start` → ro'yxatdan o'ting (o'zingiz ham kitobxon sifatida ko'rasiz).
2. CSV bilan haqiqiy katalogni yuklang, `/sovga_qosh` bilan sovg'alar sonini kiriting.
3. `/aksiya_qoy <Muqaddima ID> 239000` → `/haftalik_test`.
4. Kanal va Instagram'ga havolani joylang.

## Fayllar

| Fayl | Nima |
|---|---|
| `bot.py` | bot: bo'limlar, ro'yxatdan o'tish, buyurtma, admin, jadval |
| `baza.py` | SQLite baza: kitobxonlar, kitoblar, buyurtmalar, sovg'alar |
| `tg.py` | Telegram Bot API (urllib) |
| `kitoblar.csv` | namuna katalog |
| `mutolaa-bot.service` | server uchun systemd xizmati |
| `../.github/workflows/mutolaa-bot.yml` | GitHub Actions'da ishlatish |

Janrlar, yosh oraliqlari, so'rovnoma savollari, sovg'alar va darajalar
`bot.py` boshida — o'zgartirish oson.

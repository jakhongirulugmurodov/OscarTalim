# Kitob do'koni — Telegram bot

Kitob do'koni uchun bot: mijozni tanib oladi, kitob bor-yo'qligini va narxini
aytadi, yangi kitoblar va juma aksiyalari haqida xabar beradi, har xariddan
keyin sovg'a yuboradi. Do'kon egasiga qaysi kitoblar so'ralayotganini ko'rsatadi.

Faqat Python standart kutubxonasi ishlatilgan — o'rnatadigan narsa yo'q.

## Mijoz nimani ko'radi

1. **/start** — do'kon bilan tanishtiruv (nomi, manzil, ish vaqti, telefon,
   juma aksiyalari), keyin ro'yxatdan o'tish:
   - ism va familiya
   - telefon raqam (tugma bilan yoki yozib)
   - yoqtirgan janrlar (bir nechtasini tanlasa bo'ladi)
   - eng yaxshi ko'rgan kitob yoki muallif
   - so'rovnoma: qanchalik ko'p o'qiydi, qaysi tilda, oyiga qancha sarflaydi,
     do'konni qayerdan bildi
   - oxirida — **ro'yxat sovg'asi** (masalan, birinchi xaridga 5% chegirma) va kod.
2. **Menyu:**
   | Tugma | Nima qiladi |
   |---|---|
   | 🔎 Kitob bormi? | Nomi yoki muallifini yozadi (tugmasiz ham bo'ladi — shunchaki yozsa kifoya) |
   | 🆕 Yangi kelganlar | Oxirgi kelgan kitoblar, narxi, chegirmasi |
   | 📅 Keyingi hafta | Keyingi hafta keladigan kitoblar |
   | 🔥 Aksiyalar | Chegirmadagi kitoblar + «eng katta aksiya — juma kuni» |
   | 🎁 Sovg'alarim | Olgan sovg'alari va kodlari |
   | 🏪 Do'kon haqida | Manzil, mo'ljal, ish vaqti, telefon, yetkazib berish |

**Kitob so'ralganda:**
- **Bor** → «✅ Ha, bor!», narxi, chegirmasi (eski narx ustidan chizilgan), nechta qolgani.
- **Tugagan / yo'q** → keyingi hafta keladimi — aytadi; kelmasa, keyingi hafta
  keladigan kitoblar ro'yxatini ko'rsatadi. So'rov yozib qo'yiladi va kitob
  kelishi bilan mijozga **o'zi xabar beradi**.

**Juma** — har juma barcha kitoblarga qo'shimcha chegirma (`juma_qoshimcha`,
standart 10%). Juma kuni botdagi hamma narxlar shu chegirma bilan chiqadi va
ertalab 09:00 da hamma mijozga aksiya xabari boradi.

## Do'kon egasi buyruqlari

Botga `/men` deb yozing — Telegram ID ingizni aytadi. Uni `KITOB_ADMIN_IDS`
ga qo'ying, keyin `/yordam` hamma buyruqni ko'rsatadi.

| Buyruq | Nima qiladi |
|---|---|
| `/xarid 901234567 350000` | Xarid yozildi → mijozga «🎉 Siz sovg'aga ega bo'ldingiz» xabari va sovg'a kodi boradi |
| `/sovga 901234567 Bepul xatcho'p` | Qo'lda sovg'a yuborish |
| `/ishlat KT-1234` | Mijoz kassada kodni ko'rsatdi — ishlatildi deb belgilash |
| `/yangi Nomi \| Muallif \| Janr \| Narx \| Chegirma \| Soni` | Yangi kitob keldi → katalogga qo'shiladi, **hamma mijozga** xabar boradi (o'sha janrni yoqtirganlarga «💚 Siz yoqtirgan janrdan!»), so'raganlarga alohida |
| `/keladi Nomi \| Muallif \| Janr` | Keyingi hafta keladigan kitob |
| `/keladi_tozala` | Yangi hafta — ro'yxatni tozalash |
| `/kitoblar` | Katalog: id, narx, soni |
| `/soni 5 10` · `/narx 5 70000` · `/chegirma 5 15` · `/ochir 5` | Kitobni o'zgartirish (id bo'yicha) |
| `/stat` | Qaysi janrlar yoqadi, so'rovnoma natijalari, **eng ko'p qidirilgan** va **so'ralgan, lekin yo'q** kitoblar |
| `/mijozlar` | Ism, telefon, janrlar |
| `/tarqat Matn` | Hammaga xabar |
| `/juma` | Juma aksiyasi xabarini hozir yuborish |

Sovg'a qanday bo'lishi xarid summasiga bog'liq — `dokon.json` dagi
`sovga_qoidalari`:

```json
{"dan": 500000, "sovga": "Keyingi xaridingizga 20% chegirma + sovg'a xatcho'p"},
{"dan": 250000, "sovga": "Keyingi xaridingizga 10% chegirma"},
{"dan": 0,      "sovga": "Keyingi xaridingizga 5% chegirma"}
```

## Sozlash

1. **@BotFather** → `/newbot` → token oling.
2. **`kitob_bot/dokon.json`** ni to'ldiring: do'kon nomi, manzil, telefon,
   ish vaqti, janrlar, so'rovnoma savollari, sovg'alar, kitoblar ro'yxati.
   ⚠️ Hozirgi kitoblar va narxlar — **namuna**, o'zingiznikiga almashtiring.
3. GitHub → **Settings → Secrets and variables → Actions**:
   - secret `KITOB_BOT_TOKEN` — token
   - variable `KITOB_ADMIN_IDS` — sizning Telegram ID ingiz (bir nechta bo'lsa vergul bilan)
4. **Actions → Kitob do'koni bot → Run workflow**:
   - `sozlash` — buyruqlar menyusi va bot tavsifi (bir marta)
   - `katalog` — `dokon.json` dagi kitoblarni qaytadan yuklash
     (bot ichida qilingan o'zgarishlar o'chadi)
   - `eslatma` — hammaga xabar
   - `juma` — juma aksiyasi xabari

Katalog birinchi ishga tushganda `dokon.json` dan olinadi; keyin kitob
qo'shish/o'zgartirishni bot ichida `/yangi`, `/soni` va boshqalar bilan qiling.

## Qayerda ishlaydi

**GitHub Actions** (tekin, server kerak emas): bot har 5 daqiqada
xabarlarni oladi. Kamchiligi — javob 5 daqiqagacha kechikadi, ro'yxatdan
o'tish ham shuncha cho'ziladi. Jadval faqat `main` shoxchasida ishlaydi.

**O'z serveringizda** (javob darhol keladi — do'kon uchun tavsiya):

```bash
export BOT_TOKEN=123:ABC
export ADMIN_IDS=123456789
python3 kitob_bot/bot.py          # doimiy ishlaydi
```

Juma xabari uchun server `cron`iga: `0 9 * * 5 python3 kitob_bot/bot.py --juma`.

Bu holda Actions'dagi workflow'ni o'chirib qo'ying — ikkalasi bir vaqtda
xabar ola olmaydi.

## Ma'lumotlar

`baza.json` (Actions'da — `actions/cache` ichida): mijozlar (ism, telefon,
janrlar, so'rovnoma javoblari, sovg'alar), xaridlar, qidiruvlar, kutish
ro'yxati va katalog. Telefon raqamlar shaxsiy ma'lumot — bazani begona
odamlarga bermang.

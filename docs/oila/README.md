# Oilaviy xarajatlar

Oila a'zolari (ota, ona, farzandlar) o'z hisobidan kirib, kunlik xarajatlarni
kiritadigan umumiy byudjet dasturi. Har kim o'z qurilmasidan yozadi, hammaga
bitta umumiy hisobot ko'rinadi.

## Nima beradi

- **Umumiy oila balansi** — oylik byudjet, shu kungacha sarflangan summa va
  qolgan pul har doim tepada ko'rinadi (progress chizig'i bilan).
- **Toifalar** — Oziq-ovqat, Kommunal to'lovlar, Transport va yoqilg'i,
  Kiyim-kechak, Ta'lim, Ko'ngilochar, Boshqa (o'zgartirish/qo'shish mumkin).
- **Kim qancha sarfladi** — har bir xarajat yonida uni kim yozgani ko'rinadi;
  "A'zolar" bo'limida oy bo'yicha reyting.
- **Grafiklar** — toifalar bo'yicha doira diagramma, toifa byudjetlari uchun
  progress chiziqlari (oshib ketganda qizil).
- **Oy xulosasi** — eng ko'p sarflangan toifa, eng ko'p xarajat qilgan a'zo,
  byudjetdan oshgan toifalar — tanlangan oy uchun avtomatik hisoblanadi.

## Qo'shilish

1. Bir kishi **"Yangi oila yaratish"** orqali oila ochadi — nom, o'z ismi va
   6+ belgili PIN kiritadi. Dastur 6 xonali **oila kodi**ni o'zi yaratadi.
2. Kod va PIN oila a'zolariga (Telegram, SMS va h.k.) yuboriladi.
3. Har bir a'zo **"Oilaga qo'shilish"** orqali kod + PIN + o'z ismi bilan
   kiradi. Shundan keyin xarajat kiritishi mumkin.

A'zolik qurilmaga bog'langan (Firebase anonim kirish). Bitta odam ikkita
qurilmadan kirsa, ikkita alohida a'zo bo'lib ko'rinadi — bu bilinadigan
cheklov.

## Texnik qurilma

Bitta fayl (`index.html`): HTML + CSS + JS, backend — Firebase Firestore
(real vaqtli, barcha qurilmalarda bir xil ma'lumot). Firebase konfiguratsiyasi
`sinf` ilovasi bilan **bir xil loyiha** — faqat yangi `families` to'plami
qo'shilgan, `classes` to'plamiga tegilmagan.

`FB_CONFIG` bo'lmasa (yoki bulutga ulanolmasa) dastur avtomatik **mahalliy
rejim**ga o'tadi: hammasi shu qurilmaning `localStorage`ida — sinov yoki
offline ishlatish uchun qulay, lekin oila a'zolari orasida sinxron emas.

Ma'lumotlar modeli (Firestore):

```
families/{code}                        — nomi, oylik byudjet, toifa byudjetlari, toifalar
families/{code}/private/auth           — PIN (faqat a'zolarga ko'rinadi)
families/{code}/members/{uid}          — ism, rol (Ota/Ona/Farzand/Boshqa)
families/{code}/expenses/{id}          — summa, toifa, sana, izoh, kim yozgani
```

Xavfsizlik qoidalari `firestore.rules` faylida (`families/{f}` bo'limi):

- Oilaga faqat **to'g'ri PIN** bilan qo'shilish mumkin (server tomonda
  tekshiriladi, mijoz kodiga ishonilmaydi).
- Boshqa a'zo nomidan xarajat yozib bo'lmaydi (`memberUid` o'zining
  `uid`siga teng bo'lishi shart).
- Xarajatni faqat **o'zi yozgan odam** tahrirlash/o'chirishi mumkin — "kim
  qancha sarfladi" hisobi ishonchli qolishi uchun.
- Byudjet va toifalarni istalgan a'zo o'zgartirishi mumkin (ishonchli oila
  muhiti uchun qulaylik).

`.github/workflows/firebase-setup.yml` skripti qoidalarni `docs/sinf/README.md`
dagi bitta ```js``` blokidan o'qib qayta yozadi — shuning uchun yangi qoidalar
**shu bloknikiga ham qo'shilgan**, aks holda keyingi "Firebase sozlash" ishga
tushirilganda o'chib qoladi.

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/oila/
```

## Fayllar

```
docs/oila/
├── index.html            # butun dastur (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg, icon-maskable.svg
└── README.md
```

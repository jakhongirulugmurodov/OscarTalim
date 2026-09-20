# Oscar Viktorina

Mavzulashtirilgan bilim viktorinasi: kategoriyalar bo'yicha testlar, shaxsiy
kabinet, nishonlar, kunlik/haftalik/umumiy reyting, do'stlar bilan **jonli**
(real-time) bellashuv xonalari va foydalanuvchilarning o'z testini
yaratib nashr qilish imkoniyati.

Arxitektura sinf/anjuman ilovalari bilan bir xil andoza: **bitta fayl**
(`index.html` — HTML + CSS + JS), Firebase Firestore backend (yoki
mahalliy rejim), PWA sifatida telefonga o'rnatiladi.

## Nima bor

| Bo'lim | Tavsif |
|---|---|
| **Kategoriyalar** | Dasturlash, Tarix, Fan, Tillar, Pop madaniyat, Madaniyat, Umumiy bilim — har birida tayyor testlar + foydalanuvchilar qo'shgan testlar |
| **O'yin** | 4 variantli savol, har savolga taymer, tezlik uchun qo'shimcha ball (Kahoot uslubida: 500–1000 ball) |
| **Profil / Kabinet** | Taxallus, avatar, XP va daraja, statistika (aniqlik, ketma-ketlik, mukammal testlar), tarix |
| **Nishonlar** | 10 xil nishon: birinchi test, 10/50 marta, mukammal natija, chaqqonlik, ko'p qirralilik, ijodkorlik va h.k. |
| **Reyting** | Kunlik, haftalik, umumiy — uchtasi ham alohida hisoblanadi |
| **Jonli bellashuv** | PIN kod bilan xona, do'stlar bir vaqtda javob beradi, har savoldan keyin javoblar taqsimoti va yakuniy reyting |
| **Test yaratuvchi** | Har kim o'z testini tuzib nashr qilishi, keyin o'chirishi mumkin |

## Ball va daraja tizimi

Har savol uchun: to'g'ri javob — 500 dan 1000 gacha ball (qolgan vaqtga
proportsional, Kahoot'dagidek tezlik bonusi). Bitta testdan yig'ilgan
ball 10 ga bo'linib **XP** ga aylanadi. Daraja: har 500 XP — 1 daraja
(`Yangi boshlovchi → ... → Oskar`, 10 nom).

Reyting uch mustaqil hisoblagichdan iborat:
- **Umumiy** — hisobning butun umri davomidagi XP;
- **Kunlik** — har kuni 00:00 da (birinchi o'sha kungi urinishda) noldan boshlanadi;
- **Haftalik** — har dushanba noldan boshlanadi (sinf ilovasidagi haftalik
  reyting g'oyasi bilan bir xil: orqada qolgan hafta boshida hammaga teng imkon).

## Jonli xona qanday ishlaydi

1. Mezbon istalgan (tayyor yoki foydalanuvchi yaratgan) testni tanlab
   xona ochadi — 6 xonali PIN kod chiqadi.
2. Do'stlar PIN va ismini kiritib qo'shiladi (lobbi holatida).
3. Mezbon "Boshlash"ni bosadi — hamma bitta savolni bir vaqtda ko'radi,
   taymer boshlaydi.
4. Hamma javob berishi bilan (yoki mezbon qo'lda bossa) javoblar
   taqsimoti ustunli diagrammada ko'rsatiladi, to'g'ri javob ochiladi.
5. "Keyingi savol" — oxirgisidan keyin yakuniy reyting chiqadi, har
   kimning shaxsiy statistikasi va XP'siga qo'shiladi.

Bu **Firestore `onSnapshot`** orqali ishlaydi — WebSocket emas, lekin
amalda deyarli bir zumda yangilanadi (odatda bir soniyadan kam).

## Firebase

Ilova **sinf** ilovasi bilan bitta Firebase loyihasini (`oscartalim-sinf-80da0`)
ishlatadi, lekin butunlay boshqa to'plamlarga yozadi: `qUsers`, `qQuizzes`,
`qRooms` (+ ichki `qResults`, `players`). Shuning uchun ikkala ilova
bir-biriga hech qanday ta'sir qilmaydi va alohida sozlash shart emas —
`firestore.rules` allaqachon yangilangan (qoidalarni Firebase konsoliga
qo'lda joylashtirish yoki repo'dagi "Firebase sozlash" Actions ish
oqimidan foydalanish mumkin, xuddi sinf ilovasidagidek).

`FB_CONFIG` bo'sh yoki bulut ulanmasa, ilova avtomatik **mahalliy
rejim**ga o'tadi (hammasi `localStorage`da). Mahalliy rejimda jonli
xonalar faqat **bitta brauzerning turli varaqlari** orasida ishlaydi
(`localStorage` + `storage` hodisasi orqali) — haqiqiy ko'p qurilmali
o'yin uchun bulut ulanishi shart.

## Xavfsizlik va bilingan cheklovlar

Himoyalangan (Firestore qoidalari bilan):
- Har kim faqat **o'z** profiliga, o'z natijalar tarixiga va o'z jonli
  xona ishtirokchisi hujjatiga yoza oladi.
- Test faqat **muallifi** tomonidan o'chiriladi/tahrirlanadi; boshqalar
  faqat "o'ynalgan marta" sonini oshirishi mumkin.
- Jonli xonani faqat **mezbon** boshqaradi (savol almashtirish, boshlash).

Bilingan cheklovlar (server funksiyasi — Cloud Functions — yo'qligi sababli,
xuddi sinf ilovasidagidek ochiq aytilgan):
- **Ball/XP mijoz tomonidan hisoblanadi va yoziladi.** Texnik jihatdan
  ustalik bilan devtools ochib firibgarlik qilish mumkin. Ommaviy, norasmiy
  bellashuv uchun yetarli; rasmiy musobaqa uchun serverda hisoblovchi
  Cloud Function kerak bo'lardi.
- **Savol va to'g'ri javoblar mijoz tomoniga to'liq yuboriladi** (xona
  hujjatida ham) — devtools orqali oldindan ko'rish mumkin.
- **Kunlik/haftalik reyting** har foydalanuvchi o'zi o'ynaganda "yangilanadi";
  agar kimdir kecha o'ynab bugun o'ynamasa, uning eski kunlik balli bir muncha
  vaqt ro'yxatda "muzlagan" holda qolishi mumkin (server cron yo'qligi
  sababli) — reyting so'rovi buni mumkin qadar filtrlaydi, lekin 100%
  kafolat yo'q.
- **Jonli xonalar avtomatik o'chirilmaydi** — vaqt o'tishi bilan Firestore'da
  yig'ilib boradi (cron/Cloud Function bo'lmagani uchun). Amaliy zarari yo'q,
  lekin uzoq muddatda konsoldan qo'lda tozalash tavsiya etiladi.
- Taymer sinxronizatsiyasi mezbon va o'yinchining **shaxsiy soatiga**
  asoslangan (server vaqtiga emas) — internet kechikishi tufayli bir necha
  o'n millisoniyalik farq bo'lishi mumkin, lekin o'yinga sezilarli ta'sir
  qilmaydi.

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/viktorina/
```

Jonli xonani mahalliy rejimda sinash uchun **bitta brauzerda ikki varaq**
oching: birida xona yarating (mezbon), ikkinchisida PIN bilan qo'shiling
(o'yinchi) — ikkisi bitta `localStorage`ni ko'radi.

## Fayllar

```
docs/viktorina/
├── index.html            # butun ilova (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg, icon-maskable.svg
└── README.md
```

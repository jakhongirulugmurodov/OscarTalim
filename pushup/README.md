# Anjuman Murabbiy

Anjuman (push-up) mashg'ulotlarini **qo'l tegizmasdan** bajarish uchun web-dastur.
1-oylik va 3-oylik rejalar dasturga kiritilgan; raqamlar sizning darajangizga qarab
o'zi hisoblanadi va har mashg'ulotdan keyin o'zi sozlanadi.

## Asosiy g'oya

Anjuman paytida qo'llar yerda — telefonni ushlab, ekranni aylantirib bo'lmaydi.
Shuning uchun dastur **o'zi gapiradi, o'zi sanaydi, o'zi dam beradi va o'zi keyingi
mashqqa o'tadi**. Telefonni yerga qo'yasiz va unga tegmaysiz.

## Nima qiladi

| | |
|---|---|
| **Kalibrovka testi** | Birinchi kuni maksimal test → butun reja shu raqamdan qayta hisoblanadi |
| **Avto-moslashuv** | Har mashqdan keyin "Oson / Normal / Qiyin" → keyingi safargi raqamlar o'zgaradi |
| **3 xil sanash** | Ekranga tegish (burun bilan), metronom (o'zi sanaydi), kamera (harakatni o'zi ko'radi) |
| **Ovozli murabbiy** | Mashq nomi, takrorlar, dam olish — hammasi ovoz bilan |
| **Tempo metronomi** | Pastga 2/3, yuqoriga 1/3 — ekran ritm bilan "nafas oladi" |
| **Dam taymeri** | Setlar orasida avtomatik sanoq, oxirgi 3 soniyada signal |
| **Faza almashuvi** | 16 ta mashg'ulotdan keyin 3-oylik rejaga o'tish taklif qilinadi |
| **Statistika** | Haftalik hajm, mushak guruhlari taqsimoti, burnout rekordi, tarix |
| **Offline** | Telefonga o'rnatiladi (PWA), internetsiz ishlaydi |

## Sanash rejimlari

- **Teginish** — ekranning istalgan joyi katta tugma. Qo'l yerda qolgani uchun burun
  yoki peshona bilan tegiladi. Telefon bosh ostida turadi.
- **Metronom** — dastur tempo bilan o'zi sanaydi va bip qiladi; siz ritmga ergashasiz.
- **Kamera** — telefon yerda, ko'krak ostida, ekran yuqoriga qaraydi. Pastga
  tushganingizda old kamera qorayadi — dastur yorug'lik o'zgarishidan takrorni sanaydi.
  Tasvir hech qayerga yuborilmaydi, faqat o'rtacha yorug'lik o'lchanadi.

## Rejalar

**1-oylik (baza, haftada 4 kun)**
1. Oddiy anjuman — 3-4 set × 10-12
2. Keng ushlab — 2-3 set × 8-10
3. Olmos (diamond) — 2 set × maksimal

**3-oylik (progress, haftada 4-5 kun)**
1. Oyoq balandda — 3 set × 15-18
2. Keng ushlab — 3 set × 15-20
3. Olmos (diamond) — 3 set × 12-15
4. Yakuniy burnout — 1 set × charchaguncha

Ko'rsatilgan raqamlar 20 marta anjuman qila oladigan odam uchun. Kalibrovka testidan
keyin ular sizning natijangizga proporsional ravishda qayta hisoblanadi
(minimum 3 takror).

## Moslashuv formulasi

Har mashq uchun alohida koeffitsient `k` saqlanadi:

```
maqsad = reja_takrori × (sizning_maksimum / 20) × k
```

Mashqdan keyingi javobga qarab:

- **Oson** → `k × 1.06`
- **Normal** → `k × 1.025`
- **Juda qiyin** → `k × 0.98`
- Maqsadning 85% dan kami bajarilsa → qo'shimcha `× 0.92`

`k` 0.5 va 3 oralig'ida ushlab turiladi. Sozlamalardan istalgan vaqtda tiklash mumkin.

## Ishga tushirish

Oddiy statik sayt — server kerak emas:

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/pushup/
```

GitHub Pages'da `/pushup/` manzilida ochiladi. Telefonda brauzer menyusidan
"Bosh ekranga qo'shish" desangiz alohida ilovaga aylanadi.

## Ma'lumot

Hamma narsa `localStorage` da, faqat shu qurilmada saqlanadi. Hech qayerga
yuborilmaydi. Sozlamalar → "Nusxa olish" orqali JSON ko'rinishida saqlab olish mumkin.

## Fayllar

```
pushup/
├── index.html            # butun dastur (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg
└── icon-maskable.svg
```

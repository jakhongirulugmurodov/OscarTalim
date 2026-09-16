# So'z Kartochkalari — AI

So'z yodlash uchun bepul, faqat brauzerda ishlaydigan dastur. Server yo'q,
ma'lumotlar bazasi yo'q — hamma narsa shu qurilmada, o'zingizning bepul
Gemini API kalitingiz bilan ishlaydi.

## Qanday ishlaydi

1. **Kirish** — sayt sizni AI yordamchi sifatida kutib oladi (Gemini kabi
   yozib chiqadigan salomlashuv).
2. **So'z kiritish** — yodlamoqchi bo'lgan so'zlarni matn qilib yozasiz
   yoki ularning rasmini (kitob sahifasi, qo'lyozma, doska) yuklaysiz.
3. **AI kartochka yasaydi** — Gemini har bir so'z uchun tarjima, talaffuz
   va testda ishlatiladigan 2 ta noto'g'ri variantni tayyorlaydi
   (`responseSchema` bilan qat'iy JSON ko'rinishida).
4. **Yodlash** — kartochkalar bittama-bitta ko'rsatiladi: old tomonida
   so'z (va 🔊 talaffuz tugmasi — brauzerning `speechSynthesis` orqali),
   bosilganda orqa tomonida talaffuz va tarjima ochiladi. "Yana ko'raman"
   yoki "Yodladim" tugmasi bilan navbatdagi so'zga o'tiladi.
5. **Test** — barcha so'zlar ko'rib chiqilgach, uchta javobli test
   boshlanadi. To'g'ri javob — so'z "yodlandi" deb belgilanadi. Noto'g'ri
   javob — so'z qaytadan kartochka bosqichiga tushadi.
6. Har bir to'plamning progressi (nechta so'z yodlandi) bosh sahifada
   saqlanadi va qurilmani yopib qaytganda ham davom etadi.

## API kalit

Dastur Gemini'ning **bepul** darajasidagi `gemini-2.5-flash` modelidan
foydalanadi. Kalit https://aistudio.google.com/apikey sahifasidan bepul
olinadi va faqat shu qurilmaning `localStorage`'ida saqlanadi — hech qayerga,
hech qanday serverga yuborilmaydi, faqat to'g'ridan-to'g'ri Google'ga.

## Fayllar

```
docs/kartochka/
├── index.html            # butun dastur (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg, icon-maskable.svg
└── README.md
```

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/kartochka/
```

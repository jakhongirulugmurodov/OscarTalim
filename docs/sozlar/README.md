# So'zdon — ingliz tili so'z o'yini

Ingliz tilida so'z yodlash o'yini. Bitta fayl (`index.html` — HTML + CSS + JS),
backend yo'q, natija brauzerda (`localStorage`) saqlanadi. PWA sifatida
telefonga o'rnatiladi.

## Qanday o'ynaladi

1. **Daraja** (Boshlang'ich / O'rta / Yuqori) va **mavzu** (Aralash, Kundalik
   hayot, Ovqat, Sayohat, IT, Ish va o'qish) tanlanadi.
2. **Yangi raund** — 5 ta yangi so'z: inglizcha so'z, o'qilishi, tarjimasi,
   misol gap va 🔊 talaffuz (brauzer ovozi bilan).
3. **Test** — savollar bittadan, turlari aralash:
   - 🇺🇿 → 🇬🇧 tarjima (yozib javob beriladi)
   - 🇬🇧 → 🇺🇿 tarjima (4 variant)
   - 🔤 aralash harflardan so'z terish
   - ✏️ bo'sh joyni to'ldirish
   - 🔘 4 variantli savol
   - 🔊 tinglab ma'nosini tanlash
4. Raund oxirida natija va takrorlash kerak bo'lgan so'zlar ro'yxati.

## Ochko va darajalar

| Holat | Ochko |
|---|---|
| Birinchi urinishda to'g'ri | +10 |
| Ikkinchi urinishda (ishoradan keyin) to'g'ri | +5 |
| Ketma-ket 3 ta to'g'ri | +15 bonus 🔥 |

Xato qilinsa, avval **ishora** beriladi (birinchi harf yoki 50/50). Ikkinchi
marta ham xato bo'lsa, to'g'ri javob misol bilan ko'rsatiladi.

Darajalar: 0–99 🥉 Boshlovchi, 100–249 🥈 Bilimdon, 250+ 🥇 So'z ustasi.

## Takrorlash tizimi

Xato qilingan (yoki ikkinchi urinishda topilgan) so'zlar eslab qolinadi va
keyingi raundlarga 2 tadan qo'shiladi. **Takrorlash** tugmasi faqat shu
so'zlar bo'yicha test o'tkazadi. So'z birinchi urinishda to'g'ri topilsa,
ro'yxatdan chiqadi.

## So'z qo'shish

`index.html` ichidagi `RAW` massiviga qator qo'shiladi:

```js
["ticket","tikit","chipta","I bought a ticket to Tashkent.","Men Toshkentga chipta sotib oldim.",1,"sayohat"],
```

Tartib: inglizcha, o'qilishi, o'zbekcha, misol, misol tarjimasi, daraja (1–3),
mavzu (`kun`, `ovqat`, `sayohat`, `it`, `ish`), ixtiyoriy boshqa yozilishlar
(masalan `["neighbor"]`). Misol gapda so'z aynan shu shaklda bo'lishi kerak —
«bo'sh joyni to'ldirish» savoli shunga tayanadi.

# Funksiyalar holati

Oxirgi yangilanish: 2026-08-14 · panel build `14-Avg 22:30`

Bu fayl — haqiqiy montajda nima sinalgan-u nima sinalmaganining ro'yxati.
«Kodda ishlaydi» bilan «Premiere'da ishlaydi» boshqa-boshqa narsa ekanini
bir necha marta ko'rdik, shuning uchun holat faqat REAL testdan keyin
«faol» deb belgilanadi.

## ✅ Faol — real ishda tasdiqlangan

| Funksiya | Izoh |
|---|---|
| **Cut → Yangi sequence** | Asosiy ish rejimi. Qator joylashuvi (V1/V3, ovozlar) saqlanadi, burilgan kadr tuzatilgan, import «Podcast Suite» biniga tushadi |

## 🧪 Hali real test qilinmagan

| Funksiya | Sinashda nimaga qarash kerak |
|---|---|
| **Intro** | Gemini transkript importidan keyin nomzodlar chiqishi; tanlanganlardan yig'ilgan XML to'g'ri ochilishi |
| **Captions** | Gemini SRT/JSON import → «Subtitr yasash»; montaj ochiq bo'lsa vaqtlar montajga ko'chishi |
| **FX (fade-up)** | Matn/grafika klipida Position pastdan suzib chiqishi, fade harakatdan OLDIN tugashi. Yiqilsa log klip komponentlari inventarini yozadi — o'shani yuborish kerak |

## 🔁 Qisman sinalgan — yana test kerak

| Funksiya | Holat |
|---|---|
| **Sync** | Ilgari ishlagan, oxirgi o'zgarishlardan keyin qayta tekshirilmagan |
| **Switch** | Ilgari ishlagan; yaqinda server xatosi (TypeError) tuzatildi — qayta sinash kerak |
| **Tozalash** | Yangi qo'shilgan, oddiy amal, lekin real bosib ko'rilmagan |
| **Cut → Shu montajda** | Sinovda. To'rt marta yiqilib, har safar aniq sabab topildi (nusxa eskirishi, ovoz juftligi, setStart cho'zishi, jim rad). Oxirgi varianti (createMoveAction, har bo'lak tekshiruvi) real montajda hali tasdiqlanmagan. FAQAT qisqa montajda sinash; ish oldidan loyiha o'zi saqlanadi, xato chiqsa File > Revert |

## ❌ Voz kechilgan

| Funksiya | Sabab |
|---|---|
| **Harakat (zoom)** | «O'xshamadi bu uslubdan men voz kechaman» — yorliq olib tashlangan. Ehtimoliy ildiz sababi keyin topildi: keyframe API noto'g'ri ishlatilgan (FX shu saboq bilan to'g'ri yozildi) |
| **Matn / Shorts** | «Umuman ishlamadi» — yorliqlar olib tashlangan |

## Zaxira

**Stagger Text (CEP)** — `com.jahongir.staggertext/`. FX bilan bir xil ish,
alohida panel. O'rnatilmagan; kerak bo'lsa `ORNATISH.command`.

## Sinov tartibi (har yangi build'da)

1. `node suite/panel/sinov.js` — 15/15 o'tishi shart (avtomatik)
2. Real Premiere'da: avval qisqa sinov-montajda, keyin ish montajida
3. Yiqilsa: «Log'ni nusxalash» → log'ni yuborish — taxminsiz tuzatiladi

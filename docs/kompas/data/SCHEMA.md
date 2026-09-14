# Kompas ma'lumot fayllari — sxema (agentlar uchun qat'iy qoida)

Barcha fayllar oddiy JS: `window.KOMPAS_*` ga yozadi, build yo'q, `file://` da ham ishlaydi.
Til: o'zbek lotin, apostrof sifatida faqat `'` (U+0027) ishlatiladi (o'zbek, g'oya). Kirill harflari taqiqlanadi.
Har faylning boshida 2–3 satrlik izoh: nima, ishonch darajasi, sana.

Tekshiruv: `node docs/kompas/scripts/validate.js` — 0 xato bilan yakunlanishi shart.

## 1. `data/fanlar.js` (tayyor, o'zgartirilmaydi)

`window.KOMPAS_FANLAR` — fan idlari:
`ona_tili`, `matematika`, `tarix` (majburiy); `matematika`, `fizika`, `kimyo`, `biologiya`, `tarix_ix`,
`geografiya`, `ingliz_tili`, `ona_tili_adabiyot`, `huquq`, `rus_tili`, `ijodiy` (ixtisoslik).

## 2. `data/otmlar.js` (tayyor, o'zgartirilmaydi)

`window.KOMPAS_OTMLAR` — `id` lari yo'nalishlarda ishlatiladi. `window.KOMPAS_HUDUDLAR` — 14 ta hudud nomi.

## 3. `data/yonalishlar/<soha>.js` — ta'lim yo'nalishlari

```js
/* Yo'nalishlar: <soha>. ishonch: taxminiy. 2026-09-14 */
window.KOMPAS_YONALISHLAR = window.KOMPAS_YONALISHLAR || [];
window.KOMPAS_YONALISHLAR.push(
  {
    id: "dasturiy_injiniring",          // lotin slug, butun tizimda unikal
    kod: "60610200",                    // klassifikator kodi (8 raqam) yoki null — ishonchsiz bo'lsa null
    nom: "Dasturiy injiniring",
    soha: "Axborot texnologiyalari",    // 20 dan kam so'z, bir xil soha nomi bir xil yozilsin
    fan1: "matematika",                 // KOMPAS_FANLAR id — koeffitsient 3,1
    fan2: "fizika",                     // KOMPAS_FANLAR id — koeffitsient 2,1
    ijodiy: false,                      // fan2 === "ijodiy" bo'lsa true
    sertifikat: false,                  // fan1 === "ingliz_tili" bo'lsa true (sertifikat asosida qabul)
    riasec: { R: 0.45, I: 0.85, A: 0.30, S: 0.15, E: 0.30, C: 0.55 },   // har biri 0..1, 6 ta kalit shart
    kasblar: ["dasturchi", "tizim arxitektori", "ma'lumotlar muhandisi"],  // 3–5 ta, kichik harf
    tavsif: "Bir gap: kim uchun, nima o'rganiladi.",                       // 90–160 belgi
    istiqbol: "yuqori",                 // mehnat bozori: yuqori | orta | past
    raqobat: "yuqori",                  // kirish raqobati: yuqori | orta | past
    otish_taxmin: { grant: [150, 178], kontrakt: [118, 150] },  // TAXMINIY oraliq, 189 shkalada; nodavlat bo'lmasa grant shart
    otmlar: ["tatu", "ozmu", "tdtu"],   // KOMPAS_OTMLAR id lari, 1–8 ta, eng ma'lumlari
    hududlar: ["Toshkent shahri", "Samarqand", "Farg'ona"],  // KOMPAS_HUDUDLAR dan yoki ["*"] (hamma joyda)
    ishonch: "taxminiy",                // taxminiy | tekshirilsin
    izoh: ""                            // shubha bo'lsa — nima aniq emasligi
  }
);
```

Qoidalar:
- `fan1`/`fan2` — fanlar majmuasidagi haqiqiy juftlikka mos bo'lishi kerak (masalan: tibbiyot → biologiya+kimyo;
  IT/muhandislik → matematika+fizika; iqtisodiyot → matematika+ingliz_tili yoki matematika+geografiya;
  huquqshunoslik → huquq+ingliz_tili; filologiya (o'zbek) → ona_tili_adabiyot+tarix_ix; tarix → tarix_ix+geografiya yoki
  tarix_ix+ona_tili_adabiyot; chet tili yo'nalishlari → fan1 ingliz_tili (sertifikat); arxitektura → matematika+ijodiy;
  pedagogika (boshlang'ich) → ona_tili_adabiyot+matematika; psixologiya → biologiya+ona_tili_adabiyot; kimyo → kimyo+matematika;
  biologiya → biologiya+kimyo; geografiya → geografiya+matematika). Ishonchsiz juftlik → `ishonch: "tekshirilsin"` + `izoh`.
- `otish_taxmin` — 2024–2026 yillardagi umumiy manzaraga asoslangan **oraliq**, aniq raqam emas.
  Kontrakt oralig'i grantdan past. Minimal chegara: tibbiyot/yuridik/biznes ≥ 94.5, boshqalar ≥ 75.6.
  Har oraliq kengligi ≥ 15 ball. Bilmasangiz keng oraliq bering va `ishonch: "tekshirilsin"`.
- `riasec` — Holland modeli: R amaliy/texnik, I tadqiqot/tahlil, A ijod, S odamlar bilan ishlash/o'qitish,
  E boshqaruv/tadbirkorlik, C tartib/aniqlik. Eng katta 1–2 qiymat 0.7–0.95, eng kichiklari 0.1–0.3 bo'lsin.
- Yo'nalishlar takrorlanmasin; bir sohada 25–40 ta yo'nalish.

## 4. `data/mavzular/<fan>.js` — fan bo'yicha mavzu daraxti

```js
/* Mavzular: biologiya. ulush — imtihondagi savollar ulushi (Σ = 1.000). bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat. ishonch: ekspert_bahosi. 2026-09-14 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.biologiya = {
  fan: "biologiya",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "bio_01", bolim: "Sitologiya", nom: "Hujayra tuzilishi va organoidlar", ulush: 0.05, bazaviy_soat: 7, qiyinlik: 0.5 },
    // ...
  ]
};
```

Qoidalar:
- 25–40 ta mavzu; `bolim` — 5–9 ta bo'lim, ketma-ket tartibda (maktab dasturi bo'yicha).
- `id` = fan prefiksi + tartib raqami (`bio_01` … `bio_34`), unikal.
- `ulush` — 3 xonagacha, Σ aynan 1.000 (±0.002). Ko'p savol tushadigan mavzularga ko'proq.
- `bazaviy_soat` — 2..14 oralig'ida; fan bo'yicha Σ: ixtisoslik fanlari 140–220 soat, majburiy (ona_tili, tarix) 90–140 soat.
- `qiyinlik` — 0.2..0.9.
- Fanlar: matematika, fizika, kimyo, biologiya, tarix (O'zbekiston tarixi, majburiy), tarix_ix (Tarix: O'zbekiston + jahon),
  ona_tili (majburiy: grammatika, imlo, nutq), ona_tili_adabiyot (til + adabiyot), ingliz_tili, geografiya, huquq, rus_tili.

## 5. `data/riasec_savollar.js` — qiziqish testi

```js
/* RIASEC qiziqish testi, 60 savol (O*NET Interest Profiler qisqa shakli asosida o'zbek tiliga moslashtirilgan; public domain). 2026-09-14 */
window.KOMPAS_RIASEC = [
  { id: "q01", shkala: "R", matn: "Avtomobil dvigatelini ta'mirlash" },
  // ...
];
```

Qoidalar:
- Aynan 60 ta: har shkala (R, I, A, S, E, C) uchun 10 ta; ketma-ketlik aralash (R,I,A,S,E,C,R,I,...).
- Har savol — **faoliyat** (ish-harakat), 3–9 so'z, «-ish/-moq» shaklida, kasb nomi emas.
- O'zbekiston sharoitiga mos misollar (paxta, bozor, mahalla, maktab, IT-park, tibbiyot, qurilish...).
- 14–18 yoshli o'quvchi tushunadigan til; bir shkala savollari bir xil faoliyat turini takrorlamasin.
- Javob shkalasi UI da: 1 «umuman yoqmaydi» … 5 «juda yoqadi».

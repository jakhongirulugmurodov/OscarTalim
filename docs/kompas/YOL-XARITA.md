# Yo'l xaritasi — ishlar ketma-ketligi

Versiya: 1.0 · Boshlanish: 2026-09-11 · Maqsad sikl: **2027-yil qabuli**

---

## Nega aynan hozir boshlash to'g'ri

2026-yil qabuli avgustda yakunlandi. Ya'ni **hozir**:

- 2026-yilning fanlar majmuasi, kvota va **o'tish ballari** yangi e'lon qilingan —
  ma'lumot poydevorini to'ldirish uchun eng yaxshi payt;
- 2027-yil iyul imtihonigacha **≈10 oy** bor — hozirgi 10–11-sinf o'quvchisi uchun
  tayyorgarlik rejasi hali to'liq ish beradi (4–6 oylik reja + zaxira);
- milliy sertifikat imtihonlari yil davomida o'tkaziladi — mahsulot **birinchi kunidanoq**
  amaliy foyda bera oladi (sertifikat = maksimal ball olishning eng arzon yo'li).

Agar aprelda boshlansa, o'quvchiga "sizga 5 oy kerak, lekin 3 oy qoldi" deyishdan boshqa
aytadigan gap qolmaydi.

---

## Fazalar

### Faza 0 — Ma'lumot poydevori · 3 hafta (sentabr 2026)

> Bu fazasiz qolgan hammasi ishlamaydi. Eng zerikarli, eng muhim qism.

| # | Vazifa | Natija |
|---|---|---|
| 0.1 | `uzbmb.uz` dan 2026/2027 fanlar majmuasi PDF ini olish va parser yozish | `fanlar_majmuasi_2026_2027.json` (~227 yo'nalish) |
| 0.2 | Yo'nalishlar klassifikatorini kiritish (`lex.uz`) | `yonalish.json` |
| 0.3 | OTM ro'yxati (davlat/nodavlat/xorijiy + filiallar) | `otm.json` |
| 0.4 | Kvota va kontrakt narxlari (2026/2027) | `taklif_2026_2027.json` |
| 0.5 | **O'tish ballari: 2024, 2025, 2026** — 3 yil | `otish_balli.json` |
| 0.6 | `config/qabul-2027.json` — koeffitsientlar, minimal ballar, kalendar | konfiguratsiya |
| 0.7 | `scripts/validate.py` + CI tekshiruvi | yashil CI |

**Chiqish mezoni:** validatsiya 100% o'tadi; kamida 3 yillik o'tish balli mavjud
yo'nalishlar ulushi ≥ 60%.

### Faza 1 — MVP: qiziqish → yo'nalish → fanlar · 4 hafta (oktabr 2026)

Statik veb-ilova (`docs/` ichida, GitHub Pages) — backend hali kerak emas,
barcha ma'lumot JSON sifatida yuklanadi, hisob-kitob brauzerda ketadi.

| # | Vazifa |
|---|---|
| 1.1 | RIASEC 60 savollik testni o'zbek/rus tillariga moslashtirish (O\*NET public domain) |
| 1.2 | Test UI + ballash + Holland kodi |
| 1.3 | Moslik dvigateli (kosinus + qattiq filtrlar + vaznlar) |
| 1.4 | Natija sahifasi: 5 ta variant, savatlar (orzu/maqsad/ishonchli) |
| 1.5 | Fan-yechuvchi: yo'nalish → 1-fan/2-fan + majburiylar + ijodiy/sertifikat bayrog'i |
| 1.6 | Blok taqqoslash jadvali (nechta yo'nalish ochiladi) |
| 1.7 | Oddiy muddat kalkulyatori (o'z-o'zini baholash asosida, diagnostikasiz) |
| 1.8 | Har bir raqam yonida manba va sana ko'rsatish |

**Chiqish mezoni:** 30 ta real o'quvchi testdan o'tadi, 5 ta tavsiya oladi;
"tavsiya mantiqli" degan baho ≥ 70%.

### Faza 2 — Diagnostika va savollar banki · 6 hafta (noyabr–dekabr 2026)

| # | Vazifa |
|---|---|
| 2.1 | Mavzu daraxti: 5 fan × ~40 mavzu, `bazaviy_soat` va `kutilgan_savol` bilan |
| 2.2 | Savollar banki v1: **fan boshiga ≥ 240 savol** (jami ≈1200), mavzuga teglangan |
| 2.3 | Adaptiv diagnostika (MVP: mavzu bo'yicha sobit 25 savol; keyin IRT) |
| 2.4 | Xom natijadan ballga o'tkazish (taxmin tuzatishi bilan) |
| 2.5 | Mavzu bo'yicha ball/soat samaradorligini hisoblash va saralash |
| 2.6 | Haftalik reja generatori + intervalli takrorlash jadvali |
| 2.7 | Backend kerak bo'ladi: foydalanuvchi hisobi, progress saqlash |

**Chiqish mezoni:** diagnostika bali va to'liq sinov imtihoni bali orasidagi
MAE < 12 ball (50 ta o'quvchida tekshiriladi).

### Faza 3 — Pilot va shaxsiylashtirish · 8 hafta (yanvar–fevral 2027)

| # | Vazifa |
|---|---|
| 3.1 | Oscar Ta'lim o'quvchilari orasida pilot: 100–300 kishi |
| 3.2 | Haftalik nazorat testi → `r_u` (o'rganish tezligi) yangilanishi |
| 3.3 | Trayektoriya grafigi va ogohlantirishlar |
| 3.4 | O'qituvchi/ota-ona paneli |
| 3.5 | Telegram bot (O'zbekistonda eng yuqori qamrovli kanal): kunlik eslatma, haftalik hisobot |

**Chiqish mezoni:** pilot ishtirokchilarining ≥ 60% rejadagi soatning yarmidan ko'pini
bajaradi; 4 haftadan keyingi ball o'sishi prognoz oralig'iga tushishi ≥ 70%.

### Faza 4 — Ehtimollik moduli · 6 hafta (mart–aprel 2027)

| # | Vazifa |
|---|---|
| 4.1 | O'tish balli prognozi (`Ĉ`, `σ_c`) |
| 4.2 | `P(kirish)` — grant va kontrakt uchun alohida |
| 4.3 | Monte-Carlo: 5 ta tanlov bo'yicha umumiy ehtimollik |
| 4.4 | Tanlov tartibini optimallashtirish (120 ta o'rin almashtirish) |
| 4.5 | Kalibrovka paneli (ichki): Brier score, kalibrovka egri chizig'i |

### Faza 5 — Blok maslahatchisi (kampaniya) · may–iyun 2027

Yilning eng muhim marketing oynasi: **5–25 iyun** — ro'yxatdan o'tish va blok tanlash.

| # | Vazifa |
|---|---|
| 5.1 | "Qaysi blokdan topshiray?" — 3 daqiqalik alohida vorontka |
| 5.2 | Blok qarorining oqibatini ko'rsatish: "bu blok 61, anavisi 34 yo'nalish ochadi" |
| 5.3 | Milliy sertifikat maslahatchisi: qaysi fandan sertifikat olish eng foydali |
| 5.4 | Maktablar/o'quv markazlari uchun ommaviy rejim |

### Faza 6 — Tanlov optimizatori · iyul–avgust 2027

**Yilning eng qimmatli 2 haftasi** (≈25 iyul – 8 avgust): abituriyent ballini biladi,
5 ta tanlovni tartiblashi kerak.

| # | Vazifa |
|---|---|
| 6.1 | "Ballimni kiritaman → 5 ta tanlovimni tartibla" rejimi |
| 6.2 | Har variant uchun ehtimollik + tushuntirish |
| 6.3 | "Agar 3-tanlovni 1-o'ringa qo'ysangiz, grant ehtimoli 12% ga oshadi" kabi maslahat |

### Faza 7 — Kalibrovka va yopilish · sentabr 2027

| # | Vazifa |
|---|---|
| 7.1 | Mandat natijalarini yig'ish (foydalanuvchilardan + rasmiy manbadan) |
| 7.2 | Barcha prognozlarni haqiqat bilan solishtirish: MAE, Brier |
| 7.3 | Modelni qayta sozlash, `bazaviy_soat` qiymatlarini real ma'lumotga moslash |
| 7.4 | 2028 sikli uchun ma'lumot poydevorini yangilash |

---

## Texnik stek (taklif)

| Qatlam | Tanlov | Sabab |
|---|---|---|
| Frontend | Statik HTML/JS (Faza 1) → keyin SPA | Repozitoriyda allaqachon shu uslub bor; GitHub Pages bepul, tez |
| Ma'lumot | JSON fayllar (Faza 1) → PostgreSQL (Faza 2) | Erta bosqichda baza ortiqcha murakkablik |
| Backend | Python (FastAPI) | Parserlar, IRT, Monte-Carlo — hammasi Python ekotizimida |
| Hisob-kitob | NumPy/SciPy | `Φ`, Monte-Carlo, IRT |
| Bot | Telegram (aiogram) | O'zbekistonda eng katta qamrov |
| Analitika | O'z hodisalar jurnali | Kalibrovka uchun xom ma'lumot kerak |

Faza 1 ni brauzerda ishlaydigan qilib qurish ataylab: server, hisob va shaxsiy ma'lumot
muammosisiz tezda bozorga chiqib, tavsiya sifatini tekshirib olamiz.

---

## Mehnat hajmi (taxminiy)

| Faza | Odam-hafta | Kim kerak |
|---|---:|---|
| 0 | 4 | 1 dasturchi + 1 ma'lumot kirituvchi |
| 1 | 6 | 1 frontend + 1 metodist |
| 2 | 14 | 1 backend + 3 fan o'qituvchisi (savollar) |
| 3 | 8 | 1 dasturchi + 1 metodist + pilot koordinatori |
| 4 | 5 | 1 ma'lumot tahlilchisi |
| 5–6 | 6 | 1 dasturchi + marketing |
| 7 | 2 | tahlilchi |

Eng katta xarajat — **savollar banki** (1200 savol × ≈20 daqiqa yozish va tekshirish
≈ 400 soat). Buni oldindan rejalashtirish kerak; eng katta kechikish xavfi ham shu yerda.

---

## Muvaffaqiyat metrikalari

| Faza | Asosiy metrika | Maqsad |
|---|---|---|
| 1 | Testni yakunlash ulushi | > 70% |
| 1 | "Tavsiya mantiqli" bahosi | > 70% |
| 2 | Diagnostika vs sinov imtihoni MAE | < 12 ball |
| 3 | Reja bajarilishi (4 hafta) | > 60% |
| 3 | Ball o'sishi prognoz oralig'ida | > 70% |
| 4 | Brier score | < 0,15 |
| 6 | Tanlov optimizatoridan foydalanuvchilar | ≥ 5 000 |
| 7 | Tavsiya qilingan variantga kirganlar ulushi | kuzatiladi, e'lon qilinadi |

---

## Monetizatsiya (qisqacha)

1. **Bepul:** qiziqish testi + yo'nalish tavsiyasi + fanlar majmuasi. Bu — vorontkaning
   kirishi va eng katta ijtimoiy foyda.
2. **Pullik (obuna):** diagnostika + shaxsiy reja + haftalik kuzatuv.
3. **B2B:** o'quv markazlari va maktablar uchun panel (guruh bo'yicha progress).
4. **Mavsumiy:** iyul–avgustdagi tanlov optimizatori — bir martalik to'lov.

Oscar Ta'lim uchun bu, birinchi navbatda, **o'z o'quvchilarini saqlab qolish va natijasini
o'lchash** vositasi; tashqi mahsulot — ikkinchi bosqich.

---

## Birinchi sprint (keyingi 2 hafta) — aniq vazifalar

1. `data/raw/` ga 2026/2027 fanlar majmuasi PDF ini joylash (tarmoq cheklovi sababli qo'lda).
2. `scripts/parse_fanlar_majmuasi.py` — PDF dan jadvalni JSON ga chiqarish.
3. `config/qabul-2027.json` — ball koeffitsientlari va kalendar (ma'lum qismi tayyor).
4. 2024–2026 o'tish ballari uchun manbalarni aniqlash va kamida 1 yilni to'liq kiritish.
5. [ALGORITM.md § 8](ALGORITM.md#8-ochiq-savollar-kod-yozishdan-oldin-tekshirilsin) dagi
   8 ta ochiq savolga rasmiy manbadan javob topish.
6. `scripts/validate.py` + GitHub Actions.

Shu 6 ta ish bajarilsa, Faza 1 ni 4 haftada yopish real.

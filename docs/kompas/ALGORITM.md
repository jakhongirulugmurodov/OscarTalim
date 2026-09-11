# Kompas — algoritm va ishlar ketma-ketligi

Versiya: 1.0 · Sana: 2026-09-11 · Holat: spetsifikatsiya (kod yozilmagan)

---

## 0. Qamrov

**Kirish (input):** o'quvchining qiziqishlari, sharoiti va joriy bilim darajasi.
**Chiqish (output):**

1. Unga mos **5 ta (OTM + ta'lim yo'nalishi)** varianti — ustuvorlik tartibida, har biri
   uchun kirish ehtimoli bilan;
2. Shu yo'nalishlar uchun **qaysi fanlardan imtihon** topshirilishi (fanlar majmuasi) va
   qaysi **blok** eng foydali ekani;
3. Har bir fandan **joriy darajasi** va **kerakli ball** orasidagi farq;
4. Shu farqni yopish uchun **necha soat / necha hafta / necha oy** kerakligi va
   **haftalik reja**.

Qamrovdan tashqarida (1-versiyada): magistratura, kasbiy (professional) ta'lim,
xorijiy universitetlar, ijodiy imtihonlarni baholash.

---

## 1. Tasdiqlangan faktlar (algoritm shularga tayanadi)

> Har bir raqamning manbai va tekshirish holati [MANBALAR.md](MANBALAR.md) da.
> Raqamlar har yili o'zgaradi — kodda ular **konfiguratsiya fayli** sifatida saqlanadi,
> hech qachon "hardcode" qilinmaydi.

### 1.1. Ball tizimi (maksimal 189,0 ball)

| Fan | Savollar | Har savol | Jami |
|---|---:|---:|---:|
| 1-ixtisoslik fani | 30 | 3,1 | **93,0** |
| 2-ixtisoslik fani | 30 | 2,1 | **63,0** |
| Ona tili (o'zbek/rus/qoraqalpoq) | 10 | 1,1 | 11,0 |
| Matematika | 10 | 1,1 | 11,0 |
| O'zbekiston tarixi | 10 | 1,1 | 11,0 |
| **Jami** | **90** | | **189,0** |

Muhim xulosa: **1-fandan olingan 1 ta savol = majburiy fandan olingan 2,8 ta savolga teng.**
Tayyorgarlik rejasi shu nomutanosiblik ustiga quriladi.

### 1.2. Yillik qabul kalendari (2026 siklidan olingan; 2027 uchun taxminiy)

| Sana | Bosqich | Mahsulot uchun ma'nosi |
|---|---|---|
| 5–25 iyun | `my.uzbmb.uz` da ro'yxatga olish: **fanlar bloki**, ta'lim tili, hudud tanlanadi | Blok maslahatchisi eng ko'p ishlatiladigan payt |
| 14–28 iyul | Test sinovlari, kuniga 2 smena (08:00–11:00, 15:00–18:00) | Tayyorgarlik deadline'i |
| Test ertasi kuni | Natijalar e'lon qilinadi | Ball kiritish → tanlov rejimiga o'tish |
| ~25 iyul – 8 avgust | **5 tagacha (OTM + yo'nalish)** ustuvorlik bilan tanlanadi | Tanlov optimizatori — mahsulotning eng qimmatli 2 haftasi |
| ~15–17 avgust | Mandat: ballar yagona reytingda qayta hisoblanib, grant va kontrakt o'rinlari taqsimlanadi | Natijalarni yig'ib, modelni kalibrlash |

### 1.3. Boshqa qoidalar

- **Minimal ball** (tanlovda qatnashish uchun quyi chegara) — yo'nalishlar guruhiga qarab
  farq qiladi (sog'liqni saqlash / yuridik / biznes va boshqaruv uchun yuqoriroq).
  Aniq raqam har yili Davlat qabul komissiyasi qarori bilan belgilanadi → **konfiguratsiyada**.
- **Milliy sertifikat:** fan bo'yicha sertifikat bo'lsa, o'sha fandan test topshirilmaydi,
  ball darajaga qarab avtomatik beriladi (A+/A → maksimal ball; B+/B/C+/C → proporsional).
  Amal muddati — 3 yil. Bu **ball olishning eng arzon yo'li** va algoritmda alohida
  «yorliq» (shortcut) sifatida hisobga olinadi.
- **Chet tili 1-fan bo'lgan yo'nalishlar** uchun qabul milliy yoki xalqaro sertifikat
  asosida amalga oshiriladi — bunday yo'nalishlar uchun tayyorgarlik rejasi butunlay
  boshqacha (sertifikat imtihoni sanalariga bog'lanadi).
- Ayrim yo'nalishlarda 2-fan o'rniga **kasbiy (ijodiy) imtihon** topshiriladi (masalan
  arxitektura) — bunday yo'nalishlar alohida bayroq bilan belgilanadi.

---

## 2. Tizim modullari

| Modul | Nomi | Vazifasi |
|---|---|---|
| **M0** | Ma'lumot poydevori | OTM, yo'nalish, fanlar majmuasi, kvota, o'tish ballari — versiyalangan datasetlar |
| **M1** | Profil yig'ish | Qiziqish testi (RIASEC) + sharoit + cheklovlar |
| **M2** | Moslik dvigateli | Yo'nalishlarni reytinglash va 5 talik "savat" yasash |
| **M3** | Fan-yechuvchi | Yo'nalish → imtihon fanlari; optimal blokni tanlash |
| **M4** | Diagnostika | Adaptiv test → har mavzu bo'yicha o'zlashtirish darajasi |
| **M5** | Ehtimollik moduli | O'tish balli prognozi + kirish ehtimoli |
| **M6** | Muddat kalkulyatori | Ball farqi → soat → hafta → oy |
| **M7** | Reja va kuzatuv | Haftalik reja, nazorat testlari, qayta hisob |
| **M8** | Tushuntirish | Har bir tavsiyaning sababi, manbai, ishonch darajasi |

---

## 3. Algoritm: qadamma-qadam

### QADAM 1 — Profil yig'ish (M1)

**Kirish:** anketa (≈3 daqiqa).

```
profil = {
  sinf: 9|10|11|bitirgan,
  maqsad_yili: 2027,
  hudud: "Namangan",
  koch_ish_imkoni: true|false,          // Toshkentga ko'chib o'qiy oladimi
  moliya: "faqat_grant"|"kontrakt_mumkin", kontrakt_shift: 20_000_000,
  talim_tili: "uz"|"ru"|"qq",
  talim_shakli: ["kunduzgi"],
  haftalik_soat: 12,                     // tayyorgarlikka ajrata oladigan soat
  mavjud_sertifikat: [{fan:"ingliz_tili", daraja:"B+", sana:"2026-05-01"}],
  imtiyoz: null                          // olimpiada, ijtimoiy himoya va h.k.
}
```

Bu maydonlar keyinchalik **qattiq filtr** (hard filter) sifatida ishlatiladi: mos kelmagan
variant reytingga umuman kirmaydi (masalan, "faqat grant" tanlagan o'quvchiga faqat
kontrakt o'rni bor yo'nalish ko'rsatilmaydi).

### QADAM 2 — Qiziqishni o'lchash (M1)

**Usul:** RIASEC (Holland) modeli — kasb qiziqishlarini o'lchashning eng ko'p tekshirilgan,
ochiq (public domain) metodikasi. Asos: **O\*NET Interest Profiler Short Form** (60 ta
ish-faoliyati bayoni, 1–5 shkala), o'zbek/rus/qoraqalpoq tillariga moslashtirilgan.

**Chiqish:** 6 o'lchovli vektor
`R` (amaliy), `I` (tadqiqotchi), `A` (ijodiy), `S` (ijtimoiy), `E` (tadbirkor), `C` (tartibli).

```
1. Har savol javobi 1..5 → tegishli shkalaga qo'shiladi (har shkalada 10 savol → 10..50)
2. Xom ball → foiz: x_k = (ball_k - 10) / 40
3. Normalizatsiya (ipsativ): v_k = x_k / sqrt(Σ x_j²)     // vektor uzunligi = 1
4. Holland kodi = eng yuqori 3 shkala harfi, masalan "SIR"
```

Nega normalizatsiya kerak: ba'zi o'quvchi hamma savolga "5" qo'yadi, ba'zisi hammasiga "3".
Vektorni birlik uzunlikka keltirish bu farqni yo'qotadi va **profil shakli** qoladi.

> **Muhim:** 14–17 yoshda qiziqish hali barqaror emas. Shuning uchun natija «sizning
> kasbingiz — shifokor» ko'rinishida emas, «sizning profilingiz S-I-R, bunga mos 18 ta
> yo'nalish bor» ko'rinishida beriladi, va 6 oydan keyin qayta topshirish taklif qilinadi.

### QADAM 3 — Yo'nalishlarga moslik (M2)

Har bir ta'lim yo'nalishi uchun ham RIASEC profili bo'ladi (`u_yonalish`, 6 o'lchovli,
normalizatsiyalangan). Ularni qanday olamiz — [MAALUMOT-MODELI.md](MAALUMOT-MODELI.md) § 4.

**Qiziqish mosligi** — kosinus o'xshashlik:

```
I(o) = Σ_k ( v_k · u_k )            // ikkala vektor ham birlik uzunlikda
I(o) ∈ [0, 1],  1 = mukammal moslik
```

Tushuntirish uchun qo'shimcha **C-indeks** (Brown & Gore) ham hisoblanadi — u 3 harfli
kodlar mosligini 0..18 oralig'ida beradi va foydalanuvchiga "SIR ↔ SIC: 15/18" kabi
sodda ko'rinishda ko'rsatiladi.

**Yakuniy reyting** (qattiq filtrlardan o'tgan har bir `o = OTM × yo'nalish × shakl × til`
varianti uchun):

```
Score(o) = w₁·I(o) + w₂·A(o) + w₃·P(o) + w₄·M(o) + w₅·V(o)

I(o) — qiziqish mosligi          [QADAM 2]
A(o) — akademik moslik: o'quvchi kuchli bo'lgan fanlar bu yo'nalish fanlari bilan mos keladimi
P(o) — kirish ehtimoli           [QADAM 6]
M(o) — mehnat bozori signali (ish bilan bandlik, maosh) — past vazn, "indikativ" deb belgilanadi
V(o) — foydalanuvchining shaxsiy ustuvorliklari (hudud, OTM obro'si, kontrakt narxi)
```

**Standart vaznlar** va 3 ta tayyor rejim:

| Rejim | w₁ qiziqish | w₂ akademik | w₃ ehtimol | w₄ bozor | w₅ shaxsiy |
|---|---:|---:|---:|---:|---:|
| Muvozanat (default) | 0,30 | 0,20 | 0,30 | 0,10 | 0,10 |
| "Qiziqishim muhim" | 0,50 | 0,15 | 0,15 | 0,10 | 0,10 |
| "Kirishim kafolatli bo'lsin" | 0,15 | 0,20 | 0,50 | 0,05 | 0,10 |

**Natijani 3 ta savatga ajratish** (5 ta tanlov strategiyasiga to'g'ridan-to'g'ri mos keladi):

```
Orzu       (P < 0,30)  → 1 ta
Maqsad     (0,30–0,70) → 2 ta
Ishonchli  (P > 0,70)  → 2 ta
```

Bu tasodifiy emas: tanlov tizimi ustuvorlik tartibida tekshirilgani uchun, faqat orzu
variantlarni qo'ygan abituriyent hech qayerga tushmay qolishi mumkin; faqat ishonchli
variantlarni qo'ygan abituriyent esa o'z ballidan past yo'nalishga tushadi.

### QADAM 4 — Imtihon fanlarini aniqlash va BLOKNI optimallashtirish (M3)

Bu — mahsulotning eng qimmatli qismi, chunki **blok qarori qaytarib bo'lmaydi**.

```
1. Tavsiya etilgan har bir yo'nalish uchun fanlar majmuasidan (1-fan, 2-fan) juftligini olamiz.
2. Juftliklarni guruhlaymiz → nomzod bloklar B = {b₁, b₂, ...}
3. Har bir blok b uchun:
     D(b)  = shu blok bilan ochiladigan barcha yo'nalishlar
     Top5(b) = D(b) ichidan Score bo'yicha eng yaxshi 5 ta (savat qoidasi bilan)
     Soat(b)  = shu blok fanlaridan imtihongacha kerak bo'ladigan tayyorgarlik soati [QADAM 7]
     Ball(b)  = imtihon sanasigacha real erishiladigan ball [QADAM 7]
     P(b)     = Ball(b) bilan Top5(b) dan kamida bittasiga kirish ehtimoli [QADAM 6]
     U(b)     = P(b) · mean(I(o) : o ∈ Top5(b))
4. b* = argmax U(b)
5. Foydalanuvchiga eng yaxshi 3 ta blok taqqoslama jadval bilan ko'rsatiladi:
   "Biologiya+Kimyo → 34 yo'nalish, kirish ehtimoli 71%, qiziqish mosligi 0,86"
   "Matematika+Fizika → 61 yo'nalish, kirish ehtimoli 58%, qiziqish mosligi 0,54"
```

Diqqat qilinadigan holatlar:

- Agar yo'nalishda **chet tili 1-fan** bo'lsa → test emas, **sertifikat** kerak → reja
  sertifikat imtihoni sanalariga qurilishi kerak, bayroq qo'yiladi.
- Agar 2-fan o'rnida **ijodiy imtihon** bo'lsa → ball modeli ishlamaydi, foydalanuvchi
  ogohlantiriladi va shu OTM ning ijodiy imtihon talablariga havola beriladi.
- Agar o'quvchida allaqachon **milliy sertifikat** bo'lsa → o'sha fan bo'yicha ball
  avtomatik maksimal/proporsional olinadi va tayyorgarlik soati **0** ga tushadi. Bu
  ko'pincha butun strategiyani o'zgartiradi.

### QADAM 5 — Diagnostika: joriy daraja (M4)

**Usul:** har fan uchun mavzularga teglangan, qiyinligi baholangan savollar bankidan
adaptiv qisqa test (fan boshiga 20–30 savol, ≈25 daqiqa).

```
Har bir mavzu t uchun o'zlashtirish darajasi:  m_t ∈ [0, 1]
Boshlang'ich baholash: 2PL IRT modeli (yoki MVP uchun — mavzu bo'yicha to'g'ri javob ulushi)
```

**Xom o'zlashtirishdan ballga o'tish** — taxmin qilishni (guessing) hisobga olish shart.
Test 4 variantli bo'lgani uchun bilmagan savolda ham 1/4 ehtimol bilan to'g'ri javob tushadi:

```
p_f = m_f + (1 − m_f) · g          // g = 0,25 (taxmin ehtimoli)
Ball_f = n_f · k_f · p_f           // n_f — savollar soni, k_f — koeffitsient (3,1 / 2,1 / 1,1)
Umumiy_ball = Σ_f Ball_f
```

Model to'g'riligining tekshiruvi: hech narsa bilmagan o'quvchi (m=0) ≈ `189 · 0,25 = 47,3`
ball oladi — bu minimal chegaradan past, ya'ni model haqiqatga mos.

`m_f` (fan darajasidagi o'zlashtirish) mavzular bo'yicha **savollar soniga vaznlangan
o'rtacha** sifatida hisoblanadi:

```
m_f = Σ_t ( q_t · m_t ) / Σ_t q_t       // q_t — shu mavzudan kutilayotgan savollar soni
```

### QADAM 6 — Kerakli ball va kirish ehtimoli (M5)

**6.1. O'tish balli prognozi.** Har bir variant uchun oxirgi 3 yil o'tish ballaridan:

```
Ĉ = 0,5·C_{y−1} + 0,3·C_{y−2} + 0,2·C_{y−3}
    + β₁·Δln(kvota) + β₂·Δln(arizalar_soni)      // ma'lumot yetarli bo'lganda

σ_c = max( std(C_{y−1..y−3}), 5,0 )               // noaniqlik, kamida 5 ball
```

MVP da `β₁ = β₂ = 0` (ya'ni faqat trend + noaniqlik). Kvota va ariza statistikasi
3 yil to'planganda regressiya bilan baholanadi.

**6.2. O'quvchi bali prognozi.**

```
S ~ Normal(μ̂, σ_s)
μ̂   — reja bo'yicha imtihon sanasiga erishiladigan ball [QADAM 7]
σ_s — prognoz xatosi: boshida 12 ball, har sinov imtihonidan keyin kamayadi
      (3+ sinovdan keyin ≈ 6–8 ball)
```

**6.3. Ehtimollik.**

```
P(kirish) = Φ( (μ̂ − Ĉ) / sqrt(σ_s² + σ_c²) )
```

Grant va kontrakt uchun alohida hisoblanadi (ikki xil `Ĉ`).

**6.4. 5 ta tanlov uchun umumiy ehtimollik va tartib.** Tanlov tizimi ustuvorlik
tartibida ishlagani uchun, Monte-Carlo simulyatsiya qilinadi:

```
N = 10 000 marta:
    S ← Normal(μ̂, σ_s) dan namuna
    har bir variant uchun C_j ← Normal(Ĉ_j, σ_c_j) dan namuna
    tanlovlarni ustuvorlik tartibida tekshir: birinchi S ≥ C_j bo'lgan variant = natija
natija statistikasi → P(kamida bittasiga kirish), har variant bo'yicha P(aynan shunga tushish)
```

Tartibni optimallashtirish: 5 ta variantning barcha o'rin almashtirishlari (120 ta) ustidan
`E[foyda]` maksimallashtiriladi, bu yerda foyda = `I(o)` (qiziqish mosligi) va grant/kontrakt
farqidan tuziladi. 120 ta variant — arzon, to'liq qidiruv yetarli.

> **Modelning cheklovi:** haqiqiy tizimda o'tish balli barcha abituriyentlarning tanlovidan
> kelib chiqib **dinamik** shakllanadi. Biz uni tarixiy taqsimot orqali taxmin qilamiz.
> Shuning uchun natija "ehtimol" deb, ishonch oralig'i bilan ko'rsatiladi.

### QADAM 7 — Tayyorgarlik muddati (M6)

Bu bosqich foydalanuvchining asosiy savoliga javob beradi: **"Qancha vaqt kerak?"**

**7.1. Har bir mavzuning "narxi" va "foydasi".**

```
Foyda (ball):     G_t = q_t · k_f · (1 − g) · Δm_t        // g = 0,25
                  ya'ni 1 birlik o'zlashtirish = q_t · k_f · 0,75 ball

Vaqt (soat):      o'rganish egri chizig'i — o'zlashtirish eksponensial to'yinadi:
                  m(τ) = 1 − (1 − m₀)·e^(−τ/T),   T = H_t / 3
                  H_t — 0 dan 0,95 gacha ko'tarilish uchun kerakli bazaviy soat (ekspert bahosi)

                  t(m₀ → m₁) = (H_t / 3) · ln( (1 − m₀) / (1 − m₁) ) / r_u

                  r_u — o'quvchining shaxsiy o'rganish tezligi (boshida 1,0)
```

Nima uchun logarifm: o'zlashtirishni 0,3 dan 0,6 ga ko'tarish 0,8 dan 0,9 ga ko'tarishdan
ancha arzon. Bu "oxirgi 10% eng qimmat" qoidasini modelga kiritadi va real tajribaga mos.

**7.2. Ustuvorlik: ball/soat bo'yicha saralash.**

```
samaradorlik(t) = G_t / t_t        [ball / soat]
```

Mavzular shu ko'rsatkich bo'yicha kamayish tartibida saralanadi, **lekin** zaruriy
bilim grafi (DAG) hisobga olinadi: agar mavzu `t` ning prerekviziti `t'` o'zlashtirilmagan
bo'lsa, `t'` ning vaqti `t` ning narxiga qo'shiladi.

Bu saralash amalda deyarli har doim **1-ixtisoslik fanini** birinchi o'ringa qo'yadi —
chunki uning har bir savoli 3,1 ball, majburiy fanniki esa 1,1 ball.

**7.3. Kerakli umumiy soat.**

```
Kerakli_ball = Ĉ_maqsad + xavfsizlik_zapasi(≈5 ball) − Joriy_ball

Mavzularni samaradorlik bo'yicha tanlab boramiz, to'plangan G yig'indisi
Kerakli_ball ga yetguncha:
    Soat_nazariy = Σ t_t

Soat_real = Soat_nazariy / η          // η = konsentratsiya samaradorligi 0,70–0,85
Soat_jami = Soat_real · (1 + ρ)  +  Soat_sinov

  ρ = 0,15–0,20 — intervalli takrorlash (spaced repetition) uchun qo'shimcha vaqt;
                  usiz o'zlashtirilgan mavzu 4–8 haftada unutiladi
  Soat_sinov    — har 3–4 haftada 1 ta to'liq sinov imtihoni (3 soat) + tahlil (1 soat)
```

**7.4. Soatdan kalendarga.**

```
Haftalar = Soat_jami / haftalik_soat
Tugash_sanasi = bugun + Haftalar

AGAR Tugash_sanasi > imtihon_sanasi:
    → maqsadga yetib bo'lmaydi
    → imtihon sanasigacha erishiladigan maksimal ballni hisoblaymiz:
         mavjud_soat = qolgan_haftalar · haftalik_soat
         Ball_max = shu soatga sig'adigan eng samarali mavzular yig'indisi
    → QADAM 3 ga qaytamiz: Ball_max bilan qaysi yo'nalishlar ochiq qoladi?
    → yoki: haftalik soatni oshirish taklifi (necha soatga oshirish kerakligi aniq aytiladi)
```

**7.5. Uch ssenariy (bitta raqam emas, oraliq beriladi).**

| Ssenariy | r_u | η | Ma'nosi |
|---|---:|---:|---|
| Ehtiyotkor | 0,8 | 0,70 | Dars qoldirishlar, sekin start |
| Realistik | 1,0 | 0,78 | Reja bo'yicha ishlasa |
| Intensiv | 1,2 | 0,85 | Repetitor + kunlik intizom |

Foydalanuvchiga **"≈4–6 oy"** ko'rinishida ko'rsatiladi, "4,3 oy" emas — soxta aniqlik
ishonchni yo'qotadi.

**7.6. Shaxsiylashtirish (eng muhim qism).** Har hafta nazorat testidan keyin:

```
r_kuzatilgan = (haqiqiy Δm) / (kutilgan Δm)
r_u ← 0,7 · r_u + 0,3 · r_kuzatilgan        // eksponensial silliqlash
```

2–3 haftadan keyin prognoz o'quvchining haqiqiy tezligiga moslashadi. Shundan keyingina
tizim "sizga 5 oy kerak" deyishga haqli — birinchi haftada bu faqat boshlang'ich taxmin,
va UI da shundayligi ochiq yozilishi kerak.

### QADAM 8 — Reja, kuzatuv va qayta hisob (M7)

```
Haftalik reja:
  - 2–4 ta mavzu (soatiga qarab), har biri: nazariya → mashq → takrorlash
  - kunlik 20 daqiqalik takrorlash bloki (oldingi mavzular, intervalli jadval bo'yicha)
  - hafta oxirida 20 savollik nazorat testi

Har hafta avtomatik qayta hisob:
  m_t yangilanadi → Joriy_ball → μ̂ → P(kirish) → qolgan soat → reja qayta tuziladi
  Trayektoriya grafigi: "shu sur'atda 12-iyulga 148 ball" + maqsad chizig'i

Ogohlantirishlar:
  - 2 hafta ketma-ket reja bajarilmasa → maqsadni yoki haftalik soatni qayta ko'rish taklifi
  - P(kirish) 0,30 dan pastga tushsa → muqobil yo'nalishlar taklifi
```

---

## 4. Namunaviy hisob-kitob (to'liq oqim)

> Raqamlar **illyustrativ** — `H_t` (bazaviy soatlar) va o'tish balli haqiqiy datasetdan
> olinishi kerak.

**Aziza, 11-sinf, Namangan. 2027-yil iyul imtihoni (bugundan ≈10 oy).
Haftasiga 10 soat vaqt ajrata oladi. Grant maqsad.**

**1–2-qadam.** RIASEC natijasi: S=0,62 I=0,55 R=0,31 A=0,22 E=0,20 C=0,18 → kod **SIR**.

**3-qadam.** Eng yuqori moslik: tibbiyot, hamshiralik ishi, pedagogika, psixologiya.

**4-qadam.** Tanlangan yo'nalish → **1-fan Biologiya, 2-fan Kimyo**. Bu blok 30+ yo'nalish
ochadi (tibbiyot, veterinariya, biotexnologiya, ekologiya...) — zaxira variantlar ko'p.

**5-qadam (diagnostika).**

| Fan | Koef. | Savol | m (o'zlashtirish) | p = m+(1−m)·0,25 | Ball |
|---|---:|---:|---:|---:|---:|
| Biologiya | 3,1 | 30 | 0,35 | 0,513 | 47,7 |
| Kimyo | 2,1 | 30 | 0,30 | 0,475 | 29,9 |
| Ona tili | 1,1 | 10 | 0,60 | 0,700 | 7,7 |
| Matematika | 1,1 | 10 | 0,40 | 0,550 | 6,1 |
| O'zbekiston tarixi | 1,1 | 10 | 0,50 | 0,625 | 6,9 |
| **Joriy ball** | | | | | **≈98** |

**6-qadam.** Maqsad yo'nalishning o'tish balli prognozi `Ĉ ≈ 140`, `σ_c = 6`.
Zapas bilan **maqsad = 145**. Farq: **47 ball**.

Hozirgi holatda `P = Φ((98 − 140)/√(12² + 6²)) = Φ(−3,1) ≈ 0,1%` — ya'ni **hozir kira olmaydi**.
Aynan shu raqam o'quvchini harakatga keltiradi.

**7-qadam (muddat).** 1 birlik o'zlashtirishning ball qiymati:

```
Biologiya:  30 · 3,1 · 0,75 = 69,8 ball
Kimyo:      30 · 2,1 · 0,75 = 47,3 ball
Majburiylar:10 · 1,1 · 0,75 =  8,3 ball  (har biri)
```

Bazaviy soatlar (ekspert): `H_bio = 180`, `H_kim = 160`.

```
Biologiya 0,35 → 0,80:
  t = (180/3) · ln(0,65/0,20) = 60 · 1,179 = 70,7 soat   → +31,4 ball  (0,44 ball/soat)
Kimyo 0,30 → 0,63:
  t = (160/3) · ln(0,70/0,37) = 53,3 · 0,638 = 34,0 soat → +15,6 ball  (0,46 ball/soat)
  ————————————————————————————————————————————————————
  Σ = 104,7 soat nazariy                                   → +47,0 ball ✓

Soat_real  = 104,7 / 0,78 ≈ 134 soat
Takrorlash = ×1,18        ≈ 158 soat
Sinovlar   = 6 × 4 soat   = 24 soat
———————————————————————————————
Soat_jami ≈ 182 soat
```

| Ssenariy | Soat | Haftasiga 10 soat | Haftasiga 15 soat |
|---|---:|---:|---:|
| Ehtiyotkor | ≈245 | 24 hafta (5,6 oy) | 16 hafta (3,8 oy) |
| **Realistik** | **≈182** | **18 hafta (4,2 oy)** | 12 hafta (2,8 oy) |
| Intensiv | ≈145 | 15 hafta (3,4 oy) | 10 hafta (2,3 oy) |

**Xulosa (foydalanuvchi ko'radigan matn):**

> Hozirgi darajangiz **≈98 ball**. Tanlagan yo'nalishingiz uchun **≈145 ball** kerak.
> Haftasiga 10 soat ishlasangiz, bu farqni **taxminan 4–6 oyda** yopasiz.
> Imtihongacha **10 oy** bor — ya'ni ulgurasiz, hatto **≈4 oy zaxira** qoladi.
> Shu zaxirani ishlatsangiz, **grant** darajasiga ham chiqishingiz mumkin.
> Vaqtingizning **67% ini Biologiyaga** sarflang: u yerdagi har bir savol 3,1 ball,
> O'zbekiston tarixidagi savol esa atigi 1,1 ball.

Diqqat: e'tiborni majburiy fanlarga bersa, xuddi shu 182 soat atigi **+15 ball** berardi.
Modelning butun qiymati — mana shu farqda.

---

## 5. Formulalar jamlanmasi

```
Ball_f      = n_f · k_f · ( m_f + (1 − m_f)·g ) ,  g = 0,25
Umumiy_ball = Σ_f Ball_f
m_f         = Σ_t q_t·m_t / Σ_t q_t

I(o)        = Σ_k v_k·u_k                                  (kosinus moslik)
Score(o)    = w₁I + w₂A + w₃P + w₄M + w₅V

Ĉ           = 0,5·C_{y−1} + 0,3·C_{y−2} + 0,2·C_{y−3}
σ_c         = max( std(C), 5 )
P(kirish)   = Φ( (μ̂ − Ĉ) / sqrt(σ_s² + σ_c²) )

G_t         = q_t · k_f · 0,75 · Δm_t                      (ball foydasi)
t(m₀→m₁)    = (H_t/3) · ln((1−m₀)/(1−m₁)) / r_u            (soat narxi)
samaradorlik= G_t / t_t
Soat_jami   = (Σt / η)·(1+ρ) + Soat_sinov
Haftalar    = Soat_jami / haftalik_soat
r_u         ← 0,7·r_u + 0,3·r_kuzatilgan
```

---

## 6. Kalibrovka va sifat metrikalari

| Metrika | Nimani o'lchaydi | Maqsad |
|---|---|---|
| **MAE(ball)** | Prognoz qilingan DTM bali vs haqiqiy ball | < 10 ball (1-yil), < 7 (2-yil) |
| **Brier score** | Kirish ehtimoli prognozining sifati | < 0,15 |
| **Kalibrovka egri chizig'i** | "70% dedik" → haqiqatda 70% kirdimi | ±10% oraliqda |
| **Muddat qamrovi** | Bashorat qilingan oraliqqa tushgan o'quvchilar ulushi | > 70% |
| **Blok o'zgarishi** | Tavsiyadan keyin blokini o'zgartirganlar ulushi | kuzatiladi |
| **Reja bajarilishi** | Rejadagi soatning necha % bajarildi | > 60% |

Har yil avgustda (mandat e'lon qilingach) barcha foydalanuvchilarning **haqiqiy natijasi**
yig'iladi va model qayta o'qitiladi. Bu — mahsulotning eng katta uzoq muddatli aktivi:
3 yildan keyin O'zbekistonda hech kimda bo'lmagan "ball → tayyorgarlik → natija" dataseti
bo'ladi.

---

## 7. Cheklovlar, risklar va etika

| Risk | Ta'siri | Yechim |
|---|---|---|
| Qabul qoidalari har yili o'zgaradi | Butun model buziladi | Barcha qoidalar — versiyalangan konfiguratsiya fayli, kodga yozilmaydi |
| O'tish ballari ma'lumoti to'liq emas | Ehtimollik hisoblab bo'lmaydi | Yo'q joyda ehtimollik ko'rsatilmaydi, "ma'lumot yetarli emas" deyiladi |
| Modelning soxta aniqligi | Ishonchni yo'qotish, noto'g'ri qaror | Oraliq + ishonch darajasi, hech qachon bitta raqam yoki kafolat emas |
| Test savollari mualliflik huquqi | Huquqiy muammo | Savollar bankini o'zimiz yozamiz, DTM testlari nusxalanmaydi |
| Voyaga yetmaganlar ma'lumoti | Maxfiylik | Minimal ma'lumot, ota-ona roziligi, ma'lumotni eksport/o'chirish huquqi |
| "Qiziqish testi taqdirni hal qiladi" taassuroti | Noto'g'ri kasb tanlash | Natija tavsiya sifatida, 6 oydan keyin qayta topshirish, maslahatchi bilan suhbat taklifi |
| Foydalanuvchi kira olmay qolsa, aybni mahsulotga qo'yadi | Obro' | Har bir prognozda ehtimollik tabiati ochiq tushuntiriladi; "kafolat" so'zi taqiqlanadi |

---

## 8. Ochiq savollar (kod yozishdan oldin tekshirilsin)

1. Matematika **majburiy fan** bo'lib turib, ayni paytda **ixtisoslik fani** bo'lsa
   (masalan matematika 1-fan bo'lgan yo'nalishlarda) — ball qanday hisoblanadi?
   Ikki marta topshiriladimi yoki ballar birlashtiriladimi?
2. 2027-yil uchun **minimal o'tish ball** chegaralari (yo'nalishlar guruhi bo'yicha).
3. Test savollarida variantlar soni (taxmin ehtimoli `g` shunga bog'liq: 4 ta → 0,25).
4. Yo'nalish bo'yicha **haqiqiy o'tish ballari** qaysi rasmiy manbada, qaysi formatda
   e'lon qilinadi (mandat portali? ochiq ma'lumotlar portali?).
5. Milliy sertifikat ballari → DTM balliga o'tkazishning **aniq proporsional formulasi**
   (B+, B, C+, C darajalari uchun).
6. Grant ustuvorligini tanlash mexanizmi 2027-yilda saqlanadimi?
7. Kvota (grant/kontrakt o'rinlari) qachon va qaysi formatda e'lon qilinadi.
8. Ijodiy imtihonli yo'nalishlar ro'yxati va ularning baholash tartibi.

> Bu savollarga javob topilmaguncha tegishli funksiyalar **"beta"** yorlig'i bilan
> chiqariladi yoki umuman yoqilmaydi.

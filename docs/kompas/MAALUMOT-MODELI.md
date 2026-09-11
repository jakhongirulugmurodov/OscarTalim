# Ma'lumot modeli va ETL quvuri

Versiya: 1.0 · Sana: 2026-09-11

Algoritm qanchalik yaxshi bo'lmasin, **ma'lumot sifati yechadi**. Bu hujjat — loyihaning
eng ko'p mehnat talab qiladigan, lekin eng katta raqobat ustunligi bo'ladigan qismi.

---

## 1. Asosiy tamoyillar

1. **Har bir yozuv manbaga bog'lanadi.** Hech qanday raqam manbasiz saqlanmaydi.
   Har bir jadvalda majburiy maydonlar: `manba_url`, `manba_sana`, `yigilgan_sana`,
   `ishonch` (`rasmiy` | `ikkilamchi` | `hisoblangan` | `ekspert_bahosi`).
2. **Yil bo'yicha versiyalash.** Qoidalar har yili o'zgaradi. Barcha jadvallarda
   `oquv_yili` maydoni bor; eski yillar o'chirilmaydi (ular prognoz uchun kerak).
3. **Konfiguratsiya kod emas.** Ball koeffitsientlari, minimal ballar, kalendar sanalari —
   hammasi `config/qabul-2027.json` da. Yangi yil = yangi fayl, kodga tegilmaydi.
4. **Avtomatik tekshiruv.** Har import'dan keyin validatsiya ishlaydi (§ 6). Tekshiruvdan
   o'tmagan dataset ishlab chiqarishga chiqmaydi.

---

## 2. Jadvallar (JSON / SQL sxemasi)

### 2.1. `otm` — oliy ta'lim tashkilotlari

```json
{
  "id": "tta",
  "nom_uz": "Toshkent tibbiyot akademiyasi",
  "nom_ru": "Ташкентская медицинская академия",
  "qisqa": "TTA",
  "tur": "davlat",                 // davlat | nodavlat | xorijiy_filial
  "hudud": "Toshkent shahri",
  "filiallar": [{"id": "tta_urganch", "hudud": "Xorazm"}],
  "sayt": "https://tma.uz",
  "manba_url": "...", "manba_sana": "2026-07-18", "ishonch": "rasmiy"
}
```

### 2.2. `yonalish` — ta'lim yo'nalishlari (klassifikator)

```json
{
  "kod": "60910400",
  "nom_uz": "Davolash ishi",
  "soha": "Sog'liqni saqlash",       // ISCED sohasi
  "daraja": "bakalavr",
  "oqish_muddati": 5,
  "riasec": {"R":0.30,"I":0.62,"A":0.10,"S":0.65,"E":0.20,"C":0.25},
  "riasec_manba": "onet_mapping+ekspert",
  "kasblar": ["shifokor", "ordinator"],
  "manba_url": "...", "ishonch": "rasmiy"
}
```

### 2.3. `fanlar_majmuasi` — yo'nalish → imtihon fanlari (yillik)

```json
{
  "oquv_yili": "2026/2027",
  "yonalish_kod": "60910400",
  "fan_1": "biologiya",              // koeffitsient 3,1
  "fan_2": "kimyo",                  // koeffitsient 2,1
  "ijodiy_imtihon": false,
  "sertifikat_talab": false,         // chet tili 1-fan bo'lsa true
  "manba_url": "uzbmb.uz/.../Fanlar_majmuasi_2026-2027.pdf",
  "ishonch": "rasmiy"
}
```

### 2.4. `taklif` — OTM × yo'nalish × shakl × til (yillik)

```json
{
  "oquv_yili": "2026/2027",
  "otm_id": "tta",
  "yonalish_kod": "60910400",
  "talim_shakli": "kunduzgi",        // kunduzgi | sirtqi | kechki | masofaviy
  "talim_tili": "uz",
  "kvota_grant": 120,
  "kvota_kontrakt": 340,
  "kontrakt_narxi": 22000000,
  "manba_url": "...", "ishonch": "rasmiy"
}
```

### 2.5. `otish_balli` — tarixiy o'tish ballari (modelning yuragi)

```json
{
  "oquv_yili": "2025/2026",
  "otm_id": "tta", "yonalish_kod": "60910400",
  "talim_shakli": "kunduzgi", "talim_tili": "uz",
  "grant_min_ball": 168.3,
  "kontrakt_min_ball": 141.7,
  "arizalar_soni": 2140,
  "manba_url": "...", "ishonch": "rasmiy"
}
```

> Bu jadval **kamida 3 yil** uchun to'ldirilishi shart, aks holda ehtimollik moduli
> ishlamaydi. Eng yuqori ustuvorlikdagi ma'lumot yig'ish vazifasi shu.

### 2.6. `mavzu` — fan → mavzu daraxti (tayyorgarlik rejasining asosi)

```json
{
  "id": "bio_genetika_mendel",
  "fan": "biologiya",
  "bolim": "Genetika",
  "nom": "Mendel qonunlari",
  "kutilgan_savol": 2.4,             // shu mavzudan o'rtacha necha savol tushadi
  "qiyinlik": 0.62,                  // 0..1
  "bazaviy_soat": 6.0,               // H_t: 0 → 0,95 o'zlashtirish uchun
  "prerekvizit": ["bio_hujayra_bolinishi"],
  "ishonch": "ekspert_bahosi"
}
```

`kutilgan_savol` boshida ekspert bahosi, keyin real test tahlilidan (blueprint) aniqlanadi.
`Σ kutilgan_savol` har fan bo'yicha aniq **30** (ixtisoslik) yoki **10** (majburiy) bo'lishi shart.

### 2.7. `savol` — savollar banki (diagnostika uchun)

```json
{
  "id": "q_00412",
  "mavzu_id": "bio_genetika_mendel",
  "matn": "...", "variantlar": ["A","B","C","D"], "togri": "B",
  "izoh": "...",                     // noto'g'ri javobdan keyin ko'rsatiladi
  "irt_b": 0.4,                      // qiyinlik parametri (kalibrlanadi)
  "irt_a": 1.1,                      // ajratish qobiliyati
  "statistika": {"urinish": 1840, "togri_ulush": 0.58},
  "muallif": "oscar_talim", "litsenziya": "ichki"
}
```

**Huquqiy talab:** savollar o'z mualliflarimiz tomonidan yoziladi. DTM test kitoblaridan
nusxa ko'chirilmaydi.

### 2.8. `foydalanuvchi_holati` — o'quvchi profili va progressi

```json
{
  "user_id": "u_1032",
  "profil": { "sinf": 11, "hudud": "Namangan", "haftalik_soat": 10, "...": "..." },
  "riasec": {"R":0.31,"I":0.55,"A":0.22,"S":0.62,"E":0.20,"C":0.18},
  "mastery": { "bio_genetika_mendel": 0.42, "...": 0.0 },
  "r_u": 1.08,                        // shaxsiy o'rganish tezligi
  "sinov_tarixi": [{"sana":"2026-10-05","ball":104.2}],
  "tanlangan_yonalishlar": ["60910400@tta", "..."],
  "yangilangan": "2026-10-05T18:20:00Z"
}
```

---

## 3. Ma'lumot manbalari va yig'ish tartibi

| Dataset | Rasmiy manba | Chiqish vaqti | Yig'ish usuli |
|---|---|---|---|
| Yo'nalishlar klassifikatori | `lex.uz` (OTFIV buyrug'i) | O'zgarganda | PDF → parser + qo'lda tekshirish |
| Fanlar majmuasi | `uzbmb.uz` (PDF) | Fevral–mart | PDF → jadval parser (`camelot`/`pdfplumber`) |
| OTM ro'yxati va kvota | Vazirlar Mahkamasi qarori / `edu.uz` | Iyun–iyul | PDF/HTML → parser |
| Qabul qoidalari, minimal ball | Davlat qabul komissiyasi qarori | May–iyun | Qo'lda kiritish (kam yozuv, yuqori xavf) |
| O'tish ballari | Mandat natijalari | Avgust | Eng qiyin qism — § 3.1 |
| Milliy sertifikat qoidalari | `lex.uz`, `uzbmb.uz` | O'zgarganda | Qo'lda |
| Kasb ↔ RIASEC | O\*NET (public domain) | Yillik | Avtomatik yuklab olish |

### 3.1. O'tish ballari — 3 ta zaxira strategiya

Bu ma'lumot markazlashgan mashina-o'qiy formatda doim ham chiqavermaydi. Shuning uchun:

1. **Rasmiy:** mandat/ochiq ma'lumotlar portalidan yuklab olish (agar mavjud bo'lsa).
2. **Agregatorlar:** abituriyentlarga mo'ljallangan portallar har yili shu jadvallarni
   e'lon qiladi — ikkilamchi manba sifatida (`ishonch: "ikkilamchi"`), kamida 2 ta
   mustaqil manba mos kelsa qabul qilinadi.
3. **O'z foydalanuvchilarimiz:** avgustda har bir foydalanuvchidan "qaysi yo'nalishga,
   necha ball bilan tushdingiz" so'raladi. 1-yil 500 ta javob — bu allaqachon
   yo'nalishlar bo'yicha real kesim beradi; 3-yil — bozordagi eng yaxshi dataset.

### 3.2. Ushbu sessiyadagi texnik cheklov

Bu tahlil bajarilgan muhitda **tarmoq siyosati `.uz` domenlariga chiqishni bloklaydi**
(`uzbmb.uz`, `lex.uz`, `data.gov.uz`, `my.uzbmb.uz` — hammasi 403). Shuning uchun bu yerdagi
faktlar qidiruv natijalaridan olingan va **rasmiy hujjatlar bilan solishtirilishi shart**.
PDF larni yuklab olish uchun: (a) tarmoq siyosatiga shu domenlarni qo'shish, yoki
(b) faylni qo'lda repozitoriyga joylash (`data/raw/` papkasi).

---

## 4. Yo'nalishlarga RIASEC profilini berish

Bu — sifatli tavsiyaning kaliti. Uch bosqichli usul:

```
1-bosqich (avtomatik, boshlang'ich):
   O'zbek yo'nalishi → unga eng yaqin O*NET kasb(lar)i (SOC kodi)
   → O*NET dan shu kasblarning RIASEC profillari (public domain)
   → o'rtacha → yo'nalishning boshlang'ich profili

2-bosqich (ekspert tekshiruvi):
   Har bir yo'nalish 3 ta mustaqil ekspert (kasb yo'naltiruvchi/o'qituvchi) tomonidan
   baholanadi. Kelishmovchilik > 0,2 bo'lsa — muhokama.
   Kelishuv darajasi (Krippendorff's alpha) o'lchanadi va hujjatlashtiriladi.

3-bosqich (real ma'lumot bilan kalibrovka):
   1-kurs talabalaridan so'rov: "tanlovingizdan qoniqasizmi?" (1–5)
   → qoniqish balli yuqori bo'lgan talabalarning RIASEC profillari
   → yo'nalish profilini shu markazga siljitish (har yili)
```

3-bosqich mahsulotni raqobatchilardan ajratadi: tavsiya **haqiqiy natijaga** asoslanadi,
taxminga emas.

---

## 5. Papka tuzilmasi

```
data/
  raw/                     # yuklab olingan asl PDF/HTML lar (o'zgartirilmaydi)
    2026/uzbmb_fanlar_majmuasi.pdf
  parsed/                  # parser chiqishi (oraliq)
  clean/                   # ishlab chiqarishga tayyor JSON lar
    otm.json
    yonalish.json
    fanlar_majmuasi_2026_2027.json
    taklif_2026_2027.json
    otish_balli.json
    mavzu.json
config/
  qabul-2027.json          # ball koeffitsientlari, minimal ballar, kalendar
scripts/
  parse_fanlar_majmuasi.py
  validate.py
  build_index.py           # qidiruv/moslik uchun oldindan hisoblangan indekslar
```

---

## 6. Validatsiya qoidalari (CI da avtomatik ishlaydi)

```
[BALL]      Σ (n_f · k_f) = 189,0 ± 0,01
[SAVOL]     Har ixtisoslik fani: Σ kutilgan_savol = 30 ± 0,1
            Har majburiy fan:    Σ kutilgan_savol = 10 ± 0,1
[FAN]       Har bir yonalish_kod uchun fanlar_majmuasi da aynan 1 ta yozuv bor
[BOG'LIQ]   Har bir taklif.yonalish_kod → yonalish jadvalida mavjud
            Har bir taklif.otm_id      → otm jadvalida mavjud
[BALL_CHEK] 0 ≤ otish_balli ≤ 189 ; grant_min ≥ kontrakt_min
[MANBA]     Har bir yozuvda manba_url va ishonch to'ldirilgan
[ESKIRISH]  yigilgan_sana 400 kundan eski bo'lsa → ogohlantirish bayrog'i
[DAG]       mavzu.prerekvizit grafida sikl yo'q (topologik saralash ishlaydi)
[RIASEC]    har profil vektori normalizatsiyalangan (|v| = 1 ± 0,01)
```

Validatsiyadan o'tmagan ma'lumot ishlab chiqarishga chiqmaydi — bu qattiq qoida.
UI da har doim "ma'lumot yangilangan: 2026-08-20" yozuvi ko'rinadi.

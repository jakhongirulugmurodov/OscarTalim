/* Kompas — 2027 qabul sikli konfiguratsiyasi.
   Raqamlar har yili o'zgaradi: bu fayl kod emas, sozlama. Manba va ishonch darajasi:
   docs/kompas/MANBALAR.md */
window.KOMPAS_CONFIG = {
  oquv_yili: "2027/2028",
  yangilangan: "2026-09-14",

  // Ball tizimi (ishonch: A)
  koef:  { fan1: 3.1, fan2: 2.1, majburiy: 1.1 },
  savol: { fan1: 30,  fan2: 30,  majburiy: 10 },
  max_ball: 189,
  majburiy_fanlar: ["ona_tili", "matematika", "tarix"],
  variantlar_soni: 4,          // taxmin ehtimoli g = 1/4 (tekshirilsin)

  // Kalendar (2026 siklidan, 2027 uchun taxminiy — ishonch: B)
  kalendar: {
    royxat_boshi:  "2027-06-05",
    royxat_oxiri:  "2027-06-25",
    test_boshi:    "2027-07-14",
    test_oxiri:    "2027-07-28",
    tanlov_boshi:  "2027-07-25",
    tanlov_oxiri:  "2027-08-08",
    mandat:        "2027-08-15"
  },

  // Minimal ball (ishonch: C — manbalar qarama-qarshi, MANBALAR.md §3)
  minimal_ball: {
    variant: "guruh",            // "guruh" | "yagona"
    guruh:  { yuqori: 94.5, oddiy: 75.6 },   // tibbiyot/yuridik/biznes → yuqori
    yagona: { grant: 68.0, kontrakt: 56.7 }
  },

  // Tayyorgarlik modeli parametrlari (ekspert bahosi — kalibrovka qilinadi)
  model: {
    g: 0.25,                     // taxmin ehtimoli
    mastery_cap: 0.92,           // reja hech qachon 100% o'zlashtirishga qurilmaydi
    rho: 0.18,                   // intervalli takrorlash uchun qo'shimcha ulush
    sinov_har_hafta: 4,          // har 4 haftada 1 sinov imtihoni
    sinov_soat: 4,               // 3 soat imtihon + 1 soat tahlil
    zapas_ball: 5,               // maqsad = o'tish balli prognozi + zapas
    sigma_s_boshlangich: 12,     // o'quvchi bali prognoz xatosi (ball)
    sigma_c_min: 6,              // o'tish balli noaniqligi (ball), kamida
    ssenariylar: {
      ehtiyotkor: { r: 0.8, eta: 0.70, nom: "Ehtiyotkor" },
      realistik:  { r: 1.0, eta: 0.78, nom: "Realistik"  },
      intensiv:   { r: 1.2, eta: 0.85, nom: "Intensiv"   }
    },
    // Tavsiya vaznlari (ALGORITM.md §3, QADAM 3)
    vaznlar: {
      muvozanat:  { I: 0.30, A: 0.20, P: 0.30, M: 0.10, V: 0.10, nom: "Muvozanat" },
      qiziqish:   { I: 0.50, A: 0.15, P: 0.15, M: 0.10, V: 0.10, nom: "Qiziqishim muhim" },
      kafolat:    { I: 0.15, A: 0.20, P: 0.50, M: 0.05, V: 0.10, nom: "Kirishim ishonchli bo'lsin" }
    },
    savat: { orzu_max: 0.30, ishonchli_min: 0.70 }
  },

  // Milliy sertifikat darajalari → fan ballining ulushi (ishonch: B; proporsional
  // koeffitsientlar tekshirilsin — MANBALAR.md §5)
  sertifikat_ulush: { "A+": 1.0, "A": 1.0, "B+": 0.85, "B": 0.75, "C+": 0.65, "C": 0.55 }
};

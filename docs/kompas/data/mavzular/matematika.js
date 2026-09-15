/* Mavzular: matematika (ixtisoslik 30 savol; majburiy 10 savol — bitta daraxt, majburiy test asosan 1–4-bo'limlardan).
   ulush — DTM ixtisoslik testida shu mavzudan savol tushish ulushi (Σ = 1.000), 2021–2025 test variantlari tahlili
   asosidagi ekspert bahosi; DTM rasmiy test spetsifikatsiyasi bilan solishtirilsin (tekshirilsin).
   bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi). ishonch: ekspert_bahosi. 2026-09-14 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.matematika = {
  fan: "matematika",
  manba: "DTM test dasturi (umumta'lim maktab dasturi 5–11-sinf asosida)",
  mavzular: [
    /* ---- 1. Arifmetika va sonlar (5–6-sinf, 8-sinf) ---- */
    { id: "mat_01", bolim: "Arifmetika va sonlar", nom: "Natural sonlar: bo'linish belgilari, tub va murakkab sonlar, EKUB va EKUK",            ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.28 },
    { id: "mat_02", bolim: "Arifmetika va sonlar", nom: "Oddiy, o'nli va davriy kasrlar, ular ustida amallar, sonlarni taqqoslash",              ulush: 0.025, bazaviy_soat: 4, qiyinlik: 0.30 },
    { id: "mat_03", bolim: "Arifmetika va sonlar", nom: "Nisbat, proporsiya va foiz, sodda foiz hisoblari",                                       ulush: 0.032, bazaviy_soat: 5, qiyinlik: 0.35 },
    { id: "mat_04", bolim: "Arifmetika va sonlar", nom: "Haqiqiy sonlar, sonning moduli, sonli oraliqlar, yaxlitlash va standart shakl",          ulush: 0.018, bazaviy_soat: 3, qiyinlik: 0.35 },
    { id: "mat_05", bolim: "Arifmetika va sonlar", nom: "Darajalar va ildizlar: butun va ratsional ko'rsatkichli daraja, arifmetik ildiz xossalari", ulush: 0.030, bazaviy_soat: 6, qiyinlik: 0.45 },

    /* ---- 2. Algebraik ifodalar (7–8-sinf) ---- */
    { id: "mat_06", bolim: "Algebraik ifodalar", nom: "Ko'phadlar, qisqa ko'paytirish formulalari, ko'paytuvchilarga ajratish",                   ulush: 0.027, bazaviy_soat: 6, qiyinlik: 0.45 },
    { id: "mat_07", bolim: "Algebraik ifodalar", nom: "Algebraik kasrlar va ratsional ifodalarni ayniy shakl almashtirish",                       ulush: 0.022, bazaviy_soat: 5, qiyinlik: 0.50 },
    { id: "mat_08", bolim: "Algebraik ifodalar", nom: "Irratsional ifodalarni shakl almashtirish, maxrajdagi irratsionallikdan qutulish",         ulush: 0.018, bazaviy_soat: 5, qiyinlik: 0.55 },

    /* ---- 3. Tenglama, tengsizlik va matn masalalari (7–9-sinf) ---- */
    { id: "mat_09", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Chiziqli tenglama va tengsizliklar, sodda parametrli hollar",         ulush: 0.020, bazaviy_soat: 4, qiyinlik: 0.35 },
    { id: "mat_10", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Kvadrat tenglama, Viyet teoremasi, kvadrat uchhadni ko'paytuvchilarga ajratish", ulush: 0.040, bazaviy_soat: 7, qiyinlik: 0.45 },
    { id: "mat_11", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Ratsional tenglama va tengsizliklar, intervallar usuli",              ulush: 0.032, bazaviy_soat: 7, qiyinlik: 0.55 },
    { id: "mat_12", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Tenglamalar va tengsizliklar sistemalari",                             ulush: 0.027, bazaviy_soat: 5, qiyinlik: 0.55 },
    { id: "mat_13", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Modul qatnashgan tenglama va tengsizliklar",                           ulush: 0.024, bazaviy_soat: 5, qiyinlik: 0.60 },
    { id: "mat_14", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Irratsional tenglama va tengsizliklar",                                ulush: 0.024, bazaviy_soat: 5, qiyinlik: 0.60 },
    { id: "mat_15", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Matn masalalari: harakat (yo'l, tezlik, oqim) va birgalikda bajarilgan ish", ulush: 0.055, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "mat_16", bolim: "Tenglama, tengsizlik va matn masalalari", nom: "Matn masalalari: foiz, aralashma va qotishma, sonlar va raqamlar haqida", ulush: 0.045, bazaviy_soat: 6, qiyinlik: 0.55 },

    /* ---- 4. Funksiyalar va progressiyalar (7–10-sinf) ---- */
    { id: "mat_17", bolim: "Funksiyalar va progressiyalar", nom: "Funksiya tushunchasi: aniqlanish va qiymatlar sohasi, juft-toqlik, monotonlik, davriylik", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.55 },
    { id: "mat_18", bolim: "Funksiyalar va progressiyalar", nom: "Elementar funksiyalar grafiklari (chiziqli, kvadrat, teskari proporsional, daraja) va grafikni almashtirish", ulush: 0.025, bazaviy_soat: 5, qiyinlik: 0.55 },
    { id: "mat_19", bolim: "Funksiyalar va progressiyalar", nom: "Arifmetik va geometrik progressiyalar, cheksiz kamayuvchi geometrik progressiya", ulush: 0.045, bazaviy_soat: 6, qiyinlik: 0.45 },
    { id: "mat_20", bolim: "Funksiyalar va progressiyalar", nom: "Ko'rsatkichli funksiya, ko'rsatkichli tenglama va tengsizliklar",               ulush: 0.030, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "mat_21", bolim: "Funksiyalar va progressiyalar", nom: "Logarifm va uning xossalari, logarifmik funksiya, tenglama va tengsizliklar",    ulush: 0.037, bazaviy_soat: 7, qiyinlik: 0.65 },

    /* ---- 5. Trigonometriya (9–10-sinf) ---- */
    { id: "mat_22", bolim: "Trigonometriya", nom: "Trigonometrik funksiyalar ta'rifi, asosiy ayniyatlar, keltirish formulalari",                  ulush: 0.028, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "mat_23", bolim: "Trigonometriya", nom: "Qo'shish, ikkilangan va yarim burchak formulalari, yig'indini ko'paytmaga aylantirish",        ulush: 0.027, bazaviy_soat: 7, qiyinlik: 0.65 },
    { id: "mat_24", bolim: "Trigonometriya", nom: "Trigonometrik funksiyalar grafiklari va xossalari, teskari trigonometrik funksiyalar",         ulush: 0.015, bazaviy_soat: 4, qiyinlik: 0.65 },
    { id: "mat_25", bolim: "Trigonometriya", nom: "Trigonometrik tenglama va tengsizliklar",                                                        ulush: 0.030, bazaviy_soat: 7, qiyinlik: 0.72 },

    /* ---- 6. Matematik analiz boshlanmalari (10–11-sinf) ---- */
    { id: "mat_26", bolim: "Matematik analiz boshlanmalari", nom: "Ketma-ketlik va funksiya limiti (sodda hollar), hosila: hisoblash qoidalari, geometrik va fizik ma'nosi", ulush: 0.027, bazaviy_soat: 7, qiyinlik: 0.60 },
    { id: "mat_27", bolim: "Matematik analiz boshlanmalari", nom: "Hosila tatbiqi: urinma tenglamasi, monotonlik, ekstremumlar, eng katta va eng kichik qiymat", ulush: 0.022, bazaviy_soat: 6, qiyinlik: 0.65 },
    { id: "mat_28", bolim: "Matematik analiz boshlanmalari", nom: "Boshlang'ich funksiya va aniq integral, egri chiziqli trapetsiya yuzi",         ulush: 0.018, bazaviy_soat: 5, qiyinlik: 0.65 },

    /* ---- 7. Kombinatorika, ehtimollik va statistika (9, 11-sinf) ---- */
    { id: "mat_29", bolim: "Kombinatorika, ehtimollik va statistika", nom: "Kombinatorika elementlari: o'rin almashtirish, o'rinlashtirish, guruhlash, Nyuton binomi", ulush: 0.017, bazaviy_soat: 5, qiyinlik: 0.60 },
    { id: "mat_30", bolim: "Kombinatorika, ehtimollik va statistika", nom: "Klassik ehtimollik, hodisalar ustida amallar, statistika elementlari (o'rtacha, mediana, moda)", ulush: 0.016, bazaviy_soat: 4, qiyinlik: 0.50 },

    /* ---- 8. Planimetriya (7–9-sinf geometriya) ---- */
    { id: "mat_31", bolim: "Planimetriya", nom: "Uchburchaklar: tenglik va o'xshashlik alomatlari, Pifagor teoremasi, mediana, bissektrisa, balandlik, sinuslar va kosinuslar teoremasi", ulush: 0.035, bazaviy_soat: 7, qiyinlik: 0.60 },
    { id: "mat_32", bolim: "Planimetriya", nom: "To'rtburchaklar va ko'pburchaklar: parallelogramm, romb, to'g'ri to'rtburchak, kvadrat, trapetsiya, muntazam ko'pburchaklar", ulush: 0.025, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "mat_33", bolim: "Planimetriya", nom: "Aylana va doira: markaziy va ichki chizilgan burchaklar, vatar va urinma, ichki va tashqi chizilgan aylanalar", ulush: 0.022, bazaviy_soat: 7, qiyinlik: 0.65 },
    { id: "mat_34", bolim: "Planimetriya", nom: "Yuzalar: uchburchak, to'rtburchak, muntazam ko'pburchak, doira va uning qismlari",               ulush: 0.022, bazaviy_soat: 5, qiyinlik: 0.55 },
    { id: "mat_35", bolim: "Planimetriya", nom: "Tekislikda koordinatalar va vektorlar, to'g'ri chiziq va aylana tenglamalari",                    ulush: 0.012, bazaviy_soat: 4, qiyinlik: 0.55 },

    /* ---- 9. Stereometriya (10–11-sinf geometriya) ---- */
    { id: "mat_36", bolim: "Stereometriya", nom: "Fazoda to'g'ri chiziq va tekisliklar: parallellik, perpendikulyarlik, burchaklar va masofalar, fazoda vektorlar", ulush: 0.010, bazaviy_soat: 5, qiyinlik: 0.65 },
    { id: "mat_37", bolim: "Stereometriya", nom: "Ko'pyoqlar: prizma, parallelepiped, kub, piramida — kesimlar, sirt yuzi va hajm",              ulush: 0.024, bazaviy_soat: 7, qiyinlik: 0.65 },
    { id: "mat_38", bolim: "Stereometriya", nom: "Aylanish jismlari: silindr, konus, shar va sfera — sirt yuzi va hajm, ichki va tashqi chizilgan jismlar", ulush: 0.016, bazaviy_soat: 6, qiyinlik: 0.68 }
  ]
};

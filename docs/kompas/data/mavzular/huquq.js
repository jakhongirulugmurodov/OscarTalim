/* Mavzular: huquq. Huquqshunoslik asoslari — ixtisoslik fani, 30 savol.
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.huquq = {
  fan: "huquq",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "huq_01", bolim: "Davlat va huquq nazariyasi", nom: "Davlat tushunchasi, belgilari, funksiyalari; davlat shakllari (boshqaruv, tuzilish, rejim)", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "huq_02", bolim: "Davlat va huquq nazariyasi", nom: "Huquq tushunchasi, huquq normasi tuzilishi, huquq manbalari, huquq tizimi va sohalari", ulush: 0.060, bazaviy_soat: 8, qiyinlik: 0.6 },
    { id: "huq_03", bolim: "Davlat va huquq nazariyasi", nom: "Huquqiy munosabat; huquqbuzarlik turlari va yuridik javobgarlik", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "huq_04", bolim: "Davlat va huquq nazariyasi", nom: "Huquqiy ong va madaniyat; qonuniylik, huquqiy davlat va fuqarolik jamiyati", ulush: 0.030, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "huq_05", bolim: "Konstitutsiyaviy huquq", nom: "O'zbekiston Konstitutsiyasi: qabul qilinishi, tuzilishi, asosiy prinsiplar, o'zgartirishlar", ulush: 0.060, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "huq_06", bolim: "Konstitutsiyaviy huquq", nom: "Inson va fuqaro huquqlari, erkinliklari va burchlari; fuqarolik", ulush: 0.060, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "huq_07", bolim: "Konstitutsiyaviy huquq", nom: "Saylov tizimi va referendum; siyosiy partiyalar", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_08", bolim: "Konstitutsiyaviy huquq", nom: "Oliy Majlis: palatalar, vakolatlar, qonunchilik jarayoni", ulush: 0.050, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_09", bolim: "Konstitutsiyaviy huquq", nom: "Prezident va ijro hokimiyati: Vazirlar Mahkamasi, mahalliy davlat hokimiyati, mahalla", ulush: 0.050, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_10", bolim: "Konstitutsiyaviy huquq", nom: "Sud hokimiyati: sudlar tizimi, Konstitutsiyaviy sud, prokuratura, advokatura, Ombudsman", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "huq_11", bolim: "Fuqarolik huquqi", nom: "Fuqarolik huquqi subyektlari: jismoniy va yuridik shaxslar, muomala layoqati", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_12", bolim: "Fuqarolik huquqi", nom: "Mulk huquqi va uning shakllari; bitimlar, shartnoma turlari, majburiyatlar", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "huq_13", bolim: "Fuqarolik huquqi", nom: "Meros huquqi; intellektual mulk; iste'molchilar huquqlari", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_14", bolim: "Oila huquqi", nom: "Nikoh tuzish va bekor qilish shartlari; er-xotin, ota-ona va bolalar huquq-majburiyatlari", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.4 },
    { id: "huq_15", bolim: "Mehnat huquqi", nom: "Mehnat shartnomasi, ish vaqti va dam olish, mehnat intizomi, voyaga yetmaganlar mehnati", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "huq_16", bolim: "Ma'muriy huquq", nom: "Ma'muriy huquqbuzarlik va ma'muriy jazolar; davlat boshqaruvi organlari", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_17", bolim: "Jinoyat huquqi", nom: "Jinoyat tushunchasi, tarkibi, turlari; jinoyatga aloqadorlik", ulush: 0.060, bazaviy_soat: 8, qiyinlik: 0.6 },
    { id: "huq_18", bolim: "Jinoyat huquqi", nom: "Jazo turlari va tayinlash; javobgarlikni istisno qiluvchi holatlar; voyaga yetmaganlar javobgarligi", ulush: 0.050, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "huq_19", bolim: "Protsessual huquq", nom: "Jinoyat va fuqarolik protsessi asoslari: ishtirokchilar, bosqichlar, dalillar", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "huq_20", bolim: "Boshqa sohalar", nom: "Ekologik huquq; moliya va soliq huquqi asoslari; tadbirkorlik huquqi", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_21", bolim: "Xalqaro huquq", nom: "Xalqaro huquq manbalari, BMT va xalqaro tashkilotlar, inson huquqlari bo'yicha hujjatlar", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "huq_22", bolim: "Huquqni muhofaza qilish", nom: "Huquqni muhofaza qiluvchi organlar; korrupsiyaga qarshi kurash; notariat", ulush: 0.020, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "huq_23", bolim: "Takrorlash", nom: "Atamalar, moddalar va sanalar bo'yicha yakuniy takrorlash", ulush: 0.010, bazaviy_soat: 6, qiyinlik: 0.5 }
  ]
};

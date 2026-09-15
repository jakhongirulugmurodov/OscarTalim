/* Mavzular: geografiya. Geografiya — ixtisoslik fani, 30 savol.
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.geografiya = {
  fan: "geografiya",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "geo_01", bolim: "Umumiy geografiya", nom: "Yerning shakli va harakati; vaqt mintaqalari; geografik koordinatalar", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_02", bolim: "Umumiy geografiya", nom: "Xarita va plan: masshtab, shartli belgilar, azimut, gorizontallar", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_03", bolim: "Litosfera", nom: "Yer tuzilishi, litosfera plitalari, zilzila va vulqonlar; relyef shakllari", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_04", bolim: "Litosfera", nom: "Tog' jinslari va foydali qazilmalar; ularning joylashishi", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_05", bolim: "Atmosfera", nom: "Atmosfera tuzilishi, harorat, bosim, shamollar; ob-havo", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_06", bolim: "Atmosfera", nom: "Iqlim mintaqalari va iqlim hosil qiluvchi omillar", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "geo_07", bolim: "Gidrosfera", nom: "Dunyo okeani: oqimlar, sho'rlik, to'lqinlar; dengizlar", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_08", bolim: "Gidrosfera", nom: "Daryolar, ko'llar, muzliklar, yer osti suvlari", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_09", bolim: "Biosfera", nom: "Tabiat zonalari, tuproqlar, o'simlik va hayvonot dunyosi; geografik qobiq qonuniyatlari", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_10", bolim: "Materiklar", nom: "Afrika: tabiati, aholisi, mamlakatlari", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_11", bolim: "Materiklar", nom: "Avstraliya va Okeaniya; Antarktida", ulush: 0.019, bazaviy_soat: 3, qiyinlik: 0.3 },
    { id: "geo_12", bolim: "Materiklar", nom: "Janubiy Amerika", ulush: 0.019, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "geo_13", bolim: "Materiklar", nom: "Shimoliy Amerika", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_14", bolim: "Materiklar", nom: "Yevrosiyo: tabiati, iqlimi, daryolari, tabiat zonalari", ulush: 0.054, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "geo_15", bolim: "O'zbekiston geografiyasi", nom: "Geografik o'rni, chegaralari, relyefi, geologik tuzilishi", ulush: 0.038, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_16", bolim: "O'zbekiston geografiyasi", nom: "Iqlimi, ichki suvlari (Amudaryo, Sirdaryo, Orol muammosi), tuproq va o'simliklari", ulush: 0.048, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_17", bolim: "O'zbekiston geografiyasi", nom: "Aholisi: soni, joylashuvi, urbanizatsiya, mehnat resurslari", ulush: 0.038, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_18", bolim: "O'zbekiston geografiyasi", nom: "Sanoat tarmoqlari: yoqilg'i-energetika, metallurgiya, mashinasozlik, kimyo, yengil sanoat", ulush: 0.048, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "geo_19", bolim: "O'zbekiston geografiyasi", nom: "Qishloq xo'jaligi: dehqonchilik, chorvachilik, irrigatsiya", ulush: 0.038, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_20", bolim: "O'zbekiston geografiyasi", nom: "Transport, tashqi iqtisodiy aloqalar; iqtisodiy geografik rayonlar va viloyatlar", ulush: 0.048, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "geo_21", bolim: "Jahon geografiyasi", nom: "Dunyo aholisi: soni, tabiiy o'sish, migratsiya, irqlar, dinlar, urbanizatsiya", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_22", bolim: "Jahon geografiyasi", nom: "Siyosiy xarita, davlat tuzilishi, xalqaro tashkilotlar", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_23", bolim: "Jahon geografiyasi", nom: "Jahon xo'jaligi tarmoqlari: energetika, sanoat, qishloq xo'jaligi, transport", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "geo_24", bolim: "Jahon geografiyasi", nom: "MDH va Markaziy Osiyo mamlakatlari", ulush: 0.038, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "geo_25", bolim: "Jahon geografiyasi", nom: "Osiyo mamlakatlari: Xitoy, Yaponiya, Hindiston, Koreya, Turkiya", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_26", bolim: "Jahon geografiyasi", nom: "Yevropa mamlakatlari: Germaniya, Fransiya, Buyuk Britaniya, Italiya, Rossiya", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "geo_27", bolim: "Jahon geografiyasi", nom: "AQSh, Kanada, Braziliya, Avstraliya, Afrika mamlakatlari", ulush: 0.029, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "geo_28", bolim: "Global muammolar", nom: "Ekologik, demografik, oziq-ovqat, energetika muammolari; barqaror rivojlanish", ulush: 0.019, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "geo_29", bolim: "Takrorlash", nom: "Xarita bilan ishlash, statistik jadvallar, aralash testlar", ulush: 0.010, bazaviy_soat: 5, qiyinlik: 0.5 }
  ]
};

/* Mavzular: ona_tili_adabiyot. Ona tili va adabiyot — ixtisoslik fani, 30 savol: til (≈45%) + adabiyot (≈55%).
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.ona_tili_adabiyot = {
  fan: "ona_tili_adabiyot",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "ota_01", bolim: "Til: fonetika va imlo", nom: "Tovushlar, bo'g'in, urg'u; imlo qoidalari (o', g', tutuq belgisi, qo'shma so'zlar)", ulush: 0.066, bazaviy_soat: 9, qiyinlik: 0.5 },
    { id: "ota_02", bolim: "Til: leksikologiya", nom: "Ma'no turlari, sinonim-antonim-omonim-paronim, frazeologizm, lug'atlar", ulush: 0.066, bazaviy_soat: 8, qiyinlik: 0.4 },
    { id: "ota_03", bolim: "Til: morfologiya", nom: "So'z tarkibi va yasalishi; ot, sifat, son, olmosh", ulush: 0.066, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "ota_04", bolim: "Til: morfologiya", nom: "Fe'l va uning shakllari; ravish; yordamchi so'zlar", ulush: 0.075, bazaviy_soat: 9, qiyinlik: 0.6 },
    { id: "ota_05", bolim: "Til: sintaksis", nom: "So'z birikmasi, gap bo'laklari, sodda gap turlari", ulush: 0.066, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "ota_06", bolim: "Til: sintaksis", nom: "Qo'shma gap turlari, ko'chirma gap, tinish belgilari", ulush: 0.066, bazaviy_soat: 8, qiyinlik: 0.7 },
    { id: "ota_07", bolim: "Til: uslubiyat", nom: "Nutq uslublari, matn tahlili, badiiy til vositalari", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "ota_08", bolim: "Adabiyot: xalq og'zaki ijodi", nom: "Doston («Alpomish», «Go'ro'g'li»), ertak, maqol, topishmoq, qo'shiq janrlari", ulush: 0.047, bazaviy_soat: 5, qiyinlik: 0.4 },
    { id: "ota_09", bolim: "Adabiyot: qadimgi va ilk davr", nom: "O'rxun-Enasoy bitiklari, Mahmud Koshg'ariy, Yusuf Xos Hojib, Ahmad Yassaviy", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_10", bolim: "Adabiyot: mumtoz", nom: "Lutfiy, Atoiy, Sakkokiy; Alisher Navoiy hayoti va lirikasi", ulush: 0.057, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "ota_11", bolim: "Adabiyot: mumtoz", nom: "Navoiy «Xamsa»si: dostonlar mazmuni, obrazlar, g'oyalar", ulush: 0.057, bazaviy_soat: 8, qiyinlik: 0.6 },
    { id: "ota_12", bolim: "Adabiyot: mumtoz", nom: "Bobur («Boburnoma», lirika), Mashrab, Turdi, Munis, Ogahiy", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "ota_13", bolim: "Adabiyot: mumtoz", nom: "Muqimiy, Furqat, Zavqiy — XIX asr ma'rifatparvarlik adabiyoti", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_14", bolim: "Adabiyot: jadid davri", nom: "Fitrat, Cho'lpon, Behbudiy dramaturgiyasi va she'riyati", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_15", bolim: "Adabiyot: jadid davri", nom: "Abdulla Qodiriy: «O'tkan kunlar», «Mehrobdan chayon»", ulush: 0.047, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_16", bolim: "Adabiyot: XX asr", nom: "Oybek («Navoiy», «Qutlug' qon»), G'afur G'ulom, Hamid Olimjon, Zulfiya", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "ota_17", bolim: "Adabiyot: XX asr", nom: "Abdulla Qahhor hikoyalari va qissalari; Said Ahmad, Shukur Xolmirzayev", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_18", bolim: "Adabiyot: mustaqillik davri", nom: "Erkin Vohidov, Abdulla Oripov, O'tkir Hoshimov, Tog'ay Murod, Xurshid Davron", ulush: 0.038, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ota_19", bolim: "Adabiyot nazariyasi", nom: "Adabiy tur va janrlar; aruz va barmoq vazni; qofiya", ulush: 0.038, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "ota_20", bolim: "Adabiyot nazariyasi", nom: "Badiiy san'atlar (tashbeh, istiora, mubolag'a...), kompozitsiya, syujet, obraz", ulush: 0.028, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "ota_21", bolim: "Takrorlash", nom: "Asarlar mazmuni, iqtiboslar, mualliflar bo'yicha takrorlash", ulush: 0.009, bazaviy_soat: 8, qiyinlik: 0.5 }
  ]
};

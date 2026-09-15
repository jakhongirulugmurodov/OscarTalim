/* Mavzular: ona_tili. Ona tili — majburiy fan, 10 savol, koef. 1,1.
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.ona_tili = {
  fan: "ona_tili",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "ot_01", bolim: "Fonetika", nom: "Nutq tovushlari: unli va undoshlar, jarangli-jarangsiz, tovush o'zgarishlari", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "ot_02", bolim: "Fonetika", nom: "Bo'g'in, urg'u, tovush va harf munosabati; alifbo", ulush: 0.038, bazaviy_soat: 3, qiyinlik: 0.3 },
    { id: "ot_03", bolim: "Imlo", nom: "Unli va undoshlar imlosi; o', g', tutuq belgisi; bosh harflar", ulush: 0.057, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "ot_04", bolim: "Imlo", nom: "Qo'shma, juft va takroriy so'zlar imlosi; qo'shimchalar imlosi", ulush: 0.057, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "ot_05", bolim: "Leksikologiya", nom: "So'zning lug'aviy ma'nosi: bir va ko'p ma'nolilik, ko'chma ma'no", ulush: 0.038, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_06", bolim: "Leksikologiya", nom: "Sinonim, antonim, omonim, paronimlar", ulush: 0.047, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_07", bolim: "Leksikologiya", nom: "Frazeologizmlar, maqol va iboralar; lug'at turlari", ulush: 0.038, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_08", bolim: "Leksikologiya", nom: "So'zlarning kelib chiqishi va qo'llanish doirasi: sheva, kasb-hunar, eskirgan va yangi so'zlar", ulush: 0.028, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_09", bolim: "So'z yasalishi", nom: "So'z tarkibi: o'zak, asos, qo'shimchalar; so'z yasash usullari", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "ot_10", bolim: "Morfologiya", nom: "Ot: turlari, son, egalik, kelishik qo'shimchalari", ulush: 0.057, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ot_11", bolim: "Morfologiya", nom: "Sifat va son: ma'no turlari, darajalar, tuzilishi", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "ot_12", bolim: "Morfologiya", nom: "Olmosh turlari va ularning qo'llanishi", ulush: 0.038, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_13", bolim: "Morfologiya", nom: "Fe'l: nisbat, mayl, zamon, shaxs-son; harakat nomi", ulush: 0.065, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "ot_14", bolim: "Morfologiya", nom: "Sifatdosh, ravishdosh; ravish turlari", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.6 },
    { id: "ot_15", bolim: "Morfologiya", nom: "Yordamchi so'zlar: ko'makchi, bog'lovchi, yuklama; modal so'zlar, undov, taqlid", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "ot_16", bolim: "Sintaksis", nom: "So'z birikmasi: turlari, bog'lanish usullari", ulush: 0.038, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "ot_17", bolim: "Sintaksis", nom: "Gap bo'laklari: ega, kesim, to'ldiruvchi, aniqlovchi, hol", ulush: 0.057, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "ot_18", bolim: "Sintaksis", nom: "Sodda gap turlari: bir va ikki bosh bo'lakli, to'liqsiz gaplar; uyushiq va ajratilgan bo'laklar", ulush: 0.047, bazaviy_soat: 4, qiyinlik: 0.6 },
    { id: "ot_19", bolim: "Sintaksis", nom: "Qo'shma gap: bog'langan, bog'lovchisiz, ergashgan; ergash gap turlari", ulush: 0.057, bazaviy_soat: 5, qiyinlik: 0.7 },
    { id: "ot_20", bolim: "Sintaksis", nom: "Ko'chirma va o'zlashtirma gap; undalma, kirish so'zlar", ulush: 0.028, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "ot_21", bolim: "Punktuatsiya", nom: "Tinish belgilari: vergul, tire, ikki nuqta, qo'shtirnoq qoidalari", ulush: 0.038, bazaviy_soat: 4, qiyinlik: 0.6 },
    { id: "ot_22", bolim: "Uslubiyat va matn", nom: "Nutq uslublari; matn turlari va tuzilishi; mantiqiy urg'u", ulush: 0.028, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "ot_23", bolim: "Takrorlash", nom: "Aralash testlar bilan yakuniy takrorlash", ulush: 0.009, bazaviy_soat: 4, qiyinlik: 0.5 }
  ]
};

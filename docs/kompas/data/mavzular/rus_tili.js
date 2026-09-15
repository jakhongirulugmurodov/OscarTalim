/* Mavzular: rus_tili. Rus tili — ixtisoslik fani, 30 savol (mavzu nomlari o'zbek lotinida, mazmun — rus tili grammatikasi).
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.rus_tili = {
  fan: "rus_tili",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "rus_01", bolim: "Fonetika va orfoepiya", nom: "Tovushlar va harflar, urg'u me'yorlari, fonetik tahlil", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "rus_02", bolim: "Orfografiya", nom: "O'zakdagi unlilar: tekshiriladigan, tekshirilmaydigan, almashinuvchi (rast-rost, ber-bir...)", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "rus_03", bolim: "Orfografiya", nom: "Old qo'shimchalar (pre-/pri-, z/s bilan tugaydiganlar) va yumshatuv/ajratuv belgilari", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "rus_04", bolim: "Orfografiya", nom: "N va NN — sifat, sifatdosh va ravishlarda", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_05", bolim: "Orfografiya", nom: "NE va NI: so'z turkumlari bilan birga va alohida yozilishi", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_06", bolim: "Orfografiya", nom: "Shipyashchiy va TS dan keyin unlilar; qo'shma so'zlar, defis bilan yozilish", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "rus_07", bolim: "Leksika", nom: "So'z ma'nosi, sinonim, antonim, omonim, paronimlar; leksik me'yorlar", ulush: 0.037, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "rus_08", bolim: "Leksika", nom: "Frazeologizmlar; o'zlashgan, eskirgan va yangi so'zlar; uslubiy bo'yoq", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "rus_09", bolim: "Morfemika va so'z yasalishi", nom: "So'z tarkibi, so'z yasash usullari, morfemik tahlil", ulush: 0.037, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "rus_10", bolim: "Morfologiya", nom: "Ot: rod, son, kelishik, tuslanish turlari; tuslanmaydigan otlar", ulush: 0.047, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "rus_11", bolim: "Morfologiya", nom: "Sifat: razryadlar, darajalar, qisqa shakl; son: turlari va tuslanishi", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "rus_12", bolim: "Morfologiya", nom: "Olmosh razryadlari va imlosi", ulush: 0.028, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "rus_13", bolim: "Morfologiya", nom: "Fe'l: tur (vid), tuslanish, zamon, mayl, shaxs; fe'l qo'shimchalari imlosi", ulush: 0.057, bazaviy_soat: 7, qiyinlik: 0.6 },
    { id: "rus_14", bolim: "Morfologiya", nom: "Sifatdosh va ravishdosh: yasalishi, qo'shimchalari, o'ramlar", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_15", bolim: "Morfologiya", nom: "Ravish va holat kategoriyasi so'zlari; ravishlar imlosi", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "rus_16", bolim: "Morfologiya", nom: "Yordamchi so'z turkumlari: predlog, bog'lovchi, yuklama; ularning imlosi (tozhe/to zhe, chtoby...)", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_17", bolim: "Sintaksis", nom: "So'z birikmasi turlari: moslashuv, boshqaruv, bitishuv", ulush: 0.028, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "rus_18", bolim: "Sintaksis", nom: "Sodda gap: bosh bo'laklar, ega bilan kesim orasida tire, kesim turlari", ulush: 0.047, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "rus_19", bolim: "Sintaksis", nom: "Ikkinchi darajali bo'laklar; bir tarkibli gaplar turlari", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "rus_20", bolim: "Sintaksis", nom: "Uyushiq bo'laklar va umumlashtiruvchi so'zlar: tinish belgilari", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.6 },
    { id: "rus_21", bolim: "Sintaksis", nom: "Ajratilgan bo'laklar: sifatdosh va ravishdosh o'ramlari, izohlovchi, aniqlashtiruvchi", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_22", bolim: "Sintaksis", nom: "Kirish so'zlar va gaplar, murojaat, undov; ularning tinish belgilari", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "rus_23", bolim: "Sintaksis", nom: "Bog'langan qo'shma gap; ergashgan qo'shma gap turlari va tinish belgilari", ulush: 0.047, bazaviy_soat: 6, qiyinlik: 0.7 },
    { id: "rus_24", bolim: "Sintaksis", nom: "Bog'lovchisiz qo'shma gap: vergul, nuqtali vergul, ikki nuqta, tire", ulush: 0.037, bazaviy_soat: 5, qiyinlik: 0.7 },
    { id: "rus_25", bolim: "Sintaksis", nom: "Ko'chirma va o'zlashtirma gap, sitata, dialog", ulush: 0.019, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "rus_26", bolim: "Matn va uslub", nom: "Nutq uslublari va turlari; matn tuzilishi, asosiy fikr, bog'lanish vositalari", ulush: 0.028, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "rus_27", bolim: "Takrorlash", nom: "Aralash testlar, xato tahlili", ulush: 0.009, bazaviy_soat: 5, qiyinlik: 0.5 }
  ]
};

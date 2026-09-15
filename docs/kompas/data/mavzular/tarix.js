/* Mavzular: tarix. O'zbekiston tarixi — majburiy fan, 10 savol, koef. 1,1.
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.tarix = {
  fan: "tarix",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "tar_01", bolim: "Eng qadimgi davr", nom: "Ibtidoiy jamoa, tosh davri makonlari (Selung'ur, Teshiktosh, Obirahmat)", ulush: 0.020, bazaviy_soat: 3, qiyinlik: 0.3 },
    { id: "tar_02", bolim: "Eng qadimgi davr", nom: "Bronza va ilk temir davri, dehqonchilik madaniyatlari (Sopolli, Zamonbobo, Chust)", ulush: 0.020, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "tar_03", bolim: "Antik davr", nom: "Qadimgi davlatlar: Baqtriya, Xorazm, Sug'd; «Avesto» va zardushtiylik", ulush: 0.040, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_04", bolim: "Antik davr", nom: "Ahamoniylar hukmronligi, Iskandar yurishi, Salavkiylar va Yunon-Baqtriya", ulush: 0.030, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_05", bolim: "Antik davr", nom: "Qang', Dovon, Kushon podsholigi; Buyuk ipak yo'li", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_06", bolim: "Ilk o'rta asrlar", nom: "Eftaliylar va Turk xoqonligi davri", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "tar_07", bolim: "Ilk o'rta asrlar", nom: "Arablar istilosi, islomning tarqalishi, Muqanna qo'zg'oloni", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "tar_08", bolim: "Ilk o'rta asrlar", nom: "Somoniylar davlati; Qoraxoniylar va G'aznaviylar", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_09", bolim: "Ilk o'rta asrlar", nom: "Xorazmshohlar davlati; mo'g'ullar istilosi, Jaloliddin Manguberdi", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_10", bolim: "Ilk o'rta asrlar", nom: "Sharq Uyg'onish davri: Xorazmiy, Farg'oniy, Beruniy, Ibn Sino, Buxoriy", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.4 },
    { id: "tar_11", bolim: "Amir Temur va Temuriylar", nom: "Chig'atoy ulusi, sarbadorlar, Amir Temur davlatining tashkil topishi", ulush: 0.040, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_12", bolim: "Amir Temur va Temuriylar", nom: "Amir Temur yurishlari, davlat boshqaruvi, «Temur tuzuklari»", ulush: 0.060, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "tar_13", bolim: "Amir Temur va Temuriylar", nom: "Temuriylar: Shohrux, Ulug'bek, Husayn Boyqaro; Navoiy davri madaniyati", ulush: 0.060, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "tar_14", bolim: "Xonliklar davri", nom: "Shayboniylar davlati; Buxoro xonligi (Ashtarxoniylar)", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_15", bolim: "Xonliklar davri", nom: "Xiva va Qo'qon xonliklari; Buxoro amirligi (Mang'itlar)", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_16", bolim: "Mustamlaka davri", nom: "Chor Rossiyasining bosqini, Turkiston general-gubernatorligi", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.5 },
    { id: "tar_17", bolim: "Mustamlaka davri", nom: "Mustamlaka siyosati, iqtisodiy o'zgarishlar, 1916-yil qo'zg'oloni", ulush: 0.040, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "tar_18", bolim: "Mustamlaka davri", nom: "Jadidchilik harakati: Behbudiy, Fitrat, Avloniy, Munavvarqori", ulush: 0.040, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "tar_19", bolim: "Sovet davri", nom: "1917-yil inqiloblari, Turkiston muxtoriyati, istiqlolchilik harakati", ulush: 0.050, bazaviy_soat: 4, qiyinlik: 0.6 },
    { id: "tar_20", bolim: "Sovet davri", nom: "Milliy chegaralanish, kollektivlashtirish, qatag'onlar", ulush: 0.040, bazaviy_soat: 4, qiyinlik: 0.6 },
    { id: "tar_21", bolim: "Sovet davri", nom: "Ikkinchi jahon urushi yillarida O'zbekiston", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "tar_22", bolim: "Sovet davri", nom: "Urushdan keyingi davr: paxta yakkahokimligi, «paxta ishi», Orol fojiasi", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.5 },
    { id: "tar_23", bolim: "Mustaqillik", nom: "Mustaqillik e'lon qilinishi, Konstitutsiya, davlat ramzlari", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.3 },
    { id: "tar_24", bolim: "Mustaqillik", nom: "Islohotlar bosqichlari, Harakatlar strategiyasi, Yangi O'zbekiston", ulush: 0.030, bazaviy_soat: 3, qiyinlik: 0.4 },
    { id: "tar_25", bolim: "Mustaqillik", nom: "O'zbekistonning xalqaro aloqalari va tashkilotlardagi ishtiroki", ulush: 0.020, bazaviy_soat: 2, qiyinlik: 0.4 },
    { id: "tar_26", bolim: "Takrorlash", nom: "Sanalar, shaxslar va atamalar bo'yicha yakuniy takrorlash", ulush: 0.010, bazaviy_soat: 4, qiyinlik: 0.5 }
  ]
};

/* Mavzular: tarix_ix. Tarix — ixtisoslik fani, 30 savol: O'zbekiston tarixi (≈60%) + jahon tarixi (≈40%).
   ulush — imtihondagi savollar ulushi (Σ = 1.000), bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi).
   ishonch: ekspert_bahosi — DTM rasmiy test dasturi bilan solishtirilsin. 2026-09-15 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.tarix_ix = {
  fan: "tarix_ix",
  manba: "DTM test dasturi (umumta'lim maktab dasturi asosida)",
  mavzular: [
    { id: "trx_01", bolim: "O'zbekiston: qadimgi davr", nom: "Tosh, bronza va temir davri; ilk davlatlar, «Avesto»", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.4 },
    { id: "trx_02", bolim: "O'zbekiston: qadimgi davr", nom: "Ahamoniylar, Iskandar, Yunon-Baqtriya, Qang', Dovon, Kushonlar; Ipak yo'li", ulush: 0.050, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "trx_03", bolim: "O'zbekiston: o'rta asrlar", nom: "Eftaliylar, Turk xoqonligi, arablar istilosi", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_04", bolim: "O'zbekiston: o'rta asrlar", nom: "Somoniylar, Qoraxoniylar, G'aznaviylar, Xorazmshohlar, mo'g'ullar", ulush: 0.060, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "trx_05", bolim: "O'zbekiston: o'rta asrlar", nom: "Sharq Uyg'onish davri allomalari", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.4 },
    { id: "trx_06", bolim: "O'zbekiston: o'rta asrlar", nom: "Amir Temur va Temuriylar davlati, madaniyati", ulush: 0.070, bazaviy_soat: 9, qiyinlik: 0.5 },
    { id: "trx_07", bolim: "O'zbekiston: o'rta asrlar", nom: "Shayboniylar, Buxoro, Xiva, Qo'qon xonliklari", ulush: 0.060, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "trx_08", bolim: "O'zbekiston: yangi davr", nom: "Chor Rossiyasi bosqini va mustamlaka siyosati; jadidchilik", ulush: 0.060, bazaviy_soat: 8, qiyinlik: 0.5 },
    { id: "trx_09", bolim: "O'zbekiston: eng yangi davr", nom: "1917-yildan 1991-yilgacha: muxtoriyat, sovet davri, urush, qatag'on", ulush: 0.070, bazaviy_soat: 9, qiyinlik: 0.6 },
    { id: "trx_10", bolim: "O'zbekiston: eng yangi davr", nom: "Mustaqillik davri islohotlari va tashqi siyosat", ulush: 0.040, bazaviy_soat: 5, qiyinlik: 0.4 },
    { id: "trx_11", bolim: "Jahon: qadimgi dunyo", nom: "Qadimgi Sharq: Misr, Mesopotamiya, Hindiston, Xitoy", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_12", bolim: "Jahon: qadimgi dunyo", nom: "Qadimgi Yunoniston: polislar, demokratiya, madaniyat", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_13", bolim: "Jahon: qadimgi dunyo", nom: "Qadimgi Rim: respublika, imperiya, xristianlik", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_14", bolim: "Jahon: o'rta asrlar", nom: "G'arbiy Yevropada feodalizm, cherkov, salib yurishlari", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_15", bolim: "Jahon: o'rta asrlar", nom: "Arab xalifaligi va islom dunyosi; Vizantiya", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "trx_16", bolim: "Jahon: o'rta asrlar", nom: "O'rta asrlarda Osiyo: Xitoy, Hindiston, Usmoniylar, Rossiya", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "trx_17", bolim: "Jahon: yangi davr", nom: "Buyuk geografik kashfiyotlar, Uyg'onish, Reformatsiya", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_18", bolim: "Jahon: yangi davr", nom: "Angliya, AQSh va Fransiya inqiloblari; Napoleon urushlari", ulush: 0.050, bazaviy_soat: 8, qiyinlik: 0.6 },
    { id: "trx_19", bolim: "Jahon: yangi davr", nom: "Sanoat inqilobi; XIX asrda milliy davlatlar va mustamlakachilik", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_20", bolim: "Jahon: eng yangi davr", nom: "Birinchi jahon urushi va ikki urush oralig'idagi dunyo", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.6 },
    { id: "trx_21", bolim: "Jahon: eng yangi davr", nom: "Ikkinchi jahon urushi", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.5 },
    { id: "trx_22", bolim: "Jahon: eng yangi davr", nom: "Sovuq urush, dekolonizatsiya, zamonaviy dunyo", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.5 },
    { id: "trx_23", bolim: "Takrorlash", nom: "Xronologiya, xaritalar, shaxslar bo'yicha yakuniy takrorlash", ulush: 0.010, bazaviy_soat: 8, qiyinlik: 0.5 }
  ]
};

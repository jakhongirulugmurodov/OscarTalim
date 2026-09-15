/* Mavzular: fizika (faqat ixtisoslik fani, 30 savol; 1-fan koef. 3,1 / 2-fan koef. 2,1).
   ulush — DTM ixtisoslik testida shu mavzudan savol tushish ulushi (Σ = 1.000), 2021–2025 test variantlari tahlili
   asosidagi ekspert bahosi; DTM rasmiy test spetsifikatsiyasi bilan solishtirilsin (tekshirilsin).
   bazaviy_soat — 0 dan 0.95 o'zlashtirishgacha soat (repetitor tajribasi, o'rtacha o'quvchi). ishonch: ekspert_bahosi. 2026-09-14 */
window.KOMPAS_MAVZULAR = window.KOMPAS_MAVZULAR || {};
window.KOMPAS_MAVZULAR.fizika = {
  fan: "fizika",
  manba: "DTM test dasturi (umumta'lim maktab dasturi 6–11-sinf asosida)",
  mavzular: [
    /* ---- 1. Mexanika (6–7-sinf, 9-sinf) ---- */
    { id: "fiz_01", bolim: "Mexanika", nom: "Fizik kattaliklar va o'lchashlar: SI birliklari, ko'paytuvchi old qo'shimchalar, o'lchash xatoligi, skalyar va vektor kattaliklar", ulush: 0.012, bazaviy_soat: 3, qiyinlik: 0.30 },
    { id: "fiz_02", bolim: "Mexanika", nom: "Kinematika asoslari: mexanik harakat, sanoq sistemasi, tekis to'g'ri chiziqli harakat, o'rtacha tezlik, harakat grafiklari",   ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.35 },
    { id: "fiz_03", bolim: "Mexanika", nom: "Tekis o'zgaruvchan harakat: tezlanish, tezlik va ko'chish tenglamalari, erkin tushish, vertikal otilgan jism",                 ulush: 0.045, bazaviy_soat: 7, qiyinlik: 0.45 },
    { id: "fiz_04", bolim: "Mexanika", nom: "Gorizontal va burchak ostida otilgan jism harakati, harakatlarni qo'shish (harakatning nisbiyligi)",                              ulush: 0.018, bazaviy_soat: 5, qiyinlik: 0.60 },
    { id: "fiz_05", bolim: "Mexanika", nom: "Aylana bo'ylab tekis harakat: burchak tezlik, davr va chastota, markazga intilma tezlanish, uzatmalar",                       ulush: 0.025, bazaviy_soat: 4, qiyinlik: 0.45 },
    { id: "fiz_06", bolim: "Mexanika", nom: "Nyuton qonunlari: inersial sanoq sistemalari, massa va kuch, kuchlarni qo'shish, ta'sir va aks ta'sir",                      ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.50 },
    { id: "fiz_07", bolim: "Mexanika", nom: "Tabiatdagi kuchlar: butun olam tortishish qonuni, og'irlik kuchi va vaznsizlik, elastiklik kuchi (Guk qonuni), ishqalanish", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.50 },
    { id: "fiz_08", bolim: "Mexanika", nom: "Dinamika qonunlarini qo'llash: qiya tekislik, bog'langan jismlar, lift, sun'iy yo'ldoshlar va kosmik tezliklar",             ulush: 0.025, bazaviy_soat: 7, qiyinlik: 0.65 },
    { id: "fiz_09", bolim: "Mexanika", nom: "Statika: kuch momenti, richag va blok, jismning muvozanat shartlari, og'irlik markazi, sodda mexanizmlar",                    ulush: 0.020, bazaviy_soat: 4, qiyinlik: 0.45 },
    { id: "fiz_10", bolim: "Mexanika", nom: "Jism impulsi va kuch impulsi, impulsning saqlanish qonuni, elastik va noelastik to'qnashuv, reaktiv harakat",                 ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.55 },
    { id: "fiz_11", bolim: "Mexanika", nom: "Mexanik ish, quvvat va FIK, kinetik va potensial energiya, mexanik energiyaning saqlanish qonuni",                            ulush: 0.035, bazaviy_soat: 7, qiyinlik: 0.55 },
    { id: "fiz_12", bolim: "Mexanika", nom: "Suyuqlik va gazlar mexanikasi: bosim, Paskal qonuni, gidrostatik va atmosfera bosimi, Arximed kuchi, jismlarning suzish shartlari", ulush: 0.015, bazaviy_soat: 5, qiyinlik: 0.45 },

    /* ---- 2. Molekulyar fizika va termodinamika (8-sinf, 10-sinf) ---- */
    { id: "fiz_13", bolim: "Molekulyar fizika va termodinamika", nom: "MKN asoslari: modda miqdori, Avogadro soni, molekulalar tezligi, ideal gaz MKNning asosiy tenglamasi, temperatura", ulush: 0.030, bazaviy_soat: 5, qiyinlik: 0.50 },
    { id: "fiz_14", bolim: "Molekulyar fizika va termodinamika", nom: "Ideal gaz holat tenglamasi (Mendeleyev–Klapeyron), izojarayonlar va ularning grafiklari, gaz aralashmalari (Dalton qonuni)", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "fiz_15", bolim: "Molekulyar fizika va termodinamika", nom: "Agregat holatlar: bug'lanish va qaynash, to'yingan bug', havo namligi, erish va kristallanish, issiqlik balansi tenglamasi", ulush: 0.025, bazaviy_soat: 5, qiyinlik: 0.50 },
    { id: "fiz_16", bolim: "Molekulyar fizika va termodinamika", nom: "Suyuqlik va qattiq jism xossalari: sirt taranglik, kapillyar hodisalar, deformatsiya va Guk qonuni (Yung moduli), issiqlikdan kengayish", ulush: 0.015, bazaviy_soat: 4, qiyinlik: 0.50 },
    { id: "fiz_17", bolim: "Molekulyar fizika va termodinamika", nom: "Termodinamika asoslari: ichki energiya, gazning ishi, issiqlik miqdori, termodinamikaning I qonuni va izojarayonlarga tatbiqi, adiabatik jarayon", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.60 },
    { id: "fiz_18", bolim: "Molekulyar fizika va termodinamika", nom: "Issiqlik dvigatellari va ularning FIK, Karno sikli, termodinamikaning II qonuni, sovitish mashinalari", ulush: 0.015, bazaviy_soat: 3, qiyinlik: 0.50 },

    /* ---- 3. Elektr va magnetizm (8-sinf, 10-sinf) ---- */
    { id: "fiz_19", bolim: "Elektr va magnetizm", nom: "Elektrostatika: zaryadning saqlanish qonuni, Kulon qonuni, elektr maydon kuchlanganligi, superpozitsiya prinsipi, kuch chiziqlari", ulush: 0.040, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "fiz_20", bolim: "Elektr va magnetizm", nom: "Maydon ishi va potensial, kuchlanish, o'tkazgich va dielektriklar elektr maydonda, kondensatorlar va ularni ulash, maydon energiyasi", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.60 },
    { id: "fiz_21", bolim: "Elektr va magnetizm", nom: "O'zgarmas tok: tok kuchi, zanjir qismi uchun Om qonuni, o'tkazgich qarshiligi, ketma-ket va parallel ulash, ampermetr va voltmetr", ulush: 0.050, bazaviy_soat: 7, qiyinlik: 0.50 },
    { id: "fiz_22", bolim: "Elektr va magnetizm", nom: "Tok ishi va quvvati, Joul–Lens qonuni, tok manbai EYK, to'la zanjir uchun Om qonuni, manbalarni ulash", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "fiz_23", bolim: "Elektr va magnetizm", nom: "Elektr toki turli muhitlarda: metallar, elektrolitlar (Faradey qonunlari), gazlar, vakuum, yarimo'tkazgichlar (p-n o'tish)", ulush: 0.020, bazaviy_soat: 4, qiyinlik: 0.50 },
    { id: "fiz_24", bolim: "Elektr va magnetizm", nom: "Magnit maydon: magnit induksiya, Amper kuchi, Lorens kuchi, zaryadli zarraning magnit maydondagi harakati, moddaning magnit xossalari", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.60 },
    { id: "fiz_25", bolim: "Elektr va magnetizm", nom: "Elektromagnit induksiya: magnit oqimi, Faradey qonuni, Lens qoidasi, harakatlanuvchi o'tkazgichdagi EYK, o'zinduksiya, induktivlik, magnit maydon energiyasi", ulush: 0.035, bazaviy_soat: 6, qiyinlik: 0.60 },

    /* ---- 4. Tebranish va to'lqinlar (9-sinf, 11-sinf) ---- */
    { id: "fiz_26", bolim: "Tebranish va to'lqinlar", nom: "Mexanik tebranishlar: garmonik tebranish tenglamasi, matematik va prujinali mayatnik, tebranish energiyasi, so'nuvchi va majburiy tebranishlar, rezonans", ulush: 0.030, bazaviy_soat: 6, qiyinlik: 0.55 },
    { id: "fiz_27", bolim: "Tebranish va to'lqinlar", nom: "Mexanik to'lqinlar va tovush: ko'ndalang va bo'ylama to'lqin, to'lqin uzunligi va tezligi, tovush balandligi va kuchi, aks sado", ulush: 0.015, bazaviy_soat: 3, qiyinlik: 0.45 },
    { id: "fiz_28", bolim: "Tebranish va to'lqinlar", nom: "Elektromagnit tebranishlar va o'zgaruvchan tok: tebranish konturi, Tomson formulasi, effektiv qiymatlar, aktiv, sig'im va induktiv qarshilik, transformator, energiya uzatish", ulush: 0.030, bazaviy_soat: 6, qiyinlik: 0.65 },
    { id: "fiz_29", bolim: "Tebranish va to'lqinlar", nom: "Elektromagnit to'lqinlar: xossalari va tarqalish tezligi, elektromagnit to'lqinlar shkalasi, radioaloqa va radiolokatsiya asoslari", ulush: 0.010, bazaviy_soat: 2, qiyinlik: 0.45 },

    /* ---- 5. Optika (8-sinf, 11-sinf) ---- */
    { id: "fiz_30", bolim: "Optika", nom: "Yorug'lik manbalari va fotometriya (yorug'lik kuchi, oqimi, yoritilganlik), to'g'ri chiziqli tarqalish, soya, qaytish qonuni, yassi ko'zgu", ulush: 0.025, bazaviy_soat: 5, qiyinlik: 0.45 },
    { id: "fiz_31", bolim: "Optika", nom: "Yorug'likning sinishi: sindirish qonuni, to'la ichki qaytish, prizma; linzalar, yupqa linza formulasi, kattalashtirish, tasvir yasash, optik asboblar va ko'z", ulush: 0.040, bazaviy_soat: 8, qiyinlik: 0.60 },
    { id: "fiz_32", bolim: "Optika", nom: "To'lqin optikasi: yorug'lik interferensiyasi va difraksiyasi (difraksion panjara), dispersiya, qutblanish", ulush: 0.020, bazaviy_soat: 5, qiyinlik: 0.65 },
    { id: "fiz_33", bolim: "Optika", nom: "Yorug'lik tezligi va maxsus nisbiylik nazariyasi elementlari: postulatlar, vaqt va uzunlikning nisbiyligi, massa va energiya bog'lanishi", ulush: 0.010, bazaviy_soat: 3, qiyinlik: 0.60 },

    /* ---- 6. Atom va yadro fizikasi (11-sinf) ---- */
    { id: "fiz_34", bolim: "Atom va yadro fizikasi", nom: "Kvant fizikasi: issiqlik nurlanishi, fotoeffekt va Eynshteyn tenglamasi, foton energiyasi va impulsi, yorug'lik bosimi, korpuskulyar-to'lqin dualizmi", ulush: 0.025, bazaviy_soat: 5, qiyinlik: 0.60 },
    { id: "fiz_35", bolim: "Atom va yadro fizikasi", nom: "Atom tuzilishi: Rezerford tajribasi, Bor postulatlari, vodorod atomi spektri va energiya sathlari, lazerlar", ulush: 0.015, bazaviy_soat: 4, qiyinlik: 0.60 },
    { id: "fiz_36", bolim: "Atom va yadro fizikasi", nom: "Atom yadrosi: proton-neytron tuzilishi, izotoplar, yadro kuchlari, massa defekti va bog'lanish energiyasi", ulush: 0.015, bazaviy_soat: 4, qiyinlik: 0.60 },
    { id: "fiz_37", bolim: "Atom va yadro fizikasi", nom: "Radioaktivlik va yadro reaksiyalari: alfa-, beta-, gamma-yemirilish, siljish qoidasi, yarim yemirilish davri, yadroning bo'linishi va sintezi, elementar zarralar", ulush: 0.025, bazaviy_soat: 5, qiyinlik: 0.55 }
  ]
};

/* Stagger Text — host tomoni (ExtendScript).
 *
 * MUHIM: bu fayl ES3 muhitida ishlaydi. Premiere'ning ExtendScript
 * dvigateli 1999-yilgi JavaScript'ni tushunadi, xolos:
 *   - arrow function YO'Q, faqat function
 *   - let/const YO'Q, faqat var
 *   - template literal YO'Q, faqat "matn" + qiymat
 *   - forEach/map YO'Q, faqat oddiy for
 *   - JSON obyekti YO'Q
 * Bittasini ishlatsangiz skript jimgina yuklanmay qoladi va panel
 * evalScript'dan "EvalScript error." oladi.
 */

/* Tanlangan kliplarni yig'ib beradigan ichki yordamchi.
 * Xato bo'lsa {xato: "..."}, bo'lmasa {kliplar: [...]} qaytaradi. */
function __tanlanganKliplar() {
  var natija = { xato: null, kliplar: [] };

  if (!app || !app.project) {
    natija.xato = "Premiere loyihasi topilmadi";
    return natija;
  }
  var seq = app.project.activeSequence;
  if (!seq) {
    natija.xato = "Ochiq sequence yo'q — avval montajni oching";
    return natija;
  }

  var i, k, trek, klip;
  for (i = 0; i < seq.videoTracks.numTracks; i++) {
    trek = seq.videoTracks[i];
    for (k = 0; k < trek.clips.numItems; k++) {
      klip = trek.clips[k];
      /* isSelected — metod; ba'zi versiyalarda xossa bo'lib qoladi,
         ikkalasini ham qabul qilamiz */
      var tanlangan = false;
      if (typeof klip.isSelected === "function") {
        tanlangan = klip.isSelected();
      } else {
        tanlangan = !!klip.isSelected;
      }
      if (tanlangan) {
        natija.kliplar[natija.kliplar.length] = klip;
      }
    }
  }

  if (natija.kliplar.length === 0) {
    natija.xato = "Birorta klip tanlanmagan — timeline'da klip(lar)ni "
                + "belgilang";
  }
  return natija;
}

/* Panel chaqiradigan funksiya: tanlov borligini tekshiradi. */
function getSelectedClips() {
  var r = __tanlanganKliplar();
  if (r.xato) {
    return "ERR: " + r.xato;
  }
  return "OK: " + r.kliplar.length + " ta klip tanlangan";
}

/* Komponentlar ichidan nomi bo'yicha xususiyatni topadi.
 * Position "Motion" komponentida, Opacity esa alohida "Opacity"
 * komponentida yashaydi — shuning uchun hammasi bo'ylab qidiramiz. */
function __xususiyatTop(klip, nomi) {
  var i, k, komp, xus;
  if (!klip.components) {
    return null;
  }
  for (i = 0; i < klip.components.numItems; i++) {
    komp = klip.components[i];
    for (k = 0; k < komp.properties.numItems; k++) {
      xus = komp.properties[k];
      if (xus.displayName === nomi) {
        return xus;
      }
    }
  }
  return null;
}

/* Bitta xususiyatga ikki keyframe qo'yadi.
 * Tartib ataylab shunday: addKey -> setValueAtKey -> interpolatsiya.
 * setInterpolationTypeAtKey(vaqt, 2, true) — 2 bu bezier. */
function __ikkiKey(xus, t0, q0, t1, q1) {
  xus.setTimeVarying(true);

  xus.addKey(t0);
  xus.setValueAtKey(t0, q0, true);

  xus.addKey(t1);
  xus.setValueAtKey(t1, q1, true);

  if (typeof xus.setInterpolationTypeAtKey === "function") {
    xus.setInterpolationTypeAtKey(t0, 2, true);
    xus.setInterpolationTypeAtKey(t1, 2, true);
  }
}

/* Asosiy amal: har tanlangan klipga pastdan suzib chiqish + fade.
 *
 * durationSec — harakat davomiyligi (soniya)
 * distancePx  — necha piksel pastdan boshlanadi (1080p o'lchovida)
 */
function applyFadeUp(durationSec, distancePx) {
  var dur = parseFloat(durationSec);
  var px = parseFloat(distancePx);
  if (!(dur > 0)) {
    return "ERR: davomiylik musbat son bo'lishi kerak";
  }
  if (!(px >= 0)) {
    return "ERR: masofa manfiy bo'lmasligi kerak";
  }

  var r = __tanlanganKliplar();
  if (r.xato) {
    return "ERR: " + r.xato;
  }

  var qollandi = 0;
  var otkazildi = 0;
  var i, klip, pos, op, t0, t1, tOp;

  for (i = 0; i < r.kliplar.length; i++) {
    klip = r.kliplar[i];

    pos = __xususiyatTop(klip, "Position");
    op = __xususiyatTop(klip, "Opacity");
    if (!pos || !op) {
      /* Grafika bo'lmagan yoki Motion'siz klip — indamay tashlab
         ketmaymiz, oxirida soni aytiladi */
      otkazildi++;
      continue;
    }

    t0 = klip.start.seconds;
    t1 = t0 + dur;

    /* Opacity harakatdan OLDIN tugashi shart — bu qasddan: matn avval
       ko'rinib bo'ladi, keyin joyiga "o'tirib" tugatadi. Shu sabab
       opacity o'z yo'lini davomiylikning 65% ida bosib bo'ladi. */
    tOp = t0 + dur * 0.65;

    /* Position normalized 0..1 qiymatda ishlaydi: [0.5, 0.5] — markaz.
       distancePx piksel 1080 balandlikka nisbatan ulushga aylantiriladi. */
    __ikkiKey(pos, t0, [0.5, 0.5 + px / 1080], t1, [0.5, 0.5]);
    __ikkiKey(op, t0, 0, tOp, 100);

    qollandi++;
  }

  if (qollandi === 0) {
    return "ERR: birorta klipga qo'llanmadi — tanlanganlarda "
         + "Position/Opacity topilmadi (" + otkazildi + " ta o'tkazildi)";
  }

  var xabar = "OK: " + qollandi + " ta klipga qo'llandi";
  if (otkazildi > 0) {
    xabar = xabar + " (" + otkazildi + " tasida Position/Opacity yo'q — "
          + "o'tkazib yuborildi)";
  }
  return xabar;
}

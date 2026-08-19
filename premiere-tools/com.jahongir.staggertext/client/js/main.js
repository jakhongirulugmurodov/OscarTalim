/* Stagger Text — panel tomoni.
 * Bu fayl CEP'ning Chromium muhitida ishlaydi (zamonaviy JS mumkin),
 * ES3 cheklovi faqat host/index.jsx ga tegishli. */

(function () {
  "use strict";

  var natija = document.getElementById("natija");
  var tugma = document.getElementById("apply");

  function korsat(matn, xatomi) {
    natija.textContent = matn;
    natija.className = xatomi ? "xato" : "ok";
  }

  /* CSInterface.js hali almashtirilmagan bo'lsa — aniq aytamiz,
     jim turib qolmaymiz */
  if (window.__csinterface_yoq) {
    korsat("CSInterface.js topilmadi. client/js/CSInterface.js faylini "
         + "Adobe'dan yuklab almashtiring — yo'l INSTALL.md da.", true);
    tugma.disabled = true;
    return;
  }

  var cs = new CSInterface();

  tugma.addEventListener("click", function () {
    var dur = parseFloat(document.getElementById("dur").value);
    var dist = parseFloat(document.getElementById("dist").value);

    if (!(dur > 0)) {
      korsat("Davomiylik musbat son bo'lishi kerak", true);
      return;
    }
    if (!(dist >= 0)) {
      korsat("Masofa manfiy bo'lmasligi kerak", true);
      return;
    }

    tugma.disabled = true;
    korsat("Qo'llanmoqda…", false);

    /* Avval tanlov borligini tekshiramiz — xato xabari aniqroq chiqadi */
    cs.evalScript("getSelectedClips()", function (tekshiruv) {
      if (typeof tekshiruv === "string" && tekshiruv.indexOf("ERR:") === 0) {
        korsat(tekshiruv.substring(4).replace(/^\s+/, ""), true);
        tugma.disabled = false;
        return;
      }
      if (tekshiruv === "EvalScript error.") {
        korsat("Host skript yuklanmadi — Premiere'ni qayta oching. "
             + "Takrorlansa, host/index.jsx da sintaksis xatosi bor.", true);
        tugma.disabled = false;
        return;
      }

      cs.evalScript("applyFadeUp(" + dur + "," + dist + ")", function (r) {
        tugma.disabled = false;
        if (typeof r !== "string") {
          korsat("Kutilmagan javob keldi", true);
          return;
        }
        if (r.indexOf("OK:") === 0) {
          korsat(r.substring(3).replace(/^\s+/, ""), false);
        } else if (r.indexOf("ERR:") === 0) {
          korsat(r.substring(4).replace(/^\s+/, ""), true);
        } else if (r === "EvalScript error.") {
          korsat("Skript xatosi — host/index.jsx bajarilmadi", true);
        } else {
          korsat(r, true);
        }
      });
    });
  });
})();

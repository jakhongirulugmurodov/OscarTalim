/* Podcast Suite — panel mantiqi (Sync, Cut, Switch, Intro, Captions, Shorts).
 *
 * Panel o'zi hech qanday og'ir ish qilmaydi: fayllarni tanlatadi,
 * lokal motorga (server.py, 127.0.0.1:8765) yuboradi, natijani
 * ko'rsatadi va tayyor XML'ni Premiere loyihasiga import qiladi.
 */

/* Motor manzili. UXP ba'zi holatlarda 127.0.0.1 ni bloklaydi, shuning uchun
 * ikkala shaklni ham sinab ko'ramiz va ishlaganini eslab qolamiz. */
/* Panel qurilgan vaqt. Panel qayta yuklanmagan bo'lsa, bu yerda eski
 * sana turadi — «yangi kod o'rnatildimi?» degan savol shu bilan hal bo'ladi. */
const PANEL_BUILD = "31-Jul 08:30";

const MOTOR_URLS = ["http://127.0.0.1:8765", "http://localhost:8765"];
let MOTOR = MOTOR_URLS[0];
let lastMotorError = "";

const uxp = require("uxp");
const lfs = uxp.storage.localFileSystem;

/* Element topilmasa — bo'sh o'rinbosar qaytadi, shunda panel hech qachon
 * qulamaydi (masalan index.html eski versiyada qolib ketgan bo'lsa ham). */
function el(id) {
  return document.getElementById(id) || document.createElement("div");
}

const els = {
  motor: el("motor"),
  motorTxt: el("motorTxt"),
  pick: el("pick"),
  files: el("files"),
  log: el("log"),
  syncBtn: el("syncBtn"),
  cutBtn: el("cutBtn"),
  switchBtn: el("switchBtn"),
  capBtn: el("capBtn"),
  sampleBtn: el("sampleBtn"),
  capWarn: el("capWarn"),
  body: document.querySelector(".body") || document.createElement("div"),
  job: el("job"),
  jobStage: el("jobStage"),
  jobStep: el("jobStep"),
  jobFill: el("jobFill"),
  jobSeg: el("jobSeg"),
  jobTicks: el("jobTicks"),
  jobChips: el("jobChips"),
  jobPulse: el("jobPulse"),
  jobDetail: el("jobDetail"),
  jobElapsed: el("jobElapsed"),
  jobEta: el("jobEta"),
  capSearch: el("capSearch"),
  capSearchBtn: el("capSearchBtn"),
  introBtn: el("introBtn"),
  buildBtn: el("buildBtn"),
  reviewBtn: el("reviewBtn"),
  shortsBtn: el("shortsBtn"),
  shortsBuildBtn: el("shortsBuildBtn"),
  markerBtn: el("markerBtn"),
  shortsList: el("shortsList"),
  staleBar: el("staleBar"),
  staleTxt: el("staleTxt"),
  logBar: el("logBar"),
  logCopy: el("logCopy"),
  logBig: el("logBig"),
  moments: el("moments"),
  matnPanel: el("matnPanel"),
  matnList: el("matnList"),
  matnAdd: el("matnAdd"),
  matnBtn: el("matnBtn"),
  matnPreview: el("matnPreview"),
  matnPrevHint: el("matnPrevHint"),
  mFont: el("mFont"),
  mSize: el("mSize"),
  mPos: el("mPos"),
  mBold: el("mBold"),
  seqBtn: el("seqBtn"),
  seqTitle: el("seqTitle"),
  seqHint: el("seqHint"),
  pickHint: el("pickHint"),
  importBtn: el("importBtn"),
  hint: el("hint"),
  diagBtn: document.getElementById("diagBtn"),
  updBtn: el("updBtn"),
};

let picked = [];   // [{name, path}]
let lastXml = null;
let whisperReady = true;   // motor aytmaguncha to'sqinlik qilmaymiz

/* ---------------------------------------------------- motor holati */

async function checkMotor() {
  const errors = [];
  for (const base of MOTOR_URLS) {
    try {
      const r = await fetch(base + "/health");
      const j = await r.json();
      if (j.ok) {
        MOTOR = base;
        markModels(j.models);
        // whisper.cpp yo'qligi faqat tugmani bosgandan keyin bilinardi —
        // endi Captions tabining tepasida turadi va tugma ochilmaydi.
        checkPanelFresh(j.panel_build);
        whisperReady = j.whisper !== false;
        els.capWarn.classList.toggle("show", !whisperReady);
        if (!pollTimer) updateRunButtons();
        els.motor.classList.add("ok");
        els.motorTxt.textContent = j.ffmpeg === false
          ? "Motor ishlayapti, lekin ffmpeg yo'q — motorni-yoqish.command ni ishlating"
          : "Motor v" + j.version + " · panel " + PANEL_BUILD;
        els.motorTxt.title = "Panel kodi: " + PANEL_BUILD
          + " — Unload/Load qilinsa shu sana yangilanadi";
        return true;
      }
    } catch (e) {
      errors.push(base.replace("http://", "") + ": " + (e.message || e));
    }
  }
  lastMotorError = errors.join(" · ");
  els.motor.classList.remove("ok");
  // Ruxsat xatosi va «motor o'chiq» — butunlay boshqa muammolar, ajratib ko'rsatamiz
  // «Manifest entry not found» — UXP panelni qayta yuklaganda tarmoq
  // ruxsatini yo'qotgan. Reload yetmaydi, Unload + Load kerak.
  const denied = /permission|denied|manifest/i.test(lastMotorError);
  els.motorTxt.textContent = denied
    ? "Motorga ruxsat berilmadi — UDT'da ••• > Unload, so'ng Load & Watch "
      + "(Reload yetmaydi). Motorning o'zi ishlab turibdi."
    : "Motor topilmadi — motorni yoqing (motorni-yoqish.command)";
  els.motorTxt.title = lastMotorError;
  return false;
}

/* Panel diskdagi kod bilan bir xilmi?
 *
 * Premiere panel kodini xotirada ushlab qoladi: git pull diskni yangilaydi,
 * panel esa eskisini ishlatib turaveradi. Shu holat bir necha marta
 * «tuzatilgan xato yana chiqdi» degan chalkashlikka olib keldi. Endi panel
 * o'zini bir marta qayta yuklaydi; shundan keyin ham farq qolsa — ekranda
 * qizil ogohlantirish turadi. */
/* Bir marta urinilganini eslab qolamiz. Diskdagi versiya kaliti bilan
 * saqlanadi: qayta yuklash yordam bermasa (UXP eski nusxani keshda ushlab
 * turgan bo'lsa) — cheksiz aylanish bo'lmaydi, faqat ogohlantirish qoladi. */
function reloadFlag(diskBuild, set) {
  const key = "psPanelReload:" + diskBuild;
  try {
    if (set) { localStorage.setItem(key, "1"); return true; }
    return localStorage.getItem(key) === "1";
  } catch (e) {
    // localStorage bo'lmasa — hech bo'lmasa shu sessiyada bir marta
    window.__psReload = window.__psReload || {};
    if (set) { window.__psReload[key] = 1; return true; }
    return !!window.__psReload[key];
  }
}

function checkPanelFresh(diskBuild) {
  if (!diskBuild || diskBuild === PANEL_BUILD) {
    els.staleBar.classList.remove("show");
    return true;
  }
  els.staleTxt.textContent = "Panelda: " + PANEL_BUILD + " · diskda: "
                           + diskBuild + " — yangi kod yuklanishi kerak";
  els.staleBar.classList.add("show");
  if (!reloadFlag(diskBuild, false)) {
    reloadFlag(diskBuild, true);
    logLine("Diskda yangi panel kodi bor (" + diskBuild + ") — panel o'zini "
            + "qayta yuklaydi…", "warn");
    setTimeout(() => { try { location.reload(); } catch (e) { /* qo'lda */ } }, 700);
  }
  return false;
}

/* ------------------------------------------------- yangilanish tekshiruvi */

async function checkUpdates() {
  try {
    const r = await fetch(MOTOR + "/version");
    const j = await r.json();
    if (j.git && j.updates > 0) {
      els.motor.classList.add("hasupd");
      els.updBtn.textContent = "Yangilash (" + j.updates + ")";
    } else {
      els.motor.classList.remove("hasupd");
    }
  } catch (e) { /* motor o'chiq — indikator o'zi aytadi */ }
}

async function doUpdate() {
  els.log.innerHTML = "";
  logLine("Yangilanish yuklanmoqda…");
  try {
    const r = await fetch(MOTOR + "/update", { method: "POST" });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error || "yangilanmadi");
    logLine("Yangilandi: " + j.current, "okline");
    logLine("Motor qayta ishga tushmoqda…");
    els.motor.classList.remove("hasupd");
    // Motor qaytishini kutamiz, so'ng panelni yangi kod bilan qayta ochamiz
    for (let i = 0; i < 20; i++) {
      await new Promise((res) => setTimeout(res, 1000));
      if (await checkMotor()) {
        logLine("Tayyor ✓ Panel yangilanmoqda…", "okline");
        setTimeout(() => location.reload(), 800);
        return;
      }
    }
    logLine("Motor qaytmadi — motorni-yoqish.command ni ishlating", "warn");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
  }
}

/* Tashxis: aniq xato matnini log oynasida ko'rsatadi */
async function showDiagnostics() {
  els.log.innerHTML = "";
  logLine("Tashxis:");
  for (const base of MOTOR_URLS) {
    try {
      const r = await fetch(base + "/health");
      const j = await r.json();
      logLine("  " + base + " → OK, v" + j.version, "okline");
    } catch (e) {
      logLine("  " + base + " → " + (e.message || e), "warn");
    }
  }
}

/* ---------------------------------------------------- fayl tanlash */

async function pickFiles() {
  const files = await lfs.getFileForOpening({ allowMultiple: true });
  if (!files) return;
  const list = Array.isArray(files) ? files : [files];
  timeline = null;   // qo'lda tanlansa — sequence rejimidan chiqamiz
  seqFormat = null;
  for (const f of list) {
    if (f && f.nativePath && !picked.some((p) => p.path === f.nativePath)) {
      picked.push({ name: f.name, path: f.nativePath });
    }
  }
  renderFiles();
}

function renderFiles(results) {
  // Ovoz manbasi ro'yxatdan olib tashlangan bo'lsa — eski yo'l qolib ketmasin
  if (audioMaster && !picked.some((p) => p.path === audioMaster)) audioMaster = null;
  els.files.innerHTML = "";
  for (const p of picked) {
    const row = document.createElement("div");
    row.className = "file";

    const nm = document.createElement("span");
    nm.className = "nm";
    nm.textContent = p.name;
    row.appendChild(nm);

    const res = results && results.find((c) => c.path === p.path);
    if (res) {
      const off = document.createElement("span");
      const bad = res.reliable === false;
      off.className = bad ? "off bad" : "off";
      off.textContent = res.is_reference ? "tayanch"
        : bad ? "mos kelmadi"
        : "+" + res.offset_sec.toFixed(3) + "s";
      row.appendChild(off);
      if (!res.is_reference) {
        const conf = document.createElement("span");
        conf.className = "conf";
        conf.textContent = res.confidence.toFixed(1) + "×";
        row.appendChild(conf);
        if (bad) row.classList.add("badrow");
      }
    } else {
      if (activeTab === "switch") {
        const r = roleOf(p, picked.indexOf(p));
        const pill = document.createElement("span");
        pill.className = "role " + r.cls;
        pill.textContent = r.label;
        pill.addEventListener("click", () => cycleRole(p, picked.indexOf(p)));
        row.appendChild(pill);
      }
      // Ovoz manbasi — vazifadan alohida: Switch'da kamera almashsa ham ovoz
      // shundan keladi, Captions'da esa aynan shu fayl matnga aylanadi.
      if (activeTab === "switch" || activeTab === "captions") {
        const isMaster = audioMaster === p.path;
        const snd = document.createElement("span");
        snd.className = "snd" + (isMaster ? " on" : "");
        snd.textContent = isMaster ? "♪ ovoz manbasi" : "♪ ovoz?";
        snd.title = isMaster
          ? "Ovoz shu fayldan olinadi — bekor qilish uchun bosing"
          : activeTab === "captions"
          ? "Subtitr shu faylning ovozidan yozilsin"
          : "Ovoz shu fayldan olinsin (yaxshi yozilgani)";
        snd.addEventListener("click", () => {
          audioMaster = isMaster ? null : p.path;
          renderFiles();
        });
        row.appendChild(snd);
      }
      const rm = document.createElement("span");
      rm.className = "rm";
      rm.textContent = "✕";
      rm.addEventListener("click", () => {
        picked = picked.filter((x) => x !== p);
        renderFiles();
      });
      row.appendChild(rm);
    }
    els.files.appendChild(row);
  }
  els.hint.textContent = picked.length + " fayl";
  updateRunButtons();
}

/* ------------------------------------------- kamera vazifalari (Switch) */

/* Har fayl uchun vazifa: pill bosilganda navbatdagisiga o'tadi.
 * Spikerlar avtomatik raqamlanadi — birinchi fayl 1-spiker va hokazo. */
let roles = {};        // path -> {role, sid, label}
let audioMaster = null;  // ovozi ishlatiladigan fayl yo'li (vazifadan mustaqil)

function roleOptions() {
  const n = Math.max(picked.length, 1);
  const out = [];
  for (let i = 0; i < n; i++)
    out.push({ role: "speaker", sid: i, label: "Spiker " + (i + 1), cls: "speaker" });
  out.push({ role: "wide", sid: null, label: "Keng plan", cls: "wide" });
  for (let i = 0; i < n; i++)
    out.push({ role: "alt", sid: i, label: "Rakurs " + (i + 1), cls: "alt" });
  out.push({ role: "insert", sid: null, label: "Detal", cls: "insert" });
  return out;
}

function defaultRole(index) {
  const opts = roleOptions();
  return opts[Math.min(index, opts.length - 1)];
}

function roleOf(p, index) {
  if (!roles[p.path]) roles[p.path] = defaultRole(index);
  return roles[p.path];
}

function cycleRole(p, index) {
  const opts = roleOptions();
  const cur = roleOf(p, index);
  let at = opts.findIndex((o) => o.role === cur.role && o.sid === cur.sid);
  roles[p.path] = opts[(at + 1) % opts.length];
  renderFiles();
}

/* ------------------------------------------------------------ tablar */

let activeTab = "sync";

/* Har tab o'z tilida gapirsin — bir xil tugma turli ish qiladi */
const TAB_TEXT = {
  sync: {
    pick: "kamera videolari va rekorder audiosi (2+ fayl)",
    seqTitle: "Ochiq sequence'dagi fayllarni olish",
    seqHint: "faqat fayllar ro'yxati olinadi — sinxron qaytadan hisoblanadi",
    next: "Endi «Sinxronlash» ni bosing",
  },
  cut: {
    pick: "yoki fayllarni qo'lda tanlang",
    seqTitle: "Ochiq sequence'ni olish",
    seqHint: "montajingiz saqlanadi — faqat pauzalar kesiladi",
    next: "Endi «Pauzalarni kesish» ni bosing — montajingiz saqlanadi",
  },
  switch: {
    pick: "kamera videolari (2+ fayl)",
    seqTitle: "Ochiq sequence'ni olish",
    seqHint: "sinxronlangan timeline'dan kameralar olinadi",
    next: "Endi kameralarga vazifa bering va «Kameralarni taqsimlash» ni bosing",
  },
  intro: {
    pick: "yozuvlar yoki ochiq sequence",
    seqTitle: "Ochiq sequence'dan lahzalarni izlash",
    seqHint: "montajingiz bo'yicha qidiriladi — markerlaringiz ham hisobga olinadi",
    next: "Endi «Lahzalarni topish» ni bosing",
  },
  shorts: {
    pick: "yozuvlar yoki ochiq sequence",
    seqTitle: "Ochiq sequence'dan bo'laklarni izlash",
    seqHint: "har bo'lak tugallangan fikr bo'ladi — 20-60 soniya",
    next: "Endi «Bo'laklarni topish» ni bosing",
  },
  matn: {
    pick: "matnlarni quyida yozasiz — fayl tanlash shart emas",
    next: "Matn yozib, vaqtini bering va «Matnlarni yasash» ni bosing",
  },
  captions: {
    pick: "ovozi yaxshi yozilgan fayl (1 ta yetadi)",
    seqTitle: "Ochiq sequence'dan ovozni olish",
    seqHint: "montajdagi fayllar chiqadi — qaysi biridan yozishni ♪ bilan tanlaysiz",
    next: "♪ bilan belgilangan fayl matnga aylanadi — «2 daqiqani sinash» ni bosing",
  },
};

function applyTabText() {
  const t = TAB_TEXT[activeTab] || TAB_TEXT.sync;
  els.pickHint.textContent = t.pick;
  if (t.seqTitle) els.seqTitle.textContent = t.seqTitle;
  if (t.seqHint) els.seqHint.textContent = t.seqHint;
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab[data-tab]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      activeTab = tab.dataset.tab;
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("on"));
      tab.classList.add("on");
      document.body.className = "tab-" + activeTab;
      lastXml = null;
      timeline = null;
      seqFormat = null;
      moments = [];
      arrangement = null;
      shorts = [];
      shortsArr = null;
      if (els.moments) els.moments.innerHTML = "";
      if (els.shortsList) els.shortsList.innerHTML = "";
      els.importBtn.disabled = true;
      els.log.innerHTML = "";
      els.log.classList.remove("show");
      if (!pollTimer) els.job.className = "job";
      applyTabText();
      renderFiles();
    });
  });
}

/* Cut sozlamalari — slayderlar qiymatini ko'rsatib turadi */
const knobs = {
  minPause: { el: el("kMinPause"), out: el("vMinPause"),
              fmt: (v) => (v / 10).toFixed(1) + " s", val: (v) => v / 10 },
  padding: { el: el("kPadding"), out: el("vPadding"),
             fmt: (v) => v * 10 + " ms", val: (v) => v / 100 },
  markerOldin: { el: el("kMarkerOldin"), out: el("vMarkerOldin"),
                 fmt: (v) => v + " s", val: (v) => v },
  markerKeyin: { el: el("kMarkerKeyin"), out: el("vMarkerKeyin"),
                 fmt: (v) => v + " s", val: (v) => v },
  minShot: { el: el("kMinShot"), out: el("vMinShot"),
             fmt: (v) => (v / 10).toFixed(1) + " s", val: (v) => v / 10 },
  maxShot: { el: el("kMaxShot"), out: el("vMaxShot"),
             fmt: (v) => v + " s", val: (v) => v },
};

/* Ovoz qat'iyligi — «jimlik chegarasi 0.18» degan son o'rniga. Chegarani
   endi motor har yozuvning o'z ovoz darajasidan hisoblaydi; bu yerda faqat
   uni jimlik tomonga yoki gap tomonga surib qo'yamiz. */
let strictness = "orta";

function setupKnobs() {
  Object.values(knobs).forEach((k) => {
    if (!k.el || !k.el.addEventListener) return;
    const show = () => { k.out.textContent = k.fmt(+k.el.value); };
    k.el.addEventListener("input", show);
    show();
  });

  ["markerOldin", "markerKeyin"].forEach((nom) => {
    const k = knobs[nom];
    if (!k.el || !k.el.addEventListener) return;
    k.el.addEventListener("input", () => {
      if (nom === "markerOldin") markerOldin = +k.el.value;
      else markerKeyin = +k.el.value;
    });
  });

  const box = el("kStrict");
  if (!box || !box.querySelectorAll) return;
  box.querySelectorAll(".pick").forEach((pick) => {
    pick.addEventListener("click", () => {
      box.querySelectorAll(".pick").forEach((p) => p.classList.remove("on"));
      pick.classList.add("on");
      strictness = pick.getAttribute("data-v") || "orta";
    });
  });
}

/* ------------------------------------------------- Captions sozlamalari */

const capOpts = { language: "uz", model: "balans" };

/* `matn` — qiymat SON emas, matn bo'lsa (masalan "avto"/"marker").
   Aks holda +"marker" NaN bo'lib, tanlov ishlamay qoladi. */
function setupPills(boxId, apply, matn) {
  const box = document.getElementById(boxId);
  if (!box) return;
  box.querySelectorAll(".opill").forEach((pill) => {
    pill.addEventListener("click", () => {
      box.querySelectorAll(".opill").forEach((x) => x.classList.remove("on"));
      pill.classList.add("on");
      apply(matn ? pill.dataset.v : +pill.dataset.v);
    });
  });
}

function setupIntroPills() {
  const box = document.getElementById("introLimit");
  if (!box) return;
  box.querySelectorAll(".opill").forEach((pill) => {
    pill.addEventListener("click", () => {
      box.querySelectorAll(".opill").forEach((x) => x.classList.remove("on"));
      pill.classList.add("on");
      introLimit = +pill.dataset.v;
    });
  });
}

function setupCaptionPills() {
  [["capLang", "language"], ["capModel", "model"]].forEach(([id, key]) => {
    const box = document.getElementById(id);
    if (!box) return;
    box.querySelectorAll(".opill").forEach((pill) => {
      pill.addEventListener("click", () => {
        box.querySelectorAll(".opill").forEach((x) => x.classList.remove("on"));
        pill.classList.add("on");
        capOpts[key] = pill.dataset.v;
      });
    });
  });
}

/* Qaysi model kompyuterda bor — yo'g'ining ostiga hajmini yozib qo'yamiz.
 * Birinchi ishlatishda 1.5 GB yuklanishi kutilmagan uzoq pauza bo'lib
 * ko'rinardi; endi tanlashdan oldin ko'rinib turadi. */
const MODEL_SIZE = { tez: "0.5 GB", balans: "1.5 GB", aniq: "1.6 GB" };

function markModels(have) {
  if (!have) return;
  document.querySelectorAll("#capModel .opill").forEach((pill) => {
    const v = pill.dataset.v;
    const em = pill.querySelector("em");
    if (!em) return;
    if (!em.dataset.base) em.dataset.base = em.textContent;
    if (have[v]) {
      em.textContent = em.dataset.base;
      pill.title = "Model tayyor — darhol boshlanadi";
    } else {
      em.textContent = "⬇ " + (MODEL_SIZE[v] || "");
      pill.title = "Birinchi ishlatishda " + (MODEL_SIZE[v] || "model") +
                   " yuklab olinadi (bir martalik)";
    }
  });
}

/* Arxivdan qidirish — barcha transkripsiya qilingan sonlar bo'ylab */
async function searchArchive() {
  const q = (els.capSearch.value || "").trim();
  if (!q) return;
  els.log.innerHTML = "";
  logLine("Arxivdan qidirilmoqda: «" + q + "»");
  try {
    const r = await fetch(MOTOR + "/search?q=" + encodeURIComponent(q));
    const j = await r.json();
    const hits = j.hits || [];
    if (!hits.length) {
      logLine("Topilmadi. Faqat transkripsiya qilingan sonlar qidiriladi.", "warn");
      return;
    }
    logLine(hits.length + " ta topildi:", "okline");
    for (const h of hits.slice(0, 20)) {
      const m = Math.floor(h.start / 60), s = Math.round(h.start % 60);
      logLine("  " + h.title + " · " +
              String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0") +
              "  «" + h.text + "»");
    }
  } catch (e) {
    logLine("Qidiruv xatosi: " + e.message, "warn");
  }
}

/* ------------------------------------- ochiq sequence'ni o'qish (Cut) */

let timeline = null;   // [{path, start, in, out}] yoki null
let seqFormat = null;  // ochiq sequence'ning kadr o'lchami (bo'lsa)

/* TickTime → soniya. `seconds` — 25.6+ dagi rasmiy yo'l; qolgani zaxira. */
const TICKS_PER_SECOND = 254016000000;
function secs(t) {
  if (t == null) return 0;
  if (typeof t.seconds === "number") return t.seconds;
  if (typeof t.ticksNumber === "number") return t.ticksNumber / TICKS_PER_SECOND;
  if (t.ticks != null) return Number(t.ticks) / TICKS_PER_SECOND;
  return Number(t) || 0;
}

/* Konstanta nomi API versiyasiga qarab farq qiladi — topganini olamiz. */
function clipTypeConst(ppro) {
  const t = (ppro.Constants && ppro.Constants.TrackItemType) || {};
  for (const key of ["CLIP", "Clip", "clip"]) {
    if (typeof t[key] === "number") return t[key];
  }
  return 1;   // TrackItemType.CLIP ning qiymati
}

/* Klip ortidagi fayl yo'li: ProjectItem'ni ClipProjectItem'ga o'tkazish kerak. */
async function mediaPathOf(ppro, trackItem) {
  const pItem = await trackItem.getProjectItem();
  if (!pItem) return null;
  const clipItem = ppro.ClipProjectItem && ppro.ClipProjectItem.cast
    ? ppro.ClipProjectItem.cast(pItem)
    : pItem;
  if (clipItem && typeof clipItem.getMediaFilePath === "function") {
    return await clipItem.getMediaFilePath();
  }
  return null;
}

/* Sequence'dagi ovoz manbasini taxmin qilamiz.
 *
 * Eng ishonchli belgi — fayl alohida audio trekda tursa-yu, video trekda
 * umuman uchramasa: bu deyarli har doim rekorder yozuvi (mikrofon). Bunday
 * fayl bo'lmasa, birinchi faylni olamiz — foydalanuvchi ♪ bilan almashtira
 * oladi. Tanlangan manbani qaytaramiz, xabarni chaqiruvchi yozadi. */
function pickAudioSource() {
  if (!timeline || !timeline.length) return null;
  const onVideo = new Set();
  const onAudio = [];
  for (const it of timeline) {
    if (it.atrack) {
      if (onAudio.indexOf(it.path) < 0) onAudio.push(it.path);
    } else {
      onVideo.add(it.path);
    }
  }
  const mic = onAudio.filter((p) => !onVideo.has(p));
  const guess = mic[0] || onAudio[0] || (picked[0] && picked[0].path) || null;
  if (!guess) return null;
  audioMaster = guess;
  const nm = guess.split("/").pop();
  return mic.length
    ? "Ovoz manbasi: " + nm + " (alohida audio trekda — mikrofon shu bo'lsa kerak)"
    : "Ovoz manbasi: " + nm + " — boshqasi kerak bo'lsa ♪ ni bosing";
}

/* Ochiq sequence'ning kadr o'lchami.
 *
 * UXP versiyalarida bu ma'lumot turli nomlar ostida turadi, shuning uchun
 * bir nechta shakl sinab ko'riladi. Topilmasa — muammo emas: `null`
 * qaytadi va motor o'lchamni manba fayllardan o'zi aniqlaydi. Shu sababli
 * butun blok o'z try/catch ida: bu yerdagi xato sequence o'qishni
 * to'xtatib qo'ymasligi kerak. */
async function readSeqFormat(seq) {
  const num = (v) => {
    const n = typeof v === "function" ? NaN : Number(v);
    return Number.isFinite(n) && n > 0 ? Math.round(n) : 0;
  };
  try {
    let s = null;
    if (typeof seq.getSettings === "function") s = await seq.getSettings();
    for (const src of [s, seq]) {
      if (!src) continue;
      const w = num(src.videoFrameWidth) || num(src.frameSizeHorizontal) ||
                num(src.videoFrameSizeHorizontal) || num(src.width);
      const h = num(src.videoFrameHeight) || num(src.frameSizeVertical) ||
                num(src.videoFrameSizeVertical) || num(src.height);
      if (w && h) return { width: w, height: h };
    }
  } catch (e) { /* o'lcham o'qilmadi — manbadan olinadi */ }
  return null;
}

async function readSequence() {
  els.log.innerHTML = "";
  logLine("Ochiq sequence o'qilmoqda…");
  let step = "boshlanish";
  try {
    const ppro = require("premierepro");
    step = "loyihani ochish";
    const project = await ppro.Project.getActiveProject();
    step = "sequence topish";
    const seq = project && (await project.getActiveSequence());
    if (!seq) throw new Error("Ochiq sequence topilmadi — timeline'ni oching");

    // Ochiq sequence'ning o'z o'lchami. Topilsa — natija shu formatda
    // bo'ladi (siz tanlagan formatni buzmaymiz). Topilmasa ham hech narsa
    // yo'qolmaydi: motor o'lchamni manba fayllarning o'zidan oladi.
    seqFormat = await readSeqFormat(seq);
    if (seqFormat) {
      logLine("Sequence formati: " + seqFormat.width + "×" + seqFormat.height +
              (seqFormat.height > seqFormat.width ? " (vertikal)" : ""));
    }

    const items = [];
    let unresolved = 0;
    step = "treklarni sanash";
    const vCount = await seq.getVideoTrackCount();
    const aCount = await seq.getAudioTrackCount();
    const clipType = clipTypeConst(ppro);

    for (let i = 0; i < vCount + aCount; i++) {
      step = "trek " + (i + 1) + " ni o'qish";
      const onAudioTrack = i >= vCount;
      const track = onAudioTrack
        ? await seq.getAudioTrack(i - vCount)
        : await seq.getVideoTrack(i);
      if (!track) continue;
      const trackItems = await track.getTrackItems(clipType, false);
      for (const it of trackItems) {
        step = "klip ma'lumotini olish";
        const path = await mediaPathOf(ppro, it);
        if (!path) {
          // Multicam yoki nested sequence klipi: uning ortida fayl yo'q,
          // sequence turadi. Jimgina o'tkazib yuborish — eng yomon yo'l:
          // natija «yarim» chiqadi va sabab ko'rinmaydi.
          unresolved++;
          continue;
        }
        const start = secs(await it.getStartTime());
        const end = secs(await it.getEndTime());
        const inP = secs(await it.getInPoint());
        if (end <= start) continue;
        items.push({ path: path, start: start, in: inP, out: inP + (end - start),
                     atrack: onAudioTrack });
      }
    }

    if (!items.length) {
      throw new Error(unresolved
        ? unresolved + " klipning ortida fayl yo'q (multicam yoki nested "
          + "sequence) — «Premiere ichida qirqish» ni ishlating"
        : "Sequence'da klip topilmadi");
    }

    // Bir xil fayl video va audio trekda takrorlanadi — dublikatlarni olib tashlaymiz
    const seen = new Set();
    timeline = items.filter((it) => {
      const key = it.path + "|" + it.start.toFixed(3) + "|" + it.in.toFixed(3);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    picked = [];
    const names = new Set();
    for (const it of timeline) {
      const nm = it.path.split("/").pop();
      if (!names.has(nm)) { names.add(nm); picked.push({ name: nm, path: it.path }); }
    }
    const sound = activeTab === "captions" ? pickAudioSource() : null;
    renderFiles();
    logLine("Sequence olindi: " + timeline.length + " klip, " +
            picked.length + " fayl ✓", "okline");
    if (unresolved) {
      // Aynan shu holat 20 soniyalik «yarim» natijaga olib kelgan edi:
      // multicam kliplar tushib qolib, faqat rekorder audiosi o'qilgan.
      logLine(unresolved + " klip o'qilmadi — ortida fayl emas, sequence "
              + "turadi (multicam / nested). Bu kliplardagi kadrlar "
              + "natijaga tushmaydi!", "warn");
      logLine("Multicam montajda «Premiere ichida qirqish» ni ishlating — "
              + "u kadrlarni Premiere'ning o'ziga qirqtiradi.", "warn");
    }
    if (sound) logLine(sound);
    const t = TAB_TEXT[activeTab] || {};
    if (t.next) logLine(t.next);
  } catch (e) {
    timeline = null;
    seqFormat = null;
    logLine("Sequence o'qilmadi (" + step + "): " + e.message, "warn");
    logLine("Fayllarni qo'lda tanlashingiz mumkin — natija bir xil bo'ladi");
  }
}


/* ------------------------------------------------------- Intro: nomzodlar
 *
 * Modul hech qachon o'zi tanlab intro yasamaydi: mashina nomzod topadi,
 * did — foydalanuvchida. Shu sababli ro'yxat belgilanadigan qilib berilgan
 * va tanlanmagan nomzod XML'ga tushmaydi. */
let moments = [];        // motordan kelgan nomzodlar
let arrangement = null;  // kliplarning timeline'dagi joylashuvi (2-bosqich uchun)
let introLimit = 18;

function tc(sec) {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return (h ? h + ":" + String(m).padStart(2, "0") : String(m)) +
         ":" + String(s % 60).padStart(2, "0");
}

function renderMoments() {
  els.moments.innerHTML = "";
  for (const m of moments) {
    const row = document.createElement("div");
    row.className = "mom " + (m.on ? "on" : "off");

    const box = document.createElement("span");
    box.className = "box";
    box.textContent = m.on ? "✓" : "";
    row.appendChild(box);

    const mid = document.createElement("div");
    mid.className = "mid";
    const top = document.createElement("div");
    top.className = "top";
    const t = document.createElement("span");
    t.className = "tc";
    t.textContent = tc(m.start);
    const k = document.createElement("span");
    k.className = "kind " + (m.kind || "");
    k.textContent = m.kind || "lahza";
    const len = document.createElement("span");
    len.className = "len";
    len.textContent = m.length.toFixed(1) + "s";
    top.appendChild(t); top.appendChild(k); top.appendChild(len);
    mid.appendChild(top);

    if (m.text) {
      const tx = document.createElement("div");
      tx.className = "txt";
      tx.textContent = "«" + m.text + "»";
      mid.appendChild(tx);
    }
    const why = document.createElement("div");
    why.className = "why";
    why.textContent = m.why + (m.text ? "" : " · matn yo'q");
    mid.appendChild(why);
    row.appendChild(mid);

    row.addEventListener("click", () => { m.on = !m.on; renderMoments(); });
    row.addEventListener("dblclick", () => goToTime(m.start));
    els.moments.appendChild(row);
  }
  const on = moments.filter((m) => m.on);
  const total = on.reduce((a, m) => a + m.length, 0);
  els.buildBtn.disabled = !on.length;
  els.reviewBtn.disabled = !moments.length;
  els.buildBtn.textContent = on.length
    ? "Intro yasash (" + on.length + " · " + Math.round(total) + "s)"
    : "Intro yasash";
  if (moments.length) {
    els.hint.textContent = moments.length + " nomzod · " + on.length + " tanlangan";
  }
}

/* TickTime yasash. Diqqat: statik metodni `const f = T.createWithSeconds`
 * deb ajratib olib chaqirish mumkin emas — UXP `this` ni talab qiladi. */
const TICKS_PER_SEC = 254016000000;

function tickTime(ppro, sec) {
  const T = ppro.TickTime;
  if (!T) throw new Error("TickTime klassi yo'q");
  if (typeof T.createWithSeconds === "function") return T.createWithSeconds(Number(sec));
  if (typeof T.createWithTicks === "function") {
    return T.createWithTicks(String(Math.round(Number(sec) * TICKS_PER_SEC)));
  }
  throw new Error("TickTime yasash yo'li topilmadi");
}

/* Premiere playhead'ini shu joyga olib boradi — nomzodni ko'rish uchun */
async function goToTime(sec) {
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) throw new Error("ochiq sequence yo'q");
    await seq.setPlayerPosition(tickTime(ppro, sec));
  } catch (e) {
    logLine("Playhead'ni ko'chirib bo'lmadi (" + (e.message || e) + ") — "
            + "vaqtni qo'lda kiriting: " + tc(sec), "warn");
  }
}

/* Timeline'dagi markerlar — mashina taxmin qilmaydi, siz aytgansiz.
 * API versiyalari farq qiladi, shuning uchun topilmasa jimgina o'tamiz. */
/* Markerlarni o'qish.
 *
 * Bu yerda ehtiyot bo'lish kerak: UXP `getMarkers()` MASSIV emas, TO'PLAM
 * obyekti qaytaradi. Ilgari kod undan to'g'ridan-to'g'ri `length` so'rardi,
 * topa olmasdi va «marker yo'q» deb xulosa qilardi — timeline markerlarga
 * to'la bo'lsa ham. Endi to'plamning har xil shakli sinab ko'riladi va
 * qaysi yo'l ishlagani logga yoziladi.
 */
async function massivga(obj, chuqurlik) {
  if (!obj || chuqurlik > 2) return null;
  if (Array.isArray(obj)) return obj;

  // Massivsimon: length + indeks
  if (typeof obj.length === "number" && typeof obj !== "function") {
    const out = [];
    for (let i = 0; i < obj.length; i++) out.push(obj[i]);
    if (out.length) return out;
  }
  // Sanoq + indeks bilan olinadigan to'plam
  for (const [sanoq, olish] of [["getMarkerCount", "getMarkerAt"],
                                ["getCount", "getItemAt"],
                                ["numItems", "getItemAt"]]) {
    if (typeof obj[sanoq] === "function" && typeof obj[olish] === "function") {
      const n = await obj[sanoq]();
      const out = [];
      for (let i = 0; i < n; i++) out.push(await obj[olish](i));
      if (out.length) return out;
    }
  }
  // Ichkarida yana bir qavat: markers.getMarkers() → massiv
  for (const nom of ["getMarkers", "getAllMarkers", "markers", "items"]) {
    const qiymat = obj[nom];
    if (typeof qiymat === "function") {
      const ichki = await obj[nom]();
      const r = await massivga(ichki, chuqurlik + 1);
      if (r && r.length) return r;
    } else if (qiymat) {
      const r = await massivga(qiymat, chuqurlik + 1);
      if (r && r.length) return r;
    }
  }
  // Iteratsiya qilinadigan bo'lsa
  try {
    if (typeof obj[Symbol.iterator] === "function") {
      const out = Array.from(obj);
      if (out.length) return out;
    }
  } catch (e) { /* iteratsiya bo'lmadi */ }
  return null;
}

async function readMarkers() {
  let manba = "";
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) {
      markerHolat = "Ochiq sequence topilmadi";
      return [];
    }

    // Markerlar sequence'da ham, uning project item'ida ham turishi mumkin —
    // ikkalasi ham sinaladi.
    const manbalar = [];
    if (ppro.Markers && typeof ppro.Markers.getMarkers === "function") {
      manbalar.push(["Markers.getMarkers(seq)",
                     () => ppro.Markers.getMarkers(seq)]);
    }
    if (typeof seq.getMarkers === "function") {
      manbalar.push(["seq.getMarkers()", () => seq.getMarkers()]);
    }
    if (typeof seq.getProjectItem === "function"
        && ppro.Markers && typeof ppro.Markers.getMarkers === "function") {
      manbalar.push(["Markers.getMarkers(projectItem)", async () => {
        const it = await seq.getProjectItem();
        return it ? ppro.Markers.getMarkers(it) : null;
      }]);
    }

    let xom = null;
    for (const [nomi, olish] of manbalar) {
      try {
        const javob = await olish();
        const r = await massivga(javob, 0);
        if (r && r.length) { xom = r; manba = nomi; break; }
        if (javob && !xom) {
          // Nimadir qaytdi, lekin ichidan markerlarni ololmadik —
          // shaklini yozib qo'yamiz, keyingi safar shu bo'yicha tuzatamiz.
          manba = nomi + " → " + shaklTavsifi(javob);
        }
      } catch (e) {
        manba = nomi + " xato berdi: " + (e.message || e);
      }
    }

    if (!xom) {
      markerHolat = "«" + (seq.name || "sequence")
                  + "» da marker topilmadi"
                  + (manba ? "  [" + manba + "]" : "");
      return [];
    }

    const out = [];
    for (const mk of xom) {
      let t = null;
      try {
        t = mk.start !== undefined && mk.start !== null ? mk.start
          : (typeof mk.getStart === "function" ? await mk.getStart() : null);
      } catch (e) { t = null; }
      if (t == null) continue;
      // Marker timeline'da cho'zib belgilangan bo'lsa — uzunligi ham bor.
      let d = null;
      try {
        d = mk.duration !== undefined && mk.duration !== null ? mk.duration
          : (typeof mk.getDuration === "function" ? await mk.getDuration() : null);
      } catch (e) { d = null; }
      const rec = { start: secs(t) };
      const ds = d == null ? 0 : secs(d);
      if (ds > 0.05) rec.duration = ds;
      out.push(rec);
    }
    out.sort((x, y) => x.start - y.start);
    markerHolat = out.length + " ta marker o'qildi — «"
                + (seq.name || "sequence") + "» dan  [" + manba + "]";
    return out;
  } catch (e) {
    markerHolat = "Markerlarni o'qib bo'lmadi: " + (e.message || e)
                + (manba ? "  [" + manba + "]" : "");
    return [];
  }
}

/* Yasalgan sequence'ni ochish. Bitta yo'lga tayanmaymiz: UXP versiyasiga
   qarab ochish ham, faol qilib qo'yish ham har xil nomlanadi. Hech biri
   ishlamasa — hech bo'lmasa qayerdan topishni aniq aytamiz. */
async function sequenceOchish(ppro, project, seq, nomi) {
  const yollar = [
    ["project.openSequence", () => project.openSequence(seq)],
    ["project.setActiveSequence", () => project.setActiveSequence(seq)],
    ["Project.openSequence", () => ppro.Project.openSequence(project, seq)],
  ];
  const xatolar = [];
  for (const [nom, urin] of yollar) {
    try {
      if (typeof urin !== "function") continue;
      await urin();
      logLine("«" + nomi + "» ochildi — timeline'da ko'ring ✓", "okline");
      return true;
    } catch (e) {
      xatolar.push(nom + ": " + (e.message || e));
    }
  }
  logLine("Sequence yasaldi, lekin o'zi ochilmadi. Project panelidan "
          + "«" + nomi + "» ni ikki marta bosing (Window > Project).", "warn");
  if (xatolar.length) logLine("  (" + xatolar.join(" · ") + ")");
  return false;
}


/* ---------------------------------------------- 9:16 (reels) ga o'tkazish
 *
 * Ikki qadam:
 *   1. sequence sozlamalarini vertikal qilish (1920x1080 → 1080x1920);
 *   2. kliplarni balandlik bo'yicha to'ldirish uchun kattalashtirish.
 *
 * Ikkinchi qadam Premiere API'sining chuqur qismiga tegadi (Motion >
 * Scale), shuning uchun u ishlamasa ham birinchi qadam qoladi va nima
 * qilish kerakligi aniq aytiladi. Yuzni markazga surishni montajchi
 * o'zi qiladi — buni mashina yaxshi qila olmaydi.
 */
async function seqOlchami(seq) {
  try {
    if (typeof seq.getSettings !== "function") return null;
    const st = await seq.getSettings();
    if (!st) return null;
    const w = Number(st.videoFrameWidth || st.frameSizeHorizontal || 0);
    const h = Number(st.videoFrameHeight || st.frameSizeVertical || 0);
    if (w > 0 && h > 0) return { w: w, h: h, st: st };
  } catch (e) { /* o'qilmadi */ }
  return null;
}

async function vertikalgaOtkazish(ppro, project, seq) {
  const olcham = await seqOlchami(seq);
  if (!olcham) {
    logLine("Sequence o'lchamini o'qib bo'lmadi — format o'zgartirilmadi. "
            + "Qo'lda: Sequence > Sequence Settings > 1080x1920.", "warn");
    return null;
  }
  if (olcham.h >= olcham.w) {
    logLine("Sequence allaqachon vertikal (" + olcham.w + "×" + olcham.h
            + ") — format o'zgartirilmadi");
    return olcham;
  }

  const yangiW = Math.min(olcham.w, olcham.h);
  const yangiH = Math.max(olcham.w, olcham.h);
  const st = olcham.st;
  try {
    if ("videoFrameWidth" in st) { st.videoFrameWidth = yangiW; st.videoFrameHeight = yangiH; }
    else { st.frameSizeHorizontal = yangiW; st.frameSizeVertical = yangiH; }
    if (typeof seq.createSetSettingsAction === "function") {
      runActions(project, () => [seq.createSetSettingsAction(st)], "Format 9:16");
    } else if (typeof seq.setSettings === "function") {
      await seq.setSettings(st);
    } else {
      throw new Error("sozlamalarni yozish yo'li yo'q");
    }
    logLine("Format 9:16 ga o'tkazildi: " + olcham.w + "×" + olcham.h
            + " → " + yangiW + "×" + yangiH + " ✓", "okline");
    return { w: yangiW, h: yangiH, eskiW: olcham.w, eskiH: olcham.h };
  } catch (e) {
    logLine("Formatni o'zgartirib bo'lmadi (" + (e.message || e) + ")", "warn");
    logLine("Qo'lda: Sequence > Sequence Settings > Frame Size "
            + yangiW + " × " + yangiH + ".", "warn");
    return null;
  }
}

/* Klipni kadr balandligiga to'ldirish uchun kerakli kattalashtirish.
   16:9 manba 9:16 kadrda: balandlik bo'yicha to'ldirsak, eni ortib
   ketadi va chetlari kesiladi — markazdagi qism qoladi. */
function toldirishFoizi(eskiW, eskiH, yangiW, yangiH) {
  const k = Math.max(yangiW / eskiW, yangiH / eskiH);
  return Math.round(k * 1000) / 10;          // foizda, bir kasr bilan
}

async function kliplarniToldirish(ppro, project, seq, foiz) {
  let ozgardi = 0, urinildi = 0;
  try {
    const n = await seq.getVideoTrackCount();
    for (let i = 0; i < n; i++) {
      const track = await seq.getVideoTrack(i);
      if (!track) continue;
      const items = await track.getTrackItems(clipTypeConst(ppro), false);
      for (const it of items) {
        urinildi++;
        try {
          const chain = await it.getComponentChain();
          const cnt = await chain.getComponentCount();
          for (let c = 0; c < cnt; c++) {
            const comp = await chain.getComponentAtIndex(c);
            let param = null;
            try { param = await comp.getParam("Scale"); } catch (e) { param = null; }
            if (!param) continue;
            runActions(project,
              () => [param.createSetValueAction(foiz, true)], "Scale");
            ozgardi++;
            break;
          }
        } catch (e) { /* shu klip bo'lmadi — qolganini davom ettiramiz */ }
      }
    }
  } catch (e) {
    logLine("Kliplarni kattalashtirib bo'lmadi: " + (e.message || e), "warn");
  }
  return { ozgardi: ozgardi, urinildi: urinildi };
}

async function reelsgaOtkazish(ppro, project, seq) {
  logLine("Reels 9:16 ga o'tkazilmoqda…");
  const yangi = await vertikalgaOtkazish(ppro, project, seq);
  if (!yangi || !yangi.eskiW) return;

  const foiz = toldirishFoizi(yangi.eskiW, yangi.eskiH, yangi.w, yangi.h);
  if (foiz <= 100.5) return;
  const r = await kliplarniToldirish(ppro, project, seq, foiz);
  if (r.ozgardi) {
    logLine(r.ozgardi + " klip kadrga to'ldirildi (" + foiz + "%) ✓", "okline");
    logLine("Yuz markazda bo'lmasa: klipni tanlang > Effect Controls > "
            + "Motion > Position ni chapga/o'ngga suring.");
  } else {
    logLine("Kadr to'ldirilmadi — kliplarni qo'lda kattalashtiring: "
            + "hammasini tanlab, Effect Controls > Motion > Scale = "
            + foiz + "%.", "warn");
    logLine("Yoki osonroq yo'l: Project panelida shu sequence ustiga o'ng "
            + "tugma > Auto Reframe Sequence > 9:16 — Adobe yuzni o'zi "
            + "kuzatib joylashtiradi.");
  }
}

/* Obyekt qanday ekanini bir qatorda tasvirlaydi — nosozlikni shu bilan
   bir bosishda aniqlaymiz. */
function shaklTavsifi(obj) {
  if (obj == null) return "null";
  const t = typeof obj;
  if (t !== "object") return t;
  const nomlar = [];
  let o = obj;
  let qavat = 0;
  while (o && o !== Object.prototype && qavat < 3) {
    for (const k of Object.getOwnPropertyNames(o)) {
      if (k !== "constructor" && nomlar.indexOf(k) < 0) nomlar.push(k);
    }
    o = Object.getPrototypeOf(o);
    qavat++;
  }
  return (obj.constructor && obj.constructor.name ? obj.constructor.name : "object")
       + " {" + nomlar.slice(0, 14).join(", ") + "}";
}

let markerHolat = "";

async function findMoments() {
  if (!(await checkMotor())) return;
  moments = [];
  arrangement = null;
  renderMoments();
  els.log.innerHTML = "";
  els.introBtn.disabled = true;
  startProgress("Lahzalar qidirilmoqda…");
  const markers = await readMarkers();
  if (markers.length) logLine(markers.length + " ta marker topildi — ular birinchi navbatda");
  try {
    const body = { limit: introLimit, markers: markers };
    if (timeline) body.timeline = timeline;
    body.files = picked.map((p) => p.path);
    const r = await fetch(MOTOR + "/intro", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of (j.logs || []).slice(shownLogs)) logLine(line);
    moments = (j.moments || []).map((m, i) => ({ ...m, on: m.rank <= 5 }));
    arrangement = j.arrangement;
    renderMoments();
    logLine(moments.length + " nomzod topildi — kerakligini belgilab, "
            + "«Intro yasash» ni bosing", "okline");
    if (!j.has_text) {
      logLine("Gaplar ko'rinmaydi (transkript yo'q) — «Nomzodlarni ko'rish» "
              + "ni bosib, hammasini ketma-ket eshitib chiqing.");
    }
    stopProgress(true, moments.length + " nomzod");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  els.introBtn.disabled = picked.length < 1;
  els.shortsBtn.disabled = picked.length < 1;
}

async function buildIntro(review) {
  // Ko'rib chiqishda hamma nomzod ketadi, introda esa faqat belgilangani
  const chosen = review ? moments.slice() : moments.filter((m) => m.on);
  if (!chosen.length || !arrangement) return;
  els.log.innerHTML = "";
  els.buildBtn.disabled = true;
  startProgress(review ? "Nomzodlar yig'ilmoqda…" : "Intro yig'ilmoqda…");
  try {
    const r = await fetch(MOTOR + "/intro-yasash", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arrangement: arrangement, moments: chosen,
                             review: !!review }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of (j.logs || []).slice(shownLogs)) logLine(line);
    lastXml = j.output;
    logLine(j.moments + " lahza · " + Math.round(j.length_sec) + "s "
            + (review ? "ko'rib chiqish sequence'i" : "intro") + " tayyor ✓",
            "okline");
    if (review) {
      logLine("Import qilib eshitib chiqing — har bo'lak boshida marker "
              + "va raqami turadi. Yoqqanini shu ro'yxatda belgilaysiz.");
    }
    logLine("Fayl: " + j.output);
    els.importBtn.disabled = false;
    stopProgress(true, Math.round(j.length_sec) + "s intro");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  renderMoments();
}


/* --------------------------------------------------------------- Shorts
 *
 * Intro bilan bir xil ishlaydi: motor nomzod bo'laklarni topadi, tanlovni
 * odam qiladi. Farqi — uzunlik (20-60 s, tugallangan fikr) va har bo'lak
 * alohida sequence bo'lib chiqishi. */
let shorts = [];
let shortsArr = null;
let shortsLimit = 8;
let shortsMode = "avto";
/* Marker atrofidan olinadigan oyna (soniya). Odam eshitib turib M ni
   bosguncha vaqt o'tadi, shuning uchun oldingi tomon kattaroq. */
/* Standart: bo'lak AYNAN markerdan boshlanadi. Ilgari 20 soniya oldin
   boshlanardi — bu montajchi belgilamagan joyni ham olib kelardi. */
let markerOldin = 0;
let markerKeyin = 30;
let markerAspect = "reels";

function renderShorts() {
  els.shortsList.innerHTML = "";
  for (const sh of shorts) {
    const row = document.createElement("div");
    row.className = "mom " + (sh.on ? "on" : "off");

    const box = document.createElement("span");
    box.className = "box";
    box.textContent = sh.on ? "✓" : "";
    row.appendChild(box);

    const mid = document.createElement("div");
    mid.className = "mid";
    const top = document.createElement("div");
    top.className = "top";
    const t = document.createElement("span");
    t.className = "tc";
    t.textContent = tc(sh.start);
    const k = document.createElement("span");
    k.className = "kind " + (sh.kind || "");
    k.textContent = sh.kind || "bo'lak";
    const len = document.createElement("span");
    len.className = "len";
    len.textContent = Math.round(sh.length) + "s";
    top.appendChild(t); top.appendChild(k); top.appendChild(len);
    mid.appendChild(top);
    if (sh.text) {
      const tx = document.createElement("div");
      tx.className = "txt";
      tx.textContent = "«" + sh.text + "»";
      mid.appendChild(tx);
    }
    const why = document.createElement("div");
    why.className = "why";
    why.textContent = sh.why;
    mid.appendChild(why);
    row.appendChild(mid);

    row.addEventListener("click", () => { sh.on = !sh.on; renderShorts(); });
    row.addEventListener("dblclick", () => goToTime(sh.start));
    els.shortsList.appendChild(row);
  }
  const on = shorts.filter((x) => x.on);
  els.shortsBuildBtn.disabled = !on.length;
  els.shortsBuildBtn.textContent = on.length
    ? "Shorts yasash (" + on.length + " ta)" : "Shorts yasash";
  if (shorts.length) {
    els.hint.textContent = shorts.length + " bo'lak · " + on.length + " tanlangan";
  }
}

async function findShorts() {
  if (!(await checkMotor())) return;
  shorts = [];
  shortsArr = null;
  renderShorts();
  els.log.innerHTML = "";
  els.shortsBtn.disabled = true;
  startProgress("Bo'laklar qidirilmoqda…");
  const markers = await readMarkers();
  try {
    logLine(markerHolat || "Markerlar tekshirilmadi");
    const body = { limit: shortsLimit, markers: markers };
    if (shortsMode === "marker") body.faqat_markerlar = true;
    if (timeline) body.timeline = timeline;
    body.files = picked.map((p) => p.path);
    const r = await fetch(MOTOR + "/shorts", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of (j.logs || []).slice(shownLogs)) logLine(line);
    shorts = (j.shorts || []).map((sh) => ({ ...sh, on: sh.rank <= 3 }));
    shortsArr = j.arrangement;
    renderShorts();
    logLine(shorts.length + " bo'lak topildi — keraklisini belgilab, "
            + "«Shorts yasash» ni bosing", "okline");
    stopProgress(true, shorts.length + " bo'lak");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  els.shortsBtn.disabled = picked.length < 1;
}

async function buildShorts() {
  const chosen = shorts.filter((sh) => sh.on);
  if (!chosen.length || !shortsArr) return;
  els.log.innerHTML = "";
  els.shortsBuildBtn.disabled = true;
  startProgress("Bo'laklar yig'ilmoqda…");
  try {
    const r = await fetch(MOTOR + "/shorts-yasash", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ arrangement: shortsArr, moments: chosen }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of (j.logs || []).slice(shownLogs)) logLine(line);
    lastXml = j.output;
    logLine(j.shorts + " sequence tayyor · jami "
            + Math.round(j.length_sec) + "s ✓", "okline");
    for (const nm of j.names || []) logLine("  " + nm);
    els.importBtn.disabled = false;
    stopProgress(true, j.shorts + " sequence");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  renderShorts();
}



/* ============================================================ Matn tabi
 *
 * Foydalanuvchi matnlarni O'ZI yozadi va har biriga timeline'dagi vaqtni
 * beradi. Motor har matn uchun shaffof fonli qisqa video yasaydi va
 * ularni kerakli joyga qo'yadigan XML yozadi.
 *
 * Animatsiya ataylab sezilmaydigan: pastdan 28 px, sekinlashib to'xtaydi.
 * Tomoshabin (ko'pincha yoshi katta) matnning chiqqanini payqamasligi
 * kerak — «yo'q edi, bor bo'ldi». Shuning uchun bu yerda hech qanday
 * sakrash/kattalashish sozlamasi yo'q: bo'lsa, ishlatilib qo'yiladi. */

let matnBloklar = [];
let matnRang = "#FFFFFF";
let matnQalin = true;
let prevTimer = null;

function matnUslub() {
  return {
    shrift: els.mFont.value || null,
    olcham: Number(els.mSize.value) || 58,
    joy: els.mPos.value || "past",
    rang: matnRang,
    qalin: matnQalin,
  };
}

/* «1:23» / «83» / «1:02:05» → soniya. Montajchi qaysi ko'rinishda
   yozsa ham tushunilsin — vaqtni qo'lda ko'chirish shundoq ham zerikarli. */
function vaqtga(s) {
  const t = String(s || "").trim().replace(",", ".");
  if (!t) return 0;
  const p = t.split(":").map((x) => parseFloat(x) || 0);
  if (p.length === 1) return p[0];
  if (p.length === 2) return p[0] * 60 + p[1];
  return p[0] * 3600 + p[1] * 60 + p[2];
}

function vaqtdan(sec) {
  const s = Math.max(0, Number(sec) || 0);
  const m = Math.floor(s / 60);
  const r = (s - m * 60);
  return m + ":" + (r < 10 ? "0" : "") + r.toFixed(r % 1 ? 1 : 0);
}

function renderMatn() {
  els.matnList.innerHTML = "";
  matnBloklar.forEach((b, i) => {
    const row = document.createElement("div");
    row.className = "mrow";

    const ta = document.createElement("textarea");
    ta.value = b.matn || "";
    ta.placeholder = "Matn… (Enter — yangi qator)";
    ta.addEventListener("input", () => {
      b.matn = ta.value;
      matnBtnHolat();          // birinchi harfdayoq tugma yonsin
      previewSoon();
    });

    const times = document.createElement("div");
    times.className = "mtimes";
    const l1 = document.createElement("div");
    l1.className = "mlbl"; l1.textContent = "boshlanishi";
    const t1 = document.createElement("input");
    t1.type = "text"; t1.value = vaqtdan(b.start);
    t1.addEventListener("change", () => { b.start = vaqtga(t1.value);
                                          t1.value = vaqtdan(b.start); });
    const l2 = document.createElement("div");
    l2.className = "mlbl"; l2.textContent = "davomiyligi (s)";
    const t2 = document.createElement("input");
    t2.type = "text"; t2.value = String(b.davomiylik);
    t2.addEventListener("change", () => {
      b.davomiylik = Math.max(1.4, parseFloat(t2.value) || 5);
      t2.value = String(b.davomiylik);
    });
    times.appendChild(l1); times.appendChild(t1);
    times.appendChild(l2); times.appendChild(t2);

    const btns = document.createElement("div");
    btns.className = "mbtns";
    const ph = document.createElement("div");
    ph.className = "mini"; ph.textContent = "⌖ playhead";
    ph.title = "Vaqtni Premiere'dagi playhead turgan joydan oladi";
    ph.addEventListener("click", async () => {
      const t = await playheadVaqti();
      if (t == null) return;
      b.start = t; t1.value = vaqtdan(t);
      logLine("Vaqt playhead'dan olindi: " + vaqtdan(t));
    });
    const rm = document.createElement("div");
    rm.className = "mini rm"; rm.textContent = "× o'chirish";
    rm.addEventListener("click", () => {
      matnBloklar.splice(i, 1); renderMatn(); previewSoon();
    });
    btns.appendChild(ph); btns.appendChild(rm);

    row.appendChild(ta); row.appendChild(times); row.appendChild(btns);
    els.matnList.appendChild(row);
  });
  matnBtnHolat();
}

function matnBtnHolat() {
  els.matnBtn.disabled = !matnBloklar.some((b) => (b.matn || "").trim());
}

function addMatn() {
  const oxirgi = matnBloklar[matnBloklar.length - 1];
  matnBloklar.push({
    matn: "",
    start: oxirgi ? oxirgi.start + oxirgi.davomiylik + 2 : 0,
    davomiylik: 5,
  });
  renderMatn();
}

/* Premiere'dagi playhead qayerda turibdi */
async function playheadVaqti() {
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) throw new Error("ochiq sequence yo'q");
    const pos = await seq.getPlayerPosition();
    return Math.max(0, secs(pos));
  } catch (e) {
    logLine("Playhead o'qilmadi: " + e.message + " — vaqtni qo'lda yozing",
            "warn");
    return null;
  }
}

/* Ochiq sequence'ning o'lchami va fps'i — matn shu formatda yasaladi */
async function matnFormat() {
  const std = { width: 1920, height: 1080, fps: 25 };
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) return std;
    const f = await readSeqFormat(seq);
    let fps = 0;
    try {
      const st = typeof seq.getSettings === "function" ? await seq.getSettings() : null;
      const v = st && (st.videoFrameRate || st.videoFrameRateTicks);
      if (v && typeof v === "object") fps = 1 / secs(v);
      else if (typeof v === "number" && v > 0 && v < 200) fps = v;
    } catch (e) { /* fps topilmadi — standart qoladi */ }
    return {
      width: (f && f.width) || std.width,
      height: (f && f.height) || std.height,
      fps: fps > 0 && fps < 200 ? fps : std.fps,
    };
  } catch (e) {
    return std;
  }
}

/* Ko'rish rasmi — yozayotganda ortiqcha so'rov ketmasin deb kechiktiriladi */
function previewSoon() {
  if (prevTimer) clearTimeout(prevTimer);
  prevTimer = setTimeout(updatePreview, 400);
}

async function updatePreview() {
  const blok = matnBloklar.find((b) => (b.matn || "").trim());
  if (!blok) {
    els.matnPreview.removeAttribute("src");
    els.matnPrevHint.textContent =
      "Matn yozing — shu yerda aynan qanday chiqishi ko'rinadi";
    return;
  }
  try {
    const fmt = await matnFormat();
    const r = await fetch(MOTOR + "/matn-oldin", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ matn: blok.matn, width: fmt.width,
                             height: fmt.height, uslub: matnUslub() }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "ko'rish rasmi chiqmadi");
    els.matnPreview.src = j.png;
    els.matnPrevHint.textContent = fmt.width + "×" + fmt.height
      + (fmt.height > fmt.width ? " (vertikal)" : "") + " — ochiq sequence'dan";
  } catch (e) {
    els.matnPrevHint.textContent = "Ko'rish rasmi chiqmadi: " + e.message;
  }
}

async function loadFonts() {
  try {
    const r = await fetch(MOTOR + "/shriftlar");
    const j = await r.json();
    const list = j.shriftlar || [];
    els.mFont.innerHTML = "";
    let tavsiyaBor = false;
    for (const f of list) {
      const o = document.createElement("option");
      o.value = f.nom;
      o.textContent = f.tavsiya ? f.nom + " ★" : f.nom;
      els.mFont.appendChild(o);
      if (f.tavsiya && !tavsiyaBor) { els.mFont.value = f.nom; tavsiyaBor = true; }
    }
  } catch (e) { /* motor o'chiq — tugma bosilganda aytiladi */ }
}

async function runMatn() {
  const bloklar = matnBloklar
    .filter((b) => (b.matn || "").trim())
    .map((b) => ({ matn: b.matn, start: b.start, davomiylik: b.davomiylik }));
  if (!bloklar.length) return;
  els.log.innerHTML = "";
  els.matnBtn.disabled = true;
  startProgress("Matnlar yasalmoqda…");
  try {
    const fmt = await matnFormat();
    const r = await fetch(MOTOR + "/matn", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bloklar: bloklar, width: fmt.width,
                             height: fmt.height, fps: fmt.fps,
                             uslub: matnUslub() }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of j.logs || []) logLine(line);
    lastXml = j.output;
    logLine(j.count + " matn tayyor ✓", "okline");
    logLine("Endi «Premiere'ga import» ni bosing — «Matn» sequence'i "
            + "ochiladi. Undagi kliplarni tanlab (Ctrl+A), nusxalab, "
            + "o'z timeline'ingizga V2 trekka qo'ying.");
    els.importBtn.disabled = false;
    stopProgress(true, j.count + " matn");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  renderMatn();
}

function setupMatn() {
  ["mFont", "mSize", "mPos"].forEach((id) => {
    const e = els[id];
    if (e && e.addEventListener) e.addEventListener("change", previewSoon);
  });
  if (els.mBold && els.mBold.addEventListener) {
    els.mBold.addEventListener("click", () => {
      matnQalin = !matnQalin;
      els.mBold.classList.toggle("on", matnQalin);
      previewSoon();
    });
  }
  document.querySelectorAll(".swatch").forEach((sw) => {
    sw.addEventListener("click", () => {
      document.querySelectorAll(".swatch").forEach((x) => x.classList.remove("on"));
      sw.classList.add("on");
      matnRang = sw.getAttribute("data-c") || "#FFFFFF";
      previewSoon();
    });
  });
  addMatn();
}


/* ================================================ Markerlardan yig'ish
 *
 * Nima uchun bu boshqacha: ovoz tahlili bilan qirqishda kadr XML orqali
 * qayta quriladi, ya'ni ortida FAYL turgan narsagina chiqadi. Multicam,
 * nested sequence, matn/grafika qatlamlari — bularning ortida fayl yo'q,
 * shuning uchun ular natijaga tushmaydi. Aynan shu sabab «faqat ovoz
 * ko'rinyapti» degan holat kelib chiqqan edi.
 *
 * Bu yerda ish butunlay Premiere'ning ICHIDA bajariladi: har marker uchun
 * sequence'ning in/out nuqtalari qo'yiladi va `createSubsequence`
 * chaqiriladi. Natijada o'sha joyda timeline'da NIMA bo'lsa — kadr, ovoz,
 * matn, grafika, effektlar, ovoz darajalari — hammasi o'z holicha chiqadi.
 * Keyin bo'laklar ketma-ket bitta sequence'ga yig'iladi.
 */
/* In/out qo'yish: avval hujjatdagi action yo'li, bo'lmasa to'g'ridan-to'g'ri
 * setter. Qaysi biri ishlaganini bir marta yozib qo'yamiz. */
let inOutWay = "";

async function setSeqInOut(ppro, project, seq, a, b) {
  if (inOutWay !== "setter" && typeof seq.createSetInPointAction === "function") {
    try {
      // TickTime ham qulf ichida yasaladi — bir xil qoida
      runActions(project, () => [
        seq.createSetInPointAction(tickTime(ppro, a)),
        seq.createSetOutPointAction(tickTime(ppro, b)),
      ], "In/Out");
      if (!inOutWay) { inOutWay = "action"; logLine("  (in/out: action yo'li)"); }
      return;
    } catch (e) {
      if (inOutWay === "action") throw e;          // ishlagan yo'l buzildi
      logLine("  action yo'li ishlamadi (" + (e.message || e)
              + ") — to'g'ridan-to'g'ri sinaladi", "warn");
    }
  }
  if (typeof seq.setInPoint === "function") {
    await seq.setInPoint(tickTime(ppro, a));
    await seq.setOutPoint(tickTime(ppro, b));
    if (!inOutWay) { inOutWay = "setter"; logLine("  (in/out: to'g'ridan-to'g'ri)"); }
    return;
  }
  throw new Error("in/out qo'yish yo'li yo'q");
}

/* Action'larni yaratish va bajarish — Adobe talab qilgan yagona shakl:
 *
 *   project.lockedAccess(() => {
 *     project.executeTransaction((compound) => {
 *       compound.addAction(obj.createSomethingAction(...));
 *     }, "izoh");
 *   });
 *
 * `create*Action` chaqiruvi lockedAccess'dan TASHQARIDA bo'lsa, Premiere
 * «The script object is no longer valid» deb rad etadi — aynan shu xato
 * bir necha marta chiqdi. lockedAccess ham, executeTransaction ham
 * sinxron: ichida `await` ishlatib bo'lmaydi, shuning uchun kerakli
 * obyektlar oldindan olinadi. */
function runActions(project, build, label) {
  let ok = false, err = null;
  if (typeof project.lockedAccess !== "function") {
    throw new Error("lockedAccess yo'q — Premiere 25.6+ kerak");
  }
  project.lockedAccess(() => {
    try {
      ok = project.executeTransaction((compound) => {
        const list = build() || [];
        for (const act of list) {
          if (act) compound.addAction(act);
        }
      }, label || "Podcast Suite");
    } catch (e) {
      err = e;
    }
  });
  if (err) throw err;
  return ok;
}

/* Obyektlar eskirmasligi uchun har amaldan oldin qaytadan olinadi */
async function freshSequence(ppro) {
  const project = await ppro.Project.getActiveProject();
  if (!project) throw new Error("Ochiq loyiha topilmadi");
  const seq = await project.getActiveSequence();
  if (!seq) throw new Error("Ochiq sequence topilmadi");
  return { project: project, seq: seq };
}

/* Nosozlik bo'lganda API'ning aynan qanday ekanini log'ga chiqaramiz —
 * shu ma'lumot bir bosishda muammoni aniqlashga yetadi. */
function methodNames(obj) {
  const names = [];
  let o = obj;
  while (o && o !== Object.prototype) {
    for (const k of Object.getOwnPropertyNames(o)) {
      try {
        if (typeof obj[k] === "function" && names.indexOf(k) < 0) names.push(k);
      } catch (e) { /* getter xato bersa — o'tkazamiz */ }
    }
    o = Object.getPrototypeOf(o);
  }
  return names.sort();
}

/* Uzun ro'yxat ekranda kesilib qolmasin: bo'laklab yozamiz va oxirida
 * hammasini faylga saqlaymiz — o'sha faylni yuborish yetadi. */
function logLong(label, text) {
  const size = 110;
  for (let i = 0; i < text.length; i += size) {
    logLine((i === 0 ? label + ": " : "   ") + text.slice(i, i + size));
  }
}

async function dumpApi(ppro, seq) {
  try {
    logLong("API (premierepro)", Object.keys(ppro || {}).join(", "));
    if (ppro && ppro.TickTime) {
      logLong("TickTime", Object.getOwnPropertyNames(ppro.TickTime).join(", "));
    }
    if (ppro && ppro.SequenceEditor) {
      logLong("SequenceEditor",
              Object.getOwnPropertyNames(ppro.SequenceEditor).join(", "));
    }
    if (seq) logLong("Sequence metodlari", methodNames(seq).join(", "));
  } catch (e) {
    logLine("Tashxis to'liq chiqmadi: " + (e.message || e), "warn");
  }
  await copyLog();        // to'liq matnni faylga (yoki buferga) olib qo'yamiz
}



/* Markerlardan oraliqlar. Marker uzunligi bilan qo'yilgan bo'lsa — aynan
   o'sha oraliq; bo'lmasa marker atrofidan oyna olinadi. Ustma-ust tushgan
   oraliqlar birlashtiriladi: bir joy ikki marta tushmasin. */
function markerOraliqlari(markers, oldin, keyin) {
  const xom = [];
  for (const mk of markers) {
    const t = Number(mk.start) || 0;
    if (mk.duration > 0.05) {
      xom.push({ a: Math.max(0, t), b: t + mk.duration, aniq: true });
    } else {
      xom.push({ a: Math.max(0, t - oldin), b: t + keyin, aniq: false });
    }
  }
  xom.sort((x, y) => x.a - y.a);
  const out = [];
  for (const r of xom) {
    const oxirgi = out[out.length - 1];
    if (oxirgi && r.a <= oxirgi.b + 0.05) {
      oxirgi.b = Math.max(oxirgi.b, r.b);       // qo'shilib ketdi
      oxirgi.qoshildi = (oxirgi.qoshildi || 1) + 1;
    } else {
      out.push({ a: r.a, b: r.b, aniq: r.aniq });
    }
  }
  return out;
}

async function markerlardanYigish() {
  els.log.innerHTML = "";
  startProgress("Markerlar o'qilmoqda…");
  let step = "boshlanish";
  const made = [];
  let ppro = null, lastSeq = null;
  try {
    ppro = require("premierepro");
    const markers = await readMarkers();
    logLine(markerHolat || "Markerlar tekshirilmadi");
    if (!markers.length) {
      throw new Error("Timeline'da marker yo'q. Sequence'ni eshitib boring "
                      + "va yoqqan joyingizda M tugmasini bosing.");
    }
    const oraliqlar = markerOraliqlari(markers, markerOldin, markerKeyin);
    const qoshilgan = oraliqlar.filter((r) => r.qoshildi).length;
    logLine(markers.length + " marker → " + oraliqlar.length + " oraliq"
            + (qoshilgan ? " (" + qoshilgan + " tasi yonma-yon bo'lgani uchun "
                           + "birlashtirildi)" : ""));

    step = "ochiq sequence";
    const first = await freshSequence(ppro);
    lastSeq = first.seq;
    let oldIn = null, oldOut = null;
    try {
      oldIn = await first.seq.getInPoint();
      oldOut = await first.seq.getOutPoint();
    } catch (e) { /* o'qilmasa — tiklamaymiz */ }
    logLine("Manba: " + (first.seq.name || "sequence"));

    for (let i = 0; i < oraliqlar.length; i++) {
      const r = oraliqlar[i];
      paintJob({ steps: [], step: 0, lines: [],
                 stage: "Bo'lak " + (i + 1) + " / " + oraliqlar.length,
                 percent: i / oraliqlar.length * 100,
                 detail: tc(r.a) + " → " + tc(r.b) });

      step = (i + 1) + "-oraliq: sequence olish";
      const cur = await freshSequence(ppro);
      lastSeq = cur.seq;
      step = (i + 1) + "-oraliq: in/out (" + tc(r.a) + "–" + tc(r.b) + ")";
      await setSeqInOut(ppro, cur.project, cur.seq, r.a, r.b);

      step = (i + 1) + "-oraliq: subsequence yasash";
      let sub = null;
      try {
        // `true` — trek nishonlashiga qaramaydi, ya'ni HAMMA trek olinadi:
        // matn/grafika yuqori treklarda tursa ham tushib qolmaydi.
        sub = await cur.seq.createSubsequence(true);
      } catch (e) {
        sub = await cur.seq.createSubsequence();
      }
      if (!sub) throw new Error("subsequence bo'sh qaytdi");
      made.push(sub);

      const nomi = "Bo'lak " + (i + 1) + " · " + tc(r.a);
      try {
        const item = await sub.getProjectItem();
        if (item && typeof item.createSetNameAction === "function") {
          runActions(cur.project, () => [item.createSetNameAction(nomi)], "Nom");
        }
      } catch (e) { /* nom qo'yilmasa ham bo'lak joyida */ }
      if (i === 0) logLine("Birinchi bo'lak olindi ✓ — qolganlari ketmoqda");
    }
    logLine(made.length + " bo'lak Premiere'da olindi ✓", "okline");

    // --- Hammasini BITTA sequence'ga ---
    step = "bitta sequence'ga yig'ish";
    let natijaNomi = "Podcast Suite — Markerlar";
    const project = await ppro.Project.getActiveProject();
    let target = null;

    // Eng toza yo'l: hamma bo'lakdan yangi sequence. Bo'lmasa —
    // birinchisini asos qilib, qolganini ketma-ket qo'shamiz (sinalgan yo'l).
    if (typeof project.createSequenceFromMedia === "function") {
      try {
        const items = [];
        for (const s of made) items.push(await s.getProjectItem());
        target = await project.createSequenceFromMedia(natijaNomi, items);
        if (target) logLine("Bo'laklar yangi sequence'ga yig'ildi ✓", "okline");
      } catch (e) {
        logLine("  (yangi sequence yo'li ishlamadi: " + (e.message || e)
                + ") — ketma-ket qo'shiladi");
        target = null;
      }
    }

    if (!target && made.length) {
      target = made[0];
      let joined = 0;
      for (let i = 1; i < made.length; i++) {
        step = (i + 1) + "-bo'lakni qo'shish";
        paintJob({ steps: [], step: 0, lines: [], stage: "Yig'ilmoqda",
                   percent: i / made.length * 100,
                   detail: (i + 1) + " / " + made.length });
        const pr = await ppro.Project.getActiveProject();
        const editor = ppro.SequenceEditor.getEditor(target);
        const item = await made[i].getProjectItem();
        const end = await target.getEndTime();
        try {
          runActions(pr,
            () => [editor.createInsertProjectItemAction(item, end, 0, 0, false)],
            "Bo'lak qo'shish");
        } catch (e) {
          if (typeof editor.createOverwriteItemAction !== "function") throw e;
          logLine("  insert ishlamadi — overwrite bilan qo'yiladi", "warn");
          runActions(pr,
            () => [editor.createOverwriteItemAction(item, end, 0, 0)],
            "Bo'lak qo'shish");
        }
        joined++;
      }
      logLine("Bitta sequence'ga yig'ildi — " + (joined + 1) + " bo'lak ✓",
              "okline");
    }

    if (target) {
      try {
        const item = await target.getProjectItem();
        if (item && typeof item.createSetNameAction === "function") {
          runActions(project, () => [item.createSetNameAction(natijaNomi)],
                     "Nom");
        }
      } catch (e) { /* nom qo'yilmasa ham bo'ladi */ }
      if (markerAspect === "reels") {
        step = "9:16 ga o'tkazish";
        try {
          await reelsgaOtkazish(ppro, project, target);
        } catch (e) {
          logLine("Format bosqichida xato: " + (e.message || e), "warn");
        }
      }
      await sequenceOchish(ppro, project, target, natijaNomi);
    }

    if (oldIn && oldOut) {
      try {
        const back = await freshSequence(ppro);
        runActions(back.project, () => [
          back.seq.createSetInPointAction(oldIn),
          back.seq.createSetOutPointAction(oldOut),
        ], "In/out tiklash");
      } catch (e) { /* muhim emas */ }
    }
    logLine("Kerak bo'lmagan bo'laklarni Project panelidan o'chirsangiz "
            + "bo'ladi (Window > Project).");
    stopProgress(true, made.length + " bo'lak");
  } catch (e) {
    logLine("To'xtadi (" + step + "): " + (e.message || e), "warn");
    if (made.length) {
      logLine(made.length + " bo'lak yasalgan — Project panelida turadi.",
              "warn");
    }
    await dumpApi(ppro, lastSeq);
    logLine("Shu xabarni menga yuboring — aynan shu qadamni tuzataman.");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
}


/* Log matnini menga yuborish oson bo'lsin: avval buferga, bo'lmasa faylga */
async function copyLog() {
  const text = Array.from(els.log.querySelectorAll("div"))
    .map((d) => d.textContent).join("\n");
  if (!text) return;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      logLine("Log buferga olindi — menga qo'yib yuborsangiz bo'ladi ✓",
              "okline");
      return;
    }
    throw new Error("bufer yo'q");
  } catch (e) {
    try {
      const r = await fetch(MOTOR + "/log-saqlash", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.error || "yozilmadi");
      logLine("Log faylga yozildi: " + j.path, "okline");
      logLine("Shu faylni ochib, matnini menga yuborsangiz bo'ladi.");
    } catch (e2) {
      logLine("Nusxalab bo'lmadi (" + (e2.message || e2)
              + ") — ekran rasmini yuborsangiz ham bo'ladi.", "warn");
    }
  }
}

/* ---------------------------------------------------- sinxronlash */

function logLine(text, cls) {
  const div = document.createElement("div");
  if (cls) div.className = cls;
  div.textContent = text;
  els.log.appendChild(div);
  els.log.classList.add("show");
  els.logBar.classList.add("show");
  els.log.scrollTop = els.log.scrollHeight;
}

/* ------------------------------------------- ish jarayonini ko'rsatish
 *
 * Uzun ishlar (model yuklash, transkripsiya) bir necha o'n daqiqa ketishi
 * mumkin. Javob faqat oxirida keladi, shuning uchun motordan holatni
 * so'rab turamiz — panel jim qolmasin va sekundlar sanalib tursin. */
let pollTimer = null;    // motordan holat so'rash (2 s)
let tickTimer = null;    // soat (1 s) — panel o'zi sanaydi, motorga bog'liq emas
let shownLogs = 0;
let jobT0 = 0;           // ish boshlangan payt
let etaSec = null;       // silliqlangan «qancha qoldi»
let lastChange = 0;      // motordan oxirgi marta yangilik kelgan payt
let lastSig = "";        // holat o'zgarganini bilish uchun barmoq izi
let stepsSig = "";       // bosqichlar ro'yxati o'zgarganda qayta chiziladi

function mmss(sec) {
  sec = Math.max(0, Math.round(sec));
  return Math.floor(sec / 60) + ":" + String(sec % 60).padStart(2, "0");
}

/* «≈ 8 daqiqa qoldi» — uzun ishda soniyagacha aniqlik keraksiz va yolg'on */
function human(sec) {
  if (sec < 90) return Math.max(5, Math.round(sec / 5) * 5) + " soniya";
  if (sec < 3600) return Math.round(sec / 60) + " daqiqa";
  const h = Math.floor(sec / 3600);
  return h + " soat " + Math.round((sec - h * 3600) / 60) + " daqiqa";
}

function drawSteps(steps, index) {
  // Bosqichlar bir marta chiziladi: chiziqdagi chegaralar va qisqa nomlar
  const sig = steps.map((s) => s.label).join("|");
  if (sig !== stepsSig) {
    stepsSig = sig;
    const total = steps.reduce((a, s) => a + s.weight, 0) || 1;
    let acc = 0;
    els.jobTicks.innerHTML = "";
    steps.slice(0, -1).forEach((s) => {
      acc += s.weight;
      const t = document.createElement("span");
      t.style.left = (acc / total * 100) + "%";
      els.jobTicks.appendChild(t);
    });
    els.jobChips.innerHTML = "";
    steps.forEach((s) => {
      const c = document.createElement("span");
      c.className = "c";
      c.textContent = s.short || s.label;
      els.jobChips.appendChild(c);
    });
  }
  const chips = els.jobChips.querySelectorAll(".c");
  chips.forEach((c, i) => {
    c.className = "c" + (i < index ? " ok" : i === index ? " now" : "");
    c.textContent = (i < index ? "✓ " : "") + c.textContent.replace(/^✓ /, "");
  });
}

function paintJob(j) {
  const steps = j.steps || [];
  const idx = j.step >= 0 ? j.step : 0;
  if (steps.length) drawSteps(steps, idx);

  // Foizni bilmasak — shu bosqichda qancha turganimizni aytamiz: «qancha
  // uzoq» degan raqam ham harakatda ekanini ko'rsatadi.
  els.jobStage.textContent = (j.stage || "Boshlanmoqda…") +
    (j.percent != null ? "  " + Math.round(j.percent) + "%"
     : j.stage_elapsed > 3 ? "  " + mmss(j.stage_elapsed) : "");
  els.jobStep.textContent = steps.length ? (idx + 1) + " / " + steps.length : "";
  els.jobDetail.textContent = j.detail || "";

  // Umumiy chiziq: tugagan bosqichlar + hozirgisining ulushi
  const total = steps.reduce((a, s) => a + s.weight, 0) || 1;
  const done = steps.slice(0, idx).reduce((a, s) => a + s.weight, 0);
  const segw = steps[idx] ? steps[idx].weight : 0;
  els.jobSeg.style.left = (done / total * 100) + "%";
  els.jobSeg.style.width = (Math.max(segw, total * 0.04) / total * 100) + "%";
  const overall = j.overall != null ? j.overall : done / total * 100;
  els.jobFill.style.width = overall + "%";

  // Qolgan vaqt: umumiy foiz va o'tgan vaqtdan. Sakrab turmasin uchun
  // silliqlaymiz va ish boshida umuman ko'rsatmaymiz — u paytda taxmin yolg'on.
  const el = (Date.now() - jobT0) / 1000;
  if (overall > 4 && el > 8) {
    const raw = el * (100 - overall) / overall;
    etaSec = etaSec == null ? raw : etaSec * 0.7 + raw * 0.3;
    els.jobEta.textContent = "· ≈ " + human(etaSec) + " qoldi";
  } else {
    els.jobEta.textContent = "";
  }

  // «Tirikmi?» — eng halol javob: har javobda chiziqqa bitta bo'lakcha
  // qo'shiladi. Motor jim qolsa, chiziq ham o'sishdan to'xtaydi.
  const sig = j.stage + "|" + j.percent + "|" + j.detail + "|" + (j.lines || []).length;
  const changed = sig !== lastSig;
  if (changed) { lastSig = sig; lastChange = Date.now(); }
  const tick = document.createElement("i");
  if (changed) tick.className = "hi";
  els.jobPulse.appendChild(tick);
  while (els.jobPulse.childNodes.length > 30) {
    els.jobPulse.removeChild(els.jobPulse.firstChild);
  }
  els.job.classList.toggle("stale", Date.now() - lastChange > 45000);
}

function startProgress(kindLabel) {
  shownLogs = 0;
  jobT0 = Date.now();
  etaSec = null;
  lastChange = Date.now();
  lastSig = "";
  stepsSig = "";
  els.job.className = "job on";
  els.jobStage.textContent = kindLabel || "Boshlanmoqda…";
  els.jobStep.textContent = "";
  els.jobDetail.textContent = "";
  els.jobEta.textContent = "";
  els.jobFill.style.width = "0%";
  els.jobSeg.style.width = "0%";
  els.jobChips.innerHTML = "";
  els.jobTicks.innerHTML = "";
  els.jobPulse.innerHTML = "";
  els.jobElapsed.textContent = "0:00";
  if (els.body && els.body.scrollTo) els.body.scrollTo(0, 0);

  // Soat panelning o'zida yuradi: motor javob bermay qolsa ham vaqt ko'rinadi
  tickTimer = setInterval(() => {
    els.jobElapsed.textContent = mmss((Date.now() - jobT0) / 1000);
  }, 1000);

  const poll = async () => {
    try {
      const r = await fetch(MOTOR + "/progress");
      const j = await r.json();
      const lines = j.lines || [];
      for (let i = shownLogs; i < lines.length; i++) logLine(lines[i]);
      if (lines.length > shownLogs) shownLogs = lines.length;
      paintJob(j);
    } catch (e) { /* motor band bo'lishi mumkin — keyingi urinishda ko'ramiz */ }
  };
  // Birinchi so'rovni kutmasdan yuboramiz: qisqa ishda karta bo'sh qolmasin
  setTimeout(poll, 250);
  pollTimer = setInterval(poll, 2000);
}

function stopProgress(ok, note) {
  if (pollTimer) clearInterval(pollTimer);
  if (tickTimer) clearInterval(tickTimer);
  pollTimer = tickTimer = null;
  const spent = mmss((Date.now() - jobT0) / 1000);
  els.job.className = "job on " + (ok ? "done" : "err");
  els.jobStage.textContent = ok ? "Tayyor ✓" : "To'xtadi";
  els.jobDetail.textContent = note || "";
  els.jobEta.textContent = "";
  els.jobStep.textContent = "";
  if (ok) els.jobFill.style.width = "100%";
  els.jobElapsed.textContent = spent;
  const chips = els.jobChips.querySelectorAll(".c");
  if (ok) chips.forEach((c) => { c.className = "c ok"; });
}

async function run(kind) {
  if (!(await checkMotor())) return;

  const isCut = kind === "cut";
  const isSwitch = kind === "switch";
  const isCap = kind === "captions" || kind === "sample";
  els.log.innerHTML = "";
  els.syncBtn.disabled = true;
  els.cutBtn.disabled = true;
  els.switchBtn.disabled = true;
  els.capBtn.disabled = true;
  els.sampleBtn.disabled = true;
  els.importBtn.disabled = true;
  logLine(kind === "sample" ? "2 daqiqalik sinov — model birinchi marta yuklansa kutiladi…"
        : isCap ? "Transkripsiya boshlandi — uzun yozuvda bir necha daqiqa ketadi…"
        : isSwitch ? "Kamera rejasi tuzilmoqda…"
        : isCut ? "Pauzalar qidirilmoqda…" : "Sinxronlash boshlandi…");

  const endpoint = isCap ? "captions" : kind;
  const body = {
    files: picked.map((p) => p.path),
    name: isCap ? "Podcast Suite — Captions"
        : isSwitch ? "Podcast Suite — Switch"
        : isCut ? "Podcast Suite — Cut" : "Podcast Suite — Sync",
  };
  if (isCap) {
    const src = audioMaster || (picked[0] && picked[0].path);
    body.files = [src];
    // Sequence'dan olingan bo'lsa — vaqtlar montajga moslanishi uchun
    // shu faylning bo'laklari ham ketadi (motor o'zi ajratib oladi).
    if (timeline) body.timeline = timeline;
    body.language = capOpts.language;
    body.model = capOpts.model;
    body.title = (src || "").split("/").pop().replace(/\.[^.]+$/, "");
    if (kind === "sample") body.sample_seconds = 120;
  }
  if (isSwitch) {
    if (timeline) body.timeline = timeline;
    body.roles = picked.map((p, i) => roleOf(p, i).role);
    body.speakers = picked.map((p, i) => roleOf(p, i).sid);
    if (audioMaster) body.audio_master = audioMaster;
    body.min_shot = knobs.minShot.val(+knobs.minShot.el.value);
    body.max_shot = knobs.maxShot.val(+knobs.maxShot.el.value);
  }
  if (isCut) {
    if (timeline) body.timeline = timeline;
    // Tayyor sequence'dan kesayotgan bo'lsak, uning formatini saqlaymiz;
    // fayllardan kesayotganda motor o'lchamni manbaning o'zidan oladi.
    if (timeline && seqFormat) body.seq_format = seqFormat;
    body.strictness = strictness;
    body.min_pause = knobs.minPause.val(+knobs.minPause.el.value);
    body.padding = knobs.padding.val(+knobs.padding.el.value);
  }

  startProgress(isCap ? "Transkripsiya boshlanmoqda…"
              : isSwitch ? "Kamera rejasi tuzilmoqda…"
              : isCut ? "Pauzalar qidirilmoqda…" : "Sinxronlash boshlandi…");
  try {
    const r = await fetch(MOTOR + "/" + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");

    // Jarayon davomida ko'rsatilganlarini qayta yozmaymiz
    for (const line of (j.logs || []).slice(shownLogs)) {
      logLine(line, line.indexOf("OGOHLANTIRISH") >= 0 ? "warn" : null);
    }
    lastXml = isCap ? null : j.output;
    if (isCap) {
      logLine(j.line_count + " qator · " + j.word_count + " so'z" +
              (j.from_sequence ? "  (montaj vaqti bo'yicha)" : "") +
              (j.sample ? "  (sinov)" : ""), "okline");
      if (j.preview) logLine("Namuna: " + j.preview);
      if (j.sample) {
        logLine("Sifat yoqsa — «To'liq transkripsiya» ni bosing.");
      } else {
        if (j.srt) logLine("SRT: " + j.srt);
        if (j.archive) logLine("Arxivga qo'shildi — endi qidiruvda topiladi ✓", "okline");
      }
    } else if (isSwitch) {
      logLine(j.shots + " kadr tuzildi · birga gapirish " +
              Math.round(j.together_sec) + "s", "okline");
      if (!audioMaster) {
        logLine("Ovoz manbasi tanlanmagan — har kamera o'z audiosi bilan " +
                "keladi. Yaxshi yozilgan fayl yonidagi ♪ ni bosing.", "warn");
      }
      for (const c of j.clips) {
        logLine("  " + c.name + " — " + c.shots + " kadr, " +
                Math.round(c.screen_sec) + "s ekranda" +
                (c.shots === 0 ? "  (ishlatilmadi)" : ""),
                c.shots === 0 ? "warn" : null);
      }
    } else if (isCut) {
      const mins = (s) => Math.floor(s / 60) + " daq " + Math.round(s % 60) + " s";
      logLine(j.pauses.length + " pauza kesildi — " + mins(j.saved_sec) +
              " qisqardi", "okline");
      logLine("Uzunlik: " + mins(j.total_sec) + " → " + mins(j.new_length_sec));
      if (j.format) {
        logLine("Sequence: " + j.format.width + "×" + j.format.height +
                " (" + j.format.shape + ", manbadan avtomatik) · chegara " +
                j.threshold + " («" + j.strictness + "»)");
        if (j.format.mixed) {
          logLine("Manbalarda turli formatlar bor — ko'p vaqt egallagani " +
                  "tanlandi. Boshqacha kerak bo'lsa, Premiere'da sequence " +
                  "ustiga o'ng tugma > Auto Reframe.", "warn");
        }
      }
    } else {
      renderFiles(j.clips);
    }
    if (!isCap) {
      logLine("Tayyor ✓ — endi «Premiere'ga import» ni bosing", "okline");
      logLine("Fayl: " + j.output);
      els.importBtn.disabled = false;
    }
    stopProgress(true, isCap ? (j.line_count + " qator subtitr")
                             : "natija tayyor");
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  updateRunButtons();
}

function updateRunButtons() {
  els.syncBtn.disabled = picked.length < 2;
  els.cutBtn.disabled = picked.length < 1;
  els.switchBtn.disabled = picked.length < 2;
  els.introBtn.disabled = picked.length < 1;
  els.shortsBtn.disabled = picked.length < 1;
  els.capBtn.disabled = picked.length < 1 || !whisperReady;
  els.sampleBtn.disabled = picked.length < 1 || !whisperReady;
}

/* ------------------------------------------- Premiere'ga import */

async function doImport() {
  if (!lastXml) return;
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    if (!project) throw new Error("Ochiq loyiha topilmadi");

    // Import oldidan mavjud sequence'larni eslab qolamiz — yangisini
    // shu ro'yxat bilan solishtirib topamiz (nomlar takrorlanishi mumkin).
    let before = [];
    try {
      before = (await project.getSequences()).map((s) => s.guid.toString());
    } catch (e) { /* eski API — pastda nom bo'yicha qidiramiz */ }

    // importFiles(filePaths, suppressUI, targetBin, asNumberedStills) — 25.6+
    await project.importFiles([lastXml], true);
    logLine("Sequence loyihaga qo'shildi ✓", "okline");

    // Yangi sequence'ni topib, darhol ochamiz — qo'lda qidirish shart bo'lmasin
    try {
      const after = await project.getSequences();
      const fresh = after.filter((s) => before.indexOf(s.guid.toString()) < 0);
      const target = fresh.length ? fresh[fresh.length - 1] : after[after.length - 1];
      if (target) {
        await project.openSequence(target);
        logLine("Sequence ochildi — montajni boshlayvering ✓", "okline");
      }
    } catch (e) {
      logLine("Sequence Project panelida — ikki bosib oching.", "warn");
    }
  } catch (e) {
    // API mos kelmasa — qo'lda import yo'lini ko'rsatamiz
    logLine("Avtomatik import ishlamadi (" + e.message + ").", "warn");
    logLine("Qo'lda: File > Import > " + lastXml);
  }
}

/* ---------------------------------------------------- ulanishlar */

/* Element topilmasa ham panel qulamasin — eski index.html bilan ham ochilaveradi */
function on(el, fn) {
  if (el) el.addEventListener("click", fn);
}
on(els.diagBtn, showDiagnostics);
on(els.updBtn, doUpdate);
on(els.pick, pickFiles);
on(els.syncBtn, function () { run("sync"); });
on(els.cutBtn, function () { run("cut"); });
on(els.switchBtn, function () { run("switch"); });
on(els.capBtn, function () { run("captions"); });
on(els.sampleBtn, function () { run("sample"); });
on(els.introBtn, findMoments);
on(els.logCopy, copyLog);
on(els.logBig, function () { els.log.classList.toggle("big"); });
on(els.shortsBtn, findShorts);
on(els.shortsBuildBtn, buildShorts);
on(els.markerBtn, markerlardanYigish);
on(els.buildBtn, function () { buildIntro(false); });
on(els.reviewBtn, function () { buildIntro(true); });
on(els.capSearchBtn, searchArchive);
on(els.seqBtn, readSequence);
on(els.matnAdd, addMatn);
on(els.matnBtn, runMatn);
on(els.importBtn, doImport);

setupTabs();
setupKnobs();
setupMatn();
setupCaptionPills();
setupIntroPills();
setupPills("shortsLimit", (v) => { shortsLimit = v; });
setupPills("markerAspect", (v) => { markerAspect = v; }, true);
setupPills("shortsMode", (v) => {
  shortsMode = v;
  const marker = v === "marker";
  const korsat = (id, bormi) => {
    const e = document.getElementById(id);
    if (e) e.style.display = bormi ? "" : "none";
  };
  korsat("shortsTipAuto", !marker);
  korsat("shortsTipMarker", marker);
  korsat("markerTip", marker);
  korsat("markerKnobs", marker);
  korsat("markerFormat", marker, "flex");
  // Avtomatik rejimda «Markerlardan yig'ish» ma'nosiz — yashiramiz
  if (els.markerBtn && els.markerBtn.style) {
    els.markerBtn.style.display = marker ? "" : "none";
  }
  const lim = document.getElementById("shortsLimit");
  if (lim && lim.parentElement) lim.parentElement.style.display = marker ? "none" : "";
}, true);
if (els.markerBtn && els.markerBtn.style) els.markerBtn.style.display = "none";
document.body.className = "tab-sync";
applyTabText();
checkMotor().then(function (ok) { if (ok) { checkUpdates(); loadFonts(); } });
setInterval(checkMotor, 5000);
setInterval(checkUpdates, 10 * 60 * 1000);   // har 10 daqiqada bir tekshiradi
renderFiles();

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
const PANEL_BUILD = "14-Avg 18:40";

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
  jobMore: el("jobMore"),
  logToggle: el("logToggle"),
  jobDetail: el("jobDetail"),
  jobElapsed: el("jobElapsed"),
  jobEta: el("jobEta"),
  jobHelp: el("jobHelp"),
  jobHelpTxt: el("jobHelpTxt"),
  jobRetry: el("jobRetry"),
  capSearch: el("capSearch"),
  capSearchBtn: el("capSearchBtn"),
  introBtn: el("introBtn"),
  trImpBtn: el("trImpBtn"),
  srtBtn: el("srtBtn"),
  trImpHolat: el("trImpHolat"),
  buildBtn: el("buildBtn"),
  reviewBtn: el("reviewBtn"),
  shortsBtn: el("shortsBtn"),
  shortsBuildBtn: el("shortsBuildBtn"),
  markerBtn: el("markerBtn"),
  trPanel: el("trPanel"),
  trList: el("trList"),
  trSearch: el("trSearch"),
  trLoad: el("trLoad"),
  trClear: el("trClear"),
  trBtn: el("trBtn"),
  harBtn: el("harBtn"),
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
  tozalaBtn: el("tozalaBtn"),
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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
    next: "Endi «Kesib, yangi sequence yasash» ni bosing — montajingiz "
        + "saqlanadi, faqat pauzalar kesiladi",
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
  harakat: {
    pick: "ochiq sequence (fayl tanlash shart emas)",
    seqTitle: "Ochiq sequence'ni olish",
    seqHint: "kadrlar shu montajdan o'qiladi",
    next: "Endi «Harakat qo'shish» ni bosing",
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
      cutRejimKorsat();   // className qayta yozildi — rejim klassini tiklaymiz
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
      tozalashTasdiq = 0;   // yorliq almashtirilsa tasdiq kuchini yo'qotadi
      if (els.tozalaBtn) els.tozalaBtn.textContent = "Tozalash";
      els.log.innerHTML = ""; logOchi(false);
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

/* Cut natijasi qayerga tushadi: yangi sequence'ga ("yangi") yoki ochiq
   montajning O'ZIGA ("joyida").

   Standart — "yangi", chunki u ishonchli ishlaydi. Fayllarning to'planib
   qolish muammosi endi boshqa yo'l bilan hal qilingan: import «Podcast
   Suite» biniga tushadi va «Tozalash» uni bir bosishda olib tashlaydi.

   "joyida" hali sinovda: Premiere API'sida razor yo'q, shuning uchun
   klip nusxa orqali bo'linadi va bu har Premiere versiyasida bir xil
   ishlashiga hozircha kafolat yo'q. */
let cutRejim = "yangi";

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

  const rejimBox = el("kCutRejim");
  if (rejimBox && rejimBox.querySelectorAll) {
    rejimBox.querySelectorAll(".pick").forEach((pick) => {
      pick.addEventListener("click", () => {
        rejimBox.querySelectorAll(".pick").forEach((p) => p.classList.remove("on"));
        pick.classList.add("on");
        cutRejim = pick.getAttribute("data-v") || "joyida";
        cutRejimKorsat();
      });
    });
  }
  cutRejimKorsat();
}

/* Tanlangan rejim tugma yozuvida va izohda ko'rinib tursin — bosishdan
   oldin nima bo'lishini bilish kerak, keyin emas. */
function cutRejimKorsat() {
  const joyida = cutRejim === "joyida";
  if (els.cutBtn) {
    els.cutBtn.textContent = joyida ? "Montajni qirqish"
                                    : "Kesib, yangi sequence yasash";
  }
  const tip = el("cutRejimTip");
  if (tip) {
    tip.innerHTML = joyida
      ? "<b>Sinovda.</b> Ochiq montajning o'zidan pauzalar olib tashlanadi, "
        + "yangi sequence yasalmaydi. Premiere API'sida klipni ikkiga "
        + "bo'lish (razor) yo'q — bo'linish nusxa orqali qilinadi, "
        + "shuning uchun avval <b>qisqa montajda sinab ko'ring</b>. "
        + "Ish boshlanishidan oldin loyiha saqlanadi; xato chiqsa "
        + "montajga tegilmaydi. Yuqoridan «Ochiq sequence'ni olish» "
        + "bosilgan bo'lishi kerak."
      : "Kesilgan montaj alohida sequence bo'lib import qilinadi. "
        + "Import <b>«Podcast Suite» biniga</b> tushadi — ishingiz "
        + "tugagach pastdagi <b>«Tozalash»</b> uni butunlay olib "
        + "tashlaydi, ya'ni fayllar to'planib qolmaydi.";
  }
  // Import tugmasi faqat XML rejimida ma'noga ega. Inline style bilan
  // yashirmaymiz — u boshqa yorliqqa o'tganda ham qolib ketardi; body
  // klassi esa CSS bilan faqat Cut yorlig'ida ta'sir qiladi.
  if (document.body) {
    document.body.classList[joyida ? "add" : "remove"]("cut-joyida");
  }
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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
        // Klip qaysi qavatda turgani. Cut natijani shu tartibda qayta
        // yig'adi — montajchi kadrlarni va ovozlarni ataylab ma'lum
        // qavatlarga qo'ygan bo'ladi.
        items.push({ path: path, start: start, in: inP, out: inP + (end - start),
                     atrack: onAudioTrack,
                     vtrack: onAudioTrack ? null : i,
                     atrack_i: onAudioTrack ? (i - vCount) : null });
      }
    }

    if (!items.length) {
      throw new Error(unresolved
        ? unresolved + " klipning ortida fayl yo'q (multicam yoki nested "
          + "sequence) — «Premiere ichida qirqish» ni ishlating"
        : "Sequence'da klip topilmadi");
    }

    // Bir xil klip video va audio trekda ikki marta uchraydi — ular
    // bog'langan. Ilgari ikkinchisi shunchaki TASHLAB yuborilardi va
    // ovoz qaysi qatorda turgani shu yerda yo'qolardi. Endi ikkalasi
    // birlashtiriladi: bitta yozuvda video qavati ham, audio qavati ham
    // qoladi.
    const xarita = new Map();
    for (const it of items) {
      const key = it.path + "|" + it.start.toFixed(3) + "|" + it.in.toFixed(3);
      const bor = xarita.get(key);
      if (!bor) { xarita.set(key, it); continue; }
      if (it.vtrack != null && bor.vtrack == null) bor.vtrack = it.vtrack;
      if (it.atrack_i != null && bor.atrack_i == null) bor.atrack_i = it.atrack_i;
      // Videoli yozuv ustun: klipda kadr ham bor degani
      if (!it.atrack) bor.atrack = false;
    }
    timeline = Array.from(xarita.values());

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
let olchamSabab = "";

/* Obyektning O'ZIDAGI va PROTOTIPIDAGI hamma nom.
 *
 * Premiere qaytaradigan obyektlar «native» — qiymatlar prototipdagi
 * getter'larda turadi, obyektning o'zida emas. Shuning uchun
 * Object.keys() bo'sh ro'yxat qaytaradi va «maydon yo'q» degan
 * noto'g'ri xulosaga olib keladi. Aynan shu sabab montaj o'lchami
 * topilmay qolgan edi. */
function xossaNomlari(obj) {
  const nomlar = [];
  let o = obj, qavat = 0;
  while (o && o !== Object.prototype && qavat < 5) {
    try {
      for (const k of Object.getOwnPropertyNames(o)) {
        if (k !== "constructor" && nomlar.indexOf(k) < 0) nomlar.push(k);
      }
    } catch (e) { /* bu qavat o'qilmasa — keyingisiga o'tamiz */ }
    o = Object.getPrototypeOf(o);
    qavat++;
  }
  return nomlar;
}

/* Nom bo'yicha qiymat: xossa bo'lsa o'qiydi, metod bo'lsa chaqiradi. */
async function xossaQiymati(obj, nom) {
  try {
    const v = obj[nom];
    if (typeof v === "function") {
      if (v.length > 0) return undefined;     // argument talab qilsa — tegmaymiz
      return await v.call(obj);
    }
    return v;
  } catch (e) { return undefined; }
}

function musbatSon(v) {
  const n = Number(v);
  return (isFinite(n) && n > 1) ? n : 0;
}

/* Montajning kadr o'lchami.
 *
 * Nom bo'yicha taxmin qilmaymiz — obyektni kezib chiqamiz va eni/bo'yiga
 * o'xshagan nomlarni o'zimiz topamiz. Shu tufayli Premiere versiyalari
 * orasidagi nom farqi ahamiyatini yo'qotadi. */
async function seqOlchami(seq) {
  olchamSabab = "";
  if (!seq) { olchamSabab = "sequence yo'q"; return null; }

  const manbalar = [];
  try {
    if (typeof seq.getSettings === "function") {
      const st = await seq.getSettings();
      if (st) manbalar.push(["settings", st]);
    }
  } catch (e) { olchamSabab = "getSettings: " + (e.message || e); }
  manbalar.push(["sequence", seq]);

  const korilgan = [];
  for (const juft of manbalar) {
    const qayer = juft[0], obj = juft[1];
    const nomlar = xossaNomlari(obj);
    korilgan.push(qayer + ": " + (nomlar.slice(0, 8).join(", ") || "bo'sh"));

    // 1-yo'l: eng ehtimolli nomlar
    const aniq = [
      ["videoFrameWidth", "videoFrameHeight"],
      ["frameSizeHorizontal", "frameSizeVertical"],
      ["videoFrameSizeHorizontal", "videoFrameSizeVertical"],
      ["getVideoFrameWidth", "getVideoFrameHeight"],
      ["width", "height"],
    ];
    for (const nom of aniq) {
      const w = musbatSon(await xossaQiymati(obj, nom[0]));
      const h = musbatSon(await xossaQiymati(obj, nom[1]));
      if (w && h) return { w: w, h: h, qayerdan: qayer + "." + nom[0] };
    }

    // 2-yo'l: nomni o'zimiz qidiramiz
    const eni = nomlar.filter((n) => /width|horizontal/i.test(n)
                                     && !/pixel|aspect|par/i.test(n));
    const boyi = nomlar.filter((n) => /height|vertical/i.test(n)
                                      && !/pixel|aspect|par/i.test(n));
    for (const wn of eni) {
      const w = musbatSon(await xossaQiymati(obj, wn));
      if (!w) continue;
      for (const hn of boyi) {
        const h = musbatSon(await xossaQiymati(obj, hn));
        if (h) return { w: w, h: h, qayerdan: qayer + "." + wn };
      }
    }

    // 3-yo'l: ichma-ich obyekt — {frameSize: {width, height}}
    for (const n of nomlar) {
      if (!/frame|size|resolution/i.test(n)) continue;
      const v = await xossaQiymati(obj, n);
      if (!v || typeof v !== "object") continue;
      const w = musbatSon(v.width || v.horizontal || v.w);
      const h = musbatSon(v.height || v.vertical || v.h);
      if (w && h) return { w: w, h: h, qayerdan: qayer + "." + n };
    }
  }

  olchamSabab = (olchamSabab ? olchamSabab + " · " : "")
              + "o'lcham topilmadi · " + korilgan.join(" · ");
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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
  els.log.innerHTML = ""; logOchi(false);
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

/* Motion (Scale/Position) va KEYFRAME imkoniyatini tekshiradi.
 *
 * Zoom, kadrni surish, «harakat qo'shish» — hammasi shu ikki narsaga
 * bog'liq: Motion parametrini o'zgartira olamizmi va unga keyframe
 * qo'ya olamizmi. Statik qiymatni o'zgartirish sinalgan (9:16 ga
 * o'tkazishda ishlatamiz), keyframe esa Premiere versiyasiga qarab
 * bo'lishi ham, bo'lmasligi ham mumkin. Shuni bir bosishda aniqlaymiz. */
async function dumpMotion(ppro, seq) {
  try {
    if (!seq) return;
    const n = await seq.getVideoTrackCount();
    let item = null;
    for (let i = 0; i < n && !item; i++) {
      const tr = await seq.getVideoTrack(i);
      if (!tr) continue;
      const items = await tr.getTrackItems(clipTypeConst(ppro), false);
      if (items && items.length) item = items[0];
    }
    if (!item) { logLine("Motion: timeline'da video klip topilmadi"); return; }

    const chain = await item.getComponentChain();
    const cnt = await chain.getComponentCount();
    const nomlar = [];
    let scaleParam = null;
    for (let c = 0; c < cnt; c++) {
      const comp = await chain.getComponentAtIndex(c);
      let nom = "";
      try { nom = await comp.getMatchName(); } catch (e) { nom = "?"; }
      let dn = "";
      try { dn = await comp.getDisplayName(); } catch (e) { dn = ""; }
      nomlar.push(dn || nom);
      if (!scaleParam) {
        try { scaleParam = await comp.getParam("Scale"); } catch (e) { /* yo'q */ }
      }
    }
    logLong("Effektlar zanjiri", nomlar.join(", "));
    if (!scaleParam) { logLine("Motion: «Scale» parametri topilmadi", "warn"); }
    else {
      const m = methodNames(scaleParam);
      logLong("Scale parametri metodlari", m.join(", "));
      const kf = m.filter((x) => /[Kk]eyframe|TimeVarying|Interpolation/.test(x));
      if (kf.length) {
        logLine("KEYFRAME QO'YSA BO'LADI ✓ — " + kf.join(", "), "okline");
      } else {
        logLine("Keyframe metodlari topilmadi — harakat XML orqali "
                + "qo'shiladi (u ham ishlaydi, faqat yangi sequence yasaydi).",
                "warn");
      }
    }
  } catch (e) {
    logLine("Motion tashxisi chiqmadi: " + (e.message || e), "warn");
  }
}


async function dumpApi(ppro, seq) {
  try {
    // xossaNomlari — prototipni ham kezadi. Object.keys() native
    // obyektlarda bo'sh qaytaradi va tashxisni ko'r qilib qo'yadi.
    logLong("API (premierepro)", xossaNomlari(ppro || {}).join(", "));
    if (ppro && ppro.TickTime) {
      logLong("TickTime", Object.getOwnPropertyNames(ppro.TickTime).join(", "));
    }
    if (ppro && ppro.SequenceEditor) {
      logLong("SequenceEditor",
              Object.getOwnPropertyNames(ppro.SequenceEditor).join(", "));
    }
    if (seq) {
      logLong("Sequence metodlari", methodNames(seq).join(", "));

      // Sequence'ni JOYIDA o'zgartirish mumkinmi — kesish, siljitish,
      // olib tashlash. Bu yo'l bo'lsa, Cut yangi sequence yasamasdan
      // montajning o'zini qirqishi mumkin.
      try {
        const ed = ppro.SequenceEditor.getEditor(seq);
        const m = methodNames(ed);
        logLong("SequenceEditor metodlari", m.join(", "));
        const kesish = m.filter((x) =>
          /remove|delete|lift|extract|ripple|trim|razor|split|move/i.test(x));
        logLine(kesish.length
          ? "Joyida kesish uchun: " + kesish.join(", ")
          : "SequenceEditor'da kesish/olib tashlash metodi topilmadi", 
          kesish.length ? "okline" : "warn");
      } catch (e) {
        logLine("SequenceEditor o'qilmadi: " + (e.message || e), "warn");
      }

      // Klipning o'zini siljitish/qirqish mumkinmi
      try {
        const tr = await seq.getVideoTrack(0);
        const items = tr ? await tr.getTrackItems(clipTypeConst(ppro), false) : [];
        if (items.length) {
          const m = methodNames(items[0]);
          logLong("TrackItem metodlari", m.join(", "));
          const ozgartir = m.filter((x) => /create(Set|Move|Remove)/i.test(x));
          logLine(ozgartir.length
            ? "Klipni o'zgartirish uchun: " + ozgartir.join(", ")
            : "TrackItem'da o'zgartirish metodi topilmadi",
            ozgartir.length ? "okline" : "warn");
        }
      } catch (e) {
        logLine("TrackItem o'qilmadi: " + (e.message || e), "warn");
      }
      // Montaj o'lchami — eng ko'p muammo chiqqan joy. Qayerdan
      // topilgani ham yoziladi, chunki nomlar versiyaga qarab o'zgaradi.
      const o = await seqOlchami(seq);
      if (o) logLine("Montaj o'lchami: " + o.w + "x" + o.h
                     + "  (" + o.qayerdan + ") ✓", "okline");
      else logLine("Montaj o'lchami topilmadi: " + olchamSabab, "warn");
      try {
        const st = await seq.getSettings();
        if (st) logLong("Sequence sozlamalari", xossaNomlari(st).join(", "));
      } catch (e) { logLine("getSettings: " + (e.message || e), "warn"); }
    }
    await dumpMotion(ppro, seq);
  } catch (e) {
    logLine("Tashxis to'liq chiqmadi: " + (e.message || e), "warn");
  }
  await copyLog();        // to'liq matnni faylga (yoki buferga) olib qo'yamiz
}



/* Markerlardan oraliqlar.
 *
 * Bu yerda uchta holat aniq hal qilinishi kerak, aks holda natija
 * kutilmagan chiqadi:
 *
 *   1. IKKI MARKER YAQIN. Agar markerlarning O'ZI yaqin bo'lsa (8 soniya
 *      ichida) — bu bitta joy, ikki marta belgilangan: birlashtiramiz.
 *      Lekin ular uzoqroq bo'lsa (masalan 20 soniya), bu IKKI BOSHQA joy.
 *      Ilgari oyna ustma-ust tushgani uchun ular ham birlashardi va
 *      to'rtta marker bitta 105 soniyalik bo'lakka aylanib ketardi.
 *      Endi birlashtirmaymiz — oldingisining oxirini keyingisi
 *      boshlanadigan joyga qisqartiramiz. Shunda ikki bo'lak chiqadi va
 *      bir kadr ikki marta tushmaydi.
 *
 *   2. BO'LAK UZUN. Instagram Reels chegarasi 90 soniya. Avtomatik
 *      oynadan yoki birlashishdan uzun chiqsa — qisqartiramiz.
 *      Markerni O'ZINGIZ cho'zib belgilagan bo'lsangiz — tegmaymiz
 *      (siz ataylab shunday qilgansiz), faqat ogohlantiramiz.
 *
 *   3. BO'LAK JUDA QISQA. 3 soniyadan qisqasi ishlatib bo'lmaydi —
 *      olib tashlaymiz va sababini aytamiz.
 */
const BIRLASHISH = 8;    // markerlar shu masofadan yaqin bo'lsa — bitta joy
const MAX_BOLAK = 90;    // Instagram Reels chegarasi (soniya)
const MIN_BOLAK = 3;

function markerOraliqlari(markers, oldin, keyin) {
  const xom = markers.map((mk) => {
    const t = Math.max(0, Number(mk.start) || 0);
    const uz = Number(mk.duration) || 0;
    return uz > 0.05
      ? { t: t, a: t, b: t + uz, aniq: true }
      : { t: t, a: Math.max(0, t - oldin), b: t + keyin, aniq: false };
  }).sort((x, y) => x.t - y.t);

  // 0-qadam: cho'zib belgilangan oraliq ICHIGA tushgan oddiy markerni
  // yutamiz. Aks holda o'zingiz aniq belgilagan oraliq shu markerda
  // ikkiga bo'linib ketardi — siz esa uni butun deb belgilagansiz.
  const aniqlar = xom.filter((r) => r.aniq);
  const qolgan = xom.filter((r) => r.aniq
      || !aniqlar.some((q) => r.t >= q.a - 0.05 && r.t <= q.b + 0.05));

  // 1-qadam: markerlarning o'zi yaqin bo'lsa — birlashtiramiz
  const birlashgan = [];
  for (const r of qolgan) {
    const oxirgi = birlashgan[birlashgan.length - 1];
    if (oxirgi && r.t - oxirgi.t <= BIRLASHISH) {
      oxirgi.a = Math.min(oxirgi.a, r.a);
      oxirgi.b = Math.max(oxirgi.b, r.b);
      oxirgi.aniq = oxirgi.aniq || r.aniq;
      oxirgi.qoshildi = (oxirgi.qoshildi || 1) + 1;
    } else {
      birlashgan.push(Object.assign({}, r));
    }
  }

  // 2-qadam: ustma-ust tushgan chegaralarni qisqartiramiz —
  // bir kadr ikki bo'lakka tushmasin
  for (let i = 0; i < birlashgan.length - 1; i++) {
    const cur = birlashgan[i], next = birlashgan[i + 1];
    if (cur.b > next.a) {
      cur.b = next.a;
      cur.qisqartirildi = true;
    }
  }

  // 3-qadam: uzunlik chegaralari
  const out = [];
  for (const r of birlashgan) {
    const uzunlik = r.b - r.a;
    if (uzunlik < MIN_BOLAK) {
      out.push({ a: r.a, b: r.b, aniq: r.aniq, qoshildi: r.qoshildi,
                 qisqa: true });
      continue;
    }
    if (uzunlik > MAX_BOLAK) {
      if (r.aniq) {
        r.uzun = true;              // o'zingiz belgilagansiz — tegmaymiz
      } else {
        r.b = r.a + MAX_BOLAK;
        r.cheklandi = true;
      }
    }
    out.push(r);
  }
  return out;
}

async function markerlardanYigish() {
  songgiIsh = { nomi: "Qayta urinish", fn: markerlardanYigish };
  els.log.innerHTML = ""; logOchi(false);
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
    const qisqalar = oraliqlar.filter((r) => r.qisqa);
    const ishga = oraliqlar.filter((r) => !r.qisqa);
    logLine(markers.length + " marker → " + ishga.length + " bo'lak:");
    for (const r of oraliqlar) {
      const izoh = [];
      if (r.qoshildi) izoh.push(r.qoshildi + " marker birlashdi (yaqin turgan)");
      if (r.aniq) izoh.push("marker uzunligi bo'yicha");
      if (r.qisqartirildi) izoh.push("keyingi markergacha qisqartirildi");
      if (r.cheklandi) izoh.push("Reels chegarasi " + MAX_BOLAK + "s ga kesildi");
      if (r.uzun) izoh.push("DIQQAT: " + MAX_BOLAK + "s dan uzun — Instagram "
                            + "qabul qilmasligi mumkin");
      if (r.qisqa) izoh.push("juda qisqa — o'tkazib yuborildi");
      logLine("   " + tc(r.a) + "–" + tc(r.b) + "  ("
              + Math.round(r.b - r.a) + "s)"
              + (izoh.length ? " — " + izoh.join(", ") : ""),
              (r.qisqa || r.uzun) ? "warn" : null);
    }
    if (qisqalar.length) {
      logLine(qisqalar.length + " ta bo'lak " + MIN_BOLAK + " soniyadan "
              + "qisqa bo'lgani uchun olinmadi.", "warn");
    }
    if (!ishga.length) {
      throw new Error("Ishlatsa bo'ladigan bo'lak qolmadi — markerlarni "
                      + "biroz uzoqroqqa qo'ying yoki cho'zib belgilang.");
    }

    await oraliqlardanYigish(ishga, "Podcast Suite — Markerlar");
  } catch (e) {
    logLine("To'xtadi: " + (e.message || e), "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
}


/* Berilgan oraliqlarni Premiere ichida kesib, BITTA sequence'ga yig'adi.
 *
 * Oraliqlar qayerdan kelgani muhim emas — markerdanmi yoki transkriptdan
 * tanlanganmi. Shu tufayli ikkala yo'l ham bir xil, sinalgan kod bo'ylab
 * ketadi: bittasini tuzatsak, ikkinchisi ham tuzaladi.
 */
async function oraliqlardanYigish(ishga, natijaNomi0) {
  let step = "boshlanish";
  const made = [];
  let ppro = null, lastSeq = null;
  try {
    ppro = require("premierepro");
    step = "ochiq sequence";
    const first = await freshSequence(ppro);
    lastSeq = first.seq;
    let oldIn = null, oldOut = null;
    try {
      oldIn = await first.seq.getInPoint();
      oldOut = await first.seq.getOutPoint();
    } catch (e) { /* o'qilmasa — tiklamaymiz */ }
    logLine("Manba: " + (first.seq.name || "sequence"));

    for (let i = 0; i < ishga.length; i++) {
      const r = ishga[i];
      paintJob({ steps: [], step: 0, lines: [],
                 stage: "Bo'lak " + (i + 1) + " / " + ishga.length,
                 percent: i / ishga.length * 100,
                 overall: i / ishga.length * 100,
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
    let natijaNomi = natijaNomi0 || "Podcast Suite — Bo'laklar";
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
                   overall: i / made.length * 100,
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



/* ======================================================= Matndan tanlash
 *
 * Muammo: 1,5 soatlik podkastdan qiziq joyni topish uchun uni eshitib
 * chiqish kerak — bu bir yarim soat. Marker qo'yish ham shu vaqtni
 * talab qiladi, chunki baribir eshitish kerak.
 *
 * Yechim: epizod bir marta matnga aylantiriladi (Captions moduli), keyin
 * matn O'QILADI. O'qish eshitishdan 5-10 barobar tez, ustiga qidiruv
 * bor: «pul», «birinchi marta» deb yozib, kerakli joyga sakraysiz.
 *
 * Tanlangan qatorlar oraliqqa aylanadi va markerlar bilan bir xil yo'ldan
 * — Premiere ichida — kesiladi, ya'ni kadr, ovoz va grafika joyida
 * qoladi.
 */
let trLines = [];        // [{start, end, text}]
let trTanlangan = {};    // indeks -> true

function trRender(filtr) {
  const box = els.trList;
  box.innerHTML = "";
  const q = (filtr || "").trim().toLowerCase();
  let korindi = 0;
  for (let i = 0; i < trLines.length; i++) {
    const ln = trLines[i];
    const mos = !q || (ln.text || "").toLowerCase().indexOf(q) >= 0;
    if (q && !mos) continue;
    korindi++;
    const row = document.createElement("div");
    row.className = "trline" + (trTanlangan[i] ? " on" : "")
                  + (q && mos ? " hit" : "");
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = tc(ln.start);
    const x = document.createElement("span");
    x.className = "x";
    x.textContent = ln.text;
    row.appendChild(t); row.appendChild(x);
    row.addEventListener("click", () => {
      if (trTanlangan[i]) { delete trTanlangan[i]; }
      else { trTanlangan[i] = true; goToTime(ln.start); }
      trRender(els.trSearch.value);
    });
    box.appendChild(row);
  }
  if (!trLines.length) {
    box.innerHTML = '<div class="trline"><span class="x">Matn hali '
                  + 'yuklanmagan — «Matnni yuklash» ni bosing</span></div>';
  } else if (!korindi) {
    box.innerHTML = '<div class="trline"><span class="x">«' + q
                  + '» topilmadi</span></div>';
  }
  // Ko'rsatma faqat boshida kerak. Matn yuklangach uni yashiramiz —
  // dok panelida balandlik tor va ro'yxatga joy kerak.
  const tip = document.getElementById("trTip");
  if (tip) tip.style.display = trLines.length ? "none" : "";

  const oraliqlar = trOraliqlar();
  els.trBtn.disabled = !oraliqlar.length;
  els.trBtn.textContent = oraliqlar.length
    ? "Tanlanganlardan yig'ish (" + oraliqlar.length + ")"
    : "Tanlanganlardan yig'ish";
}

/* Ketma-ket tanlangan qatorlar bitta bo'lakka qo'shiladi. Orada tanlanmagan
   qator bo'lsa — yangi bo'lak boshlanadi. Shu tufayli bir gapni to'liq
   tanlash uchun qatorlarni ketma-ket bosish yetadi. */
function trOraliqlar() {
  const idx = Object.keys(trTanlangan).map(Number).sort((a, b) => a - b);
  const out = [];
  for (const i of idx) {
    const ln = trLines[i];
    if (!ln) continue;
    const oxirgi = out[out.length - 1];
    if (oxirgi && oxirgi.oxirgiIdx === i - 1) {
      oxirgi.b = ln.end;
      oxirgi.oxirgiIdx = i;
      oxirgi.qatorlar++;
    } else {
      out.push({ a: ln.start, b: ln.end, oxirgiIdx: i, qatorlar: 1 });
    }
  }
  // Chetlariga ozgina zaxira: gapning boshi/oxiri kesilib qolmasin
  for (const r of out) {
    r.a = Math.max(0, r.a - 0.35);
    r.b = r.b + 0.45;
  }
  return out;
}

async function trYuklash() {
  if (!(await checkMotor())) return;
  els.log.innerHTML = ""; logOchi(false);
  els.trLoad.textContent = "Yuklanmoqda…";
  try {
    const body = {};
    if (timeline) body.timeline = timeline;
    body.files = picked.map((p) => p.path);
    if (!body.files.length && !timeline) {
      throw new Error("Avval «Ochiq sequence'ni olish» ni bosing yoki "
                      + "fayllarni tanlang");
    }
    const r = await fetch(MOTOR + "/transkript", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    trLines = j.lines || [];
    trTanlangan = {};
    trRender("");
    const soz = trLines.reduce((n, l) => n + (l.text || "").split(/\s+/).length, 0);
    logLine(trLines.length + " qator, ~" + soz + " so'z yuklandi"
            + (j.title ? " — «" + j.title + "»" : ""), "okline");
    logLine("Qidiruv maydoniga so'z yozing yoki ro'yxatni ko'zdan kechiring. "
            + "Qatorni bosing — playhead o'sha joyga boradi va qator tanlanadi.");
  } catch (e) {
    logLine("Matn yuklanmadi: " + e.message, "warn");
  }
  els.trLoad.textContent = "Matnni yuklash";
}

async function trYigish() {
  const oraliqlar = trOraliqlar();
  if (!oraliqlar.length) return;
  els.log.innerHTML = ""; logOchi(false);
  startProgress("Tanlangan joylar olinmoqda…");
  logLine(Object.keys(trTanlangan).length + " qator → "
          + oraliqlar.length + " bo'lak:");
  const ishga = [];
  for (const r of oraliqlar) {
    const uzunlik = r.b - r.a;
    const rec = { a: r.a, b: r.b };
    if (uzunlik > MAX_BOLAK) { rec.b = r.a + MAX_BOLAK; rec.cheklandi = true; }
    if (uzunlik < MIN_BOLAK) {
      logLine("   " + tc(r.a) + "–" + tc(r.b) + "  ("
              + Math.round(uzunlik) + "s) — juda qisqa, olinmadi", "warn");
      continue;
    }
    logLine("   " + tc(rec.a) + "–" + tc(rec.b) + "  ("
            + Math.round(rec.b - rec.a) + "s, " + r.qatorlar + " qator)"
            + (rec.cheklandi ? " — " + MAX_BOLAK + "s ga kesildi" : ""));
    ishga.push(rec);
  }
  if (!ishga.length) {
    logLine("Ishlatsa bo'ladigan bo'lak qolmadi — ko'proq qator tanlang.",
            "warn");
    stopProgress(false, "bo'lak yo'q");
    return;
  }
  await oraliqlardanYigish(ishga, "Podcast Suite — Matndan");
}


/* ========================================================= Harakat
 *
 * Statik kameradan olingan podkastda kadr o'nlab daqiqa qimirlamaydi va
 * tomoshabin zerikadi. Bu yerda har klipga sekin harakat qo'shiladi:
 * tanlangan oraliqda kadr yaqinlashadi, keyin to'xtab turadi, keyin
 * uzoqlashadi. Ketma-ket kliplar turlicha qirqiladi.
 *
 * Rejani motor tuzadi (qaysi soniyada qancha), panel esa uni
 * Premiere'ning Motion > Scale parametriga yozadi.
 */
let harOraliq = 15, harRejim = "kesim", harDaraja = "orta";

/* Scale parametriga keyframe qo'yish.
 *
 * Premiere versiyasiga qarab bu metodlar bor yoki yo'q. Shuning uchun
 * nomini oldindan tekshiramiz va yo'q bo'lsa — kamida klipga statik
 * qirqim beramiz (harakatsiz, lekin har plan boshqacha bo'ladi).
 * Jimgina ishlamay qo'yishdan ko'ra, yarim natija va ochiq xabar
 * yaxshiroq.
 */
function keyframeUsuli(param) {
  const bor = (n) => typeof param[n] === "function";
  return {
    vaqtli: bor("createSetTimeVaryingAction") ? "createSetTimeVaryingAction" : null,
    qoy: bor("createSetValueAtKeyframeAction") ? "createSetValueAtKeyframeAction"
       : bor("createAddKeyframeAction") ? "createAddKeyframeAction" : null,
    statik: bor("createSetValueAction") ? "createSetValueAction" : null,
  };
}

/* Butun montajning NUSXASINI yasaydi.
 *
 * Asl montajga tegmaslik uchun. Harakat yoqmasa, foydalanuvchi shunchaki
 * nusxani o'chiradi va asl montaji joyida turadi. Ikkalasi yonma-yon
 * turgani uchun taqqoslash ham oson.
 *
 * Yo'li: in/out nuqtalarini butun montajga qo'yamiz va
 * createSubsequence chaqiramiz — bu markerlardan yig'ishda sinalgan
 * usul. Natijada timeline'da NIMA bo'lsa hammasi ko'chadi: kadr, ovoz,
 * matn, grafika, effektlar, multicam.
 */
async function sequenceNusxasi(ppro, project, seq) {
  // Foydalanuvchi qo'ygan in/out belgilarini eslab qolamiz — nusxa
  // yasash uchun ularni vaqtincha o'zgartiramiz, keyin tiklaymiz.
  let eskiIn = null, eskiOut = null;
  try {
    eskiIn = secs(await seq.getInPoint());
    eskiOut = secs(await seq.getOutPoint());
  } catch (e) { /* o'qilmasa — tiklamaymiz */ }

  const oxir = secs(await seq.getEndTime());
  if (!(oxir > 0)) throw new Error("Montaj uzunligi o'qilmadi");
  await setSeqInOut(ppro, project, seq, 0, oxir);

  // finally SHART: nusxa yasash yiqilsa ham foydalanuvchining in/out
  // belgilari tiklanishi kerak. Aks holda ish to'xtaydi-yu, montajdagi
  // belgilar butun timeline'ga cho'zilib qoladi va buni foydalanuvchi
  // o'zi sezmasdan yo'qotadi.
  let sub = null;
  try {
    try {
      // `true` — trek nishonlashiga qaramaydi, ya'ni HAMMA trek ko'chadi
      sub = await seq.createSubsequence(true);
    } catch (e) {
      sub = await seq.createSubsequence();
    }
  } finally {
    if (eskiIn !== null && eskiOut !== null && eskiOut > eskiIn) {
      try { await setSeqInOut(ppro, project, seq, eskiIn, eskiOut); }
      catch (e) { /* tiklanmasa ham qolganini davom ettiramiz */ }
    }
  }
  if (!sub) throw new Error("Montaj nusxasi yasalmadi");
  return sub;
}


async function harakatQoshish() {
  songgiIsh = { nomi: "Qayta urinish", fn: harakatQoshish };
  els.log.innerHTML = ""; logOchi(false);
  startProgress("Montaj nusxasi yasalmoqda…");
  let step = "boshlanish";
  try {
    if (!(await checkMotor())) { stopProgress(false, "motor yo'q"); return; }
    const ppro = require("premierepro");

    step = "ochiq sequence";
    const project = await ppro.Project.getActiveProject();
    if (!project) throw new Error("Ochiq loyiha yo'q");
    const asl = await project.getActiveSequence();
    if (!asl) {
      throw new Error("Ochiq sequence yo'q — Premiere'da montajni oching "
                      + "(Project panelidan sequence'ni ikki marta bosing)");
    }
    // Nom cho'zilib ketmasin: nusxadan nusxa olinsa «— harakat» qayta-qayta
    // qo'shilib, «C0430 — harakat — harakat — harakat» bo'lib ketardi.
    const aslNomi = String(asl.name || "Montaj").replace(/(\s*—\s*harakat)+$/, "");

    step = "montaj nusxasi";
    logLine("Asl montajga tegilmaydi — nusxa yasalmoqda…");
    // O'lchamni ASL montajdan o'qiymiz — nusxa bilan aynan bir xil
    // bo'ladi. Nusxadan o'qish ishonchsiz: createSubsequence qaytargan
    // obyektda getSettings boshqacha ishlashi mumkin, va aynan shu
    // sabab ish «Sequence o'lchami o'qilmadi» deb to'xtagan edi.
    let olcham = await seqOlchami(asl);
    const aslSabab = olchamSabab;

    const seq = await sequenceNusxasi(ppro, project, asl);
    const nusxaNomi = aslNomi + " — harakat";
    try {
      const pi = await seq.getProjectItem();
      if (pi && typeof pi.createSetNameAction === "function") {
        runActions(project, () => [pi.createSetNameAction(nusxaNomi)], "Nom");
      }
    } catch (e) { /* nom qo'yilmasa ham nusxa joyida */ }
    logLine("Nusxa yasaldi: «" + nusxaNomi + "» ✓", "okline");
    try { await sequenceOchish(ppro, project, seq, nusxaNomi); }
    catch (e) { logLine("  (nusxa o'zi ochilmadi — Project panelidan oching)"); }

    // Asldan chiqmasa — nusxadan sinab ko'ramiz
    if (!olcham || !olcham.w) olcham = await seqOlchami(seq);
    if (!olcham || !olcham.w) {
      throw new Error("Montaj o'lchamini o'qib bo'lmadi (kadr eni va "
                      + "bo'yi). Asl montaj: " + (aslSabab || "?")
                      + " · Nusxa: " + (olchamSabab || "?")
                      + ". Motor qatoridagi «tekshirish» ni bosib, log'ni "
                      + "yuboring.");
    }
    logLine("Montaj: " + olcham.w + "x" + olcham.h);

    // FAQAT ASOSIY KADR. Yuqoridagi treklarda b-roll, grafika, logotip,
    // qoplama turadi — ularga zoom qo'shish montajni buzadi: b-roll
    // ataylab tanlangan kadrda turadi va uni kattalashtirish kerak emas.
    //
    // Shuning uchun asosiy trek (eng pastki, V1) olinadi. Yuqoridagi
    // trekdagi klip esa faqat AYNAN SHU fayllardan biri bo'lsa qo'shiladi
    // — ya'ni asosiy kadrning nusxasi (masalan kesib, tepaga ko'chirilgan).
    // Boshqa fayl bo'lsa — bu b-roll, tegilmaydi.
    step = "kliplarni o'qish";
    const items = [], clips = [];
    const n = await seq.getVideoTrackCount();
    const oqi = async (tr) => {
      const out = [];
      if (!tr) return out;
      for (const it of await tr.getTrackItems(clipTypeConst(ppro), false)) {
        const path = await mediaPathOf(ppro, it);
        if (!path) { out.push(null); continue; }
        const st = secs(await it.getStartTime());
        const en = secs(await it.getEndTime());
        const ip = secs(await it.getInPoint());
        if (en <= st) continue;
        // Ikki xil davomiylik, va ular TENG EMAS:
        //   tl  — klip timeline'da qancha turadi (tomoshabin ko'radigan vaqt)
        //   op  — manbadagi out nuqtasi
        // Tezlik o'zgartirilgan klipda (50% yoki 200%) ular farq qiladi.
        // Reja timeline sezimida tuziladi, keyframe esa MANBA vaqt o'qiga
        // yoziladi — shuning uchun ikkalasi ham kerak.
        let op = ip + (en - st);
        try {
          const o = secs(await it.getOutPoint());
          if (typeof o === "number" && o > ip) op = o;
        } catch (e) { /* o'qilmasa timeline uzunligini olamiz */ }
        out.push({ it: it, path: path, start: st, in: ip,
                   out: ip + (en - st),      // motor uchun: timeline uzunligi
                   manbaOut: op, tl: en - st });
      }
      return out;
    };

    const v1Xom = await oqi(await seq.getVideoTrack(0));
    const asosiy = v1Xom.filter(Boolean);
    const yolsiz = v1Xom.length - asosiy.length;
    if (!asosiy.length) {
      throw new Error(yolsiz
        ? "V1 dagi " + yolsiz + " klipning ortida fayl yo'q (multicam yoki "
          + "nested sequence). Harakat bunday klipga tegib bo'lmaydi — "
          + "avval ularni oddiy klipga aylantiring."
        : "Eng pastki video trekda (V1) klip topilmadi.");
    }
    const asosiyFayllar = new Set(asosiy.map((c) => c.path));
    for (const c of asosiy) { items.push(c.it); clips.push(c); }

    let nusxa = 0, broll = 0, tepaYolsiz = 0;
    const brollNomlari = new Set();
    for (let i = 1; i < n; i++) {
      for (const c of await oqi(await seq.getVideoTrack(i))) {
        // Ortida fayl yo'q (multicam/nested/adjustment layer). Buni
        // JIMGINA tashlab ketish mumkin emas: montajchi o'sha kliplarga
        // ham harakat tushdi deb o'ylaydi.
        if (!c) { tepaYolsiz++; continue; }
        if (asosiyFayllar.has(c.path)) {
          items.push(c.it); clips.push(c); nusxa++;
        } else {
          broll++; brollNomlari.add(c.path.split("/").pop());
        }
      }
    }
    logLine("V1 (asosiy kadr): " + asosiy.length + " klip");
    if (yolsiz) {
      logLine(yolsiz + " klipning ortida fayl yo'q (multicam/nested) — "
              + "tegilmadi", "warn");
    }
    if (nusxa) logLine("Yuqoridagi treklardan: " + nusxa
                       + " klip (asosiy kadrning nusxasi)");
    if (tepaYolsiz) {
      logLine("Yuqoridagi treklarda " + tepaYolsiz + " klipning ortida fayl "
              + "yo'q (multicam / nested / adjustment layer) — ularga "
              + "tegilmadi", "warn");
    }
    if (broll) {
      logLine(broll + " klipga tegilmaydi — b-roll/grafika, boshqa fayl:");
      for (const nm of Array.from(brollNomlari).slice(0, 5)) {
        logLine("   " + nm);
      }
      if (brollNomlari.size > 5) {
        logLine("   … yana " + (brollNomlari.size - 5) + " fayl");
      }
    }

    step = "reja so'rash";
    const r = await fetch(MOTOR + "/harakat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clips: clips, width: olcham.w, height: olcham.h,
                             oraliq: harOraliq, rejim: harRejim,
                             daraja: harDaraja }),
    });
    const jj = await r.json();
    if (!r.ok) throw new Error(jj.error || "Motor xatosi");
    for (const l of (jj.log || [])) logLine(l);
    if (!jj.rejalar.length) {
      throw new Error("Hech bir klipga harakat qo'shib bo'lmadi — manba "
                      + "montajdan kattaroq bo'lishi kerak (masalan 4K "
                      + "manba, 1080p montaj).");
    }

    // Ikki bosqich. Avval parametrlar topiladi (bu async ish), keyin
    // hamma o'zgarish BITTA tranzaksiyada bajariladi.
    //
    // Nima uchun bitta: har klip alohida tranzaksiya bo'lsa, Premiere
    // tarixida har biri alohida qadam bo'lib qoladi va 200 klipli
    // montajni bekor qilish uchun 200 marta Cmd+Z bosish kerak bo'ladi.
    step = "parametrlarni topish";
    const tayyor = [];
    let topilmadi = 0, usulAytildi = false, birinchiXato = "";
    for (let i = 0; i < jj.rejalar.length; i++) {
      const reja = jj.rejalar[i];
      // Umumiy foiz: parametrlarni topish ishning ~85% i, yozish qolgani.
      // «overall» berilmasa chiziq to'lmaydi va «qancha qoldi» chiqmaydi —
      // aynan shu sabab foydalanuvchi «qotib qoldi» deb o'ylagan edi.
      paintJob({ steps: [], step: 0, lines: [],
                 stage: "Klip o'qilmoqda " + (i + 1) + " / " + jj.rejalar.length,
                 percent: i / jj.rejalar.length * 100,
                 overall: i / jj.rejalar.length * 85,
                 detail: reja.nomi });
      const item = items[reja.idx];
      const klip = clips[reja.idx];
      if (!item) { topilmadi++; continue; }
      try {
        const chain = await item.getComponentChain();
        const cnt = await chain.getComponentCount();
        let param = null;
        for (let c = 0; c < cnt && !param; c++) {
          const comp = await chain.getComponentAtIndex(c);
          try { param = await comp.getParam("Scale"); } catch (e) { param = null; }
        }
        if (!param) {
          topilmadi++;
          if (!birinchiXato) birinchiXato = "«Scale» parametri topilmadi";
          continue;
        }

        // Ikkinchi marta bosilsa qiymatlar KO'PAYIB ketmasin.
        //
        // Parametr allaqachon keyframe qilingan bo'lsa, getValue() barqaror
        // asosni emas, o'sha paytdagi harakatlangan qiymatni qaytaradi.
        // Uni asos qilib olsak, har bosishda kadr yana kattalashaveradi va
        // sifat chegarasidan jimgina oshib ketadi. Shuning uchun avval
        // keyframe'larni o'chirib, parametrni tinch holatga qaytaramiz.
        try {
          if (typeof param.isTimeVarying === "function"
              && typeof param.createSetTimeVaryingAction === "function"
              && await param.isTimeVarying()) {
            runActions(project, () => [param.createSetTimeVaryingAction(false)],
                       "Eski keyframe'larni tozalash");
          }
        } catch (e) { /* tozalanmasa — pastdagi tekshiruv ushlaydi */ }

        // ASOSNI O'QIY OLMASAK — KLIPGA TEGMAYMIZ.
        //
        // Ilgari bu holatda 100 deb olinardi, lekin asos faqat o'qish
        // uchun emas — u yoziladi ham. Ya'ni «o'qiy olmadim» klipni
        // chetlab o'tish o'rniga uning Scale qiymatini 100% ga majburan
        // tushirardi va 9:16 montajda kadr kichrayib, tepa-pastda qora
        // yo'l paydo bo'lardi.
        let asos = null;
        try {
          const v = await param.getValue();
          if (typeof v === "number" && v > 0) asos = v;
        } catch (e) {
          if (!birinchiXato) birinchiXato = "Scale qiymati o'qilmadi: " + (e.message || e);
        }
        if (asos === null) {
          topilmadi++;
          if (!birinchiXato) birinchiXato = "Scale qiymati son emas";
          continue;
        }

        let inSec = 0;
        try { inSec = secs(await item.getInPoint()); } catch (e) { inSec = 0; }

        // Tezlik: manba davomiyligi / timeline davomiyligi.
        // 50% tezlikdagi klipda 40 soniyalik timeline bo'lagi manbada 20
        // soniyani egallaydi. Reja timeline sezimida tuzilgani uchun
        // keyframe vaqtini shu koeffitsientga ko'paytiramiz, aks holda
        // harakatning yarmi klipdan tashqarida qolib ketadi.
        let tezlik = 1;
        if (klip && klip.tl > 0 && klip.manbaOut > klip.in) {
          const k = (klip.manbaOut - klip.in) / klip.tl;
          if (k > 0.05 && k < 20) tezlik = k;
        }

        const usul = keyframeUsuli(param);
        if (!usulAytildi) {
          usulAytildi = true;
          if (usul.qoy && usul.vaqtli) {
            logLine("Keyframe qo'yish mumkin ✓ — kadr harakatlanadi", "okline");
          } else {
            logLine("Bu Premiere'da keyframe qo'yib bo'lmadi. Har klipga "
                    + "boshqacha qirqim beriladi (harakatsiz).", "warn");
          }
        }
        tayyor.push({ param: param, keys: reja.keys, asos: asos,
                      inSec: inSec, usul: usul, tezlik: tezlik });
      } catch (e) {
        // Sababni yo'qotmaymiz: aks holda pastda «log'ni yuboring» deb
        // yozamiz-u, log'da bitta ham xato matni bo'lmaydi.
        topilmadi++;
        if (!birinchiXato) birinchiXato = (e.message || String(e));
      }
    }

    if (!tayyor.length) {
      throw new Error("Hech bir klipning «Scale» parametriga yetib bo'lmadi"
                      + (birinchiXato ? ". Sabab: " + birinchiXato : "")
                      + ". Motor qatoridagi «tekshirish» tugmasini bosib, "
                      + "log'ni yuboring.");
    }
    if (birinchiXato && topilmadi) {
      logLine(topilmadi + " klip o'tkazib yuborildi. Birinchi sabab: "
              + birinchiXato, "warn");
    }

    step = "Premiere'ga yozish";
    paintJob({ steps: [], step: 0, lines: [], stage: "Timeline'ga yozilmoqda",
               percent: 100, overall: 90,
               detail: tayyor.length + " klip — bitta qadamda" });
    let harakatli = 0, qirqim = 0, otdi = 0, bosh = 0;
    const yozildi = runActions(project, () => {
      const acts = [];
      for (const t of tayyor) {
        try {
          if (t.usul.qoy && t.usul.vaqtli && t.keys.length > 1) {
            const v = t.param[t.usul.vaqtli](true);
            // Bu action null qaytarsa, keyingi keyframe'lar time-varying
            // qilinmagan parametrga tushadi va hech narsa harakatlanmaydi.
            // runActions yolg'on qiymatni jimgina tashlab yuboradi —
            // shuning uchun bu yerda o'zimiz ushlaymiz.
            if (!v) { bosh++; otdi++; continue; }
            acts.push(v);
            for (const k of t.keys) {
              // k.t — TIMELINE soniyasi, keyframe esa MANBA vaqt o'qiga
              // yoziladi. Tezligi o'zgartirilgan klipda ular teng emas.
              acts.push(t.param[t.usul.qoy](
                tickTime(ppro, t.inSec + k.t * t.tezlik),
                t.asos * (1 + k.d / 100), true));
            }
            harakatli++;
          } else if (t.usul.statik) {
            const orta = t.keys.reduce((a, k) => a + k.d, 0) / t.keys.length;
            acts.push(t.param[t.usul.statik](t.asos * (1 + orta / 100), true));
            qirqim++;
          } else {
            otdi++;
          }
        } catch (e) {
          // Bitta klip yiqilsa qolganlari baribir yoziladi
          otdi++;
        }
      }
      return acts;
    }, "Harakat qo'shish");

    // TRANZAKSIYA HAQIQATAN BAJARILDIMI.
    //
    // Hisoblagichlar action OBYEKTI yasalganda oshiriladi — ya'ni ular
    // «nima qilmoqchi edik» ni sanaydi, «nima bo'ldi» ni emas. Premiere
    // tranzaksiyani xato tashlamasdan rad etsa (false qaytarsa), pastdagi
    // «N klipga harakat qo'shildi ✓» sof yolg'on bo'lardi.
    if (yozildi === false) {
      throw new Error("Premiere o'zgarishlarni qabul qilmadi (tranzaksiya "
                      + "rad etildi). Montaj o'zgarmagan. Premiere'da "
                      + "boshqa amal ketayotgan bo'lishi mumkin — tugashini "
                      + "kutib, qayta urining.");
    }

    logLine("");
    // Haqiqiy Scale qiymatlari — foydalanuvchi Effect Controls'da o'zi
    // tekshira olsin. «Qo'shildi» degan quruq xabar yetarli emas: bir
    // marta hech narsa o'zgarmagani holda ham shunday yozilgan edi.
    if (tayyor.length) {
      const nam = tayyor.slice(0, 4).map(function (t) {
        const d = t.keys[0] ? t.keys[0].d : 0;
        return Math.round(t.asos) + "% → " + Math.round(t.asos * (1 + d / 100)) + "%";
      });
      logLine("Scale qiymatlari (dastlabki kliplar): " + nam.join(" · "));
      logLine("Tekshirish: klipni tanlang > Effect Controls > Motion > Scale");
    }
    if (harakatli) logLine(harakatli + " klipga harakat qo'shildi ✓", "okline");
    if (qirqim) logLine(qirqim + " klipga qirqim berildi", "okline");
    if (otdi || topilmadi) {
      logLine((otdi + topilmadi) + " klipga tegib bo'lmadi"
              + (bosh ? " (" + bosh + " tasida keyframe yoqilmadi)" : ""),
              "warn");
    }
    if (jj.joysiz && jj.joysiz.length) {
      logLine(jj.joysiz.length + " klip manbasi montajdan katta emas — "
              + "ularga tegilmadi (kattalashtirsak rasm xiralashardi):",
              "warn");
      for (const x of jj.joysiz.slice(0, 6)) {
        logLine("   " + x.path + " — " + x.manba + " (" + tc(x.start) + ")");
      }
    }
    logLine("");
    logLine("Natija «" + nusxaNomi + "» sequence'ida. Asl montajingiz "
            + "«" + aslNomi + "» tegilmagan holda turibdi.", "okline");
    logLine("Yoqmasa — nusxani o'chiring, yoki bitta Cmd+Z bosing.");
    stopProgress(true, (harakatli + qirqim) + " klip");
  } catch (e) {
    logLine("To'xtadi (" + step + "): " + (e.message || e), "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
}


/* Gemini transkriptini olib kirish.
 *
 * transcriber.py yasaydigan SRT (yoki JSON) faylni suite arxiviga
 * o'tkazadi. Shundan keyin Intro lahzalarni matn bo'yicha tanlaydi —
 * ilgari u faqat ovoz balandligiga qarab ishlardi.
 *
 * Transkript QAYSI video faylga tegishli ekani muhim: arxivdan aynan
 * shu yo'l bo'yicha qidiriladi. Shuning uchun avval video tanlangan
 * bo'lishi shart.
 */
async function transkriptYuklash() {
  if (!picked.length) {
    logOchi(true);
    logLine("Avval video faylni tanlang yoki «Ochiq sequence'ni olish» ni "
            + "bosing — transkript o'sha faylga bog'lanadi.", "warn");
    return;
  }
  if (!(await checkMotor())) return;

  let fayl = null;
  try {
    fayl = await lfs.getFileForOpening({ allowMultiple: false });
  } catch (e) {
    logLine("Fayl tanlanmadi: " + (e.message || e), "warn");
    return;
  }
  if (!fayl || !fayl.nativePath) return;

  els.trImpHolat.textContent = "yuklanmoqda…";
  try {
    const r = await fetch(MOTOR + "/transkript-import", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fayl: fayl.nativePath, manba: picked[0].path,
                             nomi: picked[0].name.replace(/\.[^.]+$/, "") }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    logOchi(true);
    for (const l of (j.log || [])) logLine(l);
    logLine("Transkript «" + picked[0].name + "» ga bog'landi ✓", "okline");
    logLine("Namuna: " + (j.preview || "").slice(0, 120));
    logLine(activeTab === "captions"
            ? "Endi «Subtitr yasash» ni bosing."
            : "Endi «Lahzalarni topish» ni bosing — matn hisobga olinadi.");
    els.trImpHolat.textContent = j.line_count + " qator ✓";
  } catch (e) {
    logOchi(true);
    logLine("Transkript yuklanmadi: " + (e.message || e), "warn");
    els.trImpHolat.textContent = "";
  }
}


/* Arxivdagi transkriptdan subtitr yasash — whisper'siz.
 *
 * Transkript bir marta olib kirilgan bo'lsa (Gemini yoki whisper —
 * farqi yo'q), subtitr shundan bir soniyada chiqadi. Montaj ochiq
 * bo'lsa vaqtlar montajga ko'chiriladi: xom yozuvda 12-daqiqada
 * aytilgan gap montajda 4-daqiqada turgan bo'lishi mumkin.
 */
async function subtitrYasash() {
  songgiIsh = { nomi: "Qayta urinish", fn: subtitrYasash };
  els.log.innerHTML = ""; logOchi(false);
  if (!(await checkMotor())) return;
  if (!picked.length && !timeline) {
    logOchi(true);
    logLine("Avval video faylni tanlang yoki «Ochiq sequence'ni olish» ni "
            + "bosing.", "warn");
    return;
  }
  startProgress("Subtitr yasalmoqda…");
  try {
    const body = {};
    if (timeline) body.timeline = timeline;
    else body.files = picked.map((p) => p.path);
    const r = await fetch(MOTOR + "/subtitr", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    logOchi(true);
    for (const l of (j.log || [])) logLine(l);
    if (j.from_sequence) {
      logLine("Vaqtlar montajga ko'chirildi ✓", "okline");
    }
    logLine("Namuna: " + (j.preview || "").slice(0, 140));
    logLine("Fayl: " + j.output, "okline");
    logLine("Premiere'da: File > Import > shu SRT ni tanlang.");
    stopProgress(true, j.line_count + " qator");
  } catch (e) {
    logOchi(true);
    logLine("Subtitr yasalmadi: " + (e.message || e), "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
}


/* ============================================ Montajning O'ZINI qirqish
 *
 * XML yozib, import qilib, yangi sequence yasash o'rniga — ochiq
 * montajning o'zidan pauzalarni olib tashlaydi. Ikki foydasi bor:
 * yangi sequence paydo bo'lmaydi va Project panelida fayllar
 * takrorlanmaydi (har XML importi ularni qaytadan olib kiradi).
 *
 * Premiere API'sida RAZOR yo'q — klipni vaqt nuqtasidan ikkiga bo'lish
 * metodi umuman mavjud emas (Sequence'da ham, Track'da ham, hujjatlar
 * bo'yicha tekshirildi). Uning o'rnini NUSXA bosadi: klip ikkiga
 * bo'linishi kerak bo'lsa, nusxa olinadi va ikkalasi kerakli joyidan
 * qirqiladi. Nusxa effektlarni ham olib o'tadi — shuning uchun
 * «project item'dan qayta qo'yish» yo'li tanlanmadi, u rang berish va
 * effektlarni yo'qotardi.
 *
 * Tartib ataylab shunday: avval nusxalar montajdan TASHQARIGA (oxiridan
 * keyin) yasaladi va haqiqatan paydo bo'lgani tekshiriladi. Shu
 * bosqichgacha montajga umuman tegilmaydi — API kutilgandek
 * ishlamasa, hech narsa buzilmagan holda to'xtaymiz.
 */
function joylashuvniHisobla(item, pauzalar) {
  // Klipdan qaysi bo'laklar QOLADI va ular yakuniy timeline'da qayerga
  // tushadi. Pauzalar vaqt bo'yicha tartiblangan bo'lishi shart.
  const a = item.start, b = item.end;
  const qoladi = [];
  let kursor = a;
  for (const p of pauzalar) {
    if (p.end <= a || p.start >= b) continue;
    const kesA = Math.max(a, p.start), kesB = Math.min(b, p.end);
    if (kesA > kursor) qoladi.push({ a: kursor, b: kesA });
    kursor = Math.max(kursor, kesB);
  }
  if (kursor < b) qoladi.push({ a: kursor, b: b });
  return qoladi;
}

/* BO'SH tanlov. `seq.getSelection()` foydalanuvchi timeline'da tanlab
 * qo'ygan kliplarni qaytaradi — ularga o'chirish amalini qo'shsak,
 * foydalanuvchining o'z tanlagani ham o'chib ketardi. Shuning uchun
 * avval bo'sh tanlov olishga urinamiz. */
async function bosTanlov(ppro, seq) {
  try {
    const TIS = ppro.TrackItemSelection;
    if (TIS && typeof TIS.createEmptySelection === "function") {
      const s = TIS.createEmptySelection();
      if (s && typeof s.addItem === "function") return s;
    }
  } catch (e) { /* pastdagi zaxira yo'l */ }
  // Zaxira: montajdagi tanlovni tozalab, bo'shini olamiz
  try {
    if (typeof seq.clearSelection === "function") await seq.clearSelection();
  } catch (e) { /* tozalanmasa ham quyida tekshiramiz */ }
  const s = await seq.getSelection();
  if (s && typeof s.getTrackItems === "function") {
    const bor = await s.getTrackItems();
    if (bor && bor.length && typeof s.removeItem === "function") {
      for (const it of bor) s.removeItem(it);
    }
  }
  return s;
}

/* MediaType nomi Premiere versiyalarida turlicha yozilgan — qaysinisi
   bor bo'lsa o'shani olamiz, topilmasa matn ko'rinishida beramiz. */
function mediaTuri(ppro) {
  const c = (ppro.Constants && ppro.Constants.MediaType) || {};
  return c.ANY || c.Any || c.any || "any";
}

function siljish(vaqt, pauzalar) {
  // Shu nuqtadan OLDIN olib tashlanadigan umumiy vaqt
  let s = 0;
  for (const p of pauzalar) {
    if (p.end <= vaqt) s += p.end - p.start;
    else if (p.start < vaqt) s += vaqt - p.start;
  }
  return s;
}

/* Montajdagi hamma klipni o'qib, ikki xil kalit bilan indekslaydi:
 *   · trek+vaqt — aniq bir klipni topish uchun
 *   · faqat vaqt — bir vaqtda turgan video+ovoz juftini topish uchun
 * Ikkinchisi bog'langan (linked) kliplar uchun kerak: nusxa olinganda
 * Premiere video bilan birga ovozini ham keltiradi, va biz ikkalasini
 * ham topib, bir xil qirqishimiz kerak. */
function klipKalit(audio, trek, start) {
  return (audio ? "A" : "V") + trek + "@" + Math.round(start * 100);
}

/* Bog'langan (linked) video+ovoz juftini BITTA birlikka yig'adi.
 *
 * Nima uchun bu shunchalik muhim: Premiere klipni nusxalaganda uning
 * bog'langan ovozini ham olib keladi. Video va ovozni alohida
 * nusxalasak, har biriga ovoz qo'shilib, ikki barobar klip paydo
 * bo'ladi, ular boshqa-boshqa joyga tushadi va bog'i uziladi — aynan
 * shu xato chiqdi. Shuning uchun nusxa FAQAT yetakchidan (videodan)
 * olinadi, ovoz o'zi ergashadi.
 *
 * Juftlik belgisi: bir manba fayl, bir vaqt oralig'i, bir in-nuqta. */
function birlikYigish(hammasi) {
  const birliklar = new Map();
  for (const c of hammasi) {
    const kalit = c.path + "|" + c.start.toFixed(3) + "|" + c.end.toFixed(3)
                + "|" + c.in.toFixed(3);
    let b = birliklar.get(kalit);
    if (!b) {
      b = { egalar: [], start: c.start, end: c.end, in: c.in,
            yetakchi: null, nusxalar: {} };
      birliklar.set(kalit, b);
    }
    b.egalar.push(c);
    // Yetakchi — video; videosi bo'lmasa (rekorder ovozi) ovozning o'zi
    if (!b.yetakchi || (b.yetakchi.audio && !c.audio)) b.yetakchi = c;
  }
  const rejalar = Array.from(birliklar.values());
  rejalar.sort((x, y) => x.start - y.start);
  return rejalar;
}

async function barchaKliplar(ppro, seq, vCount, aCount) {
  // Klipning o'zi emas, YOZUV saqlanadi: {it, audio, trek, start}.
  // Video va ovoz yarmini ajratish uchun kerak — qaysi amal qaysi
  // yarimda ishlashini bilmasak, xatoni tashxis qilib bo'lmaydi.
  const xarita = new Map();       // trek+vaqt → yozuv
  const vaqtBoyicha = new Map();  // vaqt → [yozuvlar]
  for (let i = 0; i < vCount + aCount; i++) {
    const audio = i >= vCount;
    const tr = audio ? await seq.getAudioTrack(i - vCount)
                     : await seq.getVideoTrack(i);
    if (!tr) continue;
    const trek = audio ? i - vCount : i;
    for (const it of await tr.getTrackItems(clipTypeConst(ppro), false)) {
      const st = secs(await it.getStartTime());
      const yozuv = { it: it, audio: audio, trek: trek, start: st };
      xarita.set(klipKalit(audio, trek, st), yozuv);
      const k = Math.round(st * 100);
      if (!vaqtBoyicha.has(k)) vaqtBoyicha.set(k, []);
      vaqtBoyicha.get(k).push(yozuv);
    }
  }
  return { xarita: xarita, vaqtBoyicha: vaqtBoyicha };
}

async function montajniQirqish() {
  songgiIsh = { nomi: "Qayta urinish", fn: montajniQirqish };
  els.log.innerHTML = ""; logOchi(false);
  startProgress("Montaj o'qilmoqda…");
  let step = "boshlanish";
  try {
    if (!(await checkMotor())) { stopProgress(false, "motor yo'q"); return; }
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    if (!project) throw new Error("Ochiq loyiha yo'q");
    const seq = await project.getActiveSequence();
    if (!seq) throw new Error("Ochiq sequence yo'q — montajni oching");

    // Montajning O'ZI o'zgaradi, shuning uchun avval loyihani saqlaymiz.
    // Cmd+Z bor, lekin saqlangan nusxa ishonchliroq: undo tarixi
    // Premiere yopilganda yo'qoladi.
    step = "loyihani saqlash";
    try {
      if (typeof project.save === "function") {
        await project.save();
        logLine("Loyiha saqlandi — kerak bo'lsa shu holatga qaytasiz ✓",
                "okline");
      }
    } catch (e) {
      logLine("Loyiha saqlanmadi (" + (e.message || e) + "). Davom etamiz, "
              + "lekin Cmd+S bosib qo'ying.", "warn");
    }

    // --- 1. Kliplarni o'qiymiz ---
    step = "kliplarni o'qish";
    const vCount = await seq.getVideoTrackCount();
    const aCount = await seq.getAudioTrackCount();
    const hammasi = [], tlItems = [], tlKorildi = new Set();
    for (let i = 0; i < vCount + aCount; i++) {
      const audio = i >= vCount;
      const tr = audio ? await seq.getAudioTrack(i - vCount)
                       : await seq.getVideoTrack(i);
      if (!tr) continue;
      for (const it of await tr.getTrackItems(clipTypeConst(ppro), false)) {
        const path = await mediaPathOf(ppro, it);
        const st = secs(await it.getStartTime());
        const en = secs(await it.getEndTime());
        const ip = secs(await it.getInPoint());
        if (en <= st) continue;
        hammasi.push({ it: it, path: path || "", start: st, end: en, in: ip,
                       audio: audio, trek: audio ? i - vCount : i });
        if (path) {
          // Bir klipning video va ovoz qismi ikkita element bo'lib
          // keladi. Motorga ikkalasini yuborsak, ayni bir bo'lak ikki
          // marta tahlil qilinadi — natija o'zgarmaydi, vaqt behuda ketadi.
          const kalit = path + "|" + st.toFixed(3) + "|" + ip.toFixed(3);
          if (!tlKorildi.has(kalit)) {
            tlKorildi.add(kalit);
            tlItems.push({ path: path, start: st, in: ip, out: ip + (en - st) });
          }
        }
      }
    }
    if (!hammasi.length) throw new Error("Montajda klip topilmadi");
    logLine(hammasi.length + " klip o'qildi (" + vCount + " video, "
            + aCount + " audio trek)");

    // --- 2. Pauzalarni motordan so'raymiz ---
    step = "pauzalarni topish";
    paintJob({ steps: [], step: 0, lines: [], stage: "Pauzalar qidirilmoqda",
               percent: 30, overall: 30, detail: tlItems.length + " klip" });
    const r = await fetch(MOTOR + "/cut", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        timeline: tlItems, faqat_pauzalar: true, threshold: "auto",
        strictness: strictness,
        min_pause: knobs.minPause.val(+knobs.minPause.el.value),
        padding: knobs.padding.val(+knobs.padding.el.value),
      }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const l of (j.logs || [])) logLine(l);

    // Pauza chegaralari KADR to'riga moslanadi. Motor 0.01s aniqlikda
    // ishlaydi, Premiere esa kadrlar bilan — 50fps'da kadr 0.02s.
    // Kadrga tushmagan vaqt bilan berilgan amalni Premiere rad etishi
    // yoki o'zicha yaxlitlab, bo'laklar orasida tirqish qoldirishi mumkin.
    const fps = (j.format && j.format.fps) || 0;
    const kadr = (t) => (fps > 0 ? Math.round(t * fps) / fps : t);
    const pauzalar = (j.pauses || [])
      .map((p) => ({ start: kadr(p.start), end: kadr(p.end) }))
      .filter((p) => p.end > p.start)
      .sort((x, y) => x.start - y.start);
    if (!pauzalar.length) {
      logLine("Kesiladigan pauza topilmadi — montaj o'zgarmadi.", "okline");
      stopProgress(true, "pauza yo'q");
      return;
    }
    const jami = pauzalar.reduce((s, p) => s + (p.end - p.start), 0);
    logLine(pauzalar.length + " pauza · jami " + jami.toFixed(1) + "s kesiladi");

    // --- 3. Bog'langan kliplarni BIR BIRLIK qilib yig'amiz ---
    //
    // Bu eng muhim joyi. Video va uning ovozi bitta birlik sifatida
    // qaraladi: ikkalasi bir xil offset bilan nusxalanadi (bir joyga
    // tushadi) va bir tranzaksiyada, bir xil qiymat bilan qirqiladi.
    // Birinchi urinishda har yarim o'z park joyini olgani uchun ovoz
    // videodan uzoqqa tushib ketgan edi; keyin faqat videoni nusxalab
    // ko'rdik — Premiere ovozni o'zi olib kelmas ekan, ovoz yo'qoldi.
    step = "reja";
    const rejalar = birlikYigish(hammasi);

    let nusxaKerak = 0, ochiriladi = 0;
    for (const b of rejalar) {
      b.qoladi = joylashuvniHisobla(b, pauzalar);
      if (!b.qoladi.length) ochiriladi++;
      else nusxaKerak += b.qoladi.length - 1;
    }
    logLine(rejalar.length + " klip (video+ovoz birga hisoblandi)");
    logLine(ochiriladi + " klip butunlay olib tashlanadi · "
            + nusxaKerak + " nusxa kerak bo'ladi");

    if (nusxaKerak > 0) {
      // --- 4. Nusxalarni MONTAJDAN TASHQARIGA yasaymiz ---
      //
      // Bu qadam hali hech narsani buzmaydi: nusxalar montaj oxiridan
      // keyin, bo'sh joyga tushadi. API kutilgandek ishlamasa, shu
      // yerda to'xtaymiz va montaj tegilmagan holda qoladi.
      step = "nusxalar";
      const oxir = secs(await seq.getEndTime());
      const chet = oxir + 60;          // montajdan ancha narida
      logLine("Nusxalar yasalmoqda…");

      const editor = ppro.SequenceEditor.getEditor(seq);
      if (typeof editor.createCloneTrackItemAction !== "function") {
        throw new Error("Bu Premiere'da klip nusxasini olish metodi yo'q "
                        + "(createCloneTrackItemAction). Montajning o'zini "
                        + "qirqib bo'lmaydi — «Natija: Yangi sequence» ni "
                        + "tanlang.");
      }

      let joy = chet;
      const kutilgan = [];
      runActions(project, () => {
        const acts = [];
        for (const b of rejalar) {
          for (let k = 1; k < b.qoladi.length; k++) {
            // Juftning HAR yarmi alohida nusxalanadi — video ham, ovoz
            // ham — bir xil offset bilan, shunda park'da bir joyga
            // tushadi. Faqat videoni nusxalash yetmaydi: Premiere'ning
            // nusxa amali bog'langan ovozni O'ZI olib kelmaydi — buni
            // haqiqiy montajda ko'rdik (ovoz butunlay yo'qolib qolgan).
            for (const c of b.egalar) {
              acts.push(editor.createCloneTrackItemAction(
                c.it, tickTime(ppro, joy - b.start), 0, 0, true, false));
            }
            b.parkJoy = b.parkJoy || {};
            b.parkJoy[k] = joy;
            kutilgan.push({ birlik: b, bolak: k, joy: joy,
                            soni: b.egalar.length });
            joy += (b.end - b.start) + 5;
          }
        }
        return acts;
      }, "Nusxalar");

      // --- 4b. Nusxa tranzaksiyasi montajni o'zgartirdi ---
      //
      // Undan OLDIN olingan klip obyektlari endi yaroqsiz: ularga
      // tegilsa Premiere «A nullptr was dereferenced» beradi (aynan
      // shu xato chiqdi). Shuning uchun hammasi qaytadan o'qiladi.
      step = "nusxalarni tekshirish";
      const yangi = await barchaKliplar(ppro, seq, vCount, aCount);

      let yetmadi = 0, ortiq = 0;
      for (const x of kutilgan) {
        const topilgan = yangi.vaqtBoyicha.get(Math.round(x.joy * 100)) || [];
        // Soni AYNAN mos bo'lishi shart. Kam — nusxa yasalmagan. Ko'p —
        // Premiere'ning bu versiyasi bog'langan ovozni o'zi ham olib
        // kelgan va bizning ovoz nusxamiz bilan ikkilangan; bu holda
        // davom etib bo'lmaydi, ikki ovoz bir joyga tushadi.
        if (topilgan.length < x.soni) { yetmadi++; continue; }
        if (topilgan.length > x.soni) { ortiq++; continue; }
        x.birlik.nusxalar[x.bolak] = topilgan.map((t) => t.it);
      }
      if (yetmadi || ortiq) {
        throw new Error(
          kutilgan.length + " nusxa kerak edi: " + yetmadi + " tasi chiqmadi, "
          + ortiq + " tasi ikkilangan. Montajning asosiy qismiga tegilmadi — "
          + "Cmd+Z ni bir marta bosib nusxalarni olib tashlang, so'ng "
          + "«Natija: Yangi sequence» bilan urining va log'ni yuboring.");
      }
      const juft = kutilgan.filter((x) => x.soni > 1).length;
      logLine(kutilgan.length + " nusxa yasaldi va tekshirildi ✓"
              + (juft ? "  (" + juft + " tasi ovozi bilan birga)" : ""),
              "okline");

      // Asl kliplarning havolalari ham yangilanadi
      step = "havolalarni yangilash";
      let yoqoldi = 0;
      for (const c of hammasi) {
        const t = yangi.xarita.get(klipKalit(c.audio, c.trek, c.start));
        if (t) c.it = t.it; else { c.it = null; yoqoldi++; }
      }
      if (yoqoldi) {
        throw new Error(
          yoqoldi + " klip qayta o'qishda topilmadi. Montaj deyarli "
          + "tegilmagan — Cmd+Z ni bir marta bosing.");
      }
    }

    // --- 5. Har bo'lakni qirqib, yakuniy joyiga qo'yamiz ---
    //
    // Har tranzaksiyadan keyin klip obyektlari yaroqsiz bo'lib qolishi
    // mumkin (nusxa bosqichida aynan shundan «nullptr» chiqdi), shuning
    // uchun har guruhdan OLDIN montaj qaytadan o'qiladi va kliplar
    // o'sha paytdagi joyi bo'yicha topiladi.
    step = "bo'laklarni joylashtirish";
    paintJob({ steps: [], step: 0, lines: [], stage: "Montaj qirqilmoqda",
               percent: 70, overall: 70, detail: rejalar.length + " klip" });

    const ish = [];
    let qoyildi = 0;
    for (const b of rejalar) {
      for (let k = 0; k < b.qoladi.length; k++) {
        const q = b.qoladi[k];
        const uzunlik = q.b - q.a;
        const manbaIn = b.in + (q.a - b.start);
        const yangiStart = q.a - siljish(q.a, pauzalar);
        if (!isFinite(manbaIn) || !isFinite(yangiStart) || uzunlik <= 0) continue;
        // Hech narsa o'zgarmaydigan bo'lak — tegmaymiz. Uzun montajda
        // bu minglab keraksiz amaldan qutqaradi.
        if (Math.abs(manbaIn - b.in) < 1e-4
            && Math.abs(yangiStart - b.start) < 1e-4
            && Math.abs(uzunlik - (b.end - b.start)) < 1e-4) {
          qoyildi++;
          continue;
        }
        ish.push({
          // Klip HOZIR qayerda turibdi: asl bo'lak o'z joyida, nusxa esa
          // montaj oxiridan keyingi «park» joyida (nusxa TO'LIQ klip,
          // shuning uchun uning in-nuqtasi ham asliniki bilan bir xil).
          asl: k === 0,
          egalar: k === 0 ? b.egalar.map(
            (c) => ({ audio: c.audio, trek: c.trek })) : null,
          hozir: k === 0 ? b.start : (b.parkJoy || {})[k],
          inAsl: b.in, uzAsl: b.end - b.start,
          manbaIn: manbaIn, start: yangiStart, uzunlik: uzunlik,
        });
      }
    }
    // Chapga surilgan bo'lak avval bo'shagan joyga tushsin
    ish.sort((x, y) => x.start - y.start);

    /* Klip HAVOLALARI bir marta olinadi va shundan keyin saqlanadi.
     *
     * Ilgari har amaldan keyin klip JOYI bo'yicha qayta topilardi va
     * aynan shu ish buzdi: `createSetInPointAction` klipni timeline'da
     * surib yuboradi, shuning uchun keyingi qadam uni eski joyidan
     * topolmay «topilmadi» derdi. Havolaning o'zi esa amaldan keyin ham
     * ishlayveradi — nusxa bosqichidagi eskirish montaj TARKIBI
     * o'zgargandagina (klip qo'shilganda) bo'ladi. */
    step = "klip havolalarini olish";
    const oq = await barchaKliplar(ppro, seq, vCount, aCount);
    const topib = (w) => {
      if (w.hozir === undefined || w.hozir === null) return [];
      if (w.asl) {
        return w.egalar.map((e) => oq.xarita.get(
          klipKalit(e.audio, e.trek, w.hozir))).filter(Boolean);
      }
      return oq.vaqtBoyicha.get(Math.round(w.hozir * 100)) || [];
    };
    let topilmadi = 0;
    for (const w of ish) {
      w.kliplar = topib(w);
      if (!w.kliplar.length) topilmadi++;
    }
    if (topilmadi) {
      throw new Error(
        topilmadi + "/" + ish.length + " bo'lakning klipi topilmadi. "
        + "Montaj deyarli tegilmagan — Cmd+Z ni bir marta bosing.");
    }

    /* Bo'lakni joyiga qo'yish IKKI qadamda, har biri alohida
     * tranzaksiyada (to'rt amal birga berilganda «nullptr» chiqqan):
     *
     *   1) manba qirqimi (in/out) — klip manbaning kerakli qismini
     *      ko'rsatadigan bo'ladi. Diqqat: in-nuqta surilganda klip
     *      timeline'da ham suriladi (boshidan qirqilgani uchun);
     *   2) joyiga surish (start) — klip yakuniy joyiga o'tadi.
     *
     * TARTIB HAL QILUVCHI. Oldingi urinish «Invalid parameter» bilan
     * yiqildi, chunki bo'lak hali BAND joyga surilgan edi: park'dagi
     * nusxa montaj boshiga surilmoqchi bo'ldi, u yerda esa asl klip
     * turardi — Premiere trekda ustma-ust turishga ruxsat bermaydi.
     * Chapdan o'ngga birma-bir yurilsa, har bo'lakning joyi undan
     * oldingilari tomonidan allaqachon bo'shatilgan bo'ladi. */
    const qirqim = (w) => {
      runActions(project, () => w.kliplar.map((r) => [
        r.it.createSetInPointAction(tickTime(ppro, w.manbaIn)),
        r.it.createSetOutPointAction(tickTime(ppro, w.manbaIn + w.uzunlik)),
      ]).flat(), "Manba qirqimi");
    };
    const surish = (w) => {
      runActions(project, () => w.kliplar.map(
        (r) => r.it.createSetStartAction(tickTime(ppro, w.start))),
        "Joyiga surish");
    };
    const joylashtir = async (w) => {
      // Qirqim faqat kerak bo'lsa — manba oralig'i o'zgarmagan bo'lakka
      // (masalan, faqat chapga suriladigan butun klipga) tegilmaydi
      const qirqimKerak = Math.abs(w.manbaIn - w.inAsl) > 1e-4
                       || Math.abs(w.uzunlik - w.uzAsl) > 1e-4;
      if (qirqimKerak) qirqim(w);
      // Qirqimdan keyin klip qayerda: in-nuqta surilgani boshini ham
      // suradi (nusxa to'liq klip bo'lgani uchun ikkalasida bir xil)
      const keyin = w.hozir + (qirqimKerak ? (w.manbaIn - w.inAsl) : 0);
      if (Math.abs(keyin - w.start) > 0.002) surish(w);
    };

    // --- 5a. Birinchi bo'lak — sinov. Natija klipning O'ZIDAN o'qiladi.
    //
    // Kutilgan joyga tushmasa, qolgan bo'laklarga umuman tegilmaydi:
    // montajda bitta bo'lakdan boshqa hamma narsa joyida qoladi.
    step = "sinov bo'lak";
    if (ish.length) {
      const s0 = ish[0];
      try {
        await joylashtir(s0);
      } catch (e) {
        throw new Error("Birinchi bo'lak qo'yilmadi: " + (e.message || e)
                        + ". Montaj deyarli tegilmagan — Cmd+Z ni bir-ikki "
                        + "marta bosing.");
      }
      const bSt = secs(await s0.kliplar[0].it.getStartTime());
      const bEn = secs(await s0.kliplar[0].it.getEndTime());
      if (Math.abs(bSt - s0.start) > 0.05
          || Math.abs((bEn - bSt) - s0.uzunlik) > 0.05) {
        throw new Error(
          "Sinov bo'lak kutilgan joyga tushmadi: " + bSt.toFixed(2) + "–"
          + bEn.toFixed(2) + "s, kutilgan " + s0.start.toFixed(2) + "–"
          + (s0.start + s0.uzunlik).toFixed(2) + "s. Qolgan kliplarga "
          + "tegilmadi — Cmd+Z ni bir-ikki marta bosing va log'ni yuboring.");
      }
      logLine("Sinov bo'lak to'g'ri joyga tushdi ✓", "okline");
      qoyildi++;
      ish.shift();
    }

    // --- 5b. Qolgani — chapdan o'ngga, birma-bir ---
    step = "bo'laklarni joylashtirish";
    let yiqildi = 0;
    for (let i = 0; i < ish.length; i++) {
      const w = ish[i];
      try { await joylashtir(w); qoyildi++; }
      catch (e) {
        yiqildi++;
        if (yiqildi <= 3) {
          logLine("Bo'lak qo'yilmadi (" + w.start.toFixed(1) + "s): "
                  + (e.message || e), "warn");
        }
        // Birin-ketin ko'p yiqilsa — davom etishning ma'nosi yo'q,
        // qolganlari ham band joy ustiga tushaveradi.
        if (yiqildi >= 10) {
          throw new Error(
            yiqildi + " bo'lak ketma-ket qo'yilmadi — to'xtatildi. "
            + "Cmd+Z bilan qaytarib, log'ni yuboring.");
        }
      }
      if (i % 25 === 0 || i === ish.length - 1) {
        const foiz = 70 + Math.round(25 * (i + 1) / ish.length);
        paintJob({ steps: [], step: 0, lines: [], stage: "Montaj qirqilmoqda",
                   percent: foiz, overall: foiz,
                   detail: qoyildi + "/" + (ish.length + 1) + " bo'lak" });
      }
    }

    // Qisman muvaffaqiyat — muvaffaqiyat emas: ba'zi bo'laklar
    // qo'yilmagan bo'lsa montaj chala holatda, buni «tayyor» deb
    // bo'lmaydi.
    if (yiqildi) {
      throw new Error(
        qoyildi + " bo'lak qo'yildi, " + yiqildi + " tasi QO'YILMADI — "
        + "montaj chala. Cmd+Z bilan qaytaring (bir necha marta) va "
        + "log'ni menga yuboring.");
    }

    // --- 6. Butunlay pauzaga tushgan kliplarni olib tashlaymiz ---
    //
    // DIQQAT: bu yerda joy bo'yicha qidirish MUMKIN EMAS. Joylashtirish
    // tugagach, o'chiriladigan klipning eski o'rnini allaqachon boshqa
    // (to'g'ri qo'yilgan) bo'lak egallagan bo'lishi mumkin — joy
    // bo'yicha qidirsak, aynan o'shani o'chirib yuborardik. Saqlangan
    // havolalar esa hali ham o'sha klipning o'zini ko'rsatadi: 5-bosqich
    // butun ish davomida shu havolalar bilan ishladi.
    step = "ortiqchani olib tashlash";
    const ortiqcha = [];
    for (const b of rejalar) {
      if (b.qoladi.length) continue;
      for (const c of b.egalar) if (c.it) ortiqcha.push(c.it);
    }
    if (ortiqcha.length) {
      try {
        const ed = ppro.SequenceEditor.getEditor(seq);
        const tanlov = await bosTanlov(ppro, seq);
        if (tanlov && typeof tanlov.addItem === "function") {
          for (const it of ortiqcha) tanlov.addItem(it, false);
          runActions(project, () => [ed.createRemoveItemsAction(
            tanlov, false, mediaTuri(ppro), false)],
            "Ortiqchani olib tashlash");
        } else {
          logLine(ortiqcha.length + " klipni olib tashlab bo'lmadi — "
                  + "ularni qo'lda o'chiring", "warn");
        }
      } catch (e) {
        logLine("Ortiqcha kliplar qoldi: " + (e.message || e), "warn");
      }
    }

    logLine("");
    logLine(qoyildi + " bo'lak joylashtirildi ✓", "okline");
    if (yiqildi) {
      logLine(yiqildi + " bo'lak qo'yilmadi — montajni ko'zdan kechiring.",
              "warn");
    }
    logLine("Montaj " + jami.toFixed(1) + " soniyaga qisqardi.");
    logLine("Yoqmasa: File > Revert — ish boshida saqlangan holatga bir "
            + "qadamda qaytadi (Cmd+Z bilan bo'lak-bo'lak qaytarish uzoq).");
    stopProgress(true, qoyildi + " bo'lak");
  } catch (e) {
    logLine("To'xtadi (" + step + "): " + (e.message || e), "warn");
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

/* Log yozilib boraveradi, lekin EKRANNI EGALLAMAYDI.
 *
 * Ish yaxshi ketayotganda qadamlarni o'qib o'tirishning hojati yo'q —
 * pastdagi jarayon qatori nima bo'layotganini aytib turadi. Log esa
 * o'zi ochiladigan ikkita holat bor: ogohlantirish va xato. Ya'ni matn
 * ko'ringan bo'lsa — demak qarash kerak. Qolgan vaqtda «Log» tugmasi
 * bilan ochasiz (tashxisni menga yuborish uchun ham o'sha yerda). */
let logOchiq = false;

function logLine(text, cls) {
  const div = document.createElement("div");
  if (cls) div.className = cls;
  div.textContent = text;
  els.log.appendChild(div);
  els.logBar.classList.add("show");
  if (cls === "warn" && !logOchiq) logOchi(true);   // e'tibor kerak
  if (logOchiq) els.log.scrollTop = els.log.scrollHeight;
}

function logOchi(ochiq) {
  logOchiq = !!ochiq;
  els.log.classList.toggle("show", logOchiq);
  if (els.logToggle) {
    els.logToggle.textContent = logOchiq ? "Log'ni yopish" : "Log'ni ochish";
  }
  if (logOchiq) els.log.scrollTop = els.log.scrollHeight;
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

/* Oxirgi boshlangan ish — «Qayta urinish» shuni qayta chaqiradi.
   Foydalanuvchi qaysi tabda ekanini eslab, tugmani qidirib yurmasin. */
let songgiIsh = null;

/* Ish qotib qolganda yoki to'xtaganda nima qilish kerakligi.
   Umumiy «xato yuz berdi» emas — aynan shu holatga mos maslahat. */
function yordamMatni(holat, izoh) {
  const t = (izoh || "").toLowerCase();
  // DIQQAT: aniq iboralar bo'yicha tekshiriladi, bitta so'z bo'yicha emas.
  // Ilgari «sequence» so'zi uchrasa bas edi va «Sequence o'lchami
  // o'qilmadi» degan xatoga «montaj ochiq emas» deb noto'g'ri javob
  // berardi — montaj esa ochiq turardi. Yolg'on tashxis xato haqida
  // umuman gapirmaslikdan yomonroq: odam bor muammoni qidirib ketadi.
  if (t.indexOf("motor") >= 0 || t.indexOf("javob bermadi") >= 0) {
    return "Motor javob bermayapti. YANGILASH.command ni ishga tushiring, "
         + "so'ng qayta urining.";
  }
  if (t.indexOf("ochiq sequence yo'q") >= 0 || t.indexOf("ochiq loyiha yo'q") >= 0
      || t.indexOf("sequence topilmadi") >= 0) {
    return "Premiere'da montaj ochiq emas. Project panelida sequence'ni "
         + "ikki marta bosing, so'ng qayta urining.";
  }
  if (t.indexOf("o'lchamini o'qib bo'lmadi") >= 0
      || t.indexOf("o'lchami o'qilmadi") >= 0) {
    return "Montaj o'lchami o'qilmadi — bu Premiere API'sining bu "
         + "versiyasidagi farq. Log'ni menga yuboring, moslashtiraman.";
  }
  // Joyida qirqish: nusxa bosqichida to'xtasa, montaj TEGILMAGAN bo'ladi.
  // Buni aniq aytish kerak — aks holda odam montajim buzildimi deb
  // qo'rqib, keraksiz Cmd+Z bosaveradi.
  if (t.indexOf("nusxa kerak edi") >= 0
      || t.indexOf("nusxasini olish metodi yo'q") >= 0) {
    return "Montajga TEGILMADI — hammasi joyida. Bu Premiere versiyasida "
         + "klip nusxalash boshqacha ishlayapti. «Natija: Yangi sequence» "
         + "ni tanlab qayta urining, u har doim ishlaydi.";
  }
  if (t.indexOf("montajda klip topilmadi") >= 0) {
    return "Ochiq montajda oddiy klip topilmadi. Yuqoridan «Ochiq "
         + "sequence'ni olish» ni bosganingizga ishonch hosil qiling.";
  }
  if (t.indexOf("v1") >= 0 || t.indexOf("klip topilmadi") >= 0) {
    return "Eng pastki video trekda (V1) oddiy klip topilmadi. Multicam "
         + "yoki nested klip bo'lsa, avval uni oddiy klipga aylantiring.";
  }
  if (t.indexOf("scale") >= 0 || t.indexOf("keyframe") >= 0) {
    return "Premiere klip parametriga ruxsat bermadi. Motor qatoridagi "
         + "«tekshirish» ni bosib, log'ni yuboring.";
  }
  if (t.indexOf("qabul qilmadi") >= 0) {
    return "Premiere o'zgarishlarni rad etdi. Boshqa amal ketayotgan "
         + "bo'lishi mumkin — bir oz kutib, qayta urining.";
  }
  if (holat === "stale") {
    return "45 soniyadan beri o'zgarish yo'q. Uzun montajda bu normal "
         + "bo'lishi mumkin — «Batafsil» bilan bosqichni ko'ring. "
         + "Yana kutsangiz ham qimirlamasa, qayta urining.";
  }
  return "Ish tugallanmadi. Log'ning oxirgi qatorini o'qing — sabab o'sha "
       + "yerda yozilgan. Tuzatib bo'lmasa, log'ni menga yuboring.";
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
  const qotdi = Date.now() - lastChange > 45000;
  els.job.classList.toggle("qotdi", qotdi);
  if (qotdi && els.jobHelpTxt && !els.job.classList.contains("err")) {
    els.jobHelpTxt.textContent = yordamMatni("stale", "");
  }
}

function startProgress(kindLabel) {
  shownLogs = 0;
  jobT0 = Date.now();
  etaSec = null;
  lastChange = Date.now();
  lastSig = "";
  stepsSig = "";
  // «Batafsil» ochiq qolsa — foydalanuvchi shunday xohlagan, yopmaymiz
  const batafsil = els.job.classList.contains("batafsil") ? " batafsil" : "";
  els.job.className = "job on" + batafsil;
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
  const batafsil = els.job.classList.contains("batafsil") ? " batafsil" : "";
  els.job.className = "job on " + (ok ? "done" : "err") + batafsil;
  els.jobStage.textContent = ok ? "Tayyor ✓" : "To'xtadi";
  els.jobDetail.textContent = note || "";
  els.jobEta.textContent = "";
  els.jobStep.textContent = "";
  if (ok) els.jobFill.style.width = "100%";
  els.jobElapsed.textContent = spent;
  const chips = els.jobChips.querySelectorAll(".c");
  if (ok) chips.forEach((c) => { c.className = "c ok"; });
  if (els.jobHelpTxt) {
    els.jobHelpTxt.textContent = ok ? "" : yordamMatni("err", note);
  }
  if (els.jobRetry && els.jobRetry.style) {
    els.jobRetry.style.display = (!ok && songgiIsh) ? "" : "none";
    if (!ok && songgiIsh) els.jobRetry.textContent = songgiIsh.nomi;
  }
}

async function run(kind) {
  if (!(await checkMotor())) return;

  const isCut = kind === "cut";
  const isSwitch = kind === "switch";
  const isCap = kind === "captions" || kind === "sample";
  els.log.innerHTML = ""; logOchi(false);
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

/* ==================================== Project panelini toza saqlash
 *
 * Muammo: XML import qilinganda Premiere sequence bilan birga MANBA
 * fayllarni ham loyihaga qo'shadi. Bir epizod ustida bir necha marta
 * ishlansa, Project panelida o'sha cam29706…cam29713 qayta-qayta paydo
 * bo'ladi va ularni qo'lda tanlab o'chirishga to'g'ri keladi.
 *
 * Yechim ikki qavatli:
 *   1) Import har doim BITTA binga tushadi — sochilmaydi;
 *   2) «Tozalash» o'sha binni butunlay olib tashlaydi — bir bosish.
 *
 * Uchinchisi eng kuchlisi: Cut «Shu montajda» rejimida umuman import
 * qilinmaydi, ya'ni tozalanadigan narsaning o'zi paydo bo'lmaydi.
 */
const SUITE_BIN = "Podcast Suite";

async function suiteBini(project) {
  // Bor bo'lsa topamiz, yo'q bo'lsa yasaymiz. Topilmasa ham ish
  // to'xtamasin — null qaytsa, import eski yo'l bilan ketaveradi.
  try {
    const ppro = require("premierepro");
    const root = await project.getRootItem();
    if (!root || typeof root.getItems !== "function") return null;

    const qidir = async () => {
      for (const it of await root.getItems()) {
        if (it && it.name === SUITE_BIN) {
          return (ppro.FolderItem && typeof ppro.FolderItem.cast === "function")
            ? (ppro.FolderItem.cast(it) || it) : it;
        }
      }
      return null;
    };

    const bor = await qidir();
    if (bor) return bor;
    if (typeof root.createBinAction !== "function") return null;

    // makeUnique = false: har safar «Podcast Suite 2», «3» chiqmasin.
    // Amal runActions orqali yasaladi — createBinAction lockedAccess
    // ichida chaqirilmasa, Premiere obyektni «no longer valid» deb rad etadi.
    runActions(project, () => [root.createBinAction(SUITE_BIN, false)],
               "Podcast Suite bini");
    return await qidir();
  } catch (e) {
    return null;
  }
}

/* Ikki bosishli tasdiq: birinchi bosishda nima o'chishi aytiladi,
   ikkinchisida o'chiriladi. Undo tarixidan tashqaridagi ishni bir
   tasodifiy bosish bilan qilib qo'ymaslik uchun. */
let tozalashTasdiq = 0;

async function tozalash() {
  let soralmoqda = false;   // tasdiq so'ralgan bo'lsa, holatni tiklamaymiz
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    if (!project) throw new Error("Ochiq loyiha yo'q");
    const root = await project.getRootItem();
    if (!root || typeof root.getItems !== "function") {
      throw new Error("Project paneli o'qilmadi");
    }

    let bin = null;
    for (const it of await root.getItems()) {
      if (it && it.name === SUITE_BIN) { bin = it; break; }
    }
    if (!bin) {
      logOchi(true);
      logLine("«" + SUITE_BIN + "» bini yo'q — tozalanadigan narsa topilmadi.",
              "okline");
      logLine("Cut «Shu montajda» rejimida ishlasa, Project paneliga hech "
              + "narsa qo'shilmaydi — shuning uchun bin ham yasalmaydi.");
      tozalashTasdiq = 0;
      return;
    }

    let soni = 0;
    try {
      const papka = (ppro.FolderItem && typeof ppro.FolderItem.cast === "function")
        ? ppro.FolderItem.cast(bin) : null;
      if (papka && typeof papka.getItems === "function") {
        soni = (await papka.getItems()).length;
      }
    } catch (e) { /* sonini bilmasak ham o'chira olamiz */ }

    if (tozalashTasdiq !== 1) {
      tozalashTasdiq = 1;
      soralmoqda = true;
      logOchi(true);
      logLine("«" + SUITE_BIN + "» bini va ichidagi hamma narsa o'chiriladi"
              + (soni ? " (" + soni + " element)" : "") + ".", "warn");
      logLine("Ichida plagin yasagan sequence'lar ham bor — ular kerak "
              + "bo'lsa, avval Project panelida binidan tashqariga sudrab "
              + "chiqaring.");
      logLine("Tasdiqlash uchun «Tozalash» ni yana bir bosing.");
      if (els.tozalaBtn) els.tozalaBtn.textContent = "Rostdan o'chirilsinmi?";
      return;
    }

    if (typeof root.createRemoveItemAction !== "function") {
      throw new Error("Bu Premiere versiyasida bin o'chirish metodi yo'q — "
                      + "Project panelida binni tanlab Delete bosing");
    }
    runActions(project, () => [root.createRemoveItemAction(bin)],
               "Podcast Suite binini tozalash");

    logOchi(true);
    logLine("«" + SUITE_BIN + "» tozalandi ✓", "okline");
    logLine("Yangi montajga o'tishingiz mumkin. Yoqmasa Cmd+Z.");
  } catch (e) {
    logOchi(true);
    logLine("Tozalanmadi: " + (e.message || e), "warn");
    logLine("Qo'lda: Project panelida «" + SUITE_BIN + "» binini tanlab "
            + "Delete bosing.");
  } finally {
    if (!soralmoqda) {
      tozalashTasdiq = 0;
      if (els.tozalaBtn) els.tozalaBtn.textContent = "Tozalash";
    }
  }
}

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

    // Hamma import bitta binga tushadi — keyin «Tozalash» shu binni
    // butunlay olib tashlaydi. Ilgari har import manba fayllarni
    // Project panelining ildiziga sochib yuborardi va ular ishdan-ishga
    // to'planib borardi.
    const bin = await suiteBini(project);

    // importFiles(filePaths, suppressUI, targetBin, asNumberedStills) — 25.6+
    if (bin) await project.importFiles([lastXml], true, bin);
    else await project.importFiles([lastXml], true);
    logLine(bin ? "Sequence «" + SUITE_BIN + "» binga qo'shildi ✓"
                : "Sequence loyihaga qo'shildi ✓", "okline");

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
on(els.cutBtn, function () {
  // «Joyida» rejim faqat ochiq montaj o'qilgan bo'lsa mumkin: qirqiladigan
  // klip Premiere ichida turishi kerak. Fayllar qo'lda tanlangan bo'lsa
  // qirqadigan montajning o'zi yo'q — buni jim o'tkazib yubormaymiz.
  if (cutRejim === "joyida") {
    if (!timeline) {
      els.log.innerHTML = ""; logOchi(true);
      logLine("Montajning o'zini qirqish uchun avval «Ochiq sequence'ni "
              + "olish» ni bosing.", "warn");
      logLine("Yoki «Natija: Yangi sequence» ni tanlang — u qo'lda "
              + "tanlangan fayllardan ham ishlaydi.");
      return;
    }
    montajniQirqish();
    return;
  }
  run("cut");
});
on(els.switchBtn, function () { run("switch"); });
on(els.capBtn, function () { run("captions"); });
on(els.sampleBtn, function () { run("sample"); });
on(els.introBtn, findMoments);
on(els.trImpBtn, transkriptYuklash);
on(els.srtBtn, subtitrYasash);
on(els.logCopy, copyLog);
on(els.logBig, function () { els.log.classList.toggle("big"); });
on(els.logToggle, function () { logOchi(!logOchiq); });
on(els.jobMore, function () {
  els.job.classList.toggle("batafsil");
  els.jobMore.textContent = els.job.classList.contains("batafsil")
    ? "Yig'ish" : "Batafsil";
});
on(els.shortsBtn, findShorts);
on(els.shortsBuildBtn, buildShorts);
on(els.markerBtn, markerlardanYigish);
on(els.trBtn, trYigish);
on(els.harBtn, harakatQoshish);
on(els.jobRetry, function () {
  if (songgiIsh && typeof songgiIsh.fn === "function") songgiIsh.fn();
});
on(els.trLoad, trYuklash);
on(els.trClear, function () { trTanlangan = {}; trRender(els.trSearch.value); });
on(els.buildBtn, function () { buildIntro(false); });
on(els.reviewBtn, function () { buildIntro(true); });
on(els.capSearchBtn, searchArchive);
on(els.seqBtn, readSequence);
on(els.matnAdd, addMatn);
on(els.matnBtn, runMatn);
on(els.importBtn, doImport);
on(els.tozalaBtn, tozalash);

setupTabs();
setupKnobs();
setupMatn();
setupCaptionPills();
setupIntroPills();
setupPills("shortsLimit", (v) => { shortsLimit = v; });
setupPills("harOraliqBox", (v) => { harOraliq = v; });
setupPills("harKuchBox", (v) => { harDaraja = v; }, true);
setupPills("harRejimBox", (v) => { harRejim = v; }, true);
setupPills("markerAspect", (v) => { markerAspect = v; }, true);
setupPills("shortsMode", (v) => {
  shortsMode = v;
  const marker = v === "marker";
  const korsat = (id, bormi) => {
    const e = document.getElementById(id);
    if (e) e.style.display = bormi ? "" : "none";
  };
  const matndan = v === "matn";
  korsat("shortsTipAuto", v === "avto");
  korsat("shortsTipMarker", marker);
  korsat("markerTip", marker);
  korsat("markerKnobs", marker);
  korsat("trPanel", matndan);
  // Format tanlagichi ikkala Premiere-ichi rejimda ham kerak
  korsat("markerFormat", marker || matndan, "flex");
  // Har rejimda FAQAT o'ziga tegishli tugma turadi.
  //
  // Ilgari beshovi birdan turardi va 420px kenglikdagi dok panelida
  // pastki qism ekranning yarmini egallab, ro'yxatga joy qolmasdi.
  // Bundan tashqari marker/matn rejimida «Bo'laklarni topish» va
  // «Premiere'ga import» umuman ma'nosiz: ish Premiere ichida bajariladi
  // va XML yasalmaydi.
  korsat("shortsBtn", v === "avto");
  korsat("shortsBuildBtn", v === "avto");
  korsat("importBtn", v === "avto");
  korsat("markerBtn", marker);
  korsat("trBtn", matndan);
  const lim = document.getElementById("shortsLimit");
  if (lim && lim.parentElement) lim.parentElement.style.display = (v === "avto") ? "" : "none";
}, true);
if (els.markerBtn && els.markerBtn.style) els.markerBtn.style.display = "none";
if (els.trBtn && els.trBtn.style) els.trBtn.style.display = "none";
if (els.trSearch && els.trSearch.addEventListener) {
  els.trSearch.addEventListener("input", function () { trRender(els.trSearch.value); });
}
document.body.className = "tab-sync";
cutRejimKorsat();
applyTabText();
checkMotor().then(function (ok) { if (ok) { checkUpdates(); loadFonts(); } });
setInterval(checkMotor, 5000);
setInterval(checkUpdates, 10 * 60 * 1000);   // har 10 daqiqada bir tekshiradi
renderFiles();

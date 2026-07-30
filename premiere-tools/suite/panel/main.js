/* Podcast Suite — panel mantiqi (Sync, Cut, Switch, Captions).
 *
 * Panel o'zi hech qanday og'ir ish qilmaydi: fayllarni tanlatadi,
 * lokal motorga (server.py, 127.0.0.1:8765) yuboradi, natijani
 * ko'rsatadi va tayyor XML'ni Premiere loyihasiga import qiladi.
 */

/* Motor manzili. UXP ba'zi holatlarda 127.0.0.1 ni bloklaydi, shuning uchun
 * ikkala shaklni ham sinab ko'ramiz va ishlaganini eslab qolamiz. */
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
  shortsList: el("shortsList"),
  timeText: el("timeText"),
  timeSum: el("timeSum"),
  timeList: el("timeList"),
  timeBtn: el("timeBtn"),
  moments: el("moments"),
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
        whisperReady = j.whisper !== false;
        els.capWarn.classList.toggle("show", !whisperReady);
        if (!pollTimer) updateRunButtons();
        els.motor.classList.add("ok");
        els.motorTxt.textContent = j.ffmpeg === false
          ? "Motor ishlayapti, lekin ffmpeg yo'q — motorni-yoqish.command ni ishlating"
          : "Motor ishlayapti (v" + j.version + ")";
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
  sync: { pick: "kamera videolari va rekorder audiosi (2+ fayl)" },
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
  vaqtlar: {
    pick: "yoki fayllarni qo'lda tanlang",
    seqTitle: "Ochiq sequence'ni olish",
    seqHint: "vaqtlar shu sequence bo'yicha o'qiladi",
    next: "Endi vaqtlarni pastdagi qutiga qo'ying",
  },
  shorts: {
    pick: "yozuvlar yoki ochiq sequence",
    seqTitle: "Ochiq sequence'dan bo'laklarni izlash",
    seqHint: "har bo'lak tugallangan fikr bo'ladi — 20-60 soniya",
    next: "Endi «Bo'laklarni topish» ni bosing",
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
  threshold: { el: el("kThreshold"), out: el("vThreshold"),
               fmt: (v) => (v / 100).toFixed(2), val: (v) => v / 100 },
  minPause: { el: el("kMinPause"), out: el("vMinPause"),
              fmt: (v) => (v / 10).toFixed(1) + " s", val: (v) => v / 10 },
  padding: { el: el("kPadding"), out: el("vPadding"),
             fmt: (v) => v * 10 + " ms", val: (v) => v / 100 },
  minShot: { el: el("kMinShot"), out: el("vMinShot"),
             fmt: (v) => (v / 10).toFixed(1) + " s", val: (v) => v / 10 },
  maxShot: { el: el("kMaxShot"), out: el("vMaxShot"),
             fmt: (v) => v + " s", val: (v) => v },
};

function setupKnobs() {
  Object.values(knobs).forEach((k) => {
    if (!k.el.addEventListener) return;
    const show = () => { k.out.textContent = k.fmt(+k.el.value); };
    k.el.addEventListener("input", show);
    show();
  });
}

/* ------------------------------------------------- Captions sozlamalari */

const capOpts = { language: "uz", model: "balans" };

function setupPills(boxId, apply) {
  const box = document.getElementById(boxId);
  if (!box) return;
  box.querySelectorAll(".opill").forEach((pill) => {
    pill.addEventListener("click", () => {
      box.querySelectorAll(".opill").forEach((x) => x.classList.remove("on"));
      pill.classList.add("on");
      apply(+pill.dataset.v);
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

    const items = [];
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
        if (!path) continue;
        const start = secs(await it.getStartTime());
        const end = secs(await it.getEndTime());
        const inP = secs(await it.getInPoint());
        if (end <= start) continue;
        items.push({ path: path, start: start, in: inP, out: inP + (end - start),
                     atrack: onAudioTrack });
      }
    }

    if (!items.length) throw new Error("Sequence'da klip topilmadi");

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
    if (sound) logLine(sound);
    renderTimes();
    const t = TAB_TEXT[activeTab] || {};
    if (t.next) logLine(t.next);
  } catch (e) {
    timeline = null;
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

/* Premiere playhead'ini shu joyga olib boradi — nomzodni ko'rish uchun */
async function goToTime(sec) {
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) throw new Error("ochiq sequence yo'q");
    const tt = ppro.TickTime.createWithSeconds
      ? ppro.TickTime.createWithSeconds(sec)
      : ppro.TickTime.createWithSeconds;
    await seq.setPlayerPosition(tt);
  } catch (e) {
    logLine("Playhead'ni ko'chirib bo'lmadi (" + (e.message || e) + ") — "
            + "vaqtni qo'lda kiriting: " + tc(sec), "warn");
  }
}

/* Timeline'dagi markerlar — mashina taxmin qilmaydi, siz aytgansiz.
 * API versiyalari farq qiladi, shuning uchun topilmasa jimgina o'tamiz. */
async function readMarkers() {
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    const seq = project && (await project.getActiveSequence());
    if (!seq) return [];
    let list = null;
    if (ppro.Markers && ppro.Markers.getMarkers) {
      list = await ppro.Markers.getMarkers(seq);
    } else if (seq.getMarkers) {
      list = await seq.getMarkers();
    }
    if (!list || !list.length) return [];
    const out = [];
    for (const mk of list) {
      const t = mk.start !== undefined ? mk.start
              : mk.getStart ? await mk.getStart() : null;
      if (t != null) out.push({ start: secs(t) });
    }
    return out;
  } catch (e) {
    return [];
  }
}

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
    const body = { limit: shortsLimit, markers: markers };
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


/* --------------------------------------------------- Vaqtlar (qo'lda qirqish)
 *
 * Bu yerda mashina hech narsa taxmin qilmaydi: qaysi kadrlar kerakligini
 * o'zingiz yozib berasiz, modul faqat qirqadi. Vaqtlar ochiq sequence
 * bo'yicha o'qiladi — Premiere'da ko'rib turgan raqamlar. Ovoz tahlil
 * qilinmaydi, shuning uchun bir necha soniyada tugaydi.
 *
 * Oraliqlar panelda ham o'qiladi (darhol ko'rsatish uchun) va motorda ham
 * (buyruq satridan ishlatilganda) — ikkalasi bir xil qoidada. */
let timeRanges = [];
let timeSplit = 0;
let timePad = 0;

/* «1:30» → 90 · «1:02:30» → 3750 · «90» → 90 */
function timeToSec(txt) {
  const t = String(txt).trim().replace(",", ".").split(";")[0];
  const p = t.split(":").map(Number);
  if (p.some(isNaN)) return null;
  if (p.length === 1) return p[0];
  if (p.length === 2) return p[0] * 60 + p[1];
  return p[0] * 3600 + p[1] * 60 + p[2];
}

function parseTimes(text) {
  const re = /(\d{1,2}(?::\d{1,2}){0,2}(?:[.,]\d+)?(?:;\d+)?)\s*(?:-|–|—|to|\.\.)\s*(\d{1,2}(?::\d{1,2}){0,2}(?:[.,]\d+)?(?:;\d+)?)/g;
  const out = [];
  let m;
  while ((m = re.exec(text || "")) !== null) {
    let a = timeToSec(m[1]), b = timeToSec(m[2]);
    if (a == null || b == null) continue;
    if (b < a) { const t = a; a = b; b = t; }
    if (b - a <= 0) continue;
    out.push({ start: +a.toFixed(3), end: +b.toFixed(3), raw: m[0].trim() });
  }
  out.sort((x, y) => x.start - y.start);
  return out;
}

function renderTimes() {
  const text = els.timeText.value || "";
  timeRanges = parseTimes(text);
  const total = timeRanges.reduce((a, r) => a + (r.end - r.start), 0);
  // Yozilgan qatorlar soni va o'qilganlar soni farq qilsa — aytib qo'yamiz
  const lines = text.split("\n").filter((l) => /\d/.test(l)).length;
  const missed = Math.max(0, lines - timeRanges.length);
  els.timeSum.innerHTML = timeRanges.length
    ? "<b>" + timeRanges.length + " kadr</b> · jami " + mmss(total)
      + (missed ? " · <span class='bad'>" + missed
                  + " qator o'qilmadi</span>" : "")
    : "oraliq kiritilmadi";
  els.timeList.innerHTML = "";
  timeRanges.forEach((r, i) => {
    const d = document.createElement("div");
    d.textContent = (i + 1) + ".  " + tc(r.start) + " → " + tc(r.end)
                  + "   " + Math.round(r.end - r.start) + "s";
    els.timeList.appendChild(d);
  });
  els.timeBtn.disabled = !timeRanges.length
    || (!timeline && picked.length < 1);
}

async function cutRanges() {
  if (!(await checkMotor())) return;
  if (!timeRanges.length) return;
  els.log.innerHTML = "";
  els.timeBtn.disabled = true;
  startProgress("Kadrlar qirqilmoqda…");
  try {
    const body = { ranges: timeRanges, split: !!timeSplit, pad: timePad };
    if (timeline) body.timeline = timeline;
    else body.files = picked.map((p) => p.path);
    const r = await fetch(MOTOR + "/vaqtlar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");
    for (const line of (j.logs || []).slice(shownLogs)) {
      logLine(line, line.indexOf("OGOHLANTIRISH") >= 0 ? "warn" : null);
    }
    lastXml = j.output;
    logLine(j.count + " kadr · jami " + mmss(j.length_sec) + " tayyor ✓",
            "okline");
    if ((j.skipped || []).length) {
      logLine("Tushmagan oraliqlar: " + j.skipped.join(", "), "warn");
    }
    logLine(j.split ? "Har kadr alohida sequence bo'ldi"
                    : "Hammasi bitta sequence'da, har kadr boshida marker");
    logLine("Fayl: " + j.output);
    els.importBtn.disabled = false;
    stopProgress(true, j.count + " kadr · " + mmss(j.length_sec));
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
    stopProgress(false, (e.message || "").slice(0, 90));
  }
  renderTimes();
}

/* ---------------------------------------------------- sinxronlash */

function logLine(text, cls) {
  const div = document.createElement("div");
  if (cls) div.className = cls;
  div.textContent = text;
  els.log.appendChild(div);
  els.log.classList.add("show");
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
    body.threshold = knobs.threshold.val(+knobs.threshold.el.value);
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
on(els.timeBtn, cutRanges);
on(els.shortsBtn, findShorts);
on(els.shortsBuildBtn, buildShorts);
on(els.buildBtn, function () { buildIntro(false); });
on(els.reviewBtn, function () { buildIntro(true); });
on(els.capSearchBtn, searchArchive);
on(els.seqBtn, readSequence);
on(els.importBtn, doImport);

setupTabs();
setupKnobs();
setupCaptionPills();
setupIntroPills();
setupPills("shortsLimit", (v) => { shortsLimit = v; });
setupPills("timeSplit", (v) => { timeSplit = v; });
setupPills("timePad", (v) => { timePad = v; });
if (els.timeText.addEventListener) {
  els.timeText.addEventListener("input", renderTimes);
  els.timeText.addEventListener("change", renderTimes);
}
renderTimes();
document.body.className = "tab-sync";
applyTabText();
checkMotor().then(function (ok) { if (ok) checkUpdates(); });
setInterval(checkMotor, 5000);
setInterval(checkUpdates, 10 * 60 * 1000);   // har 10 daqiqada bir tekshiradi
renderFiles();

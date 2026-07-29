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
  capSearch: el("capSearch"),
  capSearchBtn: el("capSearchBtn"),
  seqBtn: el("seqBtn"),
  importBtn: el("importBtn"),
  hint: el("hint"),
  diagBtn: document.getElementById("diagBtn"),
  updBtn: el("updBtn"),
};

let picked = [];   // [{name, path}]
let lastXml = null;

/* ---------------------------------------------------- motor holati */

async function checkMotor() {
  const errors = [];
  for (const base of MOTOR_URLS) {
    try {
      const r = await fetch(base + "/health");
      const j = await r.json();
      if (j.ok) {
        MOTOR = base;
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
  const denied = /permission|denied|manifest/i.test(lastMotorError);
  els.motorTxt.textContent = denied
    ? "Motorga ruxsat berilmadi — panelni UDT'da Unload/Load qiling"
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

        // Ovoz manbasi — vazifadan alohida: kamera ham, ovoz ham bo'lishi mumkin
        const snd = document.createElement("span");
        const isMaster = audioMaster === p.path;
        snd.className = "snd" + (isMaster ? " on" : "");
        snd.textContent = isMaster ? "♪ ovoz manbasi" : "♪ ovoz?";
        snd.title = isMaster
          ? "Ovoz shu fayldan olinadi — bekor qilish uchun bosing"
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
      els.importBtn.disabled = true;
      els.log.innerHTML = "";
      els.log.classList.remove("show");
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
      const track = i < vCount
        ? await seq.getVideoTrack(i)
        : await seq.getAudioTrack(i - vCount);
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
        items.push({ path: path, start: start, in: inP, out: inP + (end - start) });
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
    renderFiles();
    logLine("Sequence olindi: " + timeline.length + " klip, " +
            picked.length + " fayl ✓", "okline");
    logLine("Endi «Pauzalarni kesish» ni bosing — montajingiz saqlanadi");
  } catch (e) {
    timeline = null;
    logLine("Sequence o'qilmadi (" + step + "): " + e.message, "warn");
    logLine("Fayllarni qo'lda tanlashingiz mumkin — natija bir xil bo'ladi");
  }
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

  try {
    const r = await fetch(MOTOR + "/" + endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");

    for (const line of j.logs || []) {
      logLine(line, line.indexOf("OGOHLANTIRISH") >= 0 ? "warn" : null);
    }
    lastXml = isCap ? null : j.output;
    if (isCap) {
      logLine(j.line_count + " qator · " + j.word_count + " so'z" +
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
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
  }
  updateRunButtons();
}

function updateRunButtons() {
  els.syncBtn.disabled = picked.length < 2;
  els.cutBtn.disabled = picked.length < 1;
  els.switchBtn.disabled = picked.length < 2;
  els.capBtn.disabled = picked.length < 1;
  els.sampleBtn.disabled = picked.length < 1;
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
on(els.capSearchBtn, searchArchive);
on(els.seqBtn, readSequence);
on(els.importBtn, doImport);

setupTabs();
setupKnobs();
setupCaptionPills();
document.body.className = "tab-sync";
checkMotor().then(function (ok) { if (ok) checkUpdates(); });
setInterval(checkMotor, 5000);
setInterval(checkUpdates, 10 * 60 * 1000);   // har 10 daqiqada bir tekshiradi
renderFiles();

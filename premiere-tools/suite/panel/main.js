/* Podcast Suite — panel mantiqi (Sync va Cut modullari).
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
};

function setupKnobs() {
  Object.values(knobs).forEach((k) => {
    if (!k.el.addEventListener) return;
    const show = () => { k.out.textContent = k.fmt(+k.el.value); };
    k.el.addEventListener("input", show);
    show();
  });
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
  els.log.innerHTML = "";
  els.syncBtn.disabled = true;
  els.cutBtn.disabled = true;
  els.importBtn.disabled = true;
  logLine(isCut ? "Pauzalar qidirilmoqda…" : "Sinxronlash boshlandi…");

  const body = {
    files: picked.map((p) => p.path),
    name: isCut ? "Podcast Suite — Cut" : "Podcast Suite — Sync",
  };
  if (isCut) {
    body.threshold = knobs.threshold.val(+knobs.threshold.el.value);
    body.min_pause = knobs.minPause.val(+knobs.minPause.el.value);
    body.padding = knobs.padding.val(+knobs.padding.el.value);
  }

  try {
    const r = await fetch(MOTOR + "/" + kind, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");

    for (const line of j.logs || []) {
      logLine(line, line.indexOf("OGOHLANTIRISH") >= 0 ? "warn" : null);
    }
    lastXml = j.output;
    if (isCut) {
      const mins = (s) => Math.floor(s / 60) + " daq " + Math.round(s % 60) + " s";
      logLine(j.pauses.length + " pauza kesildi — " + mins(j.saved_sec) +
              " qisqardi", "okline");
      logLine("Uzunlik: " + mins(j.total_sec) + " → " + mins(j.new_length_sec));
    } else {
      renderFiles(j.clips);
    }
    logLine("Tayyor ✓ — endi «Premiere'ga import» ni bosing", "okline");
    logLine("Fayl: " + j.output);
    els.importBtn.disabled = false;
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
  }
  updateRunButtons();
}

function updateRunButtons() {
  els.syncBtn.disabled = picked.length < 2;
  els.cutBtn.disabled = picked.length < 1;
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
on(els.importBtn, doImport);

setupTabs();
setupKnobs();
document.body.className = "tab-sync";
checkMotor().then(function (ok) { if (ok) checkUpdates(); });
setInterval(checkMotor, 5000);
setInterval(checkUpdates, 10 * 60 * 1000);   // har 10 daqiqada bir tekshiradi
renderFiles();

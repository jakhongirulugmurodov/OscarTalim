/* Podcast Suite — panel mantiqi (1-bosqich: Sync moduli).
 *
 * Panel o'zi hech qanday og'ir ish qilmaydi: fayllarni tanlatadi,
 * lokal motorga (server.py, 127.0.0.1:8765) yuboradi, natijani
 * ko'rsatadi va tayyor XML'ni Premiere loyihasiga import qiladi.
 */

const MOTOR = "http://127.0.0.1:8765";

const uxp = require("uxp");
const lfs = uxp.storage.localFileSystem;

const els = {
  motor: document.getElementById("motor"),
  motorTxt: document.getElementById("motorTxt"),
  pick: document.getElementById("pick"),
  files: document.getElementById("files"),
  log: document.getElementById("log"),
  syncBtn: document.getElementById("syncBtn"),
  importBtn: document.getElementById("importBtn"),
  hint: document.getElementById("hint"),
};

let picked = [];   // [{name, path}]
let lastXml = null;

/* ---------------------------------------------------- motor holati */

async function checkMotor() {
  try {
    const r = await fetch(MOTOR + "/health");
    const j = await r.json();
    if (j.ok) {
      els.motor.classList.add("ok");
      els.motorTxt.textContent = "Motor ishlayapti (v" + j.version + ")";
      return true;
    }
  } catch (e) { /* motor o'chiq */ }
  els.motor.classList.remove("ok");
  els.motorTxt.textContent =
    "Motor topilmadi — engine papkasida «python3 server.py» ni ishga tushiring";
  return false;
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
      off.className = "off";
      off.textContent = res.is_reference
        ? "tayanch"
        : "+" + res.offset_sec.toFixed(3) + "s";
      row.appendChild(off);
      if (!res.is_reference) {
        const conf = document.createElement("span");
        conf.className = "conf";
        conf.textContent = Math.round(res.confidence) + "×";
        row.appendChild(conf);
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
  els.syncBtn.disabled = picked.length < 2;
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

async function doSync() {
  if (!(await checkMotor())) return;

  els.log.innerHTML = "";
  els.syncBtn.disabled = true;
  els.importBtn.disabled = true;
  logLine("Sinxronlash boshlandi…");

  try {
    const r = await fetch(MOTOR + "/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: picked.map((p) => p.path),
        name: "Podcast Suite — Sync",
      }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "Motor xatosi");

    for (const line of j.logs || []) {
      logLine(line, line.indexOf("OGOHLANTIRISH") >= 0 ? "warn" : null);
    }
    lastXml = j.output;
    renderFiles(j.clips);
    logLine("Tayyor ✓ — endi «Premiere'ga import» ni bosing", "okline");
    els.importBtn.disabled = false;
  } catch (e) {
    logLine("Xato: " + e.message, "warn");
  }
  els.syncBtn.disabled = picked.length < 2;
}

/* ------------------------------------------- Premiere'ga import */

async function doImport() {
  if (!lastXml) return;
  try {
    const ppro = require("premierepro");
    const project = await ppro.Project.getActiveProject();
    if (!project) throw new Error("Ochiq loyiha topilmadi");
    await project.importFiles([lastXml]);
    logLine("Sequence loyihaga qo'shildi ✓", "okline");
  } catch (e) {
    // API mos kelmasa — qo'lda import yo'lini ko'rsatamiz
    logLine("Avtomatik import ishlamadi (" + e.message + ").", "warn");
    logLine("Qo'lda: File > Import > " + lastXml);
  }
}

/* ---------------------------------------------------- ulanishlar */

els.pick.addEventListener("click", pickFiles);
els.syncBtn.addEventListener("click", doSync);
els.importBtn.addEventListener("click", doImport);

checkMotor();
setInterval(checkMotor, 5000);
renderFiles();

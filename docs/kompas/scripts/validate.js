#!/usr/bin/env node
/* Kompas ma'lumot validatori. Ishlatish: node docs/kompas/scripts/validate.js [--quiet]
   Barcha data/*.js fayllarini soxta `window` bilan yuklaydi va sxema qoidalarini tekshiradi. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const quiet = process.argv.includes("--quiet");
const errors = [], warns = [];
const err = (m) => errors.push(m);
const warn = (m) => warns.push(m);

const window = {};
function load(rel) {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) return false;
  const src = fs.readFileSync(p, "utf8");
  if (/[Ѐ-ӿ]/.test(src.replace(/nom_ru:\s*"[^"]*"/g, ""))) err(`${rel}: kirill harflari bor`);
  if (/[‘’ʻʼ`]/.test(src)) warn(`${rel}: nostandart apostrof (‘ ’ ʻ ʼ \`) — faqat ' ishlatilsin`);
  try { vm.runInNewContext(src, { window, console }); } catch (e) { err(`${rel}: JS xatosi — ${e.message}`); }
  return true;
}
function loadDir(rel) {
  const p = path.join(ROOT, rel);
  if (!fs.existsSync(p)) return [];
  return fs.readdirSync(p).filter(f => f.endsWith(".js")).sort().map(f => { load(rel + "/" + f); return f; });
}

load("js/config.js");
load("data/fanlar.js");
load("data/otmlar.js");
const yFiles = loadDir("data/yonalishlar");
const mFiles = loadDir("data/mavzular");
load("data/riasec_savollar.js");

const cfg = window.KOMPAS_CONFIG, FAN = window.KOMPAS_FANLAR || {}, OTM = window.KOMPAS_OTMLAR || [];
const HUD = window.KOMPAS_HUDUDLAR || [];
const otmIds = new Set(OTM.map(o => o.id));
const KEYS = ["R", "I", "A", "S", "E", "C"];

/* ---- config ---- */
if (cfg) {
  const sum = cfg.savol.fan1 * cfg.koef.fan1 + cfg.savol.fan2 * cfg.koef.fan2 + 3 * cfg.savol.majburiy * cfg.koef.majburiy;
  if (Math.abs(sum - cfg.max_ball) > 0.01) err(`config: ball yig'indisi ${sum} ≠ ${cfg.max_ball}`);
} else err("config.js yuklanmadi");

/* ---- yo'nalishlar ---- */
const Y = window.KOMPAS_YONALISHLAR || [];
const ids = new Set(), noms = new Set();
const LEVELS = ["yuqori", "orta", "past"];
Y.forEach((y, i) => {
  const tag = `yonalish[${y.id || i}]`;
  if (!y.id || !/^[a-z0-9_]+$/.test(y.id)) err(`${tag}: id lotin slug bo'lishi kerak`);
  if (ids.has(y.id)) err(`${tag}: id takrorlangan`); ids.add(y.id);
  if (!y.nom) err(`${tag}: nom yo'q`);
  if (noms.has((y.nom || "").toLowerCase())) warn(`${tag}: nom takror — "${y.nom}"`); noms.add((y.nom || "").toLowerCase());
  if (y.kod != null && !/^\d{8}$/.test(String(y.kod))) err(`${tag}: kod 8 raqam yoki null bo'lsin`);
  if (!FAN[y.fan1]) err(`${tag}: fan1 noma'lum — ${y.fan1}`);
  if (!FAN[y.fan2]) err(`${tag}: fan2 noma'lum — ${y.fan2}`);
  if (y.fan1 && y.fan1 === y.fan2) err(`${tag}: fan1 va fan2 bir xil`);
  if (FAN[y.fan1] && !FAN[y.fan1].rollar.includes("ixtisoslik")) err(`${tag}: fan1 ixtisoslik fani emas`);
  if (y.fan1 === "ijodiy") err(`${tag}: ijodiy imtihon faqat fan2 bo'ladi`);
  if ((y.fan2 === "ijodiy") !== !!y.ijodiy) err(`${tag}: ijodiy bayrog'i fan2 bilan mos emas`);
  if ((y.fan1 === "ingliz_tili") !== !!y.sertifikat) err(`${tag}: sertifikat bayrog'i fan1 bilan mos emas`);
  if (!y.riasec) err(`${tag}: riasec yo'q`);
  else {
    KEYS.forEach(k => { const v = y.riasec[k]; if (typeof v !== "number" || v < 0 || v > 1) err(`${tag}: riasec.${k} 0..1 emas`); });
    const vals = KEYS.map(k => y.riasec[k] || 0);
    if (Math.max(...vals) < 0.6) warn(`${tag}: riasec profili sust (max < 0.6)`);
    if (Math.max(...vals) - Math.min(...vals) < 0.3) warn(`${tag}: riasec profili yassi`);
  }
  if (!Array.isArray(y.kasblar) || y.kasblar.length < 2) err(`${tag}: kasblar kamida 2 ta`);
  if (!y.tavsif || y.tavsif.length < 40) warn(`${tag}: tavsif qisqa`);
  if (!LEVELS.includes(y.istiqbol)) err(`${tag}: istiqbol ${y.istiqbol}`);
  if (!LEVELS.includes(y.raqobat)) err(`${tag}: raqobat ${y.raqobat}`);
  if (!y.otish_taxmin) err(`${tag}: otish_taxmin yo'q`);
  else {
    ["grant", "kontrakt"].forEach(t => {
      const b = y.otish_taxmin[t];
      if (!b) { if (t === "grant") warn(`${tag}: grant oralig'i yo'q`); return; }
      if (!Array.isArray(b) || b.length !== 2 || !(b[0] < b[1])) err(`${tag}: otish_taxmin.${t} [lo,hi] emas`);
      else {
        if (b[0] < 56 || b[1] > 189) err(`${tag}: otish_taxmin.${t} 56..189 tashqarisida`);
        if (b[1] - b[0] < 12) warn(`${tag}: otish_taxmin.${t} oralig'i tor (<12)`);
      }
    });
    const g = y.otish_taxmin.grant, k = y.otish_taxmin.kontrakt;
    if (g && k && k[0] > g[0]) err(`${tag}: kontrakt oralig'i grantdan yuqori`);
  }
  if (!Array.isArray(y.otmlar) || !y.otmlar.length) err(`${tag}: otmlar bo'sh`);
  else y.otmlar.forEach(o => { if (!otmIds.has(o)) err(`${tag}: noma'lum OTM id — ${o}`); });
  if (!Array.isArray(y.hududlar) || !y.hududlar.length) err(`${tag}: hududlar bo'sh`);
  else y.hududlar.forEach(h => { if (h !== "*" && !HUD.includes(h)) err(`${tag}: noma'lum hudud — ${h}`); });
  if (!["taxminiy", "tekshirilsin"].includes(y.ishonch)) err(`${tag}: ishonch qiymati`);
});
if (Y.length < 60) warn(`yo'nalishlar soni kam: ${Y.length}`);

/* ---- mavzular ---- */
const M = window.KOMPAS_MAVZULAR || {};
Object.keys(M).forEach(fan => {
  const tag = `mavzular[${fan}]`;
  if (!FAN[fan]) err(`${tag}: noma'lum fan`);
  const t = M[fan];
  if (!t || !Array.isArray(t.mavzular)) { err(`${tag}: mavzular massivi yo'q`); return; }
  const n = t.mavzular.length;
  if (n < 20 || n > 45) warn(`${tag}: mavzular soni ${n} (kutilgan 25–40)`);
  let sum = 0, hours = 0; const mids = new Set();
  t.mavzular.forEach((m, i) => {
    const mt = `${tag}.${m.id || i}`;
    if (!m.id) err(`${mt}: id yo'q`); if (mids.has(m.id)) err(`${mt}: id takror`); mids.add(m.id);
    if (!m.nom || !m.bolim) err(`${mt}: nom/bolim yo'q`);
    if (typeof m.ulush !== "number" || m.ulush <= 0) err(`${mt}: ulush`); else sum += m.ulush;
    if (typeof m.bazaviy_soat !== "number" || m.bazaviy_soat < 1 || m.bazaviy_soat > 16) err(`${mt}: bazaviy_soat 1..16 emas`); else hours += m.bazaviy_soat;
    if (typeof m.qiyinlik !== "number" || m.qiyinlik < 0.1 || m.qiyinlik > 0.95) err(`${mt}: qiyinlik 0.1..0.95 emas`);
  });
  if (Math.abs(sum - 1) > 0.003) err(`${tag}: Σ ulush = ${sum.toFixed(3)} ≠ 1.000`);
  const majburiy = ["ona_tili", "tarix"].includes(fan);
  const [lo, hi] = majburiy ? [80, 150] : [130, 240];
  if (hours < lo || hours > hi) warn(`${tag}: Σ bazaviy_soat = ${hours} (kutilgan ${lo}–${hi})`);
});

/* ---- RIASEC ---- */
const R = window.KOMPAS_RIASEC;
if (!R) err("riasec_savollar.js yuklanmadi");
else {
  if (R.length !== 60) err(`riasec: ${R.length} savol (60 kerak)`);
  const cnt = {}; const qids = new Set();
  R.forEach((q, i) => {
    if (!q.id || qids.has(q.id)) err(`riasec[${i}]: id yo'q/takror`); qids.add(q.id);
    if (!KEYS.includes(q.shkala)) err(`riasec[${q.id}]: shkala ${q.shkala}`);
    cnt[q.shkala] = (cnt[q.shkala] || 0) + 1;
    const w = (q.matn || "").trim().split(/\s+/).length;
    if (w < 2 || w > 12) warn(`riasec[${q.id}]: matn uzunligi ${w} so'z`);
  });
  KEYS.forEach(k => { if (cnt[k] !== 10) err(`riasec: ${k} shkalasida ${cnt[k] || 0} savol (10 kerak)`); });
}

/* ---- xulosa ---- */
if (!quiet) {
  warns.forEach(w => console.log("  ⚠ " + w));
  errors.forEach(e => console.log("  ✗ " + e));
}
console.log(`\nyo'nalishlar: ${Y.length} (${yFiles.length} fayl) · mavzular: ${Object.keys(M).length} fan (${mFiles.length} fayl) · riasec: ${R ? R.length : 0} · OTM: ${OTM.length}`);
console.log(`${errors.length} xato, ${warns.length} ogohlantirish`);
process.exit(errors.length ? 1 : 0);

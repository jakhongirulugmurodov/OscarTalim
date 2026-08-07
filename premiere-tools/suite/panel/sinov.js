#!/usr/bin/env node
/* Panel kodini Premiere'siz ishga tushirib sinaydigan qurilma.
 *
 * Nima uchun kerak: `node --check` faqat SINTAKSISNI tekshiradi. U
 * «yozildi is not defined» kabi xatolarni ko'rmaydi, chunki bunday xato
 * faqat kod ISHLAGANDA chiqadi. Aynan shunday xato bir marta o'tib
 * ketdi: Harakat moduli hamma ishni bajarib, oxirida qizil «To'xtadi»
 * berardi.
 *
 * Bu yerda Premiere API'si, DOM va motor soxta qilib berilади, so'ng
 * asosiy funksiyalar chaqiriladi. Xato chiqsa — sinov yiqiladi.
 *
 * Ishga tushirish:  node sinov.js
 */

const fs = require("fs");
const path = require("path");
const vm = require("vm");

// ───────────────────────────────── soxta DOM
function element(id) {
  const e = {
    id: id, tagName: "DIV", textContent: "", innerHTML: "", value: "",
    disabled: false, checked: false, dataset: {},
    style: { display: "", width: "", left: "" },
    childNodes: [], parentElement: null, offsetParent: {},
    classList: {
      _s: new Set(),
      add(...c) { c.forEach((x) => this._s.add(x)); },
      remove(...c) { c.forEach((x) => this._s.delete(x)); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    },
    addEventListener() {}, removeEventListener() {},
    appendChild(c) { this.childNodes.push(c); return c; },
    removeChild(c) {
      const i = this.childNodes.indexOf(c);
      if (i >= 0) this.childNodes.splice(i, 1);
      return c;
    },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    getAttribute() { return null; },
    setAttribute() {},
    scrollTo() {}, focus() {}, click() {},
    getBoundingClientRect() { return { width: 100, height: 20, top: 0, x: 0, y: 0 }; },
  };
  Object.defineProperty(e, "firstChild", { get() { return this.childNodes[0] || null; } });
  return e;
}

const kesh = {};
const hujjat = {
  getElementById(id) { return (kesh[id] = kesh[id] || element(id)); },
  createElement(t) { const e = element(""); e.tagName = (t || "div").toUpperCase(); return e; },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  addEventListener() {},
  body: element("body"),
};

// ───────────────────────────────── soxta Premiere
let YOZILGAN = [];        // tranzaksiyaga tushgan amallar
let TRANZAKSIYA = 0;      // necha marta executeTransaction chaqirildi

function param(scale) {
  return {
    _v: scale,
    getValue: async () => scale,
    isTimeVarying: async () => false,
    createSetValueAction: (v) => ({ tur: "statik", qiymat: v }),
    createSetTimeVaryingAction: (b) => ({ tur: "vaqtli", qiymat: b }),
    createSetValueAtKeyframeAction: (t, v) => ({ tur: "keyframe", vaqt: t, qiymat: v }),
  };
}

function trackItem(nomi, opts) {
  const o = opts || {};
  return {
    _nomi: nomi,
    getStartTime: async () => ({ seconds: o.start || 0 }),
    getEndTime: async () => ({ seconds: o.end != null ? o.end : 40 }),
    getInPoint: async () => ({ seconds: o.in || 0 }),
    getOutPoint: async () => ({ seconds: o.srcOut != null ? o.srcOut : 40 }),
    getComponentChain: async () => ({
      getComponentCount: async () => 1,
      getComponentAtIndex: async () => ({
        getParam: async (n) => (n === "Scale" ? param(o.scale || 100) : null),
        getMatchName: async () => "AE.ADBE Motion",
        getDisplayName: async () => "Motion",
      }),
    }),
    getProjectItem: async () => ({ getMediaFilePath: async () => o.path || "/m/kamera.mp4" }),
  };
}

function premierepro(qurilish) {
  const q = qurilish || {};
  const treklar = q.treklar || [[trackItem("v1a"), trackItem("v1b")]];
  const seq = {
    name: q.nomi || "Montaj v3",
    getVideoTrackCount: async () => treklar.length,
    getVideoTrack: async (i) => (treklar[i]
      ? { getTrackItems: async () => treklar[i] } : null),
    getAudioTrackCount: async () => 0,
    getAudioTrack: async () => null,
    getSettings: async () => {
      if (q.sozlamaYoq) return null;
      // Haqiqiy Premiere qiymatlarni PROTOTIPDA beradi — Object.keys()
      // bo'sh chiqadi. Foydalanuvchida aynan shu holat bo'lgan.
      const nomlar = q.olchamNomlari
        || { videoFrameWidth: 1920, videoFrameHeight: 1080 };
      const proto = {};
      for (const k of Object.keys(nomlar)) {
        Object.defineProperty(proto, k, { get: () => nomlar[k], enumerable: false });
      }
      return Object.create(proto);
    },
    getEndTime: async () => ({ seconds: 300 }),
    getInPoint: async () => ({ seconds: 0 }),
    getOutPoint: async () => ({ seconds: 300 }),
    createSetInPointAction: (t) => ({ tur: "in", vaqt: t }),
    createSetOutPointAction: (t) => ({ tur: "out", vaqt: t }),
    createSubsequence: async () => {
      const nusxa = { ...seq, name: seq.name + " (nusxa)",
        getProjectItem: async () => ({ createSetNameAction: (n) => ({ tur: "nom", nomi: n }) }) };
      // Haqiqiy Premiere'da nusxaning getSettings'i ishlamay qolgan edi —
      // shuni taqlid qilamiz
      if (q.nusxaOlchamsiz) nusxa.getSettings = async () => null;
      return nusxa;
    },
    getProjectItem: async () => ({ createSetNameAction: (n) => ({ tur: "nom", nomi: n }) }),
    getMarkers: async () => [],
  };
  const project = {
    getActiveSequence: async () => seq,
    openSequence: async () => true,
    setActiveSequence: async () => true,
    lockedAccess(fn) { return fn(); },
    executeTransaction(fn) {
      TRANZAKSIYA++;
      const compound = { addAction: (a) => YOZILGAN.push(a) };
      fn(compound);
      return q.tranzaksiyaRad ? false : true;
    },
  };
  return {
    Project: { getActiveProject: async () => project },
    Sequence: {}, Markers: {}, ClipProjectItem: {},
    TickTime: { createWithSeconds: (s) => ({ seconds: s }) },
    SequenceEditor: { getEditor: () => ({}) },
    Constants: { MediaType: { VIDEO: "video" } },
  };
}

// ───────────────────────────────── ishga tushirish
function muhit(qurilish, reja) {
  const g = {
    document: hujjat,
    window: { addEventListener() {} },
    console: { log() {}, warn() {}, error() {} },
    setTimeout, clearTimeout, setInterval: () => 1, clearInterval() {},
    Date, Math, JSON, Set, Map, Promise, Object, Array, String, Number, Error,
    require: (m) => {
      if (m === "premierepro") return premierepro(qurilish);
      if (m === "uxp") return { storage: {}, shell: {} };
      if (m === "fs") return { existsSync: () => false };
      return {};
    },
    fetch: async (url) => ({
      ok: true,
      json: async () => {
        if (String(url).indexOf("/harakat") >= 0) return reja;
        if (String(url).indexOf("/health") >= 0) {
          return { ok: true, version: "0.2.0", modules: ["harakat"], panel_build: null };
        }
        return {};
      },
    }),
  };
  g.globalThis = g;
  return g;
}

/* Log matni: logLine() element yasab qo'shadi, shuning uchun matnni
   innerHTML dan emas, qo'shilgan bolalardan yig'amiz. */
function logMatni() {
  const el = kesh.log;
  if (!el) return "";
  return (el.childNodes || []).map((c) => c.textContent || "").join("\n")
       + String(el.innerHTML || "");
}

const KOD = fs.readFileSync(path.join(__dirname, "main.js"), "utf8");

async function sinov(nomi, qurilish, reja, tekshir) {
  YOZILGAN = []; TRANZAKSIYA = 0;
  for (const k of Object.keys(kesh)) delete kesh[k];
  const g = muhit(qurilish, reja);
  const ctx = vm.createContext(g);
  try {
    vm.runInContext(KOD, ctx, { filename: "main.js" });
  } catch (e) {
    console.log(`  ✗ ${nomi}: kod yuklanmadi — ${e.message}`);
    return false;
  }
  // Panel PANEL_BUILD ni motorga solishtiradi; soxta motor null qaytaradi
  try {
    await ctx.harakatQoshish();
  } catch (e) {
    console.log(`  ✗ ${nomi}: ISHLAB TURGANDA XATO — ${e.message}`);
    return false;
  }
  const r = tekshir
    ? tekshir({ yozilgan: YOZILGAN, tranzaksiya: TRANZAKSIYA, log: logMatni() })
    : true;
  if (r === true) { console.log(`  ✓ ${nomi}`); return true; }
  console.log(`  ✗ ${nomi}: ${r}`);
  return false;
}

(async () => {
  console.log("Panel sinovi (Premiere'siz)\n");
  let ok = 0, jami = 0;

  const rejaOddiy = {
    rejalar: [{ idx: 0, nomi: "kamera.mp4", uzunlik: 40, max_k: 1.98, kuch: 5,
                harakat: true,
                keys: [{ t: 0, d: 0 }, { t: 12, d: 4.5 }, { t: 25, d: 0 },
                       { t: 40, d: 4.2 }] }],
    joysiz: [], log: ["1 klipga reja tuzildi"],
    stat: { jami: 1, harakatli: 1, joysiz: 0 },
  };

  jami++; ok += await sinov(
    "oddiy holat: keyframe yoziladi va tranzaksiya bitta",
    {}, rejaOddiy,
    (r) => {
      if (r.tranzaksiya < 1) return "tranzaksiya umuman bo'lmadi";
      const kf = r.yozilgan.filter((a) => a && a.tur === "keyframe");
      if (kf.length !== 4) return `4 keyframe kutilgandi, ${kf.length} ta yozildi`;
      return true;
    }) ? 1 : 0;

  // Tezlik: klip timeline'da 40s, manbada 20s (50% tezlik).
  // Keyframe'lar manba o'qida in..in+20 oralig'ida bo'lishi kerak.
  jami++; ok += await sinov(
    "50% tezlik: keyframe'lar klip ichida qoladi",
    { treklar: [[trackItem("sekin", { start: 0, end: 40, in: 10, srcOut: 30 })]] },
    rejaOddiy,
    (r) => {
      const kf = r.yozilgan.filter((a) => a && a.tur === "keyframe");
      if (!kf.length) return "keyframe yozilmadi";
      const oxirgi = Math.max(...kf.map((k) => k.vaqt.seconds));
      if (oxirgi > 30.01) {
        return `oxirgi keyframe ${oxirgi.toFixed(1)}s — klip chegarasi 30s dan tashqarida`;
      }
      return true;
    }) ? 1 : 0;

  // Tranzaksiya rad etilsa — «tayyor» deb yozmasligi kerak
  jami++; ok += await sinov(
    "tranzaksiya rad etilsa xato beriladi",
    { tranzaksiyaRad: true }, rejaOddiy,
    (r) => {
      if (r.log.indexOf("qabul qilmadi") < 0) {
        return "rad etilgani aytilmadi. Log: " + r.log.slice(0, 120);
      }
      return true;
    }) ? 1 : 0;

  jami++; ok += await sinov(
    "nusxadan o'lcham o'qilmasa — asl montajdan olinadi",
    { nusxaOlchamsiz: true }, rejaOddiy,
    (r) => {
      if (r.log.indexOf("o'lchamini o'qib bo'lmadi") >= 0) {
        return "o'lcham topilmadi deb to'xtadi — asl montajdan olinishi kerak edi";
      }
      const kf = r.yozilgan.filter((a) => a && a.tur === "keyframe");
      if (!kf.length) return "keyframe yozilmadi";
      return true;
    }) ? 1 : 0;

  jami++; ok += await sinov(
    "o'lcham prototipda bo'lsa ham topiladi (haqiqiy Premiere shakli)",
    {}, rejaOddiy,
    (r) => (r.log.indexOf("o'lchamini o'qib bo'lmadi") >= 0
            ? "prototipdagi o'lcham topilmadi" : true)) ? 1 : 0;

  jami++; ok += await sinov(
    "noma'lum nomdagi o'lcham ham topiladi",
    { olchamNomlari: { seqFrameWidth: 1080, seqFrameHeight: 1920 } }, rejaOddiy,
    (r) => (r.log.indexOf("o'lchamini o'qib bo'lmadi") >= 0
            ? "noma'lum nomdagi o'lcham topilmadi" : true)) ? 1 : 0;

  jami++; ok += await sinov(
    "o'lcham umuman topilmasa — nima ko'rilgani aytiladi",
    { sozlamaYoq: true, treklar: [[trackItem("x")]] }, rejaOddiy,
    (r) => {
      if (r.log.indexOf("o'lchamini o'qib bo'lmadi") < 0) return "xato berilmadi";
      if (r.log.indexOf("Ko'rilgan") < 0 && r.log.indexOf("sequence:") < 0) {
        return "nima ko'rilgani aytilmadi — tashxis uchun shart";
      }
      return true;
    }) ? 1 : 0;

  console.log(`\n${ok}/${jami} sinov o'tdi`);
  process.exit(ok === jami ? 0 : 1);
})();

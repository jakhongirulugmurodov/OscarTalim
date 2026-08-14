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


/* ═══════════════════ Joyida qirqish: boshdan-oxir sinov
 *
 * Bu sinov montajniQirqish() ni SOXTA Premiere bilan to'liq yugurtiradi.
 * Soxta API haqiqiy Premiere kabi o'zini tutadi: nusxa olinganda
 * bog'langan ovoz ham ko'chiriladi, amallar esa klip joyini haqiqatan
 * o'zgartiradi. Shundan keyin natija tekshiriladi.
 *
 * Nima uchun kerak: bu yerda ikki xato chiqqan edi — ovoz video tagiga
 * tushmay unlink bo'lib qolgani va tranzaksiyadan keyin obyektlar
 * eskirgani. Ikkalasi ham faqat KOD ISHLAGANDA ko'rinadi. */
function qirqishMuhiti(q) {
  const treklarV = [[]], treklarA = [[]];

  function klip(st, en, ip, audio, path) {
    const o = {
      _a: audio, _p: path, start: st, end: en, in: ip,
      _trekV: treklarV[0], _trekA: treklarA[0],
      getStartTime: async () => ({ seconds: o.start }),
      getEndTime: async () => ({ seconds: o.end }),
      getInPoint: async () => ({ seconds: o.in }),
      getProjectItem: async () => ({ getMediaFilePath: async () => path }),
      // Haqiqiy Premiere'da in-nuqtani surish klipning BOSHINI qirqadi,
      // ya'ni u timeline'da ham suriladi. Ilgari panel klipni eski joyi
      // bo'yicha qidirar edi va shu sababdan «topilmadi» derdi —
      // soxta API buni taqlid qilmasa, sinov o'sha xatoni ko'rmaydi.
      createSetInPointAction: (t) => ({
        bajar() { o.start += t.seconds - o.in; o.in = t.seconds; } }),
      createSetOutPointAction: (t) => ({
        bajar() { o.end = o.start + (t.seconds - o.in); } }),
      // DIQQAT: haqiqiy Premiere'da setStart klipni SURMAYDI — chap
      // chetini cho'zadi, oxiri joyida qoladi. Haqiqiy montajda bo'lak
      // «0.12–905.42s» bo'lib chiqqani shundan. Soxta API ham shunday
      // tutadi: panel surish uchun setStart ishlatsa, sinov yiqiladi.
      createSetStartAction: (t) => ({ bajar() { o.start = t.seconds; } }),
      createSetEndAction: (t) => ({ bajar() { o.end = t.seconds; } }),
      // Klipni haqiqatan suradigan amal. Semantika sozlanadi: nisbiy
      // (standart) yoki q.mutlaqMove bilan mutlaq — panel ikkalasiga
      // ham moslasha olishi kerak, chunki hujjatda bu yozilmagan.
      createMoveAction: (t) => {
        if (q.joyRad) throw new Error("A nullptr was dereferenced.");
        return { bajar() {
          const d = o.end - o.start;
          const a = q.mutlaqMove ? t.seconds : o.start + t.seconds;
          const b = a + d;
          // Premiere band joyga surishga ruxsat bermaydi
          const ro = o._a ? o._trekA : o._trekV;
          for (const x of ro) {
            if (x === o) continue;
            if (a < x.end - 1e-6 && x.start < b - 1e-6) {
              throw new Error("Invalid parameter.");
            }
          }
          o.start = a; o.end = b;
        } };
      },
    };
    return o;
  }

  // Bitta bog'langan juft: V1 da video, A1 da uning ovozi
  treklarV[0].push(klip(0, 30, 0, false, "/m/a.mp4"));
  treklarA[0].push(klip(0, 30, 0, true, "/m/a.mp4"));

  const seq = {
    name: "Sinov",
    getVideoTrackCount: async () => treklarV.length,
    getAudioTrackCount: async () => treklarA.length,
    getVideoTrack: async (i) => (treklarV[i]
      ? { getTrackItems: async () => treklarV[i].slice() } : null),
    getAudioTrack: async (i) => (treklarA[i]
      ? { getTrackItems: async () => treklarA[i].slice() } : null),
    getEndTime: async () => ({ seconds: 30 }),
    getSelection: async () => ({
      _x: [], addItem(it) { this._x.push(it); return true; },
      removeItem() { return true; }, getTrackItems: async () => [] }),
    clearSelection: async () => true,
  };

  const editor = {
    // Haqiqiy Premiere bog'langan klipni nusxalaganda OVOZINI HAM
    // ko'chiradi. Soxta API shuni taqlid qiladi — aks holda sinov
    // aynan o'sha xatoni o'tkazib yuborardi.
    // Haqiqiy Premiere nusxa olganda FAQAT berilgan klipni ko'chiradi —
    // bog'langan ovozni O'ZI olib kelmaydi. Buni haqiqiy montajda
    // ko'rdik: faqat video nusxalanganda ovoz butunlay yo'qolib qoldi.
    // Soxta API ham xuddi shunday tutadi — panel ikkala yarmini o'zi
    // nusxalamasa, sinovdagi ovoz tekshiruvi yiqiladi.
    createCloneTrackItemAction: (it, t) => ({
      bajar() {
        const ro = it._a ? treklarA : treklarV;
        ro[0].push(klip(it.start + t.seconds, it.end + t.seconds,
                        it.in, it._a, it._p));
      },
    }),
    createRemoveItemsAction: () => ({ bajar() {} }),
  };

  const project = {
    save: async () => true,
    getActiveSequence: async () => seq,
    lockedAccess(fn) { return fn(); },
    executeTransaction(fn, nomi) {
      const amallar = [];
      fn({ addAction: (a) => amallar.push(a) });
      // «Jim rad»: xato tashlamaydi, amallarni BAJARMAYDI, false
      // qaytaradi. Haqiqiy Premiere'da surish aynan shunday rad etilib,
      // 55 nusxa park'da qolgan, panel esa «Tayyor ✓» deb yozgan edi.
      if (q.jimRad && String(nomi).indexOf("surish") >= 0) return false;
      if (q.tranzaksiyaRad) return false;
      for (const a of amallar) if (a && a.bajar) a.bajar();
      return true;
    },
  };

  return {
    ppro: {
      Project: { getActiveProject: async () => project },
      ClipProjectItem: {}, Constants: { MediaType: { ANY: "any" } },
      TickTime: { createWithSeconds: (s) => ({ seconds: s }) },
      SequenceEditor: { getEditor: () => editor },
      TrackItemSelection: {},
    },
    treklarV: treklarV, treklarA: treklarA,
  };
}

async function qirqishSinovi(q) {
  for (const k of Object.keys(kesh)) delete kesh[k];
  const m = qirqishMuhiti(q || {});
  const g = muhit({}, {});
  // Faqat premierepro almashtiriladi — qolgan modullar (uxp, fs) o'z
  // joyida qolsin, aks holda main.js yuklanmay qoladi.
  const aslRequire = g.require;
  g.require = (mod) => (mod === "premierepro" ? m.ppro : aslRequire(mod));
  g.fetch = async (url) => ({
    ok: true,
    json: async () => {
      if (String(url).indexOf("/cut") >= 0) {
        return { pauses: [{ start: 10, end: 14 }, { start: 20, end: 22 }], logs: [] };
      }
      if (String(url).indexOf("/health") >= 0) {
        return { ok: true, version: "0.2.0", modules: ["cut"], panel_build: null };
      }
      return {};
    },
  });

  const ctx = vm.createContext(g);
  try { vm.runInContext(KOD, ctx, { filename: "main.js" }); }
  catch (e) { return "kod yuklanmadi — " + e.message; }

  try { await ctx.montajniQirqish(); }
  catch (e) { return "ISHLAB TURGANDA XATO — " + e.message; }

  const log = logMatni();
  // Kod xatosi log'ga yashirinib qolmasin — try/catch uni yutib yuboradi
  for (const belgi of ["is not defined", "is not a function", "undefined is not",
                       "Cannot read"]) {
    if (log.indexOf(belgi) >= 0) return "kod xatosi log'da: «" + belgi + "»";
  }
  if (q && (q.joyRad || q.jimRad)) {
    // Amal rad etilgan: panel to'xtashi, sababni yozishi va YOLG'ON
    // «tayyor» demasligi shart.
    if (log.indexOf("To'xtadi") < 0) return "amal rad etildi, lekin to'xtamadi";
    if (q.joyRad && log.indexOf("nullptr") < 0) return "sabab log'da yozilmagan";
    if (q.jimRad && log.indexOf("qabul qilmadi") < 0) {
      return "jim rad sababi log'da yozilmagan";
    }
    if (log.indexOf("bo'lak joylashtirildi") >= 0) return "yolg'on «tayyor» yozdi";
    return true;
  }
  if (log.indexOf("To'xtadi") >= 0) {
    return "to'xtadi: " + log.split("To'xtadi")[1].slice(0, 120);
  }

  // Kutilgan natija: [0,10] → 0–10, [14,20] → 10–16, [22,30] → 16–24
  const kutilgan = [[0, 10], [10, 16], [16, 24]];
  for (const [nom, ro] of [["V1", m.treklarV[0]], ["A1", m.treklarA[0]]]) {
    const bor = ro.map((x) => [+x.start.toFixed(2), +x.end.toFixed(2)])
                  .sort((a, b) => a[0] - b[0]);
    if (JSON.stringify(bor) !== JSON.stringify(kutilgan)) {
      return nom + ": " + JSON.stringify(bor) + ", kutilgan "
           + JSON.stringify(kutilgan);
    }
  }
  // Video va ovoz bir joyda turishi shart — bog'i uzilmasin
  const v = m.treklarV[0].slice().sort((a, b) => a.start - b.start);
  const a = m.treklarA[0].slice().sort((x, y) => x.start - y.start);
  for (let i = 0; i < v.length; i++) {
    if (Math.abs(v[i].start - a[i].start) > 0.01
        || Math.abs(v[i].end - a[i].end) > 0.01) {
      return "ovoz video tagida emas: V " + v[i].start + "–" + v[i].end
           + " · A " + a[i].start + "–" + a[i].end;
    }
  }
  return true;
}

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

  // «Har kesimda» rejimi: bitta keyframe — demak statik yo'ldan ketishi
  // va Premiere'ning keyframe API'siga umuman bog'liq bo'lmasligi kerak.
  const rejaKesim = {
    rejalar: [{ idx: 0, nomi: "kamera.mp4", uzunlik: 20, max_k: 1.0, kuch: 14,
                harakat: false, tor: true, keys: [{ t: 0, d: 14 }] }],
    joysiz: [], log: [], stat: { jami: 1, harakatli: 0, tor: 1, joysiz: 0 },
  };
  jami++; ok += await sinov(
    "kesim rejimi: keyframe'siz, statik Scale yoziladi",
    {}, rejaKesim,
    (r) => {
      const st = r.yozilgan.filter((a) => a && a.tur === "statik");
      const kf = r.yozilgan.filter((a) => a && a.tur === "keyframe");
      if (kf.length) return "keyframe yozildi — kesim rejimida kerak emas";
      if (st.length !== 1) return `1 statik qiymat kutilgandi, ${st.length} ta`;
      const kutilgan = 100 * 1.14;
      if (Math.abs(st[0].qiymat - kutilgan) > 0.5) {
        return `Scale ${st[0].qiymat} — kutilgan ${kutilgan}`;
      }
      return true;
    }) ? 1 : 0;

  /* ───────────── Montajni joyida qirqish: hisob-kitobi
   *
   * Bu ikki funksiya butun ishning asosi: qaysi bo'lak qoladi va u
   * yakuniy timeline'da qayerga tushadi. Xato bo'lsa montaj buziladi,
   * shuning uchun Premiere'siz, sof matematika sifatida sinaladi. */
  jami++; ok += (() => {
    const g = muhit({}, rejaOddiy);
    const ctx = vm.createContext(g);
    try { vm.runInContext(KOD, ctx, { filename: "main.js" }); }
    catch (e) { console.log("  ✗ qirqish hisobi: kod yuklanmadi — " + e.message); return 0; }

    const J = ctx.joylashuvniHisobla, S = ctx.siljish;
    if (typeof J !== "function" || typeof S !== "function") {
      console.log("  ✗ qirqish hisobi: funksiyalar topilmadi");
      return 0;
    }
    const teng = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const p = [{ start: 10, end: 14 }, { start: 20, end: 22 }];

    // Klip ikkita pauza bilan uchta bo'lakka bo'linadi
    if (!teng(J({ start: 0, end: 30 }, p),
              [{ a: 0, b: 10 }, { a: 14, b: 20 }, { a: 22, b: 30 }])) {
      console.log("  ✗ qirqish hisobi: uch bo'lakka bo'linmadi");
      return 0;
    }
    // Butunlay pauza ichida qolgan klipdan hech narsa qolmaydi
    if (J({ start: 10.5, end: 13 }, p).length !== 0) {
      console.log("  ✗ qirqish hisobi: pauza ichidagi klip o'chirilmadi");
      return 0;
    }
    // Pauzalarga umuman tegmagan klip butun qoladi
    if (!teng(J({ start: 40, end: 50 }, p), [{ a: 40, b: 50 }])) {
      console.log("  ✗ qirqish hisobi: tegilmagan klip bo'lindi");
      return 0;
    }
    // Pauza chetiga tegib turgan klip qisqaradi, yo'qolmaydi
    if (!teng(J({ start: 12, end: 18 }, p), [{ a: 14, b: 18 }])) {
      console.log("  ✗ qirqish hisobi: chetdagi klip noto'g'ri qirqildi");
      return 0;
    }
    // Siljish: 20-soniyagacha 4s olib tashlangan (10..14)
    if (Math.abs(S(20, p) - 4) > 1e-9) {
      console.log("  ✗ qirqish hisobi: siljish " + S(20, p) + ", kutilgan 4");
      return 0;
    }
    // Birinchi pauzadan oldin hech narsa siljimaydi
    if (S(5, p) !== 0) { console.log("  ✗ qirqish hisobi: erta siljish"); return 0; }
    // Hamma pauzadan keyin — ikkalasining yig'indisi
    if (Math.abs(S(30, p) - 6) > 1e-9) {
      console.log("  ✗ qirqish hisobi: yakuniy siljish " + S(30, p));
      return 0;
    }
    // Bo'laklar yakuniy timeline'da ustma-ust tushmasligi kerak
    const b = J({ start: 0, end: 30 }, p);
    let oxir = -1;
    for (const x of b) {
      const yangi = x.a - S(x.a, p);
      if (yangi < oxir - 1e-9) {
        console.log("  ✗ qirqish hisobi: bo'laklar ustma-ust tushdi");
        return 0;
      }
      oxir = yangi + (x.b - x.a);
    }
    console.log("  ✓ qirqish hisobi: bo'laklar va siljish to'g'ri");
    return 1;
  })();

  /* ───────────── Bog'langan video+ovoz juftini yig'ish
   *
   * Bu aynan bir marta yiqilgan joy: video va ovoz alohida nusxalanib,
   * ovoz butunlay boshqa vaqtga tushib, bog'i uzilgan edi. Juft bitta
   * birlikka yig'ilishi va nusxa faqat VIDEOdan olinishi shart. */
  jami++; ok += (() => {
    const g = muhit({}, rejaOddiy);
    const ctx = vm.createContext(g);
    try { vm.runInContext(KOD, ctx, { filename: "main.js" }); }
    catch (e) { console.log("  ✗ juft yig'ish: kod yuklanmadi — " + e.message); return 0; }
    const B = ctx.birlikYigish;
    if (typeof B !== "function") {
      console.log("  ✗ juft yig'ish: birlikYigish topilmadi"); return 0;
    }

    // Ikki kamera (video+ovoz bog'langan) + rekorder ovozi A2 da
    const kliplar = [
      { path: "/x/cam1.mp4", start: 0, end: 10, in: 0, audio: false, trek: 0 },
      { path: "/x/cam1.mp4", start: 0, end: 10, in: 0, audio: true,  trek: 0 },
      { path: "/x/cam2.mp4", start: 10, end: 20, in: 3, audio: false, trek: 0 },
      { path: "/x/cam2.mp4", start: 10, end: 20, in: 3, audio: true,  trek: 0 },
      { path: "/x/mic.wav",  start: 0, end: 20, in: 0, audio: true,  trek: 1 },
    ];
    const r = B(kliplar);
    if (r.length !== 3) {
      console.log(`  ✗ juft yig'ish: 3 birlik kutilgandi, ${r.length} ta`);
      return 0;
    }
    // Ikki kamera juft bo'lib birlashishi va yetakchisi VIDEO bo'lishi kerak
    const kamera = r.filter((b) => b.egalar.length === 2);
    if (kamera.length !== 2) {
      console.log(`  ✗ juft yig'ish: 2 juft kutilgandi, ${kamera.length} ta `
                  + "— video va ovoz birlashmadi");
      return 0;
    }
    if (kamera.some((b) => b.yetakchi.audio)) {
      console.log("  ✗ juft yig'ish: yetakchi ovoz bo'lib qoldi — nusxa "
                  + "videodan olinishi kerak");
      return 0;
    }
    // Rekorder ovozi yolg'iz qoladi va o'zi yetakchi bo'ladi
    const mic = r.find((b) => b.egalar.length === 1);
    if (!mic || !mic.yetakchi.audio) {
      console.log("  ✗ juft yig'ish: videosiz ovoz birligi noto'g'ri");
      return 0;
    }
    // Vaqt bo'yicha tartiblangan bo'lishi kerak
    for (let i = 1; i < r.length; i++) {
      if (r[i].start < r[i - 1].start) {
        console.log("  ✗ juft yig'ish: tartiblanmagan"); return 0;
      }
    }
    // Turli fayllar bir vaqtda tursa ham aralashmasligi kerak
    const ikki = B([
      { path: "/x/a.mp4", start: 0, end: 5, in: 0, audio: false, trek: 0 },
      { path: "/x/b.mp4", start: 0, end: 5, in: 0, audio: false, trek: 1 },
    ]);
    if (ikki.length !== 2) {
      console.log("  ✗ juft yig'ish: turli fayllar bitta birlikka qo'shildi");
      return 0;
    }
    console.log("  ✓ juft yig'ish: video+ovoz birga, yetakchi — video");
    return 1;
  })();

  jami++; ok += await (async () => {
    const r = await qirqishSinovi();
    if (r === true) {
      console.log("  \u2713 joyida qirqish (nisbiy move): uch bo'lak, ovoz video tagida");
      return 1;
    }
    console.log("  \u2717 joyida qirqish (nisbiy move): " + r);
    return 0;
  })();

  jami++; ok += await (async () => {
    const r = await qirqishSinovi({ mutlaqMove: true });
    if (r === true) {
      console.log("  \u2713 joyida qirqish (mutlaq move): moslashib ishladi");
      return 1;
    }
    console.log("  \u2717 joyida qirqish (mutlaq move): " + r);
    return 0;
  })();

  jami++; ok += await (async () => {
    const r = await qirqishSinovi({ joyRad: true });
    if (r === true) {
      console.log("  \u2713 amal rad etilsa: to'xtaydi va sababini yozadi");
      return 1;
    }
    console.log("  \u2717 amal rad etilsa: " + r);
    return 0;
  })();

  jami++; ok += await (async () => {
    const r = await qirqishSinovi({ jimRad: true });
    if (r === true) {
      console.log("  \u2713 jim rad (false): «tayyor» demaydi, to'xtaydi");
      return 1;
    }
    console.log("  \u2717 jim rad (false): " + r);
    return 0;
  })();

  console.log(`\n${ok}/${jami} sinov o'tdi`);
  process.exit(ok === jami ? 0 : 1);
})();

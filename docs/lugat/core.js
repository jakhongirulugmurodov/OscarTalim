// Yadro: holat, saqlash, takrorlash tizimi (SRS), XP, ovoz, grammatika tekshiruvi.
"use strict";

/* ================= yordamchilar ================= */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
const rnd = n => Math.floor(Math.random() * n);
const pick = a => a[rnd(a.length)];
const shuffle = a => { a = [...a]; for (let i = a.length - 1; i > 0; i--) { const j = rnd(i + 1); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const DAY = 864e5;
const dayKey = (d = new Date()) => { const x = new Date(d); return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`; };
const norm = s => String(s || "").toLowerCase().replace(/[’`]/g, "'").replace(/[^a-z0-9'Ѐ-ӿ\s-]/g, " ").replace(/\s+/g, " ").trim();
const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;

function lev(a, b) {
  a = a || ""; b = b || "";
  const m = a.length, n = b.length; if (!m) return n; if (!n) return m;
  let prev = Array.from({ length: n + 1 }, (_, i) => i);
  for (let i = 1; i <= m; i++) {
    const cur = [i];
    for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    prev = cur;
  }
  return prev[n];
}
const similarity = (a, b) => { a = norm(a); b = norm(b); const L = Math.max(a.length, b.length); return L ? 1 - lev(a, b) / L : 1; };

/* ================= holat ================= */
const KEY = "lugat.v1";
const DEFAULT_STATE = () => ({
  v: 1,
  words: [],
  customCats: [],
  profile: {
    name: "", level: "beginner", xp: 0, streak: 0, bestStreak: 0, lastGoalDay: null,
    goal: { new: 10, review: 20, speakMin: 5, listenMin: 5, writing: 5 },
    weeklyXp: 1000, theme: "auto", rate: 0.95, voice: "", apiKey: "", model: "claude-opus-5",
    seeded: false, onboarded: false,
  },
  days: {},
  skills: { writing: { c: 0, t: 0 }, speaking: { sum: 0, n: 0 }, listening: { c: 0, t: 0 }, vocab: { c: 0, t: 0 } },
  adapt: {},
  achievements: {},
  mistakes: [],
  records: { bestSpeed: 0, convos: 0, goalsDone: 0, imported: false },
  challenges: {},
});

let S = load();
function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const d = JSON.parse(raw), base = DEFAULT_STATE();
      return { ...base, ...d, profile: { ...base.profile, ...d.profile, goal: { ...base.profile.goal, ...(d.profile || {}).goal } },
        skills: { ...base.skills, ...d.skills }, records: { ...base.records, ...d.records } };
    }
  } catch (e) { console.warn(e); }
  return DEFAULT_STATE();
}
let saveTimer = null;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { toast("⚠️ Saqlab bo'lmadi: xotira to'lgan bo'lishi mumkin"); }
  }, 150);
}
window.addEventListener("beforeunload", () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} });

function today() {
  const k = dayKey();
  if (!S.days[k]) S.days[k] = { xp: 0, newW: 0, review: 0, speakSec: 0, listenSec: 0, writing: 0, correct: 0, total: 0, done: false, ch: false };
  return S.days[k];
}

/* ================= so'zlar ================= */
function newWord(o) {
  return {
    id: uid(), en: (o.en || "").trim(), uz: (o.uz || "").trim(), ex: (o.ex || "").trim(), pron: (o.pron || "").trim(),
    pos: o.pos || "", note: o.note || "", level: o.level || "beginner", cat: o.cat || "daily", fav: false, created: Date.now(),
    srs: { due: 0, ivl: 0, ease: 2.5, reps: 0, lapses: 0, last: 0, hist: [] },
  };
}
const wordById = id => S.words.find(w => w.id === id);
function allCats() { return [...CATEGORIES, ...S.customCats]; }
function catOf(id) { return allCats().find(c => c.id === id) || { id, name: id, icon: "🏷️" }; }

const isNew = w => w.srs.reps === 0 && w.srs.hist.length === 0;
const isLearned = w => w.srs.reps > 0;
const isMastered = w => w.srs.ivl >= 21;
const isDifficult = w => w.srs.lapses >= 2 || (w.srs.hist.length >= 2 && w.srs.ease < 2.0);
const isDue = (w, t = Date.now()) => !isNew(w) && w.srs.due <= t;
function stageOf(w) {
  if (isNew(w)) return { k: "new", uz: "Yangi", c: "var(--muted)" };
  if (isMastered(w)) return { k: "mastered", uz: "Yodlangan", c: "var(--ok)" };
  if (w.srs.ivl >= 4) return { k: "young", uz: "Mustahkamlanmoqda", c: "var(--accent)" };
  return { k: "learning", uz: "O'rganilmoqda", c: "var(--warn)" };
}

/* ================= takrorlash tizimi (SM-2 asosida) ================= */
// baho: 0 unutdim, 1 qiyin, 2 yaxshi, 3 oson
const GRADES = [
  { g: 0, e: "😵", t: "Unutdim" }, { g: 1, e: "😐", t: "Qiyin" }, { g: 2, e: "🙂", t: "Yaxshi" }, { g: 3, e: "😎", t: "Oson" },
];
function previewIvl(w, g) { return schedule({ ...w.srs, hist: [] }, g).ivl; }
function schedule(s, g) {
  s = { ...s };
  const wasNew = s.reps === 0;
  if (g === 0) {
    s.lapses++; s.reps = 0; s.ease = Math.max(1.3, s.ease - 0.2);
    s.ivl = 10 / 1440; // 10 daqiqa
  } else if (g === 1) {
    s.ease = Math.max(1.3, s.ease - 0.15);
    s.ivl = wasNew ? 1 : Math.max(1, s.ivl * 1.2);
    s.reps++;
  } else if (g === 2) {
    s.ivl = wasNew ? 3 : Math.max(s.ivl + 1, s.ivl * s.ease);
    s.reps++;
  } else {
    s.ease = Math.min(3.2, s.ease + 0.15);
    s.ivl = wasNew ? 5 : Math.max(s.ivl + 2, s.ivl * s.ease * 1.3);
    s.reps++;
  }
  // Ko'p unutilgan so'z tez-tez chiqadi
  if (g > 0 && s.lapses >= 3) s.ivl = Math.max(1, s.ivl * 0.6);
  s.ivl = Math.min(s.ivl, 365);
  return s;
}
function fmtIvl(d) {
  if (d < 1 / 24) return Math.round(d * 1440) + " daq";
  if (d < 1) return Math.round(d * 24) + " soat";
  if (d < 30) return Math.round(d) + " kun";
  if (d < 365) return Math.round(d / 30) + " oy";
  return "1 yil";
}
function rateWord(id, g) {
  const w = wordById(id); if (!w) return;
  const firstTime = isNew(w);
  // Muddati kelmagan so'zni qo'shimcha mashq qilish jadvalni surmaydi,
  // lekin unutilgan yoki qiyin bo'lsa jadval qisqaradi.
  if (!firstTime && w.srs.reps > 0 && w.srs.due > Date.now() && g >= 2) {
    w.srs.hist = [...w.srs.hist, { t: Date.now(), g, extra: true }].slice(-30);
    addXp(3); save(); return;
  }
  const s = schedule(w.srs, g);
  s.last = Date.now(); s.due = Date.now() + s.ivl * DAY;
  s.hist = [...w.srs.hist, { t: Date.now(), g }].slice(-30);
  w.srs = s;
  const d = today();
  if (firstTime) d.newW++; else d.review++;
  addXp(g === 0 ? 2 : 5 + g * 2);
  save(); checkGoal();
}

// Mashq uchun so'zlar navbati: muddati kelganlar (qiyinlari oldinda), keyin yangilar
function dueWords() {
  const t = Date.now();
  return S.words.filter(w => isDue(w, t)).sort((a, b) => (b.srs.lapses - a.srs.lapses) || (a.srs.due - b.srs.due));
}
function newWordsLeft() {
  const d = today();
  const left = Math.max(0, S.profile.goal.new - d.newW);
  const lv = LEVELS[S.profile.level].n;
  return S.words.filter(isNew).sort((a, b) => Math.abs(LEVELS[a.level].n - lv) - Math.abs(LEVELS[b.level].n - lv) || a.created - b.created).slice(0, left);
}
// O'yin/mashqlar uchun so'z tanlash: qiyin va muddati kelganlar ko'proq chiqadi
function weightedWords(n, pool = S.words) {
  const t = Date.now();
  const scored = pool.map(w => {
    let wt = 1;
    if (isDue(w, t)) wt += 3;
    if (isDifficult(w)) wt += 3;
    if (isNew(w)) wt += 0.5;
    if (isMastered(w)) wt *= 0.4;
    return { w, k: Math.random() * wt };
  });
  return scored.sort((a, b) => b.k - a.k).slice(0, n).map(x => x.w);
}

/* ================= XP, daraja, seriya ================= */
function levelInfo(xp = S.profile.xp) {
  let lvl = 1, need = 100, acc = 0;
  while (xp >= acc + need) { acc += need; lvl++; need = Math.round(need * 1.25); }
  return { lvl, into: xp - acc, need, name: LEVEL_NAMES[Math.min(lvl - 1, LEVEL_NAMES.length - 1)] };
}
function addXp(n, why) {
  if (!n) return;
  const before = levelInfo().lvl;
  S.profile.xp += n; today().xp += n;
  bumpXp(n, why);
  const after = levelInfo().lvl;
  if (after > before) setTimeout(() => celebrate(`🆙 ${after}-daraja!`, `Siz endi «${levelInfo().name}» darajasidasiz`), 400);
  save();
  checkAchievements();
}
function streakNow() {
  // Seriya: kunlik maqsad bajarilgan ketma-ket kunlar (bugun hali bajarilmagan bo'lsa kechagidan hisoblanadi)
  const last = S.profile.lastGoalDay;
  if (!last) return 0;
  const diff = Math.round((new Date(dayKey()) - new Date(last)) / DAY);
  return diff <= 1 ? S.profile.streak : 0;
}
function weekXp() {
  let sum = 0;
  for (let i = 0; i < 7; i++) sum += (S.days[dayKey(Date.now() - i * DAY)] || {}).xp || 0;
  return sum;
}

/* ================= kunlik reja ================= */
function planItems() {
  const d = today(), g = S.profile.goal;
  const unseen = S.words.filter(isNew).length + d.newW;
  const dueN = dueWords().length;
  const items = [
    { k: "new", icon: "🆕", t: "Yangi so'zlar", cur: d.newW, goal: Math.min(g.new, unseen), unit: "", go: "practice" },
    { k: "review", icon: "🔁", t: "Takrorlash", cur: d.review, goal: Math.min(g.review, d.review + dueN), unit: "", go: "practice" },
    { k: "speak", icon: "🎤", t: "Gapirish", cur: Math.floor(d.speakSec / 60), goal: g.speakMin, unit: " daq", go: "speaking" },
    { k: "listen", icon: "🎧", t: "Tinglash", cur: Math.floor(d.listenSec / 60), goal: g.listenMin, unit: " daq", go: "listening" },
    { k: "write", icon: "✍️", t: "Yozish mashqlari", cur: d.writing, goal: g.writing, unit: "", go: "writing" },
  ];
  items.forEach(i => { i.done = i.cur >= i.goal; i.pct = i.goal ? clamp(i.cur / i.goal, 0, 1) : 1; });
  return items;
}
function checkGoal() {
  const d = today();
  if (d.done) return;
  if (!S.words.length) return;
  if (planItems().every(i => i.done)) {
    d.done = true;
    const last = S.profile.lastGoalDay;
    const diff = last ? Math.round((new Date(dayKey()) - new Date(last)) / DAY) : 99;
    S.profile.streak = diff === 1 ? S.profile.streak + 1 : diff === 0 ? S.profile.streak : 1;
    S.profile.bestStreak = Math.max(S.profile.bestStreak, S.profile.streak);
    S.profile.lastGoalDay = dayKey();
    S.records.goalsDone++;
    save();
    setTimeout(() => { celebrate("🎉 Kunlik maqsad bajarildi!", `🔥 ${S.profile.streak} kunlik seriya · +50 XP`); addXp(50); }, 600);
  }
}
// Vaqtni hisoblash (gapirish / tinglash daqiqalari)
const timers = {};
function trackStart(kind) { timers[kind] = Date.now(); }
function trackStop(kind) {
  if (!timers[kind]) return;
  const sec = Math.min(300, (Date.now() - timers[kind]) / 1000);
  timers[kind] = 0;
  const d = today();
  if (kind === "speak") d.speakSec += sec; else d.listenSec += sec;
  save(); checkGoal();
}
function addTime(kind, sec) {
  const d = today();
  if (kind === "speak") d.speakSec += sec; else d.listenSec += sec;
  save(); checkGoal();
}

/* ================= ko'nikmalar va moslashuvchan qiyinlik ================= */
function recordSkill(kind, ok, score) {
  const sk = S.skills[kind];
  if (kind === "speaking") { sk.sum += score; sk.n++; }
  else { sk.t++; if (ok) sk.c++; }
  const d = today(); d.total++; if (ok) d.correct++;
  adaptPush(kind, kind === "speaking" ? score >= 70 : ok);
  save();
}
function skillPct(kind) {
  const sk = S.skills[kind];
  if (kind === "speaking") return sk.n ? Math.round(sk.sum / sk.n) : 0;
  return sk.t ? Math.round(sk.c / sk.t * 100) : 0;
}
function adaptLvl(kind) {
  if (!S.adapt[kind]) S.adapt[kind] = { lvl: LEVELS[S.profile.level].n, h: [] };
  return S.adapt[kind].lvl;
}
function adaptPush(kind, ok) {
  adaptLvl(kind);
  const a = S.adapt[kind];
  a.h.push(ok ? 1 : 0);
  if (a.h.length >= 8) {
    const acc = a.h.reduce((x, y) => x + y, 0) / a.h.length;
    if (acc >= 0.85 && a.lvl < 3) { a.lvl++; a.h = []; toast(`📈 Qiyinlik oshdi: ${["", "Beginner", "Intermediate", "Advanced"][a.lvl]}`); }
    else if (acc < 0.5 && a.lvl > 1) { a.lvl--; a.h = []; toast("📉 Qiyinlik biroz pasaytirildi — shoshilmang"); }
    else a.h = a.h.slice(-8);
  }
}

/* ================= xatolar va yutuqlar ================= */
function logMistake(type, wrong, right, note) {
  S.mistakes.unshift({ t: Date.now(), type, wrong, right, note });
  S.mistakes = S.mistakes.slice(0, 200);
  save();
}
function statsSnapshot() {
  const sk = S.skills;
  return {
    learned: S.words.filter(isLearned).length, mastered: S.words.filter(isMastered).length,
    streak: Math.max(streakNow(), S.profile.bestStreak), xp: S.profile.xp, goalsDone: S.records.goalsDone,
    sp: { n: sk.speaking.n, avg: skillPct("speaking") }, wr: { t: sk.writing.t, pct: skillPct("writing") },
    li: { t: sk.listening.t, pct: skillPct("listening") }, vo: { t: sk.vocab.t, pct: skillPct("vocab") },
    bestSpeed: S.records.bestSpeed, convos: S.records.convos, imported: S.records.imported,
  };
}
function checkAchievements() {
  const st = statsSnapshot();
  for (const a of ACHIEVEMENTS) {
    if (!S.achievements[a.id] && a.test(st)) {
      S.achievements[a.id] = Date.now();
      save();
      setTimeout(() => celebrate(`${a.icon} Yutuq: ${a.name}`, a.uz), 900);
    }
  }
}
function todayChallenge() {
  const n = Math.floor(new Date(dayKey()).getTime() / DAY);
  return DAILY_CHALLENGES[n % DAILY_CHALLENGES.length];
}
function progressChallenge(id, amount = 1, target = 1) {
  const ch = todayChallenge();
  if (ch.id !== id) return;
  const k = dayKey();
  S.challenges[k] = (S.challenges[k] || 0) + amount;
  if (!today().ch && S.challenges[k] >= target) {
    today().ch = true;
    setTimeout(() => { celebrate("🏅 Kunlik sinov bajarildi!", ch.t); addXp(ch.xp); }, 700);
  }
  save();
}
function challengeDone() { return !!today().ch; }

/* ================= ovoz: o'qib berish (TTS) ================= */
let VOICES = [];
function loadVoices() {
  if (!("speechSynthesis" in window)) return;
  VOICES = speechSynthesis.getVoices().filter(v => /^en(-|_|$)/i.test(v.lang));
}
if ("speechSynthesis" in window) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
function speak(text, opts = {}) {
  return new Promise(res => {
    if (!("speechSynthesis" in window)) { toast("🔇 Bu brauzerda ovozli o'qish yo'q"); res(); return; }
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "en-US";
    u.rate = opts.rate || S.profile.rate;
    const v = VOICES.find(v => v.name === S.profile.voice) || VOICES.find(v => /en-US/i.test(v.lang) && /Google|Samantha|Jenny|Aria|Natural/i.test(v.name)) || VOICES.find(v => /en-US/i.test(v.lang)) || VOICES[0];
    if (v) u.voice = v;
    u.onend = u.onerror = () => res();
    speechSynthesis.speak(u);
    setTimeout(res, 12000 + text.length * 120); // xavfsizlik uchun
  });
}

/* ================= ovoz: nutqni tanish ================= */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const hasSR = !!SR;
// Bitta gapni tinglaydi: {text, conf, sec, words}
function listenOnce({ onInterim, maxSec = 20 } = {}) {
  return new Promise((resolve, reject) => {
    if (!hasSR) { reject(new Error("nosr")); return; }
    const r = new SR();
    r.lang = "en-US"; r.interimResults = true; r.maxAlternatives = 1; r.continuous = true;
    let finalText = "", confs = [], start = Date.now(), firstAt = 0, lastAt = 0, done = false;
    const stopT = setTimeout(() => r.stop(), maxSec * 1000);
    let silence;
    r.onresult = e => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (!firstAt) firstAt = Date.now();
        lastAt = Date.now();
        if (res.isFinal) { finalText += res[0].transcript + " "; if (res[0].confidence) confs.push(res[0].confidence); }
        else interim += res[0].transcript;
      }
      onInterim && onInterim((finalText + interim).trim());
      clearTimeout(silence);
      silence = setTimeout(() => r.stop(), 2200);
    };
    r.onerror = e => { if (!done) { done = true; clearTimeout(stopT); reject(new Error(e.error || "error")); } };
    r.onend = () => {
      clearTimeout(stopT); clearTimeout(silence);
      if (done) return; done = true;
      const text = finalText.trim();
      const conf = confs.length ? confs.reduce((a, b) => a + b, 0) / confs.length : 0;
      resolve({ text, conf, sec: Math.max(0.5, ((lastAt || Date.now()) - (firstAt || start)) / 1000), total: (Date.now() - start) / 1000 });
    };
    try { r.start(); } catch (e) { reject(e); }
    listenOnce.current = r;
  });
}
function stopListening() { try { listenOnce.current && listenOnce.current.stop(); } catch (e) {} }

/* ================= so'z shakllari ================= */
const IRREG = {
  be: ["am", "is", "are", "was", "were", "been", "being"], go: ["goes", "went", "gone"], do: ["does", "did", "done"],
  have: ["has", "had"], make: ["made"], take: ["took", "taken"], see: ["saw", "seen"], come: ["came"], get: ["got", "gotten"],
  give: ["gave", "given"], know: ["knew", "known"], think: ["thought"], buy: ["bought"], bring: ["brought"], eat: ["ate", "eaten"],
  drink: ["drank", "drunk"], write: ["wrote", "written"], read: ["read"], speak: ["spoke", "spoken"], forget: ["forgot", "forgotten"],
  begin: ["began", "begun"], find: ["found"], feel: ["felt"], leave: ["left"], meet: ["met"], pay: ["paid"], say: ["said"],
  tell: ["told"], sell: ["sold"], send: ["sent"], spend: ["spent"], teach: ["taught"], catch: ["caught"], sleep: ["slept"],
  keep: ["kept"], lose: ["lost"], win: ["won"], run: ["ran"], swim: ["swam", "swum"], fly: ["flew", "flown"], drive: ["drove", "driven"],
  ride: ["rode", "ridden"], choose: ["chose", "chosen"], break: ["broke", "broken"], wake: ["woke", "woken"], wear: ["wore", "worn"],
  understand: ["understood"], stand: ["stood"], sit: ["sat"], put: [], cut: [], let: [], hit: [], cost: [], hurt: [], set: [],
  build: ["built"], learn: ["learnt", "learned"], hear: ["heard"], hold: ["held"], lend: ["lent"], borrow: [], grow: ["grew", "grown"],
  draw: ["drew", "drawn"], fall: ["fell", "fallen"], become: ["became"], show: ["showed", "shown"], sing: ["sang", "sung"],
};
const PAST = {};
for (const [b, f] of Object.entries(IRREG)) if (f.length) PAST[b] = b === "be" ? "was" : b === "have" ? "had" : b === "do" ? "did" : b === "go" ? "went" : f.find(x => !x.endsWith("s") || b === "read") || f[0];
Object.assign(PAST, { make: "made", take: "took", see: "saw", come: "came", get: "got", give: "gave", eat: "ate", write: "wrote", speak: "spoke", forget: "forgot", buy: "bought" });
const PAST_SET = new Set(Object.values(PAST).concat(Object.values(IRREG).flat().filter(x => !/s$/.test(x))));
function thirdPerson(v) {
  if (v === "have") return "has"; if (v === "be") return "is";
  if (/(s|sh|ch|x|z|o)$/.test(v)) return v + "es";
  if (/[^aeiou]y$/.test(v)) return v.slice(0, -1) + "ies";
  return v + "s";
}
function pastOf(v) {
  if (PAST[v]) return PAST[v];
  if (/e$/.test(v)) return v + "d";
  if (/[^aeiou]y$/.test(v)) return v.slice(0, -1) + "ied";
  if (/^[^aeiou]*[aeiou][^aeiouwxy]$/.test(v)) return v + v.slice(-1) + "ed";
  return v + "ed";
}
function wordForms(en) {
  const w = norm(en);
  const set = new Set([w]);
  if (w.includes(" ")) return [...set];
  set.add(w + "s"); set.add(w + "es"); set.add(w + "ed"); set.add(w + "d"); set.add(w + "ing"); set.add(w + "er"); set.add(w + "ly");
  set.add(thirdPerson(w)); set.add(pastOf(w));
  if (/e$/.test(w)) { set.add(w.slice(0, -1) + "ing"); set.add(w.slice(0, -1) + "ion"); }
  if (/[^aeiou]y$/.test(w)) { set.add(w.slice(0, -1) + "ies"); set.add(w.slice(0, -1) + "ied"); set.add(w.slice(0, -1) + "ily"); }
  if (/^[^aeiou]*[aeiou][^aeiouwxy]$/.test(w)) { set.add(w + w.slice(-1) + "ing"); set.add(w + w.slice(-1) + "ed"); }
  set.add(w + "ment");
  (IRREG[w] || []).forEach(f => set.add(f));
  return [...set];
}
function usesWord(sentence, en) {
  const s = " " + norm(sentence) + " ";
  const w = norm(en);
  if (w.includes(" ")) return s.includes(" " + w + " ") || s.includes(" " + w.split(" ")[0] + " ");
  return wordForms(en).some(f => s.includes(" " + f + " "));
}
// Gapdagi so'zni (istalgan shaklini) topib, blank qo'yish
function findWordInSentence(sentence, en) {
  const forms = wordForms(en).sort((a, b) => b.length - a.length);
  for (const f of forms) {
    const re = new RegExp(`\\b${f.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    const m = sentence.match(re);
    if (m) return { index: m.index, match: m[0] };
  }
  return null;
}
function cloze(w) {
  const ex = w.ex || "";
  const f = ex && findWordInSentence(ex, w.en);
  if (!f) return null;
  return { before: ex.slice(0, f.index), after: ex.slice(f.index + f.match.length), answer: f.match };
}

/* ================= grammatika tekshiruvi (oflayn) ================= */
const VERBS_BASE = ["go", "do", "have", "want", "like", "work", "live", "play", "need", "make", "eat", "study", "watch", "know", "think", "love", "speak", "read", "write", "come", "get", "take", "see", "buy", "drink", "teach", "learn", "try", "say", "help", "use", "visit", "cook", "wake", "sleep", "run", "improve"];
const NO_S_AFTER = /\b(did|does|do|will|would|can|could|should|must|may|might|to|let|make|help|don't|doesn't|didn't|won't|can't)\s+$/i;
const VOWEL_EXC_A = /^(uni|use|usu|euro|one|once|u[bcfgklmnprst]i)/; // "a university"
const VOWEL_EXC_AN = /^(hour|honest|honou?r|heir)/;
const UNCOUNT = { informations: "information", advices: "advice", homeworks: "homework", furnitures: "furniture", knowledges: "knowledge", equipments: "equipment", luggages: "luggage", baggages: "baggage", researches: "research", feedbacks: "feedback" };

const APOS = { dont: "don't", doesnt: "doesn't", didnt: "didn't", cant: "can't", wont: "won't", isnt: "isn't", arent: "aren't", wasnt: "wasn't", im: "I'm", ive: "I've", youre: "you're", theyre: "they're", shouldnt: "shouldn't", couldnt: "couldn't", havent: "haven't" };
const PROPER = /\b(english|uzbek|russian|german|french|turkish|korean|chinese|arabic|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|april|june|july|august|september|october|november|december|tashkent|samarkand|bukhara|uzbekistan|london|america)\b/g;
const GRAMMAR_RULES = [
  { re: /\b(dont|doesnt|didnt|cant|wont|isnt|arent|wasnt|im|ive|youre|theyre|shouldnt|couldnt|havent)\b/gi, fix: m => APOS[m.toLowerCase()], why: "Qisqartmada apostrof (') kerak: don't, can't, I'm." },
  { re: /\bi\b/g, fix: () => "I", why: "«I» (men) har doim katta harf bilan yoziladi." },
  { re: PROPER, fix: m => cap(m), why: "Tillar, kunlar, oylar va joy nomlari katta harf bilan yoziladi." },
  { re: /\b(go|went|going|goes)\s+to\s+(shopping|swimming|fishing|skiing|jogging|camping|hiking)\b/gi, fix: (m, a, b) => `${a} ${b}`, why: "«go shopping» — «to» kerak emas." },
  { re: /\b(go|went|going|goes|come|came|coming|get|got)\s+to\s+home\b/gi, fix: (m, a) => `${a} home`, why: "«go home» — «home» oldidan «to» qo'yilmaydi." },
  { re: /\bI\s+(is|are)\b/g, fix: () => "I am", why: "«I» bilan «am» ishlatiladi: I am." },
  { re: /\b(he|she|it)\s+(are|am)\b/gi, fix: (m, a) => `${a} is`, why: "He/She/It bilan «is» ishlatiladi." },
  { re: /\b(you|we|they)\s+(is|am)\b/gi, fix: (m, a) => `${a} are`, why: "You/We/They bilan «are» ishlatiladi." },
  { re: /\b(people|children|men|women)\s+is\b/gi, fix: (m, a) => `${a} are`, why: `Bu so'z ko'plikda — «are» kerak.` },
  { re: /\b(he|she|it)\s+don't\b/gi, fix: (m, a) => `${a} doesn't`, why: "He/She/It bilan «doesn't» ishlatiladi." },
  { re: /\b(I|you|we|they)\s+doesn't\b/gi, fix: (m, a) => `${a} don't`, why: "I/You/We/They bilan «don't» ishlatiladi." },
  { re: /\b(I|you|we|they)\s+has\b/gi, fix: (m, a) => `${a} have`, why: "I/You/We/They bilan «have» ishlatiladi." },
  { re: /\b(am|is|are)\s+agree\b/gi, fix: () => "agree", why: "«agree» fe'l — «I agree» deyiladi, «am» kerak emas." },
  { re: /\bmore\s+(better|worse|easier|bigger|smaller|faster|cheaper|happier|older|younger)\b/gi, fix: (m, a) => a, why: "Qiyosiy daraja allaqachon «-er» bilan — «more» ortiqcha." },
  { re: /\b(did not|didn't|did)\s+(\w+)\b/gi, test: (m, a, b) => PAST_SET.has(b.toLowerCase()) && !["read", "put", "cut", "let", "hit", "cost", "hurt", "set"].includes(b.toLowerCase()), fix: (m, a, b) => `${a} ${Object.keys(PAST).find(k => PAST[k] === b.toLowerCase()) || Object.keys(IRREG).find(k => IRREG[k].includes(b.toLowerCase())) || b}`, why: "«did/didn't» dan keyin fe'lning 1-shakli keladi (didn't go, not didn't went)." },
  { re: /\b(can|must|should|will|could|would|may|might)\s+to\s+(\w+)/gi, fix: (m, a, b) => `${a} ${b}`, why: "Modal fe'llardan (can, must, should...) keyin «to» qo'yilmaydi." },
  { re: /\b(want|wants|wanted|need|needs|needed|would like|decide|decided|plan|planned|hope|hoped)\s+(go|buy|eat|see|learn|do|make|have|get|visit|play|study|work|improve|become|travel|speak|try|find|start|be)\b/gi, fix: (m, a, b) => `${a} to ${b}`, why: "«want/need/decide» dan keyin «to + fe'l» keladi: want to go." },
  { re: /\bI\s+have\s+(\d{1,2})\s+years(\s+old)?\b/gi, fix: (m, a) => `I am ${a} years old`, why: "Yosh «be» bilan aytiladi: I am 20 years old." },
  { re: /\bexplain\s+(me|him|her|us|them)\b/gi, fix: (m, a) => `explain to ${a}`, why: "«explain to me» — «to» kerak." },
  { re: /\bdiscuss\s+about\b/gi, fix: () => "discuss", why: "«discuss» dan keyin «about» qo'yilmaydi." },
  { re: /\bmarried\s+with\b/gi, fix: () => "married to", why: "«married to someone» deyiladi." },
  { re: /\blisten\s+(music|the music|to me|me|him|her|them|the radio|radio)\b/gi, test: (m, a) => !/^to\b/i.test(a), fix: (m, a) => `listen to ${a}`, why: "«listen to something» — «to» kerak." },
  { re: /\bsince\s+(\d+|two|three|four|five|six|ten|many)\s+(years|months|weeks|days|hours)\b/gi, fix: (m, a, b) => `for ${a} ${b}`, why: "Davomiylik uchun «for» ishlatiladi (for 3 years), «since» — boshlanish nuqtasi uchun." },
  { re: /\bvery\s+(like|love|enjoy|want)\b/gi, fix: (m, a) => `really ${a}`, why: "«very» fe'l bilan ishlatilmaydi: I really like..." },
  { re: /\b(\w+)\s+\1\b/gi, test: (m, a) => !["that", "had", "very", "bye", "so"].includes(a.toLowerCase()), fix: (m, a) => a, why: "So'z ikki marta takrorlangan." },
  { re: /\b(informations|advices|homeworks|furnitures|knowledges|equipments|luggages|baggages|researches|feedbacks)\b/gi, fix: m => UNCOUNT[m.toLowerCase()], why: "Bu so'z sanalmaydi — ko'plik «-s» qo'shilmaydi." },
  { re: /\bmuch\s+(people|friends|books|cars|students|things|words|times|problems|questions)\b/gi, fix: (m, a) => `many ${a}`, why: "Sanaladigan ko'plik bilan «many» ishlatiladi." },
  { re: /\ba\s+([aeiou]\w*)/gi, test: (m, a) => !VOWEL_EXC_A.test(a.toLowerCase()), fix: (m, a) => (m[0] === "A" ? "An " : "an ") + a, why: "Unli tovush bilan boshlangan so'z oldidan «an» qo'yiladi." },
  { re: /\ban\s+([a-z]\w*)/gi, test: (m, a) => (/^[b-df-hj-np-tv-z]/i.test(a) && !VOWEL_EXC_AN.test(a.toLowerCase())) || VOWEL_EXC_A.test(a.toLowerCase()), fix: (m, a) => (m[0] === "A" ? "A " : "a ") + a, why: "Undosh tovush oldidan «a» qo'yiladi." },
  { re: /\b(he|she|it|my \w+|his \w+|her \w+)\s+(go|do|have|want|like|work|live|play|need|eat|study|watch|know|love|speak|read|write|come|get|take|drink|teach|learn|try|say|use|visit|cook|wake|sleep)\b/gi,
    test: (m, a, b, off, str) => !(/^(my|his|her)\s/i.test(a) && /s$/i.test(a)) && !NO_S_AFTER.test(str.slice(0, off)) && !/\b(did|does|will|can|could|should|would|must|might|may|let|make|help|to)\s+$/i.test(str.slice(0, off)),
    fix: (m, a, b) => `${a} ${thirdPerson(b.toLowerCase())}`, why: "He/She/It bilan hozirgi zamonda fe'lga «-s» qo'shiladi: she works." },
];
const PAST_MARKERS = /\b(yesterday|was|were|last (night|week|month|year|weekend|summer|sunday|monday|friday|saturday)|ago|in 20[01]\d)\b/i;

function grammarCheck(text) {
  let fixed = String(text || "").trim();
  const issues = [];
  if (!fixed) return { fixed, issues };
  for (const r of GRAMMAR_RULES) {
    fixed = fixed.replace(r.re, (...args) => {
      const m = args[0];
      if (r.test && !r.test(...args)) return m;
      const out = r.fix(...args);
      if (out !== m) issues.push({ wrong: m, right: out, why: r.why });
      return out;
    });
  }
  // o'tgan zamon belgisi bor, lekin fe'l hozirgi zamonda
  if (PAST_MARKERS.test(fixed)) {
    fixed = fixed.replace(/\b(I|you|we|they|he|she|it|my \w+)\s+(go|goes|eat|eats|see|sees|buy|buys|do|does|have|has|come|comes|make|makes|take|takes|visit|visits|play|plays|watch|watches|meet|meets|get|gets|drink|drinks|write|writes|read|reads|work|works|cook|cooks|study|studies)\b/gi, (m, a, b, off, str) => {
      if (/\b(will|to|can|did|didn't|don't|doesn't)\s+$/i.test(str.slice(0, off))) return m;
      const base = b.toLowerCase().replace(/ies$/, "y").replace(/(ch|sh|s|x|o)es$/, "$1").replace(/(?<!s)s$/, "");
      const past = pastOf(base === "ha" ? "have" : base === "doe" ? "do" : base);
      const out = `${a} ${past}`;
      if (out.toLowerCase() !== m.toLowerCase()) issues.push({ wrong: m, right: out, why: "Gapda o'tgan zamon belgisi bor (yesterday, last..., ago) — fe'l o'tgan zamonda bo'lishi kerak." });
      return out;
    });
  }
  // bosh harf va tinish belgisi
  if (/^[a-z]/.test(fixed)) { issues.push({ wrong: fixed.split(" ")[0], right: cap(fixed.split(" ")[0]), why: "Gap katta harf bilan boshlanadi.", minor: true }); fixed = cap(fixed); }
  if (!/[.!?]$/.test(fixed)) {
    const isQ = /^(what|where|when|why|who|how|do|does|did|is|are|can|could|would|will|have|has|should)\b/i.test(fixed);
    fixed += isQ ? "?" : ".";
    issues.push({ wrong: "", right: isQ ? "?" : ".", why: "Gap oxirida tinish belgisi bo'lishi kerak.", minor: true });
  }
  return { fixed, issues };
}

// Yozilgan/aytilgan gapni tahlil qilish
function analyzeSentence(text, targetEn, { spoken = false } = {}) {
  const raw = String(text || "").trim();
  const words = norm(raw).split(" ").filter(Boolean);
  const { fixed, issues } = grammarCheck(raw);
  const real = issues.filter(i => !(spoken && i.minor));
  const used = targetEn ? usesWord(raw, targetEn) : true;
  const uniq = new Set(words).size;
  const hasVerb = words.some(w => /^(am|is|are|was|were|be|been|have|has|had|do|does|did|can|will|would|should|could|must|may|might)$/.test(w) || VERBS_BASE.includes(w) || VERBS_BASE.some(v => w === thirdPerson(v) || w === pastOf(v)) || /(ed|ing)$/.test(w));
  const grammar = clamp(100 - real.filter(i => !i.minor).length * 22 - real.filter(i => i.minor).length * 6, 0, 100);
  const vocab = clamp((used ? 70 : 25) + Math.min(30, (uniq - 3) * 4), 0, 100);
  let structure = 40;
  if (words.length >= 4) structure += 25;
  if (words.length >= 7) structure += 15;
  if (hasVerb) structure += 20;
  if (words.length > 30) structure -= 10;
  structure = clamp(structure, 0, 100);
  const feedback = [];
  if (words.length < 3) feedback.push({ k: "bad", t: "Gap juda qisqa. Kamida 4–5 so'zli to'liq gap tuzing." });
  else if (!real.filter(i => !i.minor).length) feedback.push({ k: "ok", t: pick(["Good sentence! 👏", "Great job! 🌟", "Nice and clear! ✅"]) });
  if (targetEn) feedback.push(used ? { k: "ok", t: `You used the word «${targetEn}» correctly. ✅` } : { k: "bad", t: `«${targetEn}» so'zi gapda yo'q. Uni albatta ishlating.` });
  if (!hasVerb && words.length >= 3) feedback.push({ k: "warn", t: "Gapda fe'l ko'rinmayapti. Ingliz gapida ega + fe'l bo'lishi kerak." });
  for (const i of real) feedback.push({ k: i.minor ? "warn" : "bad", t: i.why + (i.wrong ? ` «${i.wrong}» → «${i.right}»` : "") });
  if (fixed !== raw && real.some(i => !i.minor)) feedback.push({ k: "tip", t: `Try saying: «${fixed}»` });
  return { raw, fixed, issues: real, used, grammar, vocab, structure, words: words.length, feedback };
}

/* ================= import tahlili ================= */
function parseImport(text) {
  const lines = String(text || "").split(/\r?\n/).map(l => l.trim()).filter(Boolean);
  const out = [];
  let hdr = null;
  for (const line of lines) {
    let parts;
    if (line.includes("|")) parts = line.split("|");
    else if (line.includes("\t")) parts = line.split("\t");
    else if (line.includes(";")) parts = line.split(";");
    else if (/\s[-–—=:]\s/.test(line)) parts = line.split(/\s[-–—=:]\s/);
    else if (line.includes(",")) parts = splitCsv(line);
    else parts = [line];
    parts = parts.map(p => p.trim().replace(/^"|"$/g, ""));
    const low = parts.map(p => p.toLowerCase());
    if (!hdr && (low[0] === "english" || low[0] === "en" || low[0] === "word") ) {
      hdr = low.map(h => ({ english: "en", en: "en", word: "en", uzbek: "uz", uz: "uz", translation: "uz", example: "ex", sentence: "ex", pronunciation: "pron", pron: "pron", "part of speech": "pos", pos: "pos", category: "cat", level: "level", difficulty: "level", note: "note" }[h] || null));
      continue;
    }
    const def = ["en", "uz", "ex", "pos", "pron", "cat", "level", "note"];
    const map = hdr || def;
    const o = {};
    parts.forEach((p, i) => { const k = i < map.length ? map[i] : def[i]; if (k && p && !o[k]) o[k] = p; });
    if (!o.en) continue;
    out.push(o);
  }
  return out;
}
function splitCsv(line) {
  const res = []; let cur = "", q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === "," && !q) { res.push(cur); cur = ""; }
    else cur += ch;
  }
  res.push(cur);
  return res;
}
function normCatId(v) {
  if (!v) return null;
  const low = v.toLowerCase().trim();
  const c = allCats().find(c => c.id === low || c.name.toLowerCase() === low);
  if (c) return c.id;
  const id = "c_" + low.replace(/[^a-z0-9]+/g, "_");
  S.customCats.push({ id, name: cap(v.trim()), icon: "🏷️" });
  return id;
}
function normLevel(v) {
  const l = String(v || "").toLowerCase();
  if (/adv|hard|yuqori|qiyin|c1|c2|b2/.test(l)) return "advanced";
  if (/int|med|o'rta|b1|a2/.test(l)) return "intermediate";
  if (/beg|easy|oson|a1|boshl/.test(l)) return "beginner";
  return null;
}
// So'z qiyinligini taxmin qilish (uzunlik bo'yicha)
function guessLevel(en) { const n = en.replace(/\s/g, "").length; return n <= 5 ? "beginner" : n <= 8 ? "intermediate" : "advanced"; }

/* ================= Lug'at API (ixtiyoriy) ================= */
async function dictLookup(en) {
  const r = await fetch("https://api.dictionaryapi.dev/api/v2/entries/en/" + encodeURIComponent(en.trim().toLowerCase()));
  if (!r.ok) throw new Error("topilmadi");
  const j = await r.json();
  const e = j[0] || {};
  const pron = e.phonetic || (e.phonetics || []).map(p => p.text).find(Boolean) || "";
  let pos = "", ex = "", def = "";
  for (const m of e.meanings || []) {
    for (const d of m.definitions || []) {
      if (!def) { def = d.definition; pos = m.partOfSpeech; }
      if (!ex && d.example) { ex = d.example; if (!pos) pos = m.partOfSpeech; }
    }
  }
  return { pron, pos, ex: ex ? cap(ex.replace(/\s*$/, "")) + (/[.!?]$/.test(ex) ? "" : ".") : "", def };
}

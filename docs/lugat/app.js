// Interfeys: yo'naltirish, sahifalar, mashq dvigateli.
"use strict";

/* ================= umumiy UI ================= */
let ACT = {};          // joriy sahifa amallari (data-act)
let CLEAN = [];        // sahifadan chiqishda tozalash
let KEYH = null;       // joriy klaviatura ishlovchisi
const V = () => $("#view");
const onLeave = fn => CLEAN.push(fn);

function toast(msg, ms = 2400) {
  const t = document.createElement("div");
  t.className = "toast"; t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(() => t.remove(), ms);
}
function bumpXp(n) {
  const chip = $("#xpchip");
  const r = chip ? chip.getBoundingClientRect() : { left: innerWidth - 90, top: 20 };
  const f = document.createElement("div");
  f.className = "xpfly"; f.textContent = `+${n} XP`;
  f.style.left = (r.left + 10) + "px"; f.style.top = (r.top + 30) + "px";
  document.body.appendChild(f);
  setTimeout(() => f.remove(), 1200);
  refreshChips();
}
const celebQ = [];
function celebrate(title, sub) {
  celebQ.push([title, sub]);
  if (celebQ.length === 1) showCeleb();
}
function showCeleb() {
  const [title, sub] = celebQ[0];
  const el = document.createElement("div");
  el.className = "celebrate";
  el.innerHTML = `<div class="box"><div style="font-size:3.4rem">${esc(title.split(" ")[0])}</div><h2>${esc(title.split(" ").slice(1).join(" "))}</h2><p class="muted">${esc(sub || "")}</p><button class="btn grad big mt">Davom etish</button></div>`;
  document.body.appendChild(el);
  confetti();
  const close = () => { el.remove(); celebQ.shift(); if (celebQ.length) setTimeout(showCeleb, 200); };
  el.querySelector("button").onclick = close;
  el.onclick = e => { if (e.target === el) close(); };
}
function confetti(n = 70) {
  const cols = ["#6d5dfc", "#ff7ab6", "#ffc53d", "#1fb57a", "#3fb6ff", "#9b5cff"];
  for (let i = 0; i < n; i++) {
    const c = document.createElement("i");
    c.className = "confetti";
    c.style.left = Math.random() * 100 + "vw";
    c.style.background = pick(cols);
    c.style.animationDuration = 1.8 + Math.random() * 1.8 + "s";
    c.style.animationDelay = Math.random() * 0.4 + "s";
    document.body.appendChild(c);
    setTimeout(() => c.remove(), 4200);
  }
}
function modal(html, { onClose } = {}) {
  const m = document.createElement("div");
  m.className = "modal";
  m.innerHTML = `<div class="sheet">${html}</div>`;
  document.body.appendChild(m);
  const close = () => { m.remove(); onClose && onClose(); };
  m.addEventListener("click", e => { if (e.target === m || e.target.closest("[data-close]")) close(); });
  m.close = close;
  return m;
}
function confirmDlg(text, yes = "Ha", danger = true) {
  return new Promise(res => {
    const m = modal(`<h2>${esc(text)}</h2><div class="row mt2"><button class="btn ${danger ? "err" : ""}" data-y>${esc(yes)}</button><button class="btn ghost" data-close>Bekor qilish</button></div>`, { onClose: () => res(false) });
    m.querySelector("[data-y]").onclick = () => { m.remove(); res(true); };
  });
}
function applyTheme() {
  const t = S.profile.theme;
  if (t === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
}
function ring(p, label, c) { return `<div class="ring" style="--p:${p};${c ? `--c:${c}` : ""}"><b>${label}</b></div>`; }
function bar(p, cls = "") { return `<div class="bar ${cls}"><i style="width:${clamp(p, 0, 100)}%"></i></div>`; }
function speakBtn(text, cls = "iconbtn") { return `<button class="${cls}" data-say="${esc(text)}" title="Tinglash">🔊</button>`; }

document.addEventListener("click", e => {
  const s = e.target.closest("[data-say]");
  if (s) { e.stopPropagation(); speak(s.dataset.say); return; }
  const ln = e.target.closest('a[href^="#/"]');
  if (ln && ln.getAttribute("href") === location.hash) { e.preventDefault(); render(); return; }
  const g = e.target.closest("[data-go]");
  if (g) { e.preventDefault(); go(g.dataset.go); return; }
  const a = e.target.closest("[data-act]");
  if (a && ACT[a.dataset.act]) { ACT[a.dataset.act](a, e); }
});
document.addEventListener("keydown", e => { if (KEYH && !e.defaultPrevented) KEYH(e); });

/* ================= navigatsiya ================= */
const NAV = [
  { r: "home", i: "🏠", t: "Bosh sahifa" }, { r: "vocab", i: "📚", t: "Lug'atim" }, { r: "practice", i: "🧠", t: "Takrorlash" },
  { r: "writing", i: "✍️", t: "Yozish" }, { r: "speaking", i: "🎤", t: "Gapirish" }, { r: "listening", i: "🎧", t: "Tinglash" },
  { r: "games", i: "🎮", t: "O'yinlar" }, { r: "teacher", i: "🤖", t: "AI Ustoz" }, { r: "talk", i: "💬", t: "Suhbat" },
  { r: "progress", i: "📊", t: "Natijalar" }, { r: "settings", i: "⚙️", t: "Sozlamalar" },
];
const VIEWS = {};
function route() {
  const h = location.hash.replace(/^#\/?/, "");
  const [r, q] = h.split("?");
  return { r: VIEWS[r] ? r : "home", p: new URLSearchParams(q || "") };
}
function go(r) { if (location.hash === "#/" + r) render(); else location.hash = "#/" + r; }
window.addEventListener("hashchange", render);

function render() {
  CLEAN.forEach(f => { try { f(); } catch (e) {} }); CLEAN = [];
  ACT = {}; KEYH = null;
  if ("speechSynthesis" in window) speechSynthesis.cancel();
  stopListening();
  $$(".modal").forEach(m => m.remove());
  const { r, p } = route();
  renderNav(r);
  V().innerHTML = "";
  VIEWS[r](V(), p);
  window.scrollTo(0, 0);
}
function renderNav(r) {
  const due = dueWords().length;
  $("#side").innerHTML = `
    <div class="brand"><div class="logo">A</div><div><b>Lug'at</b><div class="tiny muted">English vocabulary</div></div></div>
    <nav class="nav">${NAV.map(n => `<a href="#/${n.r}" class="${n.r === r ? "on" : ""}"><span class="ic">${n.i}</span>${n.t}${n.r === "practice" && due ? `<span class="badge tag err">${due}</span>` : ""}</a>`).join("")}</nav>
    ${sideMini()}`;
  const bottom = ["home", "vocab", "practice", "games"];
  $("#bottom").innerHTML = bottom.map(k => { const n = NAV.find(x => x.r === k); return `<a href="#/${k}" class="${k === r ? "on" : ""}"><span class="ic">${n.i}</span>${n.t}</a>`; }).join("")
    + `<a href="#" class="${bottom.includes(r) ? "" : "on"}" id="morebtn"><span class="ic">☰</span>Ko'proq</a>`;
  $("#morebtn").onclick = e => {
    e.preventDefault();
    const m = modal(`<h2>Bo'limlar</h2><div class="grid g3 mt">${NAV.map(n => `<a class="tile" href="#/${n.r}" style="text-decoration:none;color:inherit;align-items:center;text-align:center"><span class="big">${n.i}</span><b>${n.t}</b></a>`).join("")}</div>`);
    m.querySelectorAll("a").forEach(a => a.addEventListener("click", () => m.remove()));
  };
}
function sideMini() {
  const L = levelInfo();
  return `<div class="mini"><div class="row between"><b>⭐ ${L.lvl}-daraja</b><span class="small">${L.name}</span></div>
    <div class="small" style="margin:6px 0">${L.into} / ${L.need} XP</div>${bar(L.into / L.need * 100)}</div>`;
}
function refreshChips() {
  const x = $("#xpchip"); if (x) x.textContent = `⭐ ${S.profile.xp} XP`;
  const f = $("#firechip"); if (f) f.textContent = `🔥 ${streakNow()}`;
  const m = $("#side .mini"); if (m) m.outerHTML = sideMini();
}
function topbar(title, sub = "") {
  return `<div class="topbar"><h1>${title}${sub ? `<div class="small muted" style="font-weight:600;margin-top:4px">${sub}</div>` : ""}</h1>
    <div class="chips"><span class="chip fire" id="firechip">🔥 ${streakNow()}</span><span class="chip xp" id="xpchip">⭐ ${S.profile.xp} XP</span>
    <button class="chip hide-sm" data-act="theme" style="cursor:pointer" title="Mavzu">${document.documentElement.getAttribute("data-theme") === "dark" || (S.profile.theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches) ? "🌙" : "☀️"}</button></div></div>`;
}
function themeAct() {
  ACT.theme = () => {
    const dark = document.documentElement.getAttribute("data-theme") === "dark" || (S.profile.theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
    S.profile.theme = dark ? "light" : "dark"; save(); applyTheme(); render();
  };
}

/* ================= mashq dvigateli ================= */
const canCloze = w => !!cloze(w);
function distractors(w, field, n = 3, pool) {
  pool = (pool || S.words).filter(x => x.id !== w.id && x[field] && norm(x[field]) !== norm(w[field]));
  if (pool.length < n) pool = pool.concat(SEED.filter(x => norm(x[field]) !== norm(w[field]) && !pool.some(p => norm(p[field]) === norm(x[field]))));
  const same = shuffle(pool.filter(x => x.pos && x.pos === w.pos)), other = shuffle(pool.filter(x => !x.pos || x.pos !== w.pos));
  const out = [];
  for (const x of [...same, ...other]) { if (out.length >= n) break; if (!out.some(o => norm(o[field]) === norm(x[field]))) out.push(x); }
  return out;
}
// Gapdagi shaklga moslab chalg'ituvchi so'zlarni o'zgartirish (improved → forgot, closed...)
function inflectLike(answer, base, other) {
  const a = answer.toLowerCase(), b = base.toLowerCase(), o = other.en.toLowerCase();
  if (a === b || o.includes(" ")) return other.en;
  if (other.pos !== "verb" && other.pos !== "noun") return other.en;
  if (a === pastOf(b)) return other.pos === "verb" ? pastOf(o) : other.en;
  if (a === thirdPerson(b)) return thirdPerson(o);
  if (a.endsWith("ing")) return other.pos === "verb" ? (/e$/.test(o) && !/ee$/.test(o) ? o.slice(0, -1) : o) + "ing" : other.en;
  return other.en;
}
const uzVariants = uz => String(uz).toLowerCase().replace(/\(.*?\)/g, "").split(/[,;/]| yoki /).map(s => norm(s)).filter(Boolean);
function gradeEn(input, answer) {
  const a = norm(input), b = norm(answer);
  if (!a) return { ok: false, empty: true };
  if (a === b) return { ok: true };
  const d = lev(a, b);
  if (d === 1 && b.length >= 4) return { ok: true, typo: true };
  return { ok: false, d };
}
function gradeUz(input, uz) {
  const a = norm(input);
  if (!a) return { ok: false, empty: true };
  const vs = uzVariants(uz).concat([norm(uz)]);
  let best = 0;
  for (const v of vs) { best = Math.max(best, similarity(a, v)); if (v.includes(a) && a.length >= 4) best = Math.max(best, 0.9); }
  return { ok: best >= 0.78, typo: best < 1 && best >= 0.78, best };
}
function charDiff(user, right) {
  // LCS asosida harf farqi
  const a = [...user], b = [...right], m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) for (let j = n - 1; j >= 0; j--) dp[i][j] = a[i].toLowerCase() === b[j].toLowerCase() ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  let i = 0, j = 0, out = "";
  while (i < m && j < n) {
    if (a[i].toLowerCase() === b[j].toLowerCase()) { out += esc(b[j]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out += `<del>${esc(a[i])}</del>`; i++; }
    else { out += `<ins>${esc(b[j])}</ins>`; j++; }
  }
  while (i < m) out += `<del>${esc(a[i++])}</del>`;
  while (j < n) out += `<ins>${esc(b[j++])}</ins>`;
  return out;
}
function wordDiff(user, right) {
  const a = String(user).trim().split(/\s+/), b = String(right).trim().split(/\s+/);
  const k = s => norm(s);
  const m = a.length, n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) for (let j = n - 1; j >= 0; j--) dp[i][j] = k(a[i]) === k(b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  let i = 0, j = 0; const out = [];
  while (i < m && j < n) {
    if (k(a[i]) === k(b[j])) { out.push(esc(b[j])); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out.push(`<del>${esc(a[i])}</del>`); i++; }
    else { out.push(`<ins>${esc(b[j])}</ins>`); j++; }
  }
  while (i < m) out.push(`<del>${esc(a[i++])}</del>`);
  while (j < n) out.push(`<ins>${esc(b[j++])}</ins>`);
  return { html: out.join(" "), acc: n ? dp[0][0] / n : 1 };
}
// Xato gap yasash ("Correct the sentence")
function breakSentence(s, w) {
  const muts = [];
  const sw = (re, to, why) => { if (re.test(s)) muts.push({ bad: s.replace(re, to), why }); };
  sw(/\bis\b/, "are", "«is/are» — ega birlikda bo'lsa «is»."); sw(/\bare\b/, "is", "«are» — ega ko'plikda.");
  sw(/\bhas\b/, "have", "He/She/It bilan «has»."); sw(/\bwas\b/, "were", "Birlikda «was»."); sw(/\bdoesn't\b/, "don't", "He/She/It bilan «doesn't».");
  sw(/\ban\b/, "a", "Unli tovush oldidan «an»."); sw(/\ba (?=[bcdfghjklmnpqrstvwxyz])/, "an ", "Undosh oldidan «a».");
  sw(/\bwent\b/, "goed", "«go» — noto'g'ri fe'l: went."); sw(/\bto (\w+)/, "$1", "Bu yerda «to» kerak.");
  const m3 = s.match(/\b(He|She|It|he|she|it)\s+(\w+?)(s)\b/);
  if (m3 && m3[2].length > 2) muts.push({ bad: s.replace(m3[0], `${m3[1]} ${m3[2]}`), why: "He/She/It bilan fe'lga «-s» qo'shiladi." });
  const f = w && findWordInSentence(s, w.en);
  if (f && f.match.length >= 4) {
    const t = f.match, i = 1 + rnd(t.length - 3);
    const wrong = t.slice(0, i) + t[i + 1] + t[i] + t.slice(i + 2);
    if (wrong !== t) muts.push({ bad: s.slice(0, f.index) + wrong + s.slice(f.index + t.length), why: `Imlo: «${t}» to'g'ri yozilishi.` });
  }
  if (!muts.length) return null;
  return pick(muts);
}

// Mashq yasash
function buildEx(kind, w, o = {}) {
  const ex = { kind, w, skill: o.skill || "vocab", hint: o.hint !== false };
  const lvl = o.lvl || 1;
  const nOpt = lvl >= 3 ? 5 : 4;
  const cz = w && cloze(w);
  const blankHtml = c => `${esc(c.before)}<span class="blank">____</span>${esc(c.after)}`;
  switch (kind) {
    case "intro":
      ex.type = "intro"; ex.label = "🆕 Yangi so'z"; break;
    case "mcq_en_uz":
      ex.type = "mcq"; ex.label = "Tarjimasini tanlang";
      ex.q = `<div class="qtext">${esc(w.en)} ${speakBtn(w.en)}</div><div class="qsub">${esc(w.pron || "")}</div>`;
      ex.answer = w.uz; ex.options = shuffle([w.uz, ...distractors(w, "uz", nOpt - 1).map(x => x.uz)]); ex.sayOnShow = w.en; break;
    case "mcq_uz_en":
      ex.type = "mcq"; ex.label = "Inglizchasini tanlang";
      ex.q = `<div class="qtext">${esc(w.uz)}</div><div class="qsub">Qaysi so'z shu ma'noni beradi?</div>`;
      ex.answer = w.en; ex.options = shuffle([w.en, ...distractors(w, "en", nOpt - 1).map(x => x.en)]); break;
    case "cloze_mcq":
      ex.type = "mcq"; ex.label = "To'g'ri so'zni tanlang";
      ex.q = `<div class="qtext">${blankHtml(cz)}</div><div class="qsub">💡 ${esc(w.uz)}</div>`;
      ex.answer = cz.answer; ex.options = shuffle([cz.answer, ...distractors(w, "en", nOpt - 1).map(x => inflectLike(cz.answer, w.en, x))]);
      ex.after = w.ex; break;
    case "cloze_type":
      ex.type = "type"; ex.label = "Bo'sh joyni to'ldiring";
      ex.q = `<div class="qtext">${blankHtml(cz)}</div>${lvl < 3 ? `<div class="qsub">💡 ${esc(w.uz)}</div>` : ""}`;
      ex.answer = cz.answer; ex.hintText = `Birinchi harf: «${cz.answer[0]}» · ${cz.answer.length} harf`; ex.after = w.ex; break;
    case "type_uz_en":
      ex.type = "type"; ex.label = "O'zbekchadan inglizchaga";
      ex.q = `<div class="qtext">${esc(w.uz)}</div><div class="qsub">Inglizcha so'zni yozing${w.pos ? ` (${esc(w.pos)})` : ""}</div>`;
      ex.answer = w.en; ex.hintText = `${w.en[0]}${"_".repeat(Math.max(0, w.en.length - 1)).split("").join(" ")}`; break;
    case "type_en_uz":
      ex.type = "type"; ex.lang = "uz"; ex.label = "Inglizchadan o'zbekchaga";
      ex.q = `<div class="qtext">${esc(w.en)} ${speakBtn(w.en)}</div>${w.ex ? `<div class="qsub">«${esc(w.ex)}»</div>` : ""}`;
      ex.answer = w.uz; ex.ph = "O'zbekcha tarjimasi..."; ex.hintText = `Birinchi harf: «${w.uz[0]}»`; break;
    case "sentence":
      ex.type = "free"; ex.label = "O'z gapingizni tuzing";
      ex.q = `<div class="qtext">«${esc(w.en)}» so'zi bilan gap tuzing ${speakBtn(w.en)}</div><div class="qsub">${esc(w.uz)}${w.pos ? ` · ${esc(w.pos)}` : ""}</div>`;
      ex.ph = "Masalan: " + (w.ex ? "..." : `I want to use «${w.en}» in a sentence.`); break;
    case "correct": {
      const b = breakSentence(w.ex, w);
      ex.type = "type"; ex.label = "Gapdagi xatoni tuzating"; ex.long = true;
      ex.q = `<div class="qtext" style="font-size:1.2rem">❌ ${esc(b.bad)}</div><div class="qsub">Gapni to'g'ri holda qayta yozing.</div>`;
      ex.answer = w.ex; ex.bad = b.bad; ex.why = b.why; ex.prefill = b.bad; ex.hintText = b.why; break;
    }
    case "paragraph":
      ex.type = "para"; ex.label = "Matnni to'ldiring"; ex.words = o.words; ex.noRate = true; break;
    // ---- tinglash ----
    case "listen_meaning":
      ex.type = "mcq"; ex.label = "Eshiting va ma'nosini tanlang"; ex.audio = w.en;
      ex.q = `<div class="qsub center">Qaysi so'zni eshitdingiz? Uning ma'nosi:</div>`;
      ex.answer = w.uz; ex.options = shuffle([w.uz, ...distractors(w, "uz", nOpt - 1).map(x => x.uz)]); ex.reveal = w.en; break;
    case "listen_word":
      ex.type = "type"; ex.label = "Eshitganingizni yozing"; ex.audio = w.en;
      ex.q = `<div class="qsub center">So'zni eshiting va yozing</div>`; ex.answer = w.en; ex.hintText = `💡 Ma'nosi: ${w.uz}`; break;
    case "listen_identify":
      ex.type = "mcq"; ex.label = "Gapda qaysi so'z bor edi?"; ex.audio = w.ex;
      ex.q = `<div class="qsub center">Gapni tinglang va unda ishlatilgan so'zni toping</div>`;
      ex.answer = w.en; ex.options = shuffle([w.en, ...distractors(w, "en", nOpt - 1).map(x => x.en)]); ex.reveal = w.ex; break;
    case "listen_missing":
      ex.type = lvl >= 3 ? "type" : "mcq"; ex.label = "Tushib qolgan so'z"; ex.audio = w.ex;
      ex.q = `<div class="qtext" style="font-size:1.2rem">${blankHtml(cz)}</div>`;
      ex.answer = cz.answer; if (ex.type === "mcq") ex.options = shuffle([cz.answer, ...distractors(w, "en", nOpt - 1).map(x => inflectLike(cz.answer, w.en, x))]); break;
    case "listen_sentence":
      ex.type = "type"; ex.long = true; ex.label = "Diktant: gapni yozing"; ex.audio = w.ex;
      ex.q = `<div class="qsub center">Gapni to'liq yozing. Kerak bo'lsa qayta tinglang.</div>`; ex.answer = w.ex; ex.dict = true; break;
    case "listen_translate":
      ex.type = "type"; ex.lang = "uz"; ex.label = "Eshiting va tarjima qiling"; ex.audio = lvl >= 2 && w.ex ? w.ex : w.en;
      ex.q = `<div class="qsub center">${lvl >= 2 && w.ex ? "Gapdagi <b>asosiy so'z</b>ning o'zbekcha tarjimasini yozing" : "So'zning o'zbekcha tarjimasini yozing"}</div>`;
      ex.answer = w.uz; ex.reveal = ex.audio; ex.hintText = `Asosiy so'z: ${w.en}`; break;
  }
  return ex;
}

function suggestGrade(res) {
  if (!res.ok) return 0;
  if (res.typo || res.hinted || res.sec > 15) return 1;
  if (res.sec < 5 && !res.long) return 3;
  return 2;
}
function rateHtml(w, sug) {
  return `<div class="rate"><div class="row between"><b>Bu so'zni qanchalik yaxshi esladingiz?</b><span class="tiny muted">1–4 tugmalari</span></div>
    <div class="rbtns">${GRADES.map(g => `<button data-g="${g.g}" class="${g.g === sug ? "sug" : ""}"><span>${g.e}</span>${g.t}<small>${!isNew(w) && w.srs.reps > 0 && w.srs.due > Date.now() && g.g >= 2 ? fmtIvl((w.srs.due - Date.now()) / DAY) : fmtIvl(previewIvl(w, g.g))}</small></button>`).join("")}</div></div>`;
}
function fbList(items) { return `<ul class="fblist">${items.map(i => `<li class="${i.k}">${esc(i.t)}</li>`).join("")}</ul>`; }

// Bitta mashqni ko'rsatish. onNext(res, grade) — keyingisiga o'tish
function runEx(box, ex, onNext) {
  const t0 = Date.now();
  let done = false, hinted = false;
  const w = ex.w;
  let html = `<div class="qcard"><div class="row between"><span class="qkind">${ex.label}</span>${w && ex.type !== "intro" ? `<span class="tag">${esc(catOf(w.cat).icon)} ${esc(LEVELS[w.level] ? LEVELS[w.level].dot : "")}</span>` : ""}</div>`;
  if (ex.type === "intro") {
    html += wordCardHtml(w, { compact: true }) + `<div class="row mt" style="justify-content:flex-end"><button class="btn big" data-next>Tushundim →</button></div>`;
  } else {
    if (ex.audio) html += `<button class="play" data-play>🔊</button><div class="center"><button class="btn ghost sm" data-slow>🐢 Sekinroq</button></div>`;
    html += ex.q || "";
    if (ex.type === "mcq") html += `<div class="opts">${ex.options.map((o, i) => `<button class="opt" data-i="${i}"><span class="k">${i + 1}</span><span>${esc(o)}</span></button>`).join("")}</div>`;
    if (ex.type === "type") html += `<div class="mt">${ex.long ? `<textarea class="inp" id="ans" rows="2" spellcheck="false" placeholder="${esc(ex.ph || "Javobingiz...")}"></textarea>` : `<input class="inp big" id="ans" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="${esc(ex.ph || "Javobingiz...")}">`}</div>
      <div class="row mt"><button class="btn" data-check>Tekshirish ↵</button><button class="btn ghost" data-skip>Bilmayman</button>${ex.hintText ? `<button class="btn ghost" data-hint>💡 Yordam</button>` : ""}</div><div class="small muted mt" id="hintbox"></div>`;
    if (ex.type === "free") html += `<textarea class="inp mt" id="ans" rows="3" placeholder="${esc(ex.ph || "")}"></textarea>
      <div class="row mt"><button class="btn" data-check>Tahlil qilish</button>${hasSR ? `<button class="btn ghost" data-mic>🎤 Gapirib yozish</button>` : ""}<button class="btn ghost" data-skip>O'tkazib yuborish</button></div>`;
    if (ex.type === "para") html += paraHtml(ex);
  }
  html += `<div id="fb"></div></div>`;
  box.innerHTML = html;
  const fb = $("#fb", box), ans = $("#ans", box);
  if (ex.prefill && ans) ans.value = ex.prefill;
  if (ex.audio) {
    const pl = $("[data-play]", box);
    const lvl = adaptLvl("listening");
    const rate = [0, 0.8, 0.95, 1.05][lvl];
    const play = r => { pl.classList.add("on"); speak(ex.audio, { rate: r }).then(() => pl.classList.remove("on")); };
    pl.onclick = () => play(rate);
    $("[data-slow]", box).onclick = () => play(0.65);
    setTimeout(() => play(rate), 350);
  } else if (ex.sayOnShow) setTimeout(() => speak(ex.sayOnShow), 250);
  if (ans && !("ontouchstart" in window)) setTimeout(() => ans.focus(), 50);

  const finish = res => {
    if (done) return; done = true;
    res.sec = (Date.now() - t0) / 1000; res.hinted = hinted; res.long = ex.long || ex.type === "free";
    if (ex.skill && ex.type !== "intro") {
      recordSkill(ex.skill, res.ok, res.score);
      if (ex.skill === "listening") addTime("listen", Math.min(res.sec, 90));
      if (ex.skill === "writing") { today().writing++; save(); checkGoal(); }
      if (!res.ok && w) logMistake(ex.kind, res.given || "", ex.answer || "", ex.label);
      if (res.ok) addXp(ex.skill === "writing" && ex.type === "free" ? 8 : 4);
    }
    if (ex.kind === "listen_word" && res.ok) progressChallenge("dict5", 1, 5);
    if (ex.kind === "listen_sentence" && res.ok) progressChallenge("dict5", 1, 5);
    $$("button[data-check],button[data-skip],button[data-hint],button[data-mic]", box).forEach(b => b.remove());
    let out = res.html || "";
    if (ex.after && res.ok) out += `<div class="small mt">📖 ${esc(ex.after)} ${speakBtn(ex.after)}</div>`;
    if (ex.reveal) out += `<div class="small mt muted">🔊 «${esc(ex.reveal)}» ${speakBtn(ex.reveal)}</div>`;
    const sug = suggestGrade(res);
    if (w && !ex.noRate) {
      out += rateHtml(w, sug);
      fb.innerHTML = out;
      $$(".rbtns button", fb).forEach(b => b.onclick = () => { const g = +b.dataset.g; rateWord(w.id, g); onNext(res, g); });
      KEYH = e => { if (/^[1-4]$/.test(e.key) && document.activeElement.tagName !== "INPUT" && document.activeElement.tagName !== "TEXTAREA") { e.preventDefault(); const g = +e.key - 1; rateWord(w.id, g); onNext(res, g); } else if (e.key === "Enter" && document.activeElement.tagName !== "TEXTAREA") { e.preventDefault(); rateWord(w.id, sug); onNext(res, sug); } };
    } else {
      out += `<div class="row mt" style="justify-content:flex-end"><button class="btn big" data-next>Keyingisi →</button></div>`;
      fb.innerHTML = out;
      $("[data-next]", fb).onclick = () => onNext(res, null);
      KEYH = e => { if (e.key === "Enter") { e.preventDefault(); onNext(res, null); } };
    }
    if (ans) ans.blur();
    fb.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };

  if (ex.type === "intro") {
    setTimeout(() => speak(w.en), 250);
    $("[data-next]", box).onclick = () => onNext({ ok: true, intro: true }, null);
    KEYH = e => { if (e.key === "Enter") { e.preventDefault(); onNext({ ok: true, intro: true }, null); } };
    bindWordCard(box, w);
    return;
  }
  if (ex.type === "mcq") {
    const pickOpt = i => {
      if (done) return;
      const btns = $$(".opt", box), chosen = ex.options[i], ok = norm(chosen) === norm(ex.answer);
      btns.forEach((b, j) => { const o = ex.options[j]; if (norm(o) === norm(ex.answer)) b.classList.add("ok"); else if (j === i) b.classList.add("bad"); else b.classList.add("dim"); });
      const other = !ok && S.words.find(x => norm(x.en) === norm(chosen) || norm(x.uz) === norm(chosen));
      finish({ ok, given: chosen, html: ok ? `<div class="fb ok">✅ To'g'ri! ${pick(["Zo'r!", "Barakalla!", "Ajoyib!", "Great!"])}</div>`
        : `<div class="fb bad">❌ To'g'ri javob: <span class="ans">${esc(ex.answer)}</span>${other && other.id !== (w && w.id) ? `<div class="small" style="color:var(--ink);margin-top:4px">«${esc(other.en)}» — ${esc(other.uz)} degani.</div>` : ""}</div>` });
    };
    $$(".opt", box).forEach(b => b.onclick = () => pickOpt(+b.dataset.i));
    KEYH = e => { if (!done && /^[1-5]$/.test(e.key) && +e.key <= ex.options.length) { e.preventDefault(); pickOpt(+e.key - 1); } };
    return;
  }
  if (ex.type === "type") {
    const check = () => {
      const v = ans.value.trim();
      if (!v) { ans.classList.add("bad"); setTimeout(() => ans.classList.remove("bad"), 500); return; }
      let res;
      if (ex.dict) {
        const d = wordDiff(v, ex.answer);
        const ok = d.acc >= 0.85 && norm(v).split(" ").length <= norm(ex.answer).split(" ").length + 2;
        res = { ok, given: v, typo: ok && d.acc < 1, html: `<div class="fb ${ok ? "ok" : "bad"}">${ok ? "✅" : "❌"} ${Math.round(d.acc * 100)}% to'g'ri<div class="diff mt" style="color:var(--ink)">${d.html}</div></div>` };
      } else if (ex.kind === "correct") {
        const sim = similarity(v, ex.answer), ok = sim >= 0.97;
        const d = wordDiff(v, ex.answer);
        res = { ok, given: v, html: `<div class="fb ${ok ? "ok" : "bad"}">${ok ? "✅ To'g'ri tuzatdingiz!" : "❌ Hali xato bor."}<div class="small mt" style="color:var(--ink)">💡 ${esc(ex.why)}</div><div class="diff mt" style="color:var(--ink)">${ok ? esc(ex.answer) : d.html}</div></div>` };
      } else if (ex.lang === "uz") {
        const g = gradeUz(v, ex.answer);
        res = { ok: g.ok, typo: g.typo, given: v, html: g.ok ? `<div class="fb ok">✅ To'g'ri! <span class="ans">${esc(ex.answer)}</span></div>` : `<div class="fb bad">❌ To'g'ri javob: <span class="ans">${esc(ex.answer)}</span></div>` };
      } else {
        const g = gradeEn(v, ex.answer);
        const other = !g.ok && S.words.find(x => norm(x.en) === norm(v));
        let msg;
        if (g.ok && !g.typo) msg = `<div class="fb ok">✅ To'g'ri! <span class="ans">${esc(ex.answer)}</span></div>`;
        else if (g.typo) msg = `<div class="fb ok">✅ Deyarli! Kichik imlo xatosi bor:<div class="diff" style="color:var(--ink)">${charDiff(v, ex.answer)}</div></div>`;
        else if (other) msg = `<div class="fb bad">❌ Siz «${esc(other.en)}» deb yozdingiz — u «${esc(other.uz)}» degani. To'g'risi: <span class="ans">${esc(ex.answer)}</span></div>`;
        else if (g.d <= 3) msg = `<div class="fb bad">❌ Imlo xatosi. Taqqoslang:<div class="diff" style="color:var(--ink)">${charDiff(v, ex.answer)}</div><div class="small" style="color:var(--ink)">To'g'risi: <b>${esc(ex.answer)}</b></div></div>`;
        else msg = `<div class="fb bad">❌ To'g'ri javob: <span class="ans">${esc(ex.answer)}</span></div>`;
        res = { ok: g.ok, typo: g.typo, given: v, html: msg };
      }
      ans.classList.add(res.ok ? "ok" : "bad");
      ans.readOnly = true;
      finish(res);
    };
    $("[data-check]", box).onclick = check;
    $("[data-skip]", box).onclick = () => finish({ ok: false, given: "", html: `<div class="fb bad">To'g'ri javob: <span class="ans">${esc(ex.answer)}</span></div>` });
    const hb = $("[data-hint]", box);
    if (hb) hb.onclick = () => { hinted = true; $("#hintbox", box).textContent = "💡 " + ex.hintText; hb.remove(); };
    ans.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey && !done) { e.preventDefault(); check(); } });
    return;
  }
  if (ex.type === "free") {
    const check = () => {
      const v = ans.value.trim();
      if (!v) return;
      const a = analyzeSentence(v, w.en);
      const score = Math.round(a.grammar * 0.4 + a.vocab * 0.35 + a.structure * 0.25);
      const ok = a.used && score >= 60;
      a.issues.filter(i => !i.minor).forEach(i => logMistake("grammar", i.wrong, i.right, i.why));
      if (ok && score >= 80) progressChallenge("sent3", 1, 3);
      finish({ ok, score, given: v, long: true, html: `<div class="fb ${ok ? "ok" : "bad"}">${ok ? "✅" : "✏️"} Baho: <b>${score}/100</b>${fbList(a.feedback)}${aiCheckBtn(v, w)}</div>` });
      bindAiCheck(box, v, w);
    };
    $("[data-check]", box).onclick = check;
    $("[data-skip]", box).onclick = () => finish({ ok: false, given: "", html: w.ex ? `<div class="fb bad">Namuna: <span class="ans">${esc(w.ex)}</span></div>` : "" });
    const mb = $("[data-mic]", box);
    if (mb) mb.onclick = async () => {
      mb.textContent = "🔴 Tinglayapman..."; mb.disabled = true;
      try { const r = await listenOnce({ onInterim: t => ans.value = t }); ans.value = r.text; } catch (e) { toast("🎤 Mikrofon ishlamadi: " + e.message); }
      mb.textContent = "🎤 Gapirib yozish"; mb.disabled = false;
    };
    ans.addEventListener("keydown", e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check(); });
    return;
  }
  if (ex.type === "para") {
    const inputs = $$(".para input", box);
    $("[data-check]", box).onclick = () => {
      let c = 0;
      inputs.forEach((inp, i) => {
        const g = gradeEn(inp.value, ex.words[i].c.answer);
        inp.classList.add(g.ok ? "ok" : "bad"); inp.readOnly = true;
        if (g.ok) c++; else inp.title = ex.words[i].c.answer;
      });
      const ok = c === inputs.length;
      const list = ex.words.map((x, i) => `<li class="${inputs[i].classList.contains("ok") ? "ok" : "bad"}">${i + 1}. ${esc(x.c.answer)} — ${esc(x.w.uz)}</li>`).join("");
      finish({ ok, long: true, html: `<div class="fb ${ok ? "ok" : "bad"}">${ok ? "✅ Mukammal!" : `${c}/${inputs.length} to'g'ri`}<ul class="fblist">${list}</ul></div>` });
      ex.words.forEach((x, i) => { if (!inputs[i].classList.contains("ok")) rateWord(x.w.id, 0); });
    };
  }
}
function paraHtml(ex) {
  const parts = ex.words.map((x, i) => `${esc(x.c.before)}<input data-i="${i}" autocomplete="off" autocapitalize="off" spellcheck="false">${esc(x.c.after)}`);
  return `<div class="bank mt">${shuffle(ex.words.map(x => x.c.answer)).map(a => `<span>${esc(a)}</span>`).join("")}</div>
    <p class="para mt">${parts.join(" ")}</p><div class="row mt"><button class="btn" data-check>Tekshirish</button></div>`;
}

// Mashqlar ketma-ketligi
function runSession(box, items, { title, skill, onDone, requeue } = {}) {
  let i = 0, correct = 0, total = 0, xp0 = S.profile.xp;
  const rated = [];
  const total0 = items.length;
  const step = () => {
    if (i >= items.length) return finish();
    const ex = items[i];
    const pct = Math.round(i / items.length * 100);
    box.innerHTML = `<div class="ex-wrap"><div class="qhead"><button class="iconbtn" data-act="quit" title="Chiqish">✕</button>${bar(pct)}<b class="small">${i + 1}/${items.length}</b></div><div id="exbox"></div></div>`;
    runEx($("#exbox", box), ex, (res, g) => {
      if (!res.intro) { total++; if (res.ok) correct++; }
      if (ex.w && g !== null && g !== undefined) rated.push({ w: ex.w, g });
      if (requeue && g === 0 && ex.w) requeue(ex, items, i);
      i++; step();
    });
  };
  const finish = () => {
    KEYH = null;
    const xp = S.profile.xp - xp0, pct = total ? Math.round(correct / total * 100) : 0;
    if (pct === 100 && total >= 5) confetti(50);
    box.innerHTML = `<div class="ex-wrap"><div class="qcard center">
      <div style="font-size:3.4rem">${pct >= 90 ? "🏆" : pct >= 70 ? "🎉" : pct >= 50 ? "👍" : "💪"}</div>
      <h2>${esc(title || "Mashq")} tugadi!</h2>
      <p class="muted">${pct >= 90 ? "Ajoyib natija!" : pct >= 70 ? "Yaxshi ish!" : pct >= 50 ? "Yomon emas — takrorlash davom etadi." : "Qiyin bo'ldi, lekin aynan shunday o'rganiladi!"}</p>
      <div class="grid g3 mt"><div class="stat"><div class="v">${correct}/${total}</div><div class="l">to'g'ri</div></div>
      <div class="stat"><div class="v">${pct}%</div><div class="l">aniqlik</div></div><div class="stat"><div class="v" style="color:var(--accent)">+${xp}</div><div class="l">XP</div></div></div>
      ${rated.length ? `<div class="mt" style="text-align:left"><b class="small">Keyingi takrorlash:</b><div class="wlist mt">${uniqRated(rated).map(r => `<div class="witem" style="cursor:default"><span>${GRADES[r.g].e}</span><div class="grow"><b>${esc(r.w.en)}</b> <span class="muted small">${esc(r.w.uz)}</span></div><span class="tag">${r.w.srs.due > Date.now() ? fmtIvl((r.w.srs.due - Date.now()) / DAY) + " dan keyin" : "hozir"}</span></div>`).join("")}</div></div>` : ""}
      <div class="row mt2" style="justify-content:center"><button class="btn big" data-act="again">🔁 Yana</button><button class="btn ghost big" data-go="home">🏠 Bosh sahifa</button></div></div></div>`;
    onDone && onDone({ correct, total });
  };
  ACT.quit = async () => { if (i === 0 || await confirmDlg("Mashqni to'xtatasizmi?", "To'xtatish", false)) finish(); };
  step();
  return { total0 };
}
function uniqRated(r) { const m = new Map(); r.forEach(x => m.set(x.w.id, x)); return [...m.values()]; }

/* ================= so'z kartasi ================= */
function wordCardHtml(w, { compact = false } = {}) {
  const lv = LEVELS[w.level] || LEVELS.beginner;
  return `<div class="vcard mt"><div class="top"><div class="row between nowrap"><div class="grow"><div class="word">${esc(cap(w.en))}</div>
    <div class="pron">${esc(w.pron || "")} ${w.pos ? `<span class="tag" style="background:rgba(255,255,255,.2);color:#fff">${esc(w.pos)}</span>` : ""}</div></div>
    <button class="btn white icon" data-say="${esc(w.en)}" style="font-size:1.3rem">🔊</button></div></div>
    <div class="body"><div class="tiny muted">O'ZBEKCHA</div><div class="uzb">${esc(w.uz)}</div>
    ${w.ex ? `<div class="ex">«${esc(w.ex)}» ${speakBtn(w.ex)}</div>` : ""}
    ${w.note ? `<div class="small mt">📝 ${esc(w.note)}</div>` : ""}
    <div class="row mt"><span class="tag">${esc(catOf(w.cat).icon)} ${esc(catOf(w.cat).name)}</span><span class="tag">${lv.dot} ${lv.name}</span>${(() => { const st = stageOf(w); return `<span class="tag" style="color:${st.c}">● ${st.uz}</span>`; })()}</div>
    ${compact ? "" : `<div class="acts"><button data-wa="listen"><span>🔊</span>Listen</button><button data-wa="speak"><span>🎤</span>Speak</button><button data-wa="write"><span>✍️</span>Write</button><button data-wa="practice"><span>🧠</span>Practice</button><button data-wa="fav" class="${w.fav ? "on" : ""}"><span>⭐</span>Favorite</button></div>`}
    </div></div>`;
}
function bindWordCard(root, w, after) {
  $$("[data-wa]", root).forEach(b => b.onclick = async () => {
    const a = b.dataset.wa;
    if (a === "listen") { await speak(w.en); if (w.ex) { await new Promise(r => setTimeout(r, 300)); speak(w.ex); } }
    if (a === "speak") location.hash = "#/speaking?w=" + w.id;
    if (a === "write") location.hash = "#/writing?w=" + w.id;
    if (a === "practice") location.hash = "#/practice?w=" + w.id;
    if (a === "fav") { w.fav = !w.fav; save(); b.classList.toggle("on", w.fav); toast(w.fav ? "⭐ Sevimlilarga qo'shildi" : "Sevimlilardan olindi"); after && after(); }
  });
}
function openWord(w, refresh) {
  const s = w.srs;
  const m = modal(`${wordCardHtml(w)}
    <div class="grid g3 mt small">
      <div class="stat"><div class="l">Keyingi takrorlash</div><b>${isNew(w) ? "—" : s.due <= Date.now() ? "Hozir" : fmtIvl((s.due - Date.now()) / DAY)}</b></div>
      <div class="stat"><div class="l">Takrorlangan</div><b>${s.hist.length} marta</b></div>
      <div class="stat"><div class="l">Unutilgan</div><b>${s.lapses} marta</b></div></div>
    <div class="row mt2"><button class="btn ghost" data-e>✏️ Tahrirlash</button><button class="btn ghost" data-d style="color:var(--err)">🗑️ O'chirish</button><span class="grow"></span><button class="btn" data-close>Yopish</button></div>`);
  bindWordCard(m, w, refresh);
  $$("[data-wa]", m).forEach(b => { if (b.dataset.wa !== "listen" && b.dataset.wa !== "fav") b.addEventListener("click", () => m.remove()); });
  m.querySelector("[data-e]").onclick = () => { m.remove(); editWord(w, refresh); };
  m.querySelector("[data-d]").onclick = async () => {
    m.remove();
    if (await confirmDlg(`«${w.en}» o'chirilsinmi?`, "O'chirish")) { S.words = S.words.filter(x => x.id !== w.id); save(); toast("🗑️ O'chirildi"); refresh && refresh(); }
  };
}

/* ================= BOSH SAHIFA ================= */
VIEWS.home = (v) => {
  themeAct();
  const hr = new Date().getHours();
  const hello = hr < 5 ? "Xayrli tun" : hr < 12 ? "Xayrli tong" : hr < 18 ? "Xayrli kun" : "Xayrli kech";
  const plan = planItems(), planPct = Math.round(plan.reduce((a, i) => a + i.pct, 0) / plan.length * 100);
  const due = dueWords().length, fresh = newWordsLeft().length;
  const learned = S.words.filter(isLearned).length, mastered = S.words.filter(isMastered).length, diff = S.words.filter(isDifficult).length;
  const L = levelInfo(), d = today(), ch = todayChallenge();
  const wk = [...Array(7)].map((_, i) => { const k = dayKey(Date.now() - (6 - i) * DAY); return { k, xp: (S.days[k] || {}).xp || 0, d: new Date(k) }; });
  const maxXp = Math.max(50, ...wk.map(x => x.xp));
  const wotd = wordOfDay();
  const skills = [["🎤", "Speaking", "speaking", ""], ["✍️", "Writing", "writing", "ok"], ["🎧", "Listening", "listening", "sky"], ["🧠", "Vocabulary", "vocab", "warn"]];
  v.innerHTML = `${topbar(`${hello}${S.profile.name ? ", " + esc(S.profile.name) : ""}! 👋`, d.done ? "🎉 Bugungi maqsad bajarildi — ertaga ham kutamiz!" : "Bugun ham bir qadam oldinga")}
  <div class="card hero"><div class="row between nowrap" style="position:relative;z-index:1">
    <div class="grow"><div class="small muted" style="font-weight:800">BUGUNGI MASHQ</div>
      <h2 style="font-size:1.5rem;margin:6px 0">${due ? `🔁 ${due} ta so'z takrorlashni kutyapti` : fresh ? `🆕 ${fresh} ta yangi so'z tayyor` : S.words.length ? "✨ Hammasi takrorlandi!" : "📚 Lug'atingizni to'ldiring"}</h2>
      <p class="muted">${due || fresh ? "Takrorlash tizimi so'zlarni aynan unutishingizdan oldin qaytaradi." : S.words.length ? "Erkin mashq yoki o'yin bilan mustahkamlang." : "So'z qo'shing yoki ro'yxatni import qiling."}</p>
      <div class="row mt">${S.words.length ? `<button class="btn white big" data-go="practice">▶ ${due || fresh ? "Boshlash" : "Erkin mashq"}</button><button class="btn big" style="background:rgba(255,255,255,.18)" data-go="games">🎮 O'yinlar</button>` : `<button class="btn white big" data-go="vocab">➕ So'z qo'shish</button>`}</div></div>
    <div class="hide-sm" style="flex:0 0 auto">${ring(planPct, planPct + "%", "#fff")}</div></div></div>

  <div class="grid g3 mt">
    <div class="stat"><div class="e">📚</div><div class="v">${learned}</div><div class="l">o'rganilgan so'z</div></div>
    <div class="stat"><div class="e">🎯</div><div class="v">${due}</div><div class="l">bugun takrorlash</div></div>
    <div class="stat"><div class="e">💎</div><div class="v">${mastered}</div><div class="l">yodlangan</div></div>
    <div class="stat"><div class="e">😵</div><div class="v">${diff}</div><div class="l">qiyin so'zlar</div></div>
    <div class="stat"><div class="e">🔥</div><div class="v">${streakNow()}</div><div class="l">kunlik seriya · eng yaxshi ${S.profile.bestStreak}</div></div>
    <div class="stat"><div class="e">⭐</div><div class="v">${S.profile.xp}</div><div class="l">XP · ${L.lvl}-daraja «${L.name}»</div></div>
  </div>

  <div class="grid g2 stack-sm mt">
    <div class="card"><div class="row between"><h3>📅 Bugungi reja</h3><span class="tag ${d.done ? "ok" : "acc"}">${d.done ? "✅ Bajarildi" : planPct + "%"}</span></div>
      <ul class="plan mt">${plan.map(i => `<li class="${i.done ? "done" : ""}"><span class="chk">${i.done ? "✓" : i.icon}</span><div class="grow"><div class="t" style="font-weight:800">${i.t}</div><div class="small muted">${i.cur}${i.unit} / ${i.goal}${i.unit}</div>${bar(i.pct * 100, "thin " + (i.done ? "ok" : ""))}</div>${i.done ? "" : `<button class="btn sm ghost go" data-go="${i.go}">Boshlash</button>`}</li>`).join("")}</ul>
      <div class="card soft mt" style="padding:14px"><div class="row between"><b>🏅 Kunlik sinov</b><span class="tag ${challengeDone() ? "ok" : "warn"}">${challengeDone() ? "✅ Bajarildi" : "+" + ch.xp + " XP"}</span></div><div class="mt small" style="font-weight:700">${ch.t}</div></div>
    </div>
    <div class="stack">
      <div class="card"><div class="row between"><h3>📈 Haftalik natija</h3><span class="small muted">${weekXp()} / ${S.profile.weeklyXp} XP</span></div>
        <div class="mt">${bar(weekXp() / S.profile.weeklyXp * 100)}</div>
        <div class="week">${wk.map((x, i) => `<div class="col ${i === 6 ? "today" : ""}"><em>${x.xp || ""}</em><div class="b" style="height:${Math.max(3, x.xp / maxXp * 100)}%"></div><span>${["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"][x.d.getDay()]}</span></div>`).join("")}</div></div>
      <div class="card"><h3>🧩 Ko'nikmalar</h3>${skills.map(([i, n, k, c]) => `<div class="mt"><div class="row between small"><b>${i} ${n}</b><b>${skillPct(k)}%</b></div>${bar(skillPct(k), c)}</div>`).join("")}</div>
    </div>
  </div>

  ${wotd ? `<div class="mt2"><h3>🌟 Kun so'zi</h3><div id="wotd"></div></div>` : ""}

  <h3 class="mt2">🚀 Tez boshlash</h3>
  <div class="grid g4 mt">
    ${[["practice", "🧠", "Takrorlash", "Takrorlash tizimi"], ["writing", "✍️", "Yozish", "Gap tuzish, xato tuzatish"], ["speaking", "🎤", "Gapirish", "Nutqni tahlil qilish"], ["listening", "🎧", "Tinglash", "Diktant va tushunish"],
       ["games", "🎮", "O'yinlar", "8 xil o'yin"], ["talk", "💬", "Suhbat", "AI bilan gaplashish"], ["teacher", "🤖", "AI Ustoz", "Savol bering"], ["progress", "📊", "Natijalar", "Statistika va yutuqlar"]]
      .map(([r, i, t, s]) => `<button class="tile" data-go="${r}"><span class="big">${i}</span><b>${t}</b><span class="muted">${s}</span></button>`).join("")}
  </div>`;
  if (wotd) { $("#wotd").innerHTML = wordCardHtml(wotd); bindWordCard($("#wotd"), wotd); }
};
function wordOfDay() {
  if (!S.words.length) return null;
  const pool = S.words.filter(isDifficult).length >= 3 ? S.words.filter(isDifficult) : S.words;
  const n = Math.floor(new Date(dayKey()).getTime() / DAY);
  return pool[n % pool.length];
}

/* ================= LUG'ATIM ================= */
const VF = { q: "", f: "all", cat: "", lvl: "", sort: "new" };
VIEWS.vocab = (v) => {
  themeAct();
  const counts = {}; S.words.forEach(w => counts[w.cat] = (counts[w.cat] || 0) + 1);
  v.innerHTML = `${topbar("📚 Lug'atim", `${S.words.length} ta so'z · ${S.words.filter(isMastered).length} ta yodlangan`)}
    <div class="row"><button class="btn" data-act="add">➕ So'z qo'shish</button><button class="btn ghost" data-act="import">📥 Import</button><button class="btn ghost" data-act="cats">🏷️ Kategoriyalar</button><button class="btn ghost" data-act="export">📤 CSV</button></div>
    <div class="card mt">
      <div class="search"><input class="inp" id="q" placeholder="Qidirish: inglizcha yoki o'zbekcha..." value="${esc(VF.q)}"></div>
      <div class="row mt"><div class="seg" id="fseg">${[["all", "Hammasi"], ["due", "Takrorlash"], ["new", "Yangi"], ["hard", "Qiyin"], ["mastered", "Yodlangan"], ["fav", "⭐"]].map(([k, t]) => `<button data-f="${k}" class="${VF.f === k ? "on" : ""}">${t}</button>`).join("")}</div></div>
      <div class="row mt">
        <select class="inp" id="fcat" style="width:auto;flex:1"><option value="">Barcha kategoriyalar</option>${allCats().map(c => `<option value="${c.id}" ${VF.cat === c.id ? "selected" : ""}>${c.icon} ${esc(c.name)} (${counts[c.id] || 0})</option>`).join("")}</select>
        <select class="inp" id="flvl" style="width:auto;flex:1"><option value="">Barcha darajalar</option>${Object.entries(LEVELS).map(([k, l]) => `<option value="${k}" ${VF.lvl === k ? "selected" : ""}>${l.dot} ${l.name}</option>`).join("")}</select>
        <select class="inp" id="fsort" style="width:auto;flex:1">${[["new", "Yangi qo'shilgan"], ["az", "A → Z"], ["due", "Takrorlash vaqti"], ["hard", "Eng qiyin"]].map(([k, t]) => `<option value="${k}" ${VF.sort === k ? "selected" : ""}>${t}</option>`).join("")}</select>
      </div>
    </div>
    <div class="row mt" id="catchips">${allCats().filter(c => counts[c.id]).map(c => `<button class="chip" style="cursor:pointer;${VF.cat === c.id ? "border-color:var(--accent);color:var(--accent)" : ""}" data-cat="${c.id}">${c.icon} ${esc(c.name)} · ${counts[c.id]}</button>`).join("")}</div>
    <div class="wlist mt" id="wl"></div>`;
  const list = () => {
    let ws = S.words.slice();
    const q = norm(VF.q);
    if (q) ws = ws.filter(w => norm(w.en).includes(q) || norm(w.uz).includes(q));
    const t = Date.now();
    if (VF.f === "due") ws = ws.filter(w => isDue(w, t));
    if (VF.f === "new") ws = ws.filter(isNew);
    if (VF.f === "hard") ws = ws.filter(isDifficult);
    if (VF.f === "mastered") ws = ws.filter(isMastered);
    if (VF.f === "fav") ws = ws.filter(w => w.fav);
    if (VF.cat) ws = ws.filter(w => w.cat === VF.cat);
    if (VF.lvl) ws = ws.filter(w => w.level === VF.lvl);
    const sorts = { new: (a, b) => b.created - a.created, az: (a, b) => a.en.localeCompare(b.en), due: (a, b) => (isNew(a) - isNew(b)) || a.srs.due - b.srs.due, hard: (a, b) => b.srs.lapses - a.srs.lapses || a.srs.ease - b.srs.ease };
    ws.sort(sorts[VF.sort]);
    $("#wl").innerHTML = ws.length ? ws.slice(0, 400).map(w => { const st = stageOf(w); return `<div class="witem" data-w="${w.id}"><span class="dot" style="background:${st.c}" title="${st.uz}"></span>
      <div class="grow"><div><span class="en">${esc(w.en)}</span> <span class="small muted">${esc(w.pron || "")}</span></div><div class="uz">${esc(w.uz)}</div></div>
      <span class="tag hide-sm">${catOf(w.cat).icon} ${esc(catOf(w.cat).name)}</span><span title="${LEVELS[w.level].name}">${LEVELS[w.level].dot}</span>${w.fav ? "⭐" : ""}${speakBtn(w.en)}</div>`; }).join("") + (ws.length > 400 ? `<p class="small muted center">... yana ${ws.length - 400} ta (qidiruvdan foydalaning)</p>` : "")
      : `<div class="empty"><div class="big">🔍</div><p>${S.words.length ? "Hech narsa topilmadi" : "Lug'atingiz hozircha bo'sh. So'z qo'shing yoki ro'yxatni import qiling!"}</p></div>`;
    $$("#wl .witem").forEach(el => el.onclick = () => openWord(wordById(el.dataset.w), () => render()));
  };
  $("#q").oninput = e => { VF.q = e.target.value; list(); };
  $$("#fseg button").forEach(b => b.onclick = () => { VF.f = b.dataset.f; $$("#fseg button").forEach(x => x.classList.toggle("on", x === b)); list(); });
  $("#fcat").onchange = e => { VF.cat = e.target.value; render(); };
  $("#flvl").onchange = e => { VF.lvl = e.target.value; list(); };
  $("#fsort").onchange = e => { VF.sort = e.target.value; list(); };
  $$("#catchips [data-cat]").forEach(b => b.onclick = () => { VF.cat = VF.cat === b.dataset.cat ? "" : b.dataset.cat; render(); });
  list();
  ACT.add = () => editWord(null, () => render());
  ACT.import = () => importDlg();
  ACT.cats = () => catsDlg();
  ACT.export = () => {
    const rows = [["English", "Uzbek", "Example", "Part of speech", "Pronunciation", "Category", "Level", "Note"]].concat(S.words.map(w => [w.en, w.uz, w.ex, w.pos, w.pron, catOf(w.cat).name, w.level, w.note]));
    download("lugat.csv", rows.map(r => r.map(c => `"${String(c || "").replace(/"/g, '""')}"`).join(",")).join("\n"), "text/csv");
  };
};
function download(name, text, type = "application/json") {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type }));
  a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function catOptions(sel) { return allCats().map(c => `<option value="${c.id}" ${sel === c.id ? "selected" : ""}>${c.icon} ${esc(c.name)}</option>`).join("") + `<option value="__new">➕ Yangi kategoriya...</option>`; }
function bindCatSelect(sel) {
  sel.addEventListener("change", () => {
    if (sel.value !== "__new") return;
    const name = prompt("Yangi kategoriya nomi:");
    if (name && name.trim()) { const id = normCatId(name); save(); sel.innerHTML = catOptions(id); }
    else sel.value = allCats()[0].id;
  });
}
function editWord(w, after) {
  const isEdit = !!w;
  const o = w || { en: "", uz: "", ex: "", pron: "", pos: "", note: "", level: S.profile.level, cat: VF.cat || "daily" };
  const m = modal(`<h2>${isEdit ? "✏️ So'zni tahrirlash" : "➕ Yangi so'z"}</h2>
    <div class="grid g2 stack-sm"><div><label class="f">English *</label><input class="inp" id="f_en" value="${esc(o.en)}" placeholder="improve" autocapitalize="off"></div>
    <div><label class="f">O'zbekcha *</label><input class="inp" id="f_uz" value="${esc(o.uz)}" placeholder="yaxshilamoq"></div></div>
    <button class="btn ghost sm mt" id="auto">🪄 Talaffuz, so'z turkumi va misolni avtomatik to'ldirish</button>
    <div class="grid g2 stack-sm"><div><label class="f">Talaffuz</label><input class="inp" id="f_pron" value="${esc(o.pron)}" placeholder="/ɪmˈpruːv/"></div>
    <div><label class="f">So'z turkumi</label><select class="inp" id="f_pos"><option value="">—</option>${POS.map(p => `<option ${o.pos === p ? "selected" : ""}>${p}</option>`).join("")}</select></div></div>
    <label class="f">Misol gap</label><input class="inp" id="f_ex" value="${esc(o.ex)}" placeholder="I want to improve my English.">
    <label class="f">Shaxsiy izoh (ixtiyoriy)</label><input class="inp" id="f_note" value="${esc(o.note)}" placeholder="Masalan: «prove» so'ziga o'xshaydi">
    <div class="grid g2 stack-sm"><div><label class="f">Kategoriya</label><select class="inp" id="f_cat">${catOptions(o.cat)}</select></div>
    <div><label class="f">Qiyinlik</label><div class="seg" id="f_lvl">${Object.entries(LEVELS).map(([k, l]) => `<button data-l="${k}" class="${o.level === k ? "on" : ""}">${l.dot} ${l.uz}</button>`).join("")}</div></div></div>
    <div class="row mt2"><button class="btn big" id="f_save">💾 Saqlash</button>${isEdit ? "" : `<button class="btn ghost big" id="f_more">Saqlab, yana qo'shish</button>`}<button class="btn ghost" data-close>Bekor</button></div>`);
  let lvl = o.level;
  bindCatSelect($("#f_cat", m));
  $$("#f_lvl button", m).forEach(b => b.onclick = () => { lvl = b.dataset.l; $$("#f_lvl button", m).forEach(x => x.classList.toggle("on", x === b)); });
  $("#auto", m).onclick = async e => {
    const en = $("#f_en", m).value.trim();
    if (!en) { toast("Avval inglizcha so'zni yozing"); return; }
    e.target.textContent = "⏳ Qidirilmoqda..."; e.target.disabled = true;
    try {
      const r = await dictLookup(en);
      if (r.pron && !$("#f_pron", m).value) $("#f_pron", m).value = r.pron;
      if (r.pos && !$("#f_pos", m).value && POS.includes(r.pos)) $("#f_pos", m).value = r.pos;
      if (r.ex && !$("#f_ex", m).value) $("#f_ex", m).value = r.ex;
      if (r.def && !$("#f_note", m).value) $("#f_note", m).value = r.def;
      toast("🪄 To'ldirildi");
    } catch (err) { toast("Lug'atda topilmadi yoki internet yo'q"); }
    e.target.textContent = "🪄 Avtomatik to'ldirish"; e.target.disabled = false;
  };
  const doSave = more => {
    const en = $("#f_en", m).value.trim(), uz = $("#f_uz", m).value.trim();
    if (!en || !uz) { toast("Inglizcha so'z va tarjimasi majburiy"); return; }
    const dup = S.words.find(x => norm(x.en) === norm(en) && (!w || x.id !== w.id));
    if (dup && !confirm(`«${dup.en}» lug'atda bor (${dup.uz}). Baribir qo'shilsinmi?`)) return;
    const data = { en, uz, pron: $("#f_pron", m).value.trim(), pos: $("#f_pos", m).value, ex: $("#f_ex", m).value.trim(), note: $("#f_note", m).value.trim(), cat: $("#f_cat", m).value === "__new" ? "daily" : $("#f_cat", m).value, level: lvl };
    if (isEdit) Object.assign(w, data); else S.words.push(newWord(data));
    save(); checkAchievements();
    toast(isEdit ? "✅ Saqlandi" : `✅ «${en}» qo'shildi`);
    if (more) { ["f_en", "f_uz", "f_pron", "f_ex", "f_note"].forEach(id => $("#" + id, m).value = ""); $("#f_pos", m).value = ""; $("#f_en", m).focus(); }
    else { m.remove(); after && after(); }
  };
  $("#f_save", m).onclick = () => doSave(false);
  const mb = $("#f_more", m); if (mb) mb.onclick = () => doSave(true);
  setTimeout(() => $("#f_en", m).focus(), 60);
}
function importDlg() {
  const m = modal(`<h2>📥 So'zlarni import qilish</h2>
    <p class="small muted">Har qatorda bitta so'z: <span class="kbd">English | Uzbek</span>. Ajratgich sifatida <b>|</b>, <b>Tab</b>, <b>;</b>, <b>-</b> yoki <b>vergul</b> (CSV) ishlaydi. Qo'shimcha ustunlar: misol, so'z turkumi, talaffuz, kategoriya, daraja.</p>
    <textarea class="inp" id="im_t" rows="8" placeholder="English | Uzbek&#10;apple | olma&#10;beautiful | chiroyli&#10;improve | yaxshilamoq | I want to improve my English."></textarea>
    <div class="row mt"><label class="btn ghost sm" style="cursor:pointer">📄 CSV / TXT fayl<input type="file" id="im_f" accept=".csv,.txt,.tsv,text/plain,text/csv" hidden></label><button class="btn sm ghost" id="im_ex">Namunani qo'yish</button></div>
    <div class="grid g2 stack-sm"><div><label class="f">Kategoriya (ustunda bo'lmasa)</label><select class="inp" id="im_cat">${catOptions(VF.cat || "daily")}</select></div>
    <div><label class="f">Daraja (ustunda bo'lmasa)</label><select class="inp" id="im_lvl"><option value="auto">🪄 Avtomatik (so'z uzunligi bo'yicha)</option>${Object.entries(LEVELS).map(([k, l]) => `<option value="${k}">${l.dot} ${l.name}</option>`).join("")}</select></div></div>
    <label class="row small mt" style="font-weight:700"><input type="checkbox" id="im_auto" checked> Talaffuz va misolni internetdagi lug'atdan to'ldirish (bo'sh bo'lsa)</label>
    <label class="row small" style="font-weight:700"><input type="checkbox" id="im_dup" checked> Lug'atda bor so'zlarni o'tkazib yuborish</label>
    <div id="im_prev" class="mt"></div>
    <div class="row mt2"><button class="btn big" id="im_go" disabled>Import</button><button class="btn ghost" data-close>Bekor</button></div>`);
  bindCatSelect($("#im_cat", m));
  let rows = [];
  const preview = () => {
    rows = parseImport($("#im_t", m).value);
    const dupOn = $("#im_dup", m).checked;
    rows.forEach(r => r.dup = S.words.some(w => norm(w.en) === norm(r.en)) || rows.filter(x => norm(x.en) === norm(r.en)).indexOf(r) > 0);
    const ok = rows.filter(r => r.uz && !(dupOn && r.dup));
    $("#im_prev", m).innerHTML = rows.length ? `<div class="row between small"><b>Ko'rib chiqish: ${ok.length} ta kartaga aylanadi</b><span class="muted">${rows.filter(r => r.dup).length} ta takroriy · ${rows.filter(r => !r.uz).length} ta tarjimasiz</span></div>
      <div class="scroll mt"><table class="tbl"><tr><th>English</th><th>Uzbek</th><th>Misol</th><th></th></tr>${rows.slice(0, 200).map(r => `<tr style="${!r.uz || (dupOn && r.dup) ? "opacity:.45" : ""}"><td><b>${esc(r.en)}</b></td><td>${esc(r.uz || "—")}</td><td class="small">${esc(r.ex || "")}</td><td>${r.dup ? '<span class="tag warn">bor</span>' : !r.uz ? '<span class="tag err">tarjima yo\'q</span>' : '<span class="tag ok">yangi</span>'}</td></tr>`).join("")}</table></div>` : "";
    $("#im_go", m).disabled = !ok.length;
    $("#im_go", m).textContent = ok.length ? `📥 ${ok.length} ta so'zni import qilish` : "Import";
  };
  $("#im_t", m).oninput = preview; $("#im_dup", m).onchange = preview;
  $("#im_ex", m).onclick = () => { $("#im_t", m).value = "English | Uzbek\napple | olma\nbeautiful | chiroyli\nimprove | yaxshilamoq | I want to improve my English.\nkitchen | oshxona\nbrave | jasur\nsuggest | taklif qilmoq"; preview(); };
  $("#im_f", m).onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = () => { $("#im_t", m).value = r.result; preview(); };
    r.readAsText(f);
  };
  $("#im_go", m).onclick = async () => {
    const dupOn = $("#im_dup", m).checked, auto = $("#im_auto", m).checked;
    const defCat = $("#im_cat", m).value === "__new" ? "daily" : $("#im_cat", m).value, defLvl = $("#im_lvl", m).value;
    const ok = rows.filter(r => r.uz && !(dupOn && r.dup));
    const btn = $("#im_go", m); btn.disabled = true;
    const added = [];
    for (const r of ok) {
      const lvl = normLevel(r.level) || (defLvl === "auto" ? guessLevel(r.en) : defLvl);
      const w = newWord({ en: r.en, uz: r.uz, ex: r.ex, pron: r.pron, pos: POS.includes((r.pos || "").toLowerCase()) ? r.pos.toLowerCase() : "", note: r.note, cat: normCatId(r.cat) || defCat, level: lvl });
      S.words.push(w); added.push(w);
    }
    S.records.imported = true;
    save();
    if (auto) {
      const need = added.filter(w => !w.pron || !w.ex).slice(0, 80);
      let n = 0;
      for (const w of need) {
        btn.textContent = `🪄 To'ldirilmoqda ${++n}/${need.length}...`;
        try { const r = await dictLookup(w.en); if (!w.pron) w.pron = r.pron; if (!w.ex) w.ex = r.ex; if (!w.pos && POS.includes(r.pos)) w.pos = r.pos; } catch (e) { if (n === 1 && !navigator.onLine) break; }
      }
      save();
    }
    m.remove();
    checkAchievements();
    celebrate("📥 Import tugadi!", `${added.length} ta yangi so'z kartasi yasaldi`);
    render();
  };
}
function catsDlg() {
  const draw = () => {
    const counts = {}; S.words.forEach(w => counts[w.cat] = (counts[w.cat] || 0) + 1);
    m.querySelector("#cl").innerHTML = allCats().map(c => `<div class="witem" style="cursor:default"><span style="font-size:1.4rem">${c.icon}</span><div class="grow"><b>${esc(c.name)}</b><div class="small muted">${counts[c.id] || 0} ta so'z</div></div>${S.customCats.includes(c) ? `<button class="iconbtn" data-del="${c.id}">🗑️</button>` : '<span class="tag">asosiy</span>'}</div>`).join("");
    $$("[data-del]", m).forEach(b => b.onclick = () => {
      S.customCats = S.customCats.filter(c => c.id !== b.dataset.del);
      S.words.forEach(w => { if (w.cat === b.dataset.del) w.cat = "daily"; });
      save(); draw();
    });
  };
  const m = modal(`<h2>🏷️ Kategoriyalar</h2><div class="row mt nowrap"><input class="inp" id="ce" style="width:64px;text-align:center" value="🏷️"><input class="inp grow" id="cn" placeholder="Yangi kategoriya nomi"><button class="btn" id="ca">Qo'shish</button></div>
    <div class="wlist mt" id="cl"></div><div class="row mt2"><button class="btn" data-close>Tayyor</button></div>`, { onClose: () => render() });
  m.querySelector("#ca").onclick = () => {
    const n = m.querySelector("#cn").value.trim(); if (!n) return;
    const id = normCatId(n); const c = S.customCats.find(c => c.id === id); if (c) c.icon = m.querySelector("#ce").value.trim() || "🏷️";
    m.querySelector("#cn").value = ""; save(); draw();
  };
  draw();
}

/* ================= TAKRORLASH (SRS) ================= */
function practiceKind(w) {
  const r = w.srs.reps, cz = canCloze(w);
  if (w.srs.lapses && r === 0) return pick(cz ? ["cloze_mcq", "mcq_uz_en"] : ["mcq_uz_en", "mcq_en_uz"]);
  if (r <= 1) return pick(cz ? ["cloze_mcq", "mcq_uz_en", "mcq_en_uz"] : ["mcq_uz_en", "mcq_en_uz"]);
  if (r === 2) return pick(cz ? ["type_uz_en", "cloze_type", "listen_meaning"] : ["type_uz_en", "type_en_uz", "listen_meaning"]);
  return pick(cz ? ["cloze_type", "type_uz_en", "listen_identify", "sentence", "listen_word"] : ["type_uz_en", "type_en_uz", "listen_word", "sentence"]);
}
function practiceItems(words) {
  const items = [];
  for (const w of words) {
    if (isNew(w)) { items.push(buildEx("intro", w)); items.push(buildEx("mcq_en_uz", w)); }
    else items.push(buildEx(practiceKind(w), w, { skill: "vocab" }));
  }
  return items;
}
function requeueForgot(ex, items, i) {
  const n = items.filter(x => x.w && x.w.id === ex.w.id).length;
  if (n >= 3) return;
  const at = Math.min(items.length, i + 3 + rnd(3));
  items.splice(at, 0, buildEx(canCloze(ex.w) ? "cloze_mcq" : "mcq_uz_en", ex.w));
}
VIEWS.practice = (v, p) => {
  themeAct();
  const one = p.get("w") && wordById(p.get("w"));
  const start = (words, title) => {
    if (!words.length) { toast("Mashq uchun so'z yo'q"); return; }
    runSession(v, practiceItems(words), { title, requeue: requeueForgot });
    ACT.again = () => render();
  };
  if (one) {
    const items = isNew(one) ? [buildEx("intro", one), buildEx("mcq_en_uz", one)] : [];
    items.push(buildEx(canCloze(one) ? "cloze_mcq" : "mcq_uz_en", one), buildEx("type_uz_en", one), buildEx("sentence", one, { skill: "writing" }));
    runSession(v, items, { title: `«${one.en}» mashqi`, requeue: requeueForgot });
    ACT.again = () => render();
    return;
  }
  const due = dueWords(), fresh = newWordsLeft(), hard = S.words.filter(isDifficult);
  const learning = S.words.filter(w => !isNew(w));
  v.innerHTML = `${topbar("🧠 Takrorlash", "Takrorlash tizimi: har bir so'z o'z vaqtida qaytadi")}
    <div class="card hero"><div style="position:relative;z-index:1"><h2 style="font-size:1.5rem">${due.length + fresh.length ? `Bugun: ${due.length} ta takrorlash + ${fresh.length} ta yangi` : "✨ Bugungi takrorlash tugadi!"}</h2>
      <p class="muted">Har bir so'zdan keyin qanchalik yaxshi eslaganingizni belgilaysiz: 😵 Unutdim → 10 daqiqadan keyin, 😐 Qiyin → ertaga, 🙂 Yaxshi → bir necha kundan keyin, 😎 Oson → ancha keyin.</p>
      <div class="row mt">${due.length + fresh.length ? `<button class="btn white big" data-act="go">▶ Boshlash (${Math.min(due.length, 40) + fresh.length})</button>` : ""}
      ${learning.length ? `<button class="btn big" style="background:rgba(255,255,255,.18)" data-act="free">🔀 Erkin mashq</button>` : ""}</div></div></div>
    <div class="grid g3 mt">
      <button class="tile" data-act="due"><span class="big">🔁</span><b>Faqat takrorlash</b><span class="muted">${due.length} ta so'z vaqti keldi</span></button>
      <button class="tile" data-act="new"><span class="big">🆕</span><b>Yangi so'zlar</b><span class="muted">${fresh.length} ta bugungi reja bo'yicha</span></button>
      <button class="tile" data-act="hard"><span class="big">😵</span><b>Qiyin so'zlar</b><span class="muted">${hard.length} ta ko'p unutilgan</span></button>
    </div>
    <div class="card mt"><h3>📅 Keyingi 7 kun</h3><div class="week" style="height:120px">${[...Array(7)].map((_, i) => {
      const s = new Date(dayKey(Date.now() + i * DAY)).getTime(), e = s + DAY;
      const n = S.words.filter(w => !isNew(w) && (i === 0 ? w.srs.due < e : w.srs.due >= s && w.srs.due < e)).length;
      return { n, i, d: new Date(s) };
    }).map((x, _, arr) => { const mx = Math.max(1, ...arr.map(a => a.n)); return `<div class="col ${x.i === 0 ? "today" : ""}"><em>${x.n}</em><div class="b" style="height:${Math.max(3, x.n / mx * 100)}%"></div><span>${x.i === 0 ? "Bugun" : ["Ya", "Du", "Se", "Ch", "Pa", "Ju", "Sh"][x.d.getDay()]}</span></div>`; }).join("")}</div></div>`;
  ACT.go = () => start([...due.slice(0, 40), ...fresh], "Kunlik takrorlash");
  ACT.due = () => start(due.slice(0, 40), "Takrorlash");
  ACT.new = () => start(fresh.length ? fresh : S.words.filter(isNew).slice(0, 10), "Yangi so'zlar");
  ACT.hard = () => start(shuffle(hard).slice(0, 20), "Qiyin so'zlar");
  ACT.free = () => start(weightedWords(15, learning), "Erkin mashq");
};

/* ================= YOZISH ================= */
const WRITING_KINDS = [
  { k: "cloze_type", i: "🕳️", t: "Bo'sh joyni to'ldirish", s: "Fill in the blank", need: "cloze" },
  { k: "cloze_mcq", i: "☑️", t: "To'g'ri so'zni tanlash", s: "Choose the correct word", need: "cloze" },
  { k: "type_uz_en", i: "🇺🇿→🇬🇧", t: "O'zbekcha → Inglizcha", s: "Translate Uzbek → English" },
  { k: "type_en_uz", i: "🇬🇧→🇺🇿", t: "Inglizcha → O'zbekcha", s: "Translate English → Uzbek" },
  { k: "sentence", i: "✏️", t: "Gap tuzish", s: "Make a sentence" },
  { k: "correct", i: "🩹", t: "Xatoni tuzatish", s: "Correct a sentence", need: "broken" },
  { k: "paragraph", i: "📄", t: "Matnni to'ldirish", s: "Complete a paragraph", need: "para" },
];
function writingItems(kind, n = 8, only) {
  const lvl = adaptLvl("writing");
  const pool = only ? [only] : S.words.slice();
  const items = [];
  const kindsByLvl = { 1: ["cloze_mcq", "cloze_type", "type_en_uz", "cloze_mcq", "sentence"], 2: ["cloze_type", "type_uz_en", "type_en_uz", "sentence", "correct"], 3: ["type_uz_en", "cloze_type", "sentence", "correct", "paragraph"] };
  const ws = only ? Array(n).fill(only) : weightedWords(n * 2, pool);
  let wi = 0;
  for (let j = 0; j < n && wi < ws.length + 5; j++) {
    let k = kind === "mixed" ? pick(kindsByLvl[lvl]) : kind;
    if (k === "paragraph") {
      const pw = shuffle(S.words.filter(canCloze)).slice(0, lvl >= 3 ? 4 : 3);
      if (pw.length >= 3) { items.push(buildEx("paragraph", null, { skill: "writing", words: pw.map(w => ({ w, c: cloze(w) })) })); continue; }
      k = "cloze_type";
    }
    let w = ws[wi++ % ws.length];
    if (!w) break;
    if ((k === "cloze_type" || k === "cloze_mcq") && !canCloze(w)) k = "type_uz_en";
    if (k === "correct" && (!w.ex || !breakSentence(w.ex, w))) k = "sentence";
    items.push(buildEx(k, w, { skill: "writing", lvl }));
  }
  return items;
}
VIEWS.writing = (v, p) => {
  themeAct();
  const one = p.get("w") && wordById(p.get("w"));
  if (!S.words.length) return emptyVocab(v, "✍️ Yozish");
  if (one) {
    const items = [buildEx("sentence", one, { skill: "writing" })];
    if (canCloze(one)) items.unshift(buildEx("cloze_type", one, { skill: "writing" }));
    if (one.ex && breakSentence(one.ex, one)) items.push(buildEx("correct", one, { skill: "writing" }));
    runSession(v, items, { title: `«${one.en}» yozish mashqi` });
    ACT.again = () => render();
    return;
  }
  const lvl = adaptLvl("writing");
  v.innerHTML = `${topbar("✍️ Yozish", "So'zlarni gapda ishlatishni o'rganing — tahlil va xatolar izohi bilan")}
    <div class="card hero"><div style="position:relative;z-index:1"><div class="row between"><h2>Aralash mashq</h2><span class="tag" style="background:rgba(255,255,255,.2);color:#fff">${["", "🟢 Beginner", "🟡 Intermediate", "🔴 Advanced"][lvl]} · avtomatik</span></div>
      <p class="muted">8 ta turli mashq. Qiyinlik natijangizga qarab o'zgaradi.</p>
      <div class="row mt"><button class="btn white big" data-act="mix">▶ Boshlash</button></div>
      <div class="row mt small" style="gap:18px"><span>✍️ Aniqlik: <b>${skillPct("writing")}%</b></span><span>📝 Bugun: <b>${today().writing}/${S.profile.goal.writing}</b></span></div></div></div>
    <h3 class="mt2">Mashq turlari</h3>
    <div class="grid g3 mt">${WRITING_KINDS.map(k => `<button class="tile" data-act="k" data-k="${k.k}"><span class="big">${k.i}</span><b>${k.t}</b><span class="muted">${k.s}</span></button>`).join("")}</div>
    ${S.mistakes.length ? `<div class="card mt2"><h3>🔎 So'nggi xatolaringiz</h3><div class="wlist mt">${S.mistakes.filter(m => m.type === "grammar").slice(0, 5).map(m => `<div class="witem" style="cursor:default;display:block"><div class="diff"><del>${esc(m.wrong)}</del> → <ins>${esc(m.right)}</ins></div><div class="small muted">${esc(m.note)}</div></div>`).join("") || '<p class="small muted">Grammatik xatolar yo\'q — zo\'r!</p>'}</div></div>` : ""}`;
  const go = (k, title) => { runSession(v, writingItems(k), { title }); ACT.again = () => go(k, title); };
  ACT.mix = () => go("mixed", "Yozish mashqi");
  ACT.k = el => { const k = WRITING_KINDS.find(x => x.k === el.dataset.k); go(k.k, k.t); };
};
function emptyVocab(v, title) {
  themeAct();
  v.innerHTML = `${topbar(title)}<div class="card empty"><div class="big">📭</div><h2>Lug'atingiz bo'sh</h2><p>Mashq qilish uchun avval so'z qo'shing yoki ro'yxat import qiling.</p><div class="row mt" style="justify-content:center"><button class="btn" data-go="vocab">📚 Lug'atga o'tish</button></div></div>`;
}

/* ================= GAPIRISH ================= */
const SPEAK_TASKS = [
  { k: "word", i: "💬", t: "So'z bilan gap", s: "Say a sentence using the word" },
  { k: "repeat", i: "🔁", t: "Takrorlang", s: "Pronunciation: repeat after me" },
  { k: "question", i: "❓", t: "Savolga javob", s: "Answer a simple question" },
  { k: "picture", i: "🖼️", t: "Rasmni tasvirlang", s: "Describe a picture / topic" },
  { k: "daily", i: "🏅", t: "Kunlik sinov", s: "Use 3 words in your answer" },
  { k: "role", i: "🎭", t: "Rol o'yini", s: "Role-play conversation" },
];
VIEWS.speaking = (v, p) => {
  themeAct();
  const one = p.get("w") && wordById(p.get("w"));
  if (!S.words.length) return emptyVocab(v, "🎤 Gapirish");
  let kind = p.get("k") || (one ? "word" : "word");
  const draw = () => {
    v.innerHTML = `${topbar("🎤 Gapirish", hasSR ? "Mikrofonni bosing va inglizcha gapiring" : "⚠️ Bu brauzerda nutqni tanish yo'q (Chrome yoki Edge'da ishlaydi) — javobni yozib yuborishingiz mumkin")}
      <div class="seg" id="sk">${SPEAK_TASKS.map(t => `<button data-k="${t.k}" class="${t.k === kind ? "on" : ""}">${t.i} ${t.t}</button>`).join("")}</div>
      <div class="row mt small muted" style="gap:18px"><span>🎤 O'rtacha ball: <b>${skillPct("speaking")}</b></span><span>⏱️ Bugun: <b>${Math.floor(today().speakSec / 60)}/${S.profile.goal.speakMin} daq</b></span></div>
      <div class="ex-wrap mt" id="sbox"></div>`;
    $$("#sk button").forEach(b => b.onclick = () => { kind = b.dataset.k; if (kind === "role") { location.hash = "#/talk?t=" + pick(ROLEPLAYS); return; } draw(); });
    speakTask($("#sbox"), kind, one && kind === "word" ? one : null, () => draw());
  };
  draw();
};
function speakTask(box, kind, word, next) {
  const t0 = Date.now();
  let task = { kind };
  if (kind === "word" || kind === "repeat") task.w = word || weightedWords(1, S.words.filter(w => kind !== "repeat" || w.ex))[0] || S.words[0];
  if (kind === "question") { task.q = pick(SIMPLE_QUESTIONS); task.w = weightedWords(1)[0]; }
  if (kind === "picture") { task.pic = pick(PICTURES); }
  if (kind === "daily") { task.ws = weightedWords(3); }
  let head = "";
  if (kind === "word") head = `<span class="qkind">Say a sentence</span><div class="qtext">«${esc(task.w.en)}» so'zi bilan gap ayting ${speakBtn(task.w.en)}</div><div class="qsub">${esc(task.w.uz)} · ${esc(task.w.pron || "")}</div>${task.w.ex ? `<details class="small mt"><summary class="muted" style="cursor:pointer">💡 Namuna</summary>«${esc(task.w.ex)}» ${speakBtn(task.w.ex)}</details>` : ""}`;
  if (kind === "repeat") { const txt = task.w.ex || task.w.en; task.expected = txt; head = `<span class="qkind">Repeat after me</span><div class="qtext">${esc(txt)}</div><div class="row"><button class="btn ghost sm" data-say="${esc(txt)}">🔊 Tinglash</button><button class="btn ghost sm" id="slow">🐢 Sekin</button></div>`; }
  if (kind === "question") head = `<span class="qkind">Answer the question</span><div class="qtext">${esc(task.q)} ${speakBtn(task.q)}</div><div class="qsub">Kamida 2 ta gap bilan javob bering. Bonus: «${esc(task.w.en)}» so'zini ishlating (${esc(task.w.uz)}).</div>`;
  if (kind === "picture") head = `<span class="qkind">Describe the picture</span><div class="scene">${task.pic.e}</div><div class="qtext center" style="font-size:1.15rem">${esc(task.pic.t)}</div><div class="qsub center">Foydali so'zlar: ${task.pic.hint.map(h => `<span class="tag acc">${esc(h)}</span>`).join(" ")}</div>`;
  if (kind === "daily") head = `<span class="qkind">🏅 Daily speaking challenge</span><div class="qtext">Bu 3 ta so'zni ishlatib, 2–3 gap ayting:</div><div class="row">${task.ws.map(w => `<span class="chip">${esc(w.en)} <span class="muted small">${esc(w.uz)}</span></span>`).join("")}</div>`;
  box.innerHTML = `<div class="qcard">${head}
    ${hasSR ? `<button class="mic" id="mic">🎤</button><div class="center small muted" id="mstat">Bosing va gapiring</div>` : ""}
    <div class="heard mt" id="heard">${hasSR ? "…" : ""}</div>
    <details class="mt" ${hasSR ? "" : "open"}><summary class="small muted" style="cursor:pointer">⌨️ Yozib yuborish</summary><textarea class="inp mt" id="typed" rows="2" placeholder="Aytmoqchi bo'lgan gapingizni yozing..."></textarea><button class="btn ghost sm mt" id="sendt">Tahlil qilish</button></details>
    <div id="res"></div></div>`;
  if (!hasSR) $("#heard", box).classList.add("hide");
  const slow = $("#slow", box); if (slow) slow.onclick = () => speak(task.expected, { rate: 0.65 });
  if (kind === "repeat") setTimeout(() => speak(task.expected), 300);
  const mic = $("#mic", box);
  let recording = false;
  if (mic) mic.onclick = async () => {
    if (recording) { stopListening(); return; }
    recording = true; mic.classList.add("rec"); mic.textContent = "⏹"; $("#mstat", box).textContent = "Tinglayapman... gapirib bo'lgach to'xtaydi";
    speechSynthesis.cancel();
    try {
      const r = await listenOnce({ onInterim: t => $("#heard", box).textContent = t || "…" });
      recording = false; mic.classList.remove("rec"); mic.textContent = "🎤";
      if (!r.text) { $("#mstat", box).textContent = "Hech narsa eshitilmadi. Qayta urinib ko'ring."; return; }
      $("#heard", box).textContent = r.text; $("#mstat", box).textContent = "Qayta gapirish uchun bosing";
      evaluate(r);
    } catch (e) {
      recording = false; mic.classList.remove("rec"); mic.textContent = "🎤";
      $("#mstat", box).textContent = e.message === "not-allowed" ? "🚫 Mikrofonga ruxsat berilmagan" : "Xato: " + e.message + ". Yozib yuborishingiz mumkin.";
    }
  };
  $("#sendt", box).onclick = () => { const t = $("#typed", box).value.trim(); if (t) evaluate({ text: t, conf: 0, sec: 0, typed: true }); };

  function evaluate(r) {
    addTime("speak", Math.min(180, (Date.now() - t0) / 1000));
    let sc, fb = [], better = "";
    if (kind === "repeat") {
      const d = wordDiff(r.text, task.expected);
      const pron = Math.round(d.acc * 100);
      const conf = r.conf ? Math.round(r.conf * 100) : pron;
      const fl = fluencyScore(r, norm(task.expected).split(" ").length);
      sc = { total: Math.round(pron * 0.6 + conf * 0.15 + fl * 0.25), parts: [["Talaffuz", pron], ["Aniqlik", conf], ["Ravonlik", fl]] };
      fb.push(pron >= 90 ? { k: "ok", t: "Excellent pronunciation! 🌟" } : pron >= 70 ? { k: "ok", t: "Good! Bir nechta so'zni aniqroq ayting." } : { k: "bad", t: "Sekinroq va har bir so'zni aniq ayting. 🐢 tugmasi bilan tinglab ko'ring." });
      const missed = d.html.match(/<ins>(.*?)<\/ins>/g);
      if (missed) fb.push({ k: "warn", t: "Tanilmagan so'zlar: " + missed.map(x => x.replace(/<\/?ins>/g, "")).join(", ") });
      $("#res", box).innerHTML = `<div class="diff mt">${d.html}</div>`;
    } else {
      const target = kind === "word" ? task.w.en : null;
      const a = analyzeSentence(r.text, target, { spoken: true });
      let vocab = a.vocab;
      if (kind === "question" && task.w) vocab = clamp(a.vocab - (a.used ? 0 : 0) + (usesWord(r.text, task.w.en) ? 15 : 0), 0, 100);
      if (kind === "daily") {
        const used = task.ws.filter(w => usesWord(r.text, w.en));
        vocab = Math.round(30 + used.length / 3 * 70);
        fb.push(used.length === 3 ? { k: "ok", t: "Uchala so'zni ham ishlatdingiz! 🏅" } : { k: "warn", t: `${used.length}/3 so'z ishlatildi. Yetishmayotgani: ${task.ws.filter(w => !used.includes(w)).map(w => w.en).join(", ")}` });
        if (used.length === 3) progressChallenge("speak3", 3, 3);
      }
      if (kind === "picture") {
        const used = task.pic.hint.filter(h => usesWord(r.text, h));
        vocab = clamp(a.vocab + used.length * 8, 0, 100);
        if (used.length) fb.push({ k: "ok", t: `Foydali so'zlar ishlatildi: ${used.join(", ")}` });
      }
      if (kind === "word" && a.used) progressChallenge("speak3", 1, 3);
      const pron = r.typed ? null : r.conf ? clamp(Math.round(r.conf * 100 + 5), 40, 100) : 78;
      const fl = r.typed ? null : fluencyScore(r, a.words);
      const parts = [["Grammatika", a.grammar], ["Lug'at", vocab], ["Tuzilish", a.structure]];
      if (!r.typed) parts.push(["Talaffuz", pron], ["Ravonlik", fl]);
      const total = r.typed ? Math.round(a.grammar * 0.4 + vocab * 0.35 + a.structure * 0.25) : Math.round(a.grammar * 0.25 + vocab * 0.2 + a.structure * 0.15 + pron * 0.2 + fl * 0.2);
      sc = { total, parts };
      fb = a.feedback.filter(f => f.k !== "tip").concat(fb);
      if (kind === "question" && a.words < 8) fb.push({ k: "tip", t: "Javobni kengaytiring: «because...», «for example...» qo'shing." });
      if (!r.typed && fl < 60) fb.push({ k: "tip", t: "Ravonlik: pauzalarni kamaytiring, gapni bir nafasda ayting." });
      a.issues.filter(i => !i.minor).forEach(i => logMistake("grammar", i.wrong, i.right, i.why));
      better = a.fixed !== a.raw && a.issues.some(i => !i.minor) ? a.fixed : "";
    }
    recordSkill("speaking", sc.total >= 60, sc.total);
    addXp(Math.round(5 + sc.total / 10));
    const c = sc.total >= 80 ? "var(--ok)" : sc.total >= 60 ? "var(--accent)" : "var(--warn)";
    $("#res", box).innerHTML = ($("#res", box).innerHTML || "") + `<div class="mt2"><div class="scorering" style="--p:${sc.total};--c:${c}"><b>${sc.total}</b></div>
      <div class="center mt"><b>${sc.total >= 85 ? "Excellent! 🌟" : sc.total >= 70 ? "Good job! 👏" : sc.total >= 50 ? "Not bad! 👍" : "Keep practicing! 💪"}</b></div>
      <div class="subscores">${sc.parts.map(([n, x]) => `<div><b>${x}</b><span>${n}</span></div>`).join("")}</div>
      ${fbList(fb)}${better ? `<div class="fb ok mt">🗣️ Try saying: <span class="ans">${esc(better)}</span> ${speakBtn(better)}</div>` : ""}
      ${aiCheckBtn(r.text, task.w)}
      ${task.w && (kind === "word" || kind === "repeat") ? rateHtml(task.w, sc.total >= 85 ? 2 : sc.total >= 60 ? 1 : 0) : ""}
      <div class="row mt" style="justify-content:flex-end"><button class="btn big" id="nx">Keyingisi →</button></div></div>`;
    bindAiCheck(box, r.text, task.w);
    $$(".rbtns button", box).forEach(b => b.onclick = () => { rateWord(task.w.id, +b.dataset.g); next(); });
    $("#nx", box).onclick = next;
    $("#res", box).scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}
function fluencyScore(r, nWords) {
  if (!r.sec || !nWords) return 70;
  const wps = nWords / r.sec;
  let s = wps >= 1.6 && wps <= 3.4 ? 100 : wps >= 1.1 ? 82 : wps >= 0.7 ? 65 : 45;
  if (nWords < 4) s -= 15;
  return clamp(Math.round(s), 0, 100);
}

/* ================= TINGLASH ================= */
function listeningItems(n = 8) {
  const lvl = adaptLvl("listening");
  const kinds = { 1: ["listen_meaning", "listen_word", "listen_identify"], 2: ["listen_missing", "listen_translate", "listen_word", "listen_identify"], 3: ["listen_sentence", "listen_missing", "listen_translate", "listen_sentence"] }[lvl];
  return weightedWords(n).map(w => {
    let k = pick(kinds);
    if (["listen_identify", "listen_missing", "listen_sentence"].includes(k) && !canCloze(w)) k = lvl >= 2 ? "listen_word" : "listen_meaning";
    return buildEx(k, w, { skill: "listening", lvl });
  });
}
VIEWS.listening = (v) => {
  themeAct();
  if (!S.words.length) return emptyVocab(v, "🎧 Tinglash");
  const lvl = adaptLvl("listening");
  v.innerHTML = `${topbar("🎧 Tinglash", "Lug'atingizdagi so'zlar bilan tinglab tushunish mashqlari")}
    <div class="card hero"><div style="position:relative;z-index:1"><div class="row between"><h2>Tinglash mashqi</h2><span class="tag" style="background:rgba(255,255,255,.2);color:#fff">${["", "🟢 Beginner", "🟡 Intermediate", "🔴 Advanced"][lvl]}</span></div>
      <p class="muted">${lvl === 1 ? "So'zlarni eshitib, ma'nosini toping." : lvl === 2 ? "Gaplarni eshitib, tushib qolgan so'zni toping va tarjima qiling." : "To'liq gaplar diktanti — tezroq nutq bilan."} Natijangiz yaxshilansa, qiyinlik o'zi oshadi.</p>
      <div class="row mt"><button class="btn white big" data-act="go">▶ Boshlash (8 ta)</button></div>
      <div class="row mt small" style="gap:18px"><span>🎧 Aniqlik: <b>${skillPct("listening")}%</b></span><span>⏱️ Bugun: <b>${Math.floor(today().listenSec / 60)}/${S.profile.goal.listenMin} daq</b></span></div></div></div>
    <div class="grid g3 mt">
      ${[["listen_meaning", "🔤", "Ma'nosini tanlash", "Listen → choose meaning"], ["listen_word", "⌨️", "Eshitganini yozish", "Type what you hear"], ["listen_missing", "🕳️", "Tushib qolgan so'z", "Choose the missing word"],
         ["listen_identify", "🔎", "So'zni aniqlash", "Identify the word"], ["listen_translate", "🌐", "Tarjima qilish", "Listen and translate"], ["listen_sentence", "📝", "Diktant", "Full sentence dictation"]]
        .map(([k, i, t, s]) => `<button class="tile" data-act="k" data-k="${k}"><span class="big">${i}</span><b>${t}</b><span class="muted">${s}</span></button>`).join("")}
    </div>
    ${"speechSynthesis" in window ? "" : `<div class="card mt fb bad">⚠️ Bu brauzer ovozli o'qishni qo'llamaydi.</div>`}`;
  const go = items => { runSession(v, items, { title: "Tinglash" }); ACT.again = () => render(); };
  ACT.go = () => go(listeningItems());
  ACT.k = el => {
    const k = el.dataset.k, lv = adaptLvl("listening");
    const needCz = ["listen_identify", "listen_missing", "listen_sentence"].includes(k);
    const pool = needCz ? S.words.filter(canCloze) : S.words;
    if (!pool.length) { toast("Buning uchun misol gapli so'zlar kerak"); return; }
    go(weightedWords(8, pool).map(w => buildEx(k, w, { skill: "listening", lvl: lv })));
  };
};

/* ================= NATIJALAR ================= */
VIEWS.progress = (v) => {
  themeAct();
  const L = levelInfo();
  const st = { new: 0, learning: 0, young: 0, mastered: 0 };
  S.words.forEach(w => st[stageOf(w).k]++);
  const tot = Math.max(1, S.words.length);
  const days = [...Array(45)].map((_, i) => { const k = dayKey(Date.now() - (44 - i) * DAY); return { k, d: S.days[k] || {} }; });
  const lv = x => !x ? "" : x < 30 ? "l1" : x < 80 ? "l2" : x < 150 ? "l3" : "l4";
  const hard = S.words.filter(isDifficult).sort((a, b) => b.srs.lapses - a.srs.lapses).slice(0, 8);
  const mis = {}; S.mistakes.filter(m => m.type === "grammar").forEach(m => { mis[m.note] = (mis[m.note] || 0) + 1; });
  const misTop = Object.entries(mis).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const totAns = Object.values(S.days).reduce((a, d) => a + (d.total || 0), 0), totOk = Object.values(S.days).reduce((a, d) => a + (d.correct || 0), 0);
  v.innerHTML = `${topbar("📊 Natijalar", "Sizning o'sishingiz")}
    <div class="grid g2 stack-sm">
      <div class="card hero"><div style="position:relative;z-index:1"><div class="small muted" style="font-weight:800">DARAJA</div><h2 style="font-size:2rem">⭐ ${L.lvl} · ${L.name}</h2><p class="muted">${L.into} / ${L.need} XP — keyingi darajagacha ${L.need - L.into} XP</p><div class="bar mt" style="background:rgba(255,255,255,.25)"><i style="width:${L.into / L.need * 100}%;background:#fff"></i></div>
        <div class="row mt small" style="gap:18px"><span>🔥 Seriya: <b>${streakNow()}</b></span><span>🏆 Eng uzun: <b>${S.profile.bestStreak}</b></span><span>🎯 Maqsad bajarilgan kunlar: <b>${S.records.goalsDone}</b></span></div></div></div>
      <div class="card"><h3>🧩 Ko'nikmalar</h3><div class="row mt" style="justify-content:space-around">
        ${[["🎤", "Speaking", "speaking", "var(--pink)"], ["✍️", "Writing", "writing", "var(--ok)"], ["🎧", "Listening", "listening", "var(--sky)"], ["🧠", "Vocab", "vocab", "var(--warn)"]].map(([i, n, k, c]) => `<div class="center">${ring(skillPct(k), skillPct(k) + "%", c)}<div class="small mt" style="font-weight:800">${i} ${n}</div></div>`).join("")}</div>
        <p class="small muted mt">Jami javoblar: ${totAns} · to'g'ri: ${totAns ? Math.round(totOk / totAns * 100) : 0}%</p></div>
    </div>
    <div class="card mt"><div class="row between"><h3>📚 So'zlar holati</h3><span class="small muted">${S.words.length} ta so'z</span></div>
      <div class="stackbar mt"><i style="width:${st.new / tot * 100}%;background:var(--faint)"></i><i style="width:${st.learning / tot * 100}%;background:var(--warn)"></i><i style="width:${st.young / tot * 100}%;background:var(--accent)"></i><i style="width:${st.mastered / tot * 100}%;background:var(--ok)"></i></div>
      <div class="legend"><span style="--c:var(--faint)">Yangi ${st.new}</span><span style="--c:var(--warn)">O'rganilmoqda ${st.learning}</span><span style="--c:var(--accent)">Mustahkamlanmoqda ${st.young}</span><span style="--c:var(--ok)">Yodlangan ${st.mastered}</span></div></div>
    <div class="grid g2 stack-sm mt">
      <div class="card"><h3>🗓️ Faollik (45 kun)</h3><div class="heat mt">${days.map(x => `<i class="${lv(x.d.xp)}" title="${x.k}: ${x.d.xp || 0} XP${x.d.done ? " ✅" : ""}"></i>`).join("")}</div><div class="small muted mt">Har bir katak — bir kun. Rang qancha to'q bo'lsa, shuncha ko'p XP.</div></div>
      <div class="card"><h3>🏅 Shaxsiy rekordlar</h3><div class="grid g2 mt">
        <div class="stat"><div class="l">⚡ Tezlik sinovi</div><div class="v">${S.records.bestSpeed}</div></div>
        <div class="stat"><div class="l">💬 Suhbatlar</div><div class="v">${S.records.convos}</div></div>
        <div class="stat"><div class="l">📅 Haftalik XP</div><div class="v">${weekXp()}</div></div>
        <div class="stat"><div class="l">⭐ Jami XP</div><div class="v">${S.profile.xp}</div></div></div></div>
    </div>
    <div class="grid g2 stack-sm mt">
      <div class="card"><div class="row between"><h3>😵 Qiyin so'zlar</h3>${hard.length ? `<button class="btn sm" data-act="hard">Mashq qilish</button>` : ""}</div>
        <div class="wlist mt">${hard.map(w => `<div class="witem" data-w="${w.id}"><div class="grow"><b>${esc(w.en)}</b> <span class="muted small">${esc(w.uz)}</span></div><span class="tag err">${w.srs.lapses}× unutilgan</span></div>`).join("") || '<p class="small muted">Hozircha qiyin so\'zlar yo\'q 🎉</p>'}</div></div>
      <div class="card"><h3>🔎 Ko'p uchraydigan xatolar</h3>
        <div class="wlist mt">${misTop.map(([n, c]) => `<div class="witem" style="cursor:default"><div class="grow small" style="font-weight:700">${esc(n)}</div><span class="tag warn">${c}×</span></div>`).join("") || '<p class="small muted">Grammatik xatolar hali qayd etilmagan.</p>'}</div></div>
    </div>
    <div class="card mt"><h3>🏆 Yutuqlar · ${Object.keys(S.achievements).length}/${ACHIEVEMENTS.length}</h3>
      <div class="ach mt">${ACHIEVEMENTS.map(a => `<div class="${S.achievements[a.id] ? "" : "lock"}"><div class="i">${a.icon}</div><b>${a.name}</b><small>${a.uz}</small></div>`).join("")}</div></div>`;
  $$("[data-w]", v).forEach(el => el.onclick = () => openWord(wordById(el.dataset.w), () => render()));
  ACT.hard = () => { runSession(v, practiceItems(shuffle(S.words.filter(isDifficult)).slice(0, 15)), { title: "Qiyin so'zlar", requeue: requeueForgot }); ACT.again = () => render(); };
};

/* ================= SOZLAMALAR ================= */
VIEWS.settings = (v) => {
  themeAct();
  const P = S.profile, g = P.goal;
  const num = (id, val, min, max) => `<input class="inp" type="number" id="${id}" value="${val}" min="${min}" max="${max}">`;
  v.innerHTML = `${topbar("⚙️ Sozlamalar")}
    <div class="grid g2 stack-sm">
      <div class="card"><h3>👤 Profil</h3>
        <label class="f">Ismingiz</label><input class="inp" id="s_name" value="${esc(P.name)}" placeholder="Ism">
        <label class="f">Daraja</label><div class="grid g3" id="s_lvl">${Object.entries(LEVELS).map(([k, l]) => `<button class="tile" data-l="${k}" style="padding:12px;align-items:center;${P.level === k ? "border-color:var(--accent);background:var(--accent-soft)" : ""}"><span style="font-size:1.4rem">${l.dot}</span><b class="small">${l.name}</b></button>`).join("")}</div>
        <p class="small muted mt">Daraja mashqlarning boshlang'ich qiyinligini belgilaydi. Keyin dastur natijangizga qarab o'zi moslashadi.</p>
        <label class="f">Mavzu</label><div class="seg" id="s_theme">${[["auto", "🖥️ Avto"], ["light", "☀️ Yorug'"], ["dark", "🌙 Qorong'i"]].map(([k, t]) => `<button data-t="${k}" class="${P.theme === k ? "on" : ""}">${t}</button>`).join("")}</div>
      </div>
      <div class="card"><h3>🎯 Kunlik maqsad</h3>
        <div class="grid g2"><div><label class="f">🆕 Yangi so'zlar</label>${num("g_new", g.new, 0, 100)}</div><div><label class="f">🔁 Takrorlash</label>${num("g_review", g.review, 0, 300)}</div>
        <div><label class="f">🎤 Gapirish (daq)</label>${num("g_speak", g.speakMin, 0, 60)}</div><div><label class="f">🎧 Tinglash (daq)</label>${num("g_listen", g.listenMin, 0, 60)}</div>
        <div><label class="f">✍️ Yozish mashqlari</label>${num("g_write", g.writing, 0, 100)}</div><div><label class="f">📅 Haftalik XP</label>${num("g_week", P.weeklyXp, 100, 20000)}</div></div>
        <p class="small muted mt">Seriya 🔥 kunlik maqsad to'liq bajarilgan kunlar bilan davom etadi.</p></div>
      <div class="card"><h3>🔊 Ovoz</h3>
        <label class="f">Ovoz</label><select class="inp" id="s_voice"><option value="">Avtomatik</option>${VOICES.map(x => `<option ${P.voice === x.name ? "selected" : ""}>${esc(x.name)}</option>`).join("")}</select>
        <label class="f">Tezlik: <span id="rv">${P.rate}</span></label><input type="range" id="s_rate" min="0.6" max="1.3" step="0.05" value="${P.rate}" style="width:100%">
        <button class="btn ghost sm mt" data-say="Hello! I want to improve my English every day.">🔊 Sinab ko'rish</button>
        <p class="small muted mt">🎤 Nutqni tanish: ${hasSR ? "✅ mavjud" : "❌ bu brauzerda yo'q (Chrome/Edge tavsiya etiladi)"}</p></div>
      <div class="card"><h3>🤖 AI Ustoz (ixtiyoriy)</h3>
        <p class="small muted">Kalitsiz ham AI Ustoz va Suhbat oflayn rejimda ishlaydi. Haqiqiy suhbat va chuqur tahlil uchun Anthropic API kalitini kiriting — u faqat shu brauzerda saqlanadi va to'g'ridan-to'g'ri api.anthropic.com ga yuboriladi.</p>
        <label class="f">API kalit</label><input class="inp" id="s_key" type="password" value="${esc(P.apiKey)}" placeholder="sk-ant-..." autocomplete="off">
        <label class="f">Model</label><select class="inp" id="s_model">${[["claude-opus-5", "Claude Opus 5 (eng aqlli)"], ["claude-sonnet-5", "Claude Sonnet 5 (tez, arzonroq)"], ["claude-haiku-4-5", "Claude Haiku 4.5 (eng tez)"]].map(([k, t]) => `<option value="${k}" ${P.model === k ? "selected" : ""}>${t}</option>`).join("")}</select>
        <button class="btn ghost sm mt" id="s_test">🔌 Ulanishni tekshirish</button></div>
    </div>
    <div class="card mt"><h3>💾 Ma'lumotlar</h3><p class="small muted">Hamma narsa shu qurilmadagi brauzer xotirasida saqlanadi. Boshqa qurilmaga o'tish uchun zaxira nusxa oling.</p>
      <div class="row mt"><button class="btn ghost" data-act="backup">📤 Zaxira nusxa (JSON)</button><label class="btn ghost" style="cursor:pointer">📥 Zaxiradan tiklash<input type="file" id="s_restore" accept=".json,application/json" hidden></label>
      <button class="btn ghost" data-act="seed">🌱 Namuna so'zlarni qo'shish</button><button class="btn ghost" data-act="resetp" style="color:var(--err)">♻️ Natijalarni tozalash</button><button class="btn ghost" data-act="wipe" style="color:var(--err)">🗑️ Hammasini o'chirish</button></div></div>
    <p class="center small muted mt2">Lug'at · English vocabulary trainer</p>`;
  const num2 = id => Math.max(0, parseInt($("#" + id).value) || 0);
  $("#s_name").onchange = e => { P.name = e.target.value.trim(); save(); };
  $$("#s_lvl [data-l]").forEach(b => b.onclick = () => { P.level = b.dataset.l; S.adapt = {}; save(); toast("Daraja: " + LEVELS[P.level].name); render(); });
  $$("#s_theme button").forEach(b => b.onclick = () => { P.theme = b.dataset.t; save(); applyTheme(); render(); });
  ["g_new", "g_review", "g_speak", "g_listen", "g_write", "g_week"].forEach(id => $("#" + id).onchange = () => {
    g.new = num2("g_new"); g.review = num2("g_review"); g.speakMin = num2("g_speak"); g.listenMin = num2("g_listen"); g.writing = num2("g_write"); P.weeklyXp = Math.max(100, num2("g_week"));
    save(); toast("✅ Maqsad saqlandi"); checkGoal();
  });
  $("#s_voice").onchange = e => { P.voice = e.target.value; save(); };
  $("#s_rate").oninput = e => { P.rate = +e.target.value; $("#rv").textContent = P.rate; save(); };
  $("#s_key").onchange = e => { P.apiKey = e.target.value.trim(); save(); toast(P.apiKey ? "🔑 Kalit saqlandi" : "Kalit o'chirildi"); };
  $("#s_model").onchange = e => { P.model = e.target.value; save(); };
  $("#s_test").onclick = async e => {
    P.apiKey = $("#s_key").value.trim(); save();
    if (!P.apiKey) { toast("Avval kalitni kiriting"); return; }
    e.target.textContent = "⏳ ...";
    try { const t = await askClaude("Reply with exactly: OK", [{ role: "user", content: "ping" }], 50); toast("✅ Ulandi: " + t.slice(0, 30)); }
    catch (err) { toast("❌ " + err.message, 4000); }
    e.target.textContent = "🔌 Ulanishni tekshirish";
  };
  ACT.backup = () => download(`lugat-zaxira-${dayKey()}.json`, JSON.stringify({ ...S, profile: { ...S.profile, apiKey: "" } }, null, 1));
  $("#s_restore").onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const r = new FileReader();
    r.onload = async () => {
      try {
        const d = JSON.parse(r.result);
        if (!Array.isArray(d.words)) throw new Error("format");
        if (!await confirmDlg(`${d.words.length} ta so'zli zaxira tiklansinmi? Joriy ma'lumotlar almashtiriladi.`, "Tiklash")) return;
        const key = S.profile.apiKey;
        localStorage.setItem(KEY, JSON.stringify(d)); S = load(); S.profile.apiKey = S.profile.apiKey || key; save();
        toast("✅ Tiklandi"); applyTheme(); render();
      } catch (err) { toast("❌ Fayl noto'g'ri"); }
    };
    r.readAsText(f);
  };
  ACT.seed = () => { const n = seedWords(); toast(n ? `🌱 ${n} ta so'z qo'shildi` : "Namuna so'zlar allaqachon bor"); };
  ACT.resetp = async () => {
    if (!await confirmDlg("Barcha natijalar (XP, seriya, takrorlash tarixi) tozalansinmi? So'zlar qoladi.", "Tozalash")) return;
    const base = DEFAULT_STATE();
    S.words.forEach(w => w.srs = newWord({}).srs);
    Object.assign(S, { days: {}, skills: base.skills, adapt: {}, achievements: {}, mistakes: [], records: base.records, challenges: {} });
    Object.assign(S.profile, { xp: 0, streak: 0, bestStreak: 0, lastGoalDay: null });
    save(); toast("♻️ Tozalandi"); render();
  };
  ACT.wipe = async () => {
    if (!await confirmDlg("Hamma so'zlar va natijalar butunlay o'chirilsinmi?", "Hammasini o'chirish")) return;
    const key = S.profile.apiKey;
    S = DEFAULT_STATE(); S.profile.onboarded = true; S.profile.seeded = true; S.profile.apiKey = key; save(); render();
  };
};
function seedWords() {
  let n = 0;
  for (const s of SEED) if (!S.words.some(w => norm(w.en) === norm(s.en))) { S.words.push(newWord(s)); n++; }
  S.profile.seeded = true; save();
  return n;
}

/* ================= ishga tushirish ================= */
function onboarding() {
  let lvl = "beginner";
  const m = modal(`<div class="center"><div class="logo" style="width:70px;height:70px;font-size:34px;margin:0 auto;border-radius:22px">A</div>
    <h2 class="mt" style="font-size:1.6rem">Xush kelibsiz! 👋</h2><p class="muted">Bu dastur inglizcha so'zlarni <b>uzoq muddat</b> eslab qolishga yordam beradi: takrorlash tizimi, o'yinlar, yozish, gapirish va tinglash.</p></div>
    <label class="f">Ismingiz (ixtiyoriy)</label><input class="inp" id="o_name" placeholder="Ism">
    <label class="f">Ingliz tili darajangiz</label><div class="grid g3" id="o_lvl">${Object.entries(LEVELS).map(([k, l]) => `<button class="tile" data-l="${k}" style="padding:12px;align-items:center;${k === lvl ? "border-color:var(--accent);background:var(--accent-soft)" : ""}"><span style="font-size:1.5rem">${l.dot}</span><b class="small">${l.name}</b><span class="tiny muted">${l.uz}</span></button>`).join("")}</div>
    <div class="grid g2 stack-sm mt2"><button class="btn big grad" id="o_seed">🌱 ${SEED.length} ta namuna so'z bilan boshlash</button><button class="btn big ghost" id="o_empty">📭 Bo'sh lug'at</button></div>`);
  $$("#o_lvl [data-l]", m).forEach(b => b.onclick = () => { lvl = b.dataset.l; $$("#o_lvl [data-l]", m).forEach(x => x.style.cssText = "padding:12px;align-items:center;" + (x === b ? "border-color:var(--accent);background:var(--accent-soft)" : "")); });
  const done = seed => {
    S.profile.name = $("#o_name", m).value.trim(); S.profile.level = lvl; S.profile.onboarded = true;
    if (seed) seedWords(); else { S.profile.seeded = true; save(); }
    m.remove(); render();
    if (!seed) location.hash = "#/vocab";
  };
  $("#o_seed", m).onclick = () => done(true);
  $("#o_empty", m).onclick = () => done(false);
}
function boot() {
  applyTheme();
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => S.profile.theme === "auto" && render());
  render();
  if (!S.profile.onboarded) onboarding();
  // yarim tunda kun almashsa, sahifani yangilash
  let lastDay = dayKey();
  setInterval(() => { if (dayKey() !== lastDay) { lastDay = dayKey(); if (route().r === "home") render(); } }, 60000);
}

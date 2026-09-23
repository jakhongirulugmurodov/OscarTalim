// 8 ta o'yin: kartochkalar, juftlash, test, so'z yig'ish, tushib qolgan so'z, tezlik, xotira, gap tuzish.
"use strict";

const GAMES = [
  { k: "flash", i: "🃏", t: "Kartochkalar", s: "Flashcards — eslang va tekshiring" },
  { k: "match", i: "🧩", t: "Juftlash", s: "Matching — so'z va tarjimani ulang" },
  { k: "mcq", i: "🔤", t: "Test", s: "Multiple choice — 4 variantdan biri" },
  { k: "build", i: "🧱", t: "So'z yig'ish", s: "Word builder — harflardan so'z" },
  { k: "missing", i: "🕳️", t: "Tushib qolgan so'z", s: "Missing word — gapni to'ldiring" },
  { k: "speed", i: "⚡", t: "Tezlik sinovi", s: "60 soniyada iloji boricha ko'p" },
  { k: "memory", i: "🧠", t: "Xotira o'yini", s: "Memory — yashirin juftlarni toping" },
  { k: "sentence", i: "✏️", t: "Gap sinovi", s: "Sentence challenge — o'z gapingiz" },
];

VIEWS.games = (v, p) => {
  themeAct();
  if (S.words.length < 4) {
    v.innerHTML = `${topbar("🎮 O'yinlar")}<div class="card empty"><div class="big">🎮</div><h2>Kamida 4 ta so'z kerak</h2><p>O'yinlar lug'atingizdagi so'zlardan tuziladi.</p><button class="btn mt" data-go="vocab">📚 So'z qo'shish</button></div>`;
    return;
  }
  const g = p.get("g");
  if (g && GAME_FN[g]) { GAME_FN[g](v); return; }
  v.innerHTML = `${topbar("🎮 O'yinlar", "O'ynang, XP to'plang — so'zlar esa xotirada qoladi")}
    <div class="card hero"><div style="position:relative;z-index:1"><div class="row between"><div><div class="small muted" style="font-weight:800">KUNLIK SINOV</div><h2 style="margin-top:4px">${todayChallenge().t}</h2></div><span class="tag" style="background:rgba(255,255,255,.2);color:#fff">${challengeDone() ? "✅ Bajarildi" : "+" + todayChallenge().xp + " XP"}</span></div>
      <p class="muted">⚡ Tezlik rekordi: <b style="color:#fff">${S.records.bestSpeed}</b> ta to'g'ri javob</p></div></div>
    <div class="grid g4 mt">${GAMES.map(x => `<button class="tile" data-act="g" data-k="${x.k}"><span class="big">${x.i}</span><b>${x.t}</b><span class="muted">${x.s}</span></button>`).join("")}</div>`;
  ACT.g = el => { location.hash = "#/games?g=" + el.dataset.k; };
};

function gameHead(title, right = "") {
  return `<div class="qhead"><button class="iconbtn" data-go="games" title="O'yinlar">✕</button><b class="grow">${title}</b>${right}</div>`;
}
// O'yin oxirida so'zlarni baholash (takrorlash tizimi uchun)
function rateSummary(v, results, { title, emoji = "🎉", stats = "", again }) {
  const uniq = new Map();
  results.forEach(r => { const o = uniq.get(r.w.id); if (!o || r.sug < o.sug) uniq.set(r.w.id, r); });
  const list = [...uniq.values()];
  const sel = {}; list.forEach(r => sel[r.w.id] = r.sug);
  v.innerHTML = `<div class="ex-wrap"><div class="qcard"><div class="center"><div style="font-size:3.4rem">${emoji}</div><h2>${esc(title)}</h2></div>${stats}
    <div class="rate"><b>Har bir so'zni qanchalik yaxshi eslaganingizni belgilang</b><div class="small muted">Taklif o'yindagi natijangizdan olindi — o'zgartirishingiz mumkin.</div>
    <div class="wlist mt">${list.map(r => `<div class="witem" style="cursor:default;flex-wrap:wrap"><div class="grow"><b>${esc(r.w.en)}</b> <span class="small muted">${esc(r.w.uz)}</span></div>
      <div class="seg" data-wid="${r.w.id}">${GRADES.map(g => `<button data-g="${g.g}" class="${g.g === r.sug ? "on" : ""}" title="${g.t}">${g.e}</button>`).join("")}</div></div>`).join("")}</div></div>
    <div class="row mt2" style="justify-content:center"><button class="btn big" id="saveR">💾 Saqlash</button><button class="btn ghost big" id="againG">🔁 Yana o'ynash</button></div></div></div>`;
  $$("[data-wid]", v).forEach(seg => $$("button", seg).forEach(b => b.onclick = () => { sel[seg.dataset.wid] = +b.dataset.g; $$("button", seg).forEach(x => x.classList.toggle("on", x === b)); }));
  let saved = false;
  const doSave = () => { if (saved) return; saved = true; Object.entries(sel).forEach(([id, g]) => rateWord(id, g)); toast("✅ Takrorlash jadvali yangilandi"); };
  $("#saveR", v).onclick = () => { doSave(); go("games"); };
  $("#againG", v).onclick = () => { doSave(); again(); };
  onLeave(() => { if (!saved && list.length) doSave(); });
}
function statsRow(items) { return `<div class="grid g3 mt">${items.map(([v, l, c]) => `<div class="stat center"><div class="v" ${c ? `style="color:${c}"` : ""}>${v}</div><div class="l">${l}</div></div>`).join("")}</div>`; }

const GAME_FN = {};

/* ---------- 1. Kartochkalar ---------- */
GAME_FN.flash = v => {
  const deck = weightedWords(12);
  let i = 0, dir = "en", flipped = false;
  const draw = () => {
    if (i >= deck.length) { addXp(10); v.innerHTML = `<div class="ex-wrap"><div class="qcard center"><div style="font-size:3.4rem">🃏</div><h2>Kartochkalar tugadi!</h2><p class="muted">${deck.length} ta so'z takrorlandi · +10 XP bonus</p><div class="row mt2" style="justify-content:center"><button class="btn big" data-act="again">🔁 Yana</button><button class="btn ghost big" data-go="games">🎮 O'yinlar</button></div></div></div>`; ACT.again = () => GAME_FN.flash(v); return; }
    const w = deck[i]; flipped = false;
    const front = dir === "en" ? `<div class="w">${esc(w.en)}</div><div style="opacity:.85;margin-top:6px">${esc(w.pron || "")}</div>` : `<div class="w" style="font-size:1.9rem">${esc(w.uz)}</div>`;
    const back = `<div class="w" style="font-size:2rem;color:var(--accent)">${esc(dir === "en" ? w.uz : w.en)}</div><div class="muted">${esc(dir === "en" ? w.en : w.pron || "")}</div>${w.ex ? `<div class="small mt" style="font-style:italic">«${esc(w.ex)}»</div>` : ""}`;
    v.innerHTML = `<div class="ex-wrap">${gameHead("🃏 Kartochkalar", `<div class="seg"><button data-d="en" class="${dir === "en" ? "on" : ""}">EN→UZ</button><button data-d="uz" class="${dir === "uz" ? "on" : ""}">UZ→EN</button></div>`)}
      ${bar(i / deck.length * 100)}<p class="small muted center">${i + 1} / ${deck.length} · Kartani bosing yoki <span class="kbd">Space</span></p>
      <div class="flash mt" id="fc"><div class="in"><div class="face front">${front}<div class="small mt" style="opacity:.8">🤔 Tarjimasini eslang...</div></div><div class="face back">${back}</div></div></div>
      <div id="fr" class="mt"></div></div>`;
    $$("[data-d]", v).forEach(b => b.onclick = () => { dir = b.dataset.d; draw(); });
    if (dir === "en") setTimeout(() => speak(w.en), 250);
    const flip = () => {
      $("#fc", v).classList.toggle("flip"); if (flipped) return; flipped = true;
      if (dir === "uz") speak(w.en);
      $("#fr", v).innerHTML = rateHtml(w, 2);
      $$(".rbtns button", v).forEach(b => b.onclick = () => rate(+b.dataset.g));
    };
    const rate = g => { rateWord(w.id, g); recordSkill("vocab", g >= 1); i++; draw(); };
    $("#fc", v).onclick = flip;
    KEYH = e => { if (e.key === " ") { e.preventDefault(); flip(); } else if (flipped && /^[1-4]$/.test(e.key)) rate(+e.key - 1); };
  };
  draw();
};

/* ---------- 2. Juftlash ---------- */
GAME_FN.match = v => {
  const ws = weightedWords(6);
  let left = null, right = null, mistakes = 0, done = 0;
  const bad = {};
  const t0 = Date.now();
  const L = shuffle(ws), R = shuffle(ws);
  v.innerHTML = `<div class="ex-wrap">${gameHead("🧩 Juftlash", `<span class="chip" id="mt">⏱ 0s</span>`)}
    <p class="small muted">Inglizcha so'zni va uning tarjimasini tanlang.</p>
    <div class="match mt"><div class="grid" style="gap:10px">${L.map(w => `<button class="mbtn" data-l="${w.id}">${esc(w.en)}</button>`).join("")}</div>
    <div class="grid" style="gap:10px">${R.map(w => `<button class="mbtn" data-r="${w.id}">${esc(w.uz)}</button>`).join("")}</div></div></div>`;
  const tick = setInterval(() => { const el = $("#mt", v); if (el) el.textContent = `⏱ ${Math.round((Date.now() - t0) / 1000)}s`; }, 500);
  onLeave(() => clearInterval(tick));
  const check = () => {
    if (!left || !right) return;
    const lb = $(`[data-l="${left}"]`, v), rb = $(`[data-r="${right}"]`, v);
    if (left === right) {
      lb.classList.add("done"); rb.classList.add("done"); lb.classList.remove("sel"); rb.classList.remove("sel");
      speak(wordById(left).en); done++; recordSkill("vocab", true);
      if (done === ws.length) finish();
    } else {
      mistakes++; bad[left] = 1; bad[right] = 1; recordSkill("vocab", false);
      [lb, rb].forEach(b => { b.classList.add("bad"); b.classList.remove("sel"); setTimeout(() => b.classList.remove("bad"), 450); });
    }
    left = right = null;
  };
  $$("[data-l]", v).forEach(b => b.onclick = () => { $$("[data-l]", v).forEach(x => x.classList.remove("sel")); b.classList.add("sel"); left = b.dataset.l; check(); });
  $$("[data-r]", v).forEach(b => b.onclick = () => { $$("[data-r]", v).forEach(x => x.classList.remove("sel")); b.classList.add("sel"); right = b.dataset.r; check(); });
  const finish = () => {
    clearInterval(tick);
    const sec = Math.round((Date.now() - t0) / 1000);
    addXp(Math.max(10, 30 - mistakes * 4));
    if (!mistakes) { progressChallenge("match"); confetti(40); }
    setTimeout(() => rateSummary(v, ws.map(w => ({ w, sug: bad[w.id] ? 1 : sec / ws.length < 4 ? 3 : 2 })), {
      title: mistakes ? "Juftlash tugadi!" : "Xatosiz! 🏆", emoji: mistakes ? "🧩" : "🏆",
      stats: statsRow([[sec + "s", "vaqt"], [mistakes, "xato", mistakes ? "var(--err)" : "var(--ok)"], [`+${Math.max(10, 30 - mistakes * 4)}`, "XP", "var(--accent)"]]), again: () => GAME_FN.match(v) }), 500);
  };
};

/* ---------- 3. Test ---------- */
GAME_FN.mcq = v => {
  const items = weightedWords(10).map(w => buildEx(Math.random() < 0.6 ? "mcq_en_uz" : "mcq_uz_en", w));
  runSession(v, items, { title: "Test" });
  ACT.again = () => GAME_FN.mcq(v);
};

/* ---------- 4. So'z yig'ish ---------- */
GAME_FN.build = v => {
  const pool = S.words.filter(w => /^[a-z]{3,12}$/i.test(w.en.trim()));
  const ws = weightedWords(8, pool.length >= 4 ? pool : S.words);
  let i = 0, score = 0;
  const results = [];
  const draw = () => {
    if (i >= ws.length) {
      addXp(score * 3);
      rateSummary(v, results, { title: "So'z yig'ish tugadi!", emoji: "🧱", stats: statsRow([[`${score}/${ws.length}`, "to'g'ri"], [`+${score * 3}`, "XP", "var(--accent)"], [results.filter(r => r.sug === 3).length, "birinchi urinishda"]]), again: () => GAME_FN.build(v) });
      return;
    }
    const w = ws[i], word = w.en.trim().toLowerCase().replace(/\s+/g, "");
    let letters = shuffle([...word].map((c, j) => ({ c, j })));
    if (letters.map(x => x.c).join("") === word && word.length > 2) letters = letters.reverse();
    const picked = [];
    let tries = 0, hint = false;
    const paint = () => {
      $("#slots", v).innerHTML = [...word].map((_, j) => `<div class="slot" data-s="${j}">${picked[j] ? esc(picked[j].c) : ""}</div>`).join("");
      $("#letters", v).innerHTML = letters.map((x, j) => `<button class="letter ${picked.includes(x) ? "used" : ""}" data-x="${j}">${esc(x.c)}</button>`).join("");
      $$("[data-x]", v).forEach(b => b.onclick = () => add(letters[+b.dataset.x]));
      $$("[data-s]", v).forEach(b => b.onclick = () => { const j = +b.dataset.s; if (picked[j]) { picked.splice(j, 1); paint(); } });
    };
    const add = x => {
      if (picked.includes(x) || picked.length >= word.length) return;
      picked.push(x); paint();
      if (picked.length === word.length) {
        const guess = picked.map(p => p.c).join("");
        if (guess === word) {
          score++; recordSkill("vocab", true); speak(w.en);
          results.push({ w, sug: tries === 0 && !hint ? 3 : tries <= 1 ? 2 : 1 });
          $("#bmsg", v).innerHTML = `<div class="fb ok">✅ ${esc(w.en)} — ${esc(w.uz)}</div>`;
          setTimeout(() => { i++; draw(); }, 1000);
        } else {
          tries++; recordSkill("vocab", false);
          $("#bmsg", v).innerHTML = `<div class="fb bad">❌ «${esc(guess)}» — qayta urinib ko'ring</div>`;
          setTimeout(() => { picked.length = 0; paint(); }, 700);
          if (tries >= 3) { results.push({ w, sug: 0 }); $("#bmsg", v).innerHTML = `<div class="fb bad">To'g'ri javob: <span class="ans">${esc(w.en)}</span></div>`; setTimeout(() => { i++; draw(); }, 1500); }
        }
      }
    };
    v.innerHTML = `<div class="ex-wrap">${gameHead("🧱 So'z yig'ish", `<span class="chip">${i + 1}/${ws.length}</span>`)}
      <div class="qcard center"><span class="qkind">Word builder</span><div class="qtext">${esc(w.uz)}</div><div class="qsub">${w.pos ? esc(w.pos) + " · " : ""}${word.length} harf</div>
      <div class="slots" id="slots"></div><div class="letters" id="letters"></div>
      <div class="row mt" style="justify-content:center"><button class="btn ghost sm" id="bh">💡 Birinchi harf</button><button class="btn ghost sm" id="bl">🔊 Eshitish</button><button class="btn ghost sm" id="bc">⌫ Tozalash</button></div><div id="bmsg"></div></div></div>`;
    paint();
    $("#bh", v).onclick = () => { hint = true; if (!picked.length) add(letters.find(x => x.j === 0)); };
    $("#bl", v).onclick = () => { hint = true; speak(w.en); };
    $("#bc", v).onclick = () => { picked.length = 0; paint(); };
    KEYH = e => {
      if (e.key === "Backspace") { picked.pop(); paint(); return; }
      const x = letters.find(x => x.c === e.key.toLowerCase() && !picked.includes(x)); if (x) add(x);
    };
  };
  draw();
};

/* ---------- 5. Tushib qolgan so'z ---------- */
GAME_FN.missing = v => {
  const pool = S.words.filter(canCloze);
  if (pool.length < 2) { toast("Buning uchun misol gapli so'zlar kerak"); go("games"); return; }
  runSession(v, weightedWords(10, pool).map(w => buildEx("cloze_mcq", w)), { title: "Tushib qolgan so'z" });
  ACT.again = () => GAME_FN.missing(v);
};

/* ---------- 6. Tezlik sinovi ---------- */
GAME_FN.speed = v => {
  v.innerHTML = `<div class="ex-wrap">${gameHead("⚡ Tezlik sinovi")}<div class="qcard center"><div style="font-size:4rem">⚡</div><h2>60 soniya</h2>
    <p class="muted">Iloji boricha ko'p savolga to'g'ri javob bering. Xato javob 3 soniya oladi!</p><p>🏆 Rekord: <b>${S.records.bestSpeed}</b></p>
    <button class="btn big grad mt" id="sg">▶ Boshlash</button></div></div>`;
  $("#sg", v).onclick = () => play();
  KEYH = e => { if (e.key === "Enter") play(); };
  function play() {
    let left = 60, score = 0, wrong = 0, lock = false;
    const res = [];
    const end = Date.now() + 60000;
    let penalty = 0;
    v.innerHTML = `<div class="ex-wrap">${gameHead("⚡ Tezlik sinovi", `<span class="chip xp" id="ss">✅ 0</span>`)}<div class="timer" id="st">60</div>${bar(100, "warn")}<div id="sq" class="mt"></div></div>`;
    const tick = setInterval(() => {
      left = Math.max(0, Math.ceil((end - penalty - Date.now()) / 1000));
      const t = $("#st", v); if (!t) return;
      t.textContent = left; t.classList.toggle("low", left <= 10);
      $(".bar i", v).style.width = (left / 60 * 100) + "%";
      if (left <= 0) finish();
    }, 200);
    onLeave(() => clearInterval(tick));
    const next = () => {
      const w = weightedWords(1)[0];
      const rev = Math.random() < 0.4;
      const opts = shuffle([w, ...distractors(w, rev ? "en" : "uz", 3)]);
      $("#sq", v).innerHTML = `<div class="qcard" style="padding:20px"><div class="qtext center" style="margin:0">${esc(rev ? w.uz : w.en)}</div>
        <div class="opts">${opts.map((o, i) => `<button class="opt" data-i="${i}"><span class="k">${i + 1}</span>${esc(rev ? o.en : o.uz)}</button>`).join("")}</div></div>`;
      const choose = i => {
        if (lock) return; lock = true;
        const o = opts[i], ok = o === w || norm(rev ? o.en : o.uz) === norm(rev ? w.en : w.uz);
        const btns = $$(".opt", v);
        btns[i].classList.add(ok ? "ok" : "bad");
        if (!ok) btns[opts.indexOf(w)].classList.add("ok");
        recordSkill("vocab", ok);
        res.push({ w, sug: ok ? 2 : 0 });
        if (ok) { score++; $("#ss", v).textContent = "✅ " + score; } else { wrong++; penalty += 3000; }
        setTimeout(() => { lock = false; if (left > 0) next(); }, ok ? 250 : 900);
      };
      $$(".opt", v).forEach(b => b.onclick = () => choose(+b.dataset.i));
      KEYH = e => { if (/^[1-4]$/.test(e.key)) choose(+e.key - 1); };
    };
    let finished = false;
    const finish = () => {
      if (finished) return; finished = true; clearInterval(tick); KEYH = null;
      const rec = score > S.records.bestSpeed;
      if (rec) { S.records.bestSpeed = score; save(); }
      addXp(score * 3);
      progressChallenge("speed15", score >= 15 ? 1 : 0, 1);
      checkAchievements();
      if (rec && score) confetti();
      rateSummary(v, res, { title: rec && score ? "Yangi rekord! 🏆" : "Vaqt tugadi!", emoji: "⚡",
        stats: statsRow([[score, "to'g'ri", "var(--ok)"], [wrong, "xato", "var(--err)"], [`+${score * 3}`, "XP", "var(--accent)"]]), again: () => GAME_FN.speed(v) });
    };
    next();
  }
};

/* ---------- 7. Xotira o'yini ---------- */
GAME_FN.memory = v => {
  const ws = weightedWords(6);
  const cards = shuffle(ws.flatMap(w => [{ w, t: w.en, s: "en" }, { w, t: w.uz, s: "uz" }]));
  let open = [], tries = 0, found = 0, lock = false;
  const miss = {};
  const t0 = Date.now();
  v.innerHTML = `<div class="ex-wrap">${gameHead("🧠 Xotira o'yini", `<span class="chip" id="mtr">Urinish: 0</span>`)}
    <p class="small muted center">Kartalarni oching va inglizcha so'zni uning tarjimasi bilan juftlang.</p>
    <div class="mem mt">${cards.map((c, i) => `<div class="mcard" data-i="${i}"><div class="in"><div class="face fr">?</div><div class="face bk">${esc(c.t)}</div></div></div>`).join("")}</div></div>`;
  $$(".mcard", v).forEach(el => el.onclick = () => {
    const i = +el.dataset.i, c = cards[i];
    if (lock || el.classList.contains("open") || el.classList.contains("done")) return;
    el.classList.add("open"); open.push({ el, c });
    if (c.s === "en") speak(c.w.en);
    if (open.length < 2) return;
    tries++; $("#mtr", v).textContent = "Urinish: " + tries;
    const [a, b] = open; open = [];
    if (a.c.w.id === b.c.w.id && a.c.s !== b.c.s) {
      setTimeout(() => { a.el.classList.add("done"); b.el.classList.add("done"); }, 300);
      found++; recordSkill("vocab", true);
      if (found === ws.length) setTimeout(finish, 700);
    } else {
      miss[a.c.w.id] = (miss[a.c.w.id] || 0) + 1; miss[b.c.w.id] = (miss[b.c.w.id] || 0) + 1;
      lock = true;
      setTimeout(() => { a.el.classList.remove("open"); b.el.classList.remove("open"); lock = false; }, 900);
    }
  });
  const finish = () => {
    const sec = Math.round((Date.now() - t0) / 1000), xp = Math.max(10, 40 - (tries - ws.length) * 2);
    addXp(xp);
    if (tries < 20) progressChallenge("memory");
    rateSummary(v, ws.map(w => ({ w, sug: (miss[w.id] || 0) >= 3 ? 1 : 2 })), { title: "Hamma juftlar topildi!", emoji: "🧠",
      stats: statsRow([[tries, "urinish"], [sec + "s", "vaqt"], [`+${xp}`, "XP", "var(--accent)"]]), again: () => GAME_FN.memory(v) });
  };
};

/* ---------- 8. Gap sinovi ---------- */
GAME_FN.sentence = v => {
  runSession(v, weightedWords(5).map(w => buildEx("sentence", w, { skill: "writing" })), { title: "Gap sinovi" });
  ACT.again = () => GAME_FN.sentence(v);
};

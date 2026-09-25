// AI Ustoz va Suhbat. API kalit bo'lsa Claude ishlatiladi, bo'lmasa oflayn (qoidalarga asoslangan) ustoz.
"use strict";

/* ================= Claude API ================= */
const hasAI = () => !!S.profile.apiKey;
async function askClaude(system, messages, maxTokens = 2000, schema = null) {
  const model = S.profile.model || "claude-opus-5";
  const body = { model, max_tokens: maxTokens, system, messages };
  const oc = {};
  if (!/haiku/.test(model)) oc.effort = "low"; // suhbat uchun tez javob
  if (schema) oc.format = { type: "json_schema", schema };
  if (Object.keys(oc).length) body.output_config = oc;
  const headers = {
    "content-type": "application/json",
    "x-api-key": S.profile.apiKey,
    "anthropic-version": "2023-06-01",
    "anthropic-dangerous-direct-browser-access": "true",
  };
  if (model === "claude-opus-5") { body.fallbacks = "default"; headers["anthropic-beta"] = "server-side-fallback-2026-07-01"; }
  let r;
  try { r = await fetch("https://api.anthropic.com/v1/messages", { method: "POST", headers, body: JSON.stringify(body) }); }
  catch (e) { throw new Error("Internet bilan aloqa yo'q"); }
  if (!r.ok) {
    let msg = r.status + "";
    try { const j = await r.json(); msg = (j.error && j.error.message) || msg; } catch (e) {}
    if (r.status === 401) msg = "API kalit noto'g'ri";
    if (r.status === 429) msg = "So'rovlar ko'p — biroz kuting";
    if (r.status === 529 || r.status >= 500) msg = "Server band — keyinroq urinib ko'ring";
    throw new Error(msg);
  }
  const j = await r.json();
  if (j.stop_reason === "refusal") throw new Error("Model bu so'rovga javob bermadi");
  return (j.content || []).filter(b => b.type === "text").map(b => b.text).join("").trim();
}
async function askClaudeJSON(system, messages, schema, maxTokens = 2000) {
  const t = await askClaude(system, messages, maxTokens, schema);
  try { return JSON.parse(t); } catch (e) { const m = t.match(/\{[\s\S]*\}/); if (m) return JSON.parse(m[0]); throw new Error("Javobni o'qib bo'lmadi"); }
}
function teacherSystem() {
  const P = S.profile;
  const vocab = S.words.slice(-80).map(w => `${w.en}=${w.uz}`).join("; ");
  const hard = S.words.filter(isDifficult).slice(0, 15).map(w => w.en).join(", ");
  const mis = S.mistakes.filter(m => m.type === "grammar").slice(0, 10).map(m => `"${m.wrong}"→"${m.right}"`).join("; ");
  return `You are a friendly, encouraging English teacher for an Uzbek-speaking learner. Level: ${LEVELS[P.level].name}.
Explain simply, like a kind tutor, not like an academic textbook. Keep answers short (usually under 120 words) and practical.
Write explanations of grammar and mistakes in Uzbek (Latin script); write English examples in English. Use a few emojis where natural.
When you correct a sentence, show the corrected sentence first, then explain each mistake in one line.
In Uzbek text, never use the verb "yaratmoq" or its forms; use "yasamoq" instead (e.g. "yasadim", "yasash").
The learner's vocabulary (recent): ${vocab || "empty"}.
Words they often forget: ${hard || "none yet"}.
Their recent grammar mistakes: ${mis || "none recorded"}.
Prefer using the learner's own vocabulary in examples and exercises.`;
}
function fmtAI(t) {
  return esc(t).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, '<span class="kbd">$1</span>').replace(/^#+\s*(.*)$/gm, "<b>$1</b>");
}
function aiCheckBtn(text, w) {
  return hasAI() ? `<div class="mt"><button class="btn ghost sm" data-aicheck>🤖 AI ustoz fikrini olish</button><div class="aiout small mt" style="white-space:pre-wrap;color:var(--ink)"></div></div>` : "";
}
function bindAiCheck(root, text, w) {
  const b = $("[data-aicheck]", root); if (!b) return;
  b.onclick = async () => {
    b.disabled = true; b.textContent = "⏳ Ustoz o'ylayapti...";
    try {
      const t = await askClaude(teacherSystem(), [{ role: "user", content: `Check my sentence${w ? ` (I had to use the word "${w.en}")` : ""}:\n"${text}"\nGive: 1) corrected sentence, 2) short Uzbek explanation of each mistake, 3) one more natural alternative, 4) a score 0-100.` }], 1200);
      $(".aiout", root).innerHTML = fmtAI(t);
      b.remove();
    } catch (e) { toast("❌ " + e.message, 3500); b.disabled = false; b.textContent = "🤖 AI ustoz fikrini olish"; }
  };
}

/* ================= AI USTOZ ================= */
if (!S.teacher) S.teacher = [];
VIEWS.teacher = (v) => {
  themeAct();
  if (!S.teacher) S.teacher = [];
  v.innerHTML = `${topbar("🤖 AI Ustoz", hasAI() ? "Claude bilan ishlayapti" : "Oflayn ustoz · Sozlamalarda API kalit qo'shsangiz, erkin suhbatlashadi")}
    <div class="card"><div class="chat" id="chat"></div>
      <div class="qchips" id="qc"></div>
      <div class="composer"><textarea class="inp" id="ti" rows="1" placeholder="Savol bering yoki inglizcha gap yozing..."></textarea>${hasSR ? `<button class="btn ghost icon" id="tm" title="Gapirish">🎤</button>` : ""}<button class="btn icon" id="ts">➤</button></div>
      <div class="row mt between"><span class="tiny muted">Enter — yuborish, Shift+Enter — yangi qator</span><button class="btn ghost sm" data-act="clear">🧹 Tozalash</button></div></div>`;
  const chat = $("#chat");
  const chips = ["📖 Explain a word", "✅ Check my sentence", "💡 Example sentences", "❓ Ask me a question", "🎯 Recommend words", "🧩 Give me an exercise", "🔎 My common mistakes", "💬 Start a conversation"];
  $("#qc").innerHTML = chips.map(c => `<button>${c}</button>`).join("");
  const add = (who, html, cls) => {
    const d = document.createElement("div");
    d.className = "msg " + (cls || (who === "me" ? "me" : "ai"));
    d.innerHTML = (who === "ai" ? `<span class="who">🤖 Ustoz</span>` : "") + html;
    chat.appendChild(d); chat.scrollTop = chat.scrollHeight;
    return d;
  };
  const draw = () => {
    chat.innerHTML = "";
    if (!S.teacher.length) add("ai", fmtAI(`Salom${S.profile.name ? ", " + S.profile.name : ""}! 👋 Men sizning ingliz tili ustozingizman.\n\nMendan so'rashingiz mumkin:\n• so'zni tushuntirish — «explain improve»\n• gapingizni tekshirish — shunchaki inglizcha gap yozing\n• misollar — «example borrow»\n• savol, mashq, so'z tavsiyasi — pastdagi tugmalar`));
    S.teacher.forEach(m => add(m.role === "user" ? "me" : "ai", m.role === "user" ? esc(m.content) : fmtAI(m.content)));
  };
  draw();
  let busy = false;
  const send = async text => {
    text = text.trim(); if (!text || busy) return;
    busy = true;
    $("#ti").value = "";
    S.teacher.push({ role: "user", content: text });
    add("me", esc(text));
    const typing = add("ai", `<span class="typing"><i></i><i></i><i></i></span>`);
    let reply;
    try {
      if (hasAI()) {
        const hist = S.teacher.slice(-20).map(m => ({ role: m.role, content: m.content }));
        while (hist.length && hist[0].role !== "user") hist.shift();
        reply = await askClaude(teacherSystem(), hist, 2000);
      }
      else { await new Promise(r => setTimeout(r, 450)); reply = await offlineTeacher(text); }
    } catch (e) {
      reply = `⚠️ ${e.message}. Oflayn ustoz javob beradi:\n\n` + await offlineTeacher(text);
    }
    typing.remove();
    S.teacher.push({ role: "assistant", content: reply });
    S.teacher = S.teacher.slice(-60);
    save();
    add("ai", fmtAI(reply));
    addXp(2);
    busy = false;
  };
  $("#ts").onclick = () => send($("#ti").value);
  $("#ti").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send($("#ti").value); } });
  $$("#qc button").forEach((b, i) => b.onclick = () => {
    const w = weightedWords(1)[0];
    const q = [`explain ${w ? w.en : "improve"}`, null, `example ${w ? w.en : "improve"}`, "ask me a question", "recommend words", "give me an exercise", "my common mistakes", "start a conversation"][i];
    if (i === 1) { $("#ti").value = "Check: "; $("#ti").focus(); return; }
    if (i === 7) { location.hash = "#/talk"; return; }
    send(q);
  });
  const tm = $("#tm");
  if (tm) tm.onclick = async () => {
    tm.textContent = "🔴";
    try { const r = await listenOnce({ onInterim: t => $("#ti").value = t }); if (r.text) send(r.text); } catch (e) { toast("🎤 " + e.message); }
    tm.textContent = "🎤";
  };
  ACT.clear = () => { S.teacher = []; OT.state = null; save(); draw(); };
};

// Oflayn ustoz
const OT = { state: null };
async function offlineTeacher(text) {
  const t = text.trim(), low = t.toLowerCase();
  // Kutilayotgan javob (savol yoki mashq)
  if (OT.state && !/^(explain|example|recommend|exercise|mistake|question|ask me|help|yordam|tushuntir|misol|mashq|xato|tavsiya)/i.test(low)) {
    const st = OT.state; OT.state = null;
    if (st.type === "question") {
      const a = analyzeSentence(t, st.w ? st.w.en : null, { spoken: true });
      const sc = Math.round(a.grammar * 0.5 + a.structure * 0.3 + a.vocab * 0.2);
      a.issues.filter(i => !i.minor).forEach(i => logMistake("grammar", i.wrong, i.right, i.why));
      return `${sc >= 80 ? "Great answer! 🌟" : sc >= 60 ? "Good answer! 👍" : "Nice try! 💪"} (${sc}/100)\n\n` +
        (a.issues.filter(i => !i.minor).length ? `**Better:** ${a.fixed}\n\n` + a.issues.filter(i => !i.minor).map(i => `• «${i.wrong}» → «${i.right}» — ${i.why}`).join("\n") : "Grammatik xato topmadim. ✅") +
        (st.w && !usesWord(t, st.w.en) ? `\n\n💡 Keyingi safar «${st.w.en}» (${st.w.uz}) so'zini ham ishlatib ko'ring.` : "") +
        (a.words < 8 ? "\n\n💡 Javobni uzunroq qiling: «because...» yoki «for example...» qo'shing." : "");
    }
    if (st.type === "exercise") {
      const g = st.lang === "uz" ? gradeUz(t, st.answer) : gradeEn(t, st.answer);
      recordSkill("vocab", g.ok);
      if (st.w) rateWord(st.w.id, g.ok ? (g.typo ? 1 : 2) : 0);
      return g.ok ? `✅ To'g'ri! **${st.answer}**${g.typo ? " (kichik imlo xatosi bor)" : ""}\n\nYana mashq kerakmi? «give me an exercise» deb yozing.` : `❌ To'g'ri javob: **${st.answer}**\n\n${st.w && st.w.ex ? `Misol: ${st.w.ex}` : ""}\nBu so'z tez orada takrorlashga qaytadi. 🔁`;
    }
  }
  let m;
  if ((m = low.match(/^(?:explain|what does|what is|meaning of|tushuntir\w*|ma'nosi)\s+["«]?([a-z' -]+?)["»]?(?:\s+mean)?\??$/i)) || (m = low.match(/^["«]?([a-z'-]+)["»]?\s+(?:nima|degani|nima degani)\??$/i))) {
    return await explainWord(m[1].trim());
  }
  if ((m = low.match(/^(?:example|examples|misol|misollar)\s+(?:for\s+|with\s+)?["«]?([a-z' -]+?)["»]?$/i))) return exampleSentences(m[1].trim());
  if (/question|savol|ask me/.test(low)) {
    const w = weightedWords(1)[0];
    OT.state = { type: "question", w };
    return `Let's practice! 🎤\n\n**${pick(SIMPLE_QUESTIONS)}**\n\n${w ? `💡 Javobingizda «${w.en}» (${w.uz}) so'zini ishlatishga harakat qiling.` : ""}\nJavobingizni yozing yoki 🎤 tugmasi bilan ayting.`;
  }
  if (/recommend|tavsiya|what should i learn|nima o'rgan/.test(low)) {
    const due = dueWords().slice(0, 5), hard = S.words.filter(isDifficult).slice(0, 5), fresh = S.words.filter(isNew).slice(0, 5);
    const topicWords = Object.values(TOPICS).flatMap(t => t.words).filter(([en]) => !S.words.some(w => norm(w.en) === norm(en)));
    return `🎯 **Tavsiyalarim:**\n\n` +
      (due.length ? `🔁 Hozir takrorlash vaqti kelgan: ${due.map(w => w.en).join(", ")}\n` : "") +
      (hard.length ? `😵 Ko'p unutiladiganlar: ${hard.map(w => w.en).join(", ")} — bularni «Kartochkalar» o'yinida mashq qiling.\n` : "") +
      (fresh.length ? `🆕 Hali o'rganilmagan: ${fresh.map(w => w.en).join(", ")}\n` : "") +
      `\n📚 Lug'atingizga qo'shish uchun foydali so'zlar:\n${shuffle(topicWords).slice(0, 6).map(([en, uz]) => `• **${en}** — ${uz}`).join("\n")}`;
  }
  if (/exercise|mashq|quiz|test me/.test(low)) {
    const w = weightedWords(1)[0];
    if (!w) return "Mashq uchun avval lug'atingizga so'z qo'shing. 📚";
    const c = cloze(w);
    const r = rnd(3);
    if (c && r === 0) { OT.state = { type: "exercise", w, answer: c.answer }; return `🧩 **Bo'sh joyni to'ldiring:**\n\n${c.before}_____${c.after}\n\n💡 Ma'nosi: ${w.uz}`; }
    if (r === 1) { OT.state = { type: "exercise", w, answer: w.uz, lang: "uz" }; return `🧩 **Tarjima qiling (inglizcha → o'zbekcha):**\n\n**${w.en}**${w.ex ? `\n\n«${w.ex}»` : ""}`; }
    OT.state = { type: "exercise", w, answer: w.en }; return `🧩 **Inglizchasini yozing:**\n\n**${w.uz}**${w.pos ? ` (${w.pos})` : ""}\n\n💡 ${w.en[0]}${"_".repeat(w.en.length - 1)}`;
  }
  if (/mistake|xato/.test(low)) {
    const mis = {}; S.mistakes.filter(m => m.type === "grammar").forEach(m => { (mis[m.note] = mis[m.note] || []).push(m); });
    const top = Object.entries(mis).sort((a, b) => b[1].length - a[1].length).slice(0, 5);
    const wrongWords = {}; S.mistakes.filter(m => m.type !== "grammar" && m.right).forEach(m => wrongWords[m.right] = (wrongWords[m.right] || 0) + 1);
    const ww = Object.entries(wrongWords).sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (!top.length && !ww.length) return "Hozircha xatolar qayd etilmagan. 🎉 Yozish va gapirish mashqlarini bajaring — men xatolarni kuzatib boraman.";
    return `🔎 **Ko'p uchraydigan xatolaringiz:**\n\n` + top.map(([why, arr]) => `• ${why} (${arr.length}×)\n  Masalan: «${arr[0].wrong}» → «${arr[0].right}»`).join("\n") +
      (ww.length ? `\n\n📚 **Ko'p adashtirgan javoblar:** ${ww.map(([w, n]) => `${w} (${n}×)`).join(", ")}` : "");
  }
  if (/conversation|suhbat|talk/.test(low)) return "💬 «Suhbat» bo'limida mavzu tanlang — men siz bilan inglizcha suhbatlashaman va xatolaringizni tuzataman!";
  if (/^(hi|hello|hey|salom|assalom)/.test(low)) return `Hello! 😊 How are you today?\n\nMen bilan inglizcha yozishingiz mumkin — gaplaringizni tekshirib boraman.`;
  if (/^(thanks|thank you|rahmat)/.test(low)) return "You're welcome! 😊 Keep practicing every day! 🔥";
  if (/^check[:\s]/i.test(t)) return checkReply(t.replace(/^check[:\s]*/i, ""));
  if (/^[a-z'-]+$/i.test(t)) return await explainWord(low);
  // Inglizcha gap bo'lsa — tekshiramiz
  if (/[a-z]/i.test(t) && t.split(/\s+/).length >= 3 && !/[ʻʼ‘’']?[oOgG][ʻʼ‘’']/.test(t) && !/\b(qanday|nima|nega|qachon|men|sen|biz|siz)\b/i.test(t)) return checkReply(t);
  return `Tushunmadim 🙂 Men quyidagilarni qila olaman:\n• **explain** so'z — so'zni tushuntiraman\n• **example** so'z — misol gaplar\n• inglizcha gap yozing — tekshiraman\n• **question** — savol beraman\n• **exercise** — mashq beraman\n• **recommend** — so'z tavsiya qilaman\n• **mistakes** — xatolaringiz tahlili\n\n💡 To'liq erkin suhbat uchun Sozlamalarda Claude API kalitini qo'shing.`;
}
function checkReply(s) {
  if (!s.trim()) return "Tekshirish uchun inglizcha gap yozing. ✍️";
  const a = analyzeSentence(s, null);
  const real = a.issues.filter(i => !i.minor);
  a.issues.forEach(i => { if (!i.minor) logMistake("grammar", i.wrong, i.right, i.why); });
  if (!a.issues.length) return `✅ Good sentence! Xato topmadim.\n\n${a.words < 6 ? "💡 Uni uzunroq qilib ko'ring: sifat yoki «because...» qo'shing." : "Zo'r! Davom eting. 🌟"}`;
  return `${real.length ? "Yaxshi urinish! Biroz tuzatamiz: ✏️" : "Deyarli mukammal! 👍"}\n\n**${a.fixed}**\n\n` + a.issues.map(i => `• ${i.wrong ? `«${i.wrong}» → «${i.right}»: ` : ""}${i.why}`).join("\n");
}
async function explainWord(en) {
  const w = S.words.find(x => norm(x.en) === norm(en));
  let out = "";
  if (w) {
    out = `📖 **${w.en}** ${w.pron || ""}${w.pos ? ` · _${w.pos}_` : ""}\n🇺🇿 ${w.uz}\n`;
    if (w.ex) out += `\n💬 ${w.ex}\n`;
    if (w.note) out += `📝 ${w.note}\n`;
    const forms = w.pos === "verb" ? `\n🔤 Shakllari: ${w.en} → ${thirdPerson(w.en)} → ${pastOf(w.en)} → ${/e$/.test(w.en) ? w.en.slice(0, -1) : w.en}ing` : "";
    out += forms;
    const st = stageOf(w);
    out += `\n\n📊 Holati: ${st.uz}${w.srs.lapses ? ` · ${w.srs.lapses} marta unutilgan` : ""}`;
  }
  try {
    const d = await dictLookup(en);
    if (!w) out = `📖 **${en}** ${d.pron || ""}${d.pos ? ` · ${d.pos}` : ""}\n`;
    if (d.def) out += `\n🇬🇧 Definition: ${d.def}`;
    if (d.ex && (!w || d.ex !== w.ex)) out += `\n💬 ${d.ex}`;
    if (!w) out += `\n\nBu so'z lug'atingizda yo'q — «📚 Lug'atim» bo'limida qo'shishingiz mumkin.`;
  } catch (e) {
    if (!w) out = `«${en}» so'zini lug'atingizda topmadim va internetdagi lug'atga ulanib bo'lmadi. 🤔`;
  }
  return out;
}
function exampleSentences(en) {
  const w = S.words.find(x => norm(x.en) === norm(en));
  const pos = w ? w.pos : "";
  const T = {
    verb: [`I want to ${en} my skills this year.`, `She will ${en} it tomorrow.`, `Did you ${en} it yesterday?`, `We should ${en} together.`],
    noun: [`This ${en} is very important to me.`, `I have a ${en} at home.`, `Tell me about your ${en}.`, `The ${en} was better than I expected.`],
    adjective: [`The weather is ${en} today.`, `She looks very ${en}.`, `It was a ${en} experience.`, `I feel ${en} when I study.`],
    adverb: [`I ${en} study in the evening.`, `He speaks ${en}.`, `She ${en} helps her friends.`],
  }[pos] || [`Can you use «${en}» in a sentence?`, `I learned the word «${en}» today.`];
  return `💡 **«${en}»** bilan misollar${w ? ` (${w.uz})` : ""}:\n\n` + (w && w.ex ? `• ${w.ex}\n` : "") + T.slice(0, 3).map(s => `• ${s}`).join("\n") + `\n\nEndi o'zingiz gap tuzing — men tekshiraman! ✍️`;
}

/* ================= SUHBAT ================= */
VIEWS.talk = (v, p) => {
  themeAct();
  const t = p.get("t");
  if (t && TOPICS[t]) return conversation(v, t);
  v.innerHTML = `${topbar("💬 Suhbat", hasAI() ? "Claude bilan jonli suhbat" : "Mavzuni tanlang — inglizcha suhbatlashamiz")}
    <div class="grid g3">${Object.entries(TOPICS).map(([k, x]) => `<button class="tile" data-act="t" data-k="${k}"><span class="big">${x.icon}</span><b>${x.name}</b><span class="muted">${x.uz}</span></button>`).join("")}</div>
    <div class="card soft mt small">💡 Har bir javobingizdan keyin ustoz tabiiyroq variantni ko'rsatadi. Suhbat oxirida: grammatik xatolar, yangi so'zlar, yaxshiroq gaplar, ball va tavsiyalar.</div>`;
  ACT.t = el => location.hash = "#/talk?t=" + el.dataset.k;
};
function conversation(v, key) {
  const T = TOPICS[key];
  const turns = []; // {role, text, fix?, score?}
  const errors = [], betters = [], newWords = [...T.words.map(([en, uz]) => ({ en, uz }))], scores = [];
  let qi = 0, busy = false, ended = false, tAsk = Date.now();
  v.innerHTML = `${topbar(`${T.icon} ${T.name}`, T.uz + " · suhbat mashqi")}
    <div class="card"><div class="chat" id="cc"></div>
    <div class="composer"><textarea class="inp" id="ci" rows="1" placeholder="Answer in English..."></textarea>${hasSR ? `<button class="btn ghost icon" id="cm" title="Gapirish">🎤</button>` : ""}<button class="btn icon" id="cs">➤</button></div>
    <div class="row mt between"><div class="row"><button class="btn ghost sm" id="chint">💡 Yordam</button><button class="btn ghost sm" id="crep">🔊 Qayta eshitish</button></div><button class="btn sm err" id="cend">🏁 Tugatish</button></div></div>`;
  const cc = $("#cc");
  const add = (cls, html) => { const d = document.createElement("div"); d.className = "msg " + cls; d.innerHTML = html; cc.appendChild(d); cc.scrollTop = cc.scrollHeight; return d; };
  const aiSay = text => { turns.push({ role: "ai", text }); add("ai", `<span class="who">${T.icon} Partner</span>${esc(text)} ${speakBtn(text)}`); speak(text); tAsk = Date.now(); };
  aiSay(T.q[0]);
  const reaction = s => {
    const l = s.toLowerCase();
    if (/\b(love|like|great|good|happy|fun|nice|enjoy|amazing|best)\b/.test(l)) return pick(["That's great!", "Sounds wonderful!", "Nice!", "I'm glad to hear that!"]);
    if (/\b(bad|tired|sad|difficult|hard|busy|sick|boring|problem)\b/.test(l)) return pick(["Oh, I'm sorry to hear that.", "That sounds difficult.", "I understand."]);
    if (/\b(no|not|never|don't)\b/.test(l)) return pick(["I see.", "Okay, no problem.", "Interesting."]);
    return pick(["I see!", "Interesting!", "Okay!", "Got it!", "Oh, really?"]);
  };
  const handle = async (text, voice) => {
    text = text.trim(); if (!text || busy || ended) return;
    busy = true; $("#ci").value = "";
    addTime("speak", Math.min(90, (Date.now() - tAsk) / 1000));
    turns.push({ role: "me", text });
    add("me", esc(text));
    const a = analyzeSentence(text, null, { spoken: !!voice });
    let sc = Math.round(a.grammar * 0.45 + a.structure * 0.3 + a.vocab * 0.25);
    if (voice && voice.conf) sc = Math.round(sc * 0.8 + clamp(voice.conf * 100, 40, 100) * 0.2);
    scores.push(sc);
    const real = a.issues.filter(i => !i.minor);
    if (hasAI()) {
      const typing = add("ai", `<span class="typing"><i></i><i></i><i></i></span>`);
      try {
        const hist = turns.map(x => ({ role: x.role === "ai" ? "assistant" : "user", content: x.text }));
        if (hist[0].role === "assistant") hist.unshift({ role: "user", content: `(Start a ${T.name} conversation.)` });
        const r = await askClaudeJSON(`You are a friendly conversation partner and English teacher for an Uzbek learner (level: ${LEVELS[S.profile.level].name}). Topic: ${T.name}. Role-play naturally.
For the learner's LAST message: if it has grammar or naturalness mistakes, give a corrected natural version and a one-sentence explanation in Uzbek (Latin). If it is correct, has_mistake=false.
Then continue the conversation: a short natural reaction plus exactly one follow-up question (max 2 sentences, simple English for the level).
Suggest 0-2 useful new topic words with Uzbek translations. Never use the Uzbek verb "yaratmoq"; use "yasamoq".`, hist, {
          type: "object", additionalProperties: false,
          properties: { has_mistake: { type: "boolean" }, better: { type: "string" }, explanation_uz: { type: "string" }, reply: { type: "string" },
            new_words: { type: "array", items: { type: "object", additionalProperties: false, properties: { en: { type: "string" }, uz: { type: "string" } }, required: ["en", "uz"] } } },
          required: ["has_mistake", "better", "explanation_uz", "reply", "new_words"] }, 1500);
        typing.remove();
        if (r.has_mistake && r.better) {
          add("fix", `✏️ A more natural sentence is:<br><b>«${esc(r.better)}»</b> ${speakBtn(r.better)}<div class="small" style="margin-top:4px">${esc(r.explanation_uz)}</div>`);
          errors.push({ wrong: text, right: r.better, why: r.explanation_uz }); betters.push(r.better);
          logMistake("grammar", text, r.better, r.explanation_uz);
          scores[scores.length - 1] = Math.min(sc, 75);
        } else add("good", pick(["✅ Good sentence!", "✅ Perfect!", "✅ Very natural!"]));
        (r.new_words || []).forEach(w => { if (!newWords.some(x => norm(x.en) === norm(w.en))) newWords.push(w); });
        aiSay(r.reply);
      } catch (e) {
        typing.remove(); toast("⚠️ " + e.message + " — oflayn rejim", 3500);
        offlineTurn();
      }
    } else offlineTurn();
    function offlineTurn() {
      if (real.length) {
        add("fix", `✏️ Good! A more natural sentence is:<br><b>«${esc(a.fixed)}»</b> ${speakBtn(a.fixed)}<div class="small" style="margin-top:4px">${real.map(i => esc(i.why)).join("<br>")}</div>`);
        real.forEach(i => { errors.push({ wrong: i.wrong, right: i.right, why: i.why }); logMistake("grammar", i.wrong, i.right, i.why); });
        betters.push(a.fixed);
      } else if (a.words < 4) add("fix", `💡 Try a longer answer — use a full sentence. For example: «${esc(cap(text.replace(/[.!?]$/, "")))}, because ...»`);
      else add("good", pick(["✅ Good sentence!", "✅ Nice answer!", "✅ Well said!"]));
      qi++;
      if (qi < T.q.length) aiSay(`${reaction(text)} ${T.q[qi]}`);
      else { aiSay("Thank you! That was a great conversation. 😊"); setTimeout(finish, 1200); }
    }
    busy = false;
    if (hasAI() && turns.filter(x => x.role === "me").length >= 8) setTimeout(finish, 1500);
  };
  $("#cs").onclick = () => handle($("#ci").value);
  $("#ci").addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handle($("#ci").value); } });
  const cm = $("#cm");
  if (cm) cm.onclick = async () => {
    if (cm.dataset.on) { stopListening(); return; }
    cm.dataset.on = 1; cm.textContent = "🔴"; speechSynthesis.cancel();
    try { const r = await listenOnce({ onInterim: t => $("#ci").value = t }); if (r.text) handle(r.text, r); }
    catch (e) { toast("🎤 " + (e.message === "not-allowed" ? "Mikrofonga ruxsat yo'q" : e.message)); }
    delete cm.dataset.on; cm.textContent = "🎤";
  };
  $("#chint").onclick = () => {
    const last = [...turns].reverse().find(x => x.role === "ai");
    add("good", `💡 Foydali so'zlar: ${T.words.map(([en, uz]) => `<b>${esc(en)}</b> (${esc(uz)})`).join(", ")}<br>Boshlash uchun: «I think...», «In my opinion...», «Usually I...», «Last week I...»`);
    if (last) speak(last.text, { rate: 0.75 });
  };
  $("#crep").onclick = () => { const last = [...turns].reverse().find(x => x.role === "ai"); if (last) speak(last.text, { rate: 0.8 }); };
  $("#cend").onclick = () => finish();
  function finish() {
    if (ended) return; ended = true;
    const mine = turns.filter(x => x.role === "me");
    if (!mine.length) { go("talk"); return; }
    const avg = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
    const avgLen = mine.reduce((a, x) => a + x.text.split(/\s+/).length, 0) / mine.length;
    const recs = [];
    if (avgLen < 7) recs.push("Javoblaringiz qisqa. Har bir javobga sabab yoki misol qo'shing: «because...», «for example...».");
    const whys = {}; errors.forEach(e => whys[e.why] = (whys[e.why] || 0) + 1);
    const topWhy = Object.entries(whys).sort((a, b) => b[1] - a[1])[0];
    if (topWhy) recs.push("Eng ko'p uchragan xato: " + topWhy[0]);
    if (mine.length < 4) recs.push("Suhbatni uzunroq davom ettiring — kamida 5–6 ta javob bering.");
    if (avg >= 85) recs.push("Ajoyib! Keyingi safar qiyinroq mavzuni tanlang (Job interview yoki Business).");
    recs.push("Yangi so'zlarni lug'atingizga qo'shing va ertaga takrorlang.");
    recordSkill("speaking", avg >= 60, avg);
    S.records.convos++; save();
    progressChallenge("convo");
    addXp(15 + mine.length * 3);
    checkAchievements();
    v.innerHTML = `${topbar(`${T.icon} Suhbat yakuni`)}
      <div class="grid g2 stack-sm">
        <div class="card center"><h3>🎤 Speaking score</h3><div class="scorering mt" style="--p:${avg};--c:${avg >= 80 ? "var(--ok)" : avg >= 60 ? "var(--accent)" : "var(--warn)"}"><b>${avg}</b></div>
          <p class="muted mt">${mine.length} ta javob · o'rtacha ${Math.round(avgLen)} so'z · +${15 + mine.length * 3} XP</p></div>
        <div class="card"><h3>📌 Tavsiyalar</h3><ul class="fblist">${recs.map(r => `<li class="tip">${esc(r)}</li>`).join("")}</ul></div>
      </div>
      <div class="card mt"><h3>✏️ Grammatik xatolar (${errors.length})</h3>${errors.length ? `<div class="wlist mt">${errors.map(e => `<div class="witem" style="cursor:default;display:block"><div class="diff"><del>${esc(e.wrong)}</del> → <ins>${esc(e.right)}</ins></div><div class="small muted">${esc(e.why)}</div></div>`).join("")}</div>` : `<p class="muted">Xato topilmadi — zo'r! 🎉</p>`}</div>
      ${betters.length ? `<div class="card mt"><h3>🗣️ Yaxshiroq gaplar</h3><ul class="fblist">${betters.map(b => `<li class="ok">${esc(b)} ${speakBtn(b)}</li>`).join("")}</ul></div>` : ""}
      <div class="card mt"><h3>📚 Yangi so'zlar</h3><div class="wlist mt">${newWords.map((w, i) => { const has = S.words.some(x => norm(x.en) === norm(w.en)); return `<div class="witem" style="cursor:default"><div class="grow"><b>${esc(w.en)}</b> <span class="muted small">${esc(w.uz)}</span></div>${speakBtn(w.en)}${has ? '<span class="tag ok">lug\'atda bor</span>' : `<button class="btn sm" data-nw="${i}">➕ Qo'shish</button>`}</div>`; }).join("")}</div></div>
      <div class="row mt2"><button class="btn big" data-act="again">🔁 Qayta suhbat</button><button class="btn ghost big" data-go="talk">💬 Boshqa mavzu</button><button class="btn ghost big" data-go="home">🏠 Bosh sahifa</button></div>`;
    $$("[data-nw]", v).forEach(b => b.onclick = () => {
      const w = newWords[+b.dataset.nw];
      S.words.push(newWord({ en: w.en, uz: w.uz, cat: { shopping: "daily", restaurant: "food", interview: "work", friends: "daily", family: "daily" }[key] || (CATEGORIES.some(c => c.id === key) ? key : "daily"), level: guessLevel(w.en) }));
      save(); b.outerHTML = '<span class="tag ok">✅ qo\'shildi</span>'; toast(`«${w.en}» lug'atga qo'shildi`);
    });
    ACT.again = () => conversation(v, key);
  }
}

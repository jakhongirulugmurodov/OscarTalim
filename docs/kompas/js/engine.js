/* Kompas — hisoblash yadrosi.
   Sof funksiyalar: DOM yo'q, global holat yo'q. Formulalar: docs/kompas/ALGORITM.md */
(function (global) {
  "use strict";

  const KEYS = ["R", "I", "A", "S", "E", "C"];
  const cfg = () => global.KOMPAS_CONFIG;

  /* ---------- umumiy matematika ---------- */

  function normalize(v) {
    let s = 0;
    KEYS.forEach(k => { s += (v[k] || 0) ** 2; });
    const len = Math.sqrt(s) || 1;
    const out = {};
    KEYS.forEach(k => { out[k] = (v[k] || 0) / len; });
    return out;
  }

  function cosine(a, b) {
    let d = 0;
    KEYS.forEach(k => { d += (a[k] || 0) * (b[k] || 0); });
    return Math.max(0, Math.min(1, d));
  }

  // Standart normal taqsimot funksiyasi Φ (Abramowitz–Stegun 7.1.26, xato < 1.5e-7)
  function phi(z) {
    const t = 1 / (1 + 0.2316419 * Math.abs(z));
    const d = 0.3989422804014327 * Math.exp(-z * z / 2);
    const p = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
    return z >= 0 ? 1 - p : p;
  }

  // Deterministik PRNG (mulberry32) — Monte-Carlo natijasi har safar bir xil bo'lsin
  function rng(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function randn(r) { // Box–Muller
    let u = 0, v = 0;
    while (u === 0) u = r();
    while (v === 0) v = r();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  /* ---------- QADAM 2: RIASEC ---------- */

  // answers: {itemId: 1..5}; items: [{id, shkala}]
  function riasecScores(answers, items) {
    const raw = {}, cnt = {};
    KEYS.forEach(k => { raw[k] = 0; cnt[k] = 0; });
    items.forEach(it => {
      const a = Number(answers[it.id]);
      if (a >= 1 && a <= 5) { raw[it.shkala] += a; cnt[it.shkala] += 1; }
    });
    const pct = {};
    KEYS.forEach(k => { pct[k] = cnt[k] ? ((raw[k] / cnt[k]) - 1) / 4 : 0; });
    const vec = normalize(pct);
    const order = KEYS.slice().sort((x, y) => pct[y] - pct[x] || KEYS.indexOf(x) - KEYS.indexOf(y));
    const answered = items.filter(it => answers[it.id] >= 1).length;
    return { raw, pct, vec, code: order.slice(0, 3).join(""), order, answered, total: items.length };
  }

  // Brown & Gore C-indeksi (0..18) — tushuntirish uchun
  const HEX = ["R", "I", "A", "S", "E", "C"];
  function hexDist(a, b) {
    const d = Math.abs(HEX.indexOf(a) - HEX.indexOf(b));
    return Math.min(d, 6 - d); // 0 bir xil, 1 qo'shni, 2 muqobil, 3 qarama-qarshi
  }
  function cIndex(codeA, codeB) {
    let c = 0;
    for (let i = 0; i < 3; i++) c += (3 - i) * (3 - hexDist(codeA[i], codeB[i]));
    return c;
  }
  function codeOf(riasec) {
    return KEYS.slice().sort((x, y) => (riasec[y] || 0) - (riasec[x] || 0)).slice(0, 3).join("");
  }

  /* ---------- QADAM 5: ball modeli ---------- */

  const ROLE_OF = (fan, block, majburiy) => {
    if (fan === block.fan1) return "fan1";
    if (fan === block.fan2) return "fan2";
    if (majburiy.includes(fan)) return "majburiy";
    return null;
  };

  function ballFromMastery(m, role, c) {
    c = c || cfg();
    const n = c.savol[role], k = c.koef[role], g = c.model.g;
    const mm = Math.max(0, Math.min(1, m));
    return n * k * (mm + (1 - mm) * g);
  }

  // Bir fan bo'yicha ballning kutilgan qiymati; sertifikat bo'lsa — konfiguratsiya ulushi
  function fanBall(fan, role, mastery, sertifikatlar, c) {
    c = c || cfg();
    const max = c.savol[role] * c.koef[role];
    const s = (sertifikatlar || []).find(x => x.fan === fan && x.daraja);
    if (s && c.sertifikat_ulush[s.daraja] != null) {
      return { ball: max * c.sertifikat_ulush[s.daraja], max, sertifikat: s.daraja };
    }
    return { ball: ballFromMastery(mastery ?? 0, role, c), max, sertifikat: null };
  }

  // block: {fan1, fan2}; mastery: {fan: 0..1}
  function totalBall(block, mastery, sertifikatlar, c) {
    c = c || cfg();
    const rows = [];
    rows.push({ fan: block.fan1, role: "fan1", ...fanBall(block.fan1, "fan1", mastery[block.fan1], sertifikatlar, c) });
    rows.push({ fan: block.fan2, role: "fan2", ...fanBall(block.fan2, "fan2", mastery[block.fan2], sertifikatlar, c) });
    c.majburiy_fanlar.forEach(f => {
      rows.push({ fan: f, role: "majburiy", ...fanBall(f, "majburiy", mastery[f], sertifikatlar, c) });
    });
    const total = rows.reduce((s, r) => s + r.ball, 0);
    return { rows, total };
  }

  /* ---------- QADAM 6: o'tish balli va ehtimollik ---------- */

  // Yo'nalishning taxminiy o'tish balli oralig'idan Ĉ va σ_c
  function cutoffEstimate(y, turi, c) {
    c = c || cfg();
    const band = y.otish_taxmin && y.otish_taxmin[turi];
    if (!band) return null;
    const [lo, hi] = band;
    return { C: (lo + hi) / 2, sigma: Math.max((hi - lo) / 3, c.model.sigma_c_min), lo, hi, ishonch: y.ishonch };
  }

  function admitProb(mu, sigmaS, C, sigmaC) {
    if (mu == null || C == null) return null;
    return phi((mu - C) / Math.sqrt(sigmaS * sigmaS + sigmaC * sigmaC));
  }

  // 5 ta tanlov ustuvorlik tartibida: Monte-Carlo (deterministik urug')
  // choices: [{id, C_grant, s_grant, C_kontrakt, s_kontrakt, kontraktMumkin}]
  // grantUstuvor=true: avval barcha tanlovlar grant bo'yicha, so'ng kontrakt bo'yicha tekshiriladi
  // (2026-yilgi "grant ustuvorligi" mexanizmi; false — tanlov tartibida grant→kontrakt)
  function simulateChoices(choices, mu, sigmaS, N, seed, grantUstuvor) {
    N = N || 4000;
    const r = rng(seed || 20270714);
    const hits = choices.map(() => ({ grant: 0, kontrakt: 0 }));
    let none = 0;
    for (let i = 0; i < N; i++) {
      const S = mu + sigmaS * randn(r);
      // har tanlov uchun o'sha yilgi o'tish balli bir marta "tortiladi"
      const cg = choices.map(ch => ch.C_grant != null ? ch.C_grant + ch.s_grant * randn(r) : Infinity);
      const ck = choices.map(ch => (ch.kontraktMumkin && ch.C_kontrakt != null) ? ch.C_kontrakt + ch.s_kontrakt * randn(r) : Infinity);
      let placed = false;
      if (grantUstuvor) {
        for (let j = 0; j < choices.length && !placed; j++) if (S >= cg[j]) { hits[j].grant++; placed = true; }
        for (let j = 0; j < choices.length && !placed; j++) if (S >= ck[j]) { hits[j].kontrakt++; placed = true; }
      } else {
        for (let j = 0; j < choices.length && !placed; j++) {
          if (S >= cg[j]) { hits[j].grant++; placed = true; }
          else if (S >= ck[j]) { hits[j].kontrakt++; placed = true; }
        }
      }
      if (!placed) none++;
    }
    return {
      perChoice: hits.map(h => ({ grant: h.grant / N, kontrakt: h.kontrakt / N, jami: (h.grant + h.kontrakt) / N })),
      any: 1 - none / N,
      anyGrant: hits.reduce((s, h) => s + h.grant, 0) / N
    };
  }

  // Eng yaxshi tartib: barcha o'rin almashtirishlar (≤5! = 120) ustidan kutilgan foyda
  function bestOrder(choices, mu, sigmaS, utilityOf, grantUstuvor) {
    const idx = choices.map((_, i) => i);
    const perms = [];
    (function permute(arr, m) {
      if (!arr.length) { perms.push(m); return; }
      for (let i = 0; i < arr.length; i++) permute(arr.slice(0, i).concat(arr.slice(i + 1)), m.concat(arr[i]));
    })(idx, []);
    let best = null;
    perms.forEach(p => {
      const ordered = p.map(i => choices[i]);
      const sim = simulateChoices(ordered, mu, sigmaS, 1500, 7, grantUstuvor);
      let u = 0;
      sim.perChoice.forEach((pc, j) => { u += pc.grant * utilityOf(ordered[j], "grant") + pc.kontrakt * utilityOf(ordered[j], "kontrakt"); });
      if (!best || u > best.u) best = { u, order: p, sim };
    });
    return best;
  }

  /* ---------- QADAM 3: moslik va reyting ---------- */

  const ISTIQBOL = { yuqori: 1, orta: 0.6, past: 0.3 };
  const RAQOBAT_SAVAT = { yuqori: "orzu", orta: "maqsad", past: "ishonchli" };

  function hardFilter(y, ctx) {
    if (ctx.sertifikatsiz && y.sertifikat) return false;     // chet tili sertifikat talab qiladi
    if (ctx.ijodiysiz && y.ijodiy) return false;
    if (ctx.moliya === "faqat_grant" && y.otish_taxmin && !y.otish_taxmin.grant) return false;
    if (ctx.faqatFanlar && ctx.faqatFanlar.length) {
      if (!ctx.faqatFanlar.includes(y.fan1) || !ctx.faqatFanlar.includes(y.fan2)) return false;
    }
    return true;
  }

  // ctx: {vec, code, fanBaho:{fan:0..1}, moliya, ballFor:(y)=>ball|null, sigmaS, hudud, kochish, ...}
  // ballFor — o'quvchining AYNAN shu yo'nalish fan juftligi bo'yicha prognoz bali (bloklar farq qiladi)
  function matchDirections(ctx, data, rejim, c) {
    c = c || cfg();
    const w = c.model.vaznlar[rejim || "muvozanat"];
    const out = [];
    data.yonalishlar.forEach(y => {
      if (!hardFilter(y, ctx)) return;
      const uvec = normalize(y.riasec);
      const I = cosine(ctx.vec, uvec);
      const fb = ctx.fanBaho || {};
      const A = 0.6 * (fb[y.fan1] ?? 0.5) + 0.4 * (fb[y.fan2] ?? 0.5);
      const turi = ctx.moliya === "faqat_grant" ? "grant" : "kontrakt";
      const est = cutoffEstimate(y, turi, c);
      const estG = cutoffEstimate(y, "grant", c);
      const ball = ctx.ballFor ? ctx.ballFor(y) : (ctx.joriyBall ?? null);
      const sig = ctx.sigmaS || c.model.sigma_s_boshlangich;
      const P = (ball != null && est) ? admitProb(ball, sig, est.C, est.sigma) : null;
      const PG = (ball != null && estG) ? admitProb(ball, sig, estG.C, estG.sigma) : null;
      const M = ISTIQBOL[y.istiqbol] ?? 0.6;
      let V = 0.6;
      if (ctx.hudud && y.hududlar) {
        const yaqin = y.hududlar.includes(ctx.hudud) || y.hududlar.includes("*");
        V = yaqin ? 1 : (ctx.kochish ? 0.7 : 0.2);
      }
      // ehtimollik yo'q bo'lsa — qolgan vaznlar qayta taqsimlanadi
      const score = P != null
        ? w.I * I + w.A * A + w.P * P + w.M * M + w.V * V
        : (w.I * I + w.A * A + w.M * M + w.V * V) / (1 - w.P);
      let savat;
      if (P != null) savat = P < c.model.savat.orzu_max ? "orzu" : (P > c.model.savat.ishonchli_min ? "ishonchli" : "maqsad");
      else savat = RAQOBAT_SAVAT[y.raqobat] || "maqsad";
      out.push({ y, I, A, P, PG, M, V, ball, score, savat, cIndex: cIndex(ctx.code, codeOf(y.riasec)), est, estG });
    });
    out.sort((a, b) => b.score - a.score);
    return out;
  }

  // 5 talik savat: 1 orzu, 2 maqsad, 2 ishonchli (yetmasa — qolganlardan)
  function pickFive(ranked) {
    const want = { orzu: 1, maqsad: 2, ishonchli: 2 };
    const got = { orzu: [], maqsad: [], ishonchli: [] };
    ranked.forEach(r => { if (got[r.savat].length < want[r.savat]) got[r.savat].push(r); });
    let pick = [...got.orzu, ...got.maqsad, ...got.ishonchli];
    if (pick.length < 5) {
      ranked.forEach(r => { if (pick.length < 5 && !pick.includes(r)) pick.push(r); });
    }
    // ustuvorlik: orzu → maqsad → ishonchli
    const rank = { orzu: 0, maqsad: 1, ishonchli: 2 };
    return pick.sort((a, b) => rank[a.savat] - rank[b.savat] || b.score - a.score);
  }

  /* ---------- QADAM 4: blok optimizatsiyasi ---------- */

  function blockOptions(ranked, data, topN) {
    topN = topN || 40;
    const top = ranked.slice(0, topN);
    const groups = {};
    top.forEach(r => {
      const key = r.y.fan1 + "+" + r.y.fan2;
      if (!groups[key]) groups[key] = { key, fan1: r.y.fan1, fan2: r.y.fan2, items: [], jamiYonalish: 0 };
      groups[key].items.push(r);
    });
    data.yonalishlar.forEach(y => {
      const key = y.fan1 + "+" + y.fan2;
      if (groups[key]) groups[key].jamiYonalish++;
    });
    const list = Object.values(groups).map(g => {
      const top5 = g.items.slice(0, 5);
      const meanI = top5.reduce((s, r) => s + r.I, 0) / top5.length;
      const meanScore = top5.reduce((s, r) => s + r.score, 0) / top5.length;
      const hasP = top5.every(r => r.P != null);
      const pAny = hasP ? 1 - top5.reduce((p, r) => p * (1 - r.P), 1) : null;
      return { ...g, top5, meanI, meanScore, pAny, utility: meanScore * (pAny ?? 1) * Math.min(1, 0.6 + g.items.length / 10) };
    });
    list.sort((a, b) => b.utility - a.utility);
    return list;
  }

  /* ---------- QADAM 7: tayyorgarlik muddati ---------- */

  // o'rganish egri chizig'i: m0 → m1 uchun soat
  function hoursFor(H, m0, m1, r) {
    if (m1 <= m0) return 0;
    return (H / 3) * Math.log((1 - m0) / (1 - m1)) / (r || 1);
  }

  // Mavzular ro'yxatini blok bo'yicha yig'ish
  function topicsForBlock(block, data, mastery, sertifikatlar, c) {
    c = c || cfg();
    const fanlar = [[block.fan1, "fan1"], [block.fan2, "fan2"], ...c.majburiy_fanlar.map(f => [f, "majburiy"])];
    const out = [];
    fanlar.forEach(([fan, role]) => {
      const sert = (sertifikatlar || []).find(s => s.fan === fan && (s.daraja === "A+" || s.daraja === "A"));
      if (sert) return; // bu fandan test topshirilmaydi
      const tree = data.mavzular[fan];
      const n = c.savol[role], k = c.koef[role];
      const m0 = Math.max(0, Math.min(c.model.mastery_cap, mastery[fan] ?? 0));
      if (!tree) { // mavzu daraxti yo'q — bitta umumiy "mavzu"
        out.push({ id: fan + "_umumiy", fan, role, nom: "Umumiy tayyorgarlik", bolim: "", q: n, k, H: 150, m0, m: m0, hours: 0, gain: 0, order: 0 });
        return;
      }
      tree.mavzular.forEach((t, i) => {
        out.push({ id: t.id, fan, role, nom: t.nom, bolim: t.bolim, q: t.ulush * n, k, H: t.bazaviy_soat, m0, m: m0, hours: 0, gain: 0, order: i });
      });
    });
    return out;
  }

  // Ochko'z (greedy) taqsimot: har qadamda eng yuqori ball/soat beradigan mavzuga Δm qo'shiladi.
  // mode: {needGain} — kerakli ballgacha; yoki {budgetHours} — vaqt chegarasida maksimal ball
  function allocate(topics, sc, mode, c) {
    c = c || cfg();
    const g = c.model.g, cap = c.model.mastery_cap, step = 0.04;
    let gained = 0, hours = 0;
    const eff = (t) => {
      if (t.m + 1e-9 >= cap) return null;
      const m1 = Math.min(cap, t.m + step);
      const dh = hoursFor(t.H, t.m, m1, sc.r);
      const dg = t.q * t.k * (1 - g) * (m1 - t.m);
      return { m1, dh, dg, e: dg / dh };
    };
    for (let guard = 0; guard < 5000; guard++) {
      if (mode.needGain != null && gained >= mode.needGain - 1e-9) break;
      let best = null, bt = null;
      topics.forEach(t => { const x = eff(t); if (x && (!best || x.e > best.e)) { best = x; bt = t; } });
      if (!best) break;
      if (mode.budgetHours != null && hours + best.dh > mode.budgetHours) break;
      bt.m = best.m1; bt.hours += best.dh; bt.gain += best.dg;
      gained += best.dg; hours += best.dh;
    }
    return { gained, hours };
  }

  /* opts: {block, mastery, sertifikatlar, targetBall, weeklyHours, weeksAvailable, scenario}
     Natija: soatlar, haftalar, imkoniyat, fan bo'yicha taqsimot, haftalik reja */
  function prepPlan(opts, data, c) {
    c = c || cfg();
    const sc = c.model.ssenariylar[opts.scenario || "realistik"];
    const cur = totalBall(opts.block, opts.mastery, opts.sertifikatlar, c);
    const need = Math.max(0, opts.targetBall - cur.total);
    const topics = topicsForBlock(opts.block, data, opts.mastery, opts.sertifikatlar, c);

    const overhead = (h, weeks) => {
      const real = h / sc.eta;
      const rev = real * c.model.rho;
      const sin = Math.floor(Math.max(1, weeks) / c.model.sinov_har_hafta) * c.model.sinov_soat;
      return { real, rev, sin, total: real + rev + sin };
    };

    // 1) kerakli ballgacha
    const a = allocate(topics, sc, { needGain: need }, c);
    let weeks = 0, oh = overhead(a.hours, 1);
    for (let i = 0; i < 4; i++) { weeks = oh.total / Math.max(1, opts.weeklyHours); oh = overhead(a.hours, weeks); }
    const reached = a.gained + 1e-6 >= need;
    const feasible = reached && weeks <= opts.weeksAvailable;

    // 2) imkoniyat bo'lmasa: mavjud vaqtga sig'adigan maksimal ball
    let alt = null;
    if (!feasible) {
      const t2 = topicsForBlock(opts.block, data, opts.mastery, opts.sertifikatlar, c);
      const sin = Math.floor(opts.weeksAvailable / c.model.sinov_har_hafta) * c.model.sinov_soat;
      const budgetTheory = Math.max(0, (opts.weeksAvailable * opts.weeklyHours - sin) / (1 + c.model.rho) * sc.eta);
      const b = allocate(t2, sc, { budgetHours: budgetTheory }, c);
      const m2 = {}; Object.keys(opts.mastery).forEach(f => { m2[f] = opts.mastery[f]; });
      t2.forEach(t => { m2[t.fan] = m2[t.fan]; });
      alt = { maxBall: cur.total + b.gained, hours: budgetTheory, topics: t2, byFan: byFan(t2) };
      // fan bo'yicha yangi o'zlashtirish (mavzularning q-vaznli o'rtachasi)
      alt.mastery = masteryByFan(t2, opts.mastery);
    }

    return {
      scenario: sc, current: cur, need, target: opts.targetBall,
      theoryHours: a.hours, gained: a.gained, reached,
      realHours: oh.real, reviewHours: oh.rev, mockHours: oh.sin, totalHours: oh.total,
      weeks, months: weeks / 4.345, feasible,
      topics: topics.filter(t => t.hours > 0).sort((x, y) => y.gain / y.hours - x.gain / x.hours),
      byFan: byFan(topics), finalMastery: masteryByFan(topics, opts.mastery),
      alt,
      weeklyPlan: weeklyPlan(topics, oh, opts.weeklyHours, sc, c)
    };
  }

  function byFan(topics) {
    const m = {};
    topics.forEach(t => {
      if (!m[t.fan]) m[t.fan] = { fan: t.fan, role: t.role, hours: 0, gain: 0 };
      m[t.fan].hours += t.hours; m[t.fan].gain += t.gain;
    });
    return Object.values(m).sort((a, b) => b.hours - a.hours);
  }
  function masteryByFan(topics, base) {
    const acc = {}, out = Object.assign({}, base);
    topics.forEach(t => { if (!acc[t.fan]) acc[t.fan] = { q: 0, mq: 0 }; acc[t.fan].q += t.q; acc[t.fan].mq += t.q * t.m; });
    Object.keys(acc).forEach(f => { out[f] = acc[f].q ? acc[f].mq / acc[f].q : base[f]; });
    return out;
  }

  // Haftalik reja: samaradorlik tartibida mavzular haftalarga joylanadi
  function weeklyPlan(topics, oh, weeklyHours, sc, c) {
    const items = topics.filter(t => t.hours > 0)
      .map(t => ({ ...t, real: t.hours / sc.eta }))
      .sort((a, b) => b.gain / b.hours - a.gain / a.hours);
    const weeks = [];
    const perWeekStudy = Math.max(1, weeklyHours) / (1 + c.model.rho);
    let wk = { n: 1, items: [], study: 0 }, i = 0, carry = 0;
    while (i < items.length) {
      const t = items[i];
      const left = t.real - carry;
      const room = perWeekStudy - wk.study;
      if (left <= room + 1e-9) {
        wk.items.push({ id: t.id, fan: t.fan, nom: t.nom, bolim: t.bolim, hours: left });
        wk.study += left; carry = 0; i++;
      } else {
        if (room > 0.25) { wk.items.push({ id: t.id, fan: t.fan, nom: t.nom, bolim: t.bolim, hours: room, davom: true }); wk.study += room; carry += room; }
        wk.review = wk.study * c.model.rho;
        wk.sinov = wk.n % c.model.sinov_har_hafta === 0;
        weeks.push(wk); wk = { n: wk.n + 1, items: [], study: 0 };
      }
      if (weeks.length > 200) break;
    }
    if (wk.items.length) { wk.review = wk.study * c.model.rho; wk.sinov = wk.n % c.model.sinov_har_hafta === 0; weeks.push(wk); }
    return weeks;
  }

  /* ---------- yordamchi ---------- */

  function weeksBetween(fromISO, toISO) {
    const a = new Date(fromISO), b = new Date(toISO);
    return Math.max(0, (b - a) / (7 * 24 * 3600 * 1000));
  }

  global.KompasEngine = {
    KEYS, normalize, cosine, phi, cIndex, codeOf,
    riasecScores, ballFromMastery, fanBall, totalBall,
    cutoffEstimate, admitProb, simulateChoices, bestOrder,
    matchDirections, pickFive, blockOptions,
    hoursFor, topicsForBlock, allocate, prepPlan, weeksBetween
  };
})(typeof window !== "undefined" ? window : globalThis);

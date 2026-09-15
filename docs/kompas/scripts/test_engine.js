#!/usr/bin/env node
/* Kompas yadrosi uchun tekshiruvlar. Ishlatish: node docs/kompas/scripts/test_engine.js */
const path = require("path");
global.window = globalThis;
require(path.join(__dirname, "../js/config.js"));
require(path.join(__dirname, "../js/engine.js"));
const E = window.KompasEngine, C = window.KOMPAS_CONFIG;

let fails = 0, n = 0;
const ok = (cond, msg) => { n++; if (!cond) { fails++; console.log("  ✗ " + msg); } };
const near = (a, b, tol, msg) => ok(Math.abs(a - b) <= tol, `${msg}: ${a} ≠ ${b} (±${tol})`);

/* --- Φ --- */
near(E.phi(0), 0.5, 1e-6, "Φ(0)");
near(E.phi(1.96), 0.975, 5e-4, "Φ(1.96)");
near(E.phi(-3.1), 0.00097, 2e-4, "Φ(−3.1)");
ok(E.phi(6) > 0.9999 && E.phi(-6) < 1e-4, "Φ chekkalari");

/* --- RIASEC --- */
const items = []; ["R", "I", "A", "S", "E", "C"].forEach(k => { for (let i = 0; i < 10; i++) items.push({ id: k + i, shkala: k }); });
const ans = {}; items.forEach(it => { ans[it.id] = it.shkala === "S" ? 5 : it.shkala === "I" ? 4 : 2; });
const r = E.riasecScores(ans, items);
ok(r.code.startsWith("SI"), "kod S-I bilan boshlanadi: " + r.code);
near(r.pct.S, 1, 1e-9, "S foizi");
near(Object.values(r.vec).reduce((s, v) => s + v * v, 0), 1, 1e-9, "vektor normasi");
ok(r.answered === 60 && r.total === 60, "javoblar soni");
// bir xil javob hammasiga — profil yassi, lekin xatosiz
const flat = {}; items.forEach(it => { flat[it.id] = 3; });
const rf = E.riasecScores(flat, items);
near(E.cosine(rf.vec, rf.vec), 1, 1e-9, "yassi profil kosinusi");
// C-indeks
ok(E.cIndex("RIA", "RIA") === 18, "C-indeks bir xil kod = 18");
near(E.profileSim({ R: .9, I: .8, A: .2, S: .1, E: .3, C: .6 }, { R: .9, I: .8, A: .2, S: .1, E: .3, C: .6 }), 1, 1e-9, "profileSim bir xil = 1");
near(E.profileSim({ R: 1, I: 0, A: 0, S: 0, E: 0, C: 0 }, { R: 0, I: 0, A: 0, S: 1, E: 0, C: 0 }), 0.4, 1e-9, "profileSim qarama-qarshi < 0,5");
near(E.profileSim({ R: .5, I: .5, A: .5, S: .5, E: .5, C: .5 }, { R: 1, I: 0, A: 0, S: 0, E: 0, C: 0 }), 0.5, 1e-9, "yassi profil = 0,5");
ok(E.cIndex("RIA", "SEC") === 0, "C-indeks qarama-qarshi = 0");

/* --- ball modeli --- */
const block = { fan1: "biologiya", fan2: "kimyo" };
const m0 = { biologiya: 0, kimyo: 0, ona_tili: 0, matematika: 0, tarix: 0 };
near(E.totalBall(block, m0, []).total, 189 * 0.25, 1e-6, "hech narsa bilmagan = 47,25");
const m1 = { biologiya: 1, kimyo: 1, ona_tili: 1, matematika: 1, tarix: 1 };
near(E.totalBall(block, m1, []).total, 189, 1e-6, "hammasi = 189");
const mA = { biologiya: .35, kimyo: .30, ona_tili: .6, matematika: .4, tarix: .5 };
near(E.totalBall(block, mA, []).total, 98.2, 0.1, "ALGORITM.md namunasi 98,2");
// sertifikat
const sert = E.totalBall(block, mA, [{ fan: "biologiya", daraja: "A" }]);
near(sert.rows[0].ball, 93, 1e-9, "A sertifikat = 93");
ok(sert.rows[0].sertifikat === "A", "sertifikat belgisi");

/* --- o'tish balli va ehtimollik --- */
const y = { otish_taxmin: { grant: [150, 178], kontrakt: [118, 150] }, ishonch: "taxminiy" };
const est = E.cutoffEstimate(y, "grant");
near(est.C, 164, 1e-9, "Ĉ grant");
ok(est.sigma >= C.model.sigma_c_min, "σ_c minimal");
ok(E.cutoffEstimate({ otish_taxmin: {} }, "grant") === null, "oraliq yo'q → null");
near(E.admitProb(164, 12, 164, est.sigma), 0.5, 1e-6, "μ = Ĉ → 50%");
ok(E.admitProb(190, 8, 164, 6) > 0.99, "juda yuqori ball → ~1");
ok(E.admitProb(100, 8, 164, 6) < 0.001, "juda past ball → ~0");

/* --- Monte-Carlo --- */
const ch = [
  { C_grant: 150, s_grant: 6, C_kontrakt: 120, s_kontrakt: 6, kontraktMumkin: true },
  { C_grant: 130, s_grant: 6, C_kontrakt: 105, s_kontrakt: 6, kontraktMumkin: true }
];
const sim = E.simulateChoices(ch, 140, 8, 4000, 1, false);
ok(Math.abs(sim.any - 1) < 0.01, "140 ball: kamida bittasiga ~100%");
ok(sim.perChoice[0].kontrakt > 0.7, "tanlov tartibi: 1-kontrakt avval");
const simG = E.simulateChoices(ch, 140, 8, 4000, 1, true);
ok(simG.perChoice[1].grant > simG.perChoice[0].kontrakt, "grant ustuvorligi: 2-grant 1-kontraktdan oldin");
const same1 = E.simulateChoices(ch, 140, 8, 2000, 5, true), same2 = E.simulateChoices(ch, 140, 8, 2000, 5, true);
ok(JSON.stringify(same1) === JSON.stringify(same2), "deterministik urug'");
const bo = E.bestOrder(ch, 140, 8, () => 1, true);
ok(bo && bo.order.length === 2, "bestOrder ishlaydi");

/* --- moslik --- */
const data = {
  yonalishlar: [
    { id: "a", fan1: "biologiya", fan2: "kimyo", riasec: { R: .3, I: .8, A: .1, S: .9, E: .2, C: .3 }, istiqbol: "yuqori", raqobat: "yuqori", otish_taxmin: { grant: [160, 180], kontrakt: [130, 155] }, hududlar: ["*"] },
    { id: "b", fan1: "matematika", fan2: "fizika", riasec: { R: .7, I: .8, A: .2, S: .1, E: .3, C: .6 }, istiqbol: "yuqori", raqobat: "orta", otish_taxmin: { grant: [130, 160], kontrakt: [100, 130] }, hududlar: ["*"] },
    { id: "c", fan1: "ingliz_tili", fan2: "ona_tili_adabiyot", sertifikat: true, riasec: { R: .1, I: .4, A: .7, S: .8, E: .3, C: .3 }, istiqbol: "orta", raqobat: "past", otish_taxmin: { grant: [110, 140], kontrakt: [80, 110] }, hududlar: ["*"] }
  ], mavzular: {}
};
const ctx = { vec: r.vec, code: r.code, moliya: "kontrakt_mumkin", hudud: "Namangan", kochish: true };
const ranked = E.matchDirections(ctx, data, "muvozanat");
ok(ranked.length === 3 && ranked[0].y.id === "a", "S-I profil → a birinchi: " + ranked.map(x => x.y.id).join(","));
ok(ranked.every(x => x.P === null), "diagnostikasiz P = null");
ok(ranked.every(x => ["orzu", "maqsad", "ishonchli"].includes(x.savat)), "savatlar");
const ctx2 = Object.assign({}, ctx, { ballFor: (yy) => yy.fan1 === "biologiya" ? 150 : null });
const ranked2 = E.matchDirections(ctx2, data, "muvozanat");
ok(ranked2.find(x => x.y.id === "a").P > 0.5 && ranked2.find(x => x.y.id === "b").P === null, "ballFor faqat mos blokda");
ok(E.matchDirections(Object.assign({}, ctx, { sertifikatsiz: true }), data).length === 2, "sertifikat filtri");
const five = E.pickFive(ranked);
ok(five.length === 3, "pickFive kam ma'lumotda hammasini qaytaradi");
const blocks = E.blockOptions(ranked, data, 40);
ok(blocks.length === 3 && blocks[0].jamiYonalish === 1, "blockOptions");

/* --- tayyorgarlik --- */
near(E.hoursFor(180, .35, .80, 1), 70.7, 0.2, "hoursFor namunasi");
ok(E.hoursFor(100, .5, .5, 1) === 0 && E.hoursFor(100, .6, .5, 1) === 0, "hoursFor nol/salbiy");
const plan = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 145, weeklyHours: 10, weeksAvailable: 43, scenario: "realistik" }, data);
ok(plan.reached && plan.feasible, "namuna: 145 ball 43 haftada erishiladi");
near(plan.current.total + plan.gained, 145, 1.5, "yig'ilgan ball maqsadga yetadi");
ok(plan.byFan[0].fan === "biologiya", "eng ko'p soat biologiyaga (3,1)");
ok(plan.weeklyPlan.length >= 1 && plan.weeklyPlan[0].items.length > 0, "haftalik reja bor");
ok(plan.totalHours > plan.realHours && plan.realHours > plan.theoryHours, "soat qatlamlari tartibi");
const tight = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 175, weeklyHours: 4, weeksAvailable: 8, scenario: "ehtiyotkor" }, data);
ok(!tight.feasible && tight.alt && tight.alt.maxBall > tight.current.total && tight.alt.maxBall < 175, "ulgurmasa — alt.maxBall oraliqda");
const impossible = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 189, weeklyHours: 20, weeksAvailable: 100, scenario: "intensiv" }, data);
ok(!impossible.reached, "189 ball chegara sababli erishilmaydi");
const withSert = E.prepPlan({ block, mastery: mA, sertifikatlar: [{ fan: "biologiya", daraja: "A+" }], targetBall: 145, weeklyHours: 10, weeksAvailable: 43, scenario: "realistik" }, data);
ok(!withSert.byFan.some(f => f.fan === "biologiya"), "A+ sertifikat: biologiyaga soat ajratilmaydi");
ok(withSert.totalHours < plan.totalHours, "sertifikat vaqtni kamaytiradi");
// ssenariylar tartibi
const pe = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 145, weeklyHours: 10, weeksAvailable: 43, scenario: "ehtiyotkor" }, data);
const pi = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 145, weeklyHours: 10, weeksAvailable: 43, scenario: "intensiv" }, data);
ok(pe.totalHours > plan.totalHours && plan.totalHours > pi.totalHours, "ehtiyotkor > realistik > intensiv");
// mavzu daraxti bilan
const data2 = { yonalishlar: [], mavzular: { biologiya: { mavzular: [
  { id: "b1", bolim: "A", nom: "oson-ko'p", ulush: 0.5, bazaviy_soat: 4, qiyinlik: .3 },
  { id: "b2", bolim: "A", nom: "qiyin-kam", ulush: 0.1, bazaviy_soat: 12, qiyinlik: .8 },
  { id: "b3", bolim: "B", nom: "o'rta", ulush: 0.4, bazaviy_soat: 8, qiyinlik: .5 } ] } } };
const p2 = E.prepPlan({ block, mastery: mA, sertifikatlar: [], targetBall: 120, weeklyHours: 10, weeksAvailable: 43, scenario: "realistik" }, data2);
ok(p2.topics[0].id === "b1", "eng samarali mavzu birinchi: " + p2.topics.map(t => t.id).join(","));
const q = E.topicsForBlock(block, data2, mA, []).filter(t => t.fan === "biologiya").reduce((s, t) => s + t.q, 0);
near(q, 30, 1e-9, "mavzular savollari yig'indisi = 30");

/* --- haftalar --- */
near(E.weeksBetween("2026-09-14", "2027-07-14"), 43.3, 0.2, "haftalar soni");
ok(E.weeksBetween("2027-07-14", "2026-09-14") === 0, "o'tgan sana → 0");

console.log(`\n${n - fails}/${n} tekshiruv o'tdi`);
process.exit(fails ? 1 : 0);

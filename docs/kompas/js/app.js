/* Kompas — ilova (ekranlar, holat, marshrutlash). Hisob-kitob: engine.js; sozlamalar: config.js */
(function () {
  "use strict";
  const E = window.KompasEngine, C = window.KOMPAS_CONFIG;
  const FAN = window.KOMPAS_FANLAR || {}, OTM = window.KOMPAS_OTMLAR || [], HUD = window.KOMPAS_HUDUDLAR || [];
  const DATA = { yonalishlar: window.KOMPAS_YONALISHLAR || [], mavzular: window.KOMPAS_MAVZULAR || {}, riasec: window.KOMPAS_RIASEC || [] };
  const TODAY = new Date().toISOString().slice(0, 10);
  const app = document.getElementById("app"), stepsEl = document.getElementById("steps");

  /* ---------- holat ---------- */
  const KEY = "kompas.v1";
  const DEFAULT = () => ({
    profil: { sinf: 11, hudud: "Toshkent shahri", kochish: true, moliya: "kontrakt_mumkin", haftalik_soat: 10, imtihon_sana: C.kalendar.test_boshi, sertifikatlar: [] },
    answers: {}, qi: 0, riasec: null, rejim: "muvozanat", tanlov: [], block: null,
    mastery: {}, sinovBall: null, target: { id: null, ball: null, turi: "kontrakt" }, scenario: "realistik", grantUstuvor: true
  });
  let S = DEFAULT();
  try { const raw = localStorage.getItem(KEY); if (raw) S = Object.assign(DEFAULT(), JSON.parse(raw)); } catch (e) { /* xotira yo'q — sessiya ichida ishlaydi */ }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* sukut */ } };

  /* ---------- yordamchilar ---------- */
  const h = (s) => String(s ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
  const fmt = (n, d = 1) => (n == null || isNaN(n)) ? "—" : Number(n).toFixed(d).replace(".", ",");
  const pct = (p) => p == null ? "—" : Math.round(p * 100) + "%";
  const fanNom = (id) => (FAN[id] && FAN[id].nom) || id;
  const fanQisqa = (id) => (FAN[id] && FAN[id].qisqa) || id;
  const otmById = (id) => OTM.find(o => o.id === id);
  const yById = (id) => DATA.yonalishlar.find(y => y.id === id);
  // uzun mavzu nomlarini ro'yxatda qisqartirish (to'liq matn title da)
  const shortNom = (nom, max = 64) => {
    nom = String(nom || "");
    if (nom.length <= max) return nom;
    const cut = Math.max(nom.lastIndexOf(";", max), nom.lastIndexOf(",", max), nom.lastIndexOf(":", max));
    return (cut > 24 ? nom.slice(0, cut) : nom.slice(0, max - 1).replace(/\s+\S*$/, "")) + "…";
  };
  const go = (p) => { location.hash = "#" + p; };
  const HOLLAND = {
    R: { nom: "Amaliy", tavsif: "qo'l bilan, texnika va tabiat bilan ishlash" },
    I: { nom: "Tadqiqotchi", tavsif: "tahlil qilish, sabab-oqibatni tushunish, masala yechish" },
    A: { nom: "Ijodkor", tavsif: "yangi narsa yaratish, o'zini ifodalash, dizayn va san'at" },
    S: { nom: "Ijtimoiy", tavsif: "odamlarga yordam berish, o'qitish, davolash, muloqot" },
    E: { nom: "Tashabbuskor", tavsif: "boshqarish, ishontirish, biznes yuritish, yetakchilik" },
    C: { nom: "Tartibli", tavsif: "aniqlik, ma'lumot va raqamlar bilan tizimli ishlash" }
  };
  let toastT;
  function toast(msg) {
    document.querySelectorAll(".toast").forEach(t => t.remove());
    const t = document.createElement("div"); t.className = "toast"; t.textContent = msg; document.body.appendChild(t);
    clearTimeout(toastT); toastT = setTimeout(() => t.remove(), 2600);
  }

  /* ---------- hisoblangan qiymatlar ---------- */
  const hasMastery = (fan) => S.mastery[fan] != null;
  function ballFor(y) {
    if (!hasMastery(y.fan1) || !hasMastery(y.fan2)) return null;
    if (!C.majburiy_fanlar.every(hasMastery)) return null;
    return E.totalBall({ fan1: y.fan1, fan2: y.fan2 }, S.mastery, S.profil.sertifikatlar).total;
  }
  function ctx() {
    const fb = {};
    Object.keys(S.mastery).forEach(f => { fb[f] = S.mastery[f]; });
    return {
      vec: S.riasec.vec, code: S.riasec.code, fanBaho: Object.keys(fb).length ? fb : null,
      moliya: S.profil.moliya, hudud: S.profil.hudud, kochish: S.profil.kochish,
      sigmaS: S.sinovBall != null ? 9 : C.model.sigma_s_boshlangich, ballFor
    };
  }
  let _rankCache = null;
  function ranked() {
    const k = JSON.stringify([S.rejim, S.mastery, S.profil, S.riasec && S.riasec.code, S.sinovBall]);
    if (_rankCache && _rankCache.k === k) return _rankCache.v;
    const v = S.riasec ? E.matchDirections(ctx(), DATA, S.rejim) : [];
    _rankCache = { k, v };
    return v;
  }
  const rankedById = (id) => ranked().find(r => r.y.id === id);
  function weeksLeft() { return E.weeksBetween(TODAY, S.profil.imtihon_sana); }
  function currentBall() { return S.block && C.majburiy_fanlar.concat([S.block.fan1, S.block.fan2]).every(hasMastery) ? E.totalBall(S.block, S.mastery, S.profil.sertifikatlar) : null; }

  /* ---------- marshrutlash ---------- */
  const STEPS = [
    { p: "/profil", nom: "Profil", ok: () => true },
    { p: "/test", nom: "Test", ok: () => true },
    { p: "/natija", nom: "Natija", ok: () => !!S.riasec },
    { p: "/fanlar", nom: "Fanlar", ok: () => !!S.riasec },
    { p: "/daraja", nom: "Daraja", ok: () => !!S.block },
    { p: "/reja", nom: "Reja", ok: () => !!currentBall() }
  ];
  function renderSteps(path) {
    stepsEl.innerHTML = STEPS.map((s, i) => {
      const idx = STEPS.findIndex(x => x.p === path);
      const cls = s.p === path ? "on" : (!s.ok() ? "off" : (i < idx ? "done" : ""));
      return `<a href="#${s.p}" class="${cls}" ${cls === "off" ? 'aria-disabled="true" tabindex="-1"' : ""}>${i + 1} ${s.nom}</a>`;
    }).join("");
  }
  const VIEWS = {};
  let lastPath = null;
  function render() {
    const path = (location.hash.replace(/^#/, "") || "/");
    const si = STEPS.findIndex(s => s.p === path);
    if (si >= 0 && !STEPS[si].ok()) {
      let j = si - 1; while (j > 0 && !STEPS[j].ok()) j--;
      go(STEPS[Math.max(0, j)].p); return;
    }
    renderSteps(path);
    const v = VIEWS[path] || VIEWS["/"];
    app.innerHTML = `<div class="view">${v.html()}</div>`;
    if (v.mount) v.mount();
    if (path !== lastPath) window.scrollTo({ top: 0 });
    lastPath = path;
  }
  window.addEventListener("hashchange", render);

  /* ---------- umumiy bo'laklar ---------- */
  function rulerHTML(block) {
    const s = C.savol, k = C.koef, T = C.max_ball;
    const seg = (n, kk, cls, label) => `<div class="${cls}" style="width:${(n * kk / T * 100).toFixed(2)}%" title="${h(label)}">${fmt(n * kk, 0)}</div>`;
    return `<div class="ruler" role="img" aria-label="189 ball taqsimoti">
      ${seg(s.fan1, k.fan1, "s1", "1-fan")}${seg(s.fan2, k.fan2, "s2", "2-fan")}${seg(s.majburiy, k.majburiy, "s3", "Ona tili")}${seg(s.majburiy, k.majburiy, "s3", "Matematika")}${seg(s.majburiy, k.majburiy, "s3", "O'zbekiston tarixi")}
    </div>
    <div class="ruler-legend">
      <div><b>${fmt(k.fan1)} × ${s.fan1}</b><span>${block ? h(fanNom(block.fan1)) : "1-ixtisoslik fani"}</span></div>
      <div><b>${fmt(k.fan2)} × ${s.fan2}</b><span>${block ? h(fanNom(block.fan2)) : "2-ixtisoslik fani"}</span></div>
      <div><b>${fmt(k.majburiy)} × ${s.majburiy}</b><span>Ona tili</span></div>
      <div><b>${fmt(k.majburiy)} × ${s.majburiy}</b><span>Matematika</span></div>
      <div><b>${fmt(k.majburiy)} × ${s.majburiy}</b><span>O'zbekiston tarixi</span></div>
    </div>`;
  }
  function radarSVG(pctv) {
    const cx = 160, cy = 160, R = 110, keys = E.KEYS;
    const pt = (i, r) => { const a = -Math.PI / 2 + i * Math.PI / 3; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; };
    const ring = (r) => keys.map((_, i) => pt(i, r).map(v => v.toFixed(1)).join(",")).join(" ");
    const area = keys.map((k, i) => pt(i, R * Math.max(0.04, pctv[k] || 0)).map(v => v.toFixed(1)).join(",")).join(" ");
    return `<svg class="radar" viewBox="0 0 320 320" role="img" aria-label="RIASEC profil diagrammasi">
      ${[0.25, 0.5, 0.75, 1].map(f => `<polygon class="grid" points="${ring(R * f)}"/>`).join("")}
      ${keys.map((_, i) => { const [x, y] = pt(i, R); return `<line class="axis" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`; }).join("")}
      <polygon class="area" points="${area}"/>
      ${keys.map((k, i) => { const [x, y] = pt(i, R * Math.max(0.04, pctv[k] || 0)); return `<circle class="dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3.5"/>`; }).join("")}
      ${keys.map((k, i) => { const [x, y] = pt(i, R + 30); return `<text class="k" x="${x.toFixed(1)}" y="${(y + 4).toFixed(1)}" text-anchor="middle">${k}</text><text x="${x.toFixed(1)}" y="${(y + 18).toFixed(1)}" text-anchor="middle">${HOLLAND[k].nom}</text>`; }).join("")}
    </svg>`;
  }
  const tagSavat = (s) => `<span class="tag ${s}">${{ orzu: "orzu", maqsad: "maqsad", ishonchli: "ishonchli" }[s]}</span>`;
  const fanChips = (y) => `<span class="chip k1">${h(fanQisqa(y.fan1))} ×${fmt(C.koef.fan1)}</span><span class="chip k2">${h(fanQisqa(y.fan2))} ×${fmt(C.koef.fan2)}</span>`;
  const flags = (y) => (y.sertifikat ? `<span class="tag flag">sertifikat</span>` : "") + (y.ijodiy ? `<span class="tag flag">ijodiy imtihon</span>` : "") + (y.ishonch === "tekshirilsin" ? `<span class="tag info" title="Ma'lumot rasmiy manba bilan tasdiqlanmagan">tekshirilsin</span>` : "");
  const footer = () => `<footer>
    <p>Ma'lumotlar yangilangan: <span class="mono">${h(C.yangilangan)}</span> · ${DATA.yonalishlar.length} yo'nalish · ${OTM.length} OTM · Qabul sikli ${h(C.oquv_yili)}</p>
    <p>Kompas rasmiy manba emas. O'tish ballari — taxminiy oraliqlar, kirish ehtimoli — model bahosi, kafolat emas. Yakuniy qaror uchun <a href="https://uzbmb.uz" rel="noopener">uzbmb.uz</a> va <a href="https://my.uzbmb.uz" rel="noopener">my.uzbmb.uz</a>. <a href="#/manba">Manbalar va model haqida</a></p>
  </footer>`;

  /* ================= BOSH ================= */
  VIEWS["/"] = {
    html: () => `
    <section class="hero">
      <div>
        <span class="eyebrow">${h(C.oquv_yili)} qabuli · Oscar Ta'lim</span>
        <h1 style="margin-top:12px">Qiziqishdan universitetgacha — hisoblab beradigan yo'l.</h1>
        <p class="lede">Nimaga qiziqishingizni ayting. Kompas sizga mos yo'nalishlarni topadi, o'sha yo'nalishga qaysi fanlardan imtihon topshirilishini ko'rsatadi va shu fanlardan <em>qancha vaqt</em> tayyorlansangiz kira olishingizni o'lchab beradi.</p>
        <div class="cta">
          <a class="btn primary lg" href="#/profil">${S.riasec ? "Davom etish" : "Boshlash"}</a>
          <a class="btn ghost" href="#/manba">Qanday ishlaydi?</a>
          <small>≈ 12 daqiqa · ro'yxatdan o'tish shart emas</small>
        </div>
      </div>
      <div class="hero-vis">
        <div class="card">
          <span class="eyebrow">Kirish imtihoni — ${C.max_ball} ball</span>
          <div style="height:10px"></div>
          ${rulerHTML(null)}
        </div>
        <div class="note"><b>1-fandagi bitta savol = O'zbekiston tarixidagi 2,8 ta savol.</b> Tayyorgarlik vaqti «qaysi fan yoqadi» bo'yicha emas, har soatning ball qiymati bo'yicha taqsimlanadi.</div>
      </div>
    </section>
    <section class="three">
      <div><span class="q">Qaysi yo'nalish?</span><h3>Qiziqish → yo'nalish</h3><p>60 savollik xalqaro RIASEC testi. Natija — sizning profilingiz va unga mos ${DATA.yonalishlar.length} yo'nalishdan eng yaqinlari, 5 talik tanlov strategiyasi bilan.</p></div>
      <div><span class="q">Qaysi fanlar?</span><h3>Yo'nalish → blok</h3><p>Har yo'nalishning 1- va 2-fani. Va teskari masala: qaysi fanlar bloki sizga eng ko'p yaxshi yo'nalishni ochadi — iyundagi qaytarib bo'lmas qaror uchun.</p></div>
      <div><span class="q">Qancha vaqt?</span><h3>Farq → muddat</h3><p>Hozirgi darajangiz va kerakli ball orasidagi farq mavzularga bo'linadi. Natija: soat, hafta, oy — uch ssenariyda, imtihon sanasiga solishtirib.</p></div>
    </section>
    <section class="why">
      <div>
        <span class="eyebrow">Nega hozir</span>
        <h2 style="margin-top:8px">Imtihongacha <span class="mono">${Math.round(weeksLeft())}</span> hafta bor</h2>
        <p class="muted" style="margin-top:10px">Qabul «avval test — so'ng tanlov» tamoyilida ishlaydi. Iyunda blok tanlanadi, iyulda test, avgustda 5 ta tanlov. Uchalasi ham — hisoblanadigan qaror. Yaxshi reja 4–6 oy oladi; hozir boshlagan o'quvchida zaxira qoladi.</p>
      </div>
      <div class="tl">
        <div><span>5–25 iyun</span><span>Ro'yxatdan o'tish, <b>fanlar blokini</b> tanlash</span></div>
        <div><span>14–28 iyul</span><span>Test sinovlari, natija ertasi kuni</span></div>
        <div><span>25 iyul – 8 avg</span><span><b>5 tagacha</b> OTM + yo'nalish, ustuvorlik tartibida</span></div>
        <div><span>~15 avgust</span><span>Mandat: grant va kontrakt taqsimoti</span></div>
      </div>
    </section>
    ${footer()}`
  };

  /* ================= PROFIL ================= */
  VIEWS["/profil"] = {
    html: () => {
      const p = S.profil;
      const seg = (name, opts, val) => `<div class="seg" role="group">${opts.map(o => `<button type="button" data-seg="${name}" data-v="${h(o[0])}" aria-pressed="${String(val) === String(o[0])}">${h(o[1])}</button>`).join("")}</div>`;
      const sertRows = p.sertifikatlar.map((s, i) => `<div class="sert-row">
          <select data-sert="fan" data-i="${i}" aria-label="Sertifikat fani">${Object.keys(FAN).filter(f => f !== "ijodiy").map(f => `<option value="${f}" ${s.fan === f ? "selected" : ""}>${h(fanNom(f))}</option>`).join("")}</select>
          <select data-sert="daraja" data-i="${i}" aria-label="Daraja">${Object.keys(C.sertifikat_ulush).map(d => `<option ${s.daraja === d ? "selected" : ""}>${d}</option>`).join("")}</select>
          <button type="button" class="btn" data-sert="del" data-i="${i}" aria-label="O'chirish">✕</button>
        </div>`).join("");
      return `
      <div class="page-head"><span class="eyebrow">1-qadam</span><h1>Sharoitingiz</h1><p>Bu javoblar tavsiyalarni filtrlaydi: siz o'qiy olmaydigan variantlar umuman ko'rsatilmaydi.</p></div>
      <div class="card">
        <div class="form-grid">
          <div class="field"><span class="lbl">Sinf</span>${seg("sinf", [[9, "9"], [10, "10"], [11, "11"], ["bitirgan", "Bitirganman"]], p.sinf)}</div>
          <div class="field"><label for="hudud">Hududingiz</label><select id="hudud">${HUD.map(x => `<option ${p.hudud === x ? "selected" : ""}>${h(x)}</option>`).join("")}</select></div>
          <div class="field"><span class="lbl">Boshqa shaharga ko'chib o'qiy olasizmi?</span><label class="toggle"><input type="checkbox" id="kochish" ${p.kochish ? "checked" : ""}><span>${p.kochish ? "Ha, mumkin" : "Yo'q, faqat o'z hududim"}</span></label></div>
          <div class="field"><span class="lbl">Moliya</span>${seg("moliya", [["faqat_grant", "Faqat grant"], ["kontrakt_mumkin", "Kontrakt ham mumkin"]], p.moliya)}<span class="hint">«Faqat grant» — kontrakt o'rni yo'q yo'nalishlar ko'rsatilmaydi va ehtimollik grant bo'yicha hisoblanadi.</span></div>
          <div class="field"><label for="soat">Haftasiga tayyorgarlikka ajrata oladigan vaqt</label>
            <div class="range-row"><input type="range" id="soat" min="3" max="30" step="1" value="${p.haftalik_soat}"><output for="soat" id="soat-out">${p.haftalik_soat} soat</output></div>
            <span class="hint">Maktab va darslardan tashqari, haqiqatan o'tiradigan soat. Rostini yozing — reja shunga quriladi.</span></div>
          <div class="field"><label for="sana">Imtihon sanasi</label><input type="date" id="sana" value="${h(p.imtihon_sana)}" min="${TODAY}"><span class="hint">Standart: ${h(C.kalendar.test_boshi)} (test sinovlarining birinchi kuni). Milliy sertifikat topshirmoqchi bo'lsangiz — o'sha sanani qo'ying.</span></div>
          <div class="field wide"><span class="lbl">Mavjud milliy sertifikatlar</span>
            <span class="hint">Sertifikat bo'lsa o'sha fandan test topshirilmaydi: A+/A — maksimal ball, B+…C — proporsional. Bu tayyorgarlik vaqtini keskin kamaytiradi.</span>
            <div class="stack" id="sert-list">${sertRows || `<span class="muted small">Hozircha yo'q</span>`}</div>
            <div><button type="button" class="btn" id="sert-add">+ Sertifikat qo'shish</button></div>
          </div>
        </div>
      </div>
      <div class="actions"><a class="btn primary lg" href="#/test">${S.riasec ? "Testga o'tish" : "Qiziqish testiga o'tish"} →</a><span class="muted small">Test: 60 ta qisqa savol, ≈ 8 daqiqa</span></div>
      ${footer()}`;
    },
    mount: () => {
      const p = S.profil;
      app.querySelectorAll("[data-seg]").forEach(b => b.addEventListener("click", () => {
        const v = b.dataset.v; p[b.dataset.seg] = isNaN(v) ? v : Number(v); save(); render();
      }));
      app.querySelector("#hudud").addEventListener("change", e => { p.hudud = e.target.value; save(); });
      app.querySelector("#kochish").addEventListener("change", e => { p.kochish = e.target.checked; save(); render(); });
      const soat = app.querySelector("#soat"), out = app.querySelector("#soat-out");
      soat.addEventListener("input", () => { out.textContent = soat.value + " soat"; });
      soat.addEventListener("change", () => { p.haftalik_soat = Number(soat.value); save(); });
      app.querySelector("#sana").addEventListener("change", e => { if (e.target.value) { p.imtihon_sana = e.target.value; save(); } });
      app.querySelector("#sert-add").addEventListener("click", () => { p.sertifikatlar.push({ fan: "ingliz_tili", daraja: "B+" }); save(); render(); });
      app.querySelectorAll("[data-sert]").forEach(el => el.addEventListener(el.tagName === "BUTTON" ? "click" : "change", () => {
        const i = Number(el.dataset.i);
        if (el.dataset.sert === "del") p.sertifikatlar.splice(i, 1);
        else p.sertifikatlar[i][el.dataset.sert] = el.value;
        save(); render();
      }));
    }
  };

  /* ================= TEST ================= */
  VIEWS["/test"] = {
    html: () => {
      const Q = DATA.riasec;
      if (!Q.length) return `<div class="note warn"><b>Savollar banki yuklanmagan.</b> data/riasec_savollar.js fayli topilmadi.</div>${footer()}`;
      const i = Math.min(S.qi, Q.length - 1), q = Q[i];
      const answered = Object.keys(S.answers).filter(k => S.answers[k]).length;
      const done = answered >= Q.length;
      const scale = [["1", "umuman yoqmaydi"], ["2", "yoqmaydi"], ["3", "bilmayman"], ["4", "yoqadi"], ["5", "juda yoqadi"]];
      return `
      <div class="quiz">
        <div class="page-head" style="text-align:center;align-items:center;margin-inline:auto"><span class="eyebrow">2-qadam · Qiziqish testi</span><h1>Bu ish sizga yoqarmidi?</h1><p>Qila olasizmi yoki daromad qanchaligi emas — faqat <em>yoqadimi</em>. Tez javob bering, birinchi his to'g'ri bo'ladi.</p></div>
        <div class="progress" aria-label="Jarayon"><i style="width:${(answered / Q.length * 100).toFixed(1)}%"></i></div>
        <div class="small muted" style="display:flex;justify-content:space-between;margin-top:6px"><span>${i + 1} / ${Q.length}</span><span class="mono">${answered} javob</span></div>
        <div class="card lift q-card">
          <p class="q">${h(q.matn)}</p>
          <div class="likert" role="group" aria-label="Javob">
            ${scale.map(([v, l]) => `<button type="button" data-ans="${v}" aria-pressed="${String(S.answers[q.id]) === v}"><b>${v}</b><span>${l}</span></button>`).join("")}
          </div>
          <p class="small muted" style="margin-top:14px">Klaviatura: 1–5 raqamlari, ← oldingi</p>
        </div>
        <div class="quiz-nav">
          <button type="button" class="btn ghost" id="prev" ${i === 0 ? "disabled" : ""}>← Oldingi</button>
          ${done ? `<button type="button" class="btn primary" id="finish">Natijani ko'rish →</button>` : `<button type="button" class="btn ghost" id="next" ${!S.answers[q.id] ? "disabled" : ""}>Keyingi →</button>`}
        </div>
        ${answered > 0 ? `<p style="text-align:center;margin-top:24px"><button type="button" class="btn ghost small" id="reset">Testni boshidan boshlash</button></p>` : ""}
      </div>`;
    },
    mount: () => {
      const Q = DATA.riasec; if (!Q.length) return;
      const i = Math.min(S.qi, Q.length - 1), q = Q[i];
      const finish = () => { S.riasec = E.riasecScores(S.answers, Q); S.tanlov = S.tanlov || []; save(); go("/natija"); };
      const answer = (v) => {
        S.answers[q.id] = v;
        const next = Q.findIndex((qq, j) => j > i && !S.answers[qq.id]);
        const any = Q.findIndex(qq => !S.answers[qq.id]);
        if (next >= 0) S.qi = next; else if (any >= 0) S.qi = any; else { save(); finish(); return; }
        save(); render();
      };
      app.querySelectorAll("[data-ans]").forEach(b => b.addEventListener("click", () => answer(Number(b.dataset.ans))));
      const prev = app.querySelector("#prev"); if (prev) prev.addEventListener("click", () => { S.qi = Math.max(0, i - 1); save(); render(); });
      const next = app.querySelector("#next"); if (next) next.addEventListener("click", () => { S.qi = Math.min(Q.length - 1, i + 1); save(); render(); });
      const fin = app.querySelector("#finish"); if (fin) fin.addEventListener("click", finish);
      const rs = app.querySelector("#reset"); if (rs) rs.addEventListener("click", () => { if (confirm("Barcha javoblar o'chiriladi. Davom etasizmi?")) { S.answers = {}; S.qi = 0; S.riasec = null; save(); render(); } });
      testKeys = (e) => {
        if (e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
        if (e.key >= "1" && e.key <= "5") answer(Number(e.key));
        else if (e.key === "ArrowLeft" && i > 0) { S.qi = i - 1; save(); render(); }
      };
    }
  };
  let testKeys = null;
  window.addEventListener("keydown", (e) => { if (location.hash === "#/test" && testKeys) testKeys(e); });

  /* ================= NATIJA ================= */
  let natijaUI = { q: "", soha: "", limit: 30 };
  VIEWS["/natija"] = {
    html: () => {
      const r = S.riasec, list = ranked();
      const top2 = r.order.slice(0, 2);
      const five = E.pickFive(list);
      const sohalar = [...new Set(DATA.yonalishlar.map(y => y.soha))].sort();
      const filtered = list.filter(x => (!natijaUI.q || x.y.nom.toLowerCase().includes(natijaUI.q.toLowerCase()) || x.y.kasblar.join(" ").toLowerCase().includes(natijaUI.q.toLowerCase())) && (!natijaUI.soha || x.y.soha === natijaUI.soha));
      const anyP = list.some(x => x.P != null);
      const myFive = S.tanlov.map(id => rankedById(id)).filter(Boolean);
      const rowHTML = (x, i) => `<button type="button" class="row ${S.tanlov.includes(x.y.id) ? "sel" : ""}" data-open="${x.y.id}">
          <span class="pick" aria-hidden="true">${S.tanlov.includes(x.y.id) ? "✓" : ""}</span>
          <span class="t"><b>${h(x.y.nom)}</b><span class="meta"><span>${h(x.y.soha)}</span> ${fanChips(x.y)} ${tagSavat(x.savat)} ${flags(x.y)}</span></span>
          <span class="fit"><span class="bar"><i style="width:${(x.I * 100).toFixed(0)}%"></i></span><span>moslik ${pct(x.I)} · C ${x.cIndex}/18</span></span>
          <span class="p">${x.P != null ? pct(x.P) : "—"}<small>${x.P != null ? (S.profil.moliya === "faqat_grant" ? "grant" : "kontrakt") : "ehtimol"}</small></span>
        </button>`;
      return `
      <div class="page-head"><span class="eyebrow">3-qadam · Natija</span><h1>Sizning profilingiz: ${h(HOLLAND[top2[0]].nom)} + ${h(HOLLAND[top2[1]].nom)}</h1><p>Bu — «sizning kasbingiz shu» degani emas. Bu sizga yoqadigan faoliyat turlari xaritasi; 6 oydan keyin qayta topshirsangiz, biroz o'zgarishi tabiiy.</p></div>
      <div class="grid2">
        <div class="card">
          ${radarSVG(r.pct)}
          <div style="display:flex;align-items:center;gap:16px;justify-content:center;margin:6px 0 16px"><span class="code-big" aria-label="Holland kodi">${h(r.code)}</span><span class="muted small">Holland kodi — eng kuchli uchta o'lchov</span></div>
          <div class="dims">${r.order.map(k => `<div class="dim"><span class="lt">${k}</span><span class="bar"><i style="width:${(r.pct[k] * 100).toFixed(0)}%"></i></span><span class="v">${pct(r.pct[k])}</span></div>`).join("")}</div>
        </div>
        <div class="stack">
          <div class="card">
            <span class="eyebrow">Bu nimani anglatadi</span>
            <div class="stack" style="margin-top:10px;gap:10px">
              ${top2.map(k => `<p><b>${h(HOLLAND[k].nom)}</b> — ${h(HOLLAND[k].tavsif)}.</p>`).join("")}
              <p class="muted small">Eng past o'lchov: <b>${h(HOLLAND[r.order[5]].nom)}</b> — ${h(HOLLAND[r.order[5]].tavsif)}. Shu turdagi ish sizni tez charchatadi.</p>
            </div>
          </div>
          <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap"><span class="eyebrow">Mening 5 taligim</span><span class="muted small">${myFive.length}/5</span></div>
            <div class="five" style="margin-top:10px">
              ${myFive.length ? myFive.map((x, i) => `<div class="it"><span class="n">${i + 1}</span><span><b>${h(x.y.nom)}</b><br><span class="small muted">${h(fanQisqa(x.y.fan1))} + ${h(fanQisqa(x.y.fan2))} · ${tagSavat(x.savat)}</span></span><button type="button" class="x" data-del="${x.y.id}" aria-label="Olib tashlash">✕</button></div>`).join("") : `<div class="empty">Ro'yxatdan yo'nalishlarni belgilang — yoki Kompas taklifini oling: 1 orzu + 2 maqsad + 2 ishonchli.</div>`}
            </div>
            <div class="actions" style="margin-top:14px">
              <button type="button" class="btn" id="auto5">Kompas taklifi (5 ta)</button>
              <a class="btn primary" href="#/fanlar" ${myFive.length ? "" : 'aria-disabled="true" style="opacity:.5;pointer-events:none"'}>Fanlar va blok →</a>
            </div>
          </div>
        </div>
      </div>
      <div class="toolbar">
        <div class="seg" role="group" aria-label="Tavsiya rejimi">${Object.keys(C.model.vaznlar).map(k => `<button type="button" data-rejim="${k}" aria-pressed="${S.rejim === k}">${h(C.model.vaznlar[k].nom)}</button>`).join("")}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><input type="text" id="q" placeholder="Qidirish: yo'nalish yoki kasb" value="${h(natijaUI.q)}" style="width:220px"><select id="soha" aria-label="Soha"><option value="">Barcha sohalar</option>${sohalar.map(s => `<option ${natijaUI.soha === s ? "selected" : ""}>${h(s)}</option>`).join("")}</select></div>
      </div>
      ${!anyP ? `<p class="small muted" style="margin-bottom:10px">Kirish ehtimoli ustuni <b>Daraja</b> qadamidan keyin to'ladi — hozircha reyting qiziqish, akademik moslik va istiqbol bo'yicha.</p>` : ""}
      <div class="list">${filtered.slice(0, natijaUI.limit).map(rowHTML).join("") || `<div style="padding:20px" class="muted">Hech narsa topilmadi.</div>`}</div>
      ${filtered.length > natijaUI.limit ? `<div class="actions"><button type="button" class="btn" id="more">Yana ko'rsatish (${filtered.length - natijaUI.limit})</button></div>` : ""}
      <div id="drawer-root"></div>
      ${footer()}`;
    },
    mount: () => {
      app.querySelectorAll("[data-rejim]").forEach(b => b.addEventListener("click", () => { S.rejim = b.dataset.rejim; save(); render(); }));
      const q = app.querySelector("#q"); q.addEventListener("input", () => { natijaUI.q = q.value; const pos = q.selectionStart; render(); const nq = app.querySelector("#q"); nq.focus(); nq.setSelectionRange(pos, pos); });
      app.querySelector("#soha").addEventListener("change", e => { natijaUI.soha = e.target.value; render(); });
      const more = app.querySelector("#more"); if (more) more.addEventListener("click", () => { natijaUI.limit += 30; render(); });
      app.querySelectorAll("[data-open]").forEach(b => b.addEventListener("click", () => openDrawer(b.dataset.open)));
      app.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => { S.tanlov = S.tanlov.filter(id => id !== b.dataset.del); save(); render(); }));
      app.querySelector("#auto5").addEventListener("click", () => { S.tanlov = E.pickFive(ranked()).map(x => x.y.id); save(); render(); toast("Kompas 5 taligi qo'shildi: 1 orzu, 2 maqsad, 2 ishonchli"); });
    }
  };
  function openDrawer(id) {
    const x = rankedById(id); if (!x) return;
    const y = x.y, root = app.querySelector("#drawer-root");
    const inList = S.tanlov.includes(id);
    root.innerHTML = `<div class="drawer-bg" id="dbg"></div>
      <aside class="drawer" role="dialog" aria-modal="true" aria-label="${h(y.nom)}">
        <button type="button" class="close" id="dclose" aria-label="Yopish">✕</button>
        <div><span class="eyebrow">${h(y.soha)}${y.kod ? ` · ${h(y.kod)}` : ""}</span><h2 style="margin-top:6px">${h(y.nom)}</h2></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">${fanChips(y)} ${tagSavat(x.savat)} ${flags(y)}</div>
        <p>${h(y.tavsif)}</p>
        <dl class="kv">
          <dt>Qiziqish mosligi</dt><dd><b class="mono">${pct(x.I)}</b> <span class="muted small">(C-indeks ${x.cIndex}/18, kod ${E.codeOf(y.riasec)})</span></dd>
          <dt>Kasblar</dt><dd>${y.kasblar.map(k => h(k)).join(", ")}</dd>
          <dt>Imtihon</dt><dd>${h(fanNom(y.fan1))} (30 × ${fmt(C.koef.fan1)}) + ${h(fanNom(y.fan2))} (30 × ${fmt(C.koef.fan2)}) + majburiy 3 fan${y.sertifikat ? `<br><span class="small" style="color:var(--signal)">Chet tili 1-fan: qabul milliy/xalqaro sertifikat asosida — testga emas, sertifikat imtihoniga tayyorlaning.</span>` : ""}${y.ijodiy ? `<br><span class="small" style="color:var(--signal)">2-fan o'rniga kasbiy (ijodiy) imtihon — OTM talablarini alohida o'rganing.</span>` : ""}</dd>
          <dt>O'tish balli (taxmin)</dt><dd>${y.otish_taxmin.grant ? `grant <b class="mono">${y.otish_taxmin.grant[0]}–${y.otish_taxmin.grant[1]}</b>` : "grant: ma'lumot yo'q"}${y.otish_taxmin.kontrakt ? ` · kontrakt <b class="mono">${y.otish_taxmin.kontrakt[0]}–${y.otish_taxmin.kontrakt[1]}</b>` : ""}<br><span class="muted small">2024–2026 umumiy manzarasi, OTMga qarab farq qiladi</span></dd>
          ${x.ball != null ? `<dt>Sizning prognoz balingiz</dt><dd><b class="mono">${fmt(x.ball, 0)}</b> — kirish ehtimoli: grant <b class="mono">${pct(x.PG)}</b>${S.profil.moliya !== "faqat_grant" ? `, kontrakt <b class="mono">${pct(x.P)}</b>` : ""}</dd>` : ""}
          <dt>Raqobat / istiqbol</dt><dd>${h(y.raqobat)} / ${h(y.istiqbol)}</dd>
          <dt>OTMlar</dt><dd>${y.otmlar.map(o => otmById(o)).filter(Boolean).map(o => `<span class="chip" title="${h(o.nom)}">${h(o.qisqa)}</span>`).join(" ")}</dd>
          <dt>Hududlar</dt><dd>${y.hududlar.includes("*") ? "Barcha hududlarda" : y.hududlar.map(h).join(", ")}</dd>
          <dt>Ma'lumot ishonchi</dt><dd>${y.ishonch === "taxminiy" ? "taxminiy — rasmiy fanlar majmuasi bilan solishtiring" : `<span style="color:var(--signal)">tekshirilsin</span>${y.izoh ? ` — ${h(y.izoh)}` : ""}`}</dd>
        </dl>
        <div class="actions" style="margin-top:6px">
          <button type="button" class="btn ${inList ? "" : "primary"}" id="dtoggle">${inList ? "Ro'yxatdan olib tashlash" : (S.tanlov.length >= 5 ? "Ro'yxat to'la (5/5)" : "Ro'yxatimga qo'shish")}</button>
        </div>
      </aside>`;
    const close = () => { root.innerHTML = ""; };
    root.querySelector("#dbg").addEventListener("click", close);
    root.querySelector("#dclose").addEventListener("click", close);
    root.querySelector("#dtoggle").addEventListener("click", () => {
      if (inList) S.tanlov = S.tanlov.filter(i => i !== id);
      else if (S.tanlov.length < 5) S.tanlov.push(id); else { toast("Ro'yxatda 5 ta bo'ladi — avval bittasini olib tashlang"); return; }
      save(); render();
    });
    root.querySelector("#dclose").focus();
  }

  /* ================= FANLAR / BLOK ================= */
  VIEWS["/fanlar"] = {
    html: () => {
      const list = ranked();
      const my = S.tanlov.map(id => yById(id)).filter(Boolean);
      const myKeys = my.map(y => y.fan1 + "+" + y.fan2);
      const blocks = E.blockOptions(list, DATA, 40, [...new Set(myKeys.concat(S.block ? [S.block.fan1 + "+" + S.block.fan2] : []))]);
      const cover = (b) => my.filter(y => y.fan1 === b.fan1 && y.fan2 === b.fan2).length;
      const best = blocks[0];
      const sel = S.block ? blocks.find(b => b.fan1 === S.block.fan1 && b.fan2 === S.block.fan2) : null;
      const myBlocks = [...new Set(myKeys)];
      return `
      <div class="page-head"><span class="eyebrow">4-qadam · Fanlar va blok</span><h1>Qaysi blokdan test topshirasiz?</h1><p>Iyunda ro'yxatdan o'tishda tanlangan ikki fan avgustda ochiladigan yo'nalishlar ro'yxatini butunlay belgilaydi. Bu qaror qaytarilmaydi — shuning uchun uni hisoblab tanlaymiz.</p></div>
      ${myBlocks.length > 1 ? `<div class="note warn" style="margin-bottom:20px"><b>Ro'yxatingizdagi 5 ta yo'nalish ${myBlocks.length} xil blokka tegishli.</b> Bitta blokdan test topshirasiz — demak, ro'yxatni bitta blok ichida qayta tuzish kerak. Quyida har blok qaysi tanlovlaringizni qamrashi ko'rsatilgan.</div>` : ""}
      <div class="blocks">
        ${blocks.filter((b, i) => i < 6 || b === sel || cover(b)).map((b, i) => `<div class="block ${sel === b ? "best" : ""}">
          <div>
            <div class="fans"><span class="chip k1">${h(fanNom(b.fan1))} ×${fmt(C.koef.fan1)}</span><span>+</span><span class="chip k2">${h(fanNom(b.fan2))} ×${fmt(C.koef.fan2)}</span>${i === 0 ? `<span class="tag maqsad">kompas tavsiyasi</span>` : ""}${cover(b) ? `<span class="tag info">ro'yxatingizdan ${cover(b)} ta</span>` : ""}</div>
            <div class="stats"><span>sizga mos top-40 dan <b>${b.items.length}</b> yo'nalish</span><span>bazada jami <b>${b.jamiYonalish}</b></span><span>o'rtacha moslik <b>${pct(b.meanI)}</b></span>${b.pAny != null ? `<span>kamida bittasiga kirish <b>${pct(b.pAny)}</b></span>` : ""}</div>
            <div class="opens">Ochadi: ${b.top5.map(x => h(x.y.nom)).join(" · ")}${b.items.length > 5 ? ` va yana ${b.items.length - 5} ta` : ""}</div>
          </div>
          <button type="button" class="btn ${sel === b ? "" : "primary"}" data-block="${b.fan1}|${b.fan2}">${sel === b ? "Tanlangan ✓" : "Shu blokni tanlash"}</button>
        </div>`).join("")}
      </div>
      ${S.block ? `<div class="card" style="margin-top:26px">
        <span class="eyebrow">Imtihon tarkibi — ${h(fanNom(S.block.fan1))} + ${h(fanNom(S.block.fan2))}</span>
        <div style="height:12px"></div>${rulerHTML(S.block)}
        ${S.block.fan1 === "matematika" || S.block.fan2 === "matematika" ? `<p class="small muted" style="margin-top:12px">Matematika ham ixtisoslik, ham majburiy fan. Bu holda ball qanday hisoblanishi rasmiy manbada tekshirilishi kerak — model ikkalasini bitta o'zlashtirish darajasi bilan hisoblaydi.</p>` : ""}
        ${(FAN[S.block.fan1] || {}).sertifikat_asosida ? `<p class="small" style="margin-top:12px;color:var(--signal)">Chet tili 1-fan: bu yo'nalishlarga qabul milliy/xalqaro sertifikat asosida. Test o'rniga sertifikat imtihoniga tayyorlaning — reja shunga moslanadi.</p>` : ""}
        ${S.block.fan2 === "ijodiy" ? `<p class="small" style="margin-top:12px;color:var(--signal)">2-fan — ijodiy imtihon. Uning bali modelda hisoblanmaydi; reja faqat 1-fan va majburiy fanlar uchun quriladi.</p>` : ""}
      </div>` : ""}
      <div class="actions"><a class="btn" href="#/natija">← Natija</a><a class="btn primary lg" href="#/daraja" ${S.block ? "" : 'aria-disabled="true" style="opacity:.5;pointer-events:none"'}>Darajamni aniqlash →</a></div>
      ${footer()}`;
    },
    mount: () => {
      app.querySelectorAll("[data-block]").forEach(b => b.addEventListener("click", () => {
        const [f1, f2] = b.dataset.block.split("|"); S.block = { fan1: f1, fan2: f2 };
        // ro'yxatni shu blok ichida qoldirish
        const inBlock = S.tanlov.filter(id => { const y = yById(id); return y && y.fan1 === f1 && y.fan2 === f2; });
        if (inBlock.length !== S.tanlov.length) toast(`Ro'yxatdan ${S.tanlov.length - inBlock.length} ta boshqa blokdagi yo'nalish olib tashlandi`);
        S.tanlov = inBlock;
        if (S.tanlov.length < 5) { const add = E.pickFive(ranked().filter(x => x.y.fan1 === f1 && x.y.fan2 === f2)).map(x => x.y.id); add.forEach(id => { if (S.tanlov.length < 5 && !S.tanlov.includes(id)) S.tanlov.push(id); }); }
        save(); render();
      }));
    }
  };

  /* ================= DARAJA ================= */
  VIEWS["/daraja"] = {
    html: () => {
      const b = S.block;
      const fanlar = [[b.fan1, "fan1"], [b.fan2, "fan2"], ...C.majburiy_fanlar.map(f => [f, "majburiy"])].filter(([f]) => f !== "ijodiy");
      const seen = new Set(); const uniq = fanlar.filter(([f]) => { if (seen.has(f)) return false; seen.add(f); return true; });
      const anchors = ["0 — hech narsa bilmayman", "50 — mavzularning yarmini bilaman", "90 — deyarli hammasi"];
      const cur = currentBall();
      const rows = uniq.map(([f, role]) => {
        const m = S.mastery[f]; const sert = S.profil.sertifikatlar.find(s => s.fan === f);
        const fb = m != null ? E.fanBall(f, role, m, S.profil.sertifikatlar) : null;
        const roles = fanlar.filter(([ff]) => ff === f).map(([, r]) => r);
        return `<div class="lvl">
          <div class="h"><span><b>${h(fanNom(f))}</b> <span class="k">${roles.map(r => r === "majburiy" ? "majburiy · 10 × 1,1" : (r === "fan1" ? "1-fan · 30 × 3,1" : "2-fan · 30 × 2,1")).join(" + ")}</span></span><span class="ball">${fb ? `${fmt(fb.ball, 1)} / ${fmt(fb.max, 0)}` : "—"}${sert ? ` <span class="tag maqsad">sertifikat ${h(sert.daraja)}</span>` : ""}</span></div>
          ${sert && (sert.daraja === "A+" || sert.daraja === "A") ? `<p class="small muted">Sertifikat maksimal ball beradi — bu fan bo'yicha tayyorgarlik kerak emas.</p>` : `<input type="range" min="0" max="95" step="5" value="${m != null ? Math.round(m * 100) : 40}" data-fan="${f}" aria-label="${h(fanNom(f))} darajasi" ${m == null ? 'class="unset"' : ""}><div class="anchor"><span>${anchors[0]}</span><span>${anchors[1]}</span><span>${anchors[2]}</span></div>`}
        </div>`;
      }).join("");
      const T = C.max_ball, minb = C.minimal_ball.variant === "guruh" ? C.minimal_ball.guruh.oddiy : C.minimal_ball.yagona.kontrakt;
      return `
      <div class="page-head"><span class="eyebrow">5-qadam · Daraja</span><h1>Hozir qayerdasiz?</h1><p>Har fan bo'yicha halol baho bering: maktab dasturidagi mavzularning necha foizini test darajasida bilasiz? Sinov imtihoni topshirgan bo'lsangiz — ballini kiriting, model shunga moslanadi.</p></div>
      <div class="grid2">
        <div class="card"><div class="topics">${rows}</div>
          <p class="small muted" style="margin-top:14px">Model bilmagan savolda ham 4 variantdan bittasi to'g'ri tushishini hisobga oladi (taxmin ehtimoli ${fmt(C.model.g * 100, 0)}%). Shuning uchun «0» ham 0 ball emas.</p>
        </div>
        <div class="stack">
          <div class="card">
            <span class="eyebrow">Joriy prognoz</span>
            <div class="hero-num" style="margin-top:6px"><b class="num">${cur ? fmt(cur.total, 0) : "—"}</b><span>/ ${T} ball</span></div>
            ${cur ? `<div class="track" style="margin-top:14px"><div class="fill" style="width:${(cur.total / T * 100).toFixed(1)}%"></div><div class="min" style="left:${(minb / T * 100).toFixed(1)}%" title="minimal chegara"></div></div>
            <div class="keys"><span class="key"><i class="sw a"></i><b>${fmt(cur.total, 0)}</b> hozir</span><span class="key"><i class="sw m"></i><b>${fmt(minb, 1)}</b> minimal chegara</span></div>
            <table class="tbl" style="margin-top:14px"><thead><tr><th>Fan</th><th>Ball</th><th>Maks.</th></tr></thead><tbody>${cur.rows.map(r => `<tr><td>${h(fanNom(r.fan))}${r.sertifikat ? ` <span class="tag maqsad">${h(r.sertifikat)}</span>` : ""}</td><td>${fmt(r.ball, 1)}</td><td class="muted">${fmt(r.max, 0)}</td></tr>`).join("")}</tbody></table>` : `<p class="muted small" style="margin-top:8px">Barcha fanlar uchun slayderni qo'ying — ball hisoblanadi.</p>`}
          </div>
          <div class="card">
            <label for="sinov" style="font-weight:600">Sinov imtihoni ballingiz (ixtiyoriy)</label>
            <p class="small muted" style="margin:4px 0 10px">Oxirgi 2 oyda to'liq 90 savollik sinov topshirgan bo'lsangiz. Model prognozi undan 15 balldan ko'p farq qilsa — slayderlarni sozlang: sinov haqiqatga yaqinroq.</p>
            <input type="number" id="sinov" min="0" max="189" step="0.1" placeholder="masalan 104,2" value="${S.sinovBall ?? ""}">
            ${S.sinovBall != null && cur ? `<p class="small" style="margin-top:8px">Farq: <b class="mono">${fmt(Math.abs(S.sinovBall - cur.total), 0)}</b> ball ${Math.abs(S.sinovBall - cur.total) > 15 ? `<span style="color:var(--signal)">— katta, slayderlarni qayta ko'rib chiqing</span>` : "— mos"}</p>` : ""}
          </div>
        </div>
      </div>
      <div class="actions"><a class="btn" href="#/fanlar">← Blok</a><a class="btn primary lg" href="#/reja" ${cur ? "" : 'aria-disabled="true" style="opacity:.5;pointer-events:none"'}>Tayyorgarlik rejasi →</a></div>
      ${footer()}`;
    },
    mount: () => {
      app.querySelectorAll("input[data-fan]").forEach(inp => {
        const set = () => { S.mastery[inp.dataset.fan] = Number(inp.value) / 100; save(); };
        inp.addEventListener("input", set);
        inp.addEventListener("change", () => { set(); render(); });
        if (inp.classList.contains("unset")) { /* boshlang'ich 40 ni faqat foydalanuvchi tegsa yozamiz */ }
      });
      const sn = app.querySelector("#sinov");
      sn.addEventListener("change", () => { const v = parseFloat(sn.value.replace(",", ".")); S.sinovBall = isNaN(v) ? null : Math.max(0, Math.min(189, v)); save(); render(); });
      // hamma slayder qo'yilmagan bo'lsa — birinchi "change" gacha ball ko'rinmaydi; qulaylik uchun "Hammasini 40% deb boshlash"
      const unset = app.querySelectorAll("input.unset");
      if (unset.length) {
        const bar = document.createElement("div"); bar.className = "actions"; bar.style.marginTop = "12px";
        bar.innerHTML = `<button type="button" class="btn" id="fill40">Hammasini 40% dan boshlash</button><span class="muted small">keyin har birini sozlaysiz</span>`;
        app.querySelector(".topics").after(bar);
        bar.querySelector("#fill40").addEventListener("click", () => { unset.forEach(i => { S.mastery[i.dataset.fan] = 0.4; }); save(); render(); });
      }
    }
  };

  /* ================= REJA ================= */
  let rejaCache = null; // html() da hisoblangan reja — mount() dagi tugmalar uchun
  VIEWS["/reja"] = {
    html: () => {
      const cur = currentBall(), b = S.block, T = C.max_ball;
      const my = S.tanlov.map(id => rankedById(id)).filter(Boolean);
      const turi = S.profil.moliya === "faqat_grant" ? "grant" : S.target.turi;
      let tgtY = S.target.id ? yById(S.target.id) : (my[0] ? my[0].y : null);
      if (tgtY && !(tgtY.fan1 === b.fan1 && tgtY.fan2 === b.fan2)) tgtY = my[0] ? my[0].y : null;
      const est = tgtY ? E.cutoffEstimate(tgtY, turi) : null;
      const targetBall = S.target.ball != null ? S.target.ball : (est ? Math.min(T, est.C + C.model.zapas_ball) : null);
      if (targetBall == null) return `<div class="page-head"><h1>Maqsad kerak</h1><p>Ro'yxatingizda yo'nalish yo'q. <a href="#/natija">Natija</a> sahifasida kamida bittasini tanlang yoki maqsad ballni qo'lda kiriting.</p></div>
        <div class="card"><label for="tb">Maqsad ball</label><input type="number" id="tb" min="57" max="189" placeholder="masalan 145"></div>${footer()}`;
      const wl = weeksLeft();
      const opts = { block: b, mastery: S.mastery, sertifikatlar: S.profil.sertifikatlar, targetBall, weeklyHours: S.profil.haftalik_soat, weeksAvailable: wl };
      const plans = {}; Object.keys(C.model.ssenariylar).forEach(k => { plans[k] = E.prepPlan({ ...opts, scenario: k }, DATA); });
      const P = plans[S.scenario];
      const pNow = est ? E.admitProb(cur.total, S.sinovBall != null ? 9 : C.model.sigma_s_boshlangich, est.C, est.sigma) : null;
      const pAfter = est ? E.admitProb(P.feasible ? targetBall : (P.alt ? P.alt.maxBall : cur.total), 8, est.C, est.sigma) : null;
      const mo = (k) => plans[k].months;
      const rangeTxt = P.reached ? `≈ ${fmt(Math.min(mo("intensiv"), mo("ehtiyotkor")), 1)}–${fmt(Math.max(mo("intensiv"), mo("ehtiyotkor")), 1)} oy` : "—";
      const totalH = P.byFan.reduce((s, f) => s + f.hours, 0) || 1;
      const reachable = !P.feasible && P.alt ? ranked().filter(x => x.y.fan1 === b.fan1 && x.y.fan2 === b.fan2).map(x => { const e2 = E.cutoffEstimate(x.y, turi); return e2 ? { x, p: E.admitProb(P.alt.maxBall, 8, e2.C, e2.sigma) } : null; }).filter(Boolean).filter(r => r.p >= 0.5).slice(0, 6) : [];
      const weeksToShow = 6;
      // 5 ta tanlov simulyatsiyasi
      const mu = P.feasible ? targetBall : (P.alt ? P.alt.maxBall : cur.total);
      const choices = my.map(x => ({ id: x.y.id, nom: x.y.nom, C_grant: (E.cutoffEstimate(x.y, "grant") || {}).C ?? null, s_grant: (E.cutoffEstimate(x.y, "grant") || {}).sigma ?? 6, C_kontrakt: (E.cutoffEstimate(x.y, "kontrakt") || {}).C ?? null, s_kontrakt: (E.cutoffEstimate(x.y, "kontrakt") || {}).sigma ?? 6, kontraktMumkin: S.profil.moliya !== "faqat_grant", I: x.I }));
      const sim = choices.length ? E.simulateChoices(choices, mu, 8, 4000, 11, S.grantUstuvor) : null;
      const best = choices.length >= 2 ? E.bestOrder(choices, mu, 8, (c, t) => 0.6 + 0.4 * c.I + (t === "grant" ? 0.25 : 0), S.grantUstuvor) : null;
      rejaCache = { P, best, ids: choices.map(c => c.id) };
      const weekHTML = (w, open) => `<details class="week" ${open ? "open" : ""}><summary><span>${w.n}-hafta${w.sinov ? ` <span class="tag flag">sinov</span>` : ""}</span><span class="n">${fmt(w.study + w.review + (w.sinov ? C.model.sinov_soat : 0), 0)} soat</span></summary><ul>${w.items.map(it => `<li><span title="${h(it.nom)}">${h(shortNom(it.nom, 56))} <span class="muted small">${h(fanQisqa(it.fan))}${it.davom ? " · davomi" : ""}</span></span><span>${fmt(it.hours, 1)} s</span></li>`).join("")}<li class="rev"><span>Intervalli takrorlash (o'tgan mavzular)</span><span>${fmt(w.review, 1)} s</span></li>${w.sinov ? `<li class="sin"><span>To'liq sinov imtihoni + tahlil</span><span>${C.model.sinov_soat} s</span></li>` : ""}</ul></details>`;
      rejaCache.weekHTML = weekHTML;
      return `
      <div class="page-head"><span class="eyebrow">6-qadam · Reja</span><h1>Qancha vaqt kerak?</h1><p>Farq mavzularga bo'linadi; har soat eng ko'p ball beradigan mavzuga sarflanadi. Uch ssenariy — chunki bitta aniq raqam yolg'on bo'lardi.</p></div>
      <div class="card" style="margin-bottom:20px">
        <div class="form-grid">
          <div class="field"><label for="tsel">Maqsad yo'nalish</label><select id="tsel">${my.map(x => `<option value="${x.y.id}" ${tgtY && tgtY.id === x.y.id ? "selected" : ""}>${h(x.y.nom)}</option>`).join("")}<option value="" ${!tgtY ? "selected" : ""}>— ball qo'lda —</option></select>${est ? `<span class="hint">O'tish balli prognozi (${turi}): <b class="mono">${fmt(est.C, 0)}</b> ± ${fmt(est.sigma, 0)} → maqsad <b class="mono">${fmt(targetBall, 0)}</b> (zapas +${C.model.zapas_ball})</span>` : ""}</div>
          <div class="field"><label for="tball">Maqsad ball (o'zgartirish mumkin)</label><input type="number" id="tball" min="57" max="189" step="1" value="${Math.round(targetBall)}">${S.profil.moliya !== "faqat_grant" ? `<div class="seg" style="margin-top:6px"><button type="button" data-turi="grant" aria-pressed="${turi === "grant"}">Grant</button><button type="button" data-turi="kontrakt" aria-pressed="${turi === "kontrakt"}">Kontrakt</button></div>` : ""}</div>
        </div>
      </div>
      <div class="grid2" style="align-items:start">
        <div class="card lift">
          <div class="tabs" role="tablist">${Object.keys(C.model.ssenariylar).map(k => `<button type="button" role="tab" data-sc="${k}" aria-selected="${S.scenario === k}">${h(C.model.ssenariylar[k].nom)}</button>`).join("")}</div>
          <div class="hero-num" style="margin-top:18px"><b>${rangeTxt}</b><span>${P.reached ? `haftasiga ${S.profil.haftalik_soat} soat bilan` : ""}</span></div>
          ${P.reached ? `<p style="margin-top:10px"><b>${h(P.scenario.nom)}</b> ssenariy: <b class="mono">${fmt(P.totalHours, 0)} soat</b> → <b class="mono">${fmt(P.weeks, 0)} hafta</b> (${fmt(P.months, 1)} oy). Imtihongacha <b class="mono">${fmt(wl, 0)} hafta</b> bor.</p>` : `<p style="margin-top:10px">Bu maqsad joriy blok bilan modelda erishib bo'lmaydigan darajada (o'zlashtirish chegarasi ${fmt(C.model.mastery_cap * 100, 0)}%). Maqsad ballni pasaytiring.</p>`}
          ${P.feasible ? `<div class="note" style="margin-top:14px"><b>Ulgurasiz.</b> Reja ${fmt(P.weeks, 0)} haftada tugaydi, zaxira ≈ ${fmt(wl - P.weeks, 0)} hafta. Zaxirani grant darajasiga chiqish uchun ishlating — yoki maqsad ballni oshirib ko'ring.</div>`
            : P.reached ? `<div class="note warn" style="margin-top:14px"><b>Bu sur'atda ulgurmaysiz.</b> Imtihongacha ${fmt(wl, 0)} hafta, reja ${fmt(P.weeks, 0)} hafta talab qiladi. Variantlar: haftalik soatni <b class="mono">${fmt(Math.ceil(P.totalHours / Math.max(1, wl)), 0)}</b> ga oshirish, yoki imtihon sanasigacha erishiladigan <b class="mono">${fmt(P.alt.maxBall, 0)}</b> ballga mos yo'nalishni tanlash${reachable.length ? `: ${reachable.map(r => `${h(r.x.y.nom)} (${pct(r.p)})`).join(", ")}` : ""}.</div>` : ""}
          <div class="stat-row" style="margin-top:16px">
            <div><b>${fmt(cur.total, 0)}</b><span>hozirgi ball</span></div>
            <div><b>${fmt(targetBall, 0)}</b><span>maqsad</span></div>
            <div><b>${pct(pNow)}</b><span>kirish ehtimoli hozir</span></div>
            <div><b>${pct(pAfter)}</b><span>reja bajarilsa</span></div>
          </div>
          <div class="track" style="margin-top:18px">
            <div class="fill" style="width:${(cur.total / T * 100).toFixed(1)}%"></div>
            <div class="gap" style="left:${(cur.total / T * 100).toFixed(1)}%;width:${(Math.max(0, targetBall - cur.total) / T * 100).toFixed(1)}%"></div>
            ${est ? `<div class="cut" style="left:${(est.C / T * 100).toFixed(1)}%"></div>` : ""}
          </div>
          <div class="keys"><span class="key"><i class="sw a"></i><b>${fmt(cur.total, 0)}</b> hozir</span>${est ? `<span class="key"><i class="sw c"></i><b>${fmt(est.C, 0)}</b> o'tish balli (prognoz)</span>` : ""}<span class="key"><i class="sw g"></i><b>${fmt(targetBall, 0)}</b> maqsad</span></div>
        </div>
        <div class="stack">
          <div class="card">
            <span class="eyebrow">Vaqt qayerga ketadi</span>
            <div class="alloc" style="margin-top:10px">${P.byFan.filter(f => f.hours > 0).map(f => `<div style="width:${(f.hours / totalH * 100).toFixed(1)}%" title="${h(fanNom(f.fan))}">${(f.hours / totalH) > 0.12 ? h(fanQisqa(f.fan)) : ""}</div>`).join("")}</div>
            <div class="alloc-legend">${P.byFan.filter(f => f.hours > 0).map(f => `<span><b>${h(fanQisqa(f.fan))}</b> ${fmt(f.hours / P.scenario.eta, 0)} s · +${fmt(f.gain, 0)} ball</span>`).join("")}</div>
            <p class="small muted" style="margin-top:10px">Jami: o'rganish ${fmt(P.realHours, 0)} s + takrorlash ${fmt(P.reviewHours, 0)} s + ${Math.round(P.mockHours / C.model.sinov_soat)} ta sinov ${fmt(P.mockHours, 0)} s.</p>
          </div>
          <div class="card">
            <span class="eyebrow">Eng foydali mavzular (ball / soat)</span>
            <div class="topics" style="margin-top:8px">${P.topics.slice(0, 10).map(t => `<div class="topic"><span title="${h(t.nom)}">${h(shortNom(t.nom))}<br><span class="f">${h(fanQisqa(t.fan))}${t.bolim ? " · " + h(t.bolim) : ""}</span></span><span class="n">${fmt(t.hours / P.scenario.eta, 1)} s</span><span class="n">+${fmt(t.gain, 1)}</span></div>`).join("") || `<p class="muted small">Mavzu daraxti yo'q — reja fan darajasida.</p>`}</div>
          </div>
        </div>
      </div>
      <section style="margin-top:26px">
        <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px"><h2 style="font-size:1.35rem">Haftalik reja</h2><span class="muted small">${P.weeklyPlan.length} hafta · har 4-haftada sinov imtihoni</span></div>
        <div class="weeks" style="margin-top:12px" id="weeks">
          ${P.weeklyPlan.slice(0, weeksToShow).map(w => weekHTML(w, w.n === 1)).join("")}
        </div>
        ${P.weeklyPlan.length > weeksToShow ? `<div class="actions"><button type="button" class="btn" id="allweeks">Barcha ${P.weeklyPlan.length} haftani ko'rsatish</button></div>` : ""}
      </section>
      ${sim ? `<section style="margin-top:30px">
        <h2 style="font-size:1.35rem">5 ta tanlov: ehtimollik va tartib</h2>
        <p class="muted small" style="margin:6px 0 12px">Reja bajarilganda (μ = ${fmt(mu, 0)} ball) tanlovlaringiz ustuvorlik tartibida qanday ishlaydi — 4000 simulyatsiya. <label class="toggle" style="margin-left:8px"><input type="checkbox" id="gu" ${S.grantUstuvor ? "checked" : ""}><span>grant ustuvorligi</span></label></p>
        <div class="card">
          <table class="tbl"><thead><tr><th>#</th><th style="text-align:left">Yo'nalish</th><th>Grant</th><th>Kontrakt</th><th>Jami</th></tr></thead><tbody>
            ${choices.map((c, i) => `<tr><td class="mono">${i + 1}</td><td style="text-align:left">${h(c.nom)}</td><td>${pct(sim.perChoice[i].grant)}</td><td>${pct(sim.perChoice[i].kontrakt)}</td><td><b>${pct(sim.perChoice[i].jami)}</b></td></tr>`).join("")}
          </tbody></table>
          <p style="margin-top:12px">Kamida bittasiga kirish: <b class="mono">${pct(sim.any)}</b> · grantga: <b class="mono">${pct(sim.anyGrant)}</b></p>
          ${best && best.order.some((v, i) => v !== i) ? `<div class="note" style="margin-top:12px"><b>Tavsiya etilgan tartib:</b> ${best.order.map(i => h(choices[i].nom)).join(" → ")}<br><span class="small muted">Qiziqish mosligi va grant imkonini hisobga olgan kutilgan foyda bo'yicha (120 ta tartib tekshirildi).</span> <button type="button" class="btn small" id="applyorder" style="margin-left:6px">Qo'llash</button></div>` : (best ? `<p class="small muted" style="margin-top:8px">Hozirgi tartib — 120 ta variant ichida eng yaxshisi.</p>` : "")}
        </div>
      </section>` : ""}
      <div class="note warn" style="margin-top:26px"><b>Bu model bahosi, kafolat emas.</b> Bazaviy soatlar — ekspert bahosi; o'tish ballari — taxminiy oraliq; sizning tezligingiz noma'lum. Haftalik nazorat testlari bilan 2–3 haftada prognoz sizga moslashadi. Rasmiy ma'lumot: uzbmb.uz.</div>
      <div class="actions"><a class="btn" href="#/daraja">← Daraja</a><button type="button" class="btn" id="print">Chop etish / PDF</button><button type="button" class="btn ghost" id="restart">Boshidan boshlash</button></div>
      ${footer()}`;
    },
    mount: () => {
      const tsel = app.querySelector("#tsel"); if (tsel) tsel.addEventListener("change", () => { S.target.id = tsel.value || null; S.target.ball = null; save(); render(); });
      const tb = app.querySelector("#tball") || app.querySelector("#tb");
      if (tb) tb.addEventListener("change", () => { const v = Number(tb.value); S.target.ball = isNaN(v) || !v ? null : Math.max(57, Math.min(189, v)); save(); render(); });
      app.querySelectorAll("[data-turi]").forEach(b => b.addEventListener("click", () => { S.target.turi = b.dataset.turi; S.target.ball = null; save(); render(); }));
      app.querySelectorAll("[data-sc]").forEach(b => b.addEventListener("click", () => { S.scenario = b.dataset.sc; save(); render(); }));
      const gu = app.querySelector("#gu"); if (gu) gu.addEventListener("change", () => { S.grantUstuvor = gu.checked; save(); render(); });
      const ao = app.querySelector("#applyorder"); if (ao) ao.addEventListener("click", () => {
        if (!rejaCache || !rejaCache.best) return;
        S.tanlov = rejaCache.best.order.map(i => rejaCache.ids[i]); save(); render(); toast("Tartib qo'llandi");
      });
      const aw = app.querySelector("#allweeks"); if (aw) aw.addEventListener("click", () => {
        if (!rejaCache) return;
        app.querySelector("#weeks").innerHTML = rejaCache.P.weeklyPlan.map(w => rejaCache.weekHTML(w, false)).join("");
        aw.remove();
      });
      const pr = app.querySelector("#print"); if (pr) pr.addEventListener("click", () => window.print());
      const rs = app.querySelector("#restart"); if (rs) rs.addEventListener("click", () => { if (confirm("Barcha ma'lumotlar o'chiriladi. Davom etasizmi?")) { S = DEFAULT(); save(); go("/"); } });
    }
  };

  /* ================= MANBA ================= */
  VIEWS["/manba"] = {
    html: () => `
    <div class="page-head"><span class="eyebrow">Model va manbalar</span><h1>Kompas qanday hisoblaydi</h1><p>Har bir raqamning qayerdan kelgani va qanchalik ishonchli ekani.</p></div>
    <div class="stack">
      <div class="card"><h3>1. Qiziqish — RIASEC (Holland)</h3><p class="small" style="margin-top:6px">60 ta faoliyat bayoni, 6 shkala. O*NET Interest Profiler (AQSh Mehnat vazirligi, public domain) qisqa shakli asosida o'zbek tiliga moslashtirilgan; asl testning ishonchliligi α = 0,78–0,85. Profil birlik vektorga keltiriladi, yo'nalish profili bilan kosinus o'xshashlik hisoblanadi. Yo'nalish profillari — ekspert bahosi (kalibrovka rejalashtirilgan).</p></div>
      <div class="card"><h3>2. Ball modeli</h3><p class="small" style="margin-top:6px">Ball = savollar × koeffitsient × (o'zlashtirish + (1 − o'zlashtirish) × ${fmt(C.model.g)}). 1-fan 30 × 3,1; 2-fan 30 × 2,1; uchta majburiy fan 10 × 1,1; jami 189. Milliy sertifikat: A+/A — maksimal, B+…C — proporsional ulush (koeffitsientlar tekshirilmoqda).</p></div>
      <div class="card"><h3>3. Kirish ehtimoli</h3><p class="small" style="margin-top:6px">O'tish balli — yo'nalish bo'yicha 2024–2026 umumiy manzarasidan taxminiy oraliq; o'rtasi Ĉ, noaniqligi σ_c ≥ ${C.model.sigma_c_min}. Sizning balingiz ham taqsimot (σ_s = ${C.model.sigma_s_boshlangich}, sinov bali kiritilsa 9). P = Φ((μ − Ĉ)/√(σ_s² + σ_c²)). 5 ta tanlov — 4000 ta Monte-Carlo simulyatsiya, ustuvorlik tartibida.</p></div>
      <div class="card"><h3>4. Tayyorgarlik muddati</h3><p class="small" style="margin-top:6px">Har mavzu uchun: foyda = savollar ulushi × koeffitsient × 0,75 × Δo'zlashtirish; vaqt = (bazaviy soat / 3) × ln((1 − m₀)/(1 − m₁)). Mavzular ball/soat bo'yicha saralanadi (ochko'z algoritm). Ustiga: konsentratsiya samaradorligi (η), takrorlash (+${fmt(C.model.rho * 100, 0)}%), har ${C.model.sinov_har_hafta} haftada sinov. Uch ssenariy: ${Object.values(C.model.ssenariylar).map(s => `${s.nom} (r=${fmt(s.r)}, η=${fmt(s.eta, 2)})`).join("; ")}.</p></div>
      <div class="card"><h3>5. Ma'lumotlar</h3><p class="small" style="margin-top:6px">${DATA.yonalishlar.length} yo'nalish, ${OTM.length} davlat OTM, ${Object.keys(DATA.mavzular).length} fan bo'yicha mavzu daraxti. Yangilangan: ${h(C.yangilangan)}. Har yo'nalishda ishonch belgisi bor: «taxminiy» yoki «tekshirilsin». Nodavlat va xorijiy OTMlar alohida qabul o'tkazadi — bu versiyada yo'q.</p></div>
      <div class="note warn"><b>Tekshirilishi kerak bo'lgan narsalar:</b> minimal o'tish ball chegaralari (manbalar qarama-qarshi), matematikaning ikki roli, sertifikat proporsional koeffitsientlari, yo'nalish darajasidagi rasmiy o'tish ballari. To'liq ro'yxat: docs/kompas/MANBALAR.md.</div>
      <p class="small muted">Rasmiy manbalar: <a href="https://uzbmb.uz" rel="noopener">uzbmb.uz</a> · <a href="https://my.uzbmb.uz" rel="noopener">my.uzbmb.uz</a> · <a href="https://lex.uz" rel="noopener">lex.uz</a> · <a href="https://www.onetcenter.org/" rel="noopener">onetcenter.org</a></p>
    </div>
    <div class="actions"><a class="btn primary" href="#/profil">Boshlash →</a></div>
    ${footer()}`
  };

  // chop etishda barcha haftalar ochiq bo'lsin
  window.addEventListener("beforeprint", () => { document.querySelectorAll("details.week").forEach(d => { d.open = true; }); });

  render();
})();

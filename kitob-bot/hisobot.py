"""
Sehrli Javon — statistika va marketing tahlili.

statistika(db, kat)  — botdagi ma'lumotdan hisob-kitob (lug'at)
matn_hisobot(st)     — Telegram uchun qisqa hisobot (HTML)
html_hisobot(st)     — adminga fayl qilib yuboriladigan to'liq sahifa:
                       ko'rsatkich doiralari, kunlik sotuv va yangi mijozlar
                       grafigi, voronka, manbalar, top kitoblar, promokodlar.
Faqat standart kutubxona.
"""

import html
import json
import time

TOSHKENT = 5 * 3600
KUN = 86400
TOLOV_NOMI = {"naqd": "Naqd", "karta": "Karta", "click": "Click / Payme"}


def _e(s):
    return html.escape(str(s), quote=False)


def som(n):
    return "{:,}".format(int(n)).replace(",", " ") + " so'm"


def qisqa_som(n):
    n = int(n)
    if n >= 1_000_000:
        return ("%.1f mln" % (n / 1_000_000)).replace(".0 ", " ").replace(".", ",")
    if n >= 1000:
        return "%d ming" % round(n / 1000)
    return str(n)


def kun(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(ts + TOSHKENT))


def statistika(db, kat, hozir=None, kunlar_soni=30):
    hozir = hozir or time.time()
    kunlar = [kun(hozir - i * KUN) for i in range(kunlar_soni - 1, -1, -1)]
    bugun = kunlar[-1]
    users = db["users"].values()
    ob = list(db["buyurtmalar"].values())
    faol = [o for o in ob if o["holat"] != "bekor"]

    sotuv = {d: 0 for d in kunlar}
    buyurtma = {d: 0 for d in kunlar}
    yangi = {d: 0 for d in kunlar}
    for o in faol:
        d = kun(o["sana"])
        if d in sotuv:
            sotuv[d] += o["jami"]
            buyurtma[d] += 1
    for u in users:
        if u.get("royxat") and u.get("royxat_sana"):
            d = kun(u["royxat_sana"])
            if d in yangi:
                yangi[d] += 1

    xaridorlar = {}
    for o in faol:
        xaridorlar[o["chat"]] = xaridorlar.get(o["chat"], 0) + 1
    royxat = [u for u in users if u.get("royxat")]

    manbalar = {}
    for u in users:
        m = u.get("manba") or "to'g'ridan-to'g'ri"
        r = manbalar.setdefault(m, {"ochgan": 0, "royxat": 0, "xaridor": 0, "tushum": 0})
        r["ochgan"] += 1
        r["royxat"] += 1 if u.get("royxat") else 0
        r["xaridor"] += 1 if u["id"] in xaridorlar else 0
    for o in faol:
        u = db["users"].get(o["chat"], {})
        m = u.get("manba") or "to'g'ridan-to'g'ri"
        manbalar.setdefault(m, {"ochgan": 0, "royxat": 0, "xaridor": 0, "tushum": 0})["tushum"] += o["jami"]

    promolar = {}
    for o in faol:
        if o.get("promo"):
            p = promolar.setdefault(o["promo"], {"soni": 0, "tushum": 0, "tejaldi": 0})
            p["soni"] += 1
            p["tushum"] += o["jami"]
            p["tejaldi"] += o["asl"] - o["jami"]

    tolov = {}
    for o in faol:
        t = TOLOV_NOMI.get(o.get("tolov"), "—")
        tolov[t] = tolov.get(t, 0) + 1

    yoshlar = {"5–12": 0, "13–17": 0, "18–24": 0, "25–34": 0, "35+": 0}
    for u in royxat:
        y = u.get("yosh") or 0
        k = "5–12" if y <= 12 else "13–17" if y <= 17 else "18–24" if y <= 24 else "25–34" if y <= 34 else "35+"
        yoshlar[k] += 1

    kitoblar = list(db["kitoblar"].values())
    top = sorted((b for b in kitoblar if b.get("sotildi")), key=lambda b: -b["sotildi"])[:5]
    sekin = sorted((b for b in kitoblar if b.get("soni", 0) > 0),
                   key=lambda b: (b.get("sotildi", 0) / (b.get("sotildi", 0) + b["soni"]), -b["soni"]))[:5]

    tushum = sum(o["jami"] for o in faol)
    oxirgi = lambda n: sum(sotuv[d] for d in kunlar[-n:])
    maqsad = int(kat.get("dokon", {}).get("maqsad_mijoz") or 1000)
    return {
        "vaqt": hozir, "kunlar": kunlar, "bugun": bugun,
        "sotuv": [sotuv[d] for d in kunlar], "buyurtma": [buyurtma[d] for d in kunlar],
        "yangi": [yangi[d] for d in kunlar],
        "tushum": tushum, "tushum_bugun": sotuv[bugun], "tushum_7": oxirgi(7), "tushum_30": oxirgi(30),
        "buyurtmalar": len(faol), "bekor": len(ob) - len(faol),
        "yangi_buyurtma": sum(1 for o in ob if o["holat"] == "yangi"),
        "ochgan": len(db["users"]), "mijozlar": len(royxat), "xaridorlar": len(xaridorlar),
        "qayta": sum(1 for n in xaridorlar.values() if n >= 2),
        "ortacha": tushum // len(faol) if faol else 0,
        "konversiya": round(100 * len(xaridorlar) / len(royxat)) if royxat else 0,
        "tejaldi": sum(o["asl"] - o["jami"] for o in faol),
        "maqsad": maqsad,
        "manbalar": sorted(manbalar.items(), key=lambda kv: (-kv[1]["tushum"], -kv[1]["ochgan"])),
        "promolar": sorted(promolar.items(), key=lambda kv: -kv[1]["soni"]),
        "tolov": sorted(tolov.items(), key=lambda kv: -kv[1]),
        "yoshlar": list(yoshlar.items()),
        "top": [(b["nomi"], b["sotildi"], b.get("soni", 0)) for b in top],
        "sekin": [(b["nomi"], b.get("sotildi", 0), b["soni"], b.get("aksiya") or 0) for b in sekin],
        "ombor": sum(b.get("soni", 0) for b in kitoblar),
    }


# ---------------------------------------------------------------- Telegram matni
def sparkline(qiymatlar):
    belgi = "▁▂▃▄▅▆▇█"
    m = max(qiymatlar) if qiymatlar else 0
    if not m:
        return "▁" * len(qiymatlar)
    return "".join(belgi[min(7, int(v / m * 7.999))] if v else "▁" for v in qiymatlar)


def progress(n, maqsad, uzun=12):
    t = min(uzun, round(uzun * n / maqsad)) if maqsad else 0
    return "▓" * t + "░" * (uzun - t)


def matn_hisobot(st):
    q = ["📊 <b>Umumiy hisobot</b>", ""]
    q.append("💰 Tushum: <b>%s</b>" % som(st["tushum"]))
    q.append("   bugun %s · 7 kun %s · 30 kun %s" % (
        qisqa_som(st["tushum_bugun"]), qisqa_som(st["tushum_7"]), qisqa_som(st["tushum_30"])))
    q.append("🧾 Buyurtmalar: <b>%d</b> (kutmoqda: %d, bekor: %d)" % (
        st["buyurtmalar"], st["yangi_buyurtma"], st["bekor"]))
    q.append("🧮 O'rtacha chek: %s" % som(st["ortacha"]))
    q.append("🎉 Mijozlar tejagan: %s" % som(st["tejaldi"]))
    q.append("")
    q.append("🎯 Maqsad — %d mijoz:" % st["maqsad"])
    q.append("<code>%s</code> %d / %d" % (progress(st["mijozlar"], st["maqsad"]), st["mijozlar"], st["maqsad"]))
    q.append("")
    q.append("👥 Botni ochgan: %d → ro'yxatdan o'tgan: %d → xarid qilgan: %d" % (
        st["ochgan"], st["mijozlar"], st["xaridorlar"]))
    q.append("🔁 Qayta xarid qilgan: %d · Konversiya: %d%%" % (st["qayta"], st["konversiya"]))
    q.append("")
    q.append("📈 Sotuv, oxirgi 14 kun:")
    q.append("<code>%s</code>" % sparkline(st["sotuv"][-14:]))
    q.append("👤 Yangi mijozlar, 14 kun:")
    q.append("<code>%s</code>" % sparkline(st["yangi"][-14:]))
    if st["top"]:
        q += ["", "🏆 <b>Eng ko'p sotilgan:</b>"]
        q += ["%d. %s — %d dona" % (i, _e(n), s) for i, (n, s, _) in enumerate(st["top"], 1)]
    if st["manbalar"]:
        q += ["", "📣 <b>Mijozlar qayerdan keldi:</b>"]
        q += ["• %s — %d kishi, %d xaridor, %s" % (_e(m), r["ochgan"], r["xaridor"], qisqa_som(r["tushum"]))
              for m, r in st["manbalar"][:6]]
    q += ["", "📈 To'liq grafiklar — «Marketing tahlil» tugmasi."]
    return "\n".join(q)


# ---------------------------------------------------------------- HTML sahifa
CSS = """
:root{color-scheme:light;--bg:#f6f6f4;--surface:#fcfcfb;--line:#e4e3de;--grid:#ecebe7;
--t1:#0b0b0b;--t2:#52514e;--t3:#7a7975;--s1:#2a78d6;--s1a:rgba(42,120,214,.14)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#111110;
--surface:#1a1a19;--line:#2e2e2c;--grid:#262624;--t1:#fff;--t2:#c3c2b7;--t3:#8f8e87;--s1:#3987e5;
--s1a:rgba(57,135,229,.22)}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#111110;--surface:#1a1a19;--line:#2e2e2c;
--grid:#262624;--t1:#fff;--t2:#c3c2b7;--t3:#8f8e87;--s1:#3987e5;--s1a:rgba(57,135,229,.22)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t1);
font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.sub{color:var(--t2);margin:0}
.bosh{display:flex;gap:14px;align-items:center;margin-bottom:20px}
.logo{flex:0 0 56px;height:56px;border-radius:50%;overflow:hidden}.logo svg{width:56px;height:56px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 10px;
display:flex;flex-direction:column;align-items:center;text-align:center}
.ring{width:96px;height:96px;border-radius:50%;display:grid;place-items:center;margin-bottom:8px;
background:conic-gradient(var(--s1) calc(var(--p)*1%),var(--grid) 0)}
.ring b{width:80px;height:80px;border-radius:50%;background:var(--surface);display:grid;place-items:center;
font-size:17px;padding:0 4px;line-height:1.1}
.kpi span{color:var(--t2);font-size:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.grid2 .card{margin-bottom:0}.grid2{margin-bottom:16px}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--t3);font-size:11px}
.hit{fill:transparent}.hit:hover{fill:var(--s1a)}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:7px 6px;border-bottom:1px solid var(--line)}
th{color:var(--t2);font-weight:600}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.bar{height:10px;border-radius:0 4px 4px 0;background:var(--s1);min-width:2px}
.muted{color:var(--t3)}.tw{overflow-x:auto}
details{margin-top:10px}summary{cursor:pointer;color:var(--t2);font-size:13px}
#tip{position:fixed;pointer-events:none;background:var(--t1);color:var(--surface);padding:6px 9px;
border-radius:8px;font-size:13px;opacity:0;transition:opacity .1s;white-space:nowrap;z-index:9}
@media (max-width:520px){main{padding:16px 16px 40px}svg text{font-size:21px}
table{font-size:13px}th,td{padding:6px 4px}.ring{width:84px;height:84px}.ring b{width:70px;height:70px;font-size:15px}}
"""

JS = """
const tip=document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el=>{
 el.addEventListener('mousemove',ev=>{tip.textContent=el.dataset.tip;tip.style.opacity=1;
  const x=Math.min(ev.clientX+12,innerWidth-tip.offsetWidth-8);tip.style.left=x+'px';tip.style.top=(ev.clientY-36)+'px'});
 el.addEventListener('mouseleave',()=>tip.style.opacity=0);
 el.addEventListener('click',ev=>{tip.textContent=el.dataset.tip;tip.style.opacity=1;
  tip.style.left=Math.max(8,Math.min(ev.clientX-40,innerWidth-tip.offsetWidth-8))+'px';tip.style.top=(ev.clientY-40)+'px'});
});
"""


def _yuqori(m):
    """O'q uchun chiroyli yuqori chegara: 4 ta teng, yumaloq qadam."""
    qadam = max(1.0, m / 4)
    q = 10 ** (len(str(int(qadam))) - 1)
    for k in (1, 2, 2.5, 5, 10):
        if k * q >= qadam and (k != 2.5 or q >= 10):
            return int(4 * k * q)
    return int(40 * q)


def _grafik(kunlar, qiymat, tur, format_):
    """tur: 'chiziq' (sotuv) yoki 'ustun' (yangi mijozlar). Bitta o'q."""
    W, H, L, R, T, B = 720, 230, 58, 12, 12, 26
    iw, ih = W - L - R, H - T - B
    n = len(kunlar)
    top = _yuqori(max(qiymat) if qiymat else 0)
    x = lambda i: L + (i + 0.5) * iw / n
    y = lambda v: T + ih - ih * v / top
    s = ['<svg viewBox="0 0 %d %d" role="img">' % (W, H)]
    for k in range(5):
        v = top * k / 4
        yy = y(v)
        s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="var(--grid)" stroke-width="1"/>'
                 % (L, W - R, yy, yy))
        s.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (L - 8, yy + 4, _e(format_(v, True))))
    for i, d in enumerate(kunlar):
        if i % 5 == (n - 1) % 5:
            s.append('<text x="%.1f" y="%d" text-anchor="middle">%s.%s</text>' % (x(i), H - 6, d[8:], d[5:7]))
    if tur == "chiziq":
        nuq = " ".join("%.1f,%.1f" % (x(i), y(v)) for i, v in enumerate(qiymat))
        s.append('<polygon points="%.1f,%.1f %s %.1f,%.1f" fill="var(--s1a)"/>'
                 % (x(0), y(0), nuq, x(n - 1), y(0)))
        s.append('<polyline points="%s" fill="none" stroke="var(--s1)" stroke-width="2" '
                 'stroke-linejoin="round" stroke-linecap="round"/>' % nuq)
        s.append('<circle cx="%.1f" cy="%.1f" r="4" fill="var(--s1)" stroke="var(--surface)" stroke-width="2"/>'
                 % (x(n - 1), y(qiymat[-1])))
    else:
        bw = max(2.0, iw / n - 4)
        for i, v in enumerate(qiymat):
            if v:
                h = ih * v / top
                r = min(4, bw / 2, h)
                x0, y0 = x(i) - bw / 2, y(v)
                s.append('<path d="M%.1f,%.1f v%.1f q0,-%.1f %.1f,-%.1f h%.1f q%.1f,0 %.1f,%.1f v%.1f z" fill="var(--s1)"/>'
                         % (x0, y(0), -(h - r), r, r, r, bw - 2 * r, r, r, r, h - r))
    for i, (d, v) in enumerate(zip(kunlar, qiymat)):
        s.append('<rect class="hit" x="%.1f" y="%d" width="%.1f" height="%d" data-tip="%s.%s — %s"/>'
                 % (L + i * iw / n, T, iw / n, ih, d[8:], d[5:7], _e(format_(v, False))))
    s.append("</svg>")
    return "".join(s)


def _jadval(sarlavha, qatorlar, raqamli=()):
    h = "".join('<th class="%s">%s</th>' % ("n" if i in raqamli else "", _e(t)) for i, t in enumerate(sarlavha))
    b = "".join("<tr>%s</tr>" % "".join('<td class="%s">%s</td>' % ("n" if i in raqamli else "", _e(c))
                                        for i, c in enumerate(q)) for q in qatorlar)
    return "<div class='tw'><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (h, b)


def _gorizontal(qatorlar, format_=str):
    """[(nom, qiymat)] — gorizontal ustunlar, qiymat matn bilan."""
    m = max((v for _, v in qatorlar), default=0) or 1
    s = ['<table>']
    for nom, v in qatorlar:
        s.append('<tr data-tip="%s — %s"><td style="width:38%%">%s</td><td><div class="bar" style="width:%.1f%%">'
                 '</div></td><td class="n" style="width:22%%">%s</td></tr>'
                 % (_e(nom), _e(format_(v)), _e(nom), 100 * v / m, _e(format_(v))))
    s.append("</table>")
    return "".join(s)


def html_hisobot(st, dokon="Sehrli Javon", logo=None):
    fs = lambda v, o: qisqa_som(v) if o else som(v)
    fm = lambda v, o: ("%d" % v) if o else "%d yangi mijoz" % v
    maqsad_p = min(100, round(100 * st["mijozlar"] / st["maqsad"])) if st["maqsad"] else 0
    kpi = [
        (maqsad_p, "%d%%" % maqsad_p, "Maqsad: %d / %d mijoz" % (st["mijozlar"], st["maqsad"])),
        (100, qisqa_som(st["tushum"]), "Jami tushum"),
        (100, str(st["buyurtmalar"]), "Buyurtmalar"),
        (100, qisqa_som(st["ortacha"]), "O'rtacha chek"),
        (st["konversiya"], "%d%%" % st["konversiya"], "Konversiya (ro'yxat → xarid)"),
        (round(100 * st["qayta"] / st["xaridorlar"]) if st["xaridorlar"] else 0,
         str(st["qayta"]), "Qayta xarid qilgan"),
    ]
    k_html = "".join('<div class="kpi"><div class="ring" style="--p:%d"><b>%s</b></div><span>%s</span></div>'
                     % (p, _e(v), _e(n)) for p, v, n in kpi)

    manba_q = [(m, r["ochgan"], r["royxat"], r["xaridor"], qisqa_som(r["tushum"])) for m, r in st["manbalar"]]
    p = [
        "<!doctype html><html lang='uz'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>Marketing tahlili</title><style>%s</style></head><body><main>" % CSS,
        "<header class='bosh'>%s<div><h1>%s — marketing tahlili</h1>" % (
            "<div class='logo'>%s</div>" % logo if logo else "", _e(dokon)),
        "<p class='sub'>%s holatiga · oxirgi %d kun</p>" % (
            time.strftime("%d.%m.%Y %H:%M", time.gmtime(st["vaqt"] + TOSHKENT)), len(st["kunlar"])) + "</div></header>",
        "<section class='kpis'>%s</section>" % k_html,
        "<section class='card'><h2>Kunlik sotuv (so'm)</h2>%s" % _grafik(st["kunlar"], st["sotuv"], "chiziq", fs),
        "<details><summary>Jadval ko'rinishi</summary>%s</details></section>" % _jadval(
            ["Kun", "Sotuv", "Buyurtmalar"],
            [(d, som(v), b) for d, v, b in zip(st["kunlar"], st["sotuv"], st["buyurtma"]) if v or b] or [("—", "—", "—")],
            raqamli=(1, 2)),
        "<section class='card'><h2>Yangi mijozlar (kuniga)</h2>%s" % _grafik(st["kunlar"], st["yangi"], "ustun", fm),
        "<details><summary>Jadval ko'rinishi</summary>%s</details></section>" % _jadval(
            ["Kun", "Yangi mijozlar"], [(d, v) for d, v in zip(st["kunlar"], st["yangi"]) if v] or [("—", "—")],
            raqamli=(1,)),
        "<div class='grid2'>",
        "<section class='card'><h2>Voronka</h2>%s</section>" % _gorizontal([
            ("Botni ochgan", st["ochgan"]), ("Ro'yxatdan o'tgan", st["mijozlar"]),
            ("Xarid qilgan", st["xaridorlar"]), ("Qayta xarid", st["qayta"])]),
        "<section class='card'><h2>Mijozlar yoshi</h2>%s</section>" % _gorizontal(st["yoshlar"]),
        "</div>",
        "<section class='card'><h2>Mijozlar qayerdan keldi</h2>%s<p class='muted'>Manba — "
        "<code>/havola nom</code> buyrug'i bergan havola (masalan, Instagram, varaqa, QR).</p></section>" % (
            _jadval(["Manba", "Ochgan", "Ro'yxat", "Xaridor", "Tushum"], manba_q, raqamli=(1, 2, 3, 4))
            if manba_q else "<p class='muted'>Hali ma'lumot yo'q.</p>"),
        "<div class='grid2'>",
        "<section class='card'><h2>Eng ko'p sotilgan</h2>%s</section>" % (
            _jadval(["Kitob", "Sotildi", "Qoldi"], st["top"], raqamli=(1, 2)) if st["top"]
            else "<p class='muted'>Hali sotuv yo'q.</p>"),
        "<section class='card'><h2>Sotilmayotganlar</h2>%s</section>" % (
            _jadval(["Kitob", "Sotildi", "Omborda", "Aksiya %"], st["sekin"], raqamli=(1, 2, 3)) if st["sekin"]
            else "<p class='muted'>Omborda kitob yo'q.</p>"),
        "</div><div class='grid2'>",
        "<section class='card'><h2>Promokodlar</h2>%s</section>" % (
            _jadval(["Kod", "Buyurtma", "Tushum", "Tejaldi"],
                    [(k, r["soni"], qisqa_som(r["tushum"]), qisqa_som(r["tejaldi"])) for k, r in st["promolar"]],
                    raqamli=(1, 2, 3)) if st["promolar"] else "<p class='muted'>Hali ishlatilmagan.</p>"),
        "<section class='card'><h2>To'lov turlari</h2>%s</section>" % (
            _gorizontal(st["tolov"]) if st["tolov"] else "<p class='muted'>Hali buyurtma yo'q.</p>"),
        "</div>",
        "<div id='tip' role='tooltip'></div><script>%s</script></main></body></html>" % JS,
    ]
    return "".join(p)


def _misol():
    """Namuna ma'lumot bilan sahifa (ko'rib chiqish uchun): python3 hisobot.py > misol.html"""
    import random
    random.seed(7)
    hozir = time.time()
    db = {"users": {}, "buyurtmalar": {}, "kitoblar": {
        "b1": {"nomi": "Alkimyogar", "sotildi": 41, "soni": 12}, "b2": {"nomi": "O'tkan kunlar", "sotildi": 33, "soni": 9},
        "b3": {"nomi": "Dyuna", "sotildi": 2, "soni": 30}, "b4": {"nomi": "Sapiens", "sotildi": 0, "soni": 18}}}
    manba = ["instagram", "varaqa", None, "telegram_kanal"]
    for i in range(420):
        ts = hozir - random.random() ** 1.6 * 29 * KUN
        c = str(i)
        db["users"][c] = {"id": c, "royxat": random.random() < .8, "royxat_sana": ts,
                          "yosh": random.randint(8, 55), "manba": random.choice(manba)}
    n = 0
    for c, u in db["users"].items():
        for _ in range(random.choice([0, 0, 1, 1, 2])):
            if not u["royxat"]:
                break
            n += 1
            db["buyurtmalar"][str(n)] = {"id": n, "chat": c, "holat": random.choice(["yangi", "yetkazildi", "yetkazildi", "bekor"]),
                                         "sana": u["royxat_sana"] + random.random() * KUN, "jami": random.randint(3, 25) * 10000,
                                         "asl": 0, "promo": random.choice([None, "SALOM10", "DOST20"]),
                                         "tolov": random.choice(["naqd", "karta", "click"])}
            db["buyurtmalar"][str(n)]["asl"] = int(db["buyurtmalar"][str(n)]["jami"] * 1.15)
    return statistika(db, {"dokon": {"maqsad_mijoz": 1000}})


if __name__ == "__main__":
    import os
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg"), encoding="utf-8") as f:
        print(html_hisobot(_misol(), logo=f.read()))

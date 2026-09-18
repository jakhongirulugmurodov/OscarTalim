#!/usr/bin/env python3
"""
Firebase loyihasini noldan tayyorlaydi — GitHub Actions ichida ishlaydi.

Kirish (muhit o'zgaruvchilari):
    GOOGLE_AUTH   Google'dan qaytgan http://localhost:9005/?...&code=... manzil
                  (yoki faqat code ning o'zi). Bir martalik, bir necha daqiqa yashaydi.
    PROJECT_ID    xohlagan loyiha identifikatori (band bo'lsa qo'shimcha qo'shiladi)
    LOCATION      Firestore joylashuvi (asia-south1 = Mumbay, O'zbekistonga eng yaqin)

Nima qiladi: loyiha → API lar → Firestore → anonim kirish → web ilova →
xavfsizlik qoidalari → config'ni docs/sinf/index.html ga yozadi.
Kalitlar faqat xotirada; log'ga chiqmaydi.
"""
import json, os, random, re, string, subprocess, sys, time
import urllib.request, urllib.parse, urllib.error

REPO = os.environ.get("GITHUB_WORKSPACE", ".")
CID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com"
CSEC = "j9iVZfS8kkCEFUPaAeJV0sAi"            # Firebase CLI ning ochiq (public) mijoz kaliti
REDIRECT = "http://localhost:9005"
PROJECT = (os.environ.get("PROJECT_ID") or "oscartalim-sinf").strip().lower()
LOCATION = (os.environ.get("LOCATION") or "asia-south1").strip()

def mask(s):
    if s: print("::add-mask::" + s, flush=True)

def die(msg):
    print("\n::error::" + msg, flush=True); sys.exit(1)

# ------------------------------------------------------------------ 0. rejim
MODE = sys.argv[1] if len(sys.argv) > 1 else "provision"

def post_form(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req) as r:
        return json.load(r)

if MODE == "exchange":
    # Birinchi qadam, npm o'rnatishdan ham oldin: bir martalik kod bir necha
    # soniyada kalitga aylanadi, kalit faqat shu ishning xotirasida (GITHUB_ENV,
    # niqoblangan) qoladi.
    raw = os.environ.get("GOOGLE_AUTH", "").strip()
    m = re.search(r"[?&]code=([^&\s]+)", raw)
    code = urllib.parse.unquote(m.group(1)) if m else raw
    mask(code)
    if not code or len(code) < 20:
        die("GOOGLE_AUTH bo'sh yoki noto'g'ri. Google'dan qaytgan localhost:9005/... manzilni to'liq bering.")
    try:
        tok = post_form("https://oauth2.googleapis.com/token", {
            "code": code, "client_id": CID, "client_secret": CSEC,
            "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "invalid_grant" in body:
            die("Kod eskirgan yoki allaqachon ishlatilgan. Google havolasini qaytadan ochib, yangi manzil bilan qayta ishga tushiring.")
        die("Token almashinuvi xatosi: " + body[:300])
    refresh = tok.get("refresh_token", "")
    mask(refresh); mask(tok.get("access_token", ""))
    if not refresh:
        die("refresh_token kelmadi — havolani 'prompt=consent' bilan qaytadan oching.")
    with open(os.environ["GITHUB_ENV"], "a") as f:
        f.write("FB_REFRESH=" + refresh + "\n")
    print("Google kirish: ok")
    sys.exit(0)

REFRESH = os.environ.get("FB_REFRESH", "")
mask(REFRESH)
if not REFRESH:
    die("FB_REFRESH yo'q — avval 'exchange' qadami bajarilishi kerak.")

def access_token():
    return post_form("https://oauth2.googleapis.com/token", {
        "client_id": CID, "client_secret": CSEC,
        "refresh_token": REFRESH, "grant_type": "refresh_token"})["access_token"]

def api(method, url, body=None):
    req = urllib.request.Request(url, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + access_token(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        try: return e.code, json.loads(txt)
        except ValueError: return e.code, {"raw": txt[:300]}

def fb(*args, project=True):
    cmd = ["firebase", *args, "--non-interactive"]
    if project: cmd += ["--project", PROJECT]
    p = subprocess.run(cmd, env=dict(os.environ, FIREBASE_TOKEN=REFRESH),
                       capture_output=True, text=True, cwd=REPO)
    return p.returncode, p.stdout, p.stderr

def fb_json(*args):
    code_, out, err = fb(*args, "--json")
    if "{" not in out:
        die(f"firebase {' '.join(args)}: JSON kelmadi\n{err[-600:]}")
    return json.loads(out[out.index("{"):])

def step(n): print(f"\n=== {n}", flush=True)

# ------------------------------------------------------------------ 1. loyiha
def wait_op(url, tries=40):
    """Uzoq davom etadigan operatsiya tugashini kutadi."""
    for _ in range(tries):
        s_, r = api("GET", url)
        if r.get("done"):
            return r
        time.sleep(3)
    return {"error": {"message": "operatsiya vaqtida tugamadi"}}

def err_text(r):
    e = r.get("error", {})
    return (e.get("message") or json.dumps(e)[:400]) if isinstance(e, dict) else str(e)[:400]

if MODE == "rules":
    # Faqat qoidalarni yangilash: loyiha allaqachon tayyor
    s_, lst = api("GET", "https://firebase.googleapis.com/v1beta1/projects?pageSize=50")
    for pr in (lst.get("results") or []) if s_ == 200 else []:
        if pr["projectId"].startswith(PROJECT.split("-")[0]) or pr["projectId"] == PROJECT:
            PROJECT = pr["projectId"]; break
    print("loyiha:", PROJECT)
    readme = open(f"{REPO}/docs/sinf/README.md", encoding="utf-8").read()
    rules = re.search(r"```js\n(rules_version.*?)```", readme, re.S).group(1)
    open(f"{REPO}/firestore.rules", "w").write(rules)
    open(f"{REPO}/firebase.json", "w").write(json.dumps({"firestore": {"rules": "firestore.rules"}}, indent=2) + "\n")
    open(f"{REPO}/.firebaserc", "w").write(json.dumps({"projects": {"default": PROJECT}}, indent=2) + "\n")
    c, out, err = fb("deploy", "--only", "firestore:rules")
    if c != 0:
        die("Qoidalar yuklanmadi:\n" + (out + err)[-2000:])
    print("qoidalar yuklandi")
    with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as f:
        f.write(f"## Qoidalar yangilandi\n\nLoyiha: `{PROJECT}`\n")
    sys.exit(0)

step("1. Google Cloud loyihasi")
s_, r = api("GET", f"https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT}")
if s_ == 200 and r.get("lifecycleState") == "ACTIVE":
    print("mavjud, davom etamiz:", PROJECT)
else:
    s_, r = api("POST", "https://cloudresourcemanager.googleapis.com/v1/projects",
                {"projectId": PROJECT, "name": "OscarTalim Sinf"})
    if s_ == 409:
        # kod dunyo bo'yicha band (boshqa odamniki) — qo'shimcha bilan
        PROJECT = f"{PROJECT}-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        s_, r = api("POST", "https://cloudresourcemanager.googleapis.com/v1/projects",
                    {"projectId": PROJECT, "name": "OscarTalim Sinf"})
    if s_ not in (200, 201):
        die("Google Cloud loyihasi yasalmadi: " + err_text(r))
    op = wait_op("https://cloudresourcemanager.googleapis.com/v1/" + r["name"])
    if "error" in op:
        die("Loyiha yasash operatsiyasi xato: " + err_text(op))
    print("yasaldi:", PROJECT)
    time.sleep(5)

step("1b. Loyihaga Firebase qo'shish")
s_, r = api("GET", f"https://firebase.googleapis.com/v1beta1/projects/{PROJECT}")
if s_ != 200:
    # Balki muallim konsolda boshqa ID bilan yasagan — nomi bo'yicha qidiramiz
    s2, lst = api("GET", "https://firebase.googleapis.com/v1beta1/projects?pageSize=50")
    for pr in (lst.get("results") or []) if s2 == 200 else []:
        if (pr.get("displayName") or "").strip().lower() in ("oscartalim sinf", PROJECT):
            PROJECT = pr["projectId"]; s_ = 200
            print("konsolda yasalgan loyiha topildi:", PROJECT)
            break
if s_ == 200:
    print("Firebase allaqachon ulangan:", PROJECT)
else:
    s_, r = api("POST", f"https://firebase.googleapis.com/v1beta1/projects/{PROJECT}:addFirebase", {})
    if s_ not in (200, 201):
        msg = err_text(r)
        if "erms of" in msg or "ToS" in msg or "TOS" in msg or s_ == 403:
            die("Firebase qo'shilmadi: " + msg + "\n\n"
                "Ko'p hollarda sabab — Firebase foydalanish shartlari hali qabul qilinmagan. "
                "Shu Google akkaunt bilan https://console.firebase.google.com ni bir marta oching, "
                "shartlarni qabul qiling (loyiha yasash shart emas), keyin yangi Google kodi bilan qayta ishga tushiring.")
        die("Firebase qo'shilmadi: " + msg)
    op = wait_op("https://firebase.googleapis.com/v1beta1/" + r["name"])
    if "error" in op:
        die("Firebase qo'shish operatsiyasi xato: " + err_text(op))
    print("Firebase ulandi")

# ------------------------------------------------------------------ 2. API lar
step("2. API larni yoqish")
for svc in ["firestore.googleapis.com", "identitytoolkit.googleapis.com", "firebaserules.googleapis.com"]:
    s, r = api("POST", f"https://serviceusage.googleapis.com/v1/projects/{PROJECT}/services/{svc}:enable", {})
    print(f"  {svc}: {s}")
time.sleep(8)

# ------------------------------------------------------------------ 3. Firestore
step("3. Firestore")
c, out, err = fb("firestore:databases:create", "(default)", "--location", LOCATION)
if c != 0 and "already exists" not in (out + err).lower():
    s, r = api("POST", f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases?databaseId=(default)",
               {"type": "FIRESTORE_NATIVE", "locationId": LOCATION})
    if s not in (200, 409):
        die("Firestore yasalmadi: " + str(r)[:400] + "\n" + err[-400:])
print("firestore:", LOCATION)

# ------------------------------------------------------------------ 4. anonim kirish
step("4. Anonim kirish")
cfg_url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{PROJECT}/config"
url = cfg_url + "?updateMask=signIn.anonymous.enabled"
body = {"signIn": {"anonymous": {"enabled": True}}}
s, r = api("PATCH", url, body)
if s == 404:
    # Authentication hali ishga tushirilmagan — ishga tushirib, config paydo bo'lishini kutamiz
    s0, r0 = api("POST", f"https://identitytoolkit.googleapis.com/v2/projects/{PROJECT}/identityPlatform:initializeAuth", {})
    print("initializeAuth →", s0, "" if s0 == 200 else str(r0)[:200])
    for _ in range(20):
        sg, rg = api("GET", cfg_url)
        if sg == 200:
            break
        time.sleep(4)
    s, r = api("PATCH", url, body)
if s != 200:
    die("Anonim kirish yoqilmadi: " + str(r)[:300] + "\n\n"
        "Konsolda bir marta qo'lda: https://console.firebase.google.com/project/" + PROJECT +
        "/authentication → Get started → Sign-in method → Anonymous → Enable → Save. "
        "Keyin yangi Google kodi bilan qayta ishga tushiring.")
print("anonim kirish: yoqildi")

# ------------------------------------------------------------------ 4b. email/parol kirish
step("4b. Email/parol kirish")
url_ep = cfg_url + "?updateMask=signIn.email.enabled,signIn.email.passwordRequired"
body_ep = {"signIn": {"email": {"enabled": True, "passwordRequired": True}}}
s, r = api("PATCH", url_ep, body_ep)
if s != 200:
    print("::warning::Email/parol kirish avtomatik yoqilmadi (" + str(r)[:200] + "). "
          "Docs/tugilgankun ilovasi mahalliy rejimda ishlayveradi; bulutli qilish uchun "
          "konsolda qo'lda yoqing: https://console.firebase.google.com/project/" + PROJECT +
          "/authentication → Sign-in method → Email/Password → Enable.")
else:
    print("email/parol kirish: yoqildi")

# ------------------------------------------------------------------ 5. web ilova
step("5. Web ilova")
apps = fb_json("apps:list", "WEB").get("result", [])
if not apps:
    c, out, err = fb("apps:create", "WEB", "AI Sinf")
    if c != 0: die("Web ilova yasalmadi: " + (out + err)[-600:])
    apps = fb_json("apps:list", "WEB").get("result", [])
app_id = apps[0]["appId"]
cfg = fb_json("apps:sdkconfig", "WEB", app_id)["result"]["sdkConfig"]
cfg = {k: cfg[k] for k in ["apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId"] if k in cfg}
print("config:", ", ".join(cfg))

# ------------------------------------------------------------------ 6. qoidalar
step("6. Xavfsizlik qoidalari")
readme = open(f"{REPO}/docs/sinf/README.md", encoding="utf-8").read()
rules = re.search(r"```js\n(rules_version.*?)```", readme, re.S).group(1)
open(f"{REPO}/firestore.rules", "w").write(rules)
open(f"{REPO}/firebase.json", "w").write(json.dumps({"firestore": {"rules": "firestore.rules"}}, indent=2) + "\n")
open(f"{REPO}/.firebaserc", "w").write(json.dumps({"projects": {"default": PROJECT}}, indent=2) + "\n")
c, out, err = fb("deploy", "--only", "firestore:rules")
if c != 0: die("Qoidalar yuklanmadi:\n" + (out + err)[-2000:])
print("qoidalar: yuklandi")

# ------------------------------------------------------------------ 7. config → dastur
step("7. Config dasturga")
p = f"{REPO}/docs/sinf/index.html"
src = open(p, encoding="utf-8").read()
new = "const FB_CONFIG = " + json.dumps(cfg, indent=2) + ";"
src, n = re.subn(r"const FB_CONFIG = (null|\{.*?\});", new, src, count=1, flags=re.S)
if not n: die("index.html ichida FB_CONFIG topilmadi")
open(p, "w", encoding="utf-8").write(src)
print("yozildi: docs/sinf/index.html")

with open(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"), "a") as f:
    f.write(f"## Firebase ulandi\n\n- Loyiha: `{PROJECT}`\n- Firestore: `{LOCATION}`\n"
            f"- Anonim kirish: yoqildi\n- Qoidalar: yuklandi\n- Config: `docs/sinf/index.html`\n\n"
            f"Konsol: https://console.firebase.google.com/project/{PROJECT}\n")
print("\nTAYYOR:", PROJECT)

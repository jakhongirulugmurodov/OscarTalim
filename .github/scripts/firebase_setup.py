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

# ------------------------------------------------------------------ 0. kod → kalit
raw = os.environ.get("GOOGLE_AUTH", "").strip()
m = re.search(r"[?&]code=([^&\s]+)", raw)
code = urllib.parse.unquote(m.group(1)) if m else raw
mask(code)
if not code or len(code) < 20:
    die("GOOGLE_AUTH bo'sh yoki noto'g'ri. Google'dan qaytgan localhost:9005/... manzilni to'liq bering.")

def post_form(url, data):
    req = urllib.request.Request(url, urllib.parse.urlencode(data).encode())
    with urllib.request.urlopen(req) as r:
        return json.load(r)

try:
    tok = post_form("https://oauth2.googleapis.com/token", {
        "code": code, "client_id": CID, "client_secret": CSEC,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code"})
except urllib.error.HTTPError as e:
    body = e.read().decode()
    if "invalid_grant" in body:
        die("Kod eskirgan yoki ishlatilgan. Google havolasini qaytadan ochib, yangi manzil bilan qayta ishga tushiring.")
    die("Token almashinuvi xatosi: " + body[:300])

REFRESH = tok.get("refresh_token", ""); ACCESS = tok.get("access_token", "")
mask(REFRESH); mask(ACCESS)
if not REFRESH:
    die("refresh_token kelmadi — havolani 'prompt=consent' bilan qaytadan oching.")
print("Google kirish: ok")

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
step("1. Loyiha")
def create(pid):
    c, out, err = fb("projects:create", pid, "--display-name", "OscarTalim Sinf", project=False)
    return c, out + err
c, out = create(PROJECT)
if c != 0:
    low = out.lower()
    if "terms of service" in low or "tos" in low and "accept" in low:
        die("Google/Firebase foydalanish shartlari qabul qilinmagan. Shu akkaunt bilan "
            "console.firebase.google.com ni bir marta ochib, shartlarni qabul qiling va qayta ishga tushiring.")
    if "already exists" in low or "already_exists" in low or "in use" in low:
        # global band bo'lsa — qo'shimcha bilan
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        alt = f"{PROJECT}-{suffix}"
        c2, out2 = create(alt)
        if c2 != 0:
            # balki bizniki — mavjud loyihani ishlataveramiz
            s, r = api("GET", f"https://firebase.googleapis.com/v1beta1/projects/{PROJECT}")
            if s != 200:
                die("Loyiha yaratilmadi:\n" + out[-800:] + "\n" + out2[-800:])
            print("mavjud loyiha ishlatiladi:", PROJECT)
        else:
            PROJECT = alt
    else:
        die("Loyiha yaratilmadi:\n" + out[-1200:])
print("loyiha:", PROJECT)

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
        die("Firestore yaratilmadi: " + str(r)[:400] + "\n" + err[-400:])
print("firestore:", LOCATION)

# ------------------------------------------------------------------ 4. anonim kirish
step("4. Anonim kirish")
url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{PROJECT}/config?updateMask=signIn.anonymous.enabled"
body = {"signIn": {"anonymous": {"enabled": True}}}
s, r = api("PATCH", url, body)
if s == 404:
    api("POST", f"https://identitytoolkit.googleapis.com/v2/projects/{PROJECT}/identityPlatform:initializeAuth", {})
    time.sleep(3)
    s, r = api("PATCH", url, body)
if s != 200:
    die("Anonim kirish yoqilmadi: " + str(r)[:400])
print("anonim kirish: yoqildi")

# ------------------------------------------------------------------ 5. web ilova
step("5. Web ilova")
apps = fb_json("apps:list", "WEB").get("result", [])
if not apps:
    c, out, err = fb("apps:create", "WEB", "AI Sinf")
    if c != 0: die("Web ilova yaratilmadi: " + (out + err)[-600:])
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
if c != 0: die("Qoidalar yuklanmadi: " + (out + err)[-800:])
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

# AI Kursi — Sinf paneli

13 darslik AI kursi uchun o'quvchilar dasturi. Telegram Mini App sifatida ham,
oddiy web-sahifa sifatida ham ishlaydi.

**Asosiy qoida: ball o'yindan emas, ishdan chiqadi.**

## Nega shunday qurilgan

O'quvchilar Kahoot so'rashadi, chunki u uchta narsani beradi: 10 soniyalik
qaytish aloqasi, natijaning noaniqligi va ko'rinadigan status. Dars buni
bermaydi — shuning uchun o'yin "darsdan qutulish" bo'lib qoladi.

Muammo o'yinning ko'pligida emas, **ball nimaga berilishida**. Shuning uchun
bu dasturda:

- ballning ~70% i **ishdan** keladi (muammo ro'yxati, prompt, yolg'on ovi,
  loyiha jurnali), o'yin qolganini beradi;
- o'yin dars **boshida** turadi (o'tgan darsni eslash), oxirida mukofot emas —
  aks holda dars o'yinga to'lanadigan narxga aylanadi;
- haftalik reyting har dushanba **noldan** boshlanadi, shuning uchun 4-haftada
  orqada qolgan bola 5-haftada yutishi mumkin;
- savollar fakt emas, **hukm** talab qiladi ("bu javobda AI yolg'on gapirdimi?"),
  ya'ni o'yin kursning o'z ko'nikmasini mashq qildiradi;
- har darsdagi 15 daqiqalik loyiha yozuvi jurnalga tushadi va 13-darsda
  **portfolio** bo'lib chiqadi.

## Ball jadvali

| Nima qildi | Ball | Dars |
|---|---|---|
| Ro'yxatga yangi real muammo qo'shdi | +10 (10 tagacha) | 1 |
| Ikki yo'l tahlili | +15 | 1 |
| 3 savol filtri | +15 | 2 |
| Katta ishni bosqichlarga bo'ldi | +20 | 3 |
| Bir fikrni uch darajada yozdi | +20 | 4 |
| **AI javobidagi yolg'onni ushladi** | **+25** | 5 |
| To'rt qismli vazifa (rol/sharoit/misol/format) | +20 | 7 |
| Chegara chizdi | +20 | 9 |
| Loyiha jurnaliga qaror yozdi | +15 | har dars |
| Jonli duel — to'g'ri javob | +10 va tezlik uchun +20 gacha | har dars |
| Ovoz berish / bahsda qatnashdi | +5 | har dars |

**Jonli o'yindan bir darsda ko'pi bilan 30 ball olinadi** (`LIVE_CAP`).
Shiftga yetgach o'yin qiziq bo'lib qolaveradi, lekin reytingni faqat ish
ko'taradi. Raqamni `index.html` dagi bitta qatordan o'zgartirsangiz bo'ladi.

Daraja: Yangi → Kuzatuvchi → Savol beruvchi → Tekshiruvchi → Ovchi →
Vazifa qo'yuvchi → Usta → Muallif → Himoyachi → **Oskar**.

## Dars ritmi (60 daqiqa)

```
0–7    Jonli duel — o'tgan darsni eslash (muallim paneli → Jonli)
7–20   Yangi g'oya (dasturda "Asosiy fikrlar")
20–45  Dasturdagi vazifa — ball shu yerda oqadi
45–57  Loyiha 15 daqiqasi + jurnal yozuvi
57–60  Proyektorda reyting, keyingi darsni e'lon qilish
```

## O'quvchi yo'li

1. Botda **/start** → "Dasturni ochish".
2. Sinf kodi, to'liq ism, loyiha guruhi.
3. **Rasmga tushadi** — muallim uni tanishi uchun.
4. **Face ID / barmoq izi** bilan tasdiqlaydi (quyiga qarang).
5. Muallim tasdiqlagach dastur ochiladi.
6. **O'tilmagan darslar qulf bilan turadi.** Muallim darsni ochganda
   o'quvchida o'zi paydo bo'ladi.

## "Face ID" aslida nima qiladi

Bu yuzni serverda taqqoslash emas — bu **qurilmadan egasini so'rash**:

- Telegram ichida: `WebApp.BiometricManager` (Face ID / Touch ID / barmoq izi);
- oddiy brauzerda: **WebAuthn** platforma autentifikatori (HTTPS shart).

Ya'ni boshqa bola sening telefoningdan sening nomingdan kira olmaydi.
Rasm esa boshqa vazifani bajaradi: muallim ro'yxatdan o'tayotgan bola
haqiqatan o'z sinfidan ekanini ko'radi. Rasm faqat sinf ma'lumotlar bazasida
saqlanadi, boshqa hech qayerga yuborilmaydi.

Qurilma biometriyani qo'llamasa, kirish to'xtatilmaydi — muallim tasdiqlashi
baribir talab qilinadi.

## Muallim paneli

| Bo'lim | Nima qiladi |
|---|---|
| **Dars** | Qaysi darsgacha ochiq — bir bosishda. Qolganlari qulfda |
| **Tasdiq** | Yangi ro'yxatdan o'tganlar rasmi bilan; tasdiqlash / rad etish |
| **Jonli** | Duel (dars savollari), Yolg'on ovi, Ovoz berish; proyektor rejimi |
| **Reyting** | Haftalik + umumiy; "Haftani yakunlash" tugmasi |
| **Ro'yxat** | Har bir o'quvchi nima yozganini o'qish |

Proyektor rejimi — "Jonli" yoki "Reyting" bo'limidagi tugma: shrift kattalashadi
va to'liq ekranga o'tadi.

## Firebase'ni ulash

### Eng oson yo'l — GitHub o'zi qiladi (2 daqiqa)

1. Shu havolani oching, Google akkauntingizga kiring, **Allow** bosing:

   ```
   https://accounts.google.com/o/oauth2/auth?client_id=563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com&scope=email+openid+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloudplatformprojects.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Ffirebase+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcloud-platform&response_type=code&state=oscartalim&redirect_uri=http%3A%2F%2Flocalhost%3A9005&access_type=offline&prompt=consent
   ```

   Brauzer `http://localhost:9005/?...&code=...` ga o'tadi va "ochilmadi" deydi —
   bu normal. Manzil qatoridagi **butun URL** ni nusxalang.
2. Repo → **Actions → Firebase sozlash → Run workflow** → `google_auth` ga o'sha
   URL ni qo'ying → Run. 2-3 daqiqada loyiha, Firestore, anonim kirish, qoidalar
   tayyor bo'ladi va config `index.html` ga o'zi yoziladi.

Kod bir martalik va bir necha daqiqa yashaydi — nusxalab darhol ishga tushiring.
Bu Firebase CLI ishlatadigan rasmiy kirish usuli; kalitlar faqat GitHub
serverining xotirasida bo'ladi, hech qayerda saqlanmaydi.

### Qo'lda (konsol orqali, 10 daqiqa)

1. [console.firebase.google.com](https://console.firebase.google.com) → yangi loyiha.
2. **Build → Firestore Database** → Create database.
3. **Build → Authentication → Sign-in method → Anonymous** → yoqing.
4. **Project settings → Your apps → Web** → config'ni nusxa oling.
5. `index.html` faylida `FB_CONFIG = null` o'rniga o'sha config'ni qo'ying.

Xavfsizlik qoidalari (Firestore → Rules):

```js
rules_version = '2';
service cloud.firestore {
  match /databases/{db}/documents {
    function signedIn(){ return request.auth != null; }
    function me(){ return request.auth.uid; }
    function isTeacher(c){ return signedIn() &&
      exists(/databases/$(db)/documents/classes/$(c)/teachers/$(request.auth.uid)); }
    function stu(c, sid){ return get(/databases/$(db)/documents/classes/$(c)/students/$(sid)).data; }
    function same(k){ return request.resource.data[k] == resource.data[k]; }
    function sameFlag(k){ return request.resource.data.get(k,false) == resource.data.get(k,false); }

    // Bosh kalit: sinf yaratish huquqi. Mijoz uni o'qiy olmaydi.
    match /config/admin {
      allow read, update, delete: if false;
      allow create: if signedIn();
    }

    match /classes/{c} {
      allow read:   if signedIn();
      allow create: if signedIn() && request.resource.data.createdBy == me() &&
        get(/databases/$(db)/documents/classes/$(c)/private/auth).data.owner == me();
      allow update: if isTeacher(c);

      match /private/auth {
        allow read:   if isTeacher(c);
        allow create: if signedIn() &&
          !exists(/databases/$(db)/documents/classes/$(c)) &&
          request.resource.data.owner == me() &&
          request.resource.data.key == get(/databases/$(db)/documents/config/admin).data.key;
        // PIN ni tiklash: bosh kalitni bilgan odam yangi PIN qo'yadi
        allow update: if isTeacher(c) ||
          (signedIn() && request.resource.data.key == resource.data.key);
      }
      match /teachers/{uid} {
        allow read:  if signedIn() && (me() == uid || isTeacher(c));
        allow write: if signedIn() && me() == uid && request.resource.data.pin ==
          get(/databases/$(db)/documents/classes/$(c)/private/auth).data.pin;
      }

      // Reyting uchun ochiq: ism, guruh, ball, streak. Egalik — authUid.
      match /students/{sid} {
        allow read:   if signedIn();
        allow create: if signedIn() && request.resource.data.authUid == me()
                      && request.resource.data.ok == false;
        allow update: if isTeacher(c)
          // egasi: o'z ballini yozadi, lekin o'zini tasdiqlay va egalikni o'zgartira olmaydi
          || (signedIn() && resource.data.authUid == me()
              && same('ok') && sameFlag('rejected') && same('authUid'))
          // qurilma bo'sh yoki Telegram hisobi — egallanadi
          || (signedIn() && request.resource.data.authUid == me()
              && (resource.data.get('authUid','') == '' || sid.matches('tg[0-9]+'))
              && same('ok') && sameFlag('rejected'))
          // boshqa qurilmadan so'rov: faqat claimUid o'zgaradi, muallim tasdiqlaydi
          || (signedIn() && request.resource.data.claimUid == me()
              && request.resource.data.diff(resource.data).affectedKeys().hasOnly(['claimUid']));
        allow delete: if isTeacher(c);

        match /entries/{e} {
          allow read:  if signedIn();
          allow write: if isTeacher(c) || (signedIn() && stu(c,sid).authUid == me());
        }
      }

      // Rasm va Telegram ma'lumoti: faqat egasi va muallim
      match /profiles/{sid} {
        allow read:  if isTeacher(c) || (signedIn() && stu(c,sid).authUid == me());
        allow write: if isTeacher(c) || (signedIn() &&
          (!exists(/databases/$(db)/documents/classes/$(c)/students/$(sid))
           || stu(c,sid).authUid == me()));
      }

      // Muallim yozadigan vazifalar va Kahoot import yozuvlari
      match /tasks/{t}   { allow read: if signedIn(); allow write: if isTeacher(c); }
      match /imports/{i} { allow read: if signedIn(); allow write: if isTeacher(c); }
      match /live/{d}  { allow read: if signedIn(); allow write: if isTeacher(c); }
      match /answers/{key}/votes/{uid} {
        allow read:  if signedIn();
        allow write: if signedIn() && me() == uid;
      }
    }
  }
}
```

> Mahalliy rejimda bir brauzerdagi barcha varaqlar bitta xotiraga yozadi,
> shuning uchun bir vaqtda bir necha "o'quvchi" ball olsa, biri yo'qolishi
> mumkin. Bulutda bunday emas — har kim o'z hujjatiga atomik yozadi.

`FB_CONFIG` bo'sh qolsa dastur **mahalliy rejim**da ishlaydi: hamma narsa shu
qurilmaning `localStorage` ida. Sinovdan o'tkazish uchun qulay, haqiqiy sinf
uchun yaramaydi (bir qurilmadagi ikki brauzer varag'i bir-birini ko'radi, xolos).

## Telegram bot

Bot **GitHub Actions'da** ishlaydi — alohida server kerak emas. Har 5
daqiqada kelgan xabarlarni tekshiradi va javob beradi (ya'ni `/start` ga javob
0–5 daqiqa ichida keladi; menyu tugmasi esa darhol ishlaydi).

Bir marta sozlash:

1. **@BotFather** → `/newbot` → token.
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**:
   nomi `TELEGRAM_BOT_TOKEN`, qiymati — token.
3. (Ixtiyoriy) o'sha yerda **Variables** → `TELEGRAM_ADMIN_IDS` = sizning
   Telegram ID ingiz (botga `/men` deb yozsangiz aytadi). Shunda `/eslatma`
   va `/kim` buyruqlari sizga ochiladi.
4. **Actions → Telegram bot → Run workflow → rejim: `sozlash`** — menyu
   tugmasi, buyruqlar va tavsif o'rnatiladi.

Eslatma yuborish: **Run workflow → rejim: `eslatma`**, matnni yozing — botga
yozilgan hamma o'quvchiga boradi. Yoki Telegram'da `/eslatma matn`.

Agar GitHub jadvalli ishga tushirishni kechiktirsa (bu bo'lib turadi),
**Run workflow → rejim: `xabarlar`** kutib turgan xabarlarga darhol javob beradi —
dars oldidan bir marta bosib qo'yish kifoya.

Sinf kodi bilan havola: `t.me/<bot>?start=AI13` — kod dastur ichiga o'zi tushadi.

Bot buyruqlari: `/start`, `/kod AI13`, `/men`, `/eslatma <matn>` (muallim),
`/kim` (muallim).

O'z serveringiz bo'lsa, doimiy rejim ham bor:

```bash
export BOT_TOKEN="..." APP_URL="https://<foydalanuvchi>.github.io/OscarTalim/sinf/"
python3 bot/bot.py
```

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/sinf/
```

Bir brauzerda ikki varaq oching: birida muallim paneli, ikkinchisida o'quvchi.
Ikkinchi varaqda boshqa o'quvchi bo'lish uchun konsolda:
`localStorage.setItem('sinf:uid','u2'); localStorage.clear` emas —
faqat `sinf:uid`, `sinf:role`, `sinf:code` kalitlarini o'zgartiring.

## Xavfsizlik: nima himoyalangan, nima emas

Himoyalangan (Firestore qoidalari bilan, mijoz kodiga ishonmasdan):

- **Sinf yaratish** faqat *bosh kalit* bilan — uni birinchi muallim belgilaydi,
  mijoz hech qachon o'qiy olmaydi, server solishtiradi.
- **Muallim PIN i** sinf hujjatida emas — `private/auth` da, faqat muallim o'qiydi.
  PIN esdan chiqsa, bosh kalit bilan tiklanadi.
- **O'quvchi o'zini tasdiqlay olmaydi** va **o'z hisobining egaligini**
  (`authUid`) o'zgartira olmaydi.
- **Boshqa o'quvchining hisobiga yozib bo'lmaydi** — faqat egalik qilayotgan
  qurilma yozadi. Yangi qurilmadan kirish = so'rov, muallim tasdiqlaydi.
- **Rasm va Telegram ID** alohida `profiles/` da — faqat egasi va muallim o'qiydi.
- **Javoblar**: har kim faqat o'z ovozini yozadi.
- **Vazifa qo'shish, darsni ochish, jonli o'yin, o'quvchini o'chirish** — faqat muallim.
- Foydalanuvchi kiritgan har qanday matn va rasm ekranga qochirib chiqariladi.

Hozircha bor cheklovlar:

- **Telegram hisobini raqamini bilgan odam egallashi mumkin.** `initData`
  server tomonda tekshirilmagani uchun, kimningdir Telegram raqamini bilgan
  odam uning hisobiga kira oladi. Raqamlar faqat muallimga ko'rinadi.
- **Savollar javobi mijoz faylida.** Duel savollari `index.html` ichida, ya'ni
  devtools ochgan bola javobni ko'ra oladi. Keyingi bosqich: savollar bazasini
  Firestore'ga ko'chirib, o'qishni faqat muallimga ochish.
- **Ballni mijoz yozadi.** Sinf sharoitida yetarli (muallim "Ro'yxat"
  bo'limida ish bor-yo'qligini ko'radi), lekin qat'iy hisob kerak bo'lsa
  Cloud Functions orqali yozish kerak.
- **PIN ni terib ko'rish** (brute force) qoidalar darajasida cheklanmagan —
  shuning uchun PIN kamida 6 belgi (dastur qisqasini qabul qilmaydi).
- **Telegram `initData` server tomonda tekshirilmagan.** Hozir dastur
  `initDataUnsafe` ga ishonadi. Ishonchli qilish uchun bot tokeni bilan HMAC-SHA256
  tekshiruvi (`WebAppData` kaliti) server tomonda bajarilishi kerak.

## Fayllar

```
docs/sinf/
├── index.html            # butun dastur (HTML + CSS + JS + kurs mazmuni)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti
├── icon.svg, icon-maskable.svg
└── README.md
bot/
├── bot.py                # Telegram bot (faqat standart kutubxona)
└── requirements.txt
.github/workflows/
└── telegram-bot.yml      # bot GitHub Actions'da: har 5 daqiqada + qo'lda
```

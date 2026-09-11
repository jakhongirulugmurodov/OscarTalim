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

## Firebase sozlash (10 daqiqa)

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
    function signedIn()  { return request.auth != null; }
    function isTeacher(c){ return signedIn() &&
      request.auth.uid in get(/databases/$(db)/documents/classes/$(c)).data.teachers; }

    match /classes/{c} {
      allow read:   if signedIn();
      allow create: if signedIn();
      allow update: if isTeacher(c);

      match /students/{uid} {
        allow read:   if signedIn();
        allow create: if signedIn() && request.auth.uid == uid;
        // o'quvchi faqat o'zini yozadi va o'zini tasdiqlay olmaydi
        allow update: if isTeacher(c) ||
          (request.auth.uid == uid &&
           request.resource.data.ok == resource.data.ok);

        match /entries/{e} {
          allow read:  if signedIn();
          allow write: if request.auth.uid == uid;
        }
      }
      match /live/{d}    { allow read: if signedIn(); allow write: if isTeacher(c); }
      match /answers/{a} { allow read: if signedIn(); allow write: if signedIn(); }
    }
  }
}
```

`FB_CONFIG` bo'sh qolsa dastur **mahalliy rejim**da ishlaydi: hamma narsa shu
qurilmaning `localStorage` ida. Sinovdan o'tkazish uchun qulay, haqiqiy sinf
uchun yaramaydi (bir qurilmadagi ikki brauzer varag'i bir-birini ko'radi, xolos).

## Telegram bot

```bash
export BOT_TOKEN="BotFather bergan token"
export APP_URL="https://<foydalanuvchi>.github.io/OscarTalim/sinf/"
export ADMIN_IDS="<sizning Telegram ID ingiz>"
python3 bot/bot.py
```

BotFather'da: `/newbot` → token; keyin `/setmenubutton` (yoki bot o'zi qo'yadi).
Sinf kodi bilan havola: `t.me/<bot>?start=AI13` — kod dastur ichiga o'zi tushadi.

Bot buyruqlari: `/start`, `/kod AI13`, `/eslatma <matn>` (muallim),
`/kim` (muallim).

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/sinf/
```

Bir brauzerda ikki varaq oching: birida muallim paneli, ikkinchisida o'quvchi.
Ikkinchi varaqda boshqa o'quvchi bo'lish uchun konsolda:
`localStorage.setItem('sinf:uid','u2'); localStorage.clear` emas —
faqat `sinf:uid`, `sinf:role`, `sinf:code` kalitlarini o'zgartiring.

## Hozircha bor cheklovlar

- **Savollar javobi mijoz faylida.** Duel savollari `index.html` ichida, ya'ni
  devtools ochgan bola javobni ko'ra oladi. Keyingi bosqich: savollar bazasini
  Firestore'ga ko'chirib, o'qishni faqat muallimga ochish.
- **Ballni mijoz yozadi.** Sinf sharoitida yetarli (muallim "Ro'yxat"
  bo'limida ish bor-yo'qligini ko'radi), lekin qat'iy hisob kerak bo'lsa
  Cloud Functions orqali yozish kerak.
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
```

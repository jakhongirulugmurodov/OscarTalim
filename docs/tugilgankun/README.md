# Tug'ilgan kunlar eslatuvchisi

Yaqinlaringizning tug'ilgan kunini hech qachon unutmaslik uchun — **to'liq bepul**
veb-ilova. Bitta fayl: HTML + CSS + JS, backend — Firebase (yoki mahalliy rejim).

## Qanday ishlaydi

1. **Ro'yxatdan o'tish** — telefon raqam yoki email + parol bilan.
2. **Kamida 5 ta tug'ilgan kun kiritiladi** (10 tagacha bo'lsa yanada yaxshi):
   har birida ism-familiya, kun, oy va (ixtiyoriy) yil. Har biri alohida
   "Saqlash" bosilib, birma-bir qo'shiladi — progress-bar nechta qolganini
   ko'rsatib turadi.
3. Kamida 5 ta kiritilgach, **asosiy panel** ochiladi — bu yerda **hamma
   ro'yxatdan o'tgan foydalanuvchi qo'shgan tug'ilgan kunlar birgalikda**
   ko'rinadi (masalan, oila yoki do'stlar guruhi uchun umumiy taqvim sifatida):
   - Tug'ilgan kuniga eng kam qolgan odamlar **tepada**, katta va rangli
     bannerlar bilan chiqadi (masalan: *"Yuldashev Olimjon tug'ilgan kuniga
     2 kun qoldi"*, ertaga uchun *"1 kun qoldi"*, bugun uchun *"Bugun!"*).
   - Uzoqroq tug'ilgan kunlar ro'yxat **pastida** turadi — sanalar o'zgargani
     sayin (kunlar kamayib borgani sayin) ular avtomatik yuqoriga ko'tariladi.
   - **Faqat o'zingiz qo'shgan yozuvni** tahrirlash yoki o'chirish mumkin
     (u "siz qo'shgansiz" deb belgilanadi) — boshqalar qo'shgan yozuvlar
     faqat ko'rish uchun. Pastdagi **➕** tugma bilan istalgan vaqt yangi
     tug'ilgan kun qo'shiladi.
4. **Brauzer bildirishnomasi**: ruxsat berilsa, tug'ilgan kuniga 2, 1 va
   0 kun qolganda tizim bildirishnomasi chiqadi (kuniga bir marta, takror
   yubormaydi) — bu hammaning ro'yxatiga tegishli.

> **Muhim:** "hamma bir-birining tug'ilgan kunini ko'rishi" faqat **bulutli
> rejim**da ishlaydi (pastga qarang). Mahalliy rejimda ma'lumot faqat shu
> qurilmada qoladi va boshqa hech kimga ko'rinmaydi — chunki u serverga
> umuman yuborilmaydi.

## Nega bepul

- **Mahalliy rejim** (standart holat, sozlash shart emas): hisob va
  tug'ilgan kunlar shu qurilmaning `localStorage`'ida saqlanadi — hech qanday
  server, hisob yoki to'lov kerak emas.
- **Bulutli rejim** (ixtiyoriy): shu repodagi umumiy Firebase loyihasi
  (`oscartalim-sinf-80da0`) qayta ishlatiladi — Firestore va
  Authentication'ning **Spark (bepul) tarifi** doirasida, telefon SMS
  tasdiqlash ishlatilmaydi (u pullik bo'lardi). Buning o'rniga telefon
  raqami email formatiga o'giriladi (`tel<raqam>@tugilgankun.uz`) va odatiy
  **Email/Parol** kirish usuli orqali hisob yaratiladi — bu usul Firebase'da
  har doim bepul.

## Bulutli rejimni yoqish (ixtiyoriy — ma'lumotlar istalgan qurilmadan ochilishi uchun)

Agar Firebase loyihasida **Email/Password** kirish usuli hali yoqilmagan
bo'lsa, ilova buni avtomatik payqaydi va **mahalliy rejimga o'tadi** — sayt
baribir to'liq ishlayveradi, faqat ma'lumot bitta qurilmada qoladi.

Bulutli (ko'p qurilmali) rejimni yoqish uchun ikki yo'l bor:

1. **Avtomatik**: repo → **Actions → Firebase sozlash → Run workflow** —
   `docs/sinf/README.md`dagi yo'riqnoma bo'yicha ishga tushiring. Skript
   endi Email/Parol kirish usulini ham avtomatik yoqadi.
2. **Qo'lda**: [console.firebase.google.com](https://console.firebase.google.com/project/oscartalim-sinf-80da0/authentication)
   → **Sign-in method → Email/Password → Enable → Save**.

Keyin foydalanuvchi brauzerida avval "mahalliy rejim"ga tushib qolgan
bo'lsa, qurilmadagi `localStorage`da `tugilgankun:forceLocal` kalitini
o'chirish (yoki sahifani "Clear site data" qilish) kerak bo'ladi — shundan
keyin sayt qayta bulutga ulanishga urinadi.

Xavfsizlik qoidalari `firestore.rules` (va `docs/sinf/README.md`dagi nusxasi)
ichida: `birthdays_shared` to'plamini ro'yxatdan o'tgan **har qanday**
foydalanuvchi o'qiy oladi (shu sabab hamma bir-birining tug'ilgan kunini
ko'radi), lekin yozuvni faqat uni qo'shgan kishi (`authUid`) tahrirlaydi
yoki o'chiradi. Shaxsiy kontakt ma'lumoti (`tugilgankun/{uid}`) esa hech
qachon ochiq emas — uni faqat egasi o'qiydi.

## Hozirgi cheklovlar (kamchiliklar — bilib turing)

- **Bildirishnoma faqat sahifa ochiq/oxirgi marta ochilgan brauzerda ishlaydi.**
  Bu — statik sayt, ya'ni sizsiz fonda ishlaydigan server yo'q. Har kuni
  sayt bir marta (yoki uni qurilmaga PWA sifatida o'rnatib, muntazam) ochib
  turilsa, o'sha kunning eslatmasi ko'rinadi/bildirishnoma chiqadi. Chinakam
  "fon rejimida" push xabar yuborish uchun kelajakda alohida server (masalan
  mavjud Telegram bot infratuzilmasi — `bot/bot.py`) ulanishi mumkin.
- **29-fevral**: kabisa bo'lmagan yilda keyingi bayram 1-mart sifatida
  hisoblanadi (brauzer sana arifmetikasining tabiiy natijasi).
- **Mahalliy rejimda** bitta brauzerda faqat bitta hisob saqlanadi (parol —
  faqat shu qurilmada tekshiriladi, haqiqiy server autentifikatsiyasi emas).

## Fayllar

```
docs/tugilgankun/
├── index.html            # butun dastur (HTML + CSS + JS)
├── sw.js                 # offline uchun service worker
├── manifest.webmanifest  # PWA manifesti (telefon ekraniga o'rnatish uchun)
├── icon.svg, icon-maskable.svg
└── README.md
```

## Sinash

```bash
python3 -m http.server 8000
# keyin: http://localhost:8000/docs/tugilgankun/
```

Nashr qilingandan keyin (GitHub Pages): `https://<foydalanuvchi>.github.io/OscarTalim/tugilgankun/`

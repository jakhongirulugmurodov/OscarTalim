# Premiere Pro / After Effects uchun sotiladigan plugin g'oyalari

O'zimiz yozib, pullik sotishimiz mumkin bo'lgan pluginlar ro'yxati.
Bozor: podkasterlar, YouTube montajchilar, prodakshn studiyalar.

## 1. AutoSync — multicam sinxronizatsiya ✅ (yadro tayyor)

Bir necha kamera + rekorder fayllarini audio orqali avtomatik sinxronlash.
PluralEyes ($299 edi) bozordan ketgan, o'rni bo'sh. Yadrosi shu repoda:
`autosync/autosync.py`. Qolgani — UXP panel o'rash va litsenziya tizimi.
**Narx taxmini:** $49–99 (bir martalik).

## 2. Silence Cutter — pauzalarni avtomatik kesish

Podcastdagi jimlik/pauzalarni topib, timeline'da avtomatik jump-cut qilib
beradi. Soatlab qo'l mehnatini 1 daqiqaga tushiradi. Texnik jihatdan
AutoSync'ga o'xshash (audio tahlil + XML/API orqali kesish).
**Narx taxmini:** $39–69.

## 3. Auto Camera Switcher — kim gapirsa, o'sha kamera

Multicam'da har bir spikerning mikrofon faolligiga qarab kamerani avtomatik
almashtirib beradi (podcast uchun juda mos — 3-4 kishi, har birida mikrofon).
AutoSync + Silence Cutter ustiga quriladi. **Narx taxmini:** $59–99.

## 4. Auto Captions Pro — mahalliy subtitr generatori

Whisper modeli bilan kompyuterda (oflayn) transkripsiya qilib, Premiere'ga
caption trek qilib beradi. O'zbek/rus/ingliz tillari — mahalliy bozorda katta
afzallik, chunki Premiere'ning o'z transkripsiyasi o'zbekchani yaxshi olmaydi.
**Narx taxmini:** $29–59 yoki oylik obuna.

## 5. Shorts Cutter — uzun videodan 9:16 kliplar

Uzun podcastdan qiziqarli qismlarni belgilab, avtomatik 9:16 (Reels/Shorts)
sequence'lar yasab beradi: kadr markazlash, subtitr, progress-bar.
**Narx taxmini:** $49 yoki obuna.

## 6. Filler Word Remover — "eee", "mmm" tozalagich

Transkripsiya asosida parazit so'zlarni topib, kesish variantlarini taklif
qiladi. Auto Captions bilan bitta paketda sotsa bo'ladi.

## 7. Podcast Loudness Kit — bir tugmali audio-master

Ovoz balandligini podcast standartiga (-16 LUFS) keltirish, ducking
(musiqa pasaytirish), shovqin tozalash — bitta panelda.

## 8. Brand Kit Inserter — intro/outro/lower-thirds avtomat

Studiyaning brend elementlarini (intro, outro, ism plashkalari) markerlar
bo'yicha avtomatik joylash. Studiyalarga litsenziya bilan sotiladi.

---

## Texnologiya tanlovi

| Yo'l | Nima uchun |
|---|---|
| **UXP plugin** (JS/HTML) | Premiere Pro 2026 standarti — yangi loyihalar shunda yozilsin |
| **Python/ffmpeg yadro** | Og'ir audio/video tahlil panelda emas, alohida protsessda |
| ExtendScript/CEP | Faqat eski versiyalar kerak bo'lsa (2026-sentabrgacha) |

## Qayerda sotiladi

- **Adobe Marketplace** (developer.adobe.com orqali) — rasmiy kanal
- **aescripts.com + aeplugins** — montajchilar eng ko'p oladigan joy
- **Gumroad / Lemon Squeezy** — o'z saytingiz orqali, komissiya kam
- Mahalliy bozor: Telegram-kanallar, montaj kurslari bilan hamkorlik

## Boshlash tartibi (tavsiya)

1. AutoSync'ni UXP panelga o'rash (yadro tayyor)
2. O'zimizning podcastlarda ishlatib, silliqlash
3. aescripts + Gumroad'da $49 dan sotuvga qo'yish
4. Tushgan fikrlar asosida №2 va №3 ni qo'shib, "Podcast Suite" paketi qilish

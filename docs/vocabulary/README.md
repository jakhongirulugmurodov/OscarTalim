# Vocabulary — ingliz tili so‘zlarini yodlash

Bitta HTML fayl (HTML + CSS + JS), PWA. Ma’lumotlar brauzerning
`localStorage` xotirasida (`vocabulary-app-v1` kaliti) saqlanadi — sahifa
yopilsa ham yo‘qolmaydi. Ro‘yxat bo‘limida JSON eksport/import bor.

## Bo‘limlar

| Bo‘lim | Holat |
|---|---|
| Bosh sahifa — kunlik maqsad, streak, XP/daraja, 7 kunlik grafik, badge’lar | ✅ |
| Vocabulary — flashcard, spaced repetition, progress | ✅ |
| Listening | tez orada |
| Reading | tez orada |
| Speaking | tez orada |
| Writing | tez orada |

## So‘z kiritish formati

Har qator — bitta so‘z, birikma yoki qisqa gap:

```
apple                                   ← tarjima va transkripsiya avtomatik
look forward to - intiqlik bilan kutmoq ← o‘z tarjimang
resilient | chidamli | /rɪˈzɪliənt/     ← hammasi qo‘lda
```

Avtomatik to‘ldirish: tarjima — Google Translate (`translate.googleapis.com`,
zaxira: MyMemory), transkripsiya — `api.dictionaryapi.dev` (6 so‘zgacha
birikmalar uchun har so‘z alohida). Internet bo‘lmasa, kartochka baribir
qo‘shiladi, tarjimani ✎ orqali qo‘lda yozish mumkin.

## Takrorlash mantig‘i (Leitner)

- Har so‘zning qutisi bor: 0…6. Intervallar: 0, 1, 2, 4, 8, 16, 32 kun.
- **Bilaman** → keyingi quti, so‘z o‘sha intervaldan keyin qaytadi.
- **Bilmayman** → 0-quti, so‘z shu sessiyaning o‘zida 2 kartadan keyin
  yana chiqadi (bir sessiyada ko‘pi bilan 3 marta).
- 3-qutiga yetgan so‘z **o‘zlashtirilgan** hisoblanadi (progress bar).
- Sessiya — 20 tagacha muddati kelgan karta. **Erkin mashq** muddati
  kelmagan so‘zlarning qutisini oshirmaydi.

Boshqaruv: bosish/Probel — aylantirish, → / o‘ngga surish — bilaman,
← / chapga surish — bilmayman.

## Ball

Bilaman: +10 XP (qayta urinishda +5, erkin mashqda +3), bilmayman: +1 XP.
Daraja: `floor(sqrt(XP/50)) + 1`. Streak — kamida bitta takrorlash qilingan
ketma-ket kunlar.

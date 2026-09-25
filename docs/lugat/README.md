# Lug'at — ingliz tili so'zlarini yodlash

Inglizcha so'zlarni **uzoq muddat** eslab qolish uchun dastur: takrorlash
tizimi, faol eslash, o'yinlar hamda yozish, gapirish va tinglash mashqlari.
Build bosqichi yo'q — oddiy HTML/CSS/JS, PWA, GitHub Pages'da ishlaydi.
Hamma ma'lumot brauzerning `localStorage` xotirasida saqlanadi.

## Fayllar

| Fayl | Nima bor |
|---|---|
| `index.html` | Qobiq: yon panel, pastki menyu, skriptlar |
| `style.css` | Dizayn: yorug'/qorong'i mavzu, kartalar, animatsiyalar |
| `data.js` | Namuna so'zlar (55 ta), suhbat mavzulari, savollar, yutuqlar |
| `core.js` | Holat, takrorlash tizimi (SRS), XP/seriya, ovoz, grammatika tekshiruvi, import |
| `app.js` | Yo'naltirish, mashq dvigateli va sahifalar |
| `games.js` | 8 ta o'yin |
| `ai.js` | AI Ustoz, Suhbat, Claude API chaqiruvi |

## Asosiy g'oya: tanishdan faol ishlatishgacha

Har bir so'z bosqichma-bosqich qiyinroq mashqqa o'tadi:

1. **Yangi** — so'z kartasi, keyin tarjimani tanlash (tanish).
2. **1-takrorlash** — gapdagi bo'sh joyga so'z tanlash, o'zbekchadan tanlash.
3. **2-takrorlash** — o'zbekchadan yozish, eshitib ma'nosini topish.
4. **3+ takrorlash** — bo'sh joyni yozish, gapdan so'zni eshitib topish,
   diktant, **o'z gapini tuzish** (faol ishlatish).

## Takrorlash tizimi

SM-2 asosida. Har mashqdan keyin foydalanuvchi baholaydi:

| Baho | Keyingi takrorlash |
|---|---|
| 😵 Unutdim | 10 daqiqadan keyin (shu mashg'ulotda ham qaytadi) |
| 😐 Qiyin | ertaga (yoki oldingi oraliq × 1.2) |
| 🙂 Yaxshi | 3 kun, keyin oraliq × «osonlik» koeffitsienti |
| 😎 Oson | 5 kun, keyin oraliq × koeffitsient × 1.3 |

- Ko'p unutilgan so'z (3+ marta) oralig'i qisqartiriladi va tez-tez chiqadi.
- Muddati kelmagan so'zni qo'shimcha mashq qilish jadvalni **surmaydi**
  (faqat unutilsa yoki qiyin bo'lsa qisqartiradi).
- O'yinlarda baho oxirida so'raladi — natijaga qarab taklif qilinadi.
- 21+ kunlik oraliq — «yodlangan».

## Ball va seriya

- XP har bir to'g'ri javob, baho, o'yin va suhbat uchun beriladi; daraja XP dan.
- **Seriya 🔥 kunlik maqsad to'liq bajarilgan kunlar bilan** davom etadi
  (yangi so'zlar, takrorlash, gapirish/tinglash daqiqalari, yozish mashqlari).
  Maqsadni Sozlamalardan o'zgartirish mumkin.
- Har kuni bitta kunlik sinov, haftalik XP maqsadi, 16 ta yutuq.

## Qiyinlik

Foydalanuvchi darajasini tanlaydi (🟢 Beginner / 🟡 Intermediate / 🔴 Advanced).
Yozish va tinglashda oxirgi 8 javob bo'yicha qiyinlik o'zi o'zgaradi:
85%+ bo'lsa oshadi, 50% dan past bo'lsa pasayadi.

## Gapirish

Brauzerning `SpeechRecognition` API'si (Chrome, Edge). Ball 0–100:
grammatika, lug'at (so'z ishlatildimi), tuzilish, talaffuz (tanish ishonchi yoki
namuna gap bilan moslik), ravonlik (so'z/soniya). Mikrofon bo'lmasa, javobni
yozib yuborish mumkin.

## AI Ustoz va Suhbat

- **Kalitsiz (oflayn):** qoidalarga asoslangan ustoz — so'zni tushuntiradi
  (lug'at + dictionaryapi.dev), gapni tekshiradi, misol, savol, mashq,
  tavsiya va xatolar tahlilini beradi. Suhbat mavzular bo'yicha tayyor
  savollar bilan boradi va har javobni tuzatadi.
- **Anthropic API kaliti bilan:** Sozlamalarda kalit kiritilsa, ustoz va
  suhbat Claude bilan ishlaydi (standart model `claude-opus-5`). Kalit faqat
  shu brauzerda saqlanadi va to'g'ridan-to'g'ri `api.anthropic.com` ga
  yuboriladi (`anthropic-dangerous-direct-browser-access`). Suhbat javobi
  JSON sxema (`output_config.format`) bilan olinadi: tuzatish, izoh, javob,
  yangi so'zlar.

Grammatika tekshiruvi (`core.js` → `GRAMMAR_RULES`) o'zbek o'quvchilarining
tipik xatolariga qaratilgan: `go to shopping`, `he go`, `I am agree`,
`didn't went`, `want go`, `a apple`, `I have 20 years`, o'tgan zamon va h.k.

## Import

Matnni joylash yoki CSV/TXT fayl: har qatorda `English | Uzbek`.
Ajratgich: `|`, Tab, `;`, ` - ` yoki vergul. Qo'shimcha ustunlar tartibi:
misol, so'z turkumi, talaffuz, kategoriya, daraja, izoh (yoki sarlavha
qatori bilan istalgan tartib). Takroriylar o'tkazib yuboriladi; bo'sh
talaffuz va misol internetdagi lug'atdan to'ldiriladi.

# AI Ustoz — uyga vazifani tekshirish

Statik PWA. Server yo'q: brauzer rasmni to'g'ridan-to'g'ri Gemini API'ga yuboradi,
natijalar `localStorage` da saqlanadi.

## Ishga tushirish

Ochish: `docs/ustoz/` (GitHub Pages'da `/ustoz/`).

1. **Sozlama** bo'limiga o'ting va Gemini API kalitini kiriting —
   [aistudio.google.com/apikey](https://aistudio.google.com/apikey) dan bepul olinadi.
2. Sinf va fanni yozing.
3. **Tekshirish**: o'quvchi ismi, dars nomi, so'ng daftarni suratga oling
   (1–6 sahifa) va "Tekshirish" tugmasini bosing.

Lokal sinov uchun oddiy server yetadi (fayl protokolida service worker ishlamaydi):

```bash
python3 -m http.server 8000 --directory docs
# http://localhost:8000/ustoz/
```

## Qanday ishlaydi

| Bosqich | Nima bo'ladi |
|---|---|
| 1 | Rasm brauzerda 1600px gacha kichraytiriladi, JPEG'ga o'tkaziladi |
| 2 | Rubrika + rasmlar Gemini'ga yuboriladi (`responseSchema` bilan, JSON qaytadi) |
| 3 | Har savol uchun: ball, xato turi, qadam, izoh, ishonch, rasmdagi joyi |
| 4 | Ishonch 0,85 dan past bo'lsa — javob **Ko'rik navbati**ga tushadi |
| 5 | O'qituvchi yakuniy ballni tasdiqlaydi (`tuzatilgan` maydoni) |
| 6 | Sinf xaritasi va ota-ona hisoboti shu ma'lumotlardan hisoblanadi |

Model baho qo'ymaydi — u o'qituvchining vaqtini qayerga sarflashini hal qiladi.

## Cheklovlar

- **API kalit brauzerda turadi.** Har kim o'z kalitini kiritadi; maktabning
  umumiy kaliti bu yerga qo'yilmaydi. Haqiqiy joriy etishda kalit serverda
  bo'lishi kerak.
- **Ma'lumot faqat shu qurilmada.** Boshqa qurilmaga o'tmaydi, sinxronlanmaydi.
  ZRU-547 bo'yicha O'zbekiston hududidagi saqlash — keyingi bosqich.
- **Davomat yo'q.** U bir nechta qurilma va server talab qiladi.
- `localStorage` to'lsa eng eski topshiriqlarning rasmlari o'chiriladi, ballar qoladi.

Batafsil: [spetsifikatsiya](../ai-ustoz/) · [ekran maketlari](../ai-ustoz/ekranlar/)

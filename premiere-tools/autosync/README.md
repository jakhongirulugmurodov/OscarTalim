# AutoSync — Podcast/Multicam avtomatik sinxronizatsiya

Bir necha kamera va tashqi audio-rekorder fayllarini **audio orqali** bir-biriga
moslab, Adobe Premiere Pro'ga import qilinadigan tayyor sequence yasab beradi.

Siz faqat fayllarni ko'rsatasiz — vosita qolganini o'zi qiladi:

1. Har bir fayldan audioni o'qiydi
2. Kross-korrelyatsiya (FFT) bilan fayllar orasidagi vaqt farqini topadi
3. Har bir faylni o'z trekiga, to'g'ri joyga qo'yilgan XML sequence yasaydi

Bu kompyuteringizda ishlaydi — internet ham, token ham kerak emas.

## Talablar

- Python 3.8+
- `numpy` — o'rnatish: `pip install numpy`
- `ffmpeg` va `ffprobe` — [ffmpeg.org](https://ffmpeg.org/download.html) dan
  yuklab, PATH ga qo'shing

## Foydalanish

```bash
python3 autosync.py cam1.mp4 cam2.mp4 cam3.mp4 recorder.wav -o synced.xml
```

So'ng Premiere Pro'da: **File > Import** → `synced.xml` ni tanlang.
Project panelida "AutoSync Sequence" paydo bo'ladi — ochsangiz, hamma kadr
sinxronlangan holda timeline'da turadi.

### Parametrlar

| Parametr | Tavsif | Standart |
|---|---|---|
| `-o, --output` | Natija XML fayl nomi | `synced.xml` |
| `--name` | Sequence nomi | `AutoSync Sequence` |
| `--minutes` | Tahlil uchun boshidan necha minut olinadi (0 = to'liq) | `20` |

### Maslahatlar

- Video fayllar bilan birga alohida diktofon/rekorder yozuvini (`.wav`) ham
  berish mumkin — u ham alohida audio-trekka sinxronlanadi.
- "Ishonch" (confidence) ustuni 15x dan past bo'lsa, natijani qo'lda tekshiring —
  bu audiolar bir-biriga o'xshamaganini bildiradi (masalan, kameralardan biri
  boshqa xonada yozilgan bo'lsa).
- Kameralar yozuvni 20 minutdan ko'proq farq bilan boshlagan bo'lsa,
  `--minutes 0` bilan to'liq tahlil qiling (sekinroq ishlaydi).

## Ishlash printsipi

Hamma professional sinxronlash vositalari (masalan, mashhur PluralEyes) xuddi
shu usulda ishlagan: har bir yozuvning audio to'lqinini tayanch yozuv bilan
solishtirib, eng katta mos kelish nuqtasini (kross-korrelyatsiya cho'qqisini)
topadi. Xona bir xil bo'lgani uchun hamma mikrofonlar bir xil tovushni —
turli sifatda — yozadi, shu o'xshashlik yetarli.

## Keyingi bosqich: UXP plugin

Bu CLI vosita — mantiqning yadrosi. Uni Premiere Pro ichida panel qilish uchun
[UXP plugin](https://developer.adobe.com/premiere-pro/uxp/) ga o'rash mumkin:
panel fayllarni tanlatadi, shu skriptni ishga tushiradi va natija XML'ni
avtomatik import qiladi. Sotiladigan mahsulot uchun `../PLUGIN_IDEAS.md` ga
qarang.

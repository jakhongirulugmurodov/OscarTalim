# O'zbekcha video transkripsiya vositasi

YouTube, Instagram havolasi yoki lokal video/audio fayldan **o'zbekcha matn
(caption)** chiqaradi — **timecode'lar bilan**, SRT / VTT / TXT formatlarda.
Gemini API asosida ishlaydi.

## Qanday ishlaydi

1. **Yuklab olish** — `yt-dlp` havoladan audioni oladi (lokal fayl bo'lsa, shu bosqich o'tkazib yuboriladi)
2. **Audio ajratish** — `ffmpeg` 16kHz mono mp3 qiladi
3. **Bo'laklash** — 20 daqiqadan uzun audio bo'laklarga bo'linadi (uzun audioda Gemini timecode'lari surilib ketishining oldini oladi)
4. **Transkripsiya** — Gemini har bir segmentga `start`/`end` vaqt bilan matn qaytaradi
5. **Tahrir o'tishi** — Gemini audioni qayta eshitib matndagi xatolarni tuzatadi (aniqlikni ~98% ga ko'taradigan asosiy bosqich; vaqtlar o'zgarmaydi)
6. **Natija** — SRT, VTT va/yoki TXT fayllar

## O'rnatish

```bash
# 1. Tizim dasturlari (Ubuntu/Debian)
sudo apt install ffmpeg

# 2. Python kutubxonalari
pip install -r requirements.txt

# 3. Gemini API kaliti — https://aistudio.google.com/apikey dan oling
export GEMINI_API_KEY="sizning-kalitingiz"
```

## Ishlatish

```bash
# YouTube videodan SRT + TXT
python transcriber.py "https://youtube.com/watch?v=..."

# Lokal fayldan, kirill yozuvida, natijalar alohida papkaga
python transcriber.py video.mp4 --yozuv kirill -o natijalar/

# Instagram (login talab qilinadi — brauzerdan cookies eksport qiling)
python transcriber.py "https://instagram.com/reel/..." --cookies cookies.txt

# Faqat VTT, tahrir o'tishisiz (tezroq, arzonroq, lekin aniqlik pastroq)
python transcriber.py video.mp4 --format vtt --tahrirsiz
```

### Parametrlar

| Parametr | Vazifasi | Standart |
|----------|----------|----------|
| `--model` | Gemini modeli | `gemini-2.5-pro` |
| `--yozuv` | `lotin` yoki `kirill` | `lotin` |
| `--format` | `srt,vtt,txt` (vergul bilan) | `srt,txt` |
| `-o` | Natija papkasi | joriy papka |
| `--nom` | Natija fayllar nomi | manba nomidan |
| `--bolak` | Bo'lak uzunligi (soniya) | `1200` |
| `--tahrirsiz` | Tahrir o'tishini o'chirish | tahrir yoqilgan |
| `--cookies` | yt-dlp cookies fayli | — |

## Aniqlikni oshirish bo'yicha maslahatlar

- **Tahrir o'tishini o'chirmang** — ikkinchi o'tish eng ko'p xatoni tuzatadi.
- Fonda musiqa kuchli bo'lsa, aniqlik tushadi — imkon bo'lsa toza ovozli manba ishlating.
- Maxsus atamalar ko'p bo'lsa, `transcriber.py` dagi `TRANSKRIPSIYA_PROMPT` ga
  atamalar ro'yxatini qo'shing.
- Narx nazorati uchun `--model gemini-2.5-flash` ishlatish mumkin (arzonroq,
  aniqlik biroz pastroq).

# Podcast Suite — Premiere Pro plugini

Podcast montaji uchun 5 modulli plugin. Qurilish holati:

| # | Modul | Holat |
|---|---|---|
| 1 | **Sync** — multicam sinxronizatsiya | ✅ Motor + panel tayyor (shu bosqich) |
| 2 | Cut — pauzalarni kesish | dizayn tasdiqlangan, navbatda |
| 3 | Switch — kamera almashtirish | dizayn tasdiqlangan |
| 4 | Captions — oflayn subtitr | dizayn tasdiqlangan |
| 5 | Shorts — 9:16 kliplar | dizayn tasdiqlangan |

## Tuzilishi

```
suite/
├── engine/          Motor — lokal server (Python, og'ir ishlar shu yerda)
│   └── server.py    http://127.0.0.1:8765 da ishlaydi
└── panel/           UXP panel — Premiere Pro ichidagi interfeys
    ├── manifest.json
    ├── index.html
    └── main.js
```

Panel o'zi hech narsa hisoblamaydi: fayl yo'llarini motorga yuboradi,
motor sinxronlab XML yasaydi, panel uni loyihaga import qiladi.
Hammasi kompyuterda, oflayn — internetga hech narsa ketmaydi.

## O'rnatish (birinchi marta)

**1. Motor talablari:**
```bash
pip install numpy
# ffmpeg: https://ffmpeg.org/download.html — PATH ga qo'shilgan bo'lsin
```

**2. Motorni ishga tushirish:**
```bash
cd premiere-tools/suite/engine
python3 server.py
# "Podcast Suite motori ishga tushdi" chiqsa — tayyor
```

**3. Panelni Premiere'ga ulash (dev-rejim):**
1. [UXP Developer Tools](https://developer.adobe.com/photoshop/uxp/2022/guides/devtool/) ni o'rnating (Creative Cloud ilovasidan ham topiladi)
2. UXP Developer Tools > **Add Plugin** > `suite/panel/manifest.json` ni tanlang
3. Premiere Pro ochiq holda plugin qatorida **Load** ni bosing
4. Premiere'da panel ochiladi: **Window > UXP Plugins > Podcast Suite**

## Ishlatish

1. Panelda motor indikatori **yashil** bo'lishini kuting
2. «Fayllarni tanlash» — kamera videolari + rekorder audiosi (2+)
3. **Sinxronlash** — har fayl yonida siljish va ishonch chiqadi
4. **Premiere'ga import** — sinxronlangan sequence loyihaga tushadi

Panelsiz, terminaldan ham ishlatish mumkin (motor talab qilinmaydi):
```bash
python3 premiere-tools/autosync/autosync.py cam1.mp4 cam2.mp4 -o synced.xml
```

## Sinov holati

- Motor + `/sync` oqimi sun'iy 4-fayl testida tekshirilgan: siljishlar
  millisekund aniqlikda (5.000s / 2.500s / 1.200s), XML to'g'ri
- Panelning Premiere ichidagi qismi (fayl tanlash, import API) haqiqiy
  Premiere Pro'da sinash kerak — bu keyingi qadam
- `project.importFiles` API mos kelmasa, panel qo'lda import yo'lini
  ko'rsatadi (File > Import) — ish to'xtab qolmaydi

## Keyingi bosqich

Sync haqiqiy podcastda sinovdan o'tgach — **2-modul: Cut** (pauzalarni
avtomatik kesish). Motorga `/cut` endpointi va panelga ikkinchi tab qo'shiladi.

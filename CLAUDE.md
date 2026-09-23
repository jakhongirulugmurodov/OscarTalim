# OscarTalim

## Til qoidalari

**«yaratish» so'zi faqat Alloh uchun ishlatiladi.** Boshqa hamma joyda —
kod, foydalanuvchi matni, izohlar, commit xabarlari, suhbat — uning
o'rniga **«yasash»** ishlatiladi.

| ✗ ishlatilmaydi | ✓ ishlatiladi |
|---|---|
| sinf yaratish | sinf yasash |
| yaratildi | yasaldi |
| yaratuvchi | yasagan |
| viktorina yarataman | viktorina yasayman |

Ingliz tilidagi kod identifikatorlari (`createdBy`, `create`, `createClass`)
o'zgarmaydi — qoida o'zbekcha matnga tegishli.

## Loyiha

- `docs/sinf/` — AI kursi (13 dars) uchun sinf paneli. Bitta HTML fayl:
  HTML + CSS + JS + kurs mazmuni. PWA, GitHub Pages'da.
- `docs/anjuman/` — anjuman mashg'uloti dasturi.
- `docs/index.html` — transkripsiya sahifasi.
- `bot/bot.py` — Telegram bot (faqat standart kutubxona).
- `kitob-bot/` — «Sehrli Javon» kitob do'koni boti: katalog, aksiya, sovg'a,
  promokod (10–50%), buyurtma, baholash. Sinov: `python3 kitob-bot/test_bot.py`.
- `.github/workflows/` — bot, Firebase sozlash, Pages shoxchasini sinxronlash.

Batafsil: `docs/sinf/README.md`.

## Muhim

- GitHub Pages **`claude/yangi-papka-ochish-zroxni`** shoxchasidan chiqadi.
  `main` ga push bo'lganda `pages-sync.yml` uni avtomatik yangilaydi.
- Firebase qoidalari `docs/sinf/README.md` ichidagi ```js blokda saqlanadi —
  sozlash skripti o'sha yerdan oladi. Qoidani o'zgartirsang, README'ni
  o'zgartir va "Firebase sozlash" workflow'ini `faqat_qoidalar` rejimida
  ishga tushir.

# ⚡ Elektr balansi — Mac'da ishlaydigan server

Payme'ga kirib hisob raqamni kiritish o'rniga balans to'g'ridan-to'g'ri
**HET shaxsiy kabinetidan** (cabinet.het.uz) olinadi. Payme ham balansni shu
yerdan oladi.

## Qanday ishlaydi

- `tekshir.py` haqiqiy brauzerni (Playwright + Chrome) yashirin ochadi va
  kabinetga kiradi. Balansni kabinet qaytargan JSON'dan oladi, topilmasa
  sahifa matnidan oladi.
- Parol saqlanmaydi. Bir marta qo'lda kirasiz, sessiya `~/.elektr/profil`
  ichida qoladi.
- `server.py` balansni http://127.0.0.1:8765 manzilida ko'rsatadi. Sahifada
  «Hozir tekshirish» tugmasi bor. Server ishga tushganda va keyin har 6 soatda
  o'zi tekshiradi, natijani macOS bildirishnomasida chiqaradi.
- `launchd` Mac yoqilib, tizimga kirganingizda serverni o'zi ishga tushiradi.
  Server yiqilsa, qayta ko'taradi.

## O'rnatish (bir marta)

1. Kabinet uchun login va parolni oling: **2100** raqamiga katta **P** harfini
   SMS qilib yuboring. Yoki cabinet.het.uz'da hisob raqam bilan ro'yxatdan
   o'ting.
2. Terminalda quyidagini ishga tushiring:
   ```bash
   cd OscarTalim/elektr && ./ornatish.sh
   ```
   Brauzer oynasi ochiladi. Kabinetga kiring va balans ko'ringach, terminalda
   Enter bosing.

Telefondan (o'sha Wi-Fi'da) ochish uchun:
```bash
ELEKTR_HOST=0.0.0.0 ELEKTR_KALIT=istalgan-maxfiy-soz ./ornatish.sh --kirishsiz
```
Keyin telefonda `http://<mac-ip>:8765/?k=istalgan-maxfiy-soz` manzilini oching
va «Bosh ekranga qo'shish» qiling.

O'chirish: `./ornatish.sh --ochir`

## Holatlar

| Sahifada | Ma'nosi | Nima qilish kerak |
|---|---|---|
| summa | balans olindi | — |
| «Sessiya tugagan» | kabinet qayta kirishni so'rayapti | `.venv/bin/python tekshir.py kirish` |
| «summa topilmadi» | sahifa ochildi, lekin raqam tanilmadi | «Tafsilotlar» va `~/.elektr/oxirgi_javoblar.json` faylini ko'ring, `KALITLAR` ro'yxatini to'g'rilang |
| «ulanib bo'lmadi» | internet yo'q yoki kabinet ishlamayapti | keyinroq tekshiring |

Ishora (minus = qarz yoki ortiqcha to'lov) kabinet qanday qaytarsa,
shundayligicha ko'rsatiladi.

## Fayllar

- `tekshir.py` — brauzer orqali tekshiruv
- `server.py` — sahifa, API va jadval (standart kutubxona)
- `sahifa.html` — interfeys
- `ornatish.sh` — venv, kirish va launchd

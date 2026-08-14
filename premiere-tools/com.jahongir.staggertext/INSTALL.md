# Stagger Text — o'rnatish

Tanlangan kliplarga pastdan suzib chiqish + fade animatsiyasi qo'yadigan
CEP panel.

## 1. CSInterface.js ni yuklab olish (bir martalik, majburiy)

`client/js/CSInterface.js` hozir placeholder — uni Adobe'ning haqiqiy
fayli bilan almashtiring:

1. Oching: <https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_11.x/CSInterface.js>
2. **Raw** tugmasini bosib faylni saqlang
3. `client/js/CSInterface.js` o'rniga qo'ying

## 2. Papkani joyiga qo'yish

`com.jahongir.staggertext` papkasini butunligicha shu yerga ko'chiring:

```
~/Library/Application Support/Adobe/CEP/extensions/
```

Terminal orqali:

```bash
mkdir -p ~/Library/Application\ Support/Adobe/CEP/extensions
cp -R com.jahongir.staggertext ~/Library/Application\ Support/Adobe/CEP/extensions/
```

## 3. PlayerDebugMode ni yoqish

Panel imzolanmagan, shuning uchun Adobe'ga «imzosizlarni ham yukla»
deyish kerak (bir martalik):

```bash
defaults write com.adobe.CSXS.11 PlayerDebugMode 1
killall cfprefsd
```

(`killall cfprefsd` — sozlama darhol kuchga kirishi uchun; bo'lmasa
tizimga qayta kirish kerak bo'ladi.)

## 4. Ochish

1. Premiere'ni **yopib, qayta oching**
2. Menyu: **Window > Extensions > Stagger Text**

## Ishlatish

1. Timeline'da klip(lar)ni belgilang (matn/grafika kliplari)
2. Panelda davomiylik va masofani sozlang
3. **Qo'llash** ni bosing

Har klipga: Position pastdan markazga suzib chiqadi, Opacity 0 dan
100 ga — harakatdan oldinroq (65% nuqtada) tugaydi, keyframe'lar bezier.

## Ishlamasa

| Belgi | Sabab / yechim |
|---|---|
| Menyuda «Stagger Text» yo'q | Papka noto'g'ri joyda yoki PlayerDebugMode yoqilmagan. 2–3-qadamlarni tekshirib, Premiere'ni qayta oching |
| Panel ochildi, «CSInterface.js topilmadi» | 1-qadam bajarilmagan |
| «Host skript yuklanmadi» | Premiere'ni qayta oching; takrorlansa `host/index.jsx` o'zgartirilgan bo'lishi mumkin |
| «Position/Opacity topilmadi» | Tanlangan klip video/grafika emas (masalan, audio) |

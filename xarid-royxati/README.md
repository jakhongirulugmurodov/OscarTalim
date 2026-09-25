# Xarid ro'yxati

Uyga kerakli mahsulotlarni kundalik kiritish va xarajatlarni kuzatish uchun oddiy veb-ilova.

## Imkoniyatlar

- Har kuni sotib olingan mahsulotlarni (nomi, kategoriyasi, miqdori, narxi) kiritish
- Xarajatlarni **bugun / bu hafta / bu oy / hammasi** bo'yicha ko'rish
- Umumiy xarajat, xaridlar soni, turli mahsulotlar soni va kunlik o'rtacha xarajat
- Kategoriya bo'yicha xarajatlar taqsimoti (diagramma)
- Eng ko'p sotib olinadigan mahsulotlar reytingi (necha marta olingani, jami miqdori, jami sarflangan summasi)
- Ma'lumotlarni JSON fayl sifatida zaxiralash va tiklash

## Ma'lumotlar qayerda saqlanadi?

Barcha ma'lumotlar faqat shu brauzerning **localStorage**'ida saqlanadi — serverga yuborilmaydi. Boshqa qurilma yoki brauzerga o'tkazish uchun "Zaxira nusxa (JSON) yuklab olish" va "JSON dan tiklash" tugmalaridan foydalaning.

## Ishga tushirish

Bu build-siz, sof HTML/CSS/JS ilova. `index.html` faylini brauzerda oching, yoki lokal serverda ishga tushiring:

```bash
python3 -m http.server 8000
```

So'ng brauzerda `http://localhost:8000` manzilini oching.

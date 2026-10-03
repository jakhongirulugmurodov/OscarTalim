#!/usr/bin/env python3
"""TestCorrect — Gemini bilan javobni tekshirish va test tuzish.

google-genai kutubxonasi ishlatilmaydi: bot.py GitHub Actions'da pip
install qilmasdan, standart kutubxona bilan ishlashi kerak (bot/bot.py
sarlavhasiga qarang). Shuning uchun Gemini REST API'ga to'g'ridan-to'g'ri
murojaat qilinadi.

Muhit o'zgaruvchisi:
    GEMINI_API_KEY   https://aistudio.google.com/apikey dan olinadi
    GEMINI_MODEL     ixtiyoriy, standart: gemini-2.5-flash
"""

import base64
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
URL = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL

TEKSHIRISH_PROMPT = """\
Sen barcha fanlar (matematika, fizika, kimyo, biologiya, ona tili, tarix, \
ingliz tili va boshqalar) bo'yicha tajribali o'qituvchisan. Foydalanuvchi \
senga bitta test savoli va o'zining javobini yuboradi — matn sifatida, \
rasm sifatida (masalan, daftar varag'i yoki test blankasi surati) yoki \
ikkalasi birga.

Vazifang:
1. Avval savol va foydalanuvchi javobini aniq o'qib chiq (rasm bo'lsa,\
   undagi yozuvni diqqat bilan o'qi).
2. Agar savol yoki javob umuman aniqlanmasa, buni ayt va savol/javobni \
   yanada aniqroq yuborishni so'ra — hech narsani o'zingdan o'ylab topma.
3. Javob TO'G'RImi yoki NOTO'G'RImi — aniqla.
4. Agar TO'G'RI bo'lsa: qisqa tabriklab, nega to'g'ri ekanini 1-2 gapda \
   tushuntir.
5. Agar NOTO'G'RI bo'lsa:
   - xato aynan qaysi qadamda/joyda qilinganini aniq ko'rsat,
   - to'g'ri yechimni boshidan oxirigacha, bosqichma-bosqich, tushunarli \
     qilib yoz,
   - oxirida to'g'ri yakuniy javobni alohida qatorda ajratib yoz.

Muhim qoidalar:
- Har doim foydalanuvchi yozgan/gapirgan TIL VA YOZUVDA javob ber (masalan \
  o'zbekcha lotin yozuvida yozilgan bo'lsa — lotinda, kirillda bo'lsa \
  kirillda, ruscha yoki inglizcha bo'lsa o'sha tilda).
- Telegram xabari uchun qisqa va aniq yoz, ortiqcha cho'zma.
- LaTeX yoki maxsus formula belgilaridan foydalanma — oddiy matn va \
  odatdagi matematik belgilar (+, -, ×, ÷, =, ^, √) bilan yoz.
"""

YARATISH_PROMPT = """\
Sen barcha fanlar bo'yicha test tuzuvchi mutaxassissan. Foydalanuvchi senga \
fan/mavzu nomini (va xohlasa savollar sonini yoki qiyinlik darajasini) \
yozadi. Shu mavzu bo'yicha sifatli, xatosiz test savollari tuz — har bir \
savolga to'g'ri javobni ham qo'shib.

Format quyidagicha bo'lsin:
1) Savol matni
   Javob: to'g'ri javob (qisqa)
2) ...

Agar savollar soni ko'rsatilmagan bo'lsa — 5 ta savol tuz. Savol va \
javoblarni foydalanuvchi yozgan til va yozuvda tuz. Telegram xabari uchun \
qisqa va tartibli yoz, LaTeX ishlatma.
"""


def _chaqir(parts):
    if not API_KEY:
        print("GEMINI_API_KEY o'rnatilmagan.", file=sys.stderr)
        return None

    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
    }).encode()
    req = Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    })
    try:
        with urlopen(req, timeout=90) as r:
            javob = json.load(r)
    except HTTPError as e:
        try:
            xato = json.load(e).get("error", {}).get("message", str(e))
        except ValueError:
            xato = str(e)
        print("gemini xatosi:", xato, file=sys.stderr)
        return None
    except URLError as e:
        print("gemini tarmoq xatosi:", e, file=sys.stderr)
        return None

    try:
        qismlar = javob["candidates"][0]["content"]["parts"]
        matn = "".join(p.get("text", "") for p in qismlar).strip()
        return matn or None
    except (KeyError, IndexError, TypeError):
        sabab = (javob.get("candidates") or [{}])[0].get("finishReason")
        print("gemini bo'sh javob qaytardi, sabab:", sabab, file=sys.stderr)
        return None


def javobni_tekshir(savol_matn=None, rasm=None, rasm_mime="image/jpeg"):
    """Savol+javobni tahlil qilib, to'g'ri/noto'g'riligini va xatoni tushuntiradi."""
    parts = [{"text": TEKSHIRISH_PROMPT}]
    if rasm:
        parts.append({"inline_data": {
            "mime_type": rasm_mime,
            "data": base64.b64encode(rasm).decode(),
        }})
    if savol_matn:
        parts.append({"text": "Foydalanuvchi yuborgan matn:\n" + savol_matn})
    return _chaqir(parts)


def test_yarat(sorov_matn):
    """Berilgan mavzu bo'yicha savol+javoblardan iborat test tuzadi."""
    parts = [{"text": YARATISH_PROMPT}, {"text": "So'rov:\n" + sorov_matn}]
    return _chaqir(parts)

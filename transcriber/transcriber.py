#!/usr/bin/env python3
"""O'zbekcha video/audio transkripsiya vositasi (Gemini asosida).

YouTube, Instagram havolasi yoki lokal video/audio fayldan o'zbekcha
matn (caption) chiqaradi — timecode'lar bilan, SRT/VTT/TXT formatlarda.

Ishlatish:
    export GEMINI_API_KEY="..."
    python transcriber.py "https://youtube.com/watch?v=..." --format srt,txt
    python transcriber.py video.mp4 --yozuv kirill -o natijalar/

Bosqichlar:
    1. yt-dlp bilan videoni yuklab olish (yoki lokal faylni olish)
    2. ffmpeg bilan audioni ajratish (16kHz mono mp3)
    3. Uzun audioni bo'laklarga bo'lish (timecode aniqligi uchun)
    4. Gemini'dan segmentlangan transkript olish (start/end soniyalarda)
    5. Tahrir o'tishi: Gemini audio bilan birga matnni qayta tekshiradi
    6. SRT / VTT / TXT fayllarga yozish
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    sys.exit("google-genai o'rnatilmagan. O'rnatish: pip install -r requirements.txt")

STANDART_MODEL = "gemini-2.5-pro"

SEGMENT_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "start": {"type": "NUMBER", "description": "Segment boshlanishi, soniyalarda"},
            "end": {"type": "NUMBER", "description": "Segment tugashi, soniyalarda"},
            "text": {"type": "STRING", "description": "Segment matni"},
        },
        "required": ["start", "end", "text"],
    },
}

TRANSKRIPSIYA_PROMPT = """\
Sen o'zbek tili bo'yicha professional transkripsiya mutaxassisisan.
Berilgan audiodagi barcha nutqni to'liq va so'zma-so'z matnga o'tkaz.

Qoidalar:
1. Matnni {yozuv} yozuvida yoz.
2. Lotin yozuvida "oʻ" va "gʻ" harflarini toʻgʻri (ʻ) belgisi bilan yoz.
3. Har bir segment 3-8 soniya bo'lsin — caption uchun qulay uzunlikda.
4. "start" va "end" — audio boshidan hisoblangan soniyalar, kasr son bo'lishi mumkin.
5. Punktuatsiyani (nuqta, vergul, so'roq) to'g'ri qo'y.
6. Ruscha yoki inglizcha aytilgan so'zlarni aynan aytilganidek yoz.
7. Musiqa, pauza va shovqinlarni yozma — faqat nutqni yoz.
8. Hech bir gapni tashlab ketma va o'zingdan hech narsa qo'shma.

Audio davomiyligi taxminan {davomiylik:.0f} soniya — timecode'lar shu oraliqda bo'lsin."""

TAHRIR_PROMPT = """\
Quyida shu audioning avtomatik transkripsiyasi JSON ko'rinishida berilgan.
Audioni diqqat bilan eshitib, matnlardagi xatolarni tuzat:
- noto'g'ri eshitilgan yoki tushib qolgan so'zlar,
- imlo va apostrof (oʻ, gʻ) xatolari,
- punktuatsiya.

"start" va "end" vaqtlarini O'ZGARTIRMA. Segmentlar soni va tartibini
saqlagan holda xuddi shu JSON formatda to'liq ro'yxatni qaytar.

Transkripsiya:
{segmentlar}"""


def xato(msg: str):
    sys.exit(f"XATO: {msg}")


def buyruq_bormi(nom: str):
    if shutil.which(nom) is None:
        xato(f"'{nom}' topilmadi. O'rnatish kerak (README'ga qarang).")


def yuklab_olish(url: str, workdir: Path, cookies: str | None) -> Path:
    """YouTube/Instagram havolasidan eng yaxshi audioni yuklab oladi."""
    buyruq_bormi("yt-dlp")
    chiqish = workdir / "manba.%(ext)s"
    cmd = ["yt-dlp", "-f", "bestaudio/best", "-o", str(chiqish), "--no-playlist", url]
    if cookies:
        cmd += ["--cookies", cookies]
    subprocess.run(cmd, check=True)
    fayllar = list(workdir.glob("manba.*"))
    if not fayllar:
        xato("yt-dlp hech narsa yuklab olmadi.")
    return fayllar[0]


def audio_ajratish(manba: Path, workdir: Path) -> Path:
    """Videodan 16kHz mono mp3 ajratadi — ASR uchun standart format."""
    buyruq_bormi("ffmpeg")
    audio = workdir / "audio.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(manba), "-vn", "-ac", "1", "-ar", "16000",
         "-b:a", "48k", str(audio)],
        check=True, capture_output=True,
    )
    return audio


def davomiylik(audio: Path) -> float:
    buyruq_bormi("ffprobe")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        check=True, capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def bolaklash(audio: Path, workdir: Path, bolak_soniya: int) -> list[Path]:
    """Uzun audioda Gemini timecode'lari suriladi — shuning uchun bo'laklaymiz."""
    if davomiylik(audio) <= bolak_soniya * 1.1:
        return [audio]
    qolip = workdir / "bolak_%03d.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(audio), "-f", "segment",
         "-segment_time", str(bolak_soniya), "-c", "copy", str(qolip)],
        check=True, capture_output=True,
    )
    return sorted(workdir.glob("bolak_*.mp3"))


def faylni_yuklash(client: genai.Client, audio: Path):
    """Audioni Gemini Files API'ga yuklab, tayyor bo'lishini kutadi."""
    f = client.files.upload(file=str(audio))
    while f.state and f.state.name == "PROCESSING":
        time.sleep(2)
        f = client.files.get(name=f.name)
    if f.state and f.state.name == "FAILED":
        xato(f"Gemini faylni qabul qilmadi: {audio.name}")
    return f


def json_ajratish(matn: str) -> list[dict]:
    matn = matn.strip()
    matn = re.sub(r"^```(?:json)?\s*|\s*```$", "", matn)
    segmentlar = json.loads(matn)
    if not isinstance(segmentlar, list):
        raise ValueError("JSON ro'yxat emas")
    return segmentlar


def gemini_sorov(client: genai.Client, model: str, contents, urinishlar: int = 3) -> list[dict]:
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SEGMENT_SCHEMA,
        temperature=0.1,
    )
    oxirgi_xato = None
    for i in range(urinishlar):
        try:
            javob = client.models.generate_content(model=model, contents=contents, config=config)
            return json_ajratish(javob.text)
        except Exception as e:  # noqa: BLE001 — API/parse xatolarida qayta urinamiz
            oxirgi_xato = e
            if i < urinishlar - 1:
                kutish = 2 ** (i + 1)
                print(f"  Xato ({e}), {kutish}s dan keyin qayta urinish...")
                time.sleep(kutish)
    xato(f"Gemini so'rovi {urinishlar} urinishda ham muvaffaqiyatsiz: {oxirgi_xato}")


def transkript_qilish(client, model: str, audio: Path, yozuv: str, tahrir: bool) -> list[dict]:
    dav = davomiylik(audio)
    fayl = faylni_yuklash(client, audio)
    yozuv_nomi = "lotin (o'zbek alifbosi)" if yozuv == "lotin" else "kirill (ўзбек алифбоси)"
    prompt = TRANSKRIPSIYA_PROMPT.format(yozuv=yozuv_nomi, davomiylik=dav)
    segmentlar = gemini_sorov(client, model, [fayl, prompt])

    if tahrir and segmentlar:
        print("  Tahrir o'tishi (audio bilan qayta tekshirish)...")
        tahrir_prompt = TAHRIR_PROMPT.format(
            segmentlar=json.dumps(segmentlar, ensure_ascii=False)
        )
        tahrirlangan = gemini_sorov(client, model, [fayl, tahrir_prompt])
        if len(tahrirlangan) == len(segmentlar):
            # Vaqtlarni asl transkripsiyadan saqlaymiz — tahrir faqat matnni tuzatadi
            for asl, yangi in zip(segmentlar, tahrirlangan):
                asl["text"] = yangi["text"]
        else:
            print("  Ogohlantirish: tahrir segmentlar sonini o'zgartirdi, asl matn qoldirildi.")

    client.files.delete(name=fayl.name)
    return segmentlar


def vaqt_srt(soniya: float) -> str:
    ms = int(round(soniya * 1000))
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt_yozish(segmentlar: list[dict], fayl: Path):
    qatorlar = []
    for i, seg in enumerate(segmentlar, 1):
        qatorlar.append(
            f"{i}\n{vaqt_srt(seg['start'])} --> {vaqt_srt(seg['end'])}\n{seg['text'].strip()}\n"
        )
    fayl.write_text("\n".join(qatorlar), encoding="utf-8")


def vtt_yozish(segmentlar: list[dict], fayl: Path):
    qatorlar = ["WEBVTT\n"]
    for seg in segmentlar:
        boshi = vaqt_srt(seg["start"]).replace(",", ".")
        oxiri = vaqt_srt(seg["end"]).replace(",", ".")
        qatorlar.append(f"{boshi} --> {oxiri}\n{seg['text'].strip()}\n")
    fayl.write_text("\n".join(qatorlar), encoding="utf-8")


def txt_yozish(segmentlar: list[dict], fayl: Path):
    fayl.write_text(
        " ".join(seg["text"].strip() for seg in segmentlar) + "\n", encoding="utf-8"
    )


def main():
    p = argparse.ArgumentParser(
        description="O'zbekcha video transkripsiya (Gemini, timecode'lar bilan)"
    )
    p.add_argument("manba", help="YouTube/Instagram havolasi yoki lokal video/audio fayl")
    p.add_argument("--model", default=STANDART_MODEL,
                   help=f"Gemini modeli (standart: {STANDART_MODEL})")
    p.add_argument("--yozuv", choices=["lotin", "kirill"], default="lotin",
                   help="Chiqish yozuvi (standart: lotin)")
    p.add_argument("--format", default="srt,txt",
                   help="Chiqish formatlari, vergul bilan: srt,vtt,txt (standart: srt,txt)")
    p.add_argument("-o", "--chiqish", default=".", help="Natija fayllar papkasi")
    p.add_argument("--nom", help="Natija fayllar nomi (standart: manba nomidan)")
    p.add_argument("--bolak", type=int, default=1200,
                   help="Uzun audio bo'lagi, soniyalarda (standart: 1200 = 20 daqiqa)")
    p.add_argument("--tahrirsiz", action="store_true",
                   help="Tahrir o'tishini o'chirish (tezroq, lekin aniqlik pastroq)")
    p.add_argument("--cookies", help="yt-dlp uchun cookies fayli (Instagram uchun kerak bo'ladi)")
    args = p.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        xato("GEMINI_API_KEY muhit o'zgaruvchisi o'rnatilmagan.\n"
             "Kalitni https://aistudio.google.com/apikey dan oling.")
    client = genai.Client(api_key=api_key)

    formatlar = [f.strip() for f in args.format.split(",")]
    nomalum = set(formatlar) - {"srt", "vtt", "txt"}
    if nomalum:
        xato(f"Noma'lum format: {', '.join(nomalum)}")

    chiqish_papka = Path(args.chiqish)
    chiqish_papka.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)

        if os.path.exists(args.manba):
            manba = Path(args.manba)
            nom = args.nom or manba.stem
        else:
            print("1/4 Video yuklab olinmoqda...")
            manba = yuklab_olish(args.manba, workdir, args.cookies)
            nom = args.nom or "transkript"

        print("2/4 Audio ajratilmoqda...")
        audio = audio_ajratish(manba, workdir)
        dav = davomiylik(audio)
        print(f"    Davomiylik: {dav / 60:.1f} daqiqa")

        bolaklar = bolaklash(audio, workdir, args.bolak)
        if len(bolaklar) > 1:
            print(f"    Audio {len(bolaklar)} bo'lakka bo'lindi (timecode aniqligi uchun)")

        print("3/4 Gemini transkripsiya qilmoqda...")
        segmentlar: list[dict] = []
        siljish = 0.0
        for i, bolak in enumerate(bolaklar, 1):
            if len(bolaklar) > 1:
                print(f"  Bo'lak {i}/{len(bolaklar)}...")
            for seg in transkript_qilish(client, args.model, bolak, args.yozuv,
                                         tahrir=not args.tahrirsiz):
                seg["start"] += siljish
                seg["end"] += siljish
                segmentlar.append(seg)
            siljish += davomiylik(bolak)

    if not segmentlar:
        xato("Audioda nutq topilmadi.")

    print("4/4 Fayllar yozilmoqda...")
    yozuvchilar = {"srt": srt_yozish, "vtt": vtt_yozish, "txt": txt_yozish}
    for fmt in formatlar:
        fayl = chiqish_papka / f"{nom}.{fmt}"
        yozuvchilar[fmt](segmentlar, fayl)
        print(f"    {fayl}")

    print(f"\nTayyor: {len(segmentlar)} segment, {dav / 60:.1f} daqiqa audio.")


if __name__ == "__main__":
    main()

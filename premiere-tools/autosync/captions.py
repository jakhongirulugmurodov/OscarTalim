#!/usr/bin/env python3
"""Captions — nutqni matnga aylantiradi (oflayn, whisper.cpp orqali).

Foydalanish (terminaldan):
    python3 captions.py yozuv.mp4 -l uz --model medium -o transkript.json

Natija: so'z darajasidagi vaqtlar bilan transkript. Aynan shu — subtitrdan
tashqari Intro, Shorts, boblar va arxiv qidiruvi uchun ham poydevor bo'ladi,
shuning uchun har so'zning boshlanish/tugash vaqti saqlanadi.

Model bir marta yuklab olinadi (~1.5 GB), keyin internetsiz ishlaydi.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autosync import FFMPEG, FFMPEG_YOQ, ffprobe

# Model nomi -> (ggml fayl, taxminiy hajm)
MODELS = {
    "tez":    ("ggml-small.bin", "0.5 GB"),
    "balans": ("ggml-medium.bin", "1.5 GB"),
    "aniq":   ("ggml-large-v3-turbo.bin", "1.6 GB"),
    "eng-aniq": ("ggml-large-v3.bin", "3.1 GB"),
}
MODEL_BASE = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"

# Subtitr qatorlari uchun
MAX_LINE_CHARS = 42
MAX_LINE_SEC = 6.0
LINE_GAP_SEC = 0.8      # shundan uzun jimlik — yangi qator


def models_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "suite", "modellar")
    return os.path.abspath(path)


_WHISPER_OK = {}


def whisper_runs(path):
    """Fayl bor bo'lishi yetmaydi — ishga tushishini ham tekshiramiz.

    Manbadan noto'g'ri qurilgan nusxa kutubxonalarini topa olmay yiqiladi;
    bu holat faqat transkripsiya o'rtasida bilinardi. Natija saqlanadi —
    har chaqiruvda jarayon ochmaymiz.
    """
    if path in _WHISPER_OK:
        return _WHISPER_OK[path]
    try:
        out = subprocess.run([path, "--help"], capture_output=True, timeout=30)
        text = (out.stdout + out.stderr).decode("utf-8", "replace").lower()
        ok = out.returncode == 0 or "usage:" in text
    except (OSError, subprocess.SubprocessError):
        ok = False
    _WHISPER_OK[path] = ok
    return ok


def find_whisper():
    """whisper.cpp ijro fayli: paket ichida, PATH da yoki Homebrew joyida."""
    here = os.path.dirname(os.path.abspath(__file__))
    names = ("whisper-cli", "whisper-cpp", "main")
    for name in names:
        found = shutil.which(name)
        if found and whisper_runs(found):
            return found
    candidates = []
    for name in names:
        candidates += [
            os.path.join(here, "..", "suite", "bin", name),
            os.path.join(here, "..", "bin", name),
            "/opt/homebrew/bin/" + name,
            "/usr/local/bin/" + name,
        ]
        candidates += glob.glob(os.path.join(
            os.path.expanduser("~"), "*", "whisper.cpp", "build", "bin", name))
    for path in candidates:
        path = os.path.abspath(path)
        if os.path.isfile(path) and os.access(path, os.X_OK) and whisper_runs(path):
            return path
    return None


WHISPER_YOQ = (
    "whisper.cpp topilmadi. O'rnatish: terminalda «brew install whisper-cpp» "
    "(Homebrew bo'lmasa — brew.sh dan o'rnating). Shundan keyin motorni qayta yoqing."
)


def have_model(model_key):
    """Model allaqachon yuklanganmi (panel oldindan ogohlantirishi uchun)."""
    entry = MODELS.get(model_key)
    if not entry:
        return False
    path = os.path.join(models_dir(), entry[0])
    return os.path.isfile(path) and os.path.getsize(path) > 1_000_000


def remote_size(url):
    """Yuklanadigan faylning hajmi (bayt) — foizni ko'rsatish uchun."""
    try:
        out = subprocess.run(["curl", "-sIL", url], capture_output=True,
                             text=True, timeout=20)
        for line in reversed(out.stdout.splitlines()):
            if line.lower().startswith("content-length:"):
                return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return 0


def ensure_model(model_key, log=print, progress=None):
    """Model faylini tekshiradi, yo'q bo'lsa yuklab oladi."""
    say = progress or (lambda **k: None)
    if model_key not in MODELS:
        raise RuntimeError(f"Noma'lum model: {model_key}")
    fname, size = MODELS[model_key]
    path = os.path.join(models_dir(), fname)
    if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
        say(stage="Model tayyorlanmoqda", percent=100, detail="model joyida")
        return path

    os.makedirs(models_dir(), exist_ok=True)
    log(f"Model yuklanmoqda ({size}, bir martalik): {fname}")
    log("  Bu bir marta bo'ladi — keyingi safar darhol boshlanadi.")
    tmp = path + ".yuklanmoqda"
    cmd = ["curl", "-L", "--fail", "--silent", "--show-error",
           "-o", tmp, MODEL_BASE + fname]

    # Yuklanish sekin bo'lsa foydalanuvchi «osilib qoldi» deb o'ylamasin —
    # panelga necha MB tushganini uzatib turamiz.
    total = remote_size(MODEL_BASE + fname)
    stop = threading.Event()
    # Bosqich nomi ro'yxatdagidek qoladi, yuklanish esa tafsilotda ko'rinadi —
    # panelda qadamlar ro'yxati bilan sarlavha bir-biriga mos tursin.
    say(stage="Model tayyorlanmoqda", percent=0 if total else None,
        detail=f"yuklanmoqda: 0 MB / {size}")

    def watch():
        spoke = 0
        while not stop.wait(1):
            try:
                mb = os.path.getsize(tmp) / 1_000_000
            except OSError:
                continue
            say(percent=(mb * 1_000_000 / total * 100) if total else None,
                detail=f"yuklanmoqda: {mb:.0f} MB / {size}")
            spoke += 1
            if spoke % 10 == 0:      # log'da har 10 soniyada bir qator yetadi
                log(f"  yuklandi: {mb:.0f} MB / {size}")

    threading.Thread(target=watch, daemon=True).start()
    try:
        out = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        stop.set()
    if out.returncode != 0 or not os.path.isfile(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"Modelni yuklab bo'lmadi: {out.stderr.strip()[:200]}")
    os.replace(tmp, path)
    log("Model tayyor ✓")
    return path


def to_wav16k(src, dest, start=None, duration=None, progress=None):
    """whisper.cpp 16 kHz mono WAV talab qiladi.

    Uzun rekorder yozuvida bu ham bir necha daqiqa oladi, shuning uchun
    ffmpeg'ning o'z hisobotini o'qiymiz. Diqqat: `out_time_ms` nomiga
    qaramay MIKROsoniyada keladi — foiz `out_time_us` dan olinadi.
    """
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)
    say = progress or (lambda **k: None)
    cmd = [FFMPEG, "-v", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-map", "a:0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-progress", "pipe:1", "-nostats", dest]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
    for line in proc.stdout:
        if line.startswith("out_time_us=") and duration:
            try:
                done = int(line.split("=", 1)[1]) / 1e6
            except ValueError:
                continue
            say(percent=max(0.0, min(99.0, done / duration * 100)))
    err = proc.stderr.read()
    if proc.wait() != 0:
        raise RuntimeError(f"Audio ajratib bo'lmadi: {err.strip()[:200]}")
    say(percent=100)
    return dest


def run_whisper(wav, model_path, language, log=print, threads=None,
                progress=None):
    """whisper.cpp ni ishga tushirib, so'z darajasidagi natijani qaytaradi."""
    binary = find_whisper()
    if not binary:
        raise RuntimeError(WHISPER_YOQ)

    out_base = os.path.splitext(wav)[0] + "_wsp"
    cmd = [binary, "-m", model_path, "-f", wav,
           "-oj", "-ml", "1",              # -ml 1 → har so'z alohida bo'lak
           "-pp",                          # foizni chiqarib tursin
           "--output-file", out_base]
    if language and language != "avto":
        cmd += ["-l", language]
    if threads:
        cmd += ["-t", str(threads)]

    # Uzun yozuvda whisper 10-20 daqiqa ishlashi mumkin. Natijani oxirida
    # kutib o'tirmay, foizni o'sha zahoti uzatamiz — panel jim turmasin.
    say = progress or (lambda **k: None)
    started = time.time()
    audio_sec = 0.0
    # Model xotiraga yuklanguncha (bir necha soniya) hech qanday belgi
    # chiqmaydi — panel «to'xtab qoldi» deb ko'rinmasin uchun aytib qo'yamiz.
    say(stage="Matnga aylantirilmoqda", percent=0,
        detail="model xotiraga yuklanmoqda…")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    tail, shown = [], -10
    for line in proc.stdout:
        tail.append(line.rstrip())
        del tail[:-25]
        # Birinchi foizgacha 3 soniyacha jimlik bo'ladi (model yuklanadi,
        # mel-spektr hisoblanadi). Shu qatordan nima ustida ishlayotganini
        # bilib, panelda ko'rsatib turamiz.
        got = re.search(r"processing .*\(([\d]+) samples, ([\d.]+) sec\)", line)
        if got:
            audio_sec = float(got.group(2))
            say(detail=f"{audio_sec / 60:.0f} daqiqalik ovoz o'qildi, "
                       "tahlil boshlanmoqda…")
        m = re.search(r"progress\s*=\s*(\d+)\s*%", line)
        if m:
            pct = int(m.group(1))
            # Tafsilotda foiz emas, ovozning qayerigacha yetgani turadi —
            # foiz baribir chiziqda ko'rinib turibdi.
            if audio_sec:
                done = audio_sec * pct / 100
                say(percent=pct,
                    detail=f"{done / 60:.0f}:{int(done % 60):02d} / "
                           f"{audio_sec / 60:.0f}:{int(audio_sec % 60):02d} ovoz")
            else:
                say(percent=pct, detail=f"{time.time() - started:.0f}s")
            if pct // 10 * 10 > shown:
                shown = pct // 10 * 10
                log(f"  {shown}% · {time.time() - started:.0f}s")
    if proc.wait() != 0:
        raise RuntimeError("whisper xatosi: " + "\n".join(tail)[-300:])

    js = out_base + ".json"
    if not os.path.isfile(js):
        raise RuntimeError("whisper natija fayli chiqmadi")
    with open(js, encoding="utf-8") as fh:
        data = json.load(fh)
    os.remove(js)

    words = []
    for item in data.get("transcription", []):
        text = (item.get("text") or "").strip()
        if not text:
            continue
        off = item.get("offsets", {})
        words.append({
            "text": text,
            "start": off.get("from", 0) / 1000.0,
            "end": off.get("to", 0) / 1000.0,
        })
    log(f"  {len(words)} so'z · {time.time() - started:.0f}s")
    return words


def join_words(words):
    """So'zlarni matnga qo'shadi: tinish belgilari oldidan bo'shliq qo'ymaydi.

    whisper -ml 1 rejimida tinish belgilari alohida «so'z» bo'lib chiqadi,
    shuning uchun oddiy join «gap .» ko'rinishidagi matn beradi.
    """
    out = ""
    for w in words:
        t = w["text"] if isinstance(w, dict) else w
        if out and not (t[:1] in ",.!?;:…»)" or out[-1:] in "(«"):
            out += " "
        out += t
    return out.strip()


def group_lines(words, max_chars=MAX_LINE_CHARS, max_sec=MAX_LINE_SEC,
                gap=LINE_GAP_SEC):
    """So'zlarni subtitr qatorlariga yig'adi.

    Yangi qator boshlanadi: uzun jimlikdan keyin, gap tugagach, yoki qator
    juda uzayib ketganda.
    """
    lines, cur = [], None
    for w in words:
        if cur is None:
            cur = {"start": w["start"], "end": w["end"], "words": [w]}
            continue
        too_long = (w["end"] - cur["start"]) > max_sec
        too_wide = len(join_words(cur["words"] + [w])) > max_chars
        long_gap = (w["start"] - cur["end"]) > gap
        ends_sentence = cur["words"][-1]["text"].endswith((".", "!", "?", "…"))
        if too_long or too_wide or long_gap or ends_sentence:
            lines.append(cur)
            cur = {"start": w["start"], "end": w["end"], "words": [w]}
        else:
            cur["words"].append(w)
            cur["end"] = w["end"]
    if cur:
        lines.append(cur)

    for ln in lines:
        ln["text"] = join_words(ln["words"])
    return [ln for ln in lines if ln["text"]]


def clip_spans(spans, seconds):
    """Sinov uchun: montaj vaqtining birinchi `seconds` qismini qoldiradi."""
    out = []
    for sp in sorted(spans, key=lambda s: s["start"]):
        if sp["start"] >= seconds:
            break
        keep = min(sp["out"] - sp["in"], seconds - sp["start"])
        if keep > 0:
            out.append({"start": sp["start"], "in": sp["in"],
                        "out": sp["in"] + keep})
    return out


def remap_words(words, spans):
    """Xom fayl vaqtini montaj (sequence) vaqtiga ko'chiradi.

    Tayyor sequence'da xom yozuvning ba'zi joylari kesib tashlangan bo'ladi.
    Subtitr xom fayl vaqti bilan chiqsa, montajga qo'yilganda siljib ketadi —
    shuning uchun har so'zni o'zi turgan bo'lakning siljishi bilan ko'chiramiz,
    kesilgan joyga tushganlarini esa tashlab yuboramiz.

    So'z qaysi bo'lakka tegishli ekani o'rtasi bo'yicha aniqlanadi: shunda
    chegaraga tushgan so'z ikki marta chiqmaydi.
    """
    out = []
    for sp in sorted(spans, key=lambda s: s["start"]):
        shift = sp["start"] - sp["in"]
        for w in words:
            mid = (w["start"] + w["end"]) / 2 if w["end"] > w["start"] else w["start"]
            if sp["in"] <= mid < sp["out"]:
                out.append({
                    "text": w["text"],
                    "start": max(w["start"], sp["in"]) + shift,
                    "end": min(w["end"], sp["out"]) + shift,
                })
    out.sort(key=lambda w: w["start"])
    return out


def attach_speakers(lines, speaker_at):
    """Har qatorga spiker nomini qo'yadi (Switch tahlilidan kelgan funksiya)."""
    if not speaker_at:
        return
    for ln in lines:
        mid = (ln["start"] + ln["end"]) / 2
        ln["speaker"] = speaker_at(mid)


def srt_time(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(lines):
    out = []
    for i, ln in enumerate(lines, start=1):
        who = ln.get("speaker")
        text = (f"[{who}] " if who else "") + ln["text"]
        out.append(f"{i}\n{srt_time(ln['start'])} --> {srt_time(ln['end'])}\n{text}\n")
    return "\n".join(out)


def archive_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "suite", "transkriptlar"))


def save_transcript(data, name, log=print):
    """Transkriptni arxivga saqlaydi — keyin hamma sonlar bo'ylab qidiriladi."""
    os.makedirs(archive_dir(), exist_ok=True)
    safe = "".join(c if c.isalnum() or c in " -_." else "_" for c in name)[:60]
    path = os.path.join(archive_dir(),
                        f"{safe}_{time.strftime('%Y-%m-%d_%H-%M')}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    log(f"Arxivga saqlandi: {os.path.basename(path)}")
    return path


def search_archive(query, limit=50):
    """Barcha saqlangan transkriptlarda qidirish."""
    query = (query or "").strip().lower()
    if not query:
        return []
    hits = []
    for path in sorted(glob.glob(os.path.join(archive_dir(), "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        for ln in data.get("lines", []):
            if query in ln.get("text", "").lower():
                hits.append({
                    "file": os.path.basename(path),
                    "title": data.get("title") or os.path.basename(path),
                    "start": ln["start"],
                    "text": ln["text"],
                    "speaker": ln.get("speaker"),
                })
                if len(hits) >= limit:
                    return hits
    return hits


def run_captions(audio_file, model="balans", language="uz", output=None,
                 sample_seconds=None, title=None, speaker_at=None,
                 spans=None, fallback=None, log=print, progress=None):
    """To'liq oqim: audio -> so'zlar -> qatorlar -> SRT + arxiv.

    `spans` berilsa (ochiq sequence'dan olingan bo'laklar:
    [{"start": montajdagi joyi, "in": xom fayldagi boshi, "out": oxiri}]),
    subtitr vaqtlari montajga moslanadi va kesilgan joylar tushib qoladi.
    """
    say = progress or (lambda **k: None)
    say(stage="Ovoz ajratilmoqda", percent=None, detail="fayl tekshirilmoqda")
    info = ffprobe(audio_file)
    if not info["has_audio"]:
        raise RuntimeError(f"{info['name']} da audio yo'q")

    spans = [s for s in (spans or []) if s.get("out", 0) > s.get("in", 0)]
    if spans and sample_seconds:
        spans = clip_spans(spans, sample_seconds)
        if not spans:
            raise RuntimeError("Bu fayl sequence boshida ishlatilmagan — "
                               "sinov uchun boshqa ovoz manbasini tanlang")

    model_path = ensure_model(model, log, progress=progress)
    if spans:
        # Xom faylning faqat montajda ishlatilgan oralig'ini eshitamiz —
        # uzun rekorder yozuvining qolgani bekorga vaqt olmasin.
        window_start = min(s["in"] for s in spans)
        window_len = max(s["out"] for s in spans) - window_start
        dur = sum(s["out"] - s["in"] for s in spans)
    else:
        window_start, window_len = None, sample_seconds
        dur = info["duration"] if not sample_seconds else min(sample_seconds,
                                                              info["duration"])
    log(f"Transkripsiya: {info['name']} · {dur:.0f}s · model «{model}»"
        + (f" · sequence ({len(spans)} bo'lak)" if spans else "")
        + (" · SINOV" if sample_seconds else ""))

    tmp_wav = os.path.join(models_dir(), "_ish.wav")
    say(stage="Ovoz ajratilmoqda", percent=None,
        detail=f"{dur:.0f} soniyalik ovoz tayyorlanmoqda")
    to_wav16k(audio_file, tmp_wav, start=window_start, duration=window_len,
              progress=progress)
    try:
        words = run_whisper(tmp_wav, model_path, language, log,
                            progress=progress)
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)

    if spans:
        for w in words:                      # oyna boshidan xom fayl vaqtiga
            w["start"] += window_start
            w["end"] += window_start
        before = len(words)
        words = remap_words(words, spans)
        if before != len(words):
            log(f"  kesilgan joylardagi {before - len(words)} so'z chiqarildi")

    say(stage="Subtitr yig'ilmoqda", percent=None,
        detail=f"{len(words)} so'z qatorlarga bo'linmoqda")
    lines = group_lines(words)
    attach_speakers(lines, speaker_at)
    log(f"{len(lines)} qator subtitr tayyor")

    data = {
        "title": title or os.path.splitext(info["name"])[0],
        "source": info["path"],
        "language": language,
        "model": model,
        "duration": round(dur, 2),
        "sample": bool(sample_seconds),
        "from_sequence": bool(spans),
        "lines": [{k: v for k, v in ln.items() if k != "words"} for ln in lines],
        "words": words,
    }

    result = {"lines": data["lines"], "word_count": len(words),
              "line_count": len(lines), "sample": bool(sample_seconds),
              "from_sequence": bool(spans),
              "preview": " ".join(ln["text"] for ln in lines[:6])[:400]}

    if not sample_seconds:
        # Sinov natijasi arxivga kirmasin — faqat to'liq transkript saqlanadi
        result["archive"] = save_transcript(data, data["title"], log)
        if output:
            srt_path = os.path.splitext(output)[0] + ".srt"
            try:
                with open(srt_path, "w", encoding="utf-8") as fh:
                    fh.write(to_srt(lines))
                result["srt"] = srt_path
                log(f"SRT: {srt_path}")
            except OSError as e:
                if fallback:
                    os.makedirs(fallback, exist_ok=True)
                    alt = os.path.join(fallback, os.path.basename(srt_path))
                    with open(alt, "w", encoding="utf-8") as fh:
                        fh.write(to_srt(lines))
                    result["srt"] = alt
                    log(f"OGOHLANTIRISH: SRT zaxira papkaga saqlandi ({e.strerror})")
    return result


def main():
    ap = argparse.ArgumentParser(description="Oflayn transkripsiya (whisper.cpp).")
    ap.add_argument("audio")
    ap.add_argument("-l", "--language", default="uz")
    ap.add_argument("--model", default="balans", choices=list(MODELS))
    ap.add_argument("-o", "--output", default="transkript.srt")
    ap.add_argument("--sample", type=float, default=None,
                    help="faqat shuncha soniyani sinash")
    args = ap.parse_args()
    try:
        r = run_captions(args.audio, model=args.model, language=args.language,
                         output=args.output, sample_seconds=args.sample)
    except RuntimeError as e:
        sys.exit(str(e))
    print(f"\n{r['line_count']} qator, {r['word_count']} so'z")
    print(r["preview"])


if __name__ == "__main__":
    main()

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
import shutil
import subprocess
import sys
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


def find_whisper():
    """whisper.cpp ijro fayli: paket ichida, PATH da yoki Homebrew joyida."""
    here = os.path.dirname(os.path.abspath(__file__))
    names = ("whisper-cli", "whisper-cpp", "main")
    for name in names:
        found = shutil.which(name)
        if found:
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
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


WHISPER_YOQ = (
    "whisper.cpp topilmadi. O'rnatish: terminalda «brew install whisper-cpp» "
    "(Homebrew bo'lmasa — brew.sh dan o'rnating). Shundan keyin motorni qayta yoqing."
)


def ensure_model(model_key, log=print):
    """Model faylini tekshiradi, yo'q bo'lsa yuklab oladi."""
    if model_key not in MODELS:
        raise RuntimeError(f"Noma'lum model: {model_key}")
    fname, size = MODELS[model_key]
    path = os.path.join(models_dir(), fname)
    if os.path.isfile(path) and os.path.getsize(path) > 1_000_000:
        return path

    os.makedirs(models_dir(), exist_ok=True)
    log(f"Model yuklanmoqda ({size}, bir martalik): {fname}")
    tmp = path + ".yuklanmoqda"
    cmd = ["curl", "-L", "--fail", "--silent", "--show-error",
           "-o", tmp, MODEL_BASE + fname]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0 or not os.path.isfile(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(f"Modelni yuklab bo'lmadi: {out.stderr.strip()[:200]}")
    os.replace(tmp, path)
    log("Model tayyor ✓")
    return path


def to_wav16k(src, dest, start=None, duration=None):
    """whisper.cpp 16 kHz mono WAV talab qiladi."""
    if not FFMPEG:
        raise RuntimeError(FFMPEG_YOQ)
    cmd = [FFMPEG, "-v", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", src]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-map", "a:0", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dest]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"Audio ajratib bo'lmadi: {out.stderr.strip()[:200]}")
    return dest


def run_whisper(wav, model_path, language, log=print, threads=None):
    """whisper.cpp ni ishga tushirib, so'z darajasidagi natijani qaytaradi."""
    binary = find_whisper()
    if not binary:
        raise RuntimeError(WHISPER_YOQ)

    out_base = os.path.splitext(wav)[0] + "_wsp"
    cmd = [binary, "-m", model_path, "-f", wav,
           "-oj", "-ml", "1",              # -ml 1 → har so'z alohida bo'lak
           "--output-file", out_base]
    if language and language != "avto":
        cmd += ["-l", language]
    if threads:
        cmd += ["-t", str(threads)]

    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("whisper xatosi: " + (proc.stderr or "")[-300:])

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
                 fallback=None, log=print):
    """To'liq oqim: audio -> so'zlar -> qatorlar -> SRT + arxiv."""
    info = ffprobe(audio_file)
    if not info["has_audio"]:
        raise RuntimeError(f"{info['name']} da audio yo'q")

    model_path = ensure_model(model, log)
    dur = info["duration"] if not sample_seconds else min(sample_seconds,
                                                          info["duration"])
    log(f"Transkripsiya: {info['name']} · {dur:.0f}s · model «{model}»"
        + (" · SINOV" if sample_seconds else ""))

    tmp_wav = os.path.join(models_dir(), "_ish.wav")
    to_wav16k(audio_file, tmp_wav, duration=sample_seconds)
    try:
        words = run_whisper(tmp_wav, model_path, language, log)
    finally:
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)

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
        "lines": [{k: v for k, v in ln.items() if k != "words"} for ln in lines],
        "words": words,
    }

    result = {"lines": data["lines"], "word_count": len(words),
              "line_count": len(lines), "sample": bool(sample_seconds),
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

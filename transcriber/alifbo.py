"""Yangi o'zbek alifbosi (2026) — amaldagi lotin yozuvidan o'girish.

2026-yil 21-oktabrda imzolangan qonun: Oʻ → Ö, Gʻ → Ğ, Sh → Ş, Ch → Ç
(28 harf va tutuq belgisi). Gemini amaldagi lotinni yaxshi biladi — u shunday
yozadi, keyin shu yerda bir xil qoida bilan o'giriladi. Xorijiy so'z va nomlar
(YouTube, meetingʼga, Facebook) o'zgarmaydi.

Veb ilovadagi (docs/index.html, yangiMatn/eskiMatn) qoidalarning aynan o'zi.
"""

import re
import unicodedata

TUTUQ = "ʼ"  # tutuq belgisi (U+02BC)
APOS = "'ʻʼ‘’`´"
YANGI_HARF = {"O": "Ö", "o": "ö", "G": "Ğ", "g": "ğ", "S": "Ş", "s": "ş", "C": "Ç", "c": "ç"}
ESKI_HARF = {"Ö": "Oʻ", "ö": "oʻ", "Ğ": "Gʻ", "ğ": "gʻ", "ş": "sh", "ç": "ch"}

_HARF = r"[^\W\d_]"
SOZ_RE = re.compile(rf"(?:{_HARF}|[{APOS}])+")
_XORIJIY = re.compile(r"c(?!h)|w|th|ph|ck|ee|oo|ou|ea|ie|^chr", re.I)
_QATIY = re.compile(r"([OoGg])[ʻ‘]")
_YUMSHOQ = re.compile(rf"([OoGg])['ʻ‘’`´]")
_S_H = re.compile(r"^(is|as|mus)(h(?:oq|ob|af))", re.I)
_SH_CH = re.compile(r"([SsCc])[Hh]")
_APOS_ICHIDA = re.compile(rf"({_HARF})[{APOS}](?={_HARF})")


def xorijiymi(soz: str) -> bool:
    """O'zbek imlosida bo'lmaydigan harf/birikma yoki so'z ichida bosh harf."""
    return bool(_XORIJIY.search(soz)) or any(a.islower() and b.isupper() for a, b in zip(soz, soz[1:]))


def yangi_matn(matn: str, qatiy: bool = True) -> str:
    """Bitta matnni yangi alifboga o'giradi.

    qatiy=True — oʻ/gʻ faqat ʻ (‘) bilan yozilgan deb qaraladi (Gemini shunday
    yozadi); unda «blog'ga» dagi apostrof harf emas, tutuq belgisi.
    """
    harf = _QATIY if qatiy else _YUMSHOQ

    def ogir(m):
        soz = m.group(0)
        if xorijiymi(soz):
            return soz
        soz = harf.sub(lambda h: YANGI_HARF[h.group(1)], soz)
        # s va h alohida tovush bo'lgan so'zlar tutuqsiz yozilgan bo'lsa ham ş bo'lmasin (Isʼhoq, asʼhob)
        soz = _S_H.sub(r"\1" + TUTUQ + r"\2", soz)
        soz = _SH_CH.sub(lambda h: YANGI_HARF[h.group(1)], soz)
        return _APOS_ICHIDA.sub(r"\1" + TUTUQ, soz)

    return SOZ_RE.sub(ogir, unicodedata.normalize("NFC", matn))


def eski_matn(matn: str) -> str:
    """Teskari: yangi alifbodan amaldagi lotinga."""
    def ogir(m):
        soz = m.group(0)
        katta = len(soz) > 1 and soz == soz.upper()
        return re.sub(r"[ÖöĞğŞşÇç]", lambda h: ESKI_HARF.get(h.group(0)) or (
            {"Ş": "SH", "Ç": "CH"} if katta else {"Ş": "Sh", "Ç": "Ch"})[h.group(0)], soz)

    return SOZ_RE.sub(ogir, unicodedata.normalize("NFC", matn))


def segmentlarni_yangila(segmentlar: list[dict]) -> list[dict]:
    """Segmentlar matnini yangi alifboga o'giradi (qat'iy/yumshoq rejim matnga qarab)."""
    m = " ".join(s.get("text", "") for s in segmentlar)
    a, b = len(re.findall(r"[OoGg][ʻ‘]", m)), len(re.findall(r"[OoGg]['’`´]", m))
    qatiy = a > 0 and b <= a * 0.2
    return [{**s, "text": yangi_matn(s.get("text", ""), qatiy)} for s in segmentlar]

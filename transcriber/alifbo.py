"""Yangi o'zbek alifbosi (2026) — amaldagi lotin yozuvidan o'girish.

2026-yil 21-oktabrda imzolangan qonun (OʻRQ-1184, 2027-yil 22-apreldan kuchga
kiradi): Oʻ → Ö, Gʻ → Ğ, Sh → Ş, Ch → Ç (28 harf va tutuq belgisi), ng o'zgarmaydi.
Gemini amaldagi lotinni yaxshi biladi — u shunday yozadi, keyin shu yerda bir xil
qoida bilan o'giriladi. Xorijiy so'z va nomlar (YouTube, meetingʼga, Facebook),
havola va emaillar o'zgarmaydi.

Veb ilovadagi (docs/index.html: yangiMatn, eskiMatn) qoidalarning aynan o'zi.
"""

import re
import unicodedata

TUTUQ = "ʼ"  # tutuq belgisi (U+02BC)
APS = "'ʻʼ‘’`´"
YANGI_HARF = {"O": "Ö", "o": "ö", "G": "Ğ", "g": "ğ", "S": "Ş", "s": "ş", "C": "Ç", "c": "ç"}
ESKI_HARF = {"Ö": "Oʻ", "ö": "oʻ", "Ğ": "Gʻ", "ğ": "gʻ", "ş": "sh", "ç": "ch"}

_HARF = r"[^\W\d_]"
SOZ_RE = re.compile(rf"(?:{_HARF}|[{APS}])+")
# Havola, email, @nik, #teg va sayt nomlari o'girilmaydi
KORUV_RE = re.compile(
    r"(?:https?://|www\.)\S+|[A-Za-z0-9_.+-]+@[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+|(?<!\w)[@#][\w.]+"
    r"|(?<!\w)[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\.(?:uz|ru|com|org|net|me|io|asia|info|edu|gov|tv|app|ai)"
    r"(?![A-Za-z0-9_])\S*", re.I)
XORIJIY_HARF = re.compile("[àáâãäåæèéêëìíîïñòóôõøùúûüýÿıłßœÀÁÂÃÄÅÆÈÉÊËÌÍÎÏÑÒÓÔÕØÙÚÛÜÝŸİŁŒ]")
UZ_QISQA = re.compile(rf"^(?:O[{APS}]z|Tosh|Qo[{APS}]q|Farg[{APS}]|Sam|Bux|Nam|Xor|Nav|Jiz|Qash|Ter|And)[A-ZÖĞŞÇ]"
                      r"|^(?:MChJ|AQSh|JCh|YaTT|XDP)$")
_KUCHLI = re.compile(r"c(?!h)|w|th|ph|ck|^chr", re.I)
_KUCHSIZ = re.compile(r"ee|oo|ou|ea|ie", re.I)
_UZ_QOSHIMCHA = re.compile(r"lash|shunos|chi", re.I)
_YAKKA = re.compile(rf"^(?:sh|ch|[og][{APS}])$", re.I)
_O = re.compile(rf"([Oo])[{APS}](?={_HARF})")
_G_QATIY = re.compile(r"([Gg])[ʻ‘]")
_G_YUMSHOQ = re.compile(rf"(?<!in)([Gg])[{APS}]", re.I)
_S_H = re.compile(r"^(is|as|mus)(h(?:oq|ob|af))", re.I)
_SH_CH = re.compile(r"([SsCc])[Hh]")
_APOS_ICHIDA = re.compile(rf"({_HARF})[{APS}](?={_HARF})")


def xorijiymi(soz: str) -> bool:
    """O'zbek imlosida bo'lmaydigan harf/birikma yoki so'z ichida bosh harf."""
    if UZ_QISQA.search(soz):
        return False
    if _KUCHLI.search(soz) or XORIJIY_HARF.search(soz) or any(
            a.islower() and b.isupper() for a, b in zip(soz, soz[1:])):
        return True
    return bool(_KUCHSIZ.search(soz)) and not _UZ_QOSHIMCHA.search(soz)


def _himoyala(matn: str, f) -> str:
    out, i = [], 0
    for m in KORUV_RE.finditer(matn):
        out += [f(matn[i:m.start()]), m.group(0)]
        i = m.end()
    out.append(f(matn[i:]))
    return "".join(out)


_O_ODDIY = re.compile(rf"[Oo]['ʼ’`´](?={_HARF})")


def _soz_yangi(soz: str, qatiy: bool, holat: dict) -> str:
    # Qo'shtirnoq so'zga kirmaydi: boshidagisi va (qo'shtirnoq ochilgan bo'lsa) oxiridagi yopuvchisi
    b = re.match(rf"^[{APS}]*", soz).group(0)
    oz, ox = soz[len(b):], ""
    if b:
        holat["ochiq"] = True
    if holat["ochiq"] and oz and oz[-1] in APS:
        oz, ox = oz[:-1], oz[-1]
        holat["ochiq"] = False
    # Shu so'zning o'zida oʻ oddiy apostrof bilan yozilgan bo'lsa — gʻ ham shunday (bo’lg’usi)
    if _O_ODDIY.search(oz):
        qatiy = False
    if not oz or xorijiymi(oz) or _YAKKA.match(oz):
        return soz
    oz = _O.sub(lambda h: YANGI_HARF[h.group(1)], oz)
    oz = (_G_QATIY if qatiy else _G_YUMSHOQ).sub(lambda h: YANGI_HARF[h.group(1)], oz)
    oz = _S_H.sub(r"\1" + TUTUQ + r"\2", oz)
    oz = _SH_CH.sub(lambda h: YANGI_HARF[h.group(1)], oz)
    oz = _APOS_ICHIDA.sub(r"\1" + TUTUQ, oz)
    return b + oz + ox


def yangi_matn(matn: str, qatiy: bool = True) -> str:
    """Bitta matnni yangi alifboga o'giradi.

    qatiy=True — gʻ ʻ (‘) bilan yozilgan deb qaraladi (Gemini shunday yozadi);
    unda «blog'ga» dagi boshqa apostrof harf emas, tutuq belgisi.
    """
    holat = {"ochiq": False}
    return _himoyala(unicodedata.normalize("NFC", matn),
                     lambda t: SOZ_RE.sub(lambda m: _soz_yangi(m.group(0), qatiy, holat), t))


def _kattami(s) -> bool:
    return bool(s) and len(s) > 1 and s == s.upper() and s != s.lower()


def eski_matn(matn: str) -> str:
    """Teskari: yangi alifbodan amaldagi lotinga."""
    def bolak(t):
        sozlar = list(SOZ_RE.finditer(t))
        out, i = [], 0
        for k, m in enumerate(sozlar):
            soz = m.group(0)
            if len(soz) > 1:
                katta = _kattami(soz)
            else:  # bitta harf (Ş. Mirziyoyev) — qo'shni so'zga qarab
                katta = (k + 1 < len(sozlar) and _kattami(sozlar[k + 1].group(0))) or \
                        (k > 0 and _kattami(sozlar[k - 1].group(0)))
            if not XORIJIY_HARF.search(soz):
                soz = re.sub(r"[ÖöĞğŞşÇç]", lambda h: ESKI_HARF.get(h.group(0)) or (
                    {"Ş": "SH", "Ç": "CH"} if katta else {"Ş": "Sh", "Ç": "Ch"})[h.group(0)], soz)
            out += [t[i:m.start()], soz]
            i = m.end()
        out.append(t[i:])
        return "".join(out)

    return _himoyala(unicodedata.normalize("NFC", matn), bolak)


def segmentlarni_yangila(segmentlar: list[dict]) -> list[dict]:
    """Segmentlar matnini yangi alifboga o'giradi (gʻ apostrofi har segmentda alohida aniqlanadi)."""
    m = " ".join(s.get("text", "") for s in segmentlar)
    a, b = len(re.findall(r"[OoGg][ʻ‘]", m)), len(re.findall(r"[OoGg]['’`´ʼ]", m))
    umumiy = a > 0 and b <= a * 0.2

    def rejim(t):
        if re.search(rf"[Oo]['’`´ʼ]{_HARF}", t):
            return False
        return True if re.search(r"[OoGg][ʻ‘]", t) else umumiy

    return [{**s, "text": yangi_matn(s.get("text", ""), rejim(s.get("text", "")))} for s in segmentlar]

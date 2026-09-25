"""Telegram Bot API bilan ishlash — faqat standart kutubxona."""

import json
import os
import re
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Token ko'chirilganda ortiqcha so'z yoki bo'sh qator qo'shilib ketsa ham,
# undan faqat tokenning o'zini (123456:ABC...) ajratib olamiz.
_xom = os.environ.get("BOT_TOKEN", "")
_top = re.search(r"\d{5,}:[A-Za-z0-9_-]{30,}", _xom)
TOKEN = _top.group(0) if _top else _xom.strip()
API = "https://api.telegram.org/bot%s/" % TOKEN

# Bu xatolar odatiy holat — logni to'ldirmaymiz.
_JIM = ("message is not modified", "query is too old", "bot was blocked",
        "user is deactivated", "chat not found")


def _sorov(req, timeout):
    """So'rov yuboradi; 429 bo'lsa kutib qayta urinadi. Natija — dict."""
    for urinish in range(3):
        try:
            with urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except HTTPError as e:
            try:
                res = json.load(e)
            except ValueError:
                res = {"ok": False, "description": str(e)}
            res["error_code"] = e.code
            kut = (res.get("parameters") or {}).get("retry_after")
            if e.code == 429 and kut and urinish < 2:
                time.sleep(kut + 1)
                continue
            izoh = res.get("description") or ""
            if not any(x in izoh for x in _JIM):
                print("telegram xatosi:", req.full_url.rsplit("/", 1)[-1], izoh, file=sys.stderr)
            return res
        except (URLError, OSError) as e:
            print("tarmoq xatosi:", e, file=sys.stderr)
            time.sleep(2)
    return {"ok": False}


def call(method, **params):
    params = {k: v for k, v in params.items() if v is not None}
    req = Request(API + method, data=json.dumps(params).encode(),
                  headers={"Content-Type": "application/json"})
    return _sorov(req, params.get("timeout", 0) + 30)


def send(chat_id, text, kb=None):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
                reply_markup=kb, link_preview_options={"is_disabled": True})


def send_photo(chat_id, photo, caption, kb=None):
    return call("sendPhoto", chat_id=chat_id, photo=photo, caption=caption,
                parse_mode="HTML", reply_markup=kb)


def edit(chat_id, message_id, text, kb=None):
    """Xabarni tahrirlaydi; bo'lmasa (masalan, rasmli xabar) yangisini yuboradi."""
    r = call("editMessageText", chat_id=chat_id, message_id=message_id, text=text,
             parse_mode="HTML", reply_markup=kb, link_preview_options={"is_disabled": True})
    if r.get("ok") or "not modified" in (r.get("description") or ""):
        return r
    return send(chat_id, text, kb)


def edit_kb(chat_id, message_id, kb):
    return call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup=kb)


def answer(callback_id, text=None, alert=False):
    return call("answerCallbackQuery", callback_query_id=callback_id, text=text,
                show_alert=alert or None)


def send_document(chat_id, filename, data, caption=""):
    chegara = uuid.uuid4().hex
    qismlar = []
    for nom, qiymat in (("chat_id", str(chat_id)), ("caption", caption)):
        qismlar.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                        % (chegara, nom, qiymat)).encode())
    qismlar.append(('--%s\r\nContent-Disposition: form-data; name="document"; filename="%s"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n' % (chegara, filename)).encode()
                   + data + b"\r\n")
    qismlar.append(("--%s--\r\n" % chegara).encode())
    req = Request(API + "sendDocument", data=b"".join(qismlar),
                  headers={"Content-Type": "multipart/form-data; boundary=" + chegara})
    return _sorov(req, 120)


def download(file_id):
    """Telegramdagi faylni baytlarga yuklab oladi (xato bo'lsa None)."""
    yol = (call("getFile", file_id=file_id).get("result") or {}).get("file_path")
    if not yol:
        return None
    try:
        with urlopen("https://api.telegram.org/file/bot%s/%s" % (TOKEN, yol), timeout=120) as r:
            return r.read()
    except (URLError, OSError) as e:
        print("fayl yuklashda xato:", e, file=sys.stderr)
        return None

"""Mutolaa bot — ma'lumotlar bazasi (SQLite, standart kutubxona)."""

import contextlib
import json
import os
import sqlite3
import time

SXEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,      -- Telegram chat id
    username      TEXT DEFAULT '',
    first_name    TEXT DEFAULT '',
    last_name     TEXT DEFAULT '',
    age           TEXT DEFAULT '',
    phone         TEXT DEFAULT '',
    genres        TEXT DEFAULT '',          -- janr kalitlari, vergul bilan
    survey        TEXT DEFAULT '{}',        -- so'rovnoma javoblari (JSON)
    ref           TEXT DEFAULT '',          -- qaysi havoladan kelgan (Instagram, Telegram...)
    invited_by    INTEGER,                  -- taklif qilgan kitobxon
    step          TEXT,                     -- ro'yxatdan o'tishning joriy qadami
    tmp           TEXT DEFAULT '{}',
    joined_at     INTEGER,
    registered_at INTEGER,
    blocked       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS users_phone ON users(phone);
CREATE TABLE IF NOT EXISTS books (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    author TEXT DEFAULT '',
    genre  TEXT DEFAULT '',
    price  INTEGER DEFAULT 0,
    stock  INTEGER DEFAULT 0,               -- qoldi
    sold   INTEGER DEFAULT 0,               -- sotildi
    about  TEXT DEFAULT '',
    photo  TEXT DEFAULT '',                 -- Telegram file_id
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,                     -- do'kondagi sotuvda bo'sh bo'lishi mumkin
    book_id    INTEGER NOT NULL,
    qty        INTEGER DEFAULT 1,
    price      INTEGER DEFAULT 0,           -- bir dona narxi (aksiya bo'lsa — aksiya narxi)
    status     TEXT DEFAULT 'yangi',        -- yangi / sotildi / bekor
    via        TEXT DEFAULT 'bot',          -- bot / dokon
    gift       TEXT DEFAULT '',
    created_at INTEGER,
    done_at    INTEGER
);
CREATE INDEX IF NOT EXISTS orders_status ON orders(status, done_at);
CREATE TABLE IF NOT EXISTS gifts (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    stock INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


class Baza:
    def __init__(self, yol):
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        self.yol = yol
        self.c = sqlite3.connect(yol, timeout=30, isolation_level=None, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SXEMA)

    def close(self):
        self.c.close()

    # ------------------------------------------------------------ umumiy
    def q(self, sql, *a):
        return self.c.execute(sql, a).fetchall()

    def one(self, sql, *a):
        return self.c.execute(sql, a).fetchone()

    def run(self, sql, *a):
        return self.c.execute(sql, a)

    @contextlib.contextmanager
    def tx(self):
        self.c.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.c.execute("ROLLBACK")
            raise
        self.c.execute("COMMIT")

    def get(self, key, default=None):
        r = self.one("SELECT value FROM settings WHERE key=?", key)
        return json.loads(r["value"]) if r else default

    def put(self, key, value):
        self.run("INSERT INTO settings(key, value) VALUES(?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 key, json.dumps(value, ensure_ascii=False))

    def backup_bytes(self):
        """Bazaning to'liq nusxasi (baytlar) — zaxira uchun."""
        tmp = self.yol + ".nusxa"
        dst = sqlite3.connect(tmp)
        self.c.backup(dst)
        dst.close()
        with open(tmp, "rb") as f:
            data = f.read()
        os.remove(tmp)
        return data

    # ------------------------------------------------------------ foydalanuvchilar
    def user(self, uid):
        return self.one("SELECT * FROM users WHERE id=?", uid)

    def add_user(self, uid, username):
        self.run("INSERT OR IGNORE INTO users(id, username, joined_at) VALUES(?, ?, ?)",
                 uid, username or "", int(time.time()))

    def upd_user(self, uid, **f):
        if f:
            self.run("UPDATE users SET %s WHERE id=?" % ", ".join("%s=?" % k for k in f),
                     *f.values(), uid)

    def user_by_phone(self, phone):
        return self.one("SELECT * FROM users WHERE phone=? AND registered_at IS NOT NULL", phone)

    def audience(self, genre=None):
        rows = self.q("SELECT * FROM users WHERE registered_at IS NOT NULL AND blocked=0")
        if genre:
            rows = [u for u in rows if genre in (u["genres"] or "").split(",")]
        return rows

    def mark_blocked(self, ids):
        self.c.executemany("UPDATE users SET blocked=1 WHERE id=?", [(i,) for i in ids])

    def invited_count(self, uid):
        return self.one("SELECT COUNT(*) n FROM users WHERE invited_by=? AND registered_at IS NOT NULL",
                        uid)["n"]

    # ------------------------------------------------------------ kitoblar
    def book(self, bid):
        return self.one("SELECT * FROM books WHERE id=?", bid)

    def books(self, genre=None):
        if genre:
            return self.q("SELECT * FROM books WHERE active=1 AND genre=? ORDER BY title", genre)
        return self.q("SELECT * FROM books WHERE active=1 ORDER BY title")

    def add_book(self, title, author, genre, price, stock, about=""):
        """Nomi va muallifi bir xil kitob bo'lsa — yangilaydi. (id, yangimi) qaytaradi."""
        r = self.one("SELECT id FROM books WHERE title=? COLLATE NOCASE AND author=? COLLATE NOCASE",
                     title, author)
        if r:
            self.run("UPDATE books SET genre=?, price=?, stock=?, active=1, "
                     "about=CASE WHEN ?<>'' THEN ? ELSE about END WHERE id=?",
                     genre, price, stock, about, about, r["id"])
            return r["id"], False
        cur = self.run("INSERT INTO books(title, author, genre, price, stock, about) "
                       "VALUES(?, ?, ?, ?, ?, ?)", title, author, genre, price, stock, about)
        return cur.lastrowid, True

    def top(self, since, limit=10):
        """Berilgan vaqtdan beri eng ko'p sotilgan kitoblar (n — sotilgan soni)."""
        return self.q("SELECT b.*, SUM(o.qty) AS n FROM orders o JOIN books b ON b.id=o.book_id "
                      "WHERE o.status='sotildi' AND o.done_at>=? AND b.active=1 "
                      "GROUP BY b.id ORDER BY n DESC, b.title LIMIT ?", int(since), limit)

    # ------------------------------------------------------------ buyurtma va sotuv
    def order(self, oid):
        return self.one("SELECT o.*, b.title, b.author, b.stock FROM orders o "
                        "JOIN books b ON b.id=o.book_id WHERE o.id=?", oid)

    def pending_order(self, uid, bid):
        return self.one("SELECT * FROM orders WHERE user_id=? AND book_id=? AND status='yangi'",
                        uid, bid)

    def new_order(self, uid, bid, price, qty=1):
        return self.run("INSERT INTO orders(user_id, book_id, qty, price, created_at) "
                        "VALUES(?, ?, ?, ?, ?)", uid, bid, qty, price, int(time.time())).lastrowid

    def _chiqim(self, bid, qty):
        """Ombordan kitob va sovg'ani chiqaradi (tranzaksiya ichida). (sovg'a, xato)."""
        b = self.book(bid)
        if not b or b["stock"] < qty:
            return "", "Qoldiq yetarli emas (%d ta bor)" % (b["stock"] if b else 0)
        self.run("UPDATE books SET stock=stock-?, sold=sold+? WHERE id=?", qty, qty, bid)
        g = self.one("SELECT * FROM gifts WHERE stock>0 ORDER BY stock DESC, id LIMIT 1")
        if not g:
            return "", None
        self.run("UPDATE gifts SET stock=stock-1 WHERE id=?", g["id"])
        return g["name"], None

    def sell_order(self, oid):
        """Bot orqali kelgan buyurtmani «sotildi» qiladi. (buyurtma, xato)."""
        with self.tx():
            o = self.one("SELECT * FROM orders WHERE id=?", oid)
            if not o:
                return None, "Buyurtma topilmadi"
            if o["status"] != "yangi":
                return self.order(oid), "Bu buyurtma allaqachon ko'rib chiqilgan"
            gift, xato = self._chiqim(o["book_id"], o["qty"])
            if xato:
                return self.order(oid), xato
            self.run("UPDATE orders SET status='sotildi', gift=?, done_at=? WHERE id=?",
                     gift, int(time.time()), oid)
        return self.order(oid), None

    def sell_direct(self, bid, qty, price, uid=None):
        """Do'kondagi (oflayn) sotuvni yozib qo'yadi. (buyurtma, xato)."""
        with self.tx():
            gift, xato = self._chiqim(bid, qty)
            if xato:
                return None, xato
            t = int(time.time())
            oid = self.run("INSERT INTO orders(user_id, book_id, qty, price, status, via, gift, "
                           "created_at, done_at) VALUES(?, ?, ?, ?, 'sotildi', 'dokon', ?, ?, ?)",
                           uid, bid, qty, price, gift, t, t).lastrowid
        return self.order(oid), None

    def cancel_order(self, oid):
        with self.tx():
            o = self.one("SELECT * FROM orders WHERE id=?", oid)
            if not o or o["status"] != "yangi":
                return self.order(oid) if o else None, "Bu buyurtma allaqachon ko'rib chiqilgan"
            self.run("UPDATE orders SET status='bekor', done_at=? WHERE id=?", int(time.time()), oid)
        return self.order(oid), None

    def bought(self, uid):
        """Kitobxon sotib olgan kitoblar (sovg'alari bilan)."""
        return self.q("SELECT o.*, b.title FROM orders o JOIN books b ON b.id=o.book_id "
                      "WHERE o.user_id=? AND o.status='sotildi' ORDER BY o.done_at DESC", uid)

    # ------------------------------------------------------------ sovg'alar
    def gifts(self):
        return self.q("SELECT * FROM gifts ORDER BY id")

    def add_gift(self, name, qty):
        self.run("INSERT INTO gifts(name, stock) VALUES(?, ?) "
                 "ON CONFLICT(name) DO UPDATE SET stock=stock+excluded.stock", name, qty)

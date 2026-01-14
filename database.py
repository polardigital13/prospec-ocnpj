import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "prospeccao.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT UNIQUE NOT NULL,
            razao_social TEXT,
            cidade TEXT,
            uf TEXT,
            cnae_principal TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            data_abertura TEXT,
            segmento TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'novo'  -- novo, contatado, respondeu, convertido, bloqueado
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            kind TEXT NOT NULL, -- first, followup_24h, followup_72h, followup_7d
            template_key TEXT,
            message_text TEXT NOT NULL,
            sent_at TEXT,
            -- queued, sent, failed
            status TEXT DEFAULT 'queued',
            provider_message_id TEXT,
            error TEXT,
            FOREIGN KEY (lead_id) REFERENCES leads(id)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS opt_out (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT DEFAULT 'user' -- user, admin, webhook
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS daily_limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT UNIQUE NOT NULL, -- YYYY-MM-DD
            sent_count INTEGER NOT NULL DEFAULT 0
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL, -- capture, send, reply, optout, error, startup
            payload TEXT,
            created_at TEXT NOT NULL
        )
        """)


def log_event(event_type: str, payload: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO events(type, payload, created_at) VALUES (?, ?, ?)",
            (event_type, payload, datetime.utcnow().isoformat())
        )


def upsert_daily_counter(day: str, inc: int = 1):
    with get_conn() as conn:
        row = conn.execute("SELECT sent_count FROM daily_limits WHERE day=?", (day,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO daily_limits(day, sent_count) VALUES(?, ?)",
                (day, inc),
            )
        else:
            conn.execute(
                "UPDATE daily_limits SET sent_count = sent_count + ? WHERE day= ?",
                (inc, day),
            )


def get_daily_sent(day: str) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT sent_count FROM daily_limits WHERE day=?", (day,)).fetchone()
        return int(row["sent_count"]) if row else 0

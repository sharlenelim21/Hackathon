"""SQLite access. One connection per operation: Streamlit sessions run in different threads."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .config import get_settings

MYT = timezone(timedelta(hours=8))

SCHEMA = """
CREATE TABLE IF NOT EXISTS laws(
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  jurisdiction TEXT NOT NULL CHECK(jurisdiction IN ('Sarawak','Federal')),
  instrument_type TEXT NOT NULL DEFAULT 'Ordinance',
  cap_no TEXT,
  sector TEXT NOT NULL,
  language TEXT NOT NULL DEFAULT 'en' CHECK(language IN ('en','ms')),
  group_code TEXT NOT NULL,
  created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS versions(
  id INTEGER PRIMARY KEY,
  law_id INTEGER NOT NULL REFERENCES laws(id),
  label TEXT NOT NULL,
  published_date TEXT, in_force_date TEXT, source_url TEXT,
  source_authority TEXT NOT NULL DEFAULT 'official' CHECK(source_authority IN ('official','unofficial')),
  file_path TEXT NOT NULL,
  sha256 TEXT UNIQUE NOT NULL,
  page_count INTEGER NOT NULL,
  parse_mode TEXT NOT NULL CHECK(parse_mode IN ('sections','pages')),
  parse_warnings TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','superseded')),
  uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL,
  reviewed_by TEXT, reviewed_at TEXT, review_note TEXT,
  diff_json TEXT);

CREATE TABLE IF NOT EXISTS sections(
  id INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL REFERENCES versions(id),
  key TEXT NOT NULL,
  section_no TEXT NOT NULL,
  part TEXT, heading TEXT,
  text TEXT NOT NULL,
  page_start INTEGER NOT NULL, page_end INTEGER NOT NULL,
  amend_notes TEXT NOT NULL DEFAULT '[]',
  ord INTEGER NOT NULL,
  UNIQUE(version_id, key));
CREATE INDEX IF NOT EXISTS ix_sections_version ON sections(version_id);

CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
  heading, text, content='sections', content_rowid='id',
  tokenize='porter unicode61 remove_diacritics 2');

CREATE TABLE IF NOT EXISTS triggers(
  id INTEGER PRIMARY KEY,
  activity_tag TEXT NOT NULL,
  law_id INTEGER NOT NULL REFERENCES laws(id),
  section_no TEXT NOT NULL,
  severity_override TEXT CHECK(severity_override IN ('red','yellow') OR severity_override IS NULL),
  note TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','needs_review')),
  proposed_by TEXT NOT NULL, proposed_at TEXT NOT NULL,
  reviewed_by TEXT, reviewed_at TEXT, review_note TEXT);

CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  target_type TEXT NOT NULL, target_id INTEGER NOT NULL, note TEXT);

CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def now_iso() -> str:
    return datetime.now(MYT).isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(MYT).date().isoformat()


def db_path():
    return get_settings().data_dir / "app.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def transaction():
    """Open a connection, commit on success, roll back on error, always close."""
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    with transaction() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('kb_version', '0')")


def get_kb_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM meta WHERE key='kb_version'").fetchone()
    return int(row["value"]) if row else 0


def bump_kb_version(conn: sqlite3.Connection) -> int:
    conn.execute("UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key='kb_version'")
    return get_kb_version(conn)


def audit(conn: sqlite3.Connection, actor: str, action: str, target_type: str,
          target_id: int, note: str | None = None) -> None:
    conn.execute(
        "INSERT INTO audit_log(ts, actor, action, target_type, target_id, note) VALUES(?,?,?,?,?,?)",
        (now_iso(), actor or "Legal officer", action, target_type, int(target_id), note),
    )

"""Laws, versions, approvals and trigger rules: the human-in-the-loop gate.

Nothing an officer uploads or proposes is searchable until it is approved.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

from . import db
from .catalog import codes_for, detect_language, detect_meta
from .config import (AUDIT_LIMIT, DIFF_TEXT_CHARS, MAX_UPLOAD_BYTES, MIN_CHARS_PER_PAGE,
                     TRIGGER_ID_OFFSET, get_settings, store_path, tags)
from .errors import ServiceError
from .parser import ParseResult, parse
from .pdftext import PageText, avg_chars_per_page, open_pdf, page_texts
from .verify import normalize

DEFAULT_ACTOR = "Legal officer"


# ---------------------------------------------------------------- validation helpers

def clean_meta(meta: dict | None) -> dict:
    m = dict(meta or {})

    def s(k: str) -> str | None:
        v = m.get(k)
        return str(v).strip() if v not in (None, "") else None

    required = {"title": s("title"), "jurisdiction": s("jurisdiction"), "sector": s("sector"),
                "version_label": s("version_label")}
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ServiceError("validation", f"Missing required field(s): {', '.join(missing)}.")
    jurisdiction = required["jurisdiction"].capitalize()
    if jurisdiction not in ("Sarawak", "Federal"):
        raise ServiceError("validation", "Jurisdiction must be 'Sarawak' or 'Federal'.")
    for d in ("published_date", "in_force_date"):
        if s(d):
            try:
                date.fromisoformat(s(d))
            except ValueError:
                raise ServiceError("validation", f"{d} must be a date like 2025-01-31.") from None
    authority = (s("source_authority") or "official").lower()
    if authority not in ("official", "unofficial"):
        raise ServiceError("validation", "source_authority must be 'official' or 'unofficial'.")
    mode = (s("parse_mode") or "auto").lower()
    if mode not in ("auto", "sections", "pages"):
        raise ServiceError("validation", "parse_mode must be 'auto', 'sections' or 'pages'.")

    def page(k: str) -> int | None:
        if s(k) is None:
            return None
        try:
            return int(s(k))
        except ValueError:
            raise ServiceError("validation", f"{k} must be a page number.") from None

    language = (s("language") or "").lower() or None
    if language not in (None, "en", "ms"):
        raise ServiceError("validation", "language must be 'en' or 'ms'.")
    return {"title": required["title"], "jurisdiction": jurisdiction, "sector": required["sector"],
            "version_label": required["version_label"], "cap_no": s("cap_no"),
            "published_date": s("published_date"), "in_force_date": s("in_force_date"),
            "source_url": s("source_url"), "source_authority": authority,
            "uploaded_by": s("uploaded_by") or DEFAULT_ACTOR, "parse_mode": mode,
            "body_page_from": page("body_page_from"), "body_page_to": page("body_page_to"),
            "instrument_type": s("instrument_type") or ("Act" if jurisdiction == "Federal" else "Ordinance"),
            "language": language, "code": s("code"), "group_code": s("group_code")}


def _open(file_bytes: bytes) -> tuple:
    if not file_bytes:
        raise ServiceError("bad_file", "The file is empty.")
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise ServiceError("bad_file", "The file is larger than 50 MB.")
    if b"%PDF" not in file_bytes[:1024]:
        raise ServiceError("bad_file", "This is not a PDF file.")
    try:
        doc = open_pdf(data=file_bytes)
    except Exception:
        raise ServiceError("bad_file", "The PDF could not be opened.") from None
    if doc.needs_pass:
        doc.close()
        raise ServiceError("bad_file", "The PDF is password-protected.")
    pages = page_texts(doc)
    if avg_chars_per_page(pages) < MIN_CHARS_PER_PAGE:
        doc.close()
        raise ServiceError("scanned_pdf", "This PDF has no text layer (it looks scanned). "
                                          "Upload a text PDF; scanned documents are not supported.")
    return doc, pages


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _norm_cap(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _find_law(conn: sqlite3.Connection, m: dict, language: str) -> sqlite3.Row | None:
    if m["code"]:
        row = conn.execute("SELECT * FROM laws WHERE code=?", (m["code"],)).fetchone()
        if row:
            return row
    row = conn.execute("SELECT * FROM laws WHERE lower(title)=lower(?) AND language=?",
                       (m["title"], language)).fetchone()
    if row or not m["cap_no"]:
        return row
    for r in conn.execute("SELECT * FROM laws WHERE jurisdiction=? AND language=?", (m["jurisdiction"], language)):
        if r["cap_no"] and _norm_cap(r["cap_no"]) == _norm_cap(m["cap_no"]):
            return r
    return None


def _unique_code(conn: sqlite3.Connection, code: str) -> str:
    base, n, out = code, 2, code
    while conn.execute("SELECT 1 FROM laws WHERE code=?", (out,)).fetchone():
        out = f"{base}-{n}"
        n += 1
    return out


def _identity(conn, m: dict, pages: list[PageText], existing, language: str) -> tuple[str, str]:
    """(code, group_code) for the version's law; language versions of an Act share the group."""
    if existing is not None:
        return existing["code"], existing["group_code"]
    if m["code"]:
        code, group = m["code"], m["group_code"] or m["code"]
    else:
        detected = detect_meta(pages)
        detected["language"] = language
        code, group = codes_for(detected, m["jurisdiction"])
        code = _unique_code(conn, code)
        group = m["group_code"] or group
    return code, group


def _parse(pages: list[PageText], code: str, m: dict) -> ParseResult:
    mode = "pages" if m["parse_mode"] == "pages" else "auto"
    return parse(pages, code, mode, m["body_page_from"], m["body_page_to"])


def current_version(conn: sqlite3.Connection, law_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM versions WHERE law_id=? AND status='approved'", (law_id,)).fetchone()


def pending_version_for(conn: sqlite3.Connection, law_id: int) -> dict | None:
    row = conn.execute("SELECT uploaded_at FROM versions WHERE law_id=? AND status='pending' "
                       "ORDER BY uploaded_at DESC LIMIT 1", (law_id,)).fetchone()
    return {"uploaded": row["uploaded_at"][:10]} if row else None


# ---------------------------------------------------------------- upload

def preview(file_bytes: bytes, meta: dict) -> dict:
    """Parse in memory; nothing is saved."""
    m = clean_meta(meta)
    doc, pages = _open(file_bytes)
    try:
        language = m["language"] or detect_language(pages)
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM versions WHERE sha256=?", (_sha(file_bytes),)).fetchone():
                raise ServiceError("duplicate_file", "This exact file has already been uploaded.")
            existing = _find_law(conn, m, language)
            code, _ = _identity(conn, m, pages, existing, language)
        result = _parse(pages, code, m)
        detected = detect_meta(pages)
    finally:
        doc.close()
    return {"sections_count": len(result.sections), "toc": result.toc,
            "is_new_version_of": existing["title"] if existing is not None else None,
            "mode": result.mode, "page_count": result.page_count, "warnings": result.warnings,
            "detected": {"title": detected["title"], "language": language, "code": code,
                         "version_label": detected["version_label"]}}


def submit(file_bytes: bytes, meta: dict, *, source_path: Path | None = None) -> dict:
    """Save the file and a PENDING version. Seed data passes source_path (file stays in Law/)."""
    m = clean_meta(meta)
    doc, pages = _open(file_bytes)
    sha = _sha(file_bytes)
    try:
        language = m["language"] or detect_language(pages)
        with db.transaction() as conn:
            if conn.execute("SELECT 1 FROM versions WHERE sha256=?", (sha,)).fetchone():
                raise ServiceError("duplicate_file", "This exact file has already been uploaded.")
            existing = _find_law(conn, m, language)
            code, group = _identity(conn, m, pages, existing, language)
            result = _parse(pages, code, m)
            if source_path is not None:
                stored = store_path(source_path)
            else:
                dest = get_settings().data_dir / "files" / f"{sha}.pdf"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(file_bytes)
                stored = store_path(dest)
            if existing is None:
                law_id = conn.execute(
                    "INSERT INTO laws(code, title, jurisdiction, instrument_type, cap_no, sector, language, "
                    "group_code, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (code, m["title"], m["jurisdiction"], m["instrument_type"], m["cap_no"], m["sector"],
                     language, group, db.now_iso())).lastrowid
            else:
                law_id = existing["id"]
            vid = conn.execute(
                "INSERT INTO versions(law_id, label, published_date, in_force_date, source_url, source_authority, "
                "file_path, sha256, page_count, parse_mode, parse_warnings, status, uploaded_by, uploaded_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,'pending',?,?)",
                (law_id, m["version_label"], m["published_date"], m["in_force_date"], m["source_url"],
                 m["source_authority"], stored, sha, result.page_count, result.mode,
                 json.dumps(result.warnings), m["uploaded_by"], db.now_iso())).lastrowid
            _insert_sections(conn, vid, result.sections)
            cur = current_version(conn, law_id)
            diff = _diff(conn, cur["id"], vid) if cur is not None else None
            if diff:
                conn.execute("UPDATE versions SET diff_json=? WHERE id=?", (json.dumps(diff), vid))
            db.audit(conn, m["uploaded_by"], "upload", "version", vid, f"{m['title']} — {m['version_label']}")
    finally:
        doc.close()
    return {"version_id": vid, "status": "pending", "law_id": law_id, "is_new_law": existing is None,
            "diff_summary": diff["summary"] if diff else None}


def _insert_sections(conn: sqlite3.Connection, vid: int, sections: list[dict]) -> None:
    conn.executemany(
        "INSERT INTO sections(version_id, key, section_no, part, heading, text, page_start, page_end, "
        "amend_notes, ord) VALUES(?,?,?,?,?,?,?,?,?,?)",
        [(vid, s["key"], s["section_no"], s["part"], s["heading"], s["text"], s["page_start"], s["page_end"],
          json.dumps(s["amend_notes"]), i) for i, s in enumerate(sections)])
    conn.execute("INSERT INTO sections_fts(rowid, heading, text) "
                 "SELECT id, coalesce(heading, ''), text FROM sections WHERE version_id=?", (vid,))


def _diff(conn: sqlite3.Connection, old_vid: int, new_vid: int) -> dict:
    def load(vid: int) -> dict[str, tuple[int, str]]:
        return {r["section_no"]: (r["ord"], r["text"]) for r in conn.execute(
            "SELECT section_no, ord, text FROM sections WHERE version_id=? AND (part IS NULL OR part != 'Appendix')",
            (vid,))}
    old, new = load(old_vid), load(new_vid)
    items, udiff, unchanged = [], [], 0
    for no in sorted(set(old) | set(new), key=lambda n: (new.get(n) or old.get(n))[0]):
        o, n = old.get(no), new.get(no)
        if o and n and normalize(o[1]) == normalize(n[1]):
            unchanged += 1
            continue
        change = "added" if o is None else "removed" if n is None else "changed"
        items.append({"section_no": no, "change": change,
                      "old": o[1][:DIFF_TEXT_CHARS] if o else None, "new": n[1][:DIFF_TEXT_CHARS] if n else None})
        if len(udiff) < 400:
            udiff += list(difflib.unified_diff((o[1] if o else "").splitlines(), (n[1] if n else "").splitlines(),
                                               f"s.{no} (old)", f"s.{no} (new)", n=1, lineterm=""))[:60]
    summary = {"added": sum(i["change"] == "added" for i in items),
               "removed": sum(i["change"] == "removed" for i in items),
               "changed": sum(i["change"] == "changed" for i in items), "unchanged": unchanged}
    return {"against_version_id": old_vid, "items": items, "unified_diff": "\n".join(udiff[:400]),
            "summary": summary}


# ---------------------------------------------------------------- review queue

def pending_items() -> list[dict]:
    with db.transaction() as conn:
        versions = conn.execute(
            "SELECT v.*, l.title AS law_title, l.code AS law_code, "
            "(SELECT COUNT(*) FROM versions v2 WHERE v2.law_id=v.law_id AND v2.status IN ('approved','superseded')) "
            "AS prior FROM versions v JOIN laws l ON l.id=v.law_id WHERE v.status='pending'").fetchall()
        triggers = conn.execute(
            "SELECT t.*, l.title AS law_title, l.code AS law_code FROM triggers t JOIN laws l ON l.id=t.law_id "
            "WHERE t.status IN ('pending','needs_review')").fetchall()
    items = []
    for v in versions:
        diff = json.loads(v["diff_json"]) if v["diff_json"] else None
        items.append({"id": v["id"], "type": "new_version" if v["prior"] else "new_law",
                      "title": f"{v['law_title']} — {v['label']}", "uploaded_by": v["uploaded_by"],
                      "uploaded_at": v["uploaded_at"], "diff": diff["items"] if diff else None,
                      "version_id": v["id"], "law_id": v["law_id"], "law_code": v["law_code"],
                      "unified_diff": diff["unified_diff"] if diff else None,
                      "diff_summary": diff["summary"] if diff else None,
                      "warnings": json.loads(v["parse_warnings"])})
    for t in triggers:
        items.append({"id": TRIGGER_ID_OFFSET + t["id"], "type": "trigger",
                      "title": f"{t['activity_tag']} → {t['law_title']} s.{t['section_no']}",
                      "uploaded_by": t["proposed_by"], "uploaded_at": t["proposed_at"], "diff": None,
                      "trigger_id": t["id"], "status": t["status"], "severity_override": t["severity_override"],
                      "note": t["note"], "law_id": t["law_id"], "law_code": t["law_code"]})
    return sorted(items, key=lambda i: i["uploaded_at"], reverse=True)


def decide(item_id: int, approve: bool, note: str | None, reviewer: str | None) -> None:
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        raise ServiceError("not_found", f"No pending item with id {item_id!r}.") from None
    reviewer = (reviewer or "").strip() or DEFAULT_ACTOR
    note = (note or "").strip() or None
    if item_id >= TRIGGER_ID_OFFSET:
        _decide_trigger(item_id - TRIGGER_ID_OFFSET, approve, note, reviewer)
    else:
        _decide_version(item_id, approve, note, reviewer)


def _decide_version(vid: int, approve: bool, note: str | None, reviewer: str) -> None:
    with db.transaction() as conn:
        v = conn.execute("SELECT * FROM versions WHERE id=?", (vid,)).fetchone()
        if v is None:
            raise ServiceError("not_found", f"No pending item with id {vid}.")
        if v["status"] != "pending":
            raise ServiceError("wrong_state", f"This version is already {v['status']}.")
        now = db.now_iso()
        if not approve:
            conn.execute("UPDATE versions SET status='rejected', reviewed_by=?, reviewed_at=?, review_note=? WHERE id=?",
                         (reviewer, now, note, vid))
            db.audit(conn, reviewer, "reject_version", "version", vid, note)
            return
        prev = current_version(conn, v["law_id"])
        if prev is not None:
            conn.execute("UPDATE versions SET status='superseded' WHERE id=?", (prev["id"],))
        conn.execute("UPDATE versions SET status='approved', reviewed_by=?, reviewed_at=?, review_note=? WHERE id=?",
                     (reviewer, now, note, vid))
        flagged = 0
        if prev is not None and v["diff_json"]:
            touched = {i["section_no"] for i in json.loads(v["diff_json"])["items"]
                       if i["change"] in ("changed", "removed")}
            for t in conn.execute("SELECT id, section_no FROM triggers WHERE law_id=? AND status='approved'",
                                  (v["law_id"],)).fetchall():
                if t["section_no"] in touched:
                    conn.execute("UPDATE triggers SET status='needs_review' WHERE id=?", (t["id"],))
                    flagged += 1
        db.bump_kb_version(conn)
        db.audit(conn, reviewer, "approve_version", "version", vid, note)
        if flagged:
            db.audit(conn, "system", "flag_triggers_needs_review", "version", vid,
                     f"{flagged} trigger rule(s) point to sections that changed")


def _decide_trigger(tid: int, approve: bool, note: str | None, reviewer: str) -> None:
    with db.transaction() as conn:
        t = conn.execute("SELECT * FROM triggers WHERE id=?", (tid,)).fetchone()
        if t is None:
            raise ServiceError("not_found", f"No pending item with id {TRIGGER_ID_OFFSET + tid}.")
        if t["status"] not in ("pending", "needs_review"):
            raise ServiceError("wrong_state", f"This trigger rule is already {t['status']}.")
        conn.execute("UPDATE triggers SET status=?, reviewed_by=?, reviewed_at=?, review_note=? WHERE id=?",
                     ("approved" if approve else "rejected", reviewer, db.now_iso(), note, tid))
        db.bump_kb_version(conn)
        db.audit(conn, reviewer, "approve_trigger" if approve else "reject_trigger", "trigger", tid, note)


# ---------------------------------------------------------------- trigger rules

def normalize_section_no(s: str) -> str:
    s = re.sub(r"^(s\.|sec\.?|section|seksyen|art\.?|article|perkara)\s*", "", str(s or "").strip(), flags=re.I)
    return s.strip().upper()


def propose_trigger(activity_tag: str, law_id: int, section_no: str, note: str | None,
                    severity_override: str | None, proposed_by: str | None) -> dict:
    if activity_tag not in tags():
        raise ServiceError("validation", f"Unknown activity tag '{activity_tag}'.")
    sev = (severity_override or "").strip().lower() or None
    if sev not in (None, "red", "yellow"):
        raise ServiceError("validation", "severity_override must be 'red', 'yellow' or empty.")
    no = normalize_section_no(section_no)
    actor = (proposed_by or "").strip() or DEFAULT_ACTOR
    with db.transaction() as conn:
        law = conn.execute("SELECT * FROM laws WHERE id=?", (law_id,)).fetchone()
        if law is None:
            raise ServiceError("validation", f"Unknown law id {law_id}.")
        cur = current_version(conn, law["id"])
        if cur is None:
            raise ServiceError("validation", f"{law['title']} has no approved version yet.")
        if not conn.execute("SELECT 1 FROM sections WHERE version_id=? AND section_no=?", (cur["id"], no)).fetchone():
            raise ServiceError("validation", f"Section {no} was not found in {law['title']}.")
        tid = conn.execute(
            "INSERT INTO triggers(activity_tag, law_id, section_no, severity_override, note, status, proposed_by, "
            "proposed_at) VALUES(?,?,?,?,?,'pending',?,?)",
            (activity_tag, law["id"], no, sev, (note or "").strip() or None, actor, db.now_iso())).lastrowid
        db.audit(conn, actor, "propose_trigger", "trigger", tid, f"{activity_tag} → {law['code']}:{no}")
    return {"id": tid, "status": "pending"}


def insert_approved_trigger(conn: sqlite3.Connection, activity_tag: str, law_id: int, section_no: str,
                            severity_override: str | None, note: str | None, actor: str) -> None:
    now = db.now_iso()
    conn.execute(
        "INSERT INTO triggers(activity_tag, law_id, section_no, severity_override, note, status, proposed_by, "
        "proposed_at, reviewed_by, reviewed_at) VALUES(?,?,?,?,?,'approved',?,?,?,?)",
        (activity_tag, law_id, normalize_section_no(section_no), severity_override, note, actor, now, actor, now))


# ---------------------------------------------------------------- catalogue

def list_triggers() -> list[dict]:
    with db.transaction() as conn:
        rows = conn.execute("SELECT t.*, l.title AS law_title, l.code AS law_code FROM triggers t "
                            "JOIN laws l ON l.id=t.law_id ORDER BY t.proposed_at DESC, t.id DESC").fetchall()
    return [{"id": r["id"], "activity_tag": r["activity_tag"], "law_title": r["law_title"],
             "section_no": r["section_no"], "note": r["note"], "status": r["status"],
             "law_id": r["law_id"], "law_code": r["law_code"], "severity_override": r["severity_override"],
             "proposed_by": r["proposed_by"], "proposed_at": r["proposed_at"], "reviewed_by": r["reviewed_by"]}
            for r in rows]


def list_laws() -> list[dict]:
    out = []
    with db.transaction() as conn:
        for law in conn.execute("SELECT * FROM laws ORDER BY jurisdiction DESC, title").fetchall():
            cur = current_version(conn, law["id"])
            shown = cur or conn.execute("SELECT * FROM versions WHERE law_id=? ORDER BY uploaded_at DESC LIMIT 1",
                                        (law["id"],)).fetchone()
            pending = conn.execute("SELECT COUNT(*) FROM versions WHERE law_id=? AND status='pending'",
                                   (law["id"],)).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM sections WHERE version_id=?",
                                 (shown["id"],)).fetchone()[0] if shown else 0
            out.append({"id": law["id"], "title": law["title"], "jurisdiction": law["jurisdiction"],
                        "cap_no": law["cap_no"], "sector": law["sector"],
                        "version_label": shown["label"] if shown else None,
                        "status": shown["status"] if shown else "none",
                        "code": law["code"], "language": law["language"], "group_code": law["group_code"],
                        "instrument_type": law["instrument_type"], "pending_versions": pending,
                        "section_count": count, "source_authority": shown["source_authority"] if shown else None})
    return out


def audit_log(limit: int = AUDIT_LIMIT) -> list[dict]:
    with db.transaction() as conn:
        rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return [{"ts": r["ts"], "actor": r["actor"], "action": r["action"], "target_type": r["target_type"],
             "target_id": int(r["target_id"]), "note": r["note"]} for r in rows]

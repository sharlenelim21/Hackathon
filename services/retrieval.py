"""Structure-aware (vectorless) retrieval over APPROVED law versions only.

Sources of candidate sections, in priority order:
  trigger rules (curated by the legal officer) > sections the LLM picks from the table of contents
  > keyword hits inside laws the LLM picked > global keyword hits (SQLite FTS5 / BM25)
  > one-hop cross-references ("section N").
English and Bahasa Melayu versions of the same Act share a group_code; we answer from the
version that matches the question's language.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass

from . import db
from .config import TOC_LINES_PER_LAW
from .verify import normalize

_STOP = set("""
a an and are as at be been but by for from has have in into is it its of on or that the their this to was were will
with which who whom any such shall may under section sections act ordinance person persons other than not no
yang dan di ke dari untuk dengan pada ini itu akan atau oleh dalam bagi kepada adalah ialah tidak boleh hendaklah
seksyen akta ordinan mana mana-mana suatu sesuatu
""".split())
_MS_HINT = re.compile(r"\b(yang|dan|untuk|ini|akan|di|ke|dengan|pada|tanah|kerajaan|membina|bina|projek|kemudahan"
                      r"|sungai|majlis|daerah|tapak|hektar|syarikat|perniagaan|lesen|jabatan|bagi|kami|saya)\b", re.I)
_EN_HINT = re.compile(r"\b(the|and|for|will|build|of|on|to|with|project|site|river|council|district|company"
                      r"|business|licence|license|department|we|our|plan|plans|new)\b", re.I)
_XREF = re.compile(r"\b(?:section|seksyen)\s+(\d{1,3}[A-Z]{0,2})\b", re.I)


def query_language(text: str) -> str:
    return "ms" if len(_MS_HINT.findall(text)) > len(_EN_HINT.findall(text)) else "en"


@dataclass
class LawInfo:
    id: int
    code: str
    title: str
    language: str
    group_code: str
    sector: str
    jurisdiction: str
    cap_no: str | None
    version_id: int
    version_label: str
    in_force_date: str | None
    source_authority: str
    file_path: str
    instrument_type: str


@dataclass
class SectionInfo:
    key: str
    law_id: int
    section_no: str
    part: str | None
    heading: str | None
    page_start: int
    page_end: int
    ord: int


@dataclass
class Index:
    kb: int
    laws: dict[int, LawInfo]
    by_code: dict[str, LawInfo]
    sections: dict[str, SectionInfo]
    toc: dict[int, list[SectionInfo]]
    groups: dict[str, list[LawInfo]]


_lock = threading.Lock()
_cache: Index | None = None


def reset() -> None:
    global _cache
    _cache = None


def get_index(conn: sqlite3.Connection) -> Index:
    global _cache
    kb = db.get_kb_version(conn)
    if _cache is not None and _cache.kb == kb:
        return _cache
    with _lock:
        if _cache is None or _cache.kb != kb:
            _cache = _build(conn, kb)
        return _cache


def _build(conn: sqlite3.Connection, kb: int) -> Index:
    laws: dict[int, LawInfo] = {}
    for r in conn.execute(
            "SELECT l.*, v.id AS vid, v.label, v.in_force_date, v.source_authority, v.file_path "
            "FROM laws l JOIN versions v ON v.law_id=l.id AND v.status='approved'"):
        laws[r["id"]] = LawInfo(r["id"], r["code"], r["title"], r["language"], r["group_code"], r["sector"],
                                r["jurisdiction"], r["cap_no"], r["vid"], r["label"], r["in_force_date"],
                                r["source_authority"], r["file_path"], r["instrument_type"])
    by_version = {law.version_id: law for law in laws.values()}
    sections: dict[str, SectionInfo] = {}
    toc: dict[int, list[SectionInfo]] = {lid: [] for lid in laws}
    if by_version:
        marks = ",".join("?" * len(by_version))
        for r in conn.execute(f"SELECT version_id, key, section_no, part, heading, page_start, page_end, ord "
                              f"FROM sections WHERE version_id IN ({marks}) ORDER BY version_id, ord",
                              list(by_version)):
            law = by_version[r["version_id"]]
            info = SectionInfo(r["key"], law.id, r["section_no"], r["part"], r["heading"], r["page_start"],
                               r["page_end"], r["ord"])
            sections[info.key] = info
            toc[law.id].append(info)
    groups: dict[str, list[LawInfo]] = {}
    for law in laws.values():
        groups.setdefault(law.group_code, []).append(law)
    return Index(kb, laws, {law.code: law for law in laws.values()}, sections, toc, groups)


# ------------------------------------------------------------- language versions

def preferred_law(idx: Index, law: LawInfo, lang: str) -> LawInfo:
    members = idx.groups.get(law.group_code, [law])
    return next((m for m in members if m.language == lang), law)


def to_language(idx: Index, key: str, lang: str) -> str:
    """Same section in the preferred-language version of the Act, if that version has it."""
    sec = idx.sections.get(key)
    if sec is None:
        return key
    target = preferred_law(idx, idx.laws[sec.law_id], lang)
    alt = f"{target.code}:{sec.section_no}"
    return alt if alt in idx.sections else key


def canon_key(idx: Index, raw: str) -> str | None:
    k = re.sub(r"\s+", "", str(raw or "")).upper()
    if ":" not in k:
        return None
    code, no = k.split(":", 1)
    no = re.sub(r"^(S\.|SEC\.?|SECTION|SEKSYEN|ART\.?|ARTICLE|PERKARA)", "", no)
    key = f"{code}:{no}"
    return key if key in idx.sections else None


def canon_code(idx: Index, raw: str) -> str | None:
    code = re.sub(r"\s+", "", str(raw or "")).upper()
    return code if code in idx.by_code else None


# ------------------------------------------------------------- keyword search (FTS5)

def fts_query(text: str) -> str:
    seen: list[str] = []
    for t in re.findall(r"[a-z0-9]+", normalize(text)):
        if len(t) < 3 or t.isdigit() or t in _STOP or t in seen:
            continue
        seen.append(t)
    return " OR ".join(f'"{t}"' for t in seen[:24])


def fts(conn: sqlite3.Connection, idx: Index, text: str, limit: int = 60,
        law_ids: list[int] | None = None) -> list[str]:
    q = fts_query(text)
    if not q:
        return []
    sql = ("SELECT s.key FROM sections_fts JOIN sections s ON s.id = sections_fts.rowid "
           "JOIN versions v ON v.id = s.version_id "
           "WHERE sections_fts MATCH ? AND v.status = 'approved'")
    args: list = [q]
    if law_ids:
        sql += f" AND v.law_id IN ({','.join('?' * len(law_ids))})"
        args += law_ids
    sql += " ORDER BY bm25(sections_fts, 2.0, 1.0) LIMIT ?"
    args.append(limit)
    try:
        return [r["key"] for r in conn.execute(sql, args) if r["key"] in idx.sections]
    except sqlite3.OperationalError:
        return []


def top_laws(idx: Index, hit_keys: list[str], lang: str, k: int) -> list[LawInfo]:
    """Laws ranked by how many strong keyword hits they have (one entry per language group)."""
    score: dict[str, float] = {}
    for rank, key in enumerate(hit_keys):
        group = idx.laws[idx.sections[key].law_id].group_code
        score[group] = score.get(group, 0.0) + 1.0 / (1 + rank * 0.1)
    best = sorted(score, key=score.get, reverse=True)[:k]
    return [preferred_law(idx, idx.groups[g][0], lang) for g in best]


# ------------------------------------------------------------- prompt material

def catalog_lines(idx: Index, lang: str) -> str:
    lines = []
    for group in sorted(idx.groups, key=lambda g: preferred_law(idx, idx.groups[g][0], lang).title):
        law = preferred_law(idx, idx.groups[group][0], lang)
        langs = ", ".join(sorted(m.language for m in idx.groups[group]))
        lines.append(f"{law.code} | {law.title} | {law.instrument_type} | {law.jurisdiction} | {law.sector} | "
                     f"{law.cap_no or '-'} | {langs}")
    return "\n".join(lines)


def toc_block(idx: Index, laws: list[LawInfo], hit_keys: list[str]) -> str:
    hits = set(hit_keys)
    blocks = []
    for law in laws:
        secs = [s for s in idx.toc.get(law.id, []) if not s.section_no.startswith("p")]
        if len(secs) > TOC_LINES_PER_LAW:
            chosen = [s for s in secs if s.key in hits] or secs[:30]
            secs = chosen[:TOC_LINES_PER_LAW]
        lines = [f"{s.key} | {s.part or ''} | {s.heading or ''}" for s in secs]
        blocks.append(f"## {law.code} — {law.title}\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def triggers_for(conn: sqlite3.Connection, idx: Index, tags: list[str], lang: str) -> list[dict]:
    if not tags:
        return []
    rows = conn.execute(
        f"SELECT t.*, l.code FROM triggers t JOIN laws l ON l.id=t.law_id "
        f"WHERE t.status IN ('approved','needs_review') AND t.activity_tag IN ({','.join('?' * len(tags))}) "
        f"ORDER BY t.id", tags).fetchall()
    out = []
    for r in rows:
        key = f"{r['code']}:{r['section_no']}"
        if key in idx.sections:
            out.append({"key": to_language(idx, key, lang), "trigger_id": r["id"], "status": r["status"],
                        "severity_override": r["severity_override"], "note": r["note"]})
    return out


def merge(idx: Index, lists: list[tuple[str, list[str]]], lang: str, cap: int) -> tuple[list[str], dict[str, list[str]]]:
    order: list[str] = []
    sources: dict[str, list[str]] = {}
    for source, keys in lists:
        for key in keys:
            key = to_language(idx, key, lang)
            if key not in sources:
                sources[key] = []
                order.append(key)
            if source not in sources[key]:
                sources[key].append(source)
    return order[:cap], sources


def section_rows(conn: sqlite3.Connection, idx: Index, keys: list[str]) -> dict[str, sqlite3.Row]:
    out = {}
    for key in keys:
        sec = idx.sections[key]
        row = conn.execute("SELECT * FROM sections WHERE version_id=? AND key=?",
                           (idx.laws[sec.law_id].version_id, key)).fetchone()
        if row is not None:
            out[key] = row
    return out


def xrefs(idx: Index, rows: dict[str, sqlite3.Row], have: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for key, row in rows.items():
        code = key.split(":", 1)[0]
        for no in _XREF.findall(row["text"]):
            ref = f"{code}:{no.upper()}"
            if ref in idx.sections and ref not in have and ref not in out:
                out.append(ref)
                if len(out) >= limit:
                    return out
    return out

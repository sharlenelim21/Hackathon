"""Read a law PDF's own cover page: title, language, Act/Chapter number, version date.

Used by scripts/build_catalog.py (seed catalog for the Law/ folder) and by uploads, so titles
come from the document, not from file names (e.g. 'LAWS OF SARAWAK.pdf' is really the
Native Customary Marriages (Maintenance) Ordinance).
"""
from __future__ import annotations

import re
from pathlib import Path

from .pdftext import PageText

_MS_WORDS = re.compile(r"\b(yang|dan|ini|bagi|tidak|hendaklah|seksyen|mana-mana|oleh|dalam|kepada)\b", re.I)
_EN_WORDS = re.compile(r"\b(the|and|shall|of|any|which|under|section|person|such)\b", re.I)

_ACT = re.compile(r"^(?:Act|Akta)\s+(A?\d{1,4})$", re.I)
_CHAPTER = re.compile(r"^(?:Chapter|Cap\.?)\s+(\d{1,3})\b", re.I)
_ORD = re.compile(r"\[Ord\.\s*No\.\s*(\d+)\s*/\s*(\d+)\]", re.I)
_EDITION = re.compile(r"^\(\d{4}\s+(?:Edition|Ed\.)\)$", re.I)
_STOP = re.compile(r"^(Incorporating|As at|Mengandungi|Sebagaimana|PUBLISHED|DITERBITKAN|Printed|Date of|Tarikh|Teks ini"
                   r"|Prepared|Disediakan|_{3,}|\d+$)", re.I)
_BOILER = re.compile(r"^(LAWS OF (MALAYSIA|SARAWAK)|UNDANG-UNDANG( MALAYSIA)?|MALAYSIA|REPRINT|CETAKAN SEMULA.*"
                     r"|ONLINE VERSION.*|VERSI .*|TEXT OF REPRINT|OF UPDATED TEXT OF REPRINT)$", re.I)
_SMALL = {"and", "of", "the", "for", "in", "to", "on", "a", "an", "dan", "bagi", "di", "ke", "dari", "yang", "atau"}


def detect_language(pages: list[PageText]) -> str:
    text = " ".join(" ".join(p.lines) for p in pages[:25])
    return "ms" if len(_MS_WORDS.findall(text)) > len(_EN_WORDS.findall(text)) else "en"


def smart_title(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" ,.")
    if not (s.isupper() or s.islower()):
        return s
    words = s.title().split(" ")
    out = [w if i == 0 or w.lower() not in _SMALL else w.lower() for i, w in enumerate(words)]
    return " ".join(out)


def _cover_lines(pages: list[PageText]) -> list[str]:
    lines: list[str] = []
    for p in pages[:2]:
        lines += [re.sub(r"\s+", " ", ln).strip() for ln in p.lines if ln.strip()]
        if len(lines) >= 8:
            break
    return lines


def detect_meta(pages: list[PageText], path: Path | None = None) -> dict:
    """Best-effort metadata from the first pages. Every field may be None."""
    lines = _cover_lines(pages)
    head = " ".join(lines[:40])
    meta: dict = {"language": detect_language(pages), "act_no": None, "chapter": None, "ord_no": None,
                  "title": None, "version_label": None, "translation": "TERJEMAHAN" in head.upper()}

    anchor = None
    for i, ln in enumerate(lines[:20]):
        if m := _ACT.match(ln):
            meta["act_no"], anchor = m.group(1).upper(), i
            break
        if m := _CHAPTER.match(ln):
            meta["chapter"], anchor = m.group(1), i
        if m := _ORD.search(ln):
            meta["ord_no"], anchor = f"{m.group(1)}/{m.group(2)}", i
        if anchor is not None and i > anchor:
            break
    if meta["chapter"] is None and (m := re.search(r"\bCHAPTER\s+(\d{1,3})\b", head, re.I)):
        meta["chapter"] = m.group(1)

    title_lines: list[str] = []
    if anchor is not None:
        for ln in lines[anchor + 1:anchor + 10]:
            if _EDITION.match(ln) or _CHAPTER.match(ln) or _ORD.search(ln):
                continue
            if _STOP.match(ln):
                break
            title_lines.append(ln)
    if "CONSTITUTION" in head.upper() and not meta["act_no"]:
        title_lines = ["Federal Constitution"]
    elif "PERLEMBAGAAN PERSEKUTUAN" in head.upper() and not meta["act_no"]:
        title_lines = ["Perlembagaan Persekutuan"]
    if not title_lines:
        title_lines = [ln for ln in lines[:4] if not _BOILER.match(ln) and not ln.isdigit()][:2]
    title = smart_title(" ".join(title_lines)) if title_lines else None
    if (not title) and path is not None:
        title = smart_title(path.stem.replace("_", " "))
    meta["title"] = title

    flat = re.sub(r"\s+", " ", " ".join(" ".join(p.lines) for p in pages[:3]))
    for pat, fmt in [
        (r"Incorporating all amendments up to ([0-9]{1,2}(?:st|nd|rd|th)? \w+,? [0-9]{4})", "Amendments up to {}"),
        (r"As at ([0-9]{1,2} \w+ [0-9]{4})", "As at {}"),
        (r"Mengandungi segala pindaan (?:sehingga|hingga) ([0-9]{1,2} \w+ [0-9]{4})", "Pindaan hingga {}"),
        (r"Sebagaimana pada ([0-9]{1,2} \w+ [0-9]{4})", "Sebagaimana pada {}"),
        (r"Tarikh Persetujuan Diraja ([0-9]{1,2}-\w+-[0-9]{4})", "Persetujuan Diraja {}"),
        (r"Date of Royal Assent ([0-9]{1,2} \w+ [0-9]{4})", "Royal Assent {}"),
    ]:
        if m := re.search(pat, flat, re.I):
            meta["version_label"] = fmt.format(m.group(1))
            break
    if meta["translation"]:
        meta["version_label"] = "Terjemahan · " + (meta["version_label"] or "tarikh tidak dinyatakan")
    return meta


def codes_for(meta: dict, jurisdiction: str) -> tuple[str, str]:
    """(code, group_code). Language versions of one Act share the group_code."""
    suffix = "-MS" if meta.get("language") == "ms" else ""
    title = (meta.get("title") or "").lower()
    if meta.get("act_no"):
        base = f"ACT{meta['act_no']}"
        return base + suffix, f"MY-{base}"
    if "constitution" in title or "perlembagaan" in title:
        return "FC" + suffix, "MY-FC"
    if meta.get("chapter"):
        base = f"CAP{meta['chapter']}"
        return base + suffix, f"SWK-{base}"
    if meta.get("ord_no"):
        base = "ORD" + meta["ord_no"].replace("/", "-")
        return base + suffix, f"SWK-{base}"
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", meta.get("title") or "X") if w.lower() not in _SMALL).upper()
    return (initials[:8] or "LAW") + suffix, f"{'MY' if jurisdiction == 'Federal' else 'SWK'}-{initials[:8] or 'LAW'}"

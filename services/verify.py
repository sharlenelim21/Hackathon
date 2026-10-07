"""Quote normalization, verification against the stored text, and highlight boxes."""
from __future__ import annotations

import math
import re
import unicodedata
from difflib import SequenceMatcher

import pymupdf

_DASHES = dict.fromkeys(map(ord, "⎯—–‐‑−"), "-")
_QUOTES = {ord("“"): '"', ord("”"): '"', ord("„"): '"',
           ord("‘"): "'", ord("’"): "'"}
_TOKEN = re.compile(r"[a-z0-9]+")

MIN_EXACT_TOKENS = 6
MIN_NEAR_TOKENS = 8
NEAR_RATIO = 0.9


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").translate(_DASHES).translate(_QUOTES)
    s = re.sub(r"\*(?=\d)", "", s)
    s = re.sub(r"\s*-\s*", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def tokens(s: str) -> list[str]:
    return _TOKEN.findall(normalize(s))


def clean_quote(quote: str) -> str:
    q = (quote or "").strip().strip('"\'“”‘’').strip()
    q = re.sub(r"(\.\.\.|…)+$", "", q).strip()
    return re.sub(r"^(\.\.\.|…)+", "", q).strip()


def verify_quote(quote: str, section_text: str) -> str | None:
    """Return 'exact', 'near' or None. The quote must come from this section's stored text."""
    q = clean_quote(quote)
    tq = tokens(q)
    if len(tq) < MIN_EXACT_TOKENS:
        return None
    if normalize(q) in normalize(section_text):
        return "exact"
    ts = tokens(section_text)
    m = SequenceMatcher(None, tq, ts, autojunk=False).find_longest_match(0, len(tq), 0, len(ts))
    if m.size >= max(MIN_NEAR_TOKENS, math.ceil(NEAR_RATIO * len(tq))):
        return "near"
    return None


def sentence_around(quote: str, section_text: str, before: int = 400, after: int = 900) -> str:
    """The legal sentence that contains the quote, for judging severity. Wording such as
    '…shall be guilty of an offence' often comes after the part the AI quoted, so judging the
    quote alone can turn a real requirement into 'info'. Falls back to the quote itself."""
    n = normalize(section_text)
    q = normalize(clean_quote(quote))
    i = n.find(q) if q else -1
    if i < 0:
        return quote
    j = i + len(q)
    start = n.rfind(". ", 0, i)
    start = 0 if start < 0 else start + 2
    end = n.find(". ", j)
    end = len(n) if end < 0 else end + 1
    return n[max(start, i - before):min(end, j + after)]


def find_highlight(pdf_path: str, page_start: int, page_end: int,
                   quote: str) -> tuple[int, list[list[float]]]:
    """Best-effort boxes for the quote. Returns (1-based page, rects); rects are all on that page."""
    tq = tokens(clean_quote(quote))
    if not tq:
        return page_start, []
    best_size, best_page, best_words, best_word_list = 0, page_start, [], []
    try:
        doc = pymupdf.open(pdf_path)
    except Exception:
        return page_start, []
    try:
        for p in range(page_start, min(page_end, doc.page_count) + 1):
            words = doc[p - 1].get_text("words")
            flat, owner = [], []
            for wi, w in enumerate(words):
                for t in tokens(w[4]):
                    flat.append(t)
                    owner.append(wi)
            if not flat:
                continue
            m = SequenceMatcher(None, tq, flat, autojunk=False).find_longest_match(0, len(tq), 0, len(flat))
            if m.size > best_size:
                best_size, best_page = m.size, p
                best_words = sorted(set(owner[m.b:m.b + m.size]))
                best_word_list = words
    finally:
        doc.close()
    if best_size < min(5, len(tq)):
        return page_start, []
    lines: dict[tuple[int, int], list[float]] = {}
    for wi in best_words:
        x0, y0, x1, y1, _, block, line, _ = best_word_list[wi]
        r = lines.get((block, line))
        lines[(block, line)] = [x0, y0, x1, y1] if r is None else [min(r[0], x0), min(r[1], y0), max(r[2], x1), max(r[3], y1)]
    rects = [[round(v, 1) for v in r] for r in sorted(lines.values(), key=lambda r: (r[1], r[0]))]
    return best_page, rects

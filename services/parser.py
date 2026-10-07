"""Split a law PDF into sections using its own structure (vectorless chunking).

LawNet (Sarawak) and AGC (federal) reprints share a layout:
- a front table of contents "N. Heading" that repeats every section number,
- section start lines like "1. This Ordinance…", "2.⎯(1) In this…", "*11A.⎯(1)…", "6A.—(1)…",
- the heading (marginal note) on its own line(s) just above the section start line,
- footnotes after a line of underscores (removed by pdftext),
- sometimes rules, forms or schedules appended with their own numbering.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from .pdftext import PageText
from .verify import tokens

SECTION_RE = re.compile(r"^\s*\*?(\d{1,3})([A-Z]{0,2})\.(?=\s|[⎯—–-]|$)")
PART_RE = re.compile(r"^\s*(PART|BAHAGIAN)\s+([IVXLC]+|\d+[A-Z]?)\b\.?\s*(.*)$", re.I)
APPENDIX_RE = re.compile(
    r"^((FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH|THIRTEENTH)\s+)?SCHEDULE$"
    r"|^JADUAL(\s+[A-Z]+)?$|^LIST OF AMENDMENTS$|^SENARAI PINDAAN$")
AMEND_RE = re.compile(r"\[((?:Am|Ins|Sub|Rep|Del|Pind|Mas|Ganti|Pot)\.[^\]]{1,80})\]")

MAX_GAP = 25              # largest allowed jump between consecutive section numbers
MIN_CHAIN = 3             # hits needed to treat a numbered run as a ToC or body
TOC_MEDIAN_CHARS = 150    # ToC entries are short; body sections are long
MAX_SECTION_CHARS = 40000
MAX_LAST_SECTION_PAGES = 6


@dataclass
class _Hit:
    line: int
    num: int
    suf: str
    page: int

    @property
    def no(self) -> str:
        return f"{self.num}{self.suf}"


@dataclass
class ParseResult:
    mode: str                          # 'sections' | 'pages'
    sections: list[dict]
    warnings: list[str] = field(default_factory=list)
    page_count: int = 0

    @property
    def toc(self) -> list[dict]:
        return [{"part": s["part"] or "", "section_no": s["section_no"], "heading": s["heading"] or "",
                 "page_start": s["page_start"]} for s in self.sections]


def _is_caps(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return len(letters) >= 3 and all(c.isupper() for c in letters)


def _can_follow(prev: _Hit, h: _Hit) -> bool:
    if h.num == prev.num:
        return h.suf > prev.suf
    return prev.num < h.num <= prev.num + MAX_GAP


def _chains(hits: list[_Hit]) -> list[list[_Hit]]:
    """Greedy: each hit extends the longest chain it can follow; otherwise starts a new one.
    Numbered lists inside a schedule start their own chain instead of breaking the body."""
    chains: list[list[_Hit]] = []
    for h in hits:
        best = None
        for c in chains:
            if _can_follow(c[-1], h) and (best is None or len(c) > len(best)):
                best = c
        if best is None:
            chains.append([h])
        else:
            best.append(h)
    return [c for c in chains if len(c) >= MIN_CHAIN]


def _seg_chars(lines: list[str], start: int, end: int) -> int:
    return sum(len(lines[k]) for k in range(start, end))


def _toc_headings(chain: list[_Hit], lines: list[str]) -> dict[str, str]:
    heads: dict[str, str] = {}
    for j, h in enumerate(chain):
        end = chain[j + 1].line if j + 1 < len(chain) else min(h.line + 3, len(lines))
        first = SECTION_RE.sub("", lines[h.line], count=1).strip()
        parts = [first] if first else []
        for k in range(h.line + 1, end):
            s = lines[k].strip()
            if not s or PART_RE.match(s) or _is_caps(s):
                break
            parts.append(s)
            if len(" ".join(parts)) > 160:
                break
        heading = re.sub(r"\s*\.{3,}\s*\d*\s*$", "", " ".join(parts)).strip(" .")
        if heading:
            heads[h.no] = heading[:160]
    return heads


def _tail_heading(seg: list[str]) -> tuple[list[str], int]:
    """Heading lines printed at the end of the previous segment (just above a section start).
    Returns (heading_lines, index where they start in seg)."""
    out: list[str] = []
    k = len(seg) - 1
    while k > 0 and not seg[k].strip():
        k -= 1
    start = len(seg)
    while k > 0 and len(out) < 3:
        s = seg[k].strip()
        if (not s or len(s) > 100 or s[-1] in ".;:,)]" or s[0] in "([" or PART_RE.match(s)
                or not any(c.isalpha() for c in s)):
            break
        out.insert(0, s)
        start = k
        k -= 1
    return out, start


def _strip_tail_noise(seg: list[str]) -> list[str]:
    """Drop trailing blank, PART and all-caps title lines (they belong to the next section)."""
    while seg and (not seg[-1].strip() or PART_RE.match(seg[-1].strip()) or _is_caps(seg[-1].strip())):
        seg = seg[:-1]
    return seg


def _overlap(a: str, b: str) -> float:
    ta, tb = set(tokens(a)), set(tokens(b))
    return len(ta & tb) / max(len(ta | tb), 1)


def _pages_mode(pages: list[PageText], code: str, from_page: int = 1) -> list[dict]:
    out = []
    for p in pages:
        if p.pdf_page < from_page:
            continue
        text = "\n".join(p.lines).strip()
        if not text:
            continue
        first = next((ln.strip() for ln in p.lines if ln.strip()), "")
        out.append({"key": f"{code}:p{p.pdf_page}", "section_no": f"p{p.pdf_page}", "part": None,
                    "heading": first[:80], "text": text, "page_start": p.pdf_page,
                    "page_end": p.pdf_page, "amend_notes": _amend_notes(text)})
    return out


def _amend_notes(text: str) -> list[str]:
    seen: list[str] = []
    for n in AMEND_RE.findall(text):
        n = re.sub(r"\s+", " ", n).strip()
        if n not in seen:
            seen.append(n)
    return seen


def parse(pages: list[PageText], code: str, mode: str = "auto",
          body_from: int | None = None, body_to: int | None = None) -> ParseResult:
    page_count = len(pages)
    warnings: list[str] = []
    if mode == "pages":
        return ParseResult("pages", _pages_mode(pages, code), ["Parsed by page (requested)."], page_count)

    lines: list[str] = []
    page_of: list[int] = []
    for p in pages:
        for ln in p.lines:
            lines.append(ln)
            page_of.append(p.pdf_page)

    hits = []
    for i, ln in enumerate(lines):
        m = SECTION_RE.match(ln)
        if not m:
            continue
        pg = page_of[i]
        if (body_from and pg < body_from) or (body_to and pg > body_to):
            continue
        hits.append(_Hit(i, int(m.group(1)), m.group(2), pg))
    chains = _chains(hits)

    def span(c: list[_Hit]) -> int:
        return _seg_chars(lines, c[0].line, c[-1].line)

    def median_seg(c: list[_Hit]) -> float:
        segs = [_seg_chars(lines, c[j].line, c[j + 1].line) for j in range(len(c) - 1)]
        return statistics.median(segs) if segs else 0

    toc = next((c for c in sorted(chains, key=lambda c: c[0].line) if median_seg(c) < TOC_MEDIAN_CHARS), None)
    bodies = [c for c in chains if c is not toc and median_seg(c) >= TOC_MEDIAN_CHARS]
    body = max(bodies, key=span, default=None)
    if body is None:
        warnings.append("No numbered sections found; parsed by page.")
        return ParseResult("pages", _pages_mode(pages, code), warnings, page_count)

    headings = _toc_headings(toc, lines) if toc else {}
    if not toc:
        warnings.append("No table of contents detected; headings were taken from the text.")

    # Where the body ends: an appendix heading or another numbered run after the last section.
    last = body[-1]
    cut = len(lines)
    later_runs = [c[0].line for c in chains if c is not body and c is not toc and c[0].line > last.line]
    if later_runs:
        cut = min(later_runs)
    for k in range(last.line + 1, cut):
        s = lines[k].strip()
        if s and _is_caps(s) and APPENDIX_RE.match(re.sub(r"\s+", " ", s)):
            cut = k
            break
    max_line = next((k for k in range(last.line, cut) if page_of[k] > last.page + MAX_LAST_SECTION_PAGES), cut)
    cut = min(cut, max_line)

    # Part labels (only PART lines inside the body region).
    part_at: list[str | None] = [None] * len(lines)
    current = None
    for i in range(len(lines)):
        if i >= body[0].line - 5:
            m = PART_RE.match(lines[i].strip())
            if m:
                title = m.group(3).strip()
                if not title and i + 1 < len(lines) and _is_caps(lines[i + 1].strip()):
                    title = lines[i + 1].strip()
                current = f"{m.group(1).upper()} {m.group(2).upper()}" + (f" {title}" if title else "")
        part_at[i] = current

    segs: list[list[str]] = []
    for j, h in enumerate(body):
        end = body[j + 1].line if j + 1 < len(body) else cut
        segs.append(lines[h.line:end])

    sections: list[dict] = []
    seen_keys: set[str] = set()
    pending_heading = None
    for j, h in enumerate(body):
        seg = list(segs[j])
        heading = headings.get(h.no) or pending_heading
        # Heading of the NEXT section sits at the tail of this segment: detect and strip it.
        if j + 1 < len(body):
            seg = _strip_tail_noise(seg)
            cand, start = _tail_heading(seg)
            nxt = headings.get(body[j + 1].no)
            if cand and (not nxt or _overlap(" ".join(cand), nxt) >= 0.5):
                seg = _strip_tail_noise(seg[:start])
                pending_heading = None if nxt else " ".join(cand)[:160]
            else:
                pending_heading = None
        text = "\n".join(seg).strip()[:MAX_SECTION_CHARS]
        if not heading:
            first = SECTION_RE.sub("", seg[0], count=1).strip() if seg else ""
            heading = " ".join(first.split()[:12]) or None
        last_line = h.line + max(len(seg) - 1, 0)
        key = f"{code}:{h.no}"
        if key in seen_keys:
            key = f"{key}.{j}"
        seen_keys.add(key)
        sections.append({"key": key, "section_no": h.no, "part": part_at[h.line], "heading": heading,
                         "text": text, "page_start": h.page, "page_end": page_of[min(last_line, len(page_of) - 1)],
                         "amend_notes": _amend_notes(text)})

    if cut < len(lines):
        first_page = page_of[cut]
        appendix = _pages_mode(pages, code, from_page=first_page)
        for s in appendix:
            s["part"] = "Appendix"
            if s["key"] not in seen_keys:
                sections.append(s)
        warnings.append(f"Pages {first_page}–{page_count} look like schedules, rules or forms; indexed page by page.")
    return ParseResult("sections", sections, warnings, page_count)

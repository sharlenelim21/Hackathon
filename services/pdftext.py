"""PyMuPDF text extraction with the cleaning the LawNet / AGC reprints need."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf

_FOOTNOTE_SEP = re.compile(r"^\s*_{5,}\s*$")
_PAGE_NO = re.compile(r"^\s*\d{1,4}\s*$")


@dataclass
class PageText:
    pdf_page: int                      # 1-based
    lines: list[str]
    footnotes: list[str] = field(default_factory=list)
    raw_chars: int = 0


def open_pdf(path: str | None = None, data: bytes | None = None) -> pymupdf.Document:
    if data is not None:
        return pymupdf.open(stream=data, filetype="pdf")
    return pymupdf.open(path)


def page_texts(doc: pymupdf.Document) -> list[PageText]:
    """Per-page lines without printed page numbers; footnote blocks (after a line of
    underscores) are kept separately so they never split a section's text."""
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        raw = text.splitlines()
        body, foot, in_foot = [], [], False
        for k, ln in enumerate(raw):
            if not in_foot and _FOOTNOTE_SEP.match(ln) and _footnote_follows(raw, k):
                in_foot = True
                continue
            if in_foot:
                foot.append(ln)
            elif not _PAGE_NO.match(ln) and not _FOOTNOTE_SEP.match(ln):
                body.append(ln.rstrip())
        pages.append(PageText(i + 1, body, foot, len(text.strip())))
    return pages


def _footnote_follows(raw: list[str], k: int) -> bool:
    """A real footnote separator is followed by a marked note ('* See …'); decorative
    underline bars around headings such as 'ARRANGEMENT OF SECTIONS' are not."""
    for ln in raw[k + 1:]:
        s = ln.strip()
        if s:
            return s[0] in "*†"
    return False


def avg_chars_per_page(pages: list[PageText]) -> float:
    return sum(p.raw_chars for p in pages) / max(len(pages), 1)

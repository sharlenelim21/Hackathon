"""Page image with the quote highlighted (PyMuPDF). Pages are 1-based."""
from __future__ import annotations

import os

import pymupdf


def render_highlight(pdf_path: str, page: int, rects: list, dpi: int = 110) -> bytes | None:
    """PNG of the 1-based `page` with highlight boxes; the plain page when `rects` is empty;
    None if the file is missing or the page does not exist."""
    if not pdf_path or not os.path.exists(pdf_path):
        return None
    doc = pymupdf.open(pdf_path)
    try:
        if not 1 <= int(page) <= doc.page_count:
            return None
        pg = doc[int(page) - 1]
        boxes = [pymupdf.Rect(*r) for r in (rects or []) if len(r) == 4]
        if boxes:
            pg.add_highlight_annot(boxes)
        return pg.get_pixmap(dpi=dpi).tobytes("png")
    finally:
        doc.close()

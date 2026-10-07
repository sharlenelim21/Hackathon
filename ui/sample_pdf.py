"""Generate a small SAMPLE PDF at runtime for the mock "View highlighted page".

The project scope forbids creating or editing files/ and committing binaries,
so instead of shipping a PDF we synthesise a one-page placeholder on demand
using PyMuPDF (already a dependency) and cache it in the OS temp directory.

The generated page lays out a few lines of clearly-labelled SAMPLE text at
known coordinates; mock_data points conditions' highlight_rects at the line
each quote refers to, so render_highlight draws a gold box over real content.

Everything here is placeholder text — never real statute wording.
"""

from __future__ import annotations

import os
import tempfile
from typing import List, Optional

# Line layout: (y-top, text). x starts at LEFT. Each line is LINE_H tall.
LEFT = 72.0
LINE_H = 26.0
FONT_SIZE = 12

# Lines rendered on the sample page, in order. The rects the mock uses point
# at these y positions (see rect_for_line / SAMPLE_RECTS below).
_LINES = [
    "SAMPLE LAW — placeholder page for UI demo only.",
    "This document contains no real statute wording.",
    "",
    "s.11A  The proponent 'shall' submit a report prior to commencement.",
    "        (SAMPLE TEXT — replace with verified s.11A wording from LawNet)",
    "",
    "s.27   No person 'may' erect a building without approval.",
    "        (SAMPLE TEXT — replace with verified s.27 wording from LawNet)",
]

# Y-top of the first line of text on the page.
_TOP = 90.0


def rect_for_line(line_index: int) -> List[float]:
    """Return an [x0, y0, x1, y1] box covering the given 0-based line."""
    y0 = _TOP + line_index * LINE_H - 2
    y1 = y0 + FONT_SIZE + 6
    return [LEFT - 2, y0, 540.0, y1]


# Convenience rects the mock can reuse for its two sample conditions.
SAMPLE_RECTS_11A: List[List[float]] = [rect_for_line(3)]  # the s.11A 'shall' line
SAMPLE_RECTS_27: List[List[float]] = [rect_for_line(6)]   # the s.27 'may' line

_cached_path: Optional[str] = None


def sample_pdf_path() -> str:
    """Create (once) and return the path to the generated sample PDF.

    Falls back to a sentinel path if PyMuPDF is unavailable; render_highlight
    and the download button both handle a missing file gracefully.
    """
    global _cached_path
    if _cached_path and os.path.exists(_cached_path):
        return _cached_path

    target = os.path.join(tempfile.gettempdir(), "rakan_sample_law.pdf")

    try:
        import fitz  # PyMuPDF

        doc = fitz.open()
        page = doc.new_page()  # default A4-ish
        y = _TOP
        for line in _LINES:
            if line:
                page.insert_text(
                    (LEFT, y + FONT_SIZE),  # insert_text y is the baseline
                    line,
                    fontsize=FONT_SIZE,
                    fontname="helv",
                    color=(0.17, 0.17, 0.17),
                )
            y += LINE_H
        doc.save(target)
        doc.close()
        _cached_path = target
    except Exception:
        # Leave _cached_path None; callers treat a missing file as "no preview".
        return target

    return _cached_path

"""Parser on the real LawNet PDFs (page numbers apply to these exact files)."""
from functools import lru_cache

from conftest import LC_PDF, NREO_PDF
from services.parser import parse
from services.pdftext import open_pdf, page_texts


@lru_cache(maxsize=None)
def _parsed(path, code, mode="auto"):
    return parse(page_texts(open_pdf(str(path))), code, mode)


def _sec(result, key):
    return next(s for s in result.sections if s["key"] == key)


def test_nreo_section_11a():
    r = _parsed(NREO_PDF, "NREO")
    assert r.mode == "sections"
    s = _sec(r, "NREO:11A")
    assert s["page_start"] == 23 and s["page_end"] == 25
    assert s["heading"].startswith("Reports on activities having impact")
    assert "No person shall carry out" in " ".join(s["text"].split())
    assert "See the Natural Resources" not in s["text"]          # footnote kept out
    assert "Am. Cap. A185/2019" in s["amend_notes"]


def test_nreo_headings_from_toc():
    r = _parsed(NREO_PDF, "NREO")
    assert _sec(r, "NREO:1")["heading"] == "Short title"
    assert _sec(r, "NREO:2")["heading"] == "Interpretation"


def test_land_code_sections():
    r = _parsed(LC_PDF, "LC")
    s5 = _sec(r, "LC:5")
    assert s5["page_start"] == 28 and s5["heading"] == "Native customary rights"
    assert _sec(r, "LC:6A")["heading"] == "Native territorial domain"
    body = [s for s in r.sections if s["part"] != "Appendix"]
    assert len(body) >= 200
    assert any("schedules, rules or forms" in w for w in r.warnings)


def test_no_duplicate_keys_and_counts():
    for path, code, minimum in [(NREO_PDF, "NREO", 40), (LC_PDF, "LC", 200)]:
        r = _parsed(path, code)
        keys = [s["key"] for s in r.sections]
        assert len(keys) == len(set(keys))
        assert len(keys) >= minimum


def test_pages_mode():
    r = _parsed(NREO_PDF, "NREO", "pages")
    assert r.mode == "pages"
    assert r.sections[0]["key"].startswith("NREO:p")

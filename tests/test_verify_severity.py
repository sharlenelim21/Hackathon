from conftest import NREO_PDF
from services.parser import parse
from services.pdftext import open_pdf, page_texts
from services.render import render_highlight
from services.severity import OVERRIDE_WORDING, classify, status_and_headline
from services.verify import find_highlight, sentence_around, verify_quote

REAL = "No person shall carry out or commence any preparatory work relating to any activity"
FAKE = "All school extensions require an EIA approval from the Ministry of Health"


def _s11a():
    r = parse(page_texts(open_pdf(str(NREO_PDF))), "NREO")
    return next(s for s in r.sections if s["key"] == "NREO:11A")


def test_verify_real_and_fake_quote():
    text = _s11a()["text"]
    assert verify_quote(REAL, text) == "exact"
    assert verify_quote(FAKE, text) is None
    assert verify_quote("“" + REAL.replace(" ", "  ") + "…”", text) == "exact"   # quotes, spacing, ellipsis
    assert verify_quote("No person shall", text) is None                         # too short to trust


def test_highlight_on_page_25():
    s = _s11a()
    page, rects = find_highlight(str(NREO_PDF), s["page_start"], s["page_end"], REAL)
    assert page == 25 and rects
    png = render_highlight(str(NREO_PDF), page, rects)
    assert png.startswith(b"\x89PNG")
    assert render_highlight("missing.pdf", 1, []) is None


def test_severity_rules():
    assert classify(REAL) == ("red", "no person shall")
    assert classify("the Board may approve the report")[0] == "yellow"
    assert classify("This Ordinance may be cited as the Test Ordinance")[0] == "yellow"
    assert classify("The Board consists of five members")[0] == "info"
    assert classify("Hendaklah mendapatkan kelulusan")[0] == "red"
    assert classify("Lembaga boleh meluluskan laporan")[0] == "yellow"
    assert classify("tidak boleh memulakan kerja")[0] == "red"
    assert classify("anything", "yellow") == ("yellow", OVERRIDE_WORDING)


def test_severity_uses_the_whole_sentence():
    # Seen live: the AI quoted the part of BPTL s.3 before "shall be guilty of an offence",
    # which turned a trading-licence requirement into "info" and the headline into ⚪.
    text = ("3. Any person who, whether alone or in partnership, carries on in Sarawak any business in respect "
            "of which a trading licence is not for the time being in force shall be guilty of an offence: "
            "Penalty, a fine of one thousand ringgit. 4. The Superintendent may issue a licence.")
    quote = "carries on in Sarawak any business in respect of which a trading licence is not for the time being in force"
    assert classify(quote)[0] == "info"
    assert classify(sentence_around(quote, text))[0] == "red"
    assert classify(sentence_around("The Superintendent may issue a licence", text))[0] == "yellow"
    assert sentence_around("words that are not in the text at all", text) == "words that are not in the text at all"


def test_headlines_never_say_clear():
    cases = [(1, 1, False), (0, 2, False), (0, 0, False), (0, 0, True)]
    for lang in ("en", "ms"):
        for red, yellow, empty in cases:
            _, h = status_and_headline(red, yellow, empty, 2, ["site area"], lang)
            for word in ("clear", "approved", "safe", "legal", "lulus", "selamat"):
                assert word not in h.lower()
    assert status_and_headline(1, 1, False, 2, [], "en") == (
        "red", "🔴 Stop — 1 mandatory requirement(s) before you proceed · 1 more to check")
    assert status_and_headline(0, 0, True, 2, ["site area"], "en")[0] == "abstain"

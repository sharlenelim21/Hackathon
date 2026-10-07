"""Test setup: fake LLM, a temporary data dir, and a small seed catalog (NREO + Land Code) for speed.

The seeded database is built once per session and copied for each test that needs a clean state.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
NREO_PDF = ROOT / "Law" / "Sarawak Environment Law" / "NATURAL RESOURCES AND ENVIRONMENT ORDINANCE.pdf"
LC_PDF = ROOT / "Law" / "Sarawak Native Law" / "LAND CODE.pdf"
SMALL_CATALOG = [e for e in json.loads((ROOT / "services" / "catalog" / "laws.json").read_text(encoding="utf-8"))
                 if e["code"] in ("NREO", "LC")]


def _activate(data_dir: Path, catalog: Path) -> None:
    os.environ.update({"DATA_DIR": str(data_dir), "LLM_PROVIDER": "fake", "CATALOG_FILE": str(catalog),
                       "HIGHLIGHT": "1", "XREFS": "1", "KEYWORD_K": "5"})
    import services
    services._reset_for_tests()


@pytest.fixture(scope="session")
def template(tmp_path_factory):
    base = tmp_path_factory.mktemp("template")
    catalog = base / "laws_small.json"
    catalog.write_text(json.dumps(SMALL_CATALOG), encoding="utf-8")
    _activate(base / "data", catalog)
    import services
    services.health()          # creates the schema and seeds NREO + Land Code
    return base, catalog


@pytest.fixture
def svc(template, tmp_path):
    base, catalog = template
    shutil.copytree(base / "data", tmp_path / "data")
    _activate(tmp_path / "data", catalog)
    import services
    return services


def make_pdf(pages: list[list[str]]) -> bytes:
    """A small text PDF; each page is a list of lines."""
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        y = 60
        for line in lines:
            page.insert_text((60, y), line, fontsize=9)
            y += 13
    data = doc.tobytes()
    doc.close()
    return data


def synthetic_law(title: str, word: str = "drain") -> bytes:
    body = [title.upper(), ""]
    for n in range(1, 6):
        body += [f"Heading of section {n}",
                 f"{n}. No person shall discharge any {word} waste into a public {word} without a permit",
                 "issued by the Council, and every permit holder shall keep records of each discharge",
                 "for inspection by an authorised officer at any reasonable time during working hours.", ""]
    return make_pdf([body])


def modified_nreo() -> bytes:
    """The NREO with one extra sentence on PDF page 25 (inside s.11A), so the diff shows a change."""
    doc = pymupdf.open(NREO_PDF)
    doc[24].insert_text((72, 760), "Inserted test sentence about drainage permits for the version diff.", fontsize=8)
    data = doc.tobytes()
    doc.close()
    return data

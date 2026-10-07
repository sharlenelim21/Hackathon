"""Scan Law/**.pdf and write services/catalog/laws.json (the seed catalog).

Run after adding PDFs to Law/:  .venv/Scripts/python -m scripts.build_catalog
Review the output; fix titles/codes in services/catalog/overrides.json, not in laws.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.catalog import codes_for, detect_meta  # noqa: E402
from services.config import CATALOG_DIR, LAW_DIR, ROOT  # noqa: E402
from services.pdftext import open_pdf, page_texts  # noqa: E402


def main() -> None:
    overrides = json.loads((CATALOG_DIR / "overrides.json").read_text(encoding="utf-8"))
    entries, used = [], set()
    for path in sorted(LAW_DIR.rglob("*.pdf")):
        rel = path.relative_to(ROOT).as_posix()
        folder = path.parent.name                      # e.g. "Malaysia Business Law"
        jurisdiction = "Federal" if folder.lower().startswith("malaysia") else "Sarawak"
        category = folder.split(" ", 1)[1] if " " in folder else folder
        doc = open_pdf(str(path))
        meta = detect_meta(page_texts(doc), path)
        code, group = codes_for(meta, jurisdiction)
        entry = {
            "file": rel,
            "code": code,
            "group_code": group,
            "title": meta["title"],
            "language": meta["language"],
            "jurisdiction": jurisdiction,
            "instrument_type": ("Constitution" if group == "MY-FC" else
                                "Amendment Act" if (meta["act_no"] or "").startswith("A") else
                                "Act" if jurisdiction == "Federal" else "Ordinance"),
            "cap_no": (f"Act {meta['act_no']}" if meta["act_no"] else
                       f"Cap. {meta['chapter']}" if meta["chapter"] else
                       f"Ord. No. {meta['ord_no']}" if meta["ord_no"] else None),
            "sector": f"{category[:1].upper()}{category[1:].lower()} ({jurisdiction})",
            "version_label": meta["version_label"] or "Version date not stated",
            "published_date": None,
            "in_force_date": None,
            "source_url": None,
            "source_authority": "unofficial" if meta["translation"] else "official",
            "parse_mode": "auto",
        }
        entry.update(overrides.get(rel, {}))
        base, n = entry["code"], 2
        while entry["code"] in used:
            entry["code"] = f"{base}-{n}"
            n += 1
        used.add(entry["code"])
        entries.append(entry)
        doc.close()
    out = CATALOG_DIR / "laws.json"
    out.write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for e in entries:
        print(f"{e['code']:12s} {e['group_code']:14s} {e['language']} {e['cap_no'] or '-':14s} "
              f"{e['title'][:60]:60s} | {e['version_label']}")
    print(f"\n{len(entries)} laws -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""Seed the database from services/catalog/laws.json (the Law/ folder) and triggers.json.

Runs automatically on the first service call when the database has no laws, so Streamlit
Cloud (which wipes data/ on restart) rebuilds itself. Manual run: python -m services.seed
"""
from __future__ import annotations

import json
import logging
import time

from . import db, laws
from .config import CATALOG_DIR, ROOT, get_settings
from .errors import ServiceError

log = logging.getLogger("services.seed")
SEED_ACTOR = "seed"
_META_KEYS = ("title", "jurisdiction", "instrument_type", "cap_no", "sector", "version_label", "published_date",
              "in_force_date", "source_url", "source_authority", "parse_mode", "language", "code", "group_code")


def seed_if_empty() -> bool:
    with db.transaction() as conn:
        if conn.execute("SELECT COUNT(*) FROM laws").fetchone()[0]:
            return False
    t0 = time.perf_counter()
    entries = json.loads(get_settings().catalog_file.read_text(encoding="utf-8"))
    loaded = 0
    for e in entries:
        path = ROOT / e["file"]
        if not path.exists():
            log.warning("Seed file missing: %s", e["file"])
            continue
        meta = {k: e.get(k) for k in _META_KEYS}
        meta["uploaded_by"] = SEED_ACTOR
        try:
            res = laws.submit(path.read_bytes(), meta, source_path=path)
        except ServiceError as err:
            log.warning("Seed skipped %s: %s", e["file"], err.message)
            continue
        laws.decide(res["version_id"], True, "Seed data", SEED_ACTOR)
        loaded += 1
    rules = json.loads((CATALOG_DIR / "triggers.json").read_text(encoding="utf-8"))["triggers"]
    with db.transaction() as conn:
        added = 0
        for t in rules:
            law = conn.execute("SELECT id FROM laws WHERE code=?", (t["law_code"],)).fetchone()
            if law is None:
                continue
            laws.insert_approved_trigger(conn, t["activity_tag"], law["id"], t["section_no"],
                                         t.get("severity_override"), t.get("note"), SEED_ACTOR)
            added += 1
        db.bump_kb_version(conn)
        db.audit(conn, SEED_ACTOR, "seed", "law", 0,
                 f"{loaded} laws and {added} trigger rules loaded in {time.perf_counter() - t0:.0f} s")
    log.info("Seeded %d laws, %d trigger rules in %.1f s", loaded, added, time.perf_counter() - t0)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db.init_schema()
    print("seeded" if seed_if_empty() else "database already has laws")

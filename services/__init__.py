"""Backend for the Compliance Impact Alert Streamlit app.

`ui/backend.py` imports these functions when USE_MOCK = False. Names, parameters and return keys
follow the frontend's contract (docs/SERVICE_CONTRACT.md). Extra keys and optional parameters are
additive only. The package initialises itself (schema + seed data) on the first call.
"""
from __future__ import annotations

import threading

from . import db, laws, pipeline, retrieval, seed
from .config import get_settings, tags
from .errors import ServiceError
from .render import render_highlight

__all__ = ["check_action", "upload_preview", "submit_upload", "list_pending", "approve", "reject",
           "list_triggers", "propose_trigger", "list_laws", "get_audit_log", "render_highlight",
           "health", "ServiceError"]

_lock = threading.Lock()
_ready = False


def _ensure_ready() -> None:
    global _ready
    if _ready:
        return
    with _lock:
        if not _ready:
            get_settings().data_dir.mkdir(parents=True, exist_ok=True)
            db.init_schema()
            seed.seed_if_empty()
            _ready = True


def _reset_for_tests() -> None:
    global _ready
    _ready = False
    get_settings.cache_clear()
    tags.cache_clear()
    retrieval.reset()


def check_action(text: str) -> dict:
    """Compliance Impact Alert for a planned action (10–30 s: it calls the LLM twice)."""
    _ensure_ready()
    return pipeline.run_check(text)


def upload_preview(file_bytes: bytes, meta: dict) -> dict:
    """Parse an uploaded law PDF without saving anything."""
    _ensure_ready()
    return laws.preview(file_bytes, meta)


def submit_upload(file_bytes: bytes, meta: dict) -> dict:
    """Save the PDF as a PENDING version; it is not searchable until approved."""
    _ensure_ready()
    return laws.submit(file_bytes, meta)


def list_pending() -> list[dict]:
    _ensure_ready()
    return laws.pending_items()


def approve(item_id: int, note: str = "", reviewer: str = "Legal officer") -> None:
    _ensure_ready()
    laws.decide(item_id, True, note, reviewer)


def reject(item_id: int, note: str = "", reviewer: str = "Legal officer") -> None:
    _ensure_ready()
    laws.decide(item_id, False, note, reviewer)


def list_triggers() -> list[dict]:
    _ensure_ready()
    return laws.list_triggers()


def propose_trigger(activity_tag: str, law_id: int, section_no: str, note: str = "",
                    severity_override: str | None = None, proposed_by: str = "Legal officer") -> None:
    _ensure_ready()
    laws.propose_trigger(activity_tag, law_id, section_no, note, severity_override, proposed_by)


def list_laws() -> list[dict]:
    _ensure_ready()
    return laws.list_laws()


def get_audit_log(limit: int = 100) -> list[dict]:
    _ensure_ready()
    return laws.audit_log(limit)


def health() -> dict:
    _ensure_ready()
    with db.transaction() as conn:
        kb = db.get_kb_version(conn)
        count = conn.execute("SELECT COUNT(*) FROM laws").fetchone()[0]
    return {"status": "ok", "kb_version": kb, "llm_provider": get_settings().llm_provider, "law_count": count}

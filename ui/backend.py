"""The single integration seam between the UI and services/.

This is the ONLY module in the UI that is allowed to talk to services/.
Views import from here; components never do.

Toggle USE_MOCK to switch between the demo mock layer and the real
services/ implementation. The TypedDicts below are the contract: the
teammate implementing services/ must return these exact shapes.
"""

from __future__ import annotations

from typing import List, Optional, TypedDict

# ---------------------------------------------------------------------------
# Mode toggle
# ---------------------------------------------------------------------------
# True  -> use ui/mock_data.py (demo mode, no backend required).
# False -> import the same-named functions from services/. If services/ is
#          missing we fall back to mock and surface an st.warning so the
#          demo never hard-crashes.
#
# The merged services/ backend is now present, so we use it by default.
USE_MOCK = False


# ---------------------------------------------------------------------------
# Fixed vocabulary
# ---------------------------------------------------------------------------
# Canonical activity tags used by the trigger map. Keep in sync with services/.
ACTIVITY_TAGS: List[str] = [
    "construction",
    "land_clearing",
    "land_acquisition",
    "native_land",
    "waste_disposal",
    "water_body",
    "procurement",
    "logging",
    "road_works",
]


# ---------------------------------------------------------------------------
# TypedDicts — the contract. These describe the exact shapes services/ returns.
# ---------------------------------------------------------------------------
class Facts(TypedDict):
    activity: Optional[str]
    location: Optional[str]
    area_ha: Optional[float]
    land_status: Optional[str]


class PendingNewerVersion(TypedDict):
    uploaded: str  # "YYYY-MM-DD"


class Condition(TypedDict):
    id: str
    sector: str
    requirement: str
    why: str
    quote: str  # verbatim, max 30 words
    severity: str  # "red" | "yellow" | "info"
    matched_wording: str  # e.g. "shall", "may"
    law_title: str
    section_no: str
    page: int
    version_label: str
    in_force_date: str  # "YYYY-MM-DD"
    not_yet_in_force: bool
    pending_newer_version: Optional[PendingNewerVersion]
    pdf_path: Optional[str]
    highlight_rects: List[List[float]]  # [[x0, y0, x1, y1], ...]


class ClosestSection(TypedDict):
    law_title: str
    section_no: str
    heading: str
    page: int


class CheckResult(TypedDict):
    status: str  # "red" | "yellow" | "none" | "abstain"
    headline: str
    facts: Facts
    missing_facts: List[str]
    conditions: List[Condition]
    indexed_laws: List[str]
    closest_sections: List[ClosestSection]
    # The backend also returns extra keys (disclaimer, explanation, language,
    # kb_version, llm_model, timings_ms, dropped_unverified). They are optional
    # for the UI; TypedDict with extras is tolerated at runtime.


class TocEntry(TypedDict):
    part: str
    section_no: str
    heading: str
    page_start: int


class UploadPreview(TypedDict):
    sections_count: int
    toc: List[TocEntry]
    is_new_version_of: Optional[str]


class SubmitUploadResult(TypedDict):
    version_id: int
    status: str  # "pending"


class DiffRow(TypedDict):
    section_no: str
    change: str  # "added" | "removed" | "changed"
    old: str
    new: str


class PendingItem(TypedDict):
    id: int
    type: str  # "new_law" | "new_version" | "trigger"
    title: str
    uploaded_by: str
    uploaded_at: str
    diff: Optional[List[DiffRow]]
    # The backend adds extras (version_id, law_id, law_code, unified_diff,
    # diff_summary, warnings) for versions, and (trigger_id, status,
    # severity_override, note) for trigger proposals.


class TriggerRow(TypedDict):
    id: int
    activity_tag: str
    law_title: str
    section_no: str
    note: str
    status: str  # "pending" | "approved" | "rejected" | "needs_review"


class LawRow(TypedDict):
    id: int
    title: str
    jurisdiction: str  # "Sarawak" | "Federal"
    cap_no: str
    sector: str
    version_label: str
    status: str


class AuditEntry(TypedDict):
    ts: str
    actor: str
    action: str
    target_type: str
    target_id: int
    note: str


# ---------------------------------------------------------------------------
# Backend wiring
# ---------------------------------------------------------------------------
# When USE_MOCK is False we attempt to bind the real implementation from
# services/. Any missing module/function falls back to the mock and raises a
# one-time st.warning so the UI degrades gracefully instead of crashing.
_SERVICES_OK = True
_SERVICES_ERR: Optional[str] = None

if not USE_MOCK:
    try:
        from services import (  # type: ignore  # noqa: F401
            approve as _approve,
            check_action as _check_action,
            get_audit_log as _get_audit_log,
            list_laws as _list_laws,
            list_pending as _list_pending,
            list_triggers as _list_triggers,
            propose_trigger as _propose_trigger,
            reject as _reject,
            submit_upload as _submit_upload,
            upload_preview as _upload_preview,
        )
    except Exception as exc:  # pragma: no cover - defensive demo fallback
        _SERVICES_OK = False
        _SERVICES_ERR = str(exc)


def _warn_once_fallback() -> None:
    """Emit a single warning when services/ was requested but unavailable."""
    import streamlit as st

    if st.session_state.get("_services_warned"):
        return
    st.session_state["_services_warned"] = True
    st.warning(
        "USE_MOCK is False but services/ could not be imported "
        f"({_SERVICES_ERR}). Falling back to mock data."
    )


def _use_services() -> bool:
    """True only when real services were requested AND imported cleanly."""
    if USE_MOCK:
        return False
    if not _SERVICES_OK:
        _warn_once_fallback()
        return False
    return True


# ---------------------------------------------------------------------------
# Public API — views call these. Each delegates to services or mock.
# ---------------------------------------------------------------------------
def check_action(text: str) -> CheckResult:
    if _use_services():
        return _check_action(text)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.check_action(text)


def upload_preview(file_bytes: bytes, meta: dict) -> UploadPreview:
    if _use_services():
        return _upload_preview(file_bytes, meta)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.upload_preview(file_bytes, meta)


def submit_upload(file_bytes: bytes, meta: dict) -> SubmitUploadResult:
    """Save an uploaded law PDF as a PENDING version (not searchable until
    approved). `meta` must include title, jurisdiction, sector, version_label;
    optional: cap_no, published_date, in_force_date, source_url,
    source_authority, instrument_type, language, parse_mode."""
    if _use_services():
        return _submit_upload(file_bytes, meta)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.submit_upload(file_bytes, meta)


def list_pending() -> List[PendingItem]:
    if _use_services():
        return _list_pending()  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.list_pending()


def approve(item_id: int, note: str = "", reviewer: str = "Legal officer") -> None:
    if _use_services():
        return _approve(item_id, note, reviewer)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.approve(item_id, note, reviewer)


def reject(item_id: int, note: str = "", reviewer: str = "Legal officer") -> None:
    if _use_services():
        return _reject(item_id, note, reviewer)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.reject(item_id, note, reviewer)


def list_triggers() -> List[TriggerRow]:
    if _use_services():
        return _list_triggers()  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.list_triggers()


def propose_trigger(activity_tag: str, law_id: int, section_no: str, note: str) -> None:
    if _use_services():
        return _propose_trigger(activity_tag, law_id, section_no, note)  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.propose_trigger(activity_tag, law_id, section_no, note)


def list_laws() -> List[LawRow]:
    if _use_services():
        return _list_laws()  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.list_laws()


def get_audit_log() -> List[AuditEntry]:
    if _use_services():
        return _get_audit_log()  # type: ignore[name-defined]
    from ui import mock_data

    return mock_data.get_audit_log()


def render_highlight(
    pdf_path: str, page: int, rects: List[List[float]]
) -> Optional[bytes]:
    """Render a PDF page to PNG with highlight boxes drawn over `rects`.

    Implemented in the UI layer (PyMuPDF) because it is pure presentation.
    Returns None if the file is missing or cannot be rendered, so callers
    can show a graceful placeholder.
    """
    try:
        import fitz  # PyMuPDF
    except Exception:
        return None

    import os

    if not pdf_path or not os.path.exists(pdf_path):
        return None

    try:
        doc = fitz.open(pdf_path)
        page_index = max(0, page - 1)  # pages in the contract are 1-based
        if page_index >= doc.page_count:
            doc.close()
            return None
        pg = doc[page_index]
        for rect in rects or []:
            try:
                x0, y0, x1, y1 = rect
            except (ValueError, TypeError):
                continue
            annot = pg.add_highlight_annot(fitz.Rect(x0, y0, x1, y1))
            # Matte gold highlight to match the design system.
            annot.set_colors(stroke=(0.78, 0.64, 0.36))
            annot.update()
        pix = pg.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x for crisp display
        png = pix.tobytes("png")
        doc.close()
        return png
    except Exception:
        return None

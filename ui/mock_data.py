"""Mock responses matching the backend contract in ui/backend.py.

All legal text here is SAMPLE / placeholder. We deliberately avoid inventing
real statute wording or real EIA thresholds. Replace with verified wording
from Sarawak LawNet when wiring services/.

Mutable collections (pending queue, triggers, submissions, library) live in
st.session_state so Approve / Reject / Submit visibly change the UI during a
demo.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import List, Optional

import streamlit as st

from ui import sample_pdf

# ---------------------------------------------------------------------------
# Scenario selection (set from the sidebar). Defaults to the red scenario.
# ---------------------------------------------------------------------------
SCENARIOS = ["red", "yellow", "none", "abstain"]


def current_scenario() -> str:
    return st.session_state.get("mock_scenario", "red")


_SAMPLE = "SAMPLE TEXT — replace with verified wording from Sarawak LawNet"


# ---------------------------------------------------------------------------
# check_action — four scenarios (now including related_minutes)
# ---------------------------------------------------------------------------
def _kapit_related_minutes() -> list:
    """Minutes linked to the Land Code s.27 condition in the Kapit scenario."""
    return [
        {
            "id": "M1",
            "title": "Land & Survey coordination meeting (SAMPLE)",
            "meeting_date": "2026-05-14",
            "body": "Legal Department",
            "related_law": "Land Code (SAMPLE)",
            "section_no": "27",
            "quote": f"{_SAMPLE} — the committee noted building approvals for "
            "rural schools follow the standard s.27 route.",
            "page": 1,
            "pdf_path": sample_pdf.sample_pdf_path(),
            "highlight_rects": sample_pdf.SAMPLE_RECTS_27,
            "approved_on": "2026-05-20",
        }
    ]


def _scenario_red() -> dict:
    return {
        "status": "red",
        "headline": "🔴 Stop — 2 mandatory requirement(s) before you proceed",
        "facts": {
            "activity": "Rural school extension (land clearing + new buildings)",
            "location": "Kapit, Sarawak",
            "area_ha": None,
            "land_status": None,
        },
        "missing_facts": [
            "Site area not given; the EIA threshold depends on it.",
        ],
        "conditions": [
            {
                "id": "C1",
                "sector": "Environment",
                "requirement": "Obtain an Environmental Impact Assessment (EIA) "
                "approval before any land clearing begins.",
                "why": "The planned work involves clearing land for new "
                "buildings. Activities of this kind can require an EIA so that "
                "environmental effects are assessed first. Confirm the site "
                "area, which determines whether the mandatory threshold applies.",
                "quote": f"{_SAMPLE} — e.g. the proponent 'shall' submit a "
                "report prior to commencement.",
                "severity": "red",
                "matched_wording": "shall",
                "law_title": "Natural Resources and Environment Ordinance (SAMPLE)",
                "section_no": "11A",
                "page": 4,
                "version_label": "2024 Consolidated (SAMPLE)",
                "in_force_date": "2024-01-01",
                "not_yet_in_force": False,
                "pending_newer_version": {"uploaded": "2026-09-30"},
                "pdf_path": sample_pdf.sample_pdf_path(),
                "highlight_rects": sample_pdf.SAMPLE_RECTS_11A,
            },
            {
                "id": "C2",
                "sector": "Land & Survey",
                "requirement": "Verify the land status and obtain any required "
                "permit for building on the site.",
                "why": "New buildings on a site in Sarawak may need a land use "
                "or occupation permit depending on the land classification. "
                "Confirm the land status with the Land & Survey Department.",
                "quote": f"{_SAMPLE} — e.g. no person 'may' erect a building "
                "without approval.",
                "severity": "yellow",
                "matched_wording": "may",
                "law_title": "Land Code (SAMPLE)",
                "section_no": "27",
                "page": 9,
                "version_label": "2019 Reprint (SAMPLE)",
                "in_force_date": "2019-06-15",
                "not_yet_in_force": False,
                "pending_newer_version": None,
                "pdf_path": sample_pdf.sample_pdf_path(),
                "highlight_rects": sample_pdf.SAMPLE_RECTS_27,
            },
        ],
        "indexed_laws": [],
        "closest_sections": [],
        "related_minutes": _kapit_related_minutes(),
    }


def _scenario_yellow() -> dict:
    return {
        "status": "yellow",
        "headline": "🟡 Review — 2 conditional requirement(s) may apply",
        "facts": {
            "activity": "Office refurbishment (interior works)",
            "location": "Kuching, Sarawak",
            "area_ha": None,
            "land_status": "Government reserve",
        },
        "missing_facts": [
            "Waste disposal method not stated; some options require a permit.",
        ],
        "conditions": [
            {
                "id": "C1",
                "sector": "Environment",
                "requirement": "Check whether construction waste must be "
                "disposed of at a licensed facility.",
                "why": "Refurbishment produces construction waste. Depending on "
                "volume and type, disposal may need to go through a licensed "
                "facility. Confirm the disposal route before works start.",
                "quote": f"{_SAMPLE} — e.g. waste 'may' only be disposed at a "
                "licensed site.",
                "severity": "yellow",
                "matched_wording": "may",
                "law_title": "Environmental Quality Rules (SAMPLE)",
                "section_no": "6",
                "page": 2,
                "version_label": "2022 Edition (SAMPLE)",
                "in_force_date": "2022-03-01",
                "not_yet_in_force": False,
                "pending_newer_version": None,
                "pdf_path": None,
                "highlight_rects": [[72.0, 140.0, 480.0, 168.0]],
            },
            {
                "id": "C2",
                "sector": "Procurement",
                "requirement": "Confirm the refurbishment contract follows the "
                "applicable procurement thresholds.",
                "why": "Government refurbishment spending can fall under "
                "procurement rules. Confirm the contract value against the "
                "relevant tendering threshold before awarding work.",
                "quote": f"{_SAMPLE} — e.g. tenders 'should' be invited above a "
                "stated value.",
                "severity": "info",
                "matched_wording": "should",
                "law_title": "Treasury Instructions (SAMPLE)",
                "section_no": "170",
                "page": 11,
                "version_label": "2020 Circular (SAMPLE)",
                "in_force_date": "2020-01-01",
                "not_yet_in_force": False,
                "pending_newer_version": None,
                "pdf_path": None,
                "highlight_rects": [[72.0, 400.0, 460.0, 430.0]],
            },
        ],
        "indexed_laws": [],
        "closest_sections": [],
        "related_minutes": [],
    }


def _scenario_none() -> dict:
    return {
        "status": "none",
        "headline": "⚪ No requirements found in the 3 laws indexed",
        "facts": {
            "activity": "Internal staff training workshop",
            "location": "Sibu, Sarawak",
            "area_ha": None,
            "land_status": None,
        },
        "missing_facts": [],
        "conditions": [],
        "indexed_laws": [
            "Natural Resources and Environment Ordinance (SAMPLE)",
            "Land Code (SAMPLE)",
            "Treasury Instructions (SAMPLE)",
        ],
        "closest_sections": [],
        "related_minutes": [],
    }


def _scenario_abstain() -> dict:
    return {
        "status": "abstain",
        "headline": "⚪ No confident answer — please check with a legal officer",
        "facts": {
            "activity": "Unclear / mixed activity description",
            "location": "Not clearly stated",
            "area_ha": None,
            "land_status": None,
        },
        "missing_facts": [
            "The action description was too vague to match reliably.",
        ],
        "conditions": [],
        "indexed_laws": [],
        "closest_sections": [
            {
                "law_title": "Natural Resources and Environment Ordinance (SAMPLE)",
                "section_no": "11A",
                "heading": "Prescribed activities",
                "page": 4,
            },
            {
                "law_title": "Land Code (SAMPLE)",
                "section_no": "27",
                "heading": "Building approvals",
                "page": 9,
            },
            {
                "law_title": "Environmental Quality Rules (SAMPLE)",
                "section_no": "6",
                "heading": "Waste disposal",
                "page": 2,
            },
        ],
        "related_minutes": [],
    }


_SCENARIO_BUILDERS = {
    "red": _scenario_red,
    "yellow": _scenario_yellow,
    "none": _scenario_none,
    "abstain": _scenario_abstain,
}


def check_action(text: str) -> dict:
    """Return a mock CheckResult for the scenario selected in the sidebar."""
    builder = _SCENARIO_BUILDERS.get(current_scenario(), _scenario_red)
    return builder()


# ---------------------------------------------------------------------------
# Upload preview (kept for the Submit-a-change preview step)
# ---------------------------------------------------------------------------
def upload_preview(file_bytes: bytes, meta: dict) -> dict:
    title = (meta or {}).get("title", "").strip()
    is_new_version_of = "Land Code (SAMPLE)" if "land code" in title.lower() else None
    return {
        "sections_count": 3,
        "toc": [
            {"part": "Part I", "section_no": "1", "heading": "Short title "
             "(SAMPLE)", "page_start": 1},
            {"part": "Part II", "section_no": "11A", "heading": "Prescribed "
             "activities (SAMPLE)", "page_start": 4},
            {"part": "Part III", "section_no": "27", "heading": "Building "
             "approvals (SAMPLE)", "page_start": 9},
        ],
        "is_new_version_of": is_new_version_of,
    }


# ---------------------------------------------------------------------------
# Submit a change (new_law | new_version | minutes)
# ---------------------------------------------------------------------------
_TYPE_TITLES = {
    "new_law": "New law",
    "new_version": "New version",
    "minutes": "Meeting minutes",
}


def submit_change(kind: str, file_bytes: bytes, meta: dict,
                  submitted_by_role: str) -> dict:
    """Create a pending submission. Returns {"id", "status": "pending"}."""
    state = _state()
    new_id = _next_id("submission")
    meta = meta or {}
    title = meta.get("title") or meta.get("meeting_title") or "Untitled (SAMPLE)"
    related_laws = meta.get("related_laws") or (
        [meta["law_title"]] if meta.get("law_title") else []
    )
    summary = (
        meta.get("summary")
        or meta.get("what_changed")
        or meta.get("decision_summary")
        or ""
    )
    item = {
        "id": new_id,
        "type": kind,
        "title": title,
        "uploaded_by": f"{submitted_by_role.lower()}@demo",
        "submitted_by_role": submitted_by_role,
        "uploaded_at": _now(),
        "related_laws": related_laws,
        "summary": summary,
        "diff": meta.get("diff"),
        "meta": copy.deepcopy(meta),
    }
    state["pending"].append(item)
    # Mirror into "my submissions" for the submitting role.
    state["submissions"].append(
        {
            "id": new_id,
            "type": kind,
            "title": title,
            "submitted_at": item["uploaded_at"],
            "status": "pending",
            "review_note": "",
            "submitted_by_role": submitted_by_role,
        }
    )
    _audit("submit_change", kind, new_id,
           f"Submitted {_TYPE_TITLES.get(kind, kind)}: '{title}' for review",
           actor=item["uploaded_by"])
    return {"id": new_id, "status": "pending"}


# Backwards-compatible alias: submit_upload -> submit_change(new_law/new_version).
def submit_upload(file_bytes: bytes, meta: dict) -> dict:
    kind = "new_version" if (meta or {}).get("is_new_version_of") else "new_law"
    res = submit_change(kind, file_bytes, meta or {}, "Officer")
    return {"version_id": res["id"], "status": res["status"]}


# ---------------------------------------------------------------------------
# Session-state-backed mutable store
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _seed() -> dict:
    """Initial mock state. Deep-copied into session_state on first use."""
    return {
        "counters": {"submission": 100, "trigger": 400, "law": 20, "minutes": 60},
        "pending": [
            {
                "id": 1,
                "type": "new_version",
                "title": "Land Code (SAMPLE) — 2026 Amendment",
                "uploaded_by": "officer@demo",
                "submitted_by_role": "Officer",
                "uploaded_at": "2026-09-30 10:15",
                "related_laws": ["Land Code (SAMPLE)"],
                "summary": "Building approval becomes mandatory; adds a native "
                "land notice subsection (SAMPLE).",
                "diff": [
                    {
                        "section_no": "27",
                        "change": "changed",
                        "old": "SAMPLE old wording — building approval optional.",
                        "new": "SAMPLE new wording — building approval required.",
                    },
                    {
                        "section_no": "27A",
                        "change": "added",
                        "old": "",
                        "new": "SAMPLE — new subsection on native land notice.",
                    },
                ],
                "meta": {},
            },
            {
                "id": 3,
                "type": "minutes",
                "title": "Native Rights working group (SAMPLE)",
                "uploaded_by": "officer@demo",
                "submitted_by_role": "Officer",
                "uploaded_at": "2026-10-03 09:20",
                "related_laws": ["Land Code (SAMPLE)"],
                "summary": "Group agreed draft guidance on native land notices "
                "ahead of the s.27A amendment (SAMPLE).",
                "diff": None,
                "meta": {"meeting_date": "2026-10-01",
                         "body": "Legal Department"},
            },
        ],
        "triggers": [
            {"id": 401, "activity_tag": "land_clearing",
             "law_title": "Natural Resources and Environment Ordinance (SAMPLE)",
             "section_no": "11A", "note": "Clearing land can trigger EIA (SAMPLE).",
             "status": "approved"},
            {"id": 402, "activity_tag": "construction",
             "law_title": "Land Code (SAMPLE)", "section_no": "27",
             "note": "New buildings need approval (SAMPLE).", "status": "approved"},
            {"id": 403, "activity_tag": "native_land",
             "law_title": "Land Code (SAMPLE)", "section_no": "27A",
             "note": "Native customary rights notice (SAMPLE).",
             "status": "needs_review"},
            {"id": 404, "activity_tag": "waste_disposal",
             "law_title": "Environmental Quality Rules (SAMPLE)", "section_no": "6",
             "note": "Waste disposal routing (SAMPLE).", "status": "pending"},
        ],
        "laws": [
            {"id": 10,
             "title": "Natural Resources and Environment Ordinance (SAMPLE)",
             "jurisdiction": "Sarawak", "cap_no": "Cap. 84 (SAMPLE)",
             "sector": "Environment", "version_label": "2024 Consolidated (SAMPLE)",
             "status": "approved"},
            {"id": 11, "title": "Land Code (SAMPLE)", "jurisdiction": "Sarawak",
             "cap_no": "Cap. 81 (SAMPLE)", "sector": "Land",
             "version_label": "2019 Reprint (SAMPLE)", "status": "approved"},
            {"id": 12, "title": "Treasury Instructions (SAMPLE)",
             "jurisdiction": "Federal", "cap_no": "T.I. (SAMPLE)",
             "sector": "Procurement", "version_label": "2020 Circular (SAMPLE)",
             "status": "approved"},
        ],
        # Approved meeting minutes (library + AI results draw from these).
        "minutes": [
            {"id": 51, "title": "Land & Survey coordination meeting (SAMPLE)",
             "meeting_date": "2026-05-14", "body": "Legal Department",
             "related_laws": ["Land Code (SAMPLE)"], "section_no": "27",
             "summary": "Confirmed building approvals for rural schools follow "
             "the standard s.27 route (SAMPLE).",
             "approved_on": "2026-05-20", "status": "approved",
             "pdf_path": None},
            {"id": 52, "title": "Environment compliance briefing (SAMPLE)",
             "meeting_date": "2026-07-02", "body": "Environment Department",
             "related_laws": ["Natural Resources and Environment Ordinance (SAMPLE)"],
             "section_no": "11A",
             "summary": "Reviewed EIA submission steps for departmental projects "
             "(SAMPLE).",
             "approved_on": "2026-07-08", "status": "approved",
             "pdf_path": None},
        ],
        "submissions": [
            {"id": 1, "type": "new_version",
             "title": "Land Code (SAMPLE) — 2026 Amendment",
             "submitted_at": "2026-09-30 10:15", "status": "pending",
             "review_note": "", "submitted_by_role": "Officer"},
            {"id": 3, "type": "minutes",
             "title": "Native Rights working group (SAMPLE)",
             "submitted_at": "2026-10-03 09:20", "status": "pending",
             "review_note": "", "submitted_by_role": "Officer"},
        ],
        "audit": [
            {"ts": "2026-10-03 09:21", "actor": "officer@demo",
             "action": "submit_change", "target_type": "minutes",
             "target_id": 3, "note": "Submitted Meeting minutes: Native Rights "
             "working group (SAMPLE)."},
            {"ts": "2026-09-30 10:16", "actor": "officer@demo",
             "action": "submit_change", "target_type": "new_version",
             "target_id": 1, "note": "Submitted New version: Land Code 2026 "
             "Amendment (SAMPLE)."},
            {"ts": "2026-07-08 11:00", "actor": "admin@demo",
             "action": "approve", "target_type": "minutes",
             "target_id": 52, "note": "Approved Environment briefing minutes (SAMPLE)."},
            {"ts": "2026-05-20 16:30", "actor": "admin@demo",
             "action": "approve", "target_type": "minutes",
             "target_id": 51, "note": "Approved Land & Survey minutes (SAMPLE)."},
            {"ts": "2026-09-20 16:30", "actor": "admin@demo",
             "action": "approve", "target_type": "law",
             "target_id": 12, "note": "Approved Treasury Instructions (SAMPLE)."},
            {"ts": "2026-09-10 08:45", "actor": "admin@demo",
             "action": "approve", "target_type": "law",
             "target_id": 10, "note": "Approved NREO (SAMPLE)."},
        ],
    }


def _state() -> dict:
    if "mock_state" not in st.session_state:
        st.session_state["mock_state"] = copy.deepcopy(_seed())
    return st.session_state["mock_state"]


def _next_id(kind: str) -> int:
    state = _state()
    state["counters"].setdefault(kind, 0)
    state["counters"][kind] += 1
    return state["counters"][kind]


def _audit(action: str, target_type: str, target_id: int, note: str,
           actor: str = "admin@demo") -> None:
    _state()["audit"].insert(
        0,
        {"ts": _now(), "actor": actor, "action": action,
         "target_type": target_type, "target_id": target_id, "note": note},
    )


# ---------------------------------------------------------------------------
# Review queue
# ---------------------------------------------------------------------------
def list_pending() -> List[dict]:
    return copy.deepcopy(_state()["pending"])


def _pop_pending(item_id: int) -> Optional[dict]:
    state = _state()
    for i, item in enumerate(state["pending"]):
        if item["id"] == item_id:
            return state["pending"].pop(i)
    return None


def _set_submission_status(item_id: int, status: str, note: str) -> None:
    for sub in _state()["submissions"]:
        if sub["id"] == item_id:
            sub["status"] = status
            sub["review_note"] = note
            return


def _promote_to_library(item: dict) -> None:
    """On approval, make a law/version/minutes item appear in the library."""
    state = _state()
    kind = item.get("type")
    if kind in ("new_law", "new_version"):
        meta = item.get("meta") or {}
        state["laws"].append(
            {
                "id": _next_id("law"),
                "title": item.get("title", "Untitled (SAMPLE)"),
                "jurisdiction": meta.get("jurisdiction", "Sarawak"),
                "cap_no": meta.get("cap_no", "(SAMPLE)"),
                "sector": meta.get("sector", "Other"),
                "version_label": meta.get("version_label", "(SAMPLE)"),
                "status": "approved",
            }
        )
    elif kind == "minutes":
        meta = item.get("meta") or {}
        state["minutes"].append(
            {
                "id": _next_id("minutes"),
                "title": item.get("title", "Untitled minutes (SAMPLE)"),
                "meeting_date": meta.get("meeting_date", ""),
                "body": meta.get("body", ""),
                "related_laws": item.get("related_laws", []),
                "section_no": meta.get("section_no"),
                "summary": item.get("summary", ""),
                "approved_on": _now()[:10],
                "status": "approved",
                "pdf_path": None,
            }
        )


def approve(item_id: int, note: str, reviewer_role: str = "Admin") -> None:
    item = _pop_pending(item_id)
    if item is None:
        return
    # Self-approval note when the reviewer submitted the item themselves.
    self_approved = item.get("submitted_by_role") == reviewer_role
    suffix = " (self-approved)" if self_approved else ""
    _promote_to_library(item)
    _set_submission_status(item_id, "approved", note or "")
    _audit("approve", item.get("type", "item"), item_id,
           f"Approved — now citable{suffix}. {note}".strip(),
           actor=f"{reviewer_role.lower()}@demo")


def reject(item_id: int, note: str, reviewer_role: str = "Admin") -> None:
    item = _pop_pending(item_id)
    if item is None:
        return
    _set_submission_status(item_id, "rejected", note or "")
    _audit("reject", item.get("type", "item"), item_id,
           f"Rejected. {note}".strip(), actor=f"{reviewer_role.lower()}@demo")


# ---------------------------------------------------------------------------
# Library (approved only) & my submissions
# ---------------------------------------------------------------------------
def list_library(kind: str) -> List[dict]:
    state = _state()
    if kind == "laws":
        return [copy.deepcopy(x) for x in state["laws"]
                if x.get("status") == "approved"]
    if kind == "minutes":
        return [copy.deepcopy(x) for x in state["minutes"]
                if x.get("status") == "approved"]
    return []


def list_my_submissions(role: str) -> List[dict]:
    # Prototype: show all submissions (single-user demo). Return newest first.
    subs = copy.deepcopy(_state()["submissions"])
    return list(reversed(subs))


# ---------------------------------------------------------------------------
# Trigger map
# ---------------------------------------------------------------------------
def list_triggers() -> List[dict]:
    return copy.deepcopy(_state()["triggers"])


def propose_trigger(activity_tag: str, law_id: int, section_no: str,
                    note: str) -> None:
    state = _state()
    new_id = _next_id("trigger")
    law_title = next(
        (law["title"] for law in state["laws"] if law["id"] == law_id),
        "Unknown law (SAMPLE)",
    )
    state["triggers"].append(
        {"id": new_id, "activity_tag": activity_tag, "law_title": law_title,
         "section_no": section_no, "note": note or "(no note)",
         "status": "pending"}
    )
    _audit("propose_trigger", "trigger", new_id,
           f"Proposed {activity_tag} → {law_title} s.{section_no}")


# ---------------------------------------------------------------------------
# Laws & audit
# ---------------------------------------------------------------------------
def list_laws() -> List[dict]:
    return copy.deepcopy(_state()["laws"])


def get_audit_log() -> List[dict]:
    return copy.deepcopy(_state()["audit"])

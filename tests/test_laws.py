"""Uploads, versions and the approval gate (human in the loop)."""
import pytest

from conftest import NREO_PDF, make_pdf, modified_nreo, synthetic_law
from services.config import TRIGGER_ID_OFFSET
from services.schemas import ConditionsOut, PlanOut

NREO_META = {"title": "Natural Resources and Environment Ordinance", "jurisdiction": "Sarawak",
             "sector": "Environment (Natural Resources and Environment Board)", "version_label": "Test reprint 2026",
             "cap_no": "Cap. 84", "uploaded_by": "Encik Lee"}
NEW_LAW_META = {"title": "Drain Protection Ordinance", "jurisdiction": "Sarawak", "sector": "Drainage (test)",
                "version_label": "Test 2026", "uploaded_by": "Encik Lee"}


def test_bad_and_scanned_files(svc):
    with pytest.raises(svc.ServiceError) as e:
        svc.upload_preview(b"hello", NEW_LAW_META)
    assert e.value.code == "bad_file"
    with pytest.raises(svc.ServiceError) as e:
        svc.upload_preview(make_pdf([[], []]), NEW_LAW_META)
    assert e.value.code == "scanned_pdf"
    with pytest.raises(svc.ServiceError) as e:
        svc.upload_preview(NREO_PDF.read_bytes(), NREO_META)
    assert e.value.code == "duplicate_file"
    with pytest.raises(svc.ServiceError) as e:
        svc.submit_upload(synthetic_law("x"), {"title": "No sector"})
    assert e.value.code == "validation"


def test_preview_saves_nothing(svc):
    p = svc.upload_preview(modified_nreo(), NREO_META)
    assert p["is_new_version_of"] == "Natural Resources and Environment Ordinance"
    assert p["sections_count"] >= 40 and {"part", "section_no", "heading", "page_start"} <= p["toc"][0].keys()
    assert svc.list_pending() == []


def test_new_version_flow(svc):
    res = svc.submit_upload(modified_nreo(), NREO_META)
    assert res["status"] == "pending" and res["is_new_law"] is False
    assert res["diff_summary"]["changed"] >= 1
    item = next(i for i in svc.list_pending() if i["id"] == res["version_id"])
    assert item["type"] == "new_version"
    assert any(d["section_no"] == "11A" and d["change"] == "changed" for d in item["diff"])

    # While pending, workers see a warning but answers still come from the approved version.
    r = svc.check_action("Council will build a municipal waste recycling facility by the river.")
    c = next(c for c in r["conditions"] if c["section_no"] == "11A")
    assert c["pending_newer_version"] is not None and c["version_label"] == "LawNet reprint 2024"

    kb_before = svc.health()["kb_version"]
    svc.approve(res["version_id"], "Checked against the gazette", reviewer="Encik Lee")
    assert svc.health()["kb_version"] > kb_before
    laws = {l["title"]: l for l in svc.list_laws()}
    assert laws["Natural Resources and Environment Ordinance"]["version_label"] == "Test reprint 2026"
    flagged = [t for t in svc.list_triggers() if t["status"] == "needs_review"]
    assert flagged and all(t["section_no"] == "11A" for t in flagged)
    r = svc.check_action("Council will build a municipal waste recycling facility by the river.")
    c = next(c for c in r["conditions"] if c["section_no"] == "11A")
    assert c["version_label"] == "Test reprint 2026" and c["rule_needs_review"] is True
    actions = [a["action"] for a in svc.get_audit_log()]
    assert "approve_version" in actions and "flag_triggers_needs_review" in actions
    with pytest.raises(svc.ServiceError) as e:
        svc.approve(res["version_id"], "again")
    assert e.value.code == "wrong_state"


def test_new_law_is_invisible_until_approved(svc, monkeypatch):
    res = svc.submit_upload(synthetic_law("Drain Protection Ordinance"), NEW_LAW_META)
    assert res["is_new_law"] is True
    item = next(i for i in svc.list_pending() if i["id"] == res["version_id"])
    assert item["type"] == "new_law" and item["diff"] is None
    law = next(l for l in svc.list_laws() if l["title"] == "Drain Protection Ordinance")
    assert law["status"] == "pending"
    from services import retrieval
    from services import db
    with db.transaction() as conn:
        idx = retrieval.get_index(conn)
        assert law["code"] not in idx.by_code                       # not searchable yet
    svc.reject(res["version_id"], "Wrong file")
    with db.transaction() as conn:
        assert law["code"] not in retrieval.get_index(conn).by_code


def test_meeting_minutes_capped_at_yellow(svc, monkeypatch):
    meta = dict(NEW_LAW_META, title="Drainage Committee Minutes 3/2026", instrument_type="Meeting minutes")
    res = svc.submit_upload(synthetic_law("Drainage Committee Minutes"), meta)
    svc.approve(res["version_id"], "ok")
    code = next(l["code"] for l in svc.list_laws() if l["title"] == meta["title"])
    plan = {"tags": ["waste_disposal"], "laws": [code], "sections": [{"key": f"{code}:2"}]}
    cond = {"conditions": [{"key": f"{code}:2", "requirement": "Get a permit.", "why": "Minutes say so.",
                            "quote": "No person shall discharge any drain waste into a public drain without a permit"}]}

    def fake(name, system, user, schema):
        return (PlanOut if name == "plan" else ConditionsOut).model_validate(plan if name == "plan" else cond), "fake"
    monkeypatch.setattr("services.pipeline.call_llm_json", fake)
    r = svc.check_action("Council will discharge drain waste during the works.")
    c = next(c for c in r["conditions"] if c["law_title"] == meta["title"])
    assert c["severity"] == "yellow" and "internal document" in c["matched_wording"]


def test_trigger_rules(svc):
    with pytest.raises(svc.ServiceError):
        svc.propose_trigger("not_a_tag", 1, "11A", "x")
    with pytest.raises(svc.ServiceError):
        svc.propose_trigger("water_body", 1, "999", "x")
    nreo_id = next(l["id"] for l in svc.list_laws() if l["title"].startswith("Natural"))
    svc.propose_trigger("road_works", nreo_id, "s. 11a", "test rule", severity_override="yellow", proposed_by="Encik Lee")
    item = next(i for i in svc.list_pending() if i["type"] == "trigger")
    assert item["id"] > TRIGGER_ID_OFFSET and item["diff"] is None
    svc.approve(item["id"], "ok", reviewer="Encik Lee")
    t = next(t for t in svc.list_triggers() if t["note"] == "test rule")
    assert t["status"] == "approved" and t["section_no"] == "11A"
    with pytest.raises(svc.ServiceError) as e:
        svc.reject(TRIGGER_ID_OFFSET + 99999, "x")
    assert e.value.code == "not_found"

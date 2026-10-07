"""check_action() and friends return exactly what ui/backend.py expects."""
import pytest

from services.schemas import ConditionsOut, PlanOut

ACTION = ("Kapit District Council will build a municipal waste recycling and storage facility "
          "on a 3-hectare site beside the Rejang River.")
TOP_KEYS = {"status", "headline", "facts", "missing_facts", "conditions", "indexed_laws", "closest_sections"}
COND_KEYS = {"id", "sector", "requirement", "why", "quote", "severity", "matched_wording", "law_title", "section_no",
             "page", "version_label", "in_force_date", "not_yet_in_force", "pending_newer_version", "pdf_path",
             "highlight_rects"}


def test_check_action_contract(svc):
    r = svc.check_action(ACTION)
    assert TOP_KEYS <= r.keys()
    assert set(r["facts"]) == {"activity", "location", "area_ha", "land_status"}
    assert r["facts"]["area_ha"] == 3.0
    assert r["status"] == "red"
    assert r["headline"] == "🔴 Stop — 1 mandatory requirement(s) before you proceed · 1 more to check"
    assert r["dropped_unverified"] == 1                      # made-up quote dropped; invented key ignored
    assert [c["id"] for c in r["conditions"]] == ["C1", "C2"]
    for c in r["conditions"]:
        assert COND_KEYS <= c.keys()
    red, yellow = r["conditions"]
    assert (red["section_no"], red["severity"], red["page"]) == ("11A", "red", 25)
    assert red["matched_wording"] == "rule set by legal officer" and red["highlight_rects"]
    assert (yellow["section_no"], yellow["severity"]) == ("5", "yellow")
    assert red["pending_newer_version"] is None and red["not_yet_in_force"] is False
    png = svc.render_highlight(red["pdf_path"], red["page"], red["highlight_rects"])
    assert png.startswith(b"\x89PNG")
    assert len(r["indexed_laws"]) == 2


def _fake(plan: dict, conditions: dict | None):
    def call(name, system, user, schema):
        if name == "plan":
            return PlanOut.model_validate(plan), "fake"
        if conditions is None:
            raise AssertionError("conditions call should not happen")
        return ConditionsOut.model_validate(conditions), "fake"
    return call


def test_none_path(svc, monkeypatch):
    monkeypatch.setattr("services.pipeline.call_llm_json",
                        _fake({"tags": ["procurement"], "sections": [], "laws": []}, {"conditions": []}))
    r = svc.check_action("Purchase of 50 laptops for the district office.")
    assert r["status"] == "none" and r["conditions"] == []
    assert r["headline"].startswith("⚪ No requirements found in the 2 laws indexed")


def test_strongest_trigger_override_wins(svc, monkeypatch):
    plan = {"tags": ["water_body", "waste_disposal", "construction"], "laws": [], "sections": []}
    cond = {"conditions": [{"key": "NREO:11A", "requirement": "r", "why": "w",
                            "quote": "No person shall carry out or commence any preparatory work relating to any activity"}]}
    monkeypatch.setattr("services.pipeline.call_llm_json", _fake(plan, cond))
    r = svc.check_action("Council will build a waste facility beside the river.")
    c = r["conditions"][0]
    assert c["severity"] == "red" and c["matched_wording"] == "rule set by legal officer"


def test_abstain_path(svc, monkeypatch):
    monkeypatch.setattr("services.pipeline.call_llm_json",
                        _fake({"missing_facts": ["what the project is"], "tags": [], "sections": [], "laws": []}, None))
    r = svc.check_action("Something next week maybe.")
    assert r["status"] == "abstain"
    assert "what the project is" in r["headline"]


def test_malay_question_gets_malay_headline(svc):
    r = svc.check_action("Majlis Daerah Kapit akan membina kemudahan kitar semula sisa di tepi Sungai Rajang.")
    assert r["language"] == "ms" and r["headline"].startswith("🔴 Henti")


def test_validation_errors(svc):
    with pytest.raises(svc.ServiceError) as e:
        svc.check_action("hi")
    assert e.value.code == "validation"


def test_llm_unavailable(svc, monkeypatch):
    from services.llm import LLMError

    def boom(*a, **k):
        raise LLMError("503 high demand")
    monkeypatch.setattr("services.pipeline.call_llm_json", boom)
    with pytest.raises(svc.ServiceError) as e:
        svc.check_action(ACTION)
    assert e.value.code == "llm_unavailable"


def test_catalogue_functions(svc):
    laws = svc.list_laws()
    assert {l["title"] for l in laws} == {"Natural Resources and Environment Ordinance", "Land Code"}
    assert {"id", "title", "jurisdiction", "cap_no", "sector", "version_label", "status"} <= laws[0].keys()
    trig = svc.list_triggers()
    assert {"id", "activity_tag", "law_title", "section_no", "note", "status"} <= trig[0].keys()
    log = svc.get_audit_log()
    assert log and isinstance(log[0]["target_id"], int)
    assert svc.health()["llm_provider"] == "fake"

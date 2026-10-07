"""check_action(): plan call -> structure-aware retrieval -> conditions call -> verify -> severity -> result.

The LLM reads, picks and quotes. Code verifies every quote, sets severity and writes the headline.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date

from . import db, laws, retrieval
from .config import (LEGAL_INSTRUMENTS, MAX_ACTION_CHARS, MAX_CANDIDATES, MAX_SECTION_CHARS, MIN_ACTION_CHARS,
                     TOC_LAWS, TOC_PICKS, XREF_LIMIT, get_settings, resolve_path, tags)
from .errors import ServiceError
from .llm import LLMError, call_llm_json
from .prompts import conditions_system, conditions_user, plan_system, plan_user
from .schemas import ConditionsOut, PlanOut
from .severity import classify, status_and_headline
from .verify import clean_quote, find_highlight, normalize, sentence_around, verify_quote

log = logging.getLogger("services.pipeline")
DISCLAIMER = {
    "en": "A reference before you act, not a legal judgement. Confirm with your legal officer.",
    "ms": "Rujukan sebelum bertindak, bukan keputusan undang-undang. Sahkan dengan pegawai undang-undang anda.",
}
_ORDER = {"red": 0, "yellow": 1, "info": 2}


def _ms() -> float:
    return time.perf_counter() * 1000


def run_check(text: str) -> dict:
    t_start = _ms()
    text = (text or "").strip()
    if not MIN_ACTION_CHARS <= len(text) <= MAX_ACTION_CHARS:
        raise ServiceError("validation", f"Please describe the planned action in {MIN_ACTION_CHARS}–"
                                         f"{MAX_ACTION_CHARS} characters.")
    s = get_settings()
    lang = retrieval.query_language(text)
    language_name = "Bahasa Melayu" if lang == "ms" else "English"
    timings: dict[str, int] = {}
    conn = db.connect()
    try:
        idx = retrieval.get_index(conn)
        t = _ms()
        hits = retrieval.fts(conn, idx, text, limit=80)
        shown = retrieval.top_laws(idx, hits, lang, TOC_LAWS)
        catalog = retrieval.catalog_lines(idx, lang)
        toc = retrieval.toc_block(idx, shown, hits)
        timings["retrieval"] = round(_ms() - t)

        t = _ms()
        try:
            plan, model_plan = call_llm_json("plan", plan_system(language_name),
                                             plan_user(text, tags(), catalog, toc), PlanOut)
        except LLMError as e:
            log.error("plan call failed: %s", e)
            raise ServiceError("llm_unavailable", "The AI service is busy or unavailable. Please try again in a minute.") from None
        timings["plan_llm"] = round(_ms() - t)

        valid_tags = [x for x in plan.tags if x in tags()]
        toc_keys = [k for k in (retrieval.canon_key(idx, p.key) for p in plan.sections) if k][:TOC_PICKS]
        law_codes = [c for c in (retrieval.canon_code(idx, x) for x in plan.laws) if c][:3]
        plan_empty = not valid_tags and not toc_keys and not law_codes

        trig = retrieval.triggers_for(conn, idx, valid_tags, lang)
        picked_law_hits: list[str] = []
        for code in law_codes:
            picked_law_hits += retrieval.fts(conn, idx, text, limit=3, law_ids=[idx.by_code[code].id])
        candidates, sources = retrieval.merge(idx, [
            ("trigger_map", [x["key"] for x in trig]),
            ("toc", toc_keys),
            ("law_pick", picked_law_hits),
            ("keyword", hits[:s.keyword_k]),
        ], lang, MAX_CANDIDATES)
        rows = retrieval.section_rows(conn, idx, candidates)
        if s.xrefs and len(candidates) < MAX_CANDIDATES:
            extra = retrieval.xrefs(idx, rows, candidates, min(XREF_LIMIT, MAX_CANDIDATES - len(candidates)))
            for key in extra:
                candidates.append(key)
                sources[key] = ["cross_reference"]
            rows.update(retrieval.section_rows(conn, idx, extra))

        conditions: list[dict] = []
        dropped = 0
        explanation = ""
        model_cond = None
        if not plan_empty and candidates:
            payload = []
            for key in candidates:
                sec = idx.sections[key]
                body = rows[key]["text"]
                if len(body) > MAX_SECTION_CHARS:
                    body = body[:MAX_SECTION_CHARS] + " […truncated]"
                payload.append((key, idx.laws[sec.law_id].title, sec.heading, body))
            t = _ms()
            try:
                cond, model_cond = call_llm_json("conditions", conditions_system(language_name),
                                                 conditions_user(text, plan.facts.model_dump(), payload), ConditionsOut)
            except LLMError as e:
                log.error("conditions call failed: %s", e)
                raise ServiceError("llm_unavailable", "The AI service is busy or unavailable. Please try again in a minute.") from None
            timings["conditions_llm"] = round(_ms() - t)
            explanation = cond.explanation

            t = _ms()
            trig_by_key = _merge_triggers(trig)
            seen: set[tuple[str, str]] = set()
            for c in cond.conditions:
                key = retrieval.canon_key(idx, c.key)
                if key is None or key not in rows:
                    continue                                   # invented or non-candidate key
                if not verify_quote(c.quote, rows[key]["text"]):
                    dropped += 1
                    continue
                sig = (key, normalize(clean_quote(c.quote)))
                if sig in seen:
                    continue
                seen.add(sig)
                conditions.append(_condition(conn, idx, key, rows[key], c, trig_by_key.get(key),
                                             sources.get(key, []), s.highlight))
            timings["verify"] = round(_ms() - t)
        conditions.sort(key=lambda x: _ORDER[x["severity"]])
        for i, c in enumerate(conditions, 1):
            c["id"] = f"C{i}"

        red = sum(c["severity"] == "red" for c in conditions)
        yellow = sum(c["severity"] == "yellow" for c in conditions)
        n_laws = len(idx.groups)
        status, headline = status_and_headline(red, yellow, plan_empty, n_laws, plan.missing_facts, lang)
        indexed = [f"{retrieval.preferred_law(idx, g[0], lang).title} ({retrieval.preferred_law(idx, g[0], lang).version_label})"
                   for g in sorted(idx.groups.values(), key=lambda g: retrieval.preferred_law(idx, g[0], lang).title)]
        closest = []
        if status == "abstain":
            for key in hits[:3]:
                sec = idx.sections[key]
                closest.append({"law_title": idx.laws[sec.law_id].title, "section_no": sec.section_no,
                                "heading": sec.heading or "", "page": sec.page_start, "section_key": key})
    finally:
        conn.close()

    timings["total"] = round(_ms() - t_start)
    return {
        "status": status,
        "headline": headline,
        "facts": {"activity": plan.facts.activity, "location": plan.facts.location,
                  "area_ha": plan.facts.area_ha, "land_status": plan.facts.land_status},
        "missing_facts": plan.missing_facts,
        "conditions": conditions,
        "indexed_laws": indexed,
        "closest_sections": closest,
        # [extra]
        "dropped_unverified": dropped,
        "kb_version": idx.kb,
        "llm_provider": s.llm_provider,
        "llm_model": model_cond or model_plan,
        "language": lang,
        "explanation": explanation,
        "disclaimer": DISCLAIMER[lang],
        "timings_ms": timings,
    }


def _merge_triggers(trig: list[dict]) -> dict[str, dict]:
    """Several rules can point at one section (NREO s.11A has six). The strongest override wins;
    the rule counts as needing review if any of them does."""
    rank = {"red": 2, "yellow": 1, None: 0}
    out: dict[str, dict] = {}
    for t in trig:
        cur = out.get(t["key"])
        if cur is None:
            out[t["key"]] = dict(t)
            continue
        if rank[t["severity_override"]] > rank[cur["severity_override"]]:
            cur["severity_override"] = t["severity_override"]
        if t["status"] == "needs_review":
            cur["status"] = "needs_review"
    return out


def _condition(conn, idx, key: str, row, c, trig: dict | None, sources: list[str], highlight: bool) -> dict:
    sec = idx.sections[key]
    law = idx.laws[sec.law_id]
    pdf = str(resolve_path(law.file_path))
    page, rects = find_highlight(pdf, sec.page_start, sec.page_end, c.quote) if highlight else (sec.page_start, [])
    severity, wording = classify(sentence_around(c.quote, row["text"]), trig["severity_override"] if trig else None)
    if law.instrument_type not in LEGAL_INSTRUMENTS and severity == "red":
        severity, wording = "yellow", f"{wording} (internal document, not law)"
    in_force = law.in_force_date
    return {
        "id": "",
        "sector": law.sector,
        "requirement": c.requirement.strip(),
        "why": c.why.strip(),
        "quote": clean_quote(c.quote),
        "severity": severity,
        "matched_wording": wording,
        "law_title": law.title,
        "section_no": sec.section_no,
        "page": page,
        "version_label": law.version_label,
        "in_force_date": in_force,
        "not_yet_in_force": bool(in_force and in_force > date.today().isoformat()),
        "pending_newer_version": laws.pending_version_for(conn, law.id),
        "pdf_path": pdf,
        "highlight_rects": rects,
        # [extra]
        "subsection": c.subsection,
        "heading": sec.heading,
        "section_key": key,
        "cap_no": law.cap_no,
        "law_code": law.code,
        "instrument_type": law.instrument_type,
        "language": law.language,
        "source_authority": law.source_authority,
        "amend_notes": json.loads(row["amend_notes"] or "[]"),
        "highlight": bool(rects),
        "rule_needs_review": bool(trig and trig["status"] == "needs_review"),
        "sources": sources,
    }

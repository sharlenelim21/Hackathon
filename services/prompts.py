"""The two LLM prompts. The model only reads, picks and quotes; code decides everything else."""
from __future__ import annotations

import json

PLAN_SYSTEM = """You help Sarawak government officers see which laws from OTHER sectors a planned action may trigger.
You receive the officer's planned ACTION, an allowed TAG LIST, a LAW CATALOG (every law in the knowledge base) and a
TABLE OF CONTENTS for the laws most likely to be relevant (section keys and headings only).
Return a json object with exactly these fields:
{"facts": {"activity": string|null, "location": string|null, "area_ha": number|null, "land_status": string|null},
 "missing_facts": [string],
 "tags": [string],
 "laws": [string],
 "sections": [{"key": string, "reason": string}]}
Rules:
- "tags": only values from TAG LIST that describe the action.
- "laws": up to 3 law codes from LAW CATALOG that may apply, including laws whose table of contents is not shown.
- "sections": at most 5 keys copied exactly from the TABLE OF CONTENTS; an empty list if none is relevant.
- "missing_facts": facts that would change which laws apply (e.g. site area, whether the land is native customary
  rights land). Write them in {language}.
- If the action is unclear or unrelated to any law, return empty "tags", "laws" and "sections".
- Do not decide whether the action is legal. Output json only."""

CONDITIONS_SYSTEM = """You extract compliance conditions for a Sarawak government officer from law sections.
You receive the planned ACTION, known FACTS, and SECTIONS (each with a key, law, heading and text).
Return a json object:
{"conditions": [{"key": string, "subsection": string|null, "requirement": string, "why": string, "quote": string}],
 "explanation": string}
Rules:
- Use ONLY the provided section texts. Never use outside knowledge of the law.
- "key": copy the section key exactly as given (e.g. "NREO:11A").
- "quote": copied character-for-character from that section's text, 8 to 30 words, the words that create the
  requirement. Keep the quote in the section's own language.
- "requirement": one imperative sentence (max 20 words) saying what to do or check before acting. Write it in {language}.
- "why": at most 3 plain-language sentences linking the action to the section, in {language}. If it depends on a
  missing fact (e.g. site area), say so.
- One condition per distinct requirement; at most 6. Only include sections that really apply to this action.
- If no section applies, return {"conditions": [], "explanation": "<why not>"}.
- Never say the action is approved, allowed, clear or legal. Output json only."""


def plan_system(language: str) -> str:
    return PLAN_SYSTEM.replace("{language}", language)


def conditions_system(language: str) -> str:
    return CONDITIONS_SYSTEM.replace("{language}", language)


def plan_user(text: str, tags: tuple[str, ...], catalog: str, toc: str) -> str:
    return (f"ACTION:\n{text}\n\nTAG LIST:\n{', '.join(tags)}\n\n"
            f"LAW CATALOG (code | title | type | jurisdiction | sector | number | languages):\n{catalog}\n\n"
            f"TABLE OF CONTENTS (key | part | heading):\n{toc or '(none)'}")


def conditions_user(text: str, facts: dict, sections: list[tuple[str, str, str, str]]) -> str:
    blocks = [f"[KEY {key}] {law} — {heading or ''}\n{body}" for key, law, heading, body in sections]
    return (f"ACTION:\n{text}\n\nFACTS:\n{json.dumps(facts, ensure_ascii=False)}\n\nSECTIONS:\n"
            + "\n---\n".join(blocks))

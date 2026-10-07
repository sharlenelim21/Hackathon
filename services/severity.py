"""Severity comes from the legal wording (or the legal officer's override), never from the LLM.
The status and headline are built here, in code, from verified conditions only."""
from __future__ import annotations

import re

from .config import SEVERITY_RED, SEVERITY_YELLOW
from .verify import normalize

_RED = [re.compile(p) for p in SEVERITY_RED]
_YELLOW = [re.compile(p) for p in SEVERITY_YELLOW]
OVERRIDE_WORDING = "rule set by legal officer"


def classify(quote: str, override: str | None = None) -> tuple[str, str]:
    """Return (severity, matched_wording)."""
    if override in ("red", "yellow"):
        return override, OVERRIDE_WORDING
    text = normalize(quote)
    for rx in _RED:
        if m := rx.search(text):
            return "red", m.group(0)
    for rx in _YELLOW:
        if m := rx.search(text):
            return "yellow", m.group(0)
    return "info", ""


_HEADLINES = {
    "en": {
        "red": "🔴 Stop — {r} mandatory requirement(s) before you proceed",
        "red_more": " · {y} more to check",
        "yellow": "🟡 Allowed — {y} condition(s) to check first",
        "none": "⚪ No requirements found in the {n} laws indexed",
        "abstain": "❔ Not enough detail to check — please add: {missing}",
        "abstain_default": "more detail about the planned action",
    },
    "ms": {
        "red": "🔴 Henti — {r} keperluan wajib sebelum anda meneruskan",
        "red_more": " · {y} lagi perlu disemak",
        "yellow": "🟡 Dibenarkan — {y} syarat perlu disemak dahulu",
        "none": "⚪ Tiada keperluan ditemui dalam {n} undang-undang yang diindeks",
        "abstain": "❔ Maklumat tidak mencukupi untuk disemak — sila tambah: {missing}",
        "abstain_default": "butiran lanjut tentang tindakan yang dirancang",
    },
}


def status_and_headline(red: int, yellow: int, plan_empty: bool, n_laws: int,
                        missing_facts: list[str], lang: str = "en") -> tuple[str, str]:
    h = _HEADLINES.get(lang, _HEADLINES["en"])
    if red:
        return "red", h["red"].format(r=red) + (h["red_more"].format(y=yellow) if yellow else "")
    if yellow:
        return "yellow", h["yellow"].format(y=yellow)
    if plan_empty:
        missing = "; ".join(m.strip().rstrip(".") for m in missing_facts[:3] if m.strip()) or h["abstain_default"]
        return "abstain", h["abstain"].format(missing=missing)
    return "none", h["none"].format(n=n_laws)

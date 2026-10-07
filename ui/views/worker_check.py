"""Worker screen — "Check an action".

Views call ui.backend only. All verdict wording comes from the backend's
`headline`/`status`; this screen never invents "clear"/"approved"/"safe".
"""

from __future__ import annotations

import html

import streamlit as st

from ui import backend
from ui.components import (
    condition_card,
    headline,
    layout,
    related_minutes,
)

_FOOTER = (
    "This is a compliance reference before action, not a legal judgment "
    "or approval."
)

# Coverage chips (sector label + emoji). Kept as a view-level constant; the
# approved-law count is derived live from list_laws().
_COVERAGE = [
    ("🌿", "Environment"),
    ("🗺", "Land"),
    ("🏘", "Native customary rights"),
]

# "Try an example" prompts -> text that fills the text area.
_EXAMPLES = {
    "School extension in Kapit": (
        "Education Dept plans a rural school extension on a site in Kapit, "
        "Sarawak, involving land clearing and new buildings."
    ),
    "Access road near a river": (
        "Public Works plans a new access road near a river in Sibu Division, "
        "Sarawak, with earthworks close to the water body."
    ),
    "Public facility on native land": (
        "Health Dept plans a public clinic on a site that may be native "
        "customary land in Kapit, Sarawak."
    ),
}

# 3-step "How RAKAN works" strip.
_STEPS = [
    ("Describe the action", "Plain language. No legal terms needed."),
    ("Matched to approved laws",
     "Only laws approved by the legal department are used."),
    ("Checklist with evidence",
     "Every item quotes the exact section and page."),
]

_TEXT_KEY = "worker_action_text"


def _fill_example(text: str) -> None:
    """Set the text area content via its session_state key (pre-rerun)."""
    st.session_state[_TEXT_KEY] = text


def _clear_text() -> None:
    st.session_state[_TEXT_KEY] = ""
    st.session_state.pop("worker_result", None)


def _coverage_chips() -> None:
    try:
        law_count = len(backend.list_laws())
    except Exception:
        law_count = 0
    chips = [
        f'<span class="rk-chip">{emoji} {html.escape(label)}</span>'
        for emoji, label in _COVERAGE
    ]
    chips.append(
        f'<span class="rk-chip">📚 <b>{law_count}</b>&nbsp;approved laws</span>'
    )
    st.markdown(
        f'<div class="rk-chips">{"".join(chips)}</div>', unsafe_allow_html=True
    )


def _how_it_works() -> None:
    layout.eyebrow("How RAKAN works")
    cols = st.columns(3)
    for col, (num, (title, body)) in zip(cols, enumerate(_STEPS, start=1)):
        with col:
            with st.container(border=True):
                st.markdown('<div class="rk-card-marker"></div>',
                            unsafe_allow_html=True)
                st.markdown(
                    f'<div class="rk-step-num">{num}</div>'
                    f'<div class="rk-step-title">{html.escape(title)}</div>'
                    f'<div class="rk-step-body">{html.escape(body)}</div>',
                    unsafe_allow_html=True,
                )


def _input_card() -> None:
    with st.container(border=True):
        st.markdown('<div class="rk-card-marker"></div>', unsafe_allow_html=True)
        st.markdown("**What do you plan to do?**")

        # Examples row.
        st.markdown('<div class="rk-notice">Try an example:</div>',
                    unsafe_allow_html=True)
        ex_cols = st.columns(len(_EXAMPLES))
        for col, (label, text) in zip(ex_cols, _EXAMPLES.items()):
            col.button(
                label, key=f"ex_{label}", type="secondary",
                on_click=_fill_example, args=(text,), use_container_width=True,
            )

        text = st.text_area(
            "What do you plan to do?",
            placeholder="e.g. Education Dept plans a rural school extension on "
            "a site in Kapit, Sarawak, involving land clearing and new "
            "buildings.",
            height=140,
            key=_TEXT_KEY,
            label_visibility="collapsed",
        )

        # Button row: Check (~75%) + Clear (~25%).
        col_check, col_clear = st.columns([3, 1])
        checked = col_check.button(
            "Check compliance impact", type="primary",
            use_container_width=True, disabled=not (text or "").strip(),
        )
        col_clear.button(
            "Clear", type="secondary", use_container_width=True,
            on_click=_clear_text,
        )

        st.markdown(
            '<div class="rk-notice">ⓘ RAKAN lists checks to do before acting. '
            "It does not give legal clearance or approval.</div>",
            unsafe_allow_html=True,
        )

    if checked:
        with st.spinner("Checking indexed laws…"):
            st.session_state["worker_result"] = backend.check_action(text)


def _facts_chips(facts: dict) -> None:
    labels = {
        "activity": "Activity", "location": "Location",
        "area_ha": "Area (ha)", "land_status": "Land status",
    }
    chips = []
    for key, label in labels.items():
        value = facts.get(key)
        shown = value if value not in (None, "") else "—"
        chips.append(
            f'<span class="sli-chip"><b>{label}:</b> {html.escape(str(shown))}</span>'
        )
    st.markdown("".join(chips), unsafe_allow_html=True)


def _summary_row(result: dict) -> None:
    conditions = result.get("conditions") or []
    n_red = sum(1 for c in conditions if c.get("severity") == "red")
    n_yellow = sum(1 for c in conditions if c.get("severity") == "yellow")
    sectors, seen = [], set()
    for c in conditions:
        sec = c.get("sector")
        if sec and sec not in seen:
            seen.add(sec)
            sectors.append(sec)

    parts = []
    if n_red:
        parts.append(f'<span class="sli-pill red">🔴 {n_red} mandatory</span>')
    if n_yellow:
        parts.append(f'<span class="sli-pill yellow">🟡 {n_yellow} conditional</span>')
    for sec in sectors:
        parts.append(f'<span class="sli-pill sector">{html.escape(sec)}</span>')
    if parts:
        st.markdown(
            f'<div class="sli-summary">{"".join(parts)}</div>',
            unsafe_allow_html=True,
        )


def _render_result(result: dict) -> None:
    status = result.get("status", "none")
    headline.render(result.get("headline", ""), status)
    _summary_row(result)

    facts = result.get("facts") or {}
    if facts:
        st.markdown("##### What we understood")
        _facts_chips(facts)

    missing = result.get("missing_facts") or []
    if missing:
        st.markdown("##### Missing information")
        for item in missing:
            st.markdown(
                f'<div class="sli-warn">{html.escape(item)}</div>',
                unsafe_allow_html=True,
            )

    minutes = result.get("related_minutes") or []

    conditions = result.get("conditions") or []
    if conditions:
        st.markdown("##### Checklist")
        for cond in conditions:
            # Count minutes that relate to this condition's law + section.
            count = sum(
                1 for m in minutes
                if m.get("related_law") == cond.get("law_title")
                and (m.get("section_no") in (None, cond.get("section_no")))
            )
            condition_card.render(cond, backend.render_highlight,
                                  related_count=count)

    # Related decisions (meeting minutes) — informational, never a condition.
    related_minutes.render(minutes, backend.render_highlight)

    if status == "none":
        indexed = result.get("indexed_laws") or []
        st.markdown(f"**No requirements found in the {len(indexed)} laws indexed.**")
        for law in indexed:
            st.markdown(f"- {law}")

    if status == "abstain":
        closest = result.get("closest_sections") or []
        st.markdown("**No confident answer. Closest sections to review:**")
        for sec in closest:
            st.markdown(
                f"- {sec.get('law_title', '')} · s.{sec.get('section_no', '')} "
                f"· {sec.get('heading', '')} (p.{sec.get('page', '')})"
            )

    st.markdown(
        f'<div class="sli-footer">{html.escape(_FOOTER)}</div>',
        unsafe_allow_html=True,
    )


def render() -> None:
    layout.page_header(
        "Compliance check",
        "Check an action",
        "Describe what your department plans to do. RAKAN lists the legal "
        "checks from other sectors that may apply, each backed by a quote "
        "from an approved law.",
    )

    _coverage_chips()
    _input_card()

    result = st.session_state.get("worker_result")
    if result:
        st.divider()
        layout.eyebrow("Result")
        _render_result(result)
    else:
        _how_it_works()

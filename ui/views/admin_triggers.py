"""Legal Officer screen — "Trigger map".

Table of triggers with status badges, a status filter, and a propose form.
Rows with status needs_review are highlighted.
"""

from __future__ import annotations

import html

import streamlit as st

from ui import backend
from ui.components import badges, layout

_STATUSES = ["all", "pending", "approved", "rejected", "needs_review"]


def _render_rows(rows: list) -> None:
    for row in rows:
        needs_review = row.get("status") == "needs_review"
        # Highlight needs_review rows with a gold left border via the warn style.
        wrapper_cls = "sli-card"
        style = ""
        if needs_review:
            style = ' style="border-left:4px solid #C8A45D;"'
        st.markdown(f'<div class="{wrapper_cls}"{style}>', unsafe_allow_html=True)
        head = (
            '<div class="sli-card-head">'
            f'<span class="sli-pill version">{html.escape(row.get("activity_tag",""))}</span>'
            f'{badges.status_badge(row.get("status","pending"))}'
            "</div>"
        )
        st.markdown(head, unsafe_allow_html=True)
        st.markdown(
            f'<div class="sli-meta">{html.escape(row.get("law_title",""))} '
            f'&middot; s.{html.escape(row.get("section_no",""))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="sli-meta">{html.escape(row.get("note",""))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def _propose_form() -> None:
    st.markdown("##### Propose row")
    laws = backend.list_laws()
    law_options = {f"{law['title']} (id {law['id']})": law["id"] for law in laws}

    with st.form("propose_trigger_form"):
        activity_tag = st.selectbox("Activity tag", backend.ACTIVITY_TAGS)
        law_label = st.selectbox("Law", list(law_options.keys()) or ["—"])
        section_no = st.text_input("Section no.", placeholder="e.g. 11A")
        note = st.text_area("Note", placeholder="Why this trigger applies (SAMPLE).")
        submitted = st.form_submit_button("Propose", type="primary")

    if submitted:
        if not law_options:
            st.warning("No laws available to link.")
        elif not section_no.strip():
            st.warning("Enter a section number.")
        else:
            try:
                backend.propose_trigger(
                    activity_tag, law_options[law_label], section_no, note
                )
                st.toast("Trigger proposed (pending review).", icon="📝")
                st.rerun()
            except Exception as exc:
                st.error(getattr(exc, "message", None) or str(exc))


def render() -> None:
    layout.page_header(
        "Law management",
        "Trigger map",
        "Maps activity tags to the law sections they trigger. Rows marked "
        "'needs review' are highlighted.",
    )

    chosen = st.selectbox("Filter by status", _STATUSES, index=0)
    triggers = backend.list_triggers()
    if chosen != "all":
        triggers = [t for t in triggers if t.get("status") == chosen]

    if triggers:
        _render_rows(triggers)
    else:
        st.info("No triggers match this filter.")

    st.divider()
    _propose_form()

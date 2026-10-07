"""Officer/Admin screen — "My submissions".

A table of the user's submissions with status badges and the review note.

Views call ui.backend only.
"""

from __future__ import annotations

import html

import streamlit as st

from ui import backend
from ui.components import badges, layout

_TYPE_LABEL = {
    "new_law": "New law",
    "new_version": "New version",
    "minutes": "Meeting minutes",
}


def render() -> None:
    role = st.session_state.get("role", "Officer")
    layout.page_header(
        "Your activity",
        "My submissions",
        "Track what you have submitted and how an Admin reviewed it.",
    )

    subs = backend.list_my_submissions(role)
    if not subs:
        st.info("You have not submitted anything yet.")
        return

    for sub in subs:
        with st.container(border=True):
            st.markdown('<div class="rk-card-marker"></div>',
                        unsafe_allow_html=True)
            type_label = _TYPE_LABEL.get(sub.get("type"), sub.get("type", ""))
            head = (
                '<div class="sli-card-head">'
                f'<span class="sli-pill version">{html.escape(type_label)}</span>'
                '<span class="sli-card-head-right">'
                f'{badges.status_badge(sub.get("status","pending"))}'
                "</span></div>"
            )
            st.markdown(head, unsafe_allow_html=True)
            st.markdown(
                f'<div class="sli-requirement">{html.escape(sub.get("title",""))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="sli-meta">Submitted {html.escape(sub.get("submitted_at",""))}</div>',
                unsafe_allow_html=True,
            )
            if sub.get("review_note"):
                st.markdown(
                    f'<div class="sli-meta"><b>Review note:</b> '
                    f'{html.escape(sub["review_note"])}</div>',
                    unsafe_allow_html=True,
                )

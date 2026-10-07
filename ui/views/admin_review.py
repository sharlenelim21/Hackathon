"""Admin screen — "Review queue".

The human-in-the-loop core. Every submission (from an Officer or an Admin)
arrives here as pending. Approve makes it citable by the AI; Reject keeps it
for the audit trail and requires a note.

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
    "trigger": "Trigger",
}

_FILTERS = {
    "All": None,
    "New law": "new_law",
    "New version": "new_version",
    "Meeting minutes": "minutes",
}
_FILTER_KEY = "review_filter"


def _filter_chips() -> str:
    """Segmented control acting as filter chips. Always one selected."""
    labels = list(_FILTERS.keys())
    default = st.session_state.get("review_filter_label", "All")

    def _on_change() -> None:
        if st.session_state.get(_FILTER_KEY) is None:
            st.session_state[_FILTER_KEY] = st.session_state.get(
                "review_filter_label", "All"
            )

    chosen = st.segmented_control(
        "Filter", options=labels, selection_mode="single",
        default=default, key=_FILTER_KEY, on_change=_on_change,
        label_visibility="collapsed",
    )
    chosen = chosen or default
    st.session_state["review_filter_label"] = chosen
    return _FILTERS[chosen]


def _render_diff(diff: list) -> None:
    st.markdown("**Section changes**")
    for row in diff:
        st.markdown(f"**s.{row.get('section_no','')}** — _{row.get('change','')}_")
        col_old, col_new = st.columns(2)
        col_old.caption("Old")
        col_old.code(row.get("old") or "—", language=None)
        col_new.caption("New")
        col_new.code(row.get("new") or "—", language=None)


def _render_item(item: dict) -> None:
    item_id = item["id"]
    type_label = _TYPE_LABEL.get(item.get("type"), item.get("type", "item"))

    with st.container(border=True):
        st.markdown('<div class="rk-card-marker"></div>', unsafe_allow_html=True)

        head = (
            '<div class="sli-card-head">'
            f'<span class="sli-pill version">{html.escape(type_label)}</span>'
            '<span class="sli-card-head-right">'
            f'<span class="sli-pill info">{html.escape(item.get("submitted_by_role","—"))}</span>'
            "</span></div>"
        )
        st.markdown(head, unsafe_allow_html=True)
        st.markdown(
            f'<div class="sli-requirement">{html.escape(item.get("title",""))}</div>',
            unsafe_allow_html=True,
        )
        meta = (
            f'Submitted by {html.escape(item.get("uploaded_by",""))} '
            f'&middot; {html.escape(item.get("uploaded_at",""))}'
        )
        st.markdown(f'<div class="sli-meta">{meta}</div>', unsafe_allow_html=True)

        related = item.get("related_laws") or []
        if related:
            st.markdown(
                f'<div class="sli-meta">Related: '
                f'{html.escape(", ".join(related))}</div>',
                unsafe_allow_html=True,
            )
        if item.get("summary"):
            label = ("Decision summary" if item.get("type") == "minutes"
                     else "What changed")
            st.markdown(
                f'<div class="sli-meta"><b>{label}:</b> '
                f'{html.escape(item["summary"])}</div>',
                unsafe_allow_html=True,
            )
        if item.get("diff"):
            _render_diff(item["diff"])

        note = st.text_input("Note (required to reject)", key=f"note_{item_id}")
        col_a, col_r = st.columns(2)
        if col_a.button("Approve — make citable", key=f"approve_{item_id}",
                        type="primary", use_container_width=True):
            backend.approve(item_id, note, reviewer_role="Admin")
            st.toast("Approved. RAKAN can now cite this source.", icon="✅")
            st.rerun()
        if col_r.button("Reject", key=f"reject_{item_id}", type="secondary",
                        use_container_width=True):
            if not note.strip():
                st.warning("A note is required to reject an item.")
            else:
                backend.reject(item_id, note, reviewer_role="Admin")
                st.toast(f"Rejected: {item.get('title','')}", icon="🚫")
                st.rerun()


def render() -> None:
    if not layout.require_admin():
        return
    layout.page_header(
        "Human in the loop",
        "Review queue",
        "Every submission waits here until you decide. Approve makes a source "
        "citable by RAKAN; Reject keeps it for the audit trail.",
    )

    type_filter = _filter_chips()
    pending = backend.list_pending()
    # The trigger proposals also live in pending; the review queue focuses on
    # law/version/minutes submissions.
    pending = [p for p in pending if p.get("type") in
               ("new_law", "new_version", "minutes")]
    if type_filter:
        pending = [p for p in pending if p.get("type") == type_filter]

    if not pending:
        st.success("Nothing is waiting for review in this filter.")
        return

    for item in pending:
        _render_item(item)

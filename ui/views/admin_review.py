"""Legal officer screen — "Review queue".

The human-in-the-loop gate. Pending law uploads, new versions and proposed
trigger rules wait here. Approving a version makes it searchable/citable;
rejecting keeps it out. Maps to backend list_pending / approve / reject.

Views call ui.backend only.
"""

from __future__ import annotations

import html

import streamlit as st

from ui import backend
from ui.components import layout

_TYPE_LABEL = {
    "new_law": "New law",
    "new_version": "New version",
    "trigger": "Trigger rule",
}

_FILTERS = {
    "All": None,
    "New law": "new_law",
    "New version": "new_version",
    "Trigger rule": "trigger",
}
_FILTER_KEY = "review_filter"


def _filter_chips() -> str:
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
    item_type = item.get("type", "item")
    type_label = _TYPE_LABEL.get(item_type, item_type)

    with st.container(border=True):
        st.markdown('<div class="rk-card-marker"></div>', unsafe_allow_html=True)

        head = (
            '<div class="sli-card-head">'
            f'<span class="sli-pill version">{html.escape(type_label)}</span>'
            "</div>"
        )
        st.markdown(head, unsafe_allow_html=True)
        st.markdown(
            f'<div class="sli-requirement">{html.escape(item.get("title",""))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sli-meta">'
            f'Submitted by {html.escape(str(item.get("uploaded_by","")))} '
            f'&middot; {html.escape(str(item.get("uploaded_at","")))}</div>',
            unsafe_allow_html=True,
        )

        # Trigger proposals carry a note; versions may carry a diff + warnings.
        if item.get("note"):
            st.markdown(
                f'<div class="sli-meta"><b>Note:</b> '
                f'{html.escape(str(item["note"]))}</div>',
                unsafe_allow_html=True,
            )
        summary = item.get("diff_summary")
        if summary:
            st.markdown(
                '<div class="sli-meta"><b>Changes:</b> '
                f'{summary.get("added",0)} added · {summary.get("removed",0)} '
                f'removed · {summary.get("changed",0)} changed · '
                f'{summary.get("unchanged",0)} unchanged</div>',
                unsafe_allow_html=True,
            )
        for w in item.get("warnings") or []:
            st.caption(f"⚠ {w}")
        if item.get("diff"):
            with st.expander("View section diff"):
                _render_diff(item["diff"])

        note = st.text_input("Note (required to reject)", key=f"note_{item_id}")
        col_a, col_r = st.columns(2)
        if col_a.button("Approve — make searchable", key=f"approve_{item_id}",
                        type="primary", use_container_width=True):
            try:
                backend.approve(item_id, note)
                st.toast("Approved. RAKAN can now use this source.", icon="✅")
                st.rerun()
            except Exception as exc:
                st.error(_err(exc))
        if col_r.button("Reject", key=f"reject_{item_id}", type="secondary",
                        use_container_width=True):
            if not note.strip():
                st.warning("A note is required to reject an item.")
            else:
                try:
                    backend.reject(item_id, note)
                    st.toast(f"Rejected: {item.get('title','')}", icon="🚫")
                    st.rerun()
                except Exception as exc:
                    st.error(_err(exc))


def _err(exc: Exception) -> str:
    return getattr(exc, "message", None) or str(exc)


def render() -> None:
    layout.page_header(
        "Human in the loop",
        "Review queue",
        "Pending uploads and proposed trigger rules wait here. Approving a "
        "version makes it searchable and citable by RAKAN; rejecting keeps it "
        "out. Reject requires a note.",
    )

    type_filter = _filter_chips()
    try:
        pending = backend.list_pending()
    except Exception as exc:
        st.error(_err(exc))
        return

    if type_filter:
        pending = [p for p in pending if p.get("type") == type_filter]

    if not pending:
        st.success("Nothing is waiting for review in this filter.")
        return

    for item in pending:
        _render_item(item)

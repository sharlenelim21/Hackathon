"""RAKAN — Regulatory Advisory & Compliance Alert Network (frontend).

Single Streamlit entry point. Draws a custom sidebar (brand → role → page
links → footer) with st.navigation(position="hidden"), and builds the page
list from the simulated role.

Roles match the backend's human-in-the-loop model:
  - Worker: checks planned actions against approved laws.
  - Legal officer: uploads laws, reviews the pending queue, curates triggers,
    reads the audit log.

The backend (services/) is wired through ui/backend.py (USE_MOCK = False).
"""

from __future__ import annotations

import streamlit as st

from ui import backend
from ui.styles import inject_css
from ui.views import (
    admin_audit as audit_view,
    admin_review as review_view,
    admin_triggers as triggers_view,
    submit_change as upload_view,
    worker_check,
)

APP_NAME = "RAKAN"

_ROLE_WORKER = "Worker"
_ROLE_OFFICER = "Legal officer"
_ROLE_OPTIONS = [_ROLE_WORKER, _ROLE_OFFICER]
_ROLE_HINTS = {
    _ROLE_WORKER: "Check planned actions against approved laws.",
    _ROLE_OFFICER: "Upload laws, review the queue, curate triggers, read the "
                   "audit log.",
}


def _worker_pages() -> list:
    return [
        st.Page(worker_check.render, title="Check an action", url_path="check",
                icon=":material/fact_check:", default=True),
    ]


def _officer_pages() -> list:
    return [
        st.Page(upload_view.render, title="Upload law", url_path="upload",
                icon=":material/upload_file:", default=True),
        st.Page(review_view.render, title="Review queue", url_path="review",
                icon=":material/rule:"),
        st.Page(triggers_view.render, title="Trigger map", url_path="triggers",
                icon=":material/account_tree:"),
        st.Page(audit_view.render, title="Audit log & laws", url_path="audit",
                icon=":material/history:"),
    ]


def _render_brand() -> None:
    st.markdown(
        '<div class="rk-brand">'
        '<div class="rk-mark">R</div>'
        "<div>"
        '<div class="rk-name">RAKAN</div>'
        '<div class="rk-full">Regulatory Advisory &amp;<br>'
        "Compliance Alert Network</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )


def _render_role_switch() -> str:
    """Segmented role control that can never be deselected."""
    previous = st.session_state.get("role", _ROLE_WORKER)

    def _on_change() -> None:
        if st.session_state.get("role_choice") is None:
            st.session_state["role_choice"] = st.session_state.get(
                "role", _ROLE_WORKER
            )

    st.markdown('<div class="rk-label">Role</div>', unsafe_allow_html=True)
    selection = st.segmented_control(
        "Role", options=_ROLE_OPTIONS, selection_mode="single",
        default=previous, key="role_choice", on_change=_on_change,
        label_visibility="collapsed",
    )
    role = selection if selection in _ROLE_OPTIONS else previous
    st.session_state["role"] = role
    st.markdown(f'<div class="rk-hint">{_ROLE_HINTS[role]}</div>',
                unsafe_allow_html=True)
    return role


def _queue_count() -> int:
    try:
        return len(backend.list_pending())
    except Exception:
        return 0


def _render_footer() -> None:
    try:
        law_count = sum(
            1 for law in backend.list_laws() if law.get("status") == "approved"
        )
    except Exception:
        law_count = 0
    note = ""
    if backend.USE_MOCK:
        note = '<div class="rk-hint">Prototype · sample data</div>'
    st.markdown(
        '<div style="margin-top:28px;">'
        f'<div class="rk-hint">{law_count} approved laws indexed</div>'
        f"{note}</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME, page_icon=":material/gavel:",
        layout="centered", initial_sidebar_state="expanded",
    )
    inject_css()  # every rerun, before navigation

    with st.sidebar:
        _render_brand()
        role = _render_role_switch()
        current_pages = (_worker_pages() if role == _ROLE_WORKER
                         else _officer_pages())

        nav = st.navigation(current_pages, position="hidden")

        st.markdown('<div class="rk-label">Navigate</div>', unsafe_allow_html=True)
        q = _queue_count()
        for p in current_pages:
            label = (f"{p.title} · {q}"
                     if p.url_path == "review" and q else p.title)
            st.page_link(p, label=label)

        _render_footer()

    nav.run()


if __name__ == "__main__":
    main()

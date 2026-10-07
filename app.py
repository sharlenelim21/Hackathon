"""RAKAN — Regulatory Advisory & Compliance Alert Network (frontend prototype).

Single Streamlit entry point. Draws a custom sidebar (brand → role → page
links → demo → footer) with st.navigation(position="hidden"), and builds the
page list from the simulated role (Officer / Admin).

We deliberately use ui/views/ (NOT pages/) so Streamlit does not auto-list
screens; access control is enforced by which pages we register per role.
"""

from __future__ import annotations

import streamlit as st

from ui import backend
from ui.styles import inject_css
from ui.views import (
    admin_audit,
    admin_review,
    admin_triggers,
    library,
    my_submissions,
    submit_change,
    worker_check,
)

APP_NAME = "RAKAN"

_ROLE_OFFICER = "Officer"
_ROLE_ADMIN = "Admin"
_ROLE_OPTIONS = [_ROLE_OFFICER, _ROLE_ADMIN]
_ROLE_HINTS = {
    _ROLE_OFFICER: "Check planned actions, read approved sources, submit changes.",
    _ROLE_ADMIN: "Everything officers can do, plus approve or reject changes.",
}

_SCENARIO_LABELS = {
    "🔴 Kapit school extension (mandatory)": "red",
    "🟡 Conditional only": "yellow",
    "⚪ No requirements found": "none",
    "❔ No confident answer": "abstain",
}


def _officer_pages() -> list:
    return [
        st.Page(worker_check.render, title="Check an action", url_path="check",
                icon=":material/fact_check:", default=True),
        st.Page(library.render, title="Library", url_path="library",
                icon=":material/menu_book:"),
        st.Page(submit_change.render, title="Submit a change", url_path="submit",
                icon=":material/upload_file:"),
        st.Page(my_submissions.render, title="My submissions",
                url_path="my-submissions", icon=":material/outbox:"),
    ]


def _admin_only_pages() -> list:
    return [
        st.Page(admin_review.render, title="Review queue", url_path="review",
                icon=":material/rule:"),
        st.Page(admin_triggers.render, title="Trigger map", url_path="triggers",
                icon=":material/account_tree:"),
        st.Page(admin_audit.render, title="Audit log", url_path="audit",
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
    """Segmented role control that can never be deselected.

    Uses key='role_choice' + an on_change callback that restores the previous
    role when the widget returns None (user clicked the active segment)."""
    previous = st.session_state.get("role", _ROLE_OFFICER)

    def _on_change() -> None:
        if st.session_state.get("role_choice") is None:
            st.session_state["role_choice"] = st.session_state.get(
                "role", _ROLE_OFFICER
            )

    st.markdown('<div class="rk-label">Role</div>', unsafe_allow_html=True)
    selection = st.segmented_control(
        "Role",
        options=_ROLE_OPTIONS,
        selection_mode="single",
        default=previous,
        key="role_choice",
        on_change=_on_change,
        label_visibility="collapsed",
    )
    role = selection if selection in _ROLE_OPTIONS else previous
    st.session_state["role"] = role
    st.markdown(f'<div class="rk-hint">{_ROLE_HINTS[role]}</div>',
                unsafe_allow_html=True)
    return role


def _render_demo_controls(role: str) -> None:
    st.markdown(
        '<div class="rk-demo-row">'
        '<span class="rk-label" style="margin:0;">Demo</span>'
        '<span class="rk-badge">MOCK DATA</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    chosen = st.selectbox(
        "Mock scenario", list(_SCENARIO_LABELS.keys()),
        label_visibility="collapsed",
        help="Switches the sample check_action response.",
    )
    st.session_state["mock_scenario"] = _SCENARIO_LABELS[chosen]


def _render_footer() -> None:
    try:
        law_count = len(backend.list_library("laws"))
    except Exception:
        law_count = 0
    proto = ('<div class="rk-hint">Prototype · sample data</div>'
             if backend.USE_MOCK else "")
    st.markdown(
        '<div style="margin-top:28px;">'
        f'<div class="rk-hint">{law_count} approved laws indexed</div>'
        f"{proto}</div>",
        unsafe_allow_html=True,
    )


def _queue_count() -> int:
    try:
        return sum(
            1 for p in backend.list_pending()
            if p.get("type") in ("new_law", "new_version", "minutes")
        )
    except Exception:
        return 0


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME, page_icon=":material/gavel:",
        layout="centered", initial_sidebar_state="expanded",
    )
    inject_css()  # every rerun, before navigation

    with st.sidebar:
        _render_brand()
        role = _render_role_switch()

        officer_pages = _officer_pages()
        admin_pages = _admin_only_pages()
        current_pages = (officer_pages if role == _ROLE_OFFICER
                         else officer_pages + admin_pages)

        nav = st.navigation(current_pages, position="hidden")

        # Shared (Officer + Admin) links.
        st.markdown('<div class="rk-label">Navigate</div>', unsafe_allow_html=True)
        for p in officer_pages:
            st.page_link(p)

        # Admin-only links under an ADMIN label.
        if role == _ROLE_ADMIN:
            st.markdown('<div class="rk-label">Admin</div>',
                        unsafe_allow_html=True)
            q = _queue_count()
            for p in admin_pages:
                label = f"{p.title} · {q}" if p.url_path == "review" and q else p.title
                st.page_link(p, label=label)

        if backend.USE_MOCK:
            _render_demo_controls(role)
        _render_footer()

    nav.run()


if __name__ == "__main__":
    main()

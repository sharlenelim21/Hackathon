"""Legal Officer screen — "Audit log & laws".

Two tabs: the indexed laws (with status) and the audit log (newest first).
"""

from __future__ import annotations

import streamlit as st

from ui import backend
from ui.components import layout


def _render_laws() -> None:
    laws = backend.list_laws()
    if not laws:
        st.info("No laws indexed yet.")
        return
    # Dataframe is fine here: this is reference data, not an action surface.
    rows = [
        {
            "Title": law.get("title", ""),
            "Jurisdiction": law.get("jurisdiction", ""),
            "Cap./Act": law.get("cap_no", ""),
            "Sector": law.get("sector", ""),
            "Version": law.get("version_label", ""),
            "Status": law.get("status", ""),
        }
        for law in laws
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_audit() -> None:
    entries = backend.get_audit_log()  # already newest-first
    if not entries:
        st.info("No audit entries yet.")
        return
    rows = [
        {
            "Timestamp": e.get("ts", ""),
            "Actor": e.get("actor", ""),
            "Action": e.get("action", ""),
            "Target": f"{e.get('target_type','')} #{e.get('target_id','')}",
            "Note": e.get("note", ""),
        }
        for e in entries
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render() -> None:
    layout.page_header(
        "Audit & records",
        "Audit log & laws",
        "A full trail of submissions, approvals and rejections (newest first), "
        "plus the indexed laws.",
    )

    tab_laws, tab_audit = st.tabs(["Indexed laws", "Audit log"])
    with tab_laws:
        _render_laws()
    with tab_audit:
        _render_audit()

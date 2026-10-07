"""Officer/Admin screen — "Submit a change".

Choose a submission type (New law / New version / Meeting minutes), fill the
relevant fields, preview, then submit for review. Everything lands in the
Review queue as pending; nothing is citable until an Admin approves it.

Views call ui.backend only.
"""

from __future__ import annotations

import streamlit as st

from ui import backend
from ui.components import layout

_SECTORS = ["Environment", "Land", "Native Rights", "Procurement", "Other"]

# Submission types. Keys are the backend `kind`; values are display labels.
_TYPES = {
    "new_law": "① New law",
    "new_version": "② New version",
    "minutes": "③ Meeting minutes",
}
_TYPE_KEY = "submit_type_choice"


def _type_switch() -> str:
    """Segmented control for the submission type. Always one selected."""
    previous = st.session_state.get("submit_type", "new_law")
    labels = list(_TYPES.values())
    default_label = _TYPES[previous]

    def _on_change() -> None:
        if st.session_state.get(_TYPE_KEY) is None:
            st.session_state[_TYPE_KEY] = _TYPES[
                st.session_state.get("submit_type", "new_law")
            ]

    chosen = st.segmented_control(
        "Submission type",
        options=labels,
        selection_mode="single",
        default=default_label,
        key=_TYPE_KEY,
        on_change=_on_change,
        label_visibility="collapsed",
    )
    if chosen is None:
        chosen = default_label
    kind = next(k for k, v in _TYPES.items() if v == chosen)
    st.session_state["submit_type"] = kind
    return kind


def _law_options() -> dict:
    return {law["title"]: law["id"] for law in backend.list_laws()}


def _new_law_fields() -> dict:
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Title", placeholder="e.g. New Ordinance (SAMPLE)")
        jurisdiction = st.selectbox("Jurisdiction", ["Sarawak", "Federal"])
        version_label = st.text_input("Version label",
                                      placeholder="e.g. 2026 Edition")
        published_date = st.date_input("Published date")
    with col2:
        cap_no = st.text_input("Cap. / Act no.", placeholder="e.g. Cap. 99")
        sector = st.selectbox("Sector", _SECTORS)
        in_force_date = st.date_input("In-force date")
        source_url = st.text_input("Source URL", placeholder="https://…")
    st.file_uploader("PDF file", type=["pdf"], key="submit_pdf_new_law")
    return {
        "title": title, "jurisdiction": jurisdiction, "cap_no": cap_no,
        "sector": sector, "version_label": version_label,
        "published_date": str(published_date), "in_force_date": str(in_force_date),
        "source_url": source_url,
    }


def _new_version_fields() -> dict:
    laws = _law_options()
    law_title = st.selectbox("Existing law", list(laws.keys()) or ["—"])
    col1, col2 = st.columns(2)
    with col1:
        version_label = st.text_input("Version label",
                                      placeholder="e.g. 2026 Amendment")
        published_date = st.date_input("Published date")
    with col2:
        in_force_date = st.date_input("In-force date")
        source_url = st.text_input("Source URL", placeholder="https://…")
    what_changed = st.text_area(
        "What changed",
        placeholder="Summarise what this version changes (SAMPLE).",
    )
    st.file_uploader("PDF file", type=["pdf"], key="submit_pdf_new_version")
    return {
        "title": f"{law_title} — {version_label or 'new version'}",
        "law_title": law_title, "version_label": version_label,
        "published_date": str(published_date), "in_force_date": str(in_force_date),
        "source_url": source_url, "what_changed": what_changed,
        "is_new_version_of": law_title,
    }


def _minutes_fields() -> dict:
    laws = _law_options()
    col1, col2 = st.columns(2)
    with col1:
        meeting_title = st.text_input("Meeting title",
                                      placeholder="e.g. Native Rights working group")
        body = st.text_input("Organising body", placeholder="e.g. Legal Department")
    with col2:
        meeting_date = st.date_input("Meeting date")
    related = st.multiselect("Related law(s)", list(laws.keys()))
    section_no = st.text_input("Related section number(s) (optional)",
                               placeholder="e.g. 27, 27A")
    decision_summary = st.text_area(
        "Decision summary",
        placeholder="What did the meeting decide? (SAMPLE)",
    )
    st.file_uploader("PDF file", type=["pdf"], key="submit_pdf_minutes")
    return {
        "title": meeting_title, "meeting_title": meeting_title,
        "meeting_date": str(meeting_date), "body": body,
        "related_laws": related, "section_no": section_no,
        "decision_summary": decision_summary,
    }


_FIELD_BUILDERS = {
    "new_law": _new_law_fields,
    "new_version": _new_version_fields,
    "minutes": _minutes_fields,
}


def render() -> None:
    role = st.session_state.get("role", "Officer")
    layout.page_header(
        "Law management",
        "Submit a change",
        "New laws, versions and meeting minutes stay pending until an Admin "
        "approves them. Nothing is searchable before review.",
    )

    kind = _type_switch()

    with st.form(f"submit_form_{kind}"):
        st.markdown('<div class="rk-card-marker"></div>', unsafe_allow_html=True)
        meta = _FIELD_BUILDERS[kind]()

        _, col_preview, col_submit = st.columns([2, 1, 1])
        preview_clicked = col_preview.form_submit_button(
            "Preview", use_container_width=True
        )
        submit_clicked = col_submit.form_submit_button(
            "Submit for review", type="primary", use_container_width=True
        )

    if preview_clicked:
        if kind == "minutes":
            st.session_state["submit_preview"] = {"minutes_meta": meta}
        else:
            st.session_state["submit_preview"] = backend.upload_preview(b"", meta)

    preview = st.session_state.get("submit_preview")
    if preview:
        st.divider()
        if "minutes_meta" in preview:
            m = preview["minutes_meta"]
            st.markdown(f"**Meeting:** {m.get('meeting_title') or '—'} · "
                        f"{m.get('meeting_date') or '—'} · {m.get('body') or '—'}")
            if m.get("related_laws"):
                st.markdown("**Related law(s):** " + ", ".join(m["related_laws"]))
            st.markdown(m.get("decision_summary") or "_No decision summary._")
        else:
            toc = preview.get("toc") or []
            parts = {e.get("part") for e in toc if e.get("part")}
            st.markdown(f"**{preview.get('sections_count', 0)} sections found · "
                        f"{len(parts)} parts**")
            if preview.get("is_new_version_of"):
                st.markdown(
                    '<div class="sli-warn">⚠ New version of '
                    f"<b>{preview['is_new_version_of']}</b>.</div>",
                    unsafe_allow_html=True,
                )
            if toc:
                st.dataframe(toc, use_container_width=True, hide_index=True)

    if submit_clicked:
        if not (meta.get("title") or "").strip():
            st.warning("Enter a title before submitting.")
        else:
            backend.submit_change(kind, b"", meta, role)
            st.session_state.pop("submit_preview", None)
            with st.container(border=True):
                st.markdown('<div class="rk-card-marker"></div>',
                            unsafe_allow_html=True)
                st.success(
                    "Submitted for review — not searchable until an Admin "
                    "approves it."
                )
                st.markdown(
                    '<div class="rk-notice">Track it under '
                    "<b>My submissions</b> in the sidebar.</div>",
                    unsafe_allow_html=True,
                )

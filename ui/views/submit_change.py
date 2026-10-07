"""Legal officer screen — "Upload law".

Upload a law PDF, preview the parsed sections, then submit it as a PENDING
version. Nothing is searchable until it is approved in the Review queue.

Maps directly to the backend: upload_preview(file_bytes, meta) and
submit_upload(file_bytes, meta). Views call ui.backend only.
"""

from __future__ import annotations

import streamlit as st

from ui import backend
from ui.components import layout

_SECTORS = ["Environment", "Land", "Native Rights", "Procurement",
            "Business", "Syariah", "Other"]


def _section_heading(num: int, label: str) -> None:
    st.markdown(
        f'<div class="rk-form-section"><span class="rk-form-num">{num}</span>'
        f"{label}</div>",
        unsafe_allow_html=True,
    )


def render() -> None:
    layout.page_header(
        "Law management",
        "Upload law",
        "Upload a law PDF. It is parsed and held as a pending version — nothing "
        "is searchable until it is approved in the Review queue.",
    )

    with st.form("upload_form"):
        st.markdown('<div class="rk-card-marker"></div>', unsafe_allow_html=True)

        # ① Document
        _section_heading(1, "Document")
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", placeholder="e.g. Land Code")
            jurisdiction = st.selectbox("Jurisdiction", ["Sarawak", "Federal"])
        with col2:
            cap_no = st.text_input("Cap. / Act no.", placeholder="e.g. Cap. 81")
            sector = st.selectbox("Sector", _SECTORS)
        st.divider()

        # ② Version & dates
        _section_heading(2, "Version & dates")
        col3, col4 = st.columns(2)
        with col3:
            version_label = st.text_input("Version label",
                                          placeholder="e.g. 2024 Consolidated")
            published_date = st.date_input("Published date", value=None)
        with col4:
            in_force_date = st.date_input("In-force date", value=None)
            source_url = st.text_input("Source URL", placeholder="https://…")
        source_authority = st.selectbox("Source authority",
                                        ["official", "unofficial"])
        st.divider()

        # ③ File
        _section_heading(3, "File")
        pdf_file = st.file_uploader("PDF file", type=["pdf"])

        _, col_preview, col_submit = st.columns([2, 1, 1])
        preview_clicked = col_preview.form_submit_button(
            "Preview sections", use_container_width=True
        )
        submit_clicked = col_submit.form_submit_button(
            "Submit for approval", type="primary", use_container_width=True
        )

    meta = {
        "title": title,
        "jurisdiction": jurisdiction,
        "cap_no": cap_no,
        "sector": sector,
        "version_label": version_label,
        "published_date": str(published_date) if published_date else "",
        "in_force_date": str(in_force_date) if in_force_date else "",
        "source_url": source_url,
        "source_authority": source_authority,
    }
    file_bytes = pdf_file.getvalue() if pdf_file else b""

    # Validate the fields the backend requires before calling it, so we show a
    # friendly message instead of a ServiceError.
    def _missing_required() -> list:
        return [label for label, val in (
            ("Title", title), ("Jurisdiction", jurisdiction),
            ("Sector", sector), ("Version label", version_label),
        ) if not (val or "").strip()]

    if preview_clicked:
        missing = _missing_required()
        if missing:
            st.warning("Fill in: " + ", ".join(missing) + ".")
        elif not file_bytes:
            st.warning("Attach a PDF to preview its sections.")
        else:
            try:
                st.session_state["upload_preview"] = backend.upload_preview(
                    file_bytes, meta
                )
            except Exception as exc:  # ServiceError or parse failure
                st.error(_friendly_error(exc))

    preview = st.session_state.get("upload_preview")
    if preview:
        st.divider()
        toc = preview.get("toc") or []
        parts = {e.get("part") for e in toc if e.get("part")}
        st.markdown(
            f"**{preview.get('sections_count', 0)} sections found · "
            f"{len(parts)} parts** ({preview.get('mode', 'auto')} mode, "
            f"{preview.get('page_count', 0)} pages)"
        )
        if preview.get("is_new_version_of"):
            st.markdown(
                '<div class="sli-warn">⚠ This will be treated as a new version '
                f"of <b>{preview['is_new_version_of']}</b>.</div>",
                unsafe_allow_html=True,
            )
        for w in preview.get("warnings") or []:
            st.caption(f"⚠ {w}")
        if toc:
            st.markdown("**Table of contents**")
            st.dataframe(toc, use_container_width=True, hide_index=True)

    if submit_clicked:
        missing = _missing_required()
        if missing:
            st.warning("Fill in: " + ", ".join(missing) + ".")
        elif not file_bytes:
            st.warning("Attach a PDF before submitting.")
        else:
            try:
                res = backend.submit_upload(file_bytes, meta)
                st.session_state.pop("upload_preview", None)
                st.success(
                    "Pending legal review — not searchable yet "
                    f"(version #{res.get('version_id', '?')})."
                )
                st.markdown(
                    '<div class="rk-notice">Find it under '
                    "<b>Review queue</b> to approve or reject.</div>",
                    unsafe_allow_html=True,
                )
            except Exception as exc:
                st.error(_friendly_error(exc))


def _friendly_error(exc: Exception) -> str:
    """ServiceError carries a human message; fall back to str()."""
    msg = getattr(exc, "message", None) or str(exc)
    return f"Could not process this file: {msg}"

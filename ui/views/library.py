"""Officer/Admin screen — "Library".

Approved sources only, in two tabs (Laws / Meeting minutes), with a search
box. These are the only documents the AI can cite.

Views call ui.backend only.
"""

from __future__ import annotations

import html

import streamlit as st

from ui import backend
from ui.components import badges, layout


def _matches(query: str, *fields: str) -> bool:
    if not query:
        return True
    q = query.lower()
    return any(q in (f or "").lower() for f in fields)


def _render_laws(query: str) -> None:
    laws = backend.list_library("laws")
    laws = [x for x in laws if _matches(query, x.get("title"), x.get("sector"),
                                        x.get("cap_no"))]
    if not laws:
        st.info("No approved laws match.")
        return
    for law in laws:
        with st.container(border=True):
            st.markdown('<div class="rk-card-marker"></div>',
                        unsafe_allow_html=True)
            head = (
                '<div class="sli-card-head">'
                f'<span class="sli-pill sector">{html.escape(law.get("sector",""))}</span>'
                '<span class="sli-card-head-right">'
                f'{badges.status_badge(law.get("status","approved"))}'
                "</span></div>"
            )
            st.markdown(head, unsafe_allow_html=True)
            st.markdown(
                f'<div class="sli-requirement">{html.escape(law.get("title",""))}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="sli-meta">{html.escape(law.get("jurisdiction",""))} '
                f'&middot; {html.escape(law.get("cap_no",""))} '
                f'&middot; Version: {html.escape(law.get("version_label",""))}</div>',
                unsafe_allow_html=True,
            )
            st.button("View PDF", key=f"lawpdf_{law['id']}", type="secondary",
                      disabled=True, help="Sample library item — no PDF attached.")


def _render_minutes(query: str) -> None:
    minutes = backend.list_library("minutes")
    minutes = [x for x in minutes if _matches(query, x.get("title"),
                                              x.get("body"))]
    if not minutes:
        st.info("No approved meeting minutes match.")
        return
    for m in minutes:
        with st.container(border=True):
            st.markdown('<div class="rk-card-marker"></div>',
                        unsafe_allow_html=True)
            head = (
                '<div class="sli-card-head">'
                '<span class="sli-pill version">Meeting minutes</span>'
                '<span class="sli-card-head-right">'
                f'{badges.status_badge(m.get("status","approved"))}'
                "</span></div>"
            )
            st.markdown(head, unsafe_allow_html=True)
            st.markdown(
                f'<div class="sli-requirement">{html.escape(m.get("title",""))}</div>',
                unsafe_allow_html=True,
            )
            related = ", ".join(m.get("related_laws") or [])
            st.markdown(
                f'<div class="sli-meta">{html.escape(m.get("body",""))} '
                f'&middot; Meeting: {html.escape(m.get("meeting_date",""))}'
                + (f' &middot; Related: {html.escape(related)}' if related else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            if m.get("summary"):
                st.markdown(
                    f'<div class="sli-meta">{html.escape(m["summary"])}</div>',
                    unsafe_allow_html=True,
                )
            st.button("View PDF", key=f"minpdf_{m['id']}", type="secondary",
                      disabled=True, help="Sample library item — no PDF attached.")


def render() -> None:
    layout.page_header(
        "Approved sources",
        "Library",
        "Approved documents only. These are the sole sources RAKAN can cite "
        "in its answers.",
    )
    st.markdown(
        '<div class="rk-notice">Only approved sources appear here and in AI '
        "answers.</div>",
        unsafe_allow_html=True,
    )

    query = st.text_input("Search", placeholder="Search by title, body or sector…",
                          label_visibility="collapsed")

    tab_laws, tab_minutes = st.tabs(["Laws", "Meeting minutes"])
    with tab_laws:
        _render_laws(query)
    with tab_minutes:
        _render_minutes(query)

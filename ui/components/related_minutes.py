"""'Related decisions' cards — meeting minutes shown after the checklist.

Minutes are an official internal record, NOT law. These cards never create a
condition and never change the headline; they are informational context.

Pure presentation. Receives the minutes list and a render_highlight callable.
"""

from __future__ import annotations

import html
from typing import Callable, List, Optional

import streamlit as st

from ui.components import citation


def render(
    minutes: List[dict],
    render_highlight: Callable[[str, int, List[List[float]]], Optional[bytes]],
) -> None:
    """Render each related meeting-minutes record as a card."""
    if not minutes:
        return
    st.markdown("##### Related decisions")
    st.markdown(
        '<div class="rk-notice">Meeting minutes are an official internal '
        "record, not law. They do not create requirements.</div>",
        unsafe_allow_html=True,
    )
    for m in minutes:
        with st.container(border=True):
            st.markdown('<div class="sli-card-marker"></div>',
                        unsafe_allow_html=True)
            st.markdown(
                '<div class="sli-card-head">'
                '<span class="rk-minutes-badge">Meeting minutes</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="sli-requirement">{html.escape(m.get("title",""))}</div>',
                unsafe_allow_html=True,
            )
            sect = m.get("section_no")
            ref = f"{html.escape(m.get('related_law',''))}"
            if sect:
                ref += f" &middot; s.{html.escape(str(sect))}"
            st.markdown(
                f'<div class="sli-meta">{html.escape(m.get("meeting_date",""))} '
                f'&middot; {html.escape(m.get("body",""))} &middot; {ref}</div>',
                unsafe_allow_html=True,
            )
            citation.render(
                quote=m.get("quote", ""),
                pdf_path=m.get("pdf_path"),
                page=int(m.get("page", 1) or 1),
                highlight_rects=m.get("highlight_rects", []),
                render_highlight=render_highlight,
                key=f"minutes_{m.get('id','M')}",
            )
            st.markdown(
                '<div class="sli-meta">Approved by Admin on '
                f'{html.escape(m.get("approved_on",""))}</div>',
                unsafe_allow_html=True,
            )

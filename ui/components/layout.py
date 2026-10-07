"""Shared layout primitives: the page-header pattern and small helpers.

Pure presentation — data in, markup out. No service or mock imports.
"""

from __future__ import annotations

import html

import streamlit as st


def page_header(eyebrow: str, title: str, lead: str) -> None:
    """Render the standard page header: eyebrow + serif H1 + lead paragraph."""
    st.markdown(
        f'<div class="rk-eyebrow">{html.escape(eyebrow)}</div>'
        f'<h1 class="rk-h1">{html.escape(title)}</h1>'
        f'<p class="rk-lead">{html.escape(lead)}</p>',
        unsafe_allow_html=True,
    )


def eyebrow(text: str) -> None:
    """Render a standalone eyebrow label (e.g. 'RESULT')."""
    st.markdown(
        f'<div class="rk-eyebrow">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )

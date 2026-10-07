"""First-line headline banner.

Displays the backend-provided `headline` string VERBATIM, coloured by status.
The UI never generates its own verdict wording (no "clear"/"approved"/"safe").
"""

from __future__ import annotations

import html

import streamlit as st

_VALID = {"red", "yellow", "none", "abstain"}


def render(headline: str, status: str) -> None:
    """Render the headline banner exactly as provided, styled by status."""
    cls = status if status in _VALID else "none"
    # headline comes from the backend and is shown verbatim; we only escape
    # it to keep the markup safe. The leading emoji is part of the string.
    st.markdown(
        f'<div class="sli-headline {cls}">{html.escape(headline)}</div>',
        unsafe_allow_html=True,
    )

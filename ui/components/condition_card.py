"""One checklist item (a single legal condition).

Pure presentation. Receives a Condition dict plus a render_highlight callable
(forwarded to the citation block). Never imports services or mock data.
"""

from __future__ import annotations

import html
from typing import Callable, List, Optional

import streamlit as st

from ui.components import badges, citation


def render(
    condition: dict,
    render_highlight: Callable[[str, int, List[List[float]]], Optional[bytes]],
    related_count: int = 0,
) -> None:
    """Render a single condition as a card.

    related_count: number of meeting-minutes records related to this law/
    section. When > 0 a small hint points to the Related decisions section.
    """
    cid = condition.get("id", "C")
    sector = condition.get("sector", "")
    requirement = condition.get("requirement", "")
    why = condition.get("why", "")
    severity = condition.get("severity", "info")
    matched = condition.get("matched_wording", "")
    law_title = condition.get("law_title", "")
    section_no = condition.get("section_no", "")
    page = int(condition.get("page", 1) or 1)
    version_label = condition.get("version_label", "")
    in_force_date = condition.get("in_force_date", "")
    not_yet = bool(condition.get("not_yet_in_force", False))
    pending_newer = condition.get("pending_newer_version")

    # Human-review hint depends on severity.
    review_hint = (
        "Human review recommended" if severity != "red" else "Mandatory wording"
    )

    # Use a real bordered container so the card look wraps the actual widgets
    # (expander, buttons), not just the HTML string blocks. The marker div is
    # the hook our CSS uses to style this specific container as a card.
    with st.container(border=True):
        st.markdown('<div class="sli-card-marker"></div>', unsafe_allow_html=True)

        # Header: severity pill (top-left) + sector chip (top-right).
        header = (
            '<div class="sli-card-head">'
            f"{badges.severity_badge(severity)}"
            '<span class="sli-card-head-right">'
            f"{badges.sector_chip(sector)}"
            "</span>"
            "</div>"
        )
        st.markdown(header, unsafe_allow_html=True)

        # Matched legal wording line.
        st.markdown(
            '<div class="sli-wording">Legal wording: '
            f"&lsquo;{html.escape(matched)}&rsquo; &middot; {review_hint}</div>",
            unsafe_allow_html=True,
        )

        # Requirement text.
        st.markdown(
            f'<div class="sli-requirement">{html.escape(requirement)}</div>',
            unsafe_allow_html=True,
        )

        # Meta line: law · s.X · p.N · Version · in force (single muted line).
        ref = (
            f"{html.escape(law_title)} &middot; s.{html.escape(section_no)} "
            f"&middot; p.{page}"
        )
        if not_yet:
            version_part = f"Version: {html.escape(version_label)} &middot; Not yet in force"
        else:
            version_part = (
                f"Version: {html.escape(version_label)} &middot; "
                f"in force: {html.escape(in_force_date)}"
            )
        st.markdown(
            f'<div class="sli-meta">{ref} &middot; {version_part}</div>',
            unsafe_allow_html=True,
        )

        # Pending newer version banner.
        if pending_newer and pending_newer.get("uploaded"):
            st.markdown(
                '<div class="sli-warn">⚠ A newer version (uploaded '
                f"{html.escape(pending_newer['uploaded'])}) is pending legal "
                "review.</div>",
                unsafe_allow_html=True,
            )

        # Collapsed explanation.
        with st.expander("Why this applies"):
            st.write(why)

        # Citation block (quote + highlighted page + download).
        citation.render(
            quote=condition.get("quote", ""),
            pdf_path=condition.get("pdf_path"),
            page=page,
            highlight_rects=condition.get("highlight_rects", []),
            render_highlight=render_highlight,
            key=f"cite_{cid}",
        )

        # Link to related meeting minutes shown lower in the result.
        if related_count:
            plural = "s" if related_count != 1 else ""
            st.markdown(
                f'<div class="rk-related-link">▾ {related_count} related '
                f"decision{plural} — see “Related decisions” below.</div>",
                unsafe_allow_html=True,
            )

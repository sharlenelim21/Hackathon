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
) -> None:
    """Render a single condition as a card."""
    # Real backend fields can be present-but-None (e.g. in_force_date,
    # version_label, section_no), so coerce every string field with `or ""`
    # — a plain .get(key, "") still returns None when the key exists.
    cid = condition.get("id") or "C"
    sector = condition.get("sector") or ""
    requirement = condition.get("requirement") or ""
    why = condition.get("why") or ""
    severity = condition.get("severity") or "info"
    matched = condition.get("matched_wording") or ""
    law_title = condition.get("law_title") or ""
    section_no = condition.get("section_no") or ""
    page = int(condition.get("page") or 1)
    version_label = condition.get("version_label") or ""
    in_force_date = condition.get("in_force_date") or ""
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

        # Matched legal wording line (only when the backend supplied wording).
        if matched:
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
        # Build from parts so missing fields are simply omitted.
        parts = [html.escape(law_title)] if law_title else []
        if section_no:
            parts.append(f"s.{html.escape(section_no)}")
        parts.append(f"p.{page}")
        if version_label:
            parts.append(f"Version: {html.escape(version_label)}")
        if not_yet:
            parts.append("Not yet in force")
        elif in_force_date:
            parts.append(f"in force: {html.escape(in_force_date)}")
        st.markdown(
            f'<div class="sli-meta">{" &middot; ".join(parts)}</div>',
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

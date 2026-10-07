"""Badge/pill renderers. Pure presentation — data in, HTML out.

These return HTML strings so callers can compose them inline inside a card
header. Nothing here imports services or mock data.
"""

from __future__ import annotations

import html

# Map a condition severity to its pill label + CSS class.
_SEVERITY = {
    "red": ("🔴 Mandatory", "red"),
    "yellow": ("🟡 Conditional", "yellow"),
    "info": ("⚪ Information", "info"),
}

# Human-friendly labels for workflow statuses.
_STATUS_LABEL = {
    "approved": "Approved",
    "pending": "Pending",
    "rejected": "Rejected",
    "needs_review": "Needs review",
}


def severity_badge(severity: str) -> str:
    """Pill for a condition severity (red / yellow / info)."""
    label, cls = _SEVERITY.get(severity, _SEVERITY["info"])
    return f'<span class="sli-pill {cls}">{label}</span>'


def status_badge(status: str) -> str:
    """Pill for an item/trigger/law status."""
    label = _STATUS_LABEL.get(status, status)
    return f'<span class="sli-pill status-{html.escape(status)}">{html.escape(label)}</span>'


def version_badge(version_label: str) -> str:
    """Pill for a version label."""
    return f'<span class="sli-pill version">{html.escape(version_label)}</span>'


def sector_chip(sector: str) -> str:
    """Navy pill for a sector."""
    return f'<span class="sli-pill sector">{html.escape(sector)}</span>'

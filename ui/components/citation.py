"""Citation block: verbatim quote + highlighted page image + PDF download.

Pure presentation. The caller passes a `render_highlight` callable so this
component does not import the backend directly (keeps the no-service rule:
components receive everything they need, including behaviour, as arguments).
"""

from __future__ import annotations

import html
from typing import Callable, List, Optional

import streamlit as st


def render(
    *,
    quote: str,
    pdf_path: Optional[str],
    page: int,
    highlight_rects: List[List[float]],
    render_highlight: Callable[[str, int, List[List[float]]], Optional[bytes]],
    key: str,
) -> None:
    """Render the quote box, a highlighted-page toggle, and a download button.

    The two actions sit in one row as small secondary buttons. "View
    highlighted page" toggles an inline image (stored per-key in session_state
    so it survives reruns); "Download PDF" appears only when pdf_path exists.

    Args:
        quote: verbatim legal quote (shown in the serif law-book box).
        pdf_path: path to the source PDF, or None if unavailable.
        page: 1-based page number of the quote.
        highlight_rects: rectangles to highlight on the page.
        render_highlight: callable returning a PNG (bytes) or None.
        key: unique key prefix for Streamlit widgets in this block.
    """
    # Serif "law book" quote box.
    st.markdown(
        f'<div class="sli-quote">&ldquo;{html.escape(quote or "")}&rdquo;</div>',
        unsafe_allow_html=True,
    )

    show_key = f"{key}_show_page"

    # Action row: view (toggle) + download, both small secondary buttons.
    col_view, col_dl = st.columns(2)
    if col_view.button(
        "View highlighted page", key=f"{key}_view", type="secondary",
        use_container_width=True,
    ):
        st.session_state[show_key] = not st.session_state.get(show_key, False)

    if pdf_path:
        pdf_bytes = _read_pdf(pdf_path)
        if pdf_bytes is not None:
            col_dl.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name=pdf_path.split("/")[-1],
                mime="application/pdf",
                key=f"{key}_dl",
                type="secondary",
                use_container_width=True,
            )
        else:
            col_dl.caption("PDF referenced but not available here.")

    # Inline highlighted page when toggled on.
    if st.session_state.get(show_key, False):
        image_bytes: Optional[bytes] = None
        if pdf_path:
            image_bytes = render_highlight(pdf_path, page, highlight_rects)
        if image_bytes:
            st.image(image_bytes, caption=f"Page {page}", use_container_width=True)
        else:
            # Graceful placeholder when no PDF/render is available (demo mode).
            st.info(
                "Highlighted page preview is not available in this environment. "
                "In production this shows the source page with the quote "
                "highlighted."
            )


def _read_pdf(pdf_path: str) -> Optional[bytes]:
    """Read PDF bytes for the download button, or None if unavailable."""
    try:
        with open(pdf_path, "rb") as fh:
            return fh.read()
    except OSError:
        return None

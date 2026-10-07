"""Design system CSS for the RAKAN frontend.

Law-firm palette: Royal Navy, Matte Gold, Cream White, Charcoal, White.
Gold is used for accents/borders/backgrounds only — never as text on white
or cream, which would fail WCAG AA contrast.

Selector notes:
- We prefer our own classes (rk-* / sli-*, injected via st.markdown
  unsafe_allow_html) so we do not depend on Streamlit's internal DOM.
- Selectors that target Streamlit's data-testid attributes are the most
  stable hook Streamlit exposes but can still change on upgrade. Each is
  marked FRAGILE.

IMPORTANT (diagnosed bug): do NOT use a blanket
`section[data-testid="stSidebar"] * { color: ... }` rule. It recolours text
inside inputs, selects and the segmented control too, making their text
invisible on white fields. Colour only our own elements + plain markdown.
"""

from __future__ import annotations

import streamlit as st

# Palette (kept as Python constants for the .sli-* result components).
NAVY = "#1E2A38"
GOLD = "#C8A45D"
GOLD_DARK = "#B8944D"
GOLD_INK = "#8A6D2F"      # gold-dark text that passes AA on cream (eyebrow)
CREAM = "#F3E9D8"
CHARCOAL = "#2B2B2B"
WHITE = "#FFFFFF"
SEV_RED = "#A63D2F"
SEV_AMBER = "#B7791F"
SEV_INFO = "#5B6573"
CARD_BORDER = "#E4DCCB"
MUTED = "#5B6573"

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Inter:wght@400;500;600&display=swap');

:root{
  --navy:#1E2A38;--gold:#C8A45D;--gold-dark:#B8944D;--gold-ink:#8A6D2F;
  --cream:#F3E9D8;--ink:#2B2B2B;--muted:#5B6573;--line:#E4DCCB;
  --red:#A63D2F;--amber:#B7791F;
}

::selection{background:var(--gold);color:var(--navy);}
::-moz-selection{background:var(--gold);color:var(--navy);}

/* ===== Chrome hiding (product look) ===================================== */
/* FRAGILE: Streamlit header/decoration/toolbar/deploy testids. We keep the
   header element present (transparent) so the sidebar expand button stays. */
[data-testid="stDecoration"]{display:none !important;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"]{display:none !important;}
/* The floating deploy / "rocket" button and the toolbar actions wrapper that
   holds it. Verified these testids exist in the installed Streamlit. */
[data-testid="stAppDeployButton"],
[data-testid="stDeployButton"],
[data-testid="stToolbarActions"]{display:none !important;}

/* ===== Main area layout ================================================= */
/* FRAGILE: main block container. */
.block-container{
  max-width:960px;
  padding-top:2rem;
  padding-bottom:3rem;
}

/* ===== Typography ======================================================= */
/* IMPORTANT (diagnosed bug): do NOT set font-family on *, span, div or
   [class*="st-"] — those selectors also hit Streamlit's Material icon spans
   and replace the icon glyphs with the ligature text ("upload_file", "rule").
   Scope the body font to specific text targets only. */
html, body, p, li, label, input, textarea, button, select,
.stMarkdown, .rk-lead, .rk-chip, .rk-hint, .rk-notice{
  font-family:'Inter',-apple-system,'Segoe UI',sans-serif;
}
.block-container h1,.block-container h2,.block-container h3,
.rk-h1,.rk-h2{
  font-family:'Source Serif 4',Georgia,'Times New Roman',serif;
  color:var(--navy);
}
/* Keep Material Symbols on the icon font no matter what. FRAGILE: icon
   testid / class names from the installed Streamlit version. */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-icons{
  font-family:'Material Symbols Rounded','Material Icons' !important;
}
.block-container p,.block-container li{color:var(--ink);}
/* Captions/help at least --muted on cream (AA). FRAGILE: caption testid. */
div[data-testid="stCaptionContainer"],
div[data-testid="stCaptionContainer"] p{color:var(--muted) !important;}

/* ===== Page-header pattern ============================================== */
.rk-eyebrow{
  font:600 11px/1 Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;
  color:var(--gold-ink);margin:0 0 6px;
}
.rk-h1{font-size:2rem;margin:0 0 .35rem;line-height:1.15;}
.rk-lead{font-size:16px;color:var(--muted);max-width:680px;margin:0 0 1.1rem;line-height:1.5;}

/* ===== Coverage chips =================================================== */
.rk-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 1.1rem;}
.rk-chip{
  display:inline-flex;align-items:center;gap:6px;background:#fff;
  border:1px solid var(--line);border-radius:999px;padding:5px 12px;
  font:400 13px Inter,sans-serif;color:var(--ink);
}
.rk-chip b{color:var(--navy);}

/* ===== Cards ============================================================ */
.rk-card{
  background:#fff;border:1px solid var(--line);border-radius:14px;
  padding:20px 22px;
  box-shadow:0 1px 2px rgba(30,42,56,.04),0 6px 18px rgba(30,42,56,.05);
  margin-bottom:14px;
}
/* Match st.container(border=True) to .rk-card. FRAGILE: bordered-container
   testid. Only containers that carry our marker get the full card look. */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.rk-card-marker){
  background:#fff;border:1px solid var(--line) !important;border-radius:14px;
  box-shadow:0 1px 2px rgba(30,42,56,.04),0 6px 18px rgba(30,42,56,.05);
  margin-bottom:14px;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.rk-card-marker) > div{
  padding:4px 6px;
}

/* ===== "How RAKAN works" steps ========================================== */
.rk-step-num{
  width:30px;height:30px;border-radius:50%;background:var(--navy);
  color:var(--gold);font:700 15px Inter,sans-serif;
  display:grid;place-items:center;margin-bottom:8px;
}
.rk-step-title{font:600 14px Inter,sans-serif;color:var(--navy);margin-bottom:2px;}
.rk-step-body{font:400 13px/1.4 Inter,sans-serif;color:var(--muted);}

/* ===== Form section headings (officer upload) =========================== */
.rk-form-section{
  font:600 13px Inter,sans-serif;color:var(--navy);
  letter-spacing:.02em;margin:.2rem 0 .2rem;
}
.rk-form-num{color:var(--gold-ink);font-weight:700;margin-right:6px;}

/* ===== Notices ========================================================== */
.rk-notice{font-size:13px;color:var(--muted);margin:.5rem 0 .2rem;line-height:1.45;}

/* ===== Buttons ========================================================== */
/* FRAGILE: button testids. Primary = gold/navy; secondary = white/navy. */
button[data-testid="stBaseButton-primary"]{
  background:var(--gold);color:var(--navy);border:1px solid var(--gold);
  border-radius:10px;font-weight:600;
}
button[data-testid="stBaseButton-primary"]:hover:enabled{
  background:var(--gold-dark);color:var(--navy);border-color:var(--gold-dark);
}
button[data-testid="stBaseButton-primary"]:disabled{
  background:#D9CBAE;color:#6B6451;border-color:#D9CBAE;
}
button[data-testid="stBaseButton-secondary"]{
  background:#fff;color:var(--navy);border:1px solid var(--line);
  border-radius:10px;font-weight:600;
}
button[data-testid="stBaseButton-secondary"]:hover:enabled{
  border-color:var(--gold);color:var(--navy);
}

/* ===================================================================== */
/* SIDEBAR                                                                */
/* ===================================================================== */
/* FRAGILE: sidebar testid + inner wrapper. */
[data-testid="stSidebar"]{width:280px !important;min-width:280px !important;}
[data-testid="stSidebar"] > div{background:var(--navy);}
/* Prevent horizontal scroll in the sidebar; keep children within width. */
[data-testid="stSidebarContent"]{overflow-x:hidden;}
[data-testid="stSidebar"] *{max-width:100%;}
[data-testid="stSidebar"] [data-testid="stButtonGroup"]{flex-wrap:wrap;}

/* Colour ONLY our own text + plain markdown/captions — never inputs. */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption{color:#E9E1D2;}

.rk-label{
  font:600 11px/1 Inter,sans-serif;letter-spacing:.12em;text-transform:uppercase;
  color:rgba(243,233,216,.6);margin:22px 0 8px;
}
.rk-hint{font-size:12.5px;color:rgba(243,233,216,.72);margin-top:6px;line-height:1.45;}

.rk-brand{
  display:flex;gap:12px;align-items:center;padding:6px 0 14px;
  border-bottom:1px solid rgba(243,233,216,.14);
}
.rk-mark{
  width:42px;height:42px;border-radius:10px;background:var(--gold);color:var(--navy);
  display:grid;place-items:center;font:700 24px 'Source Serif 4',Georgia,serif;
  flex:0 0 auto;
}
.rk-name{font:700 20px 'Source Serif 4',Georgia,serif;letter-spacing:.08em;color:#FFFFFF;}
.rk-full{font:500 11px/1.35 Inter,sans-serif;color:var(--gold);margin-top:2px;}

.rk-badge{
  display:inline-block;background:var(--gold);color:var(--navy);
  font:700 10px Inter,sans-serif;letter-spacing:.08em;padding:3px 7px;border-radius:5px;
}
.rk-demo-row{display:flex;align-items:center;gap:10px;margin-bottom:4px;}
.rk-demo-row .rk-label{margin:22px 0 0;}

/* Segmented control — FRAGILE: Streamlit segmented_control testids. */
[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_control"]{
  background:transparent;color:#E9E1D2;border-color:rgba(243,233,216,.28);
}
[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_control"]:hover{
  background:rgba(243,233,216,.08);color:#FFFFFF;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_control"] p{color:inherit !important;}
[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_controlActive"]{
  background:var(--gold);color:var(--navy);border-color:var(--gold);font-weight:600;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-segmented_controlActive"] p{color:var(--navy) !important;}

/* Page links — FRAGILE: stPageLink-NavLink testid. */
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{border-radius:8px;padding:6px 10px;}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p{color:#E9E1D2;}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:rgba(243,233,216,.08);}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"]{
  background:rgba(200,164,93,.16);box-shadow:inset 3px 0 0 var(--gold);
}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] p{
  color:#FFFFFF;font-weight:600;
}

/* ===== Inputs everywhere (sidebar included): dark text on light fields == */
/* FRAGILE: baseweb select/input/popover internals. */
[data-baseweb="select"] > div,[data-baseweb="input"] > div,textarea,input{
  background:#FFFFFF !important;color:var(--ink) !important;
}
[data-baseweb="select"] *{color:var(--ink) !important;}
[data-baseweb="select"]:focus-within > div,
[data-baseweb="input"]:focus-within > div{
  border-color:var(--gold) !important;box-shadow:0 0 0 2px rgba(200,164,93,.4) !important;
}
textarea:focus,input:focus{
  border-color:var(--gold) !important;box-shadow:0 0 0 2px rgba(200,164,93,.4) !important;
}
[data-baseweb="popover"] li{color:var(--ink);background:#FFFFFF;}
[data-baseweb="popover"] li:hover{background:var(--cream);}
[data-baseweb="popover"] li[aria-selected="true"]{background:#E9DCC2;color:var(--navy);}
::placeholder{color:var(--muted) !important;}

/* ===================================================================== */
/* RESULT COMPONENTS (.sli-* — unchanged behaviour)                       */
/* ===================================================================== */
.sli-card{
  background:#fff;border:1px solid var(--line);border-radius:14px;
  padding:16px;margin-bottom:12px;
  box-shadow:0 1px 2px rgba(30,42,56,.04),0 6px 18px rgba(30,42,56,.05);
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(> div .sli-card-marker){
  background:#fff;border:1px solid var(--line) !important;border-radius:14px;
  box-shadow:0 1px 2px rgba(30,42,56,.04),0 6px 18px rgba(30,42,56,.05);margin-bottom:12px;
}
.sli-card-head{display:flex;align-items:center;justify-content:space-between;gap:.5rem;flex-wrap:wrap;margin-bottom:.4rem;}
.sli-card-head-right{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;}
.sli-requirement{font-size:16px;font-weight:600;color:var(--ink);margin:.4rem 0 .3rem;}
.sli-meta{color:var(--muted);font-size:.85rem;margin:.15rem 0;}
.sli-wording{color:var(--muted);font-size:.85rem;font-style:italic;}

.sli-headline{
  border-radius:12px;padding:1rem 1.2rem;font-family:'Source Serif 4',Georgia,serif;
  font-size:21px;font-weight:600;color:var(--navy);margin-bottom:.6rem;border-left:6px solid;
}
.sli-headline.red{background:#F6E4E1;border-color:var(--red);}
.sli-headline.yellow{background:#FBF1DD;border-color:var(--amber);}
.sli-headline.none{background:#ECEEF0;border-color:var(--muted);}
.sli-headline.abstain{background:#ECEEF0;border-color:var(--muted);}
.sli-summary{display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;margin-bottom:1rem;}

.sli-pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.78rem;font-weight:600;line-height:1.6;white-space:nowrap;}
.sli-pill.red{background:#F6E4E1;color:var(--red);border:1px solid var(--red);}
.sli-pill.yellow{background:#FBF1DD;color:var(--amber);border:1px solid var(--amber);}
.sli-pill.info{background:#ECEEF0;color:var(--muted);border:1px solid var(--muted);}
.sli-pill.sector{background:var(--navy);color:var(--cream);}
.sli-pill.status-approved{background:#E3EFE6;color:#246B45;border:1px solid #246B45;}
.sli-pill.status-pending{background:#FBF1DD;color:var(--amber);border:1px solid var(--amber);}
.sli-pill.status-rejected{background:#F6E4E1;color:var(--red);border:1px solid var(--red);}
.sli-pill.status-needs_review{background:var(--navy);color:var(--gold);border:1px solid var(--gold);}
.sli-pill.version{background:#ECEEF0;color:var(--ink);border:1px solid rgba(30,42,56,.2);}

.sli-chip{display:inline-block;background:var(--cream);border:1px solid var(--gold);color:var(--ink);border-radius:8px;padding:4px 10px;margin:0 6px 6px 0;font-size:.85rem;}
.sli-chip b{color:var(--navy);}

.sli-quote{font-family:'Source Serif 4',Georgia,'Times New Roman',serif;background:var(--cream);border-left:5px solid var(--gold);color:var(--ink);padding:.9rem 1.1rem;border-radius:6px;font-size:1rem;line-height:1.5;margin:.5rem 0;}
.sli-warn{background:#FBF1DD;border:1px solid var(--amber);color:#6B4A12;border-radius:8px;padding:.7rem .9rem;margin:.4rem 0;font-size:.9rem;}
.sli-result-label{color:var(--muted);font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.3rem;}
/* Related-decisions link inside a condition card + navy-outline minutes badge */
.rk-related-link{color:var(--gold-ink);font-size:.82rem;font-weight:600;margin-top:.4rem;}
.rk-minutes-badge{display:inline-block;border:1px solid var(--navy);color:var(--navy);background:#fff;border-radius:999px;padding:2px 10px;font-size:.78rem;font-weight:600;}
.sli-footer{color:var(--muted);font-size:.82rem;font-style:italic;border-top:1px solid rgba(30,42,56,.12);padding-top:.6rem;margin-top:1rem;}
</style>
"""


def inject_css() -> None:
    """Inject the design-system CSS. Must run once per rerun, before nav."""
    st.markdown(_CSS, unsafe_allow_html=True)

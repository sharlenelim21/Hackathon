# Project structure (single Streamlit app)

```
Hackathon/
├── streamlit_app.py            ← frontend team (DONE). Entry point / Streamlit Cloud main file
├── ui/                         ← frontend team (DONE)
│   ├── backend.py              the contract: USE_MOCK=True → mocks; False → `from services import …`
│   └── …                       screens, components, mock data
├── .streamlit/
│   ├── config.toml             ← frontend team: theme / colour palette
│   └── secrets.toml            LOCAL ONLY, gitignored (LLM keys)
├── services/                   ← Jy (backend; no Streamlit UI APIs)
│   ├── __init__.py             PUBLIC FACADE = docs/SERVICE_CONTRACT.md (exact names/keys), lazy init, ServiceError, health()
│   ├── config.py               settings (env → st.secrets → .env), paths, TAGS, SEVERITY_RULES, flags
│   ├── db.py                   connect(), init_schema(), kb_version, audit(), now_iso()
│   ├── schemas.py              PlanOut/ConditionsOut (pydantic) + TypedDicts for contract shapes
│   ├── llm.py                  call_llm_json(); providers openai_compatible | anthropic | fake
│   ├── prompts.py              PLAN_SYSTEM, CONDITIONS_SYSTEM, user-message builders
│   ├── pdftext.py              PyMuPDF cleaned page text, footnotes, words
│   ├── parser.py               section tree (ToC run, body run, headings, amend notes, pages fallback)
│   ├── laws.py                 preview/submit, diff, pending items, decide (approve/reject), triggers
│   ├── retrieval.py            ToC text, triggers, BM25, cross-refs, candidate merge
│   ├── verify.py               normalize(), verify_quote(), find_highlight()
│   ├── severity.py             classify() → (severity, matched_wording); status_and_headline()
│   ├── pipeline.py             run_check() orchestration → contract dict
│   ├── render.py               render_highlight()
│   └── seed.py                 seed_if_empty()
├── seed/                       pdfs/ (official LawNet PDFs), laws.json, triggers.json, eval.json
├── scripts/                    smoke_pdf.py, smoke_llm.py, eval.py
├── tests/                      test_*.py, fixtures/llm/*.json
├── data/                       gitignored, created at runtime (app.db, files/, renders/)
├── requirements.txt            repo root (Streamlit Cloud)
├── docs/                       SERVICE_CONTRACT.md, RUNBOOK.md, BUILD_STATUS.md
└── .kiro/                      steering + specs
```

Rules:
- The UI reaches the backend **only** through `ui/backend.py` → `services` (public functions in `services/__init__.py`).
- Folder ownership avoids merge conflicts between `hackathon/backend` and `hackathon/frontend`:
  backend work touches `services/`, `seed/`, `scripts/`, `tests/`; UI work touches `streamlit_app.py`, `ui/`, `.streamlit/config.toml`. Both may touch `requirements.txt`, so merge it by hand.
- The frontend contract is fixed. Backend changes may only **add** keys or optional parameters, and must update `docs/SERVICE_CONTRACT.md` in the same commit.
- Don't commit `data/`, `.venv/`, `.env` or `.streamlit/secrets.toml`.

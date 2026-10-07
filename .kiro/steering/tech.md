# Tech stack: one Streamlit app (decided by the team)

| Layer | Choice |
|---|---|
| Frontend + backend | **One Streamlit app** (Python). UI in `streamlit_app.py` + `ui/` (done); logic in `services/` |
| Hosting | **Streamlit Community Cloud** (free, deploys from GitHub) |
| Data | SQLite at `data/app.db`, **auto-seeded on startup** from `seed/` (PDFs + JSON) |
| Files | `data/files/<sha256>.pdf` (uploads) and `data/renders/` |
| AI | One provider behind `services/llm.py` (see below) |

- **Python 3.12** locally and on Streamlit Cloud (Advanced settings → Python 3.12; Cloud supports 3.9–3.13).
- **Streamlit**, **PyMuPDF** (`import pymupdf`), **rank-bm25**, **pydantic v2**, **python-dotenv**, **pytest**, plus the LLM SDK (`openai` for OpenAI-compatible providers; `anthropic` only if the team picks Claude).
- Do NOT use pypdf: it took 16 s on the 266-page Land Code in our test and gives no word boxes.
- `requirements.txt` lives at the **repo root** (Streamlit Cloud installs from it).

## LLM (`services/llm.py` → `call_llm_json(name, system, user) -> dict`)
- `LLM_PROVIDER=openai_compatible` (default): `openai` package with `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. Covers Google Gemini (OpenAI-compatible endpoint), DeepSeek, OpenAI and OpenRouter. JSON mode `response_format={"type":"json_object"}`; the prompt must contain the word "json"; `temperature=0`.
- `LLM_PROVIDER=anthropic` (only if the team picks Claude): official `anthropic` SDK, structured outputs per its docs; do not send `temperature` to current Claude models; check `stop_reason`.
- `LLM_PROVIDER=fake`: canned JSON from `tests/fixtures/llm/<name>.json`. Used by all tests. Results carry `llm_provider`, so the UI can show a "Replay mode" badge.

## Secrets and settings
- Locally: `.streamlit/secrets.toml` (gitignored) or `.env`. On Cloud: App settings → Secrets (TOML), root-level keys, e.g. `LLM_API_KEY = "…"`.
- `services/config.py` reads: environment variables → `streamlit.secrets` (lazy import inside try/except) → `.env` → defaults. `services/` uses no Streamlit UI APIs, so it stays testable with plain pytest.
- `services` initialises itself on the first call (schema + seed if empty). The contract has no init function.
- Never commit keys. The repo may be public.

## Commands (PowerShell, repo root)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install streamlit pymupdf rank-bm25 pydantic python-dotenv openai pytest
.\.venv\Scripts\python -m pip freeze > requirements.txt
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python -m streamlit run streamlit_app.py
.\.venv\Scripts\python -m pytest -q
```

## Streamlit rules (UI and backend must both respect these)
- Streamlit **reruns the whole script on every click**. `check_action()` must be called only inside
  the Check button handler, with the result kept in `st.session_state`; never call the LLM at top level.
- `services` must be safe to call from several sessions at once: a lock around lazy init and one
  SQLite connection per operation.
- No `st.cache_data` on anything that changes after approvals (laws, pending, triggers, audit).
- The cited page is shown with `st.image(render_highlight(pdf_path, page, rects))`. No static file serving needed.

## Known pitfalls (Windows and Cloud)
- **One SQLite connection per operation** (`db.connect()`): Streamlit runs sessions in different threads and Python sqlite3 objects can't cross threads. Use `timeout=10`, WAL, foreign keys, Row factory.
- The Windows console is cp1252 and crashes printing law text ("⎯"). Set `PYTHONIOENCODING=utf-8` and open files with `encoding="utf-8"`.
- **Cloud storage is temporary:** a restart or redeploy wipes `data/`. `services` re-seeds automatically on the first call, but live uploads and approvals made in the demo are lost on restart (fine within one demo session).
- **Cloud apps sleep after 12 h without traffic.** Open the app 10+ minutes before judging.
- Pages are **1-based PDF page numbers** in DB and service results; convert to 0-based only inside PyMuPDF.
- Store uploads as `data/files/<sha256>.pdf`; never use original filenames (LawNet names have spaces and brackets).
- Pin versions after the first successful install.

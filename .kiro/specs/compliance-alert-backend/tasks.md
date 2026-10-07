# Implementation Plan (`services` package, owned by Jy)

The frontend is already built against `docs/SERVICE_CONTRACT.md` with mocks. These tasks build
the real `services` package so the UI can switch `USE_MOCK = False`.

Run tasks in order. Times are budgets inside the 3-hour build. If a task overruns its timebox,
apply its Plan B and move on. Never cut: verified citations (Req 3), conditions-first status
(Req 2), approval gate (Req 7).

- [ ] 1. Setup and smoke tests (0:00–0:15)
  - [ ] 1.1 Create `services/`, `scripts/`, `tests/` per structure.md; venv (Python 3.12) and dependencies (tech.md); `requirements.txt` at the repo root (merge with the UI's needs: streamlit, pymupdf); `.gitignore`: `.venv/`, `data/`, `.env`, `.streamlit/secrets.toml`
  - [ ] 1.2 `scripts/smoke_pdf.py`: open `seed/pdfs/NREO_Cap84_LawNet2024.pdf` with PyMuPDF; print page_count (expect 45) and the first 300 characters of PDF page 23 (expect the s.11A heading); get words on page 25; add a highlight annot on the first 5 words; save the PNG to `data/renders/smoke.png`. Must run without errors.
  - [ ] 1.3 `services/config.py` (settings: env → st.secrets lazy → .env; TAGS = the `tags` list in `seed/triggers.json`; SEVERITY_RULES from design §7; flags HIGHLIGHT/XREFS/BM25_K) and `services/llm.py` (providers `openai_compatible`, `fake`); `scripts/smoke_llm.py` makes one real JSON-mode call and prints the parsed dict
  - Plan B: LLM key or network fails → continue with `LLM_PROVIDER=fake`; fix the key in parallel
  - _Requirements: 10_

- [ ] 2. Database and schemas (0:15–0:25)
  - [ ] 2.1 `db.py`: `connect()` (timeout=10, WAL, foreign keys, Row factory), `init_schema()` with the DDL from design §2, `get_kb_version()`/`bump_kb_version()`, `audit()`, `now_iso()`
  - [ ] 2.2 `schemas.py`: pydantic models `PlanOut`, `ConditionsOut` (LLM validation) and TypedDicts mirroring the contract shapes
  - _Requirements: 6, 7, 9_

- [ ] 3. PDF text and section parser (0:25–0:55, TIMEBOX 30 min)
  - [ ] 3.1 `pdftext.py`: per-page cleaned lines (drop page-number lines, cut footnote blocks), words; open from a path or from bytes
  - [ ] 3.2 `parser.py`: algorithm in design §3.2 → `ParseResult(mode, sections, toc, warnings, page_count)`
  - [ ] 3.3 `tests/test_parser.py` with the real seed PDFs (assertions in design §12)
  - Plan B: if the Land Code still fails at 0:55, seed it with `parse_mode="pages"` and keep the NREO in sections mode; note it in docs/BUILD_STATUS.md
  - _Requirements: 6.4_

- [ ] 4. Laws, versions, approvals, triggers, seed (0:55–1:15)
  - [ ] 4.1 `laws.py`: `preview()`, `submit()` (validation, sha256 dedupe, store file, find/create law with a generated code, pending version, diff), `pending_items()`, `decide()` (unified ids: triggers = 1_000_000 + id), `propose_trigger()`, `pending_version_for()`; audit on every action
  - [ ] 4.2 `seed.py`: `seed_if_empty()` ingests `seed/laws.json` entries approved as `seed`, then loads `seed/triggers.json` (law_code → law_id) as approved
  - [ ] 4.3 `tests/test_laws.py` (design §12)
  - _Requirements: 6, 7, 8_

- [ ] 5. Retrieval (1:15–1:30)
  - [ ] 5.1 `retrieval.py`: `toc_text()`, `valid_keys()`, `triggers_for()`, `bm25_top()`, `xrefs()`, `merge_candidates()` with caches keyed by kb_version
  - [ ] 5.2 Test: keys from pending versions never appear; invented keys and tags are rejected
  - _Requirements: 4_

- [ ] 6. Verification, highlight, severity (1:30–1:45)
  - [ ] 6.1 `verify.py`: `normalize`, `tokens`, `verify_quote`, `find_highlight` (design §6)
  - [ ] 6.2 `severity.py`: `classify` (returns severity + matched_wording), `status_and_headline` (design §7)
  - [ ] 6.3 `render.py`: `render_highlight` (design §9)
  - [ ] 6.4 `tests/test_verify.py`, `tests/test_severity.py` (design §12)
  - Plan B: highlight not matching → set `HIGHLIGHT=0` and continue
  - _Requirements: 3, 5_

- [ ] 7. Check pipeline + public facade (1:45–2:05)
  - [ ] 7.1 `prompts.py`: PLAN_SYSTEM and CONDITIONS_SYSTEM verbatim from design §5, plus user-message builders
  - [ ] 7.2 `pipeline.py`: `run_check(text)` → plan call → candidates → conditions call → filter keys → verify → highlight → severity → status/headline → contract dict (ids "C1"…, `pdf_path` absolute, `page` = highlight page, extras)
  - [ ] 7.3 `services/__init__.py`: the public functions with **exact contract names and keys**, `_ensure_ready()` lazy thread-safe init + `seed_if_empty()`, `ServiceError`, `health()`
  - [ ] 7.4 `tests/fixtures/llm/plan.json` and `conditions.json` (one valid condition quoting NREO s.11A(3), one with a made-up quote, one with key `NREO:999`) and `tests/test_contract.py` (design §12)
  - _Requirements: 1, 2, 3, 9, 10_

- [ ] 8. INTEGRATION with the UI (2:05–2:20)
  - [ ] 8.1 Pull the frontend branch; set `USE_MOCK = False` in `ui/backend.py`; `streamlit run streamlit_app.py`; click through every screen: worker check, view highlighted source, upload preview, submit, pending list + diff, approve/reject, triggers, laws, audit
  - [ ] 8.2 Fix key/shape mismatches in `services/__init__.py` only (never ask the UI to change, unless a contract key is impossible)
  - _Requirements: all_

- [ ] 9. FEATURE FREEZE at 2:20. Live run, evaluation, deploy (2:20–2:45)
  - [ ] 9.1 With the real LLM run the 3 demo actions from `docs/RUNBOOK.md`; fix prompt or trigger issues only
  - [ ] 9.2 `scripts/eval.py`: run `seed/eval.json` through `check_action`, print per-case expected vs found section keys and status, pass rate, average time; record the numbers for the pitch
  - [ ] 9.3 Deploy (or redeploy) on Streamlit Community Cloud from the demo branch: main file `streamlit_app.py`, Python 3.12, secrets pasted in App settings; open the app once to confirm it seeds and answers
  - _Requirements: 1.3, 10_

- [ ] 10. Rehearsal (2:45–3:00): two full demo runs on the deployed app; record a backup video; update docs/BUILD_STATUS.md with what works

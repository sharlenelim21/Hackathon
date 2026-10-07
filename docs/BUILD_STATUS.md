# Build status and team notes

> **Status (2026-10-07):** frontend done on mocks (`ui/backend.py`, `USE_MOCK = True`).
> Backend (`services/`) is **planned, not yet coded**: it gets built during the hackathon with
> Kiro from `.kiro/specs/compliance-alert-backend/`. Seed data is ready in `seed/`.

## Who builds what
| Part | Owner | Works from |
|---|---|---|
| Streamlit UI (`streamlit_app.py`, `ui/`, theme) | Frontend teammates (**done**) | their own spec + `ui/backend.py` contract |
| Backend `services/` (parsing, retrieval, LLM, verification, approvals) | Jy | `.kiro/specs/compliance-alert-backend/` (Kiro runs `tasks.md` in order) |
| Contract between them | Frontend's `ui/backend.py`, mirrored in `docs/SERVICE_CONTRACT.md` | Backend matches it exactly; it may only **add** keys |
| Demo, pitch, deployment | Everyone | `docs/RUNBOOK.md` |

Integration: **2:05–2:20** into the build (`USE_MOCK = False`). Feature freeze: **2:20**.

## What's in the repo for the backend
| Path | What |
|---|---|
| `.kiro/steering/` | product rules, tech stack (Streamlit + Cloud pitfalls), folder ownership |
| `.kiro/specs/compliance-alert-backend/` | `requirements.md` (what), `design.md` (how: DB schema, PDF parser built around the real LawNet layout, prompts, verification), `tasks.md` (timed steps, each with a Plan B) |
| `docs/SERVICE_CONTRACT.md` | the frontend's contract + backend clarifications (1-based pages, unique ids, nullable fields, extra keys) |
| `docs/RUNBOOK.md` | pre-event checklist, 3-hour timeline, problems found + Plan B, demo script, judge Q&A, LLM provider choice |
| `seed/pdfs/` | official LawNet PDFs: NREO (Cap. 84) reprint 2024, Land Code (Cap. 81) reprint 2025 |
| `seed/laws.json`, `triggers.json`, `eval.json` | seed metadata, trigger rules on the frontend's 9 tags, 10 evaluation cases |

## Notes for the frontend team (no code changes needed)
1. **Pages are 1-based PDF pages.** In `render_highlight`, PyMuPDF needs `doc[page - 1]`. The backend also provides `render_highlight`; import it if you like.
2. **`list_pending` ids are unique across types:** versions use their id; triggers use `1_000_000 + trigger_id`. So `approve(item_id, note)` works without a type.
3. **Nullable fields:** `in_force_date` is usually `null` for the seed reprints. `highlight_rects` can be `[]` (show the page without boxes).
4. **Optional extras:** pass `reviewer=` to `approve`/`reject`, `proposed_by=`/`severity_override=` to `propose_trigger`, and `uploaded_by`/`source_authority` in upload `meta`. The audit log then shows real names; otherwise it says "Legal officer".
5. **Extra result keys you may show:** `dropped_unverified` ("1 unverified claim removed"), `source_authority` ("Unofficial copy" badge), `amend_notes` (chips), `llm_provider == "fake"` ("Replay mode" badge).
6. The **activity tags** are your fixed list; the seed trigger rules use exactly those 9 tags.

## How it works
```
worker action ─► 1) LLM "plan": facts, missing facts, activity tags, sections from the laws' table of contents
              ─► 2) structure-aware retrieval (no vector DB): trigger rules + table of contents + keyword search + cross-references
              ─► 3) LLM "conditions": requirement + verbatim quote per section
              ─► 4) code verifies every quote against the stored text (unverified → dropped and counted)
              ─► 5) code sets severity (legal wording or the officer's override) and builds the headline
              ─► result + highlight boxes for the source page
legal officer ─► upload PDF ─► parsed preview ─► submit (pending + diff) ─► approve/reject ─► searchable (audit-logged)
```

## Facts we checked (2026-10-07), so nobody gets caught out in Q&A
- Both seed PDFs have a real text layer. NREO: 45 pages, s.11A on PDF pages 23–25. Land Code: 266 pages, s.5 on PDF page 28. ([LawNet](https://lawnet.sarawak.gov.my/))
- NREO s.11A(1) lists activities that need an environmental report, including (h) landfill and municipal waste storage/treatment/recycling, (i) sewage plants, (f) rock extraction. s.11A(3) bars preparatory work before the Board approves the report; s.11A(6) makes contravention an offence (fine and/or imprisonment).
- **LawNet keeps only the latest version:** the 2024 Land Code link now returns 404 (an archived copy exists in the Internet Archive). This is why we archive versions ourselves.
- The EIA area thresholds are in the Prescribed Activities Order, which is not listed with the NREO's subsidiary legislation on LawNet's by-year list. We treat site area as a "missing fact" and never invent thresholds.
- **ADAM AI** (Sarawak civil service, launched 7 Jul 2026) is the comparator judges will know. ([UKAS](https://ukas.sarawak.gov.my/web/subpage/news_view/44571))
- Korea's "AI legal secretary" for civil servants (trial since Jul 2026) uses the same "reference, not legal judgement" framing. ([Malay Mail](https://www.malaymail.com/news/world/2026/07/13/south-korea-trials-ai-legal-secretary-to-help-public-officials-navigate-the-law/227392))

## Run locally (once `services/` exists)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
# put LLM_PROVIDER / LLM_BASE_URL / LLM_API_KEY / LLM_MODEL in .streamlit/secrets.toml (or LLM_PROVIDER = "fake")
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python -m streamlit run streamlit_app.py
```

## Rules for everyone
- Never invent law text, section numbers or thresholds, in the UI, the slides or the pitch.
- Never commit `.streamlit/secrets.toml`, `.env` or API keys.
- If you change a contract shape, update `docs/SERVICE_CONTRACT.md` in the same commit.

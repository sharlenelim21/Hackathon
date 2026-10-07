# Design: Compliance Impact Alert `services` package

## 1. Overview

```
Streamlit app (one process)
  streamlit_app.py / ui/*  ── frontend (DONE, mocks) ──►  ui/backend.py (USE_MOCK=False)
                                                              │  from services import …
                                                              ▼
services/__init__.py  (public functions = docs/SERVICE_CONTRACT.md; lazy init on first call)
  check_action(text) ──► pipeline.run_check()
     1. PLAN call (LLM): facts, missing_facts, tags (fixed list), ≤5 ToC keys
     2. retrieval: triggers(tags) ∪ ToC keys ∪ BM25 top5 ∪ cross-refs(≤3) → ≤10 sections
     3. CONDITIONS call (LLM): conditions with key + verbatim quote
     4. verify: drop invalid keys and unverified quotes → highlight rects (best page)
     5. severity (+ matched_wording) and status/headline (code) → contract dict
  render_highlight(pdf_path, page, rects) ──► render.py (PyMuPDF → PNG)
  upload_preview / submit_upload ──► laws.py → parser.py (→ pending version + diff)
  list_pending / approve / reject ──► laws.py (versions + triggers, unified ids)
                                     │
                     SQLite data/app.db  +  data/files/<sha256>.pdf   (data/ rebuilt from seed/ on startup)
```

## 2. Data model (`db.py: init_schema()`)

```sql
CREATE TABLE IF NOT EXISTS laws(
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,              -- 'NREO', 'LC'; generated for new laws (title initials, made unique)
  title TEXT NOT NULL,
  jurisdiction TEXT NOT NULL CHECK(jurisdiction IN ('Sarawak','Federal')),
  instrument_type TEXT NOT NULL DEFAULT 'Ordinance',
  cap_no TEXT,
  sector TEXT NOT NULL,
  created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS versions(
  id INTEGER PRIMARY KEY,
  law_id INTEGER NOT NULL REFERENCES laws(id),
  label TEXT NOT NULL,
  published_date TEXT, in_force_date TEXT, source_url TEXT,
  source_authority TEXT NOT NULL DEFAULT 'official' CHECK(source_authority IN ('official','unofficial')),
  file_path TEXT NOT NULL,                       -- absolute path data/files/<sha256>.pdf
  sha256 TEXT UNIQUE NOT NULL,
  page_count INTEGER NOT NULL,
  parse_mode TEXT NOT NULL CHECK(parse_mode IN ('sections','pages')),
  parse_warnings TEXT NOT NULL DEFAULT '[]',     -- JSON list
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','superseded')),
  uploaded_by TEXT NOT NULL, uploaded_at TEXT NOT NULL,
  reviewed_by TEXT, reviewed_at TEXT, review_note TEXT,
  diff_json TEXT);                                -- JSON or NULL

CREATE TABLE IF NOT EXISTS sections(
  id INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL REFERENCES versions(id),
  key TEXT NOT NULL,                  -- 'NREO:11A' (stable across versions)
  section_no TEXT NOT NULL,           -- '11A' or 'p23'
  part TEXT, heading TEXT,
  text TEXT NOT NULL,                 -- cleaned text (no page numbers, no footnote blocks)
  page_start INTEGER NOT NULL, page_end INTEGER NOT NULL,   -- 1-based PDF pages
  amend_notes TEXT NOT NULL DEFAULT '[]',                   -- JSON list
  ord INTEGER NOT NULL,
  UNIQUE(version_id, key));

CREATE TABLE IF NOT EXISTS triggers(
  id INTEGER PRIMARY KEY,
  activity_tag TEXT NOT NULL, law_id INTEGER NOT NULL REFERENCES laws(id), section_no TEXT NOT NULL,
  severity_override TEXT CHECK(severity_override IN ('red','yellow') OR severity_override IS NULL),
  note TEXT,
  status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected','needs_review')),
  proposed_by TEXT NOT NULL, proposed_at TEXT NOT NULL,
  reviewed_by TEXT, reviewed_at TEXT, review_note TEXT);

CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL,
  target_type TEXT NOT NULL, target_id INTEGER NOT NULL, note TEXT);

CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);  -- kb_version
```
Timestamps are ISO 8601 with +08:00. A law's "current version" is its single `approved` version.

## 3. Ingestion and parser (`pdftext.py`, `parser.py`)

### 3.1 What the real PDFs look like (checked on 2026-10-07)
Observed in the two seed PDFs, extracted with pypdf. PyMuPDF should give the same text; Task 1
confirms it.

| Fact | NREO (45 pages) | Land Code (266 pages) |
|---|---|---|
| Text layer | yes | yes (2 blank pages) |
| Front table of contents "N. Heading" | PDF pages ≈2–4 | PDF pages ≈2–27 |
| Body starts | PDF page 6 | s.5 on PDF page 28 |
| Section start lines | `1. This Ordinance…`, `2.⎯(1) In this…`, `*11A.⎯(1) The Board…` | `5.⎯(1) As from the 1st day…`, `6A.—(1) Any native community…` (PDF page 34) |
| Appended material | none | rules and forms from ≈ page 200 with their own numbering restarting at 1 |
| Amendment notes in text | e.g. `[Am. Cap. A12.]`, `[Ins. Cap. A120.]`, `[Am. Cap. A185/2019]` | ≈180, e.g. `[Sub. Swk. L.N. 109/2006.]` |

Other details:
- The dash after a section number is usually **U+23AF "⎯"**, sometimes an em dash **"—"**, never a plain hyphen.
- A leading `*` marks a footnote.
- The heading (marginal note) is printed on its own line(s) **directly above** the section start line, and can wrap onto 2 lines.
- Footnotes sit at the page bottom after a line of underscores (`_______________`), then `* See …`.
- The first non-empty line of each body page is the printed page number (PDF page − 1).

### 3.2 Algorithm
```
pdftext.page_texts(doc) -> list[PageText(pdf_page, lines, footnotes)]
  for each page: text = page.get_text("text"); lines = splitlines
    drop lines matching ^\s*\d{1,4}\s*$                      (printed page numbers)
    cut from the first line matching ^\s*_{5,}\s*$ to page end → footnotes
parser.parse(lines_by_page, law_code, mode, body_from, body_to) -> ParseResult
  SECTION_RE = r'^\s*\*?(\d{1,3}[A-Z]{0,2})\.(?=\s|[⎯—–-])'
  PART_RE    = r'^\s*PART\s+([IVXLC]+|\d+)\b'
  AMEND_RE   = r'\[((?:Am|Ins|Sub|Rep|Del)\.[^\]]{1,80})\]'
  1. hits = all SECTION_RE matches (line index, page, number), limited to body_from..body_to if given
  2. split into runs: new run when number == 1 or numeric value drops by > 5
  3. inside each run keep monotonic hits only:
       numeric(next) in [numeric(prev), numeric(prev)+15]; equal numeric needs a larger letter suffix (11 → 11A → 11B)
  4. toc_run  = first run with ≥5 hits whose median segment length < 150 chars
     body_run = run (not toc_run) with the largest total text, ≥5 hits
     other runs → warning "pages a–b look like appended rules/forms; not indexed"
  5. headings = {no: segment text of toc_run (join wrapped lines, strip dots and trailing page numbers)}
  6. sections = for each hit in body_run: text = lines from hit to next hit;
       heading = headings.get(no); if the heading's lines are at the tail of the previous
       section's text, remove them there; part = last PART_RE seen;
       amend_notes = AMEND_RE.findall(text); page_start/end from line pages
  7. fallback to pages mode (key LAW:p<n>, heading = first line) when mode == 'pages', no
     body_run, or body_run < 5 sections → warning "parsed by page"
```
Upload validation: reject when `doc.needs_pass`, when there are under 50 characters per page on
average (scanned), or when the file is not a PDF. `upload_preview` runs the same parse in memory
(`pymupdf.open(stream=file_bytes, filetype="pdf")`) and writes nothing.
`submit_upload` stores the file as `data/files/<sha256>.pdf`.

### 3.3 Diff (`laws.diff_versions(old_id, new_id)`)
Compare sections by key → for each added/removed/changed key build
`{section_no, change, old, new}` (texts truncated to 2,000 characters). Also build a compact
`difflib.unified_diff(old.splitlines(), new.splitlines(), n=1)` string (≤ 60 lines per section,
≤ 400 lines total) and `diff_summary` counts. Store everything in `versions.diff_json`.

## 4. Retrieval (`retrieval.py`)
- `toc_text(conn)`: for every approved version, one line per section:
  `NREO:11A | <part from PDF> | Reports on activities having impact on environment and natural resources`.
  If the heading is missing, use the first 15 words of the text. Cached by kb_version.
- `triggers_for(tags)`: approved or needs_review rows → keys `f"{law.code}:{section_no}"`.
- `bm25_top(query, k=5)`: BM25Okapi over `heading + text` of approved sections. Tokens are
  `re.findall(r"[a-z0-9]+", normalize(s))`; keep tokens like `11a`. Cached by kb_version.
- `xrefs(section, limit=3)`: `r'\bsection\s+(\d{1,3}[A-Z]{0,2})\b'` within the same law; only keys that exist.
- `merge_candidates()`: priority trigger > toc > bm25 > xref; dedupe; cap 10; remember `sources` per key.
- Section text sent to the LLM is capped at 6,000 characters (append `[…truncated]`).

## 5. LLM (`llm.py`, `prompts.py`)
`call_llm_json(name: str, system: str, user: str, max_tokens: int = 2000) -> dict`
- openai_compatible: `OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY).chat.completions.create(model=LLM_MODEL,
  messages=[system, user], response_format={"type":"json_object"}, temperature=0, max_tokens)` → `json.loads`.
- anthropic (only if chosen): official `anthropic` SDK per its docs (structured outputs; no `temperature`).
- Validate with the pydantic model for `name` (`PlanOut`, `ConditionsOut`). On failure, retry once
  with the validation error appended to `user`. On a second failure → `ServiceError("llm_unavailable")`.
- fake: return `tests/fixtures/llm/{name}.json`.

### 5.1 PLAN_SYSTEM
```
You help Sarawak government officers see which laws from OTHER sectors a planned action may trigger.
You receive the officer's planned ACTION, an allowed TAG LIST, and the TABLE OF CONTENTS of the laws
in the knowledge base (section keys and headings only).
Return a json object with exactly these fields:
{"facts": {"activity": string|null, "location": string|null, "area_ha": number|null,
           "land_status": string|null},
 "missing_facts": [string],
 "tags": [string],
 "sections": [{"key": string, "reason": string}]}
Rules:
- "tags": only values from TAG LIST.
- "sections": at most 5; copy keys exactly from the TABLE OF CONTENTS; empty list if none is relevant.
- "missing_facts": facts that would change which laws apply (e.g. "site area in hectares",
  "whether the land is native customary rights land").
- Do not decide whether the action is legal. Output json only.
```
User message: `ACTION:\n{text}\n\nTAG LIST:\n{tags}\n\nTABLE OF CONTENTS:\n{toc}`

### 5.2 CONDITIONS_SYSTEM
```
You extract compliance conditions for a Sarawak government officer from law sections.
You receive the planned ACTION, known FACTS, and SECTIONS (each with a key, heading and text).
Return a json object:
{"conditions": [{"key": string, "subsection": string|null, "requirement": string,
                 "why": string, "quote": string}],
 "explanation": string}
Rules:
- Use ONLY the provided section texts. Never use outside knowledge of the law.
- "quote": copied character-for-character from that section's text, 8 to 30 words, the words
  that create the requirement.
- "requirement": one imperative sentence (max 20 words) saying what to do or check before acting.
- "why": at most 3 plain-language sentences linking the action to the section; if it depends on a
  missing fact (e.g. site area), say so.
- One condition per distinct requirement; at most 6.
- If no section applies, return {"conditions": [], "explanation": "<why not>"}.
- Never say the action is approved, allowed, clear or legal. Output json only.
```
User message: `ACTION: …\nFACTS: {json}\n\nSECTIONS:\n[KEY NREO:11A] <heading>\n<text>\n---\n…`

## 6. Verification and highlight (`verify.py`)
```
normalize(s): NFKC; [⎯—–‐−] → '-'; “ ” „ → '"'; ‘ ’ → "'"; drop '*' before a digit;
              re.sub(r'\s*-\s*', '-'); collapse whitespace; lower(); strip()
tokens(s):    re.findall(r'[a-z0-9]+', normalize(s))
verify_quote(quote, section_text) -> 'exact' | 'near' | None
  exact if normalize(quote) in normalize(section_text)
  near  if SequenceMatcher(None, tq, ts, autojunk=False).find_longest_match(0,len(tq),0,len(ts)).size
           >= max(8, ceil(0.9*len(tq)))
find_highlight(pdf_path, page_start, page_end, quote) -> (page, rects) | (page_start, [])
  for p in page_start..page_end:
     words = page.get_text("words")      # (x0,y0,x1,y1,word,block,line,wno)
     flatten tokens(word) with back-pointer to word index
     m = longest contiguous match of tq in page tokens (SequenceMatcher)
  pick the page with the largest m; if m.size >= min(5, len(tq)):
     rects = boxes of the matched words merged per (block, line) → [[x0,y0,x1,y1], …]
```
Verification is against the **same cleaned text** that was sent to the LLM, so footnotes and
page numbers can't break a quote. Highlighting is best effort; the contract needs all rects on
one page, so only the best page is returned.

## 7. Severity and status (`severity.py`)
```
RED    = [r"\bno person shall\b", r"\bshall not\b", r"\bshall\b", r"\bmust\b",
          r"\bguilty of an offence\b", r"\bliable to\b", r"\bpenalty\b"]
YELLOW = [r"\bmay\b", r"\bsubject to\b", r"\bthinks? fit\b", r"\bdeems? (fit|necessary|desirable)\b"]
classify(quote, override) -> (severity, matched_wording)
  override → (override, "rule set by legal officer")
  first RED match → ("red", matched text lower-cased); first YELLOW match → ("yellow", text); else ("info", "")
status_and_headline(conds, plan_empty, n_laws, missing_facts):
  r, y = counts
  r>0  → red,     "🔴 Stop — {r} mandatory requirement(s) before you proceed" + (" · {y} more to check" if y)
  y>0  → yellow,  "🟡 Allowed — {y} condition(s) to check first"
  plan_empty → abstain, "❔ Not enough detail to check — please add: {', '.join(missing_facts) or 'more detail about the action'}"
  else → none,    "⚪ No requirements found in the {n_laws} laws indexed"
```
Real example: NREO s.11A(3) starts "No person shall carry out or commence any preparatory
work", which classifies as red. s.11A(1) says the Board "may … require", which would classify as
yellow, so the seed trigger for `waste_disposal` sets `severity_override: "red"`. That override is
the legal officer's call, and it is exactly what the human-in-the-loop design is for.

## 8. Laws, versions, approvals (`laws.py`)
- `preview(file_bytes, meta)`: validate → parse in memory → toc + `is_new_version_of` (match an existing law by `cap_no`+`jurisdiction`, else title, case-insensitive) → no writes.
- `submit(file_bytes, meta)`: validate → sha256 dedupe → save file → find or create law (new code = initials of the title, made unique, e.g. "SRWMO") → version(pending) + sections → diff against the current approved version → audit(`upload`).
- `pending_items()`: pending versions (`type` new_law if the law has no approved version, else new_version; `id = version_id`; diff from `diff_json`) + pending/needs_review triggers (`type` trigger; `id = 1_000_000 + trigger_id`; diff None). Newest first.
- `decide(item_id, approve: bool, note, reviewer)`: `item_id >= 1_000_000` → trigger, else version. Version approve: must be pending → previous approved → superseded → this → approved → triggers of this law whose section changed or was removed → needs_review → bump kb_version → audit. Version reject: pending → rejected → audit. Trigger approve/reject: from pending or needs_review → bump kb_version → audit.
- `propose_trigger(...)`: validate → insert pending → audit.
- `pending_version_for(law_id)` → `{"uploaded": "YYYY-MM-DD"}` or None.

## 9. Rendering (`render.py`)
```
render_highlight(pdf_path, page, rects, dpi=110) -> bytes | None:
  if not os.path.exists(pdf_path): return None
  doc = pymupdf.open(pdf_path); pg = doc[page - 1]          # page is 1-based
  if rects: pg.add_highlight_annot([pymupdf.Rect(*r) for r in rects])
  png = pg.get_pixmap(dpi=dpi).tobytes("png"); doc.close(); return png   # never save the doc
```

## 10. Public facade (`services/__init__.py`)
Exports exactly: `check_action, upload_preview, submit_upload, list_pending, approve, reject,
list_triggers, propose_trigger, list_laws, get_audit_log, render_highlight` + [extra]
`health, ServiceError`. Each public function first calls `_ensure_ready()` (a module-level
`threading.Lock` + flag: init schema; seed if there are no laws). Each one maps internal results
to the **exact contract keys** (`docs/SERVICE_CONTRACT.md`); a test asserts every required key
is present.

## 11. Configuration
Read in order: environment variables → `streamlit.secrets` (lazy `import streamlit` inside
try/except) → `.env` → defaults.
```
LLM_PROVIDER=openai_compatible        # openai_compatible | anthropic | fake
LLM_BASE_URL=…                        # e.g. Gemini: https://generativelanguage.googleapis.com/v1beta/openai/
                                      #      DeepSeek: https://api.deepseek.com   OpenAI: https://api.openai.com/v1
LLM_API_KEY=replace-me
LLM_MODEL=replace-me                  # copy the current model name from the provider's docs/console
DATA_DIR=data
HIGHLIGHT=1   XREFS=1   BM25_K=5
```
Local secrets go in `.streamlit/secrets.toml` (gitignored). On Streamlit Cloud: App settings → Secrets.

## 12. Testing strategy
All tests run with `LLM_PROVIDER=fake` and a temporary `DATA_DIR`.
- `test_parser.py` (real seed PDFs `seed/pdfs/NREO_Cap84_LawNet2024.pdf` and `seed/pdfs/LandCode_Cap81_LawNet2025.pdf`; page numbers below apply to these exact files):
  - NREO: `NREO:11A` exists, `page_start == 23`, heading starts "Reports on activities having impact".
  - Land Code: `LC:5` has `page_start == 28` and heading "Native customary rights"; `LC:6A` exists.
  - No duplicate keys; at least 40 NREO sections and at least 200 LC sections; pages mode works.
- `test_verify.py`:
  - The real quote "No person shall carry out or commence any preparatory work" is exact against `NREO:11A`.
  - A made-up quote ("All school extensions require an EIA approval") returns None.
  - Curly quotes and "⎯" variants still verify.
  - The highlight is found on PDF page 25 with non-empty rects.
- `test_severity.py`: red, yellow and info cases with `matched_wording`; the override wins.
- `test_laws.py`:
  - A pending version is not in the ToC or BM25; after approval it is, and kb_version is bumped.
  - A duplicate upload raises `duplicate_file`.
  - Approving a new version supersedes the old one and flags triggers.
  - `list_pending` ids are unique across types.
  - Audit rows are written.
- `test_contract.py` (fixtures `plan.json` / `conditions.json`):
  - `check_action` returns **every required contract key** (top level and per condition).
  - The waste-disposal case returns status red; an invented key is dropped; a made-up quote is dropped, so `dropped_unverified == 1`.
  - The none and abstain paths work, and no headline contains clear/approved/safe/legal.
  - `render_highlight` returns PNG bytes (starting with `\x89PNG`) and None for a missing file.

## 13. Plan B switches (flip a config flag rather than debugging when time is short)
| Problem | Switch |
|---|---|
| Parser wrong for a law | upload with `meta.parse_mode="pages"` (or set `body_page_from/to`) |
| Highlight rects unreliable | `HIGHLIGHT=0` → `highlight_rects=[]`, page still shown, quote in text |
| Cross-refs add noise | `XREFS=0` |
| BM25 noisy | `BM25_K=0` (trigger map + ToC only) |
| LLM slow/flaky | switch `LLM_MODEL`/provider in secrets; worst case `LLM_PROVIDER=fake` (results say `llm_provider: "fake"`, so the UI shows Replay mode) |
| Backend not ready at integration time | the UI keeps `USE_MOCK = True` (already built) |

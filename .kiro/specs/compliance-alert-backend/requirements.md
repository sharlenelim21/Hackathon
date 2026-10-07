# Requirements: Compliance Impact Alert `services` package (backend of the Streamlit app)

## Introduction
The team builds **one Streamlit app** (deployed on Streamlit Community Cloud). The frontend is
**already built**: `ui/backend.py` (with `USE_MOCK = True`) defines the functions the UI calls.
When `USE_MOCK = False` it imports the same-named functions from the **`services`** package.

This spec covers that `services` package, owned by Jy. **`docs/SERVICE_CONTRACT.md` is the source
of truth**: same function names, parameters and return keys as the frontend contract, plus a few
additive [extra] keys and optional parameters that change nothing in the UI.

The backend checks a government worker's planned action against laws from other sectors and
returns a conditions-first result. Each condition carries a verified quote and highlight boxes on
the source page. A legal officer approves every law, version and trigger rule before it is used.

Seed laws (official Sarawak LawNet PDFs, in `seed/pdfs/`):
- Natural Resources and Environment Ordinance (Cap. 84), LawNet reprint 2024: code `NREO`
- Land Code (Cap. 81), LawNet reprint 2025: code `LC` (optionally the archived 2024 reprint, for the version demo)

Glossary: **section key** = `<LAW_CODE>:<section_no>` (internal, e.g. `NREO:11A`), or
`<LAW_CODE>:p<n>` in pages mode. **kb_version** = integer bumped on every approval or rejection that
changes searchable content. **ServiceError** = `Exception` subclass with `code` and `message`.
**Fixed tags** = `construction, land_clearing, land_acquisition, native_land, waste_disposal,
water_body, procurement, logging, road_works`.

---

### Requirement 1: Check a planned action
**User story:** As a worker, I describe an action I plan to take, so I learn which other-sector laws it triggers before I act.

1. WHEN the UI calls `check_action(text)` with 5–2000 characters THE SYSTEM SHALL return the dict defined in the contract (every required key, plus the [extra] keys).
2. THE SYSTEM SHALL extract `facts` (`activity`, `location`, `area_ha`, `land_status`) and list `missing_facts` that would change which laws apply.
3. THE SYSTEM SHALL use at most 2 LLM calls per check (plan call, conditions call).
4. THE SYSTEM SHALL record per-step timings in `timings_ms` [extra].
5. IF an LLM call fails or returns invalid JSON twice THEN THE SYSTEM SHALL raise `ServiceError("llm_unavailable")` and return no partial answer.
6. IF `text` is outside 5–2000 characters THEN THE SYSTEM SHALL raise `ServiceError("validation")`.

### Requirement 2: Conditions-first verdict (no bare "yes")
**User story:** As a worker, I see the most important constraint first, so I can't miss a condition by reading only the first line.

1. THE SYSTEM SHALL compute `status` and `headline` in code from verified conditions only. The LLM never writes the headline.
2. WHEN at least one condition is `red` THE SYSTEM SHALL set status `red`, headline `🔴 Stop — {r} mandatory requirement(s) before you proceed`, plus ` · {y} more to check` when there are yellow conditions.
3. WHEN there are no red conditions and at least one is `yellow` THE SYSTEM SHALL set status `yellow`, headline `🟡 Allowed — {y} condition(s) to check first`.
4. WHEN candidates were checked and no red/yellow condition was verified THE SYSTEM SHALL set status `none`, headline `⚪ No requirements found in the {n} laws indexed`, and return `indexed_laws` (and `info` conditions, if any).
5. WHEN the plan call returns no tags and no sections THE SYSTEM SHALL set status `abstain`, headline `❔ Not enough detail to check — please add: {missing facts}`, and return `closest_sections` (top 3 BM25).
6. THE SYSTEM SHALL NOT produce the words "clear", "approved", "safe" or "legal" in any headline (enforced by a test).
7. Each condition SHALL include every key listed in the contract: `id` ("C1", "C2"…), `sector`, `requirement`, `why`, `quote`, `severity`, `matched_wording`, `law_title`, `section_no`, `page`, `version_label`, `in_force_date`, `not_yet_in_force`, `pending_newer_version`, `pdf_path`, `highlight_rects`.

### Requirement 3: Verified citations with highlight boxes
**User story:** As a worker, I open a citation and see the exact clause highlighted, so I can trust the answer in seconds.

1. Each condition proposed by the LLM SHALL contain a section `key` and a `quote` (8–30 words).
2. IF the key is not one of the candidate sections sent to the LLM THEN THE SYSTEM SHALL drop the condition.
3. THE SYSTEM SHALL accept a quote only if its normalized form is a substring of the normalized section text (exact), or at least 90% of its tokens (minimum 8) appear as one contiguous block (near).
4. IF a quote is not verified THEN THE SYSTEM SHALL drop that condition and increment `dropped_unverified` [extra].
5. Each condition SHALL carry `pdf_path` (absolute path), `page` (1-based page where the quote was found) and `highlight_rects` (PyMuPDF points, all on that page). IF no boxes are found THEN `highlight_rects = []`, `highlight = false` [extra], and `page` = the section's first page.
6. `render_highlight(pdf_path, page, rects)` SHALL return PNG bytes of that page (1-based) with the rects highlighted, the plain page if `rects` is empty, or `None` if the file is missing.
7. Each condition SHALL also include [extra] `subsection`, `heading`, `section_key`, `cap_no`, `source_authority` (`official`/`unofficial`), `amend_notes` (e.g. `Am. Cap. A185/2019`), `highlight`, `rule_needs_review`, `sources`.

### Requirement 4: Structure-aware (vectorless) retrieval
**User story:** As the team, we retrieve law sections by structure and curated rules, so citations are exact and explainable.

1. THE SYSTEM SHALL use only sections of `approved` versions and triggers with status `approved` or `needs_review`.
2. THE SYSTEM SHALL build candidates from (a) trigger rows for the extracted tags, (b) up to 5 section keys picked by the LLM from the table of contents, (c) BM25 top 5 over approved sections, and (d) up to 3 sections cross-referenced ("section N") by (a)–(c). Deduplicate and cap at 10, in priority order a > b > c > d.
3. THE SYSTEM SHALL discard any LLM-proposed key or tag that isn't in the table of contents or the fixed tag list.
4. The table of contents sent to the LLM SHALL contain law code, part, section key and heading only (no body text).
5. Retrieval caches (ToC text, BM25 index) SHALL be keyed by `kb_version`.

### Requirement 5: Severity from legal wording
1. THE SYSTEM SHALL classify each verified condition and put the deciding words in `matched_wording`. The trigger's `severity_override` applies if present (`matched_wording = "rule set by legal officer"`). Otherwise `red` if the quote matches a red pattern (`no person shall`, `shall not`, `shall`, `must`, `guilty of an offence`, `liable to`, `penalty`); otherwise `yellow` if it matches a yellow pattern (`may`, `subject to`, `thinks fit`, `deems fit|necessary|desirable`); otherwise `info`.
2. Patterns SHALL live in `services/config.py`.

### Requirement 6: Add a law or a new version (legal officer)
**User story:** As a legal officer, I upload a new law or a newer version, check how it was parsed, and submit it for approval.

1. `upload_preview(file_bytes, meta)` SHALL parse a PDF ≤ 50 MB **without saving anything**; `submit_upload(file_bytes, meta)` SHALL parse and save it. Both accept the `meta` keys in the contract.
2. IF the file is not a PDF or is encrypted THEN THE SYSTEM SHALL raise `ServiceError("bad_file")`. IF it averages under 50 extractable characters per page THEN it SHALL raise `ServiceError("scanned_pdf")` (OCR is out of scope).
3. IF a file with the same SHA-256 already exists THEN THE SYSTEM SHALL raise `ServiceError("duplicate_file")`.
4. `upload_preview` SHALL return `sections_count`, `toc` (`part`, `section_no`, `heading`, `page_start`), `is_new_version_of` (title of an existing law with the same `cap_no` + `jurisdiction`, or the same title ignoring case; otherwise null), and [extra] `mode`, `page_count`, `warnings`.
5. `submit_upload` SHALL store the version with status `pending` and return `version_id` and `status: "pending"` (+ [extra] `law_id`, `is_new_law`, `diff_summary`). A new law gets a generated code (initials of the title, made unique). Pending versions SHALL NOT be searchable.
6. IF the law already has an approved version THEN THE SYSTEM SHALL compute a diff by section key (added / removed / changed) for `list_pending()`: items `{section_no, change, old, new}` (old/new truncated to 2,000 characters) + [extra] `unified_diff`.

### Requirement 7: Approval gate (human in the loop)
**User story:** As a legal officer, I approve or reject every change to the knowledge base, so workers only see vetted content.

1. `list_pending()` SHALL return pending new laws, pending new versions, and pending or needs_review triggers as items `{id, type, title, uploaded_by, uploaded_at, diff}`. IDs SHALL be unique across types: versions use `version_id`, triggers use `1_000_000 + trigger_id`.
2. `approve(item_id, note, reviewer="Legal officer")` and `reject(item_id, note, reviewer="Legal officer")` SHALL decode the id, record the reviewer and note, and return None. An item in the wrong state SHALL raise `ServiceError("wrong_state")`; an unknown id SHALL raise `ServiceError("not_found")`.
3. WHEN a version is approved THE SYSTEM SHALL mark the law's previous approved version `superseded`, set triggers whose section changed or was removed to `needs_review`, and bump `kb_version`.
4. `propose_trigger(activity_tag, law_id, section_no, note, severity_override=None, proposed_by="Legal officer")` SHALL create a `pending` trigger after validating the tag (fixed list), `law_id`, and that the section exists in the law's approved version; otherwise `ServiceError("validation")`.
5. THE SYSTEM SHALL write an audit_log row for every upload, approval, rejection and trigger proposal.

### Requirement 8: Freshness and version warnings
1. IF a cited law has a pending version THEN the condition SHALL include `pending_newer_version: {"uploaded": "YYYY-MM-DD"}`; otherwise null.
2. IF a citation's `in_force_date` is later than today THEN `not_yet_in_force` SHALL be true. `in_force_date` may be null.
3. IF a condition came from a trigger with status `needs_review` THEN `rule_needs_review` [extra] SHALL be true.
4. Every result SHALL include `indexed_laws` as strings `"<title> (<version label>)"`.

### Requirement 9: Catalogue, audit and health
1. THE SYSTEM SHALL provide `list_laws()`, `list_triggers()` and `get_audit_log()` (newest first, ≤ 100 rows, `target_id` as int) with the contract shapes, plus [extra] `health()` (`status`, `kb_version`, `llm_provider`, `law_count`).

### Requirement 10: Startup, configuration and testability
1. `services` SHALL initialise itself lazily and thread-safely on the first call of any public function (the contract has no init call): create `data/`, create the schema, and IF the database has no laws THEN seed it from `seed/laws.json` (approved by reviewer `seed`) and `seed/triggers.json` (approved). Streamlit Cloud wipes `data/` on restart, so the app must rebuild itself.
2. Settings SHALL be read from environment variables, then Streamlit secrets (optional lazy import inside try/except), then `.env`, then defaults.
3. With `LLM_PROVIDER=fake` THE SYSTEM SHALL answer from fixtures, so tests and UI integration work without an API key; results SHALL report `llm_provider` [extra].
4. `services/` SHALL NOT use Streamlit UI APIs, so it runs under plain pytest.

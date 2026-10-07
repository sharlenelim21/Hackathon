# Backend contract: `services` ⇄ `ui/backend.py`

**Source of truth:** the frontend's `ui/backend.py` contract. The backend (`services/` package,
owned by Jy) implements **exactly these function names, parameters and return keys**, so the UI
can switch `USE_MOCK = False` without changes.

Backend notes are marked **[backend]**. Everything marked **[extra]** is additive: extra dict keys
or optional parameters with defaults. The UI may ignore them, and nothing in the UI's code has to
change.

```python
from services import (check_action, upload_preview, submit_upload, list_pending, approve, reject,
                      list_triggers, propose_trigger, list_laws, get_audit_log, render_highlight)
```

## Ground rules (both sides)
- **Pages are 1-based PDF page numbers** everywhere (`page`, `page_start`). PyMuPDF uses 0-based
  indexes, so `render_highlight` opens `doc[page - 1]`. This is the most likely integration bug.
- **Rects** are PyMuPDF page coordinates in points `[x0, y0, x1, y1]` (origin top-left), from `page.get_text("words")`.
- `pdf_path` **[backend]** is an absolute path to `data/files/<sha256>.pdf` inside the running app. Pass it straight to `pymupdf.open()`.
- Nullable fields: `in_force_date` is usually `null` for the seed reprints. `pending_newer_version`, `highlight_rects` can be `[]`, and `pdf_path` can be `null`.
- `check_action` takes **10–30 s**. Call it only when the Check button is pressed, keep the result in `st.session_state`, and show a spinner. Streamlit reruns the script on every click.
- Errors: functions raise `services.ServiceError` (`.code`, `.message`; subclass of `Exception`). UI: `except Exception as e: st.error(str(e))`.
  Codes: `validation`, `bad_file`, `scanned_pdf`, `duplicate_file`, `not_found`, `wrong_state`, `llm_unavailable`.
- **[backend]** `services` initialises itself on first call: creates `data/`, the DB schema, and seeds the two laws + trigger rules if the DB is empty. On Streamlit Cloud a restart wipes `data/`, so the first call after a restart takes a few seconds longer.

## Activity tags (fixed list, used by both sides)
`construction, land_clearing, land_acquisition, native_land, waste_disposal, water_body, procurement, logging, road_works`

---

## `check_action(text: str) -> dict`
```json
{
  "status": "red",
  "headline": "🔴 Stop — 1 mandatory requirement(s) before you proceed · 1 more to check",
  "facts": {"activity": "build a municipal waste recycling and storage facility",
            "location": "beside the Rejang River, Kapit", "area_ha": 3, "land_status": null},
  "missing_facts": ["Whether the site is native customary rights (NCR) land"],
  "conditions": [{
      "id": "C1",
      "sector": "Environment (Natural Resources and Environment Board)",
      "requirement": "Get the Board's approval of an environmental impact report before any preparatory work.",
      "why": "Facilities for storing, treating or recycling municipal waste are listed activities. No preparatory work may start until the Board approves the report.",
      "quote": "No person shall carry out or commence any preparatory work …",
      "severity": "red",
      "matched_wording": "no person shall",
      "law_title": "Natural Resources and Environment Ordinance",
      "section_no": "11A",
      "page": 25,
      "version_label": "LawNet reprint 2024",
      "in_force_date": null,
      "not_yet_in_force": false,
      "pending_newer_version": null,
      "pdf_path": "C:/…/data/files/753d87b3….pdf",
      "highlight_rects": [[72.0, 410.5, 520.3, 424.1], [72.0, 426.0, 300.2, 439.6]],

      "subsection": "(3)", "heading": "Reports on activities having impact on environment and natural resources",
      "section_key": "NREO:11A", "cap_no": "Cap. 84", "source_authority": "official",
      "amend_notes": ["Am. Cap. A185/2019", "Am. Cap. A120.", "Ins. Cap. A120."],
      "highlight": true, "rule_needs_review": false, "sources": ["trigger_map", "toc"]
  }],
  "indexed_laws": ["Natural Resources and Environment Ordinance (LawNet reprint 2024)", "Land Code (LawNet reprint 2025)"],
  "closest_sections": [],

  "dropped_unverified": 1, "kb_version": 4, "llm_provider": "openai_compatible",
  "explanation": "…", "disclaimer": "A reference before you act, not a legal judgement. Confirm with your legal officer.",
  "timings_ms": {"plan_llm": 4100, "retrieval": 40, "conditions_llm": 6800, "verify": 120, "total": 11200}
}
```
The keys after the blank line in each object are **[extra]**. Semantics:
- `status`: `red` | `yellow` | `none` | `abstain`. **[backend]** `headline` is built in code from verified conditions only:
  - `🔴 Stop — {r} mandatory requirement(s) before you proceed` (+ ` · {y} more to check`)
  - `🟡 Allowed — {y} condition(s) to check first`
  - `⚪ No requirements found in the {n} laws indexed` (UI: show `indexed_laws`)
  - `❔ Not enough detail to check — please add: …` (`abstain`; UI: show `missing_facts` and `closest_sections`)
  It never contains "clear", "approved", "safe" or "legal".
- `severity`: `red` | `yellow` | `info`. `matched_wording` is the legal wording that set it (e.g. `"shall"`, `"may"`), or `"rule set by legal officer"` when a trigger rule overrides it.
- `page` is the page where the quote was found (where the highlight is). `highlight_rects` all belong to that page.
- `pending_newer_version`: `{"uploaded": "YYYY-MM-DD"}` when a newer version of that law is waiting for approval → UI banner.
- Suggested UI use of extras: `dropped_unverified > 0` → caption "1 unverified claim removed"; `source_authority == "unofficial"` → badge; `amend_notes` → chips; `llm_provider == "fake"` → "Replay mode" badge.

## `render_highlight(pdf_path: str, page: int, rects: list) -> bytes | None`
PNG of the page with highlight boxes (PyMuPDF `add_highlight_annot` then `get_pixmap(dpi=110)`).
Returns `None` if the file is missing. **[backend]** implemented in `services` too, so the UI can
import it instead of writing its own. With `rects == []` it returns the plain page.

## `upload_preview(file_bytes: bytes, meta: dict) -> dict`
```json
{"sections_count": 276,
 "toc": [{"part": "…", "section_no": "5", "heading": "Native customary rights", "page_start": 28}],
 "is_new_version_of": "Land Code",

 "mode": "sections", "page_count": 266,
 "warnings": ["Pages 200–266 look like appended rules/forms and were not indexed"]}
```
**[backend]** Parses only; nothing is saved. Raises `bad_file`, `scanned_pdf` or `duplicate_file`.
`is_new_version_of` is the title of an existing law that matches `meta` (same `cap_no` +
`jurisdiction`, or the same title ignoring case).

### `meta` keys (UI form → both upload functions)
| key | required | example |
|---|---|---|
| `title` | yes | `Land Code` |
| `jurisdiction` | yes | `Sarawak` \| `Federal` |
| `cap_no` | no | `Cap. 81` (Cap./Act no.) |
| `sector` | yes | `Land (Land and Survey Department)` |
| `version_label` | yes | `LawNet reprint 2025` |
| `published_date`, `in_force_date` | no | `2025-01-01` |
| `source_url` | no | LawNet URL |
| `source_authority` | **[extra]** default `official` | `official` \| `unofficial` (unofficial → badge in answers) |
| `uploaded_by` | **[extra]** default `Legal officer` | name for the audit log |
| `parse_mode` | **[extra]** default `auto` | `auto` \| `sections` \| `pages` (use `pages` if the preview looks wrong) |
| `body_page_from`, `body_page_to` | **[extra]** | `28`, `199` |

## `submit_upload(file_bytes: bytes, meta: dict) -> dict`
```json
{"version_id": 3, "status": "pending",
 "law_id": 2, "is_new_law": false, "diff_summary": {"added": 3, "removed": 0, "changed": 12, "unchanged": 261}}
```
The new version is **not searchable until approved**.

## `list_pending() -> list[dict]`
```json
[{"id": 3, "type": "new_version", "title": "Land Code — LawNet reprint 2025",
  "uploaded_by": "Encik Lee", "uploaded_at": "2026-10-09T10:05:00+08:00",
  "diff": [{"section_no": "5", "change": "changed", "old": "…", "new": "…"},
           {"section_no": "6A", "change": "added", "old": null, "new": "…"}],
  "unified_diff": "--- old\n+++ new\n@@ …", "diff_summary": {"changed": 12}},
 {"id": 1000011, "type": "trigger", "title": "waste_disposal → Natural Resources and Environment Ordinance s.11A",
  "uploaded_by": "Encik Lee", "uploaded_at": "…", "diff": null,
  "status": "pending", "severity_override": "red", "note": "…"}]
```
- **[backend] IDs are unique across types:** versions use their `version_id`; trigger items use `1_000_000 + trigger_id`. So `approve(item_id, …)` knows what to approve without a type parameter.
- `type`: `new_law` (first version of a law), `new_version`, `trigger`. Triggers flagged after a law update appear with `status: "needs_review"`.
- `old`/`new` are truncated to 2,000 characters; `unified_diff` **[extra]** is the compact view (`st.code(..., language="diff")`).

## `approve(item_id: int, note: str, reviewer: str = "Legal officer") -> None`
## `reject(item_id: int, note: str, reviewer: str = "Legal officer") -> None`
`reviewer` is **[extra]**; pass the user's name if you have it. Raises `wrong_state` if the item
isn't pending (or needs_review, for triggers). Approving a new version supersedes the old one,
flags affected trigger rules `needs_review`, and changes the next answers.

## `list_triggers() -> list[dict]`
```json
[{"id": 7, "activity_tag": "waste_disposal", "law_title": "Natural Resources and Environment Ordinance",
  "section_no": "11A", "note": "s.11A(1)(h) …", "status": "approved",
  "law_id": 1, "severity_override": "red", "proposed_by": "seed"}]
```
(Here `id` is the plain trigger id, not the `list_pending` id.)

## `propose_trigger(activity_tag: str, law_id: int, section_no: str, note: str, severity_override: str | None = None, proposed_by: str = "Legal officer") -> None`
Creates a **pending** rule. Raises `validation` if the tag isn't in the fixed list, the law doesn't
exist, or the section isn't in the law's approved version. The last two parameters are **[extra]**.

## `list_laws() -> list[dict]`
```json
[{"id": 1, "title": "Natural Resources and Environment Ordinance", "jurisdiction": "Sarawak",
  "cap_no": "Cap. 84", "sector": "Environment (Natural Resources and Environment Board)",
  "version_label": "LawNet reprint 2024", "status": "approved",
  "pending_versions": 0, "section_count": 48, "source_authority": "official"}]
```
`version_label`/`status` describe the current approved version, or the latest pending one if
the law has none approved yet.

## `get_audit_log() -> list[dict]`
```json
[{"ts": "2026-10-09T10:07:12+08:00", "actor": "Encik Lee", "action": "approve_version",
  "target_type": "version", "target_id": 3, "note": "Checked against gazette"}]
```
Newest first, up to 100 rows.

## `health() -> dict` **[extra]**
`{"status": "ok", "kb_version": 4, "llm_provider": "openai_compatible", "law_count": 2}`. Optional; useful for the Replay-mode badge.

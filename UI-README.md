# RAKAN — Frontend (UI)

**RAKAN — Regulatory Advisory & Compliance Alert Network.** Streamlit prototype
for the compliance impact alert tool. This document covers only the UI layer
(the `frontend` branch). The logic lives in `services/` on a separate branch.

## Run locally

```bash
# From the repo root
pip install -r requirements-frontend.txt
streamlit run app.py
```

The app opens with a sidebar **Role** segmented control (no login — the switch
simulates the two roles):

- **Officer** → Check an action, Library, Submit a change, My submissions
- **Admin** → everything Officers see, plus (under an ADMIN label) Review
  queue, Trigger map, Audit log

Access is enforced by which pages are registered per role; Admin-only views
also guard with "This page is for Admins".

While on mock data, the sidebar shows a **MOCK DATA** label and a **Mock
scenario** selector with four scenarios: `red`, `yellow`, `none`, `abstain`.

### Human-in-the-loop review flow

Every submission (from an Officer or an Admin) enters the **Review queue** as
`pending`. Nothing is citable by the AI until an Admin approves it:

- `pending → approved` ⇒ becomes searchable/citable and appears in the Library.
- `pending → rejected` ⇒ kept for the audit trail; a note is required.
- An Admin approving their own submission is logged as **self-approved**.

**Meeting minutes** are an official internal record, not law: they never create
a 🔴/🟡 condition and never change the headline. They surface after the
checklist as "Related decisions" cards and may be linked from a condition.

> Python note: targets Python 3.11 for Streamlit Community Cloud. `pymupdf`
> provides the `fitz` module used to render highlighted PDF pages.

## Turning mock mode off (wiring the real backend)

Everything the UI calls goes through **`ui/backend.py`** — the single
integration seam. To switch from mock data to the real logic:

1. Open `ui/backend.py`.
2. Set `USE_MOCK = False`.

When `USE_MOCK` is `False`, `backend.py` imports the same-named functions from
`services`. If the import fails (module missing), the UI falls back to mock
data and shows a one-time `st.warning` so a demo never hard-crashes. Remove or
ignore that warning once `services/` is in place.

## Functions `services/` must implement

`services` must expose these functions with the exact return shapes defined as
`TypedDict`s in `ui/backend.py`. All date strings are `YYYY-MM-DD`.

| Function | Signature | Returns |
| --- | --- | --- |
| `check_action` | `(text: str)` | `CheckResult` (now includes `related_minutes`) |
| `upload_preview` | `(file_bytes: bytes, meta: dict)` | `UploadPreview` |
| `submit_change` | `(kind, file_bytes: bytes, meta: dict, submitted_by_role)` | `SubmitChangeResult` |
| `list_pending` | `()` | `list[PendingItem]` |
| `approve` | `(item_id: int, note: str, reviewer_role: str)` | `None` |
| `reject` | `(item_id: int, note: str, reviewer_role: str)` | `None` |
| `list_library` | `(kind: "laws" \| "minutes")` | approved items only |
| `list_my_submissions` | `(role: str)` | `list[SubmissionRow]` |
| `list_triggers` | `()` | `list[TriggerRow]` |
| `propose_trigger` | `(activity_tag: str, law_id: int, section_no: str, note: str)` | `None` |
| `list_laws` | `()` | `list[LawRow]` |
| `get_audit_log` | `()` | `list[AuditEntry]` |

`kind` is `"new_law" | "new_version" | "minutes"`; `submitted_by_role` /
`reviewer_role` are `"Officer" | "Admin"`. `submit_upload(file_bytes, meta)`
is kept as a thin backward-compatible alias over `submit_change`.

`render_highlight(pdf_path, page, rects) -> bytes | None` is implemented in the
UI layer (`ui/backend.py`) via PyMuPDF and returns `None` when the file is
missing — `services/` does **not** need to provide it, though it may override it.

### Shape reference

See the `TypedDict` definitions in `ui/backend.py` for authoritative field
lists. Summary:

- **`CheckResult`**: `status` (`red|yellow|none|abstain`), `headline` (shown
  verbatim), `facts`, `missing_facts`, `conditions[]`, `indexed_laws[]`
  (⚪ path), `closest_sections[]` (abstain path), **`related_minutes[]`** (new).
- **`Condition`**: `id, sector, requirement, why, quote` (≤30 words),
  `severity` (`red|yellow|info`), `matched_wording`, `law_title, section_no,
  page, version_label, in_force_date, not_yet_in_force,
  pending_newer_version, pdf_path, highlight_rects`.
- **`RelatedMinute`** (new): `id, title, meeting_date, body, related_law,
  section_no` (nullable), `quote, page, pdf_path, highlight_rects,
  approved_on`. Minutes never create a condition or change the headline.
- **`PendingItem`**: `id, type` (`new_law|new_version|minutes|trigger`),
  `title, uploaded_by, uploaded_at`, **`submitted_by_role`**,
  **`related_laws[]`**, **`summary`**, `diff` (`null` or rows of `section_no,
  change (added|removed|changed), old, new`).
- **`SubmissionRow`** (new): `id, type, title, submitted_at, status`
  (`pending|approved|rejected`), `review_note`.
- **`MinutesRow`** (new, library): `id, title, meeting_date, body,
  related_laws[], section_no, summary, approved_on, status, pdf_path`.
- **`TriggerRow`**: `id, activity_tag, law_title, section_no, note, status`
  (`pending|approved|rejected|needs_review`).
- **`LawRow`**: `id, title, jurisdiction (Sarawak|Federal), cap_no, sector,
  version_label, status`.
- **`AuditEntry`**: `ts, actor, action, target_type, target_id, note`
  (returned newest-first).

### Fixed activity tags

`backend.ACTIVITY_TAGS`: `construction, land_clearing, land_acquisition,
native_land, waste_disposal, water_body, procurement, logging, road_works`.

## Architecture rules (kept intentionally)

- **`ui/views/` not `ui/pages/`** — Streamlit auto-lists `pages/` in the
  sidebar, which would expose Admin screens to Officers. Navigation is scoped
  per role via `st.navigation(position="hidden")` with custom `st.page_link`s;
  Admin-only views also guard with `layout.require_admin()`.
- **Components** (`ui/components/`) receive data and render it; they never
  import `services` or mock data. `render_highlight` is passed into the
  citation component as an argument to preserve this.
- **Views** call `ui/backend.py` only.
- The UI never generates verdict wording ("clear"/"approved"/"safe"); it shows
  the backend's `headline` verbatim and ends every result with:
  _"This is a compliance reference before action, not a legal judgment or
  approval."_

## Sample PDF (highlighted-page demo)

So the Worker "View highlighted page" and "Download PDF" paths work without a
real corpus, `ui/sample_pdf.py` generates a one-page placeholder PDF at
runtime (PyMuPDF) and caches it in the OS temp dir. In the `red` scenario both
conditions point `pdf_path` at it, with `highlight_rects` aligned to the s.11A
and s.27 sample lines, so `render_highlight` draws a gold box over real page
content. Nothing is written into `files/` and no binary is committed. The
`yellow` scenario intentionally leaves `pdf_path` as `null` to also exercise
the graceful "preview not available" fallback. All text in the generated PDF
is placeholder SAMPLE text. When `services/` provides real `pdf_path`s, this
generator is unused.

## Notes for the demo

Mock state (pending/review queue, submissions, triggers, laws, approved
minutes, audit) lives in `st.session_state`, so **Submit, Approve/Reject and
Propose visibly change the UI** during a session: an approved submission moves
into the Library, a rejected one shows its note in My submissions, and both are
recorded in the audit log. The seed includes 2 approved minutes (one linked to
the Land Code s.27 condition used in the Kapit scenario) and 1 pending minutes
item. Reload the page to reset to the seed state. All sample legal text is
clearly marked `SAMPLE`.

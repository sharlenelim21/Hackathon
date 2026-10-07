# Compliance Impact Alert

**Team Name:** 404

**Team Members:**
1. Sharlene Lim
2. Ngui Jia Yi
3. Liew Mei Qi
4. Stefani Lee

---

## About the Project

Compliance Impact Alert helps government sector workers quickly check whether a planned
action (e.g. construction, land clearing, procurement) triggers legal or regulatory
requirements from laws outside their own department — before they proceed.

Instead of a generic "yes/no", the system returns a **Compliance Impact Alert**: a
conditions-first checklist built from verified, citable sources, so no answer is ever a bare
approval or an invented legal claim.

### Key Features

- **Plain-language action check** — a worker describes a planned action in free text and
  receives a compliance alert within seconds, along with any missing facts needed for a
  complete answer (e.g. site area, land status).
- **Conditions-first answers** — the headline (🔴 Stop / 🟡 Allowed with conditions / ⚪ No
  requirements found) is generated from verified rules in code, never from raw LLM text.
- **Verified, highlighted citations** — every condition carries a verbatim quote from the
  actual law PDF, checked against the source document and linked to the exact highlighted
  page.
- **Severity from legal wording** — conditions are flagged 🔴/🟡/⚪ based on the strength of
  the legal language itself (e.g. "shall" vs "may"), using an editable rules table.
- **Human-in-the-loop legal review** — a Legal Officer uploads and curates all laws, trigger
  mappings, and new versions. Nothing becomes searchable by workers until it's approved.
- **Version tracking & stale warnings** — when a law is updated, workers are warned if an
  answer cites a version that's pending review, and section-level diffs are shown to the
  Legal Officer before approval.

### How It Works

1. A worker submits a planned action in plain text.
2. The system extracts key facts and activity tags, then retrieves relevant law sections
   using a structure-aware (vectorless) approach: a curated trigger map, table-of-contents
   navigation, a keyword safety net, and one-hop cross-references — all restricted to
   **Legal-Officer-approved** law versions.
3. Candidate sections are turned into draft conditions with verbatim quotes.
4. Each quote is verified against the actual PDF; unverified claims are dropped.
5. Severity is assigned from fixed rules on the verified legal wording.
6. The worker sees a checklist with citations linking straight to the highlighted PDF page.

### Tech Stack

- **Backend:** Local Python + a direct LLM API (`llm.py`, provider-agnostic)
- **Retrieval:** Structure-aware (vectorless) RAG — trigger map + table-of-contents
  navigation + BM25 keyword safety net + cross-reference following (no embeddings, no
  vector database)
- **PDF handling:** PyMuPDF — text extraction, page mapping, quote verification, and
  highlight annotations
- **Storage:** SQLite + files on disk
- **UI:** Streamlit, with separate Worker and Legal Officer tabs

### Scope

This is a hackathon prototype focused on demonstrating verified, conditions-first compliance
checking for a small curated set of Sarawak/federal laws. It does not cover case law, advice
for the public, automatic consolidation of amendments, gazette parsing, real authentication,
or complete legal coverage.

---

## Screenshots

> _Screenshots to be added._

| Worker View | Legal Officer View | Citation / Highlighted PDF |
|---|---|---|
| ![Worker view](./screenshots/worker-view.png) | ![Legal officer view](./screenshots/legal-officer-view.png) | ![Citation view](./screenshots/citation-view.png) |

---

## Getting Started

_Setup instructions to be added once the app is ready to run._

---

## Team docs (build plan & status)

- **Status:** frontend done on mocks; backend `services/` planned, built during the hackathon. See [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md).
- **Backend ⇄ frontend contract:** [docs/SERVICE_CONTRACT.md](docs/SERVICE_CONTRACT.md) (mirrors `ui/backend.py`).
- **Checklist, timeline, Plan B, demo script, judge Q&A, LLM choice:** [docs/RUNBOOK.md](docs/RUNBOOK.md).
- **Backend spec for Kiro:** [.kiro/specs/compliance-alert-backend/](.kiro/specs/compliance-alert-backend/).
- **Seed data:** [seed/](seed/) (official Sarawak LawNet PDFs + trigger rules + evaluation cases).

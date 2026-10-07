# Product: Compliance Impact Alert (working name)

## Problem (hackathon brief: AWS / FPT / SDEC / SHARING)
Government agencies hold thousands of policies, SOPs, circulars and laws. Finding the right
information takes too long, which slows down decisions.

## What we build
A tool for **Sarawak government sector workers (not lawyers)**:
1. The worker describes an action they plan to take (e.g. "Council will build a waste recycling
   facility beside the Rejang River").
2. The system returns a **Compliance Impact Alert**: the laws from *other* sectors that the
   action triggers, as a conditions-first checklist.
3. Every item cites the exact clause, and the source page is shown with that clause **highlighted**.
4. A **legal officer** controls the knowledge base. Every new law, new version and trigger rule
   must be approved before workers' answers use it (human in the loop).

## Non-negotiable rules (apply to all code and every prompt)
1. Never invent law text, section numbers, thresholds or penalties. Law content comes only from
   ingested PDFs.
2. A condition is shown only if its quote is found in the stored source text. Unverified
   conditions are dropped and counted (`dropped_unverified`).
3. The headline/verdict is computed **in code** from verified conditions. Never output "clear",
   "approved", "safe to proceed" or a bare "yes".
4. Pending (unapproved) content is never used to answer workers.
5. Every answer lists which laws and versions were checked (`indexed_laws`).
6. It is a reference before acting, not legal advice.

## Users
- **Worker**: checks a planned action.
- **Legal officer**: uploads laws and versions, approves or rejects, curates trigger rules.
- No real authentication in the prototype; a name is passed in requests for the audit log.

## Out of scope
Case law, public-facing advice, automatic consolidation of amendments, gazette scraping,
OCR of scanned PDFs, authentication, routing requests to other departments.

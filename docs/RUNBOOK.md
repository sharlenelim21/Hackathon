# Runbook: before, during and after the 3-hour build

Architecture: **one Streamlit app** on Streamlit Community Cloud. The frontend (`streamlit_app.py`,
`ui/`) is **done with mocks**; the backend `services/` package (Jy) is built during the hackathon
and plugged in by setting `USE_MOCK = False` in `ui/backend.py`.

## 1. Before the event (checklist)

**Jy (backend)**
- [ ] Confirm the hackathon rules: is pre-written code allowed? (Docs and data prep usually are; the frontend team should check the same for their UI.)
- [x] LLM provider: **Gemini**. The key is in `.streamlit/secrets.toml` (gitignored, local only) and was tested on 2026-10-07 (section 6). At deploy time, paste the same lines into Streamlit Cloud → App settings → Secrets. Teammates who run locally copy `.streamlit/secrets.toml.example` and get the key from Jy privately, never via git or chat groups.
- [ ] Install Python 3.12 and the packages once at home, so the venue Wi-Fi doesn't matter.
- [ ] Open the **`Hackathon` repo folder** in Kiro, not the parent `C:\School\Hackhathon` (placeholder steering only). Check that Kiro shows the spec `compliance-alert-backend`.
- [ ] Read NREO s.11A (PDF pages 23–25) and Land Code s.5 (PDF page 28). Confirm or edit `seed/triggers.json` and `seed/eval.json`.

**Team**
- [ ] Merge plan: the frontend lives on `hackathon/frontend`, the backend on `hackathon/backend`, demo from `main`. Folder ownership (structure.md) keeps merges clean; only `requirements.txt` needs a hand merge.
- [ ] Version demo (Plan A): download the archived 2024 Land Code and save it as `seed/pdfs/LandCode_Cap81_LawNet2024_archived.pdf`:
      `https://web.archive.org/web/20240901012758id_/https://lawnet.sarawak.gov.my/lawnet_file/Ordinance/ORD_LANDCODE%20LAWNET%202024%20(1).pdf`
      Then point the `LC` entry in `seed/laws.json` at that file with label `LawNet reprint 2024 (archived copy)`. The 2025 file (already in `seed/pdfs/`) is uploaded live in the demo as the "new version".
- [ ] Optional "new law" demo (Plan B for versions): download the *Sustainable Resources and Waste Management Ordinance, 2025* from LawNet, read it, and decide whether it fits the waste story. Nobody has read it yet, so make no claims about it before then.
- [ ] Streamlit Cloud dry run: deploy the current frontend (mocks) once from GitHub with Python 3.12, so account, permissions and URL are sorted before the event.
- [ ] Prepare the 3 demo actions (section 4) plus one Malay version of the first one; set up screen recording for the backup video.

## 2. The 3 hours

| Time | Backend (Jy + Kiro, `tasks.md`) | Rest of team | Sync point |
|---|---|---|---|
| 0:00–0:15 | Task 1: setup + PDF/LLM smoke tests | Polish UI, colour palette, demo data in mocks | |
| 0:15–0:55 | Tasks 2–3: DB, schemas, parser (timebox) | Slides, demo script, pitch | 0:55 parser status |
| 0:55–1:30 | Tasks 4–5: laws/approvals/seed, retrieval | Slides; prepare the eval sheet | |
| 1:30–2:05 | Tasks 6–7: verify, severity, render, `check_action` + facade | Rehearse the pitch on mocks | |
| 2:05–2:20 | **Task 8: integration**: `USE_MOCK = False`, click through every screen | Pair with Jy on mismatches | **2:20 FEATURE FREEZE** |
| 2:20–2:45 | Task 9: live run, eval numbers, deploy | Put the eval numbers in the slides | |
| 2:45–3:00 | Task 10: 2 rehearsals on the deployed app, backup video | Same | |

If integration fails at 2:20 → demo with `USE_MOCK = True` and show the real backend separately
(e.g. one live `check_action` + highlighted page). Say which parts are mocked.

## 3. Problems found while checking the plan, and the Plan B for each

| # | Problem (what we found) | Plan A (built in) | Plan B |
|---|---|---|---|
| 1 | Real LawNet PDFs have a front table of contents that repeats every section number; section numbers use "⎯" or "—" dashes and `*` markers; footnotes sit inside pages; the Land Code has rules and forms appended with their own numbering | Parser designed for exactly this (design §3), tested on the real PDFs | Upload with `parse_mode="pages"` or a body page range; the officer sees the preview before submitting |
| 2 | Some government PDFs may be scanned (no text) | Both seed PDFs have text (checked); a scanned upload raises `scanned_pdf` | OCR is roadmap; choose text PDFs for the demo |
| 3 | **LawNet keeps only the newest version**: the 2024 Land Code URL now returns 404 (a copy is in the Internet Archive) | Version demo uses the archived 2024 copy + live upload of the 2025 file | Demo a "new law" upload instead. Either way it's a pitch point: *we archive every version and show what changed* |
| 4 | EIA area thresholds are in the Prescribed Activities Order, which is **not** in LawNet's subsidiary list for the NREO (checked on the by-year list) | "Site area" appears as a missing fact; the system never invents a threshold | Upload an unofficial copy with `source_authority="unofficial"` (shown with a badge) |
| 5 | Severity by wording can mislabel: s.11A(1) says the Board "may … require" | Trigger rules carry the legal officer's `severity_override` (seeded red for `waste_disposal`) | Edit the rule live, which shows human in the loop |
| 6 | LLM paraphrases quotes, so conditions get dropped | Prompt demands verbatim; we verify against the exact text sent; near-match ≥ 90% allowed | Shorten quotes to 8–15 words in the prompt, or switch to a stronger model |
| 7 | LLM returns invalid JSON | JSON mode + pydantic validation + 1 retry | Switch model/provider in secrets |
| 8 | Check too slow (> 30 s) | 2 LLM calls, ≤ 10 sections, text capped at 6,000 chars each | Faster model; cap candidates at 6 |
| 8b | **Gemini free tier overloaded**: on 2026-10-07 several Flash models returned 503 "high demand", and the same model took 2–16 s | `llm.py` tries `LLM_MODEL` then `LLM_FALLBACK_MODELS` on 503/429/timeout | Enable billing on the Google project (paid tier) before the demo, or keep a second provider key ready; backup video |
| 9 | Venue internet down | Phone hotspot | Backup video; `LLM_PROVIDER=fake` (shown as "Replay mode", never hidden) |
| 10 | Kiro slow or out of credits | Small tasks, full design written | Jy codes directly from design.md |
| 11 | Streamlit Cloud wipes `data/` on restart; apps sleep after 12 h without traffic | `services` re-seeds itself on the first call | Open the app 10+ minutes before judging; don't redeploy between the live upload and the approval step |
| 12 | Contract mismatches between `ui/backend.py` and `services` (page numbering, ids, null dates) | Backend matches the frontend contract exactly; a contract test checks every key | Fix in `services/__init__.py` only |
| 13 | Windows pitfalls (cp1252 console crash on "⎯", sqlite threads) | Rules in `.kiro/steering/tech.md` | n/a |
| 14 | Original demo idea ("school extension") isn't clearly covered by NREO s.11A(1) | Demo uses a council **waste facility by a river**, which s.11A(1)(h) lists explicitly | School + NCR land is eval case 6 (Land Code s.5) |
| 15 | PyMuPDF is AGPL-licensed | Fine for a hackathon prototype | For production: licence review or switch to pdfplumber |

## 4. Demo script (≈3 minutes)
1. **Hook (20 s):** "An officer is about to approve a project. The law that blocks it belongs to another agency. Nobody told them."
2. **Worker check (40 s):** enter *"Kapit District Council will build a municipal waste recycling and storage facility on a 3-hectare site beside the Rejang River."* Narrate while it loads. Result: 🔴 headline, then the checklist.
3. **Trust (30 s):** open the source: NREO s.11A(3) on PDF page 25, highlighted. Point to "Checked against: …" and to the version and amendment chips.
4. **Human in the loop (60 s):** switch to Legal officer → upload the Land Code 2025 → preview + "N sections changed" → back to the worker: "newer version pending legal review" banner → approve → banner gone → audit log entry.
5. **Rule curation (20 s, optional):** propose a trigger rule → approve.
6. **Close (20 s):** "Never says 'clear'. Every claim is checked against the source. The legal department controls what it knows." Then the eval pass rate from task 9.2.

Other demo actions: *"The Public Works Department plans a new sewage treatment plant for Sibu town."* and *"Purchase of 50 laptops for the district office."* The second is a negative control, which shows the system doesn't flag everything.

## 5. Judge Q&A crib
- **Different from ADAM AI?** ADAM (Sarawak, launched 7 Jul 2026) answers questions from authorised documents and says when information is missing. Ours starts from a *planned action*, finds *other agencies'* laws it triggers, highlights the exact clause, and adds version control + legal-officer approval. It's designed to plug into ADAM, not replace it.
- **Why not built on AWS?** We optimised for a verified, working prototype in 3 hours. The LLM layer is one swappable module; production would run on AWS (e.g. Bedrock) in-region.
- **Where does the data go?** The prototype sends only public law text and demo questions to the LLM API. Production would use an in-region, no-training deployment.
- **Liability?** A reference before acting, not a legal judgement (the same framing as Korea's AI legal secretary pilot for civil servants). The legal department approves everything the system knows.
- **What if it misses a law?** It never says "clear"; it lists exactly which laws were checked. Officers add trigger rules. Quote our eval numbers honestly.
- **How do you stay current?** LawNet replaces old versions (the 2024 Land Code is gone from the site). We archive every version, diff it and require approval. Gazette monitoring is roadmap.
- **Scanned documents? Malay?** Scanned PDFs are rejected (OCR is roadmap). Malay questions work through the LLM; test one before claiming it.
- **Scale?** For thousands of documents: narrow by metadata and keyword search first, then navigate the structure inside each law.

## 6. LLM provider: **chosen: Google Gemini** (key set up and tested on 2026-10-07)
Test on real NREO s.11A text, JSON mode, "copy the quote character-for-character":

| Model | Result |
|---|---|
| `gemini-3.5-flash-lite` (**main**) | valid JSON, quote verbatim, 2.4 s and 15.5 s on two calls |
| `gemini-3.1-flash-lite` (backup 1) | valid JSON, quote verbatim, 6.8 s |
| `gemini-3.5-flash` (backup 2) | 503 once; then valid JSON + verbatim with `reasoning_effort="low"`, 16.5 s; invalid (cut-off) JSON when `max_tokens` was only 800 |
| `gemini-3.8/3.7/3.6-flash`, `gemini-flash-latest` | 503 "high demand" at test time |
| `gemini-2.5-flash` | 404, no longer available to new users |

Free-tier prompts may be used by Google to improve its products, so send only public law text and demo inputs.

Other options, if Gemini becomes unreliable: `services/llm.py` supports any OpenAI-compatible API (one `LLM_BASE_URL` + `LLM_MODEL` + `LLM_API_KEY`), and Claude through its own SDK.

| Provider | Cost for us | Notes |
|---|---|---|
| **Google Gemini, Flash model** (chosen) | Free tier | Key from Google AI Studio; OpenAI-compatible endpoint, so no extra code. Free-tier prompts may be used by Google to improve products: fine for public laws and demo inputs, and an answer ready for the data question |
| Anthropic Claude (Sonnet 5.5 / Opus 5.5) | Paid, about US$0.04 per check with Sonnet 5.5 at list prices (≈12k input + 1.5k output tokens). Opus 5.5 costs more and always thinks, so it's slower | Strong at copying quotes exactly and following format rules; also offered on AWS Bedrock (sponsor story). Needs the `anthropic` SDK branch in `llm.py` |
| DeepSeek | Paid, fractions of a cent per check | OpenAI-compatible JSON mode (the prompt must contain "json"); China-hosted, so expect a data-residency question |
| OpenAI | Paid | OpenAI SDK native; strict JSON-schema outputs |

Rule: use whichever key works first; run `scripts/eval.py`. If `dropped_unverified` is high or JSON fails, switch model.

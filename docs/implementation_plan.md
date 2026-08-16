# FleetFlow — Gap Analysis & Step-by-Step Implementation Plan

> **Status:** Planning only. No code changes made. This document maps the product vision in `docs/product_details.md` against the current codebase and defines an ordered, verifiable implementation plan.

---

## 1. Purpose

`docs/product_details.md` describes the **end-state product**: a WhatsApp-native, zero-app, AI-OCR-driven expense audit engine with automated settlement. The current repo is a **web simulator prototype** (`fleetflow_interactive_demo.py`) that emulates that vision with form posts. This file documents **what is missing** to reach the product spec and how to get there step by step.

---

## 2. What Currently Exists (Baseline)

| Area | Current State |
| --- | --- |
| **Web app** | FastAPI single-file demo (`fleetflow_interactive_demo.py`) with Tailwind-CDN server-rendered HTML. |
| **Database** | Postgres/Neon. `trips`, `expenses`, `fleets`, `vehicles`, `fuel_benchmarks`. Rules constants hardcoded in `utils.py`. |
| **Rules engine** | `evaluate_rules()` in `utils.py` — FUEL (math/price-band/tank/mileage/rollback), TOLL (always flag), REPAIR (>₹3k flag), CHALLAN/RTO-FINE (always flag), DEF (rate + ratio). |
| **Settlement** | ReportLab PDF (`/generate-settlement-pdf`), live ledger, settle-trip flow. |
| **Manager review** | `/action-expense` approve/reject on flagged + goods transactions. |
| **Admin UI** | Dashboard with savings chart, trips list, fuel-benchmark CRUD, rule-engine explainer. |
| **Seeding** | `database/seed.sql`, `schema.sql`, `incremental.sql`, `cleanup.sql`. |

---

## 3. What Is MISSING vs. the Product Spec

### 3.1 Core / Foundational Gaps (blockers for the product vision)

| # | Product Spec | Current State | Gap |
| --- | --- | --- | --- |
| G1 | **Real WhatsApp Cloud API** integration (inbound media webhooks, outbound message templates, session binding by WhatsApp number). | Only a browser **simulator** posts to `/simulate-whatsapp`. `requirements.txt` lists `requests`/`httpx` but nothing calls WhatsApp. | No webhook endpoint, no template handling, no real driver WhatsApp flow. |
| G2 | **AI OCR / Vision parsing** of fuel receipts (extract Amount, Liters, Rate, Pump Name, Odometer timestamp) and odometer photos. | Upload hints mention "OCR" but **no OCR library or model** is wired. `receipt_image_url`/`raw_receipt_text` columns exist but are never populated. | No automatic receipt parsing; driver must type all fields. |
| G3 | **Dual-photo evidence protocol** with **EXIF metadata check** for repairs (damaged-part photo + mechanic invoice). | Only UI hint text. No dual-image enforcement, no EXIF check. | Repair overbilling mitigation not enforced. |
| G4 | **State-dynamic fuel benchmark** (per-state price index, ±8% band). | `fuel_benchmarks` table + CRUD exists, but `evaluate_rules()` uses the **global constant** `BENCHMARK_PRICE=90.50`; it never reads per-state benchmark or tolerance. | Rate check ignores the per-state dynamic benchmark the product promises. |
| G5 | **FASTag corridor whitelisting** (per-route). | `TOLL` is always flagged; no route/corridor data to differentiate cash vs FASTag-mandated. | Cannot distinguish legit cash toll on off-corridor roads from fake claims. |
| G6 | **Photo-based trip initiation & driver onboarding via WhatsApp** (trip binds driver WhatsApp number, bot greeting). | Trip created via web form; no bot greeting or WhatsApp binding beyond storing phone. | No automated driver welcome/context. |

### 3.2 Flow / Parity Gaps

| # | Product Spec | Current State | Impact |
| --- | --- | --- | --- |
| G7 | "Log parsed in <3s without driver text input." | Manual form entry per claim. | Slower, error-prone UX. |
| G8 | **Bilingual (Hindi/English) + audio confirmations** to driver. | Confirmations are web-only text. | Doesn't match WhatsApp-native bilingual promise. |
| G9 | **Live WhatsApp bot replies** (verified slip back to driver). | No outbound messages. | Driver never receives verification. |
| G10 | **Dual-Odometer mandatory dashboard photo at fuel entry** (hard requirement, not just hint). | Not enforced server-side. | Mileage/toll fraud detection incomplete. |
| G11 | Anti-fraud **EXIF/metadata tamper check** + **verified parts** for repairs. | No metadata checks. | Forgery not detected. |
| G12 | Deduction requires **explicit manager confirmation** (labor protection). | Approve/reject covers flagged items; goods auto-pending. **Mostly satisfied — keep.** | Minor: extend confirmation message language. |

### 3.3 Product-doc-only (no code needed)
| # | Item | Note |
| --- | --- | --- |
| G13 | ROI/unit-economics tables, competitive matrix, DPDPA privacy statement. | Marketing/strategy artifacts; optionally add to `README.md`. Not code. |

---

## 4. Proposed Implementation Plan (Ordered)

> Each step is independently verifiable. Backend-first; WhatsApp/OCR come last since they need external credentials.

### Phase A — Data-model & Rules-Engine upgrades (foundation)
- **A1.** Make `evaluate_rules()` benchmark-aware: read per-trip `fuel_benchmarks` (by state) instead of the single constant. Keep `BENCHMARK_PRICE` as fallback. Use `tolerance_pct` for the band.
- **A2.** Add `toll_corridors` table (corridor_name, state, is_fastag_mandated) + seed. Update TOLL rule to flag cash only when the corridor is `100% FASTag`; allow cash on off-corridor. Requires a `corridor` field on the expense.
- **A3.** Enforce **dual-photo / odometer-photo** requirement server-side for FUEL/REPAIR (store photo refs, reject claim if missing). Add `evidence_photos` column on `expenses`.
- **A4.** Add **repair EXIF/metadata check** as a configurable soft flag.

### Phase B — DB Schema updates
- **B1.** New/changed columns: `expenses.corridor`, `expenses.evidence_photos`, `expenses.exif_ok`; new `toll_corridors` table; per-state benchmark linkage on `trips`.
- **B2.** Update `schema.sql` + add statements to `database/incremental.sql` (mirror `trips` FK). Keep zero-DDL-in-app invariant. Seed `toll_corridors`.

### Phase C — WhatsApp Cloud API integration (external creds required)
- **C1.** Add webhook route `POST /whatsapp/webhook` (verify token, `signature`); config via `.env` (`WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`, `WEBHOOK_VERIFY_TOKEN`).
- **C2.** Media receive: download `image` messages → store object/blob → trigger OCR.
- **C3.** Outbound messages: reply confirmation / flag alert / greeting using verified templates.
- **C4.** Trip initialization via WhatsApp inbound text/photo → bind `driver_phone`.

### Phase D — OCR pipeline
- **D1.** Add OCR dependency (e.g., PaddleOCR/Tesseract) + text post-processing to extract Amount/Liters/Rate/Pump/Odometer.
- **D2.** Persist raw text to `raw_receipt_text`; fill form fields; route low-confidence to human review.
- **D3.** Odometer photo → read reading, cross-check vs. claimed `odometer`.

### Phase E — UX / bilingual confirmations
- **E1.** Bilingual (hi/en) confirmation strings; audio via WhatsApp outbound template.
- **E2.** Driver-verification slip rendering (mirror settlement style).

### Phase F — Testing & Docs
- **F1.** Unit tests: benchmark-aware rules, corridor toll rule, dual-photo enforcement, OCR parser.
- **F2.** Update `README.md`, `docs/product_details.md` (mark implemented), and `APP_MINDMAP.md` (add new routes/tables/invariants).

---

## 5. Recommendation Order (Dependencies)

```
Phase A → Phase B → Phase C → Phase D → Phase E → Phase F
   (rules)   (schema)  (WhatsApp)  (OCR)   (UX)   (tests/docs)
```
- **Do Phases A–B first** — no external credentials needed, and they harden the core audit value prop.
- **Phases C–D require WhatsApp Cloud API + an OCR provider** credentials; biggest lift, treat as separate milestones.

---

## 6. Acceptance Criteria (when done)

- A driver's WhatsApp photo yields a parsed expense in <3s with no manual typing (G7).
- FUEL/REPAIR claims missing required photos/odometer photo are blocked server-side (G10/G3).
- TOLL cash claims on FASTag corridors flag; off-corridor cash tolls proceed (G5).
- Per-state benchmark drives the ±8% fuel band per trip (G4).
- Driver receives bilingual + audio WhatsApp confirmation (G8/G9).
- Settlement is untouched and remains 1-click audit-proof.

---

## 7. Note on APP_MINDMAP.md

`APP_MINDMAP.md` was **not modified** in this pass because no implementation was performed. It should be updated **during Phase B/C** once the new tables, columns, and routes actually exist. Changes expected then:
- Add `toll_corridors` to Core Tables; note new `expenses` columns (`corridor`, `evidence_photos`, `exif_ok`).
- Add routes `/whatsapp/webhook`, `/whatsapp/ocr-callback` (if any) to the Routes section.
- Add per-state benchmark lookup to the System Invariants rules-engine constants section.
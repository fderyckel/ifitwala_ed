# docs/portal/guardian/implementation_plan_phase1.md

**Ifitwala_Ed — Guardian Portal (Phase-1)**
Status: Draft (agent-ready)
Audience: Humans + Coding Agents
Depends on (must already exist and remain authoritative):

* `docs/portal/guardian/01_guardian_product.md`
* `docs/portal/guardian/02_information_contract.md`
* `docs/portal/guardian/03_visibility_contract.md`
* `docs/portal/guardian/04_guardian_actions.md`

---

## 0) Goal

Ship a **Guardian Home (Parent Portal landing)** that answers, in <30 seconds:

1. What is happening with my family today and over the next 7 school days?
2. Is anything requiring my attention?
3. What do I need to help my child(ren) prepare for?

Phase-1 is **read-mostly**. Actions are limited and explicitly gated.

---

## 1) Phase-1 Scope (what ships)

### 1.1 Guardian Home (IA Zones 1–4)

Guardian Home renders 4 zones (per contract):

1. **Family Timeline** (backbone)

* Next **7 school days** (calendar-aware, excludes non-school days or labels them explicitly)
* Aggregated across all linked children
* Plain language only (no rotation days, no block numbers)

2. **Attention Needed**

* Only exceptions/alerts where a guardian-visible record exists

3. **Preparation & Support**

* Upcoming assessments / due items / near-term prep cues
* Narrative-first, progressive disclosure

4. **Recent Activity**

* Recently published results, communications, guardian-visible logs, recent attendance exceptions

### 1.2 Minimal “Read state” tracking

* Support marking items as “read” where it is already modeled via `Portal Read Receipt` (or equivalent).

### 1.3 Minimal actions (Phase-1 only)

* **Acknowledge / Read** (where supported by existing doctypes: communications, read receipts, etc.)
* **Booking / Messaging / Upload / Pay**: **not implemented** in Phase-1 (see Non-Goals).
  (UI may show “coming soon” only in a clearly separated area, never as core Home CTAs.)

---

## 2) Explicit Non-Goals (Phase-1)

Phase-1 must NOT implement:

* Payments / invoices / checkout
* Document upload workflows
* Reply/threaded messaging (communications are read-only)
* Real-time grade monitoring or threshold alerts (Monitoring Mode remains **disabled by default** and **not implemented** as alerts)
* Any child comparison feature
* Any exposure of rotation day / block number / internal scheduling mechanics
* Any UI-only permission hiding (all rules enforced server-side)

---

## 3) Architecture Rules (A+ and SPA governance)

### 3.1 Transport boundary

* Only `ifitwala_ed/ui-spa/src/resources/frappe.ts` may call the raw request transport.
* Services must use that wrapper and return **domain payloads only** (no envelope leaking).

### 3.2 Side-effect ownership

* **Services**: no toasts, no UI signals unless explicitly a mutation that affects other surfaces.
* **Pages/Shell**: own refresh, coalescing, toasts (if any), and signal handling.
* **Overlays**: no toasts, no signals, no implicit refresh; inline errors only.

### 3.3 POST shape

* SPA POST requests send a **flat payload** (no `{ payload: ... }` wrapper).
* Server whitelisted methods must accept explicit args and must not read/validate `frappe.form_dict`.

### 3.4 Performance invariants

* Guardian Home should load with **one** backend call (preferred) or at most **two**.
* No N+1 queries.
* Batch queries with `IN` lists for student names.
* Use Redis caching (`frappe.cache()`) for stable/shared computation (short TTL), never in-process dict caching.

---

## 4) Backend Design (Phase-1)

### 4.1 Endpoints (recommended minimal set)

#### Endpoint A — Guardian Home Snapshot (single bundle)

**Purpose:** One call returns everything needed for Guardian Home zones.

* **Whitelisted method:** `ifitwala_ed.api.guardian_home.get_guardian_home_snapshot`

* **HTTP:** `GET` or `POST` (read-only; either is fine, but be consistent with your SPA conventions)

* **Inputs (explicit args):**

  * `start_date` (optional; default = site “today”)
  * `horizon_school_days` (optional; default = 7)
  * `debug` (optional; default = 0) — if enabled, include debug payload (types + counts), never silently ignore missing context

* **Must enforce server-side:**

  * Guardian identity and guardian → student scope
  * Per-record visibility rules:

    * Student Log: guardian-visible only
    * Task Outcome: published-to-parents only
    * Events: audience scoping (if applicable)
    * Attendance: only what guardians are allowed to see (exceptions first)

#### Endpoint B — Mark Read (optional, if existing model supports it)

**Purpose:** Mark an item as “read” using `Portal Read Receipt`.

* **Whitelisted method:** `ifitwala_ed.portal.api.read_receipt.mark_read`
* **Inputs (explicit args):**

  * `ref_doctype`
  * `ref_name`

(If Phase-1 can ship without read receipts, skip Endpoint B and rely on client-side “local seen state” only; do not invent new schema.)

### 4.2 Data sources in scope (already shared)

Phase-1 snapshot may draw from these already-provided doctypes/modules:

* Guardian ↔ Student links:

  * `Guardian`, `Student Guardian`, `Guardian Student`
* Student core:

  * `Student`
* Student support:

  * `Student Log`, `Student Log Follow Up`
* Academics:

  * `Task`, `Task Outcome`, `Task Outcome Criterion`
  * task services: `task_creation_service.py`, `task_submission_service.py`, `task_outcome_service.py`
* Calendar/schedule:

  * `School`, `Academic Year`
  * `School Calendar`, `School Calendar Holidays`
  * `School Event`, `School Event Audience`, `School Event Participant`
  * `School Schedule`, `School Schedule Day`, `School Schedule Block`
* Attendance:

  * `Student Attendance`, `Student Attendance Code`
* Read state:

  * `Portal Read Receipt`

### 4.3 Plain-language schedule translation

Guardian Home must never expose:

* rotation days
* block numbers

Backend should translate schedule items into parent-friendly fields:

* `time_label` (e.g., “Morning”, “After lunch”) and/or `from_time`/`to_time` formatted `hh:mm`
* `title` (subject/class name)
* `location` (if available)
* `child_name`

(Exact field mapping must follow actual doctype fields—do not invent.)

---

## 5) Frontend Design (Phase-1)

### 5.1 SPA file locations

The SPA lives inside the Frappe app folder:

* `ifitwala_ed/ui-spa/…`

### 5.2 Service pattern (existing, confirmed)

Services live under:

* `ifitwala_ed/ui-spa/src/lib/service/<page-or-domain>/…`

Examples already provided:

* `admissionsService.ts`
* `communicationInteractionService.ts`
* `organizationChartService.ts`

### 5.3 New service (Phase-1)

Create a dedicated Guardian Home service folder:

* `ifitwala_ed/ui-spa/src/lib/service/guardianHome/guardianHomeService.ts`

Responsibilities:

* Call `get_guardian_home_snapshot`
* Return typed domain payload
* No UI side-effects (no toasts)

### 5.4 Page wiring

Update / implement the Guardian Home page:

* `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue` (or your current route target)

Responsibilities:

* Fetch snapshot as Refresh Owner
* Render zones in order
* Handle empty states
* Progressive disclosure for details (expand inline, “View all” links)
* No hardcoded `/hub/` prefix in internal navigation (router base already uses it)

---

## 6) TypeScript Contracts (Phase-1)

### 6.1 Contract files

Create contract types consistent with your existing contract governance (do not invent folder conventions beyond your repo):

* `ifitwala_ed/ui-spa/src/contracts/guardian/guardianHomeContracts.ts` (or equivalent)

Define:

* `GuardianHomeSnapshotRequest`
* `GuardianHomeSnapshotResponse`
* `GuardianHomeTimelineDay`
* `GuardianHomeItem` (discriminated union strongly preferred)

**Important:** Types must match server output exactly. No “any”.

---

## 7) Codex Agent Task Breakdown (PR-sized, reversible)

### PR-G1 — Backend snapshot endpoint skeleton

* Add `get_guardian_home_snapshot` method (return empty structured payload with correct keys and types)
* Enforce guardian scope resolution (guardian → linked students)
* Add debug option

**Acceptance**

* Endpoint reachable
* Returns stable JSON shape
* No permission leakage

### PR-G2 — Populate Timeline + Calendar horizon logic

* Implement next 7 **school days** resolution using School Calendar + holidays
* Populate Timeline items using schedule/events/tasks due (signal-only)

**Acceptance**

* Non-school days handled correctly
* No rotation/block exposed
* 1 request returns a coherent timeline

### PR-G3 — Populate Attention Needed

* Add guardian-visible Student Logs
* Add attendance exceptions (as permitted)
* Add unread communications indicator (if comms doctype provided)

**Acceptance**

* All visibility gates enforced server-side
* No staff-only data leaks

### PR-G4 — Populate Preparation & Support + Recent Activity

* Prep: upcoming assessments/due soon (task signal)
* Recent: recently published task outcomes (published-to-parents only)

**Acceptance**

* Results only appear after publish-to-parents
* No draft outcomes appear

### PR-G5 — SPA contracts + service + page wiring

* Add TS contracts
* Add guardianHomeService
* Wire GuardianHome.vue

**Acceptance**

* One network call for Home
* Loading + empty states behave
* No console errors
* No toasts in service/page (unless shell owns it explicitly)

### PR-G6 — Optional read receipts

* Implement `mark_read` endpoint if `Portal Read Receipt` is intended Phase-1
* Wire client call

**Acceptance**

* Read state changes do not cause permission escalation
* Idempotent behavior

---

## 8) Acceptance Criteria (Phase-1 Done Definition)

Guardian Home is Phase-1 complete when:

1. A guardian with 2–4 children can open Home and see:

* today + next 7 school days aggregated
* clear preparation cues
* any exceptions requiring attention

2. No internal schedule jargon is visible (rotation/block never appears).

3. Results are shown only when published to parents.

4. Student logs appear only when guardian-visible.

5. One call loads the Home snapshot (preferred).

6. No sibling comparison surfaces exist.

7. Server-side permissions prevent all cross-family leakage.

---

## 9) Required Inputs from Repo (next batch, to avoid assumptions)

To fully implement communications and policy acknowledgements on Home, I still need:

* Communication doctype + audience child table (`communication.json/.py` and related doctypes)
* Any Policy/Acknowledgement doctypes if you want them in Phase-1 Home

If those are not included in Phase-1, explicitly exclude them in this plan and ship Home with Tasks/Logs/Schedule/Attendance only.

---

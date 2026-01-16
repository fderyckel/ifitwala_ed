## Codex Prompt: StudentLogCreateOverlay Contracts + A+ Compliance

You are working in Ifitwala_Ed SPA (`ifitwala_ed/ui-spa`). Your task: implement **Phase-0 “Contracts & Types Governance”** + the **A+ UI Services + Overlay Lifecycle Contract** for the **StudentLogCreateOverlay** workflow.

### Hard constraints (must obey)

1. **No runtime in `types/`**

   * In `ui-spa/src/types/**`: only `export type` / `export interface`.
   * No `export const`, no functions, no Vue imports, no side effects.

2. **No fetch()** anywhere in SPA.

   * All server calls must use `createResource` (directly or inside a service).

3. **A+ overlay lifecycle**

   * Services orchestrate API calls + invalidation signals.
   * **Overlay owns closing**: on successful submit, overlay closes itself (emits `close`), not the service.
   * Avoid silent failures: always surface errors via toast and/or inline errors.

4. **Contracts are the boundary**

   * Any request/response shapes for API calls used by StudentLogCreateOverlay must live in `ui-spa/src/types/contracts/student_log/...` and be imported as `import type`.

5. **Keep changes minimal**

   * Do not refactor unrelated styles/layout; focus only on types/contracts/service boundaries and correctness.

---

## Inputs you must start from

* File to refactor (authoritative):
  `ui-spa/src/components/student_log/StudentLogCreateOverlay.vue` (use the uploaded content as baseline).
* Existing domain types (if needed):
  `ui-spa/src/types/focusItem.ts`, `ui-spa/src/types/interactions.ts`, etc. (do not introduce runtime into types).
* Existing UI signals pattern (if present):
  `ui-spa/src/lib/uiSignals.ts` (or similar).

---

## Step 1 — Identify endpoints and payload shapes

In StudentLogCreateOverlay, locate every API call (createResource / submit). For each unique server method URL, infer:

* Request kwargs payload keys and types
* Response message shape (the `message` payload after frappe standard wrapping)

Do **not** “guess” new fields. Use what the overlay currently sends/reads.

List the endpoints you found at the top of your PR output as comments (for review).

---

## Step 2 — Create contract files (Phase-0)

Create folder (if not exists):

* `ui-spa/src/types/contracts/student_log/`

For each endpoint used by this overlay, create a contract file:

* `types/contracts/student_log/<action>.ts`

Each contract file exports **only**:

* `export type Request = { ... }`
* `export type Response = { ... }`

Rules:

* Exact field names must match the payload keys used by the overlay today.
* Use literal unions where appropriate (no const arrays).
* No runtime exports.

Example file name patterns (choose names that match what the server does):

* `create_student_log.ts`
* `submit_student_log.ts`
* `get_student_log_context.ts`
  (Use actual method intent from the overlay; do not invent.)

---

## Step 3 — Create/Refactor a service (A+)

Create a service module:

* `ui-spa/src/lib/services/studentLog/studentLogService.ts`

This service must:

* Use `createResource` with `method: 'POST'`
* Accept a `Request` type from the contract
* Return typed `Response` message payload (normalize `data.message` if your app does that consistently)

Required functions (derive from overlay needs; typical):

* `submitStudentLog(payload: SubmitStudentLogRequest): Promise<SubmitStudentLogResponse>`

Service rules:

* No overlay closing logic.
* No direct DOM work.
* It MAY emit invalidation signals (see Step 4).
* It MAY call `toast` best-effort, but overlay must not depend on toast for correctness.

---

## Step 4 — Invalidation / UI signals (A+ correctness)

On success, the service should trigger a clear invalidation event so the rest of the app can refresh:

* Focus list refresh
* Student log list refresh (if relevant)
* Morning briefing refresh (if relevant)

Use the existing signals pattern in the repo (likely `uiSignals.ts`). If none exists, create a minimal one in:

* `ui-spa/src/lib/uiSignals.ts`

Signals must be:

* runtime only (belongs in `lib/`)
* dumb events (e.g. `emit('student_log:created')`)
* no business logic

Overlay will call service, service emits signals, overlay closes itself.

---

## Step 5 — Refactor StudentLogCreateOverlay.vue to consume contracts + service

Update the overlay to:

* Import endpoint types from `types/contracts/student_log/...` using `import type`.
* Call the service function(s) only.
* Maintain correct busy state; disable submit while busy.
* Handle errors explicitly:

  * Show toast error with a safe message
  * Keep overlay open on failure
  * If there is an inline error UI pattern in the overlay, populate it

On success:

* Reset local form state as needed (optional but preferred).
* Emit `close` (or call overlay stack close callback) according to your OverlayHost pattern.
* Do not rely on toast to decide closing.

**Do not change UX layout** besides what’s needed for correct busy/error handling.

---

## Step 6 — Remove any local “API payload” types from the overlay

If StudentLogCreateOverlay currently defines request/response types inline, remove them and move to contracts.

Local types are allowed only if they are purely UI internal and not server-bound.

---

## Step 7 — Guardrails (fast enforcement)

Add a lightweight check (choose one):
A) A small script `scripts/contracts_guardrails.sh` that fails if:

* any file under `ui-spa/src/types/` contains `export const`
* any file under `ui-spa/src/` contains `fetch(`
  OR
  B) If the repo already has lint rules for this, extend them.

Keep it minimal: Phase-0 is about drift prevention, not perfect tooling.

---

## Deliverables (your output)

1. Updated `StudentLogCreateOverlay.vue`
2. New contract files under `types/contracts/student_log/`
3. New/updated service file `lib/services/studentLog/studentLogService.ts`
4. New/updated `lib/uiSignals.ts` (only if needed)
5. Optional guardrail script/lint rule (minimal)

---

## Acceptance tests (must pass mentally, no need to run)

* Submitting a student log:

  * calls service → service calls server via createResource
  * on success: signals emitted, overlay closes reliably
  * on failure: overlay stays open, error is visible (toast and/or inline)
* No `fetch()` introduced
* No runtime exports introduced in `types/`
* Overlay close does not depend on toast existing

---

## Output format required

When you answer, output:

1. A short change summary
2. A file list (added/modified)
3. Full code for each modified/added file (no partial snippets)

End.

---

### What I need from you (only if missing in repo)

If Codex cannot infer the exact server endpoint names from the overlay (URL strings), it must open the related server method files (likely `ifitwala_ed/api/student_log.py` or similar). If still unclear, stop and report the missing endpoint names rather than inventing.

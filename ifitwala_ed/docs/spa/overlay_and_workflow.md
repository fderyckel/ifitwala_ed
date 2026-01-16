# Overlay & Workflow Lifecycle Contract — A+ Model

> **Status:** Canonical (subordinate only to `spa_architecture_and_rules.md`)
>
> **Scope:** Any overlay that triggers a user‑initiated workflow action (submit, complete, reassign, approve, decide, etc.)
>
> **Applies to:** Vue 3 SPA (`ui-spa/`) overlays rendered via `OverlayHost.vue`

---

## 0. Authority

This document is **binding** for any workflow‑triggering overlay.

If an overlay violates this contract, it is a **defect**.

**Parent authority:** `spa_architecture_and_rules.md` remains the *mother file* and overrides this doc if there is any conflict.

---

## 1. Core Decision (A+)

> **Overlay owns closing. UI Services own orchestration.**

Overlay closure must be:

* **local** (owned by the overlay component)
* **immediate** (on server success)
* **deterministic** (no timing dependencies)

**Hard invariant:**

> A successful workflow must never depend on services, toasts, events, refresh, or reload completing in order for the overlay to close.

---

## 1.1 Definitions (shared vocabulary)

**Overlay**
A top-layer UI surface rendered by `OverlayHost.vue` (HeadlessUI `Dialog + TransitionRoot`). Overlays can stack; only the top layer is active; lower layers are inert.

**Workflow**
A domain action that triggers server side-effects (ToDo open/close, notifications, Focus item changes). Workflows are owned by **UI Services + server controllers**, not by pages or Focus.

**UI Services**
Client orchestration modules in `ui-spa/src/lib/services/**` that call endpoints (via `createResource`), normalize responses/errors, emit invalidation signals, and optionally show toasts.

**UI Signals / Invalidation Bus**
Runtime infra (`ui-spa/src/lib/uiSignals.ts`) used to broadcast “a workflow happened; refresh interested surfaces.” It decouples workflow success from refresh policy.

---

## 2. Ownership Matrix (Locked)

| Concern                           | Owner                                      |
| --------------------------------- | ------------------------------------------ |
| API calls                         | **UI Services** (`ui-spa/src/lib/…`)       |
| Business validation               | **Server**                                 |
| Idempotency enforcement           | **Server**                                 |
| Refresh policy / invalidation     | **UI Services**                            |
| Toasts / messaging                | **UI Services** (or shared UI layer later) |
| **Overlay close**                 | **Overlay**                                |
| Overlay stack removal / lifecycle | **OverlayHost**                            |

---

## 3. Mandatory Overlay API (Hard Requirement)

### 3.1 Inputs (props)

Every workflow overlay must accept:

```ts
{
  open: boolean
  zIndex?: number
  overlayId?: string
}
```

**Source of truth:** these props are owned by `OverlayHost` via the overlay stack.

### 3.2 Outputs (events)

Every workflow overlay must emit:

```ts
emit('close')
emit('after-leave')
emit('done', payload?)
```

* `close` — **mandatory**
* `after-leave` — **mandatory** (so OverlayHost can finalize removal)
* `done(payload?)` — **optional** and **advisory only** (never gates closing)

---

## 4. Success Sequence (Locked)

On **successful workflow completion**:

1. **Immediately** emit `close`
2. Optionally emit `done(payload)` (best‑effort)
3. Return control to `OverlayHost`

Everything else (toast, refresh, analytics, local reload) is **best‑effort** and must happen **after** close.

### 4.1 Prohibitions

* Never wait for refresh before closing
* Never wait for toast availability before closing
* Never block close behind `busy` cleanup
* Never use “reload then close”

---

## 5. UI Services Contract (Hard Rules)

### 5.1 What UI Services own

UI Services:

* call whitelisted endpoints (via `createResource`)
* normalize responses/errors
* generate client request ids (for server‑side idempotency)
* emit invalidation signals (Focus refresh, list refresh, etc.)
* show toasts/banners (optional)

### 5.2 What UI Services must never do

UI Services must **never**:

* close overlays
* mutate the overlay stack
* depend on HeadlessUI lifecycle timing
* call overlay APIs

**Rule:** UI Services **never** call overlay stack APIs.

---

### 5.3 Signals subscription rule (A+)

**Rule:** If you need a disposer/unsubscribe function, do **not** use `uiSignals.on()`.

- `uiSignals.on()` is low-level registration and requires `uiSignals.off(name, handler)`
- `uiSignals.subscribe()` returns a disposer and is the preferred API for Vue `setup()` blocks

Violations are **defects**, not style issues.

---

## 6. OverlayHost Responsibilities (Non‑Negotiable)

`OverlayHost` is the **single authority** for overlay existence and lifecycle.

It must guarantee:

1. When an overlay is removed from the stack, it:

   * becomes inactive/inert if not top
   * transitions out (`open=false`)
   * is removed after `after-leave`
2. Removal must not depend on child overlay correctness
3. Errors inside overlays must not trap the user

OverlayHost treats overlays as potentially faulty children.

---

## 7. Naming Rules (Critical / Frappe‑safe)

### 7.1 Forbidden names

Do **not** use:

* `get_context`
* `context`
* `resolve_context`

### 7.2 Approved intent patterns

* **Resolve** = “turn an ID into an enriched payload”

  * client: `resolveFocusItemPayload()`
  * server: `resolve_focus_item_payload`

* **List** = list endpoints

  * client: `listFocusItems()`
  * server: `focus_list_items`

* **Workflow verbs** for actions

  * client: `submitFollowUp()`
  * server: `student_log_follow_up_submit`

**Rule:** if a name could be confused with framework internals, rename it **now**, not later.

---

## 8. Focus Interaction (Clarified)

### 8.1 Focus is not a workflow engine

Focus:

* surfaces attention
* routes to overlays/workflows
* refreshes after completion

Focus does **not**:

* decide outcomes
* close overlays
* interpret success beyond “server call succeeded”

### 8.2 Refresh is advisory

* Overlays may emit `done`
* UI Services emit invalidation signals
* Pages/surfaces listening to signals refresh themselves

**Overlay closure is never dependent on Focus refresh.**

### 8.3 Pages own refresh (explicit)

Under A+:

- **Pages** subscribe to invalidation signals and decide how/when to refresh
- **Services** emit invalidation after successful workflows
- **Overlays** close immediately on success and must not “refresh-gate” closing

---

## 9. UX Contract (User‑Visible)

From the user’s perspective:

* **Success = overlay disappears immediately**
* no spinner purgatory
* no “did it work?” ambiguity

Any delay (refresh, list updates, toasts) happens **after** the overlay is gone.

---

## 10. Enforcement Checklist (Humans + Agents)

Before merging any workflow overlay:

* [ ] Emits `close` immediately on success
* [ ] Emits `after-leave`
* [ ] Does not wait for refresh/toast/reload before closing
* [ ] Uses a UI Service for API calls
* [ ] No forbidden naming (`get_context`, `context`, `resolve_context`)
* [ ] OverlayHost remains lifecycle authority (no stack mutations in overlays/services)

If any fails → reject PR.

---

## 11. Subsumed Notes

This document **subsumes** (reference only, non‑authority):

* `overlay_contract_governance.md`
* `ui_services_note.md`

---

## 12. Refactor guidance (A+ alignment targets)

**StudentLogCreateOverlay (baseline)**
Treat as the reference behavior: closes immediately on server success; never gated by toast/refresh/reload.

**StudentLogFollowUpOverlay (must align)**
Must:
- emit `close` immediately on success
- never block close behind `busy`
- treat any reload/refresh as best-effort via signals (after close)

**FocusRouterOverlay (router only)**
Must:
- resolve routing payload once (via service)
- pass resolved payload down
- avoid child overlays refetching the same payload
- never intercept or gate overlay close

---

# Appendix A — Contracts & Types Governance (Phase 0) — Reference

> **Status:** Phase 0 (now) — governance + guardrails + first contracts
>
> **Scope:** `ui-spa/src/{types,lib,utils}`, SPA ↔ server contracts, service transport, role-scoped DTOs
>
> **Authority note:** This appendix is **subordinate** to `spa_architecture_and_rules.md`.

---

## 0) Why this exists

We already saw predictable drift:

* runtime constants/configs sneaking into `types/`
* duplicate “payload types” living inside Vue pages
* a parallel `fetch()` transport existing alongside `createResource`

At small scale this is tolerable.
At scale (more modules, analytics, agents), it becomes:

* silent contract mismatches
* accidental data exposure across surfaces
* fragmented caching/error handling
* expensive refactors later

**Phase 0 goal:** make contracts and types *enforceable*, not aspirational.

---

## 1) Non‑negotiable rules

### 1.1 `types/` = contracts only (zero runtime)

Hard rules:

* ✅ Allowed: `export type`, `export interface`, literal unions
* ❌ Forbidden: `export const`, `export function`, side effects, Vue imports

**Review rule:** if `types/` contains runtime code → FAIL.

---

### 1.2 `utils/` = pure stateless helpers

* deterministic helpers only
* no state, no registries, no orchestration

---

### 1.3 `lib/` = runtime + services + orchestration

* services calling server
* runtime configs / constants
* signals, orchestration

❌ Not allowed:

* business rules (server owns them)
* overlay closing (overlay owns it)

---

### 1.4 One transport only

* ❌ no `fetch()` (direct or wrapped)
* ✅ all server calls use `createResource`

---

## 2) What we mean by **Contracts** (core concept)

### 2.1 Plain definition

A **contract** is an explicit, named description of:

* what the client is allowed to send to the server
* what the server promises to return

Nothing more. Nothing less.

A contract is **not**:

* UI state
* business logic
* workflow rules

It is the *boundary agreement* between SPA and server.

---

### 2.2 Why types alone are not enough

Today, many payload types live:

* inside Vue pages
* inside services
* sometimes duplicated

That means the *real contract* exists only implicitly, in the server code.

Contracts make that boundary:

* visible
* reviewable
* enforceable

---

## 3) Contract files (Phase‑0 format)

Create:

```
ui-spa/src/types/contracts/
```

Structure by domain:

```
types/contracts/
  focus/
    list_focus_items.ts
    resolve_focus_item.ts
  student_log/
    submit_follow_up.ts
```

Each file exports **only types**.

---

## 4) Contract file structure

Example:

```
export type Request = {
  open_only: 0 | 1
  limit?: number
  offset?: number
}

export type Response = {
  items: FocusItemDTO[]
  total: number
}
```

Rules:

* matches server whitelisted method **exactly**
* no runtime code
* no defaults
* no inference

---

## 5) Role‑scoped DTOs (security by design)

If the same DocType is exposed differently:

* staff
* student
* guardian

Then define separate DTOs:

```
StudentLogStaffDTO
StudentLogStudentDTO
StudentLogGuardianDTO
```

Even if identical today.

This prevents accidental UI leakage.

---

## 6) Runtime enums & configs

Pattern:

* `types/` → literal unions only
* `lib/constants/` → runtime arrays/maps

Never colocate runtime data in `types/`.

---

## 7) Services and contracts

Services:

* live in `lib/services/`
* call `createResource`
* import contract types

Services do NOT:

* close overlays
* implement workflow rules

---

## 8) Enforcement (Phase‑0)

### CI / script checks

Fail build if:

* `types/` contains `export const`
* any file contains `fetch(`

### Review checklist

* new endpoint → new contract file
* no page‑local API payload types
* role‑scoped DTOs where relevant

---

## 9) Phase‑0 completion criteria

Done when:

* zero runtime code in `types/`
* zero `fetch()` usage
* Focus + Student Log endpoints have contracts
* at least one domain uses role‑scoped DTOs

---

## 10) Mental model

> **Server owns truth.**
> **Contracts name the truth.**
> **Types enforce the truth.**
> **Services obey the truth.**
> **UI renders the truth.**

---

A+ Governance Appendix
All services must return already-normalized domain payloads. Components never unwrap.
Components must not unwrap transport shapes. Ever.

Services must return domain payloads. Always.
Pages MUST subscribe to uiSignals
Overlays MUST NOT emit refresh events
Services MUST be the only emitters
DOM events are forbidden for SPA invalidation
Violations are defects, not stylistic differences

---

# Appendix B — Codex Prompt (Reference)

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

# Appendix C — Implementation plan (universal A+ rollout) — Reference

**Phase 1 — Lock naming + contract compliance**
- Prefer `payload/resolved` over exported `context` naming

**Phase 2 — UI Signals / Invalidation Bus**
- Centralize signals in `ui-spa/src/lib/uiSignals.ts`
- Pages subscribe; services emit; overlays never depend on refresh to close

**Phase 3 — Thin services**
- Move endpoint calling + normalization to `ui-spa/src/lib/services/**`

**Phase 4 — Workflows into services**
- Services emit invalidation on success
- Overlays close immediately on success

**Phase 5 — OverlayHost / stack boundary**
- OverlayHost uses only stack public API
- No raw stack mutations from overlays/services

**Phase 6 — Hardening**
- In-flight dedupe per service method
- Optional signal throttling on the page side
- Server TTL caching where safe

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







Step 2 — Remove transport logic from FocusRouterOverlay (NEXT, highest impact)

Goal: FocusRouterOverlay.vue becomes a pure overlay shell + router.
It must not contain:

createResource

unwrapMessage

any axios-shape handling

Instead it calls:

focusService.getFocusContext(payload) (service already normalizes)

This step is the main source of “circles.” Fixing it stops the churn.

✅ What I need from you now (no debate):
Paste the exact current <script setup lang="ts"> from your ui-spa/src/components/focus/FocusRouterOverlay.vue.

Only the script. Nothing else.

Why: I will patch it precisely (no assumptions) and after you apply it, we treat it as DONE.

Step 3 — OverlayHost enforcement + no direct mutation

Goal:

OverlayHost.requestClose() must call only overlay stack API methods.

No overlay.state.stack = ... anywhere.

Enforce closeOnBackdrop/closeOnEsc centrally as far as the host can.

Use your new forceRemove(id) as the only emergency hatch.

✅ What I need when we get there:
Paste the current <script setup> of OverlayHost.vue from your machine (the one you actually have now).

Step 4 — Done semantics Option A (child emits done only)

Goal: Remove double-close risk:

Child emits done (success)

Router closes on done

Child does not close itself on success

✅ What I need when we get there:
Paste the current <script setup> of StudentLogFollowUpAction.vue from your machine (even if you already pasted it earlier—what matters is what’s in your repo now).

Non-negotiable working rules (to stop looping)

I will not output patches for files you haven’t pasted in their current state.

Once I output a patch and you apply it, we treat that file as authoritative and do not revisit it unless there’s a new bug report with evidence.

One file per message, script-only if that’s the only change.

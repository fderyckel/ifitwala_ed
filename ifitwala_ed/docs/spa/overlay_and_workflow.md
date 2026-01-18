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
Client orchestration modules in `ui-spa/src/lib/services/**` that call endpoints (via `createResource`), normalize responses/errors, and emit invalidation signals.

> **Locked:** Services do **not** toast. UX feedback is owned by refresh owners (page/shell). (See §9.2)

**UI Signals / Invalidation Bus**
Runtime infra (`ui-spa/src/lib/uiSignals.ts`) used to broadcast “a workflow happened; refresh interested surfaces.” It decouples workflow success from refresh policy.

---

## 2. Ownership Matrix (Locked)

| Concern                           | Owner                                                |
| --------------------------------- | ---------------------------------------------------- |
| API calls                         | **UI Services** (`ui-spa/src/lib/services/**`)       |
| Business validation               | **Server**                                           |
| Idempotency enforcement           | **Server**                                           |
| Refresh policy / invalidation     | **UI Services** (emit) + **Pages/Shell** (subscribe) |
| Toasts / messaging                | **Refresh Owners** (page/shell)                      |
| **Overlay close**                 | **Overlay**                                          |
| Overlay stack removal / lifecycle | **OverlayHost**                                      |

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

Everything else (refresh, analytics, UX feedback) is **best‑effort** and must happen **after** close.

### 4.1 Prohibitions

* Never wait for refresh before closing
* Never wait for “toast availability” before closing
* Never block close behind `busy` cleanup
* Never use “reload then close”

---

## 5. UI Services Contract (Hard Rules)

### 5.1 What UI Services own

UI Services:

* call whitelisted endpoints (via `createResource`)
* **emit invalidation signals only after confirmed semantic success**
* generate client request ids (for server-side idempotency) when relevant

> **Locked:** Transport envelope unwrapping is centralized in `ui-spa/src/resources/frappe.ts`.
> Services return **domain payloads only**.

### 5.1.1 When to introduce a new invalidate signal (NEW / LOCKED)

Add a **dedicated** `uiSignals` constant (and emit it from the service) if the mutation can affect **any other mounted surface** besides the current page (counts, badges, lists, cards, focus, dashboards).

Keep **local refresh only** if the mutated data is **guaranteed** to be rendered nowhere else in the SPA.
**Default:** if uncertain, add a signal (cross-surface safety beats hidden staleness).
**Rule:** shared invalidation signals must be exported constants in `ui-spa/src/lib/uiSignals.ts`
(no raw string literals in services/components/pages).

### 5.2 What UI Services must never do

UI Services must **never**:

* close overlays
* mutate the overlay stack
* depend on HeadlessUI lifecycle timing
* call overlay APIs
* show toasts

**Rule:** UI Services never call overlay stack APIs.

---

### 5.3 Signals subscription rule (A+)

**Rule:** If you need a disposer/unsubscribe function, do **not** use `uiSignals.on()`.

* `uiSignals.on()` is low-level registration and requires `uiSignals.off(name, handler)`
* `uiSignals.subscribe()` returns a disposer and is the preferred API for Vue `setup()` blocks

Violations are **defects**, not style issues.

---

## 5.4 Service Success Gating (semantic, not HTTP)

Services may emit invalidation signals **only** after *semantic mutation success*.

**Not allowed:**

* emission “on submit”
* emission on HTTP 200 alone
* emission on “no exception thrown”

**Allowed patterns:**

* `ok === true`
* explicit `status` representing mutation (`'created' | 'updated' | 'processed'`)
* other explicit backend-owned success field

> **Rule:** Components/overlays are forbidden from deciding mutation success or emitting signals.

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
* interpret success beyond “service call succeeded”

### 8.2 Refresh is advisory

* Overlays may emit `done`
* UI Services emit invalidation signals
* Pages/surfaces listening to signals refresh themselves

**Overlay closure is never dependent on Focus refresh.**

### 8.3 Pages own refresh (explicit)

Under A+:

* **Pages/Shell** subscribe to invalidation signals and decide how/when to refresh
* **Services** emit invalidation after *confirmed semantic success*
* **Overlays** close immediately on success and must not “refresh-gate” closing

**Signal scope rule (LOCKED):**
If a workflow mutation can affect any other mounted surface, the service must emit a dedicated invalidate signal.
Local refresh-only is allowed only when the mutation is strictly page-local.

---

## 9. UX Contract (User‑Visible)

From the user’s perspective:

* **Success = overlay disappears immediately**
* no spinner purgatory
* no “did it work?” ambiguity

Any delay (refresh, list updates, UX feedback) happens **after** the overlay is gone.

---

## 9.2 UX Feedback Ownership (LOCKED)

**UX feedback after success is owned by Refresh Owners (page/shell) and is triggered by signal semantics.**

Meaning:

* Services emit `*_invalidate` signals **only after confirmed semantic success**
* Refresh owners (page/shell) receive the signal, refetch, and may show a “Saved” toast
* Overlays close immediately and do **zero** UX signaling (**no toast, no signals, no refetch**)

**Safeguard:** Every surface that can initiate that workflow must have a refresh owner subscribed (page or shell-level listener).

---

## 10. Enforcement Checklist (Humans + Agents)

Before merging any workflow overlay:

* [ ] Emits `close` immediately on success
* [ ] Emits `after-leave`
* [ ] Does not wait for refresh/toast/reload before closing
* [ ] Uses a UI Service for API calls
* [ ] No forbidden naming (`get_context`, `context`, `resolve_context`)
* [ ] OverlayHost remains lifecycle authority (no stack mutations in overlays/services)
* [ ] Overlays do not emit signals
* [ ] Services emit signals only after semantic success
* [ ] Pages/Shell subscribe and own refresh + optional UX feedback

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

* emit `close` immediately on success
* never block close behind `busy`
* treat any reload/refresh as best-effort via signals (after close)

**FocusRouterOverlay (router only)**
Must:

* resolve routing payload once (via service)
* pass resolved payload down
* avoid child overlays refetching the same payload
* never intercept or gate overlay close

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

At scale, this becomes:

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
* ✅ all server calls use `createResource` (via `ui-spa/src/resources/frappe.ts`)

---

## 2) What we mean by **Contracts** (core concept)

A **contract** is an explicit, named description of:

* what the client is allowed to send to the server
* what the server promises to return

Nothing more. Nothing less.

---

## 3) Contract files (Phase‑0 format)

Create:

```txt
types/contracts/
```

Structure by domain:

```txt
types/contracts/
  focus/
  student_log/
```

Each file exports **only types**.

---

## 4) Contract file structure

Example:

```ts
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

```txt
StudentLogStaffDTO
StudentLogStudentDTO
StudentLogGuardianDTO
```

Even if identical today.

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
* call the transport via `resources/frappe.ts`
* import contract types

Services do NOT:

* close overlays
* implement workflow rules

---

## 8) Enforcement (Phase‑0)

Fail build if:

* `types/` contains runtime code
* any file contains `fetch(`

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


What this means (rules, in one screen)

Overlays: never toast (already locked)

Services: never toast; only emit uiSignals after confirmed success

Pages / Shell (refresh owners):

may toast for local validation + local failures

should not toast global “Saved” unless they are the refresh owner for that workflow (your existing pattern)

# UI Services + Overlay Lifecycle Contract (SPA) — **A+ Model**

> **Status:** Locked architectural direction
> **Scope:** Vue 3 SPA (`ui-spa`), `OverlayHost`, Focus, Student Log, Task, and all future workflows
> **Applies to:** Any overlay that triggers a **user-initiated workflow action** (submit, complete, reassign, approve, etc.)

---

## 1) Architecture and intents

### 1.1 Why this exists

We keep hitting the same failure class:

* Overlays that **don’t close after success**
* “Silent failures” created by accidental coupling to:

  * toast wrappers
  * event ordering
  * missing `after-leave`
  * busy states blocking close
* Confusion about **who owns “done” vs “close”**
* Increasing fragility as workflows expand (Focus, Follow-up, Review, Reassign, etc.)

These are not isolated component bugs. They are symptoms of a missing, enforceable contract.

---

### 1.2 Core decision: A+ ownership split

We adopt **A+**:

> **Overlay owns closing. UI Services own orchestration.**

This deliberately separates **UI lifecycle correctness** from **workflow correctness** while keeping overlay closing **local, immediate, and reliable**.

---

### 1.3 High-level model (what owns what)

| Responsibility                    | Owner                                      |
| --------------------------------- | ------------------------------------------ |
| API calls                         | **UI Services**                            |
| Business validation               | **Server**                                 |
| Idempotency                       | **Server**                                 |
| Refresh policy / invalidation     | **UI Services**                            |
| Toast / user messaging            | **UI Services** (or shared UI layer later) |
| **Overlay close**                 | **Overlay component**                      |
| Overlay stack removal / lifecycle | **OverlayHost**                            |

**Key invariant (non-negotiable):**

> A successful workflow must never depend on services, toasts, events, refresh, or reload completing in order for the overlay to close.

That one sentence is the entire “A+” model.

---

### 1.4 Definitions (shared vocabulary)

#### Overlay (UI container)

A top-layer UI surface rendered by `OverlayHost.vue` using HeadlessUI (`Dialog + TransitionRoot`) and the Overlay Stack. Overlays can stack. Only the top is active; lower layers are inert.

#### Workflow (domain action)

A domain operation that triggers server side effects (ToDo open/close, notifications, Focus list changes). Workflows are owned by **UI Services + server controllers**, not by Focus or pages.

#### UI Services (client orchestration layer)

Client modules that:

* call whitelisted endpoints
* normalize responses/errors
* handle idempotency tokens (client-generated, server-enforced)
* decide invalidation/refresh signals
* show toasts/banners (or route to a UI messaging service later)

They exist to stop each overlay from becoming a mini app.

#### UI Signals / Invalidation Bus (integration glue)

A single, stable mechanism for saying: “a workflow happened; refresh the surfaces that care.”
This is the integration point between **workflow success** and **refreshable UI surfaces** (Focus list today; more later).

---

### 1.5 The Overlay Lifecycle Contract (hard rules)

#### Inputs (props) every workflow overlay must accept

```ts
{
  open: boolean
  zIndex?: number
  overlayId?: string
}
```

These are owned by `OverlayHost` (source of truth), not by overlays.

#### Outputs (events) every workflow overlay must emit

```ts
emit('close')         // mandatory
emit('after-leave')   // mandatory
emit('done', payload?) // optional, best-effort
```

#### Mandatory success sequence (A+ rule)

On **successful workflow completion**, the overlay must do this in a deterministic way:

1. **Immediately emit `close`**
2. Optionally emit `done(payload)` (advisory only)
3. Return control to `OverlayHost`
4. Anything else (toast, refresh, analytics, local reload) is **best-effort** and must never gate closing

**Prohibition:** never wait for refresh, toast, reload, or “service confirmation UI” before closing.
If the server call succeeded, the overlay closes.

---

### 1.6 UI Services Contract (hard rules)

#### What UI Services own

* calling endpoints
* retries/backoff (if needed)
* client request id tokens (for server idempotency)
* normalizing server responses
* emitting invalidation signals (Focus refresh, list invalidation, etc.)
* showing toasts/banners

#### What UI Services must never do

* close overlays
* mutate overlay stack
* know about `open`, `zIndex`, HeadlessUI lifecycle, DOM timing
* call overlay APIs

**Rule:** UI Services **never** call overlay stack APIs.

---

### 1.7 OverlayHost responsibilities (non-negotiable)

`OverlayHost` is the **single authority** for overlay existence and lifecycle.

It must guarantee:

1. When an entry is removed from the store stack, the rendered overlay:

   * becomes inactive/inert (if not top)
   * transitions out (`open=false`)
   * is removed after `after-leave`
2. Removal must not depend on child code behaving correctly
3. Errors inside overlays must not block unmount or trap the user

OverlayHost treats overlays as potentially faulty children.

---

### 1.8 Naming rules (critical / Frappe-safe)

#### Forbidden names

Do **not** use:

* `get_context`
* `context`
* `resolve_context`

These collide semantically with Frappe Website conventions, frappe-ui, Vue, and HeadlessUI mental models.

#### Approved intent-based patterns

* **Resolve** = “turn an ID into an enriched payload”

  * server: `focus_resolve_item_payload` / `resolve_focus_item_payload`
  * client: `focusService.resolveItemPayload()`
* **List** = list endpoints

  * server: `focus_list_items`
  * client: `focusService.list()`
* **Workflow verbs** for actions

  * `student_log_follow_up_submit`
  * `student_log_review_decide`
  * client: `studentLogFollowUpService.submitFollowUp()`

**Rule:** if a name could be confused with framework internals, rename it now, not later.

---

### 1.9 Focus + Overlay interaction (clarified)

#### Focus is not a workflow engine

Focus:

* surfaces attention
* routes to overlays/workflows
* refreshes after completion

Focus does **not**:

* decide outcomes
* close overlays
* interpret “success” beyond “service told us it succeeded”

#### Focus refresh is advisory

* Overlays may emit `done`
* UI Services emit invalidation signals
* Pages/surfaces listening to invalidation refresh themselves

**Overlay closure is never dependent on Focus refresh.**

---

### 1.10 UX contract (explicit, user-visible)

From a user’s perspective:

* **Success = overlay disappears immediately**
* No spinner purgatory
* No “did it work?” ambiguity
* Any delay (refresh, list updates, toasts) happens **after** the overlay is gone

This is non-negotiable UX.

---

### 1.11 Refactor guidance (how existing parts must behave)

#### StudentLogCreateOverlay (baseline)

This already behaves correctly (close on success, no gating). Treat it as the reference.

#### StudentLogFollowUpOverlay (must align to A+)

Must be refactored to:

* emit `close` immediately on success
* never block close on `busy`
* treat any `reload()` as optional UX improvement (and do it after close if needed via invalidation)

#### FocusRouterOverlay (router only)

Must:

* resolve routing data once
* pass resolved payload down
* avoid child overlays refetching the same payload
* never intercept close logic

---

### 1.12 Future-proofing and honest complexity assessment

#### Why A+ scales to thousands of users

* closing is local → no server coupling
* refresh policies can be throttled/cached/debounced without affecting close
* no cascade failure when refresh endpoints slow down
* multi-tab safe: idempotency is server-side; client uses request ids

#### Added complexity

* a services layer
* a signals bus
* discipline in overlays

#### Removed complexity

* most “why didn’t it close?” debugging
* hidden lifecycle coupling
* brittle toast-driven timing logic
* per-overlay bespoke refresh logic

Net: higher short-term discipline, lower long-term complexity.

---

### 1.13 Enforcement checklist (for humans + agents)

Before merging any workflow overlay:

* [ ] emits `close` on success (immediate)
* [ ] emits `after-leave`
* [ ] does not wait for refresh/toast/reload before closing
* [ ] uses a UI Service for workflow API calls
* [ ] no `get_context` naming (server or client)
* [ ] OverlayHost remains the lifecycle authority (no stack mutations in overlays/services)

If any fails → reject PR.

---

### 1.14 Final principle (memorize)

> **Overlays close because the user action is done — not because the system feels ready.**

---

## 2) Implementation plan (universal, A+ aligned)

### Phase 1 — Lock naming + contract compliance (doc + small safe changes)

**Goal:** eliminate collision risk and make contract enforceable.

1. **Rename** `ifitwala_ed.api.focus.get_focus_context`

   * Replace with an explicit “resolve” name (example):

     * server: `ifitwala_ed.api.focus.resolve_focus_item_payload`
     * client: `focusService.resolveItemPayload()`
   * Keep the old endpoint temporarily as an alias if needed, then delete.

2. Update client code to avoid ambiguous local naming where it creates confusion:

   * prefer `payload`, `resolved`, `focusPayload` over `context` in public-facing APIs.
   * internal `ctx` variables are fine, but don’t call exported functions “get_context”.

3. Document the overlay contract as a required template for every new overlay.

**Deliverable:** updated note (this file) becomes canonical; add it to your architecture notes repo.

---

### Phase 2 — Add the UI Signals / Invalidation Bus (the glue)

**Goal:** make refresh behavior consistent and decoupled.

Create:

* `ui-spa/src/services/uiSignals.ts`

Must provide:

* `on(signal, handler)`
* `emit(signal, payload?)`
* `off(signal, handler)` (recommended)

Define stable signals now:

* `focus:invalidate`
* optionally `student_log:invalidate` (future-proof)
* optionally `toast:show` (only if you later centralize toasts)

Refactors:

1. Replace `window.dispatchEvent(new CustomEvent('ifitwala:focus:refresh'))`

   * with `uiSignals.emit('focus:invalidate')`

2. `StaffHome.vue` (Focus surface) subscribes:

   * on `focus:invalidate` → call `refreshFocus('signal')`
   * unsubscribe on unmount

**Why this matters:** overlays stop “reloading themselves before closing,” which is a major source of stuck overlays and race conditions.

---

### Phase 3 — Introduce thin services (wrappers first, keep behavior identical)

**Goal:** stop scattering `createResource` + endpoints across overlays.

Create:

* `ui-spa/src/services/focus/focusService.ts`

  * `list({ openOnly, limit, offset })`
  * `resolveItemPayload({ focusItemId, referenceDoctype?, referenceName? })`

Refactor:

* `FocusRouterOverlay.vue` uses `focusService.resolveItemPayload()` instead of calling endpoints directly.

**Decision to lock:** pick one internal transport:

* either `frappeRequest` (recommended for service purity), or
* `createResource` (ok but keep it consistent)
  Don’t mix patterns per service.

---

### Phase 4 — Move workflows into services (real A+ benefit)

**Goal:** overlays become thin shells; services emit invalidation; overlays close immediately.

Create:

* `ui-spa/src/services/student_log/studentLogFollowUpService.ts`

  * `submitFollowUp({ focusItemId, studentLog, followUp, clientRequestId })`
  * `reviewOutcome({ focusItemId, decision, followUpPerson?, clientRequestId })`

Service responsibilities:

* call endpoints
* normalize errors
* toast (optional)
* emit `uiSignals.emit('focus:invalidate')` on success (and later `student_log:invalidate`)

Refactor:

* `StudentLogFollowUpAction.vue` / `StudentLogFollowUpOverlay.vue`:

  * call service
  * on success: `emit('done', result?)` then `emit('close')` immediately
  * no “reload before closing”

---

### Phase 5 — Standardize OverlayHost / OverlayStack boundary (remove “guessing”)

**Goal:** OverlayHost uses only the overlay stack public API; no raw state writes.

1. Ensure `OverlayHost` only calls:

* `overlay.close(id)` (or `overlay.forceClose(id)` if you intentionally add it as a public escape hatch)

2. If you want emergency fallback behavior:

* implement `forceClose(id)` in `useOverlayStack.ts`
* do **not** mutate `overlay.state.stack` directly inside `OverlayHost`

3. Make fallback timers and transition durations consistent:

* if overlays use longer transitions, ensure cleanup timer doesn’t preempt.

---

### Phase 6 — Cloud readiness hardening (performance + correctness at scale)

**Goal:** avoid thundering herds and stale UI under load.

Client:

* in-flight dedupe per service method (don’t start 3 resolve calls for the same focus id)
* throttle `focus:invalidate` handling (optional; e.g., collapse bursts to 1 refresh)

Server:

* per-user short TTL caching for focus list (e.g., 30–60s)
* idempotency enforced server-side using `clientRequestId` keys for workflow actions
* ensure endpoints are cheap and avoid N+1 doc loads (already your principle)

---

### Refactor targets summary (what changes where)

* **Rename** focus resolve endpoint (server + client callers)
* Add `uiSignals.ts`
* Wire `StaffHome` to listen to `focus:invalidate`
* Refactor `FocusRouterOverlay` to:

  * resolve via `focusService`
  * emit invalidation via signals (not raw window events)
  * remain purely router + view
* Refactor workflow overlays/actions to:

  * call services
  * close immediately on success

---

If you want, paste your current `StudentLogFollowUpAction.vue` and I’ll align its exact responsibilities to this A+ contract (without changing your new CSS/style decisions).

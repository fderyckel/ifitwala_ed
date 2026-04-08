# Vue SPA Architecture & Development Rules (AUTHORITATIVE)

> **Status:** Canonical, highest-authority SPA document
> **Scope:** All Vue 3 SPA code in `ui-spa/` (pages, components, overlays, composables, API usage, styling)
> **Audience:** Humans + coding agents
>
> **Important:** This file is the authoritative superset. Earlier summaries are superseded.

---

## Source Notes (Subsumed, Not Deleted)

This canonical file **subsumes** (kept for reference, not authority):

* `developing_vue_pages_note.md`
* `contract_and_type_phase0.md`
* `overlay_contract_governance.md`
* `ui_services_note.md`

---

# Ifitwala_Ed — Vue SPA Development Rules

## 0. First Principles (Read Before Writing Code)

### 0.1 The SPA is a *client*, not a workflow engine

The SPA:

* renders state
* triggers actions
* reacts to server truth

The SPA **never**:

* decides business outcomes
* infers workflow state
* duplicates controller logic
* “fixes” server inconsistencies

> **All business logic lives on the server.**
> The SPA follows it — it does not override it.

---

### 0.2 Determinism beats cleverness

Prefer:

* explicit payloads
* named modes
* deterministic IDs
* boring code

Over:

* inference
* guessing from partial state
* clever watchers
* “it should work”

### 0.3 Build & Asset Delivery Contract (LOCKED)

* Canonical production build entrypoint is repo-root `yarn build`; it must compile Desk Rollup + `ui-spa` Vite in one run (and therefore through `bench build`).
* Manual deployment runbooks must not rely on a second standalone `yarn --cwd ifitwala_ed/ui-spa build` step.
* Production bundles must stay minified and hash-named where supported, with source maps disabled by default and enabled only for incident debugging.

---

## 1. File & Folder Structure (Locked)

### 1.1 Canonical folders

```
ui-spa/src/
├─ pages/              # route-level views only
├─ components/         # reusable UI components
├─ overlays/           # overlay panels rendered via OverlayHost
├─ composables/        # shared reactive logic (useX)
├─ api/                # API wrappers (thin, legacy-compatible)
├─ types/              # TypeScript contracts only (zero runtime)
├─ lib/                # SPA runtime infra + UI services + signals
├─ utils/              # pure stateless helpers only
├─ styles/             # tokens / app / layout / components
```

Rules:

* ❌ No business logic in pages
* ❌ No API calls inside components
* ❌ No cross-importing between `pages/` and `overlays/`
* ✅ Pages orchestrate; components render

Runtime orchestration (services, invalidation, signals) **must** live in `lib/`.

ui-spa/src/components/** must never contain workflow overlays. Any file named *Overlay.vue must live under ui-spa/src/overlays/**.

---

### 1.2 Folder semantics (non-negotiable)

| Folder   | Must contain                      | Must NOT contain                             |
| -------- | --------------------------------- | -------------------------------------------- |
| `types/` | contracts, DTOs, unions           | runtime code, state, constants, side effects |
| `utils/` | pure stateless helpers            | registries, event buses, subscriptions       |
| `lib/`   | runtime infra (services, signals) | business logic, overlay close logic          |

UX feedback hosts (toast/notifications) belong in the **shell/page layer** (Refresh Owners), never in overlays and never in services.

---

### 1.3  **Request Ownership Rule (Proposal F — LOCKED)**

* **Rule:** `frappeRequest` must not be imported outside `ui-spa/src/resources/frappe.ts`.
* **Allowed:** import `apiRequest` / `apiMethod` from `resources/frappe.ts` (or your eventual thin client module).
* **Enforcement:** refactor any direct usage as a defect.
* **Rationale:** one request pipe = deterministic debugging + upgrade safety.

---

## 2. Contracts & Types Governance (Phase-0 — Integrated)

### 2.1 Purpose

We already saw predictable drift:

* runtime constants sneaking into `types/`
* payload types duplicated inside Vue files
* parallel `fetch()` usage next to `createResource`

At scale, this causes silent contract mismatches and data leakage.

**Goal:** make contracts enforceable, not aspirational.

---

### 2.2 `types/` = contracts only

Hard rules:

* ✅ `export type`, `export interface`, literal unions
* ❌ `export const`, `export function`, side effects, Vue imports

If runtime code exists in `types/` → **FAIL review**.

---

### 2.3 Contract files (required structure)

```
ui-spa/src/types/contracts/
  focus/
    list_focus_items.ts
    resolve_focus_item.ts
  student_log/
    submit_follow_up.ts
```

Each file exports **only**:

```ts
export type Request = { ... }
export type Response = { ... }
```

Rules:

* must match server whitelisted signature **exactly**
* no defaults, no inference

---

### 2.4 Role-scoped DTOs (security by design)

If the same DocType is exposed differently:

* staff
* student
* guardian

Define **separate DTOs**, even if identical today.

This prevents accidental UI leakage later.

---

#### **2.5 Transport Boundary Rule (LOCKED)**

* **Rule:** Only `ui-spa/src/resources/frappe.ts` may handle transport shapes/envelopes.
* **Rule:** All SPA consumers receive **domain payloads only** (`T`), never `{message:T}`.
* **Forbidden:** Unwrapping `message`, `data.message`, Axios-shapes, or any envelope handling in services/pages/components.
* **Rationale:** prevents drift across frappe-ui versions and eliminates double-unwrapping failures.

---

### 2.6 UI View-Model Types (Page-Owned)
Types that exist only to assemble UI state (view-models / projections) **must be page-owned and co-located** with the page or feature folder (e.g., pages/.../types.ts). These types must not mirror backend payloads, must not be imported by services, and are allowed to evolve with UX without triggering contract churn. If a UI type is reused across multiple pages and remains stable, it may be promoted to src/types/ui/; otherwise it stays local. Backend DTOs always live in src/types/contracts/ and are the only types services may use for request/response shapes.

---

## 3. API Usage Rules (Hard-Won)

### 3.1 One transport only

* ❌ `fetch()`
* ❌ `frappe.call`
* ✅ `createResource`

---

### 3.2 Payload shape (locked)

```ts
resource.submit(payload)
```

Rules:

* ❌ never `{ payload: {...} }`
* ❌ never `cmd`
* ❌ never read or validate `frappe.form_dict`

All server methods **must declare explicit arguments**.


### 3.2.1 When to add a new signal vs local refresh (NEW / LOCKED)
**Add a new `SIGNAL_*_INVALIDATE`** when a mutation can affect data shown in **other mounted surfaces** (e.g. counts, previews, list cards, Focus, dashboards, shell badges).

**Local refresh only** is allowed only when the affected data is **strictly page-local** and not rendered
anywhere else in the SPA.

**Default:** if uncertain, add a signal and let Refresh Owners decide refetch policy.

---

### 3.3 Filters + POST rule (critical)

If filters exist → **POST + submit(payload)**.

No GET param encoding. No mixing styles.

This prevents silent filter loss.

---

### 3.4 UI Signals usage rule (A+ enforced)

Signals are runtime infra and belong in `ui-spa/src/lib/`.

**A+ rule (non-negotiable):**

- `uiSignals.on()` is **low-level registration**
  - requires explicit `uiSignals.off(name, handler)`
  - handler reference must be stable
  - **do not use** if you expect an unsubscribe function

- `uiSignals.subscribe()` is the **ergonomic subscription API**
  - returns a disposer (unsubscribe function)
  - safe for inline usage
  - **preferred in Vue `setup()` blocks**

Violations are **defects**, not style issues.

---

### 3.4.1 Portal Calendar Resolution Contract (Locked)

For SPA calendar surfaces (staff, student, guardian):

* Clients must treat calendar scope as **server-owned**.
* Clients must not infer Academic Year or School Calendar from local school context.
* Clients must call calendar APIs and render returned events/preferences as-is.

Server contract for staff portal:

1. Attempt `Staff Calendar` holidays using nearest lineage school match.
2. If no Staff Calendar holidays are available, fallback to effective `School Calendar Holidays` for the same window (`self -> nearest ancestor`).
3. If the logged-in user is the built-in `Administrator` account and no active `Employee` record resolves, the calendar feed must still return a normal payload instead of raising a permission error.
4. This fallback is only for the built-in `Administrator` user. Other staff portal users without an active `Employee` record must still receive the explicit permission error.
5. In the `Administrator` fallback path, employee-scoped sources stay empty, while user-scoped participant sources may still return events.

Server + client contract for student portal:

1. Class calendar events must carry schedule-resolvable ids:
   `sg::<student_group>::<rotation_day>::<block_number>::<session_date>`.
2. School Calendar Holidays must be returned as all-day events with source `holiday`.
3. Student calendar source controls must expose `Holidays` as a distinct chip (not merged into `School` events).
4. Class-detail drill-down authorization must allow Student/Guardian users when the class belongs to
   their own active Student Group enrollment (Student) or a linked child enrollment (Guardian).

Client anti-patterns (forbidden):

* Building parent fallback in Vue.
* Assuming `Employee.school` has direct `Academic Year` / `School Calendar`.
* Hardcoding school calendar IDs in SPA state.

This rule prevents silent portal drift when AY/calendar is maintained at a parent school node.

---

### 3.4.2 Portal Navigation Shell Contract (Locked)

For Student/Guardian SPA shell navigation:

* `PortalLayout.vue` remains the single shell authority for Student + Guardian routes.
* `PortalSidebar.vue` remains the single navigation component for this shell.
* `StudentContextSidebar.vue` is the secondary student-only contextual rail for route-scoped shortcuts and must remain read-only navigation (no workflow mutations).
* Desktop uses a persistent rail pattern (collapsed/expanded), never full hide.
* Mobile uses an overlay drawer pattern (hamburger + backdrop), never desktop rail behavior.
* Canonical portal URLs are namespaced under `/hub/*` while internal SPA route paths stay base-less (`/student/*`, `/guardian/*`, `/staff/*`), and router history base is `/hub`.
* All portal links must stay named-route based (`{ name: '...' }`) with no hardcoded `/hub/...` paths.

State ownership:

1. `PortalLayout` owns `isMobileSidebarOpen`.
2. `PortalLayout` owns `isDesktopRailExpanded`.
3. `PortalLayout` owns contextual-sidebar visibility (`showStudentContextSidebar`) based on route name and active portal section.
4. Desktop rail preference persists per section (`student` / `guardian`) via explicit local storage keys.
5. Route changes must close only the mobile drawer.

Accessibility and UX invariants:

* Rail toggle must expose `aria-expanded`.
* Collapsed rail must preserve accessible labels (screen reader-visible text + tooltip on hover/focus).
* Active navigation must include a non-color cue in addition to color.
* Motion for rail transitions must respect `prefers-reduced-motion`.

Forbidden:

* Parallel student/guardian shell implementations for sidebar behavior.
* New icon libraries for portal navigation when `FeatherIcon` already satisfies the need.
* Route-shape drift (hardcoded paths replacing named routes).

---

### 3.4.3 Routed Page Root Shell Contract (Locked)

For routed SPA pages, the page root is part of the layout contract, not page-local decoration.

Rules:

* Staff pages must mount inside the canonical staff page shell (`staff-shell`) unless the canonical SPA docs are updated first.
* Student and Guardian routed pages must mount inside their canonical portal shell/container contract and must not replace that with ad-hoc page-local wrappers.
* A routed page must not replace a shared shell/container with local classes such as `min-h-screen`, custom padding, or ad-hoc max-width rules unless that shell change is intentional, documented, and applied consistently across the owning surface.
* Inner grids/panels must not rely on accidental inherited width. The root container must explicitly preserve the intended shell width contract.

Regression to prevent:

* Removing `staff-shell` from a staff page root can collapse a previously wide two-column page into a stacked layout even when the inner grid classes are unchanged.

Required review check when editing routed pages:

1. Verify the page root still uses the canonical shell/container class for that surface.
2. Compare the changed page against sibling routes in the same surface (`/staff/*`, `/student/*`, `/guardian/*`) instead of validating the page in isolation.
3. If the shell contract itself needs to change, update this note and the relevant layout/style note in the same change before modifying page roots.

Forbidden:

* Treating shared page-root shell classes as optional styling sugar.
* Replacing canonical shell classes during a feature rewrite without documenting the new shell contract.

---

### 3.5 Architectural reason (why this matters)

Under the A+ model:

- **Pages own refresh**
- **Services emit signals**
- **Signals are infra**

If signal subscriptions leak:

- refresh storms happen
- throttling becomes unreliable
- overlays/pages appear to “randomly” re-trigger refreshes
- debugging becomes non-deterministic

This sits below business logic but above rendering — exactly where silent damage accumulates.

---

### 3.6 UX feedback after success (A+ — LOCKED)

**UX feedback after success is owned by Refresh Owners (page/shell) and is triggered by signal semantics.**

Rules:

* **Overlays** must not toast, must not emit `uiSignals`, and must not refetch pages. They close immediately on success and display inline errors on failure.
* **Services** must not toast. They call endpoints and emit `*_invalidate` signals **only after confirmed semantic success**.
* **Refresh Owners** (pages or shell-level listeners) subscribe to `uiSignals`, decide when to refetch, and may optionally show a “Saved” toast **after refetch success**.

This prevents:

* toast/runtime coupling (“toast unavailable”)
* duplicate success toasts across entry points
* refresh storms from mixed ownership
* workflow correctness depending on UX availability

---

## 4. Overlay Architecture & A+ Lifecycle Contract

### 4.1 Core decision (A+)

> **Overlay owns closing. UI Services own orchestration.**

Overlay closing is **local, immediate, deterministic**.

---

### 4.2 Ownership split
| Responsibility                   | Owner                                |
| -------------------------------- | ------------------------------------ |
| API calls                        | UI Services                          |
| Business rules / idempotency     | Server                               |
| Invalidation signals (emit)      | UI Services                          |
| Refresh policy / refetch timing  | Refresh Owners (page/shell)          |
| UX feedback after success        | Refresh Owners (page/shell), via refetch semantics |
| Overlay close                    | Overlay                              |
| Overlay lifecycle                | OverlayHost                          |

---

### 4.3 Mandatory overlay success sequence

On success:

1. `emit('close')` immediately
2. optional `emit('done')`
3. OverlayHost handles teardown

Never wait for refresh, toast, reload.
Overlay must perform **zero UX signaling**: no toast, no signal emission, no refetch calls.

---

### 4.4 Naming rules (collision-safe)

Forbidden:

* `get_context`
* `context`
* `resolve_context`

Approved patterns:

* `resolveFocusItemPayload`
* `listFocusItems`
* `submitStudentLogFollowUp`

If a name collides with framework semantics → rename **now**.

---

## 5. State, Reactivity & Watchers

* ❌ infer modes from data
* ❌ immediate watchers touching undeclared refs
* ❌ side-effect watchers
* ✅ explicit modes, computed values

TDZ errors → fix declaration order first.

---

## 6. Workflow Boundaries

* SPA never closes ToDo
* SPA never decides workflow outcome
* Focus reflects server truth only

---

## 7. Performance & UX Invariants

* calm-first UI
* pagination always (`limit + offset`)
* no unbounded lists

---

## 8. Agent Checklist (Mandatory)

Before coding:

1. identify workflow owner
2. confirm server method
3. confirm contract file
4. confirm overlay ownership
5. confirm no ToDo logic client-side

If unclear → stop.

---

## 9. Final Invariant

> **If a Vue component makes business decisions, closes ToDos, infers workflow state, or invents styling — it is wrong.**

---




### 🔒 **Runtime Normalization Rule (Hard / Non-Negotiable)**

#### ❌ Forbidden pattern

Under no circumstances may client code represent server responses as unions such as:

```ts
T | { message: T }
T | { data: T }
T | { data: { message: T } }
```

This includes:

* `type` definitions
* generics
* inline unions
* “temporary” safety types

**Any occurrence is a defect.**

---


#### ✅ Required pattern (LOCKED)

Transport envelope handling is owned by **one place only**:

* `ui-spa/src/resources/frappe.ts`

After the transport adapter unwraps the framework envelope, **services and all downstream code** must see **contract-pure domain payloads only**:

No overlay, page, component, or service may:
unwrap { message }
check { data }
branch on transport shape
compensate for framework response wrappers

---

#### 🧠 Rationale (binding)

Types describe **contracts**, not **transport noise**.

Transport wrappers (`message`, `data`, Axios envelopes, Frappe internals) are:

* framework concerns
* runtime concerns
* **never part of the contract**

Allowing union types to represent transport ambiguity:

* defeats contract enforcement
* hides server/client drift
* causes silent routing failures
* re-introduces “it works in network tab but not in UI” bugs

---

#### 🧪 Enforcement checklist (mandatory)

Before merge, reviewers must verify:

* [ ] No `Response | { message: Response }` types exist
* [ ] All unwrapping happens in **services only**
* [ ] Overlays/components consume **contract-pure DTOs**
* [ ] Missing fields cause visible errors, not silent fallbacks

Violation → **reject PR**.

---

#### 📌 Summary invariant

> **Contracts are pure.
> Transport is impure.
> `resources/frappe.ts` absorbs transport once.
> Services return domain payloads only.
> UI never sees transport.**

---



## A+ Governance Appendix

### Purpose

A+ exists to keep the SPA scalable by enforcing **clear ownership**:

* **Pages own refresh policy**
* **UI Services own data access + workflows**
* **Overlays own the UX shell + close discipline**
* **uiSignals is the single in-SPA invalidation bus**

If a rule here is violated, treat it as a **defect**, not style.

---

## 1) Folder and ownership rules

### 1.1 Pages

**Pages are refresh owners.**

* Pages decide *when* to refresh (stale rules, throttling, polling, visibility checks).
* Pages must not contain business workflow logic (submit/reassign/approve).
* Pages may call services and update local view state.

**Pages may subscribe to uiSignals.**

* They must unsubscribe on unmount.
* They must coalesce refresh triggers (avoid stampedes).

### 1.2 UI Services

**Services are the only place that should:**

* call endpoints
* return contract-pure domain payloads (transport handled in `resources/frappe.ts`)
* perform workflow actions (submit follow up, reassign, close, etc.)
* emit invalidation signals after success

Services must not:

* manipulate overlays directly
* call page refresh functions
* depend on component instances

### 1.3 Overlays

**Overlays are workflow shells, not owners.**

* Overlays call service actions.
* On success: overlays **close immediately**.
* After success: overlays must do **no invalidation**. Services emit signals after confirmed semantic success; pages/shell subscribe and refetch what they own.

Overlays must not:

* refresh pages directly
* dispatch custom SPA invalidation via window events
* “wait for refresh to finish” before closing

---

## 2) Invalidation rules

### 2.1 Single in-SPA invalidation bus

Inside the Vue SPA, **uiSignals is the only allowed invalidation mechanism**.

**Forbidden in SPA for invalidation:**

* `window.dispatchEvent(new CustomEvent('ifitwala:*'))`
* `document.dispatchEvent(...)`
* ad-hoc event buses per module

**Allowed:**

* `uiSignals.emit(SIGNAL_*)` from services/workflows
* `uiSignals.subscribe(SIGNAL_*, handler)` from pages

### 2.2 Window events: allowed only as explicit bridges

Window events are allowed **only** for cross-runtime bridging (SPA ↔ Desk or non-SPA surfaces).

If used:

* must live in a single file: `ui-spa/src/lib/bridges/windowBridge.ts`
* must be documented as a bridge (not a primary invalidation path)
* app code must not call window events directly

---

## 3) uiSignals usage rules

### 3.1 Subscribe API rule (locked)

**Never treat `uiSignals.on()` as returning an unsubscribe function.**
Use:

* `uiSignals.subscribe(name, handler)` → returns disposer

`uiSignals.on/off` are allowed only if:

* handler is a stable named function
* unsubscribe is explicit and correct

### 3.2 Signal naming rule

* All shared signals must be exported constants in `uiSignals.ts`
* No raw string literals in components/services for shared invalidation

### 3.3 Payload rule

* Payloads must be optional and minimal.
* Prefer `{ id }` over dumping full objects.
* Never require payload to avoid refresh (pages should refresh safely without it).

---

## 4) Refresh policy rule

Pages must coalesce refresh triggers:

* dedupe in-flight requests
* throttle bursts from multiple invalidation sources
* avoid “refresh storms” after workflows

Recommended minimum:

* `inFlight` gate
* one queued refresh while in-flight
* light throttle window (300–1000ms)

---

## 5) Anti-patterns (treat as defects)

1. Overlay dispatches `window` event to refresh a page
2. Page contains submit/reassign/approve logic
3. Multiple invalidation systems inside SPA (uiSignals + window events)
4. Services importing Vue components or overlay stack
5. uiSignals used with inline handlers via `on()` without stable handler references
6. Silent failures: “return null” with no structured debug when core context exists

---

## 6) Definition of done for A+ compliance

* One invalidation path (uiSignals) for SPA refresh
* Workflows emit invalidation from service layer
* Pages subscribe and own refresh policy
* Overlays close independently on success
* No DOM event invalidation remains (except explicit bridge file)

---




Here are **10 concrete refactor rules** to *any Vue page* to make it **A+ compliant** in your codebase, with **file paths, naming, what to change, and why**.

## 1) Page owns refresh, services own invalidation

**Where:** any page under `ui-spa/src/pages/**`
**Do:**

* Page fetches data on mount / visibility / polling (if needed)
* Page subscribes to `uiSignals` and decides when to refetch
* Services never “reach into” pages

**Why:** prevents “workflow close” coupling, keeps refresh policy centralized.

---

## 2) Never call APIs directly in pages or components

**Where:** `ui-spa/src/pages/**`, `ui-spa/src/components/**`, `ui-spa/src/overlays/**`
**Do:**

* No `createResource()` in pages/components/overlays
* No `fetch()` / `axios` / `frappe.call` in pages/components/overlays
* All remote calls go through `ui-spa/src/lib/services/**`

**Why:** stops transport drift + duplicated wrappers.

---

## 3) Services return domain payloads only (no envelope handling)

**Where:** `ui-spa/src/lib/services/**`
**Do:**

* Services must return **contract Response types** directly
* No `normalizeMessage/unwrapMessage/transform` in services
* Transport envelope `{ message: T }` is owned by `ui-spa/src/resources/frappe.ts`

**Why:** A+ rule: “backend contract is authoritative; no transport normalization anywhere else.”

---

## 4) Strict contract imports: one endpoint ↔ one Request/Response import

**Where:** any service file
**Pattern:**

```ts
import type { Request as XRequest, Response as XResponse } from '@/types/contracts/...'
```

**Do:**

* Every method in a service uses explicit contract types
* No inline ad-hoc response typing

**Why:** contract discipline; prevents “shape creep”.

---

## 5) POST invariant: always `.submit(payload)` with flat args

**Where:** services using `createResource`
**Do:**

* Always `method: 'POST'`
* Always `resource.submit(payload)`
* No GET-style params, no `{ payload: ... }` wrapper

**Why:** your locked frappe-ui + server kwarg invariant.

---

## 6) Signal subscription must use `uiSignals.subscribe()` only

**Where:** pages / components using signals
**Do:**

* No `uiSignals.on/off` (and you already removed them from export)
* Always:

```ts
const dispose = uiSignals.subscribe(SIGNAL_..., handler)
onBeforeUnmount(() => dispose())
```

**Why:** prevents leaks + refresh storms.

---

## 7) Overlays: close is owned by overlay infra, not by refresh

**Where:** `ui-spa/src/components/**Overlay.vue` or `ui-spa/src/overlays/**`
**Do:**

* Overlay calls service mutation
* On success: overlay closes immediately (via overlay stack / host lifecycle)
* Overlay does NOT emit signals
* Overlay does NOT trigger page refetch directly

**Why:** decouples workflow completion from list refresh; fixes “overlay didn’t close” class of bugs.

---

## 8) Pages must coalesce refresh triggers (anti-stampede)

**Where:** pages that poll + listen to signals (e.g. `StaffHome.vue`)
**Do:**

* Keep a `refreshInFlight` promise + `refreshQueued` boolean
* Add a small throttle window for bursts (`~500–1000ms`)
* Keep visibility-stale logic

**Why:** signal bursts + interval + visibility can collide; page must protect the backend.

---

## 9) No fake safety types: ban `any`, ban permissive unions

**Where:** types + services + pages
**Do:**

* No `any` in payloads (`Record<string, unknown>` or index `unknown` only)
* No unions like `T | { message: T }`
* No “defensive transport branching” outside transport adapter

**Why:** fake safety creates ambiguity; ambiguity causes duplicated unwrappers and component drift.

---

## 10) File/folder naming conventions are contracts

**Where:** everywhere
**Do:**

* Services live in: `ui-spa/src/lib/services/<domain>/<domain>Service.ts`

  * Example: `ui-spa/src/lib/services/focus/focusService.ts`
* Contracts live in: `ui-spa/src/types/contracts/<domain>/<endpoint>.ts`
* Page names match route intent: `ui-spa/src/pages/<surface>/<PageName>.vue`
* Components: `ui-spa/src/components/<domain>/<ComponentName>.vue`

**Why:** keeps the architecture navigable; “where does this logic live?” becomes deterministic.

---

### 🔒 Transport & Invalidation Rule (LOCKED)

* Transport envelope unwrapping happens only in `ui-spa/src/resources/frappe.ts`.
* Services contain **zero** transport-shape branching and return **domain contract payloads only**.
* Services may emit `*_invalidate` signals **only after confirmed semantic mutation success** (backend-owned success field like `ok === true` or explicit status).
* Components/overlays/pages must never decide mutation success and must never emit signals.


---

## Overlay Boundary Rule (LOCKED)

### A. Workflow Overlays (MANDATORY)

A UI surface **must** be a workflow overlay rendered via `OverlayHost` **iff** it satisfies **any** of the following:

1. Triggers a **server mutation**
   (submit, create, update, approve, reassign, follow-up, decide)
2. Can affect **other mounted surfaces**
   (Focus, counts, dashboards, lists, badges)
3. Participates in **A+ workflow lifecycle**
   (service call → success → invalidation → refresh elsewhere)

**Requirements:**

* Lives under `ui-spa/src/overlays/**`
* Uses UI Services
* Closes immediately on success
* Emits **no** toasts, **no** signals, **no** refetches

**Examples (in this codebase):**

* `StudentLogCreateOverlay`
* `StudentLogFollowUpOverlay`
* `EventQuickCreateOverlay`
* `FocusRouterOverlay`
* `QuickCFUOverlay`
* `TaskReviewOverlay`

---

### B. Non-Workflow Dialogs (ALLOWED, constrained)

A UI surface **may** remain a standalone dialog **only if**:

1. It is **read-only or local-only**
2. Performs **no server mutation**
3. Affects **no other mounted surface**
4. Has **no workflow semantics**

**Rules:**

* Must not call services that emit invalidation
* Must not close ToDos or imply completion
* Must use controlled z-index
* Naming must reflect intent (`*Dialog`, not `*Overlay`)

**Examples (currently):**

* `ContentDialog.vue`
* `GenericListDialog.vue`

If a dialog later gains workflow behavior → **it must be promoted to an Overlay**.

---

### C. Calendar Event Views (CLARIFIED)

Calendar event views are classified as:

* **Read-only event inspection** → **Non-workflow dialog**
* **Event mutation (edit, cancel, reschedule)** → **Workflow overlay**
* **Event creation (Meeting / School Event)** → **Workflow overlay**

**Current read-only dialogs (inspection-only):**

* `MeetingEventModal`
* `ClassEventModal`
* `SchoolEventModal`

**Current workflow overlay (mutation):**

* `EventQuickCreateOverlay`

➡️ The read-only modals above remain **non-workflow dialogs**
➡️ `EventQuickCreateOverlay` is a **workflow overlay** for event creation

They may remain dialogs **for now**, but:

* API calls inside them are still **violations**
* If edit actions are added later → they must move to overlays

---



---
components/ must never contain workflow overlays; any *Overlay.vue must live in overlays/.

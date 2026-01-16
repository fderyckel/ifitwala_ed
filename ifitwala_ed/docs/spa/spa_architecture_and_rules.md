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

---

### 1.2 Folder semantics (non-negotiable)

| Folder   | Must contain                      | Must NOT contain                             |
| -------- | --------------------------------- | -------------------------------------------- |
| `types/` | contracts, DTOs, unions           | runtime code, state, constants, side effects |
| `utils/` | pure stateless helpers            | registries, event buses, subscriptions       |
| `lib/`   | runtime infra (services, signals) | business logic, overlay close logic          |

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

## 4. Overlay Architecture & A+ Lifecycle Contract

### 4.1 Core decision (A+)

> **Overlay owns closing. UI Services own orchestration.**

Overlay closing is **local, immediate, deterministic**.

---

### 4.2 Ownership split

| Responsibility               | Owner       |
| ---------------------------- | ----------- |
| API calls                    | UI Services |
| Business rules / idempotency | Server      |
| Refresh & invalidation       | UI Services |
| Overlay close                | Overlay     |
| Overlay lifecycle            | OverlayHost |

---

### 4.3 Mandatory overlay success sequence

On success:

1. `emit('close')` immediately
2. optional `emit('done')`
3. OverlayHost handles teardown

Never wait for refresh, toast, reload.

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

#### ✅ Required pattern

All server responses **must be normalized exactly once**, inside **UI Services** (`ui-spa/src/lib/services/**`), before being exposed to the rest of the application.

After normalization:

```ts
// downstream code must see ONLY this
Response
```

No overlay, page, or component may:

* unwrap `{ message }`
* check `{ data }`
* branch on transport shape
* compensate for framework response wrappers

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
> Services absorb impurity exactly once.
> UI never sees it.**

---


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

---

# Ifitwala_Ed — Vue SPA Development Rules (Authoritative)

> **Scope**
>
> These rules apply to **all Vue 3 SPA code** in `ui-spa/`:
>
> * pages
> * components
> * overlays
> * composables
> * API usage
> * styling
>
> They are not suggestions.
> They exist to prevent architectural drift, subtle bugs, performance regressions, and UX incoherence.

---

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
├─ api/                # API wrappers (thin)
├─ types/              # TypeScript contracts only (zero runtime, zero state)
├─ lib/                # SPA infrastructure + UI services + overlay lifecycle glue (A+ model)
├─ utils/              # pure stateless helpers only (deterministic, easy to test)
├─ styles/             # tokens / app / layout / components
```

Rules:

* ❌ No business logic in pages
* ❌ No API calls inside components directly
* ❌ No cross-importing between `pages/` and `overlays/`
* ✅ Pages orchestrate; components render

**Locked placement rule (A+ aligned):**
Runtime orchestration modules (UI Services, invalidation bus, cross-surface coordination) go in `ui-spa/src/lib/`.

---

### 1.2 Types are sacred

`types/` contains:

* interfaces
* enums
* discriminated unions
* API contracts

Rules:

* ❌ No Vue imports
* ❌ No reactive state
* ❌ No functions with side effects
* ✅ Types must match **server payloads exactly**

If server payload changes → types must change first.

---

### 1.3 Runtime boundary (A+ aligned)

The folder split is not aesthetic. It enforces the A+ model:

* `types/` defines contracts (safe anywhere, no runtime impact)
* `utils/` transforms values (pure helpers, no lifecycle)
* `lib/` orchestrates runtime behavior (services + signals), but **never** owns overlay closing

If a module maintains in-memory state, subscriptions, or cross-surface invalidation, it belongs in `lib/` — not `utils/` or `types/`.

---

### 1.4 Folder semantics (do not drift)

| Folder   | Must contain                                | Must NOT contain                                            |
| -------- | ------------------------------------------- | ----------------------------------------------------------- |
| `types/` | type contracts only                         | runtime behavior, state, side effects                       |
| `utils/` | pure stateless helpers                      | registries, event buses, subscriptions, lifecycles          |
| `lib/`   | runtime infrastructure (services + signals) | business logic, overlay-stack mutations, workflow inference |

---

## 2. Styling Rules (Non-Negotiable)

### 2.1 Single Tailwind entrypoint

Tailwind is imported **exactly once**:

```css
/* ui-spa/src/style.css */
@import "tailwindcss";
@import "./styles/tokens.css";
@import "./styles/app.css";
@import "./styles/layout.css";
@import "./styles/components.css";
```

Rules:

* ❌ No `@import "tailwindcss"` elsewhere
* ❌ No `@reference "tailwindcss"`
* ❌ No per-component Tailwind imports

---

### 2.2 Layer discipline

| File             | Purpose                       |
| ---------------- | ----------------------------- |
| `tokens.css`     | Design values only            |
| `app.css`        | Base elements, tiny utilities |
| `layout.css`     | Page shells, structure        |
| `components.css` | Reusable UI patterns          |

If it doesn’t clearly belong — **it does not go in CSS**.

---

### 2.3 Overlay styling is single-source

All dialogs and overlays must use:

* `OverlayHost.vue`
* HeadlessUI `Dialog` + `Transition`
* `.if-overlay*` CSS classes

Rules:

* ❌ No ad-hoc modals
* ❌ No inline dialog styling
* ❌ No page-local dialog CSS
* ✅ Extend via modifier classes only

---

### 2.4 Typography is semantic

Use typography helpers:

* `.type-h1`
* `.type-body`
* `.type-meta`

Rules:

* ❌ No `text-sm`, `text-lg`, etc. in templates
* ❌ No inline font decisions
* ✅ Rhythm is global, not per component

---

### 2.5 Tailwind v4 Silent Failure Class

Tailwind CSS v4 failures are often **non-fatal** but highly destructive.

**Common silent failures:**

* Importing Tailwind more than once
* Importing Tailwind inside components
* Layer duplication across bundles

**Effects:**

* CSS size inflation
* Order-dependent utility behavior
* Styling bugs that are impossible to reason about

**Rule:**

> If Tailwind is imported anywhere except the single entrypoint, it is a **defect**, even if “it works”.

---

## 3. Overlay Architecture (Critical)

### 3.1 One overlay system

All overlays:

* are opened via `useOverlayStack`
* are rendered by `OverlayHost`
* receive props + `open` + `zIndex`

Rules:

* ❌ No local modal state
* ❌ No `Dialog` mounted directly in pages
* ❌ No duplicate backdrops

---

### 3.1.1 Why frappe-ui Dialogs Are Forbidden

`frappe-ui` dialogs:

* manage their own focus
* manage their own z-index
* are unaware of `OverlayHost`
* conflict with HeadlessUI focus traps

They may appear to work in isolation, but they break:

* keyboard navigation
* stacked overlays
* accessibility guarantees

> Using `frappe-ui` dialogs inside the SPA is **technical debt**.

---

### 3.2 Overlay responsibilities

An overlay:

* renders context
* collects user input
* calls **one** workflow action
* closes itself

An overlay **never**:

* queries ToDo
* infers assignment
* mutates unrelated state
* implements workflow rules

---

### 3.4 UI Services + Overlay Lifecycle Contract (A+ model)

Workflow overlays must follow the locked A+ ownership split:

* **Overlay owns closing** (local, immediate, deterministic)
* **UI Services own orchestration** (API calls, refresh policy, messaging, invalidation)
* `OverlayHost` is the lifecycle authority (mount, inerting, after-leave cleanup)

Key invariant:

> A successful workflow must never depend on services, toasts, events, refresh, or reload completing in order for the overlay to close.

Implementation location implications:

* UI Services live in `ui-spa/src/lib/`
* The invalidation bus (`uiSignals`) lives in `ui-spa/src/lib/`
* Overlays never call services that mutate overlay stack
* Services never close overlays

---

### 3.3 HeadlessUI Failure Modes (Non-Obvious but Critical)

HeadlessUI `Dialog` components can fail **silently** under the following conditions:

* No focusable element exists inside the `DialogPanel`
* `open` becomes `true` before required props are available
* Overlay is rendered but immediately inerted by `OverlayHost` layering
* Dialog is mounted outside `OverlayHost`

**Symptoms:**

* Empty overlay
* No Vue runtime error
* Possibly a console warning about focus trapping (often missed)

**Debug protocol (in order):**

1. Verify the overlay is rendered via `OverlayHost`
2. Verify **at least one focusable element** exists inside the dialog
3. Verify `open` is controlled only by overlay stack state
4. Verify required props are resolved **before** `open = true`

---

## 4. API Usage Rules (Hard-won lessons)

### 4.1 createResource is mandatory

All SPA → server calls use `createResource`.

Rules:

* ❌ No `fetch()`
* ❌ No `frappe.call`
* ❌ No querystring payload hacks

---

### 4.2 Payload shape (locked)

Server methods must accept:

```ts
resource.submit(payload)
```

Rules:

* ❌ Never send `{ payload: {...} }`
* ❌ Never send `cmd`
* ❌ Never mix kwargs + payload conventions

> **Never validate or read `frappe.form_dict`.**
> All `@frappe.whitelist()` methods **must declare explicit function arguments**.
> Validation applies **only** to those arguments.

---

### 4.3 No chatty APIs

Rules:

* ❌ No N+1 calls from UI
* ❌ No “fetch details after click” chains
* ✅ One call per user action

---

### 4.4 Server Contract Debug Checklist (Mandatory Before Client Changes)

1. Inspect **Network → Response Preview**
2. Check explicitly for:

   * `"Unexpected keys"`
   * `"cmd"`
3. Compare payload keys **exactly** against server method signature
4. Fix the **server contract first**, not the UI

---

### 4.5 Filters + POST rule (Critical — prevent silent filter loss)

**If a request includes filters, it must be POST + `resource.submit(payload)`**.

This includes list views, dashboards, and archives where filters are reactive.

Forbidden patterns:

* encoding filters in query params for correctness
* mixing GET params with POST endpoints

Required pattern:

* keep all filters in one reactive object
* POST the full filter object via `resource.submit(filtersPayload)`

Reason:

* GET/POST mismatches and param encoding have repeatedly caused filters to drop silently (e.g., `student_group`), creating “works sometimes” failures.

---

## 5. State Management & Reactivity

### 5.1 No hidden inference

Rules:

* ❌ No “derive mode from data”
* ❌ No “if this field exists then…”
* ✅ Explicit `mode`, `action_type`, or `context`

---

### 5.2 Watchers are dangerous

Rules:

* ❌ No `watch()` with side effects unless unavoidable
* ❌ No immediate watchers touching undeclared refs (TDZ bug)
* ❌ No console.log inside watch arguments
* ✅ Prefer computed values

---

### 5.3 TDZ Debug Playbook (Vue `<script setup>`)

If you see:

```
Cannot access 'x' before initialization
```

Assume **Temporal Dead Zone**, not logic failure.

Fix declaration order first.

---

## 6. Workflow Boundaries (Student Log, Focus, etc.)

### 6.1 SPA never closes ToDo

ToDo lifecycle is handled by:

* server controllers
* workflow methods
* scheduler jobs

The SPA:

* triggers workflow endpoints
* refreshes its own view

---

### 6.2 Focus List rules

Focus List:

* is **not** a task manager
* reflects server truth only

Rules:

* ❌ No manual FocusItem creation in SPA
* ❌ No ToDo manipulation in SPA
* ✅ Focus items disappear by server action

---

## 7. Deterministic IDs & Contracts

### 7.1 Deterministic identity

Workflow items must have reproducible IDs.

Rules:

* ❌ No random UUIDs
* ❌ No client-generated workflow IDs

---

## 8. Permissions & Privacy

Rules:

* ❌ Never assume permission client-side
* ❌ Never hide data instead of enforcing access
* ✅ Server enforces permissions

---

## 9. Performance & UX

### 9.1 Calm-first UX

Avoid:

* aggressive colors
* flashing indicators
* panic language

---

### 9.2 Pagination always

Rules:

* ❌ No unbounded lists
* ✅ Always `limit + offset`

---

## 10. What Codex Agents Must Do

Before writing Vue code, an agent must:

1. Identify the **workflow owner**
2. Confirm the **server method**
3. Confirm the **payload contract**
4. Confirm the **overlay mode**
5. Confirm **no ToDo logic client-side**
6. Confirm styles reuse existing patterns

If unclear → **stop and ask**.

---

## 11. Final Invariant (Non-Negotiable)

> **If a Vue component makes business decisions, closes ToDos, infers workflow state, or styles itself ad-hoc — it is wrong.**

The SPA is calm, thin, deterministic, and obedient to server truth.

That discipline is what makes Ifitwala scalable, teachable, and safe to extend.

---

New rule (important — lock this)

In SPA files:

❌ _ prefix must NOT be used for:

lifecycle guards

workflow completion logic

idempotency helpers

overlay close semantics

✅ _ prefix is allowed only for:

throwaway formatting helpers

one-line transforms

code you’d be OK deleting tomorrow

This aligns with your broader contracts & governance direction.

If you want to mark intent, use naming, not punctuation:

requireFocusItemId

aPlusSuccessCloseThenDone

newClientRequestId

Those names are explicit contracts.

---

# Appendix A — Contract & Types Phase-0 (Subsumed source, kept verbatim)

> This appendix preserves the Phase-0 governance content. It is subordinate to the main rules above.

(Contents from `contract_and_type_phase0.md` should remain here verbatim; keep as reference-only.)

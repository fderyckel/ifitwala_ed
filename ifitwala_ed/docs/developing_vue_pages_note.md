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
├─ types/              # TypeScript contracts (no logic)
├─ lib/                # framework glue, i18n, helpers
├─ utils/              # pure functions only
├─ styles/             # tokens / app / layout / components
```

Rules:

* ❌ No business logic in pages
* ❌ No API calls inside components directly
* ❌ No cross-importing between `pages/` and `overlays/`
* ✅ Pages orchestrate; components render

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

**Therefore:**

> Using `frappe-ui` dialogs inside the SPA is not a shortcut — it is **technical debt**.

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

**Do not debug styling first.**
This is almost never a CSS issue.

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

Server methods should accept `payload=None, **kwargs` if needed.

The SPA communicates only with **explicitly-defined server contracts**.

> **Never validate or read `frappe.form_dict`.**
> All `@frappe.whitelist()` methods **must declare explicit function arguments**.
> Validation applies **only** to those arguments.
> Any endpoint that reads raw request dictionaries is a **bug**.

### Why this rule exists (do not debate)

* Frappe **always injects** framework keys (e.g. `cmd`) into `/api/method` calls
* `frappe-ui` **always POSTs JSON**
* Bench and Frappe upgrades **will not change this behavior**

Validating raw request payloads inevitably causes:

* `"Unexpected keys"` errors
* brittle APIs
* repeated regressions across features

### What this rule guarantees

* Deterministic validation
* Framework-aligned behavior
* Future-proof endpoints
* Zero coupling to transport internals

### Client implications (SPA)

* The SPA sends a **flat payload** using:

  ```ts
  resource.submit(payload)
  ```

* Payload keys must match the **server method signature exactly**

* The SPA must **never** work around server validation failures

If a request fails due to unexpected keys, the **server contract is wrong**.

> **Fix the server. Never patch the client.**




### 4.3 No chatty APIs

Rules:

* ❌ No N+1 calls from UI
* ❌ No “fetch details after click” chains
* ✅ One call per user action

If the UI needs data → the endpoint must return it **already enriched**.

---

### **4.4 Server Contract Debug Checklist (Mandatory Before Client Changes)**

When a POST request fails or behaves unexpectedly:

1. Inspect **Network → Response Preview**
2. Check explicitly for:

   * `"Unexpected keys"`
   * `"cmd"`
   * missing required fields
3. Compare payload keys **exactly** against the server method signature
4. Confirm whether the server expects:

   * `payload`
   * named keyword arguments
   * both (`payload=None, **kwargs`)
5. Fix the **server contract first**, not the UI, unless proven otherwise

Never “patch around” server validation from the SPA.

---

## 5. State Management & Reactivity

### 5.1 No hidden inference

Rules:

* ❌ No “derive mode from data”
* ❌ No “if this field exists then…”
* ✅ Explicit `mode`, `action_type`, or `context`

If the server knows the mode, the server sends it.

---

### 5.2 Watchers are dangerous

Rules:

* ❌ No `watch()` with side effects unless unavoidable
* ❌ No immediate watchers touching undeclared refs (TDZ bug)
* ❌ No console.log inside watch arguments
* ✅ Prefer computed values
* ✅ Prefer explicit lifecycle hooks

---

### **5.3 TDZ Debug Playbook (Vue `<script setup>`)**

If you encounter errors such as:

```
Cannot access 'x' before initialization
```

Assume **Temporal Dead Zone (TDZ)**, not logic failure.

**Checklist:**

1. Look for `watch(..., { immediate: true })`
2. Identify refs or computed values referenced inside the watcher
3. Ensure **all referenced symbols are declared above the watcher**
4. Prefer watching `props` directly
5. Move side effects to explicit lifecycle hooks if possible

**Rules:**

* Do **not** rename variables
* Do **not** refactor logic
* Fix declaration order first

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
* is **not** user-editable
* reflects server truth only

Rules:

* ❌ No manual FocusItem creation in SPA
* ❌ No ToDo manipulation in SPA
* ✅ Focus items disappear by server action, not UI hacks

---

## 7. Deterministic IDs & Contracts

### 7.1 Deterministic identity

Any item representing workflow state must have:

* a deterministic ID
* derived from reference + role + action

Rules:

* ❌ No random UUIDs for workflow items
* ❌ No client-generated identifiers
* ✅ IDs must be reproducible server-side

---

## 8. Permissions & Privacy

Rules:

* ❌ Never assume permission client-side
* ❌ Never hide data instead of enforcing access
* ✅ Server enforces permissions
* ✅ SPA renders only what it is given

If the user shouldn’t see it — it must not be returned.

---

## 9. Performance & UX

### 9.1 Calm-first UX

Avoid:

* aggressive colors
* flashing indicators
* “overdue” panic language

Prefer:

* neutral phrasing
* soft surfaces
* predictable motion

---

### 9.2 Pagination always

Rules:

* ❌ No unbounded lists
* ❌ No “load everything”
* ✅ Always `limit + offset`

---

## 10. What Codex Agents Must Do

Before writing any Vue code, an agent must:

1. Identify the **workflow owner** (Student Log, Inquiry, etc.)
2. Confirm the **server method** that owns state transitions
3. Confirm the **payload contract**
4. Confirm the **overlay mode**
5. Confirm **no ToDo logic is required client-side**
6. Confirm styles reuse existing components

If any point is unclear → **stop and ask**.

---

## 11. Final Invariant (Non-Negotiable)

> **If a Vue component makes business decisions, closes ToDos, infers workflow state, or styles itself ad-hoc — it is wrong.**

The SPA is calm, thin, deterministic, and obedient to server truth.

That discipline is what makes Ifitwala scalable, teachable, and safe to extend.

---


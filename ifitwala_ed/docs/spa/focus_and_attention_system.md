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
@import "./
```

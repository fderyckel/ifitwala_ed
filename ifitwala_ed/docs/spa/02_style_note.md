# Ifitwala UI Style Architecture & Philosophy

> **Audience**: Human developers, designers, reviewers, and coding agents (LLMs).
>
> **Scope**: Vue 3 + Tailwind CSS v4 + frappe-ui SPA (Staff / Admin surfaces).
> This document defines *how* styles are structured, *why* decisions were made, and *what invariants must never be broken*.
>
> **Authority**: Canonical styling authority. Must be consistent with **Vue SPA Architecture & Development Rules (AUTHORITATIVE)**.

---

## 1. Core Philosophy

### 1.1 Pedagogy-first, calm-first UI

Ifitwala is not a SaaS dashboard factory. The UI must:

* reduce cognitive load for educators,
* feel calm, grounded, and human,
* privilege clarity over density,
* avoid visual aggression (no harsh contrasts, no noisy gradients, no jittery motion).

Design choices intentionally favor:

* soft surfaces over pure white,
* restrained color usage,
* consistent spacing and rhythm,
* predictable component behavior.

This is *not* a Tailwind demo. Tailwind is an implementation detail.

---

## 2. Architectural Principles (Non‑Negotiable)

### 2.1 Single Tailwind entrypoint

Tailwind **must be imported exactly once**.

```css
/* ui-spa/src/style.css */
@import "tailwindcss";
@import "./styles/tokens.css";
@import "./styles/app.css";
@import "./styles/layout.css";
@import "./styles/components.css";
```

Rules:

* ❌ No `@import "tailwindcss"` in sub-files
* ❌ No `@reference "tailwindcss"` in sub-files
* ✅ All other CSS lives under `@layer` blocks

This avoids directive drift, ordering bugs, and upgrade fragility.

---

### 2.2 Hard separation of concerns

Styles are split into **four files**, each with a single responsibility:

| File             | Responsibility                                     |
| ---------------- | -------------------------------------------------- |
| `tokens.css`     | Design tokens only (colors, shadows, radii, fonts) |
| `app.css`        | Global element defaults & tiny utilities           |
| `layout.css`     | Page shells & structural layouts                   |
| `components.css` | Reusable UI components (atoms → molecules)         |

No exceptions.

---

## 3. Design Tokens (`tokens.css`)

### 3.1 Tokens are *values*, not components

Tokens define **meaningful primitives**, never UI shapes.

Allowed:

* CSS variables for color channels (`--ink-rgb`, `--surface-rgb`, …)
* shadow variables
* radius variables
* typography scales (if needed)

Forbidden:

* `.card`, `.button`, `.toolbar`, etc.
* layout rules
* `@apply`

Tokens are shared truth across:

* Vue SPA
* future PWA
* potential design system exports

---

### 3.2 Color system philosophy

Colors are semantic, not decorative.

Examples:

* `ink` → readable foreground
* `surface` → cards, panels, shells
* `border` → structure, not decoration
* `jacaranda`, `canopy`, `leaf`, `flame` → *meaningful accents only*

RGBA is **never** used. All opacity is via:

```css
rgb(var(--color-rgb) / alpha)
```

This is locked.

---

## 4. Global Base Layer (`app.css`)

### 4.1 Purpose

`app.css` defines:

* base element styling (`body`, headings, anchors)
* safe defaults (font smoothing, text color)
* *very small* helper utilities

It must remain minimal.

---

### 4.2 What must NOT live here

* Page layout
* Components
* Input theming (unless extremely generic)

If you hesitate whether something belongs here — it doesn’t.

---

## 5. Layout Layer (`layout.css`)

### 5.1 What layouts are

Layouts are **structural shells**, not components.

Examples:

* `.staff-layout`
* portal background gradients
* max-width containers
* header/footer scaffolding

Layouts answer: *“Where does content live?”*

---

### 5.2 What layouts are NOT

* Buttons
* Cards
* Chips
* Filters

Layouts must not assume *what* content is rendered inside them.

---

## 6. Component Layer (`components.css`)

This is the heart of the system.

### 6.1 Scope

Components are reusable, named UI patterns:

* overlays & modals
* cards
* chips & toggles
* analytics containers
* calendar cells
* action tiles

Everything here lives under:

```css
@layer components { … }
```

---

### 6.1.1 Portal Sidebar Rail Contract (Student/Guardian Shell)

Portal navigation for Student/Guardian surfaces uses one canonical component pair:

* `PortalLayout.vue` (state ownership)
* `PortalSidebar.vue` (rendering + interactions)

Styling must be driven by tokenized component classes in `components.css`, including:

* `.portal-sidebar`
* `.portal-sidebar--expanded`
* `.portal-sidebar--collapsed`
* `.portal-sidebar__item`
* `.portal-sidebar__label`
* `.portal-sidebar__tooltip`
* `.portal-sidebar__toggle`

Behavior contract (style-coupled):

1. Desktop (`lg+`) is rail mode:
   * collapsed width + expanded width variants
   * icons always visible
   * labels visually collapsed in rail mode
2. Mobile (`<lg`) is drawer mode:
   * full-width panel + backdrop
   * no collapsed rail treatment
3. Tooltips appear only in collapsed desktop mode, on hover and keyboard focus.
4. Active item state must include non-color cue (for example, inset edge marker), not color alone.

Accessibility + motion:

* Label text remains screen-reader available when visually collapsed.
* Rail transitions must disable motion under `prefers-reduced-motion`.

Forbidden:

* ad-hoc utility-only sidebar styling inside Vue templates
* component-level font-family overrides for sidebar typography
* introducing a second sidebar style system parallel to the portal rail classes

---

### 6.2 Overlay & Dialog System (HeadlessUI — Canonical)

Ifitwala uses **HeadlessUI Dialog + Transition** as the *behavior layer* and a **custom CSS overlay system** as the *visual + spatial truth*.

This is intentional.

#### 6.2.1 Separation of concerns

| Layer                      | Responsibility                                         |
| -------------------------- | ------------------------------------------------------ |
| HeadlessUI                 | Accessibility, focus trapping, keyboard handling, ARIA |
| OverlayHost / OverlayStack | Z-ordering, stacking, lifecycle                        |
| CSS (`.if-overlay*`)       | Visual appearance, spacing, motion, theming            |

No visual styling is allowed inside Vue Dialog components themselves.

---

#### 6.2.2 Single overlay truth

All dialogs, modals, and sheets must render through **one system**:

* `OverlayHost.vue` — global mount point
* `useOverlayStack.ts` — state + stacking control
* `.if-overlay*` classes — visual shell

There must **never** be:

* ad-hoc modals
* page-local dialog CSS
* duplicated backdrops

This prevents modal drift and inconsistent UX.

---

#### 6.2.3 Canonical CSS classes

The following classes are **locked API** between Vue and CSS:

* `.if-overlay`
* `.if-overlay__backdrop`
* `.if-overlay__wrap`
* `.if-overlay__panel`
* `.if-overlay__body`
* `.if-overlay__footer`

Transition hooks (used by HeadlessUI `TransitionChild`):

* `.if-overlay__fade-*`
* `.if-overlay__panel-*`

These names must not change without updating both CSS **and** Vue.

---

#### 6.2.4 Visual & motion philosophy

Overlay design follows the same calm-first principles as the rest of the UI:

* soft backdrop blur (not opaque blackout)
* centered, bounded panels (never full-screen by default)
* subtle vertical motion + fade (no scale popping)
* generous padding for touch + mouse

Animations are:

* short (≤ 180ms)
* ease-out only
* never chained or spring-based

---

#### 6.2.5 Z-order & stacking rules

The overlay stack is **explicit**, not incidental.

Rules:

* New dialogs stack above old ones
* Backdrops are shared but stacking-aware
* Closing the top dialog restores focus correctly

Agents must never manipulate z-index directly in CSS.

---

#### 6.2.6 Where NOT to style dialogs

Forbidden locations:

* Vue `<DialogPanel>` inline styles
* page-level CSS files
* Tailwind utility soup inside templates

If the dialog needs a new visual variant:

* extend `.if-overlay__panel` with a modifier class
* do **not** fork the system

---

### 6.3 Typography helpers are semantic

Classes like:

* `.type-h1`
* `.type-body`
* `.type-meta`

exist to:

* standardize text rhythm
* avoid ad-hoc font sizing in templates
* enable global typography evolution later

Vue templates **must use these**, not raw Tailwind text utilities.

---

### 6.4 Surfaces over colors

Cards are surfaces, not boxes.

Patterns:

* `.card-surface`
* `.palette-card`
* `.analytics-card`

Rules:

* Prefer soft surface colors over `bg-white`
* Borders are structural, never decorative
* Shadows are restrained and consistent

---

### 6.5 Analytics system is canonical

Analytics components are reused across dashboards.

Canonical pieces:

* `.analytics-shell`
* `.analytics-grid`
* `.analytics-card`
* `.analytics-chart*`

Important invariant:

> **Never use `min-height` on charts inside CSS grids.**

This avoids ResizeObserver feedback loops with `vue-echarts`.

---

### 6.6 Scoped form theming (critical rule)

Aggressive input theming is **always scoped**.

Pattern:

```css
.ifit-filters input,
.ifit-filters select,
…
```

Why:

* frappe-ui controls are complex
* teleported dropdowns bypass parent scopes
* global input overrides cause subtle breakage

Never style `input`, `select`, `textarea` globally.

---

## 7. Legacy Styles & Deletion Strategy

### 7.1 No blind deletions

A selector may look unused but still be required for:

* teleported menus
* conditional states
* modals not opened during dev
* responsive-only views

---

### 7.2 Approved cleanup process

1. **Static scan** (grep / ripgrep)
2. **Runtime coverage** (Chrome DevTools)
3. **Quarantine first**, delete later

Mark candidates as:

```css
/* LEGACY CANDIDATE — verify usage before deletion */
```

Never mass-delete.

---

## 8. Rules for Coding Agents (LLMs)

When modifying or adding styles:

### DO

* Respect file boundaries
* Reuse existing components
* Extend with variants (`--active`, `--wide`, …)
* Ask before inventing new primitives

### DO NOT

* Add Tailwind imports
* Add global element overrides
* Duplicate existing components
* Introduce new color semantics casually

If unsure, **stop and ask**.

---

## 9. Forward Compatibility

This architecture supports:

* Tailwind v4+ upgrades
* PWA extraction
* theme refinement
* partial design-system documentation

It intentionally avoids:

* CSS-in-JS
* component-local styling drift
* framework lock-in

---

## 10. Final Invariant (Read Twice)

> **If a style does not clearly belong to tokens, app, layout, or components — it does not belong in the codebase.**

Discipline here is what keeps the UI calm, scalable, and teachable.

---

## 11. Subsumed Notes

This document subsumes:

* `style_note.md` (kept for reference, not authority)

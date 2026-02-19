# AGENTS.md — Ifitwala Ed AI Agent Constitution

This repository is a **production-grade, multi-tenant Education ERP**.

AI agents **MUST** follow the rules below exactly.
If a rule is unclear or context is missing: **STOP. ASK. WAIT.**

Silent assumptions are considered defects.

---

## 0. Prime Directive (Non-Negotiable)

> **Do not invent. Do not assume. Do not drift.**

* Never invent fieldnames, DocTypes, schemas, permissions, or defaults
* Never rely on memory of “earlier versions”
* Always work from files currently present in the workspace
* If required files or schemas are missing → **STOP and ask**

A correct pause is better than a confident mistake.

---

## 0.1 Product Manager Mandate (Non-Negotiable)

Agents must operate with a **product manager mindset** and prioritize friction reduction for real users.

* Prefer in-product workflows (buttons, actions, guided UI) over CLI/manual operator steps.
* If a recurring operational task requires CLI, treat it as a product gap and propose/implement a UI path.
* Eliminate avoidable navigation and context-switching (surface links/actions where users already work).
* Silent UI dead-ends are defects; users must always have a clear next action.

---

## 1. Operating Discipline

### 1.1 Mandatory Workflow

Agents MUST follow:

1. **Plan**

   * Restate the task precisely
   * List exact files to be touched
   * Identify risks (data integrity, permissions, UX regressions)

2. **Green-Light**

   * Wait for explicit approval before:

     * Structural refactors
     * Schema changes
     * Cross-module logic changes

3. **Execute**

   * Perform **only** approved work
   * No opportunistic cleanup
   * No scope creep

---

## 2. Architectural Authority & Drift Control

* Architecture is **explicitly locked**
* Markdown files under:

  * `ifitwala_ed/docs/ are **authoritative**
* Code and documentation **must never diverge**
* If behavior changes (when explicitly requested):

  * Update the relevant markdown files
  * No exceptions

Drift is a bug.

---

## 3. Doctype & Data Model Invariants (Hard Rules)

### 3.1 No Business Logic in Child Tables

* Child table controllers:

  * Must be empty or UI-only
* ALL validation, computation, and side-effects belong in the **parent DocType**
* Logic in a child controller = **bug**

### 3.2 Never Assume Schemas

Agents MUST NOT invent fieldnames.

Mapping contract (hard rule):

* Never map or copy a field unless that field exists in the source DocType schema.
* Forbidden pattern in business flows: reading non-existent fields via defensive access (e.g., `doc.get("missing_field")`) just to avoid runtime errors.
* If a target requires data that the source DocType does not have, STOP and require an explicit architecture/schema decision.

Allowed sources:

* JSON schema files explicitly provided
* `frappe.get_meta()` **only when instructed**

If schema is incomplete or ambiguous → ASK.

### 3.3 NestedSet Is Sacred

Any DocType using `NestedSet` (`lft`, `rgt`):

* Must preserve hierarchy integrity
* Must use framework helpers only
* Manual SQL touching `lft` / `rgt` is forbidden

---

## 4. Enrollment, Assessment & Academic Invariants

### 4.1 Enrollment Is Transactional

* Enrollment requests are evaluated **once**
* Rule evaluation is snapshotted:

  * rule evaluated
  * value compared
  * outcome
* Approved enrollments are **never recomputed**
* Rule changes affect **future requests only**

### 4.2 Assessment Truth Model

* Criterion-level outcomes are the **authoritative truth**
* Task-level totals / grades are:

  * Optional
  * Derived
* Official grades:

  * MUST NOT link directly to child table rows
* No duplication of grade truth across tables

---

## 5. Backend (Frappe) Engineering Rules

### 5.1 Controllers & Hooks

* Prefer **Document controllers**:

  * `before_insert`
  * `before_save`
  * `after_insert`
  * `on_update`
  * `on_submit`
* Avoid hooks unless unavoidable
* Child table controllers remain empty

### 5.2 Database Discipline

* Reduce DB round-trips
* Prefer:

  * `frappe.db.get_value`
  * `frappe.db.get_values`
  * `frappe.get_all`
* Use Query Builder or parameterized SQL
* Never interpolate SQL strings manually

### 5.3 Caching Rules

* Shared or stable data MUST use Redis:

  * `frappe.cache()`
  * `@redis_cache(ttl=…)`
* Never rely on in-process dict caching
* Never cache:

  * Permission-sensitive queries
  * User-specific state (unless approved)

Assume multi-worker Gunicorn + scheduler.

---

## 6. Time, Calendar & Scheduling Rules (CRITICAL)

* Always use **Frappe site timezone**
* Never use server OS timezone
* Never hardcode country timezones

Helpers handling time MUST support:

* `datetime.timedelta` (Frappe `Time` fields)
* `datetime.time`
* `datetime.datetime`
* `str`

Rules:

* Centralize coercion (e.g. `_coerce_time`)
* No ad-hoc parsing
* Silent failures are forbidden
* Missing resolution must emit structured debug info

---

## 7. Frontend Architecture (LOCKED)

### 7.1 Direction of Travel

* Canonical stack:

  * **Vue 3**
  * **Tailwind CSS v4**
  * **frappe-ui**
* Legacy UI may exist:

  * It is tolerated
  * It must NOT be extended

### 7.2 Surfaces

**Portal / SPA (students, guardians, staff)**

* Vue 3 + Tailwind
* Built with Vite
* Output:

  * `public/ui`
  * `public/desk_vue`

**Desk**

* Transitional legacy surface
* No new Tailwind leakage
* New work prefers Vue where feasible

---

### 7.3 Frontend Interaction & API Contract Invariants (CRITICAL)

These rules exist to prevent silent UI failures, runtime-only bugs, and client/server contract drift.
They are **non-negotiable**.

---

#### 7.3.1 No Silent User-Action Failures

* Any user-triggered action (Create, Save, Submit, Confirm, etc.) MUST NOT fail silently.

* Code patterns like:

  if (!canSubmit.value) return

  without user feedback are considered **bugs**.

* If an action is blocked by validation, the UI MUST provide:

  * an inline error message near the action area, and/or
  * a toast explaining what is missing.

Users must always understand **why nothing happened**.

---

#### 7.3.2 Canonical POST Payload Shape (Hard Invariant)

* All POST calls via the SPA client MUST follow this rule:

  api(method, payload)

* The second argument is sent as the **JSON body directly**.

* Payloads MUST NOT be wrapped as:

  api(method, { payload })   // forbidden

  unless the server method explicitly requires a named argument.

* For frappe-ui resources:

  * POST endpoints MUST be called with:

    resource.submit(payload)

  * auto: true MUST NOT be used for POST resources.

Client/server payload shape drift is considered a **contract violation**.

---

#### 7.3.3 Watchers, Setup Order & TDZ Safety

* In <script setup>, any ref() or computed() referenced by a watcher MUST be declared **before** the watcher.
* watch(..., { immediate: true }) executes during setup and can trigger **Temporal Dead Zone (TDZ)** runtime crashes if it references later-declared constants.
* Prefer watching **props directly** rather than derived computed values when possible.

Minified runtime errors such as:

Cannot access 'w' before initialization

are usually TDZ issues, not naming or scoping issues.

---

#### 7.3.4 Modal Entry-Point Modes Must Be Explicit

Any modal that can be opened from multiple entry points MUST explicitly support two modes:

1. Prefilled / Locked Context Mode

   * Required context (e.g. student_group) is provided
   * Related fields are read-only or hidden
   * Unnecessary data fetches MUST be skipped

2. Unscoped / Selection Required Mode

   * No context is provided (e.g. quick links)
   * Modal MUST load selectable options
   * Required selections MUST be enforced before submission

If a modal works from one entry point but fails from another, this is a **design bug**, not a usage error.

---

#### 7.3.5 Debugging Minified Runtime Errors

* Do NOT infer meaning from minified variable names (w, t, e, etc.).
* When encountering runtime-only errors:

  * Check immediate watchers
  * Check setup-time evaluation
  * Check destructuring of watched values

Assume evaluation order issues before assuming logic or typing errors.

---

### 7.4 Historically-Derived Invariants (Read Carefully)

Some rules exist **not by design preference**, but because the team has already paid the cost of violating them.

These include (non-exhaustive):

* SPA payload shape rules
* HeadlessUI overlay constraints
* Tailwind CSS v4 single-entry discipline
* Vue `<script setup>` declaration order rules

Agents **MUST** treat these as **hard constraints**, even if they appear “over-strict” or redundant.

They are locked because they prevent **silent failures** that are expensive to debug post-build and difficult to detect during review.

---

## 8. Tailwind, Styling & Typography

### 8.1 Styling Discipline

* Tailwind must be scoped to Vue roots
* No global resets
* No cross-surface leakage
* Design tokens are the single source of truth

### 8.2 Typography (Locked)

* Use semantic helpers only: `.type-*`
* No component-level `font-family`
* Layout owns typography, not pages

---

## 9. Overlay & Modal System (Non-Negotiable)

* ONE modal system only:

  * HeadlessUI `Dialog` + `Transition`
* Rendered exclusively via **OverlayHost**
* Frappe-UI dialogs MUST NOT coexist
* Never mix modal systems

If an overlay opens empty:

* Assume overlay stack or focus-trap issue
* Not styling
* Debug before touching UI

---

## 10. SPA Navigation Rules

Inside the SPA:

❌ Forbidden

* Hardcoded `/portal/...`
* `window.location = '/portal/…'`

✅ Required

* Named routes
* Base-less paths (`/staff/...`, `/student/...`)

Router base already includes `/portal`.

---

## 11. Permissions, Visibility & Hierarchy

* Schools belong to Organizations (NestedSet)
* Selecting a parent includes all descendants
* Sibling isolation is mandatory

Visibility rules:

* Instructors see only students they teach
* Logs visible only to:

  * author
  * assigned follow-up
  * explicitly privileged roles
* Students and guardians NEVER use Desk

Permissions must be enforced **server-side**.

---

## 12. Scheduling & Attendance Invariants

* `rotation_day` → integer
* `block_number` → integer
* One instructor per schedule row
* Validate overlaps:

  * instructor
  * student
  * location
* Attendance:

  * Multi-block per day
  * Update only changed values
  * Inserts must include analytics fields
  * Default `attendance_method = "Manual"` for tools

---

## 13. Files & Media Handling

* Always use rename / move pattern
* Avoid orphaned files
* Respect:

  * `attached_to_doctype`
  * `attached_to_name`
  * folder case-sensitivity
* Sync images with linked User / Contact when required

### 13.1 File Governance (Non-Negotiable)

* **Dispatcher-only**: create files via `create_and_classify_file(...)` (or a governed API); no direct `File.insert()` in business flows.
* **Classification required**: a `File` without `File Classification` is a bug; derivatives must also be classified with `source_file`.
* **Atomic routing**: only update `file_url` after verifying the file exists at the destination.
* **No URL guessing in UI**: use canonical URLs returned by server/classification, then fallback safely.
* **Slots are semantics**: use explicit slots for derivatives (e.g., `profile_image_thumb`) and keep them deterministic.
* **Docs are authority**: follow `ifitwala_ed/docs/files_and_policies/*.md` for governance rules and allowed purposes/data classes.

---

## 14. Analytics & Reporting Rules

* Guard permissions early
* Build WHERE clauses centrally
* Prefer one indexed query over many
* Strip HTML in summaries (not print views)
* Display time as `hh:mm`
* Sort by real datetime, not formatted strings

---

## 15. Error Handling & Debug Protocol

* Silent failures are forbidden
* If core context exists but resolution fails:

  * Emit structured debug payload
  * Log Python types when relevant
* Never return `None` without explanation

---

## 16. Documentation Synchronization (Mandatory)

When architecture changes are made (if approved), agents MUST update corresponding docs, including but not limited to:

* `assessment_notes.md`
* `gradebook_notes.md`
* `task_notes.md`
* `curriculum_relationship_notes.md`

Docs must reflect **reality**, not aspiration.

---

## 17. Final Safety Rule

If unsure:

* Pause
* Ask
* Wait

> **A correct pause beats a confident regression.**


### Never swallow framework exceptions in permission or visibility logic.
Framework APIs must be called with documented signatures only.
Any silent failure in permission checks is a bug.


### Lesson: UI must be treated as “best effort”; invariants belong on the server

What happened is the classic trap:

You assumed “the modal closes → user can’t click again → no duplicates”.

But UI is not a security boundary, and not an invariant boundary.

Any glitch (slow network, component not unmounting, rerender, user rage-clicking) can spam your API.

So the rule is:

Client-side guard = good UX.
Server-side idempotency/uniqueness = real correctness.

You’ve implemented the UX guard. Now you must add the server invariant.

### Never let the client assemble a workflow out of generic CRUD calls.

If an action has meaning (submit, follow up, decide, close), it deserves:

a named endpoint

a single transaction

server-owned idempotency

You just moved this feature from “it works” to production-grade.

---

THE FILE PATH name and path is always on top of the file before the imports.

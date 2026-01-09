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

  * `/docs/
    are **authoritative**
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



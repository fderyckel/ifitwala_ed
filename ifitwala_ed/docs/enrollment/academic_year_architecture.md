<!-- ifitwala_ed/docs/enrollment/academic_year_architecture.md -->

# Academic Year Architecture & Design — Ifitwala_Ed

**Status:** Active (locked where marked)
**Audience:** humans + coding agents
**Scope:** Academic Year lifecycle, visibility, permissions, school-tree behavior, end-of-year governance, and how admissions/enrollment must consume Academic Year safely.

This document complements:

* `enrollment_notes.md` (enrollment decision-system invariants)
* `enrollment_examples.md` (reality checks / edge cases)

It also aligns with Admissions’ “requirements are local, lifecycle is global” framing.

---

## 0) Definitions (canonical)

### 0.1 Academic Year (AY)

An **Academic Year** is the institutional time container for enrollment, scheduling, terms, and year-based reporting.

In Ifitwala_Ed, AY is **school-scoped** (each AY belongs to exactly one School via `Academic Year.school`).

### 0.2 School tree scope

School scoping is **tree-aware**: selecting a parent School implies a scope expansion to all descendants.

We already have school-tree utilities that support ancestor/descendant resolution and cached “effective record” lookups.

### 0.3 Lifecycle vs visibility

* **Lifecycle** answers: “Is this year operational or closed?”
* **Visibility** answers: “Should Admissions / Applicant intake show this year as an option?”

These must not be conflated.

---

## 1) Guiding principles (locked)

### 1.1 Governance, not convenience

Academic Year transitions are **governed lifecycle events**, not ad-hoc filtering decisions.

Admissions and enrollment must **consume** lifecycle state; they must not invent their own “current year” heuristics.

### 1.2 School-scoped closure is the default

In multi-school environments, AY closure is **per-school**, even if multiple schools share the same calendar pattern.

No feature may assume the whole institution closes on the same day.

### 1.3 Parent-school authority can cascade

A parent-school Academic Admin may execute “close year” actions that **apply to all descendant schools**, but only with explicit permission and explicit confirmation of the affected scope (see §6).

---

## 2) Data model (current)

### 2.1 Academic Year fields (relevant)

Academic Year currently includes:

* `school` (Link, required)
* `archived` (Check) — “year is over / retired”
* `visible_to_admission` (Check) — “show in Student Applicant admission form”

**Interpretation (locked):**

* `archived = 0` → operational year
* `archived = 1` → closed year (no new operational activity should target it)
* `visible_to_admission = 1` → allowed as an “intent year” for Applicants
* `visible_to_admission = 0` → must not appear in Admissions pickers

### 2.2 Naming and uniqueness

Academic Year autonaming is school-based (`{School.abbr} {academic_year_name}`) and duplicate validation prevents the same `academic_year_name` from existing twice in the same school.

### 2.3 Calendar anchoring

Academic Year creates/updates School Event entries for start/end dates (with school + audience explicitly set).

---

## 3) Current behavior that must be treated as **legacy / unsafe**

### 3.1 `retire_ay()` is not school-scoped today

Current `AcademicYear.retire_ay()` updates **Terms** and **Program Enrollment** by `academic_year = X` without restricting by school.

This is unsafe in a multi-school system if:

* different schools share a year name pattern, or
* you ever introduce global years, or
* a parent school closes later/earlier than its descendants.

**Decision (locked):**

> Retirement/archival side-effects must be executed via the **End of Year Checklist** scope engine (school node + descendants), not via a global AY method.

`retire_ay()` can remain as a legacy admin shortcut only if it is later refactored to accept a scoped school list (and defaults to the caller’s permitted scope).

---

## 4) Admissions and Applicant usage (consumer rules)

### 4.1 Student Applicant stores “intent”

Student Applicant has:

* `school` (required)
* `academic_year` (intent) as Link to Academic Year

**Rule (locked):**

> Applicant “intent” does not grant enrollment truth. It is informational until promotion/enrollment decisions occur.

This mirrors the enrollment architecture: “requests and intent are not committed truth.”

### 4.2 Admissions dropdown filtering (locked)

For a given applicant `school = S`, Academic Year options must be filtered to:

* `Academic Year.school IN scope_schools(S)`
* `visible_to_admission = 1`
* `archived = 0`

Where:

* `scope_schools(S)` means:

  * if S is a leaf:
    * use **S** if it has any Academic Year with `visible_to_admission = 1` and `archived = 0`
    * otherwise inherit the **nearest ancestor** that has any Academic Year with `visible_to_admission = 1` and `archived = 0`
  * if S is a parent: S + descendants

The underlying school-tree resolution must use the existing utilities patterns (ancestor/descendant) to avoid bespoke logic.

---

## 5) End of Year Checklist (future authority)

### 5.1 Current state

“End of Year Checklist” is currently a **Single** doctype with only buttons and no scoping fields.

That is insufficient for multi-school governance because it cannot express:

* which school node is being closed
* which academic year is being closed
* which descendants are included
* who is authorized to execute it

### 5.2 Decision (locked): Checklist becomes the authority surface

The checklist is the **only supported governance surface** for year closure operations (terms, enrollments, student groups, admission visibility).

Academic Year itself remains the data container; the checklist is the controlled executor.

---

## 6) School-scoped execution model (the “top filter” design)

### 6.1 Scope selector (UI/UX rule)

The checklist must have **one school selector at the top** (“Target School”).

When the selected school is a parent, execution scope expands to:

* `target_school + all descendants`

The UI must display the **resolved affected schools list** before any destructive action.

### 6.2 Permission rule (locked)

Selecting a parent school for cascade requires:

1. user default school == that parent school (institutional anchor)
2. user holds an administrative role for that parent school (e.g., Academic Admin / System Manager)

This matches the broader “scope is institutional, not only role-based” invariant.

### 6.3 Execution is per-school, not global

Even when cascading from a parent, operations are applied **per affected school**, never as an unscoped global SQL update.

This prevents “closing the year for a sibling school” by accident.

---

## 7) What “closing an academic year” means (explicit outcomes)

When executing year closure for `(school scope, academic_year_name or AY record)`:

### 7.1 Hard invariants

For each affected school:

* Terms in that school+year are archived
* Program Enrollments in that school+year are archived
* Student Groups in that school+year are archived (if applicable)
* Academic Years in that school+year are set:

  * `archived = 1`
  * `visible_to_admission = 0` (must never remain visible)

Academic Year retirement implies “not selectable for new admissions intents” by definition.

### 7.2 Idempotency requirement

All checklist actions must be idempotent:

* re-running an action should not create duplicates or change meaning
* repeated executions should produce the same end state

---

## 8) Enrollment alignment (why Academic Year matters to enrollment)

Enrollment is a **decision system** with institutional memory.

Academic Year provides the “time container” used by:

* Program Offering selection windows
* Enrollment Requests evaluation windows
* Program Enrollment committed truth
* Scheduling and attendance aggregation

**Rule (locked):**

> Enrollment evaluation must never infer “current year” from dates. It must use explicitly chosen Academic Year context (from Program Offering / Request / Student context).

This prevents policy drift across institutions (see examples).

---

## 9) Anti-patterns (bugs, not preferences)

### 9.1 Date math as authority

❌ “Show only years whose start_date is within N months”
❌ “Pick the latest by year_end_date”

AY visibility must be lifecycle-driven (`archived`, `visible_to_admission`) and school-scoped.

### 9.2 Global SQL updates without school scoping

❌ `UPDATE tabProgram Enrollment SET archived=1 WHERE academic_year=%s` (unscoped)
This is the current legacy behavior and must not be used in new code.

### 9.3 Silent cascade

❌ Parent selection affecting children without explicit confirmation list

---

## 10) Required refactors (implementation backlog derived from these decisions)

1. **Refactor End of Year Checklist from Single-with-buttons to scoped executor**

   * Add: `school` (Link), `academic_year` (Link), `status` (Draft/In Progress/Completed)
   * Add a scope preview showing affected schools (target + descendants)

2. **Deprecate or harden `AcademicYear.retire_ay()`**

   * Must accept a school scope; must not run unscoped global SQL updates

3. **Admissions filtering**

   * Student Applicant academic_year link query must filter:

     * `school in scope_schools(applicant.school)`
     * `visible_to_admission = 1`
     * `archived = 0`

4. **Permissions**

   * Ensure only parent-anchored admins can cascade closures (default-school + role check)

---

## 11) Non-goals (explicit)

* This document does not define term windows, offerings, or basket rules (see enrollment docs).
* This document does not decide UI placement (Desk vs Portal) beyond the “top filter + scope preview” governance requirement.

---

## Final statement (locked)

Academic Year visibility and closure in Ifitwala_Ed is:

* **school-tree scoped**
* **lifecycle-governed**
* **auditable**
* **idempotent**
* **never inferred**

Admissions and enrollment are consumers of this state, not owners of it.

---

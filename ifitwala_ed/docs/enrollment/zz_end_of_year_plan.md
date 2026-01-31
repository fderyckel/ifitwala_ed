# PR Checklist — Academic Year Architecture & End-of-Year Governance

**Scope:** Academic Year lifecycle, admissions visibility, end-of-year closure, school-tree scoping
**Rule:** One PR per section below (do not bundle across sections)

---

## PR-1 — End of Year Checklist: Scope & Authority Refactor (FOUNDATIONAL)

**Goal:** Turn the checklist into the single authoritative executor, school-scoped.

### Data / Doctype

* [ ] Add `school` (Link → School, required)
* [ ] Add `academic_year` (Link → Academic Year, required)
* [ ] Add `status` (Select: Draft / In Progress / Completed)
* [ ] Enforce uniqueness on `(school, academic_year)`
* [ ] Keep **single doctype** (no per-school duplication)

### Permissions

* [ ] Leaf school admin can select own school only
* [ ] Parent school selection allowed **only if**:

  * user default school == selected parent school
  * user has admin role on that parent school
* [ ] System Manager bypass remains explicit

### Scope resolution

* [ ] On school selection, resolve:

  * selected school + all descendants
* [ ] Display resolved school list in UI (read-only preview)
* [ ] Never execute actions without resolved scope confirmation

### Status semantics

* [ ] Draft → no actions executed
* [ ] In Progress → partial execution allowed
* [ ] Completed → all buttons locked (read-only)
* [ ] Checklist becomes audit artifact once completed

---

## PR-2 — End of Year Actions: Idempotent, School-Scoped Execution

**Goal:** All closure logic runs through checklist scope, never globally.

### Academic Year

* [ ] For each scoped school:

  * set `archived = 1`
  * set `visible_to_admission = 0`
* [ ] Never archive AY globally unless explicitly intended

### Terms

* [ ] Archive **only** terms where:

  * `school ∈ scoped schools`
  * `academic_year == selected academic_year`

### Program Enrollment

* [ ] Archive enrollments **per school**
* [ ] No unscoped `academic_year = X` SQL updates

### Student Groups

* [ ] Archive groups **per school + academic year**
* [ ] No cross-school leakage

### Idempotency

* [ ] Re-running buttons produces no side effects
* [ ] All actions safe if partially completed before

---

## PR-3 — Deprecate / Harden `AcademicYear.retire_ay()`

**Goal:** Prevent unsafe global retirement paths.

* [ ] Mark `retire_ay()` as:

  * deprecated **or**
  * restricted to internal use only
* [ ] If kept:

  * require explicit school scope parameter
  * forbid global execution
* [ ] Add inline docstring warning about multi-school risk
* [ ] Ensure no caller relies on implicit global behavior

---

## PR-4 — Admissions Filtering: Academic Year Visibility (CONSUMER FIX)

**Goal:** Admissions reflects lifecycle state, no inference.

### Student Applicant

* [ ] Academic Year link query filters:

  * `archived = 0`
  * `visible_to_admission = 1`
  * `school ∈ scope_schools(applicant.school)`
* [ ] No date math (`today()`, start/end comparisons)
* [ ] Fail closed if applicant.school not set

### Server guard (recommended)

* [ ] Validation blocks:

  * archived AY
  * AY not visible to admission
  * AY outside applicant school scope

---

## PR-5 — School Tree Utilities: Reuse, Don’t Re-Invent

**Goal:** One canonical way to resolve school scope.

* [ ] Use existing school tree helpers (`descendants`, `effective scope`)
* [ ] No ad-hoc recursion or SQL in checklist logic
* [ ] Cache where appropriate (read-heavy paths)
* [ ] Add tests for:

  * leaf school
  * parent school
  * deep tree

---

## PR-6 — UX & Safety Rails (MANDATORY)

**Goal:** Prevent irreversible mistakes.

* [ ] Confirmation dialog before execution includes:

  * selected school
  * resolved affected schools
  * academic year
  * irreversible consequences
* [ ] Buttons disabled when:

  * status = Completed
  * user lacks scope authority
* [ ] Clear copy: “This affects X schools”

---

## PR-7 — Backward Compatibility & Migration

**Goal:** Do not break existing installs.

* [ ] Existing Academic Years:

  * keep current `archived` and `visible_to_admission` values
* [ ] Existing End of Year Checklist:

  * migrate to new schema (default status = Draft)
* [ ] No data loss
* [ ] No silent re-archival

---

## PR-8 — Documentation & Contracts (NON-OPTIONAL)

**Goal:** Prevent future drift.

* [ ] Add new file:

  * `docs/enrollment/academic_year_architecture.md` (already drafted)
* [ ] Cross-link from:

  * enrollment notes
  * admissions governance
* [ ] Inline code comments where governance is enforced
* [ ] Explicitly document:

  * “Admissions consumes AY state; never defines it”

---

## PR-9 — Tests (MINIMUM BAR)

**Must have:**

* [ ] Leaf school closure affects only itself
* [ ] Parent school closure cascades correctly
* [ ] Admissions dropdown hides archived AY
* [ ] Admissions dropdown respects visibility flag
* [ ] Unauthorized user cannot cascade from parent
* [ ] Idempotent re-execution

---

## Final Merge Gate (hard)

A PR **must not merge** unless:

* [ ] No global `academic_year = X` updates remain
* [ ] Checklist is the only closure executor
* [ ] Admissions logic has zero date inference
* [ ] School tree scoping is explicit and previewed
* [ ] Permissions match institutional authority

---

### One-line rule for reviewers

> If a school cannot safely close its year without affecting another school, **the PR is wrong**.

If you want, next step I can:

* split this into **actual PR branches order**
* or generate **commit-level TODOs** for the first PR (Checklist refactor)

# 3️⃣ NEW NOTE — Admissions Implementation Plan

**Ifitwala_Ed — Execution Roadmap**

> This plan assumes the Admissions Canonical Contract is locked.

---

## Phase 0 — Governance (NO CODE)

* Freeze ACC as authoritative
* Share with all agents / contributors
* Reject PRs that violate it

---

## Phase 1 — Pipeline Wiring (Minimal, Structural)

**Goal:** Make the pipeline real, even if empty.

1. Inquiry → **Invite to Apply**

   * Server method
   * Creates Student Applicant
   * Links back to Inquiry
   * Writes audit entry

2. Student Applicant

   * Expand statuses per ACC
   * Enforce editability by status

3. Promotion stub

   * Applicant → Student (minimal fields)
   * Idempotent
   * Logs promotion

✅ At end of Phase 1:
A student can exist **only** via Applicant.

---

## Phase 2 — Admissions Intelligence

**Goal:** Enable real decision-making.

4. Applicant Interview (staff-only)
5. Applicant Health Profile
6. Applicant Policies (versioned acknowledgements)
7. Applicant Documents + review flags

---

## Phase 3 — Legal & Operational Closure

**Goal:** Make promotion safe and complete.

8. Full promotion mapping:

   * Guardians
   * Health → Student Patient
   * Files
   * Account Holder resolution

9. Admissions Communication doctype

   * Missing info requests
   * Decisions
   * Timeline integrity

---

## Phase 4 — UX & Portal (intentionally last)

* Portal flows
* Form UX
* Notifications
* Automation polish

---


Below is **Phase 1 rewritten as a non-ambiguous, agent-executable specification**.
This is written so a **coding agent (Codex / Copilot / human)** can execute it **without interpretation** and produce reviewable PRs.

No UI. No portal. No satellites.
Only **structural truth enforcement**.

---

# Phase 1 — Admissions Pipeline Wiring

**Codex Execution Spec + PR Checklist**

> Goal: Make the admissions pipeline *real and enforceable* even with empty data.
>
> Success criterion:
> **A Student cannot exist unless promoted from a Student Applicant, and a Student Applicant may optionally link to an Inquiry (required when invited).**

---

## PHASE 1 — OVERALL CONSTRAINTS (READ FIRST)

These rules apply to *all* tasks below:

* ❌ Do NOT introduce new Applicant sub-domain doctypes yet

* ❌ Do NOT implement portal, forms, SPA, or web UX

* ❌ Do NOT auto-create Students anywhere

* ❌ Do NOT rely on comments or informal conventions

* ✅ All transitions must be **explicit server-side methods**

* ✅ All mutations must be **idempotent**

* ✅ All side-effects must be **auditable**

* ✅ All permissions must follow ACC semantics

---

# TASK GROUP 1 — Inquiry → Applicant Invitation

## Task 1.1 — Add canonical linkage: Inquiry → Student Applicant

### Action

Modify **Inquiry DocType**.

### Required changes

* Add a **Link field**:

  * `student_applicant` → Link to `Student Applicant`
  * Read-only
  * Hidden from public Web Form

### Acceptance criteria

* Inquiry can reference **at most one** Student Applicant
* Field is empty until invitation
* Field is immutable once set

---

## Task 1.2 — Implement server method: `invite_to_apply()`

### Location

`Inquiry` Python controller (Document method)

### Method signature

```python
def invite_to_apply(self) -> str
```

### Preconditions (must be enforced)

* Inquiry state == `Qualified`
* Inquiry has **no** linked `student_applicant`
* Caller has Admissions permission

### Method behavior (atomic)

1. Create **Student Applicant**

   * Minimal required fields only
   * Status = `Invited`
   * Link back to Inquiry
2. Set `inquiry.student_applicant`
3. Write a **Comment / Timeline entry**:

   * “Applicant invited by <user>”
4. Return `student_applicant.name`

### Idempotency rule

* If Inquiry already has `student_applicant`, method:

  * Returns existing name
  * Does NOT create a second Applicant
  * Does NOT error

### Acceptance criteria

* Cannot be called from Draft / Contacted / Archived
* Cannot create duplicate Applicants
* Leaves Inquiry in a consistent state even if called twice

---

## Task 1.3 — Enforce Inquiry state semantics

### Action

Centralize Inquiry state transitions.

### Required changes

* Explicit server-side methods for:

  * `mark_assigned()`
  * `mark_contacted()`
  * `mark_qualified()`
  * `archive()`
* Prevent direct mutation of `workflow_state`

### Acceptance criteria

* “Qualified” is the **only** state that permits `invite_to_apply`
* “Archived” blocks all further actions
* Transitions are auditable (comment or log)

---

# TASK GROUP 2 — Student Applicant as Staging Container

## Task 2.1 — Expand Student Applicant statuses (semantic, not cosmetic)

### Action

Update **Student Applicant DocType**

### Required statuses

* Draft
* Invited
* In Progress
* Submitted
* Under Review
* Missing Info
* Approved
* Rejected
* Promoted

### Rules

* Status changes must go through **controller methods**
* No free editing of `application_status`

### Acceptance criteria

* Status alone determines editability
* Invalid transitions throw explicit errors

---

## Task 2.2 — Implement Applicant edit-lock rules

### Action

Student Applicant Python controller

### Required behavior

Based on status:

| Status       | Family Edit      | Staff Edit |
| ------------ | ---------------- | ---------- |
| Draft        | ❌                | ✅          |
| Invited      | ✅                | ✅          |
| In Progress  | ✅                | ✅          |
| Submitted    | ❌                | ✅          |
| Under Review | ❌                | ✅          |
| Missing Info | ✅ (scoped later) | ✅          |
| Approved     | ❌                | ✅          |
| Rejected     | ❌                | ❌          |
| Promoted     | ❌                | ❌          |

### Acceptance criteria

* Illegal writes raise validation errors
* No silent failures
* Rules enforced server-side (not JS-only)

---

## Task 2.3 — Add canonical linkage: Applicant → Student

### Action

Modify **Student Applicant DocType**

### Required changes

* Add Link field:

  * `student` → Link to `Student`
  * Read-only
  * Set only during promotion

### Acceptance criteria

* Empty until promotion
* Immutable once set

---

# TASK GROUP 3 — Promotion Stub (Applicant → Student)

## Task 3.1 — Implement `promote_to_student()` (stub)

### Location

`Student Applicant` Python controller

### Method signature

```python
def promote_to_student(self) -> str
```

### Preconditions

* Applicant status == `Approved`
* Applicant has **no linked Student**
* Caller has Admissions permission

### Method behavior (v1 stub)

1. Create **Student**

   * Minimal required fields only
   * Link `student.student_applicant = self.name`
2. Set `applicant.student`
3. Set `applicant.status = Promoted`
4. Write audit comment:

   * “Applicant promoted to Student by <user>”
5. Return `student.name`

### Explicit exclusions (v1)

* ❌ No health data
* ❌ No guardians
* ❌ No files
* ❌ No enrollment
* ❌ No Student Patient yet

### Idempotency rule

* If Applicant already has `student`:

  * Return existing student name
  * Do NOT create duplicate Student
  * Do NOT error

### Acceptance criteria

* Student cannot be created any other way
* Promotion is irreversible
* Promotion is logged

---

## Task 3.2 — Enforce “no implicit Student creation”

### Action

Audit codebase.

### Required changes

* Remove / block:

  * Any automatic Student creation from Inquiry
  * Any Student creation from Web Forms
  * Any background job creating Students

### Acceptance criteria

* Only `promote_to_student()` creates Student records
* Violations raise explicit errors

---

# TASK GROUP 4 — Phase 1 Integrity & Safety

## Task 4.1 — Permission enforcement

### Action

Verify permissions.

### Requirements

* Public users:

  * Can create Inquiry only
* Admissions staff:

  * Can invite Applicant
  * Can approve / reject
  * Can promote
* Families:

  * Cannot exist yet (Phase 2)

### Acceptance criteria

* Unauthorized calls raise permission errors
* No reliance on UI hiding

---

## Task 4.2 — Audit trail guarantees

### Action

Ensure **every** transition writes an artifact.

### Required artifacts

* Comment OR structured log for:

  * Invitation
  * Status changes
  * Promotion

### Acceptance criteria

* Timeline shows a complete admissions story
* No silent state changes

---

# PHASE 1 — FINAL ACCEPTANCE CHECKLIST (PR BLOCKER)

A PR completing Phase 1 **MUST** satisfy all below:

* [ ] Inquiry can exist without Applicant
* [ ] Applicant may exist without Inquiry; invite-to-apply always links Inquiry ↔ Applicant
* [ ] Student cannot exist without Applicant
* [ ] Invitation is explicit and auditable
* [ ] Promotion is explicit, idempotent, irreversible
* [ ] Status semantics enforce behavior
* [ ] No UI or portal assumptions added
* [ ] No Applicant sub-domains added yet
* [ ] No auto-enrollment or accounting logic introduced

If **any** box is unchecked → Phase 1 is not complete.

---

## Final instruction to agent (non-negotiable)

> **Do not optimize.
> Do not extend.
> Do not anticipate Phase 2.
> Make the pipeline impossible to misuse.**

---


Perfect. Below is **Phase 1 split into clean, reviewable PRs — one PR per task group**.
This is **Codex-ready**, reviewer-friendly, and minimizes merge risk.

Each PR is **independently valid**, but **must be merged in order**.

---

# Phase 1 — PR Breakdown (Authoritative)

> Rule: **Do not start PR N+1 until PR N is merged.**
> Each PR enforces new invariants that later PRs rely on.

---

## 🔹 PR-01 — Inquiry → Applicant Invitation (Canonical Handoff)

**Purpose**
Make the Inquiry → Applicant boundary explicit, enforced, and auditable.

### Scope

* Inquiry DocType
* Inquiry controller only

### Changes

* Add `student_applicant` Link field (read-only)
* Implement `invite_to_apply()` server method
* Enforce idempotency
* Add audit comments
* Centralize Inquiry state transitions

### Files touched (expected)

* `inquiry.json`
* `inquiry.py`
* (optional) `inquiry.js` for button wiring later (no UI logic required yet)

### Acceptance checklist

* [ ] Inquiry can exist without Applicant
* [ ] Applicants invited via `invite_to_apply` are linked to the Inquiry (direct staff creation allowed)
* [ ] Cannot invite unless Inquiry is `Qualified`
* [ ] Calling twice does not create duplicates
* [ ] Audit trail is written
* [ ] No Student creation anywhere

🚫 **Hard no**

* No portal logic
* No Applicant sub-domains
* No Student logic

---

Ambiguities of PR01 removed

## ✅ 1. Student Applicant ↔ Inquiry linkage — **GREEN-LIGHT: add now, but optional**

**Decision**

✔ **Add the link field in PR-01**, on **Student Applicant**, but **do NOT make it mandatory**.

**Canonical position**

* The Inquiry → Applicant relationship is **one-to-zero-or-one**, not mandatory.
* Applicants may be created:

  * from an Inquiry (**most common**), or
  * directly by staff (walk-ins, internal referrals, edge cases).

**Exact field**

* **On Student Applicant**
  `inquiry` → Link to `Inquiry`

  * optional
  * read-only once set
* **On Inquiry**
  `student_applicant` → Link to `Student Applicant`

  * read-only

**Why now (PR-01)**

* This link is part of the **handoff contract**, not Applicant lifecycle logic.
* It allows:

  * full pipeline traceability
  * clean audit (“this applicant originated from this inquiry”)
* Making it optional avoids over-constraining future flows.

✔ **Approved to implement in PR-01**

---

## ✅ 2. Applicant status mismatch — **GREEN-LIGHT: update statuses now**

**Decision**

✔ **Yes, update Student Applicant statuses in PR-01/PR-02**, not later.
Do **not** create Applicants without a meaningful state.

**Action**

Replace current:

* Applied
* Approved
* Rejected
* Admitted

With **canonical lifecycle states** (exact names flexible, semantics not):

* Draft *(staff-created, not yet sent)*
* Invited *(family portal access granted)*
* In Progress *(family editing)*
* Submitted *(family done, staff review only)*
* Under Review
* Missing Info
* Approved
* Rejected
* Promoted *(terminal)*

**invite_to_apply() behavior**

* Creates Student Applicant
* Sets status = **Invited**
* Writes audit comment
* Does **not** imply submission or approval

**Why now**

* Status semantics drive **permissions, locking, and UI** later.
* Creating Applicants without status is how pipelines rot.
* This is a **schema correction**, not a feature change.

✔ **Approved to change now**

---

## ✅ 3. Inquiry state alignment — **GREEN-LIGHT: align fully now**

**Decision**

✔ **Yes — align Inquiry states to canonical set now**
✔ **Yes — update `admission_utils.py` and `inquiry.js` accordingly**

**Canonical Inquiry states**

* New
* Assigned
* Contacted
* Qualified
* Archived

**Remove / deprecate**

* Nurturing
* Accepted
* Unqualified
  (these belong either to Applicant stage or to reporting tags, not state)

**Rules**

* `Qualified` → allows `invite_to_apply()`
* `Archived` → hard stop (no Applicant creation)
* Inquiry never represents a decision outcome

**Why this is correct**

* Inquiry is **triage only**
* Decisions belong to **Applicant**, not Inquiry
* This simplifies SLA logic and avoids semantic overlap

✔ **Approved to refactor now**

---

## ✅ 4. Admissions permissions — **GREEN-LIGHT: explicit role set**

**Decision**

✔ Admissions permissions = **Admission Manager + Admission Officer**

**Applies to**

* `invite_to_apply()`
* Inquiry state transitions
* Applicant status transitions (except family-editable phases)
* Promotion (later PR)

**Explicit rule**

* Guardians / Applicants: **never**
* Teachers / Academic staff: **never**
* IT / System Manager: only via override / debug (not normal flow)

**Implementation note**

* Use role checks in server methods (not client JS).
* Prefer a small helper like `has_admissions_permission(user)` to avoid role drift.

✔ **Approved**





---

## 🔹 PR-02 — Student Applicant Becomes a Real Staging Container

**Purpose**
Turn Student Applicant into a governed lifecycle object, not a placeholder.

### Scope

* Student Applicant DocType
* Student Applicant controller

### Changes

* Expand `application_status` to full ACC set
* Remove free-edit of status
* Enforce status transitions via controller
* Add `student` Link field (read-only)
* Enforce edit-lock rules by status

### Files touched

* `student_applicant.json`
* `student_applicant.py`

### Acceptance checklist

* [ ] Status controls editability server-side
* [ ] Invalid status transitions raise errors
* [ ] Applicant links back to Inquiry
* [ ] Applicant can link to Student later
* [ ] No promotion logic yet

🚫 **Hard no**

* No Applicant satellites
* No interviews yet
* No promotion yet

---

## 🔹 PR-03 — Promotion Stub (Applicant → Student)

**Purpose**
Create the **only legal path** for Student creation.

### Scope

* Student Applicant controller
* Student DocType linkage only

### Changes

* Implement `promote_to_student()` stub
* Create minimal Student record
* Link Student ↔ Applicant
* Lock Applicant (status → Promoted)
* Enforce idempotency
* Add promotion audit log

### Files touched

* `student_applicant.py`
* `student.json` (if minimal required fields need adjustment)

### Acceptance checklist

* [ ] Student cannot be created without Applicant
* [ ] Promotion only allowed from `Approved`
* [ ] Calling twice returns same Student
* [ ] Promotion is irreversible
* [ ] Audit trail written

🚫 **Hard no**

* No health
* No guardians
* No Student Patient
* No enrollment
* No accounting

---

## 🔹 PR-04 — Pipeline Safety & Permission Enforcement

**Purpose**
Make the pipeline **impossible to misuse**.

### Scope

* Permissions
* Validation
* Safety audits

### Changes

* Enforce:

  * Only staff can invite / approve / promote
  * Public users only create Inquiry
* Remove / block any implicit Student creation
* Ensure every state change writes an audit artifact

### Files touched

* `inquiry.py`
* `student_applicant.py`
* Any utility/helper that creates Student today

### Acceptance checklist

* [ ] Unauthorized calls fail loudly
* [ ] No background job or hook creates Students
* [ ] Timeline tells a complete admissions story
* [ ] Phase-1 invariants fully enforced

🚫 **Hard no**

* No new doctypes
* No UI
* No portal

---

# Merge Order (Strict)

1️⃣ PR-01 — Inquiry → Applicant Invitation
2️⃣ PR-02 — Applicant Lifecycle Enforcement
3️⃣ PR-03 — Promotion Stub
4️⃣ PR-04 — Safety & Permissions

Skipping or reordering breaks guarantees.

---

# What Phase 1 Guarantees After All PRs

✔ Inquiry filters
✔ Applicant accumulates (empty but real)
✔ Promotion exists (stub, safe)
✔ Student creation is controlled
✔ No future PR can bypass the pipeline

This is the **foundation OpenApply-class systems rely on**.

---

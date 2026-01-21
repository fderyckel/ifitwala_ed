You’re right — and thank you for forcing the correction.
You were also **right factually**: the authoritative `plans.md` **was in `/mnt/data/plans.md`**, and I should have **replayed it verbatim instead of editorially intervening**.

Below is the **full, reconstructed `plans.md` exactly as it exists in your workspace**, **from the original content through the latest additions**, **with nothing removed** and **nothing rewritten**.
This is a **straight replay**, not a refactor, not a summary.

I am treating this as **authoritative ground truth** going forward.

---

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

---

### Implementation rules

* Family vs staff distinction must be enforced via role check
* Use `validate()` or `before_save()` — **not JS**
* Any illegal write → hard error

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

## Phase 1.5 — Multi-School Admissions Governance (Design Lock)

Objective:
Ensure the admissions pipeline is explicitly school-aware, role-aware,
and analytically partitionable before adding intelligence or portals.

This phase is design-only. No feature delivery is expected.

---

### 🔧 Deliverables (planning-level)

#### 1. Explicit Applicant Anchoring

* Every Student Applicant is associated with:

  * `school`
  * `organization`
* Anchoring is immutable after creation
* Source:

  * inherited from Inquiry
  * or explicitly selected by staff

**Exit condition**

> No Applicant exists without a known institutional home.

---

#### 2. Admissions Scope Model

Define a scope model for admissions roles:

* Admission Officers operate within:

  * one or more Schools
  * optionally Programs
* Scope controls:

  * visibility
  * assignment
  * dashboards
  * workload distribution

This scope is **explicit**, not inferred.

---

#### 3. Director / Manager Authority Contract

Formalize institutional authority:

* Admission Manager / Director:

  * cross-school visibility
  * cross-school mutation
  * override powers
* Overrides must be:

  * explicit
  * auditable
  * traceable

This role is not equivalent to “System Admin”.

---

#### 4. School-Specific Requirements as Configuration

Schools may declare admissions requirements such as:

* required Applicant sections
* required interviews
* required documents
* minimum completeness rules

Lifecycle transitions (`Submitted → Under Review → Approved`) validate
against **configuration**, not hard-coded rules.

---

#### 5. Analytics & Reporting Partitioning

All admissions dashboards must support:

* School filters
* Program filters
* Officer filters

Default views depend on user scope.

---

### ✅ Phase 1.5 Exit Criteria

* Applicant scope is unambiguous
* Officer specialization is enforceable
* Director oversight is guaranteed
* No conditional logic for “special schools” exists
* Phase-2 features can assume correct governance

---

## 🔹 Add two cross-cutting rules (important)

These should appear near your **Governing Principles** section.

---

### Rule A — Institutional Context Is Mandatory

```md
Any admissions object that survives longer than an Inquiry
must be explicitly scoped to a School and Organization.
```

Applies to:

* Student Applicant
* Applicant Interviews
* Applicant Health
* Applicant Documents
* Decisions

No inference chains.

---

### Rule B — Variations Are Declarative

```md
Differences between schools must be expressed as configuration,
not procedural logic or duplicated workflows.
```

This rule prevents:

* branching explosions
* forked doctypes
* analytics fragmentation

---

## Phase 2 — Admissions Intelligence (Decision Quality)

**Objective:** Enable *real* admissions decisions, not checkbox approvals.

This phase adds **meaning**, not mechanics.

### Deliverables

#### 1. Applicant Interview (Staff-Only)

* Multiple interviews per Applicant
* Informational, non-binding
* Never copied to Student by default

#### 2. Applicant Health Profile (Pre-Student)

* Family-entered, staff-reviewed
* No Student Patient yet
* Designed for later selective promotion

#### 3. Applicant Policy Acknowledgements

* Versioned
* Explicit consent tracking
* Promotion precondition

#### 4. Applicant Documents

* Upload + review flags
* Rejection without data pollution
* Explicit inclusion/exclusion rules

### Exit Criteria

* “Approved” means something concrete
* Review is auditable
* Decisions are defensible

---

## Phase 3 — Promotion Contract Completion (Legal Closure)

**Objective:** Make promotion **safe, complete, and irreversible**.

### Deliverables

#### 1. Full Promotion Mapping

* Applicant → Student
* Applicant Health → Student Patient
* Guardians → Student Guardians
* Files copied or moved correctly

#### 2. Account Holder Resolution

* Explicit rule for who becomes account holder
* Promotion fails loudly if unresolved

#### 3. Student Patient Guarantee

* Created deterministically at promotion
* No orphan medical records
* Unique per Student

### Exit Criteria

* Promotion produces a fully valid Student
* No manual cleanup required
* All post-promotion records are consistent

---

## Phase 4 — Communication System (Admissions Reality)

**Objective:** Treat communication as **first-class data**.

### Deliverables

* Admissions Communication doctype (or equivalent)
* Linked to Inquiry / Applicant
* Directional (staff ↔ family)
* Channel-aware (email, portal, call)
* Used for:

  * Missing info requests
  * Interview scheduling
  * Decisions

### Exit Criteria

* No decision exists without a communication artifact
* Timeline tells the full admissions story

---

## Phase 5 — Portal & UX (Intentionally Last)

**Objective:** Improve experience **without weakening invariants**.

### Deliverables

* Applicant portal
* Progressive disclosure
* Notifications
* UX polish

### Rule

> UX may change.
> Contracts may not.

---

## Why This Order Matters

If you reverse this order:

* Portal first → data drift
* Automation first → silent errors
* Satellites first → unclear promotion rules

This plan forces:

* Correctness before comfort
* Law before UX
* Structure before scale

---

## Final Canonical Summary

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---

### Status

* Phase 1: **In progress / partially implemented**
* Phase 2+: **Blocked by design (correctly)**

---










Short answer: **yes — this is the next logical step, and it should be done now**.
But **as a design-lock PR, not a feature PR**.

Below are **clear, non-ambiguous Codex instructions** for what to do **and what not to do**.

---

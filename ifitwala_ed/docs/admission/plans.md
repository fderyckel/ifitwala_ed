Good. Proceeding **now** with **one file only**.

### Scope (explicit)

* **File:** `plans.md`
* **Action:** Refactor + tighten + align with *current reality*
* **Rules respected:**

  * Nothing removed unless **obsolete or inaccurate**
  * Content **added / clarified**, not rewritten
  * No code, no schema changes
  * No cross-file edits

---

# ✅ Refactored `plans.md`

*(Full replacement — authoritative version)*

---

# Admissions Implementation Plan

**Ifitwala_Ed — Execution Roadmap (Locked v1)**

> This plan operationalizes the **Admissions Canonical Contract (ACC)**.
> It is intentionally **boring, staged, and restrictive**.
>
> Any implementation that shortcuts this plan will create data debt.

---

## 0. Governing Principles (Non-Negotiable)

Before any code:

1. **Inquiry ≠ Applicant ≠ Student**
2. **Promotion is the only creation path for Student**
3. **Admissions is communication-first, not form-first**
4. **All state transitions are server-owned**
5. **UI is convenience — never authority**

This plan assumes:

* `Inquiry` is already operational
* `Student Applicant` exists but is still maturing
* No portal UX is relied upon for correctness

---

## Phase 0 — Governance & Freeze (NO CODE)

**Objective:** Eliminate architectural drift before scaling.

### Actions

* Lock **Admissions Canonical Contract**
* Lock **Student Applicant contract**
* Share with all agents / contributors
* Reject any PR that:

  * Creates Students implicitly
  * Adds Applicant logic to Student
  * Skips Applicant lifecycle stages

### Exit Criteria

* ACC referenced by agents
* No parallel “shortcut” implementations

---

## Phase 1 — Pipeline Wiring (Structural Truth)

**Objective:** Make the admissions pipeline *real and enforceable*, even with empty data.

### What this phase does

* Establishes **legal boundaries**
* Makes misuse **impossible**
* Accepts that Applicant has little data at first

### Deliverables

#### 1. Inquiry → Applicant Invitation

* Explicit server-side `invite_to_apply`
* One Inquiry → max one Applicant
* Fully auditable
* Idempotent

#### 2. Student Applicant Lifecycle Enforcement

* Canonical status set enforced server-side
* Status transitions validated
* Editability locked by status + role
* Applicant becomes a real staging container

#### 3. Promotion Stub (Applicant → Student)

* Explicit `promote_to_student`
* Minimal Student creation
* Applicant permanently locked
* No satellites, no enrollment, no billing

#### 4. Safety & Permissions

* Only Admissions roles can mutate pipeline
* No background job or web form creates Students
* All transitions leave an audit trail

### Explicitly excluded

* Applicant sub-domains
* Portal UX
* Interviews
* Health, documents, guardians
* Automation polish

### Exit Criteria

* A Student **cannot exist** without Applicant
* A rejected Applicant leaves **no residue**
* Pipeline cannot be bypassed

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

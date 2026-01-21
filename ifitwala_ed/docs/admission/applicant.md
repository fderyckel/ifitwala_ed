# ✅ Refactored `applicant.md`

*(This is the full updated document — intended to replace the existing one verbatim)*

---

# Student Applicant — Canonical Admissions Staging Contract

**Ifitwala_Ed — v1 (Authoritative, Living Document)**

> A *Student Applicant* is **not** a student, **not** an inquiry, and **not** a form submission.
> It is a **controlled staging container** that accumulates admissions data and human judgment
> **until** an explicit institutional decision is made.

This document defines the **non-negotiable role** of the Student Applicant in the admissions pipeline.
If implementation contradicts this document, **the implementation is wrong**.

---

## 1. Position in the Admissions Pipeline

The admissions pipeline has **three distinct objects**, each with a different legal and operational role:

```
Inquiry → Student Applicant → Student
```

### 1.1 Inquiry (Triage Object)

* Captures *intent* and *initial contact*
* Operational, discardable
* No legal authority
* May or may not result in an Applicant

### 1.2 Student Applicant (Staging Container)

* Sole container for **all pre-student data**
* Accumulates information, documents, interviews, and review outcomes
* Mutable **until locked**
* May be rejected or archived without polluting canonical student records

### 1.3 Student (Canonical Record)

* Created **only** by promotion
* Permanent, auditable, institutional truth
* Admissions logic does **not** live here

**Invariant**

> A Student **cannot exist** without having been a Student Applicant first.

---

## 2. Core Responsibilities of Student Applicant

The Student Applicant exists to do **exactly four things**:

1. **Aggregate** admissions data (directly or via Applicant-scoped sub-records)
2. **Control editability** based on lifecycle state
3. **Support human review and judgment**
4. **Gate promotion** into the canonical Student record

It must **never**:

* Behave like a lightweight form
* Auto-create students
* Bypass review via automation
* Leak data into Student or Student Patient prematurely

---

## 3. Canonical Fields & Identity

At minimum, a Student Applicant contains:

* Identity (name fields)
* Optional link to originating **Inquiry**
* Target **Program**
* Target **Academic Year / Term**
* `application_status` (lifecycle control)
* Optional applicant image

The Applicant **may exist without an Inquiry**
(e.g. walk-ins, internal referrals, manual entry).

**Invariant**

> The Inquiry ↔ Applicant relationship is optional, one-directional, and immutable once set.

---

## 4. Application Status — Lifecycle Authority

`application_status` is **not cosmetic**.
It is the **primary enforcement mechanism** for permissions, editability, and promotion.

### 4.1 Canonical Status Set

The only allowed statuses are:

```
Draft
Invited
In Progress
Submitted
Under Review
Missing Info
Approved
Rejected
Promoted
```

Any other value is invalid.

---

### 4.2 Status Semantics (Behavioral Truth)

| Status       | Family Edit | Staff Edit | Meaning                            |
| ------------ | ----------- | ---------- | ---------------------------------- |
| Draft        | ❌           | ✅          | Internal draft, not yet shared     |
| Invited      | ✅           | ✅          | Family invited, access granted     |
| In Progress  | ✅           | ✅          | Family actively filling data       |
| Submitted    | ❌           | ✅          | Family finished; staff review only |
| Under Review | ❌           | ✅          | Formal admissions review           |
| Missing Info | ✅ (scoped)  | ✅          | Limited family edits requested     |
| Approved     | ❌           | ✅          | Decision made; promotion allowed   |
| Rejected     | ❌           | ❌          | Terminal, read-only                |
| Promoted     | ❌           | ❌          | Terminal; Student exists           |

**Rules**

* Status changes are **server-controlled**
* Invalid transitions must hard-fail
* UI read-only flags are *not* enforcement

---

## 5. Editability Is a Server-Side Invariant

Edit permissions are determined by:

* `application_status`
* User role (Admissions staff vs family)

**Invariant**

> No user may modify an Applicant if the status disallows it,
> even if the UI is bypassed.

This prevents:

* Late edits after submission
* Silent data drift during review
* Post-decision tampering

---

## 6. Applicant Sub-Domains (Conceptual, Not Yet Implemented)

The Student Applicant is designed to host **satellite Applicant-scoped records**, including:

### Mandatory (v1+)

* Applicant Guardians
* Applicant Academic Background
* Applicant Health Profile
* Applicant Policy Acknowledgements
* Applicant Documents

### Optional / Contextual

* Applicant Interviews
* Applicant Language Profile
* Applicant Logistics
* Applicant Financial Responsibility

**Invariant**

> Applicant sub-domains belong to the Applicant —
> never directly to Student or Student Patient.

---

## 7. Applicant Interview (Architectural Requirement)

Applicant Interview is a **first-class admissions artifact**.

* Staff-only
* Informational, never decisive
* Multiple per Applicant
* Never copied to Student by default

Interviews exist to **inform judgment**, not automate decisions.

---

## 8. Promotion Boundary (Applicant → Student)

Promotion is the **only legal path** to Student creation.

### 8.1 Preconditions

* `application_status = Approved`
* Required Applicant data complete (school-defined)
* Required policies acknowledged

### 8.2 Promotion Effects

* Create Student
* Link Student ↔ Applicant
* Lock Applicant permanently
* Record promotion metadata (who / when)

### 8.3 Explicit Non-Effects

Promotion does **not** automatically:

* Enroll programs
* Create billing records
* Copy interviews
* Copy rejected documents

**Invariants**

> Promotion is explicit
> Promotion is idempotent
> Promotion is irreversible

---

## 9. Design Prohibitions (Hard Rules)

The system must **never**:

* Merge Student Applicant and Student
* Allow family edits post-approval
* Create Student implicitly
* Treat interviews as decisions
* Write Applicant data directly into Student Patient
* Auto-enroll from Applicant intent

Violations are **architecture bugs**, not feature gaps.

---

## 10. Why This Structure Exists

This model exists to support:

* Legal defensibility
* Multi-round review
* Partial submissions
* Rejections without data pollution
* Auditable admissions decisions
* Future re-applications

Without schema rewrites.

---

## 11. Canonical Summary

> Inquiry filters
> Applicant accumulates
> Interviews inform
> Promotion converts
> Student operates

Everything else is implementation detail.

---


## 12. Institutional Scope & Authority (Multi-School Contract)

### 12.1 Applicant Institutional Anchoring

A `Student Applicant` must be **explicitly anchored** to an institutional context.

Each Applicant is associated with:

* exactly one **Organization**
* exactly one **School**

This association:

* is set **once**, at Applicant creation
* is immutable for the lifetime of the Applicant
* is never inferred dynamically at runtime

**Source of truth**

* If created from an Inquiry, `school` and `organization` are inherited
* If created manually, staff must explicitly choose the school

**Invariant**

> An Applicant always “belongs” to one School, even if academic Programs are shared across campuses.

---

### 12.2 Why Program Is Not Sufficient

Programs may be:

* shared across schools
* migrated between schools
* reused across academic structures

Therefore:

> Program affiliation is **not** a substitute for institutional scope.

School anchoring exists to support:

* admissions ownership
* officer specialization
* analytics partitioning
* permission enforcement
* legal accountability

---

### 12.3 Admissions Authority Model (Conceptual)

Admissions authority is **role-based and scope-based**.

* **Admission Officer**

  * operates within a declared scope
  * scope may include:

    * one or more Schools
    * optionally specific Programs
* **Admission Manager / Director**

  * has cross-school visibility within an Organization
  * may override decisions (audited)

**Invariant**

> Visibility, assignment, and dashboards must respect institutional scope — not just role.

---

### 12.4 Applicant Lifecycle Is Global, Requirements Are Local

The Applicant lifecycle (`application_status`) is **globally consistent**.

However:

* validation requirements
* required interviews
* required documents
* approval readiness

may vary **by School**.

These variations must be:

* declarative
* configuration-driven
* evaluated at lifecycle transitions

**Prohibition**

> School-specific rules must not be encoded as conditional logic inside Applicant lifecycle code.

---

### 12.5 Cross-School Oversight Guarantee

Institutional leadership must be able to:

* view Applicants across all Schools
* filter by School / Program
* audit overrides and decisions

This visibility is **explicitly granted**, not emergent.

---

## ✅ Result

After this addition, `applicant.md` now:

* still treats Applicant as a **process container**
* but no longer assumes a single-school world
* formally supports:

  * specialization
  * oversight
  * analytics
  * future scaling

### ✔ Status

This document is now:

* Aligned with the current `Student Applicant` schema
* Aligned with your Inquiry → Applicant → Student pipeline
* Forward-compatible with the gap audit and Phase plans
* Strict enough to prevent future drift

---

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

**System Manager override (exception)**

In terminal states (`Rejected`, `Promoted`), edits are blocked unless a System Manager
performs an explicit override. Overrides must be intentional, audited, and include a
reason. This is a legal escape hatch, not a normal workflow.

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

## 8.4 Transitional Exception — Legacy Students & Institutional Onboarding

The Student Applicant contract governs **steady-state admissions**.
It does **not** invalidate the reality that institutions may enter the system
with **pre-existing enrolled students**.

### 8.4.1 Legacy Student Import (Non-Admissions Context)

When an institution onboards onto Ifitwala_Ed:

* Existing enrolled students **may be imported directly**
* These Students **may not** have a corresponding Student Applicant
* This path exists **only** for migration and onboarding

This exception is:

* explicit
* intentional
* auditable
* non-repeatable in normal operations

**Invariant**

> Direct Student creation without a Student Applicant is permitted
> **only** under an explicit migration or system-level import context.

This exception must never be used to bypass admissions workflow.

---

### 8.4.2 Enforcement Boundary

Outside of a migration or import context:

* Creating a Student **without** a Student Applicant is forbidden
* Any such attempt is a hard architecture violation

Admissions-driven Students must **always** originate from:

```
Student Applicant → Promotion → Student
```

---

### 8.4.3 Audit & Traceability Requirement

All legacy or migration-created Students must be:

* clearly marked as **imported**
* distinguishable from admissions-promoted Students
* traceable to an onboarding or migration event

This ensures:

* legal clarity
* historical accuracy
* protection of admissions analytics

---

### 8.4.4 Prohibition on Retroactive Fabrication

The system must **never**:

* auto-generate Student Applicants for imported Students
* backfill admissions history artificially
* imply that a migrated Student passed through admissions workflow

**Invariant**

> Absence of a Student Applicant for a legacy Student
> is a truthful historical state — not a defect.

---

### 8.4.5 Steady-State Guarantee

Once onboarding is complete:

* the migration exception is disabled
* all new Students must originate from Student Applicant promotion
* no hybrid or ambiguous creation paths exist

This preserves:

* admissions integrity
* legal defensibility
* analytical correctness

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

## 12. Institutional Scope & Authority (Applicability Layer)

> **This section aligns the Student Applicant contract with the
> Phase 1.5 — Multi-School Admissions Governance Contract.**
>
> It does **not** redefine governance.
> It specifies how that governance **applies to the Applicant object**.

If a conflict exists, **Phase 1.5 governance wins** on matters of scope,
authority, and visibility.

---

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

> An Applicant always “belongs” to one School,
> even if academic Programs are shared across campuses.

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

### 12.3 Admissions Authority Model (Alignment)

Admissions authority is **role-based and scope-based**, as defined by Phase 1.5.

* **Admission Officer**

  * operates within an explicitly declared scope
  * scope may include:

    * one or more Schools
    * optionally specific Programs

* **Admission Manager / Director**

  * has cross-school visibility within an Organization
  * may override decisions (audited)

**Invariant**

> Visibility, assignment, and dashboards must respect institutional scope —
> not just role.

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

> School-specific rules must not be encoded as conditional logic
> inside Applicant lifecycle code.

---

### 12.5 Cross-School Oversight Guarantee

Institutional leadership must be able to:

* view Applicants across all Schools
* filter by School / Program
* audit overrides and decisions

This visibility is **explicitly granted**, not emergent.

---

NEW NEW

## 13
---

### **Admissions Boundary Rules (Authoritative)**

These rules define **hard ownership boundaries** between admissions and student records.

#### 1. Canonical owner of admissions files

* All admissions files belong to `Applicant Document`.
* Files must never be attached directly to:

  * `Student Applicant`
  * `Student`

The only exception is:

| Doctype           | Field             | Purpose               |
| ----------------- | ----------------- | --------------------- |
| Student Applicant | `applicant_image` | Identity preview only |

---

#### 2. File lifecycle across promotion

Admissions files **do not migrate**.

Instead:

* Promotion creates **new File records** for Student
* Applicant-side File records are immutable
* No File record is shared across stages

This preserves:

* audit history
* GDPR erasure safety
* legal defensibility

---

#### 3. Folder semantics (normative)

| Stage     | Root Folder                       |
| --------- | --------------------------------- |
| Applicant | `Home/Admissions/Applicant/<ID>/` |
| Student   | `Home/Students/<ID>/`             |

Folders must never overlap across stages.

---

#### 4. Prohibited patterns

The following are architectural violations:

* Re-linking a File record from Applicant to Student
* Attaching admissions files to Student Applicant
* Using shared folders for Applicant and Student
* Mutating Applicant file metadata during promotion

Violations are bugs, not edge cases.

---

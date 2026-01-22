Below is **Phase 1.5 written as a standalone governance contract**.
This is meant to live as its **own markdown file** (e.g. `admissions_governance_phase_1_5.md`) and be **referenced** by `plans.md` and `applicant.md`, not duplicated inside them.

Tone: firm, architectural, non-optional.
Scope: design + authority only (no implementation).

---

# Phase 1.5 — Multi-School Admissions Governance Contract

**Ifitwala_Ed (Authoritative, Design-Level Lock)**

> This document defines the **governance layer** required for admissions to function correctly in a **multi-school, multi-organization ERP**.
>
> It introduces **no new features**, **no UI**, and **no automation**.
>
> Its sole purpose is to **eliminate ambiguity** around scope, authority, visibility, and responsibility **before Phase 2**.

If any implementation contradicts this contract, **the implementation is incorrect**.

---

## 1. Purpose and Timing

### 1.1 Why Phase 1.5 Exists

Phase 1 established the **structural admissions pipeline**:

```
Inquiry → Student Applicant → Student
```

However, that pipeline alone assumes a **single-school operational context**.

In a real ERP:

* Multiple schools coexist under one organization
* Admissions officers specialize
* Directors oversee across schools
* Programs may be shared or migrated
* Analytics must partition cleanly

Phase 1.5 exists to make these realities **explicit and enforceable**.

---

### 1.2 What Phase 1.5 Is (and Is Not)

**Phase 1.5 IS:**

* A governance and authority contract
* A scoping and visibility definition
* A prerequisite for Phase 2+

**Phase 1.5 IS NOT:**

* A feature delivery phase
* A portal phase
* An automation phase
* A schema rewrite mandate

---

## 2. Core Governance Principles

These principles apply to **all admissions objects and workflows**.

### Principle A — Institutional Scope Must Be Explicit

> No admissions object may rely on inferred institutional context.

If an object matters long-term, its **School and Organization must be known explicitly**.

---

### Principle B — Authority Is Scoped, Not Assumed

> Roles alone do not grant access.
> Authority is defined by **role + scope**.

---

### Principle C — Oversight Is a First-Class Concept

> Cross-school visibility is not a side effect — it is an explicit institutional right.

---

### Principle D — Variation Is Declarative

> Differences between schools are expressed as configuration, not procedural logic.

---

## 3. Institutional Anchoring Contract

### 3.1 Mandatory Anchoring

Every **Student Applicant** must be anchored to:

* exactly one **Organization**
* exactly one **School**

This anchoring:

* is set at creation time
* is immutable for the lifetime of the Applicant
* is never reconstructed later via inference

**Source rules**

* From Inquiry → inherited automatically
* Manual creation → explicitly chosen by staff

---

### 3.2 Rationale

Programs:

* may be shared across schools
* may move between schools
* may not represent operational ownership

Therefore:

> Program affiliation is insufficient to determine admissions responsibility.

Institutional anchoring exists to support:

* workload ownership
* officer specialization
* analytics correctness
* legal accountability
* escalation clarity

---

## 4. Admissions Authority Model

### 4.1 Admission Officer Scope

Admission Officers operate within an **explicitly declared scope**.

A scope may include:

* one or more **Schools**
* optionally one or more **Programs**

Scope controls:

* which Applicants are visible
* which Inquiries may be assigned
* which dashboards are populated
* which actions are permitted

**Invariant**

> An Admission Officer cannot see or act on Applicants outside their declared scope.

---

### 4.2 Admission Manager / Director Authority

Admission Managers (Directors) represent **institutional oversight**.

They have:

* cross-school visibility within an Organization
* cross-school mutation rights
* override authority

Overrides must be:

* explicit
* auditable
* traceable to a human decision

**Important**

> This role is not equivalent to System Administrator access.
> It represents institutional authority, not technical privilege.

---

NEW NEW NEW

### **Admissions Data & File Governance**

---

### **Admissions Data & File Governance**

Admissions data is **stage-scoped** and legally bounded.

#### 1. Admissions file authority

Admissions officers and systems may only interact with:

* `Applicant Document`
* Applicant-scoped files

They have **no authority** over Student file structures.

---

#### 2. Promotion as a legal boundary

Promotion marks a **legal data boundary**:

* Before promotion:

  * Files are admissions evidence
  * Subject to Applicant GDPR rules
* After promotion:

  * Files become Student records
  * Subject to Student retention rules

No file may straddle both contexts.

---

#### 3. GDPR accountability

Because Applicant and Student files are distinct records:

* Applicant erasure requests:

  * do not affect Student records
* Student erasure or pseudonymization:

  * does not retroactively alter admissions evidence

This separation is required for compliance.

---

#### 4. Institutional obligation

Any implementation that:

* shares File records across stages
* weakens Applicant erasure guarantees
* blurs admissions vs student ownership

is a **governance violation**, not an optimization.



END OF NEW

---

## 5. Applicant Lifecycle vs Local Requirements

### 5.1 Global Lifecycle (Fixed)

The Applicant lifecycle (`application_status`) is:

* global
* uniform
* consistent across all schools

Lifecycle meaning does **not change** per school.

---

### 5.2 Local Admission Requirements (Variable)

Schools may define local requirements, such as:

* required Applicant sections
* required interviews
* required documents
* readiness rules for approval

These requirements are:

* declarative
* configuration-driven
* evaluated at lifecycle transitions

**Explicit Prohibition**

> School-specific requirements must not be implemented as conditional logic
> inside Applicant lifecycle code.

---

## 6. Visibility, Assignment, and Analytics

### 6.1 Visibility Rules

Visibility of admissions objects is determined by:

```
(role) + (scope) + (institutional anchoring)
```

Never by:

* UI filters alone
* implicit relationships
* human convention

---

### 6.2 Assignment Rules

* Assignment of Inquiries and Applicants must respect officer scope
* Cross-school assignment requires Director authority
* All assignments are auditable

---

### 6.3 Analytics Partitioning

All admissions analytics must support:

* School-level partitioning
* Program-level partitioning
* Officer-level partitioning

Default views are scope-aware.

---

## 7. Cross-Cutting Governance Rules

### Rule 1 — Institutional Context Is Mandatory

> Any admissions object that survives longer than an Inquiry
> must be explicitly scoped to a School and Organization.

This includes:

* Student Applicant
* Applicant Interviews
* Applicant Health
* Applicant Documents
* Decisions

---

### Rule 2 — No Inference Chains

> Institutional context must never be reconstructed from indirect relationships.

If the system must “figure it out”, the model is wrong.

---

### Rule 3 — No Workflow Forking by School

> Schools may differ in requirements, not in core workflow shape.

There is:

* one admissions pipeline
* many configurations
* zero forks

---

## 8. Exit Criteria for Phase 1.5

Phase 1.5 is considered complete when:

* Every Applicant has an explicit institutional home
* Admissions authority is unambiguous
* Officer specialization is enforceable
* Director oversight is guaranteed
* No future phase depends on inference or convention

---

## 9. Relationship to Other Documents

This contract is subordinate only to:

1. System-wide governance principles
2. Security and permission invariants

It is referenced by:

* `applicant.md`
* `plans.md`

If conflicts arise, **this document wins** on matters of scope and authority.

---

## 10. Canonical Summary

> Admissions pipelines define **flow**
> Phase 1.5 defines **ownership**
> Without ownership, flow collapses under scale

---


## Admissions File Boundary (Non-Negotiable)

Admissions files belong exclusively to the Student Applicant.

They are:
- created during admissions
- used to support decision-making
- retained for audit and legal traceability

They are **not**:
- operational student records
- guardian identity records
- portable assets across lifecycle stages

This boundary must be preserved across all phases and implementations.

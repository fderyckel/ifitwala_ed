# Admissions Governance — Multi‑School / Multi‑Org (LOCKED)

> Consolidated from:
> - `/mnt/data/admissions_governance_contract.md`
> - `/mnt/data/phase015.md`
> - `/mnt/data/plans.md` (governance sections only)

> Purpose: lock scope/authority/anchoring rules for Admissions. Remove execution-phase scaffolding; keep design meaning.

Related architecture:
- `docs/enrollment/academic_year_architecture.md`

---


## 0. Authority & non‑drift rule

If anything in implementation contradicts this document, **implementation is wrong**.
This governance note is design‑level; it introduces **no UI**, **no features**, **no automation**.


---


## 1. Canonical pipeline boundary

Admissions pipeline is fixed:

```
Inquiry → Student Applicant → Promotion → Student
```

* Inquiry = triage (discardable)
* Student Applicant = **sole pre‑student container**
* Student = canonical institutional record

A Student **cannot** exist except through Applicant promotion.


---


## 2. Institutional anchoring (mandatory)

Every admissions object with lifecycle meaning (especially **Student Applicant**) must be anchored to:

* `organization`
* `school`

This anchoring is:

* explicit at creation time
* not inferred via Program or Program Offering
* required for permissions, visibility, analytics partitioning, and legal accountability


---


## 3. Full governance contract (verbatim source)


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


---

## 4. Program Offering integration & admissions/enrollment semantic bridge (verbatim source)


# Phase 1.5 — Admissions Governance & Program Offering Integration

> **Status:** Design‑lock phase (no behavioral refactors)
>
> **Position in roadmap:** Between Phase 1 (Applicant → Student pipeline) and Phase 2 (full admissions & enrollment enforcement)
>
> **Purpose:** Close the semantic and governance gap between *Admissions* and *Enrollment* by anchoring decisions to **Program Offering**, while keeping the applicant experience simple and non‑technical.

---

## 1. Why Phase 1.5 exists

Phase 1 successfully established a **hard, enforceable pipeline**:

* Inquiry → Student Applicant → Promotion → Student
* A Student **cannot exist** except through Applicant promotion
* Enrollment logic already operates on **Program Offering**

However, a structural blind spot remained:

> Admissions decisions were still expressed in terms of **Program**, while the system’s operational truth lives in **Program Offering**.

Phase 1.5 exists to **lock governance semantics** *before* additional features (portal, interviews, documents, health, self‑enroll) are added.

This phase introduces **no new workflows**, **no UX expansion**, and **no automatic enforcement yet**.

It clarifies *what is authoritative*, *who can act*, and *what future phases must respect*.

---

## 2. Core principle (locked)

### Programs are conceptual. Program Offerings are contractual.

| Entity               | Nature                    | Purpose                                                                      |
| -------------------- | ------------------------- | ---------------------------------------------------------------------------- |
| **Program**          | Conceptual / curricular   | Describes *what* is taught (IB DP, PYP, STEM Track)                          |
| **Program Offering** | Operational / contractual | Describes *where, when, and under what constraints* the program is delivered |

**Admissions, approvals, capacity, eligibility, and enrollment rules always belong to Program Offering.**

Programs remain visible for clarity, reporting, and applicant comprehension — but **they are not enrollment targets**.

---

## 3. Student Applicant — authoritative targeting model

### Current state (Phase 1)

Student Applicant captures:

* Program
* Academic Year
* Term

This is sufficient for Phase 1, but ambiguous for multi‑school and multi‑offering scenarios.

### Phase 1.5 clarification

* **Program Offering becomes the authoritative enrollment target**
* Program / Academic Year / Term remain **descriptive and transitional**

> Phase 1.5 does **not** yet require `program_offering` — it only establishes that it *exists* and will become mandatory later.

---

## 4. Admissions Officer scope model (locked)

Admissions authority is **multi‑layered**, not mutually exclusive.

An Admissions Officer may be scoped to:

* ✅ Organization‑wide
* ✅ One or more Schools
* ✅ One or more Program Offerings

### Precedence (important)

1. **Program Offering** — decision authority (approve / reject / promote)
2. **School** — operational boundary
3. **Organization** — oversight and override

> Admissions actions ultimately resolve at the **Program Offering level**, even if the UI or role assignment is broader.

---

## 5. Program Offering visibility to applicants (design decision)

Applicants **must not** be exposed to internal architecture.

They should:

* Choose *what they want to apply for*
* Never think about offerings, capacity, rules, or enrollment mechanics

### Design rule (locked)

> Applicants select a **Program intention**.
> The system resolves this to an **eligible Program Offering**.

### Implication

Program Offering must expose a **controlled availability signal** for admissions.

This is **not** self‑enrollment.
It is **admissions discoverability**.

---

## 6. Program Offering — admissions availability toggle (Phase 1.5 design)

### New semantic concept (design‑only)

Program Offering must be able to express:

> “Is this offering currently accepting applicants?”

This is **distinct from**:

* `status = Active`
* `allow_self_enroll`

### Proposed semantics

| Concern                    | Field / Concept                        |
| -------------------------- | -------------------------------------- |
| Operational existence      | `status` (Planned / Active / Archived) |
| Student self‑enrollment    | `allow_self_enroll`                    |
| Admissions discoverability | **Admissions availability flag**       |

This flag:

* Controls whether applicants can *see / choose* the offering
* Does **not** guarantee approval
* Does **not** bypass capacity or rules

> Enforcement will come in Phase 2.

---

## 7. Applicant experience (non‑negotiable UX principle)

Applicants must experience:

* A **smooth, human‑readable choice** (e.g. “IB Diploma Programme – Roots Campus”)
* No exposure to academic years tables, offerings, rules, or capacity

### Behind the scenes

* Applicant selects Program intention
* System filters eligible Program Offerings based on:

  * School context
  * Admissions availability
  * Academic year relevance

The mapping is **system‑owned**, not applicant‑owned.

---

## 8. What Phase 1.5 explicitly does *not* do

To avoid scope creep, Phase 1.5 does **not** include:

* ❌ Mandatory `program_offering` on Applicant
* ❌ Capacity enforcement at admissions stage
* ❌ Enrollment rule execution
* ❌ Interviews, health, documents
* ❌ Applicant portal flows
* ❌ Auto‑assignment logic

Those belong to Phase 2.

---

## 9. Invariants locked by Phase 1.5

From this point onward:

* Admissions decisions are **conceptually bound to Program Offering**
* Any future PR must respect Program Offering as the operational anchor
* Applicant UX must remain abstraction‑safe
* No feature may bypass the Applicant → Student promotion invariant

---

## 10. Exit condition for Phase 1.5

Phase 1.5 is considered **complete** when:

* This document is accepted
* Program Offering is acknowledged as the admissions authority
* Availability semantics are agreed (even if not yet implemented)
* No PR may contradict these rules

> Only after this lock does Phase 2 begin.

---

## 11. Forward reference (Phase 2)

Phase 2 will:

* Make `program_offering` mandatory before approval
* Enforce capacity and enrollment rules
* Integrate admissions availability into portal flows
* Align admissions, enrollment, and scheduling definitively

Phase 1.5 ensures this can happen **without refactors or data breakage**.

---

**This document is authoritative for Phase 1.5.**


---

## 5. Notes on execution documents

The following document remains useful for historical execution ordering, but is **not** authoritative for design semantics:

* `/mnt/data/plans.md`

This governance note intentionally does **not** reproduce the execution roadmap.

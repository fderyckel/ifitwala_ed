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


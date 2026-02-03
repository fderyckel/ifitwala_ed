# enrollment_notes.md

**Authoritative Architecture & Invariants**

**Status:**
**Active – Locked where marked, Living elsewhere**

This document defines the **architecture, invariants, intent, and guardrails** for enrollment and self-enrollment in **Ifitwala_Ed**.

It exists to:

* prevent architectural drift
* guide contributors and coding agents
* preserve institutional auditability

This is **not UI**, **not policy**, and **not marketing**.

If code and this document ever disagree, **this document wins**.

Related architecture:
- `docs/enrollment/academic_year_architecture.md`

---

## 1. Core Definition (Non-Negotiable)

### 1.1 What enrollment is

Enrollment in Ifitwala_Ed is **not a CRUD operation**.

It is a **decision system** that evaluates:

* eligibility (prerequisites, grades, attempts)
* structural constraints (capacity, baskets, offerings)
* human judgment (review, override)
* and produces **committed academic truth**

Any implementation that bypasses this process is **invalid by design**.

---

### 1.2 Guiding principles

Enrollment must be:

* **Curriculum-agnostic**
* **Historically auditable**
* **Explicitly overrideable**
* **Policy-driven, not hard-coded**
* **Reality-anchored**

Automation supports humans — it never replaces institutional judgment.

---

## 2. Layer Separation (Locked)

Enrollment logic is only correct when these layers remain isolated:

| Layer              | Responsibility                      |
| ------------------ | ----------------------------------- |
| Course / Activity  | Catalog (what exists)               |
| Program            | Academic intent & structure         |
| Program Offering   | What is available now               |
| Enrollment Request | What someone is asking for          |
| Validation Engine  | Eligibility & constraint evaluation |
| Program Enrollment | Committed academic truth            |
| Course Term Result | Outcome evidence                    |

Any leakage across layers is a **design regression**.

---

## 3. Enrollment Entry Points

### 3.1 Portal (Students & Guardians)

Portal users **never** write to `Program Enrollment`.

They create **Enrollment Requests** that:

* collect a basket
* run validation
* wait for approval or override
* materialize only when approved

This applies to:

* academic courses
* activities
* pathway selections

---

### 3.2 Staff Actions

Staff may:

* create Enrollment Requests on behalf of users
* approve, reject, or override requests
* create Program Enrollments directly **only with explicit provenance**

Bypassing validation without an override is forbidden.

---

## 4. Enrollment Request (Staging Object)

### 4.1 Why it is mandatory

Direct mutation of `Program Enrollment` is invalid because:

* baskets are partial
* validation must be transactional
* overrides must be recorded
* audit trails must remain intact

Therefore:

> **Enrollment Requests are the only valid staging mechanism.**

---

### 4.2 Role of the Enrollment Request

An Enrollment Request:

* captures user intent
* holds an uncommitted basket
* stores a **frozen validation snapshot**
* records override decisions
* materializes into Program Enrollment only after approval

---

## 5. Eligibility & Prerequisites Engine

### 5.1 Constraint model (Locked)

Eligibility rules use a **DNF (OR-of-AND)** model:

```
(A AND B AND min_grade(A))
OR (C)
OR (D AND NOT E)
```

This matches real institutional logic without boolean parsing.

All prerequisites are **program-scoped**.
Catalog-level prerequisites **must not exist**.

---

### 5.2 Numeric eligibility truth (Locked)

Eligibility comparisons are **numeric only**.

* `numeric_score` → `numeric_score`
* Float → Float
* Never parse grade labels at runtime

Grade labels exist **only for humans**.

If numeric resolution fails → validation **fails**.

---

### 5.3 Grade scale resolution (Locked)

The system explicitly separates **intent** from **evidence**.

Resolution order (deterministic):

1. `Course Term Result.grade_scale` (evidence)
2. `Course.grade_scale` (override intent)
3. `Program.grade_scale` (baseline intent)
4. otherwise → validation error

Prerequisites **snapshot**:

* `grade_scale_used`
* `min_numeric_score`

No retroactive recomputation is allowed.

---

## 6. Source of Academic Truth

Eligibility may only consult:

* `Program Enrollment`
* `Course Term Result`
* allowed Reporting Cycle states

Eligibility **must never** consult:

* draft assessments
* unreleased tasks
* inferred or transient data

---

## 7. Retakes, Repeats, Attempts (Policy-Driven)

There is no universal rule.

Institutions define:

* which attempts count
* how results are selected
* what constitutes a pass

Enrollment logic **consumes policy** — it does not encode it.

---

## 8. Basket-Level Constraints

Prerequisites answer:

> “Can you take this course?”

Basket rules answer:

> “Is this combination valid?”

Basket rules are:

* offering-scoped
* evaluated on Enrollment Requests
* independent of course-level eligibility

Storage models (both allowed):

* Option A: JSON rules
* Option B: structured child table

No final lock yet.

---

## 9. Capacity Modeling (Locked)

### 9.1 Allocation capacity (choice stage)

Lives on **Program Offering Course**.

Used during request validation.

Must never depend on Student Groups.

---

### 9.2 Delivery capacity (sections)

There is **no Course Section doctype**.

**Student Group is the section.**

Capacity enforced via:

* `Student Group.maximum_size`
* membership limits

Allocation ≠ placement.

---

## 10. Overrides (First-Class)

Overrides are not exceptions.

Every override must record:

* scope
* reason
* approver
* timestamp

Overrides never mutate validation snapshots.

---

## 11. Core System Invariants (Non-Negotiable)

1. **Single Evaluation Service**
   All validation goes through
   `enrollment_engine.evaluate_enrollment_request`.

2. **Transactional Evaluation**
   Validation runs only on submission or explicit revalidation.

3. **Immutable Snapshots**
   Validation results are frozen.

4. **No Retroactive Mutation**
   Rule changes never invalidate past decisions.

5. **Explicit Overrides Only**
   Silent bypasses are forbidden.

6. **Enrollment Is a Legal Act**
   Every enrollment records provenance.

7. **Child Tables Are Passive**
   No logic in child controllers or scripts.

8. **Separation of Concerns**
   Enrollment never computes grades.
   Assessment never decides eligibility.

9. **Forward-Only System**
   Corrections are additive, not mutative.

---

## 12. Known Deferred Problems

* activity age semantics
* course equivalencies
* external credits / transfers
* caching strategy (engine-level)

All are acknowledged, none block current architecture.

---

## 13. Architectural North Star

> **Enrollment in Ifitwala_Ed is a decision system with institutional memory,
> not a form that mutates tables.**

If an institution says *“we do it differently”*:

> **Configure it — don’t rewrite it.**

---

## Final Note

Enrollment is academically, legally, and politically sensitive.

Ifitwala_Ed treats it accordingly.

---

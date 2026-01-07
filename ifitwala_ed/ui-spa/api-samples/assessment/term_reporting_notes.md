# Term Reporting Architecture Notes

> **Status: Authoritative / Locked unless explicitly revised**
>
> This document summarizes the architectural decisions for **End‑of‑Term / Term Results Reporting** in Ifitwala_Ed. It is written for **humans and coding agents**. Any implementation that violates these principles is a regression.
>
> Last updated: 2026-01-07

---

## 1. Core Philosophy

**Term reporting is a controlled snapshot, not a live view.**

* Tasks and gradebooks are *mutable during the term*
* Reports are *immutable representations* of academic truth at a point in time
* Once published, results must be **reproducible, auditable, and stable**

No on‑the‑fly recalculation. No silent drift.

---

## 2. Separation of Concerns (Non‑Negotiable)

| Layer              | Responsibility                                   |
| ------------------ | ------------------------------------------------ |
| Task               | Assessment definitions & delivery intent         |
| Gradebook          | Live aggregation & analytics                     |
| Reporting Cycle    | Temporal + policy control                        |
| Course Term Result | Frozen academic truth                            |
| Term Report        | Presentation only                                |

Presentation logic must never influence calculation. Calculation logic must never leak into rendering.

---

## 3. Reporting Cycle (Controller)

The **Reporting Cycle** defines *when* and *how* academic truth is frozen.

### Scope

A Reporting Cycle is uniquely defined by:

* School
* Academic Year
* Term
* (Optional) Program

It also carries a **human‑readable identity** (`name_label`).

### Temporal Controls

* `task_cutoff_date` — determines which tasks are eligible
* `teacher_edit_open` / `teacher_edit_close` — comment editing window

### Status Lifecycle

```
Draft → Open → Calculated → Locked → Published
```

Meaning:

* **Draft**: configuration only
* **Open**: teachers may write comments
* **Calculated**: results generated from gradebook
* **Locked**: no further edits (except explicit overrides)
* **Published**: student / parent visibility allowed

Skipping states is forbidden.

---

## 4. Course Term Result (Atomic Result)

A **Course Term Result** represents:

> One student × one course × one term × one reporting cycle

This is the **only source of truth** for term grades.

### Intentional Redundancy

Course Term Result intentionally duplicates:

* student
* program enrollment
* program
* academic year
* term
* course
* instructor
* grade scale

This protects reports from future structural changes (enrollment moves, instructor reassignment, etc.).

---

## 5. Grade Calculation Rules

**Source of truth:** Task Outcome (official fields only).

### Source Data

Grades are calculated from:

* **Task Outcome** official fields (score / grade / feedback)
* Filtered by Reporting Cycle scope (school, academic_year, term, program)
* Filtered by cutoff rules using Task Delivery dates
* Filtered by grading_status policy (Released only, or Finalized + Released)

Submissions and contributions are **never** used directly in term aggregation.
Evidence stubs do not affect reporting beyond enabling grading to occur.

### Persisted Values

Each Course Term Result stores:

* numeric_score
* grade_value
* task_counted
* total_weight
* calculated_on
* calculated_by

Once calculated, these values are **never auto‑recomputed**.

---

## 6. Overrides & Moderation

Overrides are a **controlled exception**, not an edit shortcut.

### Rules

* Overrides only allowed if enabled on the Reporting Cycle
* Overrides require:

  * override_grade_value
  * override_reason
  * moderated_by
  * moderated_on
  * is_override = true

Calculated values are **retained** for audit.

---

## 7. Teacher & Advisor Comments

Comment requirements are **policy‑driven**, not per‑field validation hacks.

* Enforced at state transitions (Calculated → Locked, Locked → Published)
* Not enforced on every save

Fields:

* `teacher_comment` — report‑facing
* `internal_note` — never visible to students

---

## 8. Orchestration Layer

All generation, locking, and publishing logic lives in **term_reporting.py**.

This layer:

* Reads Reporting Cycle state
* Queries Task Outcome as the only grading input
* Creates / updates Course Term Results
* Enforces lifecycle rules

No UI logic. No permissions hacks. No side effects.

---

## 9. Configuration as Data

Reporting rules are progressively externalized (JSON / config modules):

* Enables school‑ or program‑specific policies
* Avoids branching logic explosion
* Makes reporting predictable and testable

---

## 10. Explicit Non‑Goals

We deliberately do **not**:

* Tie reports to live gradebook views
* Auto‑recalculate after lock
* Allow silent post‑publish edits
* Mix attendance / behaviour into grading
* Embed layout logic in result storage

---

## 11. One‑Sentence Contract

> **A Reporting Cycle defines when academic truth is frozen; Course Term Results store that truth immutably; everything else is commentary or presentation.**

Any code that violates this sentence is wrong.

---

### Inputs (Read-Only)

Course Term Results are generated from:
- Task Outcome (official fields only)
- Filtered by Reporting Cycle scope + grading_status policy
- Filtered by Reporting Cycle.task_cutoff_date (via Task Delivery dates)

Task-level details (rubrics, marks, feedback) are never embedded here.

This is intentional:
- Tasks may change after reporting
- Reports must not

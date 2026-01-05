# Assessment Architecture Notes

> **Status: Authoritative / Foundational**
>
> This document defines the assessment architecture in Ifitwala_Ed. It explains where criteria, scales, and grading logic come from and how they interact. Written for **humans and coding agents**.

---

## 1. Design Intent

Assessment systems fail when:

* criteria are duplicated per task
* grading logic is inferred at read time
* scales are implicit or hard‑coded

Ifitwala_Ed avoids these failures by enforcing **explicit, layered assessment primitives**.

---

## 2. Core Assessment Primitives

### 2.1 Assessment Category

**Purpose:** Semantic grouping of tasks (e.g. Formative, Summative, Project).

Responsibilities:

* Visual identity (color)
* High‑level flags:

  * is_summative
  * include_in_final

Non‑Responsibilities:

* No grading logic
* No weight computation

Categories describe *what a task is*, not *how it is graded*.

---

### 2.2 Assessment Criteria

**Purpose:** Define *what is being assessed*.

An Assessment Criteria:

* Has a unique identity (name + abbreviation)
* Defines a maximum mark
* Belongs to an optional Course Group
* Contains qualitative descriptors

Criteria are **curriculum artifacts**, not task artifacts.

---

### 2.3 Assessment Criteria Levels

**Purpose:** Describe performance bands for a criterion.

Stored as a child table of Assessment Criteria:

* achievement_level (e.g. 1–8, Emerging → Exemplary)
* level_descriptor (rich qualitative description)

These levels:

* Are used for teacher reference and rubric‑based assessment
* Are not responsible for numeric‑to‑grade conversion

---

## 3. Grade Scale

### 3.1 Grade Scale

**Purpose:** Convert numeric scores into symbolic grades.

A Grade Scale:

* Defines a maximum grade
* Contains ordered Grade Scale Intervals
* Is versionable (amended_from)

Grade Scales are **institutional policy**, not course logic.

---

### 3.2 Grade Scale Interval

Each interval defines:

* grade_code (e.g. A, 7, Distinction)
* boundary_interval (numeric threshold)
* grade_descriptor

Intervals must be:

* Ordered
* Non‑overlapping
* Exhaustive for the scale

---

## 4. Tasks (Assessment Evidence)

Tasks are **assessment events**, not grading rules.

### Supported grading modes (exactly one active)

A Task may operate in **one and only one** grading mode at a time:

1. **Observations** — qualitative feedback only (no grading)
2. **Binary** — complete / incomplete
3. **Points** — numeric score out of max points
4. **Criteria** — rubric‑based assessment using Assessment Criteria

The `is_graded` flag is **derived**, never user‑editable.

---

### Criteria‑based Tasks

When `criteria = 1`:

* The Task references **Assessment Criteria** via *Task Assessment Criteria*
* Each criterion may define:

  * weighting
  * max points
* Per‑student rubric data is stored in **Task Criterion Score**
* Rubric rows are **materialized**, not inferred at read time

Criteria grading is **explicit and irreversible once grading has started**.

---

### Points‑based Tasks

When `points = 1` and `criteria = 0`:

* A single numeric mark is entered per student
* `max_points` defines the denominator
* Percentage is derived and stored
* A **Grade Scale** is resolved from:

  * Task.grade_scale (explicit)
  * else Course.default_grade_scale (implicit)

---

### Task Student (Per‑student Evidence)

The **Task Student** table stores:

* raw marks (points mode)
* completion state (binary mode)
* feedback
* visibility flags

Status (Assigned / Graded / Returned) is **derived**, not manually set.

---

### Guardrails

Tasks explicitly **do not**:

* compute final course grades
* resolve reporting policies
* infer criteria or grade scales implicitly

They provide evidence only.

---

## 5. Gradebook (Live Aggregation)

The Gradebook:

* Aggregates task results per student × course
* Applies weights and inclusion rules
* Produces live numeric summaries

Gradebook output is:

* Mutable
* Time‑sensitive
* Analytical

It is **never** used directly for reports.

---

## 6. Reporting Boundary

At the Reporting Cycle boundary:

* Gradebook values are *read*
* Results are *materialized* into Course Term Results
* Grade Scales are *resolved and frozen*

After this point:

* Tasks may change
* Gradebooks may change
* Reports must not

---

## 7. Where Things Come From (Quick Map)

| Concept                 | Source                     |
| ----------------------- | -------------------------- |
| Criteria definition     | Assessment Criteria        |
| Performance descriptors | Assessment Criteria Levels |
| Numeric → grade mapping | Grade Scale + Intervals    |
| Evidence                | Tasks                      |
| Live aggregation        | Gradebook                  |
| Official result         | Course Term Result         |

---

## 8. Explicit Non‑Goals

We deliberately avoid:

* Per‑task grade scales
* Hidden grading formulas
* Implicit criteria inference
* Auto‑grading without policy

---

## 9. Contract Summary

> **Criteria define what is assessed, scales define how scores are interpreted, tasks provide evidence, gradebooks aggregate live data, and reports freeze institutional truth.**

If a piece of code mixes these responsibilities, it is wrong.

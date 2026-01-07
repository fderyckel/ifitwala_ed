# Assessment Architecture Notes

> **Status: Authoritative / Foundational**
>
> This document defines the assessment architecture in Ifitwala_Ed. It explains where criteria, scales, and grading logic come from and how they interact. Written for **humans and coding agents**.
>
> Last updated: 2026-01-07

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

Tasks define evidence intent; Delivery turns that intent into Outcomes and Submissions.
Task supports multiple criteria via `task_criteria`, and Delivery snapshots those rows for rubric grading.
Delivery applies `rubric_scoring_strategy` (defaulted from Task) to decide whether totals are computed.
Evidence may be offline and is still represented via a **Submission stub**.

### Supported grading modes (exactly one active)

A Task may operate in **one and only one** grading mode at a time:

1. **None** — feedback only (ungraded)
2. **Completion** — complete / incomplete
3. **Binary** — yes / no
4. **Points** — numeric score out of max points
5. **Criteria** — rubric‑based assessment using Assessment Criteria

The grading mode is **explicit**, never inferred at read time.

---

### Criteria‑based Tasks

When `criteria = 1`:

* The Delivery snapshots rubric structure (Task Rubric Version)
* Each criterion may define weighting and max points
* Per‑student rubric marks live in **Task Contributions** (criterion rows)
* Official result rolls up to **Task Outcome**

Criteria grading is **explicit and irreversible once grading has started**.

---

### Points‑based Tasks

When `points = 1` and `criteria = 0`:

* A numeric score is entered via **Task Contributions**
* `max_points` defines the denominator
* Official score is stored on **Task Outcome**
* Grade Scale is resolved at delivery time (policy‑driven)

---

## 4.5 Source of truth / layers

Authoring

* Students author **Task Submission** (evidence only).
* Teachers author **Task Contribution** (+ Task Contribution Criterion rows).

Derived official truth

* **Task Outcome** stores status + optional scalar totals.
* **Task Outcome Criterion** stores per‑criterion official results (always).

Aggregation

* Reporting uses Outcome totals where present, else Outcome Criterion rows.

**Canonical statement:** A Task Outcome always stores official results per criterion. Task totals are optional and only computed when the delivery strategy allows it.

### Per‑student Layers (Outcome / Submission / Contribution)

Assessment evidence is represented by a **three‑layer per‑student model**:

* **Outcome** — official fact table (score / grade / feedback + statuses)
* **Submission** — versioned evidence (files / text / links)
* **Contribution** — teacher judgment inputs (scores, rubric marks, moderation)

Delivery provides context; Outcome is the official record; Submissions carry evidence.
Evidence may be offline and still be represented via a **Submission stub**.

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

# Ifitwala_Ed — Task & Assessment Architecture (Authoritative)

Status: **ARCHITECTURE LOCK — v2 (LMS‑ready)**
Scope: Tasks, Delivery, Outcomes, Submissions, Grading, Review & Moderation
Audience: Humans + Coding Agents
Last updated: 2026-01-07

This document defines the **end‑state architecture** for Tasks in Ifitwala_Ed.
It explicitly incorporates LMS‑scale realities (high volume, low friction) and replaces earlier Task‑centric designs.

Any implementation that violates these principles is a **regression**.

---

## 0. Design Intent (Reality‑First)

In a real school:

* ~1,000 students
* ~2–3 tasks per student per day
* **Most tasks are not assessed** (homework, classwork, reading, practice)
* Many tasks only require *tracking or collection*, not grading
* A smaller subset are formally assessed (points or criteria)
* Team teaching and informal peer review are common
* Formal moderation exists but is rare and policy‑driven

Therefore:

> **First-principle statement**

A Task is not curriculum.
A Task is an artifact used during teaching to produce evidence.

> **Assessment is a mode, not the identity of a task.**

If the system treats every task as an assessment, the gradebook becomes unusable and teachers disengage.

---

## 1. Core Principle (Non‑Negotiable)

### Task ≠ Delivery ≠ Outcome ≠ Submission ≠ Contribution

Each concept exists to protect:

* performance
* cognitive simplicity
* auditability
* UX clarity

Teachers must experience **one seamless grading surface**.
Developers may maintain a multi‑layer backend.

The UI *must never* expose backend complexity.

---

## 1.1 Multi-criteria tasks (locked)

* Task supports multiple Assessment Criteria via `Task.task_criteria` (child table Task Template Criterion). No single default rubric link exists anymore.
* Task stores default scoring strategy in `default_rubric_scoring_strategy`:

  * Sum Total
  * Separate Criteria

**Canonical statement:** A Task Outcome always stores official results per criterion. Task totals are optional and only computed when the delivery strategy allows it.

---

## 1.2 Rubric scoring strategy (locked)

* Strategy is evaluated from Task Delivery (`rubric_scoring_strategy`).
* Delivery snapshots the strategy from Task at creation time (historical stability).
* Strategy determines whether a task-level total is produced:

  * Sum Total: total score is computed on outcome, mapped to grade scale.
  * Separate Criteria: no task total; only per-criterion official results exist.

---

## 2. Five‑Layer Model (Locked)

### Layer 1 — Task (Definition / Library Item)

**Purpose:** Reusable instructional intent.

Holds:

* title, description, instructions
* attachments / resources
* `task_kind`: Work Item | Assessment
* optional `course` (library tagging)
* assessment potential (grading mode, rubric ref, max points)

Does NOT hold:

* student groups
* dates
* submissions
* grades

Tasks may be reused, refined, duplicated, or versioned over time.

---

### Layer 2 — Task Delivery (Audience & Timing)

**Purpose:** Who gets the task, when, and how.

Holds:

* task
* student_group (authoritative context)
* **course / academic_year / school (denormalized, read‑only)**
* delivery_mode:

  * Assign Only
  * Collect Work
  * Assess
* dates (available, due, lock)
* group_submission policy

**Lazy creation rule:**

* Outcomes are created on submit
* No per‑student rows before delivery

---

### Layer 3 — Task Outcome (Official Fact Table)

**Purpose:** Single source of truth per student.

One row per:

```
(Task Delivery × Student)
```

Holds:

* submission_status
* grading_status
* procedural_status (Excused, Absent, Extension, Dishonesty)
* official score / grade / feedback
* **school, academic_year, course, program (denormalized)**

Invariant:

> **Exactly one official outcome exists per student per delivery.**

> **Task Outcome stores grades as (symbol + numeric value), validated against the Grade Scale active at delivery time.  Grade Scale Intervals are never linked directly; they are interpreted, not referenced.**

---

### Layer 4 — Task Submission (Student Evidence)

**Purpose:** Versioned evidence container.

Holds:

* outcome
* version
* attachments / text / links
* submitted_at
* submitted_by
* optional `group_submission_id`

Resubmission creates a new version.

#### Evidence Stub (Teacher / Offline / No Upload)

Task Submission is the evidence anchor even when evidence is offline.
When a teacher grades without a digital upload, the system auto‑creates a new Task Submission version as a stub:

* `is_stub = 1`
* optional `evidence_note` (e.g., “Paper collected in class”)
* no score / grade / feedback stored here

Evidence stubs are required for:

* paper homework collected
* in‑class written tasks
* oral presentations
* teacher observation

Evidence stub ≠ “new student evidence.”
`has_new_submission` is reserved for student resubmits only.

---

### Layer 5 — Task Contribution (Teacher Grading / Review)

**Purpose:** Non‑destructive grading inputs.

Holds:

* outcome
* submission (explicit version link)
* contributor (teacher)
* contribution_type (Self, Review, Moderation)
* score / rubric scores / feedback
* is_stale flag

Contributions never overwrite each other.

---

## 3. Delivery Modes (Google Classroom Parity)

### Assign Only

* no submission required
* optional completion check
* excluded from gradebook

### Collect Work

* submission required
* feedback optional
* no grades unless explicitly switched to Assess

### Assess

* graded (points or criteria)
* appears in gradebook and analytics
* allows grading without a student upload via evidence stub

Invariant:

> **Not assessed ≠ Missing grade.**

---

## 4. Group Submission (Resolved)

### Adopted Model: Clone + Group ID

When group submission is enabled:

* First uploader submits once
* Backend clones submissions for all group members
* All clones share `group_submission_id`
* Each outcome retains 1:1 submission linkage

Why:

* simple queries
* independent grading later
* no conditional joins

UI rule:

* Non‑uploading students see: “Submitted by {Student A} on behalf of group”

Resubmission policy is explicit and configurable.

---

## 5. Multi‑Teacher Grading (No Overwrites)

### Contributions, not collisions

* Each teacher grades independently
* System highlights differences
* One **official outcome** is finalized

This supports:

* team teaching
* sanity checks
* audit trails

---

## 6. Review vs Moderation (Clarified)

### Peer Review (Default)

* teacher‑initiated
* lightweight
* no release gate

### Formal Moderation (Policy‑Driven)

* role‑gated
* release blocked until resolved
* moderator may:

  * approve
  * adjust
  * return to grader (with note)

Same engine, different rules.

---

## 7. Staleness & Resubmissions

* Contributions are tied to a submission version
* **Student** resubmission ⇒ existing contributions flagged `is_stale`
* **Teacher‑created evidence stubs** do **not** stale contributions by default

UX must show:

* “New evidence available” badge

Policy toggle:

* reset grading status
* or flag only

---

## 8. Rubric Integrity

* Rubric structure is snapshotted at delivery (all Task criteria rows)
* Descriptor text governance:

  * minor edits allowed
  * major semantic edits require duplication

Historical meaning must be preserved.

---

## 9. Performance Strategy

### Gradebook Rule

The gradebook grid must render from **Task Outcome** plus **Task Outcome Criterion** (Outcome layer truth only).

* no deep joins
* denormalized context fields
* batched lookups for names

### Query Surfaces

* Assign Only → feed / agenda
* Collect Work → submission tracking
* Assess → gradebook & analytics

---

## 10. UX Contract (Non‑Negotiable)

### One Surface for Teachers

Teachers must:

* open the gradebook
* click a cell
* grade, review, finalize, release

They must **never** navigate between doctypes.

---

### Grading Drawer

Default tab:

* My Contribution (editable)

Secondary:

* Official Outcome (read‑only)
* Compare / History (diff‑only)
* Review / Moderation (role‑gated)

No spreadsheets. Differences only.

---

## 11. Final Contract

1. Tasks are learning items
2. Assessment is a mode
3. One official outcome per student
4. Multi‑teacher grading via contributions
5. Moderation is policy‑driven
6. Finalization ≠ Release
7. Backend may be complex
8. **Teacher UX must be effortless**

---

# Expected Behavior Matrix — Step 2
## Outcome recompute / Official truth (Authoritative)

This matrix defines the **non-negotiable expected behavior** of the Outcome recompute pipeline.
It is written for **humans and coding agents**. Any deviation is a regression.

---

## Definitions (locked)

### Winning contribution selection (priority order)
1. `contribution_type = Moderator`
2. else `contribution_type = Official Override`
3. else `contribution_type = Self`

Exclude any contribution where:
- `status = Draft`, or
- `is_stale = 1`

### Official truth writers
Only:

apply_official_outcome_from_contributions(outcome_id)

may write:
- `Task Outcome.official_*`
- `Task Outcome.official_criteria` (Task Outcome Criterion rows)

No controllers, reports, or UI code may write official fields.

### Student evidence vs stub
- **Student evidence** (Student Upload / Student In-Class):
  - may set `has_new_submission = 1`
- **Teacher stubs** (`is_stub = 1`, origin Teacher Observation / System):
  - must **never** set `has_new_submission = 1`

### Criteria-first invariant
When `grading_mode == "Criteria"`:
- Per-criterion official truth is **always materialized**
- Task-level totals/grade are **strategy-gated**

---

## A) Recompute entry behavior (always)

| Condition | Expected behavior |
|---|---|
| Recompute called for valid outcome | Load delivery context: `grading_mode`, `rubric_scoring_strategy`, `grade_scale`, `rubric_version`, `require_grading`. |
| No eligible contributions | Clear official fields; clear official criteria (if Criteria mode); set `grading_status` (see section D). |
| Winning contribution exists | Apply official criteria **first**, then strategy-gated totals/grade, then grading_status. |
| Moderator action = “Return to Grader” | Do **not** overwrite official fields or criteria; set `grading_status = "In Progress"`; return early. |

---

## B) Criteria mode — official criteria behavior (always)

Applies when:

Task Delivery.grading_mode == "Criteria"

yaml
Copy code

| Condition | Task Outcome Criterion behavior |
|---|---|
| Winning contribution exists | Replace entire child table to exactly match the winning contribution’s criterion rows. |
| No winning contribution | Child table must be empty (no stale rows allowed). |
| Moderator “Return to Grader” | Do not change existing official criteria. |

### Row mapping (locked)

Each Task Outcome Criterion row must contain:
- `assessment_criteria`
- `level`
- `level_points`
- `feedback`

Source: **winning Task Contribution Criterion rows only**.

---

## C) Criteria mode — strategy-gated totals and grade

### C1 — Strategy = `Separate Criteria`

Applies when:

Task Delivery.rubric_scoring_strategy == "Separate Criteria"


| Field | Expected value |
|---|---|
| `official_score` | **NULL** (never 0) |
| `official_grade` | **NULL** |
| `official_grade_value` | **NULL** |
| `official_feedback` | Allowed |
| `official_criteria` | Always refreshed from winning contribution |

**Reason:**
Prevents analytics pollution and enforces per-criterion truth.

---

### C2 — Strategy = `Sum Total`

Applies when:

Task Delivery.rubric_scoring_strategy == "Sum Total"


| Field | Expected value |
|---|---|
| `official_score` | Computed numeric total (weighted if weights exist) |
| `official_grade` | Resolved grade symbol (via grade scale) |
| `official_grade_value` | Resolved numeric value (via grade scale mapping) |
| `official_feedback` | Allowed |
| `official_criteria` | Always refreshed from winning contribution |

**Notes (locked):**
- Grade resolution is **computed**, not linked to a child row.
- If no grade scale exists, grade fields must remain NULL.

---

## D) Grading status outcomes (minimum policy)

### D1 — No eligible contribution

| Condition | grading_status |
|---|---|
| `require_grading = 0` | `Not Applicable` |
| `require_grading = 1` | `Not Started` |

(If Criteria mode: official criteria must be empty.)

---

### D2 — Winning contribution exists

| Contribution type | grading_status |
|---|---|
| Self | `Finalized` |
| Official Override | `Finalized` |
| Moderator | `Moderated` |

---

### D3 — Moderator “Return to Grader”

| Condition | grading_status |
|---|---|
| Moderator + Return to Grader | `In Progress` (do not overwrite official truth) |

---

## E) Submission + flags behavior (must not drift)

### E1 — Stub grading (no student submission)

| Condition | Expected behavior |
|---|---|
| Grading without submission id | Create/ensure stub `Task Submission`; attach contribution to it. |
| Stub exists | `has_submission = 1` |
| Stub exists | **Do not** set `has_new_submission = 1` |

---

### E2 — Student evidence

| Condition | Expected behavior |
|---|---|
| First student submission | `has_submission = 1`, `has_new_submission = 1` |
| Student resubmission | New version; `has_new_submission = 1`; prior contributions may become stale (policy-controlled). |

**Hard rule:**
`has_new_submission` is reserved **only** for student-originated evidence.

---

## F) Official field write permissions (enforced invariant)

| Data | Writable by |
|---|---|
| `official_score`, `official_grade`, `official_grade_value`, `official_feedback` | `apply_official_outcome_from_contributions()` only |
| `official_criteria` | `apply_official_outcome_from_contributions()` only |
| Contributions | Contribution service |
| Submissions | Submission service |

Any other codepath writing official fields is a **regression**.

---

## Status

This matrix is **authoritative** for Step 2.
UI, analytics, and reporting **must trust Outcome + Outcome Criterion only**.

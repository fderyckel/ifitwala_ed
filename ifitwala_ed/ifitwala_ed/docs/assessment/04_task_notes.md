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
When a teacher grades without a digital upload and the delivery requires a submission, the system auto‑creates a new Task Submission version as a stub:

* `is_stub = 1`
* optional `evidence_note` (e.g., “Paper collected in class”)
* no score / grade / feedback stored here

Evidence stubs are used for:

* paper homework collected
* in‑class written tasks
* oral presentations
* teacher observation

Evidence stub ≠ “new student evidence.”
`has_new_submission` is reserved for student-originated submissions (first or resubmit).

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
* instructor scope is limited to taught student groups (cannot broaden via filters)

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
  - sets `has_new_submission = 1` on any new submission
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
| Grading without submission id, requires_submission = 1 | Create/ensure stub `Task Submission`; attach contribution to it. |
| Grading without submission id, requires_submission = 0 | Allow contribution without a submission; do not create stub. |
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

---

## Architecture lock notes

- Official truth is internal (Task Outcome.official_* and Task Outcome Criterion). It is computed via the truth pipeline and is not automatically visible to students/guardians.
- Teacher submit/moderation updates official truth; draft does not.

**A Task Outcome is the per-student truth for a Task Delivery; evidence is versioned as Task Submission; assessment actions are Task Contributions; official outcome truth is derived from the highest-priority non-stale contribution (Moderator > Official Override > Assessor/Self), and criteria truth is always stored per-criterion with totals only when strategy permits; peer moderation is never official.**

---

## Task & Assessment System — Complete Case Grid (Submission + Grading + Moderation)

### Fixed definitions (non-negotiable)

* **Task Delivery** defines rules: `requires_submission`, `require_grading`, `grading_mode`, `rubric_scoring_strategy`, lock/due rules.
* **Task Outcome** is the per-student operational truth for a delivery.
* **Task Submission** is **versioned evidence** (append-only; v1, v2…).
* **Task Contribution** is an assessment action (scoring/grade/feedback/rubric rows), normally tied to a submission version.
* **Moderation (Peer Review)** is **never official**: it is stored but cannot become the official outcome truth.
* **Moderator** contribution can override and becomes official selection priority.
* **Official truth storage rule**:

  * For **Criteria grading**: **per-criterion official truth is always stored** (Task Outcome Criterion).
  * **Totals/grade are optional** and depend on `rubric_scoring_strategy`:

    * **Sum Total** → totals may exist
    * **Separate Criteria** → totals should be blank

---

## Delivery configuration grid (what the system supports)

### A. Ungraded deliveries (feedback-only)

| ID | requires_submission | require_grading | delivery_mode | grading_mode  | What’s allowed                               | Official truth written                                      |
| -- | ------------------: | --------------: | ------------- | ------------- | -------------------------------------------- | ----------------------------------------------------------- |
| U1 |                   0 |               0 | Assign Only   | (any/ignored) | Feedback contributions only                  | Outcome may track `is_complete` (if used); no grades/scores |
| U2 |                   1 |               0 | Collect Work  | (any/ignored) | Submission evidence + feedback contributions | Outcome: submission flags + `official_feedback` only        |

**Notes**

* These cases exist for work collection and formative feedback without scoring.
* Submission is still versioned when required.

---

### B. Graded deliveries with **submission required**

| ID | requires_submission | require_grading | grading_mode | rubric_scoring_strategy | Student action      | Teacher action                                     | Official truth written                                                  |
| -- | ------------------: | --------------: | ------------ | ----------------------- | ------------------- | -------------------------------------------------- | ----------------------------------------------------------------------- |
| G1 |                   1 |               1 | Points       | n/a                     | Submit evidence v1+ | Score contribution tied to latest submission       | Outcome `official_score` (+ optional feedback)                          |
| G2 |                   1 |               1 | Grade        | n/a                     | Submit evidence v1+ | Grade contribution tied to latest submission       | Outcome `official_grade`, `official_grade_value` (+ feedback)           |
| G3 |                   1 |               1 | Criteria     | Sum Total               | Submit evidence v1+ | Rubric rows contribution tied to latest submission | Outcome `official_criteria` + totals (`official_score` and maybe grade) |
| G4 |                   1 |               1 | Criteria     | Separate Criteria       | Submit evidence v1+ | Rubric rows contribution tied to latest submission | Outcome `official_criteria` only (+ feedback); totals blank             |

**Notes**

* When a new submission arrives after grading started, the outcome becomes **stale** and prior contributions become stale.

---

### C. Graded deliveries with **submission NOT required** (teacher observation / oral / in-class)

| ID | requires_submission | require_grading | grading_mode | rubric_scoring_strategy | Student action | Teacher action                                       | Official truth written                           |
| -- | ------------------: | --------------: | ------------ | ----------------------- | -------------- | ---------------------------------------------------- | ------------------------------------------------ |
| O1 |                   0 |               1 | Points       | n/a                     | None           | Score contribution (may attach stub evidence record) | Outcome `official_score` (+ feedback)            |
| O2 |                   0 |               1 | Grade        | n/a                     | None           | Grade contribution                                   | Outcome `official_grade`, `official_grade_value` |
| O3 |                   0 |               1 | Criteria     | Sum Total               | None           | Rubric rows contribution                             | Outcome `official_criteria` + totals             |
| O4 |                   0 |               1 | Criteria     | Separate Criteria       | None           | Rubric rows contribution                             | Outcome `official_criteria` only; totals blank   |

**Notes**

* Evidence can be represented by a **stub submission** for audit linkage, but the delivery does not require student evidence.

---

## Evidence / submission grid (versioning + flags)

### A. Evidence creation modes

| Evidence origin     | Mechanism                                   | Creates Task Submission? | Typical usage                    |
| ------------------- | ------------------------------------------- | -----------------------: | -------------------------------- |
| Student Upload      | student submits via portal                  |               Yes (real) | attachments/link/text            |
| Student In-Class    | student submits in class (teacher-assisted) |               Yes (real) | quick capture                    |
| Teacher Observation | teacher records evidence note               |               Often stub | grading without student upload   |
| System              | system generates                            |                    Maybe | imported evidence / placeholders |

### B. Submission version lifecycle

| Case                          | Trigger                             | Task Submission version | Append-only enforced | Outcome flags                                                                  |
| ----------------------------- | ----------------------------------- | ----------------------: | -------------------: | ------------------------------------------------------------------------------ |
| S1 First submission           | student uploads                     |                      v1 |                  Yes | `has_submission=1`, `has_new_submission=1`, `submission_status=Submitted/Late` |
| S2 Resubmission               | student uploads again               |                     v2+ |                  Yes | `has_new_submission=1`, `submission_status=Resubmitted/Late`                   |
| S3 No student submission ever | delivery doesn’t require submission |            none or stub |                  n/a | still can be graded                                                            |
| S4 Teacher stub               | teacher grades without evidence     |         stub submission |                  Yes | does **not** imply student evidence; used for linkage/audit                    |

### C. Locking / lateness (submission gate)

| Condition                                              | Effect on submission creation                    |
| ------------------------------------------------------ | ------------------------------------------------ |
| `lock_date` passed and no extension + late not allowed | block new submission                             |
| `due_date` passed and no extension                     | allow submission but mark `is_late=1` if allowed |
| `procedural_status = Extension Granted`                | bypass lateness / lock logic as defined          |

---

## Contribution grid (who can write what)

### A. Contribution types and meaning

| contribution_type | Meaning                                                       | Can be official truth? | Priority in selection |
| ----------------- | ------------------------------------------------------------- | ---------------------: | --------------------- |
| Self              | assessor’s grading action (not student self-assessment label) |                    Yes | below Moderator       |
| Peer Review       | moderation check by peer teacher                              |                 **No** | never selected        |
| Moderator         | moderation action (approve/adjust/return)                     |                    Yes | highest               |
| Official Override | admin/system forced override                                  |                    Yes | below Moderator       |

> Naming note: if you want to eliminate confusion later, “Self” could be renamed to **Assessor**. But the rules above are the truth regardless of labels.

### B. Contribution payload constraints by grading mode

| grading_mode | Required in contribution         | Forbidden / irrelevant                                                       |
| ------------ | -------------------------------- | ---------------------------------------------------------------------------- |
| Points       | `score`                          | rubric rows required; grade optional depending on policy (usually forbidden) |
| Grade        | `grade` (mapped via grade scale) | score optional depending on policy (usually forbidden)                       |
| Criteria     | `rubric_scores` rows required    | score/grade may be derived only when strategy is Sum Total                   |
| Ungraded     | only `feedback`                  | score/grade/rubric rows forbidden                                            |

### C. Submission linkage rules

| Delivery requires_submission | Contribution must reference Task Submission? | How handled                                             |
| ---------------------------: | -------------------------------------------: | ------------------------------------------------------- |
|                            1 |                                          Yes | must reference the **latest submission version**        |
|                            0 |                                           No | may reference none, or a **stub** can be used for audit |

---

## Official truth computation grid (Outcome resolution)

### A. Official selection priority

| Available contributions for outcome                      | Selected official contribution |
| -------------------------------------------------------- | ------------------------------ |
| Any Moderator contribution exists (not stale, not draft) | latest Moderator               |
| Else any Official Override exists                        | latest Official Override       |
| Else any Self exists                                     | latest Self                    |
| Peer Review only                                         | **none** (no official truth)   |

### B. Criteria strategy effects

| rubric_scoring_strategy | Outcome official_criteria | Outcome totals / grade                               |
| ----------------------- | ------------------------- | ---------------------------------------------------- |
| Separate Criteria       | always written            | totals blank                                         |
| Sum Total               | always written            | compute total points (+ grade if grade_scale exists) |

### C. Outcome “released” validity rule

| grading_mode      | What qualifies as “official result exists”               |
| ----------------- | -------------------------------------------------------- |
| Criteria          | official_criteria exists (rows) OR feedback (if allowed) |
| Points            | official_score exists                                    |
| Grade             | official_grade exists                                    |
| Completion/Binary | is_complete is set                                       |
| Ungraded          | feedback exists (or completion if used)                  |

---

## Staleness + “new evidence” grid (what flips when)

### A. New submission arrives

| Situation at time of submission | Outcome `has_new_submission` | Outcome `is_stale` |                         Contributions become stale? |
| ------------------------------- | ---------------------------: | -----------------: | --------------------------------------------------: |
| No grading started              |                            1 |                  0 |                                                  no |
| Grading already started         |                            1 |                  1 | yes (all contributions not tied to latest evidence) |

### B. Grading action happens

| Action                       | Outcome status effect                                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------- |
| First contribution submitted | grading_status moves from Not Started → In Progress / Finalized / Moderated depending on type and rules |
| Moderator “Return to Grader” | grading_status forced back to In Progress                                                               |
| Official truth recomputed    | official fields refreshed; publish cleared if it was published                                          |

### C. Teacher stub submission created

| Why                                                            | Outcome flags                                                                                           |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Need an evidence anchor for grading without student submission | outcome shows submitted state for process tracking, but should not be treated as “new student evidence” |

---

##  Procedural overrides grid (status constraints)

| procedural_status   | Allowed submission statuses                  | Allowed official results                              |
| ------------------- | -------------------------------------------- | ----------------------------------------------------- |
| Excused             | not Submitted/Late/Resubmitted               | no score/grade; feedback optional depending on policy |
| Absent              | depends on policy                            | depends on policy                                     |
| Extension Granted   | Submitted/Resubmitted allowed without “Late” | grading allowed                                       |
| Academic Dishonesty | depends on policy                            | may force override/notes                              |

---

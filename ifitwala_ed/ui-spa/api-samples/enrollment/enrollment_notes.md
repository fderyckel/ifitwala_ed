# enrollment_notes.md

## Status

**Draft – Critical Architecture Notes (Authoritative, Living Document)**

This document defines the **intent, constraints, confirmed design decisions, open questions, and identified risks** for enrollment and self-enrollment in Ifitwala_Ed.

It is written for:

* core maintainers
* future contributors
* coding agents (Codex / automation)

This is **not marketing** and **not a UI specification**.
It exists to prevent architectural drift and to ensure that enrollment logic remains **correct, auditable, and institution-agnostic**.

---

## 1. Core Intent (Non-Negotiable)

### 1.1 What enrollment actually means

Enrollment in Ifitwala_Ed is **not a CRUD operation**.

It is a **decision process** involving:

* eligibility checks (prerequisites, grades, pathways)
* structural constraints (capacity, baskets, group requirements)
* institutional judgment (manual review and overrides)
* final materialization into academic truth

Any design that bypasses this process is considered **invalid**.

---

### 1.2 Guiding principles

Ifitwala_Ed enrollment must be:

* **Curriculum-agnostic**
  (IB, AP, BTEC, national curricula, custom pathways)

* **Historically auditable**
  Enrollment decisions must be explainable years later

* **Human-overrideable**
  Institutions may override rules, but must leave evidence

* **Policy-driven, not hard-coded**
  The platform provides tools, not ideology

* **Reality-anchored**
  Matches how schools, colleges, and universities actually operate

---

## 2. Explicit Layer Separation (Critical)

Ifitwala_Ed enforces a strict separation of responsibilities:

| Layer                                | Responsibility                      |
| ------------------------------------ | ----------------------------------- |
| Course / Activity                    | Catalog (what exists)               |
| Program                              | Academic structure and intent       |
| Program Offering / Activity Context  | What is available now               |
| Enrollment Request                   | What a user is asking for           |
| Validation Engine                    | Eligibility & constraint evaluation |
| Program Enrollment                   | Committed academic truth            |
| Course Term Result                   | Outcome evidence                    |

Any leakage across layers is a **design regression**.

---

## 3. Portal Enrollment (Students & Guardians)

### 3.1 Student self-enrollment (courses)

Typical use cases:

* Grade 10 → DP course selection
* University pre-registration
* Pathway or track selection

Characteristics:

* time-bounded selection windows
* multiple choices (sometimes ranked)
* prerequisite validation
* basket-level constraints
* frequent need for counselor/admin review

**Portal users never write directly to Program Enrollment.**
They submit **Enrollment Requests**.

Staff tools may write directly, but must either:
* use the same validation engine, or
* explicitly bypass it with a logged override.

---

### 3.2 Guardian self-enrollment (activities)

Typical use cases:

* after-school activities
* clubs, sports, enrichment

Characteristics:

* capacity-driven
* age / grade / program eligibility
* often auto-approved
* sometimes wait-listed

Same architecture, different rules.

---

## 4. Enrollment Requests (Staging Area)

### 4.1 Why a staging object is mandatory

Basket selection **cannot** operate directly on Program Enrollment because:

* partial selections would create dirty states
* validation must run on an uncommitted basket
* approval and overrides must be recorded
* audit trails must remain clean

Therefore, a **Program Enrollment Request** ("shopping cart") is mandatory.

---

### 4.2 Role of the Enrollment Request

An Enrollment Request:

* captures user intent
* holds a draft basket of courses or activities
* stores validation results (snapshotted)
* records approvals and overrides
* materializes into Program Enrollment only after approval

This applies to **both** academic courses and activities.

---

## 5. Prerequisites Engine (Eligibility Logic)

### 5.1 Constraint model

Ifitwala_Ed uses a **DNF (OR-of-AND) model**:

(A AND B AND min_grade(A))
OR (C)
OR (D AND NOT E)

This reflects real institutional rules without requiring a full boolean parser.

---

### 5.2 Grade normalization (Locked Design Decision)

**Prerequisites never compare raw grade labels.**

All eligibility comparisons use a **numeric comparable scalar** (`numeric_score`)
and compare **Float → Float only**.

Facts:

* Course Term Result already stores `numeric_score`
* Grade labels (`A-`, `6`, `84%`) are human-facing only

Important clarification:

* `numeric_score` is a **comparable scalar**
* it is often normalized to 0–100
* but the invariant is comparability, **not the range**

#### Design consequence

* Runtime logic never parses grade strings
* Prerequisite evaluation is fast and SQL-friendly
* Human labels exist for display and audit only

#### Schema alignment (required)

`Program Course Prerequisite` must include:

* `min_grade` (Data, human label)
* `min_numeric_score` (Float, hidden, resolved at save time)
* `grade_scale_used` (Link, resolved at save time; see §5.3)

Runtime evaluation must **never** parse `min_grade`.

---

### 5.3 Grade scale: explicit intent vs evidence (Locked)

This system must support **both**:

1) A **program baseline grading intent** (default expectation)
2) A **course-specific grading override** (exceptions)
3) A **frozen evidence grade scale** (what actually happened)

Ifitwala_Ed is reality-anchored: programs declare intent, courses may override,
and results record what was actually used.

#### 5.3.1 Program baseline grade scale (intent layer)

**DocType + fieldname**

* `Program.grade_scale` (Link → Grade Scale)

Meaning:

* default grade semantics for the program
* used for prerequisite authoring and baseline comparisons
* policy/config intent, not evidence

#### 5.3.2 Course grade scale override (intent layer)

**DocType + fieldname**

* `Course.grade_scale` (Link → Grade Scale, optional)

Meaning:

* overrides the program scale for this course
* supports pass/fail or special scales
* policy/config intent, not evidence

#### 5.3.3 Evidence grade scale (frozen truth)

**DocType + fieldname**

* `Course Term Result.grade_scale` (Link → Grade Scale)

Meaning:

* immutable, historically auditable truth
* what was actually used for the student’s result
* never recomputed or inferred after the fact

#### 5.3.4 Resolution order (deterministic)

When eligibility needs a grade scale, resolve in this order:

1. `Course Term Result.grade_scale` (evidence always wins)
2. `Course.grade_scale` (course override)
3. `Program.grade_scale` (program baseline)
4. otherwise: validation error (no silent fallback)

#### 5.3.5 Prerequisite authoring (snapshotted)

To prevent drift when grade scale configs change later:

* each prerequisite row must store `grade_scale_used`
* `min_numeric_score` is computed from (`min_grade`, `grade_scale_used`) at save time
* eligibility evaluation compares Float → Float only

This ensures prerequisite rules remain auditable years later.

---

## 6. Source of Truth for Eligibility

Eligibility checks use **official academic truth only**:

* Program Enrollment (course taken / completed)
* Course Term Result (grades, numeric_score, and evidence grade_scale)
* Reporting Cycle status (Locked / Published thresholds)

Eligibility **never** uses:

* draft teacher input
* unreleased tasks
* inferred or transient data

Institutions define which Reporting Cycle states are considered valid evidence.

---

## 7. Retakes, Repeats, and Attempts

There is no universal retake rule.

Institutions vary on:

* best attempt vs most recent
* first passing attempt
* averaging attempts
* manual decisions

### Locked principle

Retake behavior is **policy-driven**, not hard-coded.

A grading / retake policy must define:

* which attempts are eligible evidence
* which reporting cycle statuses are eligible evidence
* how a single “counted” result is chosen
* what numeric threshold constitutes a pass

This policy is reused across:

* enrollment eligibility
* transcript logic
* reporting and analytics

---

## 8. Basket-Level Constraints (DP-style rules)

Prerequisites answer:

> “Can you take this course?”

Basket constraints answer:

> “Is this **combination** valid?”

Examples:

* exactly 6 courses
* HL / SL counts
* group coverage with substitution rules

### Critical distinction

Basket constraints are **not prerequisites**.

They are:

* offering-scoped
* evaluated against the **Enrollment Request basket**
* independent of individual course eligibility

### Configuration (Pending Choice)

Two viable storage models:

* **Option A** — JSON rules on Program Offering
  * very flexible
  * fast to evolve
  * harder to validate in UI

* **Option B** — structured child-table rules
  * safer UI
  * clearer validation
  * less expressive

No decision yet — both must remain viable.

---

## 9. Capacity Modeling (Clarified & Locked)

Capacity exists at **two distinct, non-interchangeable layers**.

---

### 9.1 Allocation capacity (choice / approval stage)

Allocation capacity answers:

> “How many students may choose this course for this offering/year?”

**Locked decision**

Allocation capacity belongs to **Program Offering Course**, because:

* capacity changes year-to-year
* selection often happens before sections exist
* approvals and waitlists live here

Required fields:

* `capacity` (Int)
* `waitlist_enabled` (Check)
* optional: `reserved_seats` (Int)

Allocation capacity is enforced during **Enrollment Request validation**.

**Guardrail**

Allocation checks must **never** depend on Student Groups existing.

---

### 9.2 Delivery capacity (timetabled sections)

Delivery capacity answers:

> “How many seats exist in the actual taught sections?”

**Locked decision**

There is **no Course Section / Course Offering doctype**.

**Student Group *is* the section.**

Delivery capacity is enforced by:

* `Student Group.maximum_size`
* membership limits in `Student Group Student`

Student Groups may:

* represent one section of a course
* inherit default capacity from Program Offering Course.capacity at creation
* later diverge due to room, teacher, or timetable constraints

---

### 9.3 Inheritance & guardrails

* Capacity inheritance happens **once**, at Student Group creation
* No auto-sync after students are assigned
* Allocation capacity ≠ section capacity
* Enrollment approval ≠ section placement

This separation mirrors real institutional workflows.

---

## 10. Overrides (Human Reality)

Overrides are first-class, not exceptions.

Every constraint system must support:

* authorized override
* mandatory reason
* timestamped audit
* item-level or basket-level scope

Ifitwala_Ed provides **guardrails and evidence**, not enforcement ideology.

---

## 11. Known Open Problems (Deferred but Acknowledged)

### 11.1 Activity age eligibility

`minimum_age` / `maximum_age` currently use Date fields.

This is ambiguous and incorrect.

Deferred resolution:

* age-in-years semantics
* or explicit birthdate cutoffs

---

### 11.2 Course equivalencies

Examples:

* “Any Math Extended”
* “Any prior Mandarin study”

Likely solution:

* Course Sets / Equivalency Groups

Not finalized.

---

### 11.3 External credits and transfers

Examples:

* prior institutions
* imported transcripts

Out of scope for initial phase, but must remain possible.

---

## 12. Blind Spots to Watch

* assuming grade systems are comparable
* encoding policy instead of configuration
* over-automating counselor decisions
* treating activities as “simpler”
* letting UI flows dictate data models
* allowing enrollment logic to mutate Program Enrollment directly
* forgetting to snapshot prerequisite grade scales (causes drift)

---

## 13. Architectural North Star

> **Enrollment in Ifitwala_Ed is a decision system with institutional memory,**
> **not a form that mutates tables.**

If an institution says:

> “We do it differently.”

The correct response is:

> “Configure it — don’t rewrite it.”

---

## 14. Pending Design Decisions (Explicit)

Still to be locked:

1. Final Program Enrollment Request schema (fieldnames and minimal audit payload)
2. Location of retake / grading policy (Program vs Offering)
3. Basket rule storage (JSON vs structured)
4. Course equivalency abstraction
5. Guardian vs student permission boundaries
6. Caching strategy for eligibility evaluation

---

## 15. Final Note

Enrollment is one of the most sensitive domains in education:

* academically
* legally
* politically

Ifitwala_Ed treats it accordingly.

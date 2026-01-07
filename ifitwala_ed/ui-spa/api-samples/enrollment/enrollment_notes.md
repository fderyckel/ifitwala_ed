# enrollment_notes.md

## Status

**Draft – Critical Architecture Notes (Authoritative, Living Document)**

This document defines the **intent, constraints, confirmed design decisions, open questions, and identified risks** for enrollment and self‑enrollment in Ifitwala_Ed.

It is written for:

* core maintainers
* future contributors
* coding agents (Codex / automation)

This is **not marketing** and **not a UI specification**. It exists to prevent architectural drift and to ensure that enrollment logic remains **correct, auditable, and institution‑agnostic**.

---

## 1. Core Intent (Non‑Negotiable)

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

* **Curriculum‑agnostic**
  (IB, AP, BTEC, national curricula, custom pathways)

* **Historically auditable**
  Enrollment decisions must be explainable years later

* **Human‑overrideable**
  Institutions may override rules, but must leave evidence

* **Policy‑driven, not hard‑coded**
  The platform provides tools, not ideology

* **Reality‑anchored**
  Matches how schools, colleges, and universities actually operate

---

## 2. Explicit Layer Separation (Critical)

Ifitwala_Ed enforces a strict separation of responsibilities:

| Layer                                | Responsibility                      |
| ------------------------------------ | ----------------------------------- |
| Course / Activity                    | Catalog (what exists)               |
| Program                              | Academic structure and intent       |
| Program Offering / Activity Offering | What is available now               |
| Enrollment Request                   | What a user is asking for           |
| Validation Engine                    | Eligibility & constraint evaluation |
| Program Enrollment                   | Committed academic truth            |
| Course Term Result                   | Outcome evidence                    |

Any leakage across layers is a **design regression**.

---

## 3. Portal Enrollment (Students & Guardians)

### 3.1 Student self‑enrollment (courses)

Typical use cases:

* Grade 10 → DP course selection
* University pre‑registration
* Pathway or track selection

Characteristics:

* time‑bounded selection windows
* multiple choices (sometimes ranked)
* prerequisite validation
* basket‑level constraints
* frequent need for counselor/admin review

**Students never write directly to Program Enrollment.**
They submit **Enrollment Requests**.

---

### 3.2 Guardian self‑enrollment (activities)

Typical use cases:

* after‑school activities
* clubs, sports, enrichment

Characteristics:

* capacity‑driven
* age / grade / program eligibility
* often auto‑approved
* sometimes wait‑listed

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

Ifitwala_Ed uses a **DNF (OR‑of‑AND) model**:

```
(A AND B AND min_grade(A))
OR (C)
OR (D AND NOT E)
```

This reflects real institutional rules without requiring a full boolean parser.

---

### 5.2 Grade normalization (Confirmed Design Decision)

**Prerequisites never compare raw grade labels.**

All grades are evaluated using a **normalized numeric_score (0–100)**.

Facts:

* Course Term Result already stores `numeric_score`
* Grade labels (`A‑`, `6`, `84%`) are human‑facing only

#### Design consequence

* Prerequisite rules compare **Float → Float only**
* Human labels exist for display and audit

#### Schema alignment action

* `Program Course Prerequisite` must include:

  * `min_grade` (Data, human label)
  * `min_numeric_score` (Float, hidden, resolved at save time)

Runtime logic must **never** parse grade strings.

---

### 5.3 Grade scale resolution

Grade meaning depends on context.

Resolution order must be explicit and deterministic:

1. Program Offering
2. Course
3. Program
4. School default

The resolved scale must be stored (or traceable) so eligibility decisions remain auditable.

---

## 6. Source of Truth for Eligibility

Eligibility checks use **official academic truth only**:

* Program Enrollment (course taken / completed)
* Course Term Result (grades)
* Reporting Cycle status (Locked / Published thresholds)

Eligibility **never** uses:

* draft teacher input
* unreleased tasks
* inferred or transient data

Institutions define which cycle states are considered valid.

---

## 7. Retakes, Repeats, and Attempts

There is no universal retake rule.

Institutions vary on:

* best attempt vs most recent
* first passing attempt
* averaging attempts
* manual decisions

### Design decision

Retake behavior is **policy‑driven**, not hard‑coded.

A grading / retake policy must define:

* which attempts are considered
* how a single "counted" result is chosen
* what numeric threshold constitutes a pass

This policy is reused across:

* enrollment eligibility
* transcript logic
* reporting and analytics

---

## 8. Basket‑Level Constraints (DP‑style rules)

Prerequisites answer:

> "Can you take this course?"

Basket constraints answer:

> "Is this **combination** valid?"

Examples:

* exactly 6 courses
* HL / SL counts
* group coverage with substitution rules

### Critical distinction

Basket constraints are **not prerequisites**.

They belong to:

* Program Offering

They validate:

* the basket as a whole
* not individual course eligibility

---

## 9. Capacity Modeling (Identified Gap)

Current state:

* Program Offering has a global capacity
* Program Offering Course has **no capacity**

Problem:

* real bottlenecks occur at course / lab / elective level

### Required design decision

One of the following must be implemented:

* **Option A (short‑term)**: add capacity and waitlist logic to Program Offering Course
* **Option B (long‑term)**: introduce Course Section / Course Offering

Enrollment architecture must support both paths.

---

## 10. Overrides (Human Reality)

Overrides are first‑class, not exceptions.

Every constraint system must support:

* authorized override
* mandatory reason
* timestamped audit
* item‑level or basket‑level scope

Ifitwala_Ed provides guardrails and evidence — not enforcement ideology.

---

## 11. Known Open Problems (Deferred but Acknowledged)

### 11.1 Activity age eligibility

`minimum_age` / `maximum_age` currently use Date fields.

This is ambiguous and incorrect for many institutions.

Deferred resolution:

* explicit age‑in‑years
* or birthdate cutoff semantics

---

### 11.2 Course equivalencies

Examples:

* "Any Math Extended"
* "Any prior Mandarin study"

Likely solution:

* Course Sets / Equivalency Groups

Not yet finalized.

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
* over‑automating counselor decisions
* treating activities as "simpler"
* letting UI flows dictate data models
* allowing enrollment logic to mutate Program Enrollment directly

---

## 13. Architectural North Star

> **Enrollment in Ifitwala_Ed is a decision system with institutional memory,**
> **not a form that mutates tables.**

If an institution says:

> "We do it differently."

The correct response should be:

> "Configure it — don’t rewrite it."

---

## 14. Pending Design Decisions (Explicit)

Still to be locked:

1. Final Program Enrollment Request schema
2. Location of retake / grading policy (Program vs Offering)
3. Capacity granularity choice
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

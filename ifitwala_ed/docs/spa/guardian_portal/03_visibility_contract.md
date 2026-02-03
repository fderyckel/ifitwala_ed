# Guardian Visibility Rules — Contract (v0.1)

**Ifitwala_Ed — Authoritative**
Status: Draft (Phase-0)
Audience: Humans, coding agents
Scope: Guardian / Parent Portal visibility only
Last updated: 2026-02-02

---

## 1. Purpose

This document defines **what data a Guardian may see**, **when it becomes visible**, and **under which conditions**.

It exists to:

* prevent accidental data leakage
* align UX with legal and academic governance
* make visibility rules explicit and auditable
* eliminate “UI-driven permissions”

**Visibility is a policy decision, not a frontend choice.**

---

## 2. Core Principles (Locked)

### 2.1 Visibility Is Explicit, Never Implied

A Guardian may see data **only if an explicit visibility gate exists**.

The system must never infer visibility from:

* submission existence
* record creation
* staff intent
* timing alone

---

### 2.2 Publication ≠ Existence

Many records exist **before** they are visible.

Visibility depends on:

* explicit flags (e.g. `published_to_parents`)
* reporting cycle state
* policy acknowledgement state
* audience scoping

---

### 2.3 Guardian Scope Is Strict

Guardians may see:

* their own Guardian record
* their linked Students
* data explicitly scoped to those Students

Guardians may **never** see:

* other students
* sibling comparisons
* school-wide aggregates
* staff-only notes

---

### 2.4 Cadence & Visibility Stability

Guardian-visible data must respect **cadence stability**.

Rules:

* Visibility does not imply immediacy
* Published data may surface:

  * immediately (Guardian Home)
  * or in periodic summaries (Weekly Summary)
* No “partial exposure” between states

**Invariant**

> A Guardian never sees *half-published* academic truth.

---



## 3. Student Identity & Relationship

### 3.1 Relationship Gate (Hard)

A Guardian may see Student-scoped data **only if**:

* a valid Guardian ↔ Student relationship exists
* the relationship is active
* the Guardian is authorized for that Student

No implicit authority.
No fallback rules.

---

## 4. Academic Visibility Rules

### 4.1 Tasks (Assignments, Assessments, Classwork)

**Internal truth**
All academic work is modeled as `Task`.

**Guardian visibility**

A Task appears to Guardians **only if**:

* it is delivered to the Student (via Task Delivery)
* it falls within the Guardian Home time horizon **or**
* it has published results

**Default Guardian fields**

* task title
* due date
* high-level status (not grading mechanics)
* preparation cues (if any)

**Hidden from Guardians**

* delivery strategy
* grading mode
* rubric internals
* submission versions (unless explicitly expanded)

---

### 4.2 Task Results (Critical)

**Visibility gate (Locked)**

A Guardian may see Task results **only if**:

* the Task Outcome is marked `published_to_parents = 1`

Before publication:

* results must not appear
* partial data must not leak
* draft grading must remain invisible

**Implication**

* Guardian Portal never queries live gradebook views
* Guardian Portal reads **published Outcome truth only**

---

### 4.3 Term / Report Results

**Visibility gate**

Term results are visible to Guardians **only if**:

* Reporting Cycle state = `Published`
* Course Term Result exists
* visibility is explicitly enabled for Guardians

**Rules**

* Term Reports are immutable snapshots
* No recalculation
* No partial release
* No preview states for Guardians

---

## 5. Behaviour, Health, and Wellbeing

### 5.1 Student Logs

A Student Log may appear to Guardians **only if**:

* `visible_to_guardians = 1`

**Rules**

* No severity scoring
* No internal categorization exposed
* No aggregation or interpretation

Guardian Portal:

* presents the fact
* does not assess meaning

---

### 5.2 Health-Related Records

Health events (e.g. nurse visits) are visible **only if**:

* explicitly marked guardian-visible
* scoped to the Student

Sensitive medical detail:

* must be minimized
* must never expose staff-only context

---

## 6. Communications

### 6.1 Canonical Communication Stream

Guardians see Communications **only if**:

* they are explicitly included in the audience
* the communication targets their Student(s) or Guardian role

**Characteristics**

* event-based (not threaded by default)
* immutable content once sent
* reactions or follow-ups may be allowed later

**Hidden**

* internal staff discussions
* draft communications
* staff-only annotations

---

## 7. Policies, Forms, and Acknowledgements

### 7.1 Policy Visibility

A Policy Version is visible to Guardians **only if**:

* it applies to `Guardian` or `Student`
* it is active
* it requires Guardian acknowledgement

---

### 7.2 Acknowledgement Visibility

Guardians may see:

* their own acknowledgements
* acknowledgements made **for their linked Students**

Guardians may **never**:

* acknowledge on behalf of another adult
* modify or revoke acknowledgements
* see acknowledgements of other families

**Invariant**
Acknowledgements are append-only legal evidence.

---

## 8. Calendar & Scheduling

### 8.1 School Calendar

Guardians may see:

* school days
* holidays
* non-instructional days
* events relevant to their Students

**Never visible**

* internal scheduling logic
* rotation days
* block numbers

All scheduling must be translated into **plain language**.

---

## 9. Explicit Prohibitions (Non-Negotiable)

The Guardian Portal must **never** expose:

* live gradebook data
* unpublished Task Outcomes
* draft teacher comments
* staff-only Student Logs
* internal moderation or overrides
* comparison between siblings
* internal system identifiers

Violations are **governance defects**, not UX bugs.

---

## 10. Enforcement Rules (Server-Side)

All visibility rules must be enforced:

* server-side
* before data reaches the client
* independent of UI state

Frontend hiding is **never sufficient**.

---

## 11. Phase-0 Lock Statement

> This document defines **guardian-visible truth**.
>
> Any UI, API, report, or export exposing guardian data must conform to these rules.
>
> Changes require:
>
> * explicit contract revision
> * governance review
> * legal consideration

---


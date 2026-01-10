# Student Log & Follow-Up System

## Architecture & Design Intent (Authoritative)

> **Status**: Locked for v1. Any implementation (Desk, SPA, API, Reports) must conform to this document. If code diverges, code must be refactored — not intent.

---

## 1. Purpose & Philosophy

The Student Log system is a **teacher‑centered observational workflow**, not a disciplinary system.

It exists to:

* Capture meaningful observations (positive, neutral, concern‑based)
* Integrate seamlessly into daily teaching workflows (especially Attendance)
* Route responsibility clearly when follow‑up is required
* Preserve history once action has begun

**Core principle**

> Capture is easy.
> Follow‑up is structured.
> History becomes immutable once acted upon.

---

## 2. Core Objects & Responsibilities

### 2.1 Student Log — Observation

Represents **what was observed**.

Key characteristics:

* Submittable document
* May or may not require follow‑up
* Can be amended **only before follow‑up exists**
* Visibility to students/guardians is explicit and opt‑in in SPA
* Desk logic is authoritative for state changes

Key fields (non‑exhaustive):

* `student`
* `date`, `time`
* `log_type`
* `log`
* `requires_follow_up`
* `next_step`
* `follow_up_person`
* `follow_up_status`
* `school` (read‑only)
* `amended_from`

---

### 2.2 Student Log Type — Classification

Defines **what kind of observation** the log represents (e.g. Positive Learning Attitude).

**Locked decision**

* `school` field exists and is required
* Log Types are **school‑scoped**
* School hierarchy rules apply

---

### 2.3 Student Log Next Step — Routing Definition

Defines **what kind of follow‑up is required** when `requires_follow_up = 1`.

Fields:

* `next_step`
* `associated_role`
* `school`
* `auto_close_after_days`

Design intent:

* Next Steps are school‑scoped
* Responsibility is defined by **role**, not person
* Assignee is chosen at log creation
* SPA must never hardcode Next Steps

---

### 2.4 Student Log Follow Up — Action Record

Represents **work done in response to a Student Log**.

Key characteristics:

* Always linked to exactly one Student Log
* Submittable and auditable
* Once a Follow Up exists, the parent log is historically frozen

This document is the **action trail** and must never be broken by amendments.

---

## 3. Visibility Rules (Teacher‑Safe Defaults)

SPA defaults (intentional override):

* Visible to student: **OFF**
* Visible to parents: **OFF**

Visibility must always be a **conscious teacher decision**.

---

## 4. School Hierarchy & Scoping (Non‑Negotiable)

### 4.1 School Model

* `School` is a NestedSet (`is_tree = 1`)
* Parent field: `parent_school`
* Hierarchy via `lft` / `rgt`

### 4.2 Allowed School Set Rule

Given a reference school **S**, the allowed set is:

* S
* all descendants of S
* parent of S (one level only)
* **never sibling schools**

This rule applies uniformly to:

* student search
* log type lists
* next step lists
* follow‑up assignee lists

---

## 5. School Context Resolution

**Canonical truth**

* `Student.anchor_school` defines the student’s school context

Usage:

* Attendance entry → school known from context (must match student scope)
* Home entry → school resolved from selected student

`Student Log.school` is derived server‑side and treated as read‑only.

---

## 6. SPA Entry Points

### 6.1 Attendance (Primary)

* Student known and locked
* No student picker
* Two‑click capture flow

### 6.2 Staff Home (Secondary)

* Student typeahead enabled
* Scope = user’s default school + descendants
* Never sibling schools

---

## 7. Follow‑Up Lifecycle

### 7.1 No Follow‑Up Required

If `requires_follow_up = 0`:

* On submit, log is automatically marked **Completed**
* No Follow Up records exist

### 7.2 Follow‑Up Required

If `requires_follow_up = 1`:

* `next_step` mandatory
* `follow_up_person` mandatory
* Status transitions are server‑owned
* ToDo / notifications created by Desk logic

SPA responsibilities:

* Fetch Next Steps (school‑scoped)
* Fetch assignees (role + school scope)
* Block submit until valid

---

## 8. Editing, Amendments & Clarifications

**Invariant**

> Once follow‑up work begins, history must not be rewritten.

### Teacher‑Facing Actions

**Edit log**

* Internally uses Frappe Amend
* Allowed only if no Follow Up exists

**Add clarification**

* Allowed always
* Append‑only (Comment / timeline note)
* Does not alter follow‑up logic

---

## 9. Reports & Dashboards

### 9.1 Reporting Philosophy

Reports are **read‑only consumers** of Student Logs and Follow Ups.
They never mutate or reinterpret business logic.

### 9.2 Student Logs Script Report

* Parent row: Student Log
* Child rows: Student Log Follow Ups
* Status derived strictly from stored fields

### 9.3 Print Templates

* Formal audit record
* One card per Student Log
* Follow Ups listed chronologically

### 9.4 Dashboards

* Student Log Dashboard → operational oversight
* Student Overview Dashboard → analytics only (no capture)

---

## 10. API Contract

SPA may:

* Fetch Log Types (school‑scoped)
* Fetch Next Steps (school‑scoped)
* Fetch assignees (role + school scope)
* Submit logs
* Submit clarifications
* Trigger amend (when allowed)

Server is authoritative for:

* School resolution
* Permissions
* Status transitions
* Follow‑up enforcement

---

## 11. Source of Truth for Staff Scoping

* Employee is authoritative
* `Employee.user_id` → User
* `Employee.school` → school node

---

## 12. UX Language Rules

Allowed:

* Edit log
* Add clarification
* Needs follow‑up?
* Who should follow up?

Forbidden:

* workflow
* docstatus
* amend
* architecture terms

---

## 13. Morning Briefing Integration

### 13.1 Purpose

The **Morning Briefing** is a *situational awareness surface*, not a workflow tool.

Its role is to:

* Surface **recent Student Logs** and **active Follow Ups** to appropriate staff
* Provide early visibility of concerns, positives, and pending actions
* Reduce the need for staff to hunt through reports or dashboards

Morning Briefing **never mutates data** and **never replaces reports**.

---

### 13.2 Data Sources

The Morning Briefing consumes:

* Student Logs (recent, submitted only)
* Student Log Follow Ups (open / in-progress)

It relies entirely on **server-side queries** and respects:

* School hierarchy scoping
* Role-based visibility
* Existing Student Log visibility flags

The Morning Briefing does **not** infer or recompute status.

---

### 13.3 Scoping & Visibility Rules

Items shown in Morning Briefing must satisfy **all** of the following:

* Belong to the user’s allowed school set (school + descendants + parent(+1))
* Match role-based relevance (e.g. counselors see wellbeing-related items)
* Respect Student Log visibility flags
* Exclude draft or unsubmitted records

No sibling-school leakage is allowed.

---

### 13.4 Interaction Rules

From Morning Briefing, users may:

* Navigate to the underlying Student Log (read-only)
* Navigate to the Follow Up record if they are involved

Users may **not**:

* Edit logs
* Amend logs
* Create follow-ups
* Change status

Morning Briefing is **read-first, action-second**.

---

### 13.5 Relationship to Other Surfaces

Morning Briefing complements:

* Attendance (capture)
* Student Log dashboards (analytics)
* Script reports (audit)

It must not duplicate:

* Task lists
* Dashboards
* Workflow screens

---

## 14. Invariants (Must Never Drift)

1. Follow Ups always belong to exactly one Student Log
2. Logs with Follow Ups are immutable
3. Reports reflect stored state only
4. School scoping uses NestedSet everywhere
5. SPA never hardcodes variants
6. Desk logic is authoritative
7. Morning Briefing is read-only and never mutates data

---

**End

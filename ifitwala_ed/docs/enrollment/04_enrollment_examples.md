# enrollment_examples.md

## Status

**Expanded Scenarios & Reality Checks (Non‑Normative, Export‑Ready)**

This document **complements** `enrollment_notes.md`.

* `enrollment_notes.md` = **authoritative architecture & intent**
* `enrollment_examples.md` = **deep scenarios, stress‑tests, and reality mapping**

If there is ever a conflict:

> **`enrollment_notes.md` always wins.**

This document exists to:

* make abstract architecture tangible
* pressure‑test decisions against real institutions
* guide Codex agents and future contributors
* prevent silent policy drift

It is deliberately **long, concrete, and repetitive** in places. That is a feature.

---

## 1. Why Examples Matter in Enrollment Systems

Enrollment is one of the few ERP domains where:

* academic policy
* legal accountability
* human judgment
* and political pressure

collide.

Most enrollment systems fail not because the rules are complex, but because **edge cases were treated as exceptions instead of first‑class reality**.

This file encodes those realities.

---

## 2. Grade Scales & Prerequisites — Deep Dive

### 2.1 IB MYP → DP (International School)

**Context**

* Student completed:

  * MYP Extended Mathematics (Grade 10)
* Applying for:

  * DP Math AI HL

**Prerequisite Rule**

* Required course: MYP Extended Mathematics
* Minimum grade: `5`

**Evidence**

* Course Term Result:

  * grade_value = `5`
  * numeric_score = `71.4`
  * grade_scale = `IB 1–7`

**Stored Prerequisite Snapshot**

* min_grade = `5`
* min_numeric_score = `70`

**Evaluation**

* Compare `71.4 ≥ 70`

**Outcome**

✅ Eligible

**Audit Explanation**

> Requires MYP Extended Mathematics (Grade ≥ 5).
> Your result: 5 (Term 2, Grade 10).

---

### 2.2 US Letter Grades → Percent Threshold

**Context**

* Student took: English 101
* Applying for: English 201

**Prerequisite Rule**

* Required course: English 101
* Minimum grade: `B-`

**Grade Scale Resolution**

* Program grade scale: US Letters
* Boundary:

  * B- → 80

**Evidence**

* Course Term Result:

  * grade_value = `B`
  * numeric_score = `83`

**Evaluation**

* Compare `83 ≥ 80`

**Outcome**

✅ Eligible

**Key Point**

Human labels are never compared. Only numeric_score is used.

---

### 2.3 Grade Boundary Drift (Audit Stability)

**Context**

* Prerequisite saved when B- = 80
* School later updates grade scale:

  * B- → 78

**Stored Prerequisite**

* min_numeric_score = `80`

**Outcome**

✅ Eligibility result does **not change**

**Reason**

Eligibility decisions must remain explainable years later.

---

## 3. Missing Evidence & Provisional Decisions

### 3.1 Grade 10 Students Selecting Grade 11 Courses

**Context**

* Course selection in March
* Final grades published in June

**Reality**

* No final Course Term Result exists

**Evaluation Inputs**

* Program Enrollment history
* Current course completion status
* Counselor expectations

**Outcome**

⚠️ Provisional approval

**Enrollment Request State**

* status = `Under Review`
* note = `Final results pending`

---

## 4. Retakes, Repeats, and Institutional Policy

### 4.1 Highest Score Policy (Common in Universities)

**Student History**

* Math 101 attempts:

  * Attempt 1: 62
  * Attempt 2: 78

**Policy**

* retake_logic = `Highest`

**Evaluation**

* Best numeric_score = `78`

**Outcome**

✅ Eligible for Math 202

---

### 4.2 Most Recent Policy (Common in IB Contexts)

Same data, different policy:

* retake_logic = `Most Recent`

**Evaluation**

* Most recent = `62`

**Outcome**

❌ Not eligible

---

### 4.3 Non‑Repeatable Course

**Course Configuration**

* repeatable = false

**Student Action**

* Attempts to select completed course again

**Outcome**

❌ Blocked

Override required with justification.

---

## 5. Basket‑Level Constraints (Program Logic)

### 5.1 IB DP Subject Groups

**Rules**

* Exactly 6 courses
* Groups 1–5 required
* Group 6 optional, substitution allowed

**Student Basket**

* Group 1 ✔
* Group 2 ✔
* Group 3 ✔
* Group 4 ✔
* Group 5 ✔
* Extra Group 4 ✔

---

## 6. Activity Booking Examples (v2)

### 6.1 Pre-open gate blocks on instructor conflict

Context:

1. Program Offering has `activity_booking_status = Ready`.
2. Linked activity section has teaching slots.
3. Instructor already has overlapping `Employee Booking` row.

Outcome:

1. Readiness report returns `ok = false`.
2. Opening window is blocked.
3. Diagnostics identify section + conflicting source.

### 6.2 FCFS booking with hard overlap guard

Context:

1. Student attempts to book activity section A.
2. Student already has confirmed activity section B with overlapping slots.

Outcome:

1. Section assignment is rejected server-side.
2. Booking falls back to next choice or waitlist policy.

### 6.3 Waitlist auto-promotion

Context:

1. Confirmed booking is cancelled.
2. Offering has `activity_auto_promote_waitlist = 1`.

Outcome:

1. Next waitlisted booking for that section is promoted to `Offered`.
2. Offer expiry is computed from `activity_waitlist_offer_hours`.
3. Event communication is published through `Org Communication`.

**Outcome**

✅ Valid basket

System records which rule path was satisfied.

---

### 5.2 Invalid Basket

**Student Basket**

* Only 5 courses selected

**Outcome**

❌ Invalid

Message:

> You must select exactly 6 courses.

---

## 6. Capacity — Allocation vs Delivery

### 6.1 Allocation Capacity (Choice Stage)

**Context**

* Biology HL (Program Offering Course)
* capacity = 24

**Current State**

* 22 Approved requests
* 1 Under Review

**Policy**

* count_toward_capacity = `Approved + Under Review`

**Outcome**

* Remaining visible seats: 1

---

### 6.2 Delivery Capacity (Sections)

**Context**

* Biology HL sections:

  * Section A (Student Group): 12
  * Section B (Student Group): 12

**Enrollment**

* 24 approved at offering level

**Placement**

* Section assignment later
* Enrollment approval ≠ guaranteed section

---

## 7. Completed Course Re‑Selection

### 7.1 Completed, Not Repeatable

❌ Blocked

Override required.

---

### 7.2 Completed, Repeatable

⚠️ Allowed with advisor confirmation

---

## 8. Guardian Activity Enrollment

### 8.1 Auto‑Approved Activity

* Capacity available
* Age criteria met

✅ Auto‑approved

---

### 8.2 Waitlist Scenario

* Capacity full
* waitlist_enabled = true

⏳ Waitlisted

Order preserved.

---

## 9. Overrides & Audit

### 9.1 Counselor Override

**Recorded**

* override_scope
* override_reason
* override_actor
* timestamp

**Outcome**

Enrollment proceeds with traceable justification.

---

## 10. Cross‑System Compatibility Check

| Setting                | Supported |
| ---------------------- | --------- |
| US High School         | ✔         |
| IB (PYP/MYP/DP)        | ✔         |
| British (GCSE/A‑Level) | ✔         |
| Canadian               | ✔         |
| Australian             | ✔         |
| Community Colleges     | ✔         |
| Universities           | ✔         |
| Activities & Clubs     | ✔         |

No curriculum logic is hard‑coded.

---

## 11. What This File Is Not

* Not schema
* Not policy
* Not UI
* Not validation code

It is a **reality mirror**.

---

## Final Statement

> Enrollment systems fail when they model clean data instead of messy institutions.

This document exists to ensure Ifitwala_Ed never forgets that.

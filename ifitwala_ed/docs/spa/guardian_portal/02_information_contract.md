# Guardian Home — Information Contract (v0.1)

**Ifitwala_Ed — Authoritative**
Status: Draft (Phase-0)
Audience: Humans, coding agents
Scope: Guardian Home (default landing surface)
Last updated: 2026-02-02

---

## 1. Purpose of Guardian Home

**Guardian Home** is the default entry surface for Guardians.

Its sole purpose is to provide a **calm, accurate, family-level briefing** answering:

1. What is happening with my family at school?
2. What does the next school days look like?
3. Is anything requiring my attention?
4. How can I support my children?

Guardian Home is **not a navigation hub**.
It is a **briefing surface**.

---

## 2. Time Horizon (Locked)

Guardian Home operates on a **time-bounded window**.

### Primary horizon

* **Today**
* **Next school days**
* Default window: **next 7 school days**

### Secondary horizon

* **Recent past** (context and continuity only)

### Rules

* Non-school days (weekends, holidays) are **explicitly shown and labeled**
* School calendars are respected **per child**
* No internal time structures (rotation days, blocks) may appear

---

## 3. Perspective & Aggregation Rules

### 3.1 Parent-Centric by Default (Locked)

* Guardian Home aggregates information at the **family level**
* Guardians are **not required** to select a child
* Child context is shown **inline**, only where relevant

### 3.2 Child Focus Is Contextual

Child-centric views are entered only when:

* an item explicitly concerns a single child
* the Guardian chooses to drill down

Child switching is **occasional**, not primary.

---

## 4. Section Ordering (Authoritative)

Guardian Home content is ordered by **cognitive priority**, not by system module.

### 4.1 Family Timeline (Primary Backbone)

**Purpose**
Provide a scannable, day-by-day view of what matters for the family.

**Characteristics**

* Grouped by **day**
* Aggregated across **all children**
* Plain language only

Each item answers:

* Which child
* What is happening
* When (human phrasing)
* Whether preparation is required

**Eligible sources**

* School schedule (translated)
* Tasks with due dates
* Assessments (as tasks)
* School events
* Calendar exceptions

**Explicit exclusions**

* Block numbers
* Rotation days
* Internal scheduling metadata

---

### 4.2 Attention Needed (Exceptions)

**Purpose**
Surface anything that may require Guardian awareness or action.

**Examples**

* Attendance issues
* Health visits
* Behaviour / student logs (guardian-visible only)
* Unread communications
* Pending acknowledgements or forms

**Rules**

* No severity labels
* No interpretation
* No moral framing
* Parents decide what is serious

---

### 4.3 Preparation & Support (Forward-Looking)

**Purpose**
Help Guardians support their children proactively.

**Examples**

* Upcoming assessments
* Projects due soon
* Patterns requiring encouragement

**Rules**

* Suggestive, not directive
* Informational, not evaluative

---

### 4.4 Recent Activity (Continuity)

**Purpose**
Provide reassurance and narrative continuity.

**Examples**

* Recently published task results
* Teacher communications
* Behaviour notes
* Health office visits

This section is **secondary** and visually quieter.

---

### 4.5 Default Presentation Rules (Clarification)

Guardian Home follows **progressive disclosure**.

**Default view**

* Narrative and contextual
* Plain language
* Low numeric density

**Expanded view**

* Numbers
* Dates
* Detailed task instructions
* Published results

**Invariant**

> Guardians should understand meaning **before** seeing metrics.

Numbers are available, but **never forced**.

---

### 4.6 Relationship to Weekly Summary

Guardian Home and Weekly Summary serve **different cognitive moments**:

* **Guardian Home**

  * situational
  * immediate
  * day-to-day

* **Weekly Summary**

  * reflective
  * periodic
  * stabilizing

They must:

* share the same visibility rules
* never contradict each other
* never expose different academic truths

---




## 5. Academic Information Rules (Guardian View)

### 5.1 Tasks

Internally, all academic work is modeled as **Tasks**.

Guardian Home:

* shows only **signal**
* suppresses internal distinctions unless meaningful

Default visibility:

* task title
* due date
* high-level status
* preparation cue (if any)

Hidden by default:

* instructions
* evidence
* grading mechanics

### 5.2 Results Visibility (Locked)

* Guardians see results **only if explicitly published to parents**
* Live gradebook data is never shown
* Term results appear only after Reporting Cycle publication

---

## 6. Behaviour, Health, and Wellbeing

* Only logs explicitly marked **visible to guardians** may appear
* No internal categories or severity scores are exposed
* No aggregation or interpretation is performed
* Guardian Home does not diagnose or summarize behaviour

---

## 7. Communications

Guardian Home surfaces communications that:

* are audience-scoped to the Guardian or their children
* are event-based (not threaded by default)

Rules:

* Communications appear as discrete items
* Inline expansion allowed
* Reply / reaction capabilities may be phased later
* No assumption of email or external messaging parity

---

## 8. Inline Expansion vs Navigation (Locked)

### Default behavior

* **Inline expansion** is preferred for understanding context

### Dedicated pages are reserved for:

* full task history
* reports / term results
* document upload
* payments
* communication archives

**Invariant**

> A Guardian must be able to understand their week **without leaving Guardian Home**.

---

## 9. Explicit Exclusions (Non-Negotiable)

Guardian Home must never show:

* sibling comparisons
* internal academic structures
* live gradebook views
* staff-only notes
* draft or provisional data
* configuration or preferences

---

## 10. Stability & Trust Guarantees

Guardian Home guarantees:

* data consistency across reloads
* no silent recalculation of published data
* no mixing of mutable and immutable academic truth
* no retroactive visibility changes

---

## 11. Phase-0 Lock Statement

> This document defines **what Guardian Home is responsible for**.
>
> UI design, IA, backend queries, caching, and permissions must conform to this contract.
>
> Any new section or deviation requires an explicit revision of this document.

---

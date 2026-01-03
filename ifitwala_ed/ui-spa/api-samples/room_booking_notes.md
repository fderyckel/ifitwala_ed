# Ifitwala_Ed — Architecture Notes (Authoritative)

This document defines **non-negotiable architectural decisions** for Ifitwala_Ed.
All future code, refactors, and features MUST respect these rules.

This file exists primarily for **coding agents (Codex)** and reviewers.

---

## 1. Core Scheduling & Room Availability Architecture

### 1.1 Source-of-Truth Model (Critical)

There are **two layers**, with strictly separated responsibilities:

#### A. Abstract Layer (Declarative)

* **Student Group Schedule**
* **School Schedule / Rotation Days**
* **Academic Calendar**

Purpose:

* Define *intent* (who should meet, when, in theory)
* Never answer operational questions directly

This layer is:

* Declarative
* Recomputed
* Never queried for availability by users

#### B. Operational Layer (Computed + Materialized)

This layer answers real-world operational questions.

It consists of TWO mechanisms:

1) **Materialized bookings**
   * Employee Booking
   * Meeting
   * School Event

2) **Computed virtual slots**
   * Student Group Schedule expanded via
     `iter_student_group_room_slots()`

Rules:

* Staff availability → materialized bookings ONLY
* Room availability → computed virtual slots + materialized bookings
* Utilization analytics → materialized bookings ONLY

---

### 1.2 Absolute Rule (No Exceptions)

❌ Student Group Schedule MUST NEVER be queried directly
   (raw rotation_day / block_number logic in availability code)

✅ Student Group Schedule MAY ONLY be used via:
   `iter_student_group_room_slots()`

No other access pattern is allowed.


---

## 2. Student Group Schedule → Employee Booking Pipeline

### 2.1 Design Intent

Student Group Schedule is an **abstract timetable**, not a booking.

Operational correctness is achieved by **materializing concrete bookings**.

---

### 2.2 Materialization Strategy (Chosen)

* **Employee Booking is the operational booking layer**
* Teaching slots are materialized as Employee Bookings
* Each teaching occurrence:
  * has absolute `from_datetime` / `to_datetime`
  * references its origin (Student Group)
  * enforces staff-level conflicts

⚠️ Location is resolved from Student Group Schedule
   during room availability computation, not from Employee Booking.


Required fields for teaching bookings:

* `employee`
* `from_datetime`
* `to_datetime`
* `location` **(mandatory)**
* `source_doctype = "Student Group"`
* `source_name = <Student Group name>`

If a teaching slot has **no location**, it is invalid.

---

### 2.3 Rebuild Rules (Bounded, Deterministic)

Employee Bookings must be rebuilt when:

* Student Group Schedule changes
* Instructor assignment changes
* Location changes
* Academic Year changes (rare)

Rebuild scope:

* **Single Student Group**
* **Bounded date range** (term or academic year)

❌ Never rebuild globally
❌ Never rebuild implicitly during reads

---

## 3. Room Availability Rules

### 3.1 How Availability Is Computed

A room is **busy** if ANY overlap exists with:

* Employee Booking
* Meeting
* School Event

SQL overlap logic:

```
from_datetime < window_end
AND to_datetime > window_start
```

---

### 3.2 What Is Explicitly NOT Used

* ❌ `rotation_day`
* ❌ `block_number`
* ❌ Student Group Schedule
* ❌ “best effort” abstract logic

Rotation logic belongs ONLY in the **materialization phase**, never in queries.

Important invariant:

If NO virtual or materialized conflicts are found for a room
in a given time window, the room is AVAILABLE.

Empty conflict sets must NEVER be interpreted as "unavailable".


---

## 4. School & Location Hierarchy Rules

### 4.1 School Scope

* Selecting **School A** includes:

  * School A
  * All descendant schools (NestedSet)

* Selecting **School B** includes:

  * School B only
  * NOT its parent
  * NOT its siblings

This applies consistently to:

* Rooms
* Bookings
* Meetings
* Analytics

---

### 4.2 Location Hierarchy

* Location is a NestedSet
* `is_group = 1` → structural node
* `is_group = 0` → real room

Only real rooms participate in availability.

---

## 5. API Design Rules (Frappe)

### 5.1 POST Invariant (Critical)

When using `frappe-ui` resources:

* **POST requests MUST use** `resource.submit(payload)`
* NEVER mix GET-style params with POST endpoints

This is a known failure mode and is treated as a **hard invariant**.

---

### 5.2 Time & Timezone Rules

* Always use **Frappe site timezone** (System Settings)
* Never rely on server OS timezone
* Never compute availability with naive datetimes
* Display times as `HH:MM` (no seconds)

---

## 6. Vue + frappe-ui Architecture Rules

### 6.1 Frontend Stack (Locked)

* Vue 3
* Tailwind CSS (**only** styling system)
* frappe-ui data utilities

No Bootstrap. No ad-hoc CSS frameworks.

---

### 6.2 Data Access Rules

Preferred utilities:

* `createResource`
* `createListResource`
* `createDocumentResource`

Rules:

* Filters live in ONE reactive object
* Watched with `{ deep: true }`
* Pagination is explicit (`start`, `page_length`)
* Changing filters resets pagination

---

### 6.3 Routing Rule (SPA)

Inside the Vue SPA:

* ❌ Never hardcode `/portal/` in routes
* Use named routes or base-less paths

Reason:

* Router uses `createWebHistory('/portal')`

---

## 7. Performance & Scaling Principles

* Optimize for **reads**, not writes
* Reads are frequent (200+ staff)
* Writes are rare (schedule edits)

Tradeoff:

* Materialize once
* Query cheaply forever

This is intentional and required for scale.

---

## 8. Explicit Non-Goals (Prevent Drift)

❌ No FULLY materialized room booking model in v1
❌ No implicit materialization during reads
❌ No hybrid logic hidden inside UI components

Hybrid availability (virtual SG slots + materialized events)
is explicit, centralized, and intentional.

---

## 9. Summary (For Codex)

* Student Group Schedule = abstract
* Employee Booking = operational truth
* Availability reads only materialized data
* Materialization is explicit, bounded, deterministic
* Vue + frappe-ui + Tailwind only
* POST via `submit(payload)` only

Violating these rules is a **regression**, not a feature.

---

## 10. Debugging Rule (Non-Negotiable)

When availability results are unexpected:

1) Verify expanded slots from `iter_student_group_room_slots()`
2) Verify materialized Employee Booking rows
3) Verify overlap logic
4) NEVER "fix" availability by filtering rooms post-query

If results look inverted (everything unavailable),
the bug is in interpretation, not in data absence.

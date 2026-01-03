# Ifitwala_Ed — Scheduling, Materialization & Conflict Management (Authoritative)

> **Status:** Locked architecture
>
> This document defines the **non‑negotiable scheduling, availability, and conflict‑management architecture** for Ifitwala_Ed.
>
> It is written for **humans and coding agents**. Any implementation that violates these rules is a **regression**, not a feature.

---

## 0. Design Intent (Why This Exists)

Scheduling systems fail when:

* abstract plans are queried as operational truth
* read paths try to infer missing data
* rebuilds create transient "free" states
* multiple modules compute conflicts differently

Ifitwala_Ed explicitly avoids these failure modes by enforcing:

* **Strict layer separation**
* **Materialization boundaries**
* **Datetime‑only operational truth**
* **Zero inference at read time**

This architecture is designed for:

* 1,000+ students checking schedules
* 200+ staff checking calendars
* high read / low write workloads
* predictable DB and CPU usage

---

## 1. Conceptual Layers (Locked)

### 1.1 Layer 1 — Abstract / Declarative Truth

**Purpose:** express *intent*, never operational truth.

Includes:

* Student Group Schedule
* School Schedule Blocks
* Rotation Day logic
* Academic Calendar

Properties:

* Abstract
* Recomputable
* Non‑blocking

**Hard rule:**

> Abstract tables MUST NEVER be queried directly to answer availability or room-conflict questions.

---

### 1.2 Layer 2 — Operational Fact Tables

**Purpose:** answer real‑world questions cheaply and correctly.

Primary fact table:

* **Employee Booking** — authoritative operational truth for **employee availability** and canonical source for staff teaching calendar events.

Also queried by aggregators (event source tables):

* **Meeting** — domain event records; may be partially materialized later
* **School Event** — domain event records; may be partially materialized later

Properties:

* Datetime‑based
* Queryable
* Conflict‑safe when merged deterministically

**Important clarification:**

> The invariant **“absence of a row means FREE” applies ONLY to Employee Booking**.
>
> It does **NOT** apply to Meeting or School Event unless those are explicitly materialized into a fact table.

There is no fallback to abstract logic at read time.

---

### 1.3 Layer 3 — Aggregation & Presentation

Includes:

* `api/calendar.py`
* availability APIs
* analytics collectors

Properties:

* Read‑only
* Aggregation only
* No inference

**Hard rule:**

> Aggregators may merge fact tables, but MUST NOT reconstruct or infer missing data.

---

## 2. Employee Booking (Operational Fact Table)

### 2.1 Purpose

Employee Booking represents **concrete, datetime‑based commitments** that:

* always block employee availability
* are suitable for conflict detection
* scale under heavy read load

Sources include:

* Teaching (materialized)
* Meetings
* Duties / Other

Employee Booking is **generic by design**.

---

### 2.2 Teaching via Employee Booking (Explicit Policy)

Teaching sessions are **materialized** into Employee Booking rows.

For `booking_type = "Teaching"`:

Required fields:

* `employee`
* `from_datetime`
* `to_datetime`
* `location` (MANDATORY)
* `source_doctype = "Student Group"`
* `source_name = <Student Group name>`

Optional cached fields (reporting only):

* `school`
* `academic_year`

**Explicit exclusions:**

* `rotation_day`
* `block_number`

Reason:
Employee Booking also stores meetings and duties that do not align with block/rotation logic. Datetime is the universal contract.

---

### 2.3 Canonical Calendar Event Identity (Critical)

For staff calendars:

> When a Teaching slot is materialized into Employee Booking, the **booking row is the canonical event**.

Canonical ID format:

```
sg-booking::<employee_booking.name>
```

Schedule‑derived IDs are **NOT allowed** in production staff calendars once bookings exist.

Schedule‑based IDs may appear only in:

* dev/debug tools
* explicit abstract schedule viewers

This rule **eliminates all read‑time inference** and guarantees stable event identity.

---

## 3. Student Group → Employee Booking Materialization

### 3.1 Single Materialization Boundary

All abstract → concrete conversion occurs in:

```
ifitwala_ed/schedule/student_group_employee_booking.py
```

No other module is allowed to materialize teaching.

---

### 3.2 Materialization Rules

For a given Student Group and bounded date window:

1. Expand timetable using `iter_student_group_room_slots()`
2. Resolve Instructor → Employee
3. Validate required data (location MUST exist)
4. Upsert Employee Booking rows (unique by slot)

**Hard failure:**

> Teaching slots without a location are invalid and must raise/debug during rebuild.

---

### 3.3 Rebuild Triggers (Clarified)

**Forbidden:**

* rebuild on READ paths

**Allowed:**

* rebuild triggered by WRITE paths

Examples:

* Student Group Schedule edit
* Instructor assignment change
* Location change

All rebuilds MUST be:

* debounced
* bounded (group + date window)
* idempotent

---

### 3.4 No Transient Emptiness (Critical)

Because absence means free, rebuilds must avoid gap windows.

**Required rebuild pattern:**

1. Compute target slots
2. Upsert target bookings
3. Delete obsolete bookings only

**Prohibited:**

* delete‑all‑then‑recreate for active windows

---

### 3.5 Incremental Rebuild Preference

Preferred strategy:

* Single schedule row change → rebuild affected blocks only

Full group rebuild allowed only for:

* structural changes
* academic year changes
* explicit admin action

---

## 4. Room Availability & Conflicts

### 4.1 Room Availability Definition

A room is BUSY if **any overlap** exists with:

* Employee Booking (with location)
* Meeting
* School Event

Overlap logic:

```
from_datetime < window_end
AND to_datetime > window_start
```

---

### 4.2 Single Room Conflict Helper (Locked)

> All room conflict checks MUST go through ONE helper function.

Example:

```
find_room_conflicts(location, start, end)
```

This helper merges:

* Employee Booking
* Meeting
* School Event

No ad‑hoc room SQL is allowed elsewhere.

---

## 5. Calendar API Rules (`api/calendar.py`)

Calendar APIs MUST:

* read only operational fact tables
* use booking‑based IDs for teaching
* never infer schedule context

Calendars aggregate:

* Employee Booking (primary)
* Meeting
* School Event

They do NOT:

* query Student Group Schedule
* derive rotation/block
* repair missing metadata

### 5.1 Optional UI Labels (Explicit Rule)

The UI MAY display human‑friendly labels such as:

* “Block 3”
* “Rotation Day 2”

**Only if** they can be resolved **deterministically** using authoritative abstract data.

Allowed inputs:

* `source_doctype / source_name` (Student Group)
* exact `from_datetime / to_datetime`
* deterministic date → rotation_day mapping (from `schedule_utils`)
* strict match against School Schedule Block windows for the relevant schedule

**Prohibited:**

* fuzzy time‑window overlap matching
* “best‑guess” inference
* reconstructing labels from partial data

If a label cannot be resolved deterministically:

* the UI MUST show **no block/rotation label**
* the system MUST emit structured debug information

**Important:**

> UI labels are **presentation‑only**.
>
> They MUST NEVER be used for conflict detection, availability enforcement, or event identity.

---

## 6. Performance & Scaling Rules

* Optimize for reads, not writes
* Avoid `get_doc()` in loops
* Use SQL joins for bulk
* Cache staff calendars (TTL + targeted invalidation)

Materialization is rare; reads are constant.

---

## 7. Debugging Protocol (Non‑Negotiable)

When availability looks wrong:

1. Inspect materialized bookings
2. Inspect room conflict helper output
3. Verify overlap logic

**Never fix bugs by reintroducing abstract logic.**

---

## 8. Summary (For Agents)

* Abstract schedules define intent only
* Employee Booking is operational truth
* Teaching uses booking‑based IDs
* No inference at read time
* No transient empty rebuilds
* One room conflict helper only

Violations of these rules are regressions.

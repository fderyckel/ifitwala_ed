# Ifitwala_Ed — Employee Booking Notes (Authoritative)

> **Status:** Locked architecture (vNext)
>
> This document defines the **non‑negotiable meaning and usage of Employee Booking**.
> It exists to prevent drift where Employee Booking becomes a dumping ground for room logic or ad‑hoc scheduling inference.

---

## 0. Core principle

**Employee Booking is the operational truth for employee availability.**

It is used for:

* staff free/busy checks
* staff calendars (when you choose the fact-table surface)
* instructor conflict validation

It is **not** used for:

* room truth (that is Location Booking)
* free-room checks

---

## 1. What creates Employee Booking rows

Employee Booking rows are projections derived from domain docs and teaching materialization.

### 1.1 Teaching (Student Group schedule materialization)

Teaching is expanded into concrete datetime slots in a bounded window, then projected into Employee Booking.

* Source: Student Group / Student Group Schedule (abstract intent)
* Fact: Employee Booking (operational truth)

### 1.2 Meetings (domain → staff truth)

Meeting is a domain doc.

* Meeting → Employee Booking: **one row per participant**
* Meeting → Location Booking: **one row per location** (separate system)

### 1.3 School Events (domain → staff truth, only when intended)

School Event can project into Employee Booking **only when your audience logic intends it**.

Current implementation resolves employees from:

* participants table
* audience rows: “Employees in Team” → Team Member → Employee

…and writes Employee Booking rows.

---

## 2. Canonical overlap predicate

For `[start, end)`:

* `from_datetime < end AND to_datetime > start`

This must be the only overlap predicate used across the codebase.

---

## 3. Canonical identity and idempotency

Employee Booking must support edits safely.

### 3.1 Stable event identity

Use the domain doc identity as the stable key:

* `source_doctype`
* `source_name`

(Optionally store `source_key = "{source_doctype}::{source_name}"` for convenience.)

### 3.2 Slot identity and rebuild-safe writes

There are two write patterns:

* **single-slot events** (Meeting): 1 slot per employee per meeting
* **multi-slot teaching** (Teaching): many slots per employee across a window

#### Required invariant: upsert-then-delete

For rebuild-safe materialization, the pattern is always:

1. compute target rows
2. upsert targets
3. delete obsolete rows

**Delete-all-then-recreate is forbidden** because it creates transient “free” states and breaks concurrency.

> Note: Your current Meeting + School Event projections delete all rows for the source, then reinsert. This works functionally but violates the rebuild safety invariant and must be refactored into upsert-then-delete.

---

## 4. Employee Booking vs datetime vs blocks

Employee Booking is **datetime-first**.

* Meetings and non-schedule events cannot be represented reliably with rotation_day/block_number.
* Teaching materialization computes datetimes from schedule blocks and rotation days, then writes datetime slots.

**Rule:** Employee Booking stores datetime as truth. Block/rotation are contextual metadata only when available.

---

## 5. Conflict checking (single source)

All employee conflict checks must go through one canonical helper:

* `find_employee_conflicts(employee, start, end, ...)`

This helper queries **Employee Booking only** and **must enforce**:

* the canonical overlap predicate
* `blocks_availability = 1`

No module is allowed to run its own ad-hoc overlap SQL.

---

## 5.1 The role of `blocks_availability` (critical)

`blocks_availability` is a **conflict‑enforcement flag**, nothing else.

It answers exactly one question:

> **“Does this booking make the employee unavailable for other bookings in this time window?”**

It is **not**:

* a room‑related field
* a priority or importance indicator
* a UI visibility toggle
* a soft delete or permission flag

### Why this field exists

Not all employee bookings should behave the same in conflict logic.

Examples:

**Must block availability (`blocks_availability = 1`)**

* Teaching
* Mandatory meetings
* Supervision / duty
* Exams / invigilation
* Required training

**Must NOT block availability (`blocks_availability = 0`)**

* Optional meetings
* FYI / informational events
* Observations or sit‑ins
* Non‑exclusive advisory roles

Without this flag, conflict logic becomes either:

* too strict (everything blocks), or
* too loose (nothing blocks), or
* hard‑coded per booking type (rigid, brittle)

`blocks_availability` provides a clean, orthogonal escape hatch.

### Canonical rule (locked)

All employee availability checks **must** apply:

```
WHERE blocks_availability = 1
```

Any employee conflict logic that ignores this flag is incorrect.

### Relationship to Location Booking

Even with:

* Employee Booking = staff truth
* Location Booking = room truth

`blocks_availability` remains essential because **room facts cannot answer staff availability questions**.

Location Booking never replaces Employee Booking for staff conflict logic.

---

---

## 6. Permissions and privacy

Employee Booking contains operational staff movement.

Baseline policy:

* Admin roles: full access
* Employees: can see their own bookings
* Managers/schedulers: broader access per role

Any broader access must be enforced server-side.

---

## 7. Debugging protocol

When staff availability looks wrong:

1. verify Employee Booking rows exist for the time range
2. verify overlap predicate
3. verify the materialization triggers ran (Meeting edit / schedule rebuild)
4. do not fix by querying Meeting/School Event/Schedule directly

---

## 8. Summary

* Employee truth = Employee Booking
* Room truth = Location Booking
* Domain docs materialize into facts
* Reads never infer
* Writes must be idempotent and rebuild-safe

---

## 9. Activity Booking Gate Integration (v2)

Activity booking windows now run a pre-open readiness gate that explicitly consumes `Employee Booking` via `find_employee_conflicts(...)`.

This enforces:

1. Linked activity sections cannot open if any instructor slot conflicts with existing staff commitments.
2. Conflict detection uses materialized datetime rows only.
3. Booking windows are blocked until staff collisions are resolved.

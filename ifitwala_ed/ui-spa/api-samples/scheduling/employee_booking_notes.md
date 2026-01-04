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

* room truth (that is Room Occupancy)
* room analytics
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
* Meeting → Room Occupancy: **one row per location** (separate system)

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

This helper queries **Employee Booking only**.

No module is allowed to run its own ad-hoc overlap SQL.

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
* Room truth = Room Occupancy
* Domain docs materialize into facts
* Reads never infer
* Writes must be idempotent and rebuild-safe

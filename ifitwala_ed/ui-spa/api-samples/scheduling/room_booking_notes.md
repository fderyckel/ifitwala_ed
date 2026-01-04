# Ifitwala_Ed — Room Booking Notes (Authoritative)

> **Status:** Locked architecture (vNext)
>
> This document defines the **non‑negotiable meaning and usage of room occupancy and room availability**.
> It exists to prevent the classic failure mode where “room truth” is inferred from staff rows, schedules, or ad‑hoc merges.

---

## 0. Core principle

**Rooms are operational truth only through a room fact table.**

* **Room Occupancy** (new) = **room operational truth** (free/busy + analytics)
* Employee Booking = employee operational truth (free/busy + staff calendar)
* Meeting / School Event / (optional) Room Booking = domain docs (workflow/audit/UI)
* Student Group Schedule = abstract intent only (never queried for room availability)

This eliminates room conflict ambiguity permanently.

---

## 1. Why we need a room fact table

### 1.1 The double counting problem

Meetings commonly create **N employee rows** (one per attendee). If you infer room usage from employee rows, you will:

* double count rooms
* inflate utilization
* break “free room” checks
* constantly fight dedupe bugs

### 1.2 The inference problem

If the system computes room availability by reading:

* Student Group Schedule
* Employee Booking location
* Meeting + School Event + bookings combined “on the fly”

…you inevitably get inconsistent answers across modules.

**Room Occupancy makes every module ask the same question against the same truth.**

---

## 2. Definitions

### 2.1 Domain docs

Domain docs are the human-facing records, e.g.

* Meeting
* School Event
* (optional) Room Booking (approvals/workflow)

They are not queried for operational truth.

### 2.2 Fact tables

Fact tables are operational truth for overlap queries:

* **Employee Booking**: employee free/busy
* **Room Occupancy**: room free/busy

Fact tables must remain:

* idempotent to rebuild
* cheap to query
* free of workflow complexity

---

## 3. Room Occupancy — required behavior

### 3.1 One row means one room is busy

A single Room Occupancy row means:

> location L is occupied for `[from_datetime, to_datetime)`

### 3.2 What materializes into Room Occupancy

Room Occupancy receives rows from:

* Teaching (materialized from Student Group schedule expansion)
* Meeting (1 row per location)
* School Event (1 row per location)
* Optional Room Booking domain doc (1 row per location)

### 3.3 Overlap predicate

Canonical overlap for `[start, end)`:

* `from_datetime < end AND to_datetime > start`

This is the only predicate used across the system.

---

## 4. Canonical identity and idempotency (critical)

Room Occupancy must support edits safely.

### 4.1 The identity problem

If your “unique key” includes timestamps, editing time can create duplicate rows unless you perfectly delete the old row.

### 4.2 Locked identity rules

We use two concepts:

* **event identity**: stable per domain doc
* **slot identity**: stable per domain doc + location, or per teaching instance

**Event identity (stable):**

* `source_key = "{source_doctype}::{source_name}"`

**Slot identity (stable per doc+location):**

* Meeting / School Event / Room Booking: `slot_key = "{source_key}::{location}"`

**Slot identity (stable per teaching instance):**

* Teaching instances: `slot_key = "{source_key}::{location}::{from_iso}::{to_iso}"`

This makes Meeting edits update the same row rather than creating new identities.

---

## 5. Write triggers (no read inference)

Room Occupancy is updated only by write-triggered materialization.

### 5.1 Meeting

* on insert/update: upsert Room Occupancy for meeting location
* on cancel/delete: remove the Room Occupancy row

### 5.2 School Event

* after_save / on_update: upsert Room Occupancy for event location
* on cancel/delete: remove the Room Occupancy row

### 5.3 Teaching

Teaching is materialized in a bounded window using:

1. compute target slots
2. upsert targets
3. delete obsolete

Delete-all-then-recreate is forbidden.

---

## 6. Read rules (non-negotiable)

### 6.1 Free rooms

Free-room checks query **Room Occupancy only**.

* No unions with Employee Booking
* No unions with domain docs
* No schedule expansion

### 6.2 Room conflicts

All room conflict checks go through one canonical helper:

* `find_room_conflicts(location(s), start, end, ...)`

This helper queries Room Occupancy only.

### 6.3 Room utilization analytics

Utilization queries Room Occupancy only.

If you need “people count” later, join against domain docs (Meeting participants, Student Group size), but do not count employee rows.

---

## 7. Permissions and privacy

Room Occupancy is operationally sensitive.

Baseline policy:

* Admin roles: full access
* Staff roles: free/busy access (optionally hide event details)
* Students/Guardians: off by default (only via explicit product decisions)

Enforce server-side.

---

## 8. Debugging protocol

When room availability looks wrong:

1. verify Room Occupancy rows exist for the time range
2. verify overlap predicate
3. verify location scope expansion (children/parents)
4. do not “fix” by querying Meeting/Employee Booking/Schedule directly

---

## 9. Summary

* Room truth = Room Occupancy
* Staff truth = Employee Booking
* Domain docs materialize into facts
* Reads never infer
* Writes must be idempotent and rebuild-safe

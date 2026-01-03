# Ifitwala_Ed — Architecture Notes (Authoritative)

This document defines **non-negotiable architectural decisions** for Ifitwala_Ed.
All future code, refactors, and features MUST respect these rules.

This file exists primarily for **coding agents (Codex)** and reviewers.

---

## Locked Scheduling Decisions (Authoritative)

This section records final, non-negotiable architectural decisions for scheduling,
calendars, availability, and conflict management in Ifitwala_Ed.

These decisions resolve all previous ambiguities between hybrid vs materialized models.

Any implementation that deviates from these decisions is a regression.

### Decision 1 — Room Availability Model

**Decision**
Room availability is computed from materialized operational data only.

**Authoritative sources**
Room availability MUST be determined exclusively by:

- Employee Booking rows with a non-null location
- Meeting rows with a location
- School Event rows with a location

**Explicitly NOT used**

- Student Group Schedule
- Rotation days
- Block numbers
- Virtual schedule expansion
- Any abstract or inferred logic at read time

**Rationale**

- Enables cheap, index-driven overlap queries
- Avoids schedule expansion on every read
- Eliminates abstract leakage into operational decisions
- Scales under heavy read load

**Status**

- Materialized-only model is LOCKED
- Hybrid models are forbidden in production availability checks

### Decision 2 — Employee Booking.location Rules

**Decision**
Employee Booking.location is conditionally mandatory, based on booking type.

**Rules by booking type**

| Booking Type | Location Required | Reason |
| --- | --- | --- |
| Teaching | Yes (mandatory) | Teaching blocks a room |
| Meeting | Yes (expected) | Meetings usually block a room |
| Duty | No | Field duty / supervision may have no room |
| Other | No | Generic commitments |

**Enforcement**

For booking_type == "Teaching":

- location MUST be set at materialization time
- Missing location → hard failure (or strict debug failure in demo mode)
- No read-time resolution from Student Group Schedule is allowed

**Interpretation**

Missing location means: blocks the employee, not a room.

This is intentional and required for duties and non-room commitments.

**Status**

- Teaching location mandatory is LOCKED

### Decision 3 — Teaching Materialization Strategy

**Decision**
Teaching sessions are fully materialized into Employee Booking.

**Authoritative pipeline**

All teaching materialization happens in:

```text
ifitwala_ed/schedule/student_group_employee_booking.py
```

No other module may create or infer teaching bookings.

**Required fields for Teaching bookings**

- employee
- from_datetime
- to_datetime
- location (mandatory)
- booking_type = "Teaching"
- source_doctype = "Student Group"
- source_name = <student_group>

**Explicit exclusions**

Employee Booking MUST NOT store:

- rotation_day
- block_number

Datetime is the universal operational contract.

**Status**

- Employee Booking is the teaching fact table

### Decision 4 — Staff Calendar Event Identity

**Decision**
Staff calendars are booking-driven, not schedule-driven.

**Canonical identity**

For Teaching events:

```text
sg-booking::<employee_booking.name>
```

**Forbidden**

- Schedule-based event IDs in staff calendars
- Schedule fallback when bookings exist
- Mixed ID models

**Allowed**

Schedule-based views ONLY in:

- explicit abstract/debug viewers
- developer tools
- non-operational schedule previews

**Status**

- Booking-based IDs are LOCKED

### Decision 5 — Calendar Read Rules

**Decision**
Calendar APIs are read-only aggregators.

**Calendars MAY read**

- Employee Booking
- Meeting
- School Event

**Calendars MUST NOT**

- Query Student Group Schedule
- Reconstruct schedule context
- Infer missing location, block, or rotation
- "Repair" incomplete data

**Optional UI labels**

Block / Rotation labels:

- MAY be displayed only if deterministically resolvable
- MUST NOT affect conflicts, availability, or identity
- MUST disappear if not strictly resolvable

**Status**

- No inference at read time is LOCKED

### Decision 6 — Room Conflict Helper

**Decision**
There is exactly ONE canonical room conflict helper.

**Rule**

All room conflict checks MUST go through a single function, e.g.:

```text
find_room_conflicts(location, start, end)
```

**This helper merges**

- Employee Booking (with location)
- Meeting
- School Event

**Forbidden**

- Ad-hoc room SQL in feature modules
- Multiple competing conflict helpers
- Schedule-based room conflict logic

**Status**

- Single helper rule is LOCKED

### Decision 7 — Rebuild Triggers

**Decision**
Rebuilds are write-triggered only, never read-triggered.

**Allowed triggers**

- Student Group Schedule change
- Instructor assignment change
- Location change
- Explicit admin action

**Forbidden**

- Rebuild during calendar reads
- Rebuild during availability queries

**Rebuilds MUST be**

- Debounced
- Bounded (group + date window)
- Idempotent

**Status**

- No rebuild on read is LOCKED

### Decision 8 — Rebuild Safety (No Transient Emptiness)

**Decision**
Rebuilds MUST NOT create "temporary free" states.

**Required pattern**

- Compute target slots
- Upsert bookings
- Delete obsolete bookings

**Forbidden**

- Delete-all-then-recreate for active windows

**Rationale**

"Absence means free" must remain safe even if rebuild fails mid-way.

**Status**

- No transient emptiness is LOCKED

### Decision 9 — Incremental Rebuild Preference

**Decision**
Rebuilds should be incremental whenever possible.

**Preferred**

- Single schedule row change → rebuild affected blocks only

**Allowed full rebuild**

- Academic year change
- Structural schedule change
- Explicit admin command

**Status**

- Incremental rebuild preference is LOCKED

### Decision 10 — Data Migration Requirement

**Decision**
A one-time backfill is REQUIRED.

**Required actions**

- Rebuild teaching Employee Bookings
- Populate location for all Teaching rows
- Remove legacy schedule-derived artifacts

**Status**

- Migration is REQUIRED before refactor completion

### Final Authority Statement

- Employee Booking is operational truth
- Student Group Schedule is intent only
- Calendars are aggregation only
- Availability is materialized only
- Inference at read time is forbidden

---

## School & Location Hierarchy Rules

### School Scope

- Selecting **School A** includes:
  - School A
  - All descendant schools (NestedSet)

- Selecting **School B** includes:
  - School B only
  - NOT its parent
  - NOT its siblings

This applies consistently to:

- Rooms
- Bookings
- Meetings
- Analytics

### Location Hierarchy

- Location is a NestedSet
- is_group = 1 → structural node
- is_group = 0 → real room

Only real rooms participate in availability.

---

## API Design Rules (Frappe)

### POST Invariant (Critical)

When using frappe-ui resources:

- POST requests MUST use resource.submit(payload)
- NEVER mix GET-style params with POST endpoints

This is a known failure mode and is treated as a hard invariant.

### Time & Timezone Rules

- Always use Frappe site timezone (System Settings)
- Never rely on server OS timezone
- Never compute availability with naive datetimes
- Display times as HH:MM (no seconds)

---

## Vue + frappe-ui Architecture Rules

### Frontend Stack (Locked)

- Vue 3
- Tailwind CSS (only styling system)
- frappe-ui data utilities

No Bootstrap. No ad-hoc CSS frameworks.

### Data Access Rules

Preferred utilities:

- createResource
- createListResource
- createDocumentResource

Rules:

- Filters live in ONE reactive object
- Watched with { deep: true }
- Pagination is explicit (start, page_length)
- Changing filters resets pagination

### Routing Rule (SPA)

Inside the Vue SPA:

- Never hardcode /portal/ in routes
- Use named routes or base-less paths

Reason:

- Router uses createWebHistory('/portal')

---

## Performance & Scaling Principles

- Optimize for reads, not writes
- Reads are frequent (200+ staff)
- Writes are rare (schedule edits)

Tradeoff:

- Materialize once
- Query cheaply forever

This is intentional and required for scale.

---

## Debugging Rule (Non-Negotiable)

When availability results are unexpected:

1) Verify expanded slots from iter_student_group_room_slots() (materialization input)
2) Verify materialized Employee Booking rows
3) Verify overlap logic
4) Never "fix" availability by filtering rooms post-query

If results look inverted (everything unavailable),
the bug is in interpretation, not in data absence.

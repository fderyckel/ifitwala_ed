# Calendar Aggregation Architecture

## Status

Active with known implementation split. Canonical note for how portal calendar feeds are assembled, which source each surface reads, where visibility rules live, and where booking facts are mandatory versus where schedule expansion is still used.

Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_core.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/api/calendar_prefs.py`
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/schedule/schedule_utils.py`

Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/api/test_calendar.py`
- `ifitwala_ed/api/test_room_utilization.py`
- no dedicated automated coverage was found for `ifitwala_ed/api/student_calendar.py` in the inspected test set

This document is authoritative for:

- which calendar feeds exist
- which runtime object each feed treats as authoritative
- how source merge and visibility rules work
- where calendar preferences and detail payloads are resolved
- which privacy rules must not be bypassed during refactors

If code and this note disagree, stop and resolve the drift explicitly.

Related architecture:

- `docs/scheduling/01_scheduling_architecture.md`
- `docs/scheduling/03_attendance_architecture.md`
- `docs/enrollment/02_school_calendar_architecture.md`
- `docs/spa/09_event_quick_create_contract.md`
- `docs/spa/15_room_utilization_contract.md`
- `docs/scheduling/employee_booking_notes.md`
- `docs/scheduling/room_booking_notes.md`

---

## 1. Core Definition

### 1.1 Calendar aggregation is a read-model layer

Calendar aggregation in Ifitwala_Ed is not one universal event table.

It is a set of portal and analytics read models that merge multiple operational sources into user-facing feeds.

Those sources include:

- `Employee Booking`
- `Student Group` schedule expansion
- `Meeting`
- `School Event`
- `Staff Calendar Holidays`
- `School Calendar Holidays`
- `Location Booking`

### 1.2 Calendar aggregation is not availability truth by default

Calendar feeds are presentation read models.

They must not be mistaken for the canonical source of:

- room availability truth
- staff availability truth
- attendance truth

When a workflow needs true occupancy or free/busy, it must read the relevant booking fact table rather than scrape merged calendar payloads.

---

## 2. Public API Boundary

Status: Active
Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_core.py`
Test refs:
- `ifitwala_ed/api/test_calendar.py`

`api/calendar.py` is the locked public facade for staff calendar workflows.

It keeps public API paths stable while implementation is split across:

- `calendar_core.py`
- `calendar_staff_feed.py`
- `calendar_details.py`
- `calendar_quick_create.py`
- `calendar_prefs.py`

Refactors may move implementation between those modules, but they must not silently drift the public API boundary without updating docs and dependent contracts.

### 2.1 Shared staff-feed source model

The canonical staff feed sources are defined in `calendar_core.py`:

- `student_group`
- `meeting`
- `school_event`
- `staff_holiday`

`_normalize_sources(...)` owns source filtering and default ordering.

Clients must not invent additional source labels client-side.

---

## 3. Staff Calendar Feed Contract

Status: Active
Code refs:
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_core.py`
- `ifitwala_ed/api/calendar_details.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`

`get_staff_calendar(...)` is the canonical merged feed for logged-in staff users.

It returns one payload containing:

- timezone
- window
- generated timestamp
- merged events
- requested sources
- per-source counts

### 3.1 Staff class events use booking facts

Staff `student_group` events are derived from `Employee Booking` rows with `source_doctype = 'Student Group'`.

This is intentional.

For staff-facing class timelines, the authoritative source is the booking fact table, not direct schedule expansion.

Operational consequence:

- absence of a booking means the staff feed should not assume a staff teaching commitment exists
- booking-derived class events are the correct bridge from abstract timetable intent into operational calendar visibility

### 3.2 Staff holiday events use a two-step fallback

Staff holiday events resolve in this order:

1. `Staff Calendar Holidays` from the best matching `Staff Calendar`
2. fallback to `School Calendar Holidays` via nearest school-calendar lineage

This means staff holiday visibility is school-lineage aware and remains usable when no direct `Staff Calendar` exists.

### 3.3 Meeting and School Event visibility is source-specific

Meetings are included when the user is a participant directly or through the linked employee.

School Events are included when:

- the user is an explicit participant
- or the event is visible through the allowed school ancestry rule used by the staff feed

These visibility rules are source-owned and must not be flattened into one generic “calendar access” check.

### 3.4 Caching

Staff calendar payloads are cached in Redis using a key built from:

- scope subject
- window start/end
- normalized source list

This cache is owned by the calendar feed, not by the SPA.

---

## 4. Student Calendar Feed Contract

Status: Active with known implementation split
Code refs:
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/api/calendar_core.py`
Test refs:
- no dedicated automated coverage was found for this module in the inspected test set

`get_student_calendar(...)` is a separate read model for the logged-in student.

It does not share the same source assembly strategy as the staff feed.

### 4.1 Student class events use schedule expansion

Student class events are expanded from active `Student Group` memberships through `iter_student_group_room_slots(...)`.

This means the student feed currently reads abstract scheduled sessions rather than staff or room booking facts.

That is a real architectural split from the staff feed and must be documented explicitly.

### 4.2 Student school-event visibility is audience-driven

Student school-event visibility is resolved by:

- loading candidate `School Event` rows in the time window
- loading the full event document
- checking audience membership against:
  - public/student-wide audiences
  - student-group audiences
  - student-specific audiences

That audience logic is server-owned.

### 4.3 Student holidays derive from enrolled-group schedules

Student holiday entries are built by:

1. resolving the student's enrolled `Student Group` rows
2. resolving each group's `school_schedule`
3. mapping schedules to `school_calendar`
4. reading `School Calendar Holidays`

This is a group-schedule-derived holiday model, not a generic school-root calendar lookup.

### 4.4 Student meetings are participant-driven

The student calendar now aggregates:

- classes
- school events
- meetings
- holidays

Meeting rows are collected from `Meeting Participant.participant` against the student's
portal user (`Student.student_email`).

Keep student-meeting support in this note, the module docstring, and direct automated tests
aligned in the same change.

---

## 5. Detail Endpoint And Visibility Contract

Status: Active
Code refs:
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/api/calendar.py`
Test refs:
- `ifitwala_ed/api/test_calendar.py`

Calendar detail payloads are not embedded wholesale in feed rows.

They are resolved through dedicated detail endpoints:

- `get_meeting_details(...)`
- `get_school_event_details(...)`
- `get_student_group_event_details(...)`

### 5.1 Student-group event detail supports two event-id shapes

Student-group detail resolution supports:

- `sg-booking::...` for booking-backed class events
- `sg::...` for schedule-expanded class events

This is how one modal contract currently spans both staff and student class feeds.

### 5.2 Access checks remain source-specific

Detail access checks are intentionally separate:

- meetings use participant or desk-read access
- school events use event visibility logic
- student-group events require concrete student-group access

Refactors must not replace these with one broad “calendar event detail” permission shortcut.

---

## 6. Calendar Preferences Contract

Status: Active
Code refs:
- `ifitwala_ed/api/calendar_prefs.py`
- `ifitwala_ed/api/calendar_core.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`

`get_portal_calendar_prefs(...)` is the canonical staff-calendar preference bootstrap.

It resolves:

- system timezone
- weekend days
- default visible slot start
- default visible slot end

### 6.1 Preference resolution follows school lineage

The endpoint resolves employee school context, then walks school lineage to determine:

- effective school calendar when needed
- portal calendar start time
- portal calendar end time

Weekend visibility is then derived from the resolved calendar through the canonical calendar helper.

Clients must not reconstruct weekend or slot-window rules locally from raw school rows.

---

## 7. Location Calendar Contract

Status: Active
Code refs:
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/docs/spa/15_room_utilization_contract.md`
Test refs:
- `ifitwala_ed/api/test_room_utilization.py`

The Location Calendar is not a general calendar feed.

It is an information-only operational surface inside Room Utilization.

### 7.1 Location Calendar reads booking facts only

`get_location_calendar(...)` is allowed to read `Location Booking` rows directly for timeline display.

It must not:

- union `Meeting` titles
- union `School Event` titles
- union raw timetable rows
- rebuild occupancy from staff calendar feeds

### 7.2 Privacy rule

Location Calendar titles are intentionally redacted to occupancy labels such as:

- `Teaching`
- `Meeting`
- `School Event`

When a location group is selected, the label may append the concrete room name for operational clarity.

It must not leak source document titles merely because a booking exists.

---

## 8. Calendar Source Authority Rules

Status: Locked
Code refs:
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/docs/scheduling/employee_booking_notes.md`
- `ifitwala_ed/docs/scheduling/room_booking_notes.md`

The current authoritative source rules are:

| Surface | Class / teaching source | Meeting source | School-event source | Holiday source | Availability truth |
| --- | --- | --- | --- | --- | --- |
| Staff calendar | `Employee Booking` | `Meeting` + `Meeting Participant` | `School Event` with source-specific visibility | `Staff Calendar` then `School Calendar` fallback | not this feed; use booking tables |
| Student calendar | `Student Group` schedule expansion | not implemented in inspected code | `School Event` audience checks | `School Calendar` via enrolled-group schedules | not this feed; use canonical domain reads |
| Location calendar | none | none directly; only redacted room occupancy labels | none directly; only redacted room occupancy labels | none | `Location Booking` |

This asymmetry is deliberate current reality and must be preserved unless architecture is explicitly changed.

---

## 9. Concurrency And Request Design

Status: Active
Code refs:
- `ifitwala_ed/api/calendar_core.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_prefs.py`
- `ifitwala_ed/api/student_calendar.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`

Calendar aggregation is a hot-path SPA support domain.

Current runtime already applies bounded read-model rules:

- one aggregated staff calendar endpoint
- one aggregated staff preference endpoint
- one aggregated student calendar endpoint
- one bounded location calendar endpoint
- Redis-backed caching for staff and student feeds

Refactors must preserve:

- no client waterfall per source
- no per-event detail fetch during initial feed load
- no client-owned source merge logic
- no duplication of school-lineage or weekend-day resolution across multiple endpoints

If a change requires extra per-source fetches from the SPA to reassemble the same feed, it is a regression against the concurrency contract.

---

## 10. Known Drift And Refactor Constraints

Status: Active with explicit drift
Code refs:
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/calendar_details.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/api/test_room_utilization.py`

### 10.1 Staff and student class feeds do not share one source of truth

Staff class events are booking-backed.

Student class events are schedule-expanded.

Do not assume the same event-id semantics, missing-event semantics, or occupancy guarantees across both surfaces.

### 10.2 Student calendar coverage is weaker

`student_calendar.py` now has direct automated coverage for:

- meeting aggregation in the student feed
- student-calendar cache invalidation helpers

Changes to student calendar aggregation still require explicit verification instead of relying
only on adjacent staff-calendar tests.

### 10.3 Feed docs must stay aligned with student-meeting support

Student-meeting support is implemented.

If the participant join, source visibility rules, or cache ownership change, update this note and
the module contract in the same change.

---

## 11. Non-Negotiable Refactor Rules

Status: Locked
Code refs:
- `ifitwala_ed/api/calendar.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/student_calendar.py`
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/api/room_utilization.py`

When refactoring calendar aggregation:

1. Keep `api/calendar.py` as the stable public facade for staff-calendar workflows unless the API contract is explicitly changed.
2. Keep source-specific visibility rules server-owned.
3. Do not replace booking-backed staff class events with raw schedule expansion.
4. Do not replace the Location Calendar with source-document hydration that leaks titles.
5. Do not claim a cross-surface unified event model where the runtime still has staff-booking ids and student-schedule ids.
6. Update this note together with code if student meetings, unified class-event ids, or source authority rules change.

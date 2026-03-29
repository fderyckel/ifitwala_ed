# School Calendar Architecture

## Status

Active. Canonical note for School Calendar authoring, term resolution, and calendar resolution for consumers.

Code refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.json`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/api/calendar_prefs.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/morning_brief.py`

Test refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/test_school_calendar.py`
- `ifitwala_ed/api/test_portal_calendar.py`
- `ifitwala_ed/school_settings/doctype/school_schedule/test_school_schedule.py`

This note defines the implemented School Calendar contract.

It complements:

- `01_academic_year_architecture.md`
- `03_enrollment_architecture.md`

---

## 1. Canonical Model

School Calendar is an explicit, school-scoped execution artifact.

It is not an inferred byproduct of Academic Year.

It owns:

- holiday and break dates
- resolved term table
- operational calendar context for downstream consumers

It must always be attached to:

- one `School`
- one `Academic Year`

---

## 2. Authoring Rules

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.json`
Test refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/test_school_calendar.py`

### 2.1 Explicit school scope is mandatory

`School Calendar.school` is required.

The model does not support a floating or implicit calendar.

### 2.2 Academic Year hierarchy rule

The calendar school must sit within the Academic Year hierarchy.

Current runtime allows:

- a calendar on the same school as the Academic Year
- a calendar on a descendant school of the Academic Year school

This is what allows a leaf school to consume an ancestor-hosted Academic Year safely.

### 2.3 Uniqueness

There is at most one `School Calendar` per `(school, academic_year)`.

### 2.4 Holiday constraints

Holiday dates must remain inside the selected Academic Year.

Duplicate holiday dates are rejected.

---

## 3. Term Resolution Contract

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
Test refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/test_school_calendar.py`

School Calendar validation repopulates its term table through `resolve_terms_for_school_calendar(...)`.

The implemented resolution order is:

1. school-scoped `Term` rows for that school
2. nearest-ancestor `Term` rows
3. global template `Term` rows where `school` is not set

Important boundary:

- global terms are templates
- they become operational only when resolved through a School Calendar

Do not document global terms as independently operational instructional records.

---

## 4. Consumer Resolution Contract

Status: Active
Code refs:
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/api/calendar_prefs.py`
- `ifitwala_ed/api/calendar_staff_feed.py`
- `ifitwala_ed/api/morning_brief.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`

Portal, attendance, analytics, and other consumers must resolve calendars through `resolve_school_calendars_for_window(...)`.

That resolver:

- matches calendars by Academic Year overlap with the requested window
- restricts candidates to the school lineage (`self -> ancestors`)
- keeps the nearest-school calendar per Academic Year

This means parent-school calendars are allowed and may be consumed by descendants, but only through explicit resolution.

There is no silent inheritance contract outside the resolver.

---

## 5. Parent-School Calendars

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
Test refs:
- `ifitwala_ed/api/test_portal_calendar.py`

Parent-school calendars are valid authored calendars.

What the current code supports:

- defining a calendar on a parent school
- resolving that calendar for descendant consumers when it is the nearest valid calendar for the window

What the current code does not encode:

- a separate non-instructional parent-calendar mode
- a parent-vs-leaf authority flag

Do not document those distinctions as if they are implemented behavior.

---

## 6. Desk Calendar Endpoint Contract

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py`
- `ifitwala_ed/school_settings/doctype/school_calendar/school_calendar_calendar.js`
Test refs:
- `ifitwala_ed/school_settings/doctype/school_calendar/test_school_calendar.py`

The Desk calendar view for `School Calendar` does not reliably send `filters` as a dict.

Implemented request-shape rules:

- `filters` may arrive as a JSON object, a JSON list, or the empty list string `[]`
- Desk list-style filters may be shaped like `[doctype, fieldname, condition, value, hidden]`
- the backend calendar endpoint must normalize the payload before reading filter values

Implemented resolution rules:

- if `school_calendar` is provided, fetch that exact calendar
- otherwise require the `(school, academic_year)` pair
- if the filter set is empty or incomplete, return an empty event list instead of raising during initial calendar load

Guardrail:

- do not call `.get(...)` on raw `filters` input in Desk calendar endpoints unless the payload has already been normalized

---

## 7. Anti-Patterns

The following are drift:

- documenting School Calendar as optional or implicit
- documenting parent calendars as a special type when the model has no such field or mode
- documenting global terms as operational by themselves
- bypassing `resolve_school_calendars_for_window(...)` with ad hoc lineage logic
- assuming Desk calendar `filters` is always a dict in whitelisted event endpoints

---

## 8. Relationship To Enrollment

Enrollment consumes Academic Year explicitly and may rely on School Calendar indirectly through schedule and attendance domains.

School Calendar is not the source of enrollment truth.

It is a time and operational-calendar support model that downstream consumers must resolve consistently.

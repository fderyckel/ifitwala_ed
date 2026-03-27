---
title: "Program Offering Selection Window: Time-Bound Self-Enrollment Campaign"
slug: program-offering-selection-window
category: Enrollment
doc_order: 3
version: "1.0.1"
last_change_date: "2026-03-27"
summary: "Launch one time-bound student or guardian self-enrollment campaign for a Program Offering and Academic Year, pre-create draft Program Enrollment Requests, and collect choices through the portal without bypassing the request-first architecture."
seo_title: "Program Offering Selection Window: Time-Bound Self-Enrollment Campaign"
seo_description: "Launch portal self-enrollment for one Program Offering and Academic Year while keeping Program Enrollment Request as the canonical staging object."
---

## Program Offering Selection Window: Time-Bound Self-Enrollment Campaign

`Program Offering Selection Window` is the operational object that opens self-enrollment for one `Program Offering` + one `Academic Year` on either the student or guardian portal.

It does not replace [**Program Enrollment Request**](/docs/en/program-enrollment-request/). It prepares and governs those requests.

## Before You Start (Prerequisites)

- Configure the target [**Program Offering**](/docs/en/program-offering/) with offering courses, basket-group memberships, and enrollment rules.
- Enable `Allow Self Enroll` on the target offering.
- Choose the audience:
  - `Guardian` for school-style family confirmation
  - `Student` for university / college self-service
- Decide the source population:
  - current `Program Enrollment`
  - `Cohort`
  - manual student list

<Callout type="info" title="Request-first contract preserved">
Opening a selection window never writes committed enrollment directly. It batch-prepares draft `Program Enrollment Request` rows first, then portal users complete or submit those requests.
</Callout>

## Why It Matters

- Gives schools a due-date driven course-selection workflow without forcing staff to create every request by hand.
- Keeps required courses visible and locked while exposing only the actual choices to students or guardians.
- Reuses the same request seeding rules as [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/), so rollover and portal-launch paths do not drift apart.

## Workflow

1. Create a window for one `Program Offering` + `Academic Year`.
2. Choose `Audience` (`Guardian` or `Student`).
3. Choose `Source Mode` (`Program Enrollment`, `Cohort`, or `Manual`).
4. Load students into the window.
5. Click `Prepare Requests`.
6. The server creates one draft `Program Enrollment Request` per student:
   - all required offering courses are already present
   - deterministic carry-forward choices are included when possible
   - unresolved optional choices remain for the portal user
7. Open the window.
8. Student or guardian portal users save drafts and submit selections before the deadline.
   - portal submission proceeds only when the current choices pass live validation
   - if validation still needs attention, the request stays in `Draft` and the portal explains what must be fixed first
9. Staff review, validate, approve, and materialize the resulting requests later.

## Portal Behavior

- Required courses remain visible but not removable.
- Optional / elective choices stay editable while the window is open and the linked request is still `Draft`.
- The portal uses live validation before submission, so "ready to submit" matches the real request validation outcome.
- After submission, the linked request becomes read-only in the portal.
- Closed windows remain visible in the portal as read-only records so families or students can still see what was submitted or which deadline was missed.
- Guardian visibility is always child-scoped from server-resolved links; students can only access their own window rows.
- Students who already have a committed target `Program Enrollment` are skipped during request preparation and removed from the active window population.

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- **Child table schema file**: `ifitwala_ed/schedule/doctype/program_offering_selection_window_student/program_offering_selection_window_student.json`
- **Required fields (`reqd=1`)**:
  - `program_offering` (`Link`)
  - `academic_year` (`Link`)
  - `audience` (`Select`)
  - `status` (`Select`)
  - `source_mode` (`Select`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**:
  - document method `load_students()` (whitelisted)
  - document method `prepare_requests()` (whitelisted)
  - document method `open_window()` (whitelisted)
  - document method `close_window()` (whitelisted)

- **DocType**: `Program Offering Selection Window` (`ifitwala_ed/schedule/doctype/program_offering_selection_window/`)
- **Autoname**: `format:SEW-{YYYY}-{####}`
- **Controller guarantees**:
  - target `academic_year` must belong to the chosen offering
  - target offering must have `allow_self_enroll = 1`
  - portal audience is explicit (`Guardian` or `Student`)
  - source population can be loaded from current enrollment, cohort, or manual rows
  - request preparation links each student row to one `Program Enrollment Request`
  - existing active requests are reused instead of duplicated

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |

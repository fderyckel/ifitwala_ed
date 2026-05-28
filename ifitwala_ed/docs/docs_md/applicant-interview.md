---
title: "Applicant Interview: Interview Event Record"
slug: applicant-interview
category: Admission
doc_order: 8
version: "1.10.0"
last_change_date: "2026-05-26"
summary: "Record admissions interview events, participants, room/calendar projection, and operational context while keeping interviewer opinions in Applicant Interview Feedback."
seo_title: "Applicant Interview: Interview Event Record"
seo_description: "Use Applicant Interview to schedule and manage interview events while storing per-interviewer opinions in Applicant Interview Feedback."
---

## What Is an Applicant Interview?

`Applicant Interview` records an admissions interview event for a Student Applicant. It captures when the interview happens, who participates, what mode or room is used, and what operational context staff need to run it.

It does not store shared panel opinions. Each interviewer's notes and recommendation belong in [**Applicant Interview Feedback**](/docs/en/applicant-interview-feedback/), so every interviewer has their own accountable record.

<Callout type="info" title="Why Ifitwala Ed is different">
Interview scheduling, calendar projection, room/employee conflict checks, staff workspace access, and per-interviewer feedback are connected without mixing event logistics with evaluative opinion.
</Callout>

## Why This Matters

- **Interviews become visible admissions evidence.** The applicant record shows interview history and latest interview context.
- **Scheduling can check conflicts.** The Schedule Interview flow creates the interview and calendar artifacts together.
- **Interviewers have personal feedback rows.** Notes do not collide in one shared parent field.
- **Staff can open interview workspace from context.** Calendar and Admissions Cockpit entry points lead back to the applicant/interview workspace.
- **Interviewers see pending feedback in Focus.** Listed interviewers get a Focus item until their own feedback is submitted.
- **Readiness summaries can show interview completion.** The applicant record can show interview count and feedback completion status.

## Before You Schedule Interviews

You should have:

- the [**Student Applicant**](/docs/en/student-applicant/) record
- interview date/time, participants, mode, and room ready where relevant
- interviewer users present in the system
- interviewers selected from users with role `Employee`

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Student Applicant | Applicant connected to the interview | Keeps interview evidence in applicant context |
| Interview date/time | Scheduled interview window | Supports calendar projection and conflict checks |
| Mode and room | In person, online, phone, and room where applicable | Helps staff prepare and book resources |
| Interview type | Family, student, or joint | Clarifies the purpose of the interaction |
| Interviewers | Users participating as interviewers | Controls feedback access and completion |
| Operational notes | Context for running the interview | Not used as interviewer opinion |
| School Event | Linked calendar projection | Makes interviews appear in staff scheduling surfaces |
| Feedback rows | Per-interviewer notes and recommendation | Stores actual evaluative feedback separately |

## How This Fits the Admissions Workflow

<Steps title="Applicant Interview flow">
  <Step title="Schedule from applicant context">
    Use Student Applicant or Admissions Cockpit Schedule Interview actions rather than raw Desk creation.
  </Step>
  <Step title="Check conflicts">
    The scheduling flow checks interviewer and room availability and returns structured conflict responses when needed.
  </Step>
  <Step title="Create calendar artifacts">
    Scheduling creates Applicant Interview, linked School Event, Employee Booking rows, and Location Booking when a room is selected.
  </Step>
  <Step title="Run the interview">
    Staff use the workspace from calendar, cockpit, or Focus to see applicant context and interview details.
  </Step>
  <Step title="Capture feedback">
    Each listed interviewer saves their own Applicant Interview Feedback row as Draft or Submitted.
  </Step>
</Steps>

## Permission Matrix

Admissions and academic admin roles manage interview records in applicant scope. Listed interviewers can read assigned interview rows and write only their own feedback through the feedback workflow.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Global privileged access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| Listed interviewer | Yes | No | No | No | Can access only interviews where they are listed |

Runtime rules:

- staff roles are evaluated against applicant scope before create/update/read
- non-admissions employees listed in `interviewers` can read only assigned interview rows
- delegated overall-application reviewers with an open assignment can open interview workspace payloads read-only
- parent interview editing stays staff-managed
- interviewer writes happen only through Applicant Interview Feedback
- records are blocked when linked applicant is `Rejected` or `Promoted`

## Practical Examples

### In-person interview

Admissions schedules a joint family/student interview, selects interviewers and a room, and the system creates the calendar projection and bookings if no conflicts exist.

### Calendar entry to workspace

A staff member clicks the School Event from StaffHome calendar. If the event references an Applicant Interview, it opens the interview workspace.

### Personal interviewer notes

Two interviewers attend the same interview. Each uses their own feedback row, so one person's recommendation does not overwrite the other's notes.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use Schedule Interview from Student Applicant or Admissions Cockpit.</Do>
  <Do>Create separate interview rows for separate interactions.</Do>
  <Do>Keep operational notes on the interview and opinion notes in feedback rows.</Do>
  <Dont>Create raw Applicant Interview records when scheduling checks are needed.</Dont>
  <Dont>Use parent interview notes as a shared panel decision.</Dont>
  <Dont>Keep overwriting one interview row for multiple meetings.</Dont>
</DoDont>

## Common Questions

### Why is feedback separate?

Feedback is per interviewer. Separate rows prevent collisions and preserve accountability by user and timestamp.

### Can applicants without portal users be scheduled?

Yes. Applicant user participation is not required for calendar projection.

### Does interview count block readiness?

Interview count is tracked and appears in readiness summaries, but the current ready boolean blocks on policies, documents, and health, not interview count.

## Related Docs

<RelatedDocs
  slugs="student-applicant,applicant-interview-feedback,applicant-health-profile,applicant-document"
  title="Continue With Related Applicant Review Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
  - `interview_date` (`Date`)
- **Autoname**: expression `INTERVIEW-.YY.-.MM.-.###`
- **Lifecycle hooks in controller**: `validate`, `after_insert`, `on_update`
- **Operational/public methods**:
  - `get_interview_schedule_options(...)`
  - `schedule_applicant_interview(...)`
  - `suggest_interview_slots(...)`
  - `get_interview_workspace(...)`
  - `get_applicant_workspace(...)`
  - `save_my_interview_feedback(...)`
  - `get_permission_query_conditions(...)`
  - `has_permission(...)`

### Scheduling Contract

- Event-context field `notes` is operational context only; not interviewer feedback.
- Scheduling fields:
  - `interview_start`
  - `interview_end`
  - `location` (`Location`, labeled `Room`)
  - `school_event`
- Datetime invariant:
  - when either start or end is set, both are required
  - `interview_end` must be strictly after `interview_start`
  - `interview_date` syncs from `interview_start`
- In-person interviews require `location`; online/phone interviews may omit it.
- `schedule_applicant_interview(...)` checks Employee Booking and Location Booking conflicts before insert.
- Conflict payloads use `EMPLOYEE_CONFLICT`, `ROOM_CONFLICT`, or `SCHEDULING_CONFLICT` and include suggested free times when available.
- Linked School Event rows use:
  - `reference_type = "Applicant Interview"`
  - `reference_name = <interview name>`
  - `location = <room>` when selected
  - audience row `Custom Users`
  - participants = selected interviewer users
- Linked School Event projection is resynced when scheduled interview time, room, applicant, or interviewer panel changes.

### Desk and Workspace Surfaces

- Parent doctype form: `ifitwala_ed/admission/doctype/applicant_interview/`
- Child table: `Applicant Interviewer`
- Form script filters `interviewers.interviewer` to users with role `Employee`.
- Form script defaults new docs to current date and appends current session user to interviewer rows when missing.
- `Open My Feedback` appears only to listed interviewers and routes to existing/prefilled Applicant Interview Feedback.
- StaffHome Focus shows `applicant_interview.feedback.submit` for listed interviewers until their own feedback is `Submitted`.
- Student Applicant readiness uses `has_required_interviews()`.
- Create/update posts audit comments onto applicant timeline.
- Admissions cockpit cards expose Schedule Interview, latest interview context, and open action.
- Workspace interview rows show compact feedback completion from Applicant Interview Feedback.
- Guardian drill-in payloads include Student Applicant Guardian intake fields.
- Governed file actions use governed admissions file URLs.

### Per-Interviewer Feedback Model

- Separate DocType: `Applicant Interview Feedback`
- One row per `(applicant_interview, interviewer_user)`
- Unique index enforced in feedback controller
- Fields: strengths, concerns, shared values, other notes, recommendation, status
- SPA writes through `save_my_interview_feedback(...)`
- No combined interview judgment is stored on the parent record.

### Key Hooks and Readiness Nuance

- `validate`: permission + applicant-state guard
- `after_insert`: audit comment "Interview recorded"
- `on_update`: audit comment "Interview updated"
- `StudentApplicant.has_required_interviews()` tracks count and snapshot section
- interview summaries show participant and feedback completion state

---
title: "Applicant Interview: Structured Interview Evidence"
slug: applicant-interview
category: Admission
doc_order: 8
version: "1.6.2"
last_change_date: "2026-03-09"
summary: "Record interview evidence, participants, calendar projection, and per-interviewer feedback with audit trail comments on the Student Applicant timeline."
seo_title: "Applicant Interview: Structured Interview Evidence"
seo_description: "Record interview evidence, participants, calendar projection, and per-interviewer feedback with audit trail comments on the Student Applicant timeline."
---

## Before You Start (Prerequisites)

- Create the `Student Applicant` record first.
- Have interview date/time and participants prepared before creating the record.
- Ensure interviewer users exist in the system for clean participant linkage.
- Interviewer selection is intentionally constrained to users with role `Employee`.

`Applicant Interview` captures interview evidence as part of admissions review. It formalizes interview context and leaves an audit trail on the applicant record.

## What It Captures

- Interview date plus scheduled time window (`interview_start` / `interview_end`) and mode (`In Person`, `Online`, `Phone`)
- Interview type (`Family`, `Student`, `Joint`)
- Confidentiality level
- Outcome impression
- Notes
- Linked scheduling artifact (`school_event`) when created through the scheduling API
- Linked interviewer workspace in StaffHome calendar (only when `School Event.reference_type = Applicant Interview`)
- Per-interviewer feedback rows in `Applicant Interview Feedback` to avoid concurrent edits on one shared notes field

## Child Table (Included in Parent)

`interviewers` uses child table **Applicant Interviewer**:

- `interviewer` -> `User`

Controller logic remains on the parent doctype; child table controller is intentionally empty.

## Where It Is Used Across the ERP

- [**Student Applicant**](/docs/en/student-applicant/):
  - interview count contributes to readiness snapshot
  - create/update events add audit comments on applicant timeline with a direct link to the interview record
- Admission workspace: direct access card under Student Applicant operations.

## Lifecycle and Linked Documents

1. Create one interview record per interview event for the applicant.
   - Desk quick-create entry points:
     - `Student Applicant` form action: `Create Interview`
     - Admissions Cockpit applicant card action: `Create Interview`
   - New interview defaults: `student_applicant`, `interview_date = today`, and current session user appended to `interviewers`.
2. Capture date/time, mode, participants, confidentiality level, and structured notes/outcome.
3. Preferred scheduling path uses `schedule_applicant_interview(...)` to atomically create:
   - `Applicant Interview` (admissions evidence)
   - linked `School Event` (calendar projection with participant audience)
4. Staff can open the same `AdmissionsWorkspaceOverlay` from two entry points:
   - StaffHome calendar (`School Event.reference_type = Applicant Interview`) in interview mode
   - Admissions Cockpit applicant card in applicant mode (file summary + interview list, then drill into a selected interview)
5. Feedback is saved per interviewer via `Applicant Interview Feedback` (`Draft` / `Submitted`).
6. Update interview records as evidence evolves; timeline comments keep a visible audit trail.
7. Interview completion contributes to applicant readiness and admissions decision confidence.

<Callout type="tip" title="Operational pattern">
Use separate interview rows for separate interactions instead of continuously overwriting one row.
</Callout>

<Callout type="info" title="Architecture rule">
Interviewers are child rows for structure only; workflow logic and validations are enforced in the parent doctype.
</Callout>

## Reporting

- No dedicated Script/Query Report currently declares this doctype as `ref_doctype`.

## Related Docs

- [**Student Applicant**](/docs/en/student-applicant/) - readiness and decision flow
- [**Applicant Health Profile**](/docs/en/applicant-health-profile/) - health review component
- [**Applicant Document**](/docs/en/applicant-document/) - file review component
- `Applicant Interview Feedback` - per-interviewer structured notes

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.json`
- **Controller file**: `ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py`
- **Required fields (`reqd=1`)**:
  - `student_applicant` (`Link` -> `Student Applicant`)
  - `interview_date` (`Date`)
- **Scheduling fields**:
  - `interview_start` (`Datetime`, optional but paired with `interview_end`)
  - `interview_end` (`Datetime`, optional but paired with `interview_start`)
  - `school_event` (`Link` -> `School Event`, read-only)
- **Datetime invariant**:
  - when either `interview_start` or `interview_end` is set, both are required
  - `interview_end` must be strictly after `interview_start`
  - `interview_date` is synchronized from `interview_start` when start is present
- **Lifecycle hooks in controller**: `validate`, `after_insert`, `on_update`
- **Operational/public methods**:
  - `schedule_applicant_interview(...)`
  - `suggest_interview_slots(...)`
  - `get_interview_workspace(...)`
  - `get_applicant_workspace(...)`
  - `save_my_interview_feedback(...)`
  - `get_permission_query_conditions(...)`
  - `has_permission(...)`

- **DocType**: `Applicant Interview` (`ifitwala_ed/admission/doctype/applicant_interview/`)
- **Autoname**: `hash`
- **Desk surface**:
  - parent doctype form in `ifitwala_ed/admission/doctype/applicant_interview/`
  - child table `Applicant Interviewer` embedded in parent
  - form script applies interviewer query filter `role = Employee` on `interviewers.interviewer`
  - form script defaults new docs to current date and appends current session user to interviewer rows when missing
- **Student Applicant integration**:
  - readiness snapshot uses `has_required_interviews()`
  - create/update posts audit comments onto applicant timeline with clickable interview links
- **Scheduling projection**:
  - interview scheduling API creates linked `School Event` rows with:
    - `reference_type = "Applicant Interview"`
    - `reference_name = <interview name>`
    - audience row `Custom Users`
    - participants = selected interviewer users (employee-facing calendar surfacing)
  - staff calendar click routing opens interview workspace only for school events with `reference_type = "Applicant Interview"` and a valid `reference_name`
  - applicants without `applicant_user` are still schedulable; applicant user participation is not required for calendar projection
- **Per-interviewer feedback model**:
  - separate doctype `Applicant Interview Feedback` stores one row per `(applicant_interview, interviewer_user)`
  - unique index enforced in doctype controller (`on_doctype_update`)
  - interviewer feedback fields: strengths, concerns, shared values, other notes, recommendation, status (`Draft` / `Submitted`)
  - SPA workspace writes through server API `save_my_interview_feedback(...)` (upsert semantics)
- **Key hooks**:
  - `validate`: permission + applicant-state guard
  - `after_insert`: audit comment "Interview recorded"
  - `on_update`: audit comment "Interview updated" (only on saves after insert)
- **Readiness nuance**:
  - `StudentApplicant.has_required_interviews()` tracks count and snapshot section
  - current `ready` boolean blocks on policies/documents/health, not interview count

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Global privileged access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant organization/school visibility |
| `Interviewer` (listed in `interviewers`) | Yes (row-level) | Yes (row-level, restricted fields) | No | No | Can access only interviews where they are listed |

Runtime controller rule:
- Staff roles (`Admission` roles + `Academic Admin` + `System Manager`) are evaluated against applicant scope before create/update/read.
- Scoped visibility is transfer-aware: access can follow linked student school context (for example, active enrollment/current anchor school) while preserving applicant-history linkage.
- Non-admissions employees listed in `interviewers` can read/write only their assigned interview rows.
- Interviewer write scope on parent interview remains restricted to `notes` and `outcome_impression`; schedule/participant fields stay staff-managed.
- Structured per-interviewer notes should be captured in `Applicant Interview Feedback` from the SPA workspace.
- Records are blocked when linked applicant is in terminal states (`Rejected`, `Promoted`).

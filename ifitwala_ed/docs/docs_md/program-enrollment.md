---
title: "Program Enrollment: Committed Academic Enrollment Truth"
slug: program-enrollment
category: Enrollment
doc_order: 5
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Store one committed enrollment per student/offering/year with source provenance, AY/term integrity checks, and traceable course status transitions."
seo_title: "Program Enrollment: Committed Academic Enrollment Truth"
seo_description: "Store one committed enrollment per student/offering/year with source provenance, AY/term integrity checks, and traceable course status transitions."
---

## Program Enrollment: Committed Academic Enrollment Truth

`Program Enrollment` is the committed record of a student being enrolled in a program offering for a specific academic year.

## Before You Start (Prerequisites)

- Ensure target [**Program Offering**](/docs/en/program-offering/) exists and includes the selected AY.
- Use [**Program Enrollment Request**](/docs/en/program-enrollment-request/) materialization for normal intake flows.
- For non-request inserts (`Admin`/`Migration`), provide explicit override reason and valid role.

<Callout type="warning" title="Provenance is enforced">
`enrollment_source` is immutable once set. Request-source rows must keep a valid linked request and cannot be silently converted from other sources.
</Callout>

## Where It Is Used Across the ERP

- Student active-enrollment truth for operations and downstream analytics.
- Enrollment engine history source for repeat/completion checks.
- Course-level truth rows (`Program Enrollment Course`) for enrolled/dropped/completed states.
- Course add-many workflows and batch enrollment tools.
- Admissions identity-upgrade and post-admission readiness checks (active enrollment presence).

## Lifecycle and Linked Documents

1. Create enrollment via approved request materialization (recommended) or explicit admin/migration path.
2. System syncs spine from offering (`program`, `school`, optional `cohort`, AY membership).
3. Required offering courses can be seeded when creating new enrollment.
4. Course rows progress through `Enrolled`, `Dropped`, `Completed`.
5. Archiving marks historical (non-current) enrollment state.

### Source Modes

- `Request`: created/updated through request materialization path.
- `Admin`: direct administrative creation with override reason and authorized role.
- `Migration`: controlled bulk/migration source with System Manager role.

## Worked Examples

### Example 1: Request Materialization

- Request is `Approved` and `Valid`.
- Materialization creates `Program Enrollment` with:
  - same `student`, `program_offering`, `academic_year`
  - `enrollment_source = Request`
  - `program_enrollment_request` link
  - course rows set to `Enrolled`

### Example 2: Mid-year Drop Traceability

- Staff removes a course row from the grid.
- System converts deletion into a soft `Dropped` row with `dropped_date` and reason to preserve history.

### Example 3: Admin Direct Enrollment

- Authorized admin creates enrollment with `enrollment_source = Admin` and `enrollment_override_reason`.
- Server enforces role and spine invariants before save.

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep one enrollment per `(student, program_offering, academic_year)` and let unique/index guards protect this.</Do>
  <Do>Use `Dropped` status + `dropped_date` instead of hard-removing historical course evidence.</Do>
  <Dont>Create request-source enrollments manually without the request conversion path.</Dont>
  <Dont>Pick terms outside the enrollment AY/offering span.</Dont>
</DoDont>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- **Required fields (`reqd=1`)**:
  - `student` (`Link`)
  - `program` (`Link`)
  - `program_offering` (`Link`)
  - `academic_year` (`Link`)
  - `enrollment_date` (`Date`)
- **Lifecycle hooks in controller**:
  - `before_insert`, `validate`, `before_save`, `on_update`, `on_trash`, `on_doctype_update`
- **Operational/public methods**:
  - document method `get_courses()` (whitelisted)
  - `get_students(...)`
  - `get_academic_years(...)`
  - `get_program_courses_for_enrollment(program_offering)`
  - `get_offering_ay_spine(offering)`
  - `get_valid_terms_with_fallback(school, academic_year)`
  - `candidate_courses_for_add_multiple(program_offering, academic_year, existing)`
  - `academic_year_link_query(...)`

- **DocType**: `Program Enrollment` (`ifitwala_ed/schedule/doctype/program_enrollment/`)
- **Autoname**: `format:PE-{YYYY}-{####}`
- **Child table**:
  - `courses` -> `Program Enrollment Course`
- **Key invariants enforced** (`program_enrollment.py`):
  - offering spine lock (`program`, `school`, optional `cohort` alignment)
  - AY must belong to offering AY spine
  - one active enrollment per student (`archived = 0` guard)
  - no duplicate `(student, program_offering, academic_year)`
  - per-course existence in offering + overlap window checks
  - dropped courses require date (reason nudged)
  - non-request source requires override reason + role gate
- **Indexes and uniqueness**:
  - index on (`student`, `academic_year`)
  - index on (`program_offering`, `academic_year`)
  - unique on (`student`, `program_offering`, `academic_year`)

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Schedule Maker` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | No |
| `Curriculum Coordinator` | Yes | Yes | Yes | No |
| `Admission Officer` | Yes | Yes | Yes | No |
| `Admission Manager` | Yes | Yes | Yes | Yes |
| `Counsellor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/)
- [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/)

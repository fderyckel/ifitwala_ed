---
title: "Program Enrollment: Committed Academic Enrollment Truth"
slug: program-enrollment
category: Enrollment
doc_order: 5
version: "1.2.3"
last_change_date: "2026-03-29"
summary: "Store one committed enrollment per student/offering/year with source provenance, AY and term integrity checks, and traceable course status transitions including required, credited basket-group, and offering-derived term-window snapshots."
seo_title: "Program Enrollment: Committed Academic Enrollment Truth"
seo_description: "Store one committed enrollment per student/offering/year with source provenance, AY and term integrity checks, and traceable course status transitions."
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
- Enrollment engine history source for repeat and completion checks.
- Course-level truth rows (`Program Enrollment Course`) for enrolled, dropped, and completed states.
- Course add-many workflows and batch enrollment tools.
- Admissions identity-upgrade trigger for promoted applicants and post-admission readiness checks.

## Lifecycle and Linked Documents

1. Create enrollment via approved request materialization (recommended) or explicit admin or migration path.
   On a new Desk form without a selected offering, `school` now prefills from the current user's default school and is later overridden by the chosen Program Offering spine when applicable.
2. System syncs spine from offering (`program`, `school`, optional `cohort`, AY membership).
3. Required offering courses can be seeded when creating a new enrollment.
4. Course rows sync `required` from the offering and keep `credited_basket_group` when applicable.
   Request materialization also copies explicit offering term windows into `term_start` / `term_end`, with the same non-term-long fallback bounds used elsewhere when the offering does not pin terms.
5. Course rows progress through `Enrolled`, `Dropped`, `Completed`.
6. Archiving marks historical, non-current enrollment state.
7. When this row becomes the first active enrollment for a promoted applicant, the server can auto-trigger identity upgrade; ordinary edits to an already-active row do not.

### Source Modes

- `Request`: created or updated through request materialization path.
- `Admin`: direct administrative creation with override reason and authorized role.
- `Migration`: controlled bulk or migration source with System Manager role.

## Worked Examples

### Example 1: Request Materialization

- Request is `Approved` and `Valid`.
- Materialization creates `Program Enrollment` with:
  - same `student`, `program_offering`, `academic_year`
  - `enrollment_source = Request`
  - `program_enrollment_request` link
  - course rows set to `Enrolled`
  - `credited_basket_group` copied from the request when applicable
  - `term_start` / `term_end` copied from the offering delivery window when defined

### Example 2: Mid-year Drop Traceability

- Staff removes a course row from the grid.
- System converts deletion into a soft `Dropped` row with `dropped_date` and reason to preserve history.

### Example 3: Admin Direct Enrollment

- Authorized admin creates enrollment with `enrollment_source = Admin` and `enrollment_override_reason`.
- Server enforces role, spine, and course-semantic invariants before save.

## Related Docs

- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Basket Group**](/docs/en/basket-group/)
- [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/)
- [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/)

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
- **Enrollment course snapshot fields**:
  - `required`
  - `credited_basket_group`
  - `term_start`
  - `term_end`
- **Key invariants enforced** (`program_enrollment.py`):
  - offering spine lock (`program`, `school`, optional `cohort` alignment)
  - AY must belong to offering AY spine
  - one active enrollment per student (`archived = 0` guard)
  - first active transition (new active row or unarchive) can auto-trigger admissions identity upgrade for promoted applicants
  - no duplicate `(student, program_offering, academic_year)`
  - per-course existence in offering + overlap window checks
  - enrollment course rows sync `required` from offering semantics
  - invalid `credited_basket_group` values are blocked
  - single-group optional rows auto-fill `credited_basket_group`
  - multi-group optional rows require explicit `credited_basket_group`
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
| `Counselor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |

---
title: "Program Enrollment Request: Transactional Staging for Enrollment"
slug: program-enrollment-request
category: Enrollment
doc_order: 4
version: "1.7.0"
last_change_date: "2026-05-29"
summary: "Capture re-enrollment intent and course choices, run deterministic validation snapshots for affirmative requests, enforce override gates, support intent/course analytics, and approve requests before materializing Program Enrollment."
seo_title: "Program Enrollment Request: Transactional Staging for Enrollment"
seo_description: "Capture enrollment intent, run deterministic validation snapshots, enforce override gates, and approve requests before materializing Program Enrollment."
---

## Program Enrollment Request: Transactional Staging for Enrollment

`Program Enrollment Request` is the mandatory staging object for enrollment intent and validation snapshots before committed enrollment is created.

It remains student-linked even when the request originates in admissions. If admissions uses [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/), the real request is hydrated only after promotion creates `Student`.

## Before You Start (Prerequisites)

- Create target [**Program Offering**](/docs/en/program-offering/) with offering courses, at least one enrollment rule, and, when needed, basket-group memberships.
- Ensure student identity exists.
- Provide at least one request course row, unless the request is recording `Does Not Intend to Enroll` or `Undecided` intent for planning/follow-up.

<Callout type="warning" title="Approval gate">
For affirmative enrollment requests, statuses `Submitted`, `Under Review`, and `Approved` require a validation snapshot aligned with basket content. The target Program Offering must have at least one enrollment rule, such as `MIN_TOTAL_COURSES` with `Value 1 = 1`; otherwise validation is marked not configured. Multi-group optional courses must carry an explicit `applied_basket_group` before an affirmative request can advance.
</Callout>

## Where It Is Used Across the ERP

- Enrollment validation service:
  - `validate_program_enrollment_request(request_name, force=...)`
- Enrollment materialization service:
  - `materialize_program_enrollment_request(request_name, enrollment_date=...)`
- Enrollment engine (`evaluate_enrollment_request`) outputs stored into `validation_payload`
- [**Program Enrollment**](/docs/en/program-enrollment/) request-source linkage (`program_enrollment_request`)
- Batch staff tooling:
  - [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/) prepares, validates, approves, and materializes requests for cohort rollover
- Desk reporting:
  - `Program Enrollment Request Overview` script report supports:
    - student-by-course matrix review
    - course demand summaries
    - selection-window tracker review for submitted, not-submitted, missing-request, intent, and problematic portal responses
  - `Enrollment Intent Course Analytics` summarizes intended course demand before academic admin validates and approves requests
  - the same report now offers:
    - `Approve Valid Requests`
    - `Create Enrollments from Approved`
    - `Approve + Create Enrollments`
    for clean academic requests in the current filtered scope
- Desk shortcut:
  - the `Program Enrollment Request` form includes `Open Request Overview`, which routes staff into the report with school, Academic Year, program, offering, request type, and selection window prefilled when available
- Self-enrollment portal workflow:
  - [**Program Offering Selection Window**](/docs/en/program-offering-selection-window/) pre-creates draft requests and links them to student/guardian portal editing
  - `ifitwala_ed.api.self_enrollment.*` saves and submits portal choices onto the linked request
- Admissions bridge:
  - `hydrate_program_enrollment_request_from_applicant_plan(applicant_enrollment_plan)`
  - read-only provenance from `Student Applicant` / `Applicant Enrollment Plan`

## Lifecycle and Linked Documents

1. Create request (`Draft`) with student, offering, and course basket.
   This may happen directly by staff, through [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/), through admissions hydration, or through [**Program Offering Selection Window**](/docs/en/program-offering-selection-window/) launch.
2. `program`, `school`, and `academic_year` are resolved from the offering context; if the offering has exactly one academic year, the request auto-fills it.
3. Request rows sync `required` from the offering.
4. Optional rows may carry `applied_basket_group` and `choice_rank`.
5. If the governing selection window collects enrollment intent, the request records one of:
   - `Intends to Enroll`
   - `Does Not Intend to Enroll`
   - `Undecided`
6. If request came from portal self-enrollment, `selection_window` records the campaign provenance.
   For affirmative course-choice submissions, the portal keeps the request in `Draft` until the current choices pass live validation; families see plain-language guidance instead of a silent invalid submit.
   If intent is `Does Not Intend to Enroll` or `Undecided`, the portal can submit without course choices and staff sees the response in review/reporting surfaces.
7. Move affirmative requests to `Submitted` / `Under Review`; server runs or refreshes the snapshot when needed.
8. Review `validation_status`, `requires_override`, and reasons in payload.
9. Approve only when request intent is `Intends to Enroll` and the request is valid, or when override is approved with traceability.
10. Materialize approved request into one [**Program Enrollment**](/docs/en/program-enrollment/).
11. For straightforward academic cohorts, staff may use the report batch actions to:
    - approve valid requests only
    - materialize already-approved valid requests only
    - or run the combined approve-and-materialize shortcut
    while skipping invalid, override-required, non-returning, undecided, or already-materialized rows.

### Status and Validation Fields

- `status`: `Draft`, `Submitted`, `Under Review`, `Approved`, `Rejected`, `Cancelled`
- `enrollment_intent`: blank, `Intends to Enroll`, `Does Not Intend to Enroll`, `Undecided`
- `validation_status`: `Not Validated`, `Valid`, `Invalid`
- `validation_payload`: frozen engine output
- override fields: `requires_override`, `override_approved`, `override_reason`, `override_by`, `override_on`

## Worked Examples

### Example 1: Valid Request

1. Request basket:
   - `ESS`, `applied_basket_group = Group 3 Humanities`
   - `History HL`
2. Validation returns `summary.valid = true`
3. Request moves to `Approved`
4. Materialization creates or updates Program Enrollment with `credited_basket_group` copied from the request row

### Example 2: Override-Required Request

1. Validation returns blocked prerequisite or full capacity.
2. System sets `requires_override = 1`, `validation_status = Invalid`.
3. Staff fills `override_reason`, sets `override_approved = 1`.
4. Request can then move to `Approved` and materialize with explicit override provenance.

### Example 3: Admissions-Bridge Hydration

1. Applicant accepts an offer in [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/).
2. Promotion creates `Student`.
3. Server hydrates a draft request with the promoted student, program offering, academic year, and seeded course basket.
4. Academic review still happens on the real request before approval and materialization.

### Example 4: Guardian Portal Selection

1. Staff opens a [**Program Offering Selection Window**](/docs/en/program-offering-selection-window/) for `Guardian`.
2. Server prepares one draft request per child with all required rows already present.
3. Guardian first confirms `Intends to Enroll`, then chooses the optional language course and submits.
4. If the choices pass live validation, the request stays canonical: `status = Submitted`, `selection_window = ...`, `submitted_by = guardian user`.
5. If the guardian chooses `Does Not Intend to Enroll` or `Undecided`, the request can be submitted without course choices and remains outside approval/materialization until staff follow-up changes the intent.
6. If affirmative choices still need attention, the request remains `Draft` and the portal explains what must be fixed first.

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | No | No |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |

Desk visibility is limited to requests whose resolved `school` is inside the user's staff school scope.

## Related Docs

<RelatedDocs
  slugs="program-offering,program-offering-selection-window,basket-group,applicant-enrollment-plan,program-enrollment,student-enrollment-playbook"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- **Desk list file**: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request_list.js`
- **Required fields (`reqd=1`)**:
  - `student` (`Link`)
  - `program_offering` (`Link`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**:
  - `get_offering_catalog(program_offering)`
  - `validate_enrollment_request(request_name)`
  - `Program Enrollment Request Overview` report supports matrix, summary, and selection-window tracker views for staff review
- **Permission hooks**:
  - `get_permission_query_conditions(user)` scopes Desk lists through `Program Enrollment Request.school`
  - `has_permission(doc, ptype, user)` enforces the same school scope at document level
  - List view strips generated linked-title joins for `program_offering` and `student` so scoped permissions do not depend on aliased target-table joins

- **DocType**: `Program Enrollment Request` (`ifitwala_ed/schedule/doctype/program_enrollment_request/`)
- **Autoname**: `format:PER-{YYYY}-{####}`
- **Admissions provenance fields**:
  - `selection_window` (`Link`, read-only)
  - `source_student_applicant` (`Link`, read-only)
  - `source_applicant_enrollment_plan` (`Link`, read-only)
- **Intent field**:
  - `enrollment_intent` (`Select`): blank, `Intends to Enroll`, `Does Not Intend to Enroll`, `Undecided`
- **Request course snapshot fields**:
  - `required`
  - `applied_basket_group`
  - `choice_rank`
- **Controller validation guarantees**:
  - sync `program` and `school` from the selected offering on save
  - require `academic_year` to belong to the selected offering
  - auto-fill `academic_year` when the offering exposes exactly one academic year
  - require explicit `academic_year` selection when the offering spans multiple academic years
  - request-kind enforcement (`Academic` or `Activity`)
  - activity requests require `activity_booking`
  - portal self-enrollment provenance through `selection_window`
  - intent-only submission support for `Does Not Intend to Enroll` and `Undecided`
  - `Approved` status is blocked unless `enrollment_intent` is `Intends to Enroll` when intent is recorded
  - request rows sync `required` from offering semantics
  - duplicate course rows are blocked
  - invalid basket-group choices are blocked
  - single-group optional rows auto-fill `applied_basket_group`
  - multi-group optional rows require explicit `applied_basket_group` in gate statuses
  - `choice_rank` requires an `applied_basket_group`
  - status-gated snapshot enforcement
  - basket-change and status-change aware revalidation
  - override approval gate before `Approved`
- **Materialization utility guarantees** (`enrollment_request_utils.py`):
  - only `Approved` + `Valid` + affirmative-intent requests can materialize
  - one enrollment target per `(student, program_offering, academic_year)`
  - request-source lock (`enrollment_source = Request`)
  - idempotent add and update of course rows
  - accepts an explicit enrollment date when a batch tool supplies one
  - copies `required`, `credited_basket_group`, and offering-derived `term_start` / `term_end` into `Program Enrollment Course`

---
title: "Program Enrollment Request: Transactional Staging for Enrollment"
slug: program-enrollment-request
category: Enrollment
doc_order: 4
version: "1.2.0"
last_change_date: "2026-03-11"
summary: "Capture enrollment intent, run deterministic validation snapshots, enforce override gates, and approve requests before materializing Program Enrollment, including basket-group snapshots and requests hydrated from admissions."
seo_title: "Program Enrollment Request: Transactional Staging for Enrollment"
seo_description: "Capture enrollment intent, run deterministic validation snapshots, enforce override gates, and approve requests before materializing Program Enrollment."
---

## Program Enrollment Request: Transactional Staging for Enrollment

`Program Enrollment Request` is the mandatory staging object for enrollment intent and validation snapshots before committed enrollment is created.

It remains student-linked even when the request originates in admissions. If admissions uses [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/), the real request is hydrated only after promotion creates `Student`.

## Before You Start (Prerequisites)

- Create target [**Program Offering**](/docs/en/program-offering/) with offering courses and, when needed, basket-group memberships.
- Ensure student identity exists.
- Provide at least one request course row.

<Callout type="warning" title="Approval gate">
For statuses `Submitted`, `Under Review`, and `Approved`, validation snapshot must exist and remain aligned with basket content. Multi-group optional courses must carry an explicit `applied_basket_group` before the request can advance.
</Callout>

## Where It Is Used Across the ERP

- Enrollment validation service:
  - `validate_program_enrollment_request(request_name, force=...)`
- Enrollment materialization service:
  - `materialize_program_enrollment_request(request_name)`
- Enrollment engine (`evaluate_enrollment_request`) outputs stored into `validation_payload`
- [**Program Enrollment**](/docs/en/program-enrollment/) request-source linkage (`program_enrollment_request`)
- Admissions bridge:
  - `hydrate_program_enrollment_request_from_applicant_plan(applicant_enrollment_plan)`
  - read-only provenance from `Student Applicant` / `Applicant Enrollment Plan`

## Lifecycle and Linked Documents

1. Create request (`Draft`) with student, offering, and course basket.
2. Request rows sync `required` from the offering.
3. Optional rows may carry `applied_basket_group` and `choice_rank`.
4. Move to `Submitted` / `Under Review`; server runs or refreshes the snapshot when needed.
5. Review `validation_status`, `requires_override`, and reasons in payload.
6. Approve only when request is valid, or when override is approved with traceability.
7. Materialize approved request into one [**Program Enrollment**](/docs/en/program-enrollment/).

### Status and Validation Fields

- `status`: `Draft`, `Submitted`, `Under Review`, `Approved`, `Rejected`, `Cancelled`
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

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Basket Group**](/docs/en/basket-group/)
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- **Required fields (`reqd=1`)**:
  - `student` (`Link`)
  - `program_offering` (`Link`)
  - `courses` (`Table`)
- **Lifecycle hooks in controller**: `validate`
- **Operational/public methods**:
  - `get_offering_catalog(program_offering)`
  - `validate_enrollment_request(request_name)`

- **DocType**: `Program Enrollment Request` (`ifitwala_ed/schedule/doctype/program_enrollment_request/`)
- **Autoname**: `format:PER-{YYYY}-{####}`
- **Admissions provenance fields**:
  - `source_student_applicant` (`Link`, read-only)
  - `source_applicant_enrollment_plan` (`Link`, read-only)
- **Request course snapshot fields**:
  - `required`
  - `applied_basket_group`
  - `choice_rank`
- **Controller validation guarantees**:
  - request-kind enforcement (`Academic` or `Activity`)
  - activity requests require `activity_booking`
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
  - only `Approved` + `Valid` requests can materialize
  - one enrollment target per `(student, program_offering, academic_year)`
  - request-source lock (`enrollment_source = Request`)
  - idempotent add and update of course rows
  - copies `required` and `credited_basket_group` into `Program Enrollment Course`

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |

---
title: "Program Enrollment Request: Transactional Staging for Enrollment"
slug: program-enrollment-request
category: Enrollment
doc_order: 4
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Capture enrollment intent, run deterministic validation snapshots, enforce override gates, and approve requests before materializing Program Enrollment."
seo_title: "Program Enrollment Request: Transactional Staging for Enrollment"
seo_description: "Capture enrollment intent, run deterministic validation snapshots, enforce override gates, and approve requests before materializing Program Enrollment."
---

## Program Enrollment Request: Transactional Staging for Enrollment

`Program Enrollment Request` is the mandatory staging object for enrollment intent and validation snapshots before committed enrollment is created.

## Before You Start (Prerequisites)

- Create target [**Program Offering**](/docs/en/program-offering/) with offering courses.
- Ensure student identity exists.
- Provide at least one request course row.

<Callout type="warning" title="Approval gate">
For statuses `Submitted`, `Under Review`, and `Approved`, validation snapshot must exist and remain aligned with basket content.
</Callout>

## Where It Is Used Across the ERP

- Enrollment validation service:
  - `validate_program_enrollment_request(request_name, force=...)`
- Enrollment materialization service:
  - `materialize_program_enrollment_request(request_name)`
- Enrollment engine (`evaluate_enrollment_request`) outputs stored into `validation_payload`.
- [**Program Enrollment**](/docs/en/program-enrollment/) request-source linkage (`program_enrollment_request`).

## Lifecycle and Linked Documents

1. Create request (`Draft`) with student, offering, and course basket.
2. Move to `Submitted` / `Under Review`; server runs/refreshes snapshot when needed.
3. Review `validation_status`, `requires_override`, and reasons in payload.
4. Approve only when request is valid, or when override is approved with traceability.
5. Materialize approved request into one [**Program Enrollment**](/docs/en/program-enrollment/).

### Status and Validation Fields

- `status`: `Draft`, `Submitted`, `Under Review`, `Approved`, `Rejected`, `Cancelled`
- `validation_status`: `Not Validated`, `Valid`, `Invalid`
- `validation_payload`: frozen engine output
- override fields: `requires_override`, `override_approved`, `override_reason`, `override_by`, `override_on`

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep request status transitions aligned with snapshot validity.</Do>
  <Do>Record explicit override metadata when request requires override.</Do>
  <Dont>Approve requests with `validation_status != Valid`.</Dont>
  <Dont>Treat request basket as committed enrollment truth before materialization.</Dont>
</DoDont>

## Worked Examples

### Example 1: Valid Request

1. Request basket: `Biology HL`, `History HL`
2. Validation returns `summary.valid = true`
3. Request moves to `Approved`
4. Materialization creates/updates Program Enrollment with both courses as `Enrolled`

### Example 2: Override-Required Request

1. Validation returns blocked prerequisite or full capacity.
2. System sets `requires_override = 1`, `validation_status = Invalid`.
3. Staff fills `override_reason`, sets `override_approved = 1`.
4. Request can then move to `Approved` and materialize with explicit override provenance.

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
- **Controller validation guarantees**:
  - request-kind enforcement (`Academic` or `Activity`)
  - activity requests require `activity_booking`
  - status-gated snapshot enforcement
  - basket-change/status-change aware revalidation
  - override approval gate before `Approved`
- **Materialization utility guarantees** (`enrollment_request_utils.py`):
  - only `Approved` + `Valid` requests can materialize
  - one enrollment target per `(student, program_offering, academic_year)`
  - request-source lock (`enrollment_source = Request`)
  - idempotent add/update of course rows

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Staff` | Yes | No | No | No |

## Related Docs

- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

---
title: "Student Enrollment Playbook: Curriculum to Ready Enrollment"
slug: student-enrollment-playbook
category: Enrollment
doc_order: 1
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Run the full enrollment workflow end-to-end: prepare curriculum, publish offering constraints, validate requests, materialize Program Enrollment, and finalize course rosters safely."
seo_title: "Student Enrollment Playbook: Curriculum to Ready Enrollment"
seo_description: "Run the full enrollment workflow end-to-end: prepare curriculum, publish offering constraints, validate requests, materialize Program Enrollment, and finalize course rosters safely."
---

## Student Enrollment Playbook: Curriculum to Ready Enrollment

This page is the operational path for enrolling students into programs and courses while preserving the locked enrollment architecture in `docs/enrollment/03_enrollment_notes.md`.

<Callout type="warning" title="Architecture boundary">
`Program Enrollment` is committed truth. Use `Program Enrollment Request` for validation and approval gates; do not treat direct edits as the default intake workflow.
</Callout>

## Before You Start (Prerequisites)

- Create [**Program**](/docs/en/program/) and [**Course**](/docs/en/course/) records in curriculum.
- Build program catalog rows in [**Program Course**](/docs/en/program-course/) and prerequisite rows in [**Program Course Prerequisite**](/docs/en/program-course-prerequisite/) where needed.
- Create at least one [**Program Offering**](/docs/en/program-offering/) with its `offering_academic_years` spine and `offering_courses` basket.
- Confirm AY/Term data exists for the school context.

## End-to-End Flow

1. Prepare curriculum policy (`Program`, catalog rows, prerequisite snapshots).
2. Publish operational availability (`Program Offering`, offering courses, basket rules, capacity model).
3. Capture student intent in [**Program Enrollment Request**](/docs/en/program-enrollment-request/).
4. Validate request snapshot (`validate_program_enrollment_request`).
5. Approve with explicit override if required.
6. Materialize approved request into [**Program Enrollment**](/docs/en/program-enrollment/) (`materialize_program_enrollment_request`).
7. Finalize or adjust course rows using in-product tools:
   - [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/) for cohort/offering rollover
   - [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/) for adding one course across many enrollments

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use request validation snapshots before approval and materialization.</Do>
  <Do>Keep offering AY scope explicit and choose enrollment AY from that spine.</Do>
  <Dont>Bypass request approval and then backfill provenance later.</Dont>
  <Dont>Treat UI success as invariant; rely on server validation and source locks.</Dont>
</DoDont>

## Worked Examples

### Example 1: Standard Academic Request Flow

1. Student requests `Biology HL` and `History HL` in a Program Offering.
2. Staff sets request `status = Submitted`.
3. Server validates prerequisites, attempts, capacity, and basket rules, then stores `validation_payload`.
4. Request becomes `Approved` only if `validation_status = Valid` (or override is approved when required).
5. Staff materializes request; system creates/updates one `Program Enrollment` for `(student, program_offering, academic_year)` and inserts course rows as `Enrolled`.

### Example 2: Override-Gated Approval

1. Request fails prerequisite threshold or capacity with `requires_override = 1`.
2. Staff records `override_reason`, sets `override_approved = 1`, and captures `override_by`/`override_on`.
3. Request can then transition to `Approved` and materialize with explicit provenance.

### Example 3: New-Year Rollover

1. In Program Enrollment Tool, source students from old `Program Enrollment` + AY.
2. Target new Program Offering + new AY.
3. Tool skips duplicates, creates missing enrollments, and returns created/skipped/failed counts.
4. For batches over 100 rows, job runs in queue and publishes realtime completion summary.

## Related Docs

- [**Program**](/docs/en/program/)
- [**Course**](/docs/en/course/)
- [**Program Offering**](/docs/en/program-offering/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/)
- [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/)

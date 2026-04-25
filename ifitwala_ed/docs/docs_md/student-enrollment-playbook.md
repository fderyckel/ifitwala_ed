---
title: "Student Enrollment Playbook: Curriculum to Ready Enrollment"
slug: student-enrollment-playbook
category: Enrollment
doc_order: 1
version: "1.2.0"
last_change_date: "2026-03-11"
summary: "Run the full enrollment workflow end-to-end: prepare curriculum, publish offering constraints, bridge admissions into draft requests safely, validate requests, materialize Program Enrollment, and finalize course rosters with the in-product tools."
seo_title: "Student Enrollment Playbook: Curriculum to Ready Enrollment"
seo_description: "Run the full enrollment workflow end-to-end: prepare curriculum, publish offering constraints, validate requests, materialize Program Enrollment, and finalize course rosters safely."
---

## Student Enrollment Playbook: Curriculum to Ready Enrollment

This page is the operational path for enrolling students into programs and courses while preserving the locked enrollment architecture in `docs/enrollment/03_enrollment_architecture.md`.

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
3. Capture student intent in [**Program Enrollment Request**](/docs/en/program-enrollment-request/), either directly or by hydrating it from an accepted [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) after promotion.
4. Validate request snapshot (`validate_program_enrollment_request`).
5. Approve with explicit override if required.
6. Materialize approved request into [**Program Enrollment**](/docs/en/program-enrollment/) (`materialize_program_enrollment_request`).
7. Finalize or adjust enrollment in-product:
   - [**Program Enrollment Tool**](/docs/en/program-enrollment-tool/) for batch request preparation, validation, approval, and materialization during cohort/offering rollover
   - [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/) for adding one course across many enrollments, including source-course-based course promotion

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
3. Tool prepares draft `Program Enrollment Request` rows for missing students.
4. Staff batch-validates, approves valid requests, and materializes the destination enrollments.
5. For batches over 100 rows, job runs in queue and publishes realtime completion summary.

## Related Docs

<RelatedDocs
  slugs="program,course,program-offering,applicant-enrollment-plan,program-enrollment-request,program-enrollment,program-enrollment-tool,course-enrollment-tool"
  title="Related Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-10)

- **Primary runtime owners**:
  - `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
  - `ifitwala_ed/schedule/enrollment_request_utils.py`
  - `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
  - `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- **Admissions bridge nuance**:
  - when enrollment starts in admissions, the playbook enters at `Applicant Enrollment Plan`
  - the real transactional path still begins only once `Program Enrollment Request` exists

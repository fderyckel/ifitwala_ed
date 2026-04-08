---
title: "Program Enrollment Tool: Batch Request Preparation and Materialization"
slug: program-enrollment-tool
category: Enrollment
doc_order: 6
version: "2.3.1"
last_change_date: "2026-04-05"
summary: "Use one in-product tool to either seed new Program Enrollment Requests from cohorts or existing enrollments, or fetch existing academic requests directly for batch validation, approval, and materialization, while the request report handles filtered approval/materialization shortcuts."
seo_title: "Program Enrollment Tool: Batch Request Preparation and Materialization"
seo_description: "Prepare Program Enrollment Requests in batch for cohorts or existing enrollment populations, then validate, approve, and materialize them into Program Enrollments."
---

## Program Enrollment Tool: Batch Request Preparation and Materialization

`Program Enrollment Tool` is the in-product tool for rollover and batch processing when staff need to move a cohort into the next offering or year without opening each student one by one.

It no longer writes `Program Enrollment` directly as the first step. Its canonical path is:

`source students -> draft Program Enrollment Request -> validate -> approve -> materialize Program Enrollment`

Use the tool when staff need to seed or manage the student population itself. It now also supports an existing-request mode when the requests already exist and staff want one operator surface to fetch, validate, approve, and materialize them in bulk.

When the goal is only to clear non-problematic academic requests quickly inside a filtered report view, use `Program Enrollment Request Overview` instead.

## Before You Start (Prerequisites)

- Choose whether the tool is sourcing:
  - `Program Enrollment`
  - `Cohort`
  - `Program Enrollment Request`
- When sourcing `Program Enrollment` or `Cohort`, set destination (`Destination Program Offering`, `Destination Academic Year`).
- When sourcing `Program Enrollment Request`, set the request scope (`Request Program Offering`, `Request Academic Year`).
- Ensure the destination offering has offering courses and enrollment rules configured.
- Ensure the destination Academic Year has valid start/end dates.

## Why It Matters

- Preserves the locked request-first architecture while keeping the older batch-tool workflow staff rely on.
- Handles large year-end rollover work without per-student navigation.
- Lets staff process straightforward cohorts in one surface, while still stopping on requests that need review.
- Gives staff a lower-friction batch lane when requests already exist, without forcing them into per-request review.
- Shares the same request-seeding engine used by [**Program Offering Selection Window**](/docs/en/program-offering-selection-window/), so staff launch and portal launch do not drift.

<Callout type="info" title="Request-first contract">
The tool prepares `Program Enrollment Request` rows first, then offers batch actions to validate, approve, and materialize them. This keeps override and audit rules intact.
</Callout>

## Supported Source Modes

- `Program Enrollment`
- `Cohort`
- `Program Enrollment Request`

## Workflow

### Mode A: Seed New Requests

1. Choose source `Program Enrollment` or `Cohort`.
2. Load students with `Get Students`.
3. Review students who are already enrolled in the destination offering/year.
4. Click `Prepare Requests`.
5. Click `Validate Requests`.
6. Click `Approve Valid Requests`.
7. Click `Materialize Requests`.

### Mode B: Process Existing Requests

1. Choose source `Program Enrollment Request`.
2. Set `Request Program Offering` and `Request Academic Year`.
3. Click `Get Existing Requests`.
4. Review the loaded request states in the tool grid.
5. Click `Validate Requests`.
6. Click `Approve Valid Requests`.
7. Click `Materialize Requests`.

Download the details CSV for any review items, blockers, or failures.

## What the Tool Carries Forward

- All destination required courses.
- Existing source-course choices when the same course still exists in the destination offering.
- Basket-group resolution when it is deterministic:
  - single-group optional courses auto-fill
  - exact-match source rows reuse their prior credited basket group when valid
  - source basket-group selections can infer a new destination course only when exactly one destination course matches that basket group

If a choice still needs staff judgment, the tool creates the draft request and reports that the request needs review before validation/approval can pass.

## Worked Examples

### Example 1: Primary-Year Language Rollover

- Source: current `Program Enrollment`
- Destination: next-year offering + next Academic Year
- Required courses are seeded automatically.
- A carried-forward language choice is included when the destination offering can resolve it deterministically.

### Example 2: Cohort Launch With Required Courses Only

- Source: `Cohort`
- Destination: one new offering/year
- Result: the tool creates draft requests with required destination courses only, then staff batch-validates, approves, and materializes.

### Example 3: Existing Requests Already Submitted

- Source: `Program Enrollment Request`
- Request scope: one offering + one Academic Year
- Result: staff load the existing academic requests directly, validate the stale drafts or submissions, approve the clean ones, and materialize enrollments without opening each request one by one.

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Schedule Maker` | Yes | Yes | Yes | Yes |
| `Counselor` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Course Enrollment Tool**](/docs/en/course-enrollment-tool/)
- [**Program Offering Selection Window**](/docs/en/program-offering-selection-window/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- **Required fields (`reqd=1`)**:
  - `get_students_from` (`Select`)
  - `target_academic_year` (`Link`, source Academic Year)
- **Operational/public methods**:
  - document method `get_students()` (whitelisted)
  - document method `prepare_requests()` (whitelisted)
  - document method `validate_requests()` (whitelisted)
  - document method `approve_requests()` (whitelisted)
  - document method `materialize_requests()` (whitelisted)
  - `academic_year_link_query(...)`
  - `program_offering_target_ay_query(...)`

- **DocType**: `Program Enrollment Tool` (`ifitwala_ed/schedule/doctype/program_enrollment_tool/`)
- **Single doc**: `issingle = 1`
- **Core behavior**:
  - sources rows from cohort, existing enrollment, or existing academic enrollment requests
  - skips students already enrolled in the destination
  - creates draft `Program Enrollment Request` rows only when no active destination request already exists
  - can fetch the latest active academic request per student for an offering/year and process those requests in place
  - supports batch validation, approval, and materialization
  - uses queue + realtime completion for large batches
  - writes review/blocker/failure detail to CSV when needed

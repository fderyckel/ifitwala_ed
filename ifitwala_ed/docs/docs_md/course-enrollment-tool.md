---
title: "Course Enrollment Tool: Add One Course to Many Enrollments"
slug: course-enrollment-tool
category: Enrollment
doc_order: 7
version: "1.2.1"
last_change_date: "2026-04-25"
summary: "Add one offering course to many Program Enrollments, with optional source-course filtering for course-to-course promotion, server-side eligibility checks, and basket-group safety rules."
seo_title: "Course Enrollment Tool: Add One Course to Many Enrollments"
seo_description: "Add a selected offering course to many eligible students' Program Enrollments, optionally filtered by a source course from a prior offering or year."
---

## Course Enrollment Tool: Add One Course to Many Enrollments

`Course Enrollment Tool` adds one selected destination course to many existing `Program Enrollment` rows.

It is the canonical staff tool for:

- adding one course across a whole cohort
- moving students from one course to the next by filtering from a prior source course
- finishing destination enrollment baskets after batch request materialization

## Before You Start (Prerequisites)

- Select destination `Program Offering`, `Academic Year`, and `Course`.
- Ensure the selected destination course exists in the offering-course rows.
- Ensure target students already have active destination `Program Enrollment`.
- If you are promoting students from one course to the next, fill all three source filters:
  - `Source Program Offering`
  - `Source Academic Year`
  - `Source Course`

## Why It Matters

- Prevents manual per-enrollment course edits.
- Supports low-friction course progression by loading only students who took a selected source course.
- Preserves offering-bound course policy and basket-group rules when adding destination rows.

<Callout type="tip" title="Source-course promotion filter">
When source filters are provided, the tool lists only students whose historical Program Enrollment contains that source course and whose destination enrollment does not already contain the target course.
</Callout>

## Workflow

1. Choose the destination `Program Offering`, `Academic Year`, and `Course`.
2. Optionally choose source offering/year/course to restrict the batch.
3. Load eligible students.
4. Optionally add individual students manually.
5. Click `Add Course`.

## Worked Examples

### Example 1: Add Optional Course Mid-Year

- Destination offering: `IB DP 2026`
- Destination AY: `AY-2026-2027`
- Destination course: `Visual Arts`
- Result: the tool lists students with matching destination enrollments and without an existing `Visual Arts` row.

### Example 2: Promote French 5 to French 6

- Source offering/year/course filter points to `French 5`
- Destination offering/year/course points to `French 6`
- Result: the tool lists only students who took `French 5` and adds `French 6` to their destination enrollments

### Example 3: Basket-Aware Boundary

- Destination course: `ESS`
- Offering basket groups:
  - `ESS -> Group 3 Humanities`
  - `ESS -> Group 4 Sciences`

Result: the tool does not guess the credited basket group. It stops with a clear error so staff use a basket-aware flow instead of creating ambiguous enrollment truth.

## Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Schedule Maker` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |

## Related Docs

<RelatedDocs
  slugs="program-enrollment,program-offering-course,program-enrollment-tool,student-enrollment-playbook"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
- **Required fields (`reqd=1`)**:
  - `program_offering` (`Link`)
  - `academic_year` (`Link`)
  - `course` (`Link`)
- **Optional source filter fields**:
  - `source_program_offering`
  - `source_academic_year`
  - `source_course`
- **Operational/public methods**:
  - document method `add_course_to_program_enrollment()` (whitelisted)
  - `fetch_eligible_students(...)`
  - `get_courses_for_offering(...)`
  - `list_offering_academic_years_desc(...)`

- **DocType**: `Course Enrollment Tool` (`ifitwala_ed/schedule/doctype/course_enrollment_tool/`)
- **Single doc**: `issingle = 1`
- **Server checks**:
  - selected destination AY must be in the destination offering AY set
  - selected destination course must exist in the destination offering-course map
  - destination rows are added only for existing active destination Program Enrollments
  - duplicate destination course rows are prevented
  - source filtering requires all three source fields together
  - source-course filtering is enforced server-side, not just in the link query
  - `required` is synced from destination offering semantics
  - single-group optional courses auto-fill `credited_basket_group`
  - multi-group optional courses are rejected so the tool cannot invent a basket assignment

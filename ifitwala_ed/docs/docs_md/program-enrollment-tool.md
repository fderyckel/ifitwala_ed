---
title: "Program Enrollment Tool: Batch Enrollment Creation"
slug: program-enrollment-tool
category: Enrollment
doc_order: 6
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Use in-product batch workflows to create Program Enrollment rows for cohorts or existing enrollment populations into a new offering/year target."
seo_title: "Program Enrollment Tool: Batch Enrollment Creation"
seo_description: "Use in-product batch workflows to create Program Enrollment rows for cohorts or existing enrollment populations into a new offering/year target."
---

## Program Enrollment Tool: Batch Enrollment Creation

`Program Enrollment Tool` is a single doctype that batches creation of new `Program Enrollment` rows for multiple students.

## Before You Start (Prerequisites)

- Define source filter (`Program Enrollment` or `Cohort`) and load students.
- Set destination (`new_program_offering`, `new_target_academic_year`).
- Ensure target AY has valid start/end dates.

## Why It Matters

- Handles year/offering rollover in-product without manual per-student creation.
- Skips duplicates safely for existing `(student, offering, AY)` combinations.
- Supports large batches with async queue and realtime progress.

<Callout type="info" title="Batch behavior">
If selected students exceed 100 rows, tool enqueues a long job and returns summary via realtime events.
</Callout>

## Supported Source Modes

- Implemented by server `_fetch_students`:
  - `Program Enrollment`
  - `Cohort`
- Present in UI options but currently not implemented in server fetch:
  - `Student Applicant`
  - `Others`

## Workflow

1. Set `get_students_from` and its required filters.
2. Click `Get Students` to populate table.
3. Review duplicates highlighted as `already_enrolled`.
4. Set destination fields and optional `new_enrollment_date`.
5. Click `Enroll Students`.
6. Review summary (`created`, `skipped`, `failed`) and download failure CSV when present.

## Worked Examples

### Example 1: Rollover From Existing Enrollment

- Source: `Program Enrollment`
- Filters: old offering + old AY
- Target: new offering + new AY
- Result: tool creates only missing rows and skips existing targets.

### Example 2: Cohort Launch

- Source: `Cohort`
- Filter: `student_cohort = Grade 10`
- Target: specific program offering and AY
- Result: active students in the cohort receive new Program Enrollment rows.

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use the built-in duplicate checks before running enrollment.</Do>
  <Do>Set `new_enrollment_date` only when it must differ from AY start date.</Do>
  <Dont>Expect `Student Applicant` source to fetch students yet.</Dont>
  <Dont>Assume failed rows abort the entire run; failures are isolated and reported.</Dont>
</DoDont>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- **Required fields (`reqd=1`)**:
  - `get_students_from` (`Select`)
  - `target_academic_year` (`Link`)
- **Lifecycle hooks in controller**: none beyond standard document behavior.
- **Operational/public methods**:
  - document method `get_students()` (whitelisted)
  - document method `enroll_students()` (whitelisted)
  - `academic_year_link_query(...)`
  - `program_offering_target_ay_query(...)`

- **DocType**: `Program Enrollment Tool` (`ifitwala_ed/schedule/doctype/program_enrollment_tool/`)
- **Single doc**: `issingle = 1`
- **Core behavior**:
  - sources students by cohort or existing enrollment
  - validates target AY window and enrollment date
  - creates `Program Enrollment` rows with duplicate guards
  - publishes realtime progress and completion events
  - writes per-row failures to CSV attachment when needed

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Schedule Maker` | Yes | Yes | Yes | Yes |
| `Counselor` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | Yes |

## Related Docs

- [**Program Enrollment**](/docs/en/program-enrollment/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Student Enrollment Playbook**](/docs/en/student-enrollment-playbook/)

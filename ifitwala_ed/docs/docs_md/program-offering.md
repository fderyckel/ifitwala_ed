---
title: "Program Offering: Operational Enrollment Contract"
slug: program-offering
category: Enrollment
doc_order: 2
version: "1.0.0"
last_change_date: "2026-02-28"
summary: "Define where and when a program is delivered, including AY span, offering courses, basket rules, capacity policy, and activity-booking readiness gates."
seo_title: "Program Offering: Operational Enrollment Contract"
seo_description: "Define where and when a program is delivered, including AY span, offering courses, basket rules, capacity policy, and activity-booking readiness gates."
---

## Program Offering: Operational Enrollment Contract

`Program Offering` is the schedule-layer contract for enrollment decisions. It binds a program to a specific school context, AY spine, and enrollment constraints.

## Before You Start (Prerequisites)

- Create base [**Program**](/docs/en/program/) and [**Course**](/docs/en/course/) records.
- Create `Academic Year` records and required `Term` rows for the target school tree.
- Decide offering seat policy and basket-rule policy before request intake opens.

## Why It Matters

- Defines what is actually available now (not just curriculum intent).
- Provides the official AY scope consumed by requests and enrollments.
- Hosts offering-level basket rules and course capacity constraints.
- Enables activity booking with server-side pre-open conflict/readiness gates.

<Callout type="warning" title="School anchoring invariant">
Program Offering must be anchored on a leaf (child) school. Ancestor-aware validation is applied for AY and term references.
</Callout>

## Where It Is Used Across the ERP

- [**Program Enrollment Request**](/docs/en/program-enrollment-request/) target (`program_offering`).
- [**Program Enrollment**](/docs/en/program-enrollment/) canonical spine source (`program`, `school`, `cohort`, AY membership).
- Enrollment engine:
  - offering course list
  - offering basket rules
  - seat-policy capacity counting
- Desk tooling and APIs:
  - catalog/non-catalog hydration helpers
  - AY scoped link queries
  - activity readiness preview API

## Lifecycle and Linked Documents

1. Set identity (`program`, `school`, optional `offering_title`, `grade_scale`).
2. Add `offering_academic_years` rows (must be non-overlapping and ancestry-valid).
3. Configure optional head window (`start_date`, `end_date`) inside AY span.
4. Add [**Program Offering Course**](/docs/en/program-offering-course/) rows.
5. Configure `enrollment_rules` (`Program Offering Enrollment Rule`) and seat policy.
6. Move offering lifecycle (`Planned` -> `Active` -> `Archived`) as operations evolve.

### Activity Booking Mode (Optional)

When `activity_booking_enabled = 1`, server enforces:

- valid activity status (`Draft`, `Ready`, `Open`, `Closed`)
- valid age/waitlist/payment controls
- active activity section integrity
- pre-open readiness checks (location + instructor conflicts)

## Worked Examples

### Example 1: Standard Academic Offering

- Program: `IB DP`
- School: `High School A`
- AY spine: `AY-2026-2027`
- Offering courses include required and elective rows with capacity values.
- Seat policy: `Approved Requests Hold Seats`

Result: enrollment request validation and materialization use this offering as authoritative scope.

### Example 2: Non-catalog Exception

A course not present in Program catalog can appear in offering only when row is explicitly marked `non_catalog = 1` and exception justification is provided (if `exception_reason` exists on the row).

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Keep offering AY rows explicit and ordered to avoid ambiguous enrollment windows.</Do>
  <Do>Use offering course rows as the single operational course set for requests.</Do>
  <Dont>Use global/unscoped AY assumptions outside the offering spine.</Dont>
  <Dont>Open activity booking without resolving readiness conflicts.</Dont>
</DoDont>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/program_offering/program_offering.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- **Required fields (`reqd=1`)**:
  - `program` (`Link`)
  - `school` (`Link`)
- **Lifecycle hooks in controller**: `validate`, `on_doctype_update`
- **Operational/public methods**:
  - `preview_activity_booking_readiness(program_offering)`
  - `compute_program_offering_defaults(program, school, ay_names)`
  - `program_course_options(program, search, exclude_courses)`
  - `hydrate_catalog_rows(program, course_names)`
  - `hydrate_non_catalog_rows(course_names, exception_reason)`
  - `academic_year_link_query(...)`
  - `create_draft_tuition_invoice(program_offering, account_holder, posting_date, items)`

- **DocType**: `Program Offering` (`ifitwala_ed/schedule/doctype/program_offering/`)
- **Key child tables**:
  - `offering_academic_years` -> `Program Offering Academic Year`
  - `offering_courses` -> `Program Offering Course`
  - `enrollment_rules` -> `Program Offering Enrollment Rule`
- **Core validation guarantees** (`program_offering.py`):
  - school must be leaf school
  - AY rows must exist, be ancestry-valid, and non-overlapping
  - head start/end dates must lie within AY span
  - offering-course windows validated against AY/term/head bounds
  - catalog membership enforced unless explicit non-catalog exception
  - status restricted to `Planned|Active|Archived`
  - activity booking guardrails and readiness gates enforced server-side

### Permission Matrix

| Role | Read | Write | Create | Delete |
|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes |
| `Academic Admin` | Yes | Yes | Yes | Yes |
| `Curriculum Coordinator` | Yes | Yes | Yes | Yes |
| `Academic Assistant` | Yes | Yes | Yes | No |
| `Activity Coordinator` | Yes | Yes | Yes | No |
| `Counselor` | Yes | No | No | No |
| `Instructor` | Yes | No | No | No |
| `Academic Staff` | Yes | No | No | No |
| `Admission Manager` | Yes | No | No | No |
| `Admission Officer` | Yes | No | No | No |

## Related Docs

- [**Program Offering Course**](/docs/en/program-offering-course/)
- [**Program Enrollment Request**](/docs/en/program-enrollment-request/)
- [**Program Enrollment**](/docs/en/program-enrollment/)

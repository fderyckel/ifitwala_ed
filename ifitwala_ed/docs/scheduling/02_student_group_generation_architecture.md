# Student Group Generation And Sectioning Architecture

## Status

Active. Canonical note for how sections are represented today, how `Student Group` rows are created and populated in current runtime, and which generation steps are still intentionally non-orchestrated.

Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.js`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.json`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.js`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool_course/student_group_creation_tool_course.json`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`

Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/test_student_group_creation_tool.py` (placeholder only; no behavioral coverage)

This document is authoritative for:

- what a delivery section is in current runtime
- how section creation and roster seeding work today
- what is manual, query-assisted, linked, or not implemented
- which enrollment, offering, and calendar invariants sectioning must preserve

If code and this note disagree, stop and resolve the drift explicitly.

Related architecture:

- `docs/scheduling/01_scheduling_architecture.md`
- `docs/enrollment/03_enrollment_architecture.md`
- `docs/enrollment/08_enrollment_scheduling_contract.md`
- `docs/enrollment/07_year_rollover_architecture.md`
- `docs/docs_md/student-group.md`

---

## 1. Core Definition

### 1.1 What a section is

There is no standalone `Course Section` doctype in the repository.

In current runtime, the delivery-section construct is:

- `Student Group`

That is already stated in enrollment architecture, and this note makes the scheduling side explicit.

### 1.2 What section generation means

Section generation is the act of creating or preparing `Student Group` rows with the correct:

- operational scope
- grouping mode
- roster eligibility
- instructor set
- timetable intent

It does not mean creating `Program Enrollment`.

It does not mean materializing bookings automatically.

---

## 2. Canonical Section Construct

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`
- `ifitwala_ed/docs/enrollment/03_enrollment_architecture.md`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

`Student Group` is the only implemented general-purpose section record for:

- course delivery
- cohort grouping
- activity sections
- pastoral or other operational grouping

This means sectioning currently inherits `Student Group` semantics:

- one group has one explicit mode (`Course`, `Cohort`, `Activity`, `Pastoral`, `Other`)
- one group binds to one `Program Offering` and one `Academic Year`
- one group may carry course, cohort, instructor, roster, and schedule context

Do not document or design around an imaginary parallel section model.

---

## 3. Current Section Creation Lanes

Status: Active but mixed
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.js`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/test_student_group_creation_tool.py` (placeholder only)

There are four distinct creation lanes in current reality.

### 3.1 Manual staff section authoring

This is the main implemented lane.

Staff creates `Student Group` directly and then:

- chooses the grouping mode
- selects `program_offering` and `academic_year`
- optionally chooses `course` or `cohort`
- uses query-assisted student loading
- assigns instructors
- defines schedule rows

This lane is implemented and must be treated as canonical.

### 3.2 Query-assisted roster seeding

The `Student Group` form exposes query-backed student selection helpers.

Those helpers do not create the section itself. They only:

- resolve eligible students from enrollment truth
- exclude conflicting or already-assigned students where required
- keep section population aligned with offering and Academic Year context

This is an operator-assist lane, not an orchestration engine.

### 3.3 Activity section linkage

`Program Offering.activity_sections` links activity booking readiness and allocation to existing `Student Group` rows of type `Activity`.

This lane does not generate groups automatically.

It assumes the referenced activity sections already exist and are scheduling-valid.

### 3.4 Student Group Creation Tool

`Student Group Creation Tool` currently exists as metadata only.

Current runtime reality:

- controller is `pass`
- client script is commented out
- child table schema exists
- there is no implemented server-owned generation workflow

Therefore it must not be documented as a working section generator.

---

## 4. Grouping Modes And Their Meaning

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool_course/student_group_creation_tool_course.json`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

Current sectioning modes are not interchangeable.

| Mode | Meaning | Eligibility model |
| --- | --- | --- |
| `Course` | delivery section for one course, often term-scoped | driven by `Program Enrollment` plus `Program Enrollment Course` |
| `Cohort` | cohort grouping inside offering/AY context | driven by `Program Enrollment` plus cohort |
| `Activity` | operational section used by activity booking workflows | manual or activity-workflow managed |
| `Pastoral` | pastoral grouping | operational/manual |
| `Other` | non-standard grouping | manual |

Refactors must preserve those different meanings instead of collapsing all groups into one generic bucket.

---

## 5. Enrollment Gate For Section Population

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`

Section population consumes committed enrollment truth.

Current rules:

- course sections require matching `Program Enrollment`
- course sections also require matching `Program Enrollment Course` rows for the selected course and term
- cohort sections require matching `Program Enrollment` and matching cohort
- activity and other sections do not use the same automatic eligibility query path

Operational consequence:

- section generation starts after enrollment truth exists
- section generation must not be the thing that invents or repairs enrollment truth

---

## 6. Offering And Calendar Scope Rules

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/schedule_utils.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

Section generation must preserve these scope rules:

1. `program_offering` is the primary operational envelope.
2. `academic_year` must belong to the offering spine.
3. school resolution must stay inside the allowed school-branch intersection between offering and Academic Year.
4. schedule resolution must use the resolved or validated `School Schedule`, not ad hoc block definitions.

This means section generation is not just row creation. It is scoped operational modeling.

---

## 7. Capacity And Sectioning Are Not The Same Layer

Status: Active
Code refs:
- `ifitwala_ed/docs/enrollment/03_enrollment_architecture.md`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

There are two separate capacity concepts:

- allocation capacity on `Program Offering Course` during request and enrollment decisions
- delivery-section capacity on `Student Group` through roster and room constraints

They must not be collapsed into one number or one workflow.

Enrollment approval does not automatically imply a resolved delivery section.

---

## 8. Current Non-Orchestrated Gaps

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/test_student_group_creation_tool.py` (placeholder only)
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`

The following are not implemented as a system-owned section-generation workflow today:

- automatic creation of academic `Student Group` rows when enrollments are materialized
- automatic next-year cloning of sections during rollover
- automatic instructor assignment when sections are created
- automatic course-section balancing or student distribution across multiple groups
- automatic retirement or migration of section rosters when enrollments change

These are real gaps, not hidden features.

They must stay explicit in docs so refactor work does not rely on behavior that does not exist.

---

## 9. Naming, Identity, And Operational Meaning

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.json`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

Section identity currently follows `Student Group` naming rules:

- course and activity groups use abbreviation plus term or Academic Year
- cohort groups use abbreviation plus cohort
- other modes use the abbreviation directly

That identity is operational and user-facing.

Refactors must treat naming as part of the delivery model, not cosmetic detail, because it affects:

- teacher-facing navigation
- instructor logs
- attendance scope
- downstream lesson and task anchors

---

## 10. Anti-Patterns

The following are architectural drift:

- documenting `Student Group Creation Tool` as a working generation engine
- assuming rollover creates sections automatically
- using section creation to silently create or repair enrollment truth
- treating `Program Offering.activity_sections` as if it generates groups instead of linking existing ones
- collapsing course sections, activity sections, and cohort groups into one undocumented generic behavior

---

## 11. Refactor Guardrails

When sectioning is refactored, preserve this sequence:

1. enrollment truth is committed first
2. eligible delivery population is resolved from committed truth
3. sections are created or updated explicitly
4. rosters and schedule rows are authored or generated explicitly
5. bookings are materialized only after the section and timetable exist

If you later introduce a real section generator, it should become the single explicit runtime owner and replace the current partial/manual landscape. Until then, docs must keep the current boundaries honest.

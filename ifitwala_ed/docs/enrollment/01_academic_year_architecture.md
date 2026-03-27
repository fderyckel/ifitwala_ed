# Academic Year Architecture

## Status

Active. Canonical note for Academic Year lifecycle, visibility, Desk visibility, and scoped year closure.

Code refs:
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.py`
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.js`
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.json`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.js`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.json`
- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`

Test refs:
- `ifitwala_ed/school_settings/doctype/academic_year/test_academic_year.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`
- `ifitwala_ed/curriculum/doctype/program/test_program.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
- `ifitwala_ed/utilities/test_school_tree.py`

This document defines the current runtime contract for Academic Year in Ifitwala_Ed.

It complements:

- `03_enrollment_architecture.md`
- `07_year_rollover_architecture.md`
- `04_enrollment_examples.md`
- `02_school_calendar_architecture.md`

---

## 1. Canonical Definition

### 1.1 What Academic Year is

Academic Year is the educational time container for:

- enrollment
- scheduling
- terms
- school calendars
- year-based reporting

It is school-scoped. Each `Academic Year` belongs to one explicit `School`.

### 1.2 What Academic Year is not

Academic Year is not:

- Fiscal Year
- an accounting lock boundary
- a convenience filter inferred from date math
- a proxy for “latest year”

Admissions, enrollment, and reporting must consume explicit Academic Year context rather than inventing it.

---

## 2. Lifecycle and Visibility

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.json`
- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/utilities/school_tree.py`
Test refs:
- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
- `ifitwala_ed/utilities/test_school_tree.py`

The core fields are:

- `school`
- `archived`
- `visible_to_admission`

Locked interpretation:

- `archived = 0` means the year is operational
- `archived = 1` means the year is closed for new operational use
- `visible_to_admission = 1` means it may appear in applicant intent pickers
- `visible_to_admission = 0` means it must not appear in admissions pickers

Lifecycle and visibility are different controls. They must not be conflated.

---

## 3. Naming, Uniqueness, and Visibility Scope

Status: Active
Code refs:
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

### 3.1 Naming and uniqueness

Academic Year names are school-based:

- runtime name = `{School.abbr} {academic_year_name}`

Duplicate `academic_year_name` values are blocked within the same school.

### 3.2 Desk visibility is branch-scoped

Desk visibility for Academic Year includes the user's branch only:

- the user's school
- descendants in that branch
- ancestors in that branch

Sibling branches remain hidden.

This is required so leaf-school operational surfaces such as `Program Offering` can consume ancestor-hosted Academic Year rows without breaking sibling isolation.

### 3.3 Operational link queries may include ancestor years

`Program Offering` academic-year queries intentionally allow ancestor-school Academic Years for a leaf offering.

That is runtime behavior, not a documentation assumption.

---

## 4. Admissions Consumption Rules

Status: Active
Code refs:
- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/utilities/school_tree.py`
Test refs:
- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
- `ifitwala_ed/utilities/test_school_tree.py`

`Student Applicant.academic_year` stores intent only.

It does not create enrollment truth.

Admissions filtering must remain:

- school-tree aware
- `visible_to_admission = 1`
- `archived = 0`

For a given applicant school:

- prefer the applicant school subtree if it has visible, non-archived years
- otherwise fall back to the nearest ancestor scope with visible, non-archived years

Do not replace this with date-based “current year” heuristics.

---

## 5. End of Year Checklist Is The Closure Authority

Status: Implemented
Code refs:
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.json`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.js`
Test refs:
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

`End of Year Checklist` is still a Single doctype, but it is no longer an unscoped button panel.

It now carries:

- `school`
- `academic_year`
- `status`
- resolved scope preview
- explicit archive actions

Closure is governed through that surface, not through ad hoc field changes on `Academic Year`.

### 5.1 Scope model

When the selected school is a leaf:

- scope is that school

When the selected school is a parent:

- scope is that school plus descendants

The UI must show the resolved affected-school list before destructive actions.

### 5.2 Permission model

Parent-school cascade requires:

1. the user's default school to equal the selected parent school
2. the `Academic Admin` role, unless the user is `System Manager`

This is an implemented permission rule, not future intent.

### 5.3 Closure outcomes

The checklist owns scoped closure of:

- `Academic Year` (`archived = 1`, `visible_to_admission = 0`)
- `Term`
- `Program Enrollment`
- `Student Group`

Those actions are designed to be rerunnable without changing the meaning of the end state.

---

## 6. Legacy `retire_ay()` Status

Status: Deprecated legacy helper
Code refs:
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.py`
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.js`
Test refs:
- `ifitwala_ed/school_settings/doctype/academic_year/test_academic_year.py`

`AcademicYear.retire_ay()` is no longer documented as the primary closure path.

Current runtime behavior:

- it is explicitly deprecated
- it requires an explicit `school_scope`
- it archives `Program Enrollment` using that scope
- it remains weaker than the checklist for full closure governance

Use `End of Year Checklist` for real closure work.

---

## 7. Enrollment Alignment

Academic Year is the explicit time container for:

- `Program Offering`
- `Program Offering Selection Window`
- `Program Enrollment Request`
- `Program Enrollment`

Enrollment evaluation must not infer “current year” from dates.

It must consume explicitly chosen Academic Year context from the offering, request, or student context.

---

## 8. Anti-Patterns

The following are bugs, not preferences:

- selecting Academic Year by “latest date” heuristics
- exposing admissions years without checking `visible_to_admission`
- unscoped closure actions across sibling schools
- documenting `End of Year Checklist` as future work

---

## 9. Non-Goals

This note does not define:

- basket rules
- course-choice semantics
- activity booking lifecycle
- school-calendar term resolution details

Those live in the other notes in this folder.

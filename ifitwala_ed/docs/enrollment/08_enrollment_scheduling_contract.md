# Enrollment To Scheduling Contract

## Status

Active. Canonical note for how enrollment truth feeds scheduling, what the bridge points are today, and which gaps remain intentionally non-orchestrated.

Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.js`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
- `ifitwala_ed/api/self_enrollment.py`

Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`
- `ifitwala_ed/api/test_self_enrollment.py`

This document is authoritative for:

- what enrollment must commit before scheduling may rely on it
- how `Program Enrollment` and `Program Enrollment Course` gate rostering
- what today remains manual or separately orchestrated
- what must not be inferred during refactors

If code and this note disagree, stop and resolve the drift explicitly.

Related architecture:

- `docs/enrollment/03_enrollment_architecture.md`
- `docs/enrollment/07_year_rollover_architecture.md`
- `docs/scheduling/01_scheduling_architecture.md`
- `docs/docs_md/student-group.md`

---

## 1. Core Distinction

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

Enrollment and scheduling are adjacent, but they are not the same layer.

Enrollment owns:

- committed academic participation
- offering, program, school, cohort, and Academic Year spine
- approved request provenance
- committed course snapshot on `Program Enrollment Course`

Scheduling owns:

- operational grouping
- instructor assignment
- timetable intent
- room and staff availability projection

One layer may consume the other, but neither may silently replace it.

---

## 2. Canonical Bridge Chain

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

The implemented bridge chain is:

`Program Offering` -> `Program Enrollment Request` -> `Program Enrollment` -> `Program Enrollment Course` -> `Student Group` roster eligibility -> `Student Group Schedule` -> materialized bookings

Important consequences:

- requests and self-enrollment stop at enrollment truth
- scheduling starts after enrollment truth is available
- a roster or timetable does not prove committed academic entitlement by itself

---

## 3. What Enrollment Commits For Scheduling To Consume

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`

The scheduling layer may rely on these committed facts:

1. one active `Program Enrollment` per student, enforced server-side
2. explicit `program_offering`, `program`, `school`, `cohort`, and `academic_year` spine
3. request-source lock and provenance when enrollment came from approved request materialization
4. committed course rows on `Program Enrollment Course`, including term and basket-group semantics carried forward from the request/offering context

This matters because scheduling queries use those exact facts to decide who is eligible for which operational group.

---

## 4. What Scheduling Reads From Enrollment

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/doctype/student_group/student_group.js`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

### 4.1 Course-based groups

Course-based `Student Group` population is offering-first and Academic-Year-first.

Current runtime requires:

- matching `Program Enrollment` for `(student, program_offering, academic_year)`
- matching `Program Enrollment Course` for the selected `course`
- matching `term_start` when the group is term-scoped
- no conflicting membership in another course-based group for the same course, term, and Academic Year

### 4.2 Cohort-based groups

Cohort-based groups require:

- matching `Program Enrollment` for `(student, program_offering, academic_year)`
- matching `cohort`

### 4.3 Activity and other groups

`Activity` and `Other` groups do not use the same automatic eligibility query path.

Current runtime treats them as manual roster selection flows, even when the surrounding activity workflow is tied to a `Program Offering`.

That distinction must remain explicit in docs and code.

---

## 5. What Scheduling Must Not Write Back Into Enrollment

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.py`
- `ifitwala_ed/schedule/student_group_employee_booking.py`
Test refs:
- `ifitwala_ed/schedule/doctype/student_group/test_student_group.py`

Scheduling changes are operational changes. They must not silently mutate academic truth.

That means:

- adding a student to a `Student Group` must not create a `Program Enrollment`
- removing a student from a `Student Group` must not drop a `Program Enrollment Course`
- changing a timetable must not rewrite course entitlement
- employee or room booking rebuilds must not be treated as enrollment-side state transitions

If a workflow needs both academic and operational change, it needs an explicit orchestration path, not hidden side effects in a group controller.

---

## 6. Non-Orchestrated Gaps That Must Be Documented Honestly

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/student_group_creation_tool/student_group_creation_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

The current runtime does not implement one system-owned enrollment-to-scheduling orchestrator.

Current gaps:

- request materialization creates or updates `Program Enrollment`, not `Student Group`
- `Program Enrollment Tool` prepares, validates, approves, and materializes requests only
- `Student Group Creation Tool` controller is currently empty and does not provide canonical generation logic
- `Program Enrollment.on_update()` handles joining-date and identity-upgrade side effects, not group creation
- no runtime automatically clones or retires timetables when rollover creates next-year enrollments

These gaps are not documentation bugs. They are real implementation boundaries and must stay explicit until code changes.

---

## 7. Rollover Boundary

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/api/test_self_enrollment.py`

Year rollover in the current runtime stops at the enrollment layer.

Staff and portal lanes may create next-year requests and next-year committed enrollments, but they do not automatically:

- create next-year teaching groups
- assign students into section rosters
- clone or resolve next-year timetable rows
- rebuild next-year booking facts unless groups already exist and are saved

That boundary is critical for refactors. Rollover and timetable generation are adjacent concerns, not one implemented transaction today.

---

## 8. Product And UX Implications

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/student_group/student_group.js`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/api/self_enrollment.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/api/test_self_enrollment.py`

Because the bridge is not fully orchestrated, low-friction UX must still preserve the boundary:

- self-service and admissions flows should edit requests, not groups
- staff group-building flows should pull from committed enrollment truth, not free text or stale rosters
- blocked scheduling actions should explain whether the blocker is missing enrollment, missing committed course, or missing timetable setup

Silent fallback from missing enrollment into manual scheduling is a product defect, not a convenience.

---

## 9. Anti-Patterns

The following are architectural drift:

- deriving enrollment truth from `Student Group`, attendance, or bookings
- auto-dropping committed course rows because a roster changed
- letting portal or admissions surfaces write `Student Group` directly
- documenting `Student Group Creation Tool` as if it already owns system-wide generation logic
- assuming next-year enrollments imply next-year operational groups without an explicit generation step

---

## 10. Refactor Guardrails

When work spans both domains, preserve this order:

1. commit or validate enrollment truth first
2. derive scheduling eligibility from committed enrollment facts
3. create or update operational groups explicitly
4. materialize bookings only from the operational scheduling layer

If a refactor wants to automate the handoff between steps 2 and 3, that must be introduced as a new explicit contract and documented together with the runtime owner.

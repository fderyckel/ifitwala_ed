# Year Rollover and Year-End Closure Architecture

## Status

Active. Canonical note for how existing students move from one academic year/program-offering context to the next, and what must be closed or archived around that transition.

Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.js`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.js`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/students/doctype/student/student.py`

Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

This document defines the current runtime contract for year rollover and year-end closure in Ifitwala_Ed.

It complements:

- `01_academic_year_architecture.md`
- `03_enrollment_architecture.md`
- `04_enrollment_examples.md`

If code and this note disagree, stop and resolve the drift explicitly.

---

## 1. Core Distinction

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

Year rollover and year-end closure are adjacent but they are not the same workflow.

- year rollover creates next-year intent and, eventually, next-year committed `Program Enrollment`
- year-end closure retires prior-year operational records

Current runtime does not have one system-owned orchestrator that performs both jobs in one transaction or one wizard.

Current ownership is split:

- `Program Enrollment Tool` owns batch request preparation, validation, approval, and materialization for next-year movement
- `Program Offering Selection Window` owns portal-governed request preparation and submission
- `End of Year Checklist` owns scoped closure of outgoing-year records

That split must be documented explicitly rather than implied away.

---

## 2. Canonical Rollover Spine

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`

For existing students, the rollover spine is:

`current Program Enrollment` -> `target Program Offering` + `target Academic Year` -> optional `Program Offering Selection Window` -> `Program Enrollment Request` -> `target Program Enrollment`

Important rules:

- the destination is always an explicit `Program Offering` and explicit `Academic Year`
- portal actors never create committed enrollment directly
- `Program Enrollment Request` remains the staging object whenever approval or self-service is involved
- there is no separate `Program Request` doctype in the repository

Source population can be gathered from:

- current `Program Enrollment`
- `Student Cohort`
- manual student rows

---

## 3. Choosing The Lane

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/api/self_enrollment.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/api/test_self_enrollment.py`

Use the lane that matches the decision model:

| Situation | Canonical lane | Why |
| --- | --- | --- |
| Staff is progressing a known student set and no family/student choice window is needed | `Program Enrollment Tool` | lowest-friction batch path under staff control |
| Student or guardian must review or choose courses before progression is approved | `Program Offering Selection Window` -> portal -> staff approval | preserves self-service without bypassing request governance |
| Student is still in admissions and is not yet part of the current student body | admissions bridge, not rollover | this uses `Applicant Enrollment Plan`, not the current-student rollover lane |

Do not pretend every student progression goes through the same surface.

---

## 4. Staff Batch Rollover Lane

Status: Implemented
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`

`Program Enrollment Tool` is the current low-friction staff lane for moving many students from one offering/year context to the next.

Current flow:

1. choose source population:
   - `Program Enrollment`
   - `Cohort`
   - manual rows
2. choose destination:
   - `new_program_offering`
   - `new_target_academic_year`
   - destination enrollment date
3. load students
4. `prepare_requests`
5. `validate_requests`
6. `approve_requests`
7. `materialize_requests`

Current behavior that matters architecturally:

- the tool creates draft `Program Enrollment Request` rows before creating next-year enrollments
- it skips students already enrolled in the destination
- it skips students who already have an active destination request
- materialization is blocked unless the request is both `Approved` and `Valid`
- batches above the queue threshold are enqueued on the long queue instead of forcing the whole run through one request path
- counts and issue CSV output are part of the operator contract

This is the primary implemented path for staff-driven progression with minimal manual friction.

---

## 5. Portal-Assisted Rollover Lane

Status: Implemented
Code refs:
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.js`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.js`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/api/test_self_enrollment.py`

`Program Offering Selection Window` is the current rollover lane when student or guardian action is required.

Current flow:

1. staff enables `allow_self_enroll` on the target `Program Offering`
2. staff creates the selection window from the offering
3. staff chooses source mode:
   - `Program Enrollment`
   - `Cohort`
   - `Manual`
4. staff loads students
5. staff prepares one draft `Program Enrollment Request` per student row
6. staff opens the window
7. student or guardian saves and submits the linked request in portal
8. staff reviews, validates, approves, and materializes later

Portal boundaries remain strict:

- portal actors see only authorized rows for their audience
- portal actors edit only the linked draft request
- portal actors do not create `Program Enrollment`
- the window is an operational envelope, not academic truth

For SPA and request-shape discipline, the current portal contract is:

- one aggregated board endpoint for window discovery
- one detail/state endpoint for the selected request
- explicit save/submit mutations

That keeps the self-service lane aligned with the repo concurrency contract instead of turning it into uncontrolled document browsing.

---

## 6. Closure Inventory

Status: Mixed
Code refs:
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
- `ifitwala_ed/school_settings/doctype/academic_year/academic_year.py`
- `ifitwala_ed/students/doctype/student/student.py`
Test refs:
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

The outgoing year has several different closure responsibilities. They are not all owned by the same runtime surface.

| Record / concern | Current closure owner | Current runtime outcome |
| --- | --- | --- |
| `Academic Year` | `End of Year Checklist` | set `archived = 1` and `visible_to_admission = 0` for resolved year names in scope |
| `Term` | `End of Year Checklist` | set `archived = 1` for terms linked to the resolved year names |
| `Program Enrollment` | `End of Year Checklist` | set `archived = 1` for scoped schools and resolved year names |
| `Student Group` | `End of Year Checklist` | set `status = "Retired"` for scoped schools and resolved year names |
| professional-development side effects tied to the year/scope | `archive_academic_year()` side effect | linked PD requests and records are cancelled as part of the AY close path |
| `Program Offering Selection Window` | not checklist-owned | no automatic close/archive action at year-end |
| `Program Enrollment Request` | not checklist-owned | no archive action; request rows remain workflow and audit records |
| `Program Offering` | not checklist-owned | no archive action; offering configuration remains separate from year closure |
| `Student` | not checklist-owned | no year-end archive action; student lifecycle remains separate |

### 6.1 Student leaving is separate from year closure

Status: Active
Code refs:
- `ifitwala_ed/students/doctype/student/student.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
Test refs:
- no dedicated year-rollover closure test for student leaving

The repository does not implement “student leaving” as a year-end checklist archive action.

Current reality is:

- `Student` has its own lifecycle fields such as `student_exit_date`
- `Student.enabled` is part of student lifecycle behavior
- year-end closure archives the outgoing `Program Enrollment`, not the `Student` record itself

Operational implication:

- a student who is leaving should be excluded from next-year progression
- that is separate from archiving the outgoing-year enrollment

Do not document student departure as if the checklist already owns it.

---

## 7. Recommended Operational Sequence

Status: Partial
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

Current runtime does not enforce one end-to-end rollover sequence.

The lowest-friction operational order, inferred from current ownership, is:

1. prepare the destination `Program Offering` and destination `Academic Year`
2. decide whether this cohort needs:
   - direct staff batch rollover, or
   - portal choice collection
3. prepare next-year requests
4. collect portal submissions where required
5. validate, approve, and materialize next-year `Program Enrollment`
6. verify leavers are excluded from next-year progression
7. run `End of Year Checklist` for the outgoing year

This sequence avoids turning year closure into a blocker before next-year intent is prepared.

It is an operational recommendation, not a single code-owned wizard.

---

## 8. Explicit Gaps And Non-Orchestrated Areas

Status: Partial
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/test_program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/end_of_year_checklist/test_end_of_year_checklist.py`

The following are not currently implemented as one unified contract:

- `End of Year Checklist` does not trigger next-year request preparation
- `End of Year Checklist` does not open or close `Program Offering Selection Window`
- `End of Year Checklist` does not approve or materialize next-year enrollments
- there is no single year-rollover cockpit that owns progression and closure together

There is also current surface drift in source-population filtering:

- `Program Enrollment Tool` filters out disabled students when sourcing from `Program Enrollment`
- `Program Offering Selection Window` does not currently apply the same disabled-student filter in its `Program Enrollment` source path

That difference should be treated as an explicit implementation gap, not hidden by the docs.

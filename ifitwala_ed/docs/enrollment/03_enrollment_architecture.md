# Enrollment Architecture

## Status

Active. Canonical enrollment architecture note for runtime object boundaries, workflow lanes, and surface ownership.

Code refs:
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.js`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.js`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.js`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
- `ifitwala_ed/schedule/program_enrollment_request_choice.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`

Test refs:
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/schedule/test_enrollment_engine.py`
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/test_applicant_enrollment_plan.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`

This document defines the real enrollment architecture in Ifitwala_Ed.

It is authoritative for:
- object boundaries
- workflow lanes
- Desk vs portal surface ownership
- validation and materialization invariants

It is not a marketing summary and it is not a policy catalog.

If code and this document disagree, stop and resolve the drift explicitly.

Related architecture:
- `docs/enrollment/01_academic_year_architecture.md`
- `docs/enrollment/02_school_calendar_architecture.md`
- `docs/enrollment/07_year_rollover_architecture.md`
- `docs/enrollment/05_course_choice_semantics.md`
- `docs/enrollment/06_activity_booking_architecture.md`

---

## 0. Naming Discipline

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.json`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`

Use the runtime names that exist in the repository:

- `Program Offering` = operational offering truth
- `Program Offering Selection Window` = the request window exposed to one portal audience
- `Program Enrollment Request` = the request object for staged academic intent
- `Program Enrollment` = committed academic truth

For product conversations, the shorthand is acceptable only if it maps back to the real object:

- “program request” means `Program Enrollment Request`
- “program request window” means `Program Offering Selection Window`

There is no separate `Program Request` doctype in the repository. Do not document one.

---

## 1. Core Definition (Non-Negotiable)

### 1.1 What enrollment is

Enrollment in Ifitwala_Ed is not CRUD.

It is a decision system that evaluates:

- eligibility
- basket and capacity constraints
- approval and override authority
- provenance

and then produces committed academic truth.

Any implementation that bypasses this process is invalid by design.

### 1.2 Guiding principles

Enrollment must be:

- curriculum-agnostic
- historically auditable
- explicitly overrideable
- policy-driven
- multi-tenant safe
- reality-anchored

Automation supports human decision-making. It does not erase accountability.

---

## 2. Canonical Object Chain

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/test_applicant_enrollment_plan.py`

Enrollment is only correct when these layers remain separate:

| Layer | Responsibility | Must not be treated as |
| --- | --- | --- |
| `Program` | academic intent and structure | operational availability |
| `Program Offering` | what this school is offering now, in explicit academic-year context | portal request state or committed enrollment |
| `Program Offering Selection Window` | operational portal exposure of one offering to one audience (`Student` or `Guardian`) | academic truth or a substitute for approval |
| `Program Enrollment Request` | staged, auditable request with validation snapshot | committed enrollment |
| `Program Enrollment` | committed academic truth | a draft, planner, or request buffer |
| `Applicant Enrollment Plan` | pre-student admissions bridge | a substitute for student-side request objects |

### 2.1 `Program Offering`

`Program Offering` is the operational envelope for enrollment.

It owns:

- the program/school spine
- the allowed academic year set
- the offering course semantics
- offering-scoped basket rules
- self-enrollment enablement

It does not own:

- portal draft state
- student-by-student request status
- final enrollment approval decisions

### 2.2 `Program Offering Selection Window`

`Program Offering Selection Window` is the operational request window for portal self-service.

It is valid only because it governs linked draft `Program Enrollment Request` rows.

It locks:

- one explicit `Program Offering`
- one explicit `Academic Year`
- one explicit audience: `Student` or `Guardian`
- one student population source
- one linked draft request per student row

It does not become committed academic truth.

Its statuses are operational only:

- `Draft`
- `Open`
- `Closed`
- `Archived`

### 2.3 `Program Enrollment Request`

`Program Enrollment Request` is the mandatory staging object for academic requests.

It owns:

- the requested basket
- request-time course semantics snapshot
- validation snapshot
- override state and rationale
- source provenance such as `selection_window` or `source_applicant_enrollment_plan`

It is the only valid transactional staging object between request intent and committed enrollment.

### 2.4 `Program Enrollment`

`Program Enrollment` is committed academic truth.

It may be created only through:

- an approved `Program Enrollment Request`
- an explicit direct staff/admin lane with preserved provenance
- an explicit migration lane

Portal users never write `Program Enrollment`.

---

## 3. Workflow Lanes

Status: Active
Code refs:
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
Test refs:
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/test_applicant_enrollment_plan.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

There are four distinct lanes. They must not be collapsed into one vague “enrollment workflow.”

### 3.1 Admissions bridge lane

Flow:

`Student Applicant` -> `Applicant Enrollment Plan` -> offer/acceptance -> student promotion -> `Program Enrollment Request`

This lane exists to keep pre-student admissions intent out of the core student enrollment tables.

### 3.2 Staff request lane

Flow:

staff chooses `Program Offering` -> optionally seeds `Program Offering Selection Window` -> creates or reviews `Program Enrollment Request` -> validates -> overrides if required -> approves -> materializes `Program Enrollment`

This is the main academic review lane for existing students.

### 3.3 Portal self-enrollment lane

Flow:

staff opens `Program Offering Selection Window` -> portal actor edits the linked draft `Program Enrollment Request` -> portal submits request -> staff reviews and approves -> materializes `Program Enrollment`

The portal edits only the linked request state. It never bypasses staff review.

### 3.4 Direct administrative lane

Flow:

`Program Enrollment Tool` or `Course Enrollment Tool` -> explicit provenance -> direct `Program Enrollment` mutation where policy allows

This is a valid lane for rollover, bulk administration, and governed exceptions.

It is not a substitute for request-based approval.

---

## 4. Surface Ownership: Desk vs Portal

Status: Active
Code refs:
- `ifitwala_ed/curriculum/workspace/curriculum/curriculum.json`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.js`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.js`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.js`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/api/self_enrollment.py`
- `ifitwala_ed/ui-spa/src/lib/services/selfEnrollment/selfEnrollmentService.ts`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCourseSelectionDetail.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelection.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue`
Test refs:
- `ifitwala_ed/api/test_self_enrollment.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts`

Surface ownership is part of the architecture, not a presentation detail.

| Actor | Surface | Objects surfaced | Allowed write scope |
| --- | --- | --- | --- |
| Academic staff / admins | Desk forms and workspaces | `Program Offering`, `Program Offering Selection Window`, `Program Enrollment Request`, `Program Enrollment`, bulk tools | full governed workflow actions within permission scope |
| Student | portal routes `/student/course-selection` and `/student/course-selection/:selection_window` | invited `Program Offering Selection Window` rows and the linked draft `Program Enrollment Request` | save and submit only that linked request while the window is open |
| Guardian | portal routes `/guardian/course-selection` and `/guardian/course-selection/:selection_window/:student_id` | invited guardian-scoped window rows for linked children and each linked child request | save and submit only the linked child request while the window is open |

### 4.1 Desk ownership

Desk is the authoritative staff surface for:

- authoring `Program Offering`
- creating a `Program Offering Selection Window` from the offering
- loading students into the window
- preparing one draft request per student
- opening and closing the portal window
- reviewing, overriding, approving, and materializing requests
- executing governed direct-enrollment tools

Students and guardians do not use Desk.

Desk visibility for school-anchored enrollment doctypes is staff-scope driven:

- when the active `Employee.school` resolves, Desk stays within that school descendant branch
- when the active `Employee` has no `school`, `Program Offering` and `Program Enrollment` Desk visibility may widen to all schools in the employee organization's descendant scope
- this changes visibility scope only; DocType read/write/create/delete authority still comes from the DocType permission matrix and scripted permission guards

### 4.2 Student portal ownership

Student portal self-enrollment is implemented through:

- `get_self_enrollment_portal_board`
- `get_self_enrollment_choice_state`
- `save_self_enrollment_choices`
- `submit_self_enrollment_choices`

The student sees only:

- windows addressed to audience `Student`
- student-authorized rows
- the request linked to that window row

The student does not see or write:

- arbitrary `Program Offering` records
- other students’ requests
- `Program Enrollment`
- Desk-only approval or override controls

### 4.3 Guardian portal ownership

Guardian portal self-enrollment is implemented through the same API family, but the actor resolution is guardian-to-linked-student scoped.

The guardian sees only:

- windows addressed to audience `Guardian`
- linked child rows
- the specific request linked to that child row

The guardian does not gain generalized visibility into draft academic truth outside those linked windows.

### 4.4 Forbidden surface drift

The following are design regressions:

- exposing `Program Offering` authoring in student or guardian portals
- letting portal users create free-floating requests without a governing window
- treating a window as approved enrollment
- letting portal save actions touch `Program Enrollment`
- documenting Desk-only actions as if they were student or guardian actions

---

## 5. Window and Request Lifecycle

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/program_enrollment_request_seed.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/api/self_enrollment.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/test_program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/api/test_self_enrollment.py`

### 5.1 Selection window lifecycle

`Program Offering Selection Window` enforces:

- the offering must exist
- the academic year must belong to the offering
- `allow_self_enroll` must be enabled on the offering
- audience must be `Student` or `Guardian`
- source mode must be one of:
  - `Program Enrollment`
  - `Cohort`
  - `Manual`

The Desk workflow is:

1. define the window
2. load target students
3. prepare requests
4. verify one linked request per student
5. open the window

Opening is blocked if the window does not already govern linked requests.

### 5.2 Request creation under a window

Preparing a window does not create committed enrollments.

It creates or attaches draft `Program Enrollment Request` rows scoped by:

- student
- target `Program Offering`
- target `Academic Year`
- selection-window provenance

If a student already has a target `Program Enrollment` or an active request in the same target context, the window must respect that instead of silently duplicating intent.

### 5.3 Portal edit and submit rules

Portal save and submit are allowed only when:

- the actor is authorized for the student row
- the window audience matches the actor type
- the window is open right now
- the linked request is still editable

Once a request leaves draft state, portal editing becomes read-only.

### 5.4 Request gate states

For `Program Enrollment Request`, gate states are:

- `Submitted`
- `Under Review`
- `Approved`

Those states require a validation snapshot.

Approval requires:

- `validation_status = Valid`
- override approval if `requires_override = 1`

The request is the only valid staging area between portal/desk intent and committed enrollment.

---

## 6. Eligibility, Basket Semantics, and Snapshots

Status: Active
Code refs:
- `ifitwala_ed/schedule/enrollment_engine.py`
- `ifitwala_ed/schedule/grade_scale_resolver_utils.py`
- `ifitwala_ed/schedule/basket_group_utils.py`
- `ifitwala_ed/schedule/program_enrollment_request_choice.py`
- `ifitwala_ed/docs/enrollment/05_course_choice_semantics.md`
Test refs:
- `ifitwala_ed/schedule/test_enrollment_engine.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

### 6.1 Constraint model

Eligibility rules use a DNF model:

```text
(A AND B AND min_grade(A))
OR (C)
OR (D AND NOT E)
```

All prerequisites are program-scoped. Catalog-level prerequisite logic must not be introduced.

### 6.2 Numeric truth only

Eligibility comparisons are numeric only:

- `numeric_score` to numeric threshold
- never label-to-label runtime comparison

If numeric resolution fails, validation fails.

### 6.3 Grade-scale resolution

Resolution order is:

1. `Course Term Result.grade_scale`
2. `Program Offering Course.grade_scale`
3. `Program Offering.grade_scale`
4. `Course.grade_scale`
5. `Program.grade_scale`

Request validation snapshots must freeze the resolved threshold context so later grade-scale edits do not rewrite history.

### 6.4 Basket semantics live on offerings and snapshots

Basket-group semantics are offering-side runtime truth.

Request rows must snapshot enough meaning to remain historically stable, including:

- whether the course was required
- the resolved `applied_basket_group` where relevant
- `choice_rank` when ranking occurs inside a basket family

Committed enrollment rows must preserve the committed meaning rather than recomputing it from later offering edits.

### 6.5 Source of academic truth for eligibility

Eligibility may consult only:

- `Program Enrollment`
- `Course Term Result`
- allowed reporting-cycle states

Eligibility must never consult:

- draft assessments
- unreleased task data
- portal draft intent as if it were evidence

---

## 7. Capacity and Delivery Separation

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/basket_group_utils.py`
- `ifitwala_ed/eca/doctype/program_offering_activity_section/program_offering_activity_section.json`
Test refs:
- `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`

Capacity and delivery are different problems.

### 7.1 Allocation capacity

Allocation capacity for academic choice lives on `Program Offering Course`.

It is evaluated during request validation and approval lanes.

It must not depend on `Student Group`.

### 7.2 Delivery capacity

There is no standalone `Course Section` doctype.

For delivery, `Student Group` is the section construct.

Do not collapse allocation-choice capacity and delivery-section capacity into one concept.

---

## 8. Direct Enrollment, Overrides, and Provenance

Status: Active
Code refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.py`
- `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
- `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs:
- `ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py`

### 8.1 Direct staff enrollment is valid only with provenance

Direct creation of `Program Enrollment` is valid only when the system records the lane explicitly.

The committed object already distinguishes governed sources such as:

- `Request`
- `Admin`
- `Migration`

“Direct” does not mean “unexplained.”

### 8.2 Overrides are first-class

Overrides are not silent exceptions.

Every override must record:

- reason
- approver
- timestamp
- affected request context

Overrides do not mutate historical validation snapshots.

### 8.3 Portal users never own committed truth

Students and guardians may influence request state.

They do not:

- approve requests
- grant overrides
- materialize enrollments
- create provenance-free enrollments

---

## 9. Activity Booking Parallel

Status: Implemented as a sibling architecture
Code refs:
- `ifitwala_ed/docs/enrollment/06_activity_booking_architecture.md`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`
Test refs:
- `ifitwala_ed/api/test_activity_booking.py`

Activity booking follows the same discipline:

- request state is not committed placement truth
- readiness checks are explicit
- portal exposure is governed

But its lifecycle is documented separately in `06_activity_booking_architecture.md`.

Do not mix academic enrollment rules and activity-booking rules inside one undocumented hybrid flow.

---

## 10. Core System Invariants (Non-Negotiable)

1. All academic request validation goes through the enrollment engine and request utilities, not ad hoc client logic.
2. `Program Offering` is the operational offering truth; it is not itself a request or an enrollment.
3. `Program Offering Selection Window` is the only governed portal envelope for academic self-enrollment.
4. `Program Enrollment Request` is the only valid transactional staging object for academic requests.
5. `Program Enrollment` is committed truth and must preserve provenance.
6. Portal users never write committed academic truth.
7. Validation snapshots are frozen at decision time.
8. Rule changes must not retroactively rewrite old decisions.
9. Child tables remain passive; business logic belongs in parent controllers and canonical services.
10. Desk vs portal ownership must stay explicit; silent surface drift is a product defect.

---

## 11. Architectural North Star

Enrollment in Ifitwala_Ed is a governed decision system with institutional memory.

The canonical chain is:

`Program Offering` -> `Program Offering Selection Window` -> `Program Enrollment Request` -> `Program Enrollment`

for portal self-service, and:

`Applicant Enrollment Plan` -> `Program Enrollment Request` -> `Program Enrollment`

for pre-student admissions handoff.

If a future change cannot explain where it sits in those chains, it is probably architectural drift.

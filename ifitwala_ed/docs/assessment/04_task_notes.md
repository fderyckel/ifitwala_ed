# Ifitwala_Ed — Task Runtime Contract

Status: **Authoritative / Current Workspace Contract**
Scope: `Task`, `Task Delivery`, `Task Outcome`, `Task Submission`, `Task Contribution`
Audience: Product, Engineering, and coding agents
Last updated: 2026-04-25

This document defines the current task runtime contract in the workspace.
It replaces older lesson-instance-era notes and removes future-state claims that are not yet true in code.

Related docs:
- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`
- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`

---

## 0. Product Intent

Status: **Implemented**

Code refs:
- `ifitwala_ed/assessment/doctype/task/task.py`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/courses.py`

Task is reusable instructional work, not curriculum.
`Task Delivery` is the operational class-scoped assignment record.
In educator-facing product language, `Task Delivery` may be surfaced as assigned work for a class, but the backend doctype remains `Task Delivery`.

The current model separates:

- reusable task definition
- class assignment context
- per-student official outcome
- versioned evidence
- teacher grading contributions

Teachers should experience one grading surface.
Students should see assigned work inside the LMS, not internal doctypes.

---

## 1. Runtime Objects

Status: **Implemented**

Code refs:
- `ifitwala_ed/assessment/doctype/task/task.json`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
- `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`
- `ifitwala_ed/assessment/doctype/task_submission/task_submission.json`
- `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`
- `ifitwala_ed/assessment/doctype/task_outcome_criterion/task_outcome_criterion.json`

Test refs:
- `ifitwala_ed/assessment/doctype/task/test_task.py`
- `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`
- `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`
- `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`
- `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`

### 1.1 Task

`Task` is the reusable definition.
It owns title, instructions, resources, task type, grading defaults, and the default comment policy.
It does not own class membership, dates, or per-student truth.

### 1.2 Task Delivery

`Task Delivery` is the class-scoped assignment record.
It owns:

- `task`
- `student_group`
- `class_teaching_plan`
- `delivery_mode`
- availability and deadline fields
- grading snapshot fields
- assessment evidence classification fields (`assessment_category`, optional `reporting_weight`)
- additive comment policy snapshot (`allow_feedback`)
- optional `class_session`
- denormalized class context such as `course`, `academic_year`, and `school`

### 1.3 Task Outcome

`Task Outcome` is the per-student operational truth for one delivery.
There should be one outcome row per `(Task Delivery x Student)`.
It owns submission state, grading state, procedural state, scalar result fields for scalar grading modes, and non-scalar official truth such as completion state.

For criteria grading, official per-criterion truth lives in `Task Outcome Criterion`.

### 1.4 Task Submission

`Task Submission` is append-only evidence.
Each new learner submission creates a new version.
Teacher-created evidence stubs are allowed when grading needs an audit anchor without learner-uploaded evidence.

Feedback-specific implication from the canonical feedback contract:

- future structured feedback records and derived feedback artifacts must bind to a selected submission version or explicit evidence stub context
- learner submissions remain immutable even when annotated return artifacts exist
- the current assessment runtime now also exposes one version-bound feedback workspace plus one teacher-owned comment-bank context through the gradebook drawer, but those remain feedback-side productivity layers rather than official outcome truth
- the student task workspace now loads the latest submission together with a release-aware result projection for that submission version; score and feedback channels remain masked until publication allows student visibility

### 1.5 Task Contribution

`Task Contribution` stores teacher-authored grading input.
It does not replace the outcome row directly in the UI contract.
The official result is derived from eligible contributions, not entered straight into the gradebook payload.
For assessed `Completion` and `Binary` deliveries, the contribution row carries `judgment_code`; `Task Outcome.is_complete`
remains the derived official truth rather than the primary write path.

Feedback-specific implication:

- reusable feedback comments and anchored feedback items remain adjacent assessment records
- they may link to rubric criteria and selected submission versions
- they must not replace `Task Contribution` as grading input or `Task Outcome` as official result truth

---

## 2. Task Delivery Contract

Status: **Implemented**

Code refs:
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/assessment/task_creation_service.py`

Test refs:
- `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`
- `ifitwala_ed/assessment/test_task_delivery_service.py`
- `ifitwala_ed/assessment/test_task_creation_service.py`

### 2.0 Shared versus local persistence rule

Status: **Partial**

Code refs:
- `ifitwala_ed/assessment/doctype/task/task.json`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/api/task.py`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Test refs:
- `ifitwala_ed/assessment/test_task_creation_service.py`
- `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`

- A task created from one class-planning or class-session workflow is class-originated by default in product semantics.
- Sharing that work across classes is deliberate reuse, not a silent side effect of creation.
- Promoting one class's work into shared reusable or common-assessment baseline space must be explicit and reviewable.
- Local delivery edits stay on `Task Delivery`, class-session context, or class-owned resource surfaces; they must not rewrite a shared baseline implicitly.

Current workspace reality:

- `Task` currently stores `default_course`, optional `unit_plan`, and `is_template`; it does not yet store a first-class ownership state such as `shared_baseline` or `class_authored`.
- `is_template` now controls explicit course-library sharing for reusable tasks. It does not promote work into governed curriculum or common-assessment baseline space.
- The class-owned context currently lives on required `Task Delivery.class_teaching_plan` and optional `Task Delivery.class_session`.
- `api/task.py::search_reusable_tasks()` and `api/task.py::search_tasks()` now resolve one course-scoped reusable-task library at a time. They return only tasks the current user owns for that course or tasks explicitly shared with the course team.
- `api/task.py::list_course_assessment_criteria()` now resolves the same course scope and exposes the course-owned criteria library to the task overlay.
- `ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue` now supports criteria authoring for new tasks directly in the main task flow, using course criteria rows plus task-local weighting and max-points metadata.
- Reusing an existing criteria task now carries `criteria_defaults` and the default rubric strategy back to the overlay, while keeping the criteria rows themselves on the reusable task definition.
- `api/task.py::create_task_delivery()` now supports the assign-existing path. Reusing a task creates a new class-scoped delivery only; it does not rewrite the reusable task definition.
- Same-teacher reuse across groups or school years stays available through task ownership. Cross-teacher reuse requires explicit course-library sharing.
- Cross-surface dependency: staff Morning Brief instructor widgets in `ifitwala_ed/api/morning_brief.py` read overdue grading state from `Task Delivery` and `Task Outcome`, so any change to task ownership, delivery due-date semantics, grading-required flags, or outcome completion statuses must update Morning Brief code and `ifitwala_ed/api/test_morning_brief.py` in the same change.

### 2.1 Context ownership

`Task Delivery` is anchored to `Student Group` and `Class Teaching Plan`.
Before validation, the delivery stamps context from the group, validates course alignment, and validates that the selected class teaching plan belongs to the same class/course/year.

Current enforced rules:

- `task` is required
- `student_group` is required
- `class_teaching_plan` is required
- `course`, `academic_year`, and `school` are stamped from `Student Group`
- if the task carries a course tag, it must match the delivery course

### 2.2 Optional `Class Session` link

`Task Delivery.class_session` is optional.
It is a soft teaching-context link beneath the required class teaching plan, not a substitute for that planning dependency.

If present, it must belong to the same:

- `class_teaching_plan`
- `student_group`
- `course`
- `academic_year`

`Task Delivery` must not auto-create `Class Session`.
The lesson-instance-era auto-creation path is retired.

### 2.3 Delivery modes

Current delivery modes are:

- `Assign Only`
- `Collect Work`
- `Assess`

The teacher-facing task overlay maps educator language onto those runtime modes:

| Overlay choice | Runtime delivery mode | `requires_submission` | Grading |
| --- | --- | --- | --- |
| Share work | `Assign Only` | `0` | none |
| Collect work | `Collect Work` | `1` | none |
| Collect and mark | `Assess` | `1` | required |
| Mark class work | `Assess` | `0` | required |

Current enforced behavior:

- `Assign Only`
  - no submission required
  - no grading settings allowed
- `Collect Work`
  - submission required
  - grading settings cleared
- `Assess`
  - grading required
  - grading mode must resolve
  - `requires_submission` may be explicitly set per delivery
  - `requires_submission = 1` means learners hand in work through the platform
  - `requires_submission = 0` means the teacher records marks and feedback for in-class, paper, oral, lab, studio, or exam work
  - grading snapshot fields are set from task defaults where applicable
  - `assessment_category` classifies evidence for scheme-aware gradebook/reporting aggregation
  - `reporting_weight` is optional and only used by reporting methods that explicitly count task weights

### 2.4 Quiz behavior

Quiz is a task type, not a separate delivery doctype.
For assessed quiz deliveries, current validation forces:

- `requires_submission = 0`
- `grading_mode = "Points"`
- rubric fields cleared
- quiz max points snapshotted from quiz configuration

Current assessed quiz grading behavior:

- choice and short-answer items are auto-scored in `quiz_service.py`
- essay items remain on `Quiz Attempt Item` rows with `requires_manual_grading = 1` until a teacher records `awarded_score`
- staff manual review for those items runs through the gradebook quiz-review endpoints, not through the standard contribution grid
- question-level criteria or rubric scoring is not part of the current assessed quiz contract

### 2.5 Outcome materialization

Delivery submission materializes student outcomes.
The current path uses eligible active `Student Group Student` rows and bulk inserts only missing outcomes.

This means:

- no per-student outcome rows before delivery submission
- rerunning materialization is idempotent against existing outcomes
- delivery creation stays compatible with high-concurrency roster materialization

### 2.6 Group submission status

Status: **Paused / Not Supported In Product**

Code refs:
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`

`group_submission` is not part of the current live contract.
Creation and validation block it.
Do not build UI, workflow, or reporting assumptions around group submission until subgroup membership and product rules are explicitly implemented.

---

## 3. Official Outcome Truth

Status: **Implemented, with one quiz-runtime exception**

Code refs:
- `ifitwala_ed/assessment/task_outcome_service.py`
- `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`
- `ifitwala_ed/assessment/task_contribution_service.py`
- `ifitwala_ed/assessment/quiz_service.py`
- `ifitwala_ed/api/gradebook.py`

Test refs:
- `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`
- `ifitwala_ed/assessment/doctype/task_outcome/test_task_outcome.py`

### 3.1 Standard contribution-driven path

For standard grading flows, official truth is recomputed from eligible contributions after insert.
Eligible contributions are:

- not `Draft`
- not stale

Current selection behavior is:

- latest eligible `Moderator` contribution wins first
- otherwise the latest eligible `Self` or `Official Override` contribution wins
- `Peer Review` is not selected as official truth

If the selected moderator action is `Return to Grader`, the system sets `grading_status = "In Progress"` and leaves official truth unchanged.

### 3.2 Criteria grading behavior

When `grading_mode = "Criteria"`:

- official criterion rows are copied into `Task Outcome Criterion`
- `rubric_scoring_strategy = "Separate Criteria"` clears task-level totals and grade fields
- `rubric_scoring_strategy = "Sum Total"` computes task-level totals and optional grade-scale resolution
- if the rubric snapshot carries positive `criteria_max_points` on every criterion and the criterion weightings total `100`, the official total is the weighted normalized result:
  `sum((criterion level_points / criteria_max_points) * criteria_weighting)`
- if a legacy rubric snapshot does not meet that contract, the runtime falls back to the older weighted raw-point behavior so historical tasks do not silently change meaning

### 3.3 Scalar non-criteria grading behavior

When `grading_mode = "Points"`, the selected contribution may write:

- `official_score`
- `official_grade`
- `official_grade_value`
- `official_feedback`

through the outcome truth service.

Comment-only contributions are additive feedback. They write `official_feedback` and status, but they do not create, require, or clear `official_score`.

For assessed `Completion` and `Binary` grading, the selected contribution writes only:

- `official_feedback`
- derived `is_complete`

using `Task Contribution.judgment_code`.

Completion and Binary grading must not write `official_score`, `official_grade`, or `official_grade_value`. A missing score in those modes is expected, not incomplete data.

For `grading_mode = "None"`, feedback-only contributions likewise do not write scalar official fields.

### 3.4 Quiz runtime exception

Assessed quiz attempts update outcome truth directly in `quiz_service.py`.
This is the current implemented exception to the standard contribution-driven path.
Do not document or enforce a broader “only one writer exists” rule while this exception remains in code.

Current write boundary for assessed quiz manual review:

- teacher scoring writes `awarded_score` to `Quiz Attempt Item`
- `quiz_service.refresh_attempt(...)` then recomputes `Quiz Attempt` and `Task Outcome`
- the staff gradebook must not treat assessed quiz totals as teacher-entered `official_score`

### 3.5 Gradebook write boundary

The gradebook API must not accept `official_*` writes from clients.
Client-facing grading routes create or update contributions and let the outcome truth pipeline recompute official results.
Current explicit exception:

- `Assign Only` completion tracking may still write `Task Outcome.is_complete` and `completed_on` directly because it is not part of the assessed grading audit path
- that direct path must stay behind named business endpoints, keep exact learner ownership checks for portal writes, and reject completion edits after publication

---

## 4. Submission And Evidence Contract

Status: **Implemented**

Code refs:
- `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/integrations/drive/tasks.py`
- `ifitwala_ed/integrations/drive/content_uploads.py`

Test refs:
- `ifitwala_ed/assessment/doctype/task_submission/test_task_submission.py`
- `ifitwala_ed/api/test_task_submission_unit.py`
- `ifitwala_ed/assessment/test_task_submission_service.py`
- `ifitwala_ed/integrations/drive/test_tasks.py`

### 4.1 Append-only evidence

Learner evidence is append-only.
Existing evidence cannot be overwritten in place.
New evidence creates a new submission version.

Student portal implication:

- `ifitwala_ed.api.task_submission.create_or_resubmit` is the canonical student mutation path for text, links, and raw uploaded files
- if governed files are present, the runtime inserts the new `Task Submission` owner row first, finalizes governed files against that persisted submission version, then saves attachment rows on that same version
- the portal must not mutate attachment rows on an existing submission version in place

### 4.2 Student evidence effects

Student-originated evidence:

- sets `has_submission = 1`
- sets `has_new_submission = 1`
- updates `submission_status`
- marks prior contributions stale when newer evidence exists
- may include text content, link evidence, governed file attachments, or a combination of those evidence types
- file evidence uses the task-submission governed upload workflow; it does not require broad Student write permission on the `Task Submission` DocType

### 4.3 Teacher evidence stubs

Teacher-created stubs are supported when grading needs a submission anchor without learner-uploaded evidence.
Stub effects are intentionally different:

- `has_submission = 1`
- `has_new_submission = 0`
- no learner-evidence badge should be implied

### 4.4 Latest-submission grading rule

If a delivery requires submission, a non-draft contribution must link to a submission.
The contribution must target the latest submission version for that outcome.

---

## 5. Surface Contract

Status: **Implemented**

Code refs:
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/courses.py`

### 5.1 Staff surface

Staff grading reads from `Task Outcome` and `Task Outcome Criterion`.
The gradebook grid and drawer must treat outcomes as the rendered truth layer.
Client code must not recompute totals or criteria summaries independently.

### 5.2 Student LMS surface

Students receive assigned work through LMS-facing course and work-board payloads.
Those payloads expose assignment timing, status, task outcome identity, submission-required flags, required class-planning context, and optional `class_session` context without exposing internal grading doctypes as the primary mental model.
The bounded LMS bootstrap may carry task summary state, but latest submission evidence should stay lazy-loaded per selected task rather than being embedded for every assigned-work row.
When a delivery requires submission, the selected LMS task workspace may submit text, link, and governed file evidence through the same business endpoint, and the read model must return Ed-owned attachment DTOs with stable `open_url` / `preview_url` values instead of raw private file paths.

---

## 6. Scope, Concurrency, And Guardrails

Status: **Implemented**

Code refs:
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Current guardrails:

- instructor-facing gradebook reads are scope-filtered to permitted classes
- delivery context is denormalized early to reduce repeated joins on hot paths
- outcome materialization uses bulk insert rather than per-student insert loops
- gradebook renders from outcome-layer truth, not client-side recomputation

Do not move grading correctness into background jobs simply to hide latency.
Outcome truth changes are correctness-critical and stay synchronous.

---

## 7. Explicit Non-Goals For The Current Contract

Status: **Current Workspace Truth**

The following are not part of the current live task contract:

- group submission workflows
- auto-creation of teaching-session records from task assignment
- documenting future-state behavior as if it already exists

If these product decisions change, update this document and the curriculum contract in the same change.

---

## 8. Contract Summary

- `Task` is reusable work definition.
- `Task Delivery` is class-scoped assigned work.
- `Class Session` is optional context, not a required dependency.
- `Task Outcome` is the per-student operational truth.
- `Task Submission` is append-only evidence.
- `Task Contribution` is the teacher input layer for standard grading flows.
- Official truth is contribution-driven, except for the current quiz runtime path.
- Group submission is paused and must not shape live product behavior.

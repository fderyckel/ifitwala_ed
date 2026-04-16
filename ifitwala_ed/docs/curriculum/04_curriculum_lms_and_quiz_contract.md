# Curriculum LMS And Quiz Contract

Status: Canonical current-state contract
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/student_communications.py`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/api/student_portfolio.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/assessment/doctype/quiz_question/quiz_question.json`, `ifitwala_ed/assessment/doctype/quiz_attempt/quiz_attempt.json`, `ifitwala_ed/assessment/doctype/quiz_attempt_item/quiz_attempt_item.json`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_quiz/open_student_quiz_session.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_hub_home.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_communication/get_student_communication_center.ts`, `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_task_quiz_manual_review.ts`, `ifitwala_ed/ui-spa/src/types/contracts/gradebook/save_task_quiz_manual_review.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/studentQuizService.ts`, `ifitwala_ed/ui-spa/src/lib/services/portfolio/portfolioService.ts`, `ifitwala_ed/ui-spa/src/lib/services/gradebook/gradebookService.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentCommunicationCenter.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/api/test_student_portfolio.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/assessment/test_quiz_service.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentQuizService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

This is the canonical source of truth for the student learning space and native quiz runtime.

The LMS is part of curriculum delivery. It is not a separate architecture outside `docs/curriculum`.

## Student Learning Space Contract

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

`get_student_learning_space(course_id, student_group?)` is the canonical bounded bootstrap for the student curriculum view.

Current response contract:

- `course`
- `access`
- `teaching_plan`
- `communications.course_updates_summary`
- `message`
- `learning`
- `resources`
- `curriculum.units`

Current source modes:

- `class_teaching_plan`
- `course_plan_fallback`
- `unavailable`

Current product behavior:

- class-aware planning is the primary student reality
- shared course-plan content is fallback only
- the student sees explicit unavailable or fallback messaging instead of silent failure
- the learning-space bootstrap exposes only bounded class-update summary data, not an inline message feed
- `CourseDetail.vue` stays learning-first and exposes a single `Class Updates` handoff into the filtered student Communication Center
- the server resolves `learning.focus`, `learning.next_actions`, `learning.reflection_entries`, `learning.selected_context`, and `learning.unit_navigation`
- the student page stays learning-first and does not expose shared-plan management labels
- non-quiz assigned work opens back into `CourseDetail.vue` as the task workspace; quiz work launches `StudentQuiz.vue` only for attempt runtime

Operational guardrails:

- `get_student_learning_space` emits a structured `student_learning_space_load` planning event with `elapsed_ms`, `payload_bytes`, `db_query_count` when available, source mode, and unit/session/assigned-work counts
- successful responses over 1200 ms or 350 KB should emit a warning-level planning event and be treated as a hot-path regression to investigate
- file-backed student materials must serialize a server-resolved `open_url` only; raw private `file_url` values must not appear in the student LMS payload
- the class-plan bootstrap path should stay within a 40-query review budget in Frappe Recorder until a site-runtime query counter is available for hard enforcement

## Curriculum Read Model In The LMS

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

The student learning space currently renders:

- learning focus
- next actions
- reflection and journal capture inside the course workspace
- unit journey
- class sessions inside each unit
- session resources inside the selected class experience
- assigned work in its own student-facing zone
- unit resources
- class-wide resources
- shared course-plan resources
- task-linked materials directly on assigned-work cards

This is the live LMS model.

The old lesson-tree bootstrap is not the current source of truth for the student learning surface.

## Reflection In The Learning Loop

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/student_portfolio.py`, `ifitwala_ed/ui-spa/src/lib/services/portfolio/portfolioService.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_student_portfolio.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

- `get_student_learning_space()` now includes bounded `learning.reflection_entries` for the current course and class context.
- `CourseDetail.vue` exposes a contextual reflection composer and recent reflection stream inside the same class-owned learning workspace.
- Student reflection creation uses `Student Reflection Entry` with course, class, and optional session anchors; it does not create a second LMS tree or a second bootstrap contract.
- Reflections are learning evidence and journal context. Official assessed truth still lives in `Task Outcome` and `Task Outcome Criterion`; the reflection flow does not rewrite gradebook or reporting truth.

## Student Hub Handoff Into Course Context

Status: Implemented
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/student_communications.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_hub/get_student_hub_home.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_communication/get_student_communication_center.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentCommunicationCenter.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`

- `get_student_hub_home()` is allowed to link into the student course page, but it must route into the exact class-owned context when that context is known.
- Work-board, next-step, and timeline links should preserve `student_group`, `unit_plan`, and `class_session` whenever the source row has them.
- `get_student_hub_home()` may also expose bounded communication highlights, but those highlights must still link students back into the owning course, activity, or Communication Center context instead of creating a second inbox on Home.
- `StudentHome.vue` should hand students into `CourseDetail.vue`; it must not become a competing second LMS tree.
- `CourseDetail.vue` remains the canonical workspace for non-quiz assigned work, session flow, materials, and class-context review; it does not render class messages inline.
- The `Class Updates` action on `CourseDetail.vue` must route into `StudentCommunicationCenter.vue` with server-owned `course_id` and `student_group` filters applied.
- `StudentCommunicationCenter.vue` owns the portal-wide student history across class, activity, pastoral/cohort, and school-event items.

## Assigned Work In The LMS

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/assessment/doctype/task_delivery/test_task_delivery.py`, `ifitwala_ed/api/test_teaching_plans.py`

- `Task` remains the reusable work definition.
- `Task Delivery` remains the class-scoped assigned-work runtime object.
- LMS assigned work is resolved through `Class Teaching Plan` and optional `Class Session` context.
- Task materials are serialized with the assigned-work payload.
- Student quiz deliveries now include bounded quiz-launch state in the learning-space payload.
- `CourseDetail.vue` is now the canonical student launch surface for quiz-backed assigned work.
- The dedicated student quiz page remains the attempt and review runtime after launch.

## Native Quiz Contract

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/assessment/doctype/quiz_question/quiz_question.json`, `ifitwala_ed/assessment/doctype/quiz_attempt/quiz_attempt.json`, `ifitwala_ed/assessment/doctype/quiz_attempt_item/quiz_attempt_item.json`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/api/quiz.py`
Test refs: `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`

Live quiz capability already includes:

- `Quiz Question Bank`
- `Quiz Question`
- `Quiz Attempt`
- `Quiz Attempt Item`
- question randomization from a bank
- question and choice shuffling
- time-limited attempts
- maximum-attempt enforcement
- pass-percentage thresholds
- practice versus assessed behavior
- auto-scoring for choice and short-answer items
- manual-review state for essay items

Current supported question types:

- `Single Choice`
- `Multiple Answer`
- `True / False`
- `Short Answer`
- `Essay`

## Quiz Authoring And Assignment Rules

Status: Implemented
Code refs: `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/assessment/test_task_creation_service.py`, `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentQuizService.test.ts`

- A reusable `Task` is quiz-backed when `task_type = Quiz` and a `quiz_question_bank` is configured.
- Staff can author and update shared course quiz banks from the staff `Course Plan` workspace before assigning them.
- Staff can launch the existing task-delivery overlay directly from a selected published quiz bank in the course-plan workspace.
- Task creation snapshots quiz settings onto `Task Delivery`.
- Practice versus assessed behavior is determined by `Task Delivery.delivery_mode`:
  - `Assess` = assessed quiz
  - any other delivery mode = practice quiz
- Staff still assign quiz-backed work from the existing task-delivery overlay; the new flow is a prefilled entry into that same overlay, not a second assignment workflow.
- The task-delivery overlay lists published quiz banks only; draft banks stay in the authoring workspace until they are ready.

## Student Quiz Runtime

Status: Implemented
Code refs: `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/lib/services/student/studentQuizService.ts`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentQuizService.test.ts`

Named runtime endpoints:

- `ifitwala_ed.api.quiz.open_session`
- `ifitwala_ed.api.quiz.save_attempt`
- `ifitwala_ed.api.quiz.submit_attempt`

Current student route:

- `/student/courses/:course_id/quizzes/:task_delivery`

Current runtime behavior:

- open or continue the active attempt if one exists
- create the next allowed attempt when allowed
- return review mode when no new attempt is allowed
- keep attempt state server-owned
- update `Task Outcome` according to practice versus assessed rules
- preserve class and unit context back to `CourseDetail.vue`

## Staff Quiz Manual Review

Status: Implemented
Code refs: `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_task_quiz_manual_review.ts`, `ifitwala_ed/ui-spa/src/types/contracts/gradebook/save_task_quiz_manual_review.ts`, `ifitwala_ed/ui-spa/src/lib/services/gradebook/gradebookService.ts`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
Test refs: `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

The staff gradebook now owns the manual-review surface for assessed quiz items that require human scoring.

Current teacher behavior:

- assessed quiz tasks route into an `Open-ended Quiz Review` panel inside the existing gradebook shell
- teachers can review manually graded quiz items `by question` across a group or `by student`
- the teacher records `awarded_score` on each `Quiz Attempt Item` in the range `0..1`
- each save refreshes the canonical quiz attempt through `quiz_service.refresh_attempt(...)`
- official outcome totals remain server-derived from quiz attempt truth; the teacher does not type the assessed quiz total directly into `Task Outcome`

Current product boundary:

- this manual-review surface is for assessed quiz items only
- question-level rubric or criteria scoring for quiz items is not implemented yet
- overall teacher feedback and visibility controls remain outside this question-level review surface

## Security And Release Rules

Status: Implemented
Code refs: `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/quiz_service.py`
Test refs: `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`

Current enforced rules:

- student attempt access is server-scoped by student and course
- answer keys and correctness are not included in active attempt payloads
- assessed quiz review redacts score, percentage, correctness, accepted answers, correct options, and explanations
- quiz runtime responses set explicit no-store cache headers
- essay items remain in manual-review state until graded

## Concurrency And Idempotency

Status: Implemented
Code refs: `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/assessment/test_quiz_service.py`

The quiz service already enforces bounded runtime behavior:

- start/open uses cache locking to avoid duplicate in-progress attempts
- submit/refresh uses cache locking to keep attempt finalization idempotent
- save writes only the attempt items for the current attempt
- heavy correctness logic stays server-side

Do not move quiz correctness or attempt sequencing into client logic.

## Current Gaps And Non-Goals

Status: Partial
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
Test refs: None

Not implemented now:

- waiting-period-between-attempts policy
- a second gradebook or second LMS tree
- inline quiz-bank quick-create inside the task-delivery overlay
- question-level rubric or criteria scoring for quiz items

These are not missing documentation. They are real product boundaries today.

Planned next-phase student and guardian audience shaping is tracked separately in:

- `ifitwala_ed/docs/curriculum/05_student_and_guardian_learning_experience_proposal.md`

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `ifitwala_ed/docs/curriculum/05_student_and_guardian_learning_experience_proposal.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`

## Technical Notes (IT)

Status: Canonical
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`

- The student learning space and the quiz player are separate runtime surfaces today. Do not document them as one merged flow until `CourseDetail.vue` actually exposes quiz launch/state behavior.
- `CourseDetail.vue` now owns quiz launch, resume, and review entry points; `StudentQuiz.vue` stays the bounded runtime player.
- `get_student_learning_space` owns curriculum context. `api/quiz.py` plus `quiz_service.py` own quiz attempt workflows.
- Assessed feedback withholding is implemented in the server serializer, not by hiding fields in the SPA.
- Any change to quiz payload secrecy, attempt rules, or LMS launch flow must update this contract in the same change.

# Curriculum LMS And Quiz Contract

Status: Canonical current-state contract
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/quiz_service.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/assessment/doctype/quiz_question/quiz_question.json`, `ifitwala_ed/assessment/doctype/quiz_attempt/quiz_attempt.json`, `ifitwala_ed/assessment/doctype/quiz_attempt_item/quiz_attempt_item.json`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student_quiz/open_student_quiz_session.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/studentLearningHubService.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/studentQuizService.ts`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentQuizService.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

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
- `message`
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

## Curriculum Read Model In The LMS

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

The student learning space currently renders:

- unit backbone
- class sessions inside each unit
- unit resources
- session resources
- class-wide resources
- shared course-plan resources
- assigned work

This is the live LMS model.

The old lesson-tree bootstrap is not the current source of truth for the student learning surface.

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
- Staff can launch the existing task-delivery overlay directly from a selected shared lesson outline or selected published quiz bank in the course-plan workspace.
- Assign-from-lesson now carries the existing `Task.lesson` anchor through task creation; `Task Delivery` still remains class-plan and optional class-session scoped.
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

## Security And Release Rules

Status: Implemented with one explicit hardening gap
Code refs: `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/quiz_service.py`
Test refs: `ifitwala_ed/api/test_quiz.py`, `ifitwala_ed/assessment/test_quiz_service.py`

Current enforced rules:

- student attempt access is server-scoped by student and course
- answer keys and correctness are not included in active attempt payloads
- assessed quiz review redacts score, percentage, correctness, accepted answers, correct options, and explanations
- essay items remain in manual-review state until graded

Current gap that remains real:

- `api/quiz.py` does not currently set explicit cache-control headers for active attempt responses

Treat that as unfinished hardening work. Do not document it as already solved.

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
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: None

Not implemented now:

- direct `Lesson Activity` anchoring for quiz runtime
- waiting-period-between-attempts policy
- a second gradebook or second LMS tree
- inline quiz-bank quick-create inside the task-delivery overlay

These are not missing documentation. They are real product boundaries today.

## Related Docs

Status: Canonical map
Code refs: None
Test refs: None

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
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

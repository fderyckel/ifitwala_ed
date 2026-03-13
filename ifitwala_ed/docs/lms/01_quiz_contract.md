# Quiz Contract (Phase 1)

Status: Canonical approved contract for phase 1
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task/task.py`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, quiz-specific backend tests to be added in the same change
Last updated: 2026-03-13

This document is the canonical phase-1 contract for native quiz capacity in Ifitwala_Ed.

## Scope

Status: Implementing
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`
Test refs: quiz-specific backend tests to be added in the same change

Phase 1 adds:

- native quiz authoring records under the assessment module
- randomized question selection from a question bank
- timed attempts
- capped attempts
- pass-percentage thresholds
- practice quizzes and assessed quizzes
- student launch and continuation inside `/hub/student`

Phase 1 does not add:

- direct `Lesson Activity` quiz linkage on the live schema
- a second gradebook
- client-owned grading logic
- external Moodle or Canvas runtime dependency

## Core Contract

Status: Approved
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/docs/assessment/04_task_notes.md`
Test refs: quiz-specific backend tests to be added in the same change

1. `Task` remains the reusable learning-work definition.
2. `Task.task_type = Quiz` marks a task as quiz-backed work.
3. `Task Delivery` remains the assignable runtime object.
4. `Task Outcome` remains the official institutional result object.
5. Quiz runtime records are subordinate to `Task Delivery` and `Task Outcome`; they do not replace them.
6. Delivery mode determines whether a quiz is practice or assessed:
   - `Assign Only` or `Collect Work` = non-assessed practice quiz
   - `Assess` = assessed quiz
7. Quiz correctness, answer keys, and attempt state are server-owned invariants.

## Result Policy

Status: Approved
Code refs: `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.json`
Test refs: quiz-specific backend tests to be added in the same change

### Practice Quiz

- A practice quiz may record attempts, completion, score, percentage, and pass/fail status.
- A practice quiz must not create an official released grade by default.
- A practice quiz may mark `Task Outcome.is_complete` when the configured completion rule is met.

### Assessed Quiz

- An assessed quiz may write an official result only through server-owned quiz services.
- Auto-gradable items may finalize or partially finalize the outcome depending on manual-grading requirements.
- If manual grading remains, the outcome must move to a review state rather than silently publishing incomplete marks.
- Student-facing phase-1 review for assessed quizzes must withhold item-level correctness, answer keys, explanations, and unofficial score disclosure until an explicit release policy exists.

## Curriculum and Student Hub Integration

Status: Approved
Code refs: `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: `ifitwala_ed/api/test_courses.py`

- Phase 1 launches quizzes from the existing student course detail surface.
- The canonical path is:
  planned curriculum -> `Task` -> `Task Delivery` -> quiz runtime -> optional `Task Outcome`
- Course, unit, and lesson integration reuse existing `Task.learning_unit` and `Task.lesson` anchors.
- Phase 1 does not add direct `Lesson Activity` anchoring to `Task` or `Task Delivery`.

## Security Requirements

Status: Approved
Code refs: new quiz APIs and services to be added in the same change
Test refs: quiz-specific backend tests to be added in the same change

- Student payloads must never include answer keys or correctness metadata before review is allowed.
- Assessed quiz payloads must default to no item-level feedback and no unofficial score disclosure.
- Quiz start, save, continue, submit, and review must use named workflow endpoints.
- Every workflow endpoint must re-check student scope server-side.
- Active attempt responses must be non-cacheable.
- Review payloads must be regenerated server-side according to release policy; they must not be the active attempt payload with client-side hiding.

## Concurrency Requirements

Status: Approved
Code refs: `ifitwala_ed/docs/concurrency_01_proposal.md`, `ifitwala_ed/docs/concurrency_02_proposal.md`, `ifitwala_ed/docs/high_concurrency_03.md`
Test refs: quiz-specific backend tests to be added in the same change

- Attempt creation must be idempotent.
- Response save must be idempotent.
- Attempt submission must be idempotent.
- High-volume scheduled quizzes should support pre-created attempt shells and bounded background preparation.
- Heavy post-submit fan-out such as notifications or analytics recomputation must leave the request path.

## Contract Matrix

Status: Approved
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, quiz-specific backend tests to be added in the same change

| Concern | Phase 1 contract |
|---|---|
| Schema / DocType | Add quiz definition/runtime doctypes; extend `Task` and `Task Delivery` with quiz settings required for stable delivery behavior. |
| Controller / Workflow logic | Keep practice vs assessed semantics on the server, using `delivery_mode` as the official result boundary. |
| API endpoints | Extend student course detail payload with quiz summaries and add dedicated quiz runtime endpoints. |
| SPA / student surfaces | Keep launch and continuation inside `/hub/student` and the existing course detail flow. |
| Reports / gradebook | Do not create a second gradebook; only assessed quizzes may feed official results. |
| Scheduler / background jobs | Use bounded background preparation where high-volume synchronized starts need it. |
| Tests | Cover start/save/submit idempotency, answer secrecy, scope enforcement, and student hub payload parity. |

## Technical Notes (IT)

Status: Approved
Code refs: `ifitwala_ed/docs/assessment/04_task_notes.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

- This contract intentionally keeps direct `Lesson Activity` schema changes out of phase 1.
- Practice-vs-assessed behavior is a delivery concern, not a separate quiz doctype family.
- The student hub remains the canonical launch surface; no hardcoded paths outside the SPA router are allowed.

---
title: "Quiz Question Bank: Shared Quiz Authoring Set For A Course"
slug: quiz-question-bank
category: Assessment
doc_order: 18
version: "1.0.3"
last_change_date: "2026-04-25"
summary: "Define a reusable course-level quiz question bank that staff can author in the course-plan workspace and assign later through quiz-backed tasks."
seo_title: "Quiz Question Bank: Shared Quiz Authoring Set For A Course"
seo_description: "Define a reusable course-level quiz question bank that staff can author in the course-plan workspace and assign later through quiz-backed tasks."
---

## Quiz Question Bank: Shared Quiz Authoring Set For A Course

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/assessment/doctype/quiz_question/quiz_question.json`, `ifitwala_ed/api/quiz.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`, `ifitwala_ed/ui-spa/src/lib/planning/coursePlanWorkspace.ts`
Test refs: `ifitwala_ed/api/test_quiz.py`

`Quiz Question Bank` is the shared reusable question set for quiz-backed tasks. In the current workspace schema it belongs to a `Course`, and the staff `Course Plan` workspace is the primary SPA authoring surface for it.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/api/quiz.py`
Test refs: `ifitwala_ed/api/test_quiz.py`

- Start from a `Course Plan` you can edit because the current SPA authoring flow derives quiz-bank write access from that governing plan.
- Decide whether the bank is still a draft or ready for assignment.
- Prepare at least one published question before expecting the bank to appear in the quiz assignment step.

## Where It Is Used Across The ERP

Status: Implemented
Code refs: `ifitwala_ed/api/quiz.py`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: `ifitwala_ed/api/test_quiz.py`

- Shared assessment authoring object for a course.
- Source bank for quiz-backed `Task` definitions through `Task.quiz_question_bank`.
- Authored in the staff `Course Plan` workspace.
- Selected later from the task-delivery overlay when teachers assign a quiz-backed task.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/api/quiz.py`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`
Test refs: `ifitwala_ed/api/test_quiz.py`

1. Open the shared `Course Plan` workspace for the relevant course.
2. Create or update a `Quiz Question Bank`.
3. Add one or more `Quiz Question` rows, including any choice options or accepted short answers.
4. Publish the bank and the questions you want teachers to assign.
5. Select the bank later when creating a quiz-backed task in the assignment flow.

## Related Docs

<RelatedDocs
  slugs="course-plan,task,task-delivery"
  title="Related Documentation"
/>

## Technical Notes (IT)

Status: Implemented
Code refs: `ifitwala_ed/assessment/doctype/quiz_question_bank/quiz_question_bank.json`, `ifitwala_ed/assessment/doctype/quiz_question/quiz_question.json`, `ifitwala_ed/api/quiz.py`
Test refs: `ifitwala_ed/api/test_quiz.py`

- `Quiz Question Bank` currently stores `bank_title`, `course`, `is_published`, and `description`.
- Questions are separate parent docs in `Quiz Question`, not child rows on the bank.
- `ifitwala_ed.api.quiz.save_question_bank` now owns SPA-side bank saves plus question replacement.
- Quiz-bank authoring UI now lives in `ui-spa/src/components/planning/course-plan-workspace/CoursePlanQuizBanksSection.vue`, while `CoursePlanWorkspace.vue` remains the route/bootstrap/save owner so the course-plan page keeps one bounded payload and one canonical assignment handoff.
- Quiz question `prompt` and `explanation` are sanitized server-side before save, and bank updates now reject stale `expected_modified` tokens using an aggregate fingerprint over the bank and its current question rows.
- Quiz-bank saves now emit bounded `ifitwala.curriculum` timing/status logs so GCP Cloud Logging metrics can track latency and failures on this hot authoring path.
- Published question banks are the only ones shown in the quiz selection step of the task-delivery overlay.
- Keep quiz attempt rules and LMS runtime behavior documented in `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`.

# Quiz Runtime And Teacher-Entered Assessment Convergence Spec

Status: **Proposed design spec / non-authoritative until canonical runtime docs are updated**
Audience: Product, Engineering, UX, and coding agents
Scope: Quiz-aware gradebook drawer, native quiz manual-review convergence, teacher-graded paper quiz compatibility, and canonical doc migration
Last updated: 2026-04-19

Important note:

- This document is a design target, not current runtime truth.
- It does not replace the canonical contracts in `04_curriculum_lms_and_quiz_contract.md`, `04_task_notes.md`, `03_gradebook_notes.md`, or `07_feedback_annotation_ecosystem_contract.md`.
- If implementation lands, update those canonical docs in the same change.

Related docs:

- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/09_feedback_records_and_publication_rfc.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

---

## 0. Bottom Line

`Quiz` must stop meaning only `native online quiz runtime`.

Ifitwala_Ed should support one pedagogical assessment family with two compatible execution paths:

- native online quiz, scored through `Quiz Attempt` and `Quiz Attempt Item`
- teacher-graded quiz, including in-class paper quizzes, scored through the standard gradebook contribution workflow

Both paths should converge on the same institutional truth:

- `Task Delivery` remains the class-scoped assignment
- `Task Outcome` remains the official result and reporting boundary
- the Gradebook drawer remains the canonical teacher workspace

Native quiz runtime remains a specialized evidence/scoring engine.
Paper quizzes must not be forced through that engine.

---

## 1. Current Mismatch

Status: **Current workspace reality**

Code refs:

- `ifitwala_ed/assessment/doctype/task/task.py`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/assessment/quiz_service.py`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_drawer.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/gradebook/get_task_quiz_manual_review.ts`

The current model has three structural problems:

1. `Task.task_type == "Quiz"` is overloaded.
   It currently means both:
   - pedagogical type: this is a quiz
   - runtime type: this must use native question-bank quiz machinery

2. Assessed native quizzes still bypass the canonical drawer workflow.
   The teacher uses `get_task_quiz_manual_review` and `save_task_quiz_manual_review`, not the standard drawer bootstrap/write contract.

3. Quiz student visibility still uses runtime-specific rules.
   `quiz_service._student_feedback_allowed()` still reduces visibility to `delivery_mode != "Assess"`, which is too blunt for the newer feedback and publication model.

The result is product drift:

- gradebook drawer is canonical for assessed work
- native quiz manual review is still parallel
- paper quizzes cannot be modeled cleanly as “a quiz the teacher grades and returns”

---

## 2. Design Goals

Status: **Target**

This refactor should achieve the following:

1. A teacher can assign a quiz in either of these ways without leaving the assessment model:
   - online in Ifitwala_Ed
   - offline in class on paper

2. Students should experience only the right runtime:
   - online quiz launches the quiz player
   - paper quiz shows instructions and later released results, not a fake online player

3. Teachers should work inside one grading product:
   - gradebook grid
   - grading drawer
   - optional queue modes such as grade-by-question

4. Official truth stays unified:
   - no second gradebook
   - no second reporting fact table
   - no fake submission model for native quiz attempts

5. Release rules stay explicit:
   - grade release
   - feedback release
   - quiz solution release

6. High-concurrency rules remain intact:
   - one bounded drawer bootstrap
   - no request waterfalls
   - no client-owned scoring logic

---

## 3. Non-Goals

Status: **Target constraint**

This design does **not** recommend:

- forcing native quiz item scoring into one `Task Contribution` per question
- creating fake `Task Submission` rows to represent native quiz attempts
- treating paper quizzes as a variant of `Collect Work`
- coupling answer-key release to generic grade release
- introducing question-level rubric scoring for native quiz items in the same phase

Question-level criteria scoring for native quiz items can be a later phase.
It should not block convergence of drawer, publication, and paper-quiz compatibility.

---

## 4. Recommended Product Model

Status: **Target**

### 4.1 Keep `task_type` pedagogical

`task_type` should describe what the work **is** in teacher and student language.

Examples:

- `Quiz`
- `Test`
- `Assignment`
- `Project`

It should not be the sole switch for runtime internals.

### 4.2 Add an explicit execution/capture mode

Recommended target field name:

- `assessment_capture_mode`

Recommended values:

- `student_submission`
- `native_quiz`
- `teacher_entered`

Recommended ownership:

- `Task.assessment_capture_mode` as the reusable default
- `Task Delivery.assessment_capture_mode` as the locked delivery snapshot

Meaning:

- `student_submission`
  student uploads or enters evidence; teacher grades through `Task Submission` + `Task Contribution`
- `native_quiz`
  student works through `Quiz Attempt` + `Quiz Attempt Item`; teacher reviews through quiz-aware drawer blocks
- `teacher_entered`
  no learner digital evidence is required; teacher records official judgment directly in the drawer through contribution writes

### 4.3 Compatibility matrix

| Teacher intent | `task_type` | `delivery_mode` | `assessment_capture_mode` | Teacher grading path | Student runtime |
| --- | --- | --- | --- | --- | --- |
| Online assessed quiz | `Quiz` | `Assess` | `native_quiz` | quiz-aware drawer + native quiz scoring | `StudentQuiz.vue` |
| Online practice quiz | `Quiz` | non-`Assess` | `native_quiz` | no official assessed grading | `StudentQuiz.vue` |
| In-class paper quiz, teacher enters scores | `Quiz` | `Assess` | `teacher_entered` | standard drawer contribution flow | no quiz player |
| Worksheet or essay submission | non-quiz task | `Assess` or `Collect Work` | `student_submission` | standard drawer contribution flow | LMS task workspace |

Key rule:

`Quiz` is now one assessment family.
`native_quiz` is only one capture mode inside that family.

---

## 5. Recommended Runtime Ownership

Status: **Target**

### 5.1 Official truth

Keep:

- `Task Delivery` as assignment context
- `Task Outcome` as official student result
- `Task Outcome Criterion` as official criterion-level truth where applicable

### 5.2 Standard teacher-entered paper quiz

For paper quizzes:

- no `Quiz Attempt`
- no `Quiz Attempt Item`
- no quiz player route
- no question bank requirement

Teacher grading uses:

- `Task Contribution`
- optionally `judgment_code`, score, grade, feedback, or criteria rows

This is already aligned with the drawer-centered assessment model.

### 5.3 Native online quiz

For online quizzes:

- `Quiz Attempt` and `Quiz Attempt Item` remain the attempt/evidence/scoring substrate
- auto-scoring remains server-side in `quiz_service.py`
- manual item scoring remains stored on `Quiz Attempt Item`
- `Task Outcome` remains derived official truth after attempt refresh

This stays a specialized runtime, but it should no longer require a parallel teacher product.

---

## 6. Target Gradebook Drawer Contract

Status: **Target API**

The drawer remains the canonical teacher workspace for all assessed work.

The current `get_drawer` contract should be extended, not replaced.

### 6.1 Target request

```ts
export type Request = {
  outcome_id: string
  submission_id?: string | null
  version?: number | null
  quiz_attempt?: string | null
  quiz_item?: string | null
  queue_mode?: 'student' | 'question' | null
}
```

Request rules:

- `submission_id` and `version` continue to select evidence for `student_submission`
- `quiz_attempt` selects the active review attempt for `native_quiz`
- `quiz_item` focuses one question/item inside the selected native quiz attempt
- `queue_mode` is optional drawer context for next/previous navigation

### 6.2 Target response additions

Keep the existing response blocks:

- `delivery`
- `student`
- `outcome`
- `latest_submission`
- `selected_submission`
- `submission_versions`
- `my_contribution`
- `moderation_history`
- `allowed_actions`
- `contributions`

Add the following blocks:

```ts
export type ReviewContext = {
  kind: 'submission_version' | 'quiz_attempt' | 'teacher_entered'
  source: 'standard_task' | 'native_quiz' | 'teacher_entered_quiz'
  queue_mode?: 'student' | 'question' | null
  navigation: {
    previous_outcome_id?: string | null
    next_outcome_id?: string | null
    previous_quiz_item?: string | null
    next_quiz_item?: string | null
  }
}

export type PublicationChannel = {
  state: 'hidden' | 'student' | 'student_and_guardian'
  released_on?: string | null
  released_by?: string | null
}

export type QuizSolutionChannel = {
  state: 'hidden' | 'student'
  policy: 'manual' | 'after_final_attempt' | 'with_grade_release'
  released_on?: string | null
  released_by?: string | null
}

export type QuizAttemptSummary = {
  quiz_attempt: string
  attempt_number: number
  status: 'In Progress' | 'Submitted' | 'Needs Review' | 'Graded'
  submitted_on?: string | null
  is_selected: boolean
}

export type QuizReviewItem = {
  item_id: string
  quiz_question: string
  title: string
  position: number
  question_type: string
  prompt_html?: string | null
  response_text?: string | null
  selected_option_ids: string[]
  selected_option_labels: string[]
  awarded_score?: number | null
  requires_manual_grading: boolean
  is_selected: boolean
}

export type QuizReviewBlock = {
  manual_item_count: number
  pending_item_count: number
  attempts: QuizAttemptSummary[]
  items: QuizReviewItem[]
}
```

Target response shape:

```ts
export type Response = ExistingDrawerResponse & {
  review_context: ReviewContext
  publication: {
    grade: PublicationChannel
    feedback: PublicationChannel
    solutions?: QuizSolutionChannel | null
  }
  quiz_review?: QuizReviewBlock | null
}
```

### 6.3 Behavioral rules

- `review_context.kind = 'submission_version'`
  - standard evidence-based work
  - `selected_submission` is meaningful
  - `quiz_review = null`

- `review_context.kind = 'teacher_entered'`
  - paper quiz or other teacher-entered assessment
  - `selected_submission = null` unless a teacher-created evidence stub exists
  - standard `my_contribution` writes remain canonical
  - `quiz_review = null`

- `review_context.kind = 'quiz_attempt'`
  - native online quiz
  - `selected_submission = null`
  - `quiz_review` contains attempt/item review context
  - contribution writes are not used for question-level manual scoring

---

## 7. Target Review Queue Contract

Status: **Target API**

`get_task_quiz_manual_review` is too specialized to remain the long-term queue contract.

Recommended replacement endpoint:

- `get_task_review_queue`

### 7.1 Target request

```ts
export type Request = {
  task: string
  queue_kind?: 'grading' | 'collect_work' | 'quiz_manual'
  view_mode?: 'student' | 'question' | null
  student?: string | null
  quiz_question?: string | null
}
```

### 7.2 Target response

```ts
export type QueueRow = {
  outcome_id: string
  student: string
  student_name: string
  student_id?: string | null
  student_image?: string | null
  grading_status?: string | null
  review_context_kind: 'submission_version' | 'quiz_attempt' | 'teacher_entered'
  submission_id?: string | null
  version?: number | null
  quiz_attempt?: string | null
  quiz_item?: string | null
  quiz_question?: string | null
  title?: string | null
  badge_count?: number | null
}

export type Response = {
  task: {
    name: string
    title: string
    student_group: string
    delivery_mode?: string | null
    task_type?: string | null
    assessment_capture_mode?: 'student_submission' | 'native_quiz' | 'teacher_entered' | null
  }
  queue_kind: 'grading' | 'collect_work' | 'quiz_manual'
  view_mode: 'student' | 'question'
  summary: {
    pending_count: number
    pending_student_count?: number | null
    pending_attempt_count?: number | null
  }
  questions?: Array<{
    quiz_question: string
    title: string
    pending_count: number
  }>
  students: Array<{
    student: string
    student_name: string
    pending_count: number
  }>
  rows: QueueRow[]
}
```

### 7.3 Why this replaces the current quiz-only endpoint

- one queue contract can support:
  - collect-work evidence inbox
  - standard grading queue
  - quiz manual-review queue
- drawer navigation becomes consistent
- the queue owns list context; the drawer owns one-student review context

---

## 8. Target Write Contracts

Status: **Target API**

### 8.1 Standard teacher-entered paper quiz

Paper quizzes should use the existing contribution writes:

- `save_draft`
- `submit_contribution`
- `moderator_action`

No quiz-specific write path is needed.

### 8.2 Native online quiz manual scoring

Recommended named endpoint:

- `save_quiz_manual_scores`

Target request:

```ts
export type Request = {
  outcome_id: string
  quiz_attempt: string
  items: Array<{
    item_id: string
    awarded_score: number | null
  }>
}
```

Target response:

```ts
export type Response = {
  updated_item_count: number
  refreshed_attempt: {
    quiz_attempt: string
    status: 'Submitted' | 'Needs Review' | 'Graded'
    pending_item_count: number
  }
  refreshed_outcome: {
    outcome_id: string
    grading_status?: string | null
    official_score?: number | null
    official_grade?: string | null
    official_grade_value?: number | null
  }
}
```

Write rules:

- validate outcome ownership and group access first
- validate the `quiz_attempt` belongs to the selected `Task Outcome`
- only `MANUAL_TYPES` remain writable from this surface
- scoring remains server-side
- the response returns enough data for optimistic drawer refresh without a full page reload

---

## 9. Publication And Student-Visibility Model

Status: **Target**

The current native quiz rule:

- `allow_feedback = delivery_mode != "Assess"`

should be retired.

Recommended release channels:

- `grade`
- `feedback`
- `solutions`

Rules:

1. `grade` controls official score / grade visibility.
2. `feedback` controls teacher-authored explanatory feedback visibility.
3. `solutions` controls correct answers, accepted answers, and explanations for native quiz review.

Key quiz rule:

`solutions` must remain independent from `grade` and `feedback`.

This prevents a regression where:

- a teacher releases grades
- the system accidentally exposes answer keys for future reuse

Recommended native quiz default:

- assessed quiz solutions stay hidden until an explicit release policy allows them

Recommended paper quiz default:

- no solution channel exists unless teacher-authored answer sheets or feedback artifacts are later introduced

---

## 10. UI Refactor Direction

Status: **Target**

### 10.1 Task creation and delivery overlay

For `task_type = "Quiz"`, the overlay should ask:

- `How will students take this quiz?`

Recommended options:

- `Online in Ifitwala_Ed`
- `In class / teacher graded`

Behavior:

- `Online in Ifitwala_Ed`
  - requires question bank
  - shows quiz runtime fields
  - sets `assessment_capture_mode = native_quiz`

- `In class / teacher graded`
  - hides question bank requirements
  - uses standard grading settings
  - sets `assessment_capture_mode = teacher_entered`

This change is required to make paper quizzes a first-class product path instead of a naming workaround.

### 10.2 Gradebook drawer

The drawer should branch by `review_context.kind`:

- `submission_version`
  standard evidence review
- `teacher_entered`
  no-digital-evidence grading view
- `quiz_attempt`
  native quiz review with attempt/items block

### 10.3 Student surfaces

- `native_quiz`
  - student sees launch/resume/review behavior through the LMS + `StudentQuiz.vue`
- `teacher_entered`
  - student sees assigned assessment context and later released result
  - student must not see a launch button for a nonexistent online runtime

---

## 11. Migration Path From `get_task_quiz_manual_review`

Status: **Target phased rollout**

### Phase 1

- add `assessment_capture_mode` to the target design
- extend `get_drawer` with `review_context`, `publication`, and optional `quiz_review`
- add `get_task_review_queue`
- add `save_quiz_manual_scores`

### Phase 2

- move Gradebook SPA from:
  - `get_task_quiz_manual_review`
  - `save_task_quiz_manual_review`

  to:
  - `get_task_review_queue`
  - extended `get_drawer`
  - `save_quiz_manual_scores`

### Phase 3

- keep `get_task_quiz_manual_review` as a thin adapter over `get_task_review_queue`
- keep `save_task_quiz_manual_review` as a thin adapter over `save_quiz_manual_scores`
- mark both deprecated in code comments and typed contracts

### Phase 4

- remove deprecated quiz-only endpoints after SPA cutover and test replacement

Key migration rule:

Do not break current teacher manual-review capability while converging to the drawer.

---

## 12. Canonical Doc Patch Set After Implementation

Status: **Target documentation plan**

When implementation lands, update the following canonical docs.

### 12.1 `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`

Refactor the doc so it focuses on:

- student launch/runtime for `native_quiz`
- LMS routing rules
- student payload secrecy
- solution-release rules
- distinction between:
  - native online quiz
  - teacher-entered quiz result

Remove long-term teacher-gradebook architecture from this doc.
That ownership belongs in assessment docs.

### 12.2 `ifitwala_ed/docs/assessment/04_task_notes.md`

Update the quiz section to state:

- `Quiz` is a task family, not only a native runtime
- `assessment_capture_mode` owns the execution path
- paper quizzes are compatible assessed tasks
- native quiz attempt truth remains specialized and still derives official outcome truth

### 12.3 `ifitwala_ed/docs/assessment/03_gradebook_notes.md`

Update the drawer spec to add:

- `review_context.kind`
- quiz-aware drawer block
- grade-by-question queue as part of the same drawer ecosystem
- teacher-entered quiz behavior as a standard assessed drawer path

### 12.4 `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

Extend the feedback contract to support review contexts beyond `submission_version`:

- `quiz_attempt`
- optionally `teacher_entered` with no selected digital evidence

Also add quiz-specific `solutions` publication guidance distinct from grade and feedback release.

### 12.5 `ifitwala_ed/docs/docs_md/task.md`

Update end-user guidance so teachers understand:

- a quiz can be assigned online or run in class on paper
- both still land in the same gradebook/reporting model

### 12.6 `ifitwala_ed/docs/docs_md/task-delivery.md`

Update end-user guidance so staff understand:

- assignment setup asks how the assessment is captured
- online quiz and teacher-entered paper quiz have different student/runtime behavior

---

## 13. Risks To Control During Implementation

Status: **Target**

### 13.1 UX risk

If the overlay keeps using `task_type == "Quiz"` as the only switch, teachers will keep treating paper quizzes as broken or unsupported.

### 13.2 Data-model risk

If paper quizzes are forced into `Quiz Attempt`, the system will create artificial runtime complexity and wrong audit semantics.

### 13.3 Release risk

If quiz solutions are folded into generic feedback release, assessed answer keys may leak earlier than intended.

### 13.4 Concurrency risk

If quiz manual review is rebuilt with multiple per-row fetches instead of bounded drawer + queue reads, the teacher grading path will regress under class-scale load.

---

## 14. Recommended First Implementation Slice

Status: **Target**

If this refactor begins, the first slice should be:

1. introduce the explicit capture-mode concept
2. make paper quizzes first-class in task/delivery authoring
3. extend `get_drawer` with `review_context`
4. move native quiz manual review into the drawer ecosystem without removing existing scoring rules

Do **not** start with rubric-scored quiz questions.
That is a second-phase enhancement after the product model is correct.

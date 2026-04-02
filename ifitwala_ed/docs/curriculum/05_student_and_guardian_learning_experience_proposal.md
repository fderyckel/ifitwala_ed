# Student And Guardian Curriculum Experience Proposal

Status: Partially implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`, `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`, `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

This document defines the current target shape for curriculum visibility in the student portal and the guardian portal.

The student learning-first LMS framing, guardian home `learning_highlights`, and guardian child learning brief are now implemented. Remaining refinements should extend this direction rather than reopen the older curriculum-tree or timeline-first shapes.

## Why This Proposal Exists

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: None yet

The educator-centered curriculum model is now live on the backend and staff surfaces:

- `Course Plan`
- `Unit Plan`
- `Class Teaching Plan`
- `Class Session`
- `Task Delivery`

Students and guardians should benefit from that model, but each audience needs a different experience.

Rules:

1. Students need a learning surface, not a planning surface.
2. Guardians need an awareness surface, not a second LMS.
3. Neither audience should inherit staff-facing language or staff-facing complexity by accident.
4. Each page mode must stay bounded under the high-concurrency contract.

## Student Product Goal

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`
Test refs: None yet

The student portal should answer four questions immediately:

1. What am I learning now?
2. What do I need to do next?
3. What do I need to complete it?
4. What should I review or revisit?

The student should not be asked to interpret curriculum management concepts.

## Guardian Product Goal

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ifitwala_ed/api/guardian_home.py`
Test refs: None yet

The guardian portal should answer four questions immediately:

1. What is my child learning right now?
2. What is coming up soon?
3. What can we talk about or support at home?
4. Is there anything requiring my attention?

The guardian should not need to parse daily lesson mechanics or internal school workflow state.

## Student Experience Principles

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: None yet

Rules:

1. Default the student to the current or next meaningful learning context, not the first curriculum row.
2. Show only student-safe content from `Unit Plan`, `Class Session`, `Class Session Activity`, and `Task Delivery`.
3. Put action before reference: next work, next session, and next quiz launch come before full-unit reading.
4. Keep standards available only as optional learning-goal context, not as the main information layer.
5. Hide all teacher-only fields and planning-state language.

## Proposed Student Page Structure

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: None yet

`CourseDetail.vue` should be reorganized into these zones:

### 1. Learning Focus

Purpose:

- establish the current unit or class focus
- orient the student without requiring navigation first

Contents:

- course title
- class label
- current unit title
- current or next class session title
- one short current focus statement

### 2. Next Actions

Purpose:

- reduce friction
- make the next required step obvious

Contents:

- next due assigned work
- next quiz start / continue / review CTA
- next class session date when relevant
- only the resources needed for the next task or session

### 3. This Unit

Purpose:

- show the big picture for what the student is learning

Contents:

- unit title
- overview
- essential understanding
- simplified learning goals drawn from `content`, `skills`, and `concepts`
- optional standards drawer labeled as learning goals or curriculum goals

### 4. Session Journey

Purpose:

- show the sequence of student-facing class sessions inside the selected unit

Contents:

- session title
- session date
- learning goal
- student-facing activity steps only
- session resources
- session-linked assigned work

### 5. Everything Else In This Course

Purpose:

- allow controlled navigation without turning the page into a data dump

Contents:

- unit navigation rail
- additional shared resources
- completed or older assigned work

## Proposed Student Read Model Changes

Status: Proposed
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: None yet

The student surface should keep one bounded bootstrap through `get_student_learning_space`.

Instead of only returning raw structural groupings, the response should add derived student-facing sections:

- `focus`
- `next_actions`
- `selected_context`
- `unit_navigation`
- `selected_unit`
- `selected_session`

Proposed additions:

```ts
type StudentLearningFocus = {
  current_unit?: { unit_plan: string; title: string } | null
  current_session?: { class_session: string; title: string; session_date?: string | null } | null
  statement?: string | null
}

type StudentNextAction = {
  kind: 'assigned_work' | 'quiz' | 'session'
  label: string
  supporting_text?: string | null
  task_delivery?: string | null
  class_session?: string | null
  unit_plan?: string | null
}
```

Rules:

1. These are read-model conveniences only; they do not create new curriculum truth.
2. They must be server-resolved, not assembled from multiple client calls.
3. Selection precedence should remain class-owned data first, shared plan fallback second.

## Student Visibility Rules

Status: Proposed
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: None yet

Students may see:

- `Unit Plan.title`
- `Unit Plan.overview`
- `Unit Plan.essential_understanding`
- `Unit Plan.content`
- `Unit Plan.skills`
- `Unit Plan.concepts`
- student-safe `standards`
- `Class Session.title`
- `Class Session.session_date`
- `Class Session.learning_goal`
- `Class Session Activity.student_direction`
- `Class Session Activity.resource_note`
- class-safe resources
- assigned work and quiz launch state

Students must not see:

- `Course Plan` as a management object
- `Class Teaching Plan` as a planning object
- `teacher_note`
- `teacher_prompt`
- shared reflections
- class reflections
- pacing notes
- governed-required flags
- internal planning status beyond necessary release state

## Guardian Experience Principles

Status: Proposed
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
Test refs: None yet

Rules:

1. Guardian home stays family-first.
2. Curriculum appears as a learning brief, not as a child-course admin console.
3. Guardians see big themes, major experiences, and support-at-home context.
4. Guardians do not see draft curriculum truth, daily teaching mechanics, or staff-only reflections.
5. Guardian curriculum visibility must be separately filtered server-side and must not reuse the student LMS payload wholesale.

## Proposed Guardian Home Additions

Status: Proposed
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
Test refs: None yet

Add a fifth family-home zone:

- `learning_highlights`

Purpose:

- give one short curriculum-aware briefing per child
- support family conversation and home support

Contents per child:

- current course or current highlight title
- current unit title
- one short current theme statement
- upcoming major assessment or learning experience
- optional home conversation prompt

This zone belongs on guardian home because it answers "what are my children learning?" without requiring a drill-down first.

## Proposed Guardian Child Page

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: None yet

The child drill-down should add a curriculum-aware section called:

- `Learning Now`

This section should be grouped by course and show:

- course title
- current unit title
- unit overview
- essential understanding
- upcoming major experiences
- upcoming assessments
- support-at-home materials or prompts when explicitly guardian-safe

It should not show:

- session activity sequence
- class session internal notes
- quiz runtime controls
- raw standards tables by default

## Proposed Guardian Endpoints

Status: Proposed
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: None yet

Two bounded contracts are recommended:

### 1. Extend `get_guardian_home_snapshot`

Add:

- `zones.learning_highlights`

This keeps family home on one bounded bootstrap.

### 2. Add `get_guardian_student_learning_brief(student_id)`

Purpose:

- provide a deeper curriculum-aware child briefing without forcing guardian home to carry every course detail for every child

Proposed response:

```ts
type GuardianStudentLearningBrief = {
  student: { student: string; full_name: string; school?: string | null }
  highlights: Array<{
    course: string
    course_name: string
    student_group?: string | null
    current_unit?: {
      unit_plan: string
      title: string
      overview?: string | null
      essential_understanding?: string | null
    } | null
    upcoming: {
      assessments: Array<{ task_delivery: string; title: string; due_date?: string | null }>
      experiences: Array<{ class_session: string; title: string; session_date?: string | null }>
    }
    family_support?: {
      discussion_prompt?: string | null
      resources: Array<{ title: string; open_url?: string | null }>
    }
  }>
}
```

Rules:

1. This endpoint is guardian-specific and must not expose the full student LMS contract.
2. It must resolve only linked children.
3. It must remain one bounded bootstrap per child page.

## Guardian Visibility Rules

Status: Proposed
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
Test refs: None yet

Guardians may see:

- course title
- class label
- current unit title
- unit overview
- essential understanding
- upcoming major learning experiences
- upcoming assigned work or assessments
- published outcomes already allowed elsewhere
- support-at-home prompts or resources explicitly marked or derived as guardian-safe

Guardians must not see:

- unpublished or draft class teaching plans
- raw class-session activity sequences
- teacher prompts
- teacher notes
- shared or class reflections
- hidden quiz correctness data
- internal planning or scheduling fields such as `rotation_day` or `block_number`

## Source Hierarchy For Both Audiences

Status: Proposed
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/guardian_home.py`
Test refs: None yet

Resolution order should remain:

1. class-owned teaching context
2. shared unit/course-plan fallback
3. explicit unavailable or awaiting-publication state

But the visible shaping must differ by audience:

- student = operational learning context
- guardian = summarized awareness context

## Implementation Sequence

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: None yet

Recommended order:

1. Reframe the student course page around `Learning Focus`, `Next Actions`, and `This Unit`.
2. Extend the student read model with server-derived focus and next-action helpers.
3. Add `learning_highlights` to guardian home.
4. Add a guardian child learning-brief endpoint and redesign the child drill-down around `Learning Now`.
5. Validate permission and sibling-isolation rules for every new guardian curriculum field.

## Optional Future Authoring

Status: Proposed
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`
Test refs: None yet

Do not add new teacher authoring burden in the first implementation unless derived summaries prove inadequate.

If a second phase is needed later, the preferred additions would be:

- one optional family-facing discussion prompt at `Unit Plan`
- one optional home-support note at `Class Session`

These should stay optional and must not block teacher workflow.

## Non-Goals

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: None yet

This proposal does not recommend:

- a second student LMS tree
- exposing staff planning semantics to students or guardians
- guardian access to daily lesson-plan internals
- student or guardian client waterfalls
- required extra teacher authoring fields before proving the need

## Related Docs

Status: Proposed
Code refs: None
Test refs: None yet

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

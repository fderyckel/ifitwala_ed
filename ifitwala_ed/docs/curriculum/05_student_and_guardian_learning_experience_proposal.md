# Student And Guardian Curriculum Experience Proposal

Status: Implemented with ongoing polish
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`, `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`, `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

This document defines the current target shape for curriculum visibility in the student portal and the guardian portal.

The student learning-first LMS framing, guardian home `learning_highlights`, and guardian child learning brief are now implemented. Remaining refinements should extend this direction rather than reopen the older curriculum-tree or timeline-first shapes.

## Current Product State

Status: Implemented
Code refs: `ifitwala_ed/curriculum/planning.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.py`, `ifitwala_ed/schedule/doctype/student_group/student_group.js`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

Current live behavior:

- the student course page leads with `Learning Focus`, `Next Actions`, a sticky `Jump to` strip, `Session Journey` before the denser `This Unit` summary, a dedicated `Assigned Work` zone, and scoped resources
- the student course page now includes a contextual `Reflection & Journal` zone inside the same course workspace instead of pushing quick reflection into a second student flow
- assigned-work resources now surface through the resource stream and the selected task workspace, while `CourseDetail.vue` remains the workspace entry for non-quiz work instead of forcing a second task page
- student hub work-board and timeline links now preserve `class_session` context when available so students land on the right class experience directly
- student-facing surfaces now hide shared-plan management labels and raw planning-state language
- the student course page now uses one colorful resource stream ordered by immediacy: needed now, this unit, your class, and collapsed course references
- staff setup now treats Class Delivery as the live student-group delivery anchor, auto-created where possible from Student Group context and surfaced through Student Group setup when a Course Plan choice is needed
- guardian home uses `learning_highlights` cards with a family-safe current theme, upcoming step, and a talk-at-home prompt
- the guardian child brief now foregrounds current theme, next class experience, upcoming learning experiences, and helpful-at-home resources
- student, guardian, and staff learning surfaces now default from the same server-owned current-curriculum resolver instead of opening the first unit by guess

## Why This Note Exists

Status: Active
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

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

Status: Implemented direction
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

The student portal should answer four questions immediately:

1. What am I learning now?
2. What do I need to do next?
3. What do I need to complete it?
4. What should I review or revisit?

The student should not be asked to interpret curriculum management concepts.

## Guardian Product Goal

Status: Implemented direction
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`, `ifitwala_ed/api/guardian_home.py`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

The guardian portal should answer four questions immediately:

1. What is my child learning right now?
2. What is coming up soon?
3. What can we talk about or support at home?
4. Is there anything requiring my attention?

The guardian should not need to parse daily lesson mechanics or internal school workflow state.

## Student Experience Principles

Status: Implemented direction
Code refs: `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

Rules:

1. Default the student to the server-resolved current or next meaningful learning context, not the first curriculum row.
2. Show only student-safe content from `Unit Plan`, `Class Session`, `Class Session Activity`, and `Task Delivery`.
3. Put action before reference: next work, next session, and next quiz launch come before full-unit reading.
4. Keep standards available only as optional learning-goal context, not as the main information layer.
5. Hide all teacher-only fields and planning-state language.

## Student Page Structure

Status: Implemented baseline
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

`CourseDetail.vue` is now organized around these zones:

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

### 3. Jump To And Unit Rail

Purpose:

- remove long-scroll drag when a student wants the current session, assigned work, or resources
- keep unit switching and section switching available without sending the student back to the top of the page

Contents:

- sticky `Jump to` strip under the course header
- clickable summary chips for units and assignments
- compact unit navigation rail on desktop
- horizontal unit strip on mobile

### 4. Session Journey

Purpose:

- show the sequence of student-facing class sessions inside the selected unit
- bring the current or selected lesson path above broader curriculum background text

Contents:

- session title
- session date
- learning goal
- student-facing activity steps only
- session resources
- session-linked assigned work

### 5. This Unit

Purpose:

- show the big picture for what the student is learning
- preserve curriculum context without forcing the student to scroll through it before reaching lessons

Contents:

- unit title
- overview
- essential understanding
- simplified learning goals drawn from `content`, `skills`, and `concepts`
- optional standards drawer labeled as learning goals or curriculum goals

### 6. Everything Else In This Course

Purpose:

- allow controlled navigation without turning the page into a data dump

Contents:

- unit navigation rail
- additional shared resources
- completed or older assigned work

## Student Read Model Shape

Status: Implemented baseline
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

The student surface keeps one bounded bootstrap through `get_student_learning_space`.

The current response includes derived student-facing sections:

- `focus`
- `next_actions`
- `selected_context`
- `unit_navigation`
- `selected_unit`
- `selected_session`

Current additions:

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
4. `selected_context` is the canonical default open state for the student page and should come from the shared current-curriculum resolver rather than a client-side first-unit guess.

## Student Visibility Rules

Status: Implemented
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

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

Status: Implemented direction
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

Rules:

1. Guardian home stays family-first.
2. Curriculum appears as a learning brief, not as a child-course admin console.
3. Guardians see big themes, major experiences, and support-at-home context.
4. Guardians do not see draft curriculum truth, daily teaching mechanics, or staff-only reflections.
5. Guardian curriculum visibility must be separately filtered server-side and must not reuse the student LMS payload wholesale.
6. The guardian-facing current unit or theme should still come from the same server-owned current-curriculum resolver before the guardian-safe summary shaping is applied.

## Guardian Home Learning Highlights

Status: Implemented
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`

Implemented family-home zone:

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

## Guardian Child Learning Brief

Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

The child drill-down now exposes a curriculum-aware section called:

- `Learning Now`

This section is grouped by course and shows:

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

## Guardian Endpoints

Status: Implemented
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_guardian_home.py`

Two bounded contracts are now live:

### 1. `get_guardian_home_snapshot`

Includes:

- `zones.learning_highlights`

This keeps family home on one bounded bootstrap.

### 2. `get_guardian_student_learning_brief(student_id)`

Purpose:

- provide a deeper curriculum-aware child briefing without forcing guardian home to carry every course detail for every child

Current response shape:

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

Status: Implemented
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

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

Status: Active
Code refs: `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/guardian_home.py`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_guardian_home.py`

Resolution order should remain:

1. class-owned teaching context
2. shared unit/course-plan fallback
3. explicit unavailable or awaiting-publication state

Current-unit precedence inside that hierarchy should remain:

1. live session truth
2. exactly one class unit marked `In Progress`
3. calendar-backed unit timing from duration plus school calendar
4. exact-date or nearest session fallback
5. explicit blocked state when no deterministic current unit exists

But the visible shaping must differ by audience:

- student = operational learning context
- guardian = summarized awareness context

## Remaining Polish Sequence

Status: Active
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts`

Recommended order:

1. Keep extending the student course workspace without reintroducing planning-heavy language or a second task page.
2. Keep tuning the resource stream only from observed student navigation friction; do not add extra buckets or labels unless they reduce clicks.
3. Refine the bounded student read model only when the UI needs additional server-derived guidance.
4. Improve guardian summaries and support prompts without turning guardian pages into a second LMS.
5. Preserve permission and sibling-isolation rules for every guardian-facing curriculum field.

## Optional Future Authoring

Status: Active
Code refs: `ifitwala_ed/curriculum/doctype/unit_plan/unit_plan.json`, `ifitwala_ed/curriculum/doctype/class_session/class_session.json`
Test refs: None yet

Do not add new teacher authoring burden in the first implementation unless derived summaries prove inadequate.

If a second phase is needed later, the preferred additions would be:

- one optional family-facing discussion prompt at `Unit Plan`
- one optional home-support note at `Class Session`

These should stay optional and must not block teacher workflow.

## Non-Goals

Status: Active
Code refs: `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: None yet

This note does not recommend:

- a second student LMS tree
- exposing staff planning semantics to students or guardians
- guardian access to daily lesson-plan internals
- student or guardian client waterfalls
- required extra teacher authoring fields before proving the need

## Related Docs

Status: Active
Code refs: None
Test refs: None yet

- `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
- `ifitwala_ed/docs/curriculum/04_curriculum_lms_and_quiz_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

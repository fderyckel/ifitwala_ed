# Product UI-UX Friction Reduction Roadmap

**Date:** 2026-04-03
**Status:** Planned proposal, non-authoritative audit note
**Scope:** Staff, admin, and student SPA experience in `ifitwala_ed/ui-spa/`
**Primary objective:** Reduce routine workflow friction and make each persona's next action obvious without adding new navigation burden.

## Rating Model

Each roadmap item is scored on a **1-5 UX Impact Score** using this weighted model:

- **Frequency (35%)**: How often the target users hit this flow in real work or learning.
- **Friction Removed (35%)**: How much click count, context switching, re-entry, or dead-end recovery the change removes.
- **Decision Clarity (20%)**: How much easier it becomes to understand status, next action, and why something is blocked.
- **Experience Elevation (10%)**: Visual/interaction quality, mobile comfort, accessibility, and perceived polish.

**Score interpretation**

- **5.0-4.5** = Critical UX leverage, should be scheduled first.
- **4.4-3.8** = Strong UX leverage, worth sequencing in the next product cycle.
- **3.7-3.0** = Useful but narrower improvement.
- **Below 3.0** = Defer unless bundled with higher-impact work.

## Bottom Line

The highest-leverage product work is to redesign the SPA around **task-first flows by persona** rather than record-first editing.
For educators, that means a tighter "what do I need to teach/assign/review today?" cockpit.
For admins, that means exception queues and bulk action surfaces.
For students, that means one-tap continuation into the next learning action with clearer progress and due-state.

## Ranked Roadmap

| Rank | Persona | Roadmap Item | Target Surfaces | Frequency | Friction Removed | Decision Clarity | Experience Elevation | UX Impact Score |
|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | Educators | Convert Staff Home into a true "today cockpit" with next class, pending grading, attendance exceptions, and one-click lesson/assignment handoff. | `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue` | 5 | 5 | 5 | 4 | **4.9** |
| 2 | Students | Make Course Detail action-first: "Continue lesson", "Resume quiz", "Submit next task", and "View feedback", with visible progress and due-state. | `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue` | 5 | 5 | 5 | 4 | **4.9** |
| 3 | Admins | Build exception-first queues with bulk resolve, inline blockers, and explainable states for admissions, attendance, enrollment, and policy signatures. | `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue` | 5 | 5 | 5 | 3 | **4.8** |
| 4 | Educators | Add autosave draft states, visible unsaved-change indicators, and conflict recovery prompts across class planning, course planning, and gradebook editing. | `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue` | 5 | 5 | 4 | 3 | **4.6** |
| 5 | Students | Unify assignment cards into one consistent action model with submission status, quiz attempts, feedback availability, and lock/due messaging. | `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentActivities.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue` | 5 | 4 | 5 | 4 | **4.5** |
| 6 | Educators | Reduce overlay depth in planning and assignment flows by replacing stacked modals with anchored side panels and inline task drawers. | `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue` | 4 | 5 | 4 | 4 | **4.4** |
| 7 | Admins | Add global search + quick open with role-aware result grouping so staff can jump to student, class, plan, task, or applicant records without sidebar hunting. | `ifitwala_ed/ui-spa/src/apps/portal`, `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue` | 4 | 5 | 4 | 3 | **4.3** |
| 8 | Students | Upgrade mobile-first reading and task interaction for course content, quiz review, and feedback, including sticky primary actions and thumb-safe layouts. | `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue` | 4 | 4 | 4 | 5 | **4.1** |
| 9 | Admins | Add inline "why blocked / what to fix next" guidance to failed or incomplete admin actions instead of generic toasts and silent disabled states. | `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/*`, `ifitwala_ed/ui-spa/src/components/*` | 4 | 4 | 5 | 3 | **4.1** |
| 10 | Educators | Improve lesson and unit authoring ergonomics: reusable snippets, duplicate-from-previous, drag ordering, and richer preview before publish/assign. | `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue` | 4 | 4 | 4 | 4 | **4.0** |
| 11 | Students | Add "My week" planning view that merges upcoming sessions, due tasks, quiz windows, and feedback release dates into one timeline. | `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentActivities.vue` | 4 | 4 | 5 | 3 | **4.0** |
| 12 | Admins | Replace dense analytics pages with progressive disclosure: KPI summary, exception drill-down, and saved filters/views. | `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceAnalytics.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue` | 3 | 4 | 4 | 4 | **3.7** |

## Educators

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/ProfessionalDevelopment.test.ts`

### 1) Staff Home As A Daily Teaching Cockpit

**Impact score:** 4.9
**Problem:** Staff Home is the natural entry point, but if it does not answer "what do I need to do next?" educators still bounce between pages and remember state manually.
**Proposal:** Make Staff Home action-first: next class session, attendance not taken, grading awaiting attention, drafts needing publish, course-plan edits pending, and direct links to the exact unit/session/task surface.
**UX acceptance bar:** An instructor can start the day, identify top 3 actions, and open the exact working surface in one click without scanning multiple menus.

### 2) Autosave + Unsaved-State Visibility + Conflict Recovery

**Impact score:** 4.6
**Problem:** Long-form planning and grade entry are high-loss workflows when save boundaries are unclear or another editor has changed the record.
**Proposal:** Add visible save state, background autosave for drafts where server invariants allow it, and inline "newer version exists" recovery prompts that preserve the user's unsaved text for copy/merge.
**UX acceptance bar:** Users never wonder whether their work is saved, and stale-write conflicts produce a guided recovery path instead of a surprise failure at the end.

### 3) Reduce Modal Stacking In Planning And Assignment

**Impact score:** 4.4
**Problem:** Stacked overlays create spatial confusion, weak back-navigation, and higher error risk in multi-step planning.
**Proposal:** Move high-frequency secondary actions into anchored side panels/drawers tied to the current row/card, while keeping one primary task in view.
**UX acceptance bar:** A teacher can edit a unit, inspect linked resources, and create an assignment without losing the mental map of where they are.

### 4) Faster Unit/Lesson Authoring

**Impact score:** 4.0
**Problem:** Repetitive unit and lesson setup still forces manual re-entry of patterns educators already used before.
**Proposal:** Add duplicate-from-previous, reusable lesson/activity snippets, drag ordering with clearer drop states, and a publish preview that shows exactly what students/classes inherit.
**UX acceptance bar:** Creating a new reusable lesson outline feels closer to editing a template than filling a blank form.

## Admins

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/EnrollmentAnalytics.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/AcademicLoad.test.ts`

### 1) Exception-First Queues And Bulk Resolution

**Impact score:** 4.8
**Problem:** Admin work is usually about resolving outliers, blockers, and pending decisions. Record-by-record navigation wastes time and obscures what matters first.
**Proposal:** Build queue-style views grouped by exception type, with bulk approve/reject/assign actions, inline row expansion, and persistent filters for school/program/year scope.
**UX acceptance bar:** An admin can process a batch of pending items without opening each record in a separate context unless they choose to.

### 2) Global Quick Search With Role-Aware Results

**Impact score:** 4.3
**Problem:** Staff often know the student/applicant/class/task they need but still have to navigate through page trees.
**Proposal:** Add a command-palette or global quick-search entry with scoped result groups and deep links to exact student, class, applicant, course-plan, and task contexts.
**UX acceptance bar:** If a staff user knows a name or ID, they can reach the right screen in under 5 seconds.

### 3) Inline Blocker Explanation

**Impact score:** 4.1
**Problem:** Disabled buttons and generic toasts force users to infer whether the issue is permission, missing prerequisite data, or workflow state.
**Proposal:** Standardize row-level blocker messaging with "why blocked" and "next fix" copy, especially in admissions/enrollment and policy-signature flows.
**UX acceptance bar:** Every blocked action explains the exact missing condition and the fastest next step.

### 4) Progressive Disclosure For Analytics

**Impact score:** 3.7
**Problem:** Dense analytics screens can overload staff who only need one answer first, then detail second.
**Proposal:** Shift each analytics page to a KPI strip + exception list + drill-down layout, with saved views for recurring operational reviews.
**UX acceptance bar:** A user can understand "is this okay, where is the problem, what do I inspect next?" without reading the entire page.

## Students

Status: Planned proposal
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentActivities.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentLogs.test.ts`

### 1) Course Detail As A Next-Action Surface

**Impact score:** 4.9
**Problem:** Students should not have to infer whether to continue a lesson, resume a quiz, submit work, or review feedback.
**Proposal:** Add a primary "Continue" action, a clearly ranked "Next up" list, progress indicators per unit/session, and due/lock messaging tied directly to the relevant action card.
**UX acceptance bar:** A student landing on a course can immediately answer "what should I do now?" and act without scrolling through unrelated content.

### 2) Unified Assignment/Quiz Card Model

**Impact score:** 4.5
**Problem:** Different task types can look and behave inconsistently, especially around attempt state, submission state, feedback readiness, and deadlines.
**Proposal:** Standardize one card model with state badges, next action, deadline/lock timer copy, feedback availability, and retry/resume semantics for quizzes.
**UX acceptance bar:** Students learn one interaction model and can predict what each card will do before clicking.

### 3) Mobile-First Learning Interaction

**Impact score:** 4.1
**Problem:** Student usage is often mobile-heavy, and long content, quiz review, or feedback reading can feel awkward when primary actions move out of reach.
**Proposal:** Introduce sticky primary actions, thumb-safe spacing, clearer section anchors, and better small-screen treatment for rich text, question options, and feedback blocks.
**UX acceptance bar:** Course learning, quiz attempts, and feedback review remain comfortable on a phone without layout collapse or hidden actions.

### 4) "My Week" Timeline

**Impact score:** 4.0
**Problem:** Students often need a cross-course mental model of what is due, what is happening in class, and where feedback has arrived.
**Proposal:** Add a weekly timeline that merges upcoming sessions, assignments, quiz windows, and feedback releases, then deep-links into each exact course/task context.
**UX acceptance bar:** Students can plan the week from one place and jump into the correct task without reconstructing deadlines from multiple screens.

## Sequencing Recommendation

Status: Planned proposal
Code refs: Same SPA surfaces listed above
Test refs: Existing page-level tests listed above; new interaction tests should be added per implemented slice

1. Ship the **educator Staff Home cockpit** and **student Course Detail next-action redesign** first. These two surfaces likely touch the highest-frequency daily interactions.
2. In parallel, define the **shared assignment/task card state model** so educator and student surfaces converge on one visual/status language.
3. Then build **admin exception queues + bulk actions** for admissions, attendance, and enrollment bottlenecks.
4. After the flow model stabilizes, add **autosave/unsaved-state UX** and **reduced overlay depth** to long-form planning/editing.
5. Finally, raise polish through **mobile-first refinements**, **global quick search**, and **progressive-disclosure analytics**.

## Open Product Questions

- Should the first educator cockpit optimize for **daily teaching execution** or **planning/grading recovery**, if one must win the top hero area?
- For students, should the primary "Continue" action prioritize **next scheduled lesson** or **nearest due assignment**, when those conflict?
- For admins, which queue has the biggest real operational pain today: **admissions decisions**, **attendance exceptions**, **enrollment cleanup**, or **policy-signature follow-up**?

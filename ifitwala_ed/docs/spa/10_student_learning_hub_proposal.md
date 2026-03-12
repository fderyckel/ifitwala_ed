# Student Hub Learning Proposal (`/hub/student`)

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPortfolioFeed.vue`, `ifitwala_ed/ui-spa/src/components/portfolio/PortfolioFeedSurface.vue`, `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`, `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`, `ifitwala_ed/api/course_schedule.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/student_portfolio.py`, `ifitwala_ed/api/student_log.py`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/student/portfolio_journal_architecture.md`, `ifitwala_ed/docs/docs_md/learning-unit.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/task.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`
Test refs: None

This proposal defines how the Student Hub at `/hub/student` should surface `Learning Unit`, `Lesson`, `Lesson Activity`, `Task`, and `Task Delivery` in one coherent student experience.

It is intentionally a proposal, not a locked contract. No canonical runtime behavior is changed by this document.

Implementation sequencing for this proposal lives in `ifitwala_ed/docs/spa/11_student_learning_hub_implementation_plan.md`.

## Goal and Product Thesis

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPortfolioFeed.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`
Test refs: None

The current Student Hub already has the right shell shape:

- `/student` for the home/dashboard
- `/student/courses` for course discovery
- `/student/courses/:course_id` for course detail

What is still missing is the full interactive learning surface.

The proposal is to make `/hub/student` a dual-surface product:

1. **Today cockpit**
   A calm planning surface that answers: "What should I do now, next, and later?"
2. **My Courses**
   A structured learning view that answers: "What am I learning, where am I in the unit, and what activity comes next?"

The key product decision is:

> Do not choose timeline *or* LMS structure. Keep both.

Students need a time-based surface for urgency, a curriculum-based surface for meaning, and a reflection loop that turns finished work into learning evidence rather than a pure compliance checklist.

## Research Anchors

Status: Proposed
Code refs: None
Test refs: None

The UX direction below is anchored to current research and official guidance, not generic ed-tech fashion.

- [Pew Research Center 2024](https://www.pewresearch.org/internet/2024/12/12/teens-social-media-and-technology-2024/) reports that 45% of U.S. teens say they are online "almost constantly". The Hub therefore has to work in a high-interruption environment and cannot rely on long, self-directed attention by default.
- [AAP Family Media Plan (updated March 19, 2024)](https://www.aap.org/en/patient-care/media-and-children/family-media-plan/) emphasizes intentional media routines, sleep protection, and adult-guided boundaries. For children and younger teens, the Hub should scaffold pace and stopping points rather than maximize feed depth.
- A [2025 rapid systematic review on excessive ICT exposure and executive functions in children and adolescents](https://pubmed.ncbi.nlm.nih.gov/40329673/) found consistent negative associations with inhibitory control, working memory, and cognitive flexibility. Interface implication: reduce competing stimuli, hard-to-predict feed jumps, and multitasking pressure.
- A [2024 Scientific Reports study on cognitive load and multimedia learning](https://pubmed.ncbi.nlm.nih.gov/39553810/) found that higher cognitive load reduced attention and that Mayer-style multimedia design matters. Interface implication: one main action, clean hierarchy, short chunks, and no dense mixed-media walls.
- A [2024 PNAS study on online learning](https://pubmed.ncbi.nlm.nih.gov/39526882/) found better performance and synchronization in instructor-present conditions. Interface implication: keep teacher presence visible through "why this matters", success criteria, class context, and timely feedback rather than making learning feel like isolated content consumption.
- A [2025 Communications Psychology study on interpolated retrieval](https://pubmed.ncbi.nlm.nih.gov/40702608/) found that short retrieval opportunities improved online learning. Product implication: lessons should alternate content with checks for understanding, not just stack passive reading and video.
- A [2024 BMC Medical Education study on self-directed online learning readiness](https://pubmed.ncbi.nlm.nih.gov/38781571/) found student-student interaction, teacher-student interaction, concentration, and planning to be key drivers. Interface implication: students need visible progress, concentration-friendly sequencing, and explicit next-step planning cues.
- A [2024 Journal of Experimental Psychology: Applied study](https://pubmed.ncbi.nlm.nih.gov/39023988/) found that reminder-setting predicted greater fulfillment of real-world intentions. Product implication: the Hub should help students externalize intended work instead of expecting them to remember everything internally.
- A [2018 Child Development study](https://pubmed.ncbi.nlm.nih.gov/29446452/) found that younger children recognized memory difficulty, but only older children consistently translated that into strategic reminder-setting. Product implication: younger students need stronger default scaffolding; the board should not assume mature self-management.
- A [2022 Frontiers in Psychology study](https://pubmed.ncbi.nlm.nih.gov/36353090/) found that students showed bias in estimating how long academic tasks would take. A [2025 PLOS One study](https://pubmed.ncbi.nlm.nih.gov/40966275/) found that students overestimated time-on-task 78% of the time in multi-day programming assignments. Product implication: let students estimate work, but use coarse time buckets and treat estimates as planning aids rather than truth.
- The [OECD report Children in the Digital Environment (January 22, 2025)](https://www.oecd.org/en/publications/children-in-the-digital-environment_ef594a3b-en.html) argues for a whole-of-society approach to digital well-being. Product implication: the Hub should be safe-by-default, predictable, and transparent in how work appears and when it is due.
- A [2024 systematic review and meta-analysis on gamification](https://pubmed.ncbi.nlm.nih.gov/39303410/) and a [2023 systematic review across high school and higher education](https://pubmed.ncbi.nlm.nih.gov/37636393/) suggest that gamification can improve motivation, but novelty effects and extrinsic rewards can fade. Product implication: use light completion feedback and progress cues, not heavy points-and-badges economics.

Inference from the sources above:

- **Children** need stronger scaffolding, fewer choices at once, and visible stop/start cues.
- **Teenagers** benefit from autonomy, but still need guardrails around task planning, attention fragmentation, and progress visibility.
- **Young adults** can handle more flexible pathways, but still perform better when lessons are chunked, retrieval-rich, and easy to resume.

## Product Proposal

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/api/course_schedule.py`, `ifitwala_ed/api/courses.py`
Test refs: None

### 1. Student Home becomes "Today"

Keep the current `student-home` route, but make it the student's daily learning cockpit.

Above the fold, show only:

- **Next live class or current class**
- **My Work Board**
- **Next learning step**

The board should sit directly under the top orientation strip and above the longer dated feed.

This should be a compact kanban-style planning layer, not a full Trello-style workspace.

Recommended board lanes:

- `Now`
- `Soon`
- `Later`
- `Done`

Why these lanes:

- `Now` limits the active set and protects attention.
- `Soon` keeps near-future work visible without creating panic.
- `Later` preserves foresight without crowding the present.
- `Done` gives closure and light gamification, but should stay collapsed by default.

This lane design is an inference from the research above on cognitive load, self-regulated learning, reminder use, and time estimation.

Below that, show a dated timeline with four sections:

- `Now`
- `Today`
- `This Week`
- `Later`

Each timeline item should be one of these types:

- scheduled class / lesson session
- continue lesson
- due task
- feedback returned
- reading checkpoint
- quiz checkpoint
- resource posted

The timeline is not the LMS itself. It is the student's attention router.

### 2. My Work Board card design

Each board card should show:

- task title
- course
- due signal
- one clear next action
- optional quick time estimate
- optional project/milestone expansion

Estimated time should use quick buckets, not open text:

- `10m`
- `20m`
- `30m`
- `45m`
- `60m`
- `90m+`

The estimate should be requested when a task moves into `Now`, not for every item in the system.

Large tasks and projects should support scaffolded breakdown:

- one canonical top-level teacher task
- optional teacher-defined milestones when the workflow requires them
- optional student planning subtasks for personal execution

Critical contract rule:

> Student planning subtasks and personal board moves must not overwrite the canonical task workflow.

That means:

- moving a card to `Done` can mean "my plan for this is complete"
- it must not mark the official `Task Delivery` as submitted, graded, or complete unless server-owned task rules are actually satisfied

### 3. Board ownership: system-curated backlog, student-managed commitment

The board should distinguish between:

- **system-curated backlog**
  `Soon` and `Later`
- **student-managed commitment**
  `Now`

Recommendation:

- `Soon` and `Later` should be server-curated from canonical `Task Delivery.available_from`, `due_date`, and course context.
- Students should not manually triage the entire backlog across all future lanes.
- Students should mainly control:
  - what enters `Now`
  - quick time estimates
  - personal planning subtasks
  - whether a personally planned item moves to `Done`

This reduces executive-function tax and avoids creating a fragile parallel workflow state.

### 4. My Courses remains "My Courses"

Keep the current `/student/courses` route, current sidebar label, and current course-card discovery pattern, but make the page explicitly the gateway to structured learning.

The course-space language should stay `My Courses`, not `My Learning`.

### 5. Course Detail becomes the real LMS surface

The student `CourseDetail.vue` surface should be the main learning space for a course.

Current implementation direction:

- keep the course header as the top orientation band
- add a persistent course map for ordered `Learning Unit` and `Lesson` navigation
- keep one active unit and one active lesson in focus at a time
- render ordered `Lesson Activity` blocks plus linked unit and lesson work inside that lesson flow
- keep success-criteria style framing and durable resume actions for the later progress/focus phase, because the current lesson schema does not yet expose a richer progress contract

### 6. Activity blocks should behave like interactive textbook pages

The activity model should feel closer to Kognity than to a file dump.

Each `Lesson Activity` block should support a predictable pattern:

- one primary content mode at a time
- short estimated time
- clear completion state
- optional retrieval check before continuing
- explicit teacher framing when the activity matters for a task or assessment

The product should not treat every activity like a separate app. It should feel like a continuous lesson with meaningful pauses.

Important implementation note:

- These low-stakes retrieval checks should not run through the formal `Task Delivery` lifecycle by default.
- They need a lighter checkpoint model so the system can give immediate reinforcement without polluting `Task Outcome`, `Task Submission`, and gradebook truth.

### 7. Reflection and portfolio should close the learning loop

The Hub should not leave reflection trapped in the separate portfolio route only.

The stronger rule should be:

- every substantial lesson or meaningful task can surface one lightweight reflection action in-context
- reflection capture should write into the existing `student_reflection_entry` model
- portfolio capture should be fed from real course and task completion, not only from a separate navigation destination

Practical proposal:

- after a meaningful activity or task completion, offer a light prompt such as:
  - `What did you understand?`
  - `What was hard?`
  - `What should you remember next time?`
  - `Do you want to save this to your portfolio?`
- if a completed task already has a real `Task Submission`, the Hub can offer a portfolio-promotion step from the board or lesson view
- if the student is completing a lesson block without a formal submission, the Hub can still capture a reflection anchored to lesson, lesson activity, or lesson instance context

This uses the existing reflection and portfolio architecture to reinforce metacognition inside the lesson loop rather than treating reflection as paperwork after learning.

### 8. Focus mode should protect execution, not replace course context

The default click from `Now` should preserve pedagogical context and then reduce distraction for execution.

Recommended rule:

- resolve the student into the relevant `My Courses` learning surface first
- anchor the experience to the specific lesson, lesson activity, or task context when that context can be resolved
- then open a focused execution surface for the active step

The execution surface should be a full-screen overlay or stripped shell with:

- the active lesson activity or task only
- a minimal breadcrumb back to course and lesson context
- short progress context
- a deliberate exit back to the full course page
- no competing timeline, board, or portal navigation chrome while the student is working

This accommodates task-switching concerns without divorcing execution from the learning schema.

### 9. Student Log should not be surfaced in Today under the current contract

The current `Student Log` contract is not safe enough for Home-surface injection.

Why:

- the current student portal contract exposes logs by `visible_to_student`, not by a positive/supportive learning-readiness classification
- `Student Log Type` does not currently carry a portal-safe polarity or intent field
- the student home surface should not risk letting a behavior or concern note hijack learning readiness at the point of task initiation

Recommendation:

- keep `Student Log` as its own dedicated route for now
- do not inject generic student log rows into the `Today` timeline or `My Work Board`
- if the product later wants supportive cues on Home, add an explicit portal-safe classification first, then design a narrow support-card contract from that classification

### 10. Task is not the lesson, but must be visible inside the lesson

From the current contract:

- `Task` is reusable learning work.
- `Task Delivery` is the dated runtime event.
- `Lesson Instance` is taught context.

The student should therefore see tasks in two places:

- on the **Today timeline** when they are due, newly assigned, or feedback has returned
- on the **My Work Board** when the student is planning or focusing execution
- inside the **lesson/course view** when the task belongs to the current unit or lesson context

That keeps the system from collapsing curriculum into deadlines.

## Timeline and Learning-Space Rules

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/student/portfolio_journal_architecture.md`, `ifitwala_ed/api/student_log.py`, `ifitwala_ed/docs/docs_md/task.md`, `ifitwala_ed/docs/docs_md/task-delivery.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`
Test refs: None

### Home board rules

- The board is a planning layer over canonical `Task Delivery` records and any future student planning records.
- Keep `Now` intentionally small. Default target: no more than 3 cards.
- `Soon` and `Later` should be system-curated by default.
- Student agency on the board should center on selecting or continuing `Now`, not on manually triaging the full backlog every day.
- `Done` should reward closure, but remain visually quiet so old completions do not displace current work.
- The board should support dragging or explicit move actions, but every move must produce clear visible feedback.
- Board state should help with focus and sequencing, not become a second grading system.

### Deep-link and focus rules

- Default `Now` execution should deep-link into course/lesson/activity context, not into a context-free standalone modal.
- If the Hub cannot resolve exact activity context, it should fall back to the course learning surface, not an orphaned task shell.
- Focus mode should launch from resolved course context and hide chrome for the active execution step while preserving a clear return path to the full course page.

### Timeline rules

- Use `Task Delivery.available_from`, `due_date`, and `lock_date` as the dated task spine.
- Use today's scheduled classes from the existing schedule APIs as the dated lesson spine.
- Show only a small number of high-priority items by default. Overflow belongs behind "See all this week", not on the first screen.
- Do not use infinite scroll as the main learning model. It increases ambiguity and attention drift.
- Completed items should collapse visually instead of competing with the next required action.
- The timeline should complement the board, not duplicate it. Timeline answers chronology; board answers planning.
- Do not inject generic `Student Log` rows into Today under the current contract.
- If supportive student-facing cues are ever added here, they need an explicit portal-safe classification beyond `visible_to_student`.

### Learning-space rules

- `Learning Unit` should be the main progress chapter.
- `Lesson` should be the main sequence row inside a unit.
- `Lesson Activity` should be the main content block inside a lesson.
- `Task` should appear as an embedded requirement or evidence point, not as the only object the student sees.
- `Lesson Instance` should add "what happened in class" context when present, but the course page must still work without it.
- Reflection prompts should live inside this surface as part of the lesson loop, not as a separate afterthought route.
- Portfolio promotion should happen from this surface when the evidence and context are real.
- Low-stakes retrieval checks should use a lightweight checkpoint contract, not the heavy `Task Delivery` launch/outcome pipeline.

### Cognitive-design rules

- Each page should expose one dominant action.
- The home page should expose one dominant planning action: choose or continue a `Now` task.
- Each lesson should display estimated duration for the whole lesson and for each activity.
- Each activity should be resumable from the exact last block the student touched.
- Reading and video should be followed by short checks, not long end-of-unit tests only.
- Notifications should be batched into the timeline rather than interrupting students with scattered urgency.
- Light gamification should focus on closure, momentum, and progress, not points economies, streak pressure, or leaderboards.

## Rollout Shape

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/api/course_schedule.py`
Test refs: None

### Phase 1: Structured read-only learning space + lightweight work board

Ship without inventing new completion state first.

- Use current course access and schedule context.
- Surface ordered units, lessons, and lesson activities as read-only curriculum.
- Surface linked tasks in-context and on the timeline.
- Add a compact home `My Work Board` using only canonical task data plus minimal student-side planning state.
- Use system-curated `Soon` and `Later` lanes; let students mainly choose `Now`.

### Phase 2: Lesson progress and resume state

- Add durable progress state for lesson and activity continuation.
- Add "continue where you left off" on home and course pages.
- Add lightweight completion affordances for non-assessed activity blocks.
- Add student-side planning subtasks for large projects without altering canonical task workflow.
- Add reflection capture and portfolio-promotion prompts using the existing portfolio services.
- Add a route-anchored focus mode for high-concentration execution with an explicit return path to the full course page.

### Phase 3: Interactive lesson experiences

- Add embedded reading, reading checks, video checkpoints, and quick quizzes.
- Add lightweight checkpoint state for retrieval checks separate from `Task Delivery`.
- Allow lessons to mix teacher-authored native blocks with imported content packages.

### Phase 4: Import compatibility

- Add cmi5-first launch/import capability.
- Add SCORM compatibility as a fallback compatibility tier where needed.

## Interoperability Direction: cmi5 First, SCORM Compatible

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/docs_md/learning-unit.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-activity.md`
Test refs: None

The internal Ifitwala_ed model should remain canonical:

- `Learning Unit`
- `Lesson`
- `Lesson Activity`
- `Task`
- `Task Delivery`

Imported package standards should adapt into this model, not replace it.

### Why cmi5 should be first

- The [current cmi5 specification](https://aicc.github.io/CMI-5_Spec_Current/) is built for LMS-launched assignable units, registration continuity, and LRS-backed xAPI tracking.
- cmi5 is better aligned than classic SCORM with modern activity tracking, attempt history, and mixed learning experiences.
- cmi5 fits the product direction where a lesson can include native activities plus external launchable learning objects.

### Why SCORM still matters

- The [SCORM 2004 4th Edition testing requirements](https://adlnet.gov/resources/scorm-2004-4th-edition-testing-requirements/) still matter for compatibility with legacy publisher content and existing school content investments.
- Schools that migrate into Ifitwala_ed will often bring SCORM packages before they bring cmi5 packages.

### Recommended interoperability stance

1. Treat imported packages as **content providers**, not as the system of record for student learning design.
2. Keep unit/lesson/activity ordering and teacher-facing curriculum structure native to Ifitwala_ed.
3. Let imported packages attach at the lesson-activity layer after explicit architecture approval.
4. Prefer cmi5 for new interoperability work.
5. Support SCORM launch/import where required, but avoid designing the Student Hub around SCORM-era constraints.

## Rationale

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: None

### Pros

- Keeps urgency and meaning separate: timeline for time, course space for learning.
- Adds a planning layer without collapsing the curriculum model into a deadline feed.
- Integrates reflection and portfolio into the actual learning loop rather than leaving them as a separate silo.
- Protects focus with a real execution surface without throwing away pedagogical context.
- Uses the existing Ifitwala_ed curriculum model instead of flattening everything into tasks.
- Fits both teacher-assigned work and interactive textbook-style content.
- Scales toward native lessons first and cmi5/SCORM imports later.
- Matches research on chunking, retrieval, visible progress, and reduced attention fragmentation.

### Cons

- This is a materially larger surface than a pure task stream.
- A board introduces another state layer that has to be carefully separated from official task status.
- Focus mode adds another execution surface that must stay aligned with route-based learning context.
- It requires stronger content-governance decisions around what students can see before/after class.
- If progress and visibility rules are weak, the experience can become inconsistent across courses.

### Blind spots

- The current live schema does not yet define student-facing progress state for `Lesson` or `Lesson Activity`.
- The current live task contract anchors only to `Learning Unit`, `Lesson`, and optional `Lesson Instance`; it does not yet link directly to `Lesson Activity`.
- The current workspace does not yet define a canonical student planning doctype for personal subtasks, estimates, or board lanes.
- The current `Lesson Activity` schema does not yet declare a dedicated reflection block type.
- The current student log model has no field that distinguishes supportive student-home cues from concern or behavior notes.
- Younger-child flows may need stronger guardian or teacher mediation patterns than this proposal spells out.

### Risks

- A feed-first implementation could silently erase curriculum meaning.
- A board-first implementation could silently replace canonical task workflow with ambiguous personal status.
- A curriculum-first implementation without a timeline could silently erase urgency.
- A focus overlay implemented as a detached execution shell could sever the learning schema rather than protect it.
- Reusing `Task Delivery` for every micro-checkpoint would flood gradebook truth with noise.
- Surfacing generic student logs on Home without a portal-safe classification could harm readiness to learn.
- If imported package players become the primary UX, the Hub will fragment into inconsistent micro-products.

## Contract Matrix

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/api/course_schedule.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`

| Concern | Current state | Proposed direction | Gap to close |
|---|---|---|---|
| SPA routes | `/student`, `/student/courses`, `/student/courses/:course_id` exist and course detail now accepts optional deep-link query anchors for `learning_unit`, `lesson`, and `lesson_instance` | Keep routes stable and upgrade meaning of existing pages | Need more producers of deep-link context from learning entry points |
| Home payload | Student home now uses one aggregated Hub payload for identity, today's classes, and a next-learning-step card | Upgrade to a `Today` cockpit with a top orientation strip, a compact `My Work Board`, and a dated learning timeline | Needs board and dated learning timeline layers |
| Planning board | No student planning board exists | Add a compact kanban-style planning layer with student-managed `Now` and system-curated `Soon/Later/Done` support | Needs a student-side planning state model that does not overwrite canonical task status |
| Course payload | Course detail now has one aggregated payload with course metadata, deep-link resolution, course-map navigation, active unit framing, active lesson flow, and inline linked tasks | Upgrade course detail into the LMS learning surface | Needs progress state and execution affordances |
| Curriculum model | `Learning Unit`, `Lesson`, `Lesson Activity` exist; task stack exists | Surface native curriculum model to students | Needs visibility/progress contract |
| Task model | `Task` and `Task Delivery` exist with dated delivery context | Embed tasks in board, timeline, and lesson context; deep-link `Now` into pedagogical context | Needs student-facing join logic without duplicating workflow |
| Portfolio / reflection | Portfolio and reflection surfaces already exist, but mostly as a separate destination | Pull reflection and portfolio prompts into the learning loop | Needs in-flow integration without pretending the current lesson schema already contains a reflection block type |
| Focus mode | Overlay architecture exists, but no student learning focus mode exists | Add a route-anchored focus execution layer for active work | Needs a focused surface that preserves course/lesson context and a clean return path |
| Student Log on Home | Student Logs surface exists, but log visibility is not the same as portal-safe learning readiness | Keep Student Log off Today for now | Needs an explicit portal-safe supportive classification before any Home surfacing |
| Retrieval checkpoints | Lessons can propose reading checks or quizzes, but Task Delivery is heavy | Use lightweight checkpoint state for micro-retrieval | Needs a separate checkpoint contract outside formal gradebook truth |
| Lesson runtime context | `Lesson Instance` exists but is lightly used | Use when available to show "what happened in class" context | Must remain optional |
| Interoperability | No student-facing cmi5/SCORM layer is present | Build cmi5-first external content compatibility | Needs separate integration architecture and launch/runtime tracking |
| Tests | Backend contract tests exist for Home and course-detail payload logic, SPA service tests exist for canonical method usage, and helper tests now cover lesson selection and adjacency logic | Add contract tests before implementation | Needs component-level route/render tests once node tooling is available in the workspace |

## Technical Notes (IT)

Status: Proposed
Code refs: `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`, `ifitwala_ed/docs/concurrency_01_proposal.md`, `ifitwala_ed/docs/concurrency_02_proposal.md`, `ifitwala_ed/docs/high_concurrency_03.md`
Test refs: None

### Implementation guardrails if this proposal is approved

- Keep internal portal navigation route-name based. Do not introduce hardcoded `/hub/...` links.
- Prefer one aggregated student-learning payload for home and one aggregated payload for course detail. Do not build the student LMS view out of a request waterfall.
- Keep server ownership of visibility, sequencing, and due-state logic. The SPA should render, not infer scope math.
- Preserve the canonical current contract that `Task` is reusable work and `Task Delivery` is runtime execution.
- Treat the `My Work Board` as a planning overlay. Personal estimates, lane moves, and subtasks must not mutate official delivery, submission, grading, or publication state unless a named server workflow explicitly allows it.
- Default execution from `Now` should resolve into course/lesson/activity context first; the focus surface should launch from that resolved context and preserve a clear return path.
- Reflection and portfolio prompts should reuse the existing student portfolio services and evidence governance, not create a second evidence store.
- Do not surface generic `Student Log` rows on Today unless the product first defines a portal-safe supportive classification beyond `visible_to_student`.
- Low-stakes retrieval checks must not default to `Task Delivery` creation.
- If estimated time is implemented, store it as student planning metadata with coarse buckets rather than as a precision promise.
- Do not let SCORM or cmi5 become the canonical authoring model for Ifitwala_ed. They should plug into the learning surface, not define it.

### Research sources used

- [Pew Research Center, Teens, Social Media and Technology 2024](https://www.pewresearch.org/internet/2024/12/12/teens-social-media-and-technology-2024/)
- [American Academy of Pediatrics, Family Media Plan](https://www.aap.org/en/patient-care/media-and-children/family-media-plan/)
- [Rapid systematic review on excessive ICT exposure and executive functions in children and adolescents (2025)](https://pubmed.ncbi.nlm.nih.gov/40329673/)
- [Scientific Reports 2024, cognitive load and multimedia learning](https://pubmed.ncbi.nlm.nih.gov/39553810/)
- [PNAS 2024, instructor-present online learning](https://pubmed.ncbi.nlm.nih.gov/39526882/)
- [Communications Psychology 2025, interpolated retrieval and online learning](https://pubmed.ncbi.nlm.nih.gov/40702608/)
- [BMC Medical Education 2024, self-directed online learning readiness](https://pubmed.ncbi.nlm.nih.gov/38781571/)
- [Journal of Experimental Psychology: Applied 2024, metacognition guides intention offloading and fulfillment of real-world plans](https://pubmed.ncbi.nlm.nih.gov/39023988/)
- [Child Development 2018, development of children's use of external reminders for hard-to-remember intentions](https://pubmed.ncbi.nlm.nih.gov/29446452/)
- [Frontiers in Psychology 2022, self-regulation of time and time estimation accuracy](https://pubmed.ncbi.nlm.nih.gov/36353090/)
- [PLOS One 2025, time-on-task estimation for tasks lasting hours spread over multiple days](https://pubmed.ncbi.nlm.nih.gov/40966275/)
- [Nurse Education Today 2024, effects of gamification on academic motivation and confidence](https://pubmed.ncbi.nlm.nih.gov/39303410/)
- [Heliyon 2023, role of gamified learning strategies in student motivation](https://pubmed.ncbi.nlm.nih.gov/37636393/)
- [OECD 2025, Children in the Digital Environment](https://www.oecd.org/en/publications/children-in-the-digital-environment_ef594a3b-en.html)
- [cmi5 current specification](https://aicc.github.io/CMI-5_Spec_Current/)
- [SCORM 2004 4th Edition testing requirements](https://adlnet.gov/resources/scorm-2004-4th-edition-testing-requirements/)

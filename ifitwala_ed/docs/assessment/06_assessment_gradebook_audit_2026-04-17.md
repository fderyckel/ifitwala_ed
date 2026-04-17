# Assessment & Gradebook Audit

Status: Audit / point-in-time review / non-canonical
Date: 2026-04-17
Audience: Product, Engineering, and reviewers
Scope: `Task`, `Task Delivery`, `Task Outcome`, `Task Submission`, `Task Contribution`, staff gradebook, task setup, and the notes under `ifitwala_ed/docs/assessment/`

Important note:
- This file is an audit report.
- It does not replace the canonical runtime contracts in:
  - `ifitwala_ed/docs/assessment/01_assessment_notes.md`
  - `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
  - `ifitwala_ed/docs/assessment/04_task_notes.md`
  - `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`

## Bottom Line

The core assessment data model is stronger than the current teacher UX.
`Task -> Task Delivery -> Task Outcome -> Task Submission -> Task Contribution` is a solid foundation, and governed submission evidence is already more mature than many LMS implementations.
The drawer-first baseline is now live, including evidence review, attachment preview/open actions, comments, compare context, and release actions.
What is still missing is the product refinement that turns that baseline into a premium day-to-day workflow: cleaner release semantics, mode-consistent auditability, first-class criteria setup and scoring, collect-work evidence inbox patterns, and richer moderation/teacher-speed flows.

## Audit Basis

Docs reviewed:
- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`
- `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`
- `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`
- `ifitwala_ed/docs/docs_md/task-delivery.md`
- `ifitwala_ed/docs/docs_md/task-outcome.md`
- `ifitwala_ed/docs/docs_md/task-submission.md`
- `ifitwala_ed/docs/docs_md/task-contribution.md`
- `ifitwala_ed/docs/docs_md/task-assessment-criteria.md`

Code reviewed:
- `ifitwala_ed/assessment/doctype/task/task.py`
- `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.py`
- `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`
- `ifitwala_ed/assessment/doctype/task_submission/task_submission.py`
- `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.py`
- `ifitwala_ed/assessment/task_creation_service.py`
- `ifitwala_ed/assessment/task_delivery_service.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/assessment/task_contribution_service.py`
- `ifitwala_ed/assessment/task_outcome_service.py`
- `ifitwala_ed/api/gradebook.py`
- `ifitwala_ed/api/gradebook_reads.py`
- `ifitwala_ed/api/gradebook_writes.py`
- `ifitwala_ed/api/gradebook_support.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/api/task.py`
- `ifitwala_ed/api/outcome_publish.py`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookOverviewView.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookQuizManualReview.vue`
- `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

Tests reviewed:
- `ifitwala_ed/api/test_gradebook.py`
- `ifitwala_ed/api/test_task_submission.py`
- `ifitwala_ed/assessment/test_task_outcome_service.py`
- `ifitwala_ed/assessment/test_task_submission_service.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`
- `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`

Market reference points reviewed, official sources only:
- Canvas SpeedGrader and Learning Mastery Gradebook: [SpeedGrader](https://community.instructure.com/en/kb/articles/661157-how-do-i-use-speedgrader), [Learning Mastery Gradebook](https://community.instructure.com/en/kb/articles/660932-unknown)
- Blackboard Ultra Gradebook and rubrics: [Ultra Gradebook](https://help.anthology.com/blackboard/instructor/en/grading/gradebook.html), [Grade with Rubrics](https://help.blackboard.com/Learn/Instructor/Ultra/Grade/Rubrics/Grade_with_Rubrics)
- Blackboard delegated/parallel grading: [Delegated Grading / Parallel Grading navigation](https://help.anthology.com/blackboard/instructor/en/original-course-view.html)
- Moodle advanced grading: [Rubrics](https://docs.moodle.org/37/en/Rubrics), [Marking guide](https://docs.moodle.org/501/en/Marking_guide), [Advanced grading methods](https://docs.moodle.org/501/en/Advanced_grading_methods)
- Google Classroom: [Classroom product page](https://edu.google.com/intl/ALL_us/workspace-for-education/products/classroom/), [Originality reports](https://support.google.com/edu/classroom/answer/10039349?hl=en), [Classroom analytics / editions](https://edu.google.com/workspace-for-education/products/classroom/editions/)

## What Is Already Strong

| Area | Status | Why it matters |
| --- | --- | --- |
| Runtime assessment model | Strong | The repo has a clear separation between reusable task definition, class-scoped delivery, per-student outcome, evidence, and teacher judgment. |
| Official truth ownership | Strong | `Task Outcome` and `Task Outcome Criterion` are the derived truth layer, and the gradebook API rejects direct `official_*` writes from clients. |
| Evidence governance | Strong backend | `Task Submission` is append-only, versioned, and exposes governed `preview_url` / `open_url` links instead of raw private file paths. |
| Drawer foundation | Strong current baseline | The staff gradebook now opens one student at a time in `GradebookStudentDrawer`, with marking, evidence, official result, compare context, and release actions in one workspace. |
| Feedback and annotation direction | Strong contract baseline | `07_feedback_annotation_ecosystem_contract.md` now locks the drawer-centered feedback/annotation architecture and keeps file governance explicit. |
| Quiz exception handling | Useful partial | Assessed quiz attempts already have a distinct manual-review path for open-ended questions. |
| Reporting boundary | Architecturally solid | Term reporting is clearly separated from mutable gradebook state. |
| Multi-tenant and hot-path direction | Mostly solid | Gradebook reads are denormalized and roster materialization is bulk/idempotent. |

## Missing / Left To Do

1. The drawer foundation is shipped, but the premium teacher workflow is not complete yet.
Code refs: `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`, `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

The staff SPA now uses `get_drawer(...)` and surfaces marking, evidence, official result, compare, and release in one drawer. The remaining gap is not drawer existence; it is workflow maturity. The current drawer still relies on legacy mutation semantics, lacks the future structured feedback domain, and does not yet deliver the fastest possible teacher flow for collect-work, moderation, or rubric-heavy marking.

2. Draft-vs-official grading semantics are drifting from the documented contract.
Code refs: `ifitwala_ed/docs/assessment/01_assessment_notes.md`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

The notes say autosave should use draft contributions and keep evidence separate until a deliberate teacher action. The live SPA autosaves through `update_task_student(...)`, which calls `submit_contribution(...)`, recomputes official truth immediately, and can create teacher evidence stubs. That is a real workflow mismatch, not just a copy issue.

3. Attachment and evidence review baseline is live, but the premium annotation/feedback workflow is still incomplete.
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/test_task_submission.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`, `ifitwala_ed/docs/assessment/07_feedback_annotation_ecosystem_contract.md`

Teachers can now review submission versions, open governed attachment previews, inspect stale/new-evidence context, and grade from the primary drawer flow. The remaining gap behind the “attachments” complaint is now narrower: no dedicated structured feedback domain yet, no anchored annotation workflow yet, no derived feedback artifact flow yet, and no collect-work evidence inbox optimized for high-volume review.

4. `Collect Work` still needs a dedicated evidence-inbox experience even though the drawer now exposes evidence review.
Code refs: `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`

The task workspace now exposes submission status, latest evidence, attachment preview, and version history through the drawer. The remaining gap is product shape: collect-work is still roster-first rather than evidence-first. A premium assessment surface should add a dedicated evidence inbox for submitted/missing/late/new-evidence scanning with deep links into the drawer.

5. Criteria authoring is still not first-class in the quick task setup flow.
Code refs: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`

The primary overlay still says criteria grading must be configured from the full `Task` record. The create service does not accept `task_criteria` or `default_rubric_scoring_strategy`, and the reuse payload does not expose rubric structure for review or adjustment.

6. Criteria scoring still lacks a clean level-to-points model.
Code refs: `ifitwala_ed/assessment/doctype/assessment_criteria_level/assessment_criteria_level.json`, `ifitwala_ed/api/gradebook_support.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

Assessment criteria levels currently store descriptors only. The gradebook support layer sends criteria levels to the SPA with `points: 0`, so choosing a level does not give the teacher a trustworthy numeric result. Teachers still need to key in `level_points` manually, which weakens consistency and speed.

7. Grade scale and symbolic-grade workflows are not first-class in the teacher UI.
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

The data model supports grade scales, and outcome services can resolve symbolic grades. The live setup flow does not expose grade-scale selection, and the task-gradebook payload does not surface symbolic grade output as a first-class teacher-facing value.

8. Release semantics are closer to the right product shape now, but the contract is still split between grading status and publication state.
Code refs: `ifitwala_ed/api/outcome_publish.py`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`

The current drawer already uses one explicit `Release` / `Unrelease` action, which is directionally correct. The remaining gap is contract clarity: `grading_status` and `is_published` are still separate concepts, and the runtime still allows states like `Finalized` or `Released` to drift away from the one publication flag unless the workflow is normalized.

9. Boolean and completion grading do not have the same audit path as points and criteria.
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`

`Task Contribution` has score, grade, feedback, and rubric rows, but no boolean judgment field. The SPA therefore writes completion/binary state directly onto `Task Outcome.is_complete`. That means auditability, moderation symmetry, and contribution history are weaker for these grading modes than for points/criteria.

10. Gradebook filtering, counts, and scanning are still below the documented teacher contract.
Code refs: `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/Gradebook.vue`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`

The notes call for time scope, status filters, Assess-first focus, and delivery-level counts such as missing/late/review/released. The live page has school/year/program/course filters, but no date scope, no status filters, no workload counts, and `fetch_group_tasks(...)` still returns `status: None`.

11. Moderation, peer review, compare, and governed review workflows are only partial foundations today.
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/task_contribution.json`, `ifitwala_ed/assessment/task_contribution_service.py`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`

The schema already includes `Peer Review`, `Moderator`, and `Official Override`, and moderator writes exist. But there is no teacher workflow for request-review, compare layers, reconcile differences, or move cleanly through moderation and release from the gradebook.

12. Documentation is still carrying some drift and note hygiene issues.
Code refs: `ifitwala_ed/docs/assessment/03_gradebook_notes.md`, `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`, `ifitwala_ed/docs/docs_md/task-assessment-criteria.md`

`03_gradebook_notes.md` mixes current-state UX, future-state flows, and leftover generated prose. The repo also still contains the dormant `Task Assessment Criteria` child table as a documented schema artifact. The notes are useful, but the assessment folder still needs a stricter canonical-vs-roadmap split.

13. Test coverage is still too thin around the most fragile grading behaviors.
Code refs: `ifitwala_ed/assessment/doctype/task_contribution/test_task_contribution.py`, `ifitwala_ed/assessment/test_task_outcome_service.py`, `ifitwala_ed/assessment/test_task_submission_service.py`

The high-risk behaviors are only partially covered: contribution precedence, moderation transitions, boolean-mode audit behavior, release-state consistency, rubric score math, stale evidence review, and grade-scale rendering all need deeper regression tests.

## Resolved Product Directions

The following follow-up decisions were resolved after the initial audit review:

1. Students and guardians should share one release state.
2. `Binary` and `Completion` should move onto the same contribution/audit contract as other grading modes, while `Task Outcome.is_complete` remains derived official truth.
3. Rubric descriptors and levels should stay globally reusable, but numeric point mapping should remain delivery-local.
4. `Collect Work` should stay inside the same assessment product, with a dedicated evidence inbox view that deep-links into the grading drawer.

## 10 Suggestions To Make This A Top-Tier Assessment Module

1. Finish the shipped drawer into the premium teacher workspace.
Why: The drawer now exists and is the correct product anchor. The next move is to harden its workflow quality so it becomes the default high-trust grading surface for evidence, rubric work, compare, and release.

2. Separate `Draft`, `Ready`, `Finalized`, and `Released` as explicit teacher states.
Why: Right now autosave and official truth are too close together. A top-tier workflow should autosave teacher thinking into draft contributions, then require an explicit “Mark ready” or “Finalize” step, and a separate governed “Release” step.

3. Make criteria authoring first-class in the task setup overlay.
Why: Moodle and Blackboard both treat rubric setup as part of the assignment workflow, not a side trip. Teachers should be able to choose criteria, set weighting, define strategy, and preview the scoring consequence before assigning.

4. Give criteria levels a real numeric scoring contract.
Why: Today the teacher can pick a level and still have to type points manually. The repo should support either:
   - per-level points directly on `Assessment Criteria Level`, or
   - a delivery/task rubric mapping layer that resolves level-to-points deterministically.
Without that, criteria grading will keep feeling half-manual.

5. Add a dedicated mastery / outcomes gradebook alongside the delivery gradebook.
Why: Canvas differentiates with its Learning Mastery Gradebook. Ifitwala_Ed should eventually let teachers switch between:
   - delivery-centric grading
   - student-centric intervention view
   - outcome / standards mastery view
This would be a major product differentiator for schools running competency, IB, or standards-based models.

6. Turn the current evidence tab into a premium evidence workflow.
Why: Competitors win when grading is evidence-first. The next step is to build on the existing drawer baseline so it shows:
   - latest submission preview
   - prior versions
   - “new evidence since you graded” warnings
   - governed file previews for documents, images, audio, and video
   - teacher-created stub context when work was observed offline

7. Replace the current release UI with a named release workflow.
Why: Blackboard and Canvas both make “posted/published” state explicit. Ifitwala_Ed should use a dedicated release action with clear audience semantics, audit trail, and bulk controls rather than a loose mix of status dropdowns and visibility checkboxes.

8. Build real moderation and reconciliation, not just moderator writes.
Why: Blackboard differentiates with delegated/parallel grading; your schema already hints at that direction. A premium Ifitwala workflow would support:
   - request peer review
   - compare grader vs reviewer vs moderator
   - reconcile to official result
   - keep moderator notes internal
   - show who changed what and when

9. Add teacher-speed features as a product requirement, not a later polish step.
Why: A daily gradebook lives or dies on speed. The next iteration should include:
   - next/previous student in drawer
   - keyboard-first rubric marking
   - quick comment banks
   - bulk release / bulk complete / bulk status actions
   - class-level counters for missing, late, needs review, stale, and released

10. Treat analytics and SIS/report handoff as part of the gradebook product, not just reporting infrastructure.
Why: Google Classroom is pushing analytics, originality, and SIS sync. Ifitwala_Ed can go further by connecting the gradebook to:
   - class risk scanning
   - criterion distribution heatmaps
   - grading turnaround metrics
   - release history
   - clean downstream export into reporting cycles without recomputation drift

## Recommended Build Sequence

1. Normalize release semantics so one release action owns visibility for both students and guardians.
2. Move `Binary` and `Completion` onto contribution-based writes while keeping `Task Outcome.is_complete` derived.
3. Add delivery-local rubric point mapping so criteria selection produces reliable score consequences.
4. Add a collect-work evidence inbox on top of the existing drawer/evidence baseline.
5. Make criteria authoring/scoring first-class in task setup and task grading.
6. Add moderation / compare / bulk operations after the drawer contract is stable.
7. Add mastery-gradebook and analytics once the day-to-day grading loop is fast and coherent.

## Audit Conclusion

Ifitwala_Ed does not need a new assessment architecture first.
It needs the current architecture to be surfaced coherently and consistently for teachers.

The repo is already strong on:
- server-owned truth
- evidence versioning
- governed file access
- denormalized outcome reads
- reporting separation

The module becomes top-tier when the shipped drawer matures into the full product contract:
- one drawer-centered workflow
- one explicit draft/finalize/release workflow
- true criteria authoring and scoring
- premium evidence review
- real moderation
- fast teacher ergonomics

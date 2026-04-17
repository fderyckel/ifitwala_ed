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
What is still missing is the product layer that makes those primitives feel like one coherent teacher workflow, especially for attachments/evidence review, criteria authoring, release governance, and mode-specific grading behavior.

## Audit Basis

Docs reviewed:
- `ifitwala_ed/docs/assessment/01_assessment_notes.md`
- `ifitwala_ed/docs/assessment/03_gradebook_notes.md`
- `ifitwala_ed/docs/assessment/04_task_notes.md`
- `ifitwala_ed/docs/assessment/05_term_reporting_notes.md`
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
| Quiz exception handling | Useful partial | Assessed quiz attempts already have a distinct manual-review path for open-ended questions. |
| Reporting boundary | Architecturally solid | Term reporting is clearly separated from mutable gradebook state. |
| Multi-tenant and hot-path direction | Mostly solid | Gradebook reads are denormalized and roster materialization is bulk/idempotent. |

## Missing / Left To Do

1. `Gradebook` is still missing the promised drawer-first teacher workflow.
Code refs: `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`, `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`

The backend already exposes `get_drawer(...)` with selected submission, version summaries, official result, and moderation history. The staff SPA does not use it. The live teacher experience is still an inline card editor plus a separate quiz-review panel, so evidence review, comments, criteria, moderation, compare, and release are not unified.

2. Draft-vs-official grading semantics are drifting from the documented contract.
Code refs: `ifitwala_ed/docs/assessment/01_assessment_notes.md`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/api/gradebook.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

The notes say autosave should use draft contributions and keep evidence separate until a deliberate teacher action. The live SPA autosaves through `update_task_student(...)`, which calls `submit_contribution(...)`, recomputes official truth immediately, and can create teacher evidence stubs. That is a real workflow mismatch, not just a copy issue.

3. Attachment and evidence review are implemented on the server but still absent from the main teacher UI.
Code refs: `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/test_task_submission.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

Teachers currently cannot review submission versions, governed attachment previews, or stale-evidence context from the primary gradebook flow. This is the clearest gap behind the current “attachments” complaint.

4. `Collect Work` is not treated as a first-class teacher mode yet.
Code refs: `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`, `ifitwala_ed/docs/assessment/03_gradebook_notes.md`

The overview grid can show `Submitted` or `Awaiting`, but task view does not expose submission status, latest evidence, attachment preview, or version history. For collect-only work, the live UI mostly degrades to comments + visibility toggles.

5. Criteria authoring is still not first-class in the quick task setup flow.
Code refs: `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/assessment/task_creation_service.py`, `ifitwala_ed/api/task.py`, `ifitwala_ed/docs/assessment/gradebook_drawer_phases.md`

The primary overlay still says criteria grading must be configured from the full `Task` record. The create service does not accept `task_criteria` or `default_rubric_scoring_strategy`, and the reuse payload does not expose rubric structure for review or adjustment.

6. Criteria scoring still lacks a clean level-to-points model.
Code refs: `ifitwala_ed/assessment/doctype/assessment_criteria_level/assessment_criteria_level.json`, `ifitwala_ed/api/gradebook_support.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

Assessment criteria levels currently store descriptors only. The gradebook support layer sends criteria levels to the SPA with `points: 0`, so choosing a level does not give the teacher a trustworthy numeric result. Teachers still need to key in `level_points` manually, which weakens consistency and speed.

7. Grade scale and symbolic-grade workflows are not first-class in the teacher UI.
Code refs: `ifitwala_ed/assessment/doctype/task/task.json`, `ifitwala_ed/assessment/doctype/task_delivery/task_delivery.json`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`

The data model supports grade scales, and outcome services can resolve symbolic grades. The live setup flow does not expose grade-scale selection, and the task-gradebook payload does not surface symbolic grade output as a first-class teacher-facing value.

8. Release semantics are fragmented.
Code refs: `ifitwala_ed/api/outcome_publish.py`, `ifitwala_ed/api/gradebook_writes.py`, `ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookTaskView.vue`

The current UI presents a grading-status dropdown plus separate “Visible to Student” and “Visible to Guardian” checkboxes. The backend, however, stores one `Task Outcome.is_published` flag and maps both visibility toggles to that same flag. It is currently possible to drift into states like `Released` without publication, or publication without a clear named release action.

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

## Highest-Leverage Decisions To Make Next

1. Decide whether autosave is truly a draft-only action or whether autosave should be allowed to mutate official truth.
2. Decide whether release is one product action or two audience-specific actions.
3. Decide whether criteria levels need canonical numeric points, or whether criteria scoring will always require separate per-criterion point entry.
4. Decide whether completion/binary assessment must be auditable through contributions or can remain an outcome-direct write path.

## 10 Suggestions To Make This A Top-Tier Assessment Module

1. Ship one unified grading drawer and make it the only rich grading workspace.
Why: Canvas wins teacher trust with a focused grading workspace, and your own backend already has most of the drawer payload. A right-side drawer with evidence, rubric, official result, compare, and release will make the module feel premium quickly.

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

6. Turn evidence review into a premium experience.
Why: Competitors win when grading is evidence-first. The drawer should show:
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

1. Deliver the drawer and switch staff grading to `get_drawer(...)`, `save_draft(...)`, `submit_contribution(...)`, and named release actions.
2. Add evidence review and governed attachment preview in the drawer.
3. Make criteria authoring/scoring first-class in task setup and task grading.
4. Fix release semantics and audience visibility so the UI matches one server-owned contract.
5. Add moderation / compare / bulk operations after the drawer contract is stable.
6. Add mastery-gradebook and analytics once the day-to-day grading loop is fast and coherent.

## Open Questions Worth Resolving Before More UI Work

- Should guardians and students always share the same release state, or do you truly want separate audience visibility?
- Should `Binary` and `Completion` keep using `is_complete`, or should they get a richer contribution/audit contract?
- Do you want rubric levels to own points globally, or should points remain delivery-local?
- Do you want `Collect Work` to live inside the same gradebook, or should it have a dedicated evidence inbox view with gradebook deep-linking?

## Audit Conclusion

Ifitwala_Ed does not need a new assessment architecture first.
It needs the current architecture to be surfaced coherently and consistently for teachers.

The repo is already strong on:
- server-owned truth
- evidence versioning
- governed file access
- denormalized outcome reads
- reporting separation

The module becomes top-tier when the product catches up with the model:
- one drawer
- one explicit draft/finalize/release workflow
- true criteria authoring and scoring
- premium evidence review
- real moderation
- fast teacher ergonomics

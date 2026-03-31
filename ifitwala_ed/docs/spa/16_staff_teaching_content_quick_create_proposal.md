# Staff Teaching Content Quick-Create Proposal

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`, `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/materials/01_materials_guideline.md`, `ifitwala_ed/docs/materials/02_materials_implementation_spec.md`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_activity/lesson_activity.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/curriculum/doctype/supporting_material/supporting_material.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/api/student_groups.py`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/api/test_file_access.py` for current materials behavior; none for the proposed overlay or proposed teacher-adaptation layer

This document proposes a Staff Home quick action for teacher-facing lesson, lesson-activity, and material authoring, plus the product architecture needed to support teacher-specific adaptation across student groups without breaking shared curriculum.

This is intentionally a proposal, not a canonical runtime contract. No existing behavior is changed by this document.

## Product problem

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/supporting-material.md`
Test refs: None

Instructors need a fast Staff Home action that lets them add:

- a lesson
- a lesson activity
- a reusable material

for a concrete teaching context:

- course
- learning unit
- student group they teach

At the same time, the product must preserve a critical distinction:

- multiple teachers can teach the same course and unit outcomes
- they should not be forced into the exact same lesson flow, activity sequence, or materials
- they still need high-leverage reuse so they can copy good work between groups instead of rebuilding everything by hand

## Current workspace facts that constrain the design

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`, `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/materials/01_materials_guideline.md`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`
Test refs: `ifitwala_ed/api/test_courses.py`

1. Staff Home quick actions already use the canonical overlay stack. Any new teacher authoring action should follow the same overlay discipline.
2. The current planned curriculum model is shared and course-owned:
   - `Learning Unit`
   - `Lesson`
   - `Lesson Activity`
3. The current taught runtime model is separate:
   - `Lesson Instance` is the real taught event for a `Student Group`
   - it is intentionally lightweight and should not become the planning library
4. Materials already have the correct reusable domain split:
   - `Supporting Material` is the reusable object
   - `Material Placement` is the contextual share
5. Current material placement anchors are `Course`, `Learning Unit`, `Lesson`, and `Task`.
6. Instructors already have course-teaching context through `Student Group`; `Lesson Instance.course` is fetched from `student_group.course`.
7. Current `fetch_groups()` already supports scoping student-group choices to what the current user can see.

Implication:

- the product should not solve teacher adaptation by overloading `Lesson Instance`
- the product should not solve teacher adaptation by turning materials into lesson-body text
- the product should not assume a shared course lesson automatically equals the exact taught sequence for every group

## Core product decision

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/materials/01_materials_guideline.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/supporting-material.md`
Test refs: None

The system should separate four layers clearly:

1. Shared curriculum
   - course outcomes
   - learning units
   - optional shared lesson blueprints
2. Teacher-owned group adaptation
   - what this teacher plans for this student group inside that unit
3. Reusable materials
   - files and links that should remain reusable across contexts
4. Taught runtime
   - what actually happened in class

Recommended product rule:

- Staff Home quick create should default to group-adaptation authoring, not shared-curriculum authoring.

Reason:

- Staff Home is the instructor’s operational workspace.
- It should optimize for “my class right now,” not for editing the canonical course map for every section.
- Shared course-level curriculum authoring should remain an explicit planning action, not an accidental side effect of a quick action.

## Recommended overlay design

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`, `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
Test refs: None

### New quick action

Add a new Staff Home quick-action tile for instructors:

- label: `Plan teaching content`
- caption: `Add a lesson, activity, or material for one class`

Recommended overlay type name:

- `teaching-content-quick-create`

Recommended entry modes:

- `entryMode='staff-home'`
- future-compatible:
  - `entryMode='class-hub'`
  - `entryMode='course-context'`

`staff-home` is selection-required mode.
Future class-hub and course-context modes should prefill and lock context where possible.

### Overlay layout

Do not use a long wizard. Use one focused overlay with three adaptive sections:

1. Content type switcher
   - `Lesson`
   - `Activity`
   - `Material`
2. Context strip
   - `Course`
   - `Learning Unit`
   - `Student Group`
   - `Scope`
3. Type-specific authoring form

Recommended top-of-overlay framing:

- eyebrow: `Teaching Content`
- title: `Add to class plan`
- helper copy: `Create content for one teaching group without leaving Staff Home.`

### Context strip behavior

The context strip should always appear before the body form.

Required fields:

- `Course`
- `Learning Unit`
- `Student Group`

Recommended filtering:

- `Course` only shows courses the instructor teaches through visible student groups
- `Learning Unit` filters by course
- `Student Group` filters by course plus the teacher’s actual teaching scope

Recommended scope selector:

- `This student group` default
- `Shared course template` advanced and explicit

Guardrail:

- from Staff Home, `This student group` should be the default every time
- `Shared course template` should never be the silent default

### Type-specific forms

#### Lesson mode

Use when the teacher is adding a new planned segment for this group inside the unit.

Fields:

- title
- optional lesson type
- optional duration
- placement in sequence
- optional teacher note
- source choice:
  - `Blank lesson`
  - `Start from shared course lesson`
  - `Copy from another student group I teach`

#### Activity mode

Use when the teacher is adding a pedagogical step into an existing lesson in the group plan.

Fields:

- target lesson in this group plan
- activity type
- title
- activity body fields based on type
- required toggle
- estimated duration

If no group lesson exists yet:

- block submission inline
- explain next step:
  - `Create or copy a lesson for this student group first.`

#### Material mode

Use when the teacher is sharing a separately openable file or link.

Fields:

- `Create new material` or `Reuse existing`
- material title
- file or reference link
- usage role
- teacher note
- placement target:
  - unit
  - lesson

Material mode should explicitly explain that materials are reusable and separately openable.

## Recommended interaction model for teacher adaptation

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/materials/01_materials_guideline.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/material-placement.md`
Test refs: None

### Shared curriculum vs local adaptation

Recommended rule:

- shared curriculum owns outcomes and the common unit structure
- teacher-owned group plans own the exact lesson flow for a student group

That means two teachers can:

- stay aligned to the same course and learning unit
- keep the same intended outcomes
- still diverge on:
  - lesson sequence
  - activity order
  - which materials are emphasized
  - how much reteaching, practice, or enrichment they add

### Copy-on-write for lessons and activities

Recommended reuse behavior for instructional flow:

- lessons and lesson activities should transfer by copy, not by live shared mutation

Reason:

- once a teacher adapts a lesson for one group, silent upstream sync becomes dangerous
- another teacher or coordinator must not accidentally overwrite that local adaptation

Recommended lineage metadata for future implementation:

- source shared lesson, if any
- source student group plan, if copied from another group
- copied by / copied at

But the product behavior should stay simple:

- copying creates a new local version for the target group
- later edits affect only that copied group version

### Link-based reuse for materials

Recommended reuse behavior for materials:

- materials should reuse the same `Supporting Material`
- placement into new contexts should happen through additional `Material Placement` rows

Reason:

- this already matches the live materials architecture
- materials are assets and references, not teacher-specific flow state
- it avoids duplicate files and duplicate links

So the transfer model should differ by content type:

- lesson and activity reuse = copy-based
- material reuse = placement-based

This is the key distinction the product should make obvious.

## Recommended architecture direction

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/docs_md/lesson.md`, `ifitwala_ed/docs/docs_md/lesson-instance.md`, `ifitwala_ed/docs/docs_md/supporting-material.md`
Test refs: None

### Recommended future layer

Do not make `Lesson Instance` carry planning.
Do not make the shared `Lesson` doctype the only place teacher adaptation lives.

Recommended future architecture:

- keep shared `Learning Unit` as the canonical curriculum anchor
- introduce a proposed group-scoped planning layer between shared curriculum and taught runtime

Working concept only, not approved schema:

- a student-group plan for a learning unit
- containing teacher-owned lesson and activity sequence for that group
- optionally derived from shared course lessons

This layer should own:

- sequence for one student group
- local lesson copies
- local activity copies
- lineage back to shared or copied source

This layer should not own:

- the actual runtime session fact
- generic reusable file storage
- grading or task-delivery truth

### Runtime alignment

Longer-term direction:

- when a class session starts, `Lesson Instance` should point to the chosen group plan context
- `Lesson Instance` remains the “what happened” record
- the group plan remains the “what I planned for this class” record

This preserves the current planned-vs-taught distinction instead of collapsing them.

## Rejected design paths

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/docs/materials/01_materials_guideline.md`, `ifitwala_ed/docs/spa/classhub/class_hub_proposal.md`
Test refs: None

### 1. One shared lesson tree for every group

Rejected because:

- it ignores real teacher adaptation
- it makes quick actions risky
- it encourages hidden workarounds outside the system

### 2. Duplicating the whole course curriculum per student group

Rejected because:

- it creates high drift
- it makes curriculum coordination harder
- transfer becomes bulk copy chaos instead of focused reuse

### 3. Using `Lesson Instance` as the planning library

Rejected because:

- the current workspace explicitly defines `Lesson Instance` as lightweight taught runtime
- it would blur planned and taught truth
- it would make transfer and curriculum browse awkward

### 4. Turning materials into lesson-body content

Rejected because:

- the live materials guideline already separates lesson flow from reusable materials
- it would break the reusable-asset model already present in the workspace

## Overlay UX details that reduce friction

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`, `ifitwala_ed/api/student_groups.py`
Test refs: None

Recommended UX details:

- show the selected context as a sticky summary chip row:
  - `Course`
  - `Unit`
  - `Group`
  - `Scope`
- keep one primary action only:
  - `Create lesson`
  - `Create activity`
  - `Add material`
- include a secondary `Save draft` only if draft state is explicitly supported later
- when blocked, explain the next action inline instead of silently disabling the form
- do not require teachers to leave the overlay to search for another group’s content
- expose reuse inside the overlay:
  - `Copy from another group`
  - `Reuse existing material`

Recommended empty-state copy examples:

- `No learning units exist for this course yet. Open curriculum planning or ask an academic lead to create the unit first.`
- `You do not teach any student groups in this course yet. Choose another course or ask an academic lead to update teaching assignments.`
- `No lessons exist for this group yet. Create one first, then add activities.`

### Suggested wireframe

```text
+--------------------------------------------------------------+
| Teaching Content                                             |
| Add to class plan                                            |
|                                                              |
| [Lesson] [Activity] [Material]                               |
|                                                              |
| Course        Learning Unit        Student Group   Scope     |
| [Math 7]      [Fractions]          [7A]            [This grp]|
|                                                              |
| Source: [Blank] [From shared lesson] [Copy from other group] |
|                                                              |
| Type-specific form                                           |
| - title / type / duration / target lesson / material fields  |
|                                                              |
| Context summary                                              |
| This will appear only in the 7A teaching plan.               |
|                                                              |
| [Cancel]                                  [Create lesson]    |
+--------------------------------------------------------------+
```

## Permission, scope, and concurrency expectations

Status: Proposed
Code refs: `ifitwala_ed/api/student_groups.py`, `ifitwala_ed/docs/high_concurrency_contract.md`, `ifitwala_ed/docs/materials/02_materials_implementation_spec.md`
Test refs: `ifitwala_ed/api/test_file_access.py`

Any future implementation should follow these rules:

- context options come from one bounded bootstrap/read endpoint for the overlay
- do not load courses, units, groups, lessons, and materials through client waterfalls
- student-group choices must be server-scoped to what the current instructor actually teaches
- material open and upload actions must reuse the current governed materials flow
- no raw private file URLs in the overlay or downstream class views

## Implementation sequence after approval

Status: Proposed
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`, `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`, `ifitwala_ed/docs/materials/02_materials_implementation_spec.md`
Test refs: None

Recommended sequence:

1. Approve the product distinction:
   - shared curriculum vs teacher-owned group adaptation
2. Approve the future persistence direction:
   - dedicated group-planning layer instead of overloading `Lesson Instance`
3. Implement one aggregated overlay-options endpoint and the Staff Home overlay shell
4. Ship material mode first if a smaller slice is needed, because the reusable materials domain already exists
5. Add lesson copy and activity copy flows only after the group-planning layer is approved

## Open decisions needing explicit approval later

Status: Proposed
Code refs: `ifitwala_ed/docs/curriculum/01_curriculum_task_delivery_contract.md`, `ifitwala_ed/curriculum/doctype/lesson/lesson.json`, `ifitwala_ed/curriculum/doctype/lesson_instance/lesson_instance.json`
Test refs: None

The following are intentionally left open and must be approved before implementation:

- exact schema shape of the group-planning layer
- whether instructors may promote local group lessons into shared course templates
- whether shared course template authoring remains open to instructors or shifts to curriculum roles
- how runtime `Lesson Instance` should reference the future group-planning layer
- whether copied group lessons ever support upstream-diff review, or remain fully independent after copy

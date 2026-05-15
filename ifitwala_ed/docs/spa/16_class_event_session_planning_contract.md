# Class Event Session Planning Contract (v1)

Status: Active

This document is the canonical contract for creating or editing a `Class Session` directly from the staff calendar class-event modal.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
3. `ifitwala_ed/docs/high_concurrency_contract.md`
4. `ifitwala_ed/docs/docs_md/class-session.md`
5. This document

## 1. Surface and Entry Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/__tests__/quickClassSessionRules.test.ts`

Rules:

1. The canonical overlay type is `quick-class-session`.
2. Staff calendar class events open the overlay from `ClassEventModal` through a dedicated `Plan This Session` action.
3. The calendar event remains the context anchor. The teacher should not be forced into the full Class Planning page for the common “plan this lesson for this date” workflow.
4. The overlay entry is prefilled with the clicked class-event context:
   - `student_group`
   - class title
   - course label
   - `session_date`
   - optional block label
   - optional start/end/time context
5. `Open Full Class Planning` remains available as a secondary escape hatch for deeper planning work.

## 2. Bootstrap and Suggestion Rules

Status: Implemented

Code refs:
- `ifitwala_ed/api/calendar_details.py`
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`
- `ifitwala_ed/ui-spa/src/overlays/planning/quickClassSessionRules.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/__tests__/quickClassSessionRules.test.ts`

Rules:

1. The overlay must bootstrap from the existing bounded class-planning read model:
   - `ifitwala_ed.api.teaching_plans.get_staff_class_planning_surface`
2. The overlay must not introduce a second class-planning bootstrap endpoint.
3. When a session already exists on the clicked `session_date`, the overlay opens in edit mode for that saved `Class Session`.
4. When no same-date session exists, the overlay opens a new draft and suggests the unit in this order:
   - current class unit with `pacing_status = "In Progress"`
   - otherwise the next untaught unit
   - otherwise the most recently active unit
5. The overlay should prefill the new draft with:
   - `session_date` from the clicked event
   - `session_status = "Planned"` when a calendar date is known
   - a suggested `sequence_index`
   - a title seed from the selected unit title
6. Teachers may override the suggested unit and all editable session fields before save.

## 3. Mutation and Initialization Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/ui-spa/src/lib/services/staff/staffTeachingService.ts`
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`

Test refs:
- `ifitwala_ed/api/test_teaching_plans.py`
- `ifitwala_ed/ui-spa/src/lib/services/staff/__tests__/staffTeachingService.test.ts`

Rules:

1. The overlay uses only existing named planning mutations:
   - `ifitwala_ed.api.teaching_plans.create_class_teaching_plan`
   - `ifitwala_ed.api.teaching_plans.save_class_session`
2. The overlay must not create `Class Session` rows through generic document insert APIs.
3. If the class does not yet have a `Class Teaching Plan`, the overlay may initialize one through `create_class_teaching_plan` before session save.
4. If no governing `Course Plan` is available, the overlay must block save and explain the next action.
5. Session activities are saved as ordered `Class Session Activity` rows inside the `save_class_session` payload.

## 4. Overlay Ownership and Concurrency Rules

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`

Test refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/__tests__/quickClassSessionRules.test.ts`

Rules:

1. The overlay closes immediately on semantic session-save success.
2. The overlay does not own calendar refresh or page refresh.
3. The overlay must stay on one bounded bootstrap read and must not fan out into a request waterfall for unit/session context.
4. Blocked actions must explain why the session cannot be saved and what the teacher needs to do next.

## 5. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`
- `ifitwala_ed/ui-spa/src/overlays/planning/quickClassSessionRules.ts`
- `ifitwala_ed/api/teaching_plans.py`

Test refs:
- `ifitwala_ed/ui-spa/src/overlays/planning/__tests__/quickClassSessionRules.test.ts`
- `ifitwala_ed/api/test_teaching_plans.py`

- This workflow intentionally stays on the current class-owned planning model:
  - `Class Teaching Plan`
  - `Class Session`
  - `Class Session Activity`
- The calendar click may supply block context for orientation, but block is not the persisted planning identity in v1.
- Cross-class or cross-year session reuse is not part of this contract yet; it requires a separate bounded read model rather than ad hoc client-side guessing.

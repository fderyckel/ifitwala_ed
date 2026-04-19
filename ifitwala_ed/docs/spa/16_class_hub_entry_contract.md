# Class Hub Entry Contract (v1)

Status: Active

This document is the canonical contract for opening Class Hub from Staff Home and for the instructor-scoped class chooser that supports that workflow.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
3. `ifitwala_ed/docs/high_concurrency_contract.md`
4. This document

If implementation changes this workflow, update this document in the same change.

## 1. Surface and Entry Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`
- `ifitwala_ed/ui-spa/src/components/overlays/class-hub/ClassHubGroupPickerOverlay.vue`
- `ifitwala_ed/ui-spa/src/components/overlays/class-hub/WheelPickerOverlay.vue`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`
- `ifitwala_ed/ui-spa/src/composables/useOverlayStack.ts`
- `ifitwala_ed/ui-spa/src/router/index.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`

Rules:

1. Staff Home exposes a dedicated quick action labeled `Open Class Hub`.
2. The Staff Home quick action is the stable entry point for opening a class workspace from the home page when the teacher wants to choose among taught groups.
3. The home-page quick action must not expose the student picker directly.
4. The student picker remains a Class Hub workflow and is launched from the Class Hub header only.
5. The canonical Class Hub route is `/staff/class/:studentGroup`.
6. Staff Home quick action behavior is:
   - exactly one taught student group -> open that Class Hub route immediately
   - multiple taught student groups -> open the chooser overlay
   - no taught student groups -> open the chooser overlay in honest blocked-state mode
7. The chooser overlay must explain what the user should do next when no student groups are available.

## 2. Permission and Scope Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/portal.py`
- `ifitwala_ed/api/class_hub.py`
- `ifitwala_ed/api/student_groups.py`

Test refs:
- `ifitwala_ed/api/test_analytics_permissions.py`
- `ifitwala_ed/api/test_class_hub.py`

Rules:

1. Staff Home capability for this surface is `quick_action_class_hub`.
2. Staff Home only shows the quick action when the current user has instructor-grade Class Hub access.
3. The chooser payload must be server-owned and instructor-scoped.
4. Class Hub group resolution may include both explicit `Student Group Instructor` assignments and operational teaching bookings derived from `Employee Booking`.
5. Staff Home must not derive accessible student groups from client-side route state, cached UI data, or broad student-group endpoints.
6. Class Hub itself remains protected by the server-side instructor membership check for the target `student_group`.

## 3. API and Overlay Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/class_hub.py`
- `ifitwala_ed/ui-spa/src/lib/classHubService.ts`
- `ifitwala_ed/ui-spa/src/types/classHub.ts`
- `ifitwala_ed/ui-spa/src/components/overlays/class-hub/ClassHubGroupPickerOverlay.vue`

Test refs:
- `ifitwala_ed/api/test_class_hub.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`

Rules:

1. Staff Home uses the named endpoint `ifitwala_ed.api.class_hub.resolve_staff_home_entry`.
2. The endpoint returns semantic status values:
   - `single`
   - `choose`
   - `empty`
3. The endpoint response carries only the group fields needed to launch Class Hub:
   - `student_group`
   - `student_group_name`
   - `title`
   - optional `course`
   - optional `academic_year`
4. The SPA must not call `resolve_current_picker_context()` to decide whether Staff Home should show a Class Hub entry.
5. The chooser overlay is a routing aid only; it does not own Class Hub data loading or permission decisions.

## 4. UX and Concurrency Rules

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/api/class_hub.py`

Test refs:
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`

Rules:

1. Staff Home must not poll the live schedule just to decide whether the Class Hub quick action should exist.
2. The Staff Home quick action decision is capability-based, not live-class-state-based.
3. The chooser request is a single bounded read and must not fan out into per-group follow-up calls before the user chooses a class.
4. Failure to resolve the quick action must surface an actionable error instead of failing silently.

## 5. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/api/class_hub.py`
- `ifitwala_ed/api/teaching_plans.py`
- `ifitwala_ed/ui-spa/src/components/overlays/class-hub/ClassHubGroupPickerOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassHub.vue`

Test refs:
- `ifitwala_ed/api/test_class_hub.py`
- `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts`

- Staff Home and Class Hub intentionally have different entry semantics:
  - Staff Home -> choose or open a taught class
  - Class Hub -> run live class workflows, including the student picker
- Class Hub teaching scope is server-owned and may be satisfied either by explicit instructor assignment on the Student Group or by authoritative teaching bookings materialized for that employee from the schedule.
- The Class Hub route is still class-scoped, but live runtime now resolves the active `Class Teaching Plan` for that class and operates on real `Class Session` records instead of demo session state.
- Class Hub planning handoffs must deep-link to `staff-class-planning` with `unit_plan` when the current session or current unit is known so the teacher lands on the right unit context directly.
- When no dated session exists, Class Hub must resolve the current unit from the shared current-curriculum resolver before showing a bundle message or creating a minimal session.
- `Start Session` must reuse the dated `Class Session` when one already exists for the target date. It may create a minimal in-progress `Class Session` only when the class already has a valid class teaching plan and governed unit backbone.
- If the shared resolver cannot determine a current unit, Class Hub must show an actionable blocked state instead of guessing a first unit.
- The chooser overlay supports `Esc`, backdrop close, and explicit close button behavior through the shared overlay host contract.

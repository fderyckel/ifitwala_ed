# A+ Audit Report: `ui-spa/components/`

**Date:** 2026-01-17
**Scope:** `ui-spa/components/` vs `docs/spa/spa_architecture_and_rules.md`

## Executive Summary

The audit reveals significant drift between the authoritative A+ documentation and the actual codebase structure. The most critical findings are:
1.  **Missing Canonical Folder**: `ui-spa/src/overlays/` does not exist, despite being the mandated home for all workflow overlays.
2.  **Architectural Violations**: Legacy components (e.g., `MeetingEventModal.vue`) perform direct API calls and error handling, bypassing the Service Layer.
3.  **Naming & Structural Inconsistency**: Overlays are scattered across `components/`, `components/overlays/`, and `components/overlay/`, with inconsistent naming (`*Overlay` vs `*Modal`).
4.  **Missing Documentation**: Components lack the required top-level comments identifying their usage/consumers.

---

## 1. Component Location Audit

**Rule**: `ui-spa/src/overlays/` is the canonical home for overlay panels rendered via `OverlayHost`. `ui-spa/src/components/` is for reusable UI parts.

### Violations & Correction Plan

| Component | Current Location | Status | Correct Location | Reason |
| :--- | :--- | :--- | :--- | :--- |
| `OverlayHost.vue` | `components/overlay/` | ❌ **Misplaced** | `src/overlays/OverlayHost.vue` | The host of the overlay stack belongs in the root of the overlay directory. |
| `StudentLogCreateOverlay.vue` | `components/student/` | ❌ **Misplaced** | `src/overlays/student/StudentLogCreateOverlay.vue` | Workflow overlay managed by OverlayHost. |
| `StudentLogFollowUpOverlay.vue` | `components/student/` | ❌ **Misplaced** | `src/overlays/student/StudentLogFollowUpOverlay.vue` | Workflow overlay. |
| `FocusRouterOverlay.vue` | `components/focus/` | ❌ **Misplaced** | `src/overlays/focus/FocusRouterOverlay.vue` | Router overlay. |
| `MeetingEventModal.vue` | `components/calendar/` | ❌ **Misplaced** | `src/overlays/calendar/MeetingEventOverlay.vue` | Workflow/Detail overlay. Rename to `*Overlay` for consistency. |
| `SchoolEventModal.vue` | `components/calendar/` | ❌ **Misplaced** | `src/overlays/calendar/SchoolEventOverlay.vue` | Workflow/Detail overlay. Rename to `*Overlay`. |
| `ClassEventModal.vue` | `components/calendar/` | ❌ **Misplaced** | `src/overlays/calendar/ClassEventOverlay.vue` | Workflow/Detail overlay. Rename to `*Overlay`. |
| `OrgCommunicationQuickCreateModal.vue` | `components/communication/` | ❌ **Misplaced** | `src/overlays/communication/OrgCommunicationQuickCreateOverlay.vue` | Workflow overlay. Rename to `*Overlay`. |
| `StudentContextOverlay.vue` | `components/overlays/class-hub/` | ❌ **Misplaced** | `src/overlays/class-hub/StudentContextOverlay.vue` | Nesting `overlays` inside `components` is anti-pattern. |
| `QuickEvidenceOverlay.vue` | `components/overlays/class-hub/` | ❌ **Misplaced** | `src/overlays/class-hub/QuickEvidenceOverlay.vue` | same as above. |
| `QuickCFUOverlay.vue` | `components/overlays/class-hub/` | ❌ **Misplaced** | `src/overlays/class-hub/QuickCFUOverlay.vue` | same as above. |
| `TaskReviewOverlay.vue` | `components/overlays/class-hub/` | ❌ **Misplaced** | `src/overlays/class-hub/TaskReviewOverlay.vue` | same as above. |
| `CreateTaskDeliveryOverlay.vue` | `components/tasks/` | ❌ **Misplaced** | `src/overlays/tasks/CreateTaskDeliveryOverlay.vue` | Workflow overlay. |

### Missing Usage Comments
**Rule**: "Each components should have comments on top that easily identify where it is used".
**Status**: **FAILED**. Almost no components have this.
**Action**: Add `<!-- Used by: <PageName>.vue, <OtherComponent>.vue -->` to the top of every component during the move.

---

## 2. Redundancy Audit

### 1. `OverlayHost` Static Imports
**Issue**: `OverlayHost.vue` statically imports every single overlay. This creates tight coupling and a massive dependency graph.
**Proposal**: Use async components (`defineAsyncComponent`) in `OverlayHost` to decouple the host from the specific implementations, improving load time and modularity.

### 2. Modal vs Overlay Styling
**Issue**: `MeetingEventModal` uses custom `meeting-modal__*` BEM classes, while `StudentLogCreateOverlay` uses `if-overlay__*` classes.
**Proposal**: Refactor `MeetingEventModal` (and other calendar modals) to use the standard `if-overlay-*` classes and structure (Header, Body, Footer) defined in `StudentLogCreateOverlay` (the Reference Implementation).

### 3. Generic Dialogs
**Issue**: `ContentDialog.vue` and `GenericListDialog.vue` overlap in purpose (displaying content in a modal).
**Proposal**:
*   `GenericListDialog` seems specific to simple lists. Keep if necessary but standardise styling to match `if-overlay`.
*   `ContentDialog` acts as a "Teleport to body" dialog, bypassing `OverlayHost`. This is risky for z-index management. Evaluate moving it to `OverlayHost` stack or strictly managing its z-index (currently hardcoded `z-[60]`).

---

## 3. Architecture Scoring (Sample)

| Component | Score (0-1) | Deductions / Notes |
| :--- | :--- | :--- |
| **`StudentLogCreateOverlay.vue`** | **0.9** | **(-0.1) Location**: Wrong folder.<br>**(+1) Architecture**: Perfect adherence. Uses Service, emits `close`, no signals, inline errors. |
| **`QuickCFUOverlay.vue`** | **0.8** | **(-0.1) Location**: Wrong folder.<br>**(-0.1) Comments**: Missing usage context.<br>**(+1) Architecture**: Uses `classHubService`, clean closing logic. |
| **`MeetingEventModal.vue`** | **0.2** | **(-0.5) API Violation**: Calls `api(...)` directly in component. <br>**(-0.1) Naming**: Uses `Modal` instead of `Overlay`.<br>**(-0.1) Location**: Wrong folder.<br>**(-0.1) Styling**: Custom CSS instead of design system tokens. |
| **`ContentDialog.vue`** | **0.8** | **(-0.1) Location**: Root `components/` is vague.<br>**(-0.1) Strategy**: Bypasses `OverlayHost`, potential z-index conflict. |
| **`PortalNavbar.vue`** | **1.0** | Assumed good as it's a pure layout component (visual check needed to confirm no business logic). |

---

## 4. Remediation Plan (Prioritized)

1.  **Folder Structure Fix**:
    *   Create `ui-spa/src/overlays/`.
    *   Move `OverlayHost.vue` and all identified overlay components to `src/overlays/`.
    *   Update imports in `OverlayHost.vue`.

2.  **Architecture Fix (Urgent)**:
    *   Refactor `MeetingEventModal.vue` (and siblings `SchoolEventModal`, `ClassEventModal`):
        *   Create `CalendarService.ts` in `lib/services/`.
        *   Move API calls there.
        *   Rename to `*Overlay`.
        *   Standardize CSS.

3.  **Documentation**:
    *   Add `<!-- Used by: ... -->` comment to all components.

4.  **Cleanup**:
    *   Delete empty `components/overlays/` and `components/overlay/` folders.

# Org Communication Quick Create Contract (v1)

Status: Active

This document is the canonical contract for the Staff Home quick-link overlay that creates `Org Communication` records, and for the locked class-event entry mode that reuses the same overlay shell.

Authority order:

1. `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
2. `ifitwala_ed/docs/spa/03_overlay_and_workflow.md`
3. `ifitwala_ed/docs/high_concurrency_contract.md`
4. This document

## 1. Surface and Entry-Point Modes

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/components/calendar/ClassEventModal.vue`
- `ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue`
- `ifitwala_ed/ui-spa/src/overlays/OverlayHost.vue`

Test refs:
- `ifitwala_ed/api/test_analytics_permissions.py`

Rules:

1. The canonical overlay type is `org-communication-quick-create`.
2. Staff Home opens the overlay as a quick link so staff can create communications without leaving the SPA for Desk.
3. The overlay supports explicit `entryMode='staff-home' | 'class-event'`.
4. `entryMode='staff-home'` is the general-purpose quick-create workflow for staff, student-group, and community communications.
5. `entryMode='class-event'` is a prefilled, locked context mode that keeps the communication anchored to the selected class event and student group.
6. In `entryMode='staff-home'`, the footer exposes two explicit actions:
   - `Publish`
   - `Save as draft`
7. The `Publish` action derives workflow state from the entered publish window:
   - future `publish_from` => `Scheduled`
   - blank or current/past `publish_from` => `Published`
8. The `Save as draft` action always persists `status='Draft'`.

## 2. API and Payload Contract

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_quick_create.py`
- `ifitwala_ed/ui-spa/src/lib/services/orgCommunicationQuickCreateService.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options.ts`
- `ifitwala_ed/ui-spa/src/types/contracts/org_communication_quick_create/create_org_communication_quick.ts`

Test refs:
- `ifitwala_ed/api/test_org_communication_quick_create.py`
- `ifitwala_ed/ui-spa/src/lib/services/__tests__/orgCommunicationQuickCreateService.test.ts`

Rules:

1. The SPA must use named POST endpoints only:
   - `ifitwala_ed.api.org_communication_quick_create.get_org_communication_quick_create_options`
   - `ifitwala_ed.api.org_communication_quick_create.create_org_communication_quick`
2. The SPA sends the payload as the flat JSON body directly, not wrapped inside a nested `payload` or `doc` object.
3. `get_org_communication_quick_create_options()` is the canonical source for:
   - organization and school authoring scope
   - allowed communication/status/priority/surface/interaction options
   - recipient rules per audience target mode
   - reference lists for organizations, schools, teams, and student groups
4. `create_org_communication_quick(...)` is the only SPA mutation path for quick-create and inserts through the existing `Org Communication` controller validations.
5. The quick-create mutation supports `client_request_id` and returns semantic success as `status='created' | 'already_processed'`.
6. Response `name` is the internal `Org Communication` record id. Visible `title` remains user-authored display text and is not required to be unique.

## 3. Validation and Scope Ownership

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_quick_create.py`
- `ifitwala_ed/setup/doctype/org_communication/org_communication.py`
- `ifitwala_ed/setup/doctype/org_communication/org_communication.js`

Test refs:
- `ifitwala_ed/api/test_org_communication_quick_create.py`
- `ifitwala_ed/setup/doctype/org_communication/test_org_communication.py`
- `ifitwala_ed/ui-spa/src/components/communication/__tests__/OrgCommunicationQuickCreateModal.test.ts`

Rules:

1. Server-side `Org Communication` controller logic remains the source of truth for organization scope, issuing school scope, audience validation, status rules, and portal-surface rules.
2. The SPA mirrors the Desk client audience-row behaviors for target-mode visibility and recipient defaults, but those checks are UX only.
3. The SPA must not bypass or replace controller validation with generic `frappe.client.insert`.
4. Role-based restrictions for wide-audience rows remain server-owned and are only mirrored in the SPA to make blocked actions obvious earlier:
   - `School Scope` rows targeting `Staff` or `Community`
   - `Organization` rows targeting `Staff`

## 4. Overlay and Invalidation Contract

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue`
- `ifitwala_ed/ui-spa/src/lib/services/orgCommunicationQuickCreateService.ts`
- `ifitwala_ed/ui-spa/src/lib/uiSignals.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/__tests__/orgCommunicationQuickCreateService.test.ts`
- `ifitwala_ed/ui-spa/src/components/communication/__tests__/OrgCommunicationQuickCreateModal.test.ts`

Rules:

1. The overlay closes immediately on semantic success.
2. The quick-create service emits `SIGNAL_ORG_COMMUNICATION_INVALIDATE` only after semantic success.
3. The overlay never owns cross-surface refresh.
4. Refresh owners such as the archive page remain responsible for reloading their own org-communication data.
5. Staff Home quick-create must not rely on the DocType default status to decide the primary action.

## 5. Technical Notes (IT)

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_quick_create.py`
- `ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue`

Test refs:
- `ifitwala_ed/api/test_org_communication_quick_create.py`
- `ifitwala_ed/ui-spa/src/components/communication/__tests__/OrgCommunicationQuickCreateModal.test.ts`

- Quick-create idempotency TTL: `900s`
- Audience target modes are:
  - `School Scope`
  - `Team`
  - `Student Group`
  - `Organization` for Academic Admin, Academic Assistant, HR Manager, Accounts Manager, and System Manager
- Class-event mode preserves the legacy quick-create intent, but now uses the same named workflow and server-owned validation path as Staff Home quick create.

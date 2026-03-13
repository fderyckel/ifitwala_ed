# Guardian Portal Authoritative Docs Map

Status: Working note
Authority: Non-authoritative
Scope: Reference map for `/hub/guardian` contracts
Last updated: 2026-03-13

This note lists which documents are authoritative for the guardian portal and which supporting contracts they import by reference.

## 1. Canonical Guardian Portal Docs

Status: Completed

Authoritative docs:

1. `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
   Purpose: product scope, route namespace, implemented surfaces, non-goals.
2. `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
   Purpose: guardian home payload, zone order, drill-down behavior.
3. `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
   Purpose: linked-student scope, publication gates, read-state rules.
4. `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`
   Purpose: implemented guardian actions and explicitly deferred actions.

Rule:

1. These four files define guardian portal behavior.
2. `z*` files are working notes only and must not redefine product truth.

## 2. Supporting Contracts Imported By Reference

Status: Completed

Supporting docs:

1. `ifitwala_ed/docs/spa/07_org_communication_messaging_contract.md`
   Imported for org communication visibility and read-state rules.
2. `ifitwala_ed/docs/enrollment/activity_booking_architecture.md`
   Imported for guardian activity booking workflows at `/guardian/activities`.
3. `ifitwala_ed/docs/docs_md/task-delivery.md`
   Imported for due-task and assessment-chip semantics used by guardian home.
4. `ifitwala_ed/docs/docs_md/task-outcome.md`
   Imported for published outcome semantics used by guardian home recent activity.

Rule:

1. If one of these supporting contracts changes guardian portal behavior, the matching guardian portal contract must be updated in the same change.

## 3. `/hub/guardian` Code Surface Map

Status: Completed

Code refs:
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/api/users.py`
- `ifitwala_ed/ui-spa/src/router/index.ts`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`

Test refs:
- `ifitwala_ed/api/test_users.py`
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Rule:

1. Documentation changes for `/hub/guardian` should point back to this code surface, not to proposed files that do not exist.

## 4. Drift Rules

Status: In progress

Rules:

1. Do not append implementation brainstorming or handoff text after a canonical lock statement.
2. Do not keep proposal-only payload shapes in notes once the real TypeScript contract exists.
3. If `/hub/guardian` gains a new route, action, or payload field, update the matching authoritative doc first or in the same PR.
4. If a note needs to mention future work, it must label itself non-authoritative and link back to the canonical contract files.

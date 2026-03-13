# Guardian Portal Backlog From The Authoritative Contracts

Status: Working note
Authority: Non-authoritative
Scope: PR-sized backlog for `/hub/guardian`
Last updated: 2026-03-13

This note translates the authoritative guardian portal contracts into a short backlog. It does not replace the contracts.

## 1. What Already Matches

Status: Completed

Authoritative docs:
- `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/guardianHomeService.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/api/test_activity_booking.py`
- `ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts`

Current matches:

1. The canonical guardian home snapshot endpoint exists.
2. The SPA has a guardian-specific service and route wiring.
3. The four guardian home zones are rendered on the landing page.
4. The student drill-down and guardian activities routes already exist.

## 2. Gaps Still Worth Closing

Status: In progress

Authoritative docs:
- `ifitwala_ed/docs/spa/guardian_portal/02_information_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/03_visibility_contract.md`
- `ifitwala_ed/docs/spa/guardian_portal/04_guardian_actions.md`

Code refs:
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`

Test refs:
- `ifitwala_ed/api/test_guardian_home.py`
- Guardian page tests: None

Open gaps:

1. Guardian Home and Guardian Student Shell do not yet have page-level regression tests.
2. The snapshot tests are narrow and do not yet prove all visibility categories together in one end-to-end fixture.
3. The current home payload does not expose direct action metadata for each attention item, so actionability remains limited to what the UI already hardcodes.
4. Planned guardian actions remain intentionally unwired and need explicit approval before implementation.

## 3. Suggested PR Breakdown

Status: Planned

Code refs:
- `ifitwala_ed/api/test_guardian_home.py`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianStudentShell.vue`
- `ifitwala_ed/api/activity_booking.py`
- `ifitwala_ed/api/test_activity_booking.py`

Test refs:
- Existing tests above plus new UI tests: Planned

PRs:

1. `PR-G1`: expand guardian snapshot backend tests to cover linked students, guardian-visible student logs, published outcomes, unread communications, and forbidden key regression.
2. `PR-G2`: add page tests for Guardian Home and Guardian Student Shell covering load, empty state, blocked state, and zone order.
3. `PR-G3`: add direct-action metadata for attention items only if the team wants blocker/action buttons on home and the contract is updated first.
4. `PR-G4`: evaluate one deferred guardian action at a time, starting with the highest-value workflow, and add route, API, tests, and doc updates together.

## 4. Follow-Up Needed Before New Scope

Status: Planned

Rules:

1. Policy acknowledgement on `/hub/guardian` needs an explicit route and named workflow endpoint before coding starts.
2. Direct messaging on `/hub/guardian` must reuse the org communication contract instead of inventing a new channel.
3. Monitoring mode requires a separate approval because it changes guardian notification behavior.
4. Payments and uploads need their own canonical contracts before they can be treated as guardian portal scope.

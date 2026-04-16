<!-- ifitwala_ed/docs/testing/05_browser_e2e_proposal.md -->
# Ifitwala_Ed Browser E2E Proposal (Non-Canonical)

Status: Implemented (phase 1, local/manual)
Scope: repo-level browser E2E for `/hub` and `/admissions`
Canonical impact: none until explicitly approved and folded into `01_test_strategy.md` and `02_ci_policy.md`
Code refs: `package.json`, `ifitwala_ed/ui-spa/package.json`, `ifitwala_ed/codex_cli.py`, `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/router/admissions.ts`, `ifitwala_ed/ui-spa/src/apps/portal/main.ts`, `ifitwala_ed/ui-spa/src/apps/admissions/main.ts`, `ifitwala_ed/ui-spa/src/composables/useAdmissionsSession.ts`, `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`
Test refs: `ifitwala_ed/api/test_users.py`, `ifitwala_ed/website/tests/test_portal_route.py`, `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/tests/factories/*`, `ifitwala_ed/docs/testing/01_test_strategy.md`, `ifitwala_ed/docs/testing/02_ci_policy.md`, `ifitwala_ed/docs/testing/03_staging_data_policy.md`

## 1. Bottom line

The supplied proposal is directionally correct on one point: Ifitwala_Ed should add a small browser E2E layer for critical cross-layer journeys.

It is not repo-accurate as written. This repository already has strong server-side auth and route tests, already has a large SPA unit layer, and actually ships two browser apps: `/hub` and `/admissions`. The first E2E phase should therefore be smaller, more browser-integration-focused, and stricter about keeping test orchestration out of the public API surface.

## 2. Current repo reality

1. The repo already has a heavy non-browser test base.
   - There are 48 API test modules under `ifitwala_ed/api`.
   - There are 51 SPA test files under `ifitwala_ed/ui-spa/src`.
   - Current CI already gates on backend smoke/domain, lint, desk build, and SPA type-check/build.

2. Browser behavior is split across two separate apps, not one unified SPA.
   - `/hub` is owned by `ifitwala_ed/ui-spa/src/router/index.ts` with base `/hub`.
   - `/admissions` is owned by `ifitwala_ed/ui-spa/src/router/admissions.ts` with base `/admissions`.
   - Each has a distinct bootstrap entry in `src/apps/portal/main.ts` and `src/apps/admissions/main.ts`.

3. Auth and route resolution already have meaningful backend coverage.
   - `ifitwala_ed/api/test_users.py` covers login redirect rules, role precedence, logout edge cases, and admissions/staff/guardian/student entry routing.
   - `ifitwala_ed/website/tests/test_portal_route.py` covers guest redirects, canonical route redirects, and staff-versus-student namespace protection.

4. The admissions portal already has a sizable browser-facing contract surface.
   - `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts` wraps the key admissions mutations and emits portal invalidation signals.
   - `ifitwala_ed/ui-spa/src/composables/useAdmissionsSession.ts` owns applicant switching and route-query synchronization.
   - `ifitwala_ed/api/test_admissions_portal.py` already validates many server-side admissions contracts.

5. There is no existing browser-test orchestration contract yet.
   - No Cypress or Playwright config exists today.
   - No scenario seed/reset runner exists for browser tests.
   - `ifitwala_ed/codex_cli.py` currently exposes `doctor`, `lint`, `backend-smoke`, `desk-build`, `spa-typecheck`, and `ci`, but nothing for browser E2E.

## 3. Critical analysis of the supplied proposal

### 3.1 What it gets right

1. Root-level browser tests are the right scope.
   - Browser E2E here is repo-wide, not just `ui-spa`, because it crosses website routing, login/session behavior, `/hub`, `/admissions`, and backend contracts.

2. Deterministic data is mandatory.
   - The existing testing docs already require synthetic deterministic data for CI/staging.
   - Browser tests that depend on ambient site state will become noisy immediately.

3. E2E should stay narrow.
   - The current test strategy already puts business-rule depth in backend tests and client contract depth in SPA unit tests.
   - Browser E2E should only cover failures that appear when those layers meet in a real browser.

4. Root package wiring is the correct eventual execution surface.
   - Root `package.json` already owns the production build contract for Desk plus `ui-spa`.
   - Hiding repo-wide browser tests inside `ifitwala_ed/ui-spa` would misstate ownership.

### 3.2 Where it drifts from this repo

1. The suggested first 8 tests over-invest in auth duplication.
   - Four of the eight are login/logout/route-guard smoke cases.
   - Those rules are already strongly covered at the backend and website-routing layers.
   - The browser budget should go first to flows only a browser can catch: shell bootstrap, route-query synchronization, save feedback, submit gating, and role-scoped content rendering.

2. “Backend seed/reset helpers” must not become public app APIs.
   - Adding whitelisted orchestration endpoints under `ifitwala_ed/api` would create alternate product-facing surfaces with permission and maintenance risk.
   - Test data orchestration should live in test-only Python modules invoked by bench or repo CLI, not in reusable browser-callable business APIs.

3. The folder split is too generic for the actual app shape.
   - The important top-level boundary is not `smoke` versus `portal`.
   - The important boundary is `/hub` versus `/admissions`, because they have different routers, bootstraps, layouts, and failure modes.

4. The CI recommendation is too aggressive for phase 1.
   - The current required PR pipeline is already expensive.
   - Adding a browser job that needs site bootstrap, assets, seeded data, and a real web server should not become merge-blocking until it proves stable on dedicated infrastructure.

5. A new auth endpoint is the wrong default.
   - This stack already has canonical login/logout behavior.
   - E2E should reuse real Frappe session mechanics, then cache the session per role/journey.

6. The selector plan is slightly over-designed for day 1.
   - The repo already uses visible labels, route shells, and a few `data-testid` attributes.
   - Start with accessible selectors and a very small number of new test IDs on unstable repeated controls only.

### 3.3 What the proposal is missing

1. A repo-owned execution contract.
   - Raw `cypress run` is not enough.
   - This repo needs one command surface that boots a site, prepares data, runs browser tests, and is compatible with current CI policy.

2. Separation between product APIs and test orchestration.
   - This is especially important in a multi-tenant system with explicit API governance.

3. A phased CI rollout.
   - The current staging policy already distinguishes GitHub-hosted PR work from heavier `ci-staging` style automation.
   - Browser E2E should follow that same staging discipline.

4. Surface-specific journey selection.
   - `/admissions` has unusually high browser value because it is workflow-heavy and applicant-stateful.
   - `/hub` needs at least one role-scoped bootstrap test, but not a huge auth-only pack.

## 4. Proposed direction

Use Cypress, but make it a narrow browser-integration layer rather than a second API-test suite.

Phase 1 should answer one question only:

> Can the repo boot the real site, seed deterministic scenarios, authenticate through real session mechanics, and complete a handful of critical browser journeys across `/hub` and `/admissions`?

If the answer becomes stable, expand later. If not, stop before adding more specs.

## 5. Proposed structure

```text
ifitwala_ed/
  cypress/
    e2e/
      admissions/
      hub/
    fixtures/
    support/
      commands.ts
      e2e.ts
      auth.ts
      scenarios.ts
  cypress.config.ts
  ifitwala_ed/
    tests/
      e2e/
        __init__.py
        scenarios.py
        reset.py
```

Rules:

1. Keep browser specs at repo root.
2. Keep scenario creation/reset logic in Python test modules under `ifitwala_ed/tests/e2e/`.
3. Do not place seed/reset orchestration in `ifitwala_ed/api/`.

## 6. Proposed first-phase journeys

Do not start with 8 tests. Start with 6 stable browser journeys.

### 6.1 `/hub`

1. `hub-staff-home.cy.ts`
   - Login as a seeded staff user.
   - Visit `/hub/staff`.
   - Assert shell bootstrap succeeds and key staff-home content renders.

2. `hub-guardian-scope.cy.ts`
   - Login as a seeded guardian.
   - Visit `/hub/guardian`.
   - Assert only linked student context is visible.
   - Attempt an unrelated student route or parameter and assert the user is redirected or blocked by the real server/client path.

3. `hub-route-resolution.cy.ts`
   - Cover one end-to-end redirect journey only.
   - Example: guest hitting `/hub/student/activities` goes to login, then the correct portal route resolves after login.

### 6.2 `/admissions`

4. `admissions-session-switch.cy.ts`
   - Seed a family-workspace scenario with more than one linked applicant.
   - Assert the admissions shell loads and applicant switching preserves the route/query contract.

5. `admissions-profile-save.cy.ts`
   - Edit a small profile field set.
   - Save through the real UI.
   - Assert success feedback and persisted reload state.

6. `admissions-submit.cy.ts`
   - Use two deterministic scenarios:
     - incomplete applicant: submit stays blocked with actionable guidance
     - ready applicant: submit succeeds and post-submit state is visible

Why this pack:

1. It spends the browser budget on real client-server integration.
2. It exercises both browser apps.
3. It validates role/scope behavior without recreating the full backend permission matrix in Cypress.

## 7. Scenario strategy

Deterministic scenario setup is the make-or-break decision.

### 7.1 Principles

1. Use synthetic seeded data only.
2. Tie scenarios directly to named journeys.
3. Reuse existing test factories and helper patterns where possible.
4. Reset by recreating or clearing the dedicated test site, not by trying to surgically clean arbitrary shared state.

### 7.2 Scenario catalog

Start with a small fixed catalog:

1. `hub_staff_basic`
2. `hub_guardian_one_child`
3. `hub_guest_redirect`
4. `admissions_single_applicant_draft`
5. `admissions_family_workspace`
6. `admissions_ready_to_submit`

### 7.3 Execution model

Preferred:

1. A Python scenario runner under `ifitwala_ed/tests/e2e/scenarios.py`
2. Invoked via bench or repo CLI before each spec pack
3. Operates only against a dedicated test site

Avoid:

1. Whitelisted public seed/reset endpoints
2. UI-driven record creation as primary setup
3. Reusing a human developer site with unknown state

## 8. Authentication strategy

Preferred order:

1. Use the real login mechanism once per role/scenario and cache it with Cypress session support.
2. If needed, use a direct request into the canonical login flow rather than a new auth helper endpoint.
3. Reuse the real `/logout` path for logout assertions.

Avoid:

1. Logging in through the full UI on every single test from scratch
2. Introducing a separate test-only authentication API into product code

## 9. Selector strategy

Default selector order:

1. visible text
2. labels
3. roles or stable semantic structure
4. `data-testid` only where the UI is repeated, dynamic, or ambiguous

Add `data-testid` only for:

1. shell roots
2. family-applicant switcher block
3. primary save CTA on admissions forms
4. submit CTA and submit state block
5. explicit access-denied or blocked-action shells where text may vary

Avoid:

1. CSS-class selectors
2. large selector registries before the first pack proves stable

## 10. Execution contract

Browser E2E should become a repo-owned command, not a loose manual recipe.

Proposed eventual command surface:

1. `./scripts/codex e2e --site <site> --base-url <url> --pack smoke`
2. `./scripts/codex e2e --site <site> --base-url <url> --pack critical`

Responsibilities of that command:

1. verify required local tooling
2. ensure assets are built or available
3. run deterministic scenario setup
4. launch Cypress with the requested pack
5. fail clearly on site/bootstrap/data errors

This keeps browser E2E aligned with the existing `codex` local workflow instead of creating a disconnected second workflow.

## 11. CI rollout proposal

### 11.1 Phase 1

Local/manual only.

Goal:

1. prove scenario determinism
2. prove developer workflow
3. measure runtime and flake rate

### 11.2 Phase 2

Nightly or manual-dispatch on dedicated non-production infrastructure.

Goal:

1. run against a clean seeded site
2. collect flake and runtime data
3. keep it non-blocking while the suite hardens

This matches the current testing docs more closely than putting browser E2E straight into PR gating.

### 11.3 Phase 3

Promote only a very small smoke subset to required PR status, and only after stability is proven.

Promotion gate:

1. runtime remains acceptably short
2. several consecutive green runs on dedicated infrastructure
3. failures are clearly actionable rather than environment noise

Keep the broader pack nightly.

## 12. Non-goals for phase 1

Do not use browser E2E for:

1. exhaustive permission matrices
2. every field validation permutation
3. every portal page
4. upload/download/file-governance depth
5. analytics correctness
6. concurrency/load behavior

Those belong in backend tests, API contract tests, SPA unit tests, or dedicated performance work.

## 13. Acceptance criteria for adoption

The proposal is successful when all of these are true:

1. Browser E2E exists as a repo-level test layer, not a hidden SPA-only add-on.
2. The first pack covers both `/hub` and `/admissions`.
3. Scenario setup is deterministic and test-only.
4. No new public business API is added solely to seed or reset browser tests.
5. Auth uses canonical session behavior.
6. CI rollout is phased, not immediately merge-blocking.
7. The suite stays intentionally small until it proves stable.

## 14. Recommendation

Approve browser E2E in principle, but do not approve the supplied proposal unchanged.

Approve a narrower Phase 1:

1. Cypress at repo root
2. Python-driven deterministic scenario seeding under `ifitwala_ed/tests/e2e/`
3. 6 initial journeys split across `/hub` and `/admissions`
4. repo-owned execution through `scripts/codex`
5. nightly/manual first, PR-gated later if stability is earned

If implementation is approved later, the canonical follow-up docs to update are:

1. `ifitwala_ed/docs/testing/01_test_strategy.md`
2. `ifitwala_ed/docs/testing/02_ci_policy.md`
3. `ifitwala_ed/docs/testing/04_developer_cli.md`

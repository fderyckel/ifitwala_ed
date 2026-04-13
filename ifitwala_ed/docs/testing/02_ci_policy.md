<!-- ifitwala_ed/docs/testing/02_ci_policy.md -->
# Ifitwala_Ed CI Policy

## 1. Required PR checks

All PRs targeting `main` must pass:
1. `backend-smoke`
2. `backend-domain`
3. `lint`
4. `desk-build`
5. `spa-typecheck-build`

## 2. Job intent

1. `backend-smoke`
- Fast confidence suite for critical backend invariants.
- Includes merge-gating portal routing, workspace sidebar contract integrity, file-access, analytics-permission, self-enrollment, staff policy signature, admissions portal, and focus workflow contract tests.

2. `backend-domain`
- Runs module-level backend tests scoped to changed Python domains.
- Falls back to a deterministic smoke module when no Python changes are detected.

3. `lint`
- Runs Ruff.
- Runs SPA contract guardrails (`scripts/contracts_guardrails.sh`).
- Publishes backend testing baseline metrics (`scripts/test_metrics.sh`).

4. `desk-build`
- Verifies root Desk asset build.

5. `spa-typecheck-build`
- Verifies SPA type-check and unit tests.

## 2.2 Browser E2E rollout

1. Browser E2E is now implemented as a repo-root Cypress layer for deterministic `/hub` and `/admissions` journeys.
2. It is not a required PR check yet.
3. The gating sequence remains:
   - stabilize locally with `./scripts/codex e2e`
   - prove repeatability on dedicated infrastructure
   - only then consider PR-gating a small smoke pack
4. Until that rollout is complete, browser E2E remains a local/manual and future-nightly concern rather than a merge requirement.

## 2.1 Framework baseline

CI benches are initialized against **Frappe `version-16`**.
CI bootstrap must also fetch repo-required companion apps before site creation.
Temporary exception: CI currently fetches `ifitwala_drive` from `main` because that dependency repo does not yet publish a `version-16` branch.

## 3. Nightly policy

Nightly workflow (`.github/workflows/nightly.yml`) is currently manual-dispatch only while the self-hosted GCE runner is not installed.
When the runner is restored, the scheduled trigger can be re-enabled.

Nightly jobs:
1. `nightly-backend-full`
2. `nightly-api-regression`
3. `nightly-spa-smoke`
4. Future: browser E2E smoke/critical packs once the dedicated runner path is restored and stable.

Nightly smoke/unit frontend step is intentionally non-blocking to keep signal while the SPA unit harness scales.

## 4. Review governance

1. `CODEOWNERS` defines domain ownership expectations.
2. PR template requires explicit invariant mapping and test mapping.
3. Merge is blocked when required checks fail.

## 5. Flaky test handling

1. Mark flaky behavior with issue/label (`ci-flaky`).
2. Fix or quarantine quickly.
3. Never silently ignore failing critical invariant tests.

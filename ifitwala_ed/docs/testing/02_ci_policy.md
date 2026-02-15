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
- Verifies SPA type-check and build.

## 3. Nightly policy

Nightly workflow (`.github/workflows/nightly.yml`) runs on self-hosted GCE runner labels.

Nightly jobs:
1. `nightly-backend-full`
2. `nightly-api-regression`
3. `nightly-spa-smoke`

Nightly smoke/unit frontend step is intentionally non-blocking to keep signal while the SPA unit harness scales.

## 4. Review governance

1. `CODEOWNERS` defines domain ownership expectations.
2. PR template requires explicit invariant mapping and test mapping.
3. Merge is blocked when required checks fail.

## 5. Flaky test handling

1. Mark flaky behavior with issue/label (`ci-flaky`).
2. Fix or quarantine quickly.
3. Never silently ignore failing critical invariant tests.

<!-- ifitwala_ed/docs/testing/03_staging_data_policy.md -->
# Ifitwala_Ed Staging & Test Data Policy (GCE)

## 1. Topology

Production and non-production must be isolated.

Required non-production design:
1. Dedicated GCE VM for testing/staging.
2. Separate bench from production bench.
3. Two non-production sites:
- `staging`: manual QA/UAT.
- `ci-staging`: destructive/automated nightly runs.

## 2. Data model (mixed)

1. Default: deterministic synthetic seed data.
2. Optional realism: scheduled anonymized production snapshot import to `staging` only.
3. Never import unsanitized production data into staging or CI sites.

## 3. Safety controls

1. No production secrets in non-production site configs.
2. Non-production email/SMS outputs must be disabled or redirected to sink inboxes.
3. Payment and third-party integrations must use sandbox keys only.
4. Access restricted via network controls (VPN/IP allowlist) and role-based access.

## 4. Operational runbook (minimum)

1. Seed command for deterministic baseline.
2. Reset command for `ci-staging` before nightly runs.
3. Snapshot anonymization + restore procedure.
4. Backup/restore test for non-production bench/site.

## 5. GitHub integration policy

1. PR checks run on GitHub-hosted runners.
2. Heavy nightly suites run on self-hosted GCE runner labels.
3. Any staging deployment automation must run only from protected branch/tag refs.

## 6. Auditability

Every staging data refresh must log:
1. source dataset identifier,
2. anonymization job version,
3. execution timestamp,
4. operator/automation identity,
5. success/failure state.

# Testing Documentation Index

Status: Canonical index
Code refs: None
Test refs: None

`ifitwala_ed/docs/testing/` is the canonical home for testing strategy, CI gates, non-production test-data policy, and repo-local developer test workflows.

Read in this order:

- `01_test_strategy.md`
  canonical test strategy and invariant priorities
- `deterministic_test_suite.md`
  app-owned deterministic DB test harness contract
- `02_ci_policy.md`
  current required checks and CI intent
- `03_staging_data_policy.md`
  staging and non-production data rules
- `04_developer_cli.md`
  repo-local CLI workflow for validation

Supporting non-canonical note:

- `05_browser_e2e_proposal.md`
  implemented phase-1 local/manual E2E note; it does not override the strategy or CI policy
- `06_eca_activity_manual_qa_checklist.md`
  manual physical QA checklist for the current ECA activity workflow; it does not override the activity-booking architecture or test strategy

Audit artifact:

- `security_audit_comprehensive.md`
  point-in-time audit output, not a canonical runtime contract

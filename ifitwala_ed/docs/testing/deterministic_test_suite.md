# Deterministic Test Suite Contract

Status: Active scaffold
Code refs: `ifitwala_ed/tests/base.py`, `ifitwala_ed/tests/bootstrap.py`, `ifitwala_ed/tests/factories/`
Test refs: `ifitwala_ed/tests/test_deterministic_suite.py`

This document defines the app-owned deterministic test layer for DB-backed `ifitwala_ed` tests.

The Frappe test runner may initialize the test site and database connection, but Ifitwala_Ed owns its own domain prerequisites. Tests must not depend on hidden recursive `test_records.json` loading, ambient site records, or cross-app setup side effects.

## 1. Base Class

Use `IfitwalaEdTestSuite` for DB-backed app tests.

Keep `unittest.TestCase` for pure unit tests that do not need a Frappe database.

Existing tests that import `IfitwalaFrappeTestCase` continue to work through a compatibility class, but new DB-backed tests should inherit `IfitwalaEdTestSuite` directly.

Responsibilities:

- initialize or reuse the Frappe test context
- ensure app-owned bootstrap reference data exists
- commit bootstrap reference data once
- roll back scenario data after each test
- reset volatile cross-test flags
- provide small shared helpers such as `set_user`

## 2. Bootstrap Data

`IfitwalaBootstrapTestData` owns persistent reference data only.

Current scaffold records:

- `_Test Ifitwala Organization`
- `_Test Ifitwala School`
- `_Test Ifitwala Child School`
- `_Test Ifitwala AY`
- `_Test Ifitwala Term`
- `_Test Ifitwala Grade Scale`

Bootstrap data must be:

- schema-verified before implementation
- deterministic and idempotent
- created with explicit duplicate keys
- committed once after creation
- small enough to be understood from `ifitwala_ed/tests/bootstrap.py`

Bootstrap data must not include scenario records such as applicants, enrollments, submissions, communications, governed files, policy acknowledgements, billing documents, or reporting results.

## 3. Scenario Data

Scenario data belongs inside the test case or a domain factory under `ifitwala_ed/tests/factories/`.

Scenario factories must:

- create the smallest contract-valid state for the invariant under test
- require explicit organization, school, academic year, or user context when the domain needs it
- avoid hidden commits
- avoid broad cleanup code that compensates for leaked state
- use deterministic names only when the test intentionally checks rollback pollution

## 4. Forbidden Patterns

Do not add new DB-backed tests that rely on:

- hidden `test_records.json` dependency loading
- records that merely happen to exist on a developer site
- `frappe.db.commit()` inside test cases
- `frappe.db.truncate()` as a cleanup shortcut
- global `frappe.flags` mutation without local restore
- factories that silently create unrelated heavy domain setup

Any exception must be documented in the test and justified by the invariant under test.

## 5. Migration Policy

Do not migrate the entire suite in one change.

Migration order:

1. new DB-backed tests use `IfitwalaEdTestSuite`
2. backend-smoke modules migrate first
3. high-risk domains migrate next: enrollment, admissions, governance, assessment, files, website routing
4. `IntegrationTestCase` remains opt-in only when a test intentionally uses Frappe's framework-owned test-record behavior

## 6. CI Determinism Gate

The canary module is:

```bash
bench --site test_site run-tests --app ifitwala_ed --module ifitwala_ed.tests.test_deterministic_suite
bench --site test_site run-tests --app ifitwala_ed --module ifitwala_ed.tests.test_deterministic_suite
```

The second run must pass on the same site. A second-run failure means scenario data leaked or a test committed state that should have rolled back.

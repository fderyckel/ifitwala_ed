# Admission API Maintainability Plan

Status: Active proposal with completed portal-test split
Code refs: `ifitwala_ed/admission/api/`, `ifitwala_ed/api/`
Test refs: `ifitwala_ed/admission/api/test_*.py`
Last updated: 2026-05-30

This proposal tracks admissions API and admissions-test files that are over 1000 lines and should be split only after their public paths, permissions, tenant scope, idempotency, and governed-file contracts are preserved.

## Current Large Files

- `ifitwala_ed/admission/api/recommendation_intake.py` (~2400 lines)
- `ifitwala_ed/admission/api/inquiry.py` (~1200 lines)
- `ifitwala_ed/admission/doctype/applicant_interview/test_applicant_interview.py` (~1700 lines)
- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py` (~2200 lines)

## Completed Splits

The former `ifitwala_ed/admission/api/test_admissions_portal.py` suite is split into focused files:

- `ifitwala_ed/admission/api/test_portal_access_contracts.py`
- `ifitwala_ed/admission/api/test_portal_invites.py`
- `ifitwala_ed/admission/api/test_portal_submission_snapshot.py`
- `ifitwala_ed/admission/api/test_portal_enrollment.py`
- `ifitwala_ed/admission/api/test_portal_policies.py`
- `ifitwala_ed/admission/api/test_portal_profile.py`
- `ifitwala_ed/admission/api/test_portal_profile_images.py`
- `ifitwala_ed/admission/api/test_portal_health.py`
- `ifitwala_ed/admission/api/portal_test_helpers.py`
- `ifitwala_ed/api/test_admissions_portal_facade.py`

## Recommended Sequence

1. Keep public RPC facades under `ifitwala_ed/api/`.
2. Move implementation tests beside admission implementation modules.
3. Split large implementation files by responsibility.
4. Split large test files by workflow, sharing only explicit fixture helpers.
5. Add small root facade tests only for delegation, payload binding, `allow_guest`, and compatibility exports.

## Split Proposal

`recommendation_intake.py` should become a package with concrete implementation modules:

- `staff_requests.py`: create, list, resend, revoke, status helpers
- `guest_intake.py`: token payload, OTP send/verify, recommendation submission
- `review_payload.py`: reviewer payload assembly
- `document_integration.py`: Applicant Document and Applicant Document Item handoff
- `access.py`: token/session/permission guards
- `dto.py`: response shaping and serializers

`inquiry.py` should split into:

- `dashboard.py`: admissions inquiry dashboard aggregation
- `zero_lost.py`: zero-lost-lead views and row DTOs
- `scope.py`: organization/school/user-scope filters
- `dates.py`: academic-year and preset-window resolution
- `link_queries.py`: Desk link query endpoints
- `lookups.py`: inquiry types, sources, organizations, schools, acknowledgement context

The admissions portal implementation test suite should stay split by workflow:

- `test_portal_access_contracts.py`
- `test_portal_invites.py`
- `test_portal_submission_snapshot.py`
- `test_portal_enrollment.py`
- `test_portal_policies.py`
- `test_portal_profile.py`
- `test_portal_profile_images.py`
- `test_portal_health.py`
- `portal_test_helpers.py` for explicit shared factories only

The DocType tests should split by product behavior:

- applicant interview scheduling, workspace access, feedback, and recommendation-review payloads
- student applicant academic period validation, document readiness/review, promotion, identity upgrade, and enrollment-plan hydration

## Risk Controls

- Do not rename public `ifitwala_ed.api.*` method strings during these splits.
- Do not add package-level `__init__.py` re-export tricks; import concrete implementation modules.
- Preserve guest access and `allow_guest` only on root public facades.
- Keep governed-file URL assembly and Drive handoffs in the existing authority path.
- Move or split tests without weakening their permission, tenant-scope, idempotency, and private-media assertions.

# Staff Policy Library Contract

## Purpose
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/policy_communication.py`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

The Staff Policy Library provides a staff-facing page where users can read active policies in scope, filter by organization/school/employee group context, and open a full policy overlay with change and history details.

## Scope And Access
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/governance/policy_scope_utils.py`, `ifitwala_ed/api/portal.py`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_analytics_permissions.py`

1. Allowed roles are `Employee`, `Academic Staff`, and policy-signature analytics roles.
2. Policy visibility remains server-owned through policy scope rules.
3. Non-manager staff are scoped to active employee organization context.
4. Manager roles keep broader organization filter scope.

## Filter Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Filters are canonical POST payload fields: `organization`, `school`, `employee_group`.
2. Filters are populated by server options and normalized by returned effective filters.
3. No client-side scope expansion is allowed.

## Signature Status Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. There is no schema field for policy signature requirement.
2. Signature requirement is derived from staff-signature workflow artifacts at policy level:
   - campaign ToDo marker (`[policy_signature]`) and/or
   - existing staff `Policy Acknowledgement` rows.
3. Status semantics:
   - `informational`: no signature requirement for this policy.
   - `signed`: current user acknowledged current active version.
   - `new_version`: user acknowledged an older version of this policy but not current active version.
   - `pending`: signature-required policy with no acknowledgement by current user.

## Overlay Contract
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/ui-spa/src/types/contracts/policy_communication/get_policy_inform_payload.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Policy details open using existing overlay stack type `staff-policy-inform`.
2. Overlay payload includes:
   - full policy text,
   - diff/change summary stats,
   - version history rows,
   - derived signature state.
3. No second modal system is introduced.

## Contract Matrix
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_analytics_permissions.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

| Layer | Contract | Status |
|---|---|---|
| Schema / DocType | Reuse `Institutional Policy`, `Policy Version`, `Policy Acknowledgement`, `Employee` | Implemented |
| Controller / workflow logic | Signature-required status is derived from existing workflow artifacts, not new schema | Implemented |
| API endpoints | `get_staff_policy_library`, `get_policy_inform_payload` | Implemented |
| SPA / UI surfaces | `/staff/policies` page + existing `staff-policy-inform` overlay | Implemented |
| Reports / dashboards | Staff Home link integration with capability gate | Implemented |
| Scheduler / background jobs | None | Implemented |
| Tests | Backend and SPA regression coverage for status and overlay flow | Implemented |

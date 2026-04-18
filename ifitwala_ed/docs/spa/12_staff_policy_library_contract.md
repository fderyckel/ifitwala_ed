# Policy Library Contract

## Purpose
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/policy_communication.py`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

The Policy Library is the canonical staff-workspace browsing surface for active institutional policies in scope. It replaces the old “staff policies” semantics with one organization-scoped library page that still preserves staff-specific acknowledgement state when the selected audience is `Staff`.

## Scope And Access
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/governance/policy_scope_utils.py`, `ifitwala_ed/api/portal.py`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_analytics_permissions.py`

1. Allowed roles remain `Employee`, `Academic Staff`, and policy-signature analytics roles.
2. Policy visibility remains server-owned through organization/school scope helpers.
3. Non-manager staff keep the narrower staff-library experience:
   - audience locked to `Staff`
   - school normalized to the active employee school when available
4. Manager roles (`Academic Admin`, `HR Manager`, `Organization Admin`, `System Manager`, `Administrator`) may browse policy rows across supported audiences inside their organization scope.

## Route And URL Contract
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
Test refs: None

1. Canonical route is `/staff/policies` in the staff SPA shell.
2. `/staff/policy-library` redirects to the canonical route.
3. Staff Home labels this surface as `Policy Library`.

## Filter Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Canonical POST payload fields are:
   - `organization`
   - `school`
   - `audience`
2. Filters are server-populated and server-normalized.
3. For manager roles:
   - `school` may remain blank to represent all schools in selected organization scope
   - `audience` options are `All`, `Staff`, `Guardian`, `Student`
4. For non-manager staff:
   - `audience` is locked to `Staff`
   - `school` falls back to the active employee school when available
5. No client-side scope expansion is allowed.

## Row Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/types/contracts/policy_signature/get_staff_policy_library.ts`
Test refs: `ifitwala_ed/api/test_policy_signature.py`

Each row represents the active nearest policy version for one `policy_key` in the selected organization/school context and includes:

1. policy identity and version metadata
2. policy scope (`policy_organization`, optional `policy_school`)
3. `applies_to_tokens` for supported library audiences:
   - `Staff`
   - `Guardian`
   - `Student`
4. Staff-only acknowledgement state fields when the selected audience is `Staff`:
   - `signature_required`
   - `acknowledgement_status`
   - `acknowledged_at`

The library does not duplicate one row per audience. Multi-audience policies appear once with audience chips.

## Staff Status Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Staff acknowledgement state is shown only when the effective audience filter is `Staff`.
2. There is still no schema field for staff signature requirement.
3. Signature requirement is derived from staff-signature workflow artifacts:
   - campaign ToDo marker (`[policy_signature]`)
   - existing staff `Policy Acknowledgement` rows
4. Status semantics remain:
   - `informational`
   - `signed`
   - `new_version`
   - `pending`
5. Guardian and student library browsing must not reuse staff-status labels for non-staff rows.

## Overlay Contract
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/ui-spa/src/types/contracts/policy_communication/get_policy_inform_payload.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Policy details continue to open through overlay type `staff-policy-inform`.
2. Overlay payload includes:
   - full policy text
   - diff/change summary stats
   - version history rows
   - audience tokens
   - staff signature state when applicable
3. Overlay presentation must stay neutral for guardian/student policies and must not label them “informational” merely because the current user has no staff signature state on them.
4. When opened from staff archive communications with `org_communication`, the payload endpoint may still use the existing communication-visibility fallback after verifying organization/school compatibility.

## Analytics Link Contract
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/ui-spa/src/lib/services/staff/staffHomeService.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

1. Policy cards expose `Open acknowledgement tracking` only for users with capability `analytics_policy_signatures`.
2. Navigation goes to route `staff-policy-signature-analytics`.
3. Navigation query pre-fills only the library scope filters that are meaningful to analytics:
   - `policy_version`
   - `organization`
   - `school`
4. `Employee Group` remains an analytics-only filter and is no longer a Policy Library filter.

## Policy Signature Analytics Surface
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyCampaignOverlay.vue`, `ifitwala_ed/ui-spa/src/overlays/staff/FamilyPolicyCampaignOverlay.vue`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_policy_family_campaign.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/PolicySignatureAnalytics.test.ts`

1. The analytics page still shows acknowledgement status across supported audiences on the selected policy version:
   - `Staff`
   - `Guardian`
   - `Student`
2. Staff campaign launch remains staff-task only and continues to create internal signature `ToDo` rows for eligible employees.
3. A separate family campaign overlay may publish student and guardian portal communications for the selected organization/school scope.
4. Family campaign publication creates one `Org Communication` per selected family audience and deep-links to the exact portal policy page with `policy_version`.
5. Guardian and student acknowledgement truth remains portal `Policy Acknowledgement` evidence. Family campaigns do not create tasks or a second compliance source.
6. The dashboard bootstrap remains a bounded summary read and large audience browsing still uses the server-backed audience register.

## Contract Matrix
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/policy_communication.py`, `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_policy_signature.py`, `ifitwala_ed/api/test_analytics_permissions.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts`

| Layer | Contract | Status |
|---|---|---|
| Schema / DocType | Reuse `Institutional Policy`, `Policy Version`, `Policy Acknowledgement`, `Employee` | Implemented |
| Controller / workflow logic | Cross-audience browsing remains library-first; actionable acknowledgement flows stay in Focus, Guardian Portal, Student Hub, and Admissions, with family campaigns publishing portal notices only | Implemented |
| API endpoints | `get_policy_library`, `get_policy_inform_payload`, `get_staff_policy_signature_dashboard`, `get_staff_policy_signature_audience_rows`, `get_family_policy_campaign_options`, `publish_family_policy_campaign` | Implemented |
| SPA / UI surfaces | `/staff/policies`, `/staff/analytics/policy-signatures`, existing policy-inform overlay, separate staff and family campaign overlays | Implemented |
| Reports / dashboards | Staff Home link integration with capability gate plus on-demand audience register for high-volume policy analytics | Implemented |
| Scheduler / background jobs | None | Implemented |
| Tests | Backend and SPA regression coverage for cross-audience browsing and staff-mode status flow | Implemented |

# Enrolled Student Durable Policy Acknowledgement Contract

## Purpose And Scope
Status: Active
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

This document is the canonical contract for durable, versioned policy acknowledgement after a student is enrolled.

Rules:

1. This feature covers handbook-style and versioned institutional policy acknowledgement only.
2. This feature reuses `Institutional Policy`, `Policy Version`, and `Policy Acknowledgement`; it does not add a new request/decision model.
3. This feature is portal-first:
   - `/hub/guardian` for guardian obligations
   - `/hub/student` for student obligations
4. One-off permission slips and mutable consents remain governed by `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md` and must not be hidden inside the durable policy flow.
5. The first implementation slice must improve product discoverability before adding new policy authoring complexity.

## Current Reality
Status: Implemented
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

Current state:

1. Guardian durable acknowledgement is implemented on `/guardian/policies`.
2. Guardian policy visibility is filtered from linked students with signer authority via `Student Guardian.can_consent`, and that enrolled signer flag must be granted only to primary guardians.
3. Guardian acknowledgement evidence is stored as immutable `Policy Acknowledgement` rows on guardian self-context.
4. Student durable acknowledgement is implemented on `/student/policies` with its own named portal APIs.
5. Guardian Home and Student Home already surface pending policy work as attention cards and counts.
6. Staff analytics can publish family policy campaigns that create portal communications for selected `Guardian` and `Student` audiences without creating staff tasks.
7. Family campaign links deep-link into `/hub/guardian/policies` and `/hub/student/policies` with `policy_version` focus so families land on the exact policy card they still need to review.

## Current Runtime Constraints
Status: Active
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`

Runtime guardrails:

1. Family campaign publication must stay aligned with durable acknowledgement truth and must not create a second request/decision layer.
2. Policies that apply to both `Student` and `Guardian` still need clear dual-obligation reporting and communication copy.
3. Family reminders remain a repeat publication workflow around unresolved durable obligations, not a mutable consent scheduler.
4. Campaign copy and portal deep-links must keep families in the acknowledgement flow they already use instead of redirecting them to Desk-style review surfaces.

## Reuse Model
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue`, `ifitwala_ed/ui-spa/src/components/focus/StaffPolicyAcknowledgeAction.vue`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_focus_policy_signature.py`, `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`

Rules:

1. Reuse the admissions e-sign flow pattern for clause checks, typed signature, attestation, and blocked-submit feedback.
2. Reuse the guardian policy query/status shape where possible for the student portal API to keep portal behavior parallel.
3. Do not reuse the staff Focus/ToDo campaign workflow directly inside student or guardian portals.
4. Staff policy diff/review patterns may be reused later for richer review UX, but they are not required for the first enrolled-student portal slice.
5. The first slice should prefer a shared portal-facing signature component over duplicating guardian and student form logic.

## Audience And Obligation Contract
Status: Implemented
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/policy_utils.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`

Rules:

1. `Applies To = Guardian` creates a guardian obligation only and surfaces on `/hub/guardian`.
2. `Applies To = Student` creates a student obligation only and surfaces on `/hub/student`.
3. `Applies To = Student + Guardian` creates two distinct obligations, one per audience, with separate immutable evidence rows.
4. The first slice does not support an implicit “student or guardian may satisfy the same durable acknowledgement” rule.
5. If the product later needs “either/or” completion, that must be documented as a separate signer-rule contract before implementation.

## UX Contract
Status: Implemented
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

Rules:

1. Pending durable policy work must surface on Home before the user has to navigate to a library page.
2. Each portal keeps one dedicated durable-policy page:
   - `/guardian/policies`
   - `/student/policies`
3. Home cards must give a direct next action and a pending count, not only a generic link.
4. The dedicated page must show current status, policy title, version label, plain-language summary, and the full policy text without requiring a second navigation.
5. Blocked actions must explain the exact issue:
   - typed name mismatch
   - missing clause selection
   - missing attestation
   - no signer authority
6. Guardian and student durable policy pages should feel like sibling surfaces, not unrelated implementations.

## Permission And Visibility Contract
Status: Implemented
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/governance/policy_utils.py`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py`

Rules:

1. Guardian durable policy visibility must stay server-owned and continue to require signer authority from `Student Guardian.can_consent`, with primary-guardian status as the upstream business rule for that signer flag.
2. Student durable policy visibility must be server-owned and limited to the current student self-context.
3. Guardian portals must not expose actionable student-only acknowledgements in the first enrolled-student slice.
4. Student portals must not expose guardian-only acknowledgements.
5. A user who can view a student in another workflow but lacks signing authority must not receive a policy action for that child.

## API And Data Contract
Status: Implemented
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts`, `ifitwala_ed/ui-spa/src/types/contracts/student/get_student_policy_overview.ts`, `ifitwala_ed/ui-spa/src/types/contracts/policy_signature/get_family_policy_campaign_options.ts`, `ifitwala_ed/ui-spa/src/types/contracts/policy_signature/publish_family_policy_campaign.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/api/test_policy_family_campaign.py`

Rules:

1. Durable acknowledgement remains an append-only `Policy Acknowledgement` insert with typed-signature evidence.
2. Student durable acknowledgement uses named student APIs instead of generic CRUD:
   - `get_student_policy_overview`
   - `acknowledge_student_policy`
3. Guardian durable acknowledgement continues to use separate guardian APIs:
   - `get_guardian_policy_overview`
   - `acknowledge_guardian_policy`
4. Family campaign publication for durable policies is a staff-side notification workflow only:
   - `get_family_policy_campaign_options`
   - `publish_family_policy_campaign`
5. Family campaign publication reuses `Org Communication` for portal notices and must not create a new durable policy evidence model.

## Staff Family Campaign Contract
Status: Implemented
Code refs: `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue`, `ifitwala_ed/ui-spa/src/overlays/staff/FamilyPolicyCampaignOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`
Test refs: `ifitwala_ed/api/test_policy_family_campaign.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/PolicySignatureAnalytics.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

Rules:

1. Family campaigns are allowed only for active `Policy Version` rows that apply to `Guardian`, `Student`, or both.
2. Publication scope is staff-selected organization/school scope and remains server-owned.
3. Family campaigns create one `Org Communication` per selected family audience so copy and portal CTA stay audience-specific.
4. Organization-wide family publication fans out to school-scope audience rows for every school in the selected organization tree.
5. School-scoped family publication uses one school-scope audience row with descendants enabled for the selected school branch.
6. Campaign CTA must deep-link to the exact policy page with `policy_version` query focus:
   - `/hub/guardian/policies?policy_version=...`
   - `/hub/student/policies?policy_version=...`
7. Publishing a family campaign does not create `ToDo` rows, does not snapshot compliance targets, and does not replace `Policy Acknowledgement` as evidence.

## Home Surface And Concurrency Contract
Status: Implemented
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`

Rules:

1. Home surfaces must receive pending durable policy counts through bounded bootstrap data, not through client-side request waterfalls.
2. Home attention cards must be derived server-side from current unresolved durable policy obligations.
3. The portal must not add polling loops to refresh durable acknowledgement status.
4. Cache keys, if introduced, must remain audience- and scope-specific.
5. The home integration must stay lightweight enough for hot-path portal loads.

## Out Of Scope
Status: Active
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`, `ifitwala_ed/docs/files_and_policies/policy_05_phase2a_guardian_first_implementation_plan.md`
Test refs: None

Not in this contract:

1. One-off permission slips.
2. Mutable consent grant, decline, withdrawal, and renewal.
3. Staff campaign authoring changes beyond what is needed to publish versioned durable policies already in scope.
4. A new schema field for enrolled-student signer rules.
5. Student co-sign for mutable consent or event permission flows.

## Implementation Reality
Status: Implemented
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

Implemented now:

1. Student durable policy API endpoints and contract types are live.
2. `/student/policies` and student sidebar navigation are live.
3. Guardian and Student Home both surface pending durable policy counts and action links through bounded bootstrap payloads.
4. Guardian and student policy pages support deep-link focus with `policy_version`.
5. Backend and SPA regression coverage exist for both portal audiences.

Still intentionally separate:

1. Durable acknowledgement continues to use audience-specific pages and APIs rather than one merged portal surface.
2. Mutable family consent remains outside this contract.

## Risks
Status: Active
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Risks:

1. If `Student + Guardian` is treated as one shared obligation without an explicit contract, compliance reporting will become ambiguous.
2. If home cards are implemented with extra client requests, portal hot paths will regress.
3. If student and guardian policy surfaces diverge too far, policy UX will become harder to teach and support.
4. If guardian pages start exposing student-only obligations, the audience model on `Institutional Policy` will lose meaning.
5. If family campaign publication starts being treated as the obligation itself, reporting will drift away from durable acknowledgement truth.

## Contract Matrix
Status: Implemented
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/student_policy.py`, `ifitwala_ed/api/policy_signature.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
Test refs: `ifitwala_ed/api/test_guardian_home.py`, `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/api/test_student_policy.py`, `ifitwala_ed/api/test_policy_family_campaign.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentPolicies.test.ts`

| Layer | Current owner | Current enrolled-student durable acknowledgement runtime | Status |
|---|---|---|---|
| Schema / DocType | `Institutional Policy`, `Policy Version`, `Policy Acknowledgement` | Reuses the existing versioned acknowledgement model; no extra durable-policy DocTypes are required in the current slice | Implemented |
| Controller / workflow logic | `policy_acknowledgement.py`, `guardian_policy.py`, `student_policy.py`, `policy_signature.py` | Guardian and student portal acknowledgement flows stay distinct, while staff family campaigns publish portal notices only | Implemented |
| API endpoints | `get_guardian_policy_overview`, `acknowledge_guardian_policy`, `get_student_policy_overview`, `acknowledge_student_policy`, `get_family_policy_campaign_options`, `publish_family_policy_campaign` | Named durable policy APIs plus staff-side family campaign publication | Implemented |
| SPA / UI surfaces | Guardian and student durable policy pages plus home attention cards | Staff analytics can publish family campaigns and portal pages honor `policy_version` deep-link focus | Implemented |
| Reports / dashboards | Existing durable acknowledgement evidence plus staff policy analytics | Portal counts and analytics remain version-acknowledgement focused; family campaign publication is notification-only | Implemented |
| Scheduler / background jobs | None | None required for the current durable acknowledgement scope | Implemented |
| Tests | Guardian and student backend coverage, portal coverage, and home-surface regressions | Durable acknowledgement, home summaries, and family campaign publication are covered in backend and SPA tests | Implemented |

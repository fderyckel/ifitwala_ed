# Enrolled Student Durable Policy Acknowledgement Contract

## Purpose And Scope
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`

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
Status: Partial
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`

Current state:

1. Guardian durable acknowledgement is implemented on `/guardian/policies`.
2. Guardian policy visibility is filtered from linked students with signer authority via `Student Guardian.can_consent`.
3. Guardian acknowledgement evidence is stored as immutable `Policy Acknowledgement` rows on guardian self-context.
4. Guardian Home and the guardian sidebar link to the policies page, but Guardian Home does not yet surface pending policy work as an attention card or count.
5. The student portal has no route, page, menu item, or home attention surface for policy acknowledgement.
6. The acknowledgement controller already supports `acknowledged_for = Student` with `context_doctype = Student`, but there is no named enrolled-student student workflow wired in the portal.

## Problem Statement
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: None

Product gaps to close:

1. Families can complete guardian acknowledgements only if they discover the dedicated page themselves.
2. Students cannot currently sign enrolled-student durable policies in `/hub/student`.
3. Policies that apply to both `Student` and `Guardian` do not yet have an explicit enrolled-student portal contract.
4. The current implementation is page-first, not action-first, which conflicts with the family UX rule that required signatures must surface on landing surfaces.

## Reuse Model
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue`, `ifitwala_ed/ui-spa/src/components/focus/StaffPolicyAcknowledgeAction.vue`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/guardian_policy.py`
Test refs: `ifitwala_ed/api/test_admissions_portal.py`, `ifitwala_ed/api/test_focus_policy_signature.py`, `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Reuse the admissions e-sign flow pattern for clause checks, typed signature, attestation, and blocked-submit feedback.
2. Reuse the guardian policy query/status shape where possible for the student portal API to keep portal behavior parallel.
3. Do not reuse the staff Focus/ToDo campaign workflow directly inside student or guardian portals.
4. Staff policy diff/review patterns may be reused later for richer review UX, but they are not required for the first enrolled-student portal slice.
5. The first slice should prefer a shared portal-facing signature component over duplicating guardian and student form logic.

## Audience And Obligation Contract
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/policy_utils.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
Test refs: None

Rules:

1. `Applies To = Guardian` creates a guardian obligation only and surfaces on `/hub/guardian`.
2. `Applies To = Student` creates a student obligation only and surfaces on `/hub/student`.
3. `Applies To = Student + Guardian` creates two distinct obligations, one per audience, with separate immutable evidence rows.
4. The first slice does not support an implicit “student or guardian may satisfy the same durable acknowledgement” rule.
5. If the product later needs “either/or” completion, that must be documented as a separate signer-rule contract before implementation.

## UX Contract
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/router/index.ts`
Test refs: None

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
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/governance/policy_utils.py`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/test_policy_acknowledgement.py`

Rules:

1. Guardian durable policy visibility must stay server-owned and continue to require signer authority from `Student Guardian.can_consent`.
2. Student durable policy visibility must be server-owned and limited to the current student self-context.
3. Guardian portals must not expose actionable student-only acknowledgements in the first enrolled-student slice.
4. Student portals must not expose guardian-only acknowledgements.
5. A user who can view a student in another workflow but lacks signing authority must not receive a policy action for that child.

## API And Data Contract
Status: Planned
Code refs: `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_policy_overview.ts`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`

Rules:

1. Durable acknowledgement remains an append-only `Policy Acknowledgement` insert with typed-signature evidence.
2. The first student slice should add named student APIs instead of making the SPA assemble generic CRUD.
3. Recommended first endpoints:
   - `get_student_policy_overview`
   - `acknowledge_student_policy`
4. Guardian APIs may remain separate in the first slice if that avoids risky refactors.
5. Shared helper code is allowed, but the first slice must not stall on a backend unification refactor.

## Home Surface And Concurrency Contract
Status: Planned
Code refs: `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: None

Rules:

1. Home surfaces must receive pending durable policy counts through bounded bootstrap data, not through client-side request waterfalls.
2. Home attention cards must be derived server-side from current unresolved durable policy obligations.
3. The portal must not add polling loops to refresh durable acknowledgement status.
4. Cache keys, if introduced, must remain audience- and scope-specific.
5. The home integration must stay lightweight enough for hot-path portal loads.

## Out Of Scope
Status: Planned
Code refs: `ifitwala_ed/docs/files_and_policies/policy_04_family_signature_and_consent_contract.md`, `ifitwala_ed/docs/files_and_policies/policy_05_phase2a_guardian_first_implementation_plan.md`
Test refs: None

Not in this contract:

1. One-off permission slips.
2. Mutable consent grant, decline, withdrawal, and renewal.
3. Staff campaign authoring changes beyond what is needed to publish versioned durable policies already in scope.
4. A new schema field for enrolled-student signer rules.
5. Student co-sign for mutable consent or event permission flows.

## Delivery Plan
Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/api/guardian_home.py`
Test refs: None

Recommended sequence:

1. Document the enrolled-student durable acknowledgement contract and correct portal behavior drift.
2. Add student durable policy API endpoints and contract types.
3. Add `/student/policies` and student sidebar navigation.
4. Add pending durable policy attention/counts to Student Home.
5. Extend Guardian Home with pending durable policy attention/counts.
6. Extract a shared portal durable-policy signing component if duplication becomes material.
7. Add backend and SPA regression coverage for both portals.

## Risks
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
Test refs: None

Risks:

1. If `Student + Guardian` is treated as one shared obligation without an explicit contract, compliance reporting will become ambiguous.
2. If home cards are implemented with extra client requests, portal hot paths will regress.
3. If student and guardian policy surfaces diverge too far, policy UX will become harder to teach and support.
4. If guardian pages start exposing student-only obligations, the audience model on `Institutional Policy` will lose meaning.

## Contract Matrix
Status: Planned
Code refs: `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.json`, `ifitwala_ed/governance/doctype/policy_version/policy_version.py`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/api/guardian_policy.py`, `ifitwala_ed/api/guardian_home.py`, `ifitwala_ed/ui-spa/src/router/index.ts`, `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianHome.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
Test refs: `ifitwala_ed/api/test_guardian_phase2.py`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts`

| Layer | Current owner | Planned enrolled-student durable acknowledgement extension | Status |
|---|---|---|---|
| Schema / DocType | `Institutional Policy`, `Policy Version`, `Policy Acknowledgement` | Reuse existing versioned acknowledgement model; no new DocTypes in first slice | Planned |
| Controller / workflow logic | `policy_acknowledgement.py`, `guardian_policy.py` | Add student portal durable acknowledgement workflow and keep guardian workflow discoverable | Planned |
| API endpoints | `get_guardian_policy_overview`, `acknowledge_guardian_policy` | Add named student durable policy endpoints and home count integration | Planned |
| SPA / UI surfaces | Guardian policy page only | Add student page and action-first home surfacing in both portals | Planned |
| Reports / dashboards | Existing durable acknowledgement evidence only | Portal counts and status chips remain version-acknowledgement focused | Planned |
| Scheduler / background jobs | None | None required for the first durable acknowledgement slice | Planned |
| Tests | Guardian backend and SPA coverage | Add student portal coverage and home-surface regressions | Planned |

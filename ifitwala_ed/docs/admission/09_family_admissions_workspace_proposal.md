# Family Admissions Workspace Proposal

This note is a non-authoritative proposal.

Current canonical runtime remains defined by:

- `ifitwala_ed/docs/admission/05_admission_portal.md`
- `ifitwala_ed/docs/admission/04_identity_upgrade.md`
- `ifitwala_ed/docs/docs_md/student-applicant.md`
- `ifitwala_ed/docs/docs_md/policy-acknowledgement.md`

This proposal exists to define a future target contract before code changes are approved.

## 1. Decision Goal

Status: Planned
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`
Test refs: `None`

Target runtime outcome:

1. One or more adult family admissions users can manage multiple `Student Applicant` records in one admissions workspace.
2. `Student Applicant` remains the child-level admissions record of truth.
3. Shared adult or household information is captured once and reused across linked applicants.
4. `Student Applicant.applicant_user` remains reserved for the future student identity and is not repurposed as the family access anchor.
5. Promotion and identity upgrade must carry explicit family structure forward so promoted students are linked as siblings without duplicate manual work.

The product goal is simple:

`one family -> one calm admissions workspace -> many child applicants -> no duplicate adult data entry`

## 2. Why The Current Model Should Change

Status: Planned
Code refs: `ifitwala_ed/docs/admission/05_admission_portal.md`, `ifitwala_ed/docs/spa/guardian_portal/01_guardian_product.md`, `ifitwala_ed/docs/spa/guardian_portal/z2_guardian_contract.md`
Test refs: `None`

Current runtime assumptions create unnecessary friction for families with multiple children:

- one login is effectively tied to one applicant
- the admissions surface is applicant-first instead of family-first
- guardian details are captured inside each applicant context
- policy acknowledgement is applicant-context first, even when the real-world signer is an adult acting for the whole family

This conflicts with the product direction already established elsewhere in the ERP:

- the guardian portal is explicitly family-first
- guardian users can be linked to multiple students
- the system already models applicant guardian rows before promotion

### Rationale

Pros:

- families with two or more children no longer juggle separate admissions identities
- adult identity data is entered once and reused
- admissions and guardian surfaces follow the same mental model: family first, child drill-down second
- the system preserves per-child auditability because each child still has a distinct `Student Applicant`

Cons:

- this is a real contract change across admissions identity, permissions, policy acknowledgement, and post-promotion linkage
- policy acknowledgement rules must become more explicit before rollout
- file/document ownership must distinguish family-scoped uploads from child-scoped uploads

Blind spots:

- separated households may have multiple adults with different authority across siblings
- schools may not want family-mode rollout immediately on every site
- some current sites may already have one-email-per-child operational workarounds that need migration support

Risks:

- overloading `applicant_user` would corrupt the student-identity upgrade path
- inferring family access from shared email alone would create permission drift and false sibling grouping
- maintaining two permanent product models would create long-term documentation and code drift

## 3. Proposed Access Model

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`, `ifitwala_ed/api/admissions_portal.py`
Test refs: `None`

### 3.1 Admissions Access Mode

Add one new admissions-portal mode selector on `Admission Settings`.

The exact field name is intentionally left undecided for schema review.

Proposed site-level modes:

1. `Single Applicant Workspace`
   - current behavior
   - one admissions login resolves one applicant
2. `Family Workspace`
   - recommended target behavior
   - one adult admissions login resolves all explicitly linked applicants for that family actor

This setting is intended as a rollout control, not a forever-forked product strategy.

Target direction after rollout maturity:

- `Family Workspace` becomes the canonical default
- `Single Applicant Workspace` remains legacy compatibility only as long as needed for migration

### 3.2 Family Access Anchor

Family admissions access must be anchored through explicit relationship rows, not guessed by email.

Recommended anchor:

- `Student Applicant Guardian` rows remain the authority for who the adult is, what relationship they have, and whether they may act
- early materialized `Guardian` records should become the stable adult identity anchor during admissions, even before long-term guardian portal access is granted
- the adult admissions user should link to that explicit guardian identity, not to `Student Applicant.applicant_user`
- one adult actor may be linked to many sibling applicants

This means the future family admissions access identity is not the child applicant identity.
It should instead be the future guardian identity, opened early for admissions collaboration.

### 3.3 `/admissions` Entry Contract

When `Family Workspace` mode is enabled:

- if the user resolves to one linked applicant, `/admissions` may open directly into that child workspace
- if the user resolves to multiple linked applicants, `/admissions` must open a family dashboard first
- the family dashboard must show:
  - each child applicant
  - current status
  - blocking items
  - next direct action

The user must never need to sign out and back in as another child applicant.

### 3.4 Multi-Adult Collaboration Contract

The family workspace should support more than one adult user for the same family.

Recommended rules:

- each adult uses their own user account; shared credentials are forbidden
- one family workspace may be visible to many explicitly linked adults
- adults may collaborate across uploads, profile completion, and child-specific steps in the same workspace
- audit must always record the actual acting user for every save, upload, acknowledgement, and submit action
- the same adult account should later become the long-term guardian account when guardian portal access is provisioned

Recommended collaboration model:

- additive actions are multi-actor friendly
  - document uploads
  - messages
  - child-by-child completion steps
- overwrite-prone actions require optimistic concurrency checks
  - shared adult profile edits
  - child profile edits
  - any replace-style upload or destructive change

The UX should not hard-lock the whole family workspace for one adult.
Instead:

- allow concurrent entry by many adults
- detect conflicting edits at save time
- return an explicit conflict message showing the section, latest editor, and latest modified time
- require the user to refresh or reconcile before overwriting newer changes

This preserves collaboration without silent data loss.

## 4. Shared Data vs Child-Specific Data

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/docs/docs_md/student-applicant.md`
Test refs: `None`

The no-duplicate-entry rule must be enforced by data ownership, not by UI tricks.

### 4.1 Shared Adult Data

These values should be captured once and reused across all linked applicants for the same adult:

- salutation
- guardian first name
- guardian last name
- guardian email
- guardian mobile phone
- guardian work email
- guardian work phone
- guardian image
- employment sector
- work place
- guardian designation
- linked adult user identity

### 4.2 Relationship-Specific Data

These values remain per guardian-child relationship row and may vary by child:

- relationship
- is_primary
- can_consent
- is_primary_guardian
- is_financial_guardian

### 4.3 Child-Specific Data

These values remain owned by each `Student Applicant` and must never be merged into a family blob:

- applicant profile fields
- applicant health profile
- applicant documents
- interview history
- recommendation status
- application status
- enrollment offer/choice state
- child-specific policies or consents

### 4.4 UX Implication

The family workspace should offer:

- a shared adult details step
- child cards or tabs for child-specific steps
- prefill and reuse of already-entered adult information when a new sibling applicant is created or linked

The server must own reuse. The SPA must not assemble its own cross-applicant copy logic.

## 5. Policy Acknowledgement Authority And Granularity

Status: Planned
Code refs: `ifitwala_ed/docs/docs_md/policy-acknowledgement.md`, `ifitwala_ed/docs/docs_md/institutional-policy.md`, `ifitwala_ed/docs/files_and_policies/policy_01_design_notes.md`
Test refs: `None`

This proposal adopts the following best-practice rule:

- do not use "consent" when there is no genuine choice
- keep acknowledgement/consent evidence purpose-specific and granular
- allow one UI workflow to generate many server-owned evidence rows when the legal subject is many children

### 5.1 Proposed Policy Modes

Add one explicit policy behavior selector on the policy contract.

The exact field placement and field name are intentionally left undecided for schema review.
It may live on `Institutional Policy` or `Policy Version`, depending on whether the team wants the mode to be identity-level or version-level.

Recommended modes:

1. `Family Acknowledgement`
   - example: school handbook, family portal rules, parent code of conduct
   - one linked adult with authority acknowledges once per policy version and scope
   - evidence should be stored once for the adult/family actor, not duplicated per child

2. `Child Acknowledgement`
   - example: acceptable use rules, required child participation terms, student conduct expectations
   - acknowledgement is required per child
   - UI may offer one bulk signing flow across siblings
   - server still writes one evidence row per child context

3. `Child Optional Consent`
   - example: media consent, optional technology use, optional directory sharing
   - decision remains per child
   - must support explicit allow/deny state and later change/withdraw flows where policy requires it
   - should not block core admissions readiness by default

### 5.2 Actor Authority Rules

Recommended authority rules:

- a linked adult may act only when the applicant guardian relationship is explicit
- adult authority for admissions-stage child action must require `can_consent = 1`
- adult authority must never be inferred from shared email alone
- child applicant self-action may still exist in legacy single-applicant mode, but family workspace should not depend on child identity reuse
- separate adults may both contribute data, but each acknowledgement record must still name the actual signer; one adult may never sign as another
- family admissions users should be treated as pre-guardian adults, not as stand-ins for the child applicant user

### 5.3 Readiness Rules

Recommended readiness behavior:

- `Family Acknowledgement` policies are satisfied once for all linked applicants in the policy scope
- `Child Acknowledgement` policies are satisfied only per child applicant
- `Child Optional Consent` policies are recorded and surfaced, but must not be mis-modeled as required acknowledgement just to force a decision

Default signer rule for family-wide acknowledgement:

- one authorized adult signature satisfies the family-wide acknowledgement requirement
- if a school needs more than one adult signer for a specific policy, that must be an explicit future policy mode, not an implied side effect of multi-adult access

If the institution requires acceptance of a mandatory rule, that rule should be modeled as acknowledgement, not optional consent.

### 5.4 Operational Example

For one family with three applicants:

- school handbook:
  - one adult acknowledgement
  - one evidence row for that adult/policy version/scope
- media consent:
  - one family UI flow may present all three children
  - the server must still store three child-specific decisions when the adult signs for all three
- acceptable use:
  - may be completed in one multi-child flow
  - server writes one acknowledgement row per child applicant

## 6. Promotion, Identity Upgrade, And Sibling Linking

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/docs/admission/04_identity_upgrade.md`, `ifitwala_ed/students/doctype/student/student.py`, `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
Test refs: `None`

The existing `Student.siblings` model remains canonical after promotion.

The proposal is not to create a new sibling data structure.
The proposal is to feed the existing sibling structure from explicit family relationships.

### 6.1 Canonical Sibling Rule

Two promoted students should be linked as siblings when they share at least one explicit guardian relationship after promotion.

Approved evidence for sibling linking:

- shared `Guardian` link carried into `Student.guardians`
- shared promoted guardian identity originating from explicit applicant guardian rows

Forbidden inference sources:

- same last name
- same portal email
- same address text
- same school only

### 6.2 Runtime Timing

Target runtime behavior:

- promotion should carry explicit guardian links onto `Student.guardians`
- promotion should trigger sibling sync immediately after those guardian links are established
- identity upgrade may re-run sibling sync defensively, but sibling creation should not wait for identity upgrade
- by the time promotion completes, the promoted student should already participate in the canonical sibling graph

### 6.3 Existing Student Contract Reuse

`Student.sync_reciprocal_siblings()` already owns bidirectional sibling consistency.

The new requirement is an admissions-to-student bridge helper that:

1. resolves promoted students sharing explicit guardians
2. updates `Student.siblings`
3. lets the existing student model enforce reciprocal consistency

The helper must be idempotent and safe to rerun.

## 7. Rollout Strategy

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
Test refs: `None`

### Phase 1

- add the admissions access mode setting
- add early guardian identity materialization for applicant guardian rows
- add one dedicated pre-guardian admissions-family role for adult collaborators
- implement family admissions dashboard and sibling applicant switching
- introduce shared adult profile reuse
- keep current child-specific applicant flows underneath

### Phase 2

- add explicit policy behavior modes
- add family-wide acknowledgement flows and child-bulk acknowledgement flows
- make promotion carry explicit guardian links into `Student.guardians`
- add post-promotion sibling sync from explicit guardian links

### Phase 3

- migrate legacy single-applicant sites and users to adult-collaborator family access
- reduce or retire legacy single-applicant access paths once operationally safe

## 8. Contract Matrix

Status: Planned
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `ifitwala_ed/students/doctype/student/student.py`
Test refs: `None`

| Area | Proposed runtime owner | Primary surfaces | State |
| --- | --- | --- | --- |
| Family admissions access resolution | admissions access helper + early guardian identity linkage | `/admissions` | Planned |
| Site rollout mode | `Admission Settings` | Desk settings, admissions portal bootstrap | Planned |
| Adult collaborator identity continuity | early `Guardian` identity + dedicated pre-guardian admissions-family role | admissions portal, later guardian portal | Planned |
| Shared adult profile reuse | parent applicant workflow + admissions API | `/admissions/profile` | Planned |
| Child-specific admissions workflow | `Student Applicant` + related child artefacts | child cards/routes in `/admissions` | Planned |
| Policy behavior mode resolution | policy contract + acknowledgement controller | `/admissions/policies`, future guardian flows | Planned |
| Family-wide acknowledgement evidence | policy acknowledgement controller using `Guardian` context | admissions policies | Planned |
| Child bulk acknowledgement flow | admissions policy API + policy acknowledgement controller | admissions policies | Planned |
| Post-promotion sibling sync | admissions-to-student bridge helper + `Student.sync_reciprocal_siblings()` | promotion, defensive rerun in identity upgrade | Planned |

## 9. Recommended Resolutions Before Coding

Status: Planned
Code refs: `None`
Test refs: `None`

This proposal recommends the following target decisions before implementation begins.

### 9.1 Identity Model

Recommended decision:

- create one dedicated pre-guardian admissions-family role for adult collaborators
- materialize or reuse `Guardian` records early during admissions as the adult identity anchor
- link adult collaborator users to those guardian identities
- do not use `Student Applicant.applicant_user` as the family admissions access anchor

Recommended continuity rule:

- the admissions-family adult user becomes the same long-term guardian user later
- `applicant_user` remains reserved for the future student user path only

Why:

- it preserves adult identity continuity from admissions into the guardian portal
- it avoids routing leakage caused by reusing the `Guardian` role too early
- it stops adult collaboration from colliding with the child future-student identity

### 9.2 Family-Wide Policy Evidence Context

Recommended decision:

- store family-wide policy evidence against explicit early materialized `Guardian` context
- keep child-specific evidence on `Student Applicant` during admissions and `Student` after promotion

Why:

- `Policy Acknowledgement` already supports `Guardian` context, so no new evidence doctype is required
- a family-wide handbook-style acknowledgement is about the adult actor, not each child record
- this preserves continuity from admissions into later guardian-stage policy review

### 9.3 Sibling Sync Timing

Recommended decision:

- promotion should establish `Student.guardians` from explicit applicant guardian links
- promotion should then call the admissions-to-student sibling sync helper immediately
- identity upgrade may rerun that helper idempotently, but should not be the primary moment siblings first appear

Why:

- the user-facing expectation is that promoted siblings already behave like siblings
- guardian structure should become data truth at promotion time, not remain deferred until role provisioning
- `Student.sync_reciprocal_siblings()` already exists and can stay the canonical enforcement path

### 9.4 Migration Strategy

Recommended decision:

- migrate through an in-product admissions operations tool, not a CLI-only process
- keep legacy one-login-per-child access working during transition
- invite adult collaborator users explicitly from applicant guardian rows
- create or reuse guardian identities deterministically from explicit guardian/contact data only
- once adult collaborator access is confirmed for a family, mark the legacy child-specific admissions access path for retirement

Recommended migration safety rules:

- never infer family grouping from email alone
- never auto-promote an adult legacy applicant login into the future student identity
- if a current `applicant_user` is really an adult admissions actor, treat it as legacy access to retire, not as the canonical student future-user
- unresolved records must surface as staff review items in the migration UI

### 9.5 Mixed Guardian And Admissions Families

Recommended decision:

- if an adult already has guardian access for enrolled children and admissions-family access for applicants, use the same user account
- grant the adult the admissions-family role in addition to any existing guardian role
- route them to `/admissions` while open linked applicants still require work, with a clear path back to the guardian portal

Why:

- families should not maintain two adult accounts for current students vs new applicants
- one adult identity across both surfaces reduces duplication and support burden

Until those decisions are approved, current canonical admissions behavior remains unchanged.

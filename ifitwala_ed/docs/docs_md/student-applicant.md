---
title: "Student Applicant: The Admission Record of Truth"
slug: student-applicant
category: Admission
doc_order: 4
version: "1.22.2"
last_change_date: "2026-05-30"
summary: "Manage each applicant from invitation to promotion, with readiness checks across profile, documents, policies, recommendations, health, offers, deposits, and enrollment handoff."
seo_title: "Student Applicant: The Admission Record of Truth"
seo_description: "Use Student Applicant to manage the applicant lifecycle from invitation to promotion, with readiness checks, portal access, family collaboration, and enrollment handoff."
---

## What Is a Student Applicant?

`Student Applicant` is the main admissions record for one prospective student. It is where an inquiry becomes an application, where families complete profile and evidence steps, where staff review readiness, and where an approved applicant can eventually become a `Student`.

Think of it as the applicant's admissions file: identity, school intent, portal access, required policies, documents, health clearance, interviews, review decisions, offer readiness, and promotion all connect back here.

<Callout type="info" title="Why Ifitwala Ed is different">
Student Applicant keeps admissions human for staff and families while still protecting the data model. Families see a guided portal. Staff see readiness summaries and next actions. The server still owns the serious rules: who may edit, what is ready, what is blocked, and when promotion is allowed.
</Callout>

## Why This Matters

- **One applicant record stays with the whole journey.** Teams can follow the applicant from `Draft` or `Invited` all the way to `Promoted`.
- **Readiness is visible instead of guessed.** Profile, policy, document, health, recommendation, and review signals come together on the applicant.
- **Families get a proper admissions portal.** Applicants or family collaborators can complete forms, acknowledge policies, upload documents, and track status through `/admissions`.
- **Teachers get a warmer handoff.** Optional learning-support context, strengths, interests, activities, achievements, and student voice can be captured before the first day.
- **Staff work from context.** Admissions teams can review evidence from the applicant record, Admissions Cockpit, and workspace overlays without hopping across disconnected files.
- **Inquiry data carries forward.** When staff invite from an inquiry, identity, intent, school context, and contact lineage move into the applicant.
- **Promotion is protected.** Approved applicants only move forward when readiness, offer, deposit, and required profile rules are satisfied.

<Callout type="tip" title="Production value">
Student Applicant is where admissions correctness is enforced. The user interface guides the team, but approval, promotion, identity, file, and portal rules are server-owned.
</Callout>

## Before You Create or Invite an Applicant

You should have:

- [**Organization**](/docs/en/organization/) and [**School**](/docs/en/school/) records ready
- admissions staff users with `Admission Officer` or `Admission Manager`
- required [**Applicant Document Type**](/docs/en/applicant-document-type/) records, if the school uses document readiness checks
- [**Institutional Policy**](/docs/en/institutional-policy/) and active [**Policy Version**](/docs/en/policy-version/) records, if applicant policy acknowledgement is required
- [**Applicant Health Profile**](/docs/en/applicant-health-profile/) workflow expectations, if health clearance is required before approval
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) and [**Admission Settings**](/docs/en/admission-settings/), if your school uses offers, deposits, or automatic enrollment-request handoff

Profile data needed for promotion should also be collected before the final step. This includes date of birth, gender, mobile number, joining date, first language, nationality, and residency status. Optional profile links such as cohort and student house can also carry forward when set.

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Applicant identity | Name, contact identity, and the applicant record itself | Gives admissions one stable applicant file |
| Organization and school | The institutional anchor for the application | Controls scope, visibility, policy matching, and promotion context |
| Application status | Draft, invited, in progress, submitted, under review, approved, promoted, and terminal states | Shows where the applicant is in the admissions journey |
| Portal account | Applicant-self or family-collaborator access to `/admissions` | Lets the right person complete the application |
| Applicant profile | Student details needed for review and promotion | Prevents missing profile data at the promotion step |
| Guardians | Parent/guardian contacts, signer authority, and family collaboration | Supports family workspace, policy acknowledgement, and later student guardian links |
| Policies | Required applicant or family acknowledgements | Keeps consent and school policy evidence auditable |
| Documents | Required admissions evidence and reviewed uploads | Keeps admissions files governed and attached to the correct applicant workflow |
| Health | Applicant health disclosure and clearance when required by school policy | Prevents approval before required health review is complete |
| Interviews and feedback | Interview event records and interviewer opinions | Keeps operational interview scheduling separate from reviewer feedback |
| Offer and deposit bridge | Applicant Enrollment Plan, offer response, and required deposit state | Protects promotion when offer or deposit policy is not complete |
| Promotion handoff | Student creation, governed artifact carry-forward, and optional enrollment request hydration | Moves the applicant into enrollment without retyping the admissions record |

## How This Fits the Admissions Workflow

<Steps title="Student Applicant lifecycle">
  <Step title="Create or invite">
    Staff create a draft applicant or invite from an Inquiry. Inquiry conversion can prefill identity, intent, school context, and contact lineage.
  </Step>
  <Step title="Open portal access">
    Staff invite either the applicant self or, when Family Workspace is enabled, a family collaborator. Each person uses their own login.
  </Step>
  <Step title="Collect profile and evidence">
    The applicant or family completes profile, guardian, policy, document, health, and course-choice steps in `/admissions` where applicable.
  </Step>
  <Step title="Review readiness">
    Admissions staff use Desk summaries, Admissions Cockpit, and review assignments to resolve blockers before approval.
  </Step>
  <Step title="Offer and accept">
    When the school uses the admissions-to-enrollment bridge, Applicant Enrollment Plan owns placement, offer, family response, deposit terms, and hydration readiness.
  </Step>
  <Step title="Promote">
    Approved applicants can be promoted to Student when required profile, offer, deposit, and readiness checks pass.
  </Step>
</Steps>

## Permission Matrix

Admissions staff manage applicant records. Applicants and family collaborators can work only in their own portal context. Academic Admins can read scoped records but do not own admissions decisions.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Academic Admin` | Yes | No | No | No | Scoped read visibility |
| `Academic Assistant` | No | No | No | No | Not in runtime admissions-file access contract |
| `Admissions Applicant` | Yes | Yes | No | No | Own applicant only; self-link enforced |
| `Admissions Family` | Yes | Yes | No | No | Family workspace only; explicit guardian linkage required |

Server-side rules also apply:

- only admissions staff can create new records
- admissions and academic-admin reads are organization/school scoped
- family/applicant editability depends on current status: `Invited`, `In Progress`, or `Missing Info`
- terminal states (`Rejected`, `Withdrawn`, `Promoted`) are locked except explicit System Manager override flow
- protected identity and anchor fields are set only through named flows
- admissions evidence belongs on [**Applicant Document**](/docs/en/applicant-document/), not as random direct attachments

## Practical Examples

### Inquiry becomes an applicant

An admissions officer receives an inquiry from a parent. When the lead is ready to apply, the officer uses the invite-to-apply flow. If the inquiry has the right context, the applicant can start with identity, program intent, academic year, term, school, organization, and contact lineage already carried forward.

### Applicant-self login

For older students or university-style admissions, the applicant may manage their own application. Staff invite the applicant self from the Student Applicant form, choose the login email, and Ifitwala Ed links the user as the applicant identity.

### Family workspace login

For K-12 admissions, the person completing the application is often a parent or guardian. When [**Admission Settings**](/docs/en/admission-settings/) uses `Family Workspace`, admissions staff can invite a family collaborator with the `Admissions Family` role. The adult gets their own login, and saves, uploads, and acknowledgements are attributed to that adult.

### Ready for approval

An applicant is not ready just because a form looks complete. Approval checks can include required policies, required documents, profile completion, recommendations, and health clearance when the school requires it. Staff should use the readiness summaries rather than guessing.

### Approved, accepted, and ready to promote

Approval is the admissions decision. Offer acceptance and deposit readiness belong to Applicant Enrollment Plan and Admission Settings. If the latest plan is not accepted or a required deposit is unpaid, promotion can be blocked.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use lifecycle actions such as submit, approve, reject, and promote so readiness and audit rules run.</Do>
  <Do>Invite portal users from the Student Applicant actions so login identity, roles, and email linkage stay server-owned.</Do>
  <Do>Use readiness summaries to explain what is blocked and what the family or staff should do next.</Do>
  <Do>Use Applicant Document for admissions evidence instead of direct file clutter on the applicant.</Do>
  <Do>Keep applicant-self and family-collaborator identities separate.</Do>
  <Dont>Manually edit application status to skip required transitions.</Dont>
  <Dont>Use the applicant user as a guardian login in family workspace mode.</Dont>
  <Dont>Promote an applicant before required offer, deposit, health, document, and profile checks are complete.</Dont>
  <Dont>Treat Inquiry interest fields as final student truth without review.</Dont>
</DoDont>

## Common Questions

### What does `Invited` mean?

`Invited` means admissions has opened the application lifecycle. It may come from a staff portal invite or an inquiry conversion. Inquiry conversion creates the applicant and carries source context, but portal login access still depends on the proper applicant or family invite flow.

### How does the school know policy acknowledgement is required?

The system checks active Institutional Policies and active Policy Versions that apply to `Applicant`, match the applicant organization scope, and match the applicant school scope. If at least one active policy matches, acknowledgement is required.

### Can a parent and applicant share the same login?

No. Family workspace collaboration is multi-user, not shared-login. Each adult collaborator has their own `User`, and applicant-self identity remains separate from guardian/family identity.

### Can applicants upload documents themselves?

Yes, when their status allows editing. Applicant document uploads go through the admissions portal and governed file workflow. Uploaded docs pending review are shown as under review, while missing required docs remain blocking.

### Does approval create the student?

No. Approval is an admissions decision. Promotion is the separate action that creates or links the `Student` record after required readiness, offer, deposit, and profile checks pass.

### Does promotion create enrollment automatically?

Promotion creates or links the student and may auto-hydrate a draft Program Enrollment Request from an accepted Applicant Enrollment Plan when Admission Settings allow it. It does not create Program Enrollment directly.

## Related Docs

<RelatedDocs
  slugs="inquiry,admission-cockpit,applicant-enrollment-plan,applicant-document-type,applicant-document,applicant-health-profile,applicant-interview,institutional-policy,policy-version,policy-acknowledgement"
  title="Continue With Related Applicant Lifecycle Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-28)

- **DocType schema file**: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.json`
- **Controller file**: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- **Required fields (`reqd=1`)**:
  - `first_name` (`Data`)
  - `last_name` (`Data`)
  - `organization` (`Link` -> `Organization`)
  - `school` (`Link` -> `School`)
- **Lifecycle hooks in controller**: `before_save`, `on_update`, `validate`
- **Operational/public methods**: `mark_in_progress`, `submit_application`, `mark_under_review`, `mark_missing_info`, `withdraw_application`, `approve_application`, `reject_application`, `promote_to_student`, `apply_system_manager_override`, `has_required_policies`, `has_required_documents`, `health_review_complete`, `has_required_interviews`, `get_readiness_snapshot`, `academic_year_intent_query`, `school_by_organization_query`

### Status Model

| Status | Typical meaning |
|---|---|
| `Draft` | Staff-created shell |
| `Invited` | Applicant user invited or inquiry conversion created the applicant |
| `In Progress` | Family/applicant is actively filling data |
| `Submitted` | Family/applicant submitted for review |
| `Under Review` | Staff review stage |
| `Missing Info` | Returned for corrections |
| `Approved` | Admissions decision approved |
| `Rejected` | Terminal rejected |
| `Withdrawn` | Terminal withdrawn |
| `Promoted` | Converted to Student |

Direct status writes are blocked; lifecycle methods own status transitions.

### Policy Acknowledgement Requirement

There is no manual toggle on `Student Applicant` for "policy required". It is computed automatically by server logic.

Policy acknowledgement is mandatory for an applicant when at least one active policy candidate matches all of these conditions:

1. `Institutional Policy.is_active = 1`
2. `Policy Version.is_active = 1` for that policy
3. `Institutional Policy.applies_to` includes `Applicant`
4. Policy organization applies to the applicant organization scope; nearest ancestor policy per `policy_key` is selected
5. Policy school scope matches: `school` blank/global, applicant school, or ancestor/parent school

If no policy rows match those rules, policy acknowledgement is not required for that applicant.

Admissions staff see policy requirement status through:

- Desk `Policies Summary`
- `Documents Summary`
- `Health Summary`
- `Review Assignments Summary`
- `Review Snapshot`
- Admissions Cockpit applicant workspace
- `/admissions` Policies page
- server approval guard: `approve_application` -> `_validate_ready_for_approval`

Applicant policy acknowledgement in portal requires explicit electronic-signature controls. The typed signer name must match the expected signer name shown for the selected policy, and legal attestation must be confirmed before server insert. Family-scoped admissions policies sign on `Guardian` context; child-scoped admissions policies sign on `Student Applicant` context. Evidence remains the immutable `Policy Acknowledgement` record with server timestamp.

### Portal Invite and Login Contract

Portal login invite is done directly from Desk on the `Student Applicant` form:

1. Open the applicant record.
2. Click `Actions` -> `Invite Admissions Portal` or `Manage Admissions Portal Invite`.
3. Choose `Applicant self` or `Family collaborator`.
4. Pick an eligible email from the dialog, or enter a new one when allowed.

The inquiry contact is only the person who inquired. In K-12 admissions that person is often a parent or adult family collaborator; in college or university admissions that person may be the applicant self. Staff must make the identity choice explicitly during invite.

Applicant-self invite uses `invite_applicant` and requires:

- `student_applicant`
- `email`

Applicant-self invite behavior:

- email is normalized before processing
- invite email is validated against applicant contact ownership
- invite email is upserted into `Contact Email`
- applicant contact is kept linked to `Student Applicant` via Contact `Dynamic Link`
- new `User` is created when needed
- role `Admissions Applicant` is ensured
- invited user is forced `enabled = 1`
- `Student Applicant.applicant_user` is set to that user identity
- `Student Applicant.portal_account_email` is set to the chosen invite email
- invite is blocked if the applicant is already linked to a different email/user
- applicant-self invite is blocked when required applicant-scoped policies use `Family Acknowledgement`

Family-collaborator invite uses `invite_family_collaborator` and requires:

- `Admission Settings.admissions_access_mode = Family Workspace`
- either a complete primary/signing `Student Applicant Guardian` row or a reusable linked Inquiry/Applicant Contact
- for an existing row: `is_primary_guardian = 1`, derived `can_consent = 1`, and either a personal email on the row or a matching linked Inquiry/Applicant Contact email
- for Contact bootstrap: Contact first name, last name, primary email, and primary mobile phone

That flow assigns role `Admissions Family` and links the login through the selected or bootstrapped family collaborator row. Contact bootstrap can create the first `Student Applicant Guardian` row or complete an existing primary signer row during the invite. It does not write `Student Applicant.applicant_user`; if the same adult was mistakenly invited as applicant self, the family invite converts that login by clearing `Student Applicant.applicant_user` / `portal_account_email` and removing the `Admissions Applicant` role.

When `Admission Settings.admissions_access_mode = Family Workspace`, `/admissions` becomes a family workspace:

- family collaborators use role `Admissions Family`
- access for signer workflows is resolved from explicit primary `Student Applicant Guardian` rows where `is_primary_guardian = 1` and derived `can_consent = 1`
- one adult user can be linked to multiple active applicants and switch between them inside `/admissions`
- collaboration is multi-user, not shared-login
- child identity field `Student Applicant.applicant_user` remains reserved for the future student identity
- applicant profile and health saves use optimistic concurrency tokens (`record_modified` / `expected_modified`)

Portal URL details:

- Portal URL: `/admissions`
- Document upload URL: `/admissions/documents`
- Applicant-self username/email: `Student Applicant.portal_account_email`
- Family workspace username/email: the invited guardian/family user email
- New invited users set passwords through welcome/reset email; existing users use existing credentials or forgot password
- If email delivery fails, portal linkage still succeeds; the invited person can use `Forgot Password` on `/login`

Website gate `ifitwala_ed/www/admissions/index.py` requires an authenticated user with either `Admissions Applicant` resolved from `Student Applicant.applicant_user`, or `Admissions Family` with family workspace mode enabled and explicit guardian linkage to one or more applicants.

### Applicant Profile Context

The applicant profile page separates required promotion data from optional context:

- Required profile completeness covers identity, language, residency, and home-address details needed for promotion.
- `program` and `program_offering` remain the canonical application intent. Families are not asked for a duplicate applying grade level on the profile form.
- Previous learning context records prior school, curriculum, language of instruction, and related notes.
- Learning and access support records family-provided context such as support-sharing preference, learning needs, helpful supports, existing plans or reports, social/emotional needs, physical or access needs, and family support priorities.
- Student strengths and interests records strengths, hobbies, activities, achievements, motivation, relationship notes, and student voice.

Learning/access and student-insight fields help admissions staff and future teachers prepare well. They do not replace the health page, medical clearance, required documents, or confidential recommendation workflows. When an applicant is promoted, these optional fields can become reviewable Student Insight Notes instead of permanent Student profile attributes.

### Applicant Portal Uploads

Applicant document upload flow:

- applicant uses `/admissions/documents`
- API wrapper: `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`
- domain delegate: `ifitwala_ed/admission/admissions_portal.py`
- Drive delegate: `ifitwala_drive.api.admissions.upload_applicant_document`
- editing/uploads allowed only in `Invited`, `In Progress`, or `Missing Info`
- upload creates/updates governed `Applicant Document` records in `ifitwala_ed`
- Drive finalizes the governed `File` and classification payload before response

Applicant/profile media notes:

- direct attachments are blocked except `applicant_image`
- Desk `applicant_image` upload follows the Drive-governed upload boundary
- applicant profile image endpoint: `ifitwala_ed.api.admissions_portal.upload_applicant_profile_image`
- profile image delegate: `ifitwala_ed.admission.admissions_portal.upload_applicant_profile_image` -> `ifitwala_drive.api.admissions.upload_applicant_profile_image`
- guardian photo endpoint: `ifitwala_ed.api.admissions_portal.upload_applicant_guardian_image`
- guardian image delegate: `ifitwala_ed.admission.admissions_portal.upload_applicant_guardian_image` -> `ifitwala_drive.api.admissions.upload_applicant_guardian_image`
- applicant/guardian photo uploads accept only `JPG`/`JPEG`/`PNG`, reject `HEIC`/`HEIF`, rewrite accepted uploads to server-owned stripped `JPEG`, and enforce `10 MB` / `25 megapixel` limits
- health vaccination proof delegate: `ifitwala_ed.admission.admissions_portal.upload_applicant_health_vaccination_proof` -> `ifitwala_drive.api.admissions.upload_applicant_health_vaccination_proof`

### Student Applicant Guardian Child Table

`guardians` uses child table **Student Applicant Guardian**. No standalone child-doc page is required; behavior is owned by the parent lifecycle.

Important fields and behavior:

- `guardian` -> `Guardian`
- `contact` -> `Contact`
- `relationship`
- `is_primary`
- `can_consent`, runtime signer-authority flag derived from `is_primary_guardian`
- guardian identity/profile fields mirrored from `Guardian`
- `use_applicant_contact`
- portal save validation requires first name, last name, personal email, mobile phone, and photo per row
- guardian personal/work emails are validated as email format
- guardian mobile/work phones are validated as phone format
- non-signing emergency or temporary-care guardians may remain linked with `can_consent = 0`

### Where Student Applicant Is Used

- **Admissions conversion**:
  - linked from [**Inquiry**](/docs/en/inquiry/)
  - created by `from_inquiry_invite`
- **Decision support records**:
  - [**Applicant Document**](/docs/en/applicant-document/)
  - [**Applicant Health Profile**](/docs/en/applicant-health-profile/)
  - [**Applicant Interview**](/docs/en/applicant-interview/)
- **Portal surfaces**:
  - website entry `/admissions`
  - SPA pages: overview, profile, documents, health, policies, messages, course choices, submit, status
  - API service: `ifitwala_ed.api.admissions_portal.*`
  - next-actions contract: document upload is blocking only when required docs are missing; uploaded docs pending review are surfaced as under-review, and Submit page shows an "Awaiting admissions review" banner while still allowing submission
- **Promotion linkage**:
  - `Student.student_applicant`
  - `promote_to_student` creates/links `Student`
  - `account_holder` is copied to the promoted `Student` when present and not already set to another payer
- **Recommendation intake**:
  - external recommender submissions use `/admissions/recommendation/<token>` and do not use applicant portal authentication
  - multiple confidential letters per applicant use per-request `Applicant Document Item` slots (`item_key`)
  - admissions creates/re-sends/revokes `Recommendation Request` records
  - recommender submission is sealed in `Recommendation Submission`
  - applicant portal surfaces recommendation status only
  - applicant documents and applicant uploads exclude recommendation-template target document types
  - architecture reference: `ifitwala_ed/docs/admission/06_recommendation_intake_architecture.md`
- **Governance policy engine**:
  - `Policy Acknowledgement.context_doctype = Student Applicant`
  - policy readiness comes from active Institutional Policy versions
- **Operational dashboards**:
  - morning brief admissions pulse
  - staff admissions cockpit route `/staff/admission-cockpit`
  - admissions cockpit API `ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data`
- **Reviewer workflow**:
  - submission trigger creates Overall Application review assignments
  - admissions roles review evidence in applicant context only
  - non-admissions reviewers handle `Applicant Document Item` assignments in Focus
  - completed Health and Overall Application assignment decisions appear in `review_assignments_summary`

### Inquiry Carry-Over

When admissions triggers invite-to-apply from an inquiry, the applicant is prefilled with:

- Identity: `first_name`, `last_name`
- Intent: `program`, `academic_year`, `term`
- Traceability: `inquiry`
- Lifecycle start: `application_status = Invited`
- Institutional anchor at invite time: `school` and `organization`
- Contact anchor: `applicant_contact` from Inquiry contact linkage, with `applicant_email` derived from Contact email rows

This mapping is deterministic server-side in `from_inquiry_invite`.

### Fresh Site / New School Prerequisites

Minimum to create the first Student Applicant:

1. Admissions staff user with admissions role.
2. A valid `Organization` and `School` pair.
3. Applicant identity fields: `first_name`, `last_name`.

Required for policy-governed admissions flow:

1. `Institutional Policy` rows scoped to the applicant organization/school:
   - `is_active = 1`
   - `applies_to` includes `Applicant`
   - organization scope aligns with school organization ancestry
2. At least one active `Policy Version` per policy that should be acknowledged:
   - `institutional_policy` points to active policy
   - `is_active = 1`
3. Schema is migrated with `Institutional Policy.applies_to` present, or policy resolution/readiness fails with `Policy schema mismatch`.

Required for approval-readiness path:

1. Required `Applicant Document Type` records are configured.
2. Applicant has corresponding `Applicant Document` requirement rows and each required one is satisfied by approved evidence or admissions override.
3. If `School.require_health_profile_for_approval = 1`, `Applicant Health Profile.review_status = Cleared`.
4. Applicant profile information required for Student promotion is complete. Optional learning/access and student-insight context does not block profile completeness.

Optional but commonly expected:

1. Media consent policy chain (`policy_key = media_consent` + active version + acknowledgement), if applicant image publish behavior is expected during promotion.
2. Applicant portal invite flow (`invite_applicant`) so families can acknowledge policies in `/admissions`.
3. Account holder and accepted-offer deposit setup, if the school requires an admissions deposit before promotion.

### Readiness and Review Model

- No stored `ready` field exists on the DocType.
- Readiness is computed on demand by `get_readiness_snapshot`.
- `review_snapshot`, `interviews_summary`, `health_summary`, `policies_summary`, and `documents_summary` are HTML UI summary fields.
- Hidden field present: `title`, a system/display helper, not readiness truth.
- `has_required_policies()` is blocking.
- `has_required_documents()` is blocking.
- `health_review_complete()` is blocking only when `School.require_health_profile_for_approval = 1`.
- `has_required_interviews()` is tracked but not currently part of the blocking ready boolean.
- Repeatable required document types are satisfied when approved submission count meets the required count, or when the parent requirement has an admissions override.
- Interview feedback completion is derived only from submitted `Applicant Interview Feedback` rows.
- `review_assignments_summary` is assignment-focused for Health + Overall Application; document reviewer metadata is surfaced in `documents_summary`.

### Offer and Enrollment Bridge

`Student Applicant` stays the admissions record of truth, but it does not own the family-facing offer lifecycle.

- `Student Applicant.application_status` remains the internal admissions lifecycle.
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) owns placement planning, `Offer Sent`, `Offer Accepted`, and `Offer Declined`.
- The applicant user on `Student Applicant` is reserved for the future student identity, not guardians.
- If a latest Applicant Enrollment Plan exists, promotion is blocked until that latest plan is `Offer Accepted` or already `Hydrated`.
- If the accepted plan requires a deposit and Admission Settings requires deposit before promotion, promotion is blocked until the deposit invoice is paid.
- Identity upgrade remains separate from promotion and can auto-run when the first active [**Program Enrollment**](/docs/en/program-enrollment/) is created or reactivated for the promoted student.

### Promotion Side Effects

`promote_to_student`:

- requires applicant status `Approved`
- requires `student_joining_date`
- requires the latest Applicant Enrollment Plan to be `Offer Accepted` or `Hydrated` when a latest plan exists
- requires paid deposit invoice when `Admission Settings.require_deposit_before_promotion = 1` and the accepted plan requires a deposit
- creates/links `Student`
- writes `Student.student_applicant`
- sets applicant status to `Promoted`
- syncs applicant `account_holder` to the promoted `Student` when present
- copies applicant `cohort` and `student_house` when populated
- creates/syncs `Student Patient` from Applicant Health Profile data
- copies approved admissions documents into Student-owned governed files; current runtime excludes only rows whose `promotion_target` is explicitly non-`Student`
- copies applicant image through the governed Drive workflow into the Student profile image slot
- creates reviewable `Student Insight Note` rows from optional learning/access, strengths, interests, relationship starter, and achievement context
- may auto-hydrate a draft `Program Enrollment Request` from the accepted Applicant Enrollment Plan when `Admission Settings.auto_hydrate_enrollment_request_after_promotion = 1`
- does not create Guardian/User portal access
- does not mutate portal roles
- does not create `Program Enrollment` directly
- does not send welcome email or print-format welcome kit by itself

### Identity Upgrade Side Effects

`upgrade_identity`:

- requires an active `Program Enrollment` for the promoted student
- is reachable from the named `upgrade_identity` action and from the first active `Program Enrollment` transition
- provisions the applicant user as `Student` access and removes `Admissions Applicant`
- provisions guardians only from explicit applicant guardian rows
- does not reuse applicant user as a guardian user
- links guardians to Student in canonical Student guardian rows
- carries primary-guardian signer authority from `Student Applicant Guardian` into `Student Guardian.can_consent`
- syncs `Student.siblings` from shared explicit guardians carried forward from admissions
- links tracked guardian Contact rows to `Student Applicant`, `Guardian`, and promoted `Student`
- is idempotent
- does not re-trigger automatically for ordinary edits to an already-active `Program Enrollment`

### Contract Matrix

Status: Implemented

Code refs:

- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/admission/doctype/student_applicant_guardian/student_applicant_guardian.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/admission/access.py`
- `ifitwala_ed/api/admissions_portal.py`
- `ifitwala_ed/api/guardian_policy.py`
- `ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py`
- `ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`
- `ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`

Test refs:

- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
- `ifitwala_ed/admission/api/test_portal_*.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/governance/doctype/institutional_policy/test_institutional_policy.py`

| Concern | Canonical owner | Code refs | Test refs |
|---|---|---|---|
| Schema / DocType | Applicant-stage and student-stage guardian relationship rows carry canonical signer authority; policy audience remains on Institutional Policy | `admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `students/doctype/student_guardian/student_guardian.json`, `governance/doctype/institutional_policy/institutional_policy.json` | `admission/doctype/student_applicant/test_student_applicant.py`, `governance/doctype/institutional_policy/test_institutional_policy.py` |
| Controller / workflow logic | Promotion carries signer authority forward; policy audience uses canonical `Table MultiSelect` rows; guardian/student acknowledgement visibility respects signer authority | `admission/doctype/student_applicant/student_applicant.py`, `governance/doctype/institutional_policy/institutional_policy.py`, `governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `api/guardian_policy.py` | `admission/doctype/student_applicant/test_student_applicant.py`, `api/test_guardian_phase2.py`, `governance/doctype/institutional_policy/test_institutional_policy.py` |
| API endpoints | Admissions family invite eligibility and guardian policy visibility use the signer-authority contract; admissions policy acknowledgement remains a named workflow | `api/admissions_portal.py`, `api/guardian_policy.py` | `admission/api/test_portal_*.py`, `api/test_guardian_phase2.py` |
| SPA / UI surfaces | Admissions family guardian rows present signer authority explicitly; guardian portal policy page consumes the filtered policy overview | `ui-spa/src/pages/admissions/ApplicantProfile.vue`, `ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue` | `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts` |
| Reports / dashboards / briefings | Staff policy communication defaults and guardian policy status views follow the canonical audience-row contract | `api/policy_communication.py`, `api/policy_signature.py`, `ui-spa/src/pages/guardian/GuardianPolicies.vue` | `api/test_guardian_phase2.py` |
| Scheduler / background jobs | None in this signer-authority workflow | None | None |
| Tests | Coverage exists for policy audience normalization, guardian policy filtering, and promotion carry-forward of signer authority | `governance/doctype/institutional_policy/test_institutional_policy.py`, `api/test_guardian_phase2.py`, `admission/doctype/student_applicant/test_student_applicant.py`, `admission/api/test_portal_*.py` | Implemented |

### Desk and SPA Surfaces

- Desk form logic/buttons/readiness widgets: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
- Interview actions on applicant form:
  - `Create Interview`
  - `Schedule Interview`
- Workspace cards: `ifitwala_ed/admission/workspace/admission/admission.json`
- Admissions portal SPA entrypoint: `ifitwala_ed/ui-spa/src/apps/admissions/main.ts`
- Admissions portal router: `ifitwala_ed/ui-spa/src/router/admissions.ts`
- Admissions portal pages:
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantPolicies.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantEnrollmentChoices.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantSubmit.vue`
  - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue`
- Service layer: `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`

Portal API endpoints in `ifitwala_ed/api/admissions_portal.py`:

- `get_admissions_session`
- `get_applicant_snapshot`
- `get_applicant_profile`
- `update_applicant_profile`
- `upload_applicant_profile_image`
- `get_applicant_health`
- `update_applicant_health`
- `list_applicant_documents`
- `list_applicant_document_types`
- `upload_applicant_document`
- `get_applicant_policies`
- `acknowledge_policy`
- `submit_application`
- `accept_enrollment_offer`
- `decline_enrollment_offer`
- staff flow endpoints:
  - `invite_applicant`
  - `get_family_invite_options`
  - `invite_family_collaborator`

Admissions policy overlay:

- page launcher: `ui-spa/src/pages/admissions/ApplicantPolicies.vue`
- overlay component: `ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue`
- acknowledgement submit: `admissionsService.acknowledgePolicy` -> `ifitwala_ed.api.admissions_portal.acknowledge_policy`
- acknowledgement requires `typed_signature_name` + `attestation_confirmed`

### Link Query Endpoints

- `academic_year_intent_query`
- `school_by_organization_query`

### Reporting and Analytics

- No dedicated Script/Query Report declares `Student Applicant` as `ref_doctype`.
- Current analytics are API/widget driven through admissions portal completeness and morning brief pulse.

### Troubleshooting: `Policy schema mismatch` (`applies_to` storage)

If you see an error log like:

- title: `Policy schema mismatch`
- caller: `StudentApplicant.has_required_policies`
- doctype: `Institutional Policy`
- missing_table: `Institutional Policy Audience`
- missing_link_doctype: `Policy Audience`

it means code expects the canonical `Institutional Policy.applies_to` child-table storage, but the site schema is missing the related audience DocTypes or child table.

Current implementation impact:

- `StudentApplicant.has_required_policies()` cannot evaluate required policies and marks readiness as not OK with a schema-error issue.
- `ifitwala_ed/api/admissions_portal.py::get_applicant_policies` throws a blocking error (`throw=True`) and policy UI cannot load.

Site operations response:

1. Run migrations for the affected site.
2. If the schema is still missing, reload the related DocTypes:
   - `governance doctype institutional_policy`
   - `governance doctype institutional_policy_audience`
   - `governance doctype policy_audience`
3. Verify the child table exists.
4. Re-test applicant policy readiness/API and confirm no new `Policy schema mismatch` logs are created.

---
title: "Student Applicant: The Admission Record of Truth"
slug: student-applicant
category: Admission
doc_order: 4
version: "1.20.0"
last_change_date: "2026-03-17"
summary: "Manage applicant lifecycle from invitation to promotion, with readiness checks across profile, documents, policies, recommendations, school-scoped health gating, and the admissions-to-enrollment bridge."
seo_title: "Student Applicant: The Admission Record of Truth"
seo_description: "Manage applicant lifecycle from invitation to promotion, with readiness checks across profile, documents, policies, recommendations, school-scoped health gating, and the admissions-to-enrollment bridge."
---

## Student Applicant: The Admission Record of Truth

## Before You Start (Prerequisites)

- Create [**Organization**](/docs/en/organization/) and [**School**](/docs/en/school/) first (required anchors).
- If you intend to require applicant consent, configure active applicant-scoped policies first ([**Institutional Policy**](/docs/en/institutional-policy/) + active [**Policy Version**](/docs/en/policy-version/)).
- Define required [**Applicant Document Type**](/docs/en/applicant-document-type/) records and [**Applicant Interview**](/docs/en/applicant-interview/) review workflow before approval/promotion decisions. Define [**Applicant Health Profile**](/docs/en/applicant-health-profile/) workflow when the school requires health clearance for approval.
- Ensure student-profile fields needed for promotion (`student_date_of_birth`, `student_gender`, `student_mobile_number`, `student_joining_date`, `student_first_language`, `student_nationality`, `residency_status`) are collected in the applicant profile step.
- Optional promotion profile links `cohort` and `student_house` can also be captured on the applicant and are copied into the promoted `Student` record when set.
- If your admissions flow uses offers before promotion, configure [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) and [**Admission Settings**](/docs/en/admission-settings/).

### How Policy Acknowledgement Becomes Mandatory

There is no manual toggle on `Student Applicant` for "policy required". It is computed automatically by server logic.

Policy acknowledgement is mandatory for an applicant when at least one active policy candidate matches all of these conditions:

1. `Institutional Policy.is_active = 1`
2. `Policy Version.is_active = 1` for that policy
3. `Institutional Policy.applies_to` includes `Applicant`
4. Policy organization applies to the applicant organization scope (nearest ancestor policy per `policy_key` is selected)
5. Policy school scope matches (`school` blank/global, or in applicant school lineage: applicant school or any ancestor/parent school)

If no policy rows match those rules, policy acknowledgement is not required for that applicant.

### How Admission Officer / Admission Manager Knows It Is Mandatory

Use the applicant readiness outputs, not guesswork:

1. Desk `Student Applicant` form:
   - `Policies Summary` shows a policy matrix with status, signer(s), signed timestamp, and version link.
   - `Documents Summary` is the canonical admissions-staff evidence view and shows requirement rows plus submitted-file rows. Staff review uploaded files directly there and do not need to reason about `Applicant Document` vs `Applicant Document Item`.
   - `Health Summary` shows cleared/pending state, health profile link, reviewer metadata, and declaration metadata.
   - `Review Assignments Summary` shows completed assignment decisions for Health and Overall Application (document review truth remains in `Documents Summary`).
   - `Review Snapshot` includes readiness issues from `get_readiness_snapshot`.
2. Admissions Cockpit applicant workspace:
   - applicant-centered workspace shows the same requirement/submission model as Desk
   - cockpit cards show interview count plus the latest interview summary/open action
   - latest interview feedback status is derived only from submitted `Applicant Interview Feedback` rows
   - admissions roles review evidence there without leaving applicant context
3. Approval action:
   - `Approve` is blocked by server guard (`approve_application` -> `_validate_ready_for_approval`) until readiness requirements are met (policies/documents/profile/recommendations and health only when required by school policy).
   - Error text includes missing policy acknowledgement details.
4. Applicant portal:
   - `/admissions` -> Policies page shows each required policy as `Pending acknowledgement` or `Acknowledged`.

`Student Applicant` is the core admissions record in Ifitwala Ed. It is where intent becomes an application, review becomes decision, and decision becomes student promotion.

## Why It Matters

- Keeps one lifecycle record from `Draft` to `Promoted`.
- Preserves institutional anchor (`organization`, `school`) as immutable once created.
- Centralizes readiness checks across profile, policies, documents, recommendations, and school-scoped health requirements.
- Links admissions to student creation and downstream enrollment operations.
- Anchors the applicant side of the admissions-to-enrollment bridge while keeping offer workflow outside `application_status`.
- Carries forward inquiry intent so teams do not restart data entry from zero.

<Callout type="tip" title="Production value">
This is where admissions correctness is enforced. Client UX helps, but status transitions and edit rules are ultimately server-controlled.
</Callout>

## Why Teams Feel the Difference

- **Paperless edge**: policy acknowledgement is handled in-portal with a permanent `Policy Acknowledgement` record (`acknowledged_by`, `acknowledged_at`, `policy_version`, context binding).
- **Speed edge**: inquiry invite flow pre-fills applicant identity and intent fields, then admissions staff focus on review and decision instead of retyping.
- **Compliance edge**: admissions files are routed through governed records (`Applicant Document`) instead of random direct attachments on the applicant.
- **Operations edge**: applicant timeline now records document upload/replace events and applicant-document review/edit events for fast audit trace.

<Callout type="note" title="Digital signature scope">
Applicant policy acknowledgement in portal requires explicit electronic-signature controls: typed signer name must match the expected signer name shown for the selected policy, and legal attestation must be confirmed before server insert. Family-scoped admissions policies sign on `Guardian` context; child-scoped admissions policies sign on `Student Applicant` context. Evidence remains the immutable `Policy Acknowledgement` record with server timestamp.
</Callout>

## Offer and Enrollment Bridge

`Student Applicant` stays the admissions record of truth, but it does not own the family-facing offer lifecycle.

Current runtime split:

- `Student Applicant.application_status` remains the internal admissions lifecycle (`Approved` is still the committee-approved applicant decision).
- [**Applicant Enrollment Plan**](/docs/en/applicant-enrollment-plan/) owns placement planning, `Offer Sent`, `Offer Accepted`, and `Offer Declined`.
- The applicant user on `Student Applicant` is reserved for the future student identity, not for guardians.
- If a latest Applicant Enrollment Plan exists, promotion is blocked until that latest plan is `Offer Accepted` or already `Hydrated`.
- Identity upgrade remains separate from promotion and can auto-run when the first active [**Program Enrollment**](/docs/en/program-enrollment/) is created or reactivated for the promoted student.

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use lifecycle actions (`approve_application`, `reject_application`, `promote_to_student`) to keep readiness and audit behavior consistent.</Do>
  <Do>Use the Desk invite/resend portal actions so `portal_account_email`, user linkage, and role assignment remain server-owned.</Do>
  <Dont>Directly mutate protected identity/anchor fields (`inquiry`, `student`, `applicant_user`, `applicant_contact`, `portal_account_email`).</Dont>
  <Dont>Treat UI-only state as truth; rely on server readiness checks before approval and promotion decisions.</Dont>
</DoDont>

## Lifecycle States

| Status | Typical meaning |
|---|---|
| `Draft` | Staff-created shell |
| `Invited` | Applicant user invited / inquiry conversion |
| `In Progress` | Family is actively filling data |
| `Submitted` | Family submitted |
| `Under Review` | Staff review stage |
| `Missing Info` | Returned for corrections |
| `Approved` | Decision approved |
| `Rejected` | Terminal rejected |
| `Promoted` | Converted to Student |

## What `Invited` Means in Practice

`Invited` means admissions has opened the application lifecycle for the applicant. In current code, this status can be reached through two server-owned paths:

- **Staff invite flow** (`ifitwala_ed/api/admissions_portal.py::invite_applicant`):
  - creates or reuses `User`
  - assigns role `Admissions Applicant`
  - anchors to `Student Applicant.applicant_contact` (Contact)
  - stores chosen login email in `Student Applicant.portal_account_email`
  - derives `Student Applicant.applicant_email` from Contact primary email
  - links `Student Applicant.applicant_user`
  - moves status `Draft -> Invited` (when currently `Draft`)
  - sends welcome/password email using framework-supported email methods
- **Inquiry conversion flow** (`invite_to_apply` / `from_inquiry_invite`):
  - creates `Student Applicant` directly in `Invited`
  - pre-fills identity and inquiry intent fields
  - ensures Inquiry has a linked `Contact` and carries it to `Student Applicant.applicant_contact`
  - ensures Contact has a `Dynamic Link` to the created/reused `Student Applicant` (idempotent sync)
  - derives `Student Applicant.applicant_email` from Contact email rows
  - does **not** by itself guarantee portal login access until an applicant `User` is linked

### How Admissions Invites the Applicant (Portal Login Invite)

Portal login invite is done directly from Desk on the `Student Applicant` form:

1. Open the applicant record.
2. Click `Actions` -> `Invite Applicant Portal` (or `Resend Portal Invite` if already linked) when `Admission Settings.admissions_access_mode = Single Applicant Workspace`.
3. Click `Actions` -> `Invite Family Collaborator` when `Admission Settings.admissions_access_mode = Family Workspace`.
4. Pick an email from Contact email options, or enter a new one in the same dialog.

This triggers the server flow `invite_applicant` and requires:

1. `student_applicant` (the Student Applicant document name)
2. `email` (the applicant login email to invite; always upserted to Contact Email)

Behavior in code:

- email is normalized to lower-case and trimmed before processing
- invite email is validated against applicant contact ownership (cross-contact drift is blocked)
- invite email is upserted into `Contact Email` for the applicant contact
- applicant contact is kept linked to `Student Applicant` via Contact `Dynamic Link` (idempotent sync)
- if user does not exist, a `User` is created with that email
- role `Admissions Applicant` is ensured on that user
- invited user is forced `enabled = 1` so login is not blocked by disabled account state
- `Student Applicant.applicant_user` is set to that user identity
- `Student Applicant.portal_account_email` is set to the chosen invite email
- if applicant is already linked to a different email/user, invite is blocked
- family collaborator eligibility is limited to guardian rows where `can_consent = 1` and a guardian personal email exists

### Family Workspace Login and Collaboration

When `Admission Settings.admissions_access_mode = Family Workspace`, `/admissions` becomes a family workspace instead of a single-applicant workspace.

- family collaborators use role `Admissions Family`
- access is resolved from explicit `Student Applicant Guardian` rows with `can_consent = 1`
- `can_consent` is the canonical admissions-stage signer-authority flag and may be enabled for more than one guardian
- one adult user can be linked to multiple active applicants and switch between them inside `/admissions`
- collaboration is multi-user, not shared-login:
  - each adult has their own `User`
  - saves, uploads, and acknowledgements are attributed to the actual actor
- child identity field `Student Applicant.applicant_user` remains reserved for the future student identity and is not reused as a family workspace identity
- applicant profile and health saves use optimistic concurrency tokens (`record_modified` / `expected_modified`) so one adult cannot silently overwrite another adult's more recent save

<Callout type="warning" title="Login identity source of truth">
The applicant username/email is `Student Applicant.portal_account_email` (set by `invite_applicant` from the selected Contact email). This is the identity used to sign in to the admissions portal.
</Callout>

<Callout type="info" title="If applicant did not receive the invite email">
Use `Actions` -> `Resend Portal Invite` on the same applicant and submit the same email again. This re-sends the portal invite email for the linked applicant user and keeps the same portal identity.
</Callout>

<Callout type="warning" title="Invite email failure handling">
If email delivery fails, portal linkage still succeeds (`User` + role + applicant link). Family can use `Forgot Password` on `/login` and sign in with `portal_account_email`.
</Callout>

### How Applicant Login Works

- Applicant opens `/admissions`.
- Server gate (`ifitwala_ed/www/admissions/index.py`) requires:
  - authenticated user (not Guest)
  - either:
    - `Admissions Applicant` with applicant access resolved from `Student Applicant.applicant_user`
    - `Admissions Family` with family-workspace mode enabled and explicit guardian linkage to one-or-more applicants
- If checks fail, user is redirected to login/logout-login flow.

### Applicant Credentials and URL

- Portal URL: `/admissions` (for example `https://<your-domain>/admissions`)
- Document upload URL: `/admissions/documents`
- Username/email: `Student Applicant.portal_account_email` (chosen by admissions from Contact emails during invite)
- In family workspace mode, invited adult collaborators log in with their own invited guardian/family user email, not with `Student Applicant.portal_account_email`.
- Password:
  - new invited user: set via welcome/reset email sent during invite
  - existing user: use existing password (or reset via forgot password)

### How Applicant Uploads Documents

- After login, applicant uses the admissions SPA documents page.
- Upload goes through `ifitwala_ed/api/admissions_portal.py::upload_applicant_document`.
- Edits/uploads are allowed only when applicant status is one of:
  - `Invited`
  - `In Progress`
  - `Missing Info`
- Upload creates/updates governed `Applicant Document` records and routes files through classification/governance services.

## Child Table (Included in Parent)

`guardians` uses child table **Student Applicant Guardian**:

- `guardian` -> `Guardian`
- `contact` -> `Contact` (tracked guardian contact used for carry-over)
- `relationship` (Mother/Father/etc.)
- `is_primary`
- `can_consent` (canonical signer-authority flag; shown in the admissions workspace as `Authorized signer for school documents and consents`)
- guardian identity/profile fields mirrored from `Guardian` (`salutation`, names, email, mobile, work fields, guardian flags)
- `use_applicant_contact` to explicitly reuse `Student Applicant.applicant_contact` for a guardian row
- applicant portal save validation enforces required guardian fields per row: first name, last name, personal email, mobile phone, and photo
- guardian personal/work emails are validated as email format; guardian mobile/work phones are validated as phone format
- non-signing emergency or temporary-care guardians may remain linked with `can_consent = 0`

No standalone child-doc page is required; behavior is owned by the parent lifecycle.

## Where Student Applicant Is Used Across the ERP

- **Admissions conversion**:
  - linked from [**Inquiry**](/docs/en/inquiry/)
  - created by `from_inquiry_invite`
- **Decision support records**:
  - [**Applicant Document**](/docs/en/applicant-document/)
  - [**Applicant Health Profile**](/docs/en/applicant-health-profile/)
  - [**Applicant Interview**](/docs/en/applicant-interview/)
- **Portal surfaces**:
  - website entry `/admissions` (`ifitwala_ed/www/admissions/index.py`)
  - SPA pages: overview, profile, documents, health, policies, submit, status
  - API service: `ifitwala_ed.api.admissions_portal.*`
  - next-actions contract: document upload is blocking only when required docs are missing; uploaded docs pending review are surfaced as under-review (non-blocking) for applicants, and Submit page shows an explicit "Awaiting admissions review" banner while still allowing submission
- **Promotion linkage**:
  - `Student.student_applicant` link
  - `promote_to_student` creates/links `Student`
- **File governance**:
  - direct attachments blocked except `applicant_image`
  - governed upload endpoint: `ifitwala_ed.utilities.governed_uploads.upload_applicant_image`
  - admissions portal self-upload endpoint: `ifitwala_ed.api.admissions_portal.upload_applicant_profile_image`
  - admissions portal guardian photo upload endpoint: `ifitwala_ed.api.admissions_portal.upload_applicant_guardian_image`
  - admissions portal applicant/guardian photo uploads accept only `JPG`/`JPEG`/`PNG`, reject `HEIC`/`HEIF`, rewrite accepted uploads to server-owned stripped `JPEG`, and enforce `10 MB` / `25 megapixel` limits before file dispatcher storage
  - all other admissions docs routed via `Applicant Document` + file classification
- **Recommendation intake (runtime)**:
  - external recommender submissions use a separate intake surface (`/admissions/recommendation/<token>`) and do not use applicant portal authentication
  - supports multiple confidential letters per applicant using per-request `Applicant Document Item` slots (`item_key`)
  - admissions creates/re-sends/revokes `Recommendation Request` records; recommender submission is sealed in `Recommendation Submission`
  - applicant portal surfaces recommendation **status only** through snapshot completeness and status summary
  - applicant documents and applicant uploads exclude recommendation-template target document types
  - if a school wants the applicant to upload a recommendation letter directly, that must use a normal `Applicant Document Type`, not `Recommendation Template`
  - architecture and contract reference: `ifitwala_ed/docs/admission/06_recommendation_intake_architecture.md`
- **Governance policy engine**:
  - `Policy Acknowledgement.context_doctype = Student Applicant`
  - policy readiness pulled from active Institutional Policy versions
- **Operational dashboards**:
  - morning brief admissions pulse (`tabStudent Applicant` weekly status counts)
  - staff admissions cockpit route `/staff/admission-cockpit` (`ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`)
  - admissions cockpit API `ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data` (applicant-stage Kanban + blocker strip)
  - cockpit applicant cards show interview count, latest interview context, and direct open action using feedback completion from `Applicant Interview Feedback`
- **Reviewer workflow**:
  - submission trigger creates Overall Application review assignments (`application_status` transition to `Submitted`)
  - admissions roles review evidence in applicant context only:
    - Desk `Student Applicant.documents_summary`
    - admissions cockpit applicant workspace overlay
  - non-admissions reviewers handle `Applicant Document Item` assignments in Focus
  - desk shows completed Health and Overall Application assignment decisions in `review_assignments_summary`
  - staff morning brief surface (`ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`) renders applicant status breakdown
- **Schedule module touchpoint**:
  - Program Enrollment Tool offers `Student Applicant` as a source option in UI.

<Callout type="warning" title="Current tool behavior">
Program Enrollment Tool currently implements fetch logic for `Cohort` and `Program Enrollment` sources. The `Student Applicant` source appears in UI options but is not yet handled in `_fetch_students`.
</Callout>

## Inquiry Carry-Over (Speed)

When admissions triggers invite-to-apply from an inquiry, the applicant is prefilled with:

- Identity: `first_name`, `last_name`
- Intent: `program`, `academic_year`, `term`
- Traceability: `inquiry`
- Lifecycle start: `application_status = Invited`
- Institutional anchor at invite time: `school` (required) and `organization` (provided or derived)
- Contact anchor: `applicant_contact` from Inquiry contact linkage, with `applicant_email` derived from Contact email rows

This is deterministic server-side mapping in `from_inquiry_invite`, so teams avoid duplicate entry and keep source lineage.

## Fresh Site / New School Prerequisites

For a brand-new site or a newly onboarded school, this is what must exist before policy-aware applicant workflow behaves correctly.

### Minimum to create the first Student Applicant

1. Admissions staff user with admissions role (`Admission Officer` or `Admission Manager`), because server validation blocks non-admissions creation.
2. A valid `Organization` and `School` pair, because `Student Applicant` requires both and locks them after insert.
3. Applicant identity fields (`first_name`, `last_name`) from the doctype required fields.

### Required for policy-governed admissions flow

1. `Institutional Policy` rows scoped to the applicant organization/school:
   - `is_active = 1`
   - `applies_to` includes `Applicant`
   - organization scope aligns with school organization ancestry
2. At least one active `Policy Version` per policy that should be acknowledged:
   - `institutional_policy` points to active policy
   - `is_active = 1`
3. Schema is migrated with `Institutional Policy.applies_to` present, or policy resolution/readiness fails (`Policy schema mismatch`).

### Required for approval-readiness path

1. Required `Applicant Document Type` records are configured (`is_required = 1`, `is_active = 1`) for the organization/school ancestor scope you expect (parent-scope document types apply to descendants).
2. Applicant has corresponding `Applicant Document` requirement rows and each required one is satisfied either by approved submission-backed evidence or an explicit admissions override (`Waived` / `Exception Approved`).
3. If `School.require_health_profile_for_approval = 1`, `Applicant Health Profile.review_status = Cleared`.
4. Applicant profile information required for Student promotion is complete.

### Optional but commonly expected in production

1. Media consent policy chain (`policy_key = media_consent` + active version + acknowledgement), if you expect applicant image publish behavior during promotion.
2. Applicant portal invite flow (`invite_applicant`) so families can acknowledge policies in `/admissions`.

## Lifecycle and Linked Documents

<Steps title="Student Applicant Lifecycle">
  <Step title="Create">
    Create applicant identity and institutional anchor (`organization`, `school`).
  </Step>
  <Step title="Collect Evidence">
    Progress through lifecycle states while collecting policies, documents, health, and interview evidence.
  </Step>
  <Step title="Review Readiness">
    Use readiness snapshot checks before approval or rejection decisions.
  </Step>
  <Step title="Offer and Acceptance">
    When the school uses the admissions-to-enrollment bridge, manage placement and family offer response in `Applicant Enrollment Plan`.
  </Step>
  <Step title="Promote">
    Promote approved applicants to `Student` records, copy governed artifacts forward, and optionally auto-hydrate a draft Program Enrollment Request from an accepted Applicant Enrollment Plan.
  </Step>
</Steps>

## Reporting and Analytics

- No dedicated Script/Query Report declares `Student Applicant` as `ref_doctype`.
- Current analytics are API/widget driven (admissions portal completeness + morning brief pulse).

## Related Docs

<RelatedDocs
  slugs="inquiry,applicant-enrollment-plan,applicant-document-type,applicant-document,applicant-health-profile,applicant-interview,institutional-policy,policy-version,policy-acknowledgement"
  title="Related Applicant Lifecycle Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-10)

- **DocType schema file**: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.json`
- **Controller file**: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- **Required fields (`reqd=1`)**:
  - `first_name` (`Data`)
  - `last_name` (`Data`)
  - `organization` (`Link` -> `Organization`)
  - `school` (`Link` -> `School`)
- **Lifecycle hooks in controller**: `before_save`, `on_update`, `validate`
- **Operational/public methods**: `mark_in_progress`, `submit_application`, `mark_under_review`, `mark_missing_info`, `withdraw_application`, `approve_application`, `reject_application`, `promote_to_student`, `apply_system_manager_override`, `has_required_policies`, `has_required_documents`, `health_review_complete`, `has_required_interviews`, `get_readiness_snapshot`, `academic_year_intent_query`, `school_by_organization_query`

- **DocType**: `Student Applicant` (`ifitwala_ed/admission/doctype/student_applicant/`)
- **Naming series**: `format:APPL-{MM}-{YYYY}-{###}` (for example `APPL-02-2026-001`)
- **Desk surfaces**:
  - form logic/buttons/readiness widgets in `ifitwala_ed/admission/doctype/student_applicant/student_applicant.js`
  - interview actions on applicant form include:
    - `Create Interview` (new prefilled `Applicant Interview` draft)
    - `Schedule Interview` (creates interview + linked `School Event` via scheduling API)
  - workspace cards in `ifitwala_ed/admission/workspace/admission/admission.json`
- **Admissions portal SPA surfaces**:
  - entrypoint `ifitwala_ed/ui-spa/src/apps/admissions/main.ts`
  - router `ifitwala_ed/ui-spa/src/router/admissions.ts` (history base `/admissions`)
  - pages:
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue` (includes optional guardian intake section controlled by Admission Settings)
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantPolicies.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantSubmit.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue`
  - service layer `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`
  - website gate `ifitwala_ed/www/admissions/index.py` validates role/link before app boot
- **Key validations**:
  - institutional anchor required and immutable
  - academic year open/visible and within school scope
  - attachment guard (only `applicant_image` directly on this doctype)
  - status transition matrix enforcement
- **Readiness field model**:
  - no stored `ready` field on the DocType
  - readiness is computed on demand by `get_readiness_snapshot`
  - `review_snapshot`, `interviews_summary`, `health_summary`, `policies_summary`, `documents_summary` are HTML UI summary fields
  - hidden field present: `title` (system/display helper, not readiness truth)
- **Whitelisted lifecycle methods**:
  - `mark_in_progress`
  - `submit_application`
  - `mark_missing_info`
  - `approve_application`
  - `reject_application(reason)`
  - `promote_to_student`
  - `apply_system_manager_override(updates, reason)`
  - `get_readiness_snapshot`
- **Readiness computation**:
  - `has_required_policies()` -> blocking
  - `has_required_documents()` -> blocking
  - `health_review_complete()` -> blocking only when `School.require_health_profile_for_approval = 1`
  - `has_required_interviews()` -> tracked; not currently part of blocking `ready` boolean
  - repeatable required document types are satisfied when approved submission count meets the required count, or when the parent requirement has an explicit admissions override
  - interview summary shows a latest interview link/panel snapshot plus a compact latest-5 table with Date/Time (linked to interview), Interviewer, and feedback completion status
  - interview feedback completion is derived only from submitted `Applicant Interview Feedback` rows; parent interview notes remain operational context only
  - `review_assignments_summary` is assignment-focused (Health + Overall Application); document reviewer metadata is surfaced in `documents_summary`
- **Promotion side-effects (`promote_to_student`)**:
  - preconditions: applicant status must be `Approved` and `student_joining_date` is required
  - if a latest `Applicant Enrollment Plan` exists, that latest plan must already be `Offer Accepted` or `Hydrated`
  - creates/links `Student`, writes `Student.student_applicant`, then sets applicant status to `Promoted`
  - copies applicant `cohort` and `student_house` links into the promoted `Student` when those applicant fields are populated
  - creates/syncs `Student Patient` from Applicant Health Profile data
  - copies approved admissions documents into Student-owned governed files; current runtime excludes only rows whose `promotion_target` is explicitly non-`Student`
  - copies applicant image through governed file dispatcher into Student profile image slot
  - when `Admission Settings.auto_hydrate_enrollment_request_after_promotion = 1`, auto-hydrates a draft `Program Enrollment Request` from the accepted Applicant Enrollment Plan
  - does **not** create Guardian/User portal access or mutate portal roles
  - does **not** create `Program Enrollment` directly
  - does **not** send welcome email or print-format welcome kit by itself
  - invite email behavior exists in staff portal endpoint `invite_applicant` (separate flow)
- **Identity upgrade side-effects (`upgrade_identity`)**:
  - requires an active `Program Enrollment` for the promoted student
  - the same server-owned logic is reachable from the named `upgrade_identity` action and from the first active `Program Enrollment` transition
  - provisions the applicant user as `Student` access and removes `Admissions Applicant`
  - provisions guardians only from explicit applicant guardian rows; there is no applicant-contact fallback guardian creation
  - applicant user is reserved for the student identity and cannot be reused as a guardian user
  - links guardians to Student in canonical Student guardian rows when guardian rows exist
  - carries `Student Applicant Guardian.can_consent` into `Student Guardian.can_consent` so signer authority survives promotion and later guardian policy workflows
  - syncs `Student.siblings` from shared explicit guardians carried forward from admissions
  - links tracked guardian Contact rows to `Student Applicant`, `Guardian`, and promoted `Student`
  - is idempotent (re-run does not duplicate users or guardian links)
  - ordinary edits to an already-active `Program Enrollment` do not re-trigger the automatic identity-upgrade path
- **Link query endpoints**:
  - `academic_year_intent_query`
  - `school_by_organization_query`
- **Portal API endpoints** (`ifitwala_ed/api/admissions_portal.py`) used by portal pages/service:
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
- **Admissions policy overlay (SPA)**:
  - page launcher: `ui-spa/src/pages/admissions/ApplicantPolicies.vue`
  - overlay component: `ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue`
  - acknowledgement submit: `admissionsService.acknowledgePolicy` -> `ifitwala_ed.api.admissions_portal.acknowledge_policy`
  - acknowledgement requires `typed_signature_name` + `attestation_confirmed` and server-validates typed name against expected applicant signer identity before insert

## Contract Matrix

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
- `ifitwala_ed/api/test_admissions_portal.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/governance/doctype/institutional_policy/test_institutional_policy.py`

| Concern | Canonical owner | Code refs | Test refs |
|---|---|---|---|
| Schema / DocType | Applicant-stage and student-stage guardian relationship rows carry canonical signer authority; policy audience remains on Institutional Policy | `admission/doctype/student_applicant_guardian/student_applicant_guardian.json`, `students/doctype/student_guardian/student_guardian.json`, `governance/doctype/institutional_policy/institutional_policy.json` | `admission/doctype/student_applicant/test_student_applicant.py`, `governance/doctype/institutional_policy/test_institutional_policy.py` |
| Controller / workflow logic | Promotion carries signer authority forward; policy audience uses canonical `Table MultiSelect` rows; guardian/student acknowledgement visibility respects signer authority | `admission/doctype/student_applicant/student_applicant.py`, `governance/doctype/institutional_policy/institutional_policy.py`, `governance/doctype/policy_acknowledgement/policy_acknowledgement.py`, `api/guardian_policy.py` | `admission/doctype/student_applicant/test_student_applicant.py`, `api/test_guardian_phase2.py`, `governance/doctype/institutional_policy/test_institutional_policy.py` |
| API endpoints | Admissions family invite eligibility and guardian policy visibility use the signer-authority contract; admissions policy acknowledgement remains a named workflow | `api/admissions_portal.py`, `api/guardian_policy.py` | `api/test_admissions_portal.py`, `api/test_guardian_phase2.py` |
| SPA / UI surfaces | Admissions family guardian rows present signer authority explicitly; guardian portal policy page consumes the filtered policy overview | `ui-spa/src/pages/admissions/ApplicantProfile.vue`, `ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue`, `ui-spa/src/pages/guardian/GuardianPolicies.vue` | `ui-spa/src/pages/guardian/__tests__/GuardianPolicies.test.ts` |
| Reports / dashboards / briefings | Staff policy communication defaults and guardian policy status views follow the canonical audience-row contract | `api/policy_communication.py`, `api/policy_signature.py`, `ui-spa/src/pages/guardian/GuardianPolicies.vue` | `api/test_guardian_phase2.py` |
| Scheduler / background jobs | None in this signer-authority workflow | None | None |
| Tests | Coverage exists for policy audience normalization, guardian policy filtering, and promotion carry-forward of signer authority | `governance/doctype/institutional_policy/test_institutional_policy.py`, `api/test_guardian_phase2.py`, `admission/doctype/student_applicant/test_student_applicant.py`, `api/test_admissions_portal.py` | Implemented |

### Troubleshooting: `Policy schema mismatch` (`applies_to` storage)

If you see an error log like:

- title: `Policy schema mismatch`
- caller: `StudentApplicant.has_required_policies`
- doctype: `Institutional Policy`
- missing_table: `Institutional Policy Audience`
- missing_link_doctype: `Policy Audience`

it means code expects the canonical `Institutional Policy.applies_to` child-table storage, but your site schema is missing the related audience DocTypes or child table.

Current implementation impact:

- `StudentApplicant.has_required_policies()` cannot evaluate required policies and marks readiness as not OK with a schema-error issue.
- `ifitwala_ed/api/admissions_portal.py::get_applicant_policies` throws a blocking error (`throw=True`) and policy UI cannot load.

What to do (site operations):

1. Run migrations for the affected site:
   - `bench --site <site-name> migrate`
2. If the schema is still missing, reload the related DocTypes:
   - `bench --site <site-name> reload-doc governance doctype institutional_policy`
   - `bench --site <site-name> reload-doc governance doctype institutional_policy_audience`
   - `bench --site <site-name> reload-doc governance doctype policy_audience`
3. Verify the child table exists:
   - `bench --site <site-name> mariadb -e "SHOW TABLES LIKE 'tabInstitutional Policy Audience';"`
4. Re-test applicant policy readiness/API and confirm no new `Policy schema mismatch` logs are created.

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Admission Officer` | Yes | Yes | Yes | Yes | Scoped to applicant visibility |
| `Academic Admin` | Yes | No | No | No | Scoped read visibility |
| `Academic Assistant` | No | No | No | No | Not in runtime admissions-file access contract |
| `Admissions Applicant` | Yes | Yes | No | No | Own applicant only (self-link enforced) |
| `Admissions Family` | Yes | Yes | No | No | Family workspace only; explicit guardian linkage required |

Runtime controller rules (server):
- Only admissions staff can create new records.
- Admissions and academic-admin reads are scope-gated by organization/school visibility; visibility can follow linked student school context during school transfers.
- Status changes must use lifecycle methods (direct writes are blocked).
- Family/applicant editability depends on current status (`Invited/In Progress/Missing Info`).
- Terminal states (`Rejected`, `Promoted`) are locked except explicit System Manager override flow.
- `inquiry`, `student`, `applicant_user`, `applicant_contact`, and `portal_account_email` are immutable and only set through named flows.
- Direct `File` clutter is blocked on this doctype except `applicant_image`; admissions evidence belongs on [**Applicant Document**](/docs/en/applicant-document/).

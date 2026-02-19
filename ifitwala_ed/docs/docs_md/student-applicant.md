---
title: "Student Applicant: The Admission Record of Truth"
slug: student-applicant
category: Admission
doc_order: 4
summary: "Manage applicant lifecycle from invitation to promotion, with readiness checks, governed files, policy acknowledgements, and portal access."
seo_title: "Student Applicant: The Admission Record of Truth"
seo_description: "Manage applicant lifecycle from invitation to promotion, with readiness checks, governed files, policy acknowledgements, and portal access."
---

## Student Applicant: The Admission Record of Truth

## Before You Start (Prerequisites)

- Create `Organization` and `School` first (required anchors).
- If you intend to require applicant consent, configure active applicant-scoped policies first (`Institutional Policy` + active `Policy Version`).
- Define required document types and health/interview review workflow before approval/promotion decisions.

### How Policy Acknowledgement Becomes Mandatory

There is no manual toggle on `Student Applicant` for "policy required". It is computed automatically by server logic.

Policy acknowledgement is mandatory for an applicant when at least one active policy candidate matches all of these conditions:

1. `Institutional Policy.is_active = 1`
2. `Policy Version.is_active = 1` for that policy
3. `Institutional Policy.applies_to` includes `Applicant`
4. Policy organization applies to the applicant organization scope (nearest ancestor policy per `policy_key` is selected)
5. Policy school scope matches (`school` blank/global or equals applicant `school`)

If no policy rows match those rules, policy acknowledgement is not required for that applicant.

### How Admission Officer / Admission Manager Knows It Is Mandatory

Use the applicant readiness outputs, not guesswork:

1. Desk `Student Applicant` form:
   - `Policies Summary` shows missing policy keys/titles when required acknowledgements are outstanding.
   - `Review Snapshot` includes readiness issues from `get_readiness_snapshot`.
2. Approval action:
   - `Approve` is blocked by server guard (`approve_application` -> `_validate_ready_for_approval`) until required policy acknowledgements are complete.
   - Error text includes missing policy acknowledgement details.
3. Applicant portal:
   - `/admissions` -> Policies page shows each required policy as `Pending acknowledgement` or `Acknowledged`.

`Student Applicant` is the core admissions record in Ifitwala Ed. It is where intent becomes an application, review becomes decision, and decision becomes student promotion.

## Why It Matters

- Keeps one lifecycle record from `Draft` to `Promoted`.
- Preserves institutional anchor (`organization`, `school`) as immutable once created.
- Centralizes readiness checks across policies, documents, and health.
- Links admissions to student creation and downstream enrollment operations.
- Carries forward inquiry intent so teams do not restart data entry from zero.

<Callout type="tip" title="Production value">
This is where admissions correctness is enforced. Client UX helps, but status transitions and edit rules are ultimately server-controlled.
</Callout>

## Why Teams Feel the Difference

- **Paperless edge**: policy acknowledgement is handled in-portal with a permanent `Policy Acknowledgement` record (`acknowledged_by`, `acknowledged_at`, `policy_version`, context binding).
- **Speed edge**: inquiry invite flow pre-fills applicant identity and intent fields, then admissions staff focus on review and decision instead of retyping.
- **Compliance edge**: admissions files are routed through governed records (`Applicant Document`) instead of random direct attachments on the applicant.

<Callout type="note" title="Digital signature scope">
Current implementation is an explicit acknowledge action with timestamped audit trail. It does not capture a handwritten/typed signature artifact field.
</Callout>

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
  - links `Student Applicant.applicant_user`
  - moves status `Draft -> Invited` (when currently `Draft`)
  - sends welcome/password email using framework-supported email methods
- **Inquiry conversion flow** (`invite_to_apply` / `from_inquiry_invite`):
  - creates `Student Applicant` directly in `Invited`
  - pre-fills identity and inquiry intent fields
  - does **not** by itself guarantee portal login access until an applicant `User` is linked

### How Applicant Login Works

- Applicant opens `/admissions`.
- Server gate (`ifitwala_ed/www/admissions/index.py`) requires:
  - authenticated user (not Guest)
  - role `Admissions Applicant`
  - exactly one linked `Student Applicant` via `applicant_user`
- If checks fail, user is redirected to login/logout-login flow.

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
- `relationship` (Mother/Father/etc.)
- `is_primary`
- `can_consent`

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
  - SPA pages: overview, documents, health, policies, submit
  - API service: `ifitwala_ed.api.admissions_portal.*`
- **Promotion linkage**:
  - `Student.student_applicant` link
  - `promote_to_student` creates/links `Student`
- **File governance**:
  - direct attachments blocked except `applicant_image`
  - governed upload endpoint: `ifitwala_ed.utilities.governed_uploads.upload_applicant_image`
  - all other admissions docs routed via `Applicant Document` + file classification
- **Governance policy engine**:
  - `Policy Acknowledgement.context_doctype = Student Applicant`
  - policy readiness pulled from active Institutional Policy versions
- **Operational dashboards**:
  - morning brief admissions pulse (`tabStudent Applicant` weekly status counts)
  - staff morning brief surface (`ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`) renders applicant status breakdown
- **Schedule module touchpoint**:
  - Program Enrollment Tool offers `Student Applicant` as a source option in UI.

<Callout type="warning" title="Current tool behavior">
Program Enrollment Tool currently implements fetch logic for `Cohort` and `Program Enrollment` sources. The `Student Applicant` source appears in UI options but is not yet handled in `_fetch_students`.
</Callout>

## Inquiry Carry-Over (Speed)

When admissions triggers invite-to-apply from an inquiry, the applicant is prefilled with:

- Identity: `first_name`, `middle_name`, `last_name`
- Intent: `program`, `academic_year`, `term`
- Traceability: `inquiry`
- Lifecycle start: `application_status = Invited`
- Institutional anchor at invite time: `school` (required) and `organization` (provided or derived)

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

1. Required `Applicant Document Type` records are configured (`is_required = 1`, `is_active = 1`) for the organization/school scope you expect.
2. Applicant has corresponding `Applicant Document` rows and required ones reach `review_status = Approved`.
3. `Applicant Health Profile.review_status = Cleared`.

### Optional but commonly expected in production

1. Media consent policy chain (`policy_key = media_consent` + active version + acknowledgement), if you expect applicant image publish behavior during promotion.
2. Applicant portal invite flow (`invite_applicant`) so families can acknowledge policies in `/admissions`.

## Lifecycle and Linked Documents

1. Create applicant identity and institutional anchor (`organization`, `school`).
2. Progress through lifecycle states while collecting policies, documents, health, and interview evidence.
3. Use readiness snapshot checks before approval or rejection decisions.
4. Promote approved applicants to `Student` records and copy governed artifacts forward.

## Technical Notes (IT)

### Schema and Controller Snapshot

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
  - workspace cards in `ifitwala_ed/admission/workspace/admission/admission.json`
- **Admissions portal SPA surfaces**:
  - entrypoint `ifitwala_ed/ui-spa/src/admissions/main.ts`
  - router `ifitwala_ed/ui-spa/src/router/admissions.ts` (history base `/admissions`)
  - pages:
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue`
    - `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue`
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
  - `health_review_complete()` -> blocking
  - `has_required_interviews()` -> tracked; not currently part of blocking `ready` boolean
- **Promotion side-effects (`promote_to_student`)**:
  - creates/links `Student`, writes `Student.student_applicant`, then sets applicant status to `Promoted`
  - copies applicant image through governed file dispatcher into Student profile image slot
  - does **not** send welcome email or print-format welcome kit by itself
  - invite email behavior exists in staff portal endpoint `invite_applicant` (separate flow)
- **Link query endpoints**:
  - `academic_year_intent_query`
  - `school_by_organization_query`
- **Portal API endpoints** (`ifitwala_ed/api/admissions_portal.py`) used by portal pages/service:
  - `get_admissions_session`
  - `get_applicant_snapshot`
  - `get_applicant_health`
  - `update_applicant_health`
  - `list_applicant_documents`
  - `list_applicant_document_types`
  - `upload_applicant_document`
  - `get_applicant_policies`
  - `acknowledge_policy`
  - `submit_application`
  - staff flow endpoint: `invite_applicant`
- **Admissions policy overlay (SPA)**:
  - page launcher: `ui-spa/src/pages/admissions/ApplicantPolicies.vue`
  - overlay component: `ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue`
  - acknowledgement submit: `admissionsService.acknowledgePolicy` -> `ifitwala_ed.api.admissions_portal.acknowledge_policy`
  - behavior is explicit acknowledge + timestamped row insert; no signature artifact capture

### Troubleshooting: `Policy schema mismatch` (`missing_column: applies_to`)

If you see an error log like:

- title: `Policy schema mismatch`
- caller: `StudentApplicant.has_required_policies`
- doctype: `Institutional Policy`
- missing_column: `applies_to`

it means code expects `Institutional Policy.applies_to`, but your site database table does not have that column.

Current implementation impact:

- `StudentApplicant.has_required_policies()` cannot evaluate required policies and marks readiness as not OK with a schema-error issue.
- `ifitwala_ed/api/admissions_portal.py::get_applicant_policies` throws a blocking error (`throw=True`) and policy UI cannot load.

What to do (site operations):

1. Run migrations for the affected site:
   - `bench --site <site-name> migrate`
2. If the column is still missing, reload the DocType schema:
   - `bench --site <site-name> reload-doc governance doctype institutional_policy`
3. Verify column presence:
   - `bench --site <site-name> mariadb -e "SHOW COLUMNS FROM \`tabInstitutional Policy\` LIKE 'applies_to';"`
4. Re-test applicant policy readiness/API and confirm no new `Policy schema mismatch` logs are created.

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | No | No | No | Read-only in DocType permissions |
| `Academic Assistant` | Yes | No | No | No | Read-only in DocType permissions |

Runtime controller rules (server):
- Only admissions staff can create new records.
- Status changes must use lifecycle methods (direct writes are blocked).
- Family/applicant editability depends on current status (`Invited/In Progress/Missing Info`).
- Terminal states (`Rejected`, `Promoted`) are locked except explicit System Manager override flow.
- `inquiry`, `student`, and `applicant_user` links are immutable and only set through named flows.
- Direct `File` clutter is blocked on this doctype except `applicant_image`; admissions evidence belongs on [**Applicant Document**](/docs/en/applicant-document/).

## Reporting and Analytics

- No dedicated Script/Query Report declares `Student Applicant` as `ref_doctype`.
- Current analytics are API/widget driven (admissions portal completeness + morning brief pulse).

## Related Docs

- [**Inquiry**](/docs/en/inquiry/) - lead conversion into applicant
- [**Applicant Document Type**](/docs/en/applicant-document-type/) - required document policy
- [**Applicant Document**](/docs/en/applicant-document/) - governed admissions files
- [**Applicant Health Profile**](/docs/en/applicant-health-profile/) - health review component
- [**Applicant Interview**](/docs/en/applicant-interview/) - interview evidence component
- [**Institutional Policy**](/docs/en/institutional-policy/) - policy identity/scope used by applicant readiness
- [**Policy Version**](/docs/en/policy-version/) - active legal text source for applicant policy cards
- [**Policy Acknowledgement**](/docs/en/policy-acknowledgement/) - acknowledgement evidence rows tied to applicant context

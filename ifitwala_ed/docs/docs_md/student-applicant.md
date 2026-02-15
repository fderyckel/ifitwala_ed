---
title: "Student Applicant: The Admission Record of Truth"
slug: student-applicant
category: Admission
doc_order: 4
summary: "Manage applicant lifecycle from invitation to promotion, with readiness checks, governed files, policy acknowledgements, and portal access."
---

# Student Applicant: The Admission Record of Truth

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

## Technical Notes (IT)

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
- **Institutional Policy / Policy Version / Policy Acknowledgement** - readiness policy source chain used by `has_required_policies()` and portal policy API

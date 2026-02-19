---
title: "Inquiry: Managing First Contact with Prospective Families"
slug: inquiry
category: Admission
doc_order: 2
summary: "Capture, assign, and track inquiry follow-up with SLA visibility, assignment ownership, and conversion into Student Applicant."
seo_title: "Inquiry: Managing First Contact with Prospective Families"
seo_description: "Capture, assign, and track inquiry follow-up with SLA visibility, assignment ownership, and conversion into Student Applicant."
---

## Inquiry: Managing First Contact with Prospective Families

## Before You Start (Prerequisites)

- Configure `Admission Settings` first so SLA and assignment behaviors are available.
- Ensure `Organization`/`School` master data exists for scoped inquiries.
- Ensure admissions users are set up before assignment/reassignment workflows begin.

Every admission cycle starts with a first question. The `Inquiry` DocType turns that first message into a managed workflow instead of a loose email thread.

## What It Solves

- Centralizes inbound interest from web forms and staff-created records.
- Assigns ownership to admissions officers and managers.
- Tracks first-contact and follow-up deadlines with SLA status.
- Converts contacted/qualified interest to [**Student Applicant**](/docs/en/student-applicant/).

<Callout type="tip" title="Outcome">
Inquiry gives admission leaders visibility on response speed and pipeline health before opportunities go cold.
</Callout>

## Workflow States

| State | Meaning |
|---|---|
| `New` | First capture, not yet assigned |
| `Assigned` | Owner set, follow-up deadline active |
| `Contacted` | Family has been contacted |
| `Qualified` | Strong fit, ready for invite-to-apply |
| `Archived` | Closed terminal state |

Legacy compatibility note: persisted `New Inquiry` values are normalized to canonical `New` during validation and Desk rendering.

## Where Inquiry Is Used Across the ERP

- **Desk form + list view**:
  - custom action buttons (`Assign`, `Reassign`, `Mark Contacted`, `Qualify`, `Archive`, `Invite to Apply`)
  - `Mark Contacted` is available in `Assigned` state for both `Admission Officer` and `Admission Manager`
  - colored list indicators for workflow and SLA status
- **Public web form**: `/apply/inquiry` creates Inquiry records.
- **Notifications**:
  - `Notify Admission Manager` on new Inquiry
  - `Inquiry Assigned` on assignee change
- **ToDo integration**:
  - assignment/reassignment creates native ToDo tasks
  - closing the related ToDo can auto-mark Inquiry as contacted
- **Staff focus overlay (SPA)**:
  - assigned inquiries appear in Staff Home "Your Focus"
  - action type `inquiry.follow_up.act.first_contact` routes to the inquiry follow-up focus action
- **CRM linkage**: `create_contact_from_inquiry` links/creates `Contact`.
- **Admissions conversion**:
  - links to [**Student Applicant**](/docs/en/student-applicant/)
  - Desk invite action calls `ifitwala_ed.admission.admission_utils.from_inquiry_invite`
- **Analytics surface**:
  - staff SPA route: `/staff/analytics/inquiry`
  - API: `ifitwala_ed.api.inquiry.get_dashboard_data` and related filter endpoints
- **Scheduler**: hourly SLA recomputation.
- **File routing fallback**: attachments routed under Admissions inquiry context in file management utilities.

## Technical Notes (IT)

- **DocType**: `Inquiry` (`ifitwala_ed/admission/doctype/inquiry/`)
- **Autoname**: `INQ-{YYYY}-{MM}-{DD}-{##}`
- **Desk surfaces**:
  - form actions in `ifitwala_ed/admission/doctype/inquiry/inquiry.js`
  - list indicators in `ifitwala_ed/admission/doctype/inquiry/inquiry_list.js`
  - workspace shortcut/card in `ifitwala_ed/admission/workspace/admission/admission.json`
- **Web form surface**:
  - config file `ifitwala_ed/admission/web_form/inquiry/inquiry.json`
  - route `apply/inquiry` (public form)
  - scoped shell assets via `hooks.py` `webform_include_css/js` for both `Inquiry` and `Registration of Interest`, using app public paths: `public/css/admissions_webform_shell.css` and `public/js/admissions_webform_shell.js`
- **Staff analytics (SPA)**:
  - page `ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue`
  - route `/staff/analytics/inquiry` via `ifitwala_ed/ui-spa/src/router/index.ts`
  - service map `ifitwala_ed/ui-spa/src/lib/admission.ts` calling inquiry analytics APIs
- **Lifecycle hooks**:
  - `before_insert`: stamps `submitted_at`
  - `after_insert`: ensures `workflow_state = New`, notifies managers
  - `before_save`: computes deadlines and SLA status
- **Validation**:
  - Organization/School hierarchy consistency check
  - strict workflow transition guard
  - `student_applicant` link immutability
- **Whitelisted methods on document**:
  - `mark_qualified`
  - `archive`
  - `invite_to_apply`
  - `create_contact_from_inquiry`
  - `mark_contacted`
- **Conversion nuance**:
  - document method `invite_to_apply` enforces `Qualified` state
  - Desk quick action currently uses `from_inquiry_invite`, available from `Contacted` and `Qualified` in client logic
  - Invite payload validation enforces selected School belongs to selected Organization (Organization NestedSet ancestry)
- **Utility endpoints** (`ifitwala_ed/admission/admission_utils.py`):
  - `assign_inquiry`
  - `reassign_inquiry`
  - `get_admission_officers`
  - `school_by_organization_scope_query`
  - `from_inquiry_invite`
- **Analytics API endpoints** (`ifitwala_ed/api/inquiry.py`):
  - `get_dashboard_data`
  - `get_inquiry_types`
  - `get_inquiry_organizations`
  - `get_inquiry_schools`
  - `academic_year_link_query`
  - `admission_user_link_query`
- **Focus API endpoints** (`ifitwala_ed/api/focus.py`):
  - `list_focus_items` (includes Inquiry action items assigned to current user)
  - `get_focus_context` (returns Inquiry context payload for focus routing)
  - `mark_inquiry_contacted` (named focus action endpoint delegating to `Inquiry.mark_contacted`)

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | No | No | No | Read-only in DocType permissions |

Action-level guard in server code: lifecycle and assignment methods enforce admissions-role checks.

## Reporting and Analytics

- No Script/Query Report currently declares `Inquiry` as `ref_doctype`.
- Operational analytics are delivered through API + SPA analytics page, not a classic Desk report object.

## Related Docs

- [**Admission Settings**](/docs/en/admission-settings/) - SLA defaults and assignment visual settings
- [**Student Applicant**](/docs/en/student-applicant/) - conversion target after qualification
- [**Registration of Interest**](/docs/en/registration-of-interest/) - alternate admissions lead intake

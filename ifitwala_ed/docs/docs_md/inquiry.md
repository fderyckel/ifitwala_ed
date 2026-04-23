---
title: "Inquiry: Managing Website Visitor Intake"
slug: inquiry
category: Admission
doc_order: 2
version: "1.4.4"
last_change_date: "2026-04-23"
summary: "Capture, assign, and track incoming website inquiries with SLA visibility and optional conversion to Student Applicant when relevant."
seo_title: "Inquiry: Managing Website Visitor Intake"
seo_description: "Capture, assign, and track incoming website inquiries with SLA visibility and optional conversion to Student Applicant when relevant."
---

## Before You Start (Prerequisites)

- Configure [**Admission Settings**](/docs/en/admission-settings/) first so that SLA and assignment behaviors are available.
- Ensure [**Organization**](/docs/en/organization/) and [**School**](/docs/en/school/) master data exist for scoped inquiries.
- Ensure admissions triage users and scoped staff `Employee` records (`user_id`, `organization`, `school`) are set up before assignment/reassignment workflows begin.

`Inquiry` is the general inbound intake record for website visitors. It can represent admission interest, general questions, media requests, or any other first-contact message that needs managed follow-up.

## What It Solves

- Centralizes inbound questions from community users and prospective applicants.
- Assigns ownership to scoped staff users when operational follow-up is needed.
- Tracks first-contact and follow-up deadlines with SLA status.
- Supports optional conversion to [**Student Applicant**](/docs/en/student-applicant/) only when the inquiry is admissions-related.

<Callout type="tip" title="Outcome">
Inquiry gives teams visibility on response speed and ownership so no inbound request disappears into email threads.
</Callout>

## Workflow States

| State | Meaning | How It Is Reached (Conditions) |
|---|---|---|
| `New` | First capture, not yet assigned | Set automatically on insert if empty (`after_insert`). |
| `Assigned` | Owner set, follow-up deadline active | Reached through assignment flows (`assign_inquiry` / `reassign_inquiry` -> `mark_assigned`) with admissions permission and a valid scoped active `Employee.user_id` assignee. |
| `Contacted` | First outreach completed | Reached from `New` or `Assigned` through `mark_contacted` by Admissions/System users or by the current assigned user. Can also be triggered by ToDo-close automation when the current assignee closes the linked task. `assigned_to` remains populated as the latest assignee for reporting/distribution analysis. |
| `Qualified` | Confirmed as admissions-ready | Reached only from `Contacted` through `mark_qualified` with admissions permission. |
| `Archived` | Closed terminal state | Reached from any non-archived state through `archive` with admissions permission. |

Allowed transitions are strictly server-validated:

- `New` -> `Assigned` or `Contacted`
- `Assigned` -> `Contacted`
- `Contacted` -> `Qualified`
- Any non-`Archived` state -> `Archived`
- Backward transitions are rejected.

## Operational Guardrails

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use `Assign`/`Reassign` actions so ownership, SLA fields, and ToDo artifacts stay consistent.</Do>
  <Do>Treat `Assigned To` as the latest assignee history field; it persists after `Contacted` and updates on reassignment.</Do>
  <Do>Move state with named actions (`Mark Contacted`, `Qualify`, `Archive`) so server transition rules and metrics are enforced.</Do>
  <Dont>Manually edit workflow fields to skip required transitions.</Dont>
  <Dont>Treat every inquiry as admissions conversion; convert only when it is actually admissions-relevant.</Dont>
</DoDont>

## Where Inquiry Is Used Across the ERP

- **Desk form + list view**:
  - custom action buttons (`Assign`, `Reassign`, `Mark Contacted`, `Qualify`, `Archive`, `Invite to Apply`)
  - `School` field link picker is client-filtered by selected `Organization` (includes descendant organizations)
  - assignee picker in `Assign`/`Reassign` is server-scoped to active `Employee.user_id` within Inquiry organization scope and the Inquiry school lineage (selected school plus parent schools)
  - `Mark Contacted` is available in `Assigned` state for both `Admission Officer` and `Admission Manager`
  - when the current session user is the assigned owner, `Mark Contacted` is also available even without admissions roles
  - list defaults to active pipeline (`workflow_state != Archived`)
  - visible deadline cue on `First Contact Deadline` (pill-highlighted for due/overdue urgency)
  - colored list pills for workflow and SLA status
  - Kanban board `Inquiry Team Pipeline` grouped by `sla_status` (with `workflow_state != Archived`) for admissions/marketing/comms triage
- **Public web form**: `/apply/inquiry` creates Inquiry records from visitor submissions and shows a post-submit confirmation message; when Organization is selected, confirmation copy references that organization.
- **Notifications**:
  - `Notify Admission Manager` on new Inquiry
  - `Inquiry Assigned` on assignee change
- **ToDo integration**:
  - assignment/reassignment creates native ToDo tasks
  - closing the related ToDo can auto-mark Inquiry as contacted
  - assignment snapshots current `assignment_lane` (`Admission` or `Staff`) and resolver assignment timestamp for lane KPI slicing
- **Staff focus overlay (SPA)**:
  - assigned inquiries appear in Staff Home "Your Focus"
  - action type `inquiry.follow_up.act.first_contact` routes to the inquiry follow-up focus action
  - inquiry follow-up focus shows inquiry identity, linked contact state, email, phone number, and the original inquiry message
  - focus users can create/link the canonical `Contact` anchor from the overlay via the same Inquiry linkage workflow
- **CRM linkage**: `create_contact_from_inquiry` links/creates `Contact`.
- **Optional admissions conversion**:
  - links to [**Student Applicant**](/docs/en/student-applicant/)
  - Desk invite action calls `ifitwala_ed.admission.admission_utils.from_inquiry_invite`
  - conversion ensures Inquiry has a `Contact` anchor and carries it into `Student Applicant.applicant_contact` when conversion is requested
  - conversion also ensures Contact has a `Dynamic Link` to the created/reused `Student Applicant` (idempotent sync)
  - conversion atomically binds `Inquiry.student_applicant` to the created/reused `Student Applicant` (idempotent, no relink overwrite)
  - derived applicant email on Student Applicant comes from Contact email rows
  - this conversion step still does not create the portal `User`; portal invite is a separate button on Student Applicant
- **Analytics surface**:
  - staff SPA route: `/staff/analytics/inquiry`
  - API: `ifitwala_ed.api.inquiry.get_dashboard_data` and related filter endpoints
- **Scheduler**: hourly SLA recomputation (`run_hourly_sla_sweep` -> `check_sla_breaches`) updates SLA status only and caches the run summary at `admissions:sla_sweep:last_run`; legacy missing `first_contact_due_on` rows are remediated through the one-shot patch `ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates`.
- **File routing fallback**: attachments routed under Admissions inquiry context in file management utilities.

## Lifecycle and Linked Documents

<Steps title="Inquiry Lifecycle">
  <Step title="Capture">
    Capture inbound request as `New` (admission-related or not).
  </Step>
  <Step title="Assign">
    Assign ownership (`Assigned`) when coordinated follow-up is needed.
  </Step>
  <Step title="Contact">
    Mark as `Contacted` when first outreach is completed and metrics are stamped.
  </Step>
  <Step title="Qualify or Close">
    If it is admissions-relevant and ready, move to `Qualified` and optionally invite/create a `Student Applicant`.
  </Step>
  <Step title="Archive">
    Archive completed/closed paths through `Archived` (including non-admissions inquiries like general or media requests).
  </Step>
</Steps>

<Callout type="info" title="Transition guardrails">
Workflow transitions are server-validated. Teams should follow the canonical state path instead of manually editing status fields.
</Callout>

<Callout type="warning" title="Two different invite actions">
`Invite to Apply` on Inquiry creates the `Student Applicant` record in `Invited` and links Contact anchor fields, but it does not provision applicant portal login credentials. After conversion, open the applicant and use `Actions` -> `Invite Applicant Portal` (or `Resend Portal Invite`) to pick/add a Contact email and trigger `invite_applicant(student_applicant, email)`.
</Callout>

## Reporting and Analytics

- No Script/Query Report currently declares `Inquiry` as `ref_doctype`.
- Operational analytics are delivered through API + SPA analytics page, not a classic Desk report object.

## Related Docs

<RelatedDocs
  slugs="admission-settings,organization,student-applicant"
  title="Continue With Related Admission Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-03-05)

- **DocType schema file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.json`
- **Controller file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: `validate`, `before_insert`, `after_insert`, `before_save`
- **Operational/public methods**: `mark_assigned`, `mark_qualified`, `archive`, `invite_to_apply`, `set_contact_metrics`, `create_contact_from_inquiry`, `mark_contacted`
- **Workflow-state contract**: only canonical Inquiry states are accepted (`New`, `Assigned`, `Contacted`, `Qualified`, `Archived`); no legacy state alias normalization in Inquiry controller or Inquiry Desk/list scripts.
- **Assignment contract**: `assigned_to` is retained as the latest assignee across workflow states (including `Contacted`) and changes only through assignment/reassignment actions.
- **Completion permission contract**: `mark_contacted` can be executed by Admissions/System users and by the current assigned user.
- **Record visibility contract**: non-privileged users are query-scoped to assigned Inquiry rows (`assigned_to = session user`) through hooks.

- **DocType**: `Inquiry` (`ifitwala_ed/admission/doctype/inquiry/`)
- **Autoname**: `INQ-{YYYY}-{MM}-{DD}-{##}`
- **Desk surfaces**:
  - form actions in `ifitwala_ed/admission/doctype/inquiry/inquiry.js`
  - desk form `school` link query uses `school_by_organization_scope_query` when `organization` is selected
  - desk form assignee link query uses `get_inquiry_assignees` with inquiry org/school scope filters
  - list indicators in `ifitwala_ed/admission/doctype/inquiry/inquiry_list.js`
  - workspace shortcut/card in `ifitwala_ed/admission/workspace/admission/admission.json`
- **Web form surface**:
  - config file `ifitwala_ed/admission/web_form/inquiry/inquiry.json`
  - route `apply/inquiry` (public form)
  - scoped shell assets via `hooks.py` `webform_include_css/js` for `Inquiry`, using app public paths: `public/css/admissions_webform_shell.css` and `public/js/admissions_webform_shell.js`
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
  - assignee scope guard for assignment/reassignment (`Employee` active + inquiry organization scope and inquiry school lineage: selected school plus parent schools)
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
  - `from_inquiry_invite` now serializes per-Inquiry conversion with a cache lock and always binds `Inquiry.student_applicant` to the resolved applicant
- **Utility endpoints** (`ifitwala_ed/admission/admission_utils.py`):
  - `assign_inquiry`
  - `reassign_inquiry`
  - `get_admission_officers`
  - `get_inquiry_assignees`
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
  - `create_inquiry_contact` (named focus action endpoint delegating to `Inquiry.create_contact_from_inquiry` with assignee-bound focus guards)

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | No | No | No | Read-only in DocType permissions |

Action-level guard in server code: assignment/reassignment require admissions permissions; contact completion allows Admissions/System and the current assigned user.

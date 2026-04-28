---
title: "Inquiry: Managing Website Visitor Intake"
slug: inquiry
category: Admission
doc_order: 2
version: "1.7.1"
last_change_date: "2026-04-28"
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
- Captures lead source across public website submissions and staff-entered leads from channels such as WhatsApp, Line, Facebook, open days, referrals, and agents.
- Shows lightweight conditional lead fields when the inquiry type is admission, current-family, or partnership/agent.
- Assigns ownership to scoped staff users when operational follow-up is needed.
- Gives staff a lightweight `Next Action Note` for the next planned follow-up without changing the original inquiry message.
- Tracks first-contact and follow-up deadlines with SLA status.
- Gives families an immediate branded thank-you page and acknowledgement email after public website submission.
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
| `Archived` | Closed terminal state with a reason | Reached from any non-archived state through `archive` with admissions permission and a required archive reason. |

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
  <Do>Use `Source` when creating inquiries from WhatsApp, Line, Facebook, referrals, agents, open days, or other non-website channels.</Do>
  <Do>Use admission-interest fields only as lead context; confirm authoritative school, program, and applicant profile data during applicant creation/review.</Do>
  <Do>Use `Next Action Note` for the next planned staff action; keep the original visitor text in `Message` unchanged.</Do>
  <Do>Move state with named actions (`Mark Contacted`, `Qualify`, `Archive`) so server transition rules and metrics are enforced.</Do>
  <Do>Record a clear archive reason when closing an inquiry so closed leads remain explainable later.</Do>
  <Dont>Manually edit workflow fields to skip required transitions.</Dont>
  <Dont>Treat student-name, grade, program, or language preferences on Inquiry as applicant truth.</Dont>
  <Dont>Treat every inquiry as admissions conversion; convert only when it is actually admissions-relevant.</Dont>
</DoDont>

## Where Inquiry Is Used Across the ERP

- **Desk form + list view**:
  - custom action buttons (`Assign`, `Reassign`, `Mark Contacted`, `Qualify`, `Archive`, `Invite to Apply`)
  - `School` field link picker is client-filtered by selected `Organization` (includes descendant organizations)
  - assignee picker in `Assign`/`Reassign` is server-scoped to active `Employee.user_id` within the Inquiry organization chain and school chain (selected node plus ancestors and descendants; sibling organizations/schools excluded; organization-level employees with no school follow the organization chain)
  - `Mark Contacted` is available in `Assigned` state for both `Admission Officer` and `Admission Manager`
  - when the current session user is the assigned owner, `Mark Contacted` is also available even without admissions roles
  - list defaults to active pipeline (`workflow_state != Archived`)
  - visible deadline cue on `First Contact Deadline` (pill-highlighted for due/overdue urgency)
  - colored list pills for workflow and SLA status
  - Kanban board `Inquiry Team Pipeline` grouped by `sla_status` (with `workflow_state != Archived`) for admissions/marketing/comms triage
- **Public web form**: `/apply/inquiry` creates Inquiry records from visitor submissions and shows a branded post-submit thank-you page with next-step timeline and safe CTAs.
  - `Organization` and `School` remain optional and visible so prospects can choose context when useful; admissions users can adjust them later.
  - the public `School` picker is filtered to schools with `Show in Inquiry` enabled under inquiry-enabled organizations; website publication is a separate setting.
  - public web submissions default `Source` to `Website`.
  - public submissions with an email address queue a transactional family acknowledgement email after commit.
  - school-specific thank-you copy, email template, visit CTA, and optional public application CTA are configured through `Admission Acknowledgement Profile`.
  - the authenticated `/admissions` portal is not shown as an anonymous application-start CTA.
  - `Type of Inquiry` supports `Admission`, `Current Family`, `General Inquiry`, `Partnership / Agent`, and `Other`.
  - admission inquiries show student name, intended academic year, grade-level interest, and program-interest fields.
  - current-family inquiries show student name/ID and relationship-to-student fields.
  - partnership/agent inquiries show organization name and partnership context fields.
- **Manual lead capture**: admissions users can create `Inquiry` directly in Desk for leads received through WhatsApp, Line, Facebook, open days, referrals, agents, or other channels, then set `Source` and `Next Action Note` before assignment.
  - Admissions Cockpit exposes a `New Inquiry` shortcut for users with Inquiry creation rights.
- **Notifications**:
  - `Notify Admission Manager` on new Inquiry
  - `Inquiry Assigned` on assignee change
  - queued family acknowledgement email on public web-form insert when the Inquiry has an email address
- **ToDo integration**:
  - assignment/reassignment creates native ToDo tasks
  - closing the related ToDo can auto-mark Inquiry as contacted
  - assignment snapshots current `assignment_lane` (`Admission` or `Staff`) and resolver assignment timestamp for lane KPI slicing
- **Staff focus overlay (SPA)**:
  - assigned inquiries appear in Staff Home "Your Focus"
  - action type `inquiry.follow_up.act.first_contact` routes to the inquiry follow-up focus action
  - inquiry follow-up focus shows inquiry identity, linked contact state, email, phone number, and the original inquiry message
  - source and next-action note are included in the focus context when present
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
  - Zero Lost Lead command center API: `ifitwala_ed.api.inquiry.get_zero_lost_lead_context`
  - operational queues appear before charts and surface unassigned, due, overdue, missing-next-action, qualified-not-invited, invited-without-progress, archived-without-reason, and stale-unowned leads
  - operational queues are all-time within selected organization/school/assignee/type/source/lane filters so old leads do not disappear behind the analytics date range
  - source filter and source distribution are included for channel-quality reporting
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
    Archive completed/closed paths through `Archived` with a reason (including non-admissions inquiries like general or media requests).
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

## Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | No | No | No | Read-only in DocType permissions |

Action-level guard in server code: assignment/reassignment require admissions permissions; contact completion allows Admissions/System and the current assigned user.

## Related Docs

<RelatedDocs
  slugs="admission-settings,organization,student-applicant"
  title="Continue With Related Admission Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-04-28)

- **DocType schema file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.json`
- **Controller file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.py`
- **Acknowledgement config**: `Admission Acknowledgement Profile` (`ifitwala_ed/admission/doctype/admission_acknowledgement_profile/`)
- **Acknowledgement service**: `ifitwala_ed/admission/inquiry_acknowledgement.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Manual lead fields**: `source` (`Website`, `WhatsApp`, `Line`, `Facebook`, `Open Day`, `Referral`, `Agent`, `Other`), contact preferences, dynamic inquiry-type fields, `next_action_note`, and `archive_reason`.
- **Indexed lookup fields**: `email`, `phone_number`, `source`, `workflow_state`, `first_contact_due_on`, `followup_due_on`.
- **Lifecycle hooks in controller**: `validate`, `before_insert`, `after_insert`, `before_save`
- **Operational/public methods**: `mark_assigned`, `mark_qualified`, `archive`, `set_contact_metrics`, `create_contact_from_inquiry`, `mark_contacted`
- **Workflow-state contract**: only canonical Inquiry states are accepted (`New`, `Assigned`, `Contacted`, `Qualified`, `Archived`); no legacy state alias normalization in Inquiry controller or Inquiry Desk/list scripts.
- **Archive reason contract**: `archive(reason)` requires and stores `archive_reason`; legacy or bypassed archived rows without a reason surface in the Zero Lost Lead command center.
- **Assignment contract**: `assigned_to` is retained as the latest assignee across workflow states (including `Contacted`) and changes only through assignment/reassignment actions.
- **Inquiry type contract**: `type_of_inquiry` options are `Admission`, `Current Family`, `General Inquiry`, `Partnership / Agent`, and `Other`; type-specific fields are optional triage context only.
- **Source contract**: public web-form inserts default missing `source` to `Website`; staff-created inquiries may set the appropriate manual lead source.
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
  - `organization` and `school` remain visible and optional; hidden `source` defaults to `Website`
  - `school` uses public-safe `inquiry_school_link_query`, scoped by selected organization where present and filtered by `School.show_in_inquiry`
  - thank-you page copy and CTAs are loaded from `get_inquiry_acknowledgement_context`
  - conditional fields are shown from `type_of_inquiry` for admission, current-family, and partnership/agent context
  - scoped shell assets via `hooks.py` `webform_include_css/js` for `Inquiry`, using app public paths: `public/css/admissions_webform_shell.css` and `public/js/admissions_webform_shell.js`
- **Staff analytics (SPA)**:
  - page `ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue`
  - route `/staff/analytics/inquiry` via `ifitwala_ed/ui-spa/src/router/index.ts`
  - service map `ifitwala_ed/ui-spa/src/lib/admission.ts` calling inquiry analytics APIs
  - Zero Lost Lead view contract `ifitwala_ed/ui-spa/src/types/contracts/inquiry/zero_lost_lead_context.ts`
- **Lifecycle hooks**:
  - `before_insert`: stamps `submitted_at`
  - `after_insert`: ensures `workflow_state = New`, notifies managers, queues family acknowledgement for public web-form submissions with email
  - `before_save`: computes deadlines and SLA status
- **Validation**:
  - Organization/School hierarchy consistency check
  - strict workflow transition guard
  - `student_applicant` link immutability
  - assignee scope guard for assignment/reassignment (`Employee` active + Inquiry organization chain and school chain: selected node plus ancestors and descendants; sibling organizations/schools excluded; organization-level employees with no school follow the organization chain)
- **Whitelisted methods on document**:
  - `mark_qualified`
  - `archive(reason)`
  - `create_contact_from_inquiry`
  - `mark_contacted`
- **Conversion nuance**:
  - Desk quick action uses `from_inquiry_invite`, available from `Contacted` and `Qualified` in client logic
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
  - `get_zero_lost_lead_context`
  - `get_dashboard_data`
  - `get_inquiry_types`
  - `get_inquiry_sources`
  - `get_inquiry_organizations`
  - `get_inquiry_schools`
  - `academic_year_link_query`
  - `inquiry_school_link_query`
  - `get_inquiry_acknowledgement_context`
  - `admission_user_link_query`
- **Focus API endpoints** (`ifitwala_ed/api/focus.py`):
  - `list_focus_items` (includes Inquiry action items assigned to current user)
  - `get_focus_context` (returns Inquiry context payload for focus routing)
  - `mark_inquiry_contacted` (named focus action endpoint delegating to `Inquiry.mark_contacted`)
  - `create_inquiry_contact` (named focus action endpoint delegating to `Inquiry.create_contact_from_inquiry` with assignee-bound focus guards)

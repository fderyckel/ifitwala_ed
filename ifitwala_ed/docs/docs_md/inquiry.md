---
title: "Inquiry: Managing Website Visitor Intake"
slug: inquiry
category: Admission
doc_order: 2
version: "1.8.0"
last_change_date: "2026-05-21"
summary: "Capture, assign, and track incoming website inquiries with SLA visibility, source tracking, acknowledgement, and optional conversion to Student Applicant."
seo_title: "Inquiry: Managing Website Visitor Intake"
seo_description: "Use Inquiry to capture website and staff-entered leads, assign follow-up, track SLA status, acknowledge families, and convert admission-ready leads to Student Applicant."
---

## What Is an Inquiry?

`Inquiry` is the first managed record for someone who reaches out to your school. It can be an admissions lead, a current-family question, a partnership message, a media request, or any other first-contact request that needs visible follow-up.

For admissions teams, Inquiry is the front door. It helps staff capture interest, assign ownership, meet response expectations, and convert the right leads into [**Student Applicant**](/docs/en/student-applicant/) records without losing source context.

<Callout type="info" title="Why Ifitwala Ed is different">
Inquiry treats first contact as a real operational workflow, not just a form submission. Visitors get a branded acknowledgement, staff get ownership and SLA visibility, and admissions-ready leads can carry clean context into the applicant lifecycle.
</Callout>

## Why This Matters

- **No lead should disappear into email.** Each inquiry has a state, owner, source, and follow-up path.
- **Admissions response speed becomes visible.** First-contact and follow-up deadlines help teams prioritize.
- **Every channel can be tracked.** Website, WhatsApp, Line, Facebook, open days, referrals, agents, and walk-ins can all become managed inquiries.
- **Visitors get immediate reassurance.** Public submissions can show type-aware thank-you copy and queue acknowledgement email.
- **Admissions conversion stays intentional.** Only admissions-relevant inquiries should become Student Applicants.

## Before You Create or Use Inquiries

You should have:

- [**Admission Settings**](/docs/en/admission-settings/) configured for SLA and assignment behavior
- [**Organization**](/docs/en/organization/) and [**School**](/docs/en/school/) records ready for scoped inquiries
- admissions triage users and scoped staff `Employee` records with `user_id`, `organization`, and `school`
- an agreed team habit for `Source`, `Next Action Note`, assignment, and archive reasons

## Information You Manage

| Area | What it controls | Why it matters |
|---|---|---|
| Type of inquiry | Admission, current family, general inquiry, partnership/agent, or other | Keeps forms, thank-you copy, and follow-up context relevant |
| Contact details | Email, phone, visitor identity, and message | Gives staff enough context to respond |
| Organization and school | Optional context chosen by the prospect or adjusted by staff | Keeps school-specific routing and reporting meaningful |
| Source | Website, phone, WhatsApp, referral, agent, open day, and other channels | Helps teams understand channel quality |
| Assigned owner | Staff user responsible for follow-up | Makes ownership explicit |
| Next Action Note | The next planned staff action | Lets staff plan follow-up without changing the original visitor message |
| Workflow state | New, assigned, contacted, qualified, or archived | Shows where the inquiry sits in the pipeline |
| SLA fields | First-contact and follow-up deadlines | Supports response-speed visibility |
| Student Applicant link | Optional conversion to applicant | Preserves source lineage when admission interest becomes an application |

## How This Fits the Admissions Workflow

<Steps title="Inquiry lifecycle">
  <Step title="Capture">
    Capture the inbound request from the public form or enter it manually from another channel.
  </Step>
  <Step title="Assign">
    Assign ownership when coordinated follow-up is needed. Assignment creates follow-up context and task visibility.
  </Step>
  <Step title="Contact">
    Mark the inquiry contacted when first outreach is complete and response metrics should be stamped.
  </Step>
  <Step title="Qualify or close">
    Qualify admissions-ready leads, or archive completed/non-admissions requests with a clear reason.
  </Step>
  <Step title="Invite to apply">
    When an inquiry is truly admissions-ready, convert or invite it into Student Applicant so the family can continue the application journey.
  </Step>
</Steps>

<Callout type="warning" title="Two different invite actions">
`Invite to Apply` on Inquiry creates the Student Applicant record in `Invited` and carries Contact anchor fields, but it does not guarantee portal login credentials. After conversion, open the applicant and use the Student Applicant portal invite action to choose the applicant or family login identity.
</Callout>

## Permission Matrix

Admissions users can create and manage inquiries. Academic Admins have read-only visibility. Some action-level rules are stricter than the base DocType matrix.

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Academic Admin` | Yes | No | No | No | Read-only in DocType permissions |

Action-level guard in server code: assignment/reassignment require admissions permissions; contact completion allows Admissions/System users and the current assigned user.

## Practical Examples

### Website admission inquiry

A parent submits the public inquiry form for a school visit. The inquiry is captured as `New`, the parent sees an acknowledgement page, and staff assign an owner for follow-up.

### WhatsApp or walk-in lead

An admissions officer receives a message outside the website. Staff create an Inquiry manually, choose the right `Source`, add a `Next Action Note`, and assign the follow-up owner.

### Qualified lead becomes applicant

After first contact, the family is ready to apply. Staff mark the inquiry `Qualified`, use `Invite to Apply`, and the new Student Applicant carries identity, intent, school context, and contact lineage forward.

### Non-admissions request

A current-family or partnership inquiry should not become a Student Applicant. Staff follow up, resolve the request, and archive it with a reason.

## Best Practices

<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Use Assign/Reassign actions so ownership, SLA fields, and ToDo artifacts stay consistent.</Do>
  <Do>Use Source for every non-website channel so reporting stays useful.</Do>
  <Do>Use Next Action Note for planned follow-up while preserving the original visitor message.</Do>
  <Do>Archive with a clear reason when the inquiry is closed.</Do>
  <Dont>Manually edit workflow fields to skip required transitions.</Dont>
  <Dont>Treat student name, grade, program, or language preferences on Inquiry as final applicant truth.</Dont>
  <Dont>Convert every inquiry into an applicant just because it came through admissions.</Dont>
</DoDont>

## Common Questions

### Can Inquiry handle non-admissions messages?

Yes. `Type of Inquiry` supports admission, current-family, general, partnership/agent, and other requests. Non-admissions inquiries should be resolved or archived without applicant conversion.

### Does the public form always show the admissions portal?

No. The public thank-you experience can show school-specific admissions next steps, visit CTAs, or public application CTAs where configured, but the authenticated `/admissions` portal is not shown as an anonymous application-start CTA.

### Can the assigned owner mark the inquiry contacted?

Yes. Admissions/System users can mark contacted, and the current assigned user can also complete contact even without broad admissions roles.

### What happens when a related ToDo is closed?

Closing the related ToDo can auto-mark the Inquiry as contacted for the current assignee path.

### Does Inquiry conversion create portal credentials?

No. Inquiry conversion creates or links the Student Applicant. Portal login invitation is handled separately on Student Applicant.

## Related Docs

<RelatedDocs
  slugs="admission-settings,admission-cockpit,organization,student-applicant"
  title="Continue With Related Admission Docs"
/>

## Technical Notes (IT)

### Latest Technical Snapshot (2026-05-21)

- **DocType schema file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.json`
- **Controller file**: `ifitwala_ed/admission/doctype/inquiry/inquiry.py`
- **Acknowledgement config**: `Admission Acknowledgement Profile` (`ifitwala_ed/admission/doctype/admission_acknowledgement_profile/`)
- **Acknowledgement service**: `ifitwala_ed/admission/inquiry_acknowledgement.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: `validate`, `before_insert`, `after_insert`, `before_save`
- **Operational/public methods**: `mark_assigned`, `mark_qualified`, `archive`, `set_contact_metrics`, `create_contact_from_inquiry`, `mark_contacted`
- **Manual lead fields**: `source`, contact preferences, dynamic inquiry-type fields, `next_action_note`, and `archive_reason`
- **Indexed lookup fields**: `email`, `phone_number`, `source`, `workflow_state`, `first_contact_due_on`, `followup_due_on`

### Workflow Contract

| State | Meaning | How it is reached |
|---|---|---|
| `New` | First capture, not yet assigned | Set automatically on insert if empty |
| `Assigned` | Owner set, follow-up deadline active | Assignment/reassignment flow with admissions permission and valid scoped active `Employee.user_id` assignee |
| `Contacted` | First outreach completed | `mark_contacted` from `New` or `Assigned`; ToDo-close automation can also mark contacted |
| `Qualified` | Confirmed as admissions-ready | `mark_qualified` from `Contacted` with admissions permission |
| `Archived` | Closed terminal state with reason | `archive(reason)` from any non-archived state |

Allowed transitions:

- `New` -> `Assigned` or `Contacted`
- `Assigned` -> `Contacted`
- `Contacted` -> `Qualified`
- any non-`Archived` state -> `Archived`
- backward transitions are rejected

Only canonical Inquiry states are accepted; no legacy state alias normalization exists in Inquiry controller or Inquiry Desk/list scripts. `assigned_to` is retained as the latest assignee across workflow states, including `Contacted`.

### Runtime Surfaces

- **Desk form + list view**:
  - custom actions: `Assign`, `Reassign`, `Mark Contacted`, `Qualify`, `Archive`, `Invite to Apply`
  - school link picker is client-filtered by selected `Organization`
  - assignee picker uses `get_inquiry_assignees` with inquiry org/school scope filters
  - list defaults to active pipeline (`workflow_state != Archived`)
  - visible deadline cue on `First Contact Deadline`
  - colored list pills for workflow and SLA status
  - Kanban board `Inquiry Team Pipeline` grouped by `sla_status`
- **Public web form**:
  - route `apply/inquiry`
  - config file `ifitwala_ed/admission/web_form/inquiry/inquiry.json`
  - `organization` and `school` remain visible and optional
  - hidden `source` defaults to `Website`
  - public `school` uses `inquiry_school_link_query`, scoped by selected organization and filtered by `School.show_in_inquiry`
  - thank-you page copy and eligible CTAs load from `get_inquiry_acknowledgement_context`
  - conditional fields are shown from `type_of_inquiry`
  - shell assets use `public/css/admissions_webform_shell.css` and `public/js/admissions_webform_shell.js`
- **Manual lead capture**:
  - admissions users can create Inquiry directly in Desk
  - Admissions Cockpit exposes `New Inquiry` when the user has Inquiry creation rights
- **Notifications**:
  - `Notify Admission Manager` on new Inquiry
  - `Inquiry Assigned` on assignee change
  - queued family acknowledgement email on public web-form insert with email
- **ToDo integration**:
  - assignment/reassignment creates native ToDo tasks
  - closing related ToDo can auto-mark Inquiry as contacted
  - assignment snapshots current `assignment_lane` and resolver assignment timestamp
- **Staff focus overlay**:
  - assigned inquiries appear in Staff Home "Your Focus"
  - action type `inquiry.follow_up.act.first_contact`
  - focus users can create/link canonical `Contact` anchor
- **CRM linkage**:
  - `create_contact_from_inquiry` links/creates `Contact`

### Conversion Nuance

- Desk quick action uses `from_inquiry_invite`, available from `Contacted` and `Qualified` in client logic.
- Conversion ensures Inquiry has a `Contact` anchor and carries it into `Student Applicant.applicant_contact`.
- Conversion ensures Contact has a `Dynamic Link` to the created/reused `Student Applicant`.
- Conversion atomically binds `Inquiry.student_applicant` to the resolved applicant.
- Derived applicant email on Student Applicant comes from Contact email rows.
- `from_inquiry_invite` serializes per-Inquiry conversion with a cache lock.
- Portal `User` creation is handled separately on Student Applicant.

### Analytics and Scheduler

- Staff SPA route: `/staff/analytics/inquiry`
- Page: `ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue`
- Service map: `ifitwala_ed/ui-spa/src/lib/admission.ts`
- Zero Lost Lead contract: `ifitwala_ed/ui-spa/src/types/contracts/inquiry/zero_lost_lead_context.ts`
- Operational queues surface unassigned, due, overdue, missing-next-action, qualified-not-invited, invited-without-progress, archived-without-reason, and stale-unowned leads.
- Operational queues are all-time within selected filters so old leads do not disappear behind the analytics date range.
- Scheduler: `run_hourly_sla_sweep` -> `check_sla_breaches`
- SLA sweep updates SLA status only and caches summary at `admissions:sla_sweep:last_run`.
- Legacy missing `first_contact_due_on` rows are remediated through `ifitwala_ed.patches.backfill_inquiry_first_contact_due_dates`.

### API and Helper References

- Utility endpoints in `ifitwala_ed/admission/admission_utils.py`:
  - `assign_inquiry`
  - `reassign_inquiry`
  - `get_admission_officers`
  - `get_inquiry_assignees`
  - `school_by_organization_scope_query`
  - `from_inquiry_invite`
- Analytics API endpoints in `ifitwala_ed/api/inquiry.py`:
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
- Focus API endpoint: `ifitwala_ed/api/focus.py::list_focus_items`

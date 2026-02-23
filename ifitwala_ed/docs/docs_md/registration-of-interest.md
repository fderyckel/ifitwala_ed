---
title: "Registration of Interest: Early Lead Capture Before Full Application"
slug: registration-of-interest
category: Admission
doc_order: 3
summary: "Capture family and student intent early, route it into admissions operations, and keep response timing visible."
seo_title: "Registration of Interest: Early Lead Capture Before Full Application"
seo_description: "Capture family and student intent early, route it into admissions operations, and keep response timing visible."
---

## Registration of Interest: Early Lead Capture Before Full Application

## Before You Start (Prerequisites)

- Configure `Admission Settings` first so SLA deadlines are set consistently.
- Ensure lookup masters exist (`Organization`, `School`, and intended academic structures used on the form).
- Ensure admissions team users are ready to own and follow up new submissions.

`Registration of Interest` is the lightweight front door for families who are not ready for a full application but want to start the conversation.

## What It Captures

- Guardian/family contact details
- Student identity and nationality
- Intended school, program, academic year, and term
- Preferred communication channel and source attribution

## Where It Is Used Across the ERP

- **Public web form**: `/apply/registration-of-interest`
- **SLA operations**: reuses admissions SLA helpers (`set_inquiry_deadlines`) and hourly SLA sweep job.
- **Assignment-close automation**: ToDo close hook supports this doctype in `on_todo_update_close_marks_contacted`.
- **Admissions intake surface**: functions as top-of-funnel input before [**Inquiry**](/docs/en/inquiry/) and [**Student Applicant**](/docs/en/student-applicant/).

<Callout type="info" title="Position in the funnel">
Use Registration of Interest when you want broad demand capture. Use Inquiry when you are actively managing admission conversations and ownership.
</Callout>

## Lifecycle and Linked Documents

1. Publish and monitor the registration form as top-of-funnel admissions intake.
2. New submissions enter operations with SLA deadlines and assignment follow-up patterns.
3. Admissions staff triage demand and decide which leads should move into managed inquiry/application flows.
4. Maintain source/channel quality so analytics remain useful for outreach planning.

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/admission/doctype/registration_of_interest/registration_of_interest.json`
- **Controller file**: `ifitwala_ed/admission/doctype/registration_of_interest/registration_of_interest.py`
- **Required fields (`reqd=1`)**: none at schema level; controller/workflow rules enforce operational completeness where applicable.
- **Lifecycle hooks in controller**: `before_insert`, `after_insert`, `before_save`
- **Operational/public methods**: none beyond standard document behavior.

- **DocType**: `Registration of Interest` (`ifitwala_ed/admission/doctype/registration_of_interest/`)
- **Autoname**: `ROI-{YY}-{MM}-{###}`
- **Web form surface**:
  - config file `ifitwala_ed/admission/web_form/registration_of_interest/registration_of_interest.json`
  - route `apply/registration-of-interest` (public form)
- **Desk surface**:
  - doctype JSON/UI in `ifitwala_ed/admission/doctype/registration_of_interest/registration_of_interest.json`
  - workspace visibility from Admission workspace links/shortcuts
- **Controller lifecycle**:
  - `before_insert`: stamps `submitted_at`
  - `after_insert`: sets workflow-like state to `New Inquiry` and notifies admission manager
  - `before_save`: runs SLA deadline helper
- **Linked fields**:
  - `proposed_program` -> `Program`
  - `proposed_academic_year` -> `Academic Year`
  - `proposed_term` -> `Term`
  - `preferred_school` -> `School`

### Permission Matrix

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Full Desk access |
| `Admission Officer` | Yes | Yes | Yes | Yes | Full Desk access |
| `Marketing User` | Yes | Yes | Yes | Yes | Marketing intake operations |

No dedicated custom permission query/has-permission hooks are registered for this doctype in `hooks.py`.

<Callout type="warning" title="Schema note for implementers">
Current controller logic writes `workflow_state`, while the exported DocType JSON shows a legacy select field named `blank_field` labeled "Worflow State". Validate your deployed schema during rollout.
</Callout>

## Reporting and Analytics

- No dedicated Script/Query Report currently uses `Registration of Interest` as its report `ref_doctype`.
- Monitoring is currently operational (Desk lists/SLA states), not report-object based.

## Related Docs

- [**Inquiry**](/docs/en/inquiry/) - managed admissions workflow with assignment and qualification
- [**Student Applicant**](/docs/en/student-applicant/) - full admissions lifecycle record
- [**Admission Settings**](/docs/en/admission-settings/) - SLA behavior settings

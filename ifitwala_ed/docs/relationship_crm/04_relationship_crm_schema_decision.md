# Relationship CRM Schema Decision Proposal

Status: Proposed approval gate; no Relationship CRM schema, runtime endpoints, or SPA routes are implemented by this note.
Code refs: None for proposed Relationship CRM DocTypes. Related current refs: `ifitwala_ed/setup/doctype/team/*`, `ifitwala_ed/admission/doctype/admission_crm_activity/*`, `ifitwala_ed/admission/doctype/admission_conversation/*`.
Test refs: None for proposed schema.

This note is the approval checkpoint required by `01_education_relationship_crm_contract.md` before any Relationship CRM DocType metadata is added.

This proposal supersedes the earlier three-DocType first slice. The revised direction is deliberately lean: start with one relationship container, prove that it solves real institutional workflows, and add activity/case records only when the product need is demonstrated.

Do not code against the proposed field names below until the schema decision is explicitly approved.

## 1. Decision Needed

Approve a minimal first Relationship CRM schema slice:

- add module label `Relationship CRM` to `ifitwala_ed/modules.txt`
- add package path `ifitwala_ed/relationship_crm/`
- add one DocType:
  - `Education Relationship`

Do not add `Relationship Case` in the first slice.

Do not add `Relationship Activity` in the first slice unless the first implementation explicitly needs queryable structured touchpoints that cannot be represented by existing contextual ledgers, tasks, comments, or communication summaries.

Do not create a `Contacts` module. Frappe core owns native `Contact`, `Address`, and related contact DocTypes.

Use existing `Team` as the first owner-team model. Do not add a separate `Relationship Team` DocType in the first slice unless `Team` proves insufficient after permission tests.

## 2. Product Rationale

The risk is real: a school CRM can easily become a maze of records that staff do not understand.

The first slice should answer only this question:

```text
Does the institution need an owned relationship context beyond admissions, students, guardians, employees, communications, and finance records?
```

If yes, the first record should be the relationship context itself, not a full CRM stack.

The relationship context is useful when the school needs to remember:

- who owns the relationship
- which team may see or work on it
- what kind of education relationship it is
- which organization/school scope it belongs to
- what the next action is
- which existing records are relevant

It should not duplicate identity, contact, communication, event, finance, admissions, or student records.

## 3. First Slice Scope

The first slice should support institution-owned relationship context for:

- sponsors
- community partners
- feeder schools
- agents or relocation partners
- employers or internship hosts
- alumni or advancement relationships
- current-family relationships only when explicitly created by permitted staff

The first slice must not create:

- a generic address book
- broad native Contact search
- automatic Inquiry-to-relationship conversion
- automatic Student Applicant-to-relationship conversion
- raw contact export
- sales pipeline terminology
- a parallel alumni/person record
- a separate case hierarchy before actual workstreams prove the need

## 4. Relationship Versus Contact

`Education Relationship` is not the contact.

Contact data stays owned by the domain record or governed contact-point layer:

- former student identity stays on `Student`
- guardian identity stays on `Guardian`
- applicant-stage identity stays on `Inquiry` or `Student Applicant`
- employee identity stays on `Employee`
- raw email/phone values stay behind approved contact-data workflows

For alumni, the expected model is:

```text
Student: the former learner identity and school history
Governed contact/contact point: how permitted workflows reach the person
Education Relationship: alumni relationship context, owner team, visibility, next action
```

Example:

```text
Student: Maria Garcia
Education Relationship: Maria Garcia - Alumni
Category: Alumni
Owner Team: Advancement
Next Action: Invite to mentor evening
```

The relationship record may link to the `Student`, but it must not become a duplicate student, contact, or alumni-person table.

## 5. Proposed DocType

### 5.1 Education Relationship

Purpose: the school-owned relationship context.

Proposed package:

```text
ifitwala_ed/relationship_crm/doctype/education_relationship/
```

Proposed controller:

```text
EducationRelationship(Document)
```

Proposed fields:

- `relationship_title` Data, required, list view
- `relationship_category` Select, required, standard filter
- `status` Select, default `Active`, standard filter
- `organization` Link `Organization`, required, standard filter
- `school` Link `School`, optional, standard filter
- `owner_user` Link `User`, required, standard filter
- `owner_team` Link `Team`, required, standard filter
- `visibility_mode` Select, default `Team`, standard filter
- `primary_external_name` Data, optional
- `summary` Small Text, optional
- `next_action_on` Date, optional, list view
- `latest_activity_at` Datetime, read only, list view
- `linked_student` Link `Student`, optional, standard filter
- `linked_inquiry` Link `Inquiry`, optional, standard filter
- `linked_student_applicant` Link `Student Applicant`, optional, standard filter

Do not add raw email, phone, address, or contact-export fields.

Proposed `relationship_category` options:

```text
Admissions Family
Current Family
Sponsor
Community Partner
Feeder School
Agent / Relocation Partner
University / Pathway Partner
Employer / Internship Host
Alumni
Foundation / Grant Funder
Government / Authority
Vendor With Student Impact
Media / Public Relations
Other
```

Proposed `status` options:

```text
Active
On Hold
Closed
No Further Action
```

Proposed `visibility_mode` options:

```text
Owner Only
Team
Cross-Functional
Leadership
```

## 6. Deferred DocTypes

### 6.1 Relationship Activity

Defer `Relationship Activity`.

Add it only if the first implementation proves that schools need structured, queryable touchpoints beyond:

- existing admissions CRM activities
- existing communication ledgers
- existing event/visit records
- existing task or follow-up mechanisms
- a relationship-level `summary`, `next_action_on`, and projected timeline

If approved later, `Relationship Activity` should be append-only and server-owned. It should not be introduced just because "CRMs usually have activities."

### 6.2 Relationship Case

Defer `Relationship Case`.

Add it only when one `Education Relationship` regularly needs multiple parallel workstreams with separate owners, statuses, and close reasons.

Examples that may justify it later:

- one chamber of commerce relationship has separate careers fair, sponsorship, and board-engagement streams
- one foundation has separate scholarship grant, annual report, and donor visit streams
- one alumni relationship has separate mentoring, advancement, and governance streams

Until then, the relationship itself can hold owner, team, status, next action, and summary.

## 7. Permission And Scope Requirements

`Education Relationship` needs server-side permission query conditions before it becomes usable:

- organization scope is mandatory
- school scope is optional but must be enforced when set
- owner user access remains tenant-scoped
- owner team access remains tenant-scoped
- `Leadership` visibility is still tenant-scoped
- role alone must not grant broad access
- no native `Contact` broad-list fallback is allowed
- linked student/applicant/inquiry context must not bypass those records' own permissions

Initial roles may be:

- System Manager
- Relationship Manager
- Relationship Officer

Role names are proposed only. They require approval with the DocType permissions.

## 8. Runtime API Direction

The first runtime endpoints after schema approval should be server-owned workflows, not generic CRUD assembly:

- `get_relationship_center_context`
- `create_education_relationship`
- `update_education_relationship_next_action`
- `assign_relationship_owner`
- `close_education_relationship`
- `link_relationship_to_inquiry`
- `link_relationship_to_applicant`
- `link_relationship_to_student`

Every endpoint must return actionable blocked reasons and apply tenant scope before DTO assembly.

Do not add `create_relationship_case`, `record_relationship_activity`, or relationship timeline endpoints in the first implementation unless the schema approval explicitly expands the slice.

## 9. Deferred Schema And Features

Defer these until the one-DocType model proves insufficient:

- `Relationship Activity`
- `Relationship Case`
- generic relationship link child table
- secondary team child table
- raw contact-point storage
- sponsor finance detail fields
- relationship scoring or quality metrics
- Relationship Timeline endpoint
- complex Relationship Center queues

This keeps the first schema slice small and avoids turning the CRM into a generic contact database.

## 10. Approval Checklist

Before adding DocType metadata, explicitly approve:

- module label: `Relationship CRM`
- package path: `ifitwala_ed/relationship_crm/`
- first DocType: `Education Relationship`
- use of existing `Team` for `owner_team`
- proposed required fields
- proposed optional links to existing domain records
- proposed select vocabularies
- proposed roles or revised role names
- no raw contact fields in the first slice
- defer `Relationship Activity`
- defer `Relationship Case`

Once approved, implementation must add complete Frappe DocType package shape: `__init__.py`, `.json`, and matching `.py` controller class for `Education Relationship`.

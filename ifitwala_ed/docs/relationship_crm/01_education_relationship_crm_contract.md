# Education Relationship CRM Contract

Status: Planned target contract; no Relationship CRM schema or runtime endpoints are implemented yet.
Code refs:
- Related current admissions CRM runtime: `ifitwala_ed/admission/doctype/inquiry/*`, `ifitwala_ed/admission/doctype/admission_conversation/*`, `ifitwala_ed/admission/doctype/admission_message/*`, `ifitwala_ed/admission/doctype/admission_crm_activity/*`, `ifitwala_ed/api/admissions_crm.py`, `ifitwala_ed/api/admissions_inbox.py`
- Related current applicant communication runtime: `ifitwala_ed/api/admissions_communication.py`, `ifitwala_ed/setup/doctype/org_communication/*`, `ifitwala_ed/setup/doctype/communication_interaction_entry/*`, `ifitwala_ed/students/doctype/portal_read_receipt/*`
- Related current contact governance runtime: `ifitwala_ed/contacts/contact_privacy.py`, `ifitwala_ed/contacts/contact_audit.py`, `ifitwala_ed/utilities/contact_utils.py`
Test refs: None for planned Relationship CRM schema/runtime; related current coverage is listed in the referenced domain contracts.

This contract defines the approved product direction for an education-native CRM. It is not a sales CRM clone and it must not become a universal address book.

## 1. Authority

This contract must remain consistent with:

- `../security/contact_data_governance.md`
- `../setup/contact_permission_contract.md`
- `../admission/01_governance.md`
- `../admission/11_admissions_crm_contract.md`
- `../spa/17_admissions_inbox_contract.md`
- `../spa/07_org_communication_messaging_contract.md`
- `../high_concurrency_contract.md`
- `../nested_scope_contract.md`

If this contract conflicts with contact-data governance, admissions pipeline governance, governed-file rules, or nested-scope rules, those existing contracts win.

## 2. Product Goal

The product goal is:

```text
one education relationship -> one contextual view -> many legitimate school workflows
```

Users should work from the educational context they already understand:

- an Inquiry
- a Student Applicant
- a family
- a sponsor
- a feeder school
- a careers partner
- an alumni relationship
- an event, visit, sponsorship, pathway, or project

Users must not need to know whether a visible timeline item is stored as `Inquiry`, `Admission CRM Activity`, `Admission Message`, `Admission Visit`, `Org Communication`, `Communication Interaction Entry`, `Sales Invoice`, `Program Enrollment Request`, or a future relationship CRM record.

The backend may keep separated ledgers. The product surface must be contextual.

## 3. Education-Native Terminology

Approved planned terms:

- `Education Relationship`
  - the school-owned relationship container
  - may represent a family, sponsor, partner, feeder school, alumni group, employer, foundation, public authority, vendor with student impact, or similar education-relevant relationship
- `Relationship Case`
  - one concrete workstream under an Education Relationship
  - examples: sponsorship renewal, feeder-school visit, internship pathway, scholarship grant, family retention conversation, university pathway agreement
- `Relationship Activity`
  - append-only structured touchpoint or internal note under a Relationship Case or Education Relationship
  - examples: call, meeting, proposal sent, follow-up scheduled, no response, visit completed, renewal declined
- `Relationship Team`
  - ownership and visibility boundary for relationship work
  - examples: Admissions, Partnerships, Advancement, Careers, Activities, Finance, Leadership, Student Support
- `Relationship Timeline`
  - server-owned projection that presents relationship-relevant items from multiple ledgers in one ordered view

Rejected terms for this domain:

- `Sales Account`
- `Sales Deal`
- `Customer Pipeline`
- `Generic Contact`
- `Address Book`

Implementation may internally reuse framework capabilities where appropriate, but user-facing labels must stay education based.

## 4. Domain Boundaries

`Inquiry` remains intake.

`Student Applicant` remains the sole pre-student admissions container.

`Org Communication` remains the audience/message container for school communications and applicant-stage case messages.

Relationship CRM must not:

- create a parallel applicant container
- replace `Student Applicant`
- replace `Org Communication`
- convert every Inquiry into a relationship record automatically
- turn native Frappe `Contact` into a broad education CRM database
- expose raw email or phone lists as a generic CRM feature

Relationship CRM may:

- receive explicit handoffs from non-admissions or broader institutional inquiries
- link to admissions contexts when the relationship genuinely matters to admissions
- project admissions, communication, finance, visit, event, and enrollment state into a contextual timeline
- own school partnership, sponsorship, feeder-school, alumni, careers, and community relationship work

## 5. Relationship Categories

The planned relationship category vocabulary should start education-native and configurable only after the base contract is implemented.

Initial planned categories:

- Admissions Family
- Current Family
- Sponsor
- Community Partner
- Feeder School
- Agent / Relocation Partner
- University / Pathway Partner
- Employer / Internship Host
- Alumni
- Foundation / Grant Funder
- Government / Authority
- Vendor With Student Impact
- Media / Public Relations
- Other

Category is not a permission boundary by itself. Permission depends on organization, school, relationship team, role, and explicit visibility rules.

## 6. Education Use Cases

### 6.1 Sponsorships And Partnerships

Examples:

- local music store sponsoring a music program
- chamber of commerce supporting a careers fair
- sports club providing facility access
- local foundation funding scholarships

Expected CRM value:

- track owner, next action, renewal date, pledged amount or non-cash support where approved
- show linked events, invoices, communications, and outcome notes in one timeline
- preserve sponsorship context without turning finance records into CRM records

### 6.2 Feeder Schools And Agents

Examples:

- nursery or primary school referral relationship
- international agent
- relocation consultant

Expected CRM value:

- track referred inquiries/applicants
- compare conversion quality by relationship
- manage visits, open days, referral follow-up, and annual check-ins

### 6.3 University And Pathway Partners

Examples:

- university counselor relationship
- dual-credit pathway
- transfer pathway
- scholarship connection

Expected CRM value:

- link school visits, student outcomes, pathway notes, deadlines, and counselor tasks
- support long-term institutional memory beyond one event

### 6.4 Employers And Career Learning

Examples:

- internship hosts
- work-experience partners
- guest speakers
- project mentors

Expected CRM value:

- track placement capacity, safeguarding status where applicable, student fit notes, and post-placement feedback
- keep careers relationship history visible without leaking student-sensitive data broadly

### 6.5 Alumni And Advancement

Examples:

- alumni mentors
- alumni donors
- alumni ambassadors
- board candidates

Expected CRM value:

- preserve alumni contribution context
- connect mentoring, giving, events, pathway support, and outreach plans

### 6.6 Current-Family Relationship Work

Examples:

- retention-risk conversation
- hardship support
- sibling planning
- high-touch family concern
- re-enrollment follow-up

Expected CRM value:

- let staff manage relationship work without treating current families as sales leads
- surface only purpose-appropriate student, guardian, finance, attendance, or support context
- audit raw contact-value access through named workflows

## 7. Planned Product Flow

The planned high-level flow is:

```text
Inquiry or staff intake
-> optional Education Relationship
-> optional Relationship Case
-> Relationship Timeline
-> next action / outcome
```

Not every Inquiry should become an Education Relationship.

Not every Education Relationship needs an active Relationship Case.

Not every Relationship Case is admissions related.

The action to create or link a relationship must be explicit, permission checked, and contextual.

## 8. Relationship Center

The planned staff route is:

```text
/staff/relationships
```

This is the Relationship Center, not a generic CRM console.

Initial planned queues:

- Needs Reply
- Unassigned
- Due Today
- Stale
- Sponsors
- Partnerships
- Current Families
- Admissions Hand-offs

Initial planned actions:

- Record Touchpoint
- Assign Owner
- Schedule Follow-up
- Create Case
- Link Inquiry
- Link Applicant
- Link Communication
- Close Case
- Mark No Further Action with reason

The Relationship Center must use bounded context endpoints and server-owned action endpoints. It must not assemble workflow behavior from generic CRUD calls.

## 9. Implementation Sequence

Implementation must proceed in this order:

1. Lock the education-native vocabulary and planned contracts in docs.
2. Implement admissions contextual timeline projection over existing records first.
3. Add shared contextual action affordances to Inquiry, Student Applicant, Admissions Inbox, and Admissions Cockpit.
4. Approve Relationship CRM schema names and fields.
5. Implement the first Relationship CRM DocTypes and server permission hooks.
6. Implement Relationship Center with bounded context endpoint and server-owned mutation endpoints.
7. Add activity plans after core ownership, scope, and timeline rules are proven.

No Relationship CRM DocType metadata should be added before step 4 is explicitly approved.

## 10. Non-Goals

This contract does not approve:

- native Frappe `Contact` as a broad CRM database
- raw contact exports from Relationship Center
- sales-style revenue forecasting as the base model
- client-side matching across all students, guardians, applicants, and contacts
- automatic fuzzy matching or auto-linking to families
- generic report-builder access over personal contact values
- duplicating `Org Communication` or admissions message ledgers
- replacing accounting, enrollment, admissions, or communication workflow ownership

## 11. Test Expectations

Every implementation slice must include focused tests for:

- tenant scope and sibling-school isolation
- role plus Relationship Team visibility
- no broad native `Contact` list or raw-value access
- explicit relationship creation/linking from Inquiry and Student Applicant contexts
- contextual timeline DTOs that do not require per-row follow-up requests
- blocked actions returning actionable reasons
- append-only activity behavior where the relevant activity contract requires it
- no client-side inference of queue membership or permission

# Ifitwala_Ed First-Traction Audit

Status: Point-in-time audit, not canonical runtime authority
Date: 2026-04-26
Scope: First commercial wedge, "The admissions pipeline that stops small schools leaking enquiries."

## Bottom line

Ifitwala_Ed is closer to demo-ready than architecture-only for the admissions wedge, but only if the public demo is tightly scoped to inquiry capture, ownership, SLA visibility, application checklist, document review, staff cockpit, applicant messages, and offer acceptance.

The strongest current product is not a broad ERP. It is a credible admissions operating layer built on real DocTypes, server-owned workflow state, governed documents, applicant portal UX, and staff review surfaces.

The largest gap for first traction is connective tissue: one admissions pipeline view that joins `Inquiry`, `Student Applicant`, readiness, messages, offer state, next action, and deadline. Deposits, re-enrolment, and communications automation have strong building blocks but are not yet workflow-ready for a public wedge promise.

Do not market this as full admissions, finance, re-enrolment, and CRM automation yet. Market the smallest reliable journey: "capture every enquiry, assign it, follow it up, convert it to an application, collect documents, and know what is stuck."

## Current assets found

Evidence was taken from current repository files only. Key canonical docs reviewed:

- `ifitwala_ed/docs/README.md`
- `ifitwala_ed/docs/admission/README.md`
- `ifitwala_ed/docs/admission/01_governance.md`
- `ifitwala_ed/docs/admission/02_applicant_and_promotion.md`
- `ifitwala_ed/docs/admission/05_admission_portal.md`
- `ifitwala_ed/docs/admission/07_applicant_evidence_review_redesign.md`
- `ifitwala_ed/docs/admission/08_admission_program_enrollment_request_proposal.md`
- `ifitwala_ed/docs/admission/10_ifitwala_drive_portal_uploads.md`
- `ifitwala_ed/docs/enrollment/03_enrollment_architecture.md`
- `ifitwala_ed/docs/enrollment/07_year_rollover_architecture.md`
- `ifitwala_ed/docs/accounting/accounting_notes.md`
- `ifitwala_ed/docs/accounting/fees_full_cycle_note.md`
- `ifitwala_ed/docs/accounting/phase1_notes.md`
- `ifitwala_ed/docs/spa/07_org_communication_messaging_contract.md`
- `ifitwala_ed/docs/spa/13_org_communication_quick_create_contract.md`
- `ifitwala_ed/docs/files_and_policies/README.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`

Existing DocTypes directly relevant to the wedge:

- Admissions: `Inquiry`, `Admission Settings`, `Student Applicant`, `Student Applicant Guardian`, `Applicant Document Type`, `Applicant Document`, `Applicant Document Item`, `Applicant Review Assignment`, `Applicant Review Rule`, `Applicant Health Profile`, `Recommendation Template`, `Recommendation Request`, `Recommendation Submission`, `Applicant Interview`, `Applicant Interview Feedback`, `Applicant Enrollment Plan`.
- Enrollment and seats: `Program Offering`, `Program Offering Selection Window`, `Program Enrollment Request`, `Program Enrollment`, `Program Enrollment Tool`, `End of Year Checklist`.
- Finance: `Account Holder`, `Billable Offering`, `Sales Invoice`, `Sales Invoice Item`, `Payment Entry`, `Payment Request`, `Payment Terms Template`, `Program Billing Plan`, `Billing Schedule`, `Billing Run`, `Payment Reconciliation`, `Dunning Notice`, `Statement Of Accounts Run`.
- Communications: `Org Communication`, `Org Communication Audience`, `Communication Interaction Entry`, `Portal Read Receipt`.

Existing controllers and domain modules:

- `ifitwala_ed/admission/doctype/inquiry/inquiry.py`
- `ifitwala_ed/admission/admission_utils.py`
- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/admission/applicant_document_readiness.py`
- `ifitwala_ed/admission/applicant_review_workflow.py`
- `ifitwala_ed/admission/admissions_portal.py`
- `ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.py`
- `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
- `ifitwala_ed/schedule/doctype/program_offering_selection_window/program_offering_selection_window.py`
- `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`
- `ifitwala_ed/schedule/doctype/program_enrollment/program_enrollment.py`
- `ifitwala_ed/accounting/doctype/sales_invoice/sales_invoice.py`
- `ifitwala_ed/accounting/doctype/payment_request/payment_request.py`
- `ifitwala_ed/accounting/billing/invoice_generation.py`
- `ifitwala_ed/accounting/billing/schedule_generation.py`
- `ifitwala_ed/setup/doctype/org_communication/org_communication.py`

Existing API and portal endpoints:

- Inquiry analytics and link queries: `ifitwala_ed/api/inquiry.py`
- Staff admissions cockpit: `ifitwala_ed/api/admission_cockpit.py`
- Applicant portal: `ifitwala_ed/api/admissions_portal.py`
- Admissions case messages: `ifitwala_ed/api/admissions_communication.py`
- Focus actions for inquiry and review work: `ifitwala_ed/api/focus.py`, `ifitwala_ed/api/focus_actions_inquiry.py`, `ifitwala_ed/api/focus_actions_applicant_review.py`
- Self-enrollment and rollover support: `ifitwala_ed/api/self_enrollment.py`
- Enrollment analytics: `ifitwala_ed/api/enrollment_analytics.py`
- Guardian finance read model: `ifitwala_ed/api/guardian_finance.py`
- Org communication quick create and interactions: `ifitwala_ed/api/org_communication_quick_create.py`, `ifitwala_ed/api/org_communication_interactions.py`

Existing UX surfaces:

- Public web form: `ifitwala_ed/admission/web_form/inquiry/inquiry.json`, route `apply/inquiry`.
- Desk Inquiry form and list: `ifitwala_ed/admission/doctype/inquiry/inquiry.js`, `inquiry_list.js`.
- Admissions SPA routes under `/admissions`: overview, profile, health, documents, policies, messages, course choices, submit, status.
- Staff pages: `InquiryAnalytics.vue`, `AdmissionsCockpit.vue`, Focus overlays and inquiry follow-up action.
- Guardian/student self-enrollment pages: existing course selection support.
- Guardian finance page: read-only family invoices/payments snapshot.

Existing settings, reports, dashboards:

- `Admission Settings`: `sla_enabled`, `sla_check_interval_hours`, `todo_color`, `first_contact_sla_days`, `followup_sla_days`, `admissions_access_mode`, `show_guardians_in_admissions_profile`, `auto_hydrate_enrollment_request_after_promotion`.
- Inquiry analytics: counts, first response, SLA status, assignee distribution, workflow pipeline, type distribution, lane breakdown.
- Admissions Cockpit: applicant counts, readiness chips, blockers, unread messages, AEP state, send offer and hydrate request actions.
- Enrollment analytics and reports: enrollment dashboard, enrollment trend/report/gaps/request overview.
- Finance reports and workflows: aged receivables, account holder statement, student attribution, payment request, dunning, statements.

## Feature 1: Enquiry-to-enrolment pipeline

* Readiness:
  * Partially usable, close to demo-ready for a controlled admissions staff demo.

* Existing assets:
  * `Inquiry` has verified fields for capture and tracking: `first_name`, `last_name`, `email`, `phone_number`, `type_of_inquiry`, `message`, `submitted_at`, `workflow_state`, `sla_status`, `assigned_to`, `assignment_lane`, `contact`, `student_applicant`, `first_contact_due_on`, `followup_due_on`, `first_contacted_at`, `assigned_at`, `intake_assigned_at`, `resolver_assigned_at`, response-hour fields, `organization`, and `school`.
  * Public inquiry web form exists at route `apply/inquiry`, mapped to `Inquiry`, anonymous and published.
  * Server-owned Inquiry states are enforced in the controller: `New`, `Assigned`, `Contacted`, `Qualified`, `Archived`.
  * Desk actions exist for assign, reassign, mark contacted, qualify, archive, create Contact, and invite to apply.
  * Assignment and reassignment use scoped assignee lookup through `get_inquiry_assignees`, scope validation, Frappe ToDo assignment, lane metrics, and notifications.
  * SLA deadlines and status are server-maintained through `set_inquiry_deadlines`, `update_sla_status`, and the hourly SLA sweep wrapper.
  * Inquiry list view displays workflow and SLA indicators.
  * Staff Focus can surface inquiry follow-up work and supports `mark_inquiry_contacted` and `create_inquiry_contact`.
  * Inquiry Analytics exists in the SPA and returns counts, SLA buckets, response metrics, assignee distribution, workflow pipeline, lane breakdown, and filters.
  * Inquiry-to-applicant handoff exists through `invite_to_apply` and `from_inquiry_invite`; the `Student Applicant.inquiry` link is immutable once set.

* Demo gaps:
  * There is no single first-traction pipeline screen spanning `Inquiry` to `Student Applicant` to `Applicant Enrollment Plan`.
  * There is no Kanban-ready or stage-board route found for the first wedge. Desk list and analytics exist, but a buyer-facing admissions pipeline board is not evident.
  * "Next action" is not a verified `Inquiry` field. The behavior is split across `first_contact_due_on`, `followup_due_on`, ToDo, Focus items, and workflow state.
  * The public web form is very thin. It captures core enquiry fields but does not expose a polished small-school admissions intake experience.
  * Inquiry source/channel/campaign attribution was not found in the verified `Inquiry` schema, which weakens demo analytics around lead quality.

* Pilot gaps:
  * One canonical pipeline read model is needed for active prospects with owner, current stage, next action, due date, SLA, application status, document blockers, message state, offer state, and enrollment handoff.
  * Admissions staff need a low-friction reassignment and follow-up workflow from the same surface where they triage enquiries.
  * Source attribution, duplicate detection, and returning-family/sibling detection should be added before claiming leakage analytics.
  * First-response and follow-up SLA settings need pilot-safe operational defaults and visible exception handling.
  * The inquiry-to-applicant conversion should consistently capture school/program/offering context without forcing Desk navigation.

* Risks:
  * Technical: inquiry workflow behavior is distributed across controller methods, `admission_utils`, Desk JS, Focus actions, and analytics APIs.
  * UX: staff may have to move between Web Form, Desk Inquiry, Focus, Inquiry Analytics, and Admissions Cockpit to explain one pipeline.
  * Data integrity: `next action` is inferred rather than stored as one canonical workflow fact; this can cause inconsistent reporting.
  * Security/privacy: row visibility is scoped by roles and assignment, but a new pipeline surface must preserve server-side scope filtering and not widen access through aggregated payloads.
  * Concurrency: assignment and mark-contacted paths already use locks/idempotency in Focus, but any new board mutation must keep those properties.

* Highest-impact next actions:
  * Build one admissions pipeline read endpoint and staff page for the first wedge: active Inquiry plus linked Applicant/AEP summary, owner, stage, next due date, SLA, and stuck reason.
  * Normalize the displayed next action from existing facts first, before adding schema: unassigned, first contact due, follow-up due, qualify, invite to apply, application blocked, offer pending.
  * Polish the public inquiry intake and immediate staff triage path so the demo starts with a live enquiry and ends with a visible owner and due date.

## Feature 2: Online application, checklist and document collection

* Readiness:
  * Demo-ready for a controlled applicant-portal and staff-review demo.

* Existing assets:
  * `Student Applicant` is the sole pre-student admissions container and has verified fields for inquiry link, applicant identity, organization, school, program, academic year, term, program offering, application status, guardians table, readiness summaries, profile fields, cohort, and house.
  * Application statuses are verified in schema and controller: `Draft`, `Invited`, `In Progress`, `Submitted`, `Under Review`, `Missing Info`, `Approved`, `Rejected`, `Withdrawn`, `Promoted`.
  * `/admissions` SPA has routes for overview, profile, health, documents, policies, messages, course choices, submit, and status.
  * Applicant portal APIs include session, snapshot, profile, health, documents, policies, messages, submission, withdrawal, family invite, applicant invite, offer accept/decline, and enrollment choices.
  * `Admission Settings.admissions_access_mode` supports `Single Applicant Workspace` and `Family Workspace`; `show_guardians_in_admissions_profile` controls guardian profile collection.
  * `Applicant Document` is the requirement card; `Applicant Document Item` is the concrete submitted file; `Applicant Review Assignment` is the review task.
  * Document review status is verified at both parent and item levels: `Pending`, `Approved`, `Rejected`, `Superseded`.
  * Requirement overrides exist through `Applicant Document.requirement_override` with `Waived` and `Exception Approved`.
  * Governed admissions uploads are Drive-backed for applicant documents, health vaccination proof, applicant profile image, and guardian image.
  * Applicant portal document DTOs return server-owned `open_url`, `preview_url`, and `thumbnail_url`; raw private paths are not the intended contract.
  * `StudentApplicant.get_readiness_snapshot()` computes readiness across profile, policies, documents, recommendations, and health when required.
  * Applicant Overview and Submit pages consume server-derived completeness and `next_actions`.
  * Admissions Cockpit surfaces readiness chips and top blockers.

* Demo gaps:
  * The application portal is broad enough for a demo, but the first wedge story needs a tighter "what is missing and what should I do next" narrative.
  * Health, recommendations, interviews, and evidence review still live in adjacent surfaces rather than one fully unified applicant decision workspace.
  * Family workspace exists as settings/access direction, but the docs still mark the richer family admissions workspace as proposal-level rather than current runtime authority.
  * There is no obvious form-builder or school-configurable application question layer in the inspected wedge paths.
  * The public demo must avoid implying automatic e-signature or advanced form automation beyond implemented policies and acknowledgements.

* Pilot gaps:
  * Schools need a repeatable setup path for required document types, repeatable requirements, waiver policy, health requirement, policies, and recommendation templates.
  * Parent-facing missing-document reminders need to be connected to the document state model.
  * Staff need one applicant workspace that joins profile, guardians, document evidence, recommendation status, interview notes, messages, and readiness.
  * Guardian/family collaboration needs pilot-safe permissions and clear ownership so `applicant_user` is not treated as the guardian identity.
  * The Inquiry to Student Applicant handoff should copy and expose enough context to remove duplicate parent entry without inventing missing schema.

* Risks:
  * Technical: `ifitwala_ed/api/admissions_portal.py` has explicit whitelisted methods, but it also contains request/form fallback helpers. This is a contract risk against the project rule that server code should use explicit whitelisted method arguments rather than raw `frappe.form_dict`.
  * UX: the portal can feel like multiple modules unless the demo emphasizes one checklist and one next action list.
  * Data integrity: readiness is server-owned, which is good, but adding new checklist dimensions requires verified schema and controller ownership.
  * Security/privacy: applicant documents, health data, recommendation data, guardian data, and private media must remain governed and scope-checked server-side.
  * Multi-tenant: document type scope and applicant school/organization immutability are strengths, but any family workspace expansion must not leak sibling/applicant data across schools.

* Highest-impact next actions:
  * Create a first-traction applicant checklist view that uses the existing readiness snapshot and document DTOs but removes secondary ERP complexity from the demo.
  * Close the contract gap in admissions portal methods by moving demo-critical mutations to explicit argument parsing only, with tests for payload shape.
  * Add a staff "applicant decision brief" panel inside Admissions Cockpit that joins readiness, document blockers, latest message, AEP state, and reviewer tasks.

## Feature 3: Re-enrolment and seat planning

* Readiness:
  * Structurally present but not workflow-ready for the first public wedge.

* Existing assets:
  * `Program Offering` has verified capacity and seat fields: `capacity`, `seat_policy`, `seat_hold_hours`, `allow_self_enroll`, `status`, `school`, `program`, `offering_academic_years`, and courses.
  * `Program Offering Selection Window` exists for student/guardian self-service choices with `program_offering`, `academic_year`, `audience`, `status`, `open_from`, `due_on`, `source_mode`, source fields, and student rows.
  * `Program Enrollment Request` supports staging with `student`, `program_offering`, `program`, `school`, `academic_year`, `status`, courses, validation fields, override fields, `selection_window`, and admissions-source fields.
  * `Program Enrollment` is committed enrollment truth with `student`, `program`, `academic_year`, `enrollment_date`, courses, `school`, `program_offering`, request link, and `enrollment_source`.
  * `Program Enrollment Tool` supports staff-driven rollover through prepare, validate, approve, and materialize.
  * Self-enrollment API supports portal board, choice state, save choices, and submit choices.
  * Enrollment Analytics exists for active enrollments, net change, archived, and drilldown.
  * Canonical docs explicitly define rollover as split across Program Enrollment Tool, Program Offering Selection Window, and End of Year Checklist.

* Demo gaps:
  * No single re-enrolment commitment workflow was found for returning, leaving, undecided, confirmed, pending, or withdrawn family intent.
  * Capacity exists on Program Offering, but a live seat-planning dashboard that combines returning students, pending requests, offers, accepted applicants, and capacity was not found.
  * Existing self-enrollment is course/choice-window oriented, not packaged as "re-enrolment confirmation" for heads.
  * Existing rollover tooling is operational and Desk-heavy, not a polished first-traction admissions wedge demo.
  * Re-enrolment is adjacent to the first wedge but would distract unless framed as a future add-on.

* Pilot gaps:
  * A pilot needs a returning-student declaration model or a verified reuse of existing request/window statuses for return intent.
  * Seat availability needs a server-owned read model that reconciles Program Offering capacity, committed enrollments, submitted/approved PERs, accepted AEPs, and seat policy.
  * Leadership needs forecast-to-actual reporting by academic year, program, school, and offering.
  * Family-facing re-enrolment reminders and deadlines need workflow ownership.
  * Leaving/withdrawal workflow must be clear and separate from year-end closure.

* Risks:
  * Technical: rollover is intentionally split by canonical docs; forcing it into one wizard without approval would create architecture drift.
  * UX: if shown too early, re-enrolment can dilute the first admissions pipeline story.
  * Data integrity: capacity cannot be trusted if it ignores AEP accepted offers, PER statuses, or `seat_policy`.
  * Security/privacy: guardian/student self-enrollment visibility must remain restricted to authorized students and linked guardians.
  * Concurrency: seat holds and waitlist-like behavior need transaction-safe claims if they become a public promise.

* Highest-impact next actions:
  * Do not include re-enrolment in the first public demo except as a future roadmap screenshot or internal architecture proof.
  * Build a read-only seat exposure panel first: capacity, active enrollments, submitted PERs, approved PERs, accepted AEPs, and remaining seats.
  * Define whether re-enrolment intent is a new first-class workflow or a constrained reuse of Program Offering Selection Window before editing schemas.

## Feature 4: Deposits, invoicing and payment plans

* Readiness:
  * Structurally present but not workflow-ready for admissions deposits.

* Existing assets:
  * Accounting architecture is ERPNext v16 aligned at the concept level, but implemented in Ifitwala_Ed with education naming.
  * `Account Holder` is the legal debtor, verified with `organization`, `account_holder_name`, `account_holder_type`, `status`, `primary_email`, and `primary_phone`.
  * `Sales Invoice` is the legal billing document with `account_holder`, `organization`, `school`, `program`, `program_offering`, `posting_date`, `due_date`, `payment_terms_template`, items, payment schedule, totals, paid amount, outstanding amount, and status.
  * `Payment Request` exists with `organization`, `account_holder`, `sales_invoice`, `status`, request/due dates, requested/outstanding amounts, contact fields, and message.
  * `Payment Terms Template` exists and drives invoice payment schedules.
  * `Payment Entry`, `Payment Reconciliation`, dunning, statements, aged receivables, and account-holder statements exist.
  * Program-based billing is implemented through `Program Billing Plan`, `Billing Schedule`, and `Billing Run`; draft invoices are generated from committed `Program Enrollment`.
  * Guardian finance snapshot is implemented as a read-only portal view for invoices and payments.
  * Accounting docs explicitly say current invoicing is Desk-first and general parent-facing payment portal / automated collection workflow is not implemented.

* Demo gaps:
  * No admissions deposit workflow was found that connects `Applicant Enrollment Plan` offer acceptance to `Account Holder`, `Sales Invoice`, `Payment Request`, or deposit status.
  * No online payment action or payment gateway workflow was found in the inspected admissions/guardian finance surfaces.
  * Promotion explicitly has no billing or finance setup side effects.
  * Program Billing Plan starts from committed `Program Enrollment`, which is too late for admissions deposits.
  * Guardian Finance is read-only and is not positioned as admissions deposit collection.

* Pilot gaps:
  * A pilot needs a minimal admissions-deposit path: accepted offer creates or links payer, creates draft/submitted deposit invoice or payment request, tracks payment status, and exposes status to admissions staff.
  * Account Holder creation/linking from financial guardian data needs explicit workflow ownership and permission tests.
  * Payment plan readiness should reuse `Payment Terms Template` and `Sales Invoice Payment Schedule`, not create a parallel installment model.
  * Gateway integration can wait, but manual payment status and payment request tracking must be reliable.
  * Finance dashboards need to show accepted offers without deposit, unpaid deposit invoices, overdue deposit requests, and paid deposits.

* Risks:
  * Technical: deposit billing bridges admissions and accounting domains; schema or workflow changes require explicit approval and doc updates.
  * UX: showing finance in the first demo before deposits are connected can overpromise.
  * Data integrity: never represent paid status outside accounting truth; `Sales Invoice`, `Payment Entry`, and `Payment Request` must remain the source of financial state.
  * Security/privacy: parent-facing finance must check guardian financial authority and Account Holder access server-side.
  * Accounting: do not create a simplified admissions balance that bypasses GL, invoices, or account-holder rules.

* Highest-impact next actions:
  * For demo, show deposits as "next milestone" unless a small backed-by-accounting deposit slice is built.
  * Define a minimal admissions deposit contract using existing `Account Holder`, `Sales Invoice`, `Payment Request`, and `Payment Terms Template`; do not add a parallel deposit table without approval.
  * Add a staff-only deposit status read model on AEP/applicant cards before exposing parent payment UX.

## Feature 5: Parent communications automation

* Readiness:
  * Structurally present but not workflow-ready for automation. Manual and threaded communication is partially usable.

* Existing assets:
  * `Org Communication` is the shared communication container with verified fields for title, type, status, priority, school, organization, activity context, admission context, publish window, portal surface, audiences, message, attachments, interaction mode, and thread flags.
  * `Communication Interaction Entry` is the runtime ledger for comments/reactions/questions with user, audience type, surface, intent, reaction, note, visibility, and resolution fields.
  * `Portal Read Receipt` is the read-state ledger per canonical docs.
  * Admissions wrappers exist: `send_admissions_case_message`, `get_admissions_case_thread`, `mark_admissions_case_thread_read`.
  * Admissions communication supports `Student Applicant` and `Inquiry` contexts through `admission_context_doctype` and `admission_context_name`.
  * Admissions Cockpit includes thread summaries such as unread count, last message, preview, and needs-reply state.
  * Org Communication quick-create supports draft, scheduled, published, portal feed, attachments, audience presets, idempotency, and server-owned validation.
  * Inquiry notifications exist as Frappe Notification fixtures for new inquiry and inquiry assignment, plus realtime `inbox_notification` publishing in code.
  * Recommendation intake sends email using `frappe.sendmail`, and admissions invite flows use email/user invite behavior.
  * Translation discipline is present in code through `_()` usage for many messages; no audit-wide localization validation was run.

* Demo gaps:
  * No stage-based automation engine was found for inquiry follow-up, missing-document reminders, application status updates, offer reminders, deposit reminders, or re-enrolment reminders.
  * Existing communications are strong as manual threads and school communications, but not yet a triggered admissions journey.
  * There is no visible template/campaign layer for admissions lifecycle messages.
  * Inquiry follow-up is ToDo/Focus/SLA oriented, not parent-message automation.
  * Offer/deposit reminders cannot be credible until deposits are connected to finance state.

* Pilot gaps:
  * Need lifecycle triggers for `Inquiry`, `Student Applicant`, `Applicant Document`, `Applicant Enrollment Plan`, `Payment Request`, and re-enrollment windows.
  * Need templates that are school-scoped, localized, and safe for variable substitution under the repo i18n rules.
  * Need an audit trail that shows which automated messages were sent, skipped, paused, or failed.
  * Need opt-out, consent, retry, and failure visibility for outbound email/SMS/WhatsApp if external channels are added.
  * Need automation pause/escalation when a parent replies or a staff owner changes.

* Risks:
  * Technical: `Org Communication` is mature but broad; admissions automation should not create a second message model.
  * UX: automation without action-specific deep links will feel like noise and weaken the "stop leakage" wedge.
  * Data integrity: reminders must be derived from server-owned workflow state, not client-inferred stage.
  * Security/privacy: applicant and guardian communication must not leak applicant, health, document, recommendation, or finance state across family members or schools.
  * Localization: dynamic messages must obey stable literal source-string rules and named placeholders.

* Highest-impact next actions:
  * Build an admissions journey reminder service on top of `Org Communication` and admissions case context, not a parallel communications subsystem.
  * Start with three triggers only: overdue first contact, missing required documents, and offer pending response.
  * Add a staff-visible communication timeline on the pipeline/applicant card before adding complex outbound channels.

## Cross-feature architecture observations

- The first wedge is spread across multiple good systems rather than expressed as one product: Inquiry Desk/list, Focus, Inquiry Analytics, Student Applicant, Admissions Portal, Admissions Cockpit, AEP, Org Communication, Enrollment, and Accounting.
- Inquiry action logic is fragmented across `Inquiry` controller methods, `admission_utils`, Desk JS, Focus wrapper endpoints, and analytics. This is workable, but the demo needs one orchestration surface.
- `Inquiry` and `Student Applicant` have a real link, but pipeline analytics do not yet appear to treat that link as a single journey from enquiry to enrolled student.
- Admissions document collection is one of the most mature areas. It should be surfaced in the wedge rather than hidden behind broad ERP positioning.
- Communications are technically strong but product-fragmented: Org Communication is general, admissions messages are wrappers, notifications are Frappe fixtures/realtime, and automation is not first-class.
- Finance is accounting-correct, but admissions deposits are not connected. Avoid presenting accounting breadth as admissions deposit readiness.
- Re-enrolment has robust enrollment structures, but it is a separate operational product. It can become a strong add-on after the enquiry-to-enrolment wedge works.
- The applicant portal API has explicit endpoints but also form/request payload fallback helpers. For first-traction polish, demo-critical endpoints should be audited against the explicit-argument rule.
- Dashboards are fragmented by domain. The buyer needs one admissions pipeline dashboard, not separate Inquiry Analytics, Admissions Cockpit, Enrollment Analytics, and finance reports.
- The codebase already follows the right principle in many places: server-owned state and permissions. The roadmap should preserve that, not move pipeline state into the SPA.

## Hidden strengths to surface publicly

- Server-owned enquiry workflow states, assignment, reassignment, SLA dates, and response-time metrics are already real.
- The system can turn an Inquiry into a Student Applicant without treating the application as a disconnected form submission.
- Applicant document collection is governed, reviewable, repeatable, waiver-aware, and parent-facing.
- The admissions portal already gives families profile, health, documents, policies, messages, submission, course choices, and offer status in one authenticated SPA.
- Admissions Cockpit already has readiness chips, blockers, unread replies, AEP state, send-offer action, and request hydration action.
- The AEP bridge is a meaningful differentiator: offer acceptance can connect admissions to enrollment staging instead of ending in a PDF/email dead end.
- Multi-tenant organization/school scope is built into Inquiry, Student Applicant, documents, enrollment, communications, and accounting concepts.
- The governed file architecture is stronger than typical small-school admissions tools, especially private previews/open URLs and Drive-owned file authority.
- Communication read state and message ledger are already shared across admissions, guardian, student, and staff surfaces.
- Accounting is not a toy module: Account Holder, invoice, payment, advances, payment terms, dunning, statements, and GL posting are present.

## Dangerous distractions to avoid

- Do not reposition publicly as a full school ERP before the admissions wedge is sharp.
- Do not build broad LMS, gradebook, attendance, timetable, HR, inventory, or portfolio demos for first traction.
- Do not build a full payment gateway integration before proving a manual admissions deposit workflow backed by accounting truth.
- Do not build a generic CRM campaign builder before three admissions-specific triggers work.
- Do not build AI document review before the checklist, missing document reminder, and staff review brief are demo-tight.
- Do not build full re-enrolment orchestration before the enquiry-to-enrolment journey has a single staff surface.
- Do not build a public website/CMS sales story around admissions before the pipeline itself is demoable.
- Do not create parallel "simple finance" or "simple messaging" tables that bypass existing accounting and Org Communication truth.

## Smallest credible school demo flow

The smallest credible demo that can be shown to a real small international/private school within 2-4 weeks:

1. A family submits a public inquiry through `apply/inquiry`.
2. Admissions manager sees the new inquiry, assigns it to an admissions officer, and the due date/SLA becomes visible.
3. Assigned officer opens the focus item or pipeline row, creates/links the Contact, marks first contact complete, and qualifies the inquiry.
4. Staff invites the family to apply, choosing verified organization/school scope.
5. Family logs into `/admissions`, sees an overview with clear next actions, completes profile/guardian fields, uploads required documents, acknowledges policies, and submits.
6. Staff opens Admissions Cockpit, sees the applicant readiness chips, document blockers, latest message state, and review actions.
7. Staff approves the application path enough to send an enrollment offer through AEP.
8. Family accepts the offer in the admissions portal status page.
9. Staff shows that the accepted offer can hydrate a `Program Enrollment Request`, while clearly stating that deposit/payment automation is the next milestone unless implemented before demo.

What not to show in this demo:

- Full accounting setup.
- Full re-enrolment.
- Payment gateway.
- General school ERP modules.
- Broad analytics beyond enquiry leakage and application blockers.

## 2-4 week roadmap

Must fix before public demo:

- Create a first-traction admissions pipeline view or route that joins Inquiry, owner, stage, SLA, next action, linked applicant, applicant status, readiness blockers, message state, and AEP state.
- Make the public inquiry-to-applicant demo path deterministic with seed/setup data for organization, school, admissions roles, document types, policies, and at least one program/offering.
- Tighten the applicant portal demo around overview, profile, documents, policies, messages, submit, and status. Hide or de-emphasize nonessential portal routes if they distract.
- Add or expose a server-derived next-action label for every pipeline row using existing fields first.
- Make Admissions Cockpit the staff decision surface for the demo, not raw Desk records.
- Add a small "missing documents" and "needs reply" story to show leakage prevention after the initial enquiry.
- Verify demo-critical whitelisted methods use explicit arguments and do not rely on broad `frappe.form_dict` fallback paths.
- Produce a short setup checklist for demo schools: roles, settings, document types, policies, program offering, and test users.

Must fix before pilot:

- Add source/channel attribution if the pilot wants to measure lead quality.
- Add a canonical admissions journey read model with tests and scoped cache behavior.
- Add lifecycle communication triggers for overdue first contact, missing required documents, and pending offer response.
- Add a minimal accounting-backed deposit status slice or explicitly remove deposit from pilot promise.
- Add staff-visible communication timeline per applicant/pipeline row.
- Add permission tests for the aggregated pipeline payload.
- Add workflow tests for Inquiry to Student Applicant to AEP to accepted offer.
- Add operational reporting: open enquiries without owner, overdue first contact, incomplete applications, missing docs aging, offers awaiting response.

Can wait until after first pilot:

- Full re-enrolment workflow.
- Capacity forecasting across returning students and admissions offers.
- Parent payment plan request and approval UX.
- Payment gateway integration.
- AI/OCR document intelligence.
- Full family workspace across multiple students and applicants.
- Advanced board analytics.
- External messaging channels beyond email/system/portal messaging.

Should be explicitly avoided for now:

- Broad ERP launch narrative.
- Parallel CRM, finance, or messaging subsystems.
- Schema-heavy re-architecture before the pipeline demo proves buyer pull.
- Large generated audit artifacts or exhaustive docs that do not directly support the first traction wedge.

## 90-day pilot-readiness roadmap

Must fix before pilot:

- Pipeline MVP: one server-owned pipeline endpoint/page with owner, current stage, next action, due date, SLA, applicant status, document blockers, unread messages, and AEP state.
- Application MVP: school-configured required document types, policy requirements, profile requirements, and clear applicant next actions.
- Review MVP: one staff applicant decision brief with documents, health, recommendations, interviews, guardians, messages, and readiness.
- Communications MVP: three triggered reminder types using `Org Communication` or admissions case context, with staff-visible timeline and audit trail.
- Offer MVP: AEP offer send, portal accept/decline, offer expiry visibility, and post-acceptance request hydration.
- Finance MVP: choose one of two explicit positions:
  - no admissions deposits in pilot scope; or
  - accounting-backed deposit invoice/payment request status, staff-only first, parent-facing second.
- Metrics MVP: time to first response, overdue first contact, inquiry-to-application conversion, application completion, missing document aging, submitted-to-offer time, offer acceptance.
- Permission MVP: server-side tests for aggregated pipeline rows, applicant access, admissions messages, document previews, and finance visibility if deposits are included.

Can wait until after first pilot:

- Payment gateway and reconciliation automation.
- Full re-enrolment commitment workflow.
- Seat forecast scenario planning.
- Full family/household identity resolution.
- Multichannel campaign automation.
- Advanced AI document checks.
- Board-ready analytics packs.

Should be avoided for 90 days:

- Trying to make every ERP module demo-quality.
- Moving correctness-critical admissions state into the SPA.
- Creating one-off bypasses around Drive governance or accounting truth for demo speed.
- Adding compatibility shims or duplicate workflows to make a demo look smoother.

## Final recommendation

Ifitwala_Ed is currently closer to demo-ready than architecture-ready for the admissions wedge, but only for a narrow, honest demo. It is not yet pilot-ready for the full five-feature bundle because deposits, re-enrolment, and communications automation are structurally present but not admissions-workflow-ready.

The smallest credible demo flow within 2-4 weeks is:

`Public Inquiry` to `Assigned Inquiry` to `Contacted/Qualified` to `Student Applicant` to applicant checklist/documents/messages to staff readiness review to `Applicant Enrollment Plan` offer to family acceptance to `Program Enrollment Request` hydration.

The first repo-level milestone should be:

`Admissions Wedge MVP: one connected enquiry-to-enrolment pipeline surface backed by existing Inquiry, Student Applicant, Applicant Document, Org Communication, and AEP state.`

This milestone should not include full deposits, full re-enrolment, or broad ERP positioning. Those should follow only after the core leakage-prevention journey is obvious, reliable, and demo-tight.

# Ifitwala_Ed First-Traction Audit
## Enquiry-to-Enrolment Pipeline for Small International & Private Schools

**Date:** 2026-04-26
**Scope:** First 5 traction features vs. current production codebase
**Constraint:** Read-only audit. No edits. No invented schemas.

---

## Bottom Line

**Ifitwala_Ed is closer to demo-ready than architecture-ready for the admissions wedge—but with a critical caveat:** the enquiry-to-application and document-collection flows are impressively complete, while re-enrolment, deposits, and parent communication automation are still structural foundations without a cohesive admissions-specific workflow layer.

**The smallest credible demo flow:** A prospect submits an inquiry via public web form → an admissions officer assigns it in the kanban cockpit → invites the applicant → the family fills profile, uploads documents, and acknowledges policies in the branded portal → staff review and approve → an offer is sent and accepted. This flow is already end-to-end runnable.

**The biggest blocker to pilot:** There is no financial bridge between offer acceptance and enrollment confirmation. A school cannot take a deposit or fee payment within the admissions workflow today.

---

## Current Assets Found

### DocTypes (verified from `.json` schemas)
- **Inquiry** — `INQ-.YY.-.MM.-.DD.-.###` naming, workflow states (`New/Assigned/Contacted/Qualified/Archived`), SLA fields (`sla_status`, `first_contact_due_on`, `followup_due_on`), assignment lane (`Admission/Staff`), link to `Student Applicant`.
- **Student Applicant** — `APPL-.YYYY.-.MM.-.###` naming, status (`Draft/Invited/In Progress/Submitted/Under Review/Missing Info/Approved/Rejected/Withdrawn/Promoted`), immutable `inquiry` link, guardian child table, profile/health/interview/document HTML summary sections.
- **Applicant Document Type** — configurable requirements with classification slot, data class, purpose, retention policy, required/repeatable flags, scoped by org/school.
- **Applicant Document / Applicant Document Item** — per-applicant document instances with review status (`Pending/Approved/Rejected/Superseded`), governed file handling via Ifitwala Drive.
- **Applicant Enrollment Plan** — offer lifecycle (`Draft → Ready for Committee → Committee Approved → Offer Sent → Offer Accepted/Declined/Expired → Hydrated → Cancelled/Superseded`), course basket selection, auto-hydrates `Program Enrollment Request`.
- **Applicant Interview / Applicant Interview Feedback** — scheduling, conflict detection, per-interviewer feedback.
- **Applicant Health Profile** — full health intake with vaccination tracking and declaration workflow.
- **Recommendation Template / Recommendation Request / Recommendation Submission** — external recommender intake with OTP, token-secure URLs, immutable submissions.
- **Admission Settings** (Single) — SLA days, portal access mode (`Single Applicant Workspace` / `Family Workspace`), auto-hydrate enrollment request toggle.
- **Org Communication** — `Draft/Scheduled/Published/Archived`, audience targeting (`School Scope/Organization/Team/Student Group`), admission context (`Student Applicant` / `Inquiry`), portal surfaces (`Desk/Morning Brief/Portal Feed/Everywhere`), read receipts via `Portal Read Receipt`.
- **Program Offering** — `capacity`, `seat_policy` (`Committed Only/Approved Requests Hold Seats/Submitted Holds Seats`), `seat_hold_hours`, `allow_self_enroll`, course-level capacities and waitlists.
- **Program Enrollment Tool / Program Offering Selection Window** — batch rollover and portal-assisted course selection.
- **Sales Invoice / Payment Entry / Payment Terms Template / Billing Schedule / Billing Run / Payment Request / Dunning Notice / Account Holder** — full double-entry finance stack.

### APIs (verified from `.py` files)
- `api/inquiry.py` — `get_dashboard_data()` with volume, SLA, response-time, source, and lane metrics.
- `api/admission_cockpit.py` — Kanban columns, blocker detection, KPI row, applicant workspace targets.
- `api/admissions_portal.py` — ~3,900 lines covering session bootstrap, profile, health, documents, policies, messages, course choices, offer accept/decline, submit.
- `api/admissions_communication.py` — Threaded case messaging with read receipts.
- `api/admissions_review.py` — Document approval/rejection and requirement overrides.
- `api/recommendation_intake.py` — External recommender full lifecycle.
- `api/guardian_finance.py` — Family-wide invoice and payment snapshot.
- `schedule/enrollment_engine.py` — Deterministic capacity evaluation.

### SPA (verified from `.vue` and `.ts` files)
- **Applicant portal** — 9 routes: `/overview`, `/profile`, `/health`, `/documents`, `/policies`, `/messages`, `/course-choices`, `/submit`, `/status`.
- **Staff Admissions Cockpit** — `AdmissionsCockpit.vue` with kanban, blocker filters, KPIs.
- **Inquiry Analytics** — `InquiryAnalytics.vue` with funnel and response-time charts.
- **Guardian portal** — `GuardianFinance.vue`, `GuardianHome.vue` with family-wide aggregates.

### Web Forms
- **Anonymous inquiry web form** at `/apply/inquiry` (`admission/web_form/inquiry/inquiry.json`), published, anonymous, creates `Inquiry` in `New` state.

### Scheduled Jobs
- Hourly SLA sweep (`admission/scheduled_jobs.py` → `check_sla_breaches`).

### Notifications
- `notify_admission_manager` — Frappe Notification on new `Inquiry`.
- `inquiry_assigned` — Frappe Notification on assignment change.

---

## Feature 1: Enquiry-to-Enrolment Pipeline

### Readiness: Demo-ready

The pipeline is the strongest part of the wedge. It has ownership, SLA visibility, stage tracking, a staff kanban cockpit, and analytics.

### Existing Assets
- **Inquiry capture:** Anonymous web form at `/apply/inquiry` with `first_name`, `last_name`, `email`, `phone_number`, `type_of_inquiry`, `organization`, `message`.
- **Ownership:** `assigned_to` (Link to `User`), `assignment_lane` (`Admission` / `Staff`), native `ToDo` creation on assignment.
- **Status tracking:** `workflow_state` (`New → Assigned → Contacted → Qualified → Archived`) with server-enforced transitions (`inquiry.py` lines 97–114).
- **SLA visibility:** `sla_status` (🔴 Overdue / 🟡 Due Today / ⚪ Upcoming / ✅ On Track), `first_contact_due_on`, `followup_due_on`, response-hour metrics stamped on contact.
- **Next action / deadlines:** SLA fields + ToDo integration. Closing a ToDo auto-marks inquiry `Contacted` via `hooks.py` doc_event.
- **Assignment/reassignment:** `add_assignment`/`remove_assignment` with comment timeline.
- **List/Kanban/Dashboard:** Admissions Cockpit SPA (`AdmissionsCockpit.vue`) with 6 kanban columns, blocker badges, KPI row. Inquiry Analytics API with funnel, source, and response-time charts.
- **Data handoff to application:** `Inquiry.invite_to_apply()` creates `Student Applicant` in `Invited` state, linked back via `inquiry` field.

### Demo Gaps
1. **No free-text "Next Action" field on Inquiry.** Staff can see SLA status but cannot record a specific planned action (e.g., "Call back after holiday"). The `message` field is the original inquiry message, not a working notes field.
2. **No inquiry source attribution beyond the basic web form.** No `source` field (e.g., "Open Day", "Referral", "Google Ads") on the `Inquiry` schema, so source-quality analytics are impossible without a schema change.
3. **No bulk actions in the cockpit.** Staff must open each applicant to move status or send messages.

### Pilot Gaps
1. **No automated inquiry distribution/round-robin assignment.** Schools with multiple officers must manually assign every inquiry.
2. **No duplicate detection on submission.** The web form does not warn families if their email already has an active inquiry.
3. **No family-level pipeline view.** A returning family inquiring for a second child appears as a completely unrelated inquiry unless staff manually recognize the email.

### Risks
- **UX risk:** The inquiry web form exposes `organization` as a Link field to anonymous users. For single schools this is confusing; for multi-campus orgs it leaks organization names.
- **Data integrity risk:** `assigned_to` is `read_only=1` in the schema but mutated via controller methods. Desk users cannot reassign via standard form edit, which is correct for workflow control but may confuse power users.
- **Technical risk:** `Inquiry` lacks `search_index` on `email` and `phone_number`, so duplicate lookups and family matching will be slow at scale.

### Highest-Impact Next Actions
1. **Add a `source` Select field to `Inquiry`** with options like `Website, Open Day, Referral, Agent, Other` — enables source-quality reporting for the pilot.
2. **Add a `next_action_note` Small Text field to `Inquiry`** — gives staff a lightweight working notes space without over-engineering.
3. **Hide `organization` from the anonymous web form** or pre-populate it via route param — removes friction for single-school prospects.

---

## Feature 2: Online Application, Checklist and Document Collection

### Readiness: Demo-ready

This is the most complete feature in the wedge. The applicant portal SPA, document governance, and review workflow are production-grade.

### Existing Assets
- **Applicant portal SPA:** 9 Vue pages under `/admissions` with `createWebHistory('/admissions')`. Profile, health, documents, policies, messages, course choices, submit, status.
- **Document checklist:** `Applicant Document Type` master data with `is_required`, `is_repeatable`, `min_items_required`, scoped by org/school. `build_document_review_payload_batch()` computes per-applicant readiness (missing, unapproved, approved counts).
- **Governed uploads:** All uploads route through Ifitwala Drive with classification slots. No raw private paths exposed. `Applicant Document Item` tracks per-file review state.
- **Review status:** Staff can approve/reject/needs-follow-up per document item. Requirement overrides (Waive/Exception Approved) supported.
- **Parent-facing clarity:** Portal shows document requirements with descriptions, upload slots, and review status. Family Workspace mode lets guardians manage multiple applicants.
- **Health intake:** `Applicant Health Profile` with 20+ condition fields, vaccination table, declaration workflow.
- **Policy acknowledgements:** `Policy Acknowledgement` with version tracking and electronic signature.
- **Data handoff from Inquiry:** `invite_to_apply()` auto-creates `Student Applicant` with `first_name`, `last_name`, `inquiry` link, `organization`, `school`. Contact auto-created/matched by email/phone.

### Demo Gaps
1. **No "application completeness percentage" surfaced simply to families.** The portal shows sections but does not present a single "75% complete — 2 documents remaining" progress indicator.
2. **No document auto-approval for low-risk uploads.** Every document requires manual staff review, which is correct for governance but creates a staffing bottleneck for small schools.
3. **Applicant portal may be overwhelming.** 9 sections plus health, policies, and recommendations is a lot for a small school's single-page application.

### Pilot Gaps
1. **No document expiry or renewal alerts.** Passport/visa/health documents uploaded in admissions have no expiry tracking or pre-enrolment renewal nudges.
2. **No sibling document reuse.** A family applying a second child must re-upload the same passport/birth certificate even if it was already approved for the first child.
3. **No conditional checklist logic.** All applicants see the same document requirements regardless of program, nationality, or transfer status.

### Risks
- **UX risk:** The document review turnaround time is entirely manual. If a small school has only one admissions officer on holiday, document approvals stall.
- **Data integrity risk:** `Student Applicant` has `EDIT_RULES` in the controller (family can edit in `Invited/In Progress/Missing Info` only). This is server-enforced, which is correct, but the SPA must mirror these rules precisely or families will hit server errors.
- **Security risk:** `applicant_image` is an `Attach Image` field on `Student Applicant`. The portal uses governed Drive routes for most files, but the profile image path must be verified against the preview contract.

### Highest-Impact Next Actions
1. **Add a simple progress bar/completeness score to the applicant portal overview page** — highest visual payoff for demo credibility.
2. **Add `expiry_date` to `Applicant Document Item`** and a pre-enrolment sweep job — prevents last-minute document crises in pilot.
3. **Enable auto-approve for certain document types** (e.g., `photo`) via a config flag on `Applicant Document Type` — reduces staff workload for small schools.

---

## Feature 3: Re-Enrolment and Seat Planning

### Readiness: Structurally present but not workflow-ready

The enrollment engine and rollover tooling exist, but there is **no dedicated returning-family workflow**. Re-enrolment is treated as generic batch enrollment, not as a distinct admissions-season experience.

### Existing Assets
- **Year rollover architecture:** `Program Enrollment Tool` with `prepare_requests → validate_requests → approve_requests → materialize_requests`. Batch mode auto-queues on `long` queue if >100 students.
- **Portal-assisted rollover:** `Program Offering Selection Window` lets students/guardians choose courses during a time window, then staff approves.
- **Capacity engine:** `schedule/enrollment_engine.py` evaluates 4 seat-hold policies (`committed_only`, `approved_requests`, `approved_plus_review`, `submitted_holds`). Course-level capacities, waitlists, reserved seats.
- **Enrollment gap reports:** `schedule/report/enrollment_gaps_report/` identifies students missing enrollment or group placement.
- **End of Year Checklist:** Archives outgoing academic year, terms, program enrollments, and retires student groups.
- **Waitlist support:** Both academic courses and ECA activities have waitlist mechanics with auto-promotion.

### Demo Gaps
1. **No "Re-Enrolment" workflow in the admissions cockpit.** The cockpit only shows new applicants (`Student Applicant`). Returning students do not appear in the admissions pipeline.
2. **No returning-family intent capture.** There is no `Intent to Return` or `Re-Enrolment Request` DocType. Families cannot confirm they are returning with a single click.
3. **No seat planning dashboard for leadership.** Capacity is evaluated per `Program Offering` but there is no consolidated "confirmed seats vs. capacity vs. returning intent" view for heads.

### Pilot Gaps
1. **No financial interlock with re-enrolment.** A family cannot be asked to pay a re-enrolment deposit as part of confirming their seat.
2. **No rollover of admissions data.** Consents, policy acknowledgements, and health profiles from the prior year are not pre-carried forward; families start from scratch.
3. **No sibling-clustered seat planning.** If Child A is returning and Child B is a new applicant, there is no family-level seat reservation logic.

### Risks
- **UX risk:** The `Program Enrollment Tool` is a batch Desk tool, not a family-friendly workflow. It is powerful for staff but invisible to parents.
- **Data integrity risk:** The `End of Year Checklist` archives prior-year `Program Enrollment` records. If a school runs the checklist before re-enrolment season completes, returning-student enrollment history is archived prematurely.
- **Technical risk:** `Program Offering Selection Window` requires `allow_self_enroll = 1` on the offering. If staff forget to enable this, portal-assisted rollover is blocked with no clear error message for families.

### Highest-Impact Next Actions
1. **Add a `Re-Enrolment Intent` child table or DocType** linked to `Student` + `Program Offering` + `Academic Year` with status `Pending/Confirmed/Declined/Waitlisted` — creates a visible returning-family pipeline.
2. **Build a "Seat Planning" staff page** aggregating `Program Offering` capacity, current enrollments, re-enrolment intents, and new applicant accepted offers — gives leadership the live picture they need.
3. **Pre-populate returning-student application data** from prior-year `Student` / `Student Patient` / `Policy Acknowledgement` records — reduces family friction and staff data entry.

---

## Feature 4: Deposits, Invoicing and Payment Plans

### Readiness: Structurally present but not workflow-ready for admissions

The accounting module is a solid double-entry GL, but it is **completely disconnected from the admissions workflow**. There is no deposit DocType, no offer-to-invoice trigger, and no payment gateway.

### Existing Assets
- **Invoice generation:** `Sales Invoice` with `Account Holder`, `Program Offering`, `payment_terms_template`, `payment_schedule` child table, status workflow (`Draft/Unpaid/Partly Paid/Paid/Overdue/Cancelled`).
- **Payment tracking:** `Payment Entry` (Receive only) posts to Bank/Cash → AR. `Payment Reconciliation` for advance allocation.
- **Billing automation:** `Program Billing Plan` → `Billing Schedule` → `Billing Run` generates draft invoices from enrollments.
- **Payment plans:** `Payment Terms Template` with installment percentages and due days. Auto-expands into `Sales Invoice Payment Schedule` rows with per-term tracking.
- **Collections tracking:** `Payment Request` (manual outreach tracker) and `Dunning Notice` (overdue invoice loader).
- **Guardian visibility:** `GuardianFinance.vue` shows family invoices, payments, outstanding totals.
- **Analytic dimensions:** GL entries tagged by `school`, `program`, `program_offering`, `student`.

### Demo Gaps
1. **No deposit invoice can be generated from an accepted offer.** `Applicant Enrollment Plan` has no link to `Sales Invoice`, `Payment Request`, or `Account Holder`. Staff must manually create an invoice in the accounting module.
2. **No `Billable Offering` type for deposits.** `Billable Offering.offering_type` options are `Program/Service Subscription/One-off Fee/Product`. A deposit is not explicitly modeled.
3. **No payment status in the admissions cockpit.** The cockpit shows application blockers (documents, health, policies) but not whether the deposit or fees have been paid.

### Pilot Gaps
1. **No payment gateway integration.** `Payment Request` is a manual tracker (`mark_sent()` records when it was presumably emailed). Families cannot pay online.
2. **No admissions-deposit workflow.** A typical admissions flow requires: offer accepted → deposit invoice issued → deposit paid → seat confirmed → enrollment materialized. Today, steps 2 and 3 are entirely manual and disconnected.
3. **No conditional enrollment gating by payment.** `Program Enrollment Request` materialization does not check invoice payment status.

### Risks
- **Data integrity risk:** `Student Applicant` has no `account_holder` field. When promoting to `Student`, the business manager must manually ensure the `Account Holder` is linked before invoicing.
- **UX risk:** Admissions staff and business managers work in separate modules with no shared workflow. An offer accepted in admissions does not surface in accounting unless someone manually creates the invoice.
- **Security risk:** `Payment Request` stores `contact_email` and `contact_phone`. Without automated dispatch, these are manually entered and prone to errors.

### Highest-Impact Next Actions
1. **Add `account_holder` to `Student Applicant`** and auto-create/link `Account Holder` on promotion (or earlier) — enables invoice generation against the applicant before promotion.
2. **Add a `deposit_required` Check and `deposit_amount` Currency to `Applicant Enrollment Plan`** — allows staff to configure deposit terms per offer.
3. **Create a whitelisted API `generate_deposit_invoice_from_offer()`** that creates a `Sales Invoice` from an accepted `Applicant Enrollment Plan` using a configurable deposit `Billable Offering` — closes the admissions-finance gap for the pilot.

---

## Feature 5: Parent Communications Automation

### Readiness: Partially usable

Communication exists but is **broadcast-oriented, not journey-orchestrated**. There are no stage-based sequences, no behavioral triggers, and no multi-channel unification.

### Existing Assets
- **Org Communication:** Custom DocType with `Draft/Scheduled/Published/Archived`, audience targeting by `School Scope/Organization/Team/Student Group`, recipient toggles (`to_staff/to_students/to_guardians`), portal surfaces, read receipts.
- **Admissions case messaging:** Threaded messages bound to `Student Applicant` via `admissions_communication.py`. Staff and applicants can exchange messages. Read receipts supported.
- **SLA alerts:** Hourly scheduled job recomputes inquiry SLA statuses. Realtime `inbox_notification` emitted on breach.
- **Notification templates:** 2 Frappe Notifications (`notify_admission_manager` on new inquiry, `inquiry_assigned` on assignment change).
- **Portal read receipts:** `Portal Read Receipt` tracks which users have seen `Org Communication` entries.
- **Realtime updates:** `frappe.publish_realtime` used for bell notifications, focus-list invalidation.

### Demo Gaps
1. **No stage-based communication sequences.** A family in `In Progress` does not receive an automatic "Don't forget to upload your passport" reminder after 7 days.
2. **No automated offer/deposit reminders.** When `Applicant Enrollment Plan` moves to `Offer Sent`, no automatic message is dispatched.
3. **No re-enrolment reminder automation.** There is no trigger for "Re-enrolment opens in 2 weeks" or "Your seat is not yet confirmed."

### Pilot Gaps
1. **No missing-document reminder automation.** Document review readiness is computed (`build_document_review_payload_batch`) but not wired to automated message dispatch.
2. **No SMS or multi-channel messaging.** Only Frappe email + in-app notifications exist. No Twilio, WhatsApp, or SMS integration.
3. **No communication template library for admissions.** Staff must compose every message manually. There is no "Offer Letter Template" or "Deposit Reminder Template."
4. **No communication effectiveness tracking.** Open rates and read receipts exist, but there is no tracking of whether a message led to the desired action (document uploaded, offer accepted, deposit paid).

### Risks
- **UX risk:** Families experience silence between staff interactions. If an admissions officer is busy, a prospect may wait days without any automated nudge.
- **Data integrity risk:** `Org Communication` `admission_context_doctype` supports `Student Applicant` and `Inquiry`, but there is no enforcement that messages are actually sent in the right context. Staff can send a message bound to an inquiry after the applicant has already been promoted.
- **Technical risk:** `frappe.sendmail` is called directly in scattered places (`admissions_portal.py` for invite, `recommendation_intake.py` for recommender request, `leave_application.py` for follow-up). There is no centralized email service or queue for admissions communications.

### Highest-Impact Next Actions
1. **Build an `Admissions Communication Template` DocType** with placeholders for applicant name, school, program, due dates, and deposit amount — gives staff one-click professional messages.
2. **Add scheduled jobs for automated stage-based nudges:** missing documents at 7 days, offer expiry at 3 days before deadline, re-enrolment open announcement — highest perceived automation value for families.
3. **Wire `Applicant Enrollment Plan` status changes to `Org Communication` auto-dispatch** (e.g., `Offer Sent` → auto-send offer letter email to applicant + guardian) — closes the offer-to-communication gap.

---

## Cross-Feature Architecture Observations

### Fragmentation Between Admissions and Finance
The most critical architectural gap is the **absence of any financial linkage in the admission module**. `Student Applicant`, `Applicant Enrollment Plan`, and the admissions cockpit have no references to `Sales Invoice`, `Payment Request`, `Account Holder`, or `Billable Offering`. For the wedge to be credible, offer acceptance must be able to trigger deposit collection. This requires either:
- Adding financial fields/links to admission DocTypes, or
- Building a bridge API that creates invoices from admission events.

The first approach is cleaner but touches schema. The second is faster for a pilot.

### Overlapping but Unconnected Enrollment Paths
There are three enrollment-related tools that a small school will find confusing:
1. `Program Enrollment Tool` — staff batch rollover
2. `Program Offering Selection Window` — portal-assisted course selection
3. `Applicant Enrollment Plan` — new applicant offer management

These share `Program Enrollment Request` as a target but have different UIs, different permissions, and no unified dashboard showing "all seats for next year: new + returning."

### Strong Governance, High Friction
The document classification system (slots, data classes, retention policies, Drive routing) is enterprise-grade. For a small school with 50 applicants/year, this may be overkill. The trade-off between governance and speed should be surfaced as a configuration option, not hardcoded.

### Hidden Multi-Tenancy Complexity in the Wedge
The anonymous inquiry web form exposes `organization` as a Link field. For a single-school pilot, this is unnecessary friction. For a multi-campus group, it is essential. The wedge should support both modes cleanly.

---

## Hidden Strengths to Surface Publicly

1. **SLA-aware inquiry pipeline with real-time breach alerts.** Most admissions CRMs track status; few track response-time SLAs with automated escalation.
2. **Governed document collection via Ifitwala Drive.** Classification slots, retention policies, and per-item review are genuinely differentiated for schools with compliance obligations (e.g., safeguarding, GDPR).
3. **Family Workspace portal mode.** Guardians can manage multiple children from one login. Most applicant portals are single-applicant only.
4. **Capacity engine with waitlist support.** Not just seat counts — deterministic evaluation with multiple hold policies and auto-promotion.
5. **Immutability and audit trail.** Status transitions are server-enforced with comment timelines. Offer acceptance/decline is timestamped and user-stamped. This builds trust with accreditors and auditors.

---

## Dangerous Distractions to Avoid

1. **Do not build a generic CRM.** The pipeline is admissions-specific. Resist adding sales-pipeline features (lead scoring, marketing campaigns, deal value) before the wedge is stable.
2. **Do not build a payment gateway yet.** The accounting stack can generate invoices and track payments manually. A Stripe/M-Pesa integration is high effort and low differentiation for the first pilot. Focus on "invoice from offer" first, "pay online" second.
3. **Do not rebuild the full ERP as part of the wedge.** Curriculum, assessment, attendance, and HR are impressive but irrelevant to an admissions officer evaluating the product. Lead with the pipeline, then upsell.
4. **Do not add AI document extraction yet.** The document system is already strong. OCR/auto-fill is a nice-to-have that diverts engineering from the finance bridge and communication automation gaps.
5. **Do not over-engineer re-enrolment.** The `Program Enrollment Tool` already handles batch rollover. The gap is intent capture and family experience, not a new enrollment engine.

---

## Smallest Credible School Demo Flow

**Target duration:** 8–10 minutes
**Target audience:** Admissions officer + Headteacher at a small international school

1. **Prospect submits inquiry** — Show the anonymous web form at `/apply/inquiry`. Fill it. Submit. Show the real-time notification to the admissions manager.
2. **Staff sees inquiry in cockpit** — Open the Admissions Cockpit. Show the inquiry card in `New`. Assign it. SLA clock starts.
3. **Staff invites to apply** — Click `invite_to_apply`. A `Student Applicant` is created. Portal credentials are sent.
4. **Family fills application** — Switch to guardian/applicant portal. Fill profile. Upload a document. Acknowledge a policy. Show the progress indicator.
5. **Staff reviews and approves** — Back to cockpit. Review document. Approve. Move applicant to `Approved`.
6. **Offer and acceptance** — Create `Applicant Enrollment Plan`. Send offer. Switch to portal. Accept offer.
7. **Promotion to student** — Promote applicant. Show `Student` record created, health profile copied, guardians linked.

**What to skip in the demo:** Re-enrolment, deposits/invoicing, communication templates, analytics beyond the cockpit KPIs. These are present structurally but not yet polished enough to show without caveats.

---

## 2–4 Week Roadmap

### Week 1: Demo Polish
- [ ] **Fix inquiry web form UX:** Hide or auto-populate `organization` for single-school mode. Add `source` field.
- [ ] **Add applicant portal progress indicator:** Compute checklist completeness percentage and display on `ApplicantOverview.vue`.
- [ ] **Add `next_action_note` to Inquiry:** Small Text field, editable by assignee, shown in cockpit card.

### Week 2: Admissions-Finance Bridge (MVP)
- [ ] **Add `account_holder` to `Student Applicant`** and auto-create/link on promotion or earlier.
- [ ] **Create a `Deposit` Billable Offering** or use `One-off Fee` with a deposit naming convention.
- [ ] **Build `generate_deposit_invoice_from_offer()` API** — whitelisted, creates `Sales Invoice` from accepted `Applicant Enrollment Plan`.
- [ ] **Show payment status as a cockpit blocker** — query `Sales Invoice` outstanding amount for linked applicant.

### Week 3: Communication Automation (MVP)
- [ ] **Build `Admissions Communication Template` DocType** with Jinja-friendly fields.
- [ ] **Auto-dispatch on offer sent** — hook `Applicant Enrollment Plan` status change to create/send `Org Communication`.
- [ ] **Add missing-document scheduled reminder** — daily job: find applicants with unapproved required documents > N days, send template message.

### Week 4: Re-Enrolment Intent (MVP)
- [ ] **Add `Re-Enrolment Intent` child table on `Student`** or lightweight DocType — status `Pending/Confirmed/Declined`.
- [ ] **Build staff "Seat Planning" page** — aggregate capacity, current enrollment, confirmed re-enrolments, new accepted offers per `Program Offering`.
- [ ] **Pre-fill returning family data** — copy prior-year `Student Patient`, `Policy Acknowledgement`, and `Address` into the new application context.

---

## 90-Day Pilot-Readiness Roadmap

### Must Fix Before Public Demo (Weeks 1–2)
- Inquiry form UX + source field + next-action note
- Applicant portal progress indicator
- Cockpit payment-status blocker (requires finance bridge)

### Must Fix Before Pilot (Weeks 3–6)
- Deposit invoice generation from accepted offer
- Admissions communication templates + auto-dispatch on offer/deposit/reminder
- Re-enrolment intent capture + seat planning dashboard
- Document expiry alerts
- Duplicate inquiry detection

### Can Wait Until After First Pilot (Weeks 7–12)
- Payment gateway integration (Stripe/M-Pesa)
- SMS/WhatsApp messaging channel
- Automated document approval for low-risk types
- Sibling document inheritance
- Source-quality analytics dashboard
- Bulk actions in admissions cockpit

### Should Be Explicitly Avoided for Now
- AI document extraction/OCR
- Predictive lead scoring
- Marketing campaign management
- Full ERP feature rollout (assessment, attendance, HR)
- Mobile native apps

---

## Final Recommendation

### Is it closer to demo-ready or architecture-ready?
**Demo-ready for Features 1 and 2. Architecture-ready for Features 3, 4, and 5.**

The enquiry-to-application flow is genuinely impressive and can be shown to schools today with only minor UX polish. The document governance, family workspace, and staff cockpit are competitive differentiators.

However, **a school cannot run a complete admissions season on this platform today** because:
1. Re-enrolment is generic enrollment machinery, not a returning-family workflow.
2. There is no financial bridge between offer acceptance and seat confirmation.
3. Communication is manual and ad-hoc, not automated around the family journey.

### What is the smallest credible demo flow?
The 7-step flow described above (inquiry → cockpit → invite → portal → review → offer → promotion). It takes 8–10 minutes and shows the core value proposition: "We stop enquiry leakage by giving every prospect an owner, a deadline, and a visible next step."

### What should be the first repo-level milestone?
**Milestone: "Offer-to-Invoice"**

Define the milestone as: *"A school can accept an applicant's offer and generate a deposit invoice without leaving the admissions workflow."*

This milestone forces the admissions and finance modules to connect for the first time. It unblocks the pilot because schools need to collect money. And it validates the architecture: if the bridge is clean, the rest of the wedge (re-enrolment, payment plans, communication automation) can build on it.

**Success criteria:**
- `Student Applicant` links to `Account Holder`.
- `Applicant Enrollment Plan` (status `Offer Accepted`) can trigger creation of a `Sales Invoice` via a whitelisted API.
- The admissions cockpit shows payment status as a blocker.
- The guardian portal shows the outstanding invoice.

Once this milestone is hit, the product moves from "impressive demo" to "usable pilot."

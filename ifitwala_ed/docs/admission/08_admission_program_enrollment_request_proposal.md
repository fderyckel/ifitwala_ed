# Admission to Program Enrollment Request Proposal

This is a proposal document.

It does not change the current runtime contract.

Current implemented behavior remains:

- `Student Applicant` is the pre-student admissions record of truth.
- `Program Enrollment Request` currently requires a linked `Student` and at least one request-course row.
- `StudentApplicant.promote_to_student()` does not currently create a `Program Enrollment Request` or `Program Enrollment`.
- `StudentApplicant.upgrade_identity()` already requires an active `Program Enrollment`.

The proposal below is therefore written in two layers:

1. a recommended path that fits the current contract with minimal drift
2. an optional deeper path that would require later approval because it changes the enrollment boundary

## 1. Recommendation

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.json`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/api/admission_cockpit.py`
Test refs: None (proposal only)

Recommendation:

- Chosen direction: `Option A`.
- Make enrollment intent an explicit admissions concern on `Student Applicant`.
- Separate internal committee decision from the family-facing offer outcome.
- Keep `Student Applicant` as the only pre-student truth for intended `academic_year`, `program`, and `program_offering`.
- After committee approval, issue an offer to the family that includes placement and, when configured, required enrollment choices.
- Generate or prepare the `Program Enrollment Request` from accepted offer data after `Student` creation, under a policy set in `Admission Settings`.
- Keep `Program Enrollment Request` as the only transactional staging object before committed `Program Enrollment`.

Recommended canonical flow:

`Inquiry -> Student Applicant -> Approved -> Offer Sent -> Offer Accepted -> Student -> Program Enrollment Request -> Program Enrollment -> Identity Upgrade`

Why this is the recommended path:

- it reuses fields already present on `Student Applicant`
- it matches the real-world distinction between an internal decision and a family acceptance event
- it respects the current `Program Enrollment Request` contract instead of forcing hidden exceptions
- it keeps admissions intent separate from committed enrollment truth
- it closes the current operational gap between promotion and identity upgrade

## 2. Current-State Contract and Gap

Status: Implemented
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.json`, `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`, `ifitwala_ed/docs/docs_md/student-applicant.md`, `ifitwala_ed/docs/docs_md/program-enrollment-request.md`, `ifitwala_ed/docs/docs_md/program-enrollment.md`
Test refs: `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`

What already exists:

- `Student Applicant` already stores `organization`, `school`, `academic_year`, `term`, `program`, and `program_offering`.
- applicant academic-year intent is already validated against admissions-visible academic years and school scope
- applicant approval and promotion are already server-owned lifecycle actions
- `Program Enrollment Request` already stages validation snapshots, override gates, and materialization into `Program Enrollment`

What is missing today:

- applicant intent is not operationalized into enrollment work
- admissions can approve and promote an applicant, but the system does not carry that decision forward into a request-generation workflow
- identity upgrade already depends on active enrollment, so operations still have a manual gap between promotion and portal-ready activation

Hard constraint in the current contract:

- `Program Enrollment Request` cannot be created before `Student` exists because it currently requires `student`
- `Program Enrollment Request` also requires `courses`, so the system needs an approved default basket or an academic-team review step before request approval/materialization

That means "make PER part of admissions" should not mean "force a pre-student PER immediately" unless the team explicitly approves a schema change later.

## 3. Proposed Product Model

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`, `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs: None (proposal only)

### 3.1 Applicant owns intent, enrollment request owns transaction

Proposed boundary:

- `Student Applicant` owns pre-student enrollment intent
- `Student Applicant` also owns the offer lifecycle before a student exists
- `Program Enrollment Request` owns post-student validation, override, and approval transaction
- `Program Enrollment` remains committed truth only after request materialization

This is the same pattern used by strong admission/SIS products:

- capture family input once
- reuse it downstream
- do not convert family intent directly into committed enrollment without reviewable workflow

### 3.2 Committee decision is not yet enrollment

The product should distinguish four different moments:

1. committee approves the applicant internally
2. institution sends an offer
3. family accepts or declines the offer
4. accepted student moves into enrollment transaction

Recommended behavior:

- committee approval is staff-only and internal
- family receives an explicit offer package
- family acceptance is recorded separately from the committee decision
- enrollment choices can be part of the acceptance package when the institution requires them

Recommended workflow wording:

- `Approved`
- `Offer Sent`
- `Offer Accepted`
- `Offer Declined`
- `Offer Expired`

Avoid:

- `Admission Offered`

Reason:

- `Approved` can remain the internal committee decision
- `Offer Sent` is clearer, shorter, and distinguishes the family-facing event from the internal admissions decision

Supporting offer outcomes:

- `Offer Sent`
- `Offer Accepted`
- `Offer Declined`
- `Offer Expired`

Optional contingent mode:

- `Offer Pending Enrollment Choices`

In that mode, the institution is effectively saying:

- admission committee has approved the candidate
- the final offer acceptance is contingent on the family confirming the offered program/offering and any required enrollment selections

This is the cleanest way to model the user requirement without pretending that committee approval already produced a finished enrollment transaction.

### 3.3 Timing policy in Admission Settings

Add one admissions-owned policy control in `Admission Settings` for when enrollment request generation happens.

Proposed product choices:

- `After offer acceptance, auto-create draft request once student is created`
- `After offer acceptance and required choices, auto-create draft request once student is created`
- `After student creation, auto-create draft request`
- `After student creation, create request only when staff clicks a guided action`
- `Do not create request automatically; admissions hub tracks "ready for request"`

Recommended default:

- `After offer acceptance, auto-create draft request once student is created`

Why this default is strongest:

- it fits the current PER contract
- it places the real family commitment event before enrollment staging
- it removes the post-promotion dead-end
- it gives Academic Admin and Curriculum Coordinator a real object to review instead of a comment or checklist note

### 3.4 Offer package and request seeding rules

The offer package should include:

- offered `academic_year`
- offered `program`
- offered `program_offering`
- any required response deadline
- any required enrollment choices
- any optional deposit / fee / agreement requirement

Enrollment-choice modes should be configurable:

- `No family choices required`
- `Family confirms offered placement only`
- `Family selects among allowed offerings`
- `Family confirms placement and selects required course preferences`

When request generation is triggered:

- copy applicant `program_offering`
- copy applicant `academic_year`
- derive `program` and `school` from the offering as the current request contract already does
- seed the request basket from required offering courses only
- leave elective completion and override handling to academic review

This keeps the first generated request safe and deterministic:

- required courses are seeded automatically
- elective choice remains a guided review step when needed
- the request still goes through existing validation snapshot logic

### 3.5 Self-enrollment policy

Self-enrollment should be optional and narrowly scoped.

Recommended rule:

- applicants/families may be allowed to choose among published offerings only when the school explicitly enables that mode
- family choice must still create or update an enrollment request, never committed enrollment
- family choice must be constrained by applicant school scope and admissions-visible academic year
- course-level self-selection should remain optional and should only be allowed where the offering is designed for it

If self-enrollment is enabled, correctness still stays server-side:

- family cannot create `Program Enrollment` directly
- family cannot bypass validation snapshots
- family cannot approve overrides

## 4. Applicant Experience Proposal

Status: Planned
Code refs: `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue`, `ifitwala_ed/ui-spa/src/types/contracts/admissions/types.ts`, `ifitwala_ed/api/admissions_portal.py`
Test refs: None (proposal only)

### 4.1 Applicant form behavior

The current applicant form already has the correct anchors:

- `academic_year`
- `program`
- `program_offering`

Proposal:

- show these fields as the "Enrollment Intent" section of the application, not as disconnected metadata
- make it explicit to the family whether this section is:
  - staff-assigned
  - applicant-confirmed
  - applicant-selectable
- if an offer has been sent, show whether the family is:
  - reviewing the offer
  - accepting with no further choices
  - accepting contingent on enrollment choices

Recommended UX modes:

- `Staff-assigned mode`: applicant sees read-only intended offering/year with guidance text
- `Applicant-confirm mode`: applicant confirms the intended offering/year but cannot pick outside published options
- `Applicant-select mode`: applicant chooses from server-provided offerings that are valid for the applicant's school and academic year
- `Offer-response mode`: family accepts or declines the offer and completes any required enrollment selections in the same guided step

### 4.2 No duplicate data entry

If offering/year are collected in admissions, they must be reused.

The product rule should be:

- applicant enters or confirms program intent once
- staff should not retype the same values during promotion
- accepted offer data should carry forward without re-entry
- generated request should inherit that intent automatically

### 4.3 Course choice handling

Not every school needs applicants to choose courses during admissions.

Recommended split:

- for fixed-program intake, seed required offering courses automatically
- for choice-driven programs, show "course selection pending academic review" rather than forcing the family into a premature course basket
- if the school wants choices at offer stage, collect them as part of the offer response and feed them into later request seeding or advisor review

This keeps admissions smooth while still supporting advanced programs later.

## 5. Admission Hub Proposal

Status: Planned
Code refs: `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`, `ifitwala_ed/ui-spa/src/types/contracts/admissions/admissions_workspace.ts`
Test refs: None (proposal only)

`/staff/admission-cockpit` should become the operational bridge between application review and enrollment readiness, not only an applicant-readiness board.

### 5.1 What should be shown

Each applicant card should keep current admissions readiness and add an enrollment strip with:

- intended `academic_year`
- intended `program_offering`
- offer state
- enrollment timing policy
- enrollment request state
- next owner
- next best action

Suggested new blocker chips:

- Missing Academic Year
- Missing Program Offering
- Offer Not Sent
- Offer Awaiting Family Response
- Offer Accepted But Choices Missing
- Student Not Yet Created
- Enrollment Request Not Generated
- Request Basket Incomplete
- Validation Failed
- Override Required
- Ready to Materialize
- Identity Upgrade Blocked by Missing Enrollment

Suggested new quick actions:

- Confirm Placement
- Send Offer
- Record Offer Acceptance
- Generate Request
- Open Request
- Review Basket
- Materialize Enrollment
- Upgrade Identity

### 5.2 Recommended board model

Keep the board applicant-centered, but add enrollment-aware progression.

Recommended top-level stages:

- `Applied / In Progress`
- `Submitted / Under Review`
- `Decision Ready`
- `Approved Awaiting Offer`
- `Offer Sent Awaiting Family`
- `Offer Accepted Awaiting Student`
- `Student Created Awaiting Request`
- `Request Under Review`
- `Ready to Materialize`
- `Enrolled Awaiting Identity Upgrade`

This is better than splitting admissions and enrollment into separate silos because the team can still see one lifecycle.

### 5.3 KPI row

Recommended admissions-hub KPIs:

- Applicants missing placement intent
- Approved applicants awaiting offer
- Offers awaiting family response
- Accepted offers awaiting student creation
- Students awaiting request generation
- Requests invalid or override-required
- Requests ready to materialize
- Promoted applicants blocked from identity upgrade by missing enrollment

### 5.4 Inbox and follow-through

The hub should highlight status changes and direct actions, not static warnings.

Every blocker row should continue the existing actionability pattern:

- target doctype
- target record
- target URL
- target label

This follows the repo's existing blocker contract and prevents dead-end warnings.

## 6. Operating Model by Role

Status: Planned
Code refs: `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/docs/docs_md/program-enrollment-request.md`, `ifitwala_ed/docs/docs_md/program-offering.md`
Test refs: None (proposal only)

### Admissions Team

Owns:

- applicant completeness
- family communication
- collecting or confirming enrollment intent
- preparing and sending offers
- moving accepted applicants to the "ready for student creation" point

Should not own:

- curriculum-rule overrides
- seat-policy exceptions
- final request validation decisions where academic constraints apply

### Academic Admin

Owns:

- final release of an offer when admissions workflow requires academic confirmation
- final placement confirmation
- deciding when student creation should trigger request generation under school policy
- approving ready requests for materialization when no curriculum override is needed
- unblocking identity upgrade when enrollment exists

### Curriculum Coordinator

Owns:

- offering quality
- required/elective basket readiness
- prerequisite and basket-rule review
- override review where request validation requires curriculum judgment

Recommended practical split:

- Admissions gets the family to a valid intended offering and sends the offer
- Academic Admin confirms the institutional placement
- Curriculum Coordinator confirms the academic basket and exceptions

## 7. Best-Practice Anchors

Status: Planned
Code refs: None
Test refs: None

This proposal is aligned with common patterns in leading admissions/SIS/LMS products:

- one-time form capture with downstream reuse rather than re-entry
- dashboarding around status changes and tasks
- explicit distinction between applicant/admitted/enrolled states
- explicit distinction between internal approval, offer, family acceptance, and enrolled status
- self-enrollment only when institutionally enabled and constrained
- server-owned enrollment transaction rather than client-assembled CRUD

External anchors:

- OpenApply form design allows schools to link forms to campus and programme and reuse standardized fields so applicants fill shared fields once: [Creating an Application & Enrollment Form](https://help.openapply.com/hc/en-us/articles/4405314001677-Creating-an-Application-Enrollment-Form)
- OpenApply dashboard focuses staff on status changes, tasks, latest activity, and academic-year filters: [Viewing your Applicant Dashboard](https://help.openapply.com/hc/en-us/articles/4405319803661-Viewing-your-Applicant-Dashboard)
- OpenApply/ManageBac synchronization treats enrolled status and student identity as a controlled sync boundary: [Bulk Create Student Emails for Synchronisation to ManageBac+](https://help.openapply.com/hc/en-us/articles/4405382217741-Bulk-Create-Student-Emails-for-Synchronisation-to-ManageBac)
- OpenApply roster/status handling distinguishes applicant states from enrolled and withdrawn states: [Understanding Rosters and Applicant Statuses](https://help.openapply.com/hc/en-us/articles/49483697387289-Understanding-Rosters-and-Applicant-Statuses)
- OpenApply also supports an enrolment form and fee path after `Admitted`, which means the family can move from offered place to enrolment through a guided post-offer form rather than through the original application alone: [Enabling Payments on a Form](https://help.openapply.com/hc/en-us/articles/4405387271565-Enabling-Payments-on-a-Form)
- Canvas self-enrollment is institution-controlled and only available when enabled by the admin: [How do I enable course self-enrollment with a join code or secret URL?](https://community.canvaslms.com/t5/Instructor-Guide/How-do-I-enable-course-self-enrollment-with-a-join-code-or/ta-p/830)
- Moodle separates account self-registration from course self-enrollment and supports enrollment keys to constrain access: [Self enrolment](https://docs.moodle.org/en/Self_enrolment)
- Toddle positions SIS sync as a way to avoid duplicate operational entry across systems: [SIS integrations supported by Toddle](https://help.toddleapp.com/en/articles/8702998-sis-integrations-supported-by-toddle)
- PowerSchool enrollment setup centralizes enrollment policy such as concurrent enrollment, grade restrictions, and minimum age: [Student enrollment setup](https://support.powerschool.com/help/sms/800/districtuser/Content/Topics/Enrollment-Setup.htm)

## 8. Higher-Ed Pattern Notes

Status: Planned
Code refs: None
Test refs: None

The K-12 pattern is not enough here.

Community colleges and small universities usually separate admission from actual enrollment much more explicitly than schools do.

### 8.1 Community colleges

Common operating pattern:

- application is often broad-access or open-admissions
- student may be admitted before they are truly registration-ready
- additional steps usually sit between admission and enrollment:
  - transcript and placement review
  - residency determination
  - orientation
  - advising / academic plan
  - financial-aid readiness
  - registration
  - payment or payment arrangement

Official examples:

- Austin Community College describes a year-round, open-admissions model and makes students eligible for credit classes only after the admissions steps are completed, then moves them into orientation, registration, and payment: [ACC Admissions](https://admissions.austincc.edu/) and [ACC Registration](https://admissions.austincc.edu/registration/)
- Foothill College explicitly ties major/goal declaration and orientation completion to enrollment readiness and priority registration: [Foothill Apply & Register](https://foothill.edu/reg/index.html)

Product implication:

- community colleges need a clear separation between:
  - `Admitted`
  - `Offer Accepted`
  - `Registration Ready`
  - `Registered`
  - `Enrolled`

They also need flexibility because many students are:

- undecided at admission
- transfer students
- dual-enrollment students
- certificate-only or workforce learners
- part-time students who may not build a full basket at once

This means Ifitwala should not assume that every admitted applicant is ready for a full program-course request immediately.

### 8.2 Small universities

Common operating pattern:

- admission decision comes first
- admitted student then confirms intent to enroll, often with a deposit or confirmation agreement
- that confirmation unlocks next steps such as housing, orientation, advising, and early registration
- course registration still sits after the commitment step, not inside the original application

Official examples:

- Regent University positions the enrollment deposit as the commitment step that claims a seat and unlocks early registration and housing access: [Regent Enrollment Deposit](https://www.regent.edu/college-of-arts-and-sciences/admissions/enrollment-agreement/)
- Wheaton College materials for admitted students show confirmation, deposit, advisor consultation, and class registration as distinct steps between admission and enrollment: [Wheaton Steps to Enrollment](https://www.wheaton.edu/media/graduate-school/graduate-admissions/2025.steps-to-enrollment.pdf) and [Wheaton Passage](https://www.wheaton.edu/life-at-wheaton/wheaton-passage/)
- Regent Registrar policy also distinguishes waitlist, registration requirements, and official in-attendance status from mere admission: [Regent Registrar](https://www.regent.edu/registrars-office/)

Product implication:

- small universities often need an explicit state between `Admitted` and `Registered`
- that state is usually something like:
  - `Intent to Enroll`
  - `Deposit Paid`
  - `Committed`

This is important because "accepted" is not the same as "yielded", and "yielded" is not yet the same as "enrolled".

### 8.3 What this means for Ifitwala

Ifitwala should support a status chain that can flex by institution type.

Recommended generalized model:

- `Applicant`
- `Admitted`
- `Offer Sent`
- `Offer Accepted / Committed`
- `Student Created`
- `Registration Ready`
- `Request Under Review`
- `Registered`
- `Enrolled`

Operationally:

- community colleges may spend longer in `Registration Ready`
- small universities may spend longer in `Committed / Intent to Enroll`
- both still benefit from using `Program Enrollment Request` as the controlled transaction before committed enrollment

## 9. Options to Build the Feature

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`, `ifitwala_ed/api/admission_cockpit.py`
Test refs: None (proposal only)

The feature should not be built until the product chooses which higher-ed model it wants to optimize for first.

### Option A. Approved -> offer -> accept -> generate request after student creation (Chosen)

Shape:

- keep current `Student Applicant` boundary
- add explicit offer and acceptance states in admissions workflow
- create draft `Program Enrollment Request` only after `Student` exists

Pros:

- lowest drift against current code and docs
- works for both K-12 and higher-ed
- matches the OpenApply-style offer/accept model
- cleanest path for Frappe v16 implementation

Cons:

- academic review starts only after student creation
- less ideal if the institution wants advising or basket-building before student creation

Best fit:

- small universities
- schools that want a commitment step before registration
- institutions that want low-risk first rollout

Chosen status additions for `Student Applicant` workflow:

- `Offer Sent`
- `Offer Accepted`

Recommended workflow sequence:

- `Under Review`
- `Approved`
- `Offer Sent`
- `Offer Accepted`
- `Promoted`

### Option B. Offer acceptance includes enrollment choices in one guided family step

Shape:

- keep `Student Applicant`
- after offer is sent, family sees one guided response flow:
  - accept or decline
  - confirm offered placement or choose from allowed offerings
  - complete required enrollment selections
  - optionally pay a deposit or fee
- create `Student`, then generate the draft request from the accepted response package

Pros:

- strongest match for the user's preferred OpenApply-style flow
- reduces handoff loss between offer acceptance and enrollment choices
- makes the family response transaction explicit

Cons:

- more admissions-portal workflow complexity
- still requires careful rule design for choice-driven programs

Best fit:

- international schools using offer/accept logic
- small universities with a commitment step
- institutions that want family choice captured before request generation

### Option C. Offer is contingent on required enrollment choices

Shape:

- committee approves internally
- institution sends an offer, but final acceptance remains incomplete until the family submits required enrollment choices
- applicant moves through:
  - `Offer Sent`
  - `Offer Pending Enrollment Choices`
  - `Offer Accepted`
- only then create `Student` and/or draft request according to policy

Pros:

- closest to the user's stated requirement
- makes program/offering/course choice part of the admission outcome
- helpful where seat allocation depends on actual family selections

Cons:

- status model becomes more complex
- deadline, partial-save, and conflict handling must be designed carefully
- institutions may confuse "approved" with "fully enrolled" unless UI is very explicit

Best fit:

- schools where the offer is tied to track, campus, stream, or basket selection
- colleges where final placement depends on the accepted program path

Recommendation:

- strong candidate if the product wants admissions and enrollment choice to feel like one guided family transaction

### Option D. Allow true pre-student enrollment requests

Shape:

- change `Program Enrollment Request` so it can exist before `Student`
- anchor the request to `Student Applicant` or a new pre-student identity

Pros:

- advising and curriculum review can start earlier
- strongest early-planning flow for complex degree pathways

Cons:

- this is a schema and contract change
- it risks duplicate truth between applicant intent and request state
- it needs a careful redesign of request identity and lifecycle

Best fit:

- community colleges with heavy advising before matriculation
- universities that treat course planning as part of pre-matriculation onboarding

Recommendation:

- do not start here first

### Option E. Skip request staging and create enrollment directly from admission

Shape:

- on approval or promotion, create `Program Enrollment` directly

Pros:

- simplest-looking UX

Cons:

- wrong architecture for this repo
- bypasses validation snapshot and override provenance
- weak fit for higher-ed operational reality

Recommendation:

- reject this option

### Questions the product team must answer before building

1. When does the institution want to create the `Student` record: at admit, at commitment, or at first registration?
2. Does the institution need an explicit `Offer Sent` and `Offer Accepted` stage, or is `Approved` enough?
3. Can an offer be accepted without enrollment choices, or must the choices be part of acceptance?
4. Does the institution need an explicit `Intent to Enroll` or deposit step?
5. Is program offering selected during application, after admission, or during advising?
6. Are students allowed to self-select only a program offering, or also a course basket?
7. For community-college scenarios, do undecided, transfer, dual-enrollment, and workforce learners all use the same admissions object?
8. What is the canonical meaning of `enrolled` in Ifitwala for higher-ed:
   - approved request
   - registered in at least one class
   - financially cleared
   - in attendance on the first day
9. Which role owns each handoff:
   - Admissions
   - Registrar / Academic Admin
   - Curriculum Coordinator
   - Advisor
10. Do we need holds before registration, and if yes, are those admissions-owned or registrar-owned?
11. Should the first generated request auto-seed required courses only, or should it stay empty until advising?
12. Do we want one universal flow across K-12 and higher-ed, or a settings-driven variant by institution type?

## 10. Frappe v16 Engineering Direction

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/admission/doctype/admission_settings/admission_settings.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs: None (proposal only)

Implementation should follow the current repo discipline and official Frappe controller model.

Engineering rules for this feature:

- extend parent DocTypes, not child-table controllers
- use `Document` lifecycle methods and named workflow actions for meaningful transitions
- keep request generation idempotent on the server so duplicate clicks cannot create duplicate staging records
- keep admissions hub actions as named workflow calls, not generic client-side CRUD assembly
- use aggregated server payloads for cockpit views instead of per-card N+1 fetches
- cache only stable shared metadata such as published offering lookups; do not cache user-sensitive review queues without scoped keys

Frappe references:

- controller hooks belong in DocType controller classes: [Controllers](https://docs.frappe.io/framework/v14/user/en/basics/doctypes/controllers)
- document event behavior should be implemented in the controller module instead of scattered hooks where avoidable: [Executing Code On Doctype Events](https://docs.frappe.io/framework/v14/user/en/guides/app-development/executing-code-on-doctype-events)
- whitelisted RPC methods are the correct fit for named workflow endpoints: [REST / RPC Introduction](https://docs.frappe.io/framework/v13/user/en/guides/integration/rest_api)

## 11. Deeper Pre-Student Enrollment Path

Status: Planned
Code refs: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.json`, `ifitwala_ed/docs/docs_md/program-enrollment-request.md`
Test refs: None (proposal only)

If the business wants a true enrollment-request record before student creation, that is a separate architecture decision.

That deeper option would need approval because it changes the current boundary by allowing enrollment staging before `Student` exists.

Pros:

- full enrollment workflow starts earlier
- academic review can begin before promotion
- admissions hub can show a real request record earlier

Cons:

- current request schema and docs would no longer match runtime assumptions
- request identity would need a new pre-student anchor
- request basket rules for applicants without final student identity become more complex

Blind spots:

- whether every school needs applicant-side course choice
- whether request approval is allowed before admissions decision or only after it
- whether self-enrollment is intended only for offering choice or also for elective basket choice

Risks:

- duplicate truth if applicant intent and request state diverge
- hidden contract drift across docs, tests, and APIs
- admissions staff owning curriculum decisions they should not own

Recommendation:

- do not start with this deeper path
- start with the current-contract path first
- revisit pre-student PER only if the operating model still feels too manual after Phase 1

## 12. Contract Matrix

Status: Planned
Code refs: `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`, `ifitwala_ed/api/admission_cockpit.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
Test refs: None (proposal only)

| Area | Current runtime owner | Proposed owner/path | State |
| --- | --- | --- | --- |
| Applicant intent capture | `Student Applicant` | Keep on `Student Applicant`; make operational in admissions flow | Planned |
| Offer lifecycle | `Student Applicant` lifecycle plus admissions workflow | Add explicit committee-approved, offer-sent, and offer-response states | Planned |
| Student creation | `StudentApplicant.promote_to_student()` | Keep as-is, but use it as request-generation trigger when policy says so | Planned |
| Enrollment staging | `Program Enrollment Request` | Keep as only transactional staging object | Planned |
| Committed enrollment | `Program Enrollment` | No change | Implemented |
| Policy switch | `Admission Settings` | Add enrollment-timing policy in admissions settings | Planned |
| Staff cockpit | `Admissions Cockpit` | Add enrollment strip, blockers, and actions | Planned |
| Applicant portal | `/admissions` profile/status flow | Optionally expose offer-response, applicant-confirm, or applicant-select modes | Planned |
| Academic validation | Enrollment engine + request validation | No change to validation authority | Implemented |
| Identity activation | `upgrade_identity()` after active enrollment | No change to invariant; use hub to remove the blocking gap earlier | Implemented |
| Tests | Admissions + enrollment test modules | Add end-to-end tests when implemented | Planned |

## 13. Rollout

Status: Planned
Code refs: None
Test refs: None

Recommended rollout:

1. Approve the product boundary: applicant owns intent, request owns transaction.
2. Implement settings-controlled request generation after student creation.
3. Add admissions hub enrollment strip and actionability.
4. Add optional applicant-confirm mode for offering/year if needed.
5. Re-evaluate whether true pre-student requests are still necessary.

## 14. Proposed Decision

Status: Planned
Code refs: None
Test refs: None

Approve the following direction:

- adopt `Option A` as the first implementation path
- make program enrollment intent a first-class part of admissions on `Student Applicant`
- add explicit `Offer Sent` and `Offer Accepted` states to the `Student Applicant` workflow
- reuse applicant `program_offering` and `academic_year` when generating the enrollment request
- add one admissions setting that controls whether request generation is automatic or guided after student creation
- redesign `/staff/admission-cockpit` to surface the applicant-to-enrollment handoff explicitly
- keep true pre-student enrollment requests out of scope for the first implementation

Naming decision:

- use `Offer Sent`, not `Admission Offered`
- use `Offer Accepted` as the family commitment state

This gets the product closer to top-tier SMS/SIS behavior without breaking the current Frappe v16 contracts already present in the codebase.

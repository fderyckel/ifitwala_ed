# Contact Data Governance - No Universal Address Book

Status: Locked target architecture with current-runtime gap register
Last updated: 2026-05-19
Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/students/doctype/student/student.py`
- `ifitwala_ed/students/doctype/guardian/guardian.py`
- `ifitwala_ed/hr/doctype/employee/employee.py`
- `ifitwala_ed/admission/doctype/inquiry/inquiry.py`
- `ifitwala_ed/admission/doctype/student_applicant/student_applicant.py`
- `ifitwala_ed/admission/admission_utils.py`
- `ifitwala_ed/api/admissions_portal.py`
- `ifitwala_ed/api/family_consent.py`
- `ifitwala_ed/contacts/contact_privacy.py`
- `ifitwala_ed/contacts/contact_audit.py`
- `ifitwala_ed/contacts/contact_export.py`
- `ifitwala_ed/governance/doctype/contact_access_log/contact_access_log.py`
- `ifitwala_ed/governance/doctype/contact_access_log/contact_access_log.json`
- `ifitwala_ed/governance/doctype/contact_export_request/contact_export_request.py`
- `ifitwala_ed/governance/doctype/contact_export_request/contact_export_request.json`
Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`
- `ifitwala_ed/students/doctype/student/test_student_unit.py`
- `ifitwala_ed/students/doctype/guardian/test_guardian_unit.py`
- `ifitwala_ed/hr/doctype/employee/test_employee.py`
- `ifitwala_ed/admission/doctype/inquiry/test_inquiry.py`
- `ifitwala_ed/admission/doctype/student_applicant/test_student_applicant.py`
- `ifitwala_ed/api/test_admissions_portal.py`
- `ifitwala_ed/api/test_family_consent.py`
- `ifitwala_ed/contacts/test_contact_privacy.py`
- `ifitwala_ed/governance/doctype/contact_access_log/test_contact_access_log.py`
- `ifitwala_ed/contacts/test_contact_export.py`

This document defines the target security posture for personal contact data across Ifitwala Ed.

It supersedes any product idea that treats native Frappe `Contact` as the canonical people registry. It does not claim the target is fully implemented today. Current native-`Contact` behavior remains documented in `../setup/contact_permission_contract.md` as the current-runtime contract and is listed here as a migration gap.

## 1. Canonical Rule

Contact data belongs to the domain record that created the relationship.

There is no universal downloadable contact database in Ifitwala Ed.

Rules:

1. `Student` owns student contact data.
2. `Guardian` owns guardian contact data.
3. `Employee` owns employee contact data.
4. `Student Applicant` and `Inquiry` own applicant-stage and lead-stage contact data.
5. Supplier, partner, and external relationship contact data must stay owned by their domain records when those workflows are implemented.
6. Native Frappe `Contact` is not the target canonical registry for education people data.
7. New work must not add another "everything becomes Contact" path.

## 2. Product Rule

Users should communicate through purpose-bound workflows, not a global address book.

Allowed product patterns:

- send a message to selected guardians for students in a permitted audience
- call an emergency contact from a student safety context
- email admissions applicants missing documents
- notify employees assigned to a supervised activity
- contact a payer from a scoped finance workflow

Rejected product patterns:

- browse all contacts
- export all contacts
- report-builder access over all personal contact values
- client-side filtering of broad person/contact payloads
- raw email or phone lists when a server-side recipient resolver can perform the action

Blocked actions must explain why the action is blocked and what the user can do next.

## 3. Target Contact Point Layer

If a cross-domain routing index is needed, it must be an internal governed layer, not a user-facing address book.

Target concept:

```text
Communication Contact Point
- owner_doctype
- owner_name
- subject_type
- subject_id
- organization
- school
- channel_type
- purpose
- value_encrypted
- normalized_hash
- masked_display
- is_primary
- verified_on
- disabled
```

Rules:

1. The contact point table is an internal routing index.
2. It must not be exposed as a normal Desk list, report-builder source, or generic API resource.
3. Raw values must stay hidden unless a named workflow has permission and purpose to use them.
4. `normalized_hash` may support deduplication and matching, but must not become a user-facing search surface.
5. `masked_display` is the default UI value.
6. Purpose is mandatory and must be specific enough to support audit and minimization.

This target requires an approved schema decision before implementation. Do not invent the DocType or fields outside that approval.

## 4. Permission Stance

System configuration authority is not the same as personal-data ownership.

Rules:

1. `System Manager` may configure the system; it must not automatically gain product ownership of the school contact graph.
2. School-level data exports belong to scoped data stewardship workflows, not raw technical roles.
3. DPO-style approval must be a separate product workflow before exceptional exports or erasure actions exist.
4. Portal users must never gain Desk access to native `Contact`.
5. Staff access to raw contact values must be relationship-scoped, purpose-scoped, and server-enforced.

Current-runtime lockdown status:

- Native `Contact` list/doc access is now deny-by-default for ordinary roles unless an employee or education relationship scope is proven.
- `System Manager` is no longer treated as unrestricted product owner for native `Contact` list/export/delete/raw-value access; the built-in `Administrator` remains the framework superuser.
- Native `Contact` delete permission is no longer seeded for ordinary Desk roles and document-level delete is blocked by the Contact permission hook.
- Admissions and marketing roles no longer bypass Contact query scoping.
- Native `Contact` create/write DocPerm rows still exist as transitional Frappe seed data, but document-level editor operations are blocked by the permission hook while domain-owned contact-point services are future work.

Remaining gaps require approved implementation slices: full export execution with per-row logging, and eventual Contact Point schema/migration.

API hardening status:

- Admissions invite/contact-option APIs now require both an admissions staff role and scoped access to the target `Student Applicant`; `System Manager` role membership alone does not bypass applicant scope for these contact-sensitive staff actions.
- Applicant portal profile APIs keep using the canonical applicant/family workspace binding before returning applicant contact prefill or guardian rows.
- Student Contact lookup and Student Guardian helper endpoints are scoped through `Student` read permission before returning native Contact names or guardian contact rows.
- Family consent write-back does not accept caller-supplied Contact IDs; it resolves Contact rows only from the already authorized student/guardian context.
- Inquiry-to-Contact creation now blocks reuse of existing native `Contact` rows already linked to protected education records (`Student`, `Guardian`, `Employee`, or `Student Applicant`).

Contact privacy service boundary status:

- `ifitwala_ed/contacts/contact_privacy.py` is the approved current-runtime boundary for the first contact-sensitive workflows.
- Covered workflows are applicant contact prefill/invite email options, Student CRM contact summaries, Student guardian summaries, family-consent profile contact write-back, and Inquiry protected-contact reuse checks.
- The service still reads legacy native `Contact`, `Contact Email`, and `Contact Phone` internally because the Contact Point schema is not implemented.
- Callers must provide a non-empty `purpose`; masked DTOs are the default for Student/Guardian summaries.
- Raw values are still allowed only through explicitly named current workflows such as applicant invite/prefill and family-consent write-back.
- Legacy Contact creation/update code in Student, Guardian, Inquiry, and admissions profile flows remains a migration gap, not an approved pattern for new surfaces.

Contact access logging status:

- `Contact Access Log` is an append-only audit DocType for contact-sensitive access metadata.
- The audit helper is `ifitwala_ed/contacts/contact_audit.py`; callers should not create log rows directly.
- Raw applicant prefill, applicant invite recipient resolution, family-consent raw read/write-back, Inquiry Contact reuse resolution, and denied contact-sensitive attempts are logged through the contact privacy boundary.
- Audit rows must never store raw email, phone, mobile, address, file names, or full request payload values.
- `Contact Access Log` rows are service-created only, immutable after insert, and cannot be deleted through the document controller.

Contact export request gate status:

- `Contact Export Request` is implemented as the governed approval object for contact-data export metadata.
- The current service boundary is `ifitwala_ed/contacts/contact_export.py`.
- The audit/export DocTypes live in the existing `Governance` module; Ifitwala Ed must not claim a `Contacts` module because Frappe core owns native `Contact`/`Address` DocTypes there.
- PR-5 supports only these scoped request types: `Student Group Guardians`, `Admissions Applicants`, `Inquiry Leads`, and `Employees`.
- Global scopes such as `All Contacts`, `All Guardians`, `All Students`, `All Applicants`, and `All Employees` are rejected.
- Approval requires `Data Protection Officer`; `System Manager` does not bypass the workflow.
- `assert_approved_contact_export(...)` denies unless the request is approved, unexpired, purpose-matched, scope-matched, and used by the requester or a privacy approver.
- Approval, rejection, allowed assertions, and denied assertions create request-level `Contact Access Log` metadata with `access_type = export`.
- No CSV generation, downloadable file, watermarking, or per-row export execution exists yet.

## 5. Export Contract

Contact-data export is a privileged business workflow, not a generic Desk action.

Target workflow:

```text
Contact Export Request
- requester
- organization
- school
- scope_type
- scope_name
- purpose
- legal_basis
- fields_requested
- estimated_row_count
- approved_by
- approved_on
- expires_on
- status
```

Implemented gate rules:

1. Default decision is denied.
2. "All contacts" is not an allowed scope.
3. Row count must be shown before approval.
4. Approval is role-separated from ordinary system configuration and requires `Data Protection Officer`.
5. Approved requests expire.
6. Export execution must not proceed unless `assert_approved_contact_export(...)` passes.
7. Approval, rejection, allowed assertions, and denied assertions must log metadata through `Contact Access Log`.

Future export execution rules:

1. Generated files must expire quickly.
2. Every export must be watermarked with requester, timestamp, school, and purpose.
3. Export execution must log each exported subject/contact point.
4. Exports must not run in the background without an approved request record.

CSV generation, watermarking, and per-row export logging are not implemented yet.

## 6. Raw-Value Access Contract

Default UI display must use masked values.

Examples:

```text
Guardian: Marie D.
Email: m****@example.com
Phone: +66 *** *** 1234
```

Raw values may be resolved only by named server-side workflows such as emergency contact, admissions follow-up, HR communication, finance payer contact, or approved export.

Each raw-value access must log:

- user
- subject
- contact point
- purpose
- source page or workflow
- timestamp
- IP/user agent when available

APIs must return purpose-specific DTOs. Do not return broad serialized people/contact objects or `fields=["*"]` for sensitive person records.

## 7. Delete And Erasure Contract

Direct deletion is not a normal contact-management action.

Target rules:

1. Native `Contact`, future `Communication Contact Point`, and sensitive person DocTypes must not be deleted through ordinary Desk buttons.
2. Deactivation, archival, erasure, and pseudonymization require named workflows.
3. Applicant erasure and Student pseudonymization are different data-subject states.
4. Destructive workflows require approval, scope proof, audit output, and retention checks.
5. Legacy remediation belongs in one-shot patches, not runtime repair paths.

Related file-erasure authority:

- `../files_and_policies/files_02_GDPR.md`

## 8. Named Service Boundary

Sensitive contact retrieval must use named services.

Allowed examples:

```python
get_guardian_contact_for_student(student, purpose)
resolve_recipients_for_org_communication(audience, purpose)
get_employee_contact_for_hr_case(employee, purpose)
get_supplier_contact_for_purchase_order(supplier, purpose)
```

Rejected examples:

```python
frappe.get_all("Contact")
frappe.get_all("Guardian", fields=["*"])
frappe.db.get_all("Student", fields=["student_name", "email", "phone"])
```

Rules:

1. Resolve tenant scope before recipient assembly.
2. Resolve purpose before raw-value access.
3. Return the smallest DTO needed by the workflow.
4. Keep server-side permission checks at the action endpoint, not only in the UI.
5. Avoid request waterfalls; communication bootstraps should use bounded context endpoints where a page needs multiple related blocks.

## 9. Current Runtime Audit

This audit identifies native-`Contact` surfaces found in the current workspace. It is not approval to change them all in one patch.

| Surface | Current behavior | Target classification |
| --- | --- | --- |
| `setup/setup.py::grant_core_crm_permissions` | Seeds native `Contact`/`Address` Desk permissions; native `Contact` delete is no longer seeded for ordinary roles. | Keep runtime lockdown; migrate away from broad Contact DocPerm after scoped services exist. |
| `hooks.py` | Registers native `Contact` permission hooks, Contact `on_update` sync, and Frappe core User-to-Contact update hook. | Keep permission hook lockdown; remove automatic global Contact coupling after replacement services exist. |
| `utilities/contact_utils.py` | Denies native `Contact` list/doc access by default; allows only scoped employee or education-linked read paths; blocks ordinary delete/export/unscoped editor access; syncs Contact changes back to Guardian fields. | Replace with purpose-bound service checks and stop Contact-as-source-of-truth writeback. |
| `students/doctype/student/student.py::ensure_contact_and_link` | Auto-creates/reuses native `Contact` for Student email and links it to Student. | Replace with Student-owned contact points. |
| `students/doctype/student/student.py::get_student_crm_summary` | Builds Student-context Contact/Address summary from linked native records after Student read permission is proven; direct Student-to-Contact lookup and guardian helper endpoints are also Student-scope guarded. | Keep product pattern, replace data source with scoped contact/address services. |
| `students/doctype/guardian/guardian.py` | Auto-creates/reuses native `Contact`, links it to Guardian, and binds Contact to Guardian User creation. | Replace with Guardian-owned contact points and explicit User identity binding. |
| `hr/doctype/employee/employee.py` | User creation creates/reuses native `Contact`, links it to Employee, and stores `Employee.empl_primary_contact`. | Replace with Employee-owned contact points; keep User profile sync separate. |
| `admission/doctype/inquiry/inquiry.py::create_contact_from_inquiry` | Staff/assigned action creates or reuses native `Contact` for Inquiry lead email/phone, but does not reuse a Contact already linked to protected education people records. | Replace with Inquiry-owned contact point; keep external CRM matching purpose-bound. |
| `admission/admission_utils.py` | Provides `ensure_contact_for_email`, email upsert, dynamic-link sync, applicant contact binding. | Replace with contact point resolver and purpose-bound dedupe. |
| `api/admissions_portal.py` | Resolves applicant Contact prefill, creates/updates guardian Contact rows, links Contact to applicant/guardian, and hydrates family collaborators only after applicant/family or scoped staff access is proven. | Replace with applicant/guardian contact points; preserve low-friction invite UX through scoped services. |
| `admission/doctype/student_applicant/student_applicant.py` | Carries guardian Contact links through promotion to Student/Guardian/Student Applicant through scoped applicant lifecycle methods. | Replace with explicit promotion of domain-owned contact points. |
| `api/family_consent.py` | Reads and writes linked Contact email/mobile during signed portal write-back from authorized student/guardian context; callers cannot supply arbitrary Contact IDs. | Replace with signed, audited contact point write-back. |
| `public/js/contact.js` and `public/js/queries.js` | Native Contact form/query helpers remain exposed to Desk flows. | Restrict to non-sensitive organization/external CRM surfaces or retire for education people data. |
| `admission/doctype/admission_external_identity/*.json` and `admission/doctype/admission_message/*.json` | Planned CRM records can link to native `Contact`. | Keep only for external CRM identity if approved; must not become universal people registry. |

Known docs that need coordinated updates before implementation:

- `../setup/contact_permission_contract.md`
- `../hr/employee.md`
- `../admission/04_identity_upgrade.md`
- `../admission/05_admission_portal.md`
- `../admission/11_admissions_crm_contract.md`
- `../files_and_policies/policy_04_family_signature_and_consent_contract.md`
- `../files_and_policies/policy_05_phase2a_desk_authoring_portal_signing_plan.md`
- `../docs_md/inquiry.md`
- `../docs_md/student-applicant.md`
- `../docs_md/student.md`

## 10. Migration Order

Migration must be explicit and incremental.

1. Freeze: no new auto-create-native-Contact behavior for education people data.
2. Guard: broad native Contact list/export/delete access is locked down; keep regression tests in place while deeper API and service work continues.
3. Design: approve the Contact Point schema and service API contract.
4. Implement: add purpose-bound contact-point writes for one domain at a time.
5. Bridge: read through contact-point services while legacy native Contact data still exists.
6. Patch: use one-shot patches to migrate verified legacy Contact links into contact points.
7. Retire: remove native Contact dynamic-link dependencies only after tests and docs prove replacement coverage.

Do not add permanent runtime repair/self-heal flows for legacy Contact drift.

## 11. Test Expectations

Every implementation slice must include focused regression coverage for:

- no global native `Contact` list access for ordinary roles
- no native `Contact` export/delete without named approval workflow
- `System Manager` not automatically gaining raw contact export authority
- tenant scope on contact-point recipient resolution
- masked DTOs by default
- audited raw-value access for explicit purposes
- no `fields=["*"]` sensitive contact payloads
- no Contact query scoping bypass for admissions/marketing roles unless a separate approved external-CRM contract requires it
- no direct delete for contact-point records or native legacy Contact rows when they represent education people data

## 12. Non-Goals

This contract does not try to stop a real database or infrastructure administrator from dumping tables. That requires operational controls outside Frappe permissions, including infrastructure access control, database audit logging, encryption/key governance, backup controls, and contractual operating procedures.

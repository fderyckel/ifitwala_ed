# Print System Contract

Status: Approved direction, initial reference implementation added

Scope:
- all Desk `Print Format` work
- all print-friendly report HTML work
- all future printable DocType surfaces in `ifitwala_ed`

Audience:
- developers
- reviewers
- coding agents

This document is the canonical developer-facing contract for print architecture in Ifitwala_Ed.

It is authoritative for new print work and for refactoring existing print surfaces. It does not claim that the full print system described here is already implemented.

## 0. Current Repo Snapshot

Status: Partial

Code refs:
- `ifitwala_ed/hr/print_format/employee_print/employee_print.json`
- `ifitwala_ed/students/print_format/student_profile/student_profile.json`
- `ifitwala_ed/patches/publish_student_profile_print_format.py`
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.html`
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.py`
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/students/doctype/student/student.py`
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`

Test refs:
- `ifitwala_ed/students/print_format/test_student_profile_print_format.py`
- existing report coverage is feature-specific, not a shared print-system contract

Current reality:

1. The repo already contains app-owned `Print Format` records for `Employee` and `Student Profile`.
2. The repo already contains report-print HTML for operational outputs, including medical and emergency contact printing.
3. This contract now defines the shared print architecture, but the repo does not yet have a shared runtime print helper layer or centralized reusable print assets.
4. App-owned print-format files do not become visible in Desk until the target site syncs them into the database. In current repo direction, that happens through site migrate plus any required patch-based publication logic.
5. `hooks.py` does not currently wire a custom Jinja methods/filters package, so new print work must assume stock Frappe/Jinja capabilities unless that infrastructure is explicitly added later.
6. Student image handling is governed and privacy-sensitive. Any print contract that includes student photos must stay aligned with the governed file and consent rules already documented elsewhere.

## 1. Strategic Position

Status: Approved

Code refs:
- `ifitwala_ed/hr/print_format/employee_print/employee_print.json`
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.html`

Test refs:
- none yet

Rules:

1. Treat print as a product system, not as one-off per-DocType decoration.
2. New serious single-record prints must default to `Print Format` with `custom_format = 1`, `print_format_type = Jinja`, and explicit HTML/CSS owned by the app.
3. Report-print HTML remains the canonical lane for multi-record, cross-record, or operational packet outputs.
4. The Desk print builder may be used for quick experimentation, but builder output is not the canonical source for serious production print layouts.
5. JS-based print formats are exception-only. They are not the default for new premium printable record layouts.
6. Print artifacts must be reviewable, version-controlled, and app-owned once approved.

## 2. Print Lane Taxonomy

Status: Approved

Code refs:
- `ifitwala_ed/hr/print_format/employee_print/employee_print.json`
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.py`
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.html`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Test refs:
- no shared print-lane tests yet

### 2.1 Lane A: Single-Record DocType Print Format

Use `Print Format` when all of the following are true:

1. The output represents one document as its primary truth source.
2. The layout is mostly driven by fields already present on that document and its existing child tables.
3. The output should appear in the standard document print flow.
4. The output does not require a separate server-owned visibility contract beyond the document's existing `print` permission model.

Examples:

- `Student Profile`
- `Employee Profile`
- future single-record `Course` or `School` profiles when they stay within the owning DocType contract

### 2.2 Lane B: Report-Print HTML

Use report-print HTML when any of the following are true:

1. The output is operational rather than a single-record profile.
2. The output spans multiple records.
3. The output requires cross-doctype shaping or dedicated server-side aggregation.
4. The output needs a narrower or otherwise specialized permission path that should not piggyback on standard document print access.

Examples:

- medical and emergency packets
- grouped review printouts
- reporting and analytics extracts

### 2.3 Non-Negotiable Rule

Do not force all printable surfaces into one lane.

If the output is fundamentally a report, keep it in the report lane. If the output is fundamentally a single-record profile, keep it in the `Print Format` lane.

## 3. Shared Visual Language

Status: Approved direction, implementation not yet centralized

Code refs:
- `ifitwala_ed/students/report/medical_info_and_emergency_contact/medical_info_and_emergency_contact.html`

Test refs:
- none yet

Rules:

1. All serious printable record layouts must share one premium visual language across modules.
2. That language should be formal, restrained, and institution-facing rather than ERP-dense.
3. Shared traits should include:
   - generous whitespace
   - quiet typography hierarchy
   - light borders and rules
   - restrained accent usage
   - compact metadata grids
   - elegant child-table rendering
4. Student, Employee, Course, and similar profile prints should feel related, but they do not need identical section order or identical page skeletons.
5. Phase 1 should standardize tokens and page grammar first. Do not assume a shared runtime CSS include or shared Jinja macro package until that infrastructure is explicitly implemented.
6. Until a shared helper layer exists, each approved print format may embed the approved token block and layout rules directly in its owned HTML/CSS.

## 4. Schema-to-Print Workflow

Status: Approved

Code refs:
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/students/doctype/student_sibling/student_sibling.json`

Test refs:
- none yet

Rules:

1. Every new print format starts from the current workspace schema, not memory.
2. For each target DocType, inspect:
   - the parent DocType JSON
   - any child table DocType JSON
   - the canonical docs that define behavior and field meaning
3. Classify fields into:
   - hero
   - supporting
   - conditional
   - excluded
   - child-table sections
4. Exclude by default:
   - hidden fields
   - helper HTML fields
   - workflow-only linkage fields unless the print purpose requires them
   - internal utility flags
5. Child tables must never print accidentally. For each child table, explicitly choose:
   - omit
   - summarize
   - compact table
   - card layout
   - full detail
6. A print format is not approved until the field map is explicit and reviewable.

## 5. Permissions, Visibility, and Scope

Status: Active

Code refs:
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/docs/setup/school_organization_scope_contract.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

Test refs:
- document-specific permission tests only; no shared print permission matrix currently exists

Rules:

1. Standard print formats follow the owning DocType's standard `print` permission contract.
2. Layout polish does not create a new permission boundary.
3. If a printable output needs a narrower audience, a different scope contract, or materially more sensitive content, do not hide that inside a standard DocType print format. Move it to a dedicated report or action with server-owned permission checks.
4. Printable surfaces must respect the same school, organization, and sibling-isolation contracts as the source documents.
5. No print template may widen visibility by using guessed links, unscoped lookups, or global queries hidden inside presentation logic.

## 6. Files, Images, and Governed Media

Status: Active

Code refs:
- `ifitwala_ed/students/doctype/student/student.py`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
- `ifitwala_ed/docs/admission/02_applicant_and_promotion.md`

Test refs:
- no dedicated print-path file-visibility tests currently exist

Rules:

1. Governed file and image rules remain in force when content is printed.
2. Print formats must not guess file URLs, create raw-path workarounds, or create new public copies as a print shortcut.
3. Student profile formats may include `student_image` when the authorized printing user already has access to print the underlying student record.
4. Student profile photos in print should be compact and restrained, not hero-sized.
5. Print implementation must verify that governed or private student images render in the print and PDF path without widening visibility. If that is not true in runtime, the owner must define a canonical print-safe image resolution contract before rollout.
6. No print work may weaken the current consent-gated student image posture documented in the file-governance notes.

## 7. Student Phase-1 Contract

Status: Implemented initial artifact

Code refs:
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/students/doctype/student_guardian/student_guardian.json`
- `ifitwala_ed/students/doctype/student_sibling/student_sibling.json`
- `ifitwala_ed/students/print_format/student_profile/student_profile.json`
- `ifitwala_ed/docs/docs_md/student.md`

Test refs:
- `ifitwala_ed/students/print_format/test_student_profile_print_format.py`

### 7.1 First Format

The first canonical Student print artifact should be:

- `Student Profile`

Current implementation:

- `ifitwala_ed/students/print_format/student_profile/student_profile.json`

It should be:

- one to two pages
- premium and institution-facing
- safe under the standard `Student.print` permission contract
- grounded in the Student schema already present in the repo

### 7.2 Included Fields

Hero:

- `student_full_name` with fallback to first/middle/last name construction
- `student_preferred_name` when present and distinct
- `student_id`
- `student_image`
- `anchor_school`
- `cohort`
- `student_house`
- `enabled` rendered as `Active` or `Inactive`
- `student_joining_date`

Personal:

- `student_date_of_birth`
- `student_gender`
- `student_email`
- `student_mobile_number`

Identity and language:

- `student_nationality`
- `student_second_nationality`
- `student_first_language`
- `student_second_language`
- `residency_status`

Family:

- `account_holder`
- `guardians` child table rendered from real child fields only:
  - `guardian_name`
  - `relation`
  - `can_consent`
  - `phone`
  - `email`

Siblings:

- `siblings` child table rendered from real child fields only:
  - `sibling_name`
  - `sibling_gender`
  - `sibling_date_of_birth`

Exit:

- show only when `enabled == 0`
- `student_exit_date`
- `student_exit_reason`

Notes:

- `additional_comment` only when present

### 7.3 Excluded Fields

Exclude from the standard Student Profile by default:

- `student_applicant`
- `contact_html`
- `address_html`
- `allow_direct_creation`
- internal tab, section, and layout helper fields

### 7.4 Explicit Non-Goals for Phase 1

Do not fold these into the standard Student Profile:

1. medical and emergency packet content
2. operational grouped outputs
3. admissions-history detail
4. internal-note or free-text comment dumps

Those belong in report or workflow-specific lanes unless a later approved contract says otherwise.

## 8. Version Control and Lifecycle

Status: Approved

Code refs:
- `ifitwala_ed/hr/print_format/employee_print/employee_print.json`
- `ifitwala_ed/students/print_format/student_profile/student_profile.json`
- `ifitwala_ed/patches/publish_student_profile_print_format.py`

Test refs:
- none yet

Rules:

1. Prototype in Desk only when needed to iterate quickly.
2. Once a print layout is approved, export and keep it as an app-owned artifact in the module's `print_format/` path.
3. Use explicit, user-facing names such as:
   - `Student Profile`
   - `Employee Profile`
   - `Course Profile`
4. Do not keep production artifacts under vague names such as `Custom Print 3`.
5. The approved app-owned artifact, not an ad hoc Desk customization, is the canonical source of truth.
6. New or changed app-owned print formats must be synced into each target site through migrate before they can be selected in Desk print dialogs.

## 9. Validation Checklist

Status: Active

Code refs:
- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`

Test refs:
- `ifitwala_ed/students/print_format/test_student_profile_print_format.py`
- manual verification is still required for live Frappe/PDF rendering and governed image visibility

Before approving a print artifact, verify:

1. the layout matches the shared visual language
2. the field map matches the real schema
3. helper HTML and internal utility fields are excluded
4. child tables use real child-schema fields only
5. standard DocType permissions still define visibility
6. no guessed file URLs or raw private paths are introduced
7. student images render compactly and correctly in PDF output
8. missing values collapse gracefully without ugly empty grids
9. page breaks remain readable
10. report-lane outputs stay server-shaped and bounded rather than client-waterfall-driven

## 10. Implementation Order

Status: In progress

Code refs:
- `ifitwala_ed/students/doctype/student/student.json`
- `ifitwala_ed/hr/print_format/employee_print/employee_print.json`

Test refs:
- none yet

Phase order:

1. establish this canonical print-system contract
2. implement `Student Profile`
3. backfit `Employee` onto the same visual language
4. expand to other profile-style DocTypes
5. only then consider shared helper infrastructure if repetition justifies it

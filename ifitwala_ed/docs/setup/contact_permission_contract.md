# Contact Permission Contract

Status: Active

This document is the canonical contract for Desk access to the native Frappe `Contact` DocType as governed by Ifitwala Ed setup code.

## 1. Contact Permission Contract

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/students/doctype/student/student.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`
- `ifitwala_ed/students/doctype/student/test_student.py`

Rules:

1. `Contact` remains the native Frappe DocType; Ifitwala Ed governs role access through seeded `Custom DocPerm` rows rather than a custom clone.
2. The canonical Desk roles with read/write/create access on `Contact` are `Academic Admin`, `Academic Assistant`, `Accounts User`, `Accounts Manager`, `Admission Officer`, and `Admission Manager`.
3. `Curriculum Coordinator` has read-only Desk access on `Contact` and `Address` so student-facing academic workflows can open linked family CRM records without granting edit authority.
4. Manager-level roles keep delete access on `Contact`: `Academic Admin`, `Academic Assistant`, `Accounts Manager`, and `Admission Manager`.
5. Non-manager editor roles keep no delete access on `Contact`: `Accounts User` and `Admission Officer`.
6. The permission seed must create any missing canonical roles before inserting `Custom DocPerm` rows, so migrate/setup never fails on a missing role record.
7. App-level Contact permission hooks may further restrict linked contacts through server-owned scope contracts:
   - employee-linked contacts use the Employee visibility contract
   - Inquiry, Student Applicant, active Student, and Guardian contacts use staff organization/school visibility scope for `Academic Admin`, `Academic Assistant`, `Admission Officer`, and `Admission Manager`; Inquiry contacts are recognized through Contact Dynamic Link rows and `Inquiry.contact`, and Student Applicant contacts are recognized through Contact Dynamic Link rows and `Student Applicant.applicant_contact`
   - unrelated contacts continue to defer to the seeded DocPerm contract
8. Student-form Contact and Address details are a read-only Student-context projection. A user who can read the Student may see the linked Contact summary and linked Address lines on the Student form even when native `Contact` or `Address` DocType opening/editing is not available.
9. Native `Contact` and `Address` open/edit affordances remain gated by the native DocType role-permission contract. The read-only Student projection must not call `frappe.has_permission("Contact" | "Address", ...)` during Student form load, because a negative native permission probe can add noisy role-permission messages to an otherwise successful Student page refresh.

## 2. Runtime Enforcement

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/patches/sync_core_crm_permissions.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`

Rules:

1. Fresh installs seed the canonical `Contact` permissions through `grant_core_crm_permissions()` during `after_install`.
2. Existing sites re-run the canonical seed through `ifitwala_ed.patches.sync_core_crm_permissions`.
3. `grant_core_crm_permissions()` ensures canonical roles exist before seeding the `Custom DocPerm` rows.
4. Contact document-level permission checks apply education-linked and employee-linked contact scope on top of Frappe core permissions. For read-like operations, a scoped education link may allow the native Contact form even when Frappe's core linked-document gate would otherwise deny the Contact.
5. Contact list visibility keeps unrelated contacts on the seeded DocPerm contract, but linked contacts are narrowed server-side:
   - `HR Manager` / `HR User`: organization descendants plus blank-organization employee rows
   - `Academic Admin` / `Academic Assistant`: effective school + descendant-school scope, where Academic Admin resolves school from the active Employee profile before persisted defaults
   - `Academic Admin` only: when no school scope resolves, or the active Employee profile exists with a blank `school`, organization descendants
   - `Employee`: own linked employee contact only
   - `Academic Admin`, `Academic Assistant`, `Admission Officer`, and `Admission Manager`: Inquiry, Student Applicant, active Student, and Guardian contacts within the user's visible organization/school scope; visible schools are the user's school descendants, or when no school is set, every school in the user's organization descendants. Inquiry contact visibility must check both Contact Dynamic Links and reverse references from `Inquiry.contact`. Student Applicant contact visibility must check both Contact Dynamic Links and reverse references from `Student Applicant.applicant_contact`.

## 3. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/patches.txt`
- `ifitwala_ed/patches/sync_core_crm_permissions.py`
- `ifitwala_ed/students/doctype/student/student.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`
- `ifitwala_ed/patches/test_sync_core_crm_permissions.py`
- `ifitwala_ed/students/doctype/student/test_student.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Permission seed | `grant_core_crm_permissions` | `setup/setup.py` | `setup/test_contact_permissions.py` |
| Runtime permission hook | `contact_has_permission`, `contact_permission_query_conditions` | `utilities/contact_utils.py` | `setup/test_contact_permissions.py` |
| Student-form read-only CRM projection | `get_student_crm_summary` | `students/doctype/student/student.py` | `students/doctype/student/test_student.py` |
| Existing-site rollout | CRM permission sync patch | `patches/sync_core_crm_permissions.py`, `patches.txt` | `patches/test_sync_core_crm_permissions.py`, `setup/test_contact_permissions.py` |

# HR Documentation Index

Status: Canonical index
Code refs: Listed by canonical doc below
Test refs: Listed by canonical doc below

This folder covers HR runtime contracts for Employee, Designation, Leave, Professional Development, and historical HR audit notes.

Read in this order:

1. `designation_visibility.md`
2. `employee.md`
3. `leave_management.md`
4. `professional_development_governance.md`
5. `notes_and_audits.md` only for historical context

Canonical docs:

- `designation_visibility.md` - active canonical visibility contract for `Designation`.
  Code refs: `ifitwala_ed/hr/doctype/designation/designation.py`, `ifitwala_ed/hr/doctype/designation/designation.js`, `ifitwala_ed/hooks.py`.
  Test refs: `ifitwala_ed/hr/doctype/designation/test_designation.py`, `ifitwala_ed/patches/test_normalize_legacy_designation_organizations.py`.
- `employee.md` - active current-runtime operational contract for `Employee`, linked User access, staff calendar resolution, and Employee image behavior.
  Code refs: `ifitwala_ed/hr/doctype/employee/employee.py`, `ifitwala_ed/hr/doctype/employee/employee.js`, `ifitwala_ed/hr/doctype/employee/employee_list.js`, `ifitwala_ed/hr/employee_access.py`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/api/file_access.py`.
  Test refs: `ifitwala_ed/hr/doctype/employee/test_employee.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`, `ifitwala_ed/api/test_organization_chart.py`, `ifitwala_ed/api/test_morning_brief.py`, `ifitwala_ed/patches/test_backfill_employee_user_links.py`, `ifitwala_ed/patches/test_backfill_employee_contact_links.py`, `ifitwala_ed/patches/test_backfill_employee_managed_access.py`, `ifitwala_ed/patches/test_clear_legacy_employee_active_list_filters.py`.
- `leave_management.md` - active canonical leave-domain contract for Desk and backend leave operations.
  Code refs: `ifitwala_ed/hr/doctype/leave_application/leave_application.py`, `ifitwala_ed/hr/doctype/leave_allocation/leave_allocation.py`, `ifitwala_ed/hr/doctype/leave_ledger_entry/leave_ledger_entry.py`, `ifitwala_ed/hr/leave_permissions.py`, `ifitwala_ed/hr/utils.py`, `ifitwala_ed/hooks.py`.
  Test refs: `ifitwala_ed/hr/test_leave_permissions.py`, `ifitwala_ed/hr/test_leave_utils.py`, `ifitwala_ed/hr/test_scheduler_dispatch.py`, `ifitwala_ed/hr/doctype/leave_application/test_leave_application.py`, `ifitwala_ed/patches/test_backfill_default_leave_types.py`.
- `professional_development_governance.md` - partial Phase 1 contract for Professional Development; core runtime exists, but lifecycle and hot-path test coverage is incomplete.
  Code refs: `ifitwala_ed/api/professional_development.py`, `ifitwala_ed/hr/professional_development_utils.py`, `ifitwala_ed/hr/professional_development_permissions.py`, `ifitwala_ed/hr/doctype/professional_development_request/professional_development_request.py`, `ifitwala_ed/ui-spa/src/pages/staff/ProfessionalDevelopment.vue`.
  Test refs: `ifitwala_ed/hr/test_professional_development_permissions.py`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/ProfessionalDevelopment.test.ts`.

Non-authoritative notes:

- `notes_and_audits.md` is a historical postmortem/audit log. It must not override the canonical docs above.

Open implementation notes:

- Professional Development needs broader backend lifecycle, API permission, and hot-path query regression coverage before its contract can be marked fully implemented.
- Legacy Employee list-filter cleanup and legacy `Designation.organization = "All Organizations"` remediation live in one-shot patches, not runtime compatibility code.

# Employee: Operational Notes

This note explains how `Employee` currently works in code, including:
- parent `Employee` document behavior (`employee.py`)
- child table `Employee History`
- linked `User` behavior
- employee picture flow (`employee.js` + `employee.py`)

## 1) Employee (parent DocType) behavior

Main controller: `ifitwala_ed/hr/doctype/employee/employee.py`

Core flow:
- `validate()` enforces invariants (dates, email format, status, reporting chain, preferred email, history validation).
- `on_update()` handles operational updates:
  - NestedSet update when `reports_to` changes.
  - cache reset and history synchronization.
  - staff calendar + primary contact synchronization.
  - role/authority helpers.
  - profile sync to linked `User` (strictly permission-gated).

The document acts as the authoritative HR staff record. It also drives access-related behavior through history/designation and linked user updates.

### 1.1 Staff Portal Holiday Resolution (Portal Calendar Contract)

For staff portal calendar reads, holiday resolution follows this server-owned precedence:

1. Resolve `Staff Calendar` by:
  - `employee_group` match
  - date-window overlap
  - nearest school in lineage (`employee.school` -> parent -> grandparent)
2. If no Staff Calendar holidays are available, fallback to `School Calendar Holidays` from the effective School Calendar resolver for the same date window.

Important:
- This fallback is lineage-based and deterministic.
- No sibling-school leakage is allowed.
- SPA clients must not guess school/AY fallback; they consume API payload only.

## 2) Employee History (child table) behavior

Child table: `Employee History` (`ifitwala_ed/hr/doctype/employee_history/employee_history.json`).

Key fields:
- position tuple context: `designation`, `organization`, `school`, `from_date`, `to_date`, `is_current`
- access context: `access_mode`, `role_profile`, `workspace_override`, `priority`

Rules from `Employee.validate_employee_history()` and sync logic:
- `from_date` is required and cannot be before employee joining date.
- `to_date` cannot be before `from_date`.
- overlap is blocked only for identical `(designation, organization, school)` tuples.
- `is_current` is derived from dates.
- history is auto-seeded/synchronized from parent tuple changes.

Access computation (`ifitwala_ed/hr/employee_access.py`) unions roles from current history rows and chooses workspace from highest priority row.

## 3) Linked User behavior

User creation entry point:
- Desk form button `create_user` in `employee.js`
- server method `create_user()` in `employee.py`

Current create flow:
- HR/System Manager authorization checks
- professional email required and uniqueness checks
- create `User`, link back to `Employee.user_id`, save employee

Role handling now follows managed sync:
- on employee save, `sync_user_access_from_employee` computes effective roles/workspace from employee history + designation defaults.
- designation-trigger path in `Employee._apply_designation_role()` now also handles first-time user linkage (`user_id` newly set), not only designation changes.
- role-management authorization includes `HR User`, `HR Manager`, `System Manager`, and `Administrator`.

## 4) Employee picture behavior (form + backend)

Frontend form logic:
- file: `ifitwala_ed/hr/doctype/employee/employee.js`
- image field is read-only and uses governed upload action.
- upload uses method `ifitwala_ed.utilities.governed_uploads.upload_employee_image`.
- after upload, form reloads and applies preferred image variants.

Backend linkage:
- file: `ifitwala_ed/hr/doctype/employee/employee.py`
- `update_user()` syncs profile fields to `User`, including `user_image` when applicable.
- missing file-on-disk situations are logged with structured error logging.

This keeps Employee image governance and User avatar synchronization aligned.

# Decisions

[2026-02-02] Decision:
We decided to treat `Designation.default_role_profile` and `Employee History.role_profile` as **Role names** (not Role Profile expansion) for fresh-install behavior.
Reason: current schema links these fields to `Role`; treating them as Role Profile caused empty role sync and failed provisioning.
Impact: role resolution is direct and predictable; no Role Profile backward-compatibility path is used.

[2026-02-02] Decision:
We decided to trigger designation-driven role sync when `Employee.user_id` is newly set (Create User flow), in addition to designation changes.
Reason: user creation from Employee often happens after designation is already set; designation-only trigger missed this case.
Impact: newly created users immediately receive designation/history-based managed roles.

[2026-02-02] Decision:
We decided to allow `HR User` in server-side role-management enforcement.
Reason: HR Users are valid operators for employee onboarding in current permission model.
Impact: HR User can execute the same controlled role-assignment automation as HR Manager/System Manager.

[2026-02-02] Decision:
We decided to grant pre-join baseline role access from designation when a user is created before joining date, while not applying workspace until active history exists.
Reason: onboarding requires immediate account usability, but workspace/default context should remain tied to active employment rows.
Impact: pre-join users get baseline role access; workspace is deferred until current history rows are active.

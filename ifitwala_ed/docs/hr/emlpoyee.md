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

Permission scope for `Employee`:
- `HR Manager` and `HR User` have scoped CRUD on Employee docs:
  - employees in their organization descendant scope
  - employees where `organization` is blank
- HR organization scope resolution uses user default `organization`, then `Global Defaults.default_organization`, and expands explicit `User Permission` grants on `Organization`; if none resolves, only unassigned-organization Employee rows are visible to HR.
- `Academic Admin` has read-only Employee access scoped to the user default school.
- `Employee` role has read-only access to their own Employee record only.

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
- on employee save, linked user defaults are aligned with Employee context when profile sync is allowed:
  - `organization` default from `Employee.organization`
  - `school` default from `Employee.school`
- on employee save, linked `User.enabled` is enforced from `Employee.employment_status`:
  - `Active` -> `enabled = 1`
  - any other status (`Temporary Leave`, `Suspended`, `Left`, or blank) -> `enabled = 0`
- role rows are preserved; status gating is enforced via user enable/disable state (no role stripping for non-active employees).
- routing policy resolves active employee status using `Employee.user_id` first, then an unambiguous active match on `employee_professional_email` to avoid false-negative staff routing when legacy user links are missing.
- at login, if a staff user has no active `Employee.user_id` link but exactly one active `Employee` row matches `employee_professional_email`, the system self-heals `user_id` and re-runs access sync.
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

[2026-02-18] Decision:
We decided that employee account access is strictly controlled by `Employee.employment_status`, and only `Active` keeps the linked `User` enabled.
Reason: non-active employees must not access either Desk or Portal while retaining historical role assignments.
Impact: the employee sync hook now toggles `User.enabled` automatically and blocks login/access for non-active employee statuses.

[2026-02-18] Decision:
We decided to self-heal missing active Employee-to-User links at login when there is exactly one unambiguous active match on `employee_professional_email`.
Reason: historical data can miss `Employee.user_id`, which produced false-negative staff redirects and sent active staff users to the student portal.
Impact: successful login now repairs the link and re-applies access sync before role-based portal redirect is resolved.

[2026-02-26] Decision:
We decided to keep `HR Manager` and `HR User` organization-subtree scoped, but include employees with empty `organization`.
Reason: HR must remain org-scoped by descendant inheritance, while still being able to triage/fix employee records that are missing organization assignment.
Impact: Employee permission hooks now allow HR access when `organization` is blank, and enforce subtree checks once organization is filled.

[2026-02-26] Decision:
We decided Employee tree root loading must surface visible scoped employees whose `reports_to` points to an out-of-scope manager.
Reason: strict `reports_to = ''` root filtering can render an empty tree for scoped users even when they have valid Employee visibility.
Impact: Employee tree root now treats "manager not visible in current scope" as a root candidate.

[2026-02-26] Decision:
We decided HR organization scope must also honor explicit `User Permission` grants on `Organization`.
Reason: role-authorized HR users can be scoped operationally through defaults and explicit org permissions without depending on Employee linkage.
Impact: Employee permission scope now unions descendants from default organization and descendants from explicit Organization User Permissions.

[2026-02-26] Decision:
We decided HR base-org resolution must not depend on linked Employee rows.
Reason: HR doctype scope is an operator scope concern and should be driven by organization defaults/permissions, not employee linkage status.
Impact: Employee linkage status no longer affects HR Employee doctype scope resolution.

[2026-02-26] Decision:
We decided HR base-org resolution falls back to `Global Defaults.default_organization` when user default `organization` is missing.
Reason: operational HR scope should still resolve to the organization tree baseline even when per-user defaults are incomplete.
Impact: HR scope can inherit organization descendants from global default organization without Employee-linkage dependency.

[2026-02-26] Decision:
We decided Employee save must sync linked user default `organization` from `Employee.organization` (same pattern as school default sync).
Reason: permissions use user/default organization scope; stale defaults can diverge from Employee form truth and produce unexpected scope behavior.
Impact: updating Employee organization now updates linked user default organization when profile sync is authorized.

[2026-02-26] Decision:
We decided Employee permission hooks enforce role-specific scope rules explicitly:
- HR roles: scoped CRUD to org descendants + blank organization rows
- Academic Admin: read-only on default school
- Employee: read-only own record
Reason: this is the required product contract and prevents implicit fallback behavior from granting or denying the wrong access.
Impact: list and form permissions are now consistent with the intended HR/academic/employee visibility model.

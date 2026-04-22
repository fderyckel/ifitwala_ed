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
  - staff calendar invalidation when the resolved holiday source changes.
  - role/authority helpers.
  - profile sync to linked `User` (strictly permission-gated).

The document acts as the authoritative HR staff record. It also drives access-related behavior through history/designation and linked user updates.

Permission scope for `Employee`:
- `HR Manager` and `HR User` have scoped CRUD on Employee docs:
  - employees in their organization descendant scope
  - employees where `organization` is blank
- HR organization scope resolution uses persisted defaults (`DefaultValue`) for user `organization`, then `Global Defaults.default_organization`, and expands explicit `User Permission` grants on `Organization`; if none resolves, only unassigned-organization Employee rows are visible to HR.
- `Academic Admin` has read-only Employee access with a two-step scope contract:
  - school scope resolves from the active `Employee.school` first; only users without an active Employee profile fall back to persisted user default `school`
  - when no school scope resolves, or the active Employee profile exists with a blank `school`, Employee visibility falls back to the user's organization descendant scope
- Academic Admin organization fallback resolves from active `Employee.organization`, then persisted user default `organization`, and unions explicit `User Permission` grants on `Organization`.
- `Employee` role has read-only access to their own Employee record only.
- Employee Desk list, tree, and report surfaces must follow the same scripted visibility scope and must not inject an implicit `employment_status = "Active"` filter.
- Employee Desk list load reconciles a legacy persisted `employment_status = "Active"` filter from older list defaults so inherited user state cannot silently narrow visibility after the contract change.

### 1.1 Staff Portal Holiday Resolution (Portal Calendar Contract)

For staff portal calendar reads, holiday resolution follows this server-owned precedence:

1. If `Employee.current_holiday_lis` resolves to a `Staff Calendar` that overlaps the requested date window, use that linked Staff Calendar.
2. Otherwise resolve `Staff Calendar` by:
  - `employee_group` match
  - date-window overlap
  - nearest school in lineage (`employee.school` -> parent -> grandparent)
3. Only if no `Staff Calendar` resolves for the employee, fallback to `School Calendar Holidays` from the effective School Calendar resolver for the same date window.

Important:
- Once a `Staff Calendar` resolves for an employee, `School Calendar` fallback does not widen or replace that employee holiday source for the same window.
- This fallback is lineage-based and deterministic.
- No sibling-school leakage is allowed.
- `Staff Calendar` writes re-sync affected `Employee.current_holiday_lis` rows so newly created or updated staff calendars take effect without requiring an Employee re-save.
- SPA clients must not guess school/AY fallback; they consume API payload only.
- If the logged-in user is the built-in `Administrator` account and no resolved active `Employee` record exists, employee-scoped calendar sources return empty instead of raising, while user-linked participant sources may still load.
- Other staff portal users without an active `Employee` record still raise the explicit permission error.

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
- immediately provision the contact graph so the user-linked `Contact` also carries an `Employee` dynamic link and `Employee.empl_primary_contact` points at that contact
- employee contact provisioning prefers `Contact.user = Employee.user_id`; if no contact exists yet, the create-user flow creates a minimal contact from employee identity data and then adds the `Employee` dynamic link

Role handling now follows managed sync:
- on employee save, `sync_user_access_from_employee` computes effective roles/workspace from employee history + designation defaults, and always includes the baseline `Employee` role for active staff users.
- when the access-sync trigger path adds new managed roles to the linked user, the Employee save flow shows an HR-facing dialog listing the roles that were added.
- on employee save, linked user defaults are always aligned with Employee context:
  - `organization` default from `Employee.organization`
  - `school` default from `Employee.school`
- on employee save, linked `User.enabled` is enforced from `Employee.employment_status`:
  - `Active` -> `enabled = 1`
  - any other status (`Temporary Leave`, `Suspended`, `Left`, or blank) -> `enabled = 0`
- employee save no longer repairs legacy contact-link drift; existing sites backfill missing `Contact.links -> Employee` rows and `empl_primary_contact` references through the one-shot patch `ifitwala_ed.patches.backfill_employee_contact_links`
- contact visibility for employee-linked contacts is server-scoped through `Contact.links -> Employee`:
  - `HR Manager` / `HR User`: read employee contacts in their organization scope
  - `Academic Admin` / `Academic Assistant`: read employee contacts in their effective school + descendant-school scope, where Academic Admin resolves school from the active Employee profile before persisted defaults
  - `Academic Admin` only: when no school scope resolves, or the active Employee profile exists with a blank `school`, employee-linked contact visibility falls back to organization descendant scope
  - `Employee`: read only the contact linked to their own employee record
- when `Employee.employment_status` is not `Active`, the linked `User` is disabled and all assigned role rows are removed.
- routing policy resolves active employee status using `Employee.user_id` first, then an unambiguous active match on `employee_professional_email` to avoid false-negative staff routing when legacy user links are missing.
- at login, if a staff user has no active `Employee.user_id` link but exactly one active `Employee` row matches `employee_professional_email`, the system self-heals `user_id` and re-runs access sync.
- if login cannot resolve any valid portal section after applying employee/admissions/student/guardian rules, the user is sent back to `/login` instead of being dropped onto `/hub/staff`.
- `Employee._apply_designation_role()` reruns managed access sync on every Employee update for linked users so imported or drifted accounts are repaired even when the Employee document itself did not change effective access fields.
- role-management authorization includes `HR User`, `HR Manager`, `System Manager`, and `Administrator`.

## 4) Employee picture behavior (form + backend)

Frontend form logic:
- file: `ifitwala_ed/hr/doctype/employee/employee.js`
- image field is read-only and uses governed upload action.
- upload uses method `ifitwala_ed.utilities.governed_uploads.upload_employee_image`.
- after upload, form reloads and applies preferred image variants from classified slots.

Backend linkage:
- file: `ifitwala_ed/hr/doctype/employee/employee.py`
- `ifitwala_ed.utilities.image_utils` owns canonical Employee image variant resolution and Drive-aware derivative scheduling.
- governed Employee uploads create one canonical governed `profile_image` Drive file.
- Drive generates the actual derivative artifacts for that file using derivative roles:
  - `thumb`
  - `card`
  - `viewer_preview`
- Ed still exposes compatibility variant keys:
  - `profile_image_thumb`
  - `profile_image_card`
  - `profile_image_medium`
  These are resolved from Drive derivative roles, not from separate governed derivative files.
- `Employee.employee_image` remains the latest canonical Employee image reference.
- consumers that need a smaller image must resolve the canonical compatibility variants instead of guessing file paths.
- `update_user()` syncs linked `User.user_image` from the preferred Employee variant (`thumb` first, then `card`, `medium`, original).

Current read consumers using canonical variant resolution:
- Employee form avatar (`employee.js`)
- Employee list refresh (`employee_list.js`)
- organization chart API (`ifitwala_ed/api/organization_chart.py`)
- morning brief staff birthdays (`ifitwala_ed/api/morning_brief.py`)
- website leadership provider (`ifitwala_ed/website/providers/leadership.py`)
- avatar-sized Employee surfaces request only Drive-managed derivatives and use a default avatar when no derivative is ready; they must not fall back to the original full-size image

Org chart visibility contract:
- the staff org chart defaults to `All Organizations`, not the viewer's base organization
- employee profile-image access for the org chart and Morning Brief staff-birthday surface is available to any authenticated active employee; base-organization scope does not gate those thumbnail/card reads
- avatar-sized Employee surfaces such as the org chart and Morning Brief birthday cards resolve Employee image derivatives in this order: `profile_image_thumb` -> `profile_image_card` -> `profile_image_medium`; they must not fall back to the original full-size image on those surfaces
- those compatibility variant keys resolve to Drive derivative roles (`thumb`, `card`, `viewer_preview`) on the current governed `profile_image` file
- when a governed Employee derivative is stored in `ifitwala_drive`, staff image consumers still resolve it through the named Employee file route, which now keeps Ed as the permission boundary for governed profile-image grants instead of relying on raw `Employee` DocType read access in Drive
- Morning Brief staff-birthday cards must resolve against the current governed Employee profile-image authority even if an older compatibility `File` id has rotated out; stale `file=` links are a bug
- changes to employee image display permissions must update the employee image route tests and the affected consumer contract tests in the same change

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
Reason: non-active employees must not access either Desk or Portal.
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

[2026-04-15] Decision:
We decided Employee list and tree surfaces must not add an implicit active-status filter on top of scripted visibility.
Reason: report view already exposes the full permitted Employee scope, and extra list/tree filtering created product drift where authorized staff were silently missing outside report view.
Impact: Employee list and tree now follow the same server-owned visibility contract as report view; status filtering is user-chosen, not hard-coded by the surface.

[2026-04-15] Decision:
We decided Employee list load must also remove a persisted legacy `employment_status = "Active"` filter when present.
Reason: some users can carry forward old list-state that was seeded by the previous hard-coded list default, which keeps list view narrower than report view even after the code contract changes.
Impact: Employee list now self-heals the inherited legacy status filter on load; users can still add a new status filter intentionally afterward.

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
Impact: updating Employee organization now updates linked user default organization on every save for linked users.

[2026-02-26] Decision:
We decided linked user default `organization`/`school` synchronization must not be blocked by profile-field sync authorization gates.
Reason: defaults drive permission scope and must stay consistent with Employee truth regardless of who performs the valid Employee save.
Impact: `Employee.on_update()` now always syncs user defaults for linked users, while `User` profile field sync remains permission-gated.

[2026-02-26] Decision:
We decided Employee permission hooks enforce role-specific scope rules explicitly:
- HR roles: scoped CRUD to org descendants + blank organization rows
- Academic Admin: read-only on default school, with organization-descendant fallback only when no default school is configured
- Employee: read-only own record
Reason: this is the required product contract and prevents implicit fallback behavior from granting or denying the wrong access.
Impact: list and form permissions are now consistent with the intended HR/academic/employee visibility model.

[2026-02-26] Decision:
We decided Employee permission scope resolution must read persisted defaults directly and avoid permission-time cache dependence.
Reason: stale default/cache state can cause transient list/form visibility mismatches after organization/school scope updates.
Impact: permission checks now resolve organization/school defaults from `DefaultValue` storage and compute descendant scope without permission-time cache reuse.

[2026-02-26] Decision:
We decided the `HR` workspace shortcut `Active Employee` must open `List` view (not `Tree`).
Reason: tree-root rendering can show only top-level scoped rows (e.g., "4 of 31"), which misrepresents scoped Employee visibility and creates operational confusion.
Impact: staff users opening `Active Employee` now land on full scoped list behavior consistent with report/image view results.

[2026-03-11] Decision:
We decided designation-driven role additions must show an operator-facing dialog during Employee save.
Reason: HR needs immediate feedback when the system adds managed roles to the linked user in the background.
Impact: designation change and first-time user-link flows now surface the exact newly added managed roles without notifying unrelated non-UI sync paths such as login self-heal.

[2026-03-20] Decision:
We decided Employee save must rerun managed user-access sync when effective access changes from `Employee History`, not only when the primary designation changes.
Reason: staff can hold multiple simultaneous designations, and secondary history rows can add server-owned roles and permissions.
Impact: adding or editing a current secondary designation row now updates the linked user's managed roles during the same Employee save flow.

[2026-03-24] Decision:
We decided active linked staff users must always carry the baseline `Employee` role in addition to current designation/history-managed roles, and non-active linked users must lose all roles.
Reason: imported or drifted staff accounts were missing the base `Employee` role, while non-active employees must not retain confidential-system access through stale roles.
Impact: every Employee save now reconciles the linked user role set; active users regain `Employee` plus current designation/history roles, and HR sees a save-time notice when non-active status strips the linked user's roles.

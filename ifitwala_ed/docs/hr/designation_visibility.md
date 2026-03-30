# Designation Visibility Contract

Status: Active

This note is the authoritative visibility contract for `Designation`.

## Rules

- `Designation.organization` is mandatory scope.
- `Designation.organization` must be a real organization. `All Organizations` is not allowed on Designation records.
- All employees can read a designation when the designation organization is the user's effective organization, one of its parents, or for HR operators one of its managed descendants.
- `Designation.school` is optional. When blank, the designation is organization-scoped only.
- When `Designation.school` is filled, the designation is visible only when the user's effective school is that school, one of its parents, or for HR operators one of its managed descendants.
- Users with no effective school scope are evaluated by organization scope only, except HR operators who can read school-scoped rows under their managed organization scope.
- HR operator roles (`HR Manager`, `HR User`) mutate designations by organization descendants: they can create/update/delete for their effective organization and all child organizations.
- HR operator visibility still includes legacy `All Organizations` rows so those records can be found and corrected.
- `Academic Admin` is read-only on `Designation`. It follows the same applicability visibility contract as other non-HR users and is not an operator-management role.
- When an HR operator has an effective school, school-scoped mutation is limited to that school and its descendants. HR operators with no effective school can still manage school-scoped rows inside their organization scope.
- Read visibility is enforced server-side through `permission_query_conditions`. Create/update/delete scope is enforced in the `Designation` controller. List JS must not own security.
- New Designation forms should prefill the current user's resolved organization when available instead of defaulting to `All Organizations`.
- Standard exact-match user-permission filtering on `Designation.organization` and `Designation.school` is disabled so the server-owned NestedSet contract can apply without excluding descendant-scoped operator rows.

## Effective User Scope Resolution

- Organization context resolves from active `Employee.organization`, then persisted user default `organization`.
- Explicit `User Permission` grants on `Organization` are included as additional organization anchors.
- School context resolves from active `Employee.school`, then persisted user default `school`.

## Designation Employee Lookup

Status: Implemented

Code refs:
- `ifitwala_ed/hr/doctype/designation/designation.py`
- `ifitwala_ed/hr/doctype/designation/designation.js`

Test refs:
- `ifitwala_ed/hr/doctype/designation/test_designation.py`

Rules:

- The Desk `Designation` form exposes a `View Employees` button for `HR Manager`, `HR User`, `System Manager`, and `Administrator`.
- The button is display-only UX. The client must call the server-owned whitelist method; it must not compute employee visibility in JS.
- Matching is the union of:
  - `Employee.designation == Designation.name`
  - current `Employee History` rows where `designation == Designation.name` and `is_current = 1`
- Results are deduplicated by employee. The response indicates whether the match came from the primary designation field, current history rows, or both.
- Result scope is enforced server-side by intersecting:
  - the designation's organization descendant scope
  - the operator's allowed organization descendant scope
  - when applicable, the designation's school descendant scope
  - when applicable, the operator's school descendant scope
- When the designation is organization-scoped (`Designation.school` blank), employees with blank school may still appear if they are inside the allowed organization scope.
- Silent empty dialogs are not allowed. When no employee is visible in scope, the modal must say so explicitly.

## Technical Notes (IT)

- Read visibility helpers and mutation guards live in `ifitwala_ed/hr/doctype/designation/designation.py`.
- Hook registration lives in `ifitwala_ed/hooks.py`.
- Regression coverage lives in `ifitwala_ed/hr/doctype/designation/test_designation.py`.
- The employee lookup endpoint is `get_scoped_designation_employees()` in `designation.py`.

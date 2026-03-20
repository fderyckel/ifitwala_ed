# Designation Visibility Contract

Status: Active

This note is the authoritative visibility contract for `Designation`.

## Rules

- `Designation.organization` is mandatory scope.
- `Designation.organization` must be a real organization. `All Organizations` is not allowed on Designation records.
- Non-operator readers see a designation when the designation organization is the user's effective organization or one of its parents.
- `Designation.school` is optional. When blank, the designation is organization-scoped only.
- For non-operator readers, when `Designation.school` is filled, the designation is visible only when the user's effective school is that school or one of its children.
- Users with no effective school scope are evaluated by organization scope only, even when the designation has a school filled.
- HR operator roles (`HR Manager`, `HR User`) manage designations by organization descendants: they can create/read/update/delete for their effective organization and all child organizations.
- HR operator visibility still includes legacy `All Organizations` rows so those records can be found and corrected.
- `Academic Admin` is read-only on `Designation`. It follows the same applicability visibility contract as other non-HR users and is not an operator-management role.
- HR operator management scope does not narrow on `Designation.school`; school applicability remains for non-HR read visibility.
- Visibility is enforced server-side through Frappe permission hooks. List JS must not own security.
- New Designation forms should prefill the current user's resolved organization when available instead of defaulting to `All Organizations`.
- Standard exact-match user-permission filtering on `Designation.organization` and `Designation.school` is disabled so the server-owned NestedSet contract can apply without excluding descendant-scoped operator rows.

## Effective User Scope Resolution

- Organization context resolves from active `Employee.organization`, then persisted user default `organization`.
- Explicit `User Permission` grants on `Organization` are included as additional organization anchors.
- School context resolves from active `Employee.school`, then persisted user default `school`.

## Technical Notes (IT)

- Permission hooks live in `ifitwala_ed/hr/doctype/designation/designation.py`.
- Hook registration lives in `ifitwala_ed/hooks.py`.
- Regression coverage lives in `ifitwala_ed/hr/doctype/designation/test_designation.py`.

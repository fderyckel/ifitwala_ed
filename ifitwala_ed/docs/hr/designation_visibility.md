# Designation Visibility Contract

Status: Active

This note is the authoritative visibility contract for `Designation`.

## Rules

- `Designation.organization` is mandatory scope. A designation is visible to users whose effective organization is that organization or a descendant organization.
- `Designation.organization = "All Organizations"` is visible to users with any resolved organization scope because `All Organizations` is the Organization NestedSet root.
- `Designation.school` is optional. When blank, the designation is organization-scoped only.
- When `Designation.school` is filled, the designation is visible only to users whose effective school is that school or a descendant school, but only if the user has an effective school scope.
- Users with no effective school scope are evaluated by organization scope only, even when the designation has a school filled. This supports parent-organization HR operators who oversee multiple schools.
- Visibility is enforced server-side through Frappe permission hooks. List JS must not own security.
- Standard exact-match user-permission filtering on `Designation.organization` and `Designation.school` is disabled so the server-owned NestedSet contract can apply without excluding ancestor-scoped rows such as `All Organizations`.

## Effective User Scope Resolution

- Organization context resolves from active `Employee.organization`, then persisted user default `organization`.
- Explicit `User Permission` grants on `Organization` are included as additional organization anchors.
- School context resolves from active `Employee.school`, then persisted user default `school`.

## Technical Notes (IT)

- Permission hooks live in `ifitwala_ed/hr/doctype/designation/designation.py`.
- Hook registration lives in `ifitwala_ed/hooks.py`.
- Regression coverage lives in `ifitwala_ed/hr/doctype/designation/test_designation.py`.

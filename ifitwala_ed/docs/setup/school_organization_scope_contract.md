# School and Organization Scope Contract

Status: Active

This document is the canonical developer-facing contract for `Organization` and `School` architecture, scope semantics, and inheritance utilities in Ifitwala Ed.

This note is authoritative for coding agents working on school-scoped or organization-scoped behavior.

## 1. Canonical Model

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/organization/organization.py`
- `ifitwala_ed/school_settings/doctype/school/school.py`
- `ifitwala_ed/docs/docs_md/organization.md`
- `ifitwala_ed/docs/docs_md/school.md`

Test refs:
- `ifitwala_ed/school_settings/doctype/school/test_school.py`
- organization controller tests are currently distributed across setup and feature-specific suites

Rules:

1. `Organization` is the legal and administrative tree. It is a `NestedSet` rooted in `parent_organization`.
2. `School` is the academic and operational tree. It is a separate `NestedSet` rooted in `parent_school`.
3. Every `School` belongs to exactly one `Organization`.
4. Parent and child `School` rows must belong to the same `Organization`; cross-organization school trees are forbidden.
5. Parent `Organization` and parent `School` rows must be group nodes (`is_group = 1`).
6. Organization-tree ancestry and school-tree ancestry are independent concepts and must not be conflated.
7. When a feature needs legal/admin scope, anchor it on `Organization`.
8. When a feature needs academic, campus, timetable, attendance, or student-operational scope, anchor it on `School`.

## 2. Scope and Inheritance Semantics

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/utilities/employee_utils.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/term/term.py`
- `ifitwala_ed/docs/nested_scope_contract.md`

Test refs:
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`

Rules:

1. Descendant scope means `self + descendants`.
2. Ancestor scope means `self + ancestors`, ordered nearest-first.
3. School visibility and school inheritance are not the same thing.
4. Descendant scope is the default for branch visibility, reporting scope, and parent-school selection behavior.
5. Ancestor scope is used only where the contract explicitly permits nearest-parent fallback.
6. Sibling isolation is mandatory for both `Organization` and `School`.
7. No helper may widen visibility across sibling branches.
8. If inheritance is allowed, nearest ancestor wins unless the owning contract says otherwise.
9. School inheritance must never silently cross organization boundaries.
10. Exact-match scope is allowed only when the owning feature contract explicitly rejects descendant or ancestor expansion.

## 3. Utility Ownership

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/utilities/employee_utils.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`

Test refs:
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`

Rules:

1. `utilities/tree_utils.py` is the generic NestedSet traversal layer.
2. `get_descendants_inclusive(doctype, node)` returns `self + descendants` for any NestedSet doctype.
3. `get_ancestors_inclusive(doctype, node)` returns `self + ancestors` for any NestedSet doctype.
4. `utilities/school_tree.py` is the school-specific compatibility and inheritance layer.
5. Use `get_descendant_schools()` and `get_ancestor_schools()` when the feature is explicitly school-scoped.
6. Use `get_school_lineage()` when nearest-first school ancestry is required.
7. Use `get_effective_record()` only for nearest-ancestor record resolution where the feature contract explicitly allows fallback by school and optionally organization.
8. Use `get_school_scope_for_academic_year()` only for Academic Year visibility semantics; it is not a generic scope helper.
9. `utilities/employee_utils.py` owns user base organization and school resolution from active `Employee` rows.
10. `employee_utils.get_descendant_organizations()` and `get_ancestor_organizations()` are the canonical organization-tree wrappers used outside governance policy code.
11. `employee_utils.get_schools_for_organization_scope()` is the canonical bridge from an already-authorized organization scope to linked schools.
12. `governance/policy_scope_utils.py` owns policy-specific scope resolution and nearest-scope override semantics.
13. `school_settings/school_settings_utils.py` owns school-settings visibility helpers and explicit calendar/term resolver helpers.

## 4. Approved Inheritance Patterns

Status: Implemented

Code refs:
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/term/term.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/governance/policy_utils.py`
- `ifitwala_ed/utilities/school_tree.py`

Test refs:
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`

Rules:

1. Branch visibility:
   - Use descendant school scope.
   - Example owner: `get_allowed_schools()` in `school_settings_utils.py`.
2. School-scoped Desk visibility with organization fallback:
   - Use descendant school scope when the active `Employee.school` resolves.
   - If an active `Employee` exists with a blank `school`, do not revive a stale default school.
   - Consumers that explicitly opt into organization fallback may widen only to schools whose `organization` is in the caller's organization descendant scope.
   - Resolve the authorized organization scope first, then call `employee_utils.get_schools_for_organization_scope()`; do not repeat the raw `School.organization in (...)` query in each feature.
   - Example owners: `employee_utils.get_user_visible_schools()`, `Program Offering`, `Program Enrollment`, Org Communication, policy communication/signature staff-context helpers, and HR Designation school-scope helpers.
2. Nearest ancestor fallback for term/calendar sources:
   - Use school lineage or ancestor helpers.
   - Example owners: `resolve_terms_for_school_calendar()` and `get_schools_per_academic_year_for_terms()`.
3. Academic Year scope:
   - Prefer subtree scope when visible Academic Years exist in the branch.
   - Otherwise fallback to the nearest ancestor school with visible Academic Years.
   - Canonical owner: `get_school_scope_for_academic_year()`.
4. Policy scope:
   - Organization policy scope may apply from ancestor organization to descendant organization.
   - School policy scope may apply from ancestor school to descendant school within the same lineage.
   - Nearest matching override wins for the same policy key.
   - Canonical owner: `policy_scope_utils.py` plus `policy_utils.py`.
5. Effective record lookup:
   - Allowed only for contracts that explicitly choose nearest-record inheritance instead of explicit scope filtering.
   - Canonical owner: `school_tree.get_effective_record()`.

## 5. Disallowed Patterns

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/docs/nested_scope_contract.md`

Test refs:
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`

Rules:

1. Do not recompute school or organization subtree math ad hoc in each API or report.
2. Do not mix organization descendants with school descendants in one synthetic scope list.
3. Do not use organization ancestry as a proxy for school ancestry.
4. Do not silently widen school scope to sibling schools because they share a parent organization.
5. Do not implement inheritance by fetching global rows and then probing `exists()` in nested loops.
6. Do not cache permission-sensitive scope without keys that include the relevant node and scope type.
7. Do not treat `get_allowed_schools()` as a calendar resolver or policy resolver; it is visibility-only.
8. Do not use `get_effective_record()` where the feature contract requires explicit local rows only.

## 6. Consumer Map

Status: Implemented

Code refs:
- `ifitwala_ed/setup/doctype/organization/organization.py`
- `ifitwala_ed/school_settings/doctype/school/school.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/school_settings/doctype/term/term.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/api/student_overview_dashboard.py`
- `ifitwala_ed/api/admission_cockpit.py`
- `ifitwala_ed/api/room_utilization.py`
- `ifitwala_ed/api/calendar_quick_create.py`

Test refs:
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/api/test_room_utilization.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Organization tree integrity | `Organization` controller | `setup/doctype/organization/organization.py` | distributed |
| School tree integrity | `School` controller | `school_settings/doctype/school/school.py` | `school_settings/doctype/school/test_school.py` |
| Generic tree traversal | `tree_utils` | `utilities/tree_utils.py` | `utilities/test_tree_utils.py` |
| School-specific lineage and fallback | `school_tree` | `utilities/school_tree.py` | `utilities/test_school_tree.py` |
| User base org/school resolution | `employee_utils` | `utilities/employee_utils.py` | indirect coverage in policy and feature tests |
| Staff Desk school visibility with org fallback | `employee_utils` + feature scripted permissions/context helpers | `utilities/employee_utils.py`, `schedule/doctype/program_offering/program_offering.py`, `schedule/doctype/program_enrollment/program_enrollment.py`, `api/admission_cockpit.py`, `api/enrollment_analytics.py`, `api/org_comm_utils.py`, `api/org_communication_archive.py`, `api/org_communication_quick_create.py`, `api/policy_communication.py`, `api/policy_signature.py`, `hr/doctype/designation/designation.py`, `setup/doctype/org_communication/org_communication.py` | `utilities/test_employee_utils.py`, `schedule/test_program_scope_permissions_unit.py` |
| Policy organization/school inheritance | `policy_scope_utils` | `governance/policy_scope_utils.py` | `governance/test_policy_scope_inheritance.py` |
| School-settings visibility and calendar resolution | `school_settings_utils` | `school_settings/school_settings_utils.py` | `school_settings/doctype/term/test_term.py`, `utilities/test_school_tree.py` |
| Term branch visibility with nearest ancestor fallback | `Term` scripted permissions | `school_settings/doctype/term/term.py` | `school_settings/doctype/term/test_term.py` |

## 7. Coding-Agent Guidance

Status: Implemented

Code refs:
- `ifitwala_ed/utilities/tree_utils.py`
- `ifitwala_ed/utilities/school_tree.py`
- `ifitwala_ed/utilities/employee_utils.py`
- `ifitwala_ed/governance/policy_scope_utils.py`
- `ifitwala_ed/school_settings/school_settings_utils.py`
- `ifitwala_ed/docs/nested_scope_contract.md`

Test refs:
- `ifitwala_ed/utilities/test_tree_utils.py`
- `ifitwala_ed/utilities/test_school_tree.py`
- `ifitwala_ed/governance/test_policy_scope_inheritance.py`
- `ifitwala_ed/school_settings/doctype/term/test_term.py`

Rules:

1. Choose the helper based on contract type, not convenience.
2. If the feature is about visibility, start with descendant scope and explicit intersection.
3. If the feature is about nearest inherited source, use nearest-first lineage helpers and stop at the first match.
4. If the feature is policy-specific, use `policy_scope_utils.py`; do not duplicate policy scope math elsewhere.
5. If the feature is school-settings-specific, use `school_settings_utils.py` or extend it instead of inventing a new resolver.
6. If you need a new inheritance pattern, document it here and in the owning feature contract before shipping behavior changes.
7. When code and old docs disagree, this note plus the current code and test refs above take precedence for developer implementation work.

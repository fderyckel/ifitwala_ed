# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_link_to_form
from frappe.utils.nestedset import get_ancestors_of

from ifitwala_ed.utilities.employee_utils import (
    get_schools_for_organization_scope,
    get_user_base_org,
    get_user_base_school,
)
from ifitwala_ed.utilities.tree_utils import get_ancestors_inclusive, get_descendants_inclusive

ALL_ORGANIZATIONS = "All Organizations"
OPERATOR_SCOPE_ROLES = {"HR Manager", "HR User"}
DESIGNATION_EMPLOYEE_LOOKUP_ROLES = OPERATOR_SCOPE_ROLES | {"System Manager"}


class Designation(Document):
    def validate(self):
        self._assert_mutation_scope_allowed(action="save")
        self.validate_organization_scope()
        self.validate_reports_to_hierarchy()
        self.validate_default_role()

    def on_trash(self):
        self._assert_mutation_scope_allowed(action="delete")

    def validate_organization_scope(self):
        organization = cstr(self.organization).strip()
        if not organization:
            frappe.throw(_("Organization is required."))

        if organization == ALL_ORGANIZATIONS:
            frappe.throw(
                _(
                    "Designation cannot use All Organizations. "
                    "Please select the actual organization that owns this designation."
                )
            )

    def validate_reports_to_hierarchy(self):
        if not self.reports_to:
            return

        # Step 1: Prevent self-reporting
        if self.reports_to == self.name:
            frappe.throw(
                _("A designation cannot report to itself: {designation}.").format(
                    designation=get_link_to_form("Designation", self.name)
                )
            )

        # Step 2: Prevent direct loops (A → B → A)
        reports_to_data = frappe.db.get_value(
            "Designation", self.reports_to, ["organization", "reports_to", "archived"], as_dict=True
        )

        # Prevent direct loop
        if reports_to_data.get("reports_to") == self.name:
            frappe.throw(
                _(
                    "The selected 'Reports to' designation {reports_to} cannot report back to {designation}, creating a direct loop."
                ).format(
                    reports_to=get_link_to_form("Designation", self.reports_to),
                    designation=get_link_to_form("Designation", self.name),
                )
            )

        # Step 3: Organizational Lineage Check (Using Organization NestedSet)
        current_org = self.organization
        reports_to_org = reports_to_data.get("organization")

        # Fetch all parent organizations for the current organization
        valid_orgs = get_ancestors_of("Organization", current_org) or []
        valid_orgs.append(current_org)  # Include the current organization itself

        if reports_to_org not in valid_orgs:
            frappe.throw(
                _(
                    "This designation {reports_to} is reporting to a designation that belongs to a different organizational lineage than the current designation's organization '{organization}' ({organization_link})."
                ).format(
                    reports_to=get_link_to_form("Designation", self.reports_to),
                    organization=current_org,
                    organization_link=get_link_to_form("Organization", current_org),
                )
            )

        # Step 4: Prevent reporting to an archived designation
        if reports_to_data.get("archived"):
            frappe.throw(
                _(
                    "The selected 'Reports to' designation {reports_to} is archived and cannot be assigned as a supervisor."
                ).format(reports_to=get_link_to_form("Designation", self.reports_to))
            )

        # Step 5: Indirect Loop Prevention (Multi-Level)
        if self._check_indirect_loop(self.name, self.reports_to):
            frappe.throw(
                _(
                    "The selected 'Reports to' designation {reports_to} would create a circular reporting loop with {designation}."
                ).format(
                    reports_to=get_link_to_form("Designation", self.reports_to),
                    designation=get_link_to_form("Designation", self.name),
                )
            )

    def validate_default_role(self):
        if not self.default_role_profile:
            return

        disallowed = {"System Manager", "Administrator", "Guest", "All"}
        if self.default_role_profile in disallowed:
            frappe.throw(_("This role cannot be assigned via Designation."))

    def _assert_mutation_scope_allowed(self, action: str, user: str | None = None) -> None:
        user = user or frappe.session.user
        if not user or user == "Guest":
            frappe.throw(
                _("You do not have permission to {action} this designation.").format(action=action),
                frappe.PermissionError,
            )

        roles = set(frappe.get_roles(user))
        if user == "Administrator" or "System Manager" in roles:
            return

        if not roles & OPERATOR_SCOPE_ROLES:
            frappe.throw(_("Only HR can {action} designations.").format(action=action), frappe.PermissionError)

        designation_org = cstr(self.organization).strip()
        visible_orgs = set(_resolve_designation_operator_org_scope(user))
        if not designation_org or designation_org not in visible_orgs:
            frappe.throw(
                _("You can only {action} designations within your organization scope.").format(action=action),
                frappe.PermissionError,
            )

        designation_school = cstr(self.school).strip()
        if not designation_school:
            return

        school_scope = set(_resolve_designation_operator_school_write_scope(user, org_scope=sorted(visible_orgs)))
        if designation_school not in school_scope:
            frappe.throw(
                _("You can only {action} school-scoped designations within your school scope.").format(action=action),
                frappe.PermissionError,
            )

    def _check_indirect_loop(self, start_designation, target_designation):
        """
        Recursively check if assigning the target_designation as a supervisor
        would create a multi-level loop.
        """
        current = target_designation

        while current:
            # Get the next level up
            next_supervisor = frappe.db.get_value("Designation", current, "reports_to")

            # If we loop back to the start, we have a problem
            if next_supervisor == start_designation:
                return True

            # Move up the hierarchy
            current = next_supervisor

        return False


@frappe.whitelist()
def get_valid_parent_organizations(organization):
    """
    Return the full parent hierarchy for a given organization,
    including the organization itself.
    """
    if not organization:
        frappe.throw(_("Organization is required"))

    # Fetch all parent organizations
    valid_orgs = get_ancestors_of("Organization", organization) or []
    valid_orgs.append(organization)  # Include the current organization itself

    return valid_orgs


@frappe.whitelist()
def get_assignable_roles(doctype, txt, searchfield, start, page_len, filters):
    # Curated Role list for Link field dropdown (search + pagination)

    excluded_roles = ("System Manager", "Administrator", "Guest", "All")

    # Frappe passes these as strings sometimes
    start = int(start or 0)
    page_len = int(page_len or 20)
    txt = (txt or "").strip()

    role_filters = [["name", "not in", excluded_roles]]
    if txt:
        role_filters.append(["name", "like", f"%{txt}%"])

    return frappe.db.get_all(
        "Role",
        filters=role_filters,
        fields=["name"],
        order_by="name asc",
        limit_start=start,
        limit=page_len,
        as_list=True,  # return list-of-lists for link queries
    )


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return None

    visible_orgs = _resolve_designation_read_org_scope(user, roles=roles)
    if not visible_orgs:
        return "1=0"

    escaped_orgs = ", ".join(frappe.db.escape(org) for org in visible_orgs)
    org_condition = f"`tabDesignation`.`organization` IN ({escaped_orgs})"

    visible_schools = _resolve_designation_read_school_scope(user, roles=roles, org_scope=visible_orgs)
    if visible_schools is None:
        school_condition = "1=1"
    elif not visible_schools:
        school_condition = "1=0"
    else:
        escaped_schools = ", ".join(frappe.db.escape(school) for school in visible_schools)
        school_condition = (
            f"(IFNULL(`tabDesignation`.`school`, '') = '' OR `tabDesignation`.`school` IN ({escaped_schools}))"
        )

    return f"({org_condition} AND {school_condition})"


def _can_user_read_designation(doc, user: str) -> bool:
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return True

    designation_org = cstr(getattr(doc, "organization", "")).strip()
    if not designation_org:
        return False

    visible_orgs = set(_resolve_designation_read_org_scope(user, roles=roles))
    if designation_org not in visible_orgs:
        return False

    designation_school = cstr(getattr(doc, "school", "")).strip()
    if not designation_school:
        return True

    visible_schools = _resolve_designation_read_school_scope(user, roles=roles, org_scope=sorted(visible_orgs))
    if visible_schools is None:
        return True
    return designation_school in set(visible_schools)


def _resolve_designation_read_org_scope(user: str, *, roles: set[str] | None = None) -> list[str]:
    roles = roles or set(frappe.get_roles(user))
    visible_orgs: set[str] = set()

    for org in _get_effective_user_organizations(user):
        visible_orgs.update(item for item in _get_ancestor_organizations_uncached(org) if item != ALL_ORGANIZATIONS)
        if roles & OPERATOR_SCOPE_ROLES:
            visible_orgs.update(item for item in _get_descendant_organizations_uncached(org) if item)

    return sorted(visible_orgs)


def _resolve_designation_read_school_scope(
    user: str,
    *,
    roles: set[str] | None = None,
    org_scope: list[str] | None = None,
) -> list[str] | None:
    roles = roles or set(frappe.get_roles(user))
    school = _resolve_user_base_school(user)
    if not school:
        if roles & OPERATOR_SCOPE_ROLES:
            scoped_orgs = [item for item in (org_scope or []) if item and item != ALL_ORGANIZATIONS]
            return _get_schools_for_organizations(scoped_orgs)
        return None

    visible_schools = set(_get_ancestor_schools_uncached(school))
    if roles & OPERATOR_SCOPE_ROLES:
        visible_schools.update(_get_descendant_schools_uncached(school))
    return sorted(visible_schools)


def _resolve_designation_applicable_org_scope(user: str) -> list[str]:
    visible_orgs: set[str] = set()

    for org in _get_effective_user_organizations(user):
        visible_orgs.update(item for item in _get_ancestor_organizations_uncached(org) if item != ALL_ORGANIZATIONS)

    return sorted(visible_orgs)


def _resolve_designation_operator_org_scope(user: str) -> list[str]:
    visible_orgs: set[str] = set()

    for org in _get_effective_user_organizations(user):
        visible_orgs.update(_get_descendant_organizations_uncached(org))

    return sorted(visible_orgs)


def _resolve_designation_school_scope(user: str) -> list[str] | None:
    school = _resolve_user_base_school(user)
    if not school:
        return None
    return _get_ancestor_schools_uncached(school)


def _resolve_designation_operator_school_write_scope(user: str, *, org_scope: list[str]) -> list[str]:
    school = _resolve_user_base_school(user)
    if school:
        return _get_descendant_schools_uncached(school)
    scoped_orgs = [item for item in org_scope if item and item != ALL_ORGANIZATIONS]
    return _get_schools_for_organizations(scoped_orgs)


def _get_effective_user_organizations(user: str) -> list[str]:
    orgs: set[str] = set()

    base_org = _resolve_user_base_org(user)
    if base_org:
        orgs.add(base_org)

    explicit_orgs = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Organization"},
        pluck="for_value",
    )
    for org in explicit_orgs or []:
        org_name = cstr(org).strip()
        if org_name:
            orgs.add(org_name)

    return sorted(orgs)


def _resolve_user_base_org(user: str) -> str | None:
    return (get_user_base_org(user) or "").strip() or (_get_user_default_from_db(user, "organization") or None)


def _resolve_user_base_school(user: str) -> str | None:
    return (get_user_base_school(user) or "").strip() or (_get_user_default_from_db(user, "school") or None)


def _get_user_default_from_db(user: str, key: str) -> str | None:
    rows = frappe.get_all(
        "DefaultValue",
        filters={"parent": user, "defkey": key},
        fields=["defvalue"],
        order_by="modified desc, creation desc, name desc",
        limit=1,
    )
    if not rows:
        return None
    return cstr(rows[0].get("defvalue")).strip() or None


def _get_ancestor_organizations_uncached(org: str) -> list[str]:
    org = cstr(org).strip()
    if not org:
        return []
    return [cstr(item).strip() for item in (get_ancestors_inclusive("Organization", org) or []) if cstr(item).strip()]


def _get_ancestor_schools_uncached(school: str) -> list[str]:
    school = cstr(school).strip()
    if not school:
        return []
    return [cstr(item).strip() for item in (get_ancestors_inclusive("School", school) or []) if cstr(item).strip()]


def _get_descendant_organizations_uncached(org: str) -> list[str]:
    org = cstr(org).strip()
    if not org:
        return []
    return [cstr(item).strip() for item in (get_descendants_inclusive("Organization", org) or []) if cstr(item).strip()]


@frappe.whitelist()
def get_default_designation_organization() -> str | None:
    return _resolve_user_base_org(frappe.session.user)


@frappe.whitelist()
def get_scoped_designation_employees(designation: str) -> dict:
    designation_name = cstr(designation).strip()
    if not designation_name:
        frappe.throw(_("Designation is required."))

    user = frappe.session.user
    designation_doc = frappe.get_doc("Designation", designation_name)
    _assert_designation_employee_lookup_allowed(designation_doc, user)

    org_scope = _resolve_designation_employee_org_scope(designation_doc, user)
    school_scope, allow_blank_school = _resolve_designation_employee_school_scope(
        designation_doc,
        user,
        org_scope=org_scope,
    )

    if not org_scope or (school_scope == [] and not allow_blank_school):
        return {
            "designation": designation_doc.name,
            "designation_label": cstr(designation_doc.designation_name).strip() or designation_doc.name,
            "employees": [],
            "count": 0,
        }

    primary_rows = _get_primary_designation_employee_matches(
        designation=designation_doc.name,
        org_scope=org_scope,
        school_scope=school_scope,
        allow_blank_school=allow_blank_school,
    )
    history_rows = _get_current_history_designation_matches(
        designation=designation_doc.name,
        org_scope=org_scope,
        school_scope=school_scope,
        allow_blank_school=allow_blank_school,
    )

    employees = _merge_designation_employee_matches(primary_rows, history_rows)
    return {
        "designation": designation_doc.name,
        "designation_label": cstr(designation_doc.designation_name).strip() or designation_doc.name,
        "employees": employees,
        "count": len(employees),
    }


def _assert_designation_employee_lookup_allowed(designation_doc, user: str) -> None:
    roles = set(frappe.get_roles(user))
    if user != "Administrator" and not (roles & DESIGNATION_EMPLOYEE_LOOKUP_ROLES):
        frappe.throw(
            _("Only HR or System Manager can view employees for a designation."),
            frappe.PermissionError,
        )

    if not _can_user_read_designation(designation_doc, user):
        frappe.throw(
            _("You do not have access to this designation."),
            frappe.PermissionError,
        )


def _resolve_designation_employee_org_scope(designation_doc, user: str) -> list[str]:
    designation_orgs = [
        item
        for item in _get_descendant_organizations_uncached(cstr(getattr(designation_doc, "organization", "")).strip())
        if item and item != ALL_ORGANIZATIONS
    ]
    if not designation_orgs:
        return []

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or "System Manager" in roles:
        return designation_orgs

    operator_scope = {
        item for item in _resolve_designation_operator_org_scope(user) if item and item != ALL_ORGANIZATIONS
    }
    return sorted(set(designation_orgs) & operator_scope)


def _resolve_designation_employee_school_scope(
    designation_doc,
    user: str,
    *,
    org_scope: list[str],
) -> tuple[list[str] | None, bool]:
    roles = set(frappe.get_roles(user))
    user_school = _resolve_user_base_school(user)

    if user == "Administrator" or "System Manager" in roles:
        user_schools = None
    elif user_school:
        user_schools = _get_descendant_schools_uncached(user_school)
    else:
        user_schools = _get_schools_for_organizations(org_scope)

    designation_school = cstr(getattr(designation_doc, "school", "")).strip()
    if designation_school:
        designation_schools = _get_descendant_schools_uncached(designation_school)
        if user_schools is None:
            return designation_schools, False
        return sorted(set(user_schools) & set(designation_schools)), False

    return user_schools, True


def _get_descendant_schools_uncached(school: str) -> list[str]:
    school = cstr(school).strip()
    if not school:
        return []
    return [cstr(item).strip() for item in (get_descendants_inclusive("School", school) or []) if cstr(item).strip()]


def _get_schools_for_organizations(org_scope: list[str]) -> list[str]:
    return get_schools_for_organization_scope(org_scope)


def _build_scope_conditions(
    *,
    organization_expr: str,
    school_expr: str,
    org_scope: list[str],
    school_scope: list[str] | None,
    allow_blank_school: bool,
) -> tuple[list[str], list]:
    conditions: list[str] = []
    params: list = []

    if org_scope:
        org_placeholders = ", ".join(["%s"] * len(org_scope))
        conditions.append(f"{organization_expr} IN ({org_placeholders})")
        params.extend(org_scope)

    if school_scope is None:
        return conditions, params

    if school_scope:
        school_placeholders = ", ".join(["%s"] * len(school_scope))
        if allow_blank_school:
            conditions.append(f"({school_expr} = '' OR {school_expr} IN ({school_placeholders}))")
        else:
            conditions.append(f"{school_expr} IN ({school_placeholders})")
        params.extend(school_scope)
        return conditions, params

    if allow_blank_school:
        conditions.append(f"{school_expr} = ''")
    else:
        conditions.append("1=0")
    return conditions, params


def _get_primary_designation_employee_matches(
    *,
    designation: str,
    org_scope: list[str],
    school_scope: list[str] | None,
    allow_blank_school: bool,
) -> list[dict]:
    conditions = [
        "emp.employment_status = %s",
        "emp.designation = %s",
    ]
    params: list = ["Active", designation]

    scope_conditions, scope_params = _build_scope_conditions(
        organization_expr="COALESCE(NULLIF(emp.organization, ''), '')",
        school_expr="COALESCE(NULLIF(emp.school, ''), '')",
        org_scope=org_scope,
        school_scope=school_scope,
        allow_blank_school=allow_blank_school,
    )
    conditions.extend(scope_conditions)
    params.extend(scope_params)

    query = f"""
        SELECT
            emp.name AS employee,
            emp.employee_full_name,
            emp.user_id,
            COALESCE(NULLIF(emp.organization, ''), '') AS organization,
            COALESCE(NULLIF(emp.school, ''), '') AS school
        FROM `tabEmployee` emp
        WHERE {" AND ".join(conditions)}
        ORDER BY
            COALESCE(NULLIF(emp.organization, ''), '') ASC,
            COALESCE(NULLIF(emp.school, ''), '') ASC,
            COALESCE(NULLIF(emp.employee_full_name, ''), emp.name) ASC,
            emp.name ASC
    """
    return frappe.db.sql(query, params, as_dict=True) or []


def _get_current_history_designation_matches(
    *,
    designation: str,
    org_scope: list[str],
    school_scope: list[str] | None,
    allow_blank_school: bool,
) -> list[dict]:
    assignment_org = "COALESCE(NULLIF(hist.organization, ''), COALESCE(NULLIF(emp.organization, ''), ''))"
    assignment_school = "COALESCE(NULLIF(hist.school, ''), COALESCE(NULLIF(emp.school, ''), ''))"

    conditions = [
        "emp.employment_status = %s",
        "hist.parenttype = %s",
        "hist.designation = %s",
        "COALESCE(hist.is_current, 0) = 1",
    ]
    params: list = ["Active", "Employee", designation]

    scope_conditions, scope_params = _build_scope_conditions(
        organization_expr=assignment_org,
        school_expr=assignment_school,
        org_scope=org_scope,
        school_scope=school_scope,
        allow_blank_school=allow_blank_school,
    )
    conditions.extend(scope_conditions)
    params.extend(scope_params)

    query = f"""
        SELECT
            emp.name AS employee,
            emp.employee_full_name,
            emp.user_id,
            {assignment_org} AS organization,
            {assignment_school} AS school,
            hist.from_date
        FROM `tabEmployee History` hist
        INNER JOIN `tabEmployee` emp
            ON emp.name = hist.parent
        WHERE {" AND ".join(conditions)}
        ORDER BY
            {assignment_org} ASC,
            {assignment_school} ASC,
            COALESCE(NULLIF(emp.employee_full_name, ''), emp.name) ASC,
            emp.name ASC,
            hist.from_date ASC
    """
    return frappe.db.sql(query, params, as_dict=True) or []


def _merge_designation_employee_matches(primary_rows: list[dict], history_rows: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}

    def ensure_entry(row: dict) -> dict:
        employee_name = cstr(row.get("employee")).strip()
        if employee_name not in merged:
            merged[employee_name] = {
                "employee": employee_name,
                "employee_full_name": cstr(row.get("employee_full_name")).strip() or employee_name,
                "user_id": cstr(row.get("user_id")).strip() or None,
                "organizations": set(),
                "schools": set(),
                "match_sources": set(),
                "history_matches": [],
            }
        entry = merged[employee_name]
        organization = cstr(row.get("organization")).strip()
        school = cstr(row.get("school")).strip()
        if organization:
            entry["organizations"].add(organization)
        if school:
            entry["schools"].add(school)
        return entry

    for row in primary_rows:
        entry = ensure_entry(row)
        entry["match_sources"].add("Primary designation")

    for row in history_rows:
        entry = ensure_entry(row)
        entry["match_sources"].add("Current history")
        history_match = {
            "organization": cstr(row.get("organization")).strip() or None,
            "school": cstr(row.get("school")).strip() or None,
            "from_date": row.get("from_date"),
        }
        if history_match not in entry["history_matches"]:
            entry["history_matches"].append(history_match)

    employees = []
    for entry in merged.values():
        organizations = sorted(entry.pop("organizations"))
        schools = sorted(entry.pop("schools"))
        history_matches = sorted(
            entry["history_matches"],
            key=lambda item: (
                cstr(item.get("organization")).strip(),
                cstr(item.get("school")).strip(),
                cstr(item.get("from_date")).strip(),
            ),
        )
        employees.append(
            {
                **entry,
                "organizations": organizations,
                "schools": schools,
                "match_sources": sorted(entry["match_sources"]),
                "history_matches": history_matches,
            }
        )

    employees.sort(
        key=lambda item: (
            cstr(item.get("employee_full_name")).strip().lower(),
            cstr(item.get("employee")).strip(),
        )
    )
    return employees

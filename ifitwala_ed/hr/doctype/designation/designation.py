# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_link_to_form
from frappe.utils.nestedset import get_ancestors_of

from ifitwala_ed.utilities.employee_utils import get_user_base_org, get_user_base_school
from ifitwala_ed.utilities.tree_utils import get_ancestors_inclusive

READ_LIKE_PERMS = {"read", "report", "export", "print"}
SCOPED_DOC_PERMS = READ_LIKE_PERMS | {"write", "delete", "submit", "cancel", "amend"}
ALL_ORGANIZATIONS = "All Organizations"


class Designation(Document):
    def validate(self):
        self.validate_reports_to_hierarchy()
        self.validate_default_role()

    def validate_reports_to_hierarchy(self):
        if not self.reports_to:
            return

        # Step 1: Prevent self-reporting
        if self.reports_to == self.name:
            frappe.throw(_(f"A designation cannot report to itself: {get_link_to_form('Designation', self.name)}."))

        # Step 2: Prevent direct loops (A → B → A)
        reports_to_data = frappe.db.get_value(
            "Designation", self.reports_to, ["organization", "reports_to", "archived"], as_dict=True
        )

        # Prevent direct loop
        if reports_to_data.get("reports_to") == self.name:
            frappe.throw(
                _(
                    f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} cannot report back to {get_link_to_form('Designation', self.name)}, creating a direct loop."
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
                    f"This designation {get_link_to_form('Designation', self.reports_to)} is reporting to a designation that belongs to a different organizational lineage than the current designation's organization '{current_org}' ({get_link_to_form('Organization', current_org)})."
                )
            )

        # Step 4: Prevent reporting to an archived designation
        if reports_to_data.get("archived"):
            frappe.throw(
                _(
                    f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} is archived and cannot be assigned as a supervisor."
                )
            )

        # Step 5: Indirect Loop Prevention (Multi-Level)
        if self._check_indirect_loop(self.name, self.reports_to):
            frappe.throw(
                _(
                    f"The selected 'Reports to' designation {get_link_to_form('Designation', self.reports_to)} would create a circular reporting loop with {get_link_to_form('Designation', self.name)}."
                )
            )

    def validate_default_role(self):
        if not self.default_role_profile:
            return

        disallowed = {"System Manager", "Administrator", "Guest", "All"}
        if self.default_role_profile in disallowed:
            frappe.throw(_("This role cannot be assigned via Designation."))

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
        limit_page_length=page_len,
        as_list=True,  # return list-of-lists for link queries
    )


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    visible_orgs = _resolve_designation_org_scope(user)
    if not visible_orgs:
        return "1=0"

    escaped_orgs = ", ".join(frappe.db.escape(org) for org in visible_orgs)
    org_condition = f"`tabDesignation`.`organization` IN ({escaped_orgs})"

    visible_schools = _resolve_designation_school_scope(user)
    if not visible_schools:
        school_condition = "IFNULL(`tabDesignation`.`school`, '') = ''"
    else:
        escaped_schools = ", ".join(frappe.db.escape(school) for school in visible_schools)
        school_condition = (
            f"(IFNULL(`tabDesignation`.`school`, '') = '' OR `tabDesignation`.`school` IN ({escaped_schools}))"
        )

    return f"({org_condition} AND {school_condition})"


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    if (ptype or "read") not in SCOPED_DOC_PERMS:
        return None

    designation_org = cstr(getattr(doc, "organization", "")).strip()
    if not designation_org:
        return False

    visible_orgs = set(_resolve_designation_org_scope(user))
    if designation_org not in visible_orgs:
        return False

    designation_school = cstr(getattr(doc, "school", "")).strip()
    if not designation_school:
        return True

    visible_schools = set(_resolve_designation_school_scope(user))
    return designation_school in visible_schools


def _resolve_designation_org_scope(user: str) -> list[str]:
    visible_orgs: set[str] = set()

    for org in _get_effective_user_organizations(user):
        visible_orgs.update(_get_ancestor_organizations_uncached(org))

    return sorted(visible_orgs)


def _resolve_designation_school_scope(user: str) -> list[str]:
    school = _resolve_user_base_school(user)
    if not school:
        return []
    return _get_ancestor_schools_uncached(school)


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

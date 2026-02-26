# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/organization/organization.py

import frappe
from frappe import _
from frappe.utils import cint, cstr
from frappe.utils.nestedset import NestedSet

from ifitwala_ed.utilities.employee_utils import get_descendant_organizations

VIRTUAL_ROOT = "All Organizations"
HR_SCOPE_ROLES = {"HR Manager", "HR User"}


class Organization(NestedSet):
    def validate(self):
        if self.name == VIRTUAL_ROOT and self.parent_organization:
            frappe.throw(_("The root organization '{0}' cannot have a parent.").format(VIRTUAL_ROOT))
        if self.parent_organization:
            parent_is_group = frappe.db.get_value("Organization", self.parent_organization, "is_group")
            if not parent_is_group:
                frappe.throw(
                    _("Parent Organization must be a Group. '{0}' is not a Group.").format(self.parent_organization)
                )
        self.validate_default_website_school()

    def validate_default_website_school(self):
        default_school = (self.default_website_school or "").strip()
        if not default_school:
            return

        school_org = frappe.db.get_value("School", default_school, "organization")
        if not school_org:
            frappe.throw(
                _("Default Website School '{0}' was not found.").format(default_school),
                frappe.ValidationError,
            )

        if school_org != self.name:
            frappe.throw(
                _(
                    "Default Website School must belong to this Organization.\n"
                    "School '{0}' belongs to '{1}', not '{2}'."
                ).format(default_school, school_org, self.name),
                frappe.ValidationError,
            )


@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **kwargs):
    """
    Return children of `parent`. For virtual root, return top-level orgs.
    Top-level = parent_organization in [NULL, "", VIRTUAL_ROOT] to support legacy rows.
    """
    filters = dict(kwargs.get("filters") or {})

    # Never show the virtual root as a child
    filters.update({"name": ["!=", VIRTUAL_ROOT]})

    if is_root or not parent or parent == VIRTUAL_ROOT:
        rows = frappe.get_all(
            "Organization",
            fields=[
                "name as value",
                "organization_name as title",
                "is_group as expandable",
                "parent_organization",
            ],
            order_by="lft asc",
            filters=filters,
        )
        visible_names = {row.get("value") for row in rows if row.get("value")}
        root_rows = []
        for row in rows:
            parent_name = cstr(row.get("parent_organization")).strip()
            if not parent_name or parent_name == VIRTUAL_ROOT or parent_name not in visible_names:
                row["expandable"] = 1 if row.get("expandable") else 0
                row.pop("parent_organization", None)
                root_rows.append(row)
        return root_rows

    filters.update({"parent_organization": parent})
    rows = frappe.get_all(
        "Organization",
        fields=[
            "name as value",
            "organization_name as title",
            "is_group as expandable",
        ],
        order_by="lft asc",
        filters=filters,
    )

    for row in rows:
        row["expandable"] = 1 if row.get("expandable") else 0
    return rows


@frappe.whitelist()
def get_parents(doc, name):
    parents = []
    doc = frappe.get_doc("Organization", name)
    while doc.parent_organization:
        parents.append(doc.parent_organization)
        doc = frappe.get_doc("Organization", doc.parent_organization)
    return parents


@frappe.whitelist()
def add_node(**kwargs):
    org_name = (kwargs.get("organization_name") or "").strip()
    abbr = (kwargs.get("abbr") or "").strip()
    is_group = cint(kwargs.get("is_group") or 0)

    parent = kwargs.get("parent_organization") or kwargs.get("parent")
    if not parent or parent == VIRTUAL_ROOT:
        parent = None

    if not org_name or not abbr:
        frappe.throw(_("Organization Name and Abbreviation are required."))

    doc = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": org_name,
            "abbr": abbr,
            "is_group": is_group,
            "parent_organization": parent,
        }
    )
    doc.insert()
    return {"name": doc.name}


def _resolve_hr_base_org(user: str) -> str | None:
    org = frappe.defaults.get_user_default("organization", user=user)
    if cstr(org).strip():
        return cstr(org).strip()

    global_org = frappe.db.get_single_value("Global Defaults", "default_organization")
    return cstr(global_org).strip() or None


def _resolve_hr_org_scope(user: str) -> list[str]:
    scope: set[str] = set()

    base_org = _resolve_hr_base_org(user)
    if base_org:
        scope.update({cstr(org).strip() for org in (get_descendant_organizations(base_org) or []) if cstr(org).strip()})

    explicit_orgs = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Organization"},
        pluck="for_value",
    )
    for org in explicit_orgs:
        org_name = cstr(org).strip()
        if not org_name:
            continue
        scope.update(
            {cstr(item).strip() for item in (get_descendant_organizations(org_name) or []) if cstr(item).strip()}
        )

    return sorted(scope)


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return None

    if roles & HR_SCOPE_ROLES:
        orgs = _resolve_hr_org_scope(user)
        if not orgs:
            return "1=0"
        vals = ", ".join(frappe.db.escape(org) for org in orgs)
        return f"`tabOrganization`.`name` IN ({vals})"

    return None


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user))
    if "System Manager" in roles:
        return True

    if roles & HR_SCOPE_ROLES and (ptype or "read") in {"read", "report", "export", "print"}:
        return doc.name in set(_resolve_hr_org_scope(user))

    return None

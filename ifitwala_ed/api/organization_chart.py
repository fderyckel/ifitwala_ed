# ifitwala_ed/api/organization_chart.py
# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import os
from typing import Iterable

import frappe
from frappe import _
from frappe.utils import formatdate, getdate

from ifitwala_ed.utilities.employee_utils import (
	get_descendant_organizations,
	get_user_base_org,
)
from ifitwala_ed.utilities.image_utils import slugify

EXPAND_MAX_NODES = 260
EXPAND_MAX_DEPTH = 6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_adminish(user: str) -> bool:
	return user == "Administrator" or ("System Manager" in frappe.get_roles(user))


def _get_allowed_org_scope(user: str) -> list[str] | None:
	"""
	Return the list of organizations the user can see.
	- Admin/System Manager: None (no restriction)
	- Staff with base org: base org + descendants
	- Staff without base org: [] (no access)
	"""
	if _is_adminish(user):
		return None

	base_org = get_user_base_org(user)
	if not base_org:
		return []
	return get_descendant_organizations(base_org)


def _resolve_org_scope(requested_org: str | None, allowed_scope: list[str] | None) -> list[str] | None:
	"""
	Return the effective organization scope for queries.
	- None means "no org restriction" (admin only)
	- list[str] means "restrict to this set"
	"""
	if allowed_scope is None:
		if requested_org:
			return get_descendant_organizations(requested_org)
		return None

	if not allowed_scope:
		frappe.throw(_("No organization access configured."), frappe.PermissionError)

	if not requested_org:
		return allowed_scope

	if requested_org not in allowed_scope:
		frappe.throw(_("Organization scope is not permitted."), frappe.PermissionError)

	return get_descendant_organizations(requested_org)


def _list_employee_thumbs() -> set[str]:
	thumb_dir = frappe.get_site_path("public", "files", "gallery_resized", "employee")
	if not os.path.isdir(thumb_dir):
		return set()
	return {name for name in os.listdir(thumb_dir) if name.startswith("thumb_")}


def _resolve_employee_image(file_url: str | None, thumb_names: set[str]) -> str:
	if not file_url:
		return ""

	filename = os.path.basename(file_url)
	if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
		return file_url

	if not file_url.startswith("/files/"):
		return file_url

	base_name, _ext = os.path.splitext(filename)
	thumb_filename = f"thumb_{slugify(base_name)}.webp"
	if thumb_filename in thumb_names:
		return f"/files/gallery_resized/employee/{thumb_filename}"

	return file_url


def _connections_from_nestedset(lft: int | None, rgt: int | None) -> int:
	if not lft or not rgt:
		return 0
	return max(0, (rgt - lft - 1) // 2)


def _serialize_employees(rows: Iterable[dict], thumb_names: set[str]) -> list[dict]:
	school_abbr_cache: dict[str, str] = {}
	org_abbr_cache: dict[str, str] = {}
	payload: list[dict] = []
	for row in rows:
		school = row.get("school")
		organization = row.get("organization")
		school_abbr = None
		org_abbr = None
		if school:
			if school in school_abbr_cache:
				school_abbr = school_abbr_cache[school]
			else:
				school_abbr = frappe.db.get_value("School", school, "abbr")
				school_abbr_cache[school] = school_abbr
		if organization:
			if organization in org_abbr_cache:
				org_abbr = org_abbr_cache[organization]
			else:
				org_abbr = frappe.db.get_value("Organization", organization, "abbr")
				org_abbr_cache[organization] = org_abbr

		joining_date = row.get("date_of_joining")
		joining_label = formatdate(getdate(joining_date), "MMMM yyyy") if joining_date else None

		connections = _connections_from_nestedset(row.get("lft"), row.get("rgt"))
		payload.append(
			{
				"id": row.get("id"),
				"name": row.get("name"),
				"first_name": row.get("first_name"),
				"preferred_name": row.get("preferred_name"),
				"title": row.get("title"),
				"school": row.get("school"),
				"school_abbr": school_abbr,
				"organization": row.get("organization"),
				"organization_abbr": org_abbr,
				"image": _resolve_employee_image(row.get("image"), thumb_names),
				"professional_email": row.get("professional_email"),
				"phone_ext": row.get("phone_ext"),
				"date_of_joining": row.get("date_of_joining"),
				"date_of_joining_label": joining_label,
				"connections": connections,
				"expandable": bool(connections),
				"parent_id": row.get("reports_to") or None,
			}
		)
	return payload


def _employee_fields() -> list[str]:
	fields = [
		"name as id",
		"employee_full_name as name",
		"employee_first_name as first_name",
		"employee_preferred_name as preferred_name",
		"designation as title",
		"school",
		"organization",
		"employee_image as image",
		"employee_professional_email as professional_email",
		"date_of_joining",
		"reports_to",
		"lft",
		"rgt",
	]
	if frappe.db.has_column("Employee", "phone_ext"):
		fields.append("phone_ext")
	return fields


def _get_root_employee_ids(filters: dict) -> list[str]:
	"""
	Compute org-scope roots: employees whose manager is missing or outside scope.
	If none exist (cycle/fully-linked), fall back to top-most by lft.
	"""
	rows = frappe.get_all(
		"Employee",
		fields=["name", "reports_to", "lft"],
		filters=filters,
		ignore_permissions=True,
	)
	if not rows:
		return []

	visible_ids = {row.get("name") for row in rows if row.get("name")}
	root_ids: list[str] = []
	for row in rows:
		emp_id = row.get("name")
		if not emp_id:
			continue
		parent = row.get("reports_to")
		if not parent or parent not in visible_ids:
			root_ids.append(emp_id)

	if root_ids:
		return root_ids

	min_lft = min((row.get("lft") for row in rows if row.get("lft") is not None), default=None)
	if min_lft is None:
		first_id = rows[0].get("name")
		return [first_id] if first_id else []

	return [row["name"] for row in rows if row.get("lft") == min_lft and row.get("name")]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_org_chart_context():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	organizations = frappe.get_all(
		"Organization",
		fields=["name", "organization_name"],
		order_by="lft asc",
		ignore_permissions=True,
	)

	default_org = get_user_base_org(user)

	return {
		"organizations": organizations,
		"default_organization": default_org,
		"expand_limits": {
			"max_nodes": EXPAND_MAX_NODES,
			"max_depth": EXPAND_MAX_DEPTH,
		},
	}


@frappe.whitelist()
def get_org_chart_children(parent: str | None = None, organization: str | None = None):
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	if organization == "All Organizations":
		organization = None
	organization = organization or None

	filters = {"status": "Active"}
	if organization:
		filters["organization"] = organization

	parent = parent or None
	if parent:
		filters["reports_to"] = parent
	else:
		root_ids = _get_root_employee_ids(filters)
		if not root_ids:
			return []
		filters["name"] = ["in", root_ids]

	rows = frappe.get_all(
		"Employee",
		fields=_employee_fields(),
		filters=filters,
		order_by="employee_full_name asc",
		ignore_permissions=True,
	)

	thumb_names = _list_employee_thumbs()
	return _serialize_employees(rows, thumb_names)


@frappe.whitelist()
def get_org_chart_tree(organization: str | None = None):
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	if organization == "All Organizations":
		organization = None
	organization = organization or None

	filters = {"status": "Active"}
	if organization:
		filters["organization"] = organization

	total = frappe.db.count("Employee", filters=filters)
	if total > EXPAND_MAX_NODES:
		return {
			"status": "blocked",
			"reason": "max_nodes",
			"total": total,
			"max_nodes": EXPAND_MAX_NODES,
			"max_depth": EXPAND_MAX_DEPTH,
			"message": _(
				"Expand all is limited to {0} people. Narrow the organization to continue."
			).format(EXPAND_MAX_NODES),
		}

	if total == 0:
		return {
			"status": "ok",
			"nodes": [],
			"roots": [],
			"total": 0,
			"max_depth": 0,
		}

	rows = frappe.get_all(
		"Employee",
		fields=_employee_fields(),
		filters=filters,
		order_by="lft asc",
		ignore_permissions=True,
	)

	thumb_names = _list_employee_thumbs()
	nodes = _serialize_employees(rows, thumb_names)

	id_set = {node["id"] for node in nodes}
	children_by_parent: dict[str, list[str]] = {}
	roots: list[str] = []
	for node in nodes:
		parent_id = node.get("parent_id")
		if not parent_id or parent_id not in id_set:
			node["parent_id"] = None
			roots.append(node["id"])
			continue
		children_by_parent.setdefault(parent_id, []).append(node["id"])

	if not roots and nodes:
		min_lft = min((node.get("lft") for node in nodes if node.get("lft") is not None), default=None)
		if min_lft is None:
			roots = [nodes[0]["id"]]
		else:
			roots = [node["id"] for node in nodes if node.get("lft") == min_lft]

	max_depth = 0
	queue: list[tuple[str, int]] = [(root_id, 1) for root_id in roots]
	while queue:
		node_id, depth = queue.pop(0)
		max_depth = max(max_depth, depth)
		if depth > EXPAND_MAX_DEPTH:
			return {
				"status": "blocked",
				"reason": "max_depth",
				"total": total,
				"max_nodes": EXPAND_MAX_NODES,
				"max_depth": EXPAND_MAX_DEPTH,
				"message": _(
					"Expand all is limited to {0} levels. Narrow the organization to continue."
				).format(EXPAND_MAX_DEPTH),
			}

		for child_id in children_by_parent.get(node_id, []):
			queue.append((child_id, depth + 1))

	return {
		"status": "ok",
		"nodes": nodes,
		"roots": roots,
		"total": total,
		"max_depth": max_depth,
	}

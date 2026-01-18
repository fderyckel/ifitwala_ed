# ifitwala_ed/api/organization_chart.py
# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import os
from typing import Iterable

import frappe
from frappe import _

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
	payload: list[dict] = []
	for row in rows:
		connections = _connections_from_nestedset(row.get("lft"), row.get("rgt"))
		payload.append(
			{
				"id": row.get("id"),
				"name": row.get("name"),
				"first_name": row.get("first_name"),
				"title": row.get("title"),
				"school": row.get("school"),
				"organization": row.get("organization"),
				"image": _resolve_employee_image(row.get("image"), thumb_names),
				"connections": connections,
				"expandable": bool(connections),
				"parent_id": row.get("reports_to") or None,
			}
		)
	return payload


def _get_root_employee_ids(filters: dict) -> list[str]:
	"""
	Compute org-scope roots: employees whose manager is missing or outside scope.
	"""
	rows = frappe.get_all(
		"Employee",
		fields=["name", "reports_to"],
		filters=filters,
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
	return root_ids


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_org_chart_context():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	if not frappe.has_permission("Employee", "read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	allowed_scope = _get_allowed_org_scope(user)
	filters = {}
	if allowed_scope is not None:
		if not allowed_scope:
			frappe.throw(_("No organization access configured."), frappe.PermissionError)
		filters["name"] = ["in", allowed_scope]

	organizations = frappe.get_all(
		"Organization",
		fields=["name", "organization_name"],
		filters=filters,
		order_by="lft asc",
	)

	default_org = None if allowed_scope is None else get_user_base_org(user)

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

	if not frappe.has_permission("Employee", "read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	if organization == "All Organizations":
		organization = None
	organization = organization or None
	allowed_scope = _get_allowed_org_scope(user)
	org_scope = _resolve_org_scope(organization, allowed_scope)

	filters = {"status": "Active"}
	if org_scope is not None:
		filters["organization"] = ["in", org_scope]

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
		fields=[
			"name as id",
			"employee_full_name as name",
			"employee_first_name as first_name",
			"designation as title",
			"school",
			"organization",
			"employee_image as image",
			"reports_to",
			"lft",
			"rgt",
		],
		filters=filters,
		order_by="employee_full_name asc",
	)

	thumb_names = _list_employee_thumbs()
	return _serialize_employees(rows, thumb_names)


@frappe.whitelist()
def get_org_chart_tree(organization: str | None = None):
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in."), frappe.PermissionError)

	if not frappe.has_permission("Employee", "read"):
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	if organization == "All Organizations":
		organization = None
	organization = organization or None
	allowed_scope = _get_allowed_org_scope(user)
	org_scope = _resolve_org_scope(organization, allowed_scope)

	filters = {"status": "Active"}
	if org_scope is not None:
		filters["organization"] = ["in", org_scope]

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
		fields=[
			"name as id",
			"employee_full_name as name",
			"employee_first_name as first_name",
			"designation as title",
			"school",
			"organization",
			"employee_image as image",
			"reports_to",
			"lft",
			"rgt",
		],
		filters=filters,
		order_by="lft asc",
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

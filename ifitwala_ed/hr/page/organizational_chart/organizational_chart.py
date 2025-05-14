# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import os
import re
import frappe
from frappe.query_builder.functions import Count

@frappe.whitelist()
def get_children(parent=None, organization=None, exclude_node=None):
	filters = [["status", "=", "Active"]]
	if organization and organization != "All Organizations":
		filters.append(["organization", "=", organization])

	if parent and organization and parent != organization:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	if exclude_node:
		filters.append(["name", "!=", exclude_node])

	employees = frappe.get_all(
		"Employee",
		fields=[
			"employee_full_name as name",
			"name as id",
			"lft",
			"rgt",
			"reports_to",
			"employee_image as image",  # e.g. "/files/employee/person1.png"
			"designation as title", 
			"organization"
		],
		filters=filters,
		order_by="name",
	)

	thumb_dir = frappe.get_site_path("public", "files", "gallery_resized", "employee")

	for emp in employees:
		orig_url = emp.image or ""
		thumb_url = None

		# only if the original comes from /files/employee/
		if orig_url.startswith("/files/employee/") and os.path.isdir(thumb_dir):
			# strip path, get "person1.png" or "person1.jpg"
			filename = orig_url.rsplit("/", 1)[-1] 
			
			# Normalize the filename 
			name, ext = os.path.splitext(filename) 
			name = re.sub(r"[-\s]+", "_", name).lower()

			# build the .webp card filename
			thumb_filename = f"thumb_{name}.webp"
			thumb_path = os.path.join(thumb_dir, thumb_filename)

			if os.path.exists(thumb_path):
				thumb_url = f"/files/gallery_resized/employee/{thumb_filename}"

		# pick the card if it exists, else the original
		emp.image = thumb_url or orig_url

		# compute connections as before
		emp.connections = get_connections(emp.id, emp.lft, emp.rgt)
		emp.expandable = bool(emp.connections)

	return employees


def get_connections(employee: str, lft: int, rgt: int) -> int:
    Employee = frappe.qb.DocType("Employee")
    query = (
        frappe.qb.from_(Employee)
        .select(Count(Employee.name))
        .where(
            (Employee.lft > lft)
            & (Employee.rgt < rgt)
            & (Employee.status == "Active")
        )
    ).run()
    return query[0][0]


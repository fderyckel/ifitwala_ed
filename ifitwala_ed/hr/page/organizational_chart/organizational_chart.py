import frappe
from frappe.query_builder.functions import Count


@frappe.whitelist()
def get_children(parent=None, organization=None, exclude_node=None):
	"""Fetch direct reports for the given Organization (or all, if none specified)"""
	filters = [["status", "=", "Active"]]
	# Only filter by organization when one is provided
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
			"employee_image as image",
			"designation as title",
		],
		filters=filters,
		order_by="name",
	)

	for employee in employees:
		employee.connections = get_connections(employee.id, employee.lft, employee.rgt)
		employee.expandable = bool(employee.connections)

	return employees


def get_connections(employee: str, lft: int, rgt: int) -> int:
	Employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(Employee)
		.select(Count(Employee.name))
		.where((Employee.lft > lft) & (Employee.rgt < rgt) & (Employee.status == "Active"))
	).run()

	return query[0][0]

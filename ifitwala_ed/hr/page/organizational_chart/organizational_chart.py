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
      "lft", "rgt",
      "reports_to",
      "employee_image as image",
      "designation as title",
    ],
    filters=filters,
    order_by="name",
  )
	
	for employee in employees:
    # ==== pick card_… if it actually exists on disk ====
		orig = employee.image or "" 
		card_url = None 
		
		if orig.startswith("/files/"):
			# extract filename, e.g. "foo.jpg" 
			fname = orig.split("/")[-1]
			card_fname = f"card_{fname}" 
			# build full disk path to public/files/resized_gallery/employee/card_<fname> 
			site = frappe.get_site_path() 
			disk_path = os.path.join(
        site, "public", "files", "resized_gallery", "employee", card_fname
      )
			if os.path.exists(disk_path): 
				# if the file exists, web‐accessible URL is:
				card_url = f"/files/resized_gallery/employee/{card_fname}"

    # fall back to original if card version missin
		employee.image = card_url or orig

    # === rest unchanged ===
		employee.connections = get_connections(employee.id, employee.lft, employee.rgt) 
		employee.expandable = bool(employee.connections) \
				
	return employees	


def get_connections(employee: str, lft: int, rgt: int) -> int:
	Employee = frappe.qb.DocType("Employee")
	query = (
		frappe.qb.from_(Employee)
		.select(Count(Employee.name))
		.where((Employee.lft > lft) & (Employee.rgt < rgt) & (Employee.status == "Active"))
	).run()

	return query[0][0]

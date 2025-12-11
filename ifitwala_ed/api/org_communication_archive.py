# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_communication_archive

import frappe
from frappe.utils import today, add_days, getdate, strip_html
from ifitwala_ed.api.org_comm_utils import check_audience_match
from frappe import _

@frappe.whitelist()
def get_archive_context():
    """Returns context data for the archive page filters."""
    user = frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school", "organization", "department"], as_dict=True)

    data = {
        "my_team": None,
        "my_groups": [],
        "schools": [], # Options
        "organizations": [], # Options
        "defaults": { # Pre-select these
            "school": "All",
            "organization": "All",
            "team": "All"
        }
    }

    if employee:
        data["my_team"] = employee.department
        if employee.department:
             data["defaults"]["team"] = employee.department

        # Defaults
        if employee.organization:
             data["defaults"]["organization"] = employee.organization
        if employee.school:
             data["defaults"]["school"] = employee.school

        # Get Instructor Groups
        groups = frappe.get_all("Student Group Instructor", filters={"instructor": employee.name}, fields=["parent"])
        data["my_groups"] = sorted(list(set([g.parent for g in groups])))

        # Organizations: strictly limits to user's org if set?
        # User said: "The organization filter should be the default organization of the employee... Based on that the school filter should only be schools that depends of that organization"
        # If user has an Org, they might only see that Org? Or strict hierarchy?
        # Let's assume if Employee has Org, they are bound to it. If not, they see all.
        if employee.organization:
             data["organizations"] = [{"name": employee.organization}]
             # Also allow fetching children orgs if Organization is a tree?
             # Assuming flat or simple for now unless specified.
             # Actually, if they are at Org level they might oversee sub-orgs?
             # Let's check if Organization matches strictness. "The organization filter should be the defautl organization of the employee".
             # Implies pre-selection. Does it imply restriction? "Then user can only select that school or one of its children."
             # For now, restrict Org list to just the employee's org to be safe/strict as requested.
        else:
             try:
                data["organizations"] = frappe.get_all("Organization", fields=["name"], order_by="name asc")
             except:
                data["organizations"] = []

        # Schools: Strict hierarchy
        # "User can only select that school or one of its children"
        if employee.school:
            # Use school_tree utility
            from ifitwala_ed.utilities.school_tree import get_descendant_schools
            allowed_schools = get_descendant_schools(employee.school)
            # Fetch names
            data["schools"] = frappe.get_all("School", filters={"name": ["in", allowed_schools]}, fields=["name", "school_name"], order_by="school_name asc")
        elif employee.organization:
             # If no school but has Org, show schools in that Org
             data["schools"] = frappe.get_all("School", filters={"organization": employee.organization}, fields=["name", "school_name"], order_by="school_name asc")
        else:
             # Fallback (System Manager or unassigned)
             data["schools"] = frappe.get_all("School", fields=["name", "school_name"], order_by="school_name asc")

    return data

@frappe.whitelist()
def get_org_communication_item(name):
    """Returns the full communication details if the user is in the audience."""
    user = frappe.session.user
    roles = frappe.get_roles(user)
    employee = frappe.db.get_value("Employee", {"user_id": user}, ["name", "school", "organization", "department"], as_dict=True)

    if not check_audience_match(name, user, roles, employee):
        frappe.throw(_("You do not have permission to view this communication."), frappe.PermissionError)

    doc = frappe.get_doc("Org Communication", name)
    return {
        "name": doc.name,
        "title": doc.title,
        "message": doc.message, # HTML Content
        "communication_type": doc.communication_type,
        "priority": doc.priority,
        "publish_from": doc.publish_from,
        "audience_label": get_audience_label(doc.name)
    }



@frappe.whitelist()
def get_org_communication_feed(
	search_text: str | None = None,
	status: str | None = "PublishedOrArchived",
	priority: str | None = None,
	portal_surface: str | None = None,
	communication_type: str | None = None,
	date_range: str | None = "90d",  # '7d' | '30d' | '90d' | 'year' | 'all'
	team: str | None = None,
	student_group: str | None = None,
	school: str | None = None,
	organization: str | None = None,
	only_with_interactions: int | None = 0,
	limit_start: int = 0,
	limit_page_length: int = 30,
) -> dict:
	user = frappe.session.user
	roles = frappe.get_roles(user)
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user},
		["name", "school", "organization", "department"],
		as_dict=True,
	)

	# Base Filters (SQL-level; school is *not* filtered here anymore)
	conditions: list[str] = []
	values: dict[str, object] = {}

	# Status
	if status == "PublishedOrArchived":
		conditions.append("status IN ('Published', 'Archived')")
	elif status == "Published":
		conditions.append("status = 'Published'")
	elif status == "All":
		# No status filter: rely on audience + permissions
		pass
	elif status:
		conditions.append("status = %(status)s")
		values["status"] = status

	# Priority
	if priority and priority != "All":
		conditions.append("priority = %(priority)s")
		values["priority"] = priority

	# Portal Surface
	if portal_surface and portal_surface != "All":
		conditions.append("portal_surface = %(portal_surface)s")
		values["portal_surface"] = portal_surface

	# Communication Type
	if communication_type and communication_type != "All":
		conditions.append("communication_type = %(communication_type)s")
		values["communication_type"] = communication_type

	# Date Range (publish_from)
	if date_range and date_range != "all":
		end_date = getdate(today())
		start_date = None

		if date_range == "7d":
			start_date = add_days(end_date, -7)
		elif date_range == "30d":
			start_date = add_days(end_date, -30)
		elif date_range == "90d":
			start_date = add_days(end_date, -90)
		elif date_range == "year":
			start_date = f"{end_date.year}-01-01"

		if start_date:
			conditions.append("publish_from >= %(start_date)s")
			values["start_date"] = start_date

	# Search Text
	if search_text:
		conditions.append("(title LIKE %(search)s OR message LIKE %(search)s)")
		values["search"] = f"%{search_text}%"

	# Organization Filter (Doc-level; OK to stay here)
	if organization and organization != "All":
		conditions.append("organization = %(org)s")
		values["org"] = organization

	# Only with interactions
	if only_with_interactions:
		conditions.append(
			"EXISTS (SELECT name FROM `tabCommunication Interaction` "
			"WHERE org_communication = `tabOrg Communication`.name)"
		)

	where_clause = " AND ".join(conditions)
	if where_clause:
		where_clause = "WHERE " + where_clause

	sql = f"""
		SELECT
			name,
			title,
			message,
			communication_type,
			status,
			priority,
			portal_surface,
			school,
			organization,
			publish_from,
			publish_to,
			brief_start_date,
			brief_end_date,
			interaction_mode,
			allow_private_notes,
			allow_public_thread
		FROM `tabOrg Communication`
		{where_clause}
		ORDER BY publish_from DESC, creation DESC
	"""

	candidates = frappe.db.sql(sql, values, as_dict=True)

	visible_items: list[dict] = []

	# Permission Checks for Filters
	filter_team_val = team
	filter_sg_val = student_group
	filter_school_val = school

	for c in candidates:
		if check_audience_match(
			c.name,
			user,
			roles,
			employee,
			filter_team=filter_team_val,
			filter_student_group=filter_sg_val,
			filter_school=filter_school_val,
		):
			raw_text = strip_html(c.message or "") if c.message else ""
			if raw_text and len(raw_text) > 260:
				snippet = raw_text[:260] + "..."
			else:
				snippet = raw_text

			visible_items.append({
				"name": c.name,
				"title": c.title,
				"communication_type": c.communication_type,
				"status": c.status,
				"priority": c.priority,
				"portal_surface": c.portal_surface,
				"school": c.school,
				"organization": c.organization,
				"publish_from": c.publish_from,
				"publish_to": c.publish_to,
				"brief_start_date": c.brief_start_date,
				"brief_end_date": c.brief_end_date,
				"interaction_mode": c.interaction_mode,
				"allow_private_notes": c.allow_private_notes,
				"allow_public_thread": c.allow_public_thread,
				"snippet": snippet,
				"has_active_thread": c.allow_public_thread,
				"audience_label": get_audience_label(c.name),
			})

	# Apply pagination on the filtered list
	total_count = len(visible_items)

	start = int(limit_start)
	length = int(limit_page_length)
	paged_items = visible_items[start : start + length]

	return {
		"items": paged_items,
		"total_count": total_count,
		"limit_start": start,
		"limit_page_length": length,
		"has_more": (start + length) < total_count,
	}



def get_audience_label(comm_name):
    # Quick helper to generate a human-readable audience summary
    # e.g. "Whole Staff · Ifitwala Secondary School"
    audiences = frappe.get_all("Org Communication Audience", filters={"parent": comm_name}, fields=["target_group", "school", "team", "program", "student_group"])
    if not audiences:
        return "Whole Organization"

    parts = []
    for a in audiences:
        label = a.target_group or a.team or "Everyone"
        if a.student_group:
             label = f"Student Group: {a.student_group}"

        if a.school:
            # Fix 500 error: Use get_cached_value to avoid column issues if caching is smart,
            # OR just fetch the correct field safely.
            # Note: frappe.db.get_value can throw if column doesn't exist in cache sometimes?
            # Safest is get_cached_value which uses `name` lookup.
            school_name = frappe.get_cached_value("School", a.school, "school_name")
            label += f" · {school_name or a.school}"
        parts.append(label)

    return ", ".join(parts)

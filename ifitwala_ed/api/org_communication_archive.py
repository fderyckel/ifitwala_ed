# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_communication_archive

import frappe
from frappe.utils import today, add_days, getdate, strip_html
from ifitwala_ed.utilities.employee_utils import (
	get_descendant_organizations,
	get_user_base_org,
	get_user_base_school,
)
from ifitwala_ed.utilities.school_tree import get_descendant_schools
from ifitwala_ed.api.org_comm_utils import check_audience_match
from frappe import _


def _parse_filters(raw):
	"""Return a dict from a JSON string or mapping."""
	if isinstance(raw, str):
		try:
			raw = frappe.parse_json(raw) or {}
		except Exception:
			raw = {}
	return raw or {}


def _normalize_filters(raw_filters: dict | None) -> dict:
	"""Coerce incoming filters into a consistent contract."""
	raw = _parse_filters(raw_filters)

	def cleaned(val):
		if val is None:
			return None
		if isinstance(val, str):
			trimmed = val.strip()
			if trimmed in {"", "All"}:
				return None
			return trimmed
		return val

	status_in_payload = "status" in raw

	date_range_raw = raw.get("date_range")
	date_range_clean = cleaned(date_range_raw)
	if isinstance(date_range_raw, str) and date_range_raw.strip().lower() == "all":
		date_range_clean = "all"
	date_range_in_payload = "date_range" in raw

	status_clean = cleaned(raw.get("status"))
	if status_clean is None and not status_in_payload:
		status_clean = "PublishedOrArchived"

	if date_range_clean is None and not date_range_in_payload:
		date_range_clean = "90d"

	status_clean = status_clean or None
	out = {
		"search_text": cleaned(raw.get("search_text") or raw.get("search")),
		"status": status_clean,
		"priority": cleaned(raw.get("priority")),
		"portal_surface": cleaned(raw.get("portal_surface")),
		"communication_type": cleaned(raw.get("communication_type")),
		"date_range": date_range_clean,
		"team": cleaned(raw.get("team")),
		"student_group": cleaned(raw.get("student_group")),
		"school": cleaned(raw.get("school")),
		"organization": cleaned(raw.get("organization")),
		"only_with_interactions": 1 if raw.get("only_with_interactions") else 0,
	}

	return out


def _get_scope(user: str, employee: dict | None):
	"""Resolve the base org/school and their descendant scopes."""
	base_org = (employee or {}).get("organization") or get_user_base_org(user)
	base_school = (employee or {}).get("school") or get_user_base_school(user)

	org_scope = []
	if base_org:
		org_scope = get_descendant_organizations(base_org) or [base_org]

	school_scope = []
	if base_school:
		school_scope = get_descendant_schools(base_school) or [base_school]
	elif org_scope:
		school_scope = frappe.get_all(
			"School",
			filters={"organization": ["in", org_scope]},
			pluck="name",
		)

	return base_org, base_school, org_scope, school_scope


@frappe.whitelist()
def get_archive_context():
	"""Returns context data for the archive page filters."""
	user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "school", "organization", "department"],
		as_dict=True,
	)

	base_org, base_school, org_scope, school_scope = _get_scope(user, employee)

	# Strict default: Employee.school first, else user default school
	default_school = (employee or {}).get("school") or frappe.defaults.get_user_default("school")

	data = {
		"my_team": (employee or {}).get("department"),
		"my_groups": [],
		"schools": [],
		"organizations": [],
		"defaults": {
			"school": default_school,
			"organization": base_org,
			# IMPORTANT: Team defaults to "All teams"
			"team": None,
		},
		"base_org": base_org,
		"base_school": base_school,
	}

	# Student Groups for instructors (Employee -> Instructor -> Student Group Instructor)
	if employee and employee.get("name"):
		instructor_name = frappe.db.get_value("Instructor", {"employee": employee.name}, "name")
		if instructor_name:
			groups = frappe.get_all(
				"Student Group Instructor",
				filters={"instructor": instructor_name},
				pluck="parent",
			)
			data["my_groups"] = sorted(list({g for g in (groups or []) if g}))

	# Organizations: base org + descendants; fallback to all
	org_filters = {}
	if org_scope:
		org_filters["name"] = ["in", org_scope]
	data["organizations"] = frappe.get_all(
		"Organization",
		filters=org_filters or None,
		fields=["name", "organization_name"],
		order_by="lft asc",
	)

	# Schools scoped to base school cone or allowed organizations
	school_filters = {}
	if school_scope:
		school_filters["name"] = ["in", school_scope]
	elif org_scope:
		school_filters["organization"] = ["in", org_scope]

	data["schools"] = frappe.get_all(
		"School",
		filters=school_filters or None,
		fields=["name", "school_name", "organization"],
		order_by="school_name asc",
	)

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
	filters: dict | None = None,
	start: int | None = None,
	page_length: int | None = None,
	limit_start: int = 0,
	limit_page_length: int = 30,
	# Legacy params (kept to avoid breaking older callers)
	search_text: str | None = None,
	status: str | None = None,
	priority: str | None = None,
	portal_surface: str | None = None,
	communication_type: str | None = None,
	date_range: str | None = None,
	team: str | None = None,
	student_group: str | None = None,
	school: str | None = None,
	organization: str | None = None,
	only_with_interactions: int | None = None,
) -> dict:
	user = frappe.session.user
	roles = frappe.get_roles(user)
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": user},
		["name", "school", "organization", "department"],
		as_dict=True,
	)

	# Merge legacy params into filters before normalization
	raw_filters = _parse_filters(filters)
	legacy_overrides = {
		"search_text": search_text,
		"status": status,
		"priority": priority,
		"portal_surface": portal_surface,
		"communication_type": communication_type,
		"date_range": date_range,
		"team": team,
		"student_group": student_group,
		"school": school,
		"organization": organization,
		"only_with_interactions": only_with_interactions,
	}
	for key, value in legacy_overrides.items():
		if value is not None and key not in raw_filters:
			raw_filters[key] = value

	filters_dict = _normalize_filters(raw_filters)

	# Pagination params (start/page_length preferred over legacy limit_start/page_length)
	offset = int(start if start is not None else limit_start or 0)
	page_len = int(page_length if page_length is not None else limit_page_length or 30)

	base_org, base_school, org_scope, school_scope = _get_scope(user, employee)
	org_guard: set[str] = set()
	if org_scope and "System Manager" not in roles:
		org_guard = set(org_scope)

	if not org_guard and school_scope and "System Manager" not in roles:
		orgs_from_schools = frappe.get_all(
			"School",
			filters={"name": ["in", school_scope]},
			pluck="organization",
		)
		org_guard = {o for o in orgs_from_schools if o}

	org_filter = filters_dict.get("organization")
	if org_filter:
		if org_guard and org_filter not in org_guard:
			frappe.throw(_("You do not have access to this organization."), frappe.PermissionError)
		org_guard = {org_filter}

	# Optional school guard for user scope
	filter_school_val = filters_dict.get("school")
	if (
		filter_school_val
		and school_scope
		and "System Manager" not in roles
		and filter_school_val not in school_scope
	):
		frappe.throw(_("You do not have access to this school."), frappe.PermissionError)

	# Base Filters (SQL-level; school is evaluated in audience checks)
	conditions: list[str] = []
	values: dict[str, object] = {}

	status_from_payload = "status" in raw_filters
	status_val = filters_dict.get("status")
	if status_val is None and not status_from_payload:
		status_val = "PublishedOrArchived"

	if status_val == "PublishedOrArchived":
		conditions.append("status IN ('Published', 'Archived')")
	elif status_val == "Published":
		conditions.append("status = 'Published'")
	elif status_val:
		conditions.append("status = %(status)s")
		values["status"] = status_val

	priority_val = filters_dict.get("priority")
	if priority_val:
		conditions.append("priority = %(priority)s")
		values["priority"] = priority_val

	portal_surface_val = filters_dict.get("portal_surface")
	if portal_surface_val:
		conditions.append("portal_surface = %(portal_surface)s")
		values["portal_surface"] = portal_surface_val

	communication_type_val = filters_dict.get("communication_type")
	if communication_type_val:
		conditions.append("communication_type = %(communication_type)s")
		values["communication_type"] = communication_type_val

	date_range_from_payload = "date_range" in raw_filters
	date_range_val = filters_dict.get("date_range")
	if date_range_val is None and not date_range_from_payload:
		date_range_val = "90d"

	if date_range_val != "all":
		end_date = getdate(today())
		start_date = None

		if date_range_val == "7d":
			start_date = add_days(end_date, -7)
		elif date_range_val == "30d":
			start_date = add_days(end_date, -30)
		elif date_range_val == "90d":
			start_date = add_days(end_date, -90)
		elif date_range_val == "year":
			start_date = f"{end_date.year}-01-01"

		if start_date:
			conditions.append("publish_from >= %(start_date)s")
			values["start_date"] = start_date

	search_val = filters_dict.get("search_text")
	if search_val:
		conditions.append("(title LIKE %(search)s OR message LIKE %(search)s)")
		values["search"] = f"%{search_val}%"

	if org_guard:
		conditions.append("organization IN %(org_guard)s")
		values["org_guard"] = tuple(org_guard)

	if filters_dict.get("only_with_interactions"):
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

	filter_team_val = filters_dict.get("team")
	filter_sg_val = filters_dict.get("student_group")

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
	paged_items = visible_items[offset : offset + page_len]

	return {
		"items": paged_items,
		"total_count": total_count,
		"limit_start": offset,
		"limit_page_length": page_len,
		"start": offset,
		"page_length": page_len,
		"has_more": (offset + page_len) < total_count,
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

# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_portfolio.py

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict, List

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime, strip_html, today

from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.utilities.school_tree import get_school_lineage


STAFF_ROLES = {
	"System Manager",
	"Administrator",
	"Academic Admin",
	"Academic Staff",
	"Instructor",
	"Curriculum Coordinator",
}
ADMIN_ROLES = {"System Manager", "Administrator"}


def _require_authenticated_user() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You must be signed in."), frappe.PermissionError)
	return user


def _user_roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def _normalize_payload(payload, kwargs):
	data = payload if payload is not None else kwargs
	if isinstance(data, str):
		data = frappe.parse_json(data)
	if not isinstance(data, dict):
		frappe.throw(_("Payload must be a dict."))
	return data


def _normalize_to_list(value: Any) -> list[str]:
	if value is None:
		return []
	if isinstance(value, str):
		value = [value]
	if not isinstance(value, (list, tuple, set)):
		return []
	return [str(v).strip() for v in value if str(v).strip()]


def _resolve_student_for_user(user: str) -> str | None:
	student = frappe.db.get_value("Student", {"student_email": user}, "name")
	if student:
		return student
	user_email = frappe.db.get_value("User", user, "email") or user
	return frappe.db.get_value("Student", {"student_email": user_email}, "name")


def _guardian_students(user: str) -> list[str]:
	guardian_name = frappe.db.get_value("Guardian", {"user": user}, "name")
	if not guardian_name:
		return []

	student_guardian_rows = frappe.get_all(
		"Student Guardian",
		filters={"guardian": guardian_name, "parenttype": "Student"},
		fields=["parent"],
	)
	guardian_student_rows = frappe.get_all(
		"Guardian Student",
		filters={"parent": guardian_name, "parenttype": "Guardian"},
		fields=["student"],
	)
	return sorted(
		{
			row.get("parent")
			for row in student_guardian_rows
			if row.get("parent")
		}
		| {
			row.get("student")
			for row in guardian_student_rows
			if row.get("student")
		}
	)


def _staff_scope_students(user: str, school_scope: list[str] | None = None) -> list[str]:
	filters = {"archived": 0}
	if school_scope:
		filters["school"] = ["in", school_scope]
	rows = frappe.get_all(
		"Program Enrollment",
		filters=filters,
		fields=["student"],
		limit_page_length=0,
	)
	return sorted({row.get("student") for row in rows if row.get("student")})


def _resolve_actor_scope(
	*,
	requested_students: list[str],
	school_filter: str | None = None,
) -> dict[str, Any]:
	user = _require_authenticated_user()
	roles = _user_roles(user)

	if "Student" in roles:
		student = _resolve_student_for_user(user)
		if not student:
			frappe.throw(_("This user is not linked to a Student record."), frappe.PermissionError)
		allowed = {student}
		if requested_students:
			requested = set(requested_students)
			allowed &= requested
		return {"role": "Student", "students": sorted(allowed), "user": user}

	if "Guardian" in roles:
		allowed = set(_guardian_students(user))
		if requested_students:
			requested = set(requested_students)
			allowed &= requested
		return {"role": "Guardian", "students": sorted(allowed), "user": user}

	if roles & STAFF_ROLES:
		if roles & ADMIN_ROLES:
			if requested_students:
				return {"role": "Staff", "students": sorted(set(requested_students)), "user": user}
			if school_filter:
				school_scope = [school_filter]
				students = _staff_scope_students(user, school_scope=school_scope)
				return {"role": "Staff", "students": students, "user": user}
			return {"role": "Staff", "students": [], "user": user, "all_students": True}

		authorized = get_authorized_schools(user)
		if not authorized:
			frappe.throw(_("You do not have school scope for portfolio access."), frappe.PermissionError)

		school_scope = authorized
		if school_filter:
			if school_filter not in authorized:
				frappe.throw(_("School filter is outside your authorized scope."), frappe.PermissionError)
			school_scope = [school_filter]

		allowed_students = set(_staff_scope_students(user, school_scope=school_scope))
		if requested_students:
			allowed_students &= set(requested_students)
		return {"role": "Staff", "students": sorted(allowed_students), "user": user}

	frappe.throw(_("Not permitted."), frappe.PermissionError)
	return {}


def _ensure_can_write_student(student: str) -> dict[str, Any]:
	scope = _resolve_actor_scope(requested_students=[student])
	if scope.get("role") == "Guardian":
		frappe.throw(_("Guardians cannot modify portfolio or reflection records."), frappe.PermissionError)
	if not scope.get("students") and not scope.get("all_students"):
		frappe.throw(_("Not permitted for this student."), frappe.PermissionError)
	return scope


def _resolve_settings_doc_for_school(school: str | None) -> str | None:
	if not school:
		return None
	for school_name in get_school_lineage(school):
		name = frappe.db.get_value("Portfolio Journal Settings", {"school": school_name, "enabled": 1}, "name")
		if name:
			return name
	return None


def _resolve_settings_for_school(school: str | None) -> Dict[str, Any]:
	defaults = {
		"enable_moderation": 1,
		"moderation_scope": "Showcase only",
		"default_visibility_for_reflection": "Teacher",
		"allow_student_external_share": 1,
		"allow_pdf_export": 1,
		"allow_external_download": 0,
		"share_link_max_days": 30,
		"require_teacher_approval_for_showcase": 1,
		"export_purge_days": 30,
	}
	if not school:
		return defaults

	name = _resolve_settings_doc_for_school(school)
	if name:
		row = frappe.db.get_value(
			"Portfolio Journal Settings",
			name,
			[
				"enable_moderation",
				"moderation_scope",
				"default_visibility_for_reflection",
				"allow_student_external_share",
				"allow_pdf_export",
				"allow_external_download",
				"share_link_max_days",
				"require_teacher_approval_for_showcase",
				"export_purge_days",
			],
			as_dict=True,
		)
		if row:
			defaults.update(row)
	return defaults


def _resolve_moderation_policy_for_school(school: str) -> Dict[str, Any]:
	settings = _resolve_settings_for_school(school)
	scope = (settings.get("moderation_scope") or "Showcase only").strip()
	policy = {
		"enable_moderation": int(settings.get("enable_moderation") or 0) == 1,
		"moderation_scope": scope,
		"showcase_roles": {"Academic Admin", "Academic Staff"},
		"reflection_roles": set(),
	}

	settings_name = _resolve_settings_doc_for_school(school)
	if settings_name:
		role_rows = frappe.get_all(
			"Portfolio Journal Setting Role",
			filters={
				"parent": settings_name,
				"parenttype": "Portfolio Journal Settings",
				"parentfield": "moderation_roles",
			},
			fields=["role", "can_moderate_showcase", "can_moderate_reflection"],
			limit_page_length=0,
		)
		showcase_roles = {
			row.get("role")
			for row in role_rows
			if row.get("role") and int(row.get("can_moderate_showcase") or 0) == 1
		}
		reflection_roles = {
			row.get("role")
			for row in role_rows
			if row.get("role") and int(row.get("can_moderate_reflection") or 0) == 1
		}
		if showcase_roles:
			policy["showcase_roles"] = showcase_roles
		if reflection_roles:
			policy["reflection_roles"] = reflection_roles

	return policy


def _moderation_state_for_action(action: str) -> str:
	mapping = {
		"approve": "Approved",
		"return_for_edit": "Returned for Edit",
		"hide": "Hidden / Rejected",
	}
	key = (action or "").strip().lower()
	state = mapping.get(key)
	if not state:
		frappe.throw(_("Invalid moderation action. Use approve, return_for_edit, or hide."))
	return state


def _ensure_can_moderate_portfolio_item(
	*,
	school: str,
	student: str,
	user_roles: set[str],
	policy_cache: Dict[str, Dict[str, Any]],
	visibility_cache: Dict[tuple[str, str], bool],
) -> Dict[str, Any]:
	if "Student" in user_roles or "Guardian" in user_roles:
		frappe.throw(_("Only staff moderators can moderate portfolio showcase items."), frappe.PermissionError)

	policy = policy_cache.get(school)
	if policy is None:
		policy = _resolve_moderation_policy_for_school(school)
		policy_cache[school] = policy

	if not policy.get("enable_moderation"):
		frappe.throw(_("Moderation is disabled for this school."), frappe.PermissionError)
	if policy.get("moderation_scope") not in {"Showcase only", "Both"}:
		frappe.throw(_("Showcase moderation is disabled for this school."), frappe.PermissionError)

	if user_roles & ADMIN_ROLES:
		return policy

	key = (student, school)
	allowed = visibility_cache.get(key)
	if allowed is None:
		scope = _resolve_actor_scope(requested_students=[student], school_filter=school)
		allowed = scope.get("role") == "Staff" and bool(scope.get("students") or scope.get("all_students"))
		visibility_cache[key] = allowed
	if not allowed:
		frappe.throw(_("Not permitted to moderate this student's portfolio in the selected school."), frappe.PermissionError)

	showcase_roles = set(policy.get("showcase_roles") or set())
	if not showcase_roles or not (user_roles & showcase_roles):
		frappe.throw(_("You are not in this school's showcase moderation roles."), frappe.PermissionError)

	return policy


def _get_or_create_portfolio(student: str, academic_year: str, school: str) -> str:
	portfolio_name = frappe.db.get_value(
		"Student Portfolio",
		{"student": student, "academic_year": academic_year, "school": school},
		"name",
	)
	if portfolio_name:
		return portfolio_name

	organization = frappe.db.get_value("School", school, "organization")
	if not organization:
		frappe.throw(_("Organization is required for this school."))

	doc = frappe.get_doc(
		{
			"doctype": "Student Portfolio",
			"student": student,
			"academic_year": academic_year,
			"school": school,
			"organization": organization,
			"title": f"Portfolio {academic_year}",
			"status": "Draft",
			"showcase_enabled": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _portfolio_item_dict(row: Dict[str, Any], tags_map: Dict[str, list[Dict[str, Any]]], evidence_map: Dict[str, Dict[str, Any]]):
	item_name = row.get("item_name")
	return {
		"item_name": item_name,
		"portfolio": row.get("portfolio"),
		"student": row.get("student"),
		"student_name": row.get("student_full_name") or row.get("student"),
		"academic_year": row.get("academic_year"),
		"school": row.get("school"),
		"item_type": row.get("item_type"),
		"task_submission": row.get("task_submission"),
		"student_reflection_entry": row.get("student_reflection_entry"),
		"artefact_file": row.get("artefact_file"),
		"evidence_date": row.get("evidence_date"),
		"program_enrollment": row.get("program_enrollment"),
		"caption": row.get("caption"),
		"reflection_summary": row.get("reflection_summary"),
		"display_order": row.get("display_order") or 0,
		"is_showcase": int(row.get("is_showcase") or 0) == 1,
		"moderation_state": row.get("moderation_state") or "Draft",
		"tags": tags_map.get(item_name, []),
		"evidence": evidence_map.get(item_name, {}),
	}


def _load_item_tags(item_names: list[str]) -> Dict[str, list[Dict[str, Any]]]:
	if not item_names:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT
			et.name,
			et.target_name,
			et.tag_taxonomy,
			tt.title AS tag_title,
			et.tagged_by_type,
			et.tagged_by_id
		FROM `tabEvidence Tag` et
		LEFT JOIN `tabTag Taxonomy` tt ON tt.name = et.tag_taxonomy
		WHERE et.target_doctype = 'Student Portfolio Item'
		  AND et.target_name IN %(item_names)s
		ORDER BY et.creation ASC
		""",
		{"item_names": tuple(item_names)},
		as_dict=True,
	)
	out: Dict[str, list[Dict[str, Any]]] = {}
	for row in rows:
		target = row.get("target_name")
		if not target:
			continue
		out.setdefault(target, []).append(
			{
				"name": row.get("name"),
				"tag_taxonomy": row.get("tag_taxonomy"),
				"title": row.get("tag_title") or row.get("tag_taxonomy"),
				"tagged_by_type": row.get("tagged_by_type"),
				"tagged_by_id": row.get("tagged_by_id"),
			}
		)
	return out


def _load_item_evidence(rows: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
	item_map: Dict[str, Dict[str, Any]] = {}
	task_submissions = sorted({row.get("task_submission") for row in rows if row.get("task_submission")})
	reflections = sorted({row.get("student_reflection_entry") for row in rows if row.get("student_reflection_entry")})
	files = sorted({row.get("artefact_file") for row in rows if row.get("artefact_file")})

	task_map = {}
	if task_submissions:
		task_rows = frappe.get_all(
			"Task Submission",
			filters={"name": ["in", task_submissions]},
			fields=["name", "submitted_on", "text_content", "link_url"],
		)
		task_map = {row.get("name"): row for row in task_rows if row.get("name")}

	reflection_map = {}
	if reflections:
		reflection_rows = frappe.get_all(
			"Student Reflection Entry",
			filters={"name": ["in", reflections]},
			fields=["name", "entry_date", "entry_type", "body", "visibility"],
		)
		reflection_map = {row.get("name"): row for row in reflection_rows if row.get("name")}

	file_map = {}
	if files:
		file_rows = frappe.get_all(
			"File",
			filters={"name": ["in", files]},
			fields=["name", "file_name", "file_url", "file_size"],
		)
		file_map = {row.get("name"): row for row in file_rows if row.get("name")}

	for row in rows:
		item_name = row.get("item_name")
		if not item_name:
			continue
		if row.get("item_type") == "Task Submission" and row.get("task_submission"):
			task = task_map.get(row.get("task_submission"), {})
			item_map[item_name] = {
				"kind": "task_submission",
				"submitted_on": task.get("submitted_on"),
				"text_preview": (task.get("text_content") or "")[:280],
				"link_url": task.get("link_url"),
			}
		elif row.get("item_type") == "Student Reflection Entry" and row.get("student_reflection_entry"):
			reflection = reflection_map.get(row.get("student_reflection_entry"), {})
			item_map[item_name] = {
				"kind": "reflection",
				"entry_date": reflection.get("entry_date"),
				"entry_type": reflection.get("entry_type"),
				"visibility": reflection.get("visibility"),
				"text_preview": strip_html(reflection.get("body") or "")[:280],
			}
		elif row.get("item_type") == "External Artefact" and row.get("artefact_file"):
			file_row = file_map.get(row.get("artefact_file"), {})
			item_map[item_name] = {
				"kind": "external_file",
				"file_name": file_row.get("file_name"),
				"file_url": file_row.get("file_url"),
				"file_size": file_row.get("file_size"),
			}
	return item_map


def _build_portfolio_feed(data: Dict[str, Any]) -> Dict[str, Any]:
	student_ids = _normalize_to_list(data.get("student_ids"))
	tag_ids = _normalize_to_list(data.get("tag_ids"))
	school_filter = (data.get("school") or "").strip() or None
	scope = _resolve_actor_scope(requested_students=student_ids, school_filter=school_filter)
	role = scope.get("role")
	allowed_students = scope.get("students") or []

	if not allowed_students and not scope.get("all_students"):
		return {
			"items": [],
			"total": 0,
			"page": 1,
			"page_length": 20,
			"actor_role": role,
			"scope_students": allowed_students,
		}

	date_from = data.get("date_from")
	date_to = data.get("date_to")	
	academic_year = (data.get("academic_year") or "").strip() or None
	program_enrollment = (data.get("program_enrollment") or "").strip() or None
	show_showcase_only = int(data.get("show_showcase_only") or 0) == 1

	page = max(int(data.get("page") or 1), 1)
	page_length = min(max(int(data.get("page_length") or 20), 1), 100)
	offset = (page - 1) * page_length

	conditions = ["p.name = pi.parent", "p.docstatus < 2"]
	params: Dict[str, Any] = {}

	if scope.get("all_students") and not allowed_students:
		pass
	else:
		conditions.append("p.student IN %(students)s")
		params["students"] = tuple(allowed_students)

	if school_filter:
		conditions.append("p.school = %(school)s")
		params["school"] = school_filter
	if academic_year:
		conditions.append("p.academic_year = %(academic_year)s")
		params["academic_year"] = academic_year
	if program_enrollment:
		conditions.append("pi.program_enrollment = %(program_enrollment)s")
		params["program_enrollment"] = program_enrollment

	if date_from:
		conditions.append("IFNULL(pi.evidence_date, DATE(pi.modified)) >= %(date_from)s")
		params["date_from"] = getdate(date_from)
	if date_to:
		conditions.append("IFNULL(pi.evidence_date, DATE(pi.modified)) <= %(date_to)s")
		params["date_to"] = getdate(date_to)

	if role == "Guardian":
		conditions.append("p.showcase_enabled = 1")
		conditions.append("pi.is_showcase = 1")
		conditions.append("pi.moderation_state = 'Approved'")
	elif show_showcase_only:
		conditions.append("pi.is_showcase = 1")
		conditions.append("pi.moderation_state = 'Approved'")

	if tag_ids:
		conditions.append(
			"""
			EXISTS (
				SELECT 1
				FROM `tabEvidence Tag` et
				WHERE et.target_doctype = 'Student Portfolio Item'
				  AND et.target_name = pi.name
				  AND et.tag_taxonomy IN %(tag_ids)s
			)
			"""
		)
		params["tag_ids"] = tuple(tag_ids)

	where_clause = " AND ".join(conditions)

	count_row = frappe.db.sql(
		f"""
		SELECT COUNT(*) AS total
		FROM `tabStudent Portfolio Item` pi
		JOIN `tabStudent Portfolio` p ON {where_clause}
		""",
		params,
		as_dict=True,
	)
	total = int((count_row[0] or {}).get("total") or 0)

	rows = frappe.db.sql(
		f"""
		SELECT
			pi.name AS item_name,
			pi.parent AS portfolio,
			p.student,
			s.student_full_name,
			p.academic_year,
			p.school,
			pi.item_type,
			pi.task_submission,
			pi.student_reflection_entry,
			pi.artefact_file,
			pi.evidence_date,
			pi.program_enrollment,
			pi.caption,
			pi.reflection_summary,
			pi.display_order,
			pi.is_showcase,
			pi.moderation_state
		FROM `tabStudent Portfolio Item` pi
		JOIN `tabStudent Portfolio` p ON {where_clause}
		LEFT JOIN `tabStudent` s ON s.name = p.student
		ORDER BY IFNULL(pi.evidence_date, DATE(pi.modified)) DESC, pi.modified DESC
		LIMIT %(page_length)s OFFSET %(offset)s
		""",
		{
			**params,
			"page_length": page_length,
			"offset": offset,
		},
		as_dict=True,
	)

	item_names = [row.get("item_name") for row in rows if row.get("item_name")]
	tags_map = _load_item_tags(item_names)
	evidence_map = _load_item_evidence(rows)

	items = [_portfolio_item_dict(row, tags_map, evidence_map) for row in rows]
	return {
		"items": items,
		"total": total,
		"page": page,
		"page_length": page_length,
		"actor_role": role,
		"scope_students": allowed_students,
	}


@frappe.whitelist()
def get_portfolio_feed(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	return _build_portfolio_feed(data)


@frappe.whitelist()
def create_reflection_entry(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	student = (data.get("student") or "").strip()
	if not student:
		frappe.throw(_("Student is required."))

	_ensure_can_write_student(student)

	academic_year = (data.get("academic_year") or "").strip()
	school = (data.get("school") or "").strip()

	program_enrollment = (data.get("program_enrollment") or "").strip()
	if program_enrollment:
		pe_ctx = frappe.db.get_value(
			"Program Enrollment",
			program_enrollment,
			["student", "academic_year", "school"],
			as_dict=True,
		)
		if pe_ctx and pe_ctx.get("student") == student:
			academic_year = academic_year or (pe_ctx.get("academic_year") or "")
			school = school or (pe_ctx.get("school") or "")

	task_submission = (data.get("task_submission") or "").strip()
	if task_submission:
		ts_ctx = frappe.db.get_value(
			"Task Submission",
			task_submission,
			["student", "academic_year", "school"],
			as_dict=True,
		)
		if ts_ctx and ts_ctx.get("student") == student:
			academic_year = academic_year or (ts_ctx.get("academic_year") or "")
			school = school or (ts_ctx.get("school") or "")

	if not school:
		school = frappe.db.get_value("Student", student, "anchor_school")
	if not academic_year:
		latest_pe = frappe.get_all(
			"Program Enrollment",
			filters={"student": student, "archived": 0},
			fields=["academic_year"],
			order_by="enrollment_date desc, modified desc",
			limit_page_length=1,
		)
		academic_year = (latest_pe[0] or {}).get("academic_year") if latest_pe else None
	if not school:
		frappe.throw(_("School is required."))
	if not academic_year:
		frappe.throw(_("Academic year is required."))

	settings = _resolve_settings_for_school(school)
	organization = (data.get("organization") or "").strip() or frappe.db.get_value("School", school, "organization")

	doc = frappe.get_doc(
		{
			"doctype": "Student Reflection Entry",
			"student": student,
			"academic_year": academic_year,
			"school": school,
			"organization": organization,
			"entry_date": data.get("entry_date") or today(),
			"entry_type": data.get("entry_type") or "Reflection",
			"visibility": data.get("visibility") or settings.get("default_visibility_for_reflection") or "Teacher",
			"moderation_state": data.get("moderation_state") or "Draft",
			"mood_scale": data.get("mood_scale"),
			"body": data.get("body"),
			"course": data.get("course"),
			"student_group": data.get("student_group"),
			"program_enrollment": program_enrollment or None,
			"activity_booking": data.get("activity_booking"),
			"lesson": data.get("lesson"),
			"lesson_instance": data.get("lesson_instance"),
			"lesson_activity": data.get("lesson_activity"),
			"task_delivery": data.get("task_delivery"),
			"task_submission": task_submission or None,
		}
	)
	doc.insert(ignore_permissions=True)
	return {
		"name": doc.name,
		"student": doc.student,
		"academic_year": doc.academic_year,
		"entry_date": doc.entry_date,
		"moderation_state": doc.moderation_state,
	}


@frappe.whitelist()
def list_reflection_entries(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	requested_students = _normalize_to_list(data.get("student_ids") or data.get("students"))
	scope = _resolve_actor_scope(requested_students=requested_students, school_filter=(data.get("school") or "").strip() or None)
	if scope.get("role") == "Guardian":
		return {"items": [], "total": 0, "page": 1, "page_length": 20}

	students = scope.get("students") or []
	if not students and not scope.get("all_students"):
		return {"items": [], "total": 0, "page": 1, "page_length": 20}

	page = max(int(data.get("page") or 1), 1)
	page_length = min(max(int(data.get("page_length") or 20), 1), 100)
	offset = (page - 1) * page_length

	filters: Dict[str, Any] = {}
	if not scope.get("all_students"):
		filters["student"] = ["in", students]
	if data.get("academic_year"):
		filters["academic_year"] = data.get("academic_year")
	if data.get("program_enrollment"):
		filters["program_enrollment"] = data.get("program_enrollment")
	if data.get("school"):
		filters["school"] = data.get("school")

	if data.get("date_from") and data.get("date_to"):
		filters["entry_date"] = ["between", [data.get("date_from"), data.get("date_to")]]
	elif data.get("date_from"):
		filters["entry_date"] = [">=", data.get("date_from")]
	elif data.get("date_to"):
		filters["entry_date"] = ["<=", data.get("date_to")]

	total = frappe.db.count("Student Reflection Entry", filters)
	rows = frappe.get_all(
		"Student Reflection Entry",
		filters=filters,
		fields=[
			"name",
			"student",
			"academic_year",
			"school",
			"entry_date",
			"entry_type",
			"visibility",
			"moderation_state",
			"body",
		],
		order_by="entry_date desc, modified desc",
		start=offset,
		page_length=page_length,
	)

	for row in rows:
		row["body_preview"] = strip_html(row.get("body") or "")[:280]

	return {
		"items": rows,
		"total": total,
		"page": page,
		"page_length": page_length,
	}


def _default_showcase_state(*, school: str, is_showcase: bool) -> str:
	if not is_showcase:
		return "Draft"
	settings = _resolve_settings_for_school(school)
	if int(settings.get("enable_moderation") or 0) != 1:
		return "Approved"
	scope = (settings.get("moderation_scope") or "Showcase only").strip()
	if scope in {"Showcase only", "Both"} and int(settings.get("require_teacher_approval_for_showcase") or 0) == 1:
		return "Submitted for Review"
	return "Approved"


def _compose_item_payload(data: Dict[str, Any], *, school: str) -> Dict[str, Any]:
	item_type = data.get("item_type")
	task_submission = data.get("task_submission")
	reflection = data.get("student_reflection_entry")
	artefact_file = data.get("artefact_file")
	references = [bool(task_submission), bool(reflection), bool(artefact_file)]
	if sum(references) != 1:
		frappe.throw(_("Exactly one evidence reference is required."))

	evidence_date = data.get("evidence_date")
	if not evidence_date and task_submission:
		evidence_date = frappe.db.get_value("Task Submission", task_submission, "submitted_on")
	if not evidence_date and reflection:
		evidence_date = frappe.db.get_value("Student Reflection Entry", reflection, "entry_date")
	if evidence_date:
		evidence_date = get_datetime(evidence_date).date()

	is_showcase = int(data.get("is_showcase") or 0) == 1
	moderation_state = data.get("moderation_state") or _default_showcase_state(school=school, is_showcase=is_showcase)

	return {
		"item_type": item_type,
		"task_submission": task_submission,
		"student_reflection_entry": reflection,
		"artefact_file": artefact_file,
		"evidence_date": evidence_date,
		"program_enrollment": data.get("program_enrollment"),
		"caption": data.get("caption"),
		"reflection_summary": data.get("reflection_summary"),
		"display_order": data.get("display_order") or 0,
		"is_showcase": 1 if is_showcase else 0,
		"show_tags": 1 if int(data.get("show_tags") if data.get("show_tags") is not None else 1) == 1 else 0,
		"moderation_state": moderation_state,
	}


@frappe.whitelist()
def add_portfolio_item(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	student = (data.get("student") or "").strip()
	academic_year = (data.get("academic_year") or "").strip()
	school = (data.get("school") or "").strip()

	portfolio_name = (data.get("portfolio") or "").strip()
	if portfolio_name:
		portfolio = frappe.get_doc("Student Portfolio", portfolio_name)
		student = student or portfolio.student
		academic_year = academic_year or portfolio.academic_year
		school = school or portfolio.school
	else:
		if not (student and academic_year and school):
			frappe.throw(_("student, academic_year, and school are required when portfolio is not provided."))

	_ensure_can_write_student(student)
	portfolio_name = portfolio_name or _get_or_create_portfolio(student, academic_year, school)
	portfolio = frappe.get_doc("Student Portfolio", portfolio_name)

	item_payload = _compose_item_payload(data, school=school)
	row = portfolio.append("items", item_payload)
	portfolio.save(ignore_permissions=True)

	return {
		"portfolio": portfolio.name,
		"item_name": row.name,
		"moderation_state": row.moderation_state,
	}


@frappe.whitelist()
def update_portfolio_item(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	item_name = (data.get("item_name") or "").strip()
	if not item_name:
		frappe.throw(_("item_name is required."))

	portfolio_name = frappe.db.get_value("Student Portfolio Item", item_name, "parent")
	if not portfolio_name:
		frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)

	portfolio = frappe.get_doc("Student Portfolio", portfolio_name)
	_ensure_can_write_student(portfolio.student)

	row = next((item for item in portfolio.items if item.name == item_name), None)
	if not row:
		frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)

	allowed_fields = {
		"caption",
		"reflection_summary",
		"display_order",
		"show_tags",
		"program_enrollment",
		"evidence_date",
		"moderation_comment",
	}
	for fieldname in allowed_fields:
		if fieldname in data:
			setattr(row, fieldname, data.get(fieldname))

	if "is_showcase" in data:
		is_showcase = int(data.get("is_showcase") or 0) == 1
		row.is_showcase = 1 if is_showcase else 0
		if not is_showcase:
			row.moderation_state = "Draft"
		else:
			row.moderation_state = _default_showcase_state(school=portfolio.school, is_showcase=True)

	portfolio.save(ignore_permissions=True)
	return {
		"portfolio": portfolio.name,
		"item_name": row.name,
		"moderation_state": row.moderation_state,
		"is_showcase": int(row.is_showcase or 0) == 1,
	}


@frappe.whitelist()
def set_showcase_state(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	item_name = (data.get("item_name") or "").strip()
	if not item_name:
		frappe.throw(_("item_name is required."))

	portfolio_name = frappe.db.get_value("Student Portfolio Item", item_name, "parent")
	if not portfolio_name:
		frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)

	portfolio = frappe.get_doc("Student Portfolio", portfolio_name)
	_ensure_can_write_student(portfolio.student)

	row = next((item for item in portfolio.items if item.name == item_name), None)
	if not row:
		frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)

	is_showcase = int(data.get("is_showcase") or 0) == 1
	row.is_showcase = 1 if is_showcase else 0
	if not is_showcase:
		row.moderation_state = "Draft"
	else:
		row.moderation_state = _default_showcase_state(school=portfolio.school, is_showcase=True)

	portfolio.save(ignore_permissions=True)
	return {
		"item_name": row.name,
		"is_showcase": int(row.is_showcase or 0) == 1,
		"moderation_state": row.moderation_state,
	}


@frappe.whitelist()
def moderate_portfolio_items(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	action = (data.get("action") or "").strip()
	item_names = _normalize_to_list(data.get("item_names"))
	if not item_names:
		frappe.throw(_("item_names is required."))

	target_state = _moderation_state_for_action(action)
	user = _require_authenticated_user()
	user_roles = _user_roles(user)
	if "Student" in user_roles or "Guardian" in user_roles:
		frappe.throw(_("Only staff moderators can moderate portfolio showcase items."), frappe.PermissionError)

	rows = frappe.db.sql(
		"""
		SELECT
			pi.name AS item_name,
			p.student,
			p.school
		FROM `tabStudent Portfolio Item` pi
		JOIN `tabStudent Portfolio` p ON p.name = pi.parent
		WHERE pi.name IN %(item_names)s
		""",
		{"item_names": tuple(item_names)},
		as_dict=True,
	)
	rows_by_name = {row.get("item_name"): row for row in rows if row.get("item_name")}

	moderation_comment = data.get("moderation_comment")
	if moderation_comment is not None:
		moderation_comment = str(moderation_comment).strip()

	policy_cache: Dict[str, Dict[str, Any]] = {}
	visibility_cache: Dict[tuple[str, str], bool] = {}
	results = []
	updated = 0

	for item_name in item_names:
		row = rows_by_name.get(item_name)
		if not row:
			results.append({"item_name": item_name, "ok": False, "error": _("Portfolio item not found.")})
			continue
		school = row.get("school")
		student = row.get("student")
		if not school or not student:
			results.append({"item_name": item_name, "ok": False, "error": _("Portfolio item context is incomplete.")})
			continue

		try:
			_ensure_can_moderate_portfolio_item(
				school=school,
				student=student,
				user_roles=user_roles,
				policy_cache=policy_cache,
				visibility_cache=visibility_cache,
			)
			values = {
				"moderation_state": target_state,
				"reviewed_by": user,
				"reviewed_on": now_datetime(),
			}
			if moderation_comment is not None:
				values["moderation_comment"] = moderation_comment
			if target_state == "Hidden / Rejected":
				values["is_showcase"] = 0

			frappe.db.set_value("Student Portfolio Item", item_name, values, update_modified=True)
			updated += 1
			results.append({"item_name": item_name, "ok": True, "moderation_state": target_state})
		except Exception as exc:
			results.append(
				{
					"item_name": item_name,
					"ok": False,
					"error": str(exc) or _("Could not moderate this item."),
				}
			)

	return {
		"action": action,
		"moderation_state": target_state,
		"updated": updated,
		"results": results,
	}


def _resolve_target_student(target_doctype: str, target_name: str) -> str | None:
	if target_doctype == "Task Submission":
		return frappe.db.get_value("Task Submission", target_name, "student")
	if target_doctype == "Student Reflection Entry":
		return frappe.db.get_value("Student Reflection Entry", target_name, "student")
	if target_doctype == "Student Portfolio Item":
		portfolio = frappe.db.get_value("Student Portfolio Item", target_name, "parent")
		if portfolio:
			return frappe.db.get_value("Student Portfolio", portfolio, "student")
	return None


def _resolve_tag_actor(student: str | None) -> tuple[str, str]:
	user = _require_authenticated_user()
	roles = _user_roles(user)
	if "Student" in roles:
		student_name = _resolve_student_for_user(user)
		if not student_name or (student and student != student_name):
			frappe.throw(_("Students can only tag their own evidence."), frappe.PermissionError)
		return "Student", student_name

	employee_name = frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, "name")
	if employee_name:
		return "Employee", employee_name
	return "System", user


@frappe.whitelist()
def apply_evidence_tag(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	target_doctype = (data.get("target_doctype") or "").strip()
	target_name = (data.get("target_name") or "").strip()
	tag_taxonomy = (data.get("tag_taxonomy") or "").strip()
	if not (target_doctype and target_name and tag_taxonomy):
		frappe.throw(_("target_doctype, target_name, and tag_taxonomy are required."))

	student = _resolve_target_student(target_doctype, target_name)
	if student:
		_ensure_can_write_student(student)
	tagged_by_type, tagged_by_id = _resolve_tag_actor(student)

	doc = frappe.get_doc(
		{
			"doctype": "Evidence Tag",
			"target_doctype": target_doctype,
			"target_name": target_name,
			"tag_taxonomy": tag_taxonomy,
			"scope": data.get("scope") or "portfolio",
			"tagged_by_type": tagged_by_type,
			"tagged_by_id": tagged_by_id,
			"student": student,
		}
	)
	doc.insert(ignore_permissions=True)
	return {
		"name": doc.name,
		"target_doctype": doc.target_doctype,
		"target_name": doc.target_name,
		"tag_taxonomy": doc.tag_taxonomy,
	}


@frappe.whitelist()
def remove_evidence_tag(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	tag_name = (data.get("name") or data.get("tag_name") or "").strip()
	if not tag_name:
		frappe.throw(_("name is required."))

	row = frappe.db.get_value(
		"Evidence Tag",
		tag_name,
		[
			"name",
			"target_doctype",
			"target_name",
			"student",
			"tagged_by_type",
			"tagged_by_id",
			"owner",
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Evidence tag not found."), frappe.DoesNotExistError)

	user = _require_authenticated_user()
	roles = _user_roles(user)
	student = row.get("student") or _resolve_target_student(row.get("target_doctype"), row.get("target_name"))

	can_delete = False
	if roles & STAFF_ROLES:
		if student:
			_ensure_can_write_student(student)
		can_delete = True
	elif "Student" in roles:
		own_student = _resolve_student_for_user(user)
		if row.get("tagged_by_type") == "Student" and row.get("tagged_by_id") == own_student:
			can_delete = True

	if not can_delete:
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	frappe.delete_doc("Evidence Tag", tag_name, ignore_permissions=True)
	return {"ok": True}


def _token_hash(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _deterministic_share_token(*, portfolio: str, user: str, idempotency_key: str) -> str:
	secret = frappe.local.conf.get("encryption_key") or frappe.local.conf.get("secret") or frappe.local.site
	msg = f"{portfolio}|{user}|{idempotency_key}".encode("utf-8")
	digest = hmac.new(str(secret).encode("utf-8"), msg, hashlib.sha256).hexdigest()
	return digest


def _share_url(token: str) -> str:
	return f"{frappe.utils.get_url()}/portfolio/share/{token}"


def _assert_share_window(expires_on: str, max_days: int):
	exp = getdate(expires_on)
	if exp < getdate(today()):
		frappe.throw(_("Share link expiry cannot be in the past."))
	if exp > add_days(getdate(today()), int(max_days or 30)):
		frappe.throw(_("Share link expiry exceeds the configured maximum days."))


@frappe.whitelist()
def create_portfolio_share_link(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	portfolio_name = (data.get("portfolio") or "").strip()
	expires_on = data.get("expires_on")
	if not portfolio_name or not expires_on:
		frappe.throw(_("portfolio and expires_on are required."))

	portfolio = frappe.get_doc("Student Portfolio", portfolio_name)
	scope = _ensure_can_write_student(portfolio.student)
	settings = _resolve_settings_for_school(portfolio.school)
	if scope.get("role") == "Student" and int(settings.get("allow_student_external_share") or 0) != 1:
		frappe.throw(_("Students cannot create external share links for this school."), frappe.PermissionError)

	_assert_share_window(expires_on, int(settings.get("share_link_max_days") or 30))

	user = _require_authenticated_user()
	idempotency_key = (data.get("idempotency_key") or "").strip() or None
	if idempotency_key:
		existing = frappe.db.get_value(
			"Portfolio Share Link",
			{"portfolio": portfolio_name, "idempotency_key": idempotency_key, "created_by_user": user},
			["name", "expires_on", "allow_download"],
			as_dict=True,
		)
		token = _deterministic_share_token(portfolio=portfolio_name, user=user, idempotency_key=idempotency_key)
		if existing:
			return {
				"name": existing.get("name"),
				"share_url": _share_url(token),
				"token": token,
				"expires_on": existing.get("expires_on"),
				"allow_download": int(existing.get("allow_download") or 0) == 1,
			}
	else:
		token = frappe.generate_hash(length=48)

	token_hash = _token_hash(token)
	doc = frappe.get_doc(
		{
			"doctype": "Portfolio Share Link",
			"portfolio": portfolio_name,
			"scope": "Showcase Only",
			"expires_on": expires_on,
			"access_mode": "view",
			"allowed_viewer_email": data.get("allowed_viewer_email"),
			"allow_download": 1 if int(data.get("allow_download") or settings.get("allow_external_download") or 0) == 1 else 0,
			"token_hash": token_hash,
			"token_hint": token[-8:],
			"idempotency_key": idempotency_key,
			"revoked": 0,
			"created_by_user": user,
			"school": portfolio.school,
			"organization": portfolio.organization,
		}
	)
	try:
		doc.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		existing = frappe.db.get_value(
			"Portfolio Share Link",
			{"token_hash": token_hash},
			["name", "expires_on", "allow_download"],
			as_dict=True,
		)
		if not existing:
			raise
		return {
			"name": existing.get("name"),
			"share_url": _share_url(token),
			"token": token,
			"expires_on": existing.get("expires_on"),
			"allow_download": int(existing.get("allow_download") or 0) == 1,
		}

	return {
		"name": doc.name,
		"share_url": _share_url(token),
		"token": token,
		"expires_on": doc.expires_on,
		"allow_download": int(doc.allow_download or 0) == 1,
	}


@frappe.whitelist()
def revoke_portfolio_share_link(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	name = (data.get("name") or "").strip()
	if not name:
		frappe.throw(_("name is required."))

	doc = frappe.get_doc("Portfolio Share Link", name)
	portfolio_student = frappe.db.get_value("Student Portfolio", doc.portfolio, "student")
	_ensure_can_write_student(portfolio_student)
	doc.revoked = 1
	doc.save(ignore_permissions=True)
	return {"ok": True, "name": doc.name}


def resolve_portfolio_share_context(token: str, viewer_email: str | None = None) -> Dict[str, Any]:
	if not token:
		frappe.throw(_("Invalid share token."), frappe.PermissionError)

	row = frappe.db.get_value(
		"Portfolio Share Link",
		{"token_hash": _token_hash(token)},
		[
			"name",
			"portfolio",
			"expires_on",
			"revoked",
			"allow_download",
			"allowed_viewer_email",
		],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Invalid share token."), frappe.PermissionError)
	if int(row.get("revoked") or 0) == 1:
		frappe.throw(_("This share link has been revoked."), frappe.PermissionError)
	if getdate(row.get("expires_on")) < getdate(today()):
		frappe.throw(_("This share link has expired."), frappe.PermissionError)

	allowed_email = (row.get("allowed_viewer_email") or "").strip().lower()
	if allowed_email and (viewer_email or "").strip().lower() != allowed_email:
		frappe.throw(_("This share link is restricted to a specific viewer email."), frappe.PermissionError)

	portfolio = frappe.get_doc("Student Portfolio", row.get("portfolio"))
	student = frappe.db.get_value(
		"Student",
		portfolio.student,
		["name", "student_full_name", "student_preferred_name"],
		as_dict=True,
	)
	file_map = {}
	file_names = [item.artefact_file for item in (portfolio.items or []) if item.artefact_file]
	if file_names:
		file_rows = frappe.get_all(
			"File",
			filters={"name": ["in", file_names]},
			fields=["name", "file_url", "file_name"],
		)
		file_map = {f.get("name"): f for f in file_rows if f.get("name")}
	items = []
	for item in portfolio.items or []:
		if int(item.is_showcase or 0) != 1:
			continue
		if (item.moderation_state or "") != "Approved":
			continue
		items.append(
			{
				"item_name": item.name,
				"item_type": item.item_type,
				"caption": item.caption,
				"reflection_summary": item.reflection_summary,
				"evidence_date": item.evidence_date,
				"task_submission": item.task_submission,
				"student_reflection_entry": item.student_reflection_entry,
				"artefact_file": item.artefact_file,
				"artefact_file_url": (file_map.get(item.artefact_file) or {}).get("file_url"),
				"artefact_file_name": (file_map.get(item.artefact_file) or {}).get("file_name"),
			}
		)

	frappe.db.set_value(
		"Portfolio Share Link",
		row.get("name"),
		{
			"last_accessed_on": now_datetime(),
			"last_accessed_ip": frappe.local.request_ip if frappe.request else None,
		},
		update_modified=True,
	)

	return {
		"share_link": {
			"name": row.get("name"),
			"allow_download": int(row.get("allow_download") or 0) == 1,
			"expires_on": row.get("expires_on"),
		},
		"portfolio": {
			"name": portfolio.name,
			"title": portfolio.showcase_title or portfolio.title,
			"subtitle": portfolio.showcase_subtitle,
			"student": portfolio.student,
			"student_name": (student or {}).get("student_preferred_name")
			or (student or {}).get("student_full_name")
			or portfolio.student,
			"academic_year": portfolio.academic_year,
			"items": items,
		},
	}


def _render_portfolio_pdf_html(feed: Dict[str, Any], title: str) -> str:
	rows = []
	for item in feed.get("items", []):
		tags = ", ".join(tag.get("title") for tag in item.get("tags") or [])
		evidence = item.get("evidence") or {}
		preview = evidence.get("text_preview") or ""
		rows.append(
			f"""
			<section style=\"margin-bottom:18px;padding:12px;border:1px solid #ddd;border-radius:8px;\">
				<h3 style=\"margin:0 0 6px 0;\">{frappe.utils.escape_html(item.get('caption') or item.get('item_type') or 'Portfolio Item')}</h3>
				<p style=\"margin:0 0 6px 0;color:#444;\">Date: {item.get('evidence_date') or ''}</p>
				<p style=\"margin:0 0 6px 0;color:#444;\">{frappe.utils.escape_html(item.get('reflection_summary') or '')}</p>
				<p style=\"margin:0 0 6px 0;color:#666;\">{frappe.utils.escape_html(preview)}</p>
				<p style=\"margin:0;color:#666;font-size:12px;\">Tags: {frappe.utils.escape_html(tags)}</p>
			</section>
			"""
		)
	content = "".join(rows) or "<p>No items matched the current filters.</p>"
	return f"""
	<html>
		<body style=\"font-family: Helvetica, Arial, sans-serif;\">
			<h1>{frappe.utils.escape_html(title)}</h1>
			{content}
		</body>
	</html>
	"""


def _render_reflection_pdf_html(rows: List[Dict[str, Any]], title: str) -> str:
	sections = []
	for row in rows:
		sections.append(
			f"""
			<section style=\"margin-bottom:18px;padding:12px;border:1px solid #ddd;border-radius:8px;\">
				<h3 style=\"margin:0 0 6px 0;\">{frappe.utils.escape_html(row.get('entry_type') or 'Reflection')}</h3>
				<p style=\"margin:0 0 6px 0;color:#444;\">Date: {row.get('entry_date') or ''}</p>
				<div style=\"color:#222;\">{row.get('body') or ''}</div>
			</section>
			"""
		)
	content = "".join(sections) or "<p>No reflections matched the current filters.</p>"
	return f"""
	<html>
		<body style=\"font-family: Helvetica, Arial, sans-serif;\">
			<h1>{frappe.utils.escape_html(title)}</h1>
			{content}
		</body>
	</html>
	"""


def _dispatch_export_file(
	*,
	student: str,
	school: str,
	purpose: str,
	slot: str,
	file_name: str,
	content: bytes,
):
	from ifitwala_ed.utilities import file_dispatcher

	organization = frappe.db.get_value("School", school, "organization")
	if not organization:
		frappe.throw(_("Organization is required for exports."))

	return file_dispatcher.create_and_classify_file(
		file_kwargs={
			"attached_to_doctype": "Student",
			"attached_to_name": student,
			"is_private": 1,
			"file_name": file_name,
			"content": content,
		},
		classification={
			"primary_subject_type": "Student",
			"primary_subject_id": student,
			"data_class": "academic",
			"purpose": purpose,
			"retention_policy": "immediate_on_request",
			"slot": slot,
			"organization": organization,
			"school": school,
			"upload_source": "API",
		},
	)


@frappe.whitelist()
def export_portfolio_pdf(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	feed = _build_portfolio_feed(data)
	if not feed.get("items"):
		frappe.throw(_("No portfolio items matched your filters."))

	students = sorted({item.get("student") for item in feed.get("items", []) if item.get("student")})
	if len(students) != 1:
		frappe.throw(_("Please filter to one student before exporting a portfolio PDF."))

	student = students[0]
	_ensure_can_write_student(student)
	school = frappe.db.get_value("Student", student, "anchor_school")
	settings = _resolve_settings_for_school(school)
	if int(settings.get("allow_pdf_export") or 0) != 1:
		frappe.throw(_("PDF export is disabled for this school."), frappe.PermissionError)

	from frappe.utils.pdf import get_pdf

	html = _render_portfolio_pdf_html(feed, title=_("Portfolio Export"))
	pdf_content = get_pdf(html)
	file_doc = _dispatch_export_file(
		student=student,
		school=school,
		purpose="portfolio_export",
		slot="portfolio_export_pdf",
		file_name=f"portfolio-export-{student}-{today()}.pdf",
		content=pdf_content,
	)
	return {
		"file_url": file_doc.file_url,
		"file_name": file_doc.file_name,
		"student": student,
	}


@frappe.whitelist()
def export_reflection_pdf(payload=None, **kwargs):
	data = _normalize_payload(payload, kwargs)
	rows_payload = list_reflection_entries(data)
	rows = rows_payload.get("items") or []
	if not rows:
		frappe.throw(_("No reflection entries matched your filters."))

	students = sorted({row.get("student") for row in rows if row.get("student")})
	if len(students) != 1:
		frappe.throw(_("Please filter to one student before exporting reflection PDF."))

	student = students[0]
	_ensure_can_write_student(student)
	school = frappe.db.get_value("Student", student, "anchor_school")
	settings = _resolve_settings_for_school(school)
	if int(settings.get("allow_pdf_export") or 0) != 1:
		frappe.throw(_("PDF export is disabled for this school."), frappe.PermissionError)

	from frappe.utils.pdf import get_pdf

	html = _render_reflection_pdf_html(rows, title=_("Reflection Export"))
	pdf_content = get_pdf(html)
	file_doc = _dispatch_export_file(
		student=student,
		school=school,
		purpose="journal_export",
		slot="journal_export_pdf",
		file_name=f"reflection-export-{student}-{today()}.pdf",
		content=pdf_content,
	)
	return {
		"file_url": file_doc.file_url,
		"file_name": file_doc.file_name,
		"student": student,
	}

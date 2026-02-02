# ifitwala_ed/api/guardian_home.py

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Tuple

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime, strip_html
from frappe.utils.caching import redis_cache

from ifitwala_ed.schedule.schedule_utils import get_effective_schedule_for_ay, get_rotation_dates
from ifitwala_ed.utilities.school_tree import get_descendant_schools


FORBIDDEN_PAYLOAD_KEYS = {"rotation_day", "block_number"}
ASSESSMENT_TASK_TYPES = {
	"Quiz",
	"Test",
	"Summative assessment",
	"Formative assessment",
	"Exam",
}
PREP_CAP_PER_CHILD_DAY = 3


@frappe.whitelist()
def get_guardian_home_snapshot(anchor_date=None, school_days=7, debug=0):
	"""
	Phase-1 Guardian Home snapshot.

	Hard guarantees:
	- Explicit args only; no form_dict parsing.
	- Guardian scope resolved only from Guardian -> Student links.
	- No rotation_day / block_number leakage in returned payload.
	"""
	anchor = _coerce_anchor_date(anchor_date)
	school_days_int = _coerce_school_days(school_days)
	debug_mode = int(debug or 0) == 1
	debug_warnings: List[str] = []

	payload: Dict[str, Any] = {
		"meta": {
			"generated_at": now_datetime().isoformat(),
			"anchor_date": str(anchor),
			"school_days": school_days_int,
			"guardian": {"name": None},
		},
		"family": {"children": []},
		"zones": {
			"family_timeline": [],
			"attention_needed": [],
			"preparation_and_support": [],
			"recent_activity": [],
		},
		"counts": {
			"unread_communications": 0,
			"unread_visible_student_logs": 0,
			"upcoming_due_tasks": 0,
			"upcoming_assessments": 0,
		},
	}

	user = frappe.session.user
	guardian_name, children = _resolve_guardian_scope(user)
	payload["meta"]["guardian"]["name"] = guardian_name
	payload["family"]["children"] = children

	if not children:
		return _finalize_payload(payload, debug_mode, debug_warnings)

	student_names = [c["student"] for c in children]
	membership = _get_student_group_membership(student_names)
	group_context = _get_student_group_context(membership, debug_warnings)

	task_bundle = _build_task_bundle(
		anchor=anchor,
		student_names=student_names,
		membership=membership,
		debug_warnings=debug_warnings,
	)
	family_timeline = _build_family_timeline(
		anchor=anchor,
		school_days=school_days_int,
		children=children,
		membership=membership,
		group_context=group_context,
		task_chips_by_student_date=task_bundle["chips_by_student_date"],
		debug_warnings=debug_warnings,
	)

	log_bundle = _build_student_log_bundle(anchor=anchor, student_names=student_names)
	attendance_attention = _build_attendance_attention(anchor=anchor, student_names=student_names)
	communication_bundle = _build_communication_bundle(
		anchor=anchor,
		user=user,
		children=children,
		membership=membership,
	)
	prep_items = _build_preparation_items(
		family_timeline=family_timeline,
		communication_bundle=communication_bundle,
	)
	recent_activity = _build_recent_activity(
		task_items=task_bundle["recent_task_results"],
		log_items=log_bundle["recent_activity_items"],
		communication_items=communication_bundle["recent_activity_items"],
	)

	attention_needed = attendance_attention + log_bundle["attention_items"] + communication_bundle["attention_items"]
	attention_needed.sort(key=_attention_sort_key, reverse=True)

	payload["zones"]["family_timeline"] = family_timeline
	payload["zones"]["attention_needed"] = attention_needed[:50]
	payload["zones"]["preparation_and_support"] = prep_items
	payload["zones"]["recent_activity"] = recent_activity

	payload["counts"]["unread_communications"] = communication_bundle["unread_count"]
	payload["counts"]["unread_visible_student_logs"] = log_bundle["unread_count"]
	payload["counts"]["upcoming_due_tasks"] = task_bundle["upcoming_due_count"]
	payload["counts"]["upcoming_assessments"] = task_bundle["upcoming_assessments_count"]

	_assert_no_internal_schedule_keys(
		payload=payload,
		debug_mode=debug_mode,
		debug_warnings=debug_warnings,
	)

	return _finalize_payload(payload, debug_mode, debug_warnings)


def _coerce_anchor_date(anchor_date: str | None) -> date:
	if not anchor_date:
		return getdate()
	try:
		return getdate(anchor_date)
	except Exception:
		frappe.throw(_("Invalid anchor_date. Expected YYYY-MM-DD."))


def _coerce_school_days(school_days: Any) -> int:
	try:
		value = int(school_days or 7)
	except Exception:
		frappe.throw(_("Invalid school_days."))

	if value < 1 or value > 30:
		frappe.throw(_("school_days must be between 1 and 30."))
	return value


def _finalize_payload(payload: Dict[str, Any], debug_mode: bool, debug_warnings: List[str]) -> Dict[str, Any]:
	if debug_mode:
		payload["debug"] = {"warnings": debug_warnings}
	return payload


def _resolve_guardian_scope(user: str) -> Tuple[str, List[Dict[str, Any]]]:
	if not user or user == "Guest":
		frappe.throw(_("You must be logged in to access Guardian Home."), frappe.PermissionError)

	guardian_name = frappe.db.get_value("Guardian", {"user": user}, "name")
	if not guardian_name:
		frappe.throw(_("This account is not linked to a Guardian record."), frappe.PermissionError)

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
	linked_students = sorted(
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
	if not linked_students:
		return guardian_name, []

	students = frappe.get_all(
		"Student",
		filters={"name": ["in", linked_students], "enabled": 1},
		fields=["name", "student_full_name", "anchor_school", "student_image"],
		order_by="student_full_name asc, name asc",
	)

	children = [
		{
			"student": row.get("name"),
			"full_name": row.get("student_full_name") or row.get("name"),
			"school": row.get("anchor_school") or "",
			"student_image_url": row.get("student_image") or None,
		}
		for row in students
		if row.get("name")
	]
	return guardian_name, children


def _get_student_group_membership(student_names: List[str]) -> Dict[str, set[str]]:
	out: Dict[str, set[str]] = {student: set() for student in student_names}
	if not student_names:
		return out

	rows = frappe.get_all(
		"Student Group Student",
		filters={"student": ["in", student_names], "active": 1},
		fields=["student", "parent"],
	)
	for row in rows:
		student = row.get("student")
		group = row.get("parent")
		if student and group:
			out.setdefault(student, set()).add(group)
	return out


def _get_student_group_context(
	membership: Dict[str, set[str]],
	debug_warnings: List[str],
) -> Dict[str, Dict[str, Any]]:
	group_names = sorted({group for groups in membership.values() for group in groups})
	if not group_names:
		return {}

	rows = frappe.get_all(
		"Student Group",
		filters={"name": ["in", group_names], "status": "Active"},
		fields=["name", "student_group_name", "course", "school_schedule", "academic_year", "school"],
	)
	out: Dict[str, Dict[str, Any]] = {}
	for row in rows:
		group = row.get("name")
		if not group:
			continue

		school_schedule = row.get("school_schedule")
		academic_year = row.get("academic_year")
		school = row.get("school")
		if not school_schedule and academic_year and school:
			school_schedule = get_effective_schedule_for_ay(academic_year, school)

		if not school_schedule:
			debug_warnings.append(
				f"student_group_missing_schedule: group={group}, academic_year={academic_year}, school={school}"
			)
			continue

		if not academic_year:
			debug_warnings.append(f"student_group_missing_academic_year: group={group}, schedule={school_schedule}")
			continue

		out[group] = {
			"name": group,
			"student_group_name": row.get("student_group_name") or group,
			"course": row.get("course"),
			"school_schedule": school_schedule,
			"academic_year": academic_year,
		}

	return out


def _build_task_bundle(
	anchor: date,
	student_names: List[str],
	membership: Dict[str, set[str]],
	debug_warnings: List[str],
) -> Dict[str, Any]:
	group_names = sorted({group for groups in membership.values() for group in groups})
	chips_by_student_date: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = defaultdict(
		lambda: defaultdict(lambda: {"tasks_due": [], "assessments_upcoming": []})
	)
	if not group_names or not student_names:
		return {
			"chips_by_student_date": chips_by_student_date,
			"upcoming_due_count": 0,
			"upcoming_assessments_count": 0,
			"recent_task_results": [],
		}

	horizon_end = add_days(anchor, 14)
	recent_start = add_days(anchor, -7)
	upcoming_window_end = add_days(anchor, 7)

	deliveries = frappe.get_all(
		"Task Delivery",
		filters={
			"docstatus": 1,
			"student_group": ["in", group_names],
			"due_date": ["between", [f"{anchor} 00:00:00", f"{horizon_end} 23:59:59"]],
		},
		fields=["name", "task", "student_group", "delivery_mode", "available_from", "due_date", "lock_date", "max_points"],
		order_by="due_date asc, name asc",
	)
	if not deliveries:
		return {
			"chips_by_student_date": chips_by_student_date,
			"upcoming_due_count": 0,
			"upcoming_assessments_count": 0,
			"recent_task_results": [],
		}

	task_names = sorted({row.get("task") for row in deliveries if row.get("task")})
	task_map = {}
	if task_names:
		task_map = {
			row["name"]: row
			for row in frappe.get_all(
				"Task",
				filters={"name": ["in", task_names]},
				fields=["name", "title", "task_type"],
			)
		}

	delivery_names = [row.get("name") for row in deliveries if row.get("name")]
	outcome_rows = frappe.get_all(
		"Task Outcome",
		filters={"task_delivery": ["in", delivery_names], "student": ["in", student_names]},
		fields=[
			"name",
			"task_delivery",
			"student",
			"submission_status",
			"grading_status",
			"is_complete",
			"is_published",
			"published_on",
			"published_by",
			"official_score",
			"official_grade",
			"official_feedback",
		],
	)
	outcome_lookup = {
		(row.get("student"), row.get("task_delivery")): row
		for row in outcome_rows
		if row.get("student") and row.get("task_delivery")
	}

	student_to_groups = membership
	upcoming_due_count = 0
	upcoming_assessments_count = 0

	for delivery in deliveries:
		delivery_name = delivery.get("name")
		student_group = delivery.get("student_group")
		due = _coerce_to_date(delivery.get("due_date"))
		available_from = _coerce_to_date(delivery.get("available_from"))
		lock_date = _coerce_to_date(delivery.get("lock_date"))
		if not delivery_name or not student_group or not due:
			continue
		if available_from and available_from > due:
			debug_warnings.append(
				f"task_delivery_invalid_window: delivery={delivery_name}, available_from={available_from}, due_date={due}"
			)
			continue

		task = task_map.get(delivery.get("task"), {})
		title = task.get("title") or delivery.get("task") or delivery_name
		kind = _task_kind(task.get("task_type"))
		date_key = due.isoformat()

		for student, groups in student_to_groups.items():
			if student_group not in groups:
				continue

			outcome = outcome_lookup.get((student, delivery_name))
			status = _resolve_chip_status(
				outcome=outcome,
				due=due,
				anchor=anchor,
				available_from=available_from,
				lock_date=lock_date,
			)
			chip = {
				"task_delivery": delivery_name,
				"title": title,
				"due_date": date_key,
				"kind": kind,
				"status": status,
			}
			if kind == "assessment":
				chips_by_student_date[student][date_key]["assessments_upcoming"].append(chip)
			else:
				chips_by_student_date[student][date_key]["tasks_due"].append(chip)

			if anchor <= due <= upcoming_window_end:
				if kind == "assessment":
					upcoming_assessments_count += 1
				else:
					upcoming_due_count += 1

	recent_outcomes = frappe.get_all(
		"Task Outcome",
		filters={
			"student": ["in", student_names],
			"is_published": 1,
			"published_on": ["between", [f"{recent_start} 00:00:00", f"{anchor} 23:59:59"]],
		},
		fields=[
			"name",
			"student",
			"task_delivery",
			"task",
			"published_on",
			"published_by",
			"official_score",
			"official_grade",
			"official_feedback",
		],
		order_by="published_on desc, modified desc",
		limit_page_length=50,
	)

	recent_task_results: List[Dict[str, Any]] = []
	for row in recent_outcomes:
		published = row.get("published_on")
		published_date = _coerce_to_date(published)
		if not published_date:
			continue

		task = task_map.get(row.get("task"), {})
		title = task.get("title") or row.get("task") or row.get("name")
		score = None
		if row.get("official_score") not in (None, ""):
			score = {"value": row.get("official_score")}
		elif row.get("official_grade"):
			score = {"value": row.get("official_grade")}

		recent_task_results.append(
			{
				"type": "task_result",
				"student": row.get("student"),
				"task_outcome": row.get("name"),
				"title": title,
				"published_on": published.isoformat() if isinstance(published, datetime) else str(published),
				"published_by": row.get("published_by"),
				"score": score,
				"narrative": _plain_summary(row.get("official_feedback")),
			}
		)

	for student in student_names:
		for date_key, bucket in chips_by_student_date.get(student, {}).items():
			bucket["tasks_due"] = sorted(bucket["tasks_due"], key=lambda x: (x.get("due_date"), x.get("title")))[:6]
			bucket["assessments_upcoming"] = sorted(
				bucket["assessments_upcoming"], key=lambda x: (x.get("due_date"), x.get("title"))
			)[:6]

	return {
		"chips_by_student_date": chips_by_student_date,
		"upcoming_due_count": upcoming_due_count,
		"upcoming_assessments_count": upcoming_assessments_count,
		"recent_task_results": recent_task_results,
	}


def _resolve_chip_status(
	outcome: Dict[str, Any] | None,
	due: date,
	anchor: date,
	available_from: date | None,
	lock_date: date | None,
) -> str:
	if outcome:
		grading_status = (outcome.get("grading_status") or "").strip()
		submission_status = (outcome.get("submission_status") or "").strip()
		if int(outcome.get("is_complete") or 0) == 1 or grading_status in {"Finalized", "Released", "Moderated"}:
			return "completed"
		if submission_status in {"Submitted", "Late", "Resubmitted"}:
			return "submitted"

	if available_from and anchor < available_from:
		return "assigned"
	if due < anchor:
		if lock_date and anchor <= lock_date:
			return "assigned"
		return "missing"
	return "assigned"


def _build_family_timeline(
	anchor: date,
	school_days: int,
	children: List[Dict[str, Any]],
	membership: Dict[str, set[str]],
	group_context: Dict[str, Dict[str, Any]],
	task_chips_by_student_date: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]],
	debug_warnings: List[str],
) -> List[Dict[str, Any]]:
	group_names = sorted({group for groups in membership.values() for group in groups if group in group_context})
	if not group_names:
		debug_warnings.append("no_active_student_groups_for_children")
		return []

	group_schedule_rows = frappe.get_all(
		"Student Group Schedule",
		filters={"parent": ["in", group_names]},
		fields=["parent", "rotation_day", "block_number", "from_time", "to_time", "location"],
		order_by="parent asc, rotation_day asc, block_number asc",
	)
	rows_by_group_rotation: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
	for row in group_schedule_rows:
		group = row.get("parent")
		rotation_day = _as_int(row.get("rotation_day"))
		if not group or rotation_day is None:
			continue
		rows_by_group_rotation[(group, rotation_day)].append(row)

	for key in list(rows_by_group_rotation.keys()):
		rows_by_group_rotation[key].sort(key=lambda r: (_as_int(r.get("block_number")) or 0))

	course_names = sorted({ctx.get("course") for ctx in group_context.values() if ctx.get("course")})
	course_name_map = {
		row.get("name"): row.get("course_name")
		for row in frappe.get_all("Course", filters={"name": ["in", course_names]}, fields=["name", "course_name"])
	}

	rotation_by_schedule_key: Dict[Tuple[str, str], Dict[str, int]] = {}
	dates_by_schedule_key: Dict[Tuple[str, str], List[date]] = {}
	for ctx in group_context.values():
		schedule_name = ctx.get("school_schedule")
		academic_year = ctx.get("academic_year")
		key = (schedule_name, academic_year)
		if key in rotation_by_schedule_key:
			continue

		date_to_rotation, school_day_dates = _get_rotation_map(
			schedule_name=schedule_name,
			academic_year=academic_year,
			anchor=anchor,
			max_days=max(school_days * 3, 21),
			debug_warnings=debug_warnings,
		)
		rotation_by_schedule_key[key] = date_to_rotation
		dates_by_schedule_key[key] = school_day_dates

	student_date_sets: Dict[str, set[date]] = defaultdict(set)
	for child in children:
		student = child.get("student")
		for group in membership.get(student, set()):
			ctx = group_context.get(group)
			if not ctx:
				continue
			key = (ctx.get("school_schedule"), ctx.get("academic_year"))
			for d in dates_by_schedule_key.get(key, []):
				student_date_sets[student].add(d)

	family_dates = sorted({d for dset in student_date_sets.values() for d in dset})
	family_dates = family_dates[:school_days]
	if not family_dates:
		debug_warnings.append("family_timeline_empty_school_days")
		return []

	event_blocks_by_student_date = _build_school_event_blocks(
		family_dates=family_dates,
		children=children,
		membership=membership,
		debug_warnings=debug_warnings,
	)

	out: List[Dict[str, Any]] = []
	for day in family_dates:
		date_key = day.isoformat()
		children_timeline: List[Dict[str, Any]] = []

		for child in children:
			student = child.get("student")
			blocks: List[Dict[str, Any]] = []
			for group in membership.get(student, set()):
				ctx = group_context.get(group)
				if not ctx:
					continue

				schedule_name = ctx.get("school_schedule")
				academic_year = ctx.get("academic_year")
				key = (schedule_name, academic_year)
				rotation_day = rotation_by_schedule_key.get(key, {}).get(date_key)
				if not rotation_day:
					continue

				template_map = _get_schedule_block_templates(schedule_name)
				rows = rows_by_group_rotation.get((group, rotation_day), [])
				for row in rows:
					block = _build_timeline_block(
						row=row,
						template_map=template_map,
						course_name=course_name_map.get(ctx.get("course")) or ctx.get("student_group_name") or "Class",
						debug_warnings=debug_warnings,
					)
					if block:
						blocks.append(block)

			blocks.extend(event_blocks_by_student_date.get(student, {}).get(date_key, []))
			blocks = _dedupe_blocks(sorted(blocks, key=lambda b: (b.get("start_time"), b.get("end_time"), b.get("title"))))
			start_time = blocks[0]["start_time"] if blocks else ""
			end_time = blocks[-1]["end_time"] if blocks else ""
			note = None if blocks else _("No scheduled blocks")

			chips = task_chips_by_student_date.get(student, {}).get(
				date_key, {"tasks_due": [], "assessments_upcoming": []}
			)
			children_timeline.append(
				{
					"student": student,
					"day_summary": {"start_time": start_time, "end_time": end_time, "note": note},
					"blocks": blocks,
					"tasks_due": chips.get("tasks_due", []),
					"assessments_upcoming": chips.get("assessments_upcoming", []),
				}
			)

		is_school_day = any(child.get("blocks") for child in children_timeline)
		out.append(
			{
				"date": date_key,
				"label": day.strftime("%a %d %b"),
				"is_school_day": bool(is_school_day),
				"children": children_timeline,
			}
		)

	return out


def _build_school_event_blocks(
	family_dates: List[date],
	children: List[Dict[str, Any]],
	membership: Dict[str, set[str]],
	debug_warnings: List[str],
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
	out: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
	if not family_dates:
		return out

	start_date = min(family_dates)
	end_date = max(family_dates)
	date_keys = {d.isoformat() for d in family_dates}
	students = [child.get("student") for child in children if child.get("student")]
	if not students:
		return out

	student_school = {child.get("student"): (child.get("school") or "") for child in children if child.get("student")}
	event_rows = frappe.db.sql(
		"""
		SELECT
			name,
			subject,
			event_category,
			school,
			starts_on,
			ends_on,
			all_day,
			location,
			description
		FROM `tabSchool Event`
		WHERE docstatus < 2
		  AND DATE(starts_on) <= %(end_date)s
		  AND DATE(COALESCE(ends_on, starts_on)) >= %(start_date)s
		ORDER BY starts_on asc, creation asc
		""",
		{"start_date": start_date, "end_date": end_date},
		as_dict=True,
	)
	if not event_rows:
		return out

	event_names = [row.get("name") for row in event_rows if row.get("name")]
	audience_rows = frappe.get_all(
		"School Event Audience",
		filters={"parent": ["in", event_names]},
		fields=[
			"parent",
			"audience_type",
			"student_group",
			"include_guardians",
			"include_students",
		],
	)
	by_event: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
	for audience in audience_rows:
		parent = audience.get("parent")
		if parent:
			by_event[parent].append(audience)

	def event_students_for_row(event_row: Dict[str, Any], audience: Dict[str, Any]) -> set[str]:
		audience_type = (audience.get("audience_type") or "").strip()
		include_guardians = int(audience.get("include_guardians") or 0) == 1
		event_school = (event_row.get("school") or "").strip()
		eligible_students = set(students)
		if event_school:
			eligible_students = {s for s in eligible_students if student_school.get(s) == event_school}

		if audience_type == "Whole School Community":
			return eligible_students
		if audience_type == "All Guardians":
			return eligible_students
		if audience_type == "All Students":
			return eligible_students if include_guardians else set()
		if audience_type == "Students in Student Group":
			if not include_guardians:
				return set()
			group = audience.get("student_group")
			if not group:
				return set()
			return {s for s in eligible_students if group in membership.get(s, set())}
		return set()

	for event_row in event_rows:
		event_name = event_row.get("name")
		if not event_name:
			continue

		start_dt = _coerce_to_datetime(event_row.get("starts_on"))
		end_dt = _coerce_to_datetime(event_row.get("ends_on")) or start_dt
		if not start_dt or not end_dt:
			debug_warnings.append(f"school_event_invalid_datetime: event={event_name}")
			continue
		if end_dt < start_dt:
			end_dt = start_dt

		audiences = by_event.get(event_name, [])
		if not audiences:
			continue

		matched_students: set[str] = set()
		for audience in audiences:
			matched_students |= event_students_for_row(event_row, audience)
		if not matched_students:
			continue

		title = (event_row.get("subject") or _("School event")).strip()
		subtitle = (event_row.get("location") or "").strip() or _plain_summary(event_row.get("description"), 80) or None
		kind = _event_kind(event_row.get("event_category"))
		all_day = int(event_row.get("all_day") or 0) == 1
		range_start = start_dt.date()
		range_end = end_dt.date()

		current = range_start
		while current <= range_end:
			date_key = current.isoformat()
			if date_key in date_keys:
				start_time = "00:00" if all_day else _coerce_time(start_dt, "school_event.start", debug_warnings) or "00:00"
				end_time = "23:59" if all_day else _coerce_time(end_dt, "school_event.end", debug_warnings) or "23:59"
				block = {
					"start_time": start_time,
					"end_time": end_time,
					"title": title,
					"subtitle": subtitle,
					"kind": kind,
				}
				for student in matched_students:
					out[student][date_key].append(block)
			current = add_days(current, 1)

	return out


def _build_timeline_block(
	row: Dict[str, Any],
	template_map: Dict[Tuple[int, int], Dict[str, Any]],
	course_name: str,
	debug_warnings: List[str],
) -> Dict[str, Any] | None:
	rotation_day = _as_int(row.get("rotation_day"))
	block_number = _as_int(row.get("block_number"))
	if rotation_day is None or block_number is None:
		return None

	template = template_map.get((rotation_day, block_number), {})
	start_time = _coerce_time(row.get("from_time") or template.get("from_time"), "timeline_block.start", debug_warnings)
	end_time = _coerce_time(row.get("to_time") or template.get("to_time"), "timeline_block.end", debug_warnings)
	if not start_time or not end_time:
		return None

	block_type = (template.get("block_type") or "Other").strip()
	kind = _timeline_kind(block_type)
	description = (template.get("description") or "").strip()
	location = (row.get("location") or "").strip()

	if kind == "course":
		title = course_name or _("Class")
	else:
		title = _block_title_from_type(block_type)

	subtitle = description or location or None
	return {
		"start_time": start_time,
		"end_time": end_time,
		"title": title,
		"subtitle": subtitle,
		"kind": kind,
	}


def _dedupe_blocks(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	seen = set()
	out = []
	for block in blocks:
		key = (
			block.get("start_time"),
			block.get("end_time"),
			block.get("title"),
			block.get("subtitle"),
			block.get("kind"),
		)
		if key in seen:
			continue
		seen.add(key)
		out.append(block)
	return out


def _build_student_log_bundle(anchor: date, student_names: List[str]) -> Dict[str, Any]:
	if not student_names:
		return {"attention_items": [], "recent_activity_items": [], "unread_count": 0}

	recent_window_start = add_days(anchor, -30)
	rows = frappe.get_all(
		"Student Log",
		filters={
			"student": ["in", student_names],
			"visible_to_guardians": 1,
			"date": ["between", [recent_window_start, anchor]],
		},
		fields=["name", "student", "date", "time", "follow_up_status", "log"],
		order_by="date desc, time desc, modified desc",
		limit_page_length=200,
	)
	if not rows:
		return {"attention_items": [], "recent_activity_items": [], "unread_count": 0}

	log_names = [row.get("name") for row in rows if row.get("name")]
	unread_names = set(_get_unread_reference_names(frappe.session.user, "Student Log", log_names))

	attention_items: List[Dict[str, Any]] = []
	recent_activity_items: List[Dict[str, Any]] = []
	recent_activity_start = add_days(anchor, -7)

	for row in rows:
		name = row.get("name")
		student = row.get("student")
		log_date = _coerce_to_date(row.get("date"))
		if not name or not student or not log_date:
			continue

		summary = _plain_summary(row.get("log"))
		date_str = log_date.isoformat()
		time_str = _coerce_time(row.get("time"), "student_log.time", [])
		status = (row.get("follow_up_status") or "").strip()
		is_unread = name in unread_names
		is_open = status in {"Open", "In Progress"}

		if is_unread or is_open:
			attention_items.append(
				{
					"type": "student_log",
					"student": student,
					"student_log": name,
					"date": date_str,
					"time": time_str,
					"summary": summary,
					"follow_up_status": status or None,
				}
			)

		if log_date >= recent_activity_start:
			recent_activity_items.append(
				{
					"type": "student_log",
					"student": student,
					"student_log": name,
					"date": date_str,
					"summary": summary,
				}
			)

	attention_items.sort(key=_attention_sort_key, reverse=True)
	return {
		"attention_items": attention_items[:40],
		"recent_activity_items": recent_activity_items[:40],
		"unread_count": len(unread_names),
	}


def _build_attendance_attention(anchor: date, student_names: List[str]) -> List[Dict[str, Any]]:
	if not student_names:
		return []

	window_start = add_days(anchor, -7)
	rows = frappe.get_all(
		"Student Attendance",
		filters={"student": ["in", student_names], "attendance_date": ["between", [window_start, anchor]]},
		fields=["student", "attendance_date", "attendance_time", "attendance_code", "whole_day"],
		order_by="attendance_date desc, attendance_time desc, modified desc",
		limit_page_length=200,
	)
	if not rows:
		return []

	code_names = sorted({row.get("attendance_code") for row in rows if row.get("attendance_code")})
	code_rows = frappe.get_all(
		"Student Attendance Code",
		filters={"name": ["in", code_names]},
		fields=["name", "attendance_code", "count_as_present"],
	)
	code_map = {row.get("name"): row for row in code_rows}

	out: List[Dict[str, Any]] = []
	for row in rows:
		code_name = row.get("attendance_code")
		code = code_map.get(code_name, {})
		if int(code.get("count_as_present") or 0) == 1:
			continue

		attendance_date = _coerce_to_date(row.get("attendance_date"))
		if not attendance_date:
			continue

		attendance_time = _coerce_time(row.get("attendance_time"), "attendance.time", [])
		code_label = (code.get("attendance_code") or code_name or _("Attendance exception")).strip()
		if int(row.get("whole_day") or 0) == 1:
			summary = _("{0} (whole day)").format(code_label)
		elif attendance_time:
			summary = _("{0} at {1}").format(code_label, attendance_time)
		else:
			summary = code_label

		out.append(
			{
				"type": "attendance",
				"student": row.get("student"),
				"date": attendance_date.isoformat(),
				"time": attendance_time,
				"summary": summary,
			}
		)

	out.sort(key=_attention_sort_key, reverse=True)
	return out[:40]


def _build_communication_bundle(
	anchor: date,
	user: str,
	children: List[Dict[str, Any]],
	membership: Dict[str, set[str]],
) -> Dict[str, Any]:
	recent_start = add_days(anchor, -7)
	candidate_start = add_days(anchor, -30)
	candidate_end = add_days(anchor, 14)

	candidates = frappe.db.sql(
		"""
		SELECT
			name,
			title,
			publish_from,
			publish_to,
			creation
		FROM `tabOrg Communication`
		WHERE status = 'Published'
		  AND IFNULL(portal_surface, 'Everywhere') IN ('Everywhere', 'Portal Feed', 'Guardian Portal')
		  AND (publish_from IS NULL OR publish_from <= %(candidate_end)s)
		  AND (publish_to IS NULL OR publish_to >= %(candidate_start)s)
		ORDER BY publish_from DESC, creation DESC
		LIMIT 200
		""",
		{"candidate_start": candidate_start, "candidate_end": candidate_end},
		as_dict=True,
	)

	if not candidates:
		return {"attention_items": [], "recent_activity_items": [], "unread_count": 0}

	child_groups = {group for groups in membership.values() for group in groups}
	child_schools = {child.get("school") for child in children if child.get("school")}
	candidate_names = [row.get("name") for row in candidates if row.get("name")]
	audience_rows = frappe.get_all(
		"Org Communication Audience",
		filters={"parent": ["in", candidate_names]},
		fields=["parent", "target_mode", "school", "student_group", "include_descendants", "to_guardians"],
	)
	audience_by_comm: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
	for row in audience_rows:
		parent = row.get("parent")
		if parent:
			audience_by_comm[parent].append(row)

	descendants_cache: Dict[str, set[str]] = {}

	def _school_scope_matches(aud_school: str, include_descendants: bool) -> bool:
		if not aud_school:
			return False
		if aud_school in child_schools:
			return True
		if not include_descendants:
			return False
		if aud_school not in descendants_cache:
			descendants_cache[aud_school] = set(get_descendant_schools(aud_school) or [])
		return bool(child_schools & descendants_cache[aud_school])

	def _audience_matches_guardian(row: Dict[str, Any]) -> bool:
		if int(row.get("to_guardians") or 0) != 1:
			return False

		mode = (row.get("target_mode") or "").strip()
		if mode == "Student Group":
			student_group = row.get("student_group")
			return bool(student_group and student_group in child_groups)
		if mode == "School Scope":
			return _school_scope_matches(
				aud_school=row.get("school"),
				include_descendants=int(row.get("include_descendants") or 0) == 1,
			)
		if mode == "Team":
			return False

		# Defensive compatibility for legacy rows missing target_mode.
		if row.get("student_group"):
			return row.get("student_group") in child_groups
		if row.get("school"):
			return _school_scope_matches(
				aud_school=row.get("school"),
				include_descendants=int(row.get("include_descendants") or 0) == 1,
			)
		return False

	visible: List[Dict[str, Any]] = []
	for row in candidates:
		comm_name = row.get("name")
		if not comm_name:
			continue
		comm_audiences = audience_by_comm.get(comm_name, [])
		if any(_audience_matches_guardian(aud) for aud in comm_audiences):
			visible.append(row)

	if not visible:
		return {"attention_items": [], "recent_activity_items": [], "unread_count": 0}

	visible_names = [row.get("name") for row in visible if row.get("name")]
	seen_rows = frappe.get_all(
		"Communication Interaction",
		filters={"user": user, "org_communication": ["in", visible_names]},
		fields=["org_communication"],
	)
	seen_names = {row.get("org_communication") for row in seen_rows if row.get("org_communication")}
	unread_names = [name for name in visible_names if name not in seen_names]
	unread_set = set(unread_names)

	attention_items: List[Dict[str, Any]] = []
	recent_activity_items: List[Dict[str, Any]] = []
	for row in visible:
		comm_name = row.get("name")
		if not comm_name:
			continue

		comm_dt = row.get("publish_from") or row.get("creation")
		comm_date = _coerce_to_date(comm_dt)
		if not comm_date:
			continue

		date_str = comm_date.isoformat()
		title = (row.get("title") or comm_name).strip()
		is_unread = comm_name in unread_set

		if is_unread:
			attention_items.append(
				{
					"type": "communication",
					"communication": comm_name,
					"date": date_str,
					"title": title,
					"is_unread": True,
				}
			)

		if comm_date >= recent_start:
			recent_activity_items.append(
				{
					"type": "communication",
					"communication": comm_name,
					"date": date_str,
					"title": title,
					"is_unread": bool(is_unread),
				}
			)

	attention_items.sort(key=_attention_sort_key, reverse=True)
	return {
		"attention_items": attention_items[:40],
		"recent_activity_items": recent_activity_items[:40],
		"unread_count": len(unread_names),
		"unread_items": attention_items[:20],
	}


def _build_preparation_items(
	family_timeline: List[Dict[str, Any]],
	communication_bundle: Dict[str, Any],
) -> List[Dict[str, Any]]:
	out: List[Dict[str, Any]] = []
	counts: Dict[Tuple[str, str], int] = defaultdict(int)

	def can_add(student: str, date_str: str) -> bool:
		return counts[(student, date_str)] < PREP_CAP_PER_CHILD_DAY

	def add_item(item: Dict[str, Any]):
		student = item.get("student")
		date_str = item.get("date")
		if not student or not date_str:
			return
		if not can_add(student, date_str):
			return
		counts[(student, date_str)] += 1
		out.append(item)

	for day in family_timeline:
		day_date = day.get("date")
		for child in day.get("children", []):
			student = child.get("student")
			if not student or not day_date:
				continue

			for chip in child.get("assessments_upcoming", []):
				add_item(
					{
						"student": student,
						"date": day_date,
						"label": _("Prepare for: {0}").format(chip.get("title") or _("Assessment")),
						"source": "task",
						"related": {"task_delivery": chip.get("task_delivery")},
					}
				)

			for chip in child.get("tasks_due", []):
				add_item(
					{
						"student": student,
						"date": day_date,
						"label": _("Due soon: {0}").format(chip.get("title") or _("Task")),
						"source": "task",
						"related": {"task_delivery": chip.get("task_delivery")},
					}
				)

			for block in child.get("blocks", []):
				if block.get("kind") not in {"activity", "assembly"}:
					continue
				add_item(
					{
						"student": student,
						"date": day_date,
						"label": block.get("title") or _("School activity"),
						"source": "schedule",
						"related": {
							"schedule_hint": {
								"start_time": block.get("start_time"),
								"end_time": block.get("end_time"),
							}
						},
					}
				)

	# Communication-to-prep is intentionally conservative in Phase-1:
	# no synthetic child mapping; keep communication in attention/recent only.
	_ = communication_bundle

	out.sort(key=lambda x: (x.get("date"), x.get("student"), x.get("label")))
	return out[:80]


def _build_recent_activity(
	task_items: List[Dict[str, Any]],
	log_items: List[Dict[str, Any]],
	communication_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
	items = list(task_items or []) + list(log_items or []) + list(communication_items or [])
	items.sort(key=_recent_activity_sort_key, reverse=True)
	return items[:80]


def _get_unread_reference_names(user: str, reference_doctype: str, names: List[str]) -> List[str]:
	if not names:
		return []
	seen_rows = frappe.get_all(
		"Portal Read Receipt",
		filters={"user": user, "reference_doctype": reference_doctype, "reference_name": ["in", names]},
		fields=["reference_name"],
	)
	seen = {row.get("reference_name") for row in seen_rows if row.get("reference_name")}
	return [name for name in names if name not in seen]


@redis_cache(ttl=21600)
def _get_schedule_blocks_cached(schedule_name: str) -> List[Dict[str, Any]]:
	return frappe.get_all(
		"School Schedule Block",
		filters={"parent": schedule_name},
		fields=["rotation_day", "block_number", "from_time", "to_time", "block_type", "description"],
		order_by="rotation_day asc, block_number asc",
	)


def _get_schedule_block_templates(schedule_name: str) -> Dict[Tuple[int, int], Dict[str, Any]]:
	rows = _get_schedule_blocks_cached(schedule_name) or []
	out: Dict[Tuple[int, int], Dict[str, Any]] = {}
	for row in rows:
		rotation_day = _as_int(row.get("rotation_day"))
		block_number = _as_int(row.get("block_number"))
		if rotation_day is None or block_number is None:
			continue
		out[(rotation_day, block_number)] = row
	return out


@redis_cache(ttl=21600)
def _get_rotation_rows_cached(schedule_name: str, academic_year: str) -> List[Dict[str, Any]]:
	return get_rotation_dates(schedule_name, academic_year, include_holidays=False) or []


def _get_rotation_map(
	schedule_name: str,
	academic_year: str,
	anchor: date,
	max_days: int,
	debug_warnings: List[str],
) -> Tuple[Dict[str, int], List[date]]:
	try:
		rows = _get_rotation_rows_cached(schedule_name, academic_year)
	except Exception:
		debug_warnings.append(f"rotation_lookup_failed: schedule={schedule_name}, ay={academic_year}")
		return {}, []

	date_to_rotation: Dict[str, int] = {}
	out_dates: List[date] = []
	for row in rows:
		current_date = _coerce_to_date(row.get("date"))
		rotation_day = _as_int(row.get("rotation_day"))
		if not current_date or rotation_day is None:
			continue
		if current_date < anchor:
			continue
		date_key = current_date.isoformat()
		date_to_rotation[date_key] = rotation_day
		out_dates.append(current_date)
		if len(out_dates) >= max_days:
			break

	return date_to_rotation, out_dates


def _task_kind(task_type: str | None) -> str:
	if not task_type:
		return "other"
	tt = task_type.strip()
	if tt in ASSESSMENT_TASK_TYPES:
		return "assessment"
	if tt == "Homework":
		return "homework"
	if tt == "Classwork":
		return "classwork"
	return "other"


def _timeline_kind(block_type: str | None) -> str:
	value = (block_type or "Other").strip().lower()
	if value == "course":
		return "course"
	if value == "activity":
		return "activity"
	if value == "recess":
		return "recess"
	if value == "assembly":
		return "assembly"
	return "other"


def _event_kind(event_category: str | None) -> str:
	value = (event_category or "").strip().lower()
	if not value:
		return "other"
	if "assembly" in value:
		return "assembly"
	if "recess" in value or "break" in value:
		return "recess"
	if any(token in value for token in ("activity", "sport", "club", "trip", "event")):
		return "activity"
	if any(token in value for token in ("class", "course", "lesson")):
		return "course"
	return "other"


def _block_title_from_type(block_type: str | None) -> str:
	value = (block_type or "Other").strip().lower()
	if value == "activity":
		return _("Activity")
	if value == "recess":
		return _("Recess")
	if value == "assembly":
		return _("Assembly")
	if value == "course":
		return _("Class")
	return _("School block")


def _plain_summary(html_or_text: Any, max_chars: int = 220) -> str:
	text = strip_html(html_or_text or "")
	text = " ".join(text.split()).strip()
	if not text:
		return ""
	if len(text) <= max_chars:
		return text
	return f"{text[:max_chars].rstrip()}..."


def _coerce_to_date(value: Any) -> date | None:
	if value is None:
		return None
	if isinstance(value, date) and not isinstance(value, datetime):
		return value
	if isinstance(value, datetime):
		return value.date()
	try:
		return getdate(value)
	except Exception:
		return None


def _coerce_to_datetime(value: Any) -> datetime | None:
	if value is None:
		return None
	if isinstance(value, datetime):
		return value
	if isinstance(value, date):
		return datetime.combine(value, time.min)
	try:
		dt = get_datetime(value)
		return dt if isinstance(dt, datetime) else None
	except Exception:
		return None


def _coerce_time(value: Any, label: str, debug_warnings: List[str]) -> str | None:
	if value is None:
		return None
	try:
		if isinstance(value, timedelta):
			total_seconds = int(value.total_seconds())
			hours = (total_seconds // 3600) % 24
			minutes = (total_seconds % 3600) // 60
			return f"{hours:02d}:{minutes:02d}"
		if isinstance(value, time):
			return f"{value.hour:02d}:{value.minute:02d}"
		if isinstance(value, datetime):
			return f"{value.hour:02d}:{value.minute:02d}"
		if isinstance(value, str):
			parts = value.strip().split(":")
			if len(parts) >= 2:
				hours = int(parts[0])
				minutes = int(parts[1])
				return f"{hours:02d}:{minutes:02d}"
	except Exception:
		debug_warnings.append(f"time_parse_failed: label={label}, value={value}, type={type(value).__name__}")
		return None

	debug_warnings.append(f"time_parse_unsupported_type: label={label}, type={type(value).__name__}")
	return None


def _as_int(value: Any) -> int | None:
	try:
		return int(value)
	except Exception:
		return None


def _attention_sort_key(item: Dict[str, Any]) -> Tuple[str, str]:
	return (str(item.get("date") or ""), str(item.get("time") or ""))


def _recent_activity_sort_key(item: Dict[str, Any]) -> str:
	if item.get("type") == "task_result":
		return str(item.get("published_on") or "")
	return str(item.get("date") or "")


def _assert_no_internal_schedule_keys(payload: Dict[str, Any], debug_mode: bool, debug_warnings: List[str]):
	found = _find_forbidden_keys(payload)
	if not found:
		return

	message = f"guardian_home_forbidden_keys_detected: {', '.join(found)}"
	frappe.log_error(title="Guardian Home Payload Leakage", message=message)
	if debug_mode:
		frappe.throw(_("Forbidden internal schedule keys detected in payload."))
	debug_warnings.append(message)


def _find_forbidden_keys(node: Any, prefix: str = "") -> List[str]:
	found: List[str] = []
	if isinstance(node, dict):
		for key, value in node.items():
			current = f"{prefix}.{key}" if prefix else str(key)
			if key in FORBIDDEN_PAYLOAD_KEYS:
				found.append(current)
			found.extend(_find_forbidden_keys(value, current))
	elif isinstance(node, list):
		for idx, value in enumerate(node):
			current = f"{prefix}[{idx}]"
			found.extend(_find_forbidden_keys(value, current))
	return found

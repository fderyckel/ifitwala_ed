# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/assessment_calendar_utils.py

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
from frappe.query_builder import Order
from frappe.utils.redis_wrapper import RedisWrapper
from frappe.utils.safe_exec import safe_json_loads

# Optional: light caching (5 minutes) to reduce round-trips on repeated calendar slices.
CACHE_TTL = 300  # seconds
CACHE_PREFIX = "ifitwala:task_calendar:v1"

def _cache_key(start, end, filters, user):
	# Normalize filters dict to a sorted tuple so identical selections hit cache
	key_filters = tuple(sorted((filters or {}).items()))
	return f"{CACHE_PREFIX}:{user}:{start}:{end}:{hash(key_filters)}"

def _maybe_get_cache(key):
	try:
		redis: RedisWrapper = frappe.cache()
		val = redis.get_value(key)
		return safe_json_loads(val) if val else None
	except Exception:
		return None

def _maybe_set_cache(key, val):
	try:
		redis: RedisWrapper = frappe.cache()
		redis.set_value(key, frappe.as_json(val), expires_in_sec=CACHE_TTL)
	except Exception:
		pass

@frappe.whitelist()
def get_task_events(start, end, filters=None):
	"""
	Native Frappe Calendar fetcher.
	Returns a list of dicts with keys: name, title, start, end, allDay, color (optional), doc (optional).
	- Uses Task.due_date as event datetime.
	- Applies optional filters on school, academic_year, program, course, instructor (User), student, status, delivery_type, is_graded.
	- Broad read by design (per project decision).
	"""
	user = frappe.session.user
	if isinstance(filters, str):
		# Coming from JS
		filters = safe_json_loads(filters) or {}

	key = _cache_key(start, end, filters, user)
	cached = _maybe_get_cache(key)
	if cached:
		return cached

	Task = frappe.qb.DocType("Task")
	query = (
		frappe.qb.from_(Task)
		.select(
			Task.name,
			Task.title,
			Task.due_date,
			Task.delivery_type,
			Task.is_graded,
			Task.status,
			Task.course,
			Task.program,
			Task.school,
			Task.academic_year,
			Task.student_group,
		)
		.where(Task.due_date.isnotnull())
		# calendar range (inclusive)
		.where(Task.due_date >= get_datetime(start))
		.where(Task.due_date <= get_datetime(end))
	)

	# ---- Dynamic filters (all optional) ----
	def _add_eq(field, val):
		nonlocal query
		if val:
			query = query.where(field == val)

	def _add_in(field, vals):
		nonlocal query
		if vals:
			query = query.where(field.isin(vals))

	# Simple equality filters
	_add_eq(Task.school, filters.get("school"))
	_add_eq(Task.academic_year, filters.get("academic_year"))
	_add_eq(Task.program, filters.get("program"))
	_add_eq(Task.course, filters.get("course"))
	_add_eq(Task.student_group, filters.get("student_group"))

	# Status / type toggles
	_add_in(Task.status, filters.get("status_in"))
	if "status" in filters:
		_add_eq(Task.status, filters.get("status"))
	if "delivery_type" in filters:
		_add_eq(Task.delivery_type, filters.get("delivery_type"))
	if "is_graded" in filters:
		try:
			_add_eq(Task.is_graded, int(filters.get("is_graded")))
		except Exception:
			pass

	# Instructor filter (User): resolve via Student Group Instructor quickly (no huge joins unless needed)
	instructor_user = filters.get("instructor_user")
	if instructor_user:
		sgi = frappe.get_all(
			"Student Group Instructor",
			filters={"user_id": instructor_user},
			pluck="parent",
			limit=0,
		)
		if sgi:
			query = query.where(Task.student_group.isin(sgi))
		else:
			# No groups ⇒ empty result quickly
			return []

	# Student filter → join Task Student only if requested
	student_id = filters.get("student")
	if student_id:
		TS = frappe.qb.DocType("Task Student")
		query = (
			query.join(TS).on(TS.parent == Task.name)
			.where(TS.student == student_id)
		)

	# Order by due_date then name for stability
	query = query.orderby(Task.due_date, order=Order.asc).orderby(Task.name)

	rows = query.run(as_dict=True)

	# Shape to Frappe Calendar
	events = []
	for r in rows:
		events.append({
			"name": r.name,
			"title": r.title,
			"start": r.due_date,  # Frappe Calendar uses 'start'/'end'
			"end": r.due_date,
			"allDay": 0,
			# Optional color hint; keep subtle. We’ll stay neutral for now.
			"color": None,
			"doc": {
				"delivery_type": r.delivery_type,
				"is_graded": r.is_graded,
				"status": r.status,
				"course": r.course,
				"program": r.program,
				"school": r.school,
				"academic_year": r.academic_year,
				"student_group": r.student_group,
			},
		})

	_maybe_set_cache(key, events)
	return events

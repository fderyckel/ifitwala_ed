from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import frappe
from frappe.utils import getdate, get_datetime

from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots
from ifitwala_ed.utilities.location_utils import is_bookable_room


BOOKING_SOURCE_DOCTYPE = "Student Group"
TEACHING_TYPE = "Teaching"


def _normalize_dt(value) -> datetime:
	if isinstance(value, datetime):
		return value
	return get_datetime(value)


def _get_ay_date_range(academic_year: Optional[str]) -> tuple[date, date]:
	if not academic_year:
		today = getdate()
		return today, today

	year_start, year_end = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
	) or (None, None)

	if not year_start or not year_end:
		today = getdate()
		return today, today

	return getdate(year_start), getdate(year_end)


def _build_schedule_index(student_group: str) -> Dict[tuple[int, int], dict]:
	"""
	Index SG schedule rows by (rotation_day, block_number) so we can resolve employee.
	Also includes row.location as fallback, but slot.location is preferred.
	"""
	rows = frappe.db.sql(
		"""
		select
			rotation_day,
			block_number,
			instructor,
			employee,
			location
		from `tabStudent Group Schedule`
		where parent = %s
		""",
		student_group,
		as_dict=True,
	)

	idx: Dict[tuple[int, int], dict] = {}
	for r in rows:
		rd = r.get("rotation_day")
		bn = r.get("block_number")
		if rd is None or bn is None:
			continue
		try:
			key = (int(rd), int(bn))
		except Exception:
			continue
		idx[key] = r
	return idx


def _resolve_employee_from_instructor(
	instructor_name: Optional[str],
	cache: Dict[str, Optional[str]],
) -> Optional[str]:
	if not instructor_name:
		return None
	if instructor_name in cache:
		return cache[instructor_name]
	emp = frappe.db.get_value("Instructor", instructor_name, "employee")
	cache[instructor_name] = emp
	return emp


def _upsert_teaching_booking(
	*,
	employee: str,
	start_dt: datetime,
	end_dt: datetime,
	location: str,
	source_name: str,
	school: Optional[str],
	academic_year: Optional[str],
) -> str:
	"""
	Unique per slot:
	(employee, source_doctype, source_name, from_datetime, to_datetime)
	"""
	if not employee or not start_dt or not end_dt or end_dt <= start_dt:
		return ""

	filters = {
		"employee": employee,
		"source_doctype": BOOKING_SOURCE_DOCTYPE,
		"source_name": source_name,
		"from_datetime": start_dt,
		"to_datetime": end_dt,
	}

	existing = frappe.db.get_value("Employee Booking", filters, "name")

	values = {
		"booking_type": TEACHING_TYPE,
		"blocks_availability": 1,
		"school": school,
		"academic_year": academic_year,
		"location": location,
	}

	if existing:
		frappe.db.set_value("Employee Booking", existing, values)
		return existing

	doc = frappe.get_doc(
		{
			"doctype": "Employee Booking",
			"employee": employee,
			"booking_type": TEACHING_TYPE,
			"blocks_availability": 1,
			"from_datetime": start_dt,
			"to_datetime": end_dt,
			"location": location,
			"source_doctype": BOOKING_SOURCE_DOCTYPE,
			"source_name": source_name,
			"school": school,
			"academic_year": academic_year,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def _delete_obsolete_teaching_bookings(
	*,
	student_group: str,
	start_dt: datetime,
	end_dt: datetime,
	target_keys: Set[Tuple[str, datetime, datetime]],
) -> int:
	"""
	Delete Teaching bookings for this group within the window
	that are not in target_keys.

	target_keys items: (employee, from_datetime, to_datetime)
	"""
	rows = frappe.db.sql(
		"""
		select name, employee, from_datetime, to_datetime
		from `tabEmployee Booking`
		where source_doctype = %s
		  and source_name = %s
		  and booking_type = %s
		  and from_datetime >= %s
		  and to_datetime <= %s
		""",
		[BOOKING_SOURCE_DOCTYPE, student_group, TEACHING_TYPE, start_dt, end_dt],
		as_dict=True,
	)

	to_delete: List[str] = []
	for r in rows:
		key = (
			r.get("employee"),
			_normalize_dt(r.get("from_datetime")),
			_normalize_dt(r.get("to_datetime")),
		)
		if key not in target_keys:
			to_delete.append(r["name"])

	if not to_delete:
		return 0

	deleted = 0
	chunk = 200
	for i in range(0, len(to_delete), chunk):
		names = to_delete[i : i + chunk]
		frappe.db.sql(
			"delete from `tabEmployee Booking` where name in %(names)s",
			{"names": tuple(names)},
		)
		deleted += len(names)

	return deleted


def rebuild_student_group_teaching_bookings(
	student_group: str,
	*,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
	strict_location: bool = True,
) -> dict:
	"""
	Rebuild Teaching Employee Bookings for ONE student group.

	Pattern (no transient emptiness):
	  1) Compute target slots
	  2) Upsert all target bookings
	  3) Delete obsolete bookings in the window
	"""
	if not student_group:
		return {"student_group": student_group, "upserted": 0, "deleted": 0, "skipped": 0}

	sg = frappe.get_doc("Student Group", student_group)
	academic_year = getattr(sg, "academic_year", None) or None
	school = getattr(sg, "school", None) or None

	# default window: full academic year of group
	if start_date is None or end_date is None:
		ay_start, ay_end = _get_ay_date_range(academic_year)
		start_date = start_date or ay_start
		end_date = end_date or ay_end

	if not start_date or not end_date or start_date > end_date:
		return {"student_group": student_group, "upserted": 0, "deleted": 0, "skipped": 0}

	start_bound = getdate(start_date)
	end_bound = getdate(end_date)

	window_start_dt = get_datetime(f"{start_bound} 00:00:00")
	window_end_dt = get_datetime(f"{end_bound} 23:59:59")

	sched_index = _build_schedule_index(student_group)
	if not sched_index:
		# nothing to materialize; also clean obsolete bookings in window (optional)
		deleted = _delete_obsolete_teaching_bookings(
			student_group=student_group,
			start_dt=_normalize_dt(window_start_dt),
			end_dt=_normalize_dt(window_end_dt),
			target_keys=set(),
		)
		return {"student_group": student_group, "upserted": 0, "deleted": deleted, "skipped": 0}

	instructor_cache: Dict[str, Optional[str]] = {}

	upserted = 0
	skipped = 0
	target_keys: Set[Tuple[str, datetime, datetime]] = set()

	for slot in iter_student_group_room_slots(student_group, start_bound, end_bound):
		rd = slot.get("rotation_day")
		bn = slot.get("block_number")
		if rd is None or bn is None:
			skipped += 1
			continue

		try:
			key = (int(rd), int(bn))
		except Exception:
			skipped += 1
			continue

		row = sched_index.get(key)
		if not row:
			skipped += 1
			continue

		employee = row.get("employee") or _resolve_employee_from_instructor(row.get("instructor"), instructor_cache)
		if not employee:
			skipped += 1
			continue

		start_dt = slot.get("start")
		end_dt = slot.get("end")
		if not start_dt or not end_dt:
			skipped += 1
			continue

		location = slot.get("location") or row.get("location")
		if not location:
			if strict_location:
				frappe.throw(f"Missing location for Teaching slot: {student_group} rd={rd} block={bn}")
			skipped += 1
			continue
		if not is_bookable_room(location):
			if strict_location:
				frappe.throw(f"Non-bookable location for Teaching slot: {student_group} rd={rd} block={bn} ({location})")
			skipped += 1
			continue

		start_dt = _normalize_dt(start_dt)
		end_dt = _normalize_dt(end_dt)

		name = _upsert_teaching_booking(
			employee=employee,
			start_dt=start_dt,
			end_dt=end_dt,
			location=location,
			source_name=student_group,
			school=school,
			academic_year=academic_year,
		)

		if name:
			upserted += 1
			target_keys.add((employee, start_dt, end_dt))
		else:
			skipped += 1

	deleted = _delete_obsolete_teaching_bookings(
		student_group=student_group,
		start_dt=_normalize_dt(window_start_dt),
		end_dt=_normalize_dt(window_end_dt),
		target_keys=target_keys,
	)

	return {
		"student_group": student_group,
		"upserted": upserted,
		"deleted": deleted,
		"skipped": skipped,
		"start_date": str(start_bound),
		"end_date": str(end_bound),
	}


def rebuild_all_teaching_bookings(
	*,
	academic_year: Optional[str] = None,
	only_active: bool = True,
	start_date: Optional[str] = None,
	end_date: Optional[str] = None,
	strict_location: bool = True,
	limit: Optional[int] = None,
) -> dict:
	"""
	Bulk rebuild for demo/admin.

	Example:
	  bench --site <site> execute ifitwala_ed.scripts.rebuild_teaching_employee_bookings.rebuild_all_teaching_bookings --kwargs "{'academic_year':'IIS 2025-2026'}"
	"""
	conditions: List[str] = []
	params: List[Any] = []

	if academic_year:
		conditions.append("sg.academic_year = %s")
		params.append(academic_year)

	if only_active:
		conditions.append("sg.status = 'Active'")

	where = (" where " + " and ".join(conditions)) if conditions else ""

	sql = f"""
		select sg.name
		from `tabStudent Group` sg
		{where}
		order by sg.modified desc
	"""
	if limit:
		sql += " limit %s"
		params.append(int(limit))

	rows = frappe.db.sql(sql, params, as_dict=True)

	sd = getdate(start_date) if start_date else None
	ed = getdate(end_date) if end_date else None

	out = {"groups": [], "totals": {"upserted": 0, "deleted": 0, "skipped": 0}}
	for r in rows:
		res = rebuild_student_group_teaching_bookings(
			r["name"],
			start_date=sd,
			end_date=ed,
			strict_location=strict_location,
		)
		out["groups"].append(res)
		out["totals"]["upserted"] += res["upserted"]
		out["totals"]["deleted"] += res["deleted"]
		out["totals"]["skipped"] += res["skipped"]

	return out


def execute():
	logger = frappe.logger("employee_booking_migration")

	if not frappe.db.table_exists("Employee Booking"):
		logger.warning("Employee Booking table not found; skipping migration.")
		return

	try:
		result = rebuild_all_teaching_bookings(strict_location=True)
	except Exception as exc:
		logger.exception(f"Teaching booking migration failed: {exc}")
		raise

	totals = (result or {}).get("totals") or {}
	logger.info(
		"Teaching booking migration complete. "
		f"Upserted: {totals.get('upserted', 0)}; "
		f"Deleted: {totals.get('deleted', 0)}; "
		f"Skipped: {totals.get('skipped', 0)}."
	)

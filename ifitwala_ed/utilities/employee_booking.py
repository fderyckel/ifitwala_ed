# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/employee_booking.py

"""
Employee Booking = concrete, materialized staff commitments.

This table represents REAL, DATETIME-BASED bookings that:
- always block employee availability
- are suitable for conflict detection and calendars

Sources include:
- Meetings
- Student Group teaching slots (when materialized)
- Future booking types

IMPORTANT:
Employee Booking is NOT an abstract schedule.
Absence of an Employee Booking means the employee is free.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import get_datetime, formatdate, format_time


# ─────────────────────────────────────────────────────────────
# Core helpers
# ─────────────────────────────────────────────────────────────

def _normalize_dt(value) -> datetime:
	if isinstance(value, datetime):
		return value
	return get_datetime(value)


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
	"""
	Half-open interval overlap check:
	[a_start, a_end) vs [b_start, b_end)
	"""
	return not (a_end <= b_start or b_end <= a_start)


@dataclass
class EmployeeSlot:
	employee: str
	start: datetime
	end: datetime
	blocks_availability: int
	source_doctype: str
	source_name: str
	booking_type: str
	extra: dict | None = None


# ─────────────────────────────────────────────────────────────
# Public conflict API
# ─────────────────────────────────────────────────────────────

def find_employee_conflicts(
	employee: str,
	start,
	end,
	*,
	include_soft: bool = False,
	exclude: Optional[Dict[str, str]] = None,
) -> List[EmployeeSlot]:
	"""
	Return ALL conflicting bookings for a given employee in [start, end).

	Args:
	    employee: Employee name
	    start / end: datetime or string; [start, end) interval
	    include_soft: include bookings where blocks_availability=0
	    exclude: {"doctype": "...", "name": "..."} to ignore current source

	Returns:
	    List[EmployeeSlot]
	"""
	start_dt = _normalize_dt(start)
	end_dt = _normalize_dt(end)

	if end_dt <= start_dt or not employee:
		return []

	if not frappe.db.table_exists("Employee Booking"):
		return []

	params: list[Any] = [employee, end_dt, start_dt]

	where_clauses = [
		"`employee` = %s",
		"`from_datetime` < %s",
		"`to_datetime` > %s",
	]

	if not include_soft:
		where_clauses.append("`blocks_availability` = 1")

	# Narrow SQL pre-filter; precise overlap check in Python for safety.
	sql = f"""
		select
			name,
			employee,
			from_datetime,
			to_datetime,
			blocks_availability,
			source_doctype,
			source_name,
			booking_type,
			school,
			academic_year
		from `tabEmployee Booking`
		where {" and ".join(where_clauses)}
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)

	conflicts: List[EmployeeSlot] = []
	exclude_dt = exclude.get("doctype") if exclude else None
	exclude_name = exclude.get("name") if exclude else None

	for r in rows:
		# Optional exact source exclusion
		if exclude_dt and exclude_name:
			if r.get("source_doctype") == exclude_dt and r.get("source_name") == exclude_name:
				continue

		b_start = _normalize_dt(r["from_datetime"])
		b_end = _normalize_dt(r["to_datetime"])

		if not _overlaps(start_dt, end_dt, b_start, b_end):
			continue

		conflicts.append(
			EmployeeSlot(
				employee=r["employee"],
				start=b_start,
				end=b_end,
				blocks_availability=int(r.get("blocks_availability") or 0),
				source_doctype=r["source_doctype"],
				source_name=r["source_name"],
				booking_type=r.get("booking_type") or "Other",
				extra={
					"booking_name": r.get("name"),
					"school": r.get("school"),
					"academic_year": r.get("academic_year"),
				},
			)
		)

	return conflicts

def is_employee_free(
	employee: str,
	start,
	end,
	*,
	exclude: Optional[Dict[str, str]] = None,
) -> bool:
	"""
	Convenience wrapper: True if there are NO hard conflicts.
	"""
	return not find_employee_conflicts(
		employee=employee,
		start=start,
		end=end,
		include_soft=False,
		exclude=exclude,
	)

def assert_employee_free(
    employee: str,
    start,
    end,
    *,
    exclude: Optional[Dict[str, str]] = None,
    allow_double_booking: bool = False,
) -> None:
    """
    Guard for controllers (Meetings, etc.).

    - If allow_double_booking=False:
          Throw if any hard conflict exists.
    - If allow_double_booking=True:
          Do not throw (but you might log/warn upstream).
    """

    conflicts = find_employee_conflicts(
        employee=employee,
        start=start,
        end=end,
        include_soft=False,
        exclude=exclude,
    )

    if not conflicts or allow_double_booking:
        return

    # Try to show a human name instead of raw Employee ID
    emp_label = frappe.db.get_value("Employee", employee, "employee_full_name") or employee

    lines: list[str] = []
    for c in conflicts:
        # Human-readable date and time (no seconds)
        date_label = formatdate(c.start, "d MMMM yyyy")          # e.g. "3 December 2025"
        start_time = format_time(c.start, "HH:mm")               # e.g. "10:00"
        end_time   = format_time(c.end, "HH:mm")                 # e.g. "10:55"

        lines.append(
            _("{booking_type} ({source_doctype} {source_name}) on {date} from {from_time} to {to_time}").format(
                booking_type=c.booking_type,
                source_doctype=c.source_doctype,
                source_name=c.source_name,
                date=date_label,
                from_time=start_time,
                to_time=end_time,
            )
        )

    msg = "<br>".join(lines)

    frappe.throw(
        _("{employee_name} is already booked in this time window:<br>{details}").format(
            employee_name=emp_label,
            details=msg,
        ),
        title=_("Employee Scheduling Conflict"),
    )

# ─────────────────────────────────────────────────────────────
# Upsert / cleanup helpers
# ─────────────────────────────────────────────────────────────

# Architectural note:
# This function materializes concrete bookings.
# It must never be called for abstract schedules unless the caller
# has explicitly decided to materialize them.
def upsert_employee_booking(
    *,
    employee: str,
    start,
    end,
    source_doctype: str,
    source_name: str,
    location: Optional[str] = None,
    booking_type: str = "Other",
    blocks_availability: int = 1,
    school: Optional[str] = None,
    academic_year: Optional[str] = None,
    unique_by_slot: bool = False,
) -> str:
	"""
	Create or update an Employee Booking row.

	Behaviour:
	- If unique_by_slot = False (default):
		one row per (employee, source_doctype, source_name)
		→ good for Meetings.
	- If unique_by_slot = True:
		one row per (employee, source_doctype, source_name, from_datetime, to_datetime)
		→ required for Student Group teaching slots.
	"""
	# NOTE:
	# Employee Booking enforces STAFF availability.
	# For Teaching, location is mandatory and used for room availability.
	assert True, "Employee Booking is the staff availability source (Teaching rows also block rooms)."
	start_dt = _normalize_dt(start)
	end_dt = _normalize_dt(end)

	if end_dt <= start_dt:
		# Nothing to book; ensure any existing row is removed.
		delete_employee_bookings_for_source(
			source_doctype,
			source_name,
			employee=employee,
		)
		return ""

	if booking_type == "Teaching" and not location:
		frappe.throw(_("Teaching bookings require a location."), frappe.ValidationError)

	# Build uniqueness filter
	filters: Dict[str, Any] = {
		"employee": employee,
		"source_doctype": source_doctype,
		"source_name": source_name,
	}
	if unique_by_slot:
		filters["from_datetime"] = start_dt
		filters["to_datetime"] = end_dt

	existing_name = frappe.db.get_value(
		"Employee Booking",
		filters,
		"name",
	)

	if existing_name:
		update_values = {
			"from_datetime": start_dt,
			"to_datetime": end_dt,
			"booking_type": booking_type,
			"blocks_availability": int(blocks_availability),
			"school": school,
			"academic_year": academic_year,
		}
		if location is not None:
			update_values["location"] = location
		frappe.db.set_value("Employee Booking", existing_name, update_values)
		return existing_name

	doc = frappe.get_doc(
		{
			"doctype": "Employee Booking",
			"employee": employee,
			"from_datetime": start_dt,
			"to_datetime": end_dt,
			"booking_type": booking_type,
			"blocks_availability": int(blocks_availability),
			"source_doctype": source_doctype,
			"source_name": source_name,
			"location": location,
			"school": school,
			"academic_year": academic_year,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def delete_employee_bookings_for_source(
	source_doctype: str,
	source_name: str,
	*,
	employee: Optional[str] = None,
) -> None:
	"""
	Delete booking rows for a given source document.

	If employee is provided, restrict deletion to that employee.
	Useful when:
	    - A meeting participant is removed
	    - A Student Group instructor changes
	    - A document is cancelled/deleted
	"""
	filters: Dict[str, Any] = {
		"source_doctype": source_doctype,
		"source_name": source_name,
	}
	if employee:
		filters["employee"] = employee

	# Direct delete – no need to load docs.
	frappe.db.delete("Employee Booking", filters)

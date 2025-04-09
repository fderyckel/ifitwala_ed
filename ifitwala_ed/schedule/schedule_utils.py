# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_days, get_datetime, get_time, getdate
from datetime import timedelta
from frappe.utils import today
from frappe import _

## function to get the start and end dates of the current academic year
## used in program enrollment, course enrollment too. 
@frappe.whitelist()
def get_school_term_bounds(school, academic_year):
	if not school or not academic_year:
		return {}

	terms = frappe.db.sql("""
		SELECT name, term_start_date, term_end_date
		FROM `tabTerm`
		WHERE school = %s AND academic_year = %s
	    """, (school,academic_year), as_dict=True)

	if not terms:
		return {}

	# Sort in memory
	term_start = min(terms, key=lambda t: t["term_start_date"])
	term_end = max(terms, key=lambda t: t["term_end_date"])

	return {
		"term_start": term_start["name"],
		"term_end": term_end["name"]
	}


## used in schedule.py (our virtual doctype for showing the schedules)
def current_academic_year():
    today_date = today()
    academic_year = frappe.db.get_value("Academic Year",
        {"year_start_date": ["<=", today_date], "year_end_date": [">=", today_date],
         "status": "Active"
        },"name"
    )

    if not academic_year:
        frappe.throw(_("No active academic year found for today's date."))

    return academic_year

def get_rotation_dates(school_schedule_name, academic_year, include_holidays=False):
    # Fetch necessary documents
    school_schedule = frappe.get_cached_doc("School Schedule", school_schedule_name)
    academic_year_doc = frappe.get_cached_doc("Academic Year", academic_year)
    school_calendar = frappe.get_cached_doc("School Calendar", school_schedule.school_calendar)

    start_date = academic_year_doc.year_start_date
    end_date = academic_year_doc.year_end_date
    rotation_days = school_schedule.rotation_days

    # Collect holidays if not included in rotations
    holidays = set()
    if not include_holidays:
        holidays = {
            getdate(h.holiday_date)
            for h in school_calendar.holidays
        }

    rotation_dates = []
    current_date = getdate(start_date)
    rotation_index = 1

    while current_date <= getdate(end_date):
        if current_date not in holidays:
            rotation_dates.append({
                "date": current_date,
                "rotation_day": rotation_index
            })
            # Increment and reset rotation index as needed
            rotation_index = (rotation_index % rotation_days) + 1
        elif include_holidays:
            # Holidays included in rotation increment rotation day
            rotation_dates.append({
                "date": current_date,
                "rotation_day": rotation_index
            })
            rotation_index = (rotation_index % rotation_days) + 1
        # Else, skip holidays without incrementing rotation

        current_date += timedelta(days=1)

    return rotation_dates

# ifitwala_ed/hr/utils.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import calendar
import datetime

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	add_months,
	date_diff,
	flt,
	get_first_day,
	get_last_day,
	get_quarter_ending,
	get_quarter_start,
	get_year_ending,
	get_year_start,
	getdate,
)

def set_employee_name(doc):
	if doc.employee and not doc.get("employee_full_name"):
		doc.employee_full_name = frappe.db.get_value("Employee", doc.employee, "employee_full_name")


def validate_active_employee(employee: str, method=None):
	if not employee:
		frappe.throw(_("Employee is required."))
	status = frappe.db.get_value("Employee", employee, "employment_status")
	if status not in {"Active", "Temporary Leave"}:
		frappe.throw(_("Employee {0} is not active.").format(frappe.bold(employee)))


def validate_dates(doc, from_date, to_date, restrict_future_dates=True):
	date_of_joining, relieving_date = frappe.db.get_value(
		"Employee", doc.employee, ["date_of_joining", "relieving_date"]
	)
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	if date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	if relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not be greater than employee's relieving date"))


def validate_overlap(doc, from_date, to_date, organization=None):
	if doc.doctype == "Compensatory Leave Request":
		overlap = frappe.db.exists(
			"Compensatory Leave Request",
			{
				"name": ["!=", doc.name or ""],
				"employee": doc.employee,
				"docstatus": ["<", 2],
				"work_from_date": ["<=", to_date],
				"work_end_date": [">=", from_date],
			},
		)
		if overlap:
			frappe.throw(_("Compensatory Leave Request overlaps with existing request: {0}").format(overlap))
		return

	if doc.doctype == "Leave Period":
		overlap = frappe.db.exists(
			"Leave Period",
			{
				"name": ["!=", doc.name or ""],
				"organization": organization,
				"from_date": ["<=", to_date],
				"to_date": [">=", from_date],
			},
		)
		if overlap:
			frappe.throw(_("Leave Period overlaps with existing record: {0}").format(overlap))


def get_leave_period(from_date, to_date, organization):
	if not organization:
		return []
	return frappe.get_all(
		"Leave Period",
		filters={
			"organization": organization,
			"is_active": 1,
			"from_date": ["<=", to_date],
			"to_date": [">=", from_date],
		},
		fields=["name", "from_date", "to_date"],
		order_by="from_date asc",
	)


def _get_employee_context(employee: str):
	if not employee:
		return frappe._dict()
	return frappe.db.get_value(
		"Employee",
		employee,
		["current_holiday_lis", "organization"],
		as_dict=True,
	) or frappe._dict()


def get_holiday_list_for_employee(employee, organization=None, raise_exception=True):
	ctx = _get_employee_context(employee)
	if ctx.current_holiday_lis:
		return ctx.current_holiday_lis

	if raise_exception:
		frappe.throw(_("No Staff Calendar could be resolved for Employee {0}").format(employee))
	return None


def get_holidays_for_employee(employee, start_date, end_date, raise_exception=True, only_non_weekly=False):
	ctx = _get_employee_context(employee)
	start_date = getdate(start_date)
	end_date = getdate(end_date)

	holidays = []
	if ctx.current_holiday_lis:
		filters = {
			"parent": ctx.current_holiday_lis,
			"holiday_date": ("between", [start_date, end_date]),
		}
		if only_non_weekly:
			filters["weekly_off"] = 0
			holidays = frappe.get_all(
				"Staff Calendar Holidays",
				fields=["holiday_date", "description", "weekly_off"],
				filters=filters,
				order_by="holiday_date asc",
			)
			return holidays

	if raise_exception:
		frappe.throw(_("No Staff Calendar holidays could be resolved for Employee {0}").format(employee))
	return []


def get_holiday_dates_for_employee(employee, start_date, end_date):
	holidays = get_holidays_for_employee(employee, start_date, end_date, raise_exception=False)
	return [str(getdate(row.holiday_date)) for row in holidays]


def get_holiday_dates_between_range(employee, from_date, to_date):
	return get_holiday_dates_for_employee(employee, from_date, to_date)


def share_doc_with_approver(doc, approver):
	if not approver:
		return
	if not frappe.db.exists("User", approver):
		return
	try:
		frappe.share.add(doc.doctype, doc.name, approver, read=1, write=1, notify=0)
	except Exception:
		# Sharing is best-effort and should not block leave processing.
		return


def validate_bulk_tool_fields(doc, mandatory_fields, employees, from_field, to_field):
	if not employees:
		frappe.throw(_("Select at least one employee."))
	for fieldname in mandatory_fields:
		if not doc.get(fieldname):
			frappe.throw(_("Field {0} is required.").format(frappe.bold(doc.meta.get_label(fieldname) or fieldname)))
	if doc.get(from_field) and doc.get(to_field) and getdate(doc.get(from_field)) > getdate(doc.get(to_field)):
		frappe.throw(_("From Date cannot be after To Date."))


def create_additional_leave_ledger_entry(allocation, leaves, date):
	allocation.new_leaves_allocated = leaves
	allocation.from_date = date
	allocation.unused_leaves = 0
	allocation.create_leave_ledger_entry()


def get_semester_start(date):
	date = getdate(date)
	return datetime.date(date.year, 1, 1) if date.month <= 6 else datetime.date(date.year, 7, 1)


def get_semester_end(date):
	date = getdate(date)
	return datetime.date(date.year, 6, 30) if date.month <= 6 else datetime.date(date.year, 12, 31)


def get_sub_period_start_and_end(date, frequency):
	return {
		"Monthly": (get_first_day(date), get_last_day(date)),
		"Quarterly": (get_quarter_start(date), get_quarter_ending(date)),
		"Half-Yearly": (get_semester_start(date), get_semester_end(date)),
		"Yearly": (get_year_start(date), get_year_ending(date)),
	}.get(frequency)


def round_earned_leaves(earned_leaves, rounding):
	if not rounding:
		return earned_leaves
	if rounding == "0.25":
		return round(earned_leaves * 4) / 4
	if rounding == "0.5":
		return round(earned_leaves * 2) / 2
	return round(earned_leaves)


def get_monthly_earned_leave(
	date_of_joining,
	annual_leaves,
	frequency,
	rounding,
	period_start_date=None,
	period_end_date=None,
	pro_rated=True,
):
	earned_leaves = 0.0
	divide_by_frequency = {"Yearly": 1, "Half-Yearly": 2, "Quarterly": 4, "Monthly": 12}
	if annual_leaves:
		earned_leaves = flt(annual_leaves) / divide_by_frequency[frequency]
		if pro_rated:
			if not (period_start_date and period_end_date):
				period_start_date, period_end_date = get_sub_period_start_and_end(getdate(), frequency)
			earned_leaves = calculate_pro_rated_leaves(
				earned_leaves,
				date_of_joining,
				period_start_date,
				period_end_date,
				is_earned_leave=True,
			)
		earned_leaves = round_earned_leaves(earned_leaves, rounding)
	return earned_leaves


def calculate_pro_rated_leaves(leaves, date_of_joining, period_start_date, period_end_date, is_earned_leave=False):
	if not leaves or getdate(date_of_joining) <= getdate(period_start_date):
		return leaves
	actual_period = date_diff(period_end_date, date_of_joining) + 1
	complete_period = date_diff(period_end_date, period_start_date) + 1
	leaves = leaves * actual_period / complete_period
	return flt(leaves) if is_earned_leave else round(leaves)


def get_expected_allocation_date_for_period(frequency, allocate_on_day, date, date_of_joining=None):
	date = getdate(date)
	doj = None
	if date_of_joining:
		doj_src = getdate(date_of_joining)
		try:
			doj = doj_src.replace(month=date.month, year=date.year)
		except ValueError:
			doj = datetime.date(date.year, date.month, calendar.monthrange(date.year, date.month)[1])
	return {
		"Monthly": {
			"First Day": get_first_day(date),
			"Last Day": get_last_day(date),
			"Date of Joining": doj or get_first_day(date),
		},
		"Quarterly": {"First Day": get_quarter_start(date), "Last Day": get_quarter_ending(date)},
		"Half-Yearly": {"First Day": get_semester_start(date), "Last Day": get_semester_end(date)},
		"Yearly": {"First Day": get_year_start(date), "Last Day": get_year_ending(date)},
	}[frequency][allocate_on_day]


def get_earned_leaves():
	return frappe.get_all(
		"Leave Type",
		fields=["name", "max_leaves_allowed", "earned_leave_frequency", "rounding", "allocate_on_day"],
		filters={"is_earned_leave": 1},
	)


def get_leave_allocations(date, leave_type):
	employee = frappe.qb.DocType("Employee")
	leave_allocation = frappe.qb.DocType("Leave Allocation")
	earned_leave_schedule = frappe.qb.DocType("Earned Leave Schedule")
	from frappe.query_builder.functions import Count

	query = (
		frappe.qb.from_(leave_allocation)
		.join(employee)
		.on(leave_allocation.employee == employee.name)
		.left_join(earned_leave_schedule)
		.on(leave_allocation.name == earned_leave_schedule.parent)
		.select(
			leave_allocation.name,
			leave_allocation.employee,
			leave_allocation.from_date,
			leave_allocation.to_date,
			leave_allocation.leave_policy_assignment,
			leave_allocation.leave_policy,
			Count(earned_leave_schedule.parent).as_("earned_leave_schedule_exists"),
		)
		.where(
			(date >= leave_allocation.from_date)
			& (date <= leave_allocation.to_date)
			& (leave_allocation.docstatus == 1)
			& (leave_allocation.leave_type == leave_type)
			& (leave_allocation.leave_policy_assignment.isnotnull())
			& (leave_allocation.leave_policy.isnotnull())
			& (employee.employment_status != "Left")
		)
		.groupby(leave_allocation.name)
	)
	return query.run(as_dict=1) or []


def get_upcoming_earned_leave_from_schedule(allocation_name, today_date):
	return frappe.db.get_value(
		"Earned Leave Schedule",
		{"parent": allocation_name, "attempted": 0, "allocation_date": today_date},
		["allocation_date", "number_of_leaves"],
	)


def get_annual_allocation_from_policy(allocation, leave_type):
	return frappe.db.get_value(
		"Leave Policy Detail",
		filters={"parent": allocation.leave_policy, "leave_type": leave_type.name},
		fieldname=["annual_allocation"],
	)


def log_allocation_error(allocation_name, error):
	error_log = frappe.log_error(error, reference_doctype="Leave Allocation")
	text = _("{0}. Check error log for more details.").format(error_log.method)
	earned_leave_schedule = frappe.qb.DocType("Earned Leave Schedule")
	today_date = getdate(frappe.flags.current_date) or getdate()
	(
		frappe.qb.update(earned_leave_schedule)
		.where(
			(earned_leave_schedule.parent == allocation_name)
			& (earned_leave_schedule.allocation_date == today_date)
		)
		.set(earned_leave_schedule.attempted, 1)
		.set(earned_leave_schedule.failed, 1)
		.set(earned_leave_schedule.failure_reason, text)
	).run()


def update_previous_leave_allocation(allocation, annual_allocation, leave_type, earned_leaves, today_date):
	allocation = frappe.get_doc("Leave Allocation", allocation.name)
	annual_allocation = flt(annual_allocation, allocation.precision("total_leaves_allocated"))
	new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)
	new_allocation_without_cf = flt(
		flt(allocation.get_existing_leave_count()) + flt(earned_leaves),
		allocation.precision("total_leaves_allocated"),
	)

	if leave_type.max_leaves_allowed > 0 and new_allocation > leave_type.max_leaves_allowed:
		frappe.throw(
			_("Allocation skipped because maximum leave limit in Leave Type would be exceeded.")
		)
	if leave_type.earned_leave_frequency != "Yearly" and new_allocation_without_cf > annual_allocation:
		frappe.throw(
			_("Allocation skipped because annual leave allocation in Leave Policy would be exceeded.")
		)

	allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
	create_additional_leave_ledger_entry(allocation, earned_leaves, today_date)
	earned_leave_schedule = frappe.qb.DocType("Earned Leave Schedule")
	(
		frappe.qb.update(earned_leave_schedule)
		.where(
			(earned_leave_schedule.parent == allocation.name)
			& (earned_leave_schedule.allocation_date == today_date)
		)
		.set(earned_leave_schedule.is_allocated, 1)
		.set(earned_leave_schedule.attempted, 1)
		.set(earned_leave_schedule.allocated_via, "Scheduler")
	).run()


def allocate_earned_leaves():
	if not frappe.db.exists("DocType", "HR Settings"):
		return
	if not frappe.db.get_single_value("HR Settings", "enable_earned_leave_scheduler"):
		return

	e_leave_types = get_earned_leaves()
	today_date = frappe.flags.current_date or getdate()
	failed_allocations = []

	for leave_type in e_leave_types:
		leave_allocations = get_leave_allocations(today_date, leave_type.name)
		for allocation in leave_allocations:
			if allocation.earned_leave_schedule_exists:
				allocation_date, earned_leaves = get_upcoming_earned_leave_from_schedule(
					allocation.name, today_date
				) or (None, None)
				annual_allocation = get_annual_allocation_from_policy(allocation, leave_type)
			else:
				date_of_joining = frappe.db.get_value("Employee", allocation.employee, "date_of_joining")
				allocation_date = get_expected_allocation_date_for_period(
					leave_type.earned_leave_frequency,
					leave_type.allocate_on_day,
					today_date,
					date_of_joining,
				)
				annual_allocation = get_annual_allocation_from_policy(allocation, leave_type)
				earned_leaves = get_monthly_earned_leave(
					date_of_joining,
					annual_allocation,
					leave_type.earned_leave_frequency,
					leave_type.rounding,
				)

			if not allocation_date or allocation_date != today_date:
				continue

			try:
				update_previous_leave_allocation(
					allocation, annual_allocation, leave_type, earned_leaves, today_date
				)
			except Exception as err:
				log_allocation_error(allocation.name, err)
				failed_allocations.append(allocation.name)

	if failed_allocations:
		frappe.log_error(
			title="Earned Leave Allocation Failures",
			message=f"Failed allocations: {', '.join(failed_allocations)}",
		)


def generate_leave_encashment():
	if not frappe.db.exists("DocType", "HR Settings"):
		return
	if not frappe.db.get_single_value("HR Settings", "enable_leave_encashment"):
		return
	if not frappe.db.get_single_value("HR Settings", "auto_leave_encashment"):
		return
	if not frappe.db.exists("DocType", "Leave Encashment"):
		return

	from ifitwala_ed.hr.doctype.leave_encashment.leave_encashment import create_leave_encashment

	leave_types = frappe.get_all("Leave Type", filters={"allow_encashment": 1}, pluck="name")
	if not leave_types:
		return

	leave_allocations = frappe.get_all(
		"Leave Allocation",
		filters=[["to_date", "=", add_days(getdate(), -1)], ["leave_type", "in", leave_types]],
		fields=[
			"employee",
			"leave_period",
			"leave_type",
			"to_date",
			"total_leaves_allocated",
			"new_leaves_allocated",
		],
	)
	create_leave_encashment(leave_allocation=leave_allocations)

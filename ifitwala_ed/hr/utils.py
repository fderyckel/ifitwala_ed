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
    cint,
    date_diff,
    flt,
    get_first_day,
    get_last_day,
    get_quarter_ending,
    get_quarter_start,
    get_year_ending,
    get_year_start,
    getdate,
    today,
)

from ifitwala_ed.utilities.school_tree import get_ancestor_schools

EARNED_LEAVE_CHUNK_SIZE = 100
EARNED_LEAVE_DISPATCH_LOCK_KEY = "ifitwala_ed:scheduler:earned_leave:dispatch"
EARNED_LEAVE_SUMMARY_CACHE_KEY = "ifitwala_ed:scheduler:earned_leave:last_run"
LEAVE_ENCASHMENT_CHUNK_SIZE = 100
LEAVE_ENCASHMENT_DISPATCH_LOCK_KEY = "ifitwala_ed:scheduler:leave_encashment:dispatch"
LEAVE_ENCASHMENT_SUMMARY_CACHE_KEY = "ifitwala_ed:scheduler:leave_encashment:last_run"
PORTAL_CALENDAR_CACHE_PREFIX = "ifitwala_ed:portal_calendar:"


def _chunk_values(values, chunk_size):
    chunk_size = max(cint(chunk_size) or 1, 1)
    for start in range(0, len(values), chunk_size):
        yield values[start : start + chunk_size]


def _record_scheduler_summary(cache_key, logger_name, summary):
    frappe.cache().set_value(
        cache_key,
        frappe.as_json(summary),
        expires_in_sec=60 * 60 * 24 * 7,
    )
    frappe.logger(logger_name, allow_site=True).info(summary)


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
    return (
        frappe.db.get_value(
            "Employee",
            employee,
            ["current_holiday_lis", "organization"],
            as_dict=True,
        )
        or frappe._dict()
    )


def _get_staff_calendar_context(employee: str):
    if not employee:
        return frappe._dict()
    return (
        frappe.db.get_value(
            "Employee",
            employee,
            ["name", "school", "employee_group", "current_holiday_lis", "employment_status"],
            as_dict=True,
        )
        or frappe._dict()
    )


def _staff_calendar_sort_date(raw_value) -> int:
    if not raw_value:
        return datetime.date.min.toordinal()
    return getdate(raw_value).toordinal()


def _calendar_overlaps_window(calendar_row, start_date=None, end_date=None) -> bool:
    start_date = getdate(start_date) if start_date else None
    end_date = getdate(end_date) if end_date else None

    if start_date and not end_date:
        end_date = start_date
    if end_date and not start_date:
        start_date = end_date

    from_date = getdate(calendar_row.get("from_date")) if calendar_row.get("from_date") else None
    to_date = getdate(calendar_row.get("to_date")) if calendar_row.get("to_date") else None

    if start_date and to_date and to_date < start_date:
        return False
    if end_date and from_date and from_date > end_date:
        return False
    return True


def _get_staff_calendar_docrow(calendar_name: str | None, *, ignore_calendar_name: str | None = None):
    calendar_name = (calendar_name or "").strip()
    if not calendar_name:
        return None
    if ignore_calendar_name and calendar_name == ignore_calendar_name:
        return None

    rows = frappe.get_all(
        "Staff Calendar",
        filters={"name": calendar_name},
        fields=["name", "school", "employee_group", "from_date", "to_date"],
        limit=1,
        ignore_permissions=True,
    )
    return rows[0] if rows else None


def _get_staff_calendar_candidates(
    employee_group: str,
    *,
    start_date=None,
    end_date=None,
    ignore_calendar_name: str | None = None,
):
    employee_group = (employee_group or "").strip()
    if not employee_group:
        return []

    filters = {"employee_group": employee_group}
    if start_date:
        filters["to_date"] = [">=", getdate(start_date)]
    if end_date:
        filters["from_date"] = ["<=", getdate(end_date)]

    rows = frappe.get_all(
        "Staff Calendar",
        filters=filters,
        fields=["name", "school", "employee_group", "from_date", "to_date"],
        limit=0,
        ignore_permissions=True,
    )
    if ignore_calendar_name:
        rows = [row for row in rows if (row.get("name") or "") != ignore_calendar_name]
    return rows


def _scope_staff_calendar_candidates(candidates, employee_school: str | None):
    if not candidates:
        return []

    if employee_school:
        school_chain = get_ancestor_schools(employee_school) or [employee_school]
        school_rank = {school: idx for idx, school in enumerate(school_chain)}
        scoped = [row for row in candidates if (row.get("school") or "").strip() in school_rank]
        scoped.sort(
            key=lambda row: (
                school_rank.get((row.get("school") or "").strip(), 10**9),
                -_staff_calendar_sort_date(row.get("from_date")),
                row.get("name") or "",
            )
        )
        return scoped

    if len(candidates) == 1:
        return sorted(
            candidates,
            key=lambda row: (-_staff_calendar_sort_date(row.get("from_date")), row.get("name") or ""),
        )

    return []


def _linked_staff_calendar_from_candidates(candidates, calendar_name: str | None):
    calendar_name = (calendar_name or "").strip()
    if not calendar_name:
        return None

    for row in candidates or []:
        if (row.get("name") or "").strip() == calendar_name:
            return row

    return None


def resolve_staff_calendar_for_employee(
    employee: str,
    *,
    start_date=None,
    end_date=None,
    ignore_calendar_name: str | None = None,
):
    ctx = _get_staff_calendar_context(employee)
    if not ctx:
        return None

    start_date = getdate(start_date) if start_date else None
    end_date = getdate(end_date) if end_date else None
    if start_date and not end_date:
        end_date = start_date
    if end_date and not start_date:
        start_date = end_date

    linked_calendar = _get_staff_calendar_docrow(
        ctx.current_holiday_lis,
        ignore_calendar_name=ignore_calendar_name,
    )
    if linked_calendar and _calendar_overlaps_window(linked_calendar, start_date, end_date):
        linked_calendar["resolution"] = "employee_link"
        return linked_calendar

    employee_group = (ctx.employee_group or "").strip()
    if not employee_group:
        return None

    candidates = _get_staff_calendar_candidates(
        employee_group,
        start_date=start_date,
        end_date=end_date,
        ignore_calendar_name=ignore_calendar_name,
    )
    if not linked_calendar:
        linked_calendar = _linked_staff_calendar_from_candidates(candidates, ctx.current_holiday_lis)
        if linked_calendar and _calendar_overlaps_window(linked_calendar, start_date, end_date):
            linked_calendar["resolution"] = "employee_link"
            return linked_calendar

    scoped = _scope_staff_calendar_candidates(candidates, ctx.school)
    if scoped:
        scoped[0]["resolution"] = "matched_scope"
        return scoped[0]

    return None


def resolve_current_staff_calendar_for_employee(
    employee: str,
    *,
    as_of_date=None,
    ignore_calendar_name: str | None = None,
):
    ctx = _get_staff_calendar_context(employee)
    if not ctx:
        return None

    if ctx.get("employment_status") != "Active":
        return None

    current_date = getdate(as_of_date or today())

    linked_calendar = _get_staff_calendar_docrow(
        ctx.current_holiday_lis,
        ignore_calendar_name=ignore_calendar_name,
    )
    if linked_calendar and _calendar_overlaps_window(linked_calendar, current_date, current_date):
        linked_calendar["resolution"] = "employee_link"
        return linked_calendar

    employee_group = (ctx.employee_group or "").strip()
    if not employee_group:
        if linked_calendar:
            linked_calendar["resolution"] = "employee_link_stale"
            return linked_calendar
        return None

    candidates = _get_staff_calendar_candidates(
        employee_group,
        ignore_calendar_name=ignore_calendar_name,
    )
    if not linked_calendar:
        linked_calendar = _linked_staff_calendar_from_candidates(candidates, ctx.current_holiday_lis)
        if linked_calendar and _calendar_overlaps_window(linked_calendar, current_date, current_date):
            linked_calendar["resolution"] = "employee_link"
            return linked_calendar

    scoped = _scope_staff_calendar_candidates(candidates, ctx.school)

    active_candidates = [row for row in scoped if _calendar_overlaps_window(row, current_date, current_date)]
    if active_candidates:
        active_candidates.sort(
            key=lambda row: (-_staff_calendar_sort_date(row.get("from_date")), row.get("name") or "")
        )
        active_candidates[0]["resolution"] = "matched_current"
        return active_candidates[0]

    if scoped:
        scoped.sort(key=lambda row: (-_staff_calendar_sort_date(row.get("from_date")), row.get("name") or ""))
        scoped[0]["resolution"] = "matched_latest"
        return scoped[0]

    if linked_calendar:
        linked_calendar["resolution"] = "employee_link_stale"
        return linked_calendar

    return None


def invalidate_staff_portal_calendar_cache(employee: str | None = None):
    cache = frappe.cache()
    pattern = f"{PORTAL_CALENDAR_CACHE_PREFIX}{employee}:*" if employee else f"{PORTAL_CALENDAR_CACHE_PREFIX}*"
    for key in cache.get_keys(pattern):
        cache.delete_value(key)


def sync_current_staff_calendar_for_employee(
    employee: str,
    *,
    update_modified: bool = False,
    ignore_calendar_name: str | None = None,
):
    if not employee or not frappe.db.exists("Employee", employee):
        return None

    resolved = resolve_current_staff_calendar_for_employee(
        employee,
        ignore_calendar_name=ignore_calendar_name,
    )
    resolved_name = (resolved or {}).get("name")
    current_name = frappe.db.get_value("Employee", employee, "current_holiday_lis")

    if (current_name or None) != (resolved_name or None):
        frappe.db.set_value(
            "Employee",
            employee,
            "current_holiday_lis",
            resolved_name,
            update_modified=update_modified,
        )
        invalidate_staff_portal_calendar_cache(employee)

    return resolved_name


def get_holiday_list_for_employee(employee, organization=None, raise_exception=True):
    ctx = _get_employee_context(employee)
    linked_calendar = (ctx.get("current_holiday_lis") or "").strip() if ctx else ""
    if linked_calendar:
        return linked_calendar

    calendar_row = resolve_current_staff_calendar_for_employee(employee)
    if calendar_row:
        return calendar_row.get("name")

    if raise_exception:
        frappe.throw(_("No Staff Calendar could be resolved for Employee {0}").format(employee))
    return None


def get_holidays_for_employee(employee, start_date, end_date, raise_exception=True, only_non_weekly=False):
    start_date = getdate(start_date)
    end_date = getdate(end_date)
    ctx = _get_employee_context(employee)
    linked_calendar = (ctx.get("current_holiday_lis") or "").strip() if ctx else ""
    calendar_name = linked_calendar

    calendar_row = None
    if not calendar_name:
        calendar_row = resolve_staff_calendar_for_employee(employee, start_date=start_date, end_date=end_date)
        calendar_name = (calendar_row or {}).get("name")

    holidays = []
    if calendar_name:
        filters = {
            "parent": calendar_name,
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


def get_leave_allocations(date, leave_type, allocation_names=None):
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
    if allocation_names:
        query = query.where(leave_allocation.name.isin(list(dict.fromkeys(allocation_names))))
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
            (earned_leave_schedule.parent == allocation_name) & (earned_leave_schedule.allocation_date == today_date)
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
        frappe.throw(_("Allocation skipped because maximum leave limit in Leave Type would be exceeded."))
    if leave_type.earned_leave_frequency != "Yearly" and new_allocation_without_cf > annual_allocation:
        frappe.throw(_("Allocation skipped because annual leave allocation in Leave Policy would be exceeded."))

    allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
    create_additional_leave_ledger_entry(allocation, earned_leaves, today_date)
    earned_leave_schedule = frappe.qb.DocType("Earned Leave Schedule")
    (
        frappe.qb.update(earned_leave_schedule)
        .where(
            (earned_leave_schedule.parent == allocation.name) & (earned_leave_schedule.allocation_date == today_date)
        )
        .set(earned_leave_schedule.is_allocated, 1)
        .set(earned_leave_schedule.attempted, 1)
        .set(earned_leave_schedule.allocated_via, "Scheduler")
    ).run()


def _earned_leave_scheduler_enabled():
    if not frappe.db.exists("DocType", "HR Settings"):
        return False
    return bool(frappe.db.get_single_value("HR Settings", "enable_earned_leave_scheduler"))


def _leave_encashment_scheduler_enabled():
    if not frappe.db.exists("DocType", "HR Settings"):
        return False
    if not frappe.db.get_single_value("HR Settings", "enable_leave_encashment"):
        return False
    if not frappe.db.get_single_value("HR Settings", "auto_leave_encashment"):
        return False
    return frappe.db.exists("DocType", "Leave Encashment")


def _get_today_date():
    return getattr(frappe.flags, "current_date", None) or getdate()


def _get_leave_type_details(leave_type_name):
    leave_type = frappe.db.get_value(
        "Leave Type",
        leave_type_name,
        ["name", "max_leaves_allowed", "earned_leave_frequency", "rounding", "allocate_on_day"],
        as_dict=True,
    )
    return frappe._dict(leave_type or {})


def _process_earned_leave_rows(leave_type, leave_allocations, today_date):
    failed_allocations = []
    processed = 0
    skipped = 0
    cache = frappe.cache()

    for allocation in leave_allocations:
        lock_key = f"ifitwala_ed:scheduler:earned_leave:allocation:{allocation.name}"
        with cache.lock(lock_key, timeout=60):
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
                skipped += 1
                continue

            try:
                update_previous_leave_allocation(allocation, annual_allocation, leave_type, earned_leaves, today_date)
                processed += 1
            except Exception as err:
                log_allocation_error(allocation.name, err)
                failed_allocations.append(allocation.name)

    return {
        "processed_count": processed,
        "skipped_count": skipped,
        "failed_count": len(failed_allocations),
        "failed_allocations": failed_allocations,
    }


def dispatch_allocate_earned_leaves(chunk_size=EARNED_LEAVE_CHUNK_SIZE):
    if not _earned_leave_scheduler_enabled():
        summary = {"job": "allocate_earned_leaves", "status": "disabled"}
        _record_scheduler_summary(EARNED_LEAVE_SUMMARY_CACHE_KEY, "earned_leave_scheduler", summary)
        return summary

    chunk_size = max(cint(chunk_size) or EARNED_LEAVE_CHUNK_SIZE, 1)
    today_date = _get_today_date()
    cache = frappe.cache()
    with cache.lock(EARNED_LEAVE_DISPATCH_LOCK_KEY, timeout=60 * 15):
        chunk_count = 0
        candidate_count = 0
        for leave_type in get_earned_leaves():
            allocation_names = [row.name for row in get_leave_allocations(today_date, leave_type.name)]
            candidate_count += len(allocation_names)
            for chunk in _chunk_values(allocation_names, chunk_size):
                frappe.enqueue(
                    "ifitwala_ed.hr.utils.process_earned_leave_allocation_chunk",
                    queue="long",
                    leave_type_name=leave_type.name,
                    allocation_names=chunk,
                    today_date=str(today_date),
                )
                chunk_count += 1

        summary = {
            "job": "allocate_earned_leaves",
            "status": "queued",
            "candidate_count": candidate_count,
            "chunk_count": chunk_count,
            "chunk_size": chunk_size,
        }
        _record_scheduler_summary(EARNED_LEAVE_SUMMARY_CACHE_KEY, "earned_leave_scheduler", summary)
        return summary


def allocate_earned_leaves():
    if not _earned_leave_scheduler_enabled():
        return {"processed_count": 0, "skipped_count": 0, "failed_count": 0}

    e_leave_types = get_earned_leaves()
    today_date = _get_today_date()
    failed_allocations = []
    processed = 0
    skipped = 0

    for leave_type in e_leave_types:
        leave_allocations = get_leave_allocations(today_date, leave_type.name)
        result = _process_earned_leave_rows(leave_type, leave_allocations, today_date)
        processed += result["processed_count"]
        skipped += result["skipped_count"]
        failed_allocations.extend(result["failed_allocations"])

    if failed_allocations:
        frappe.log_error(
            title="Earned Leave Allocation Failures",
            message=f"Failed allocations: {', '.join(failed_allocations)}",
        )
    return {
        "processed_count": processed,
        "skipped_count": skipped,
        "failed_count": len(failed_allocations),
    }


def process_earned_leave_allocation_chunk(leave_type_name, allocation_names=None, today_date=None):
    allocation_names = list(dict.fromkeys(allocation_names or []))
    if not allocation_names:
        summary = {
            "job": "allocate_earned_leaves",
            "status": "processed",
            "requested_count": 0,
            "processed_count": 0,
        }
        _record_scheduler_summary(EARNED_LEAVE_SUMMARY_CACHE_KEY, "earned_leave_scheduler", summary)
        return summary

    target_date = getdate(today_date) if today_date else _get_today_date()
    leave_type = _get_leave_type_details(leave_type_name)
    leave_allocations = get_leave_allocations(target_date, leave_type_name, allocation_names=allocation_names)
    result = _process_earned_leave_rows(leave_type, leave_allocations, target_date)
    summary = {
        "job": "allocate_earned_leaves",
        "status": "processed",
        "leave_type": leave_type_name,
        "requested_count": len(allocation_names),
        "processed_count": result["processed_count"],
        "skipped_count": len(allocation_names) - result["processed_count"] - result["failed_count"],
        "failed_count": result["failed_count"],
    }
    _record_scheduler_summary(EARNED_LEAVE_SUMMARY_CACHE_KEY, "earned_leave_scheduler", summary)
    return summary


def _get_leave_encashment_rows(target_date, allocation_names=None):
    leave_types = frappe.get_all("Leave Type", filters={"allow_encashment": 1}, pluck="name")
    if not leave_types:
        return []

    filters = [["to_date", "=", target_date], ["leave_type", "in", leave_types]]
    if allocation_names:
        filters.append(["name", "in", list(dict.fromkeys(allocation_names))])

    return frappe.get_all(
        "Leave Allocation",
        filters=filters,
        fields=[
            "name",
            "employee",
            "leave_period",
            "leave_type",
            "to_date",
            "total_leaves_allocated",
            "new_leaves_allocated",
        ],
    )


def _process_leave_encashment_rows(leave_allocations):
    from ifitwala_ed.hr.doctype.leave_encashment.leave_encashment import (
        create_leave_encashment,
        get_assigned_salary_structure,
    )

    processed = 0
    skipped = 0
    failed = 0
    cache = frappe.cache()

    for allocation in leave_allocations:
        lock_key = f"ifitwala_ed:scheduler:leave_encashment:allocation:{allocation.name}"
        with cache.lock(lock_key, timeout=60):
            if frappe.db.exists("Leave Encashment", {"leave_allocation": allocation.name, "docstatus": ["<", 2]}):
                skipped += 1
                continue
            if not get_assigned_salary_structure(allocation.employee, allocation.to_date):
                skipped += 1
                continue
            try:
                create_leave_encashment(leave_allocation=[allocation])
                processed += 1
            except Exception:
                failed += 1
                frappe.logger("leave_encashment_scheduler", allow_site=True).exception(
                    "Failed to create leave encashment for allocation %s",
                    allocation.name,
                )

    return {
        "processed_count": processed,
        "skipped_count": skipped,
        "failed_count": failed,
    }


def dispatch_generate_leave_encashment(chunk_size=LEAVE_ENCASHMENT_CHUNK_SIZE):
    if not _leave_encashment_scheduler_enabled():
        summary = {"job": "generate_leave_encashment", "status": "disabled"}
        _record_scheduler_summary(LEAVE_ENCASHMENT_SUMMARY_CACHE_KEY, "leave_encashment_scheduler", summary)
        return summary

    chunk_size = max(cint(chunk_size) or LEAVE_ENCASHMENT_CHUNK_SIZE, 1)
    target_date = add_days(getdate(), -1)
    cache = frappe.cache()
    with cache.lock(LEAVE_ENCASHMENT_DISPATCH_LOCK_KEY, timeout=60 * 15):
        allocations = _get_leave_encashment_rows(target_date)
        chunk_count = 0
        for chunk in _chunk_values([row.name for row in allocations], chunk_size):
            frappe.enqueue(
                "ifitwala_ed.hr.utils.process_leave_encashment_chunk",
                queue="long",
                allocation_names=chunk,
                target_date=str(target_date),
            )
            chunk_count += 1

        summary = {
            "job": "generate_leave_encashment",
            "status": "queued",
            "candidate_count": len(allocations),
            "chunk_count": chunk_count,
            "chunk_size": chunk_size,
        }
        _record_scheduler_summary(LEAVE_ENCASHMENT_SUMMARY_CACHE_KEY, "leave_encashment_scheduler", summary)
        return summary


def generate_leave_encashment():
    if not _leave_encashment_scheduler_enabled():
        return {"processed_count": 0, "skipped_count": 0, "failed_count": 0}

    target_date = add_days(getdate(), -1)
    leave_allocations = _get_leave_encashment_rows(target_date)
    return _process_leave_encashment_rows(leave_allocations)


def process_leave_encashment_chunk(allocation_names=None, target_date=None):
    allocation_names = list(dict.fromkeys(allocation_names or []))
    if not allocation_names:
        summary = {
            "job": "generate_leave_encashment",
            "status": "processed",
            "requested_count": 0,
            "processed_count": 0,
        }
        _record_scheduler_summary(LEAVE_ENCASHMENT_SUMMARY_CACHE_KEY, "leave_encashment_scheduler", summary)
        return summary

    run_date = getdate(target_date) if target_date else add_days(getdate(), -1)
    leave_allocations = _get_leave_encashment_rows(run_date, allocation_names=allocation_names)
    result = _process_leave_encashment_rows(leave_allocations)
    summary = {
        "job": "generate_leave_encashment",
        "status": "processed",
        "requested_count": len(allocation_names),
        "processed_count": result["processed_count"],
        "skipped_count": result["skipped_count"],
        "failed_count": result["failed_count"],
    }
    _record_scheduler_summary(LEAVE_ENCASHMENT_SUMMARY_CACHE_KEY, "leave_encashment_scheduler", summary)
    return summary

# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.hr.doctype.staff_calendar.staff_calendar

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, formatdate, getdate


class StaffCalendar(Document):
    def validate(self):
        self._validate_period()
        self._validate_overlaps()
        self.validate_duplicate_date()
        self.sort_holidays()

        # totals
        self.total_holidays = len(self.holidays or [])
        if self.from_date and self.to_date:
            # inclusive of both from_date and to_date
            self.total_working_day = date_diff(self.to_date, self.from_date) + 1 - self.total_holidays
        else:
            self.total_working_day = 0

    def _validate_period(self):
        if not self.from_date or not self.to_date:
            frappe.throw(_("From Date and To Date are required."))

        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw(_("From Date cannot be after To Date. Please adjust the date."))

        # enforce Employee Group (core of the design)
        if not getattr(self, "employee_group", None):
            frappe.throw(_("Employee Group must be specified for this Staff Calendar."))

    def _validate_overlaps(self):
        """Block overlapping staff calendars for same school + employee_group (+ AY)."""
        if not (self.school and self.employee_group and self.from_date and self.to_date):
            return

        params = {
            "name": self.name or "New Staff Calendar",
            "school": self.school,
            "employee_group": self.employee_group,
            "from_date": self.from_date,
            "to_date": self.to_date,
        }

        # Optional: also scope by academic_year if set
        ay_clause = ""
        if self.academic_year:
            ay_clause = "and academic_year = %(academic_year)s"
            params["academic_year"] = self.academic_year

        # Overlap logic: NOT (other.to_date < this.from_date OR other.from_date > this.to_date)
        conflicts = frappe.db.sql(
            f"""
			select
				name
			from
				`tabStaff Calendar`
			where
				name != %(name)s
				and school = %(school)s
				and employee_group = %(employee_group)s
				{ay_clause}
				and not (
					to_date < %(from_date)s
					or from_date > %(to_date)s
				)
			""",
            params,
            as_dict=True,
        )

        if conflicts:
            conflict_names = ", ".join(c["name"] for c in conflicts)
            frappe.throw(
                _(
                    "Staff Calendar overlaps with existing calendar(s): {0}. "
                    "Please adjust the dates or reuse the existing calendar."
                ).format(conflict_names)
            )

    def validate_duplicate_date(self):
        unique_dates = []
        for day in self.holidays:
            if day.holiday_date in unique_dates:
                frappe.throw(
                    _("Date {0} is duplicated. Please remove the duplicate date.").format(formatdate(day.holiday_date))
                )
            unique_dates.append(day.holiday_date)

    def sort_holidays(self):
        self.holidays.sort(key=lambda x: getdate(x.holiday_date))
        for idx, row in enumerate(self.holidays, start=1):
            row.idx = idx

    def get_holidays(self) -> list[date]:
        return [getdate(h.holiday_date) for h in (self.holidays or [])]

    # ──────────────────────────────────────────────────────────────
    # Persistence helpers (fix for "nothing appears in child table")
    # ──────────────────────────────────────────────────────────────

    def _ensure_saved(self):
        if self.get("__islocal") or not self.name:
            frappe.throw(_("Please save this Staff Calendar first, then add holidays."))

    def _commit_holidays(self):
        # keep ordering deterministic + persist to DB
        self.sort_holidays()
        # validate() recomputes totals during save()
        self.save()

    # ──────────────────────────────────────────────────────────────
    # Holiday generators (must save to persist rows)
    # ──────────────────────────────────────────────────────────────

    @frappe.whitelist()
    def get_weekly_off_dates(self):
        self._ensure_saved()

        if not self.weekly_off:
            frappe.throw(_("Please select first the weekly off day."))

        existing = self.get_holidays()
        added = 0

        for d in self.get_weekly_off_dates_list(self.from_date, self.to_date):
            if d in existing:
                continue

            self.append(
                "holidays",
                {
                    "holiday_date": d,
                    "description": _("Weekly Off"),
                    "color": self.weekend_color,
                    "weekly_off": 1,
                },
            )
            added += 1

        if added:
            self._commit_holidays()

        return {"added": added}

    def get_weekly_off_dates_list(self, start_date, end_date):
        start, end = getdate(start_date), getdate(end_date)
        import calendar
        from datetime import timedelta

        from dateutil import relativedelta

        date_list = []
        existing = [getdate(h.holiday_date) for h in (self.get("holidays") or [])]
        weekday = getattr(calendar, (self.weekly_off).upper())
        reference = start + relativedelta.relativedelta(weekday=weekday)

        while reference <= end:
            if reference not in existing:
                date_list.append(reference)
            reference += timedelta(days=7)

        return date_list

    @frappe.whitelist()
    def get_country_holidays(self):
        self._ensure_saved()

        from holidays import country_holidays

        if not self.country:
            frappe.throw(_("Please select the country first."))

        existing = self.get_holidays()
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        added = 0

        for holiday_date, holiday_name in country_holidays(
            self.country,
            subdiv=self.subdivision,
            years=list(range(from_date.year, to_date.year + 1)),
            language=frappe.local.lang,
        ).items():
            if holiday_date in existing:
                continue
            if holiday_date < from_date or holiday_date > to_date:
                continue

            self.append(
                "holidays",
                {
                    "holiday_date": holiday_date,
                    "description": holiday_name,
                    "weekly_off": 0,
                    "color": self.local_holiday_color,
                },
            )
            added += 1

        if added:
            self._commit_holidays()

        return {"added": added}

    @frappe.whitelist()
    def get_supported_countries(self):
        from holidays.utils import list_supported_countries

        subdivisions_by_country = list_supported_countries()
        countries = [{"value": code, "label": code} for code in sorted(subdivisions_by_country.keys())]
        return {
            "countries": countries,
            "subdivisions_by_country": subdivisions_by_country,
        }

    @frappe.whitelist()
    def get_break_holidays(self):
        self._ensure_saved()

        self.validate_break_values()
        existing = self.get_holidays()
        added = 0

        for d in self.get_long_break_dates_list(self.start_of_break, self.end_of_break):
            if d in existing:
                continue

            self.append(
                "holidays",
                {
                    "holiday_date": d,
                    "description": self.break_description,
                    "color": self.break_color,
                    "weekly_off": 0,
                },
            )
            added += 1

        if added:
            self._commit_holidays()

        return {"added": added}

    def validate_break_values(self):
        if not (self.start_of_break and self.end_of_break):
            frappe.throw(_("Please select the start and end of the break."))
        if getdate(self.start_of_break) > getdate(self.end_of_break):
            frappe.throw(_("The start of the break cannot be after its end."))
        if not (getdate(self.from_date) <= getdate(self.start_of_break) <= getdate(self.to_date)) or not (
            getdate(self.from_date) <= getdate(self.end_of_break) <= getdate(self.to_date)
        ):
            frappe.throw(_("The break period must fall within the calendar period."))

    def get_long_break_dates_list(self, start_date, end_date):
        start, end = getdate(start_date), getdate(end_date)
        from datetime import timedelta

        date_list = []
        existing = [getdate(h.holiday_date) for h in (self.get("holidays") or [])]
        reference = start

        while reference <= end:
            if reference not in existing:
                date_list.append(reference)
            reference += timedelta(days=1)

        return date_list

    @frappe.whitelist()
    def clear_table(self):
        self._ensure_saved()

        self.set("holidays", [])
        self._commit_holidays()
        return {"cleared": 1}

    @frappe.whitelist()
    def copy_from_calendar(self, source_calendar):
        self._ensure_saved()

        if not source_calendar:
            frappe.throw(_("Please specify a source calendar."))

        src = frappe.get_doc("Staff Calendar", source_calendar)

        if src.school != self.school:
            frappe.throw(_("Source calendar must belong to the same school."))

        existing = {getdate(h.holiday_date) for h in (self.holidays or [])}
        added = 0

        for row in src.holidays or []:
            if getdate(row.holiday_date) in existing:
                continue
            self.append(
                "holidays",
                {
                    "holiday_date": row.holiday_date,
                    "description": row.description,
                    "color": row.color,
                    "weekly_off": row.weekly_off,
                },
            )
            added += 1

        if added:
            self._commit_holidays()

        return {"added": added}

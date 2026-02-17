# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
    cint,
    date_diff,
    formatdate,
    get_link_to_form,
    getdate,
)
from frappe.utils.nestedset import get_ancestors_of

from ifitwala_ed.school_settings.school_settings_utils import (
    resolve_terms_for_school_calendar,
)
from ifitwala_ed.utilities.school_tree import (
    ParentRuleViolation,
    get_descendant_schools,
)


class SchoolCalendar(Document):
    def autoname(self):
        if not self.academic_year or not self.school:
            frappe.throw(_("Academic Year and School are required to generate the Calendar Name."))

        abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
        ay_name = frappe.db.get_value("Academic Year", self.academic_year, "academic_year_name") or self.academic_year

        if not self.calendar_name:
            self.calendar_name = ay_name

        self.name = f"{abbr} {self.calendar_name}"
        self.title = self.name

    def onload(self):
        if not self.school:
            return

        self.set_onload(
            "weekend_color",
            frappe.db.get_value("School", self.school, "weekend_color"),
        )
        self.set_onload(
            "break_color",
            frappe.db.get_value("School", self.school, "break_color"),
        )

    def validate(self):
        self._sync_school_with_ay()
        self._validate_uniqueness()
        self._populate_term_table()

        self.validate_dates()
        self.validate_holiday_uniqueness()

        ay = frappe.get_doc("Academic Year", self.academic_year)

        self.total_number_day = date_diff(getdate(ay.year_end_date), getdate(ay.year_start_date)) + 1

        # Holidays include:
        # - breaks
        # - public holidays
        # - weekends (weekly_off = 1)
        self.total_holiday_days = len(self.holidays or [])

        self.total_instruction_days = self.total_number_day - self.total_holiday_days

    # ----------------------------------------------------------------
    def _sync_school_with_ay(self):
        """
        Pattern B enforcement.

        A School Calendar MUST be explicitly scoped to a school.
        Academic Year defines the allowed hierarchy, but never assigns implicitly.
        """
        if not self.school:
            frappe.throw(
                _("School is required. School Calendars must be explicitly scoped to a school."),
                title=_("Missing School"),
            )

        ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
        allowed = [self.school] + get_ancestors_of("School", self.school)

        if ay_school not in allowed:
            raise ParentRuleViolation(
                _("School {0} is not within the Academic Year's hierarchy ({1}).").format(self.school, ay_school)
            )

    # ----------------------------------------------------------------
    def _validate_uniqueness(self):
        """Disallow two calendars with same Academic Year + School."""
        if frappe.db.exists(
            "School Calendar",
            {
                "academic_year": self.academic_year,
                "school": self.school,
                "name": ("!=", self.name),
                "docstatus": ("<", 2),
            },
        ):
            frappe.throw(
                _("A School Calendar for {0} – {1} already exists.").format(self.school, self.academic_year),
                title=_("Duplicate"),
            )

    # ----------------------------------------------------------------
    def _populate_term_table(self):
        """
        Option B:
        Terms are resolved explicitly via School Calendar,
        not inferred from Academic Year or school hierarchy.
        """

        term_names = resolve_terms_for_school_calendar(
            self.school,
            self.academic_year,
        )

        self.terms = []

        if not term_names:
            return

        terms = frappe.get_all(
            "Term",
            fields=["name", "term_start_date", "term_end_date"],
            filters={"name": ["in", term_names]},
            order_by="term_start_date",
        )

        # Use in-memory holidays (authoritative during validate)
        holiday_dates = {getdate(h.holiday_date) for h in (self.holidays or [])}

        for term in terms:
            start = getdate(term["term_start_date"])
            end = getdate(term["term_end_date"])

            total_days = date_diff(end, start) + 1

            non_instructional_days = len([d for d in holiday_dates if start <= d <= end])

            self.append(
                "terms",
                {
                    "term": term["name"],
                    "start": start,
                    "end": end,
                    "number_of_instructional_days": (total_days - non_instructional_days),
                },
            )

    # ----------------------------------------------------------------
    def validate_holiday_uniqueness(self):
        seen = set()
        for h in self.get("holidays"):
            d = getdate(h.holiday_date)
            if d in seen:
                frappe.throw(_("Duplicate holiday date found: {0}").format(formatdate(d)))
            seen.add(d)

    def validate_dates(self):
        """Ensure holidays are within the academic year"""
        ay = frappe.get_doc("Academic Year", self.academic_year)

        for day in self.get("holidays"):
            if not (getdate(ay.year_start_date) <= getdate(day.holiday_date) <= getdate(ay.year_end_date)):
                frappe.throw(
                    _("The {0} holiday is not within your school's academic year {1}").format(
                        formatdate(day.holiday_date),
                        get_link_to_form("Academic Year", self.academic_year),
                    )
                )

    # ----------------------------------------------------------------
    @frappe.whitelist()
    def get_long_break_dates(self):
        self.validate_break_dates()
        date_list = self.get_long_break_dates_list(self.start_of_break, self.end_of_break)
        last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0])

        for i, d in enumerate(date_list):
            ch = self.append("holidays", {})
            ch.description = self.break_description or "Break"
            ch.color = self.break_color or ""
            ch.holiday_date = d
            ch.idx = last_idx + i + 1

        frappe.msgprint(_("Break dates for '{0}' have been successfully added.").format(self.break_description))

    def validate_break_dates(self):
        ay = frappe.get_doc("Academic Year", self.academic_year)

        if not self.start_of_break or not self.end_of_break:
            frappe.throw(_("Please select both start and end dates for the break."))

        if getdate(self.start_of_break) > getdate(self.end_of_break):
            frappe.throw(_("Break start date must be before end date."))

        if not (
            getdate(ay.year_start_date) <= getdate(self.start_of_break) <= getdate(ay.year_end_date)
            and getdate(ay.year_start_date) <= getdate(self.end_of_break) <= getdate(ay.year_end_date)
        ):
            frappe.throw(
                _("Break must be within the academic year {0}.").format(
                    get_link_to_form("Academic Year", self.academic_year)
                )
            )

    def get_long_break_dates_list(self, start_date, end_date):
        from datetime import timedelta

        start_date, end_date = getdate(start_date), getdate(end_date)
        existing = {getdate(h.holiday_date) for h in self.get("holidays")}

        ref = start_date
        out = []
        while ref <= end_date:
            if ref not in existing:
                out.append(ref)
            ref += timedelta(days=1)

        return out

    # ----------------------------------------------------------------
    @frappe.whitelist()
    def get_weekly_off_dates(self):
        ay = frappe.get_doc("Academic Year", self.academic_year)
        self.validate_values()

        date_list = self.get_weekly_off_dates_list(ay.year_start_date, ay.year_end_date)
        last_idx = max([cint(d.idx) for d in self.get("holidays")] or [0])

        for i, d in enumerate(date_list):
            ch = self.append("holidays", {})
            ch.description = _(self.weekly_off)
            ch.holiday_date = d
            ch.color = self.weekend_color or ""
            ch.weekly_off = 1
            ch.idx = last_idx + i + 1

    def validate_values(self):
        if not self.weekly_off:
            frappe.throw(_("Please select the weekly off day."))

    def get_weekly_off_dates_list(self, start_date, end_date):
        import calendar
        from datetime import timedelta

        from dateutil import relativedelta

        start_date, end_date = getdate(start_date), getdate(end_date)
        weekday = getattr(calendar, self.weekly_off.upper())
        existing = {getdate(h.holiday_date) for h in self.get("holidays")}

        ref = start_date + relativedelta.relativedelta(weekday=weekday)
        out = []

        while ref <= end_date:
            if ref not in existing:
                out.append(ref)
            ref += timedelta(days=7)

        return out

    def on_doctype_update():
        frappe.db.add_index("School Calendar", ["academic_year", "school"])


# ---------------------------------------------------------------------
@frappe.whitelist()
def get_events(start, end, filters=None):
    filters = json.loads(filters) if filters else {}

    school = filters.get("school")
    academic_year = filters.get("academic_year")

    if not school or not academic_year:
        frappe.throw(_("School and Academic Year are required."))

    calendar = frappe.get_all(
        "School Calendar",
        filters={
            "school": school,
            "academic_year": academic_year,
        },
        pluck="name",
        limit=1,
    )

    if not calendar:
        return []

    event_filters = [
        ["School Calendar Holidays", "parent", "=", calendar[0]],
    ]

    if start:
        event_filters.append(["School Calendar Holidays", "holiday_date", ">=", getdate(start)])
    if end:
        event_filters.append(["School Calendar Holidays", "holiday_date", "<=", getdate(end)])

    return frappe.get_list(
        "School Calendar Holidays",
        fields=[
            "holiday_date as start",
            "description as title",
            "color",
        ],
        filters=event_filters,
        update={"allDay": 1},
    )


@frappe.whitelist()
def clone_calendar(source_calendar, academic_year, schools):
    src = frappe.get_doc("School Calendar", source_calendar)
    created = []

    for school in frappe.parse_json(schools):
        if frappe.db.exists(
            "School Calendar",
            {"academic_year": academic_year, "school": school},
        ):
            continue

        dup = frappe.copy_doc(src, ignore_no_copy=True)
        dup.school = school
        dup.academic_year = academic_year
        dup.calendar_name = academic_year
        dup.save()

        created.append(get_link_to_form("School Calendar", dup.name))

    return ", ".join(created) if created else _("No new calendars created.")


def get_permission_query_conditions(user):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"

    schools = [user_school] + get_descendant_schools(user_school)
    if not schools:
        return "1=0"

    schools_list = "', '".join(schools)
    return f"`tabSchool Calendar`.`school` IN ('{schools_list}')"


def has_permission(doc, ptype=None, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    allowed_schools = [user_school] + get_descendant_schools(user_school)
    return doc.school in allowed_schools

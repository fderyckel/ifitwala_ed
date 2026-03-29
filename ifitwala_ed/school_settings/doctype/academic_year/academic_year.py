# Copyright (c) 2024, François de Ryckel
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/academic_year/academic_year.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_link_to_form, getdate

from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools


def _get_branch_school_scope(user_school) -> list[str]:
    """
    Return the caller's school branch only:
    - the user's school and descendants
    - the user's school and ancestors

    This keeps sibling isolation intact while allowing users to see ancestor-school
    Academic Years needed by descendant-school operational surfaces.
    """
    if not user_school:
        return []

    descendants = get_descendant_schools(user_school) or [user_school]
    ancestors = get_ancestor_schools(user_school) or [user_school]
    return list(dict.fromkeys([*descendants, *ancestors]))


class AcademicYear(Document):
    def autoname(self):
        abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
        self.name = f"{abbr} {self.academic_year_name}"

    # ──────────────────────────────────────────────────────────────────
    def validate(self):
        self.title = self.name
        self._validate_duplicate()
        self._validate_dates()

    def on_update(self):
        if self.year_start_date and self.year_end_date:
            self.create_calendar_events()

    def _validate_duplicate(self):
        # same ay_name in same school not allowed
        if frappe.db.exists(
            "Academic Year",
            {
                "academic_year_name": self.academic_year_name,
                "school": self.school,
                "name": ("!=", self.name),
                "docstatus": ("<", 2),
            },
        ):
            frappe.throw(
                _("Academic Year {academic_year} already exists for school {school}.").format(
                    academic_year=self.academic_year_name,
                    school=self.school,
                ),
                title=_("Duplicate"),
            )

    def _validate_dates(self):
        if self.year_start_date and self.year_end_date and getdate(self.year_start_date) > getdate(self.year_end_date):
            frappe.throw(
                _("Start date ({start_date}) must be before end date ({end_date}).").format(
                    start_date=self.year_start_date,
                    end_date=self.year_end_date,
                ),
                title=_("Date Error"),
            )

    def create_calendar_events(self):
        # Update existing linked events (dates only)
        if self.ay_start:
            start_ay = frappe.get_doc("School Event", self.ay_start)
            if getdate(start_ay.starts_on) != getdate(self.year_start_date):
                start_ay.db_set("starts_on", self.year_start_date)
                start_ay.db_set("ends_on", self.year_start_date)
                frappe.msgprint(
                    _(
                        "Date for the start of the year {start_date} has been updated on the School Event Calendar {school_event}"
                    ).format(
                        start_date=self.year_start_date,
                        school_event=get_link_to_form("School Event", start_ay.name),
                    )
                )

        if self.ay_end:
            end_ay = frappe.get_doc("School Event", self.ay_end)
            if getdate(end_ay.ends_on) != getdate(self.year_end_date):
                end_ay.db_set("starts_on", self.year_end_date)
                end_ay.db_set("ends_on", self.year_end_date)
                frappe.msgprint(
                    _(
                        "Date for the end of the year {end_date} has been updated on the School Event Calendar {school_event}"
                    ).format(
                        end_date=self.year_end_date,
                        school_event=get_link_to_form("School Event", end_ay.name),
                    )
                )

        # Create missing events (MUST set school + audience)
        if not self.ay_start:
            start_year = frappe.get_doc(
                {
                    "doctype": "School Event",
                    "owner": frappe.session.user,
                    "school": self.school,
                    "subject": _("Start of the {academic_year} Academic Year").format(academic_year=cstr(self.name)),
                    "starts_on": getdate(self.year_start_date),
                    "ends_on": getdate(self.year_start_date),
                    "event_category": "Other",
                    "all_day": 1,
                    "color": "#7575ff",
                    "reference_type": "Academic Year",
                    "reference_name": self.name,
                    "audience": [{"audience_type": "Whole School Community"}],
                }
            )
            start_year.flags.ignore_audience_permissions = True
            start_year.insert(ignore_permissions=True)

            self.db_set("ay_start", start_year.name)
            frappe.msgprint(
                _(
                    "Date for the start of the year {start_date} has been created on the School Event Calendar {school_event}"
                ).format(
                    start_date=self.year_start_date,
                    school_event=get_link_to_form("School Event", start_year.name),
                )
            )

        if not self.ay_end:
            end_year = frappe.get_doc(
                {
                    "doctype": "School Event",
                    "owner": frappe.session.user,
                    "school": self.school,
                    "subject": _("End of the {academic_year} Academic Year").format(academic_year=cstr(self.name)),
                    "starts_on": getdate(self.year_end_date),
                    "ends_on": getdate(self.year_end_date),
                    "event_category": "Other",
                    "all_day": 1,
                    "color": "#7575ff",
                    "reference_type": "Academic Year",
                    "reference_name": self.name,
                    "audience": [{"audience_type": "Whole School Community"}],
                }
            )
            end_year.flags.ignore_audience_permissions = True
            end_year.insert(ignore_permissions=True)

            self.db_set("ay_end", end_year.name)
            frappe.msgprint(
                _(
                    "Date for the end of the year {end_date} has been created on the School Event Calendar {school_event}"
                ).format(
                    end_date=self.year_end_date,
                    school_event=get_link_to_form("School Event", end_year.name),
                )
            )

    @frappe.whitelist()
    def retire_ay(self, school_scope=None):
        """
        Deprecated: use End of Year Checklist for scoped closures.
        This legacy method requires an explicit school scope to avoid global updates.
        """
        if not school_scope:
            frappe.throw(
                _("retire_ay() is deprecated and requires an explicit school scope."),
                title=_("Deprecated"),
            )
        if isinstance(school_scope, str):
            school_scope = frappe.parse_json(school_scope)
        if not isinstance(school_scope, (list, tuple)) or not school_scope:
            frappe.throw(_("school_scope must be a non-empty list."), title=_("Invalid Scope"))
        if self.school not in school_scope:
            frappe.throw(_("Academic Year school must be included in school_scope."), title=_("Invalid Scope"))

        # 1. Retire all active Terms linked to this Academic Year
        frappe.db.sql(
            """
            UPDATE `tabTerm`
            SET archived = 1
            WHERE academic_year = %s
            AND archived = 0
        """,
            (self.name,),
        )

        # 2. Retire all active Program Enrollments for this Academic Year
        frappe.db.sql(
            """
            UPDATE `tabProgram Enrollment`
               SET archived = 1
             WHERE academic_year = %(academic_year)s
               AND school IN %(schools)s
               AND archived = 0
            """,
            {"schools": tuple(school_scope), "academic_year": self.name},
        )

        # Update the Academic Year's own status to indicate it is retired
        self.db_set("archived", 1)
        frappe.db.commit()
        frappe.msgprint(
            _(
                "Academic Year retired successfully. Archived status set to 1 for linked program enrollments and terms. "
                "Use End of Year Checklist for full, scoped closure."
            )
        )
        return "Academic Year archived successfully."


@frappe.whitelist()
def retire_academic_year(academic_year, school_scope=None):
    # Fetch the Academic Year doc and call its retire method
    doc = frappe.get_doc("Academic Year", academic_year)
    return doc.retire_ay(school_scope=school_scope)


def get_permission_query_conditions(user):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"

    schools = _get_branch_school_scope(user_school)
    if not schools:
        return "1=0"
    schools_list = "', '".join(schools)
    return f"`tabAcademic Year`.`school` IN ('{schools_list}')"


def has_permission(doc, ptype=None, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    schools = _get_branch_school_scope(user_school)
    return doc.school in schools

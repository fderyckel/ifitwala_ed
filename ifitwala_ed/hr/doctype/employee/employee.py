# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed.hr.doctype.employee.employee

import importlib

import frappe
from frappe import _, scrub
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.permissions import get_doc_permissions
from frappe.utils import add_years, cstr, getdate, today, validate_email_address
from frappe.utils.nestedset import NestedSet

from ifitwala_ed.utilities.employee_utils import (
    get_descendant_organizations,
    get_user_base_org,
)
from ifitwala_ed.utilities.image_utils import get_preferred_employee_image_url
from ifitwala_ed.utilities.transaction_base import delete_events
from ifitwala_ed.website.utils import slugify_route_segment


class EmployeeUserDisabledError(frappe.ValidationError):
    pass


class InactiveEmployeeStatusError(frappe.ValidationError):
    pass


def invalidate_staff_portal_calendar_cache(*args, **kwargs):
    from ifitwala_ed.hr.utils import invalidate_staff_portal_calendar_cache as current_invalidate

    return current_invalidate(*args, **kwargs)


def resolve_current_staff_calendar_for_employee(*args, **kwargs):
    from ifitwala_ed.hr.utils import (
        resolve_current_staff_calendar_for_employee as current_resolve_staff_calendar,
    )

    return current_resolve_staff_calendar(*args, **kwargs)


def get_school_lineage(*args, **kwargs):
    from ifitwala_ed.utilities.school_tree import get_school_lineage as current_get_school_lineage

    return current_get_school_lineage(*args, **kwargs)


def _refresh_runtime_bindings():
    global frappe, _, scrub, load_address_and_contact, get_doc_permissions
    global invalidate_staff_portal_calendar_cache, resolve_current_staff_calendar_for_employee
    global get_descendant_organizations, get_user_base_org, get_preferred_employee_image_url
    global get_school_lineage, delete_events, slugify_route_segment

    current_frappe = importlib.import_module("frappe")
    bound_is_stub = getattr(frappe, "__file__", None) is None
    current_is_real = getattr(current_frappe, "__file__", None) is not None

    if not bound_is_stub or not current_is_real or current_frappe is frappe:
        return frappe

    frappe = current_frappe
    _ = getattr(current_frappe, "_", _)
    scrub = getattr(current_frappe, "scrub", scrub)

    from frappe.contacts.address_and_contact import load_address_and_contact as current_load_address_and_contact
    from frappe.permissions import get_doc_permissions as current_get_doc_permissions

    from ifitwala_ed.hr.utils import (
        invalidate_staff_portal_calendar_cache as current_invalidate_staff_portal_calendar_cache,
    )
    from ifitwala_ed.hr.utils import (
        resolve_current_staff_calendar_for_employee as current_resolve_current_staff_calendar_for_employee,
    )
    from ifitwala_ed.utilities.employee_utils import (
        get_descendant_organizations as current_get_descendant_organizations,
    )
    from ifitwala_ed.utilities.employee_utils import get_user_base_org as current_get_user_base_org
    from ifitwala_ed.utilities.image_utils import (
        get_preferred_employee_image_url as current_get_preferred_employee_image_url,
    )
    from ifitwala_ed.utilities.school_tree import get_school_lineage as current_get_school_lineage
    from ifitwala_ed.utilities.transaction_base import delete_events as current_delete_events
    from ifitwala_ed.website.utils import slugify_route_segment as current_slugify_route_segment

    load_address_and_contact = current_load_address_and_contact
    get_doc_permissions = current_get_doc_permissions
    invalidate_staff_portal_calendar_cache = current_invalidate_staff_portal_calendar_cache
    resolve_current_staff_calendar_for_employee = current_resolve_current_staff_calendar_for_employee
    get_descendant_organizations = current_get_descendant_organizations
    get_user_base_org = current_get_user_base_org
    get_preferred_employee_image_url = current_get_preferred_employee_image_url
    get_school_lineage = current_get_school_lineage
    delete_events = current_delete_events
    slugify_route_segment = current_slugify_route_segment
    return frappe


class Employee(NestedSet):
    nsm_parent_field = "reports_to"

    def onload(self):
        """
        Load Contact and Address for HR convenience.

        RULE:
        - HR can read Contact + Address
        - HR must NOT require User read permission
        - Use the standard loader to populate __onload for the form renderer
        """
        load_address_and_contact(self)

    def get_doc_before_save(self):
        parent_getter = getattr(super(), "get_doc_before_save", None)
        if callable(parent_getter):
            return parent_getter()
        return None

    def validate(self):
        from ifitwala_ed.controllers.status_updater import validate_status

        validate_status(self.employment_status, ["Active", "Temporary Leave", "Left", "Suspended"])

        self.employee = self.name
        self.employee_full_name = " ".join(
            filter(
                None,
                [
                    self.employee_first_name,
                    self.employee_middle_name,
                    self.employee_last_name,
                ],
            )
        )

        # Pure invariants only (no heavy side-effects)
        self.validate_date()
        self.validate_email()
        self.validate_status()
        self.validate_reports_to()
        self.validate_preferred_email()
        self.validate_employee_history()
        self.validate_public_website_fields()
        self._sync_staff_calendar()

        if self.user_id:
            self.validate_user_details()
        else:
            existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
            if existing_user_id:
                user = frappe.get_doc("User", existing_user_id)
                validate_employee_role(user, ignore_emp_check=True)
                user.flags.ignore_permissions = True
                user.save(ignore_permissions=True)

        # Ensure the employee history is sorted before saving
        if self.employee_history:
            self.employee_history.sort(
                key=lambda row: getdate(row.to_date) if row.to_date else getdate("9999-12-31"),
                reverse=True,
            )

    def after_rename(self, old, new, merge):
        self.db_set("employee", new)

    def update_nsm_model(self):
        frappe.utils.nestedset.update_nsm(self)

    def _reports_to_changed(self):
        prev = self.get_doc_before_save()
        if not prev:
            # New doc insert or unknown state: be safe and update
            return True
        return (prev.reports_to or "") != (self.reports_to or "")

    def on_update(self):
        _refresh_runtime_bindings()

        # ---------------------------------------------------------
        # 1) Structural graph integrity (always allowed)
        # ---------------------------------------------------------
        if self._reports_to_changed():
            self.update_nsm_model()

        self.reset_employee_emails_cache()
        self.sync_employee_history()
        self._ensure_primary_contact()

        prev = self.get_doc_before_save() or {}
        if (prev.get("current_holiday_lis") or None) != (self.current_holiday_lis or None):
            invalidate_staff_portal_calendar_cache(self.name)

        # ---------------------------------------------------------
        # 2) Role / authority enforcement (HR-governed, safe)
        # ---------------------------------------------------------
        self._apply_designation_role()
        self._apply_approver_roles()

        # ---------------------------------------------------------
        # 3) User profile sync (STRICTLY gated)
        # ---------------------------------------------------------
        if self.user_id:
            if self._can_sync_user_profile():
                self.update_user()
            # Keep permission-driving defaults aligned regardless of profile sync gate.
            self.update_user_default_organization()
            self.update_user_default_school()

    def on_trash(self):
        _refresh_runtime_bindings()

        # Keep consistency on delete; guard to avoid unnecessary work
        if self._reports_to_changed():
            self.update_nsm_model()
        delete_events(self.doctype, self.name)

    # call on validate. Broad check to make sure birthdate, joining date are making sense.
    def validate_date(self):
        if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(today()):
            frappe.throw(_("Date of Birth cannot be after today."))
        if self.employee_date_of_birth and getdate(self.employee_date_of_birth) > getdate(add_years(today(), -16)):
            frappe.throw(_("Maybe you are too young to be an employee of this school!"))
        if (
            self.employee_date_of_birth
            and self.date_of_joining
            and getdate(self.employee_date_of_birth) >= getdate(self.date_of_joining)
        ):
            frappe.throw(_("Date of Joining must be after Date of Birth"))
        if self.notice_date and self.relieving_date and getdate(self.relieving_date) < getdate(self.notice_date):
            frappe.throw(
                _("Date of Notice {0} should be before Relieving Date {1}. Please adjust dates.").format(
                    getdate(self.notice_date), getdate(self.relieving_date)
                )
            )
        if (
            self.relieving_date
            and self.date_of_joining
            and getdate(self.relieving_date) < getdate(self.date_of_joining)
        ):
            frappe.throw(
                _("Date of Joining {0} should be before Relieving Date {1}. Please adjust dates.").format(
                    getdate(self.date_of_joining), getdate(self.relieving_date)
                )
            )

    # call on validate. Broad check to make sure the email address has an appropriate format.
    def validate_email(self):
        if self.employee_professional_email:
            validate_email_address(self.employee_professional_email, True)
        if self.employee_personal_email:
            validate_email_address(self.employee_personal_email, True)

    # call on validate. If employment status is set to left, then need to put relieving date.
    # also you can not be set as left if there are people reporting to you.
    def validate_status(self):
        if self.employment_status == "Left":
            reports_to = frappe.db.get_all(
                "Employee",
                filters={"reports_to": self.name, "employment_status": "Active"},
                fields=["name", "employee_full_name"],
            )
            if reports_to:
                link_to_employees = [
                    frappe.utils.get_link_to_form("Employee", employee.name, label=employee.employee_full_name)
                    for employee in reports_to
                ]
                message = _("The following employees are currently still reporting to {0}:").format(
                    frappe.bold(self.employee_full_name)
                )
                message += "<br><br><ul><li>" + "</li><li>".join(link_to_employees)
                message += "</li></ul><br>"
                message += _("Please make sure the employees above report to another Active employee.")
                frappe.throw(message, InactiveEmployeeStatusError, _("Cannot Relieve Employee"))
            if not self.relieving_date:
                frappe.throw(_("Please enter relieving date."))

    # You cannot report to yourself or cross organizations (only parents)
    def validate_reports_to(self):
        # Prevent self-reporting
        if self.reports_to == self.name:
            frappe.throw(_("An Employee cannot report to themselves."))

        # If no reports_to is set, skip validation
        if not self.reports_to or not self.organization:
            return

        # Get the organization of the supervisor (reports_to)
        supervisor_org = frappe.db.get_value("Employee", self.reports_to, "organization")
        if not supervisor_org:
            return  # Skip if the supervisor has no organization (edge case)

        # Allow reporting within the same organization
        if self.organization == supervisor_org:
            return

        # Validate upward hierarchy
        is_parent_org = frappe.db.sql(
            """
			SELECT 1
			FROM `tabOrganization`
			WHERE name = %s
			AND lft <= (SELECT lft FROM `tabOrganization` WHERE name = %s)
			AND rgt >= (SELECT rgt FROM `tabOrganization` WHERE name = %s)
		""",
            (supervisor_org, self.organization, self.organization),
        )

        if not is_parent_org:
            frappe.throw(
                _(
                    "Employee cannot report to a supervisor from a different organization unless it is a parent organization."
                )
            )

    def validate_public_website_fields(self):
        if int(self.show_public_profile_page or 0) == 1:
            self.show_on_website = 1

        slug = (self.public_profile_slug or "").strip()
        if not int(self.show_public_profile_page or 0):
            self.public_profile_slug = slug or None
        else:
            if not self.school:
                frappe.throw(
                    _("School is required before enabling a public profile page."),
                    frappe.ValidationError,
                )

            if not slug:
                preferred = (self.employee_preferred_name or "").strip()
                full_name = (self.employee_full_name or "").strip()
                slug = slugify_route_segment(preferred or full_name, fallback="employee")

            slug = slugify_route_segment(slug, fallback="employee")
            self.public_profile_slug = slug

            exists = frappe.db.exists(
                "Employee",
                {
                    "school": self.school,
                    "public_profile_slug": slug,
                    "name": ["!=", self.name],
                },
            )
            if exists:
                frappe.throw(
                    _("Another employee in this school already uses the public profile slug '{0}'.").format(slug),
                    frappe.ValidationError,
                )

        if self.website_sort_order in ("", None):
            self.website_sort_order = None

        # Validate downward consistency (no cross-lineage connections)
        # Fetch all direct reports of the current employee
        direct_reports = frappe.db.get_values(
            "Employee",
            filters={"reports_to": self.name},
            fieldname=["name", "organization"],
            as_dict=True,
        )

        # Get the organization lineage of the current employee
        lineage = frappe.db.sql(
            """
			SELECT name
			FROM `tabOrganization`
			WHERE lft <= (SELECT lft FROM `tabOrganization` WHERE name = %s)
			AND rgt >= (SELECT rgt FROM `tabOrganization` WHERE name = %s)
		""",
            (self.organization, self.organization),
        )

        valid_orgs = {org[0] for org in lineage}

        # Check each direct report for cross-lineage violations
        for report in direct_reports:
            if report["organization"] not in valid_orgs:
                frappe.throw(
                    _(
                        "Direct report '{0}' (Organization: {1}) cannot belong to an organization outside the hierarchy of '{2}' (Organization: {3})."
                    ).format(report["name"], report["organization"], self.name, self.organization)
                )

    # call on validate. Check that there is at least one email to use.
    def validate_preferred_email(self):
        """
        Validates the preferred contact email for an employee.

        This method checks if the preferred contact email is set and ensures that the corresponding
        field (either "User ID" or the scrubbed version of the preferred contact email) is filled.
        If the required field is not filled, it displays a message prompting the user to enter the
        preferred contact email.

        Raises:
                frappe.msgprint: If the required field for the preferred contact email is not filled.
        """
        if self.preferred_contact_email:
            if self.preferred_contact_email == "User ID" and not self.get("user_id"):
                frappe.msgprint(_("Please enter {0}").format(self.preferred_contact_email))
            elif self.preferred_contact_email and not self.get("employee_" + scrub(self.preferred_contact_email)):
                frappe.msgprint(_("Please enter {0}").format(self.preferred_contact_email))

    def update_user_default_school(self):
        _refresh_runtime_bindings()

        """Set or update the default school for the user linked to this employee."""
        if not self.user_id:
            return  # No linked user to update

        # Get the current default school for this user
        current_default = _get_user_default_from_db(self.user_id, "school")

        # Set the default if missing and a school is already filled
        if not current_default and self.school:
            frappe.defaults.set_user_default("school", self.school, self.user_id)
            frappe.cache().hdel("user:" + self.user_id, "defaults")
            frappe.msgprint(
                _("Default school set to {0} for user {1} (first-time setup).").format(self.school, self.user_id)
            )
            return

        # Handle clearing the default if the field is empty
        if not self.school:
            if current_default:
                frappe.defaults.clear_default("school", self.user_id)
                frappe.cache().hdel("user:" + self.user_id, "defaults")
                frappe.msgprint(_("Default school cleared for user {0}.").format(self.user_id))
                return

        # Update default school only if it has changed
        if self.school != current_default:
            frappe.defaults.set_user_default("school", self.school, self.user_id)
            frappe.cache().hdel("user:" + self.user_id, "defaults")
            frappe.msgprint(_("Default school set to {0} for user {1}.").format(self.school, self.user_id))

    def update_user_default_organization(self):
        _refresh_runtime_bindings()

        """Set or update the default organization for the user linked to this employee."""
        if not self.user_id:
            return  # No linked user to update

        current_default = _get_user_default_from_db(self.user_id, "organization")
        target_org = cstr(self.organization).strip()

        if not current_default and target_org:
            frappe.defaults.set_user_default("organization", target_org, self.user_id)
            frappe.cache().hdel("user:" + self.user_id, "defaults")
            frappe.msgprint(
                _("Default organization set to {0} for user {1} (first-time setup).").format(target_org, self.user_id)
            )
            return

        if not target_org:
            if current_default:
                frappe.defaults.clear_default("organization", self.user_id)
                frappe.cache().hdel("user:" + self.user_id, "defaults")
                frappe.msgprint(_("Default organization cleared for user {0}.").format(self.user_id))
            return

        if target_org != current_default:
            frappe.defaults.set_user_default("organization", target_org, self.user_id)
            frappe.cache().hdel("user:" + self.user_id, "defaults")
            frappe.msgprint(_("Default organization set to {0} for user {1}.").format(target_org, self.user_id))

    def validate_employee_history(self):
        """Validate history rows:
        - from_date required and not before date_of_joining
        - to_date >= from_date (if set)
        - NO overlap ONLY when (designation, organization, school) are the same
        - is_current is derived from dates

        NOTE: employee_history is expected to remain small; O(n²) overlap check is acceptable.
        """
        if not self.date_of_joining:
            frappe.throw(_("Please set the Employee's Date of Joining before adding Employee History."))

        today_d = getdate(today())
        join_d = getdate(self.date_of_joining)
        history = self.get("employee_history", []) or []

        def key(r):
            return (r.designation or "", r.organization or "", r.school or "")

        def rng(r):
            start = getdate(r.from_date or "0001-01-01")
            end = getdate(r.to_date or "9999-12-31")
            return start, end

        for i, row in enumerate(history):
            # require from_date
            if not row.from_date:
                frappe.throw(_("Please set 'From Date' for row #{0}.").format(i + 1))

            # row.from_date >= joining date
            if getdate(row.from_date) < join_d:
                frappe.throw(
                    _("Row #{0}: From Date cannot be before Date of Joining ({1}).").format(i + 1, self.date_of_joining)
                )

            # to_date >= from_date (if set)
            if row.to_date and getdate(row.to_date) < getdate(row.from_date):
                frappe.throw(_("Row #{0}: 'To Date' cannot be before 'From Date'.").format(i + 1))

        # pairwise overlap ONLY for identical (designation, org, school)
        for i, a in enumerate(history):
            ka = key(a)
            a_start, a_end = rng(a)
            for j, b in enumerate(history):
                if i >= j:
                    continue
                if key(b) != ka:
                    continue
                b_start, b_end = rng(b)
                # intervals intersect?
                if b_start <= a_end and a_start <= b_end:
                    frappe.throw(
                        _("Overlap detected for '{0}' @ '{1}/{2}' between row #{3} and row #{4}.").format(
                            a.designation or "-", a.organization or "-", a.school or "-", i + 1, j + 1
                        )
                    )

        # compute is_current from dates
        for row in history:
            start, end = rng(row)
            row.is_current = 1 if (start <= today_d <= end) else 0

    def sync_employee_history(self):
        """Auto-maintain history when primary tuple changes.
        - Detect change via previous doc (designation/org/school).
        - Close the latest row for the *previous* tuple to (new_from - 1).
        - Append a new row for the *current* tuple with from_date = today (idempotent).
        - Allow multiple 'current' rows across different tuples; overlap forbids only same tuple.
        """
        if not self.date_of_joining or not self.designation:
            return

        history = self.get("employee_history", []) or []
        prev = self.get_doc_before_save()

        # Initial seed if no history
        if not history:
            self.append(
                "employee_history",
                {
                    "designation": self.designation,
                    "organization": self.organization,
                    "school": self.school,
                    "from_date": self.date_of_joining,
                    # is_current will be recomputed in validate()
                },
            )
            return

        # Need previous values to detect a tuple change
        if not prev:
            return

        prev_tuple = (prev.designation, prev.organization, prev.school)
        cur_tuple = (self.designation, self.organization, self.school)

        # no change → nothing to do
        if prev_tuple == cur_tuple:
            return

        # if employee hasn't joined yet, just update the most recent matching row for prev tuple
        if getdate(self.date_of_joining) > getdate(today()):
            # update the last row (assume preparatory history)
            last = history[-1]
            last.designation = self.designation
            last.organization = self.organization
            last.school = self.school
            return

        # Change happened after joining → close previous tuple's latest row and add new one
        new_from = getdate(today())

        # correct close_to to new_from - 1 day
        close_to = getdate(frappe.utils.add_days(new_from, -1))

        # 1) close the latest row for the previous tuple (if open or crossing new_from)
        for row in reversed(history):
            if (row.designation, row.organization, row.school) == prev_tuple:
                # If it's already closed before new_from, leave it
                if not row.to_date or getdate(row.to_date) >= close_to:
                    row.to_date = close_to
                break

        # 2) avoid duplicate (same tuple @ same from_date)
        for r in history:
            if (r.designation, r.organization, r.school) == cur_tuple and getdate(
                r.from_date or "9999-12-31"
            ) == new_from:
                return

        # 3) append new row for current tuple starting today
        self.append(
            "employee_history",
            {
                "designation": self.designation,
                "organization": self.organization,
                "school": self.school,
                "from_date": new_from,
                # is_current computed in validate()
            },
        )

        # keep your sorter
        self._sort_employee_history()

    def _sort_employee_history(self):
        history = self.get("employee_history", [])

        current_roles = [row for row in history if not row.to_date]
        past_roles = [row for row in history if row.to_date]

        current_roles.sort(key=lambda row: getdate(row.from_date), reverse=True)
        past_roles.sort(key=lambda row: getdate(row.to_date), reverse=True)

        sorted_history = current_roles + past_roles
        self.set("employee_history", sorted_history)

        for idx, row in enumerate(self.employee_history, start=1):
            row.idx = idx

    # call on validate. Check that if there is already a user, a few more checks to do.
    def validate_user_details(self):
        _refresh_runtime_bindings()

        if not self.user_id:
            return

        data = frappe.db.get_value("User", self.user_id, ["enabled"], as_dict=1)
        if not data:
            frappe.throw(_("User {0} does not exist").format(self.user_id))

        self.validate_for_enabled_user_id(data.get("enabled"))
        self.validate_duplicate_user_id()

    # call on validate through validate_user_details().
    # If employee is referring to a user, that user has to be active.
    def validate_for_enabled_user_id(self, enabled):
        if not self.employment_status == "Active":
            return
        if enabled is None:
            frappe.throw(_("User {0} does not exist").format(self.user_id))
        if enabled == 0:
            frappe.throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

    # call on validate through validate_user_details().
    def validate_duplicate_user_id(self):
        Employee = frappe.qb.DocType("Employee")
        employee = (
            frappe.qb.from_("Employee")
            .select(Employee.name)
            .where(
                (Employee.user_id == self.user_id)
                & (Employee.employment_status == "Active")
                & (Employee.name != self.name)
            )
        ).run()
        if employee:
            frappe.throw(
                _("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0][0]),
                frappe.DuplicateEntryError,
            )

    # to update the user fields when employee fields are changing
    def update_user(self):
        _refresh_runtime_bindings()

        if not self.user_id:
            return

        user = frappe.get_doc("User", self.user_id)
        user.flags.ignore_permissions = True

        # Keep the base role for active staff only; non-active users are role-stripped by access sync.
        if self.employment_status == "Active" and "Employee" not in {r.role for r in user.roles}:
            user.append("roles", {"role": "Employee"})

        user.first_name = self.employee_first_name
        user.last_name = self.employee_last_name
        user.full_name = self.employee_full_name

        if self.employee_date_of_birth:
            user.birth_date = self.employee_date_of_birth

        # ---- image sync -------------------------------------------------------
        avatar_url = get_preferred_employee_image_url(self.name, original_url=self.employee_image)
        if avatar_url and user.user_image != avatar_url:
            user.user_image = avatar_url

        user.save(ignore_permissions=True)

    def _sync_staff_calendar(self):
        _refresh_runtime_bindings()

        """Resolve the authoritative Staff Calendar link for this employee before save."""
        if self.employment_status != "Active":
            self.current_holiday_lis = None
            return

        employee_name = (self.name or "").strip()
        if employee_name and frappe.db.exists("Employee", employee_name):
            selected = resolve_current_staff_calendar_for_employee(employee_name)
            self.current_holiday_lis = (selected or {}).get("name")
            return

        today_d = getdate(today())
        selected = None
        linked_name = (self.current_holiday_lis or "").strip()

        linked_rows = []
        if linked_name:
            linked_rows = frappe.get_all(
                "Staff Calendar",
                filters={"name": linked_name},
                fields=["name", "school", "from_date", "to_date"],
                limit=1,
                ignore_permissions=True,
            )
            if linked_rows:
                linked = linked_rows[0]
                from_date = getdate(linked.get("from_date")) if linked.get("from_date") else None
                to_date = getdate(linked.get("to_date")) if linked.get("to_date") else None
                if from_date and to_date and from_date <= today_d <= to_date:
                    selected = linked

        if not selected and self.employee_group:
            calendars = frappe.get_all(
                "Staff Calendar",
                filters={"employee_group": self.employee_group},
                fields=["name", "school", "from_date", "to_date"],
                limit=0,
                ignore_permissions=True,
            )

            if self.school:
                school_rank = {school: idx for idx, school in enumerate(get_school_lineage(self.school))}
                scoped = [row for row in calendars if (row.get("school") or "").strip() in school_rank]
                active = []
                for row in scoped:
                    from_date = getdate(row.get("from_date")) if row.get("from_date") else None
                    to_date = getdate(row.get("to_date")) if row.get("to_date") else None
                    if from_date and to_date and from_date <= today_d <= to_date:
                        active.append(row)

                ranked = active or scoped
                ranked.sort(
                    key=lambda row: (
                        school_rank.get((row.get("school") or "").strip(), 10**9),
                        -(getdate(row.get("from_date")).toordinal() if row.get("from_date") else 0),
                        row.get("name") or "",
                    )
                )
                selected = ranked[0] if ranked else None
            elif linked_rows:
                selected = linked_rows[0]
            elif len(calendars) == 1:
                selected = calendars[0]

        self.current_holiday_lis = (selected or {}).get("name")

    def reset_employee_emails_cache(self):
        _refresh_runtime_bindings()

        prev_doc = self.get_doc_before_save() or {}
        cell_number = cstr(self.get("employee_mobile_phone"))
        prev_number = cstr(prev_doc.get("employee_mobile_phone"))
        if cell_number != prev_number or self.get("user_id") != prev_doc.get("user_id"):
            frappe.cache().hdel("employees_with_number", cell_number)
            frappe.cache().hdel("employees_with_number", prev_number)

    def _resolve_primary_contact_name(self) -> str | None:
        _refresh_runtime_bindings()

        if not self.user_id:
            return None

        contact_name = frappe.db.get_value("Contact", {"user": self.user_id}, "name")
        if contact_name:
            return contact_name

        contact_name = frappe.db.get_value(
            "Dynamic Link",
            {
                "link_doctype": "User",
                "link_name": self.user_id,
                "parenttype": "Contact",
            },
            "parent",
        )
        if contact_name:
            return contact_name

        if self.empl_primary_contact and frappe.db.exists("Contact", self.empl_primary_contact):
            return self.empl_primary_contact

        return None

    def _get_or_create_primary_contact(self) -> str | None:
        _refresh_runtime_bindings()

        contact_name = self._resolve_primary_contact_name()
        if contact_name:
            return contact_name

        if not self.user_id:
            return None

        contact = frappe.new_doc("Contact")
        contact.user = self.user_id
        contact.first_name = self.employee_first_name or self.employee_full_name or self.name
        contact.last_name = self.employee_last_name or ""

        if cstr(self.employee_gender).strip() and frappe.db.exists("Gender", self.employee_gender):
            contact.gender = self.employee_gender

        email = cstr(self.employee_professional_email).strip()
        if email:
            contact.append("email_ids", {"email_id": email, "is_primary": 1})

        mobile = cstr(self.employee_mobile_phone).strip()
        if mobile:
            contact.mobile_no = mobile
            contact.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})

        try:
            contact.insert(ignore_permissions=True)
            return contact.name
        except Exception:
            contact_name = self._resolve_primary_contact_name()
            if contact_name:
                return contact_name
            raise

    def _ensure_contact_employee_link(self, contact_name: str):
        _refresh_runtime_bindings()

        if not contact_name:
            return

        exists = frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact_name,
                "link_doctype": "Employee",
                "link_name": self.name,
            },
        )
        if exists:
            return

        contact = frappe.get_doc("Contact", contact_name)
        contact.append("links", {"link_doctype": "Employee", "link_name": self.name})
        contact.save(ignore_permissions=True)

    def _ensure_primary_contact(self):
        _refresh_runtime_bindings()

        """
        NOTE:
        Employee does NOT own contact/address data.
        Contact is the single source of truth.
        This method only ensures correct graph linking:
        User → Contact → Employee (via Dynamic Link).

        Dependency:
        User creation is expected to auto-create a Contact linked to the User (hook-level behavior).
        """
        if not self.user_id:
            return

        contact_name = self._get_or_create_primary_contact()
        if not contact_name:
            frappe.log_error(
                title="Employee Contact Link Missing",
                message=f"No Contact found for User {self.user_id}",
            )
            return

        self._ensure_contact_employee_link(contact_name)

        if self.empl_primary_contact != contact_name:
            self.empl_primary_contact = contact_name
            self.db_set("empl_primary_contact", contact_name, update_modified=False)

    def _can_sync_user_profile(self) -> bool:
        _refresh_runtime_bindings()

        """
        Only System Manager or the user themself can sync Employee -> User profile fields.
        HR should not be editing other User attributes as a side-effect of editing Employee.
        """
        if frappe.session.user == "Administrator":
            return True
        if "System Manager" in set(frappe.get_roles()):
            return True
        return bool(self.user_id and self.user_id == frappe.session.user)

    def _can_manage_user_roles(self) -> bool:
        _refresh_runtime_bindings()

        """
        HR Manager / HR User / System Manager can enforce roles programmatically.
        (This does NOT grant generic User write permissions in the UI.)
        """
        roles = set(frappe.get_roles())
        return bool(roles & {"HR Manager", "HR User", "System Manager"}) or frappe.session.user == "Administrator"

    def _ensure_user_has_role(self, user: str, role: str):
        _refresh_runtime_bindings()

        """Add role to user if missing, using ignore_permissions to avoid User doctype access issues."""
        if not user or not role:
            return

        exists = frappe.db.exists("Has Role", {"parent": user, "role": role})
        if exists:
            return

        u = frappe.get_doc("User", user)
        u.flags.ignore_permissions = True
        u.append("roles", {"role": role})
        u.save(ignore_permissions=True)

    def _access_sync_signature(self, doc=None) -> tuple[bool, tuple[str, ...], str]:
        source = doc or self
        if not source:
            return False, tuple(), ""

        from ifitwala_ed.hr.employee_access import compute_effective_access_from_employee

        roles, workspace = compute_effective_access_from_employee(source)
        is_active = cstr(getattr(source, "employment_status", "")).strip().lower() == "active"
        return is_active, tuple(sorted(roles)), cstr(workspace).strip()

    def _apply_designation_role(self):
        if not self.user_id:
            return
        if not self._can_manage_user_roles():
            return

        # Keep designation-driven roles aligned with the managed sync model,
        # including baseline Employee role repair and non-active role stripping.
        from ifitwala_ed.hr.employee_access import sync_user_access_from_employee

        sync_user_access_from_employee(self, notify_role_additions=True)

    def _apply_approver_roles(self):
        if not self._can_manage_user_roles():
            return

        prev = self.get_doc_before_save() or {}

        if self.leave_approver and self.leave_approver != prev.get("leave_approver"):
            self._ensure_user_has_role(self.leave_approver, "Leave Approver")

        if self.expense_approver and self.expense_approver != prev.get("expense_approver"):
            self._ensure_user_has_role(self.expense_approver, "Expense Approver")

    # ------------------------------------------------------------------
    # Employee Image Governance
    # ------------------------------------------------------------------


@frappe.whitelist()
def create_user(employee, user=None, email=None):
    _refresh_runtime_bindings()

    # 0) Basic guards
    if not employee:
        frappe.throw(_("Missing Employee"), frappe.ValidationError)

    # 1) Authorize caller
    caller = frappe.session.user
    caller_roles = set(frappe.get_roles(caller))

    # Allow System Manager unconditionally
    is_sysman = "System Manager" in caller_roles

    # Allow HR Manager/HR User only within their org subtree
    if not is_sysman:
        is_hr = bool(caller_roles & {"HR Manager", "HR User"})
        if not is_hr:
            frappe.throw(_("Only HR can create users from Employee."), frappe.PermissionError)

        # Resolve caller's base org
        base_org = get_user_base_org(caller)
        if not base_org:
            frappe.throw(
                _("Your account is not linked to an Active Employee or has no Organization."), frappe.PermissionError
            )

        # Target employee must be in caller's org subtree
        target_org = frappe.db.get_value("Employee", employee, "organization")
        allowed_orgs = set(get_descendant_organizations(base_org) or [])
        if target_org not in allowed_orgs:
            frappe.throw(
                _("You can only create users for Employees in your Organization subtree."), frappe.PermissionError
            )

    # 2) Load employee (you already enforce form access via PQC/has_permission)
    emp = frappe.get_doc("Employee", employee)

    # 3) Prevent duplicates
    if emp.user_id:
        frappe.throw(_("This Employee already has a User: {0}").format(frappe.bold(emp.user_id)))

    if not emp.employee_professional_email:
        frappe.throw(_("Please set a Professional Email on the Employee before creating a User."))

    existing = frappe.db.exists("User", {"name": emp.employee_professional_email})
    if existing:
        frappe.throw(_("A User with email {0} already exists.").format(frappe.bold(emp.employee_professional_email)))

    # 4) Build the User document (keep your privacy handling)
    privacy = frappe.get_single("Org Setting")
    birth_date = emp.employee_date_of_birth if getattr(privacy, "dob_to_user", 0) == 1 else None
    phone = emp.employee_mobile_phone if getattr(privacy, "mobile_to_user", 0) == 1 else None

    user_doc = frappe.new_doc("User")
    user_doc.flags.ignore_permissions = True
    user_doc.update(
        {
            # NOTE: do NOT force 'name' here; let Frappe name it as the email
            "email": emp.employee_professional_email,
            "enabled": 1,
            "first_name": emp.employee_first_name,
            "middle_name": emp.employee_middle_name,
            "last_name": emp.employee_last_name,
            "gender": emp.employee_gender,
            "birth_date": birth_date,
            "mobile_no": phone,
        }
    )

    user_doc.insert(ignore_permissions=True)

    emp.user_id = user_doc.name
    emp.save(ignore_permissions=True)
    emp._ensure_primary_contact()

    return user_doc.name


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False, is_tree=False):
    _refresh_runtime_bindings()

    # NOTE:
    # - Treeview calls this often; avoid N+1 queries.
    # - We keep the existing "All Organizations" sentinel for compatibility with current JS.
    # - Tree visibility must mirror scripted Employee visibility; do not inject an extra status gate here.

    filters = []

    # Organization filter (compat with current treeview default)
    if organization and organization != "All Organizations":
        filters.append(["organization", "=", organization])

    fields = ["name as value", "employee_full_name as title"]

    # Root resolution
    if is_root:
        parent = ""

    # Children of a node vs top-level nodes
    if parent:
        filters.append(["reports_to", "=", parent])
        employees = frappe.get_list(
            doctype,
            fields=fields,
            filters=filters,
            order_by="name",
        )
    else:
        # For scoped users, visible employees can all report to out-of-scope managers.
        # In that case, treat "parent not visible" as a root so the tree doesn't appear empty.
        root_fields = fields + ["reports_to"]
        all_visible = frappe.get_list(
            doctype,
            fields=root_fields,
            filters=filters,
            order_by="name",
        )
        visible_names = {row.get("value") for row in all_visible if row.get("value")}
        employees = []
        for row in all_visible:
            manager = cstr(row.get("reports_to")).strip()
            if not manager or manager not in visible_names:
                row.pop("reports_to", None)
                employees.append(row)

    # Nothing to expand
    if not employees:
        return employees

    # --- Batch-expandable check (single query) -----------------------------
    names = [e.get("value") for e in employees if e.get("value")]

    # Count children per supervisor among returned names
    # (We only care whether count > 0)
    rows = frappe.db.sql(
        """
		SELECT reports_to, COUNT(*) AS cnt
		FROM `tabEmployee`
		WHERE reports_to IN %(names)s
		GROUP BY reports_to
		""",
        {"names": tuple(names)},
        as_dict=True,
    )

    count_by_reports_to = {r.reports_to: int(r.cnt or 0) for r in (rows or [])}

    for e in employees:
        e.expandable = 1 if count_by_reports_to.get(e.get("value"), 0) > 0 else 0

    return employees


def on_doctype_update():
    _refresh_runtime_bindings()

    frappe.db.add_index("Employee", ["lft", "rgt"])


def validate_employee_role(doc, method=None, ignore_emp_check=False):
    _refresh_runtime_bindings()

    # called via User hook
    if not ignore_emp_check:
        if frappe.db.get_value("Employee", {"user_id": doc.name}):
            return

    user_roles = [d.role for d in doc.get("roles")]
    if "Employee" in user_roles:
        frappe.msgprint(_("User {0}: Removed Employee role as there is no mapped employee.").format(doc.name))
        doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

    if "Employee Self Service" in user_roles:
        frappe.msgprint(
            _("User {0}: Removed Employee Self Service role as there is no mapped employee.").format(doc.name)
        )
        doc.get("roles").remove(doc.get("roles", {"role": "Employee Self Service"})[0])


def update_user_permissions(doc, method):
    """No-op: we no longer use Employee User Permissions at all."""
    return


def has_upload_permission(doc, ptype="read", user=None):
    _refresh_runtime_bindings()

    if not user:
        user = frappe.session.user
    if get_doc_permissions(doc, user=user, ptype=ptype).get(ptype):
        return True
    return doc.user_id == user


def get_permission_query_conditions(user=None):
    _refresh_runtime_bindings()

    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    roles = set(frappe.get_roles(user))

    # System Manager has full visibility
    if "System Manager" in roles:
        return None

    # HR: scope by Organization subtree + always include unassigned organization rows
    if roles & {"HR Manager", "HR User"}:
        orgs = _resolve_hr_org_scope(user)
        if not orgs:
            return "IFNULL(`tabEmployee`.`organization`, '') = ''"

        vals = ", ".join(frappe.db.escape(o) for o in orgs)
        return f"(`tabEmployee`.`organization` IN ({vals}) OR IFNULL(`tabEmployee`.`organization`, '') = '')"

    # Academic Admin: default school stays school-scoped; blank-school falls back to org descendants
    if "Academic Admin" in roles:
        school_scope = _resolve_academic_admin_school_scope(user)
        if school_scope:
            return f"`tabEmployee`.`school` = {frappe.db.escape(school_scope)}"

        orgs = _resolve_academic_admin_org_scope(user)
        if not orgs:
            return "1=0"

        vals = ", ".join(frappe.db.escape(o) for o in orgs)
        return f"`tabEmployee`.`organization` IN ({vals})"

    # Employee: own record only
    if "Employee" in roles:
        own_employee = _resolve_self_employee(user)
        if not own_employee:
            return "1=0"
        return f"`tabEmployee`.`name` = {frappe.db.escape(own_employee)}"

    return None


def employee_has_permission(doc=None, ptype=None, user=None):
    _refresh_runtime_bindings()

    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    ptype = ptype or "read"

    # System Manager full access
    if "System Manager" in frappe.get_roles(user):
        return True

    roles = set(frappe.get_roles(user))
    read_like = {"read", "report", "export", "print"}
    scoped_crud = read_like | {"write", "delete", "create", "submit", "cancel", "amend"}

    # HR -> Organization subtree + unassigned organization rows
    if roles & {"HR Manager", "HR User"} and ptype in scoped_crud:
        if doc is None:
            return True
        if not cstr(doc.organization).strip():
            return True
        orgs = set(_resolve_hr_org_scope(user))
        if not orgs:
            return False
        return doc.organization in orgs

    # Academic Admin -> read only; default school stays school-scoped, blank-school falls back to org descendants
    if "Academic Admin" in roles:
        if ptype not in read_like:
            return False
        school_scope = _resolve_academic_admin_school_scope(user)
        if doc is None:
            return bool(school_scope or _resolve_academic_admin_org_scope(user))
        if school_scope:
            return bool(cstr(doc.school).strip() == school_scope)

        orgs = set(_resolve_academic_admin_org_scope(user))
        if not orgs:
            return False
        return cstr(doc.organization).strip() in orgs

    # Employee -> read only own record
    if "Employee" in roles:
        if ptype not in read_like:
            return False
        own_employee = _resolve_self_employee(user)
        if doc is None:
            return bool(own_employee)
        if not own_employee:
            return False
        return doc.name == own_employee or cstr(doc.user_id).strip() == user

    # Others fall back to standard perms
    return None


def _resolve_hr_base_org(user: str) -> str | None:
    _refresh_runtime_bindings()

    """Resolve HR base org from persistent defaults only (no Employee-linkage dependency)."""
    org = _get_user_default_from_db(user, "organization")
    if org:
        return org

    global_org = frappe.db.get_single_value("Global Defaults", "default_organization")
    return cstr(global_org).strip() or None


def _resolve_academic_admin_school_scope(user: str) -> str | None:
    _refresh_runtime_bindings()

    """
    Resolve school scope for Academic Admin visibility.

    The active Employee profile is authoritative. If that profile exists with a blank school,
    treat the user as schoolless and fall back to organization scope instead of reviving a stale
    persisted default school.
    """
    active_employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        ["name", "school"],
        as_dict=True,
    )
    if active_employee:
        return cstr(active_employee.get("school")).strip() or None

    return _get_user_default_from_db(user, "school")


def _resolve_academic_admin_base_org(user: str) -> str | None:
    _refresh_runtime_bindings()

    """Resolve Academic Admin base org from active Employee context first, then persisted defaults."""
    employee_org = cstr(get_user_base_org(user)).strip()
    if employee_org:
        return employee_org

    return _get_user_default_from_db(user, "organization")


def _resolve_academic_admin_org_scope(user: str) -> list[str]:
    _refresh_runtime_bindings()

    """Resolve read-only Academic Admin org scope for blank-school fallback."""
    scope: set[str] = set()

    base_org = _resolve_academic_admin_base_org(user)
    if base_org:
        scope.update(
            {cstr(org).strip() for org in (_get_descendant_organizations_uncached(base_org) or []) if cstr(org).strip()}
        )

    explicit_orgs = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Organization"},
        pluck="for_value",
    )
    for org in explicit_orgs:
        org_name = cstr(org).strip()
        if not org_name:
            continue
        scope.update(
            {
                cstr(item).strip()
                for item in (_get_descendant_organizations_uncached(org_name) or [])
                if cstr(item).strip()
            }
        )

    return sorted(scope)


def _resolve_hr_org_scope(user: str) -> list[str]:
    _refresh_runtime_bindings()

    """Resolve full HR organization scope from default org + explicit user permissions."""
    scope: set[str] = set()

    base_org = _resolve_hr_base_org(user)
    if base_org:
        scope.update(
            {cstr(org).strip() for org in (_get_descendant_organizations_uncached(base_org) or []) if cstr(org).strip()}
        )

    explicit_orgs = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Organization"},
        pluck="for_value",
    )
    for org in explicit_orgs:
        org_name = cstr(org).strip()
        if not org_name:
            continue
        scope.update(
            {
                cstr(item).strip()
                for item in (_get_descendant_organizations_uncached(org_name) or [])
                if cstr(item).strip()
            }
        )

    return sorted(scope)


def _get_user_default_from_db(user: str, key: str) -> str | None:
    _refresh_runtime_bindings()

    rows = frappe.get_all(
        "DefaultValue",
        filters={"parent": user, "defkey": key},
        fields=["defvalue"],
        order_by="modified desc, creation desc, name desc",
        limit=1,
    )
    if not rows:
        return None
    return cstr(rows[0].get("defvalue")).strip() or None


def _get_descendant_organizations_uncached(org: str) -> list[str]:
    _refresh_runtime_bindings()

    org = cstr(org).strip()
    if not org:
        return []

    bounds = frappe.db.get_value("Organization", org, ["lft", "rgt"], as_dict=True)
    if not bounds or bounds.lft is None or bounds.rgt is None:
        return []

    return frappe.get_all(
        "Organization",
        filters={"lft": (">=", bounds.lft), "rgt": ("<=", bounds.rgt)},
        pluck="name",
    )


def _resolve_self_employee(user: str) -> str | None:
    _refresh_runtime_bindings()

    rows = frappe.get_all(
        "Employee",
        filters={"user_id": user},
        fields=["name", "employment_status"],
        order_by="modified desc",
        limit=5,
    )
    active = next(
        (cstr(row.get("name")).strip() for row in rows if cstr(row.get("employment_status")).strip() == "Active"),
        None,
    )
    if active:
        return active
    return next((cstr(row.get("name")).strip() for row in rows if cstr(row.get("name")).strip()), None)

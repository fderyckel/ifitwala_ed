# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/instructor/instructor.py

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

from ifitwala_ed.utilities.school_tree import get_descendant_schools

INSTRUCTOR_LOG_ROW_FIELDS = (
    "program",
    "academic_year",
    "term",
    "student_group",
    "course",
    "designation",
    "other_details",
    "from_date",
    "to_date",
)


class Instructor(Document):
    def autoname(self):
        full_name = frappe.db.get_value("Employee", self.employee, "employee_full_name")
        if not full_name:
            frappe.throw(_("Cannot set Instructor name without employee full name."))
        self.name = full_name

    def validate(self):
        self._sync_employee_fields()
        self._validate_duplicate_employee()

    def before_save(self):
        # Reconcile the persisted instructor assignment history before saving.
        self.rebuild_instructor_log()

    def after_insert(self):
        # Grant role only for active instructors
        if self.status != "Inactive" and self.linked_user_id:
            _ensure_instructor_role(self.linked_user_id)

    def on_update(self):
        status_changed = self.has_value_changed("status")
        user_changed = self.has_value_changed("linked_user_id")
        # Previous snapshot (pre-save values)
        before = getattr(self, "get_doc_before_save", None)
        old_user = None
        if before:
            prev = self.get_doc_before_save()
            old_user = getattr(prev, "linked_user_id", None)

        # If linked user changed, move the role from old -> new
        if user_changed:
            if old_user and old_user != self.linked_user_id:
                _remove_instructor_role(old_user)
            if self.linked_user_id and self.status != "Inactive":
                _ensure_instructor_role(self.linked_user_id)

        # If just status changed (user id same), toggle accordingly
        if status_changed and not user_changed:
            if self.status == "Inactive":
                if self.linked_user_id:
                    _remove_instructor_role(self.linked_user_id)
            else:
                if self.linked_user_id:
                    _ensure_instructor_role(self.linked_user_id)

    def _sync_employee_fields(self):
        employee = frappe.db.get_value(
            "Employee",
            self.employee,
            ["user_id", "employee_gender", "employee_full_name", "employee_image"],
            as_dict=True,
        )
        if not employee or not employee.user_id:
            frappe.throw(_("Linked Employee must have a User ID."))

        self.linked_user_id = employee.user_id
        self.gender = employee.employee_gender
        self.instructor_name = employee.employee_full_name
        self.instructor_image = employee.employee_image

    def rebuild_instructor_log(self):
        """
        Reconcile Instructor Log against current Student Group Instructor assignments.

        Legacy undated rows from the old computed snapshot contract are treated as
        migratable display artifacts, not authoritative history.
        """
        previous_state = _serialize_instructor_log_rows(self.get("instructor_log", []))
        assignments = _get_current_instructor_assignments(self.name)
        current_assignments = {
            _instructor_log_key(a.get("student_group"), a.get("designation")): a for a in assignments
        }
        today = getdate(nowdate())
        handled_keys = set()
        reconciled_rows = []

        for existing_row in self.get("instructor_log", []) or []:
            row = _extract_instructor_log_row(existing_row)
            key = _instructor_log_key(row.get("student_group"), row.get("designation"))
            is_legacy_snapshot = not row.get("from_date") and not row.get("to_date")
            is_open_history_row = bool(row.get("from_date")) and not row.get("to_date")

            if is_legacy_snapshot:
                assignment = current_assignments.get(key)
                if assignment and key not in handled_keys:
                    row.update(_assignment_to_instructor_log_row(assignment))
                    row["from_date"] = _assignment_start_date(assignment)
                    row["to_date"] = None
                    handled_keys.add(key)
                    reconciled_rows.append(row)
                continue

            if is_open_history_row:
                assignment = current_assignments.get(key)
                if assignment and key not in handled_keys:
                    row.update(_assignment_to_instructor_log_row(assignment))
                    row["to_date"] = None
                    handled_keys.add(key)
                else:
                    row["to_date"] = today

            reconciled_rows.append(row)

        for key, assignment in current_assignments.items():
            if key in handled_keys:
                continue
            row = _assignment_to_instructor_log_row(assignment)
            row["from_date"] = _assignment_start_date(assignment)
            row["to_date"] = None
            reconciled_rows.append(row)

        reconciled_rows.sort(key=_instructor_log_sort_key, reverse=True)

        self.set("instructor_log", [])
        for row in reconciled_rows:
            self.append("instructor_log", row)

        return previous_state != _serialize_instructor_log_rows(self.get("instructor_log", []))

    def _validate_duplicate_employee(self):
        if self.employee and frappe.db.get_value(
            "Instructor", {"employee": self.employee, "name": ["!=", self.name]}, "name"
        ):
            frappe.throw(_("Employee ID is linked with another instructor."))


# --- Linked User ID role management -------------------------------------------


def _ensure_instructor_role(user_id: str):
    """Idempotently add Instructor role to user_id."""
    if not user_id or not frappe.db.exists("User", user_id):
        return
    if not frappe.db.exists("Has Role", {"parent": user_id, "role": "Instructor"}):
        user = frappe.get_doc("User", user_id)
        user.flags.ignore_permissions = True
        user.add_roles("Instructor")


def _format_instructor_log_details(group: dict) -> str | None:
    """Return a compact text summary for the Instructor Log optional details column."""
    parts = []
    group_based_on = group.get("group_based_on")
    if group_based_on:
        parts.append(f"Group Type: {group_based_on}")
    school = group.get("school")
    if school:
        parts.append(f"School: {school}")
    offering = group.get("program_offering")
    if offering:
        parts.append(f"Program Offering: {offering}")
    return "\n".join(parts) if parts else None


def _remove_instructor_role(user_id: str):
    """Idempotently remove Instructor role from user_id."""
    if not user_id or not frappe.db.exists("User", user_id):
        return
    if frappe.db.exists("Has Role", {"parent": user_id, "role": "Instructor"}):
        user = frappe.get_doc("User", user_id)
        user.flags.ignore_permissions = True
        user.remove_roles("Instructor")


def sync_instructor_logs(instructor_names) -> None:
    """Rebuild and persist Instructor Log rows for the provided Instructor ids."""
    names = sorted({(name or "").strip() for name in (instructor_names or []) if (name or "").strip()})
    for instructor_name in names:
        if not frappe.db.exists("Instructor", instructor_name):
            continue

        instructor_doc = frappe.get_doc("Instructor", instructor_name)
        if instructor_doc.rebuild_instructor_log():
            instructor_doc.flags.ignore_version = True
            instructor_doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_instructor_log(instructor: str):
    if not instructor:
        return {"rows": [], "changed": False}
    instructor_doc = frappe.get_doc("Instructor", instructor)
    changed = instructor_doc.rebuild_instructor_log()
    if changed:
        instructor_doc.flags.ignore_version = True
        instructor_doc.save(ignore_permissions=True)
    return {"rows": _serialize_instructor_log_rows(instructor_doc.get("instructor_log", [])), "changed": changed}


def _get_current_instructor_assignments(instructor_name: str) -> list[dict]:
    if not instructor_name:
        return []

    group_links = frappe.db.get_all(
        "Student Group Instructor",
        filters={"instructor": instructor_name},
        fields=["parent as student_group", "designation", "creation"],
    )
    if not group_links:
        return []

    student_group_names = [g["student_group"] for g in group_links if g.get("student_group")]
    groups = frappe.db.get_all(
        "Student Group",
        filters={"name": ["in", student_group_names]},
        fields=[
            "name as student_group",
            "school",
            "program_offering",
            "program",
            "academic_year",
            "term",
            "course",
            "group_based_on",
        ],
    )
    group_lookup = {g["student_group"]: g for g in groups}

    assignments = []
    for link in group_links:
        group = group_lookup.get(link.get("student_group"))
        if not group:
            continue
        assignments.append(
            {**group, "designation": link.get("designation"), "assignment_created": link.get("creation")}
        )
    return assignments


def _assignment_to_instructor_log_row(assignment: dict) -> dict:
    return {
        "program": assignment.get("program"),
        "academic_year": assignment.get("academic_year"),
        "term": assignment.get("term"),
        "student_group": assignment.get("student_group"),
        "course": assignment.get("course"),
        "designation": assignment.get("designation"),
        "other_details": _format_instructor_log_details(assignment),
    }


def _assignment_start_date(assignment: dict):
    creation = assignment.get("assignment_created")
    if creation:
        try:
            return getdate(creation)
        except Exception:
            pass
    return getdate(nowdate())


def _instructor_log_key(student_group: str | None, designation: str | None) -> tuple[str, str]:
    return ((student_group or "").strip(), (designation or "").strip())


def _extract_instructor_log_row(row) -> dict:
    extracted = {}
    for fieldname in INSTRUCTOR_LOG_ROW_FIELDS:
        extracted[fieldname] = getattr(row, fieldname, None)
    return extracted


def _serialize_instructor_log_value(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


def _serialize_instructor_log_rows(rows) -> list[dict]:
    serialized_rows = []
    for row in rows or []:
        serialized_rows.append(
            {
                fieldname: _serialize_instructor_log_value(getattr(row, fieldname, None))
                for fieldname in INSTRUCTOR_LOG_ROW_FIELDS
            }
        )
    return serialized_rows


def _instructor_log_sort_key(row: dict):
    is_active = not row.get("to_date")
    end_date = getdate(row.get("to_date") or row.get("from_date") or nowdate())
    start_date = getdate(row.get("from_date") or row.get("to_date") or nowdate())
    return (1 if is_active else 0, end_date.toordinal(), start_date.toordinal(), row.get("student_group") or "")


# --- Permissions: Instructor visibility by school tree -----------------------


def _user_allowed_schools(user: str) -> list[str]:
    """
    Return the list of schools the given user may see for Instructor docs.
    Rule: Academic Admin / Academic Assistant → default school + all descendants.
    Everyone else → only their default school (leaf or not), still using descendants to keep behavior consistent.
    """
    # Administrator/System Manager handled by callers; short-circuit here if needed
    user_school = frappe.defaults.get_user_default("school", user=user)
    if not user_school:
        return []

    # Always include descendants (the helper already includes `user_school` itself)
    try:
        return get_descendant_schools(user_school) or []
    except Exception:
        # never hard-fail permission path
        return [user_school]


@frappe.whitelist()
def get_permission_query_conditions(user):
    # Superusers see all
    if user in ("Administrator",) or "System Manager" in frappe.get_roles(user):
        return ""

    _roles = set(frappe.get_roles(user))
    # _is_academic_controller = bool(roles)  # noqa: F841  # noqa: F841
    # _is_academic_controller = bool(roles)  # noqa: F841 & {"Academic Admin", "Academic Assistant"})

    schools = _user_allowed_schools(user)
    user_escaped = frappe.db.escape(user, percent=False)

    if not schools:
        # No default school → still allow their own Instructor doc
        return f"`tabInstructor`.linked_user_id = {user_escaped}"

    escaped_values = ", ".join(frappe.db.escape(s, percent=False) for s in schools)

    # Normal school-based filter OR their own Instructor doc
    return f"`tabInstructor`.school IN ({escaped_values}) OR `tabInstructor`.linked_user_id = {user_escaped}"


def has_permission(doc, ptype, user):
    # Full access for superusers
    if user in ("Administrator",) or "System Manager" in frappe.get_roles(user):
        return True

    # Allow an instructor to see their own Instructor doc (read-only rule)
    if ptype == "read" and getattr(doc, "linked_user_id", None) == user:
        return True

    # Safety guards
    if not doc or not getattr(doc, "school", None):
        return False

    # Academic Admin/Assistant (and everyone else) → within allowed schools list
    schools = _user_allowed_schools(user)
    return bool(schools) and doc.school in schools


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def instructor_employee_query(doctype, txt, searchfield, start, page_len, filters):
    user = frappe.session.user
    filters = filters or {}

    if not (
        frappe.has_permission("Instructor", ptype="create", user=user)
        or frappe.has_permission("Instructor", ptype="write", user=user)
    ):
        return []

    roles = set(frappe.get_roles(user))
    is_admin = user == "Administrator" or "System Manager" in roles
    schools = _user_allowed_schools(user)

    if not is_admin and not schools:
        return []

    current_instructor = (filters.get("current_instructor") or "").strip()
    current_employee = (filters.get("current_employee") or "").strip()
    query_filters = {
        key: value for key, value in filters.items() if key not in {"current_instructor", "current_employee"}
    }

    employee_conditions = []
    employee_filters = {}

    if not is_admin:
        escaped_schools = ", ".join(frappe.db.escape(school, percent=False) for school in schools)
        employee_conditions.append(f"`tabEmployee`.`school` IN ({escaped_schools})")

    if current_employee:
        employee_conditions.append(
            """
            (
                `tabEmployee`.`name` = %(current_employee)s
                OR NOT EXISTS (
                    SELECT 1
                    FROM `tabInstructor` instructor
                    WHERE instructor.employee = `tabEmployee`.`name`
                    AND (%(current_instructor)s = '' OR instructor.name != %(current_instructor)s)
                )
            )
            """
        )
    else:
        employee_conditions.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM `tabInstructor` instructor
                WHERE instructor.employee = `tabEmployee`.`name`
            )
            """
        )

    filter_condition = get_filters_cond("Employee", query_filters, employee_filters)

    if filter_condition:
        employee_conditions.append(filter_condition)

    where_clause = " and ".join(
        [
            "`tabEmployee`.`employment_status` in ('Active', 'Suspended')",
            "`tabEmployee`.`docstatus` < 2",
            "(`tabEmployee`.`name` like %(txt)s or `tabEmployee`.`employee_full_name` like %(txt)s)",
            *employee_conditions,
        ]
    )

    return frappe.db.sql(
        f"""
        select `tabEmployee`.`name`, `tabEmployee`.`employee_full_name`
        from `tabEmployee`
        where {where_clause}
        order by
            (case when locate(%(_txt)s, `tabEmployee`.`name`) > 0 then locate(%(_txt)s, `tabEmployee`.`name`) else 99999 end),
            (case when locate(%(_txt)s, `tabEmployee`.`employee_full_name`) > 0 then locate(%(_txt)s, `tabEmployee`.`employee_full_name`) else 99999 end),
            `tabEmployee`.`idx` desc,
            `tabEmployee`.`name`,
            `tabEmployee`.`employee_full_name`
        limit %(page_len)s offset %(start)s
        """,
        {
            "txt": f"%{txt}%",
            "_txt": txt.replace("%", ""),
            "start": start,
            "page_len": page_len,
            "current_instructor": current_instructor,
            "current_employee": current_employee,
        },
    )

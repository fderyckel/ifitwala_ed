# ifitwala_ed/governance/doctype/policy_acknowledgement/policy_acknowledgement.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from ifitwala_ed.governance.policy_scope_utils import (
    get_user_policy_scope,
    is_policy_organization_applicable_to_context,
    is_policy_within_user_scope,
)
from ifitwala_ed.governance.policy_utils import (
    POLICY_ADMIN_ROLES,
    SCHOOL_ADMIN_ROLE,
    has_admissions_applicant_role,
    has_guardian_role,
    has_staff_role,
    has_student_role,
    is_system_manager,
)

ACK_CONTEXT_MAP = {
    "Applicant": ("Student Applicant",),
    "Student": ("Student",),
    "Guardian": ("Guardian",),
    "Staff": ("Employee",),
}


class PolicyAcknowledgement(Document):
    def before_insert(self):
        self._validate_policy_version()
        self._validate_acknowledged_by()
        self._validate_context()
        self._validate_role_for_acknowledgement()
        self._validate_unique_acknowledgement()
        self.acknowledged_at = now_datetime()

    def before_save(self):
        if self.is_new():
            return

        before = self.get_doc_before_save()
        if (
            before
            and cint(before.get("docstatus")) == 0
            and cint(self.get("docstatus")) == 1
            and not self._has_immutable_field_changes(before)
        ):
            return

        frappe.throw(_("Policy Acknowledgements are append-only and cannot be edited."))

    def before_submit(self):
        if not self.acknowledged_at:
            self.acknowledged_at = now_datetime()
        if not self._validate_submit_transition():
            frappe.throw(_("Policy Acknowledgements can only be submitted from Draft state."))

    def before_update_after_submit(self):
        frappe.throw(_("Submitted Policy Acknowledgements are immutable."))

    def before_cancel(self):
        frappe.throw(_("Policy Acknowledgements cannot be cancelled."))

    def before_delete(self):
        frappe.throw(_("Policy Acknowledgements cannot be deleted."))

    def after_insert(self):
        self._auto_submit()

    def on_submit(self):
        if is_system_manager() and not self._is_role_allowed_for_ack():
            self.add_comment(
                "Comment",
                text=_("System Manager override acknowledgement by {0} on {1}.").format(
                    frappe.bold(frappe.session.user), now_datetime()
                ),
            )

    def _auto_submit(self):
        if cint(self.docstatus) == 1:
            return
        self.flags.ignore_permissions = True
        self.submit()

    def _validate_submit_transition(self) -> bool:
        before = self.get_doc_before_save()
        if not before:
            return False
        return cint(before.get("docstatus")) == 0 and cint(self.get("docstatus")) == 1

    def _has_immutable_field_changes(self, before) -> bool:
        immutable_fields = (
            "policy_version",
            "acknowledged_by",
            "acknowledged_for",
            "context_doctype",
            "context_name",
        )
        return any(before.get(field) != self.get(field) for field in immutable_fields)

    def _validate_policy_version(self):
        if not self.policy_version:
            frappe.throw(_("Policy Version is required."))
        is_active = frappe.db.get_value("Policy Version", self.policy_version, "is_active")
        if not is_active:
            frappe.throw(_("Policy Version must be active to acknowledge."))

    def _validate_acknowledged_by(self):
        if self.acknowledged_by != frappe.session.user:
            frappe.throw(_("Acknowledged By must match the current user."))

    def _validate_context(self):
        if not self.context_doctype or not self.context_name:
            frappe.throw(_("Context DocType and Context Name are required."))

        if not frappe.db.exists("DocType", self.context_doctype):
            frappe.throw(_("Invalid context DocType."))

        if not frappe.db.exists(self.context_doctype, self.context_name):
            frappe.throw(_("Context record does not exist."))

        allowed_contexts = ACK_CONTEXT_MAP.get(self.acknowledged_for)
        if allowed_contexts and self.context_doctype not in allowed_contexts:
            frappe.throw(_("Context DocType does not match acknowledged_for."))

        self._validate_policy_scope_for_context()

    def _validate_policy_scope_for_context(self):
        policy = frappe.db.get_value("Policy Version", self.policy_version, "institutional_policy")
        policy_org = frappe.db.get_value("Institutional Policy", policy, "organization")
        if not policy_org:
            return

        context_orgs = self._resolve_context_organizations()
        if not context_orgs:
            debug_payload = {
                "policy_version": self.policy_version,
                "policy_organization": policy_org,
                "acknowledged_for": self.acknowledged_for,
                "context_doctype": self.context_doctype,
                "context_name": self.context_name,
            }
            frappe.log_error(
                message=frappe.as_json(debug_payload),
                title="Policy acknowledgement scope resolution failed",
            )
            frappe.throw(_("Could not resolve Organization scope for acknowledgement context."))

        if any(
            is_policy_organization_applicable_to_context(
                policy_organization=policy_org,
                context_organization=context_org,
            )
            for context_org in context_orgs
        ):
            return

        frappe.throw(_("Policy does not apply to this acknowledgement context organization."))

    def _resolve_context_organizations(self) -> list[str]:
        if self.context_doctype == "Student Applicant":
            org = frappe.db.get_value("Student Applicant", self.context_name, "organization")
            return [org] if org else []

        if self.context_doctype == "Employee":
            org = frappe.db.get_value("Employee", self.context_name, "organization")
            return [org] if org else []

        if self.context_doctype == "Student":
            return self._organizations_for_students([self.context_name])

        if self.context_doctype == "Guardian":
            student_names = frappe.get_all(
                "Student Guardian",
                filters={"guardian": self.context_name},
                pluck="parent",
            )
            if not student_names:
                return []
            return self._organizations_for_students(student_names)

        return []

    def _organizations_for_students(self, student_names: list[str]) -> list[str]:
        if not student_names:
            return []

        rows = frappe.get_all(
            "Student",
            filters={"name": ["in", student_names]},
            fields=["anchor_school", "student_applicant"],
        )

        orgs: list[str] = []
        seen = set()
        for row in rows:
            anchor_school = row.get("anchor_school")
            if anchor_school:
                org = frappe.db.get_value("School", anchor_school, "organization")
                if org and org not in seen:
                    seen.add(org)
                    orgs.append(org)

            student_applicant = row.get("student_applicant")
            if student_applicant:
                org = frappe.db.get_value("Student Applicant", student_applicant, "organization")
                if org and org not in seen:
                    seen.add(org)
                    orgs.append(org)

        return orgs

    def _validate_unique_acknowledgement(self):
        exists = frappe.db.exists(
            "Policy Acknowledgement",
            {
                "policy_version": self.policy_version,
                "acknowledged_by": self.acknowledged_by,
                "context_doctype": self.context_doctype,
                "context_name": self.context_name,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("This acknowledgement already exists for the same context."))

    def _guardian_name_for_user(self) -> str | None:
        return frappe.db.get_value("Guardian", {"user": frappe.session.user}, "name")

    def _guardian_linked_to_student(self, guardian_name: str, student_name: str) -> bool:
        return bool(
            frappe.db.exists(
                "Student Guardian",
                {
                    "parent": student_name,
                    "parenttype": "Student",
                    "parentfield": "guardians",
                    "guardian": guardian_name,
                },
            )
        )

    def _is_applicant_user_for_context(self) -> bool:
        if self.context_doctype != "Student Applicant":
            return False
        applicant_user = frappe.db.get_value("Student Applicant", self.context_name, "applicant_user")
        return bool(applicant_user and applicant_user == frappe.session.user)

    def _role_validation_error(self) -> str | None:
        if self.acknowledged_for == "Applicant":
            if not has_admissions_applicant_role():
                return _("Only Admissions Applicants can acknowledge Applicant policies.")
            if not self._is_applicant_user_for_context():
                return _("You do not have permission to acknowledge policies for this Applicant.")
            return None
        if self.acknowledged_for == "Student":
            if has_student_role():
                return None
            if has_guardian_role():
                guardian_name = self._guardian_name_for_user()
                if not guardian_name:
                    return _("Guardian account is not linked to a Guardian record.")
                if not self._guardian_linked_to_student(guardian_name, self.context_name):
                    return _("You are not a guardian of this student.")
                return None
            return _("You do not have permission to acknowledge student policies.")
        if self.acknowledged_for == "Guardian":
            if not has_guardian_role():
                return _("Only Guardians can acknowledge Guardian policies.")
            guardian_name = self._guardian_name_for_user()
            if not guardian_name:
                return _("Guardian account is not linked to a Guardian record.")
            if self.context_name != guardian_name:
                return _("Guardians may only acknowledge policies for themselves.")
            return None
        if self.acknowledged_for == "Staff":
            if has_staff_role():
                return None
            return _("Only Staff may acknowledge Staff policies.")
        return _("Invalid acknowledgement context.")

    def _is_role_allowed_for_ack(self) -> bool:
        return self._role_validation_error() is None

    def _validate_role_for_acknowledgement(self):
        error = self._role_validation_error()
        if not error:
            return
        if is_system_manager():
            return
        frappe.throw(error)


def _escaped_in(values: list[str]) -> str:
    cleaned = [(value or "").strip() for value in values if (value or "").strip()]
    if not cleaned:
        return ""
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def _policy_scope_for_acknowledgement(policy_version: str) -> tuple[str, str]:
    policy_version = (policy_version or "").strip()
    if not policy_version:
        return "", ""

    row = frappe.db.sql(
        """
        SELECT
            ip.organization AS organization,
            ip.school AS school
        FROM `tabPolicy Version` pv
        JOIN `tabInstitutional Policy` ip
          ON ip.name = pv.institutional_policy
        WHERE pv.name = %(policy_version)s
        LIMIT 1
        """,
        {"policy_version": policy_version},
        as_dict=True,
    )
    if not row:
        return "", ""
    resolved = row[0]
    return (resolved.get("organization") or "").strip(), (resolved.get("school") or "").strip()


def _guardian_name_for_user(user: str) -> str:
    return (frappe.db.get_value("Guardian", {"user": user}, "name") or "").strip()


def _student_name_for_user(user: str) -> str:
    return (frappe.db.get_value("Student", {"student_email": user}, "name") or "").strip()


def _employee_names_for_user(user: str) -> list[str]:
    rows = frappe.get_all(
        "Employee",
        filters={"user_id": user},
        pluck="name",
    )
    return sorted({(row or "").strip() for row in rows if (row or "").strip()})


def _student_applicant_names_for_user(user: str) -> list[str]:
    rows = frappe.get_all(
        "Student Applicant",
        filters={"applicant_user": user},
        pluck="name",
    )
    return sorted({(row or "").strip() for row in rows if (row or "").strip()})


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return None

    roles = set(frappe.get_roles(user))
    conditions: list[str] = []
    escaped_user = frappe.db.escape(user)

    if roles & POLICY_ADMIN_ROLES or SCHOOL_ADMIN_ROLE in roles:
        organization_scope, school_scope = get_user_policy_scope(user)
        organizations_sql = _escaped_in(organization_scope)
        if organizations_sql:
            schools_sql = _escaped_in(school_scope)
            school_condition = (
                f"(ifnull(ip.school, '') = '' OR ip.school in ({schools_sql}))"
                if schools_sql
                else "ifnull(ip.school, '') = ''"
            )
            conditions.append(
                "exists ("
                "select 1 from `tabPolicy Version` pv "
                "join `tabInstitutional Policy` ip on ip.name = pv.institutional_policy "
                "where pv.name = `tabPolicy Acknowledgement`.`policy_version` "
                f"and ip.organization in ({organizations_sql}) "
                f"and {school_condition}"
                ")"
            )

    if "Admission Officer" in roles:
        organization_scope, school_scope = get_user_policy_scope(user)
        organizations_sql = _escaped_in(organization_scope)
        if organizations_sql:
            schools_sql = _escaped_in(school_scope)
            if schools_sql:
                applicant_scope_condition = (
                    "exists ("
                    "select 1 from `tabStudent Applicant` sa "
                    "where sa.name = `tabPolicy Acknowledgement`.`context_name` "
                    f"and sa.organization in ({organizations_sql}) "
                    f"and sa.school in ({schools_sql})"
                    ")"
                )
            else:
                applicant_scope_condition = (
                    "exists ("
                    "select 1 from `tabStudent Applicant` sa "
                    "where sa.name = `tabPolicy Acknowledgement`.`context_name` "
                    f"and sa.organization in ({organizations_sql})"
                    ")"
                )
            conditions.append(
                f"(`tabPolicy Acknowledgement`.`context_doctype` = 'Student Applicant' and {applicant_scope_condition})"
            )

    guardian_name = _guardian_name_for_user(user)
    if guardian_name:
        escaped_guardian = frappe.db.escape(guardian_name)
        conditions.append(
            "(`tabPolicy Acknowledgement`.`context_doctype` = 'Guardian' "
            f"and `tabPolicy Acknowledgement`.`context_name` = {escaped_guardian})"
        )
        conditions.append(
            "(`tabPolicy Acknowledgement`.`context_doctype` = 'Student' "
            "and exists ("
            "select 1 from `tabStudent Guardian` sg "
            "where sg.parent = `tabPolicy Acknowledgement`.`context_name` "
            "and sg.parenttype = 'Student' "
            "and sg.parentfield = 'guardians' "
            f"and sg.guardian = {escaped_guardian}"
            "))"
        )

    student_name = _student_name_for_user(user)
    if student_name:
        escaped_student = frappe.db.escape(student_name)
        conditions.append(
            "(`tabPolicy Acknowledgement`.`context_doctype` = 'Student' "
            f"and `tabPolicy Acknowledgement`.`context_name` = {escaped_student})"
        )

    if has_admissions_applicant_role(user):
        applicant_names = _student_applicant_names_for_user(user)
        applicants_sql = _escaped_in(applicant_names)
        if applicants_sql:
            conditions.append(
                "(`tabPolicy Acknowledgement`.`context_doctype` = 'Student Applicant' "
                f"and `tabPolicy Acknowledgement`.`context_name` in ({applicants_sql}))"
            )

    if has_staff_role(user):
        employee_names = _employee_names_for_user(user)
        employees_sql = _escaped_in(employee_names)
        if employees_sql:
            conditions.append(
                "(`tabPolicy Acknowledgement`.`context_doctype` = 'Employee' "
                f"and `tabPolicy Acknowledgement`.`context_name` in ({employees_sql}))"
            )

    conditions.append(f"`tabPolicy Acknowledgement`.`acknowledged_by` = {escaped_user}")
    if not conditions:
        return "1=0"
    return "(" + " OR ".join(conditions) + ")"


def has_permission(doc: "PolicyAcknowledgement", user: str | None = None, ptype: str | None = None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return True

    if not doc:
        return True

    if isinstance(doc, str):
        row = frappe.db.get_value(
            "Policy Acknowledgement",
            doc,
            ["policy_version", "acknowledged_by", "context_doctype", "context_name"],
            as_dict=True,
        )
        if not row:
            return False
        policy_version = (row.get("policy_version") or "").strip()
        acknowledged_by = (row.get("acknowledged_by") or "").strip()
        context_doctype = (row.get("context_doctype") or "").strip()
        context_name = (row.get("context_name") or "").strip()
    else:
        policy_version = (getattr(doc, "policy_version", None) or "").strip()
        acknowledged_by = (getattr(doc, "acknowledged_by", None) or "").strip()
        context_doctype = (getattr(doc, "context_doctype", None) or "").strip()
        context_name = (getattr(doc, "context_name", None) or "").strip()

    if acknowledged_by and acknowledged_by == user:
        return True

    roles = set(frappe.get_roles(user))
    if roles & POLICY_ADMIN_ROLES or SCHOOL_ADMIN_ROLE in roles:
        policy_organization, policy_school = _policy_scope_for_acknowledgement(policy_version)
        if is_policy_within_user_scope(
            policy_organization=policy_organization,
            policy_school=policy_school,
            user=user,
        ):
            return True

    if "Admission Officer" in roles and context_doctype == "Student Applicant":
        organization_scope, school_scope = get_user_policy_scope(user)
        applicant = frappe.db.get_value(
            "Student Applicant",
            context_name,
            ["organization", "school"],
            as_dict=True,
        )
        if applicant:
            organization = (applicant.get("organization") or "").strip()
            school = (applicant.get("school") or "").strip()
            if organization in set(organization_scope) and (not school_scope or school in set(school_scope)):
                return True

    guardian_name = _guardian_name_for_user(user)
    if guardian_name:
        if context_doctype == "Guardian" and context_name == guardian_name:
            return True
        if context_doctype == "Student":
            linked = frappe.db.exists(
                "Student Guardian",
                {
                    "parent": context_name,
                    "parenttype": "Student",
                    "parentfield": "guardians",
                    "guardian": guardian_name,
                },
            )
            if linked:
                return True

    student_name = _student_name_for_user(user)
    if student_name and context_doctype == "Student" and context_name == student_name:
        return True

    if has_admissions_applicant_role(user) and context_doctype == "Student Applicant":
        applicant_user = frappe.db.get_value("Student Applicant", context_name, "applicant_user")
        if (applicant_user or "").strip() == user:
            return True

    if has_staff_role(user) and context_doctype == "Employee":
        employee_user = frappe.db.get_value("Employee", context_name, "user_id")
        if (employee_user or "").strip() == user:
            return True

    return False

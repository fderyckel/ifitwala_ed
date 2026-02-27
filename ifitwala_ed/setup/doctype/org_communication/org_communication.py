# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/org_communication/org_communication.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime
from frappe.utils.nestedset import get_descendants_of

# --------------------------------------------------------------------
# Role constants & basic role helper
# --------------------------------------------------------------------

# Full admin: global control + delete rights
ADMIN_ROLES_FULL = {"System Manager", "Academic Admin"}

# Elevated audience rights: can target School Scope audiences with
# Staff or Community recipients, and can choose Issuing School within their nested scope.
ELEVATED_WIDE_AUDIENCE_ROLES = {"System Manager", "Academic Admin", "Assistant Admin"}
# Allowed to target/publish School Scope audiences that include Staff or Community.
# Kept separate from issuing-school elevation to avoid widening school-selection privileges.
WIDE_AUDIENCE_RECIPIENT_ROLES = {
    "System Manager",
    "Academic Admin",
    "Assistant Admin",
    "HR Manager",
    "Accounts Manager",
}

AUDIENCE_TARGET_MODES = {"School Scope", "Team", "Student Group"}
RECIPIENT_TOGGLE_FIELDS = ("to_staff", "to_students", "to_guardians", "to_community")
RECIPIENT_TOGGLE_LABELS = {
    "to_staff": "Staff",
    "to_students": "Students",
    "to_guardians": "Guardians",
    "to_community": "Community",
}
TARGET_MODE_ALLOWED_RECIPIENTS = {
    "School Scope": {"to_staff", "to_students", "to_guardians", "to_community"},
    "Team": {"to_staff"},
    "Student Group": {"to_staff", "to_students", "to_guardians"},
}


def _user_has_any_role(user: str, roles: set[str]) -> bool:
    """Return True if given user has any of the roles in `roles`."""
    if not user or user == "Guest":
        return False
    user_roles = set(frappe.get_roles(user))
    return bool(user_roles & roles)


def _as_bool(value) -> bool:
    return value in (1, "1", True)


def _get_recipient_flags(row) -> dict[str, bool]:
    return {field: _as_bool(getattr(row, field, 0)) for field in RECIPIENT_TOGGLE_FIELDS}


def _get_enabled_recipient_fields(row) -> set[str]:
    flags = _get_recipient_flags(row)
    return {field for field, enabled in flags.items() if enabled}


# --------------------------------------------------------------------
# Main Document controller
# --------------------------------------------------------------------


class OrgCommunication(Document):
    def validate(self):
        """Main validation pipeline.

        Order matters:
        1. Resolve and validate Organization scope.
        2. Enforce optional Issuing School based on user scope (node + descendants).
        3. Validate School<->Organization alignment when school is set.
        4. Handle date logic.
        5. Validate audience rows.
        6. Enforce audience role restrictions.
        7. Enforce status + publish window rules.
        8. Enforce portal_surface rules.
        9. Enforce Class Announcement pattern.
        """
        self._resolve_and_validate_organization_scope()
        self._validate_and_enforce_issuing_school_scope()
        self._validate_school_organization_alignment()
        self._validate_activity_context_links()
        self._normalize_and_validate_dates()
        self._validate_audiences()
        self._enforce_role_restrictions_on_audiences()
        self._enforce_status_rules()
        self._enforce_portal_surface_rules()
        self._validate_class_announcement_pattern()

    # ----------------------------------------------------------------
    # Issuing School / Organization
    # ----------------------------------------------------------------

    def _resolve_and_validate_organization_scope(self):
        """Resolve mandatory Organization and enforce user scope."""
        user = frappe.session.user
        is_privileged = _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES)

        selected_org = (self.organization or "").strip()
        if not selected_org and self.school:
            selected_org = (frappe.db.get_value("School", self.school, "organization") or "").strip()
        if not selected_org:
            selected_org = (_resolve_user_base_org(user) or "").strip()

        if not selected_org:
            default_school = _get_user_default_school(user)
            if default_school:
                selected_org = (frappe.db.get_value("School", default_school, "organization") or "").strip()

        if selected_org:
            self.organization = selected_org

        if not (self.organization or "").strip():
            frappe.throw(
                _("Organization is required for Org Communication."),
                title=_("Missing Organization"),
            )

        if is_privileged:
            return

        allowed_orgs = set(_resolve_user_org_scope(user))
        if not allowed_orgs:
            default_school = _get_user_default_school(user)
            if default_school:
                school_org = frappe.db.get_value("School", default_school, "organization")
                if school_org:
                    allowed_orgs.add(school_org)

        if not allowed_orgs:
            frappe.throw(
                _(
                    "You do not have an organization scope configured. "
                    "Please set a default organization or organization permission."
                ),
                title=_("No Organization Scope"),
            )

        if self.organization not in allowed_orgs:
            frappe.throw(
                _("You can only issue communications for organizations within your authorized scope."),
                title=_("Organization Not Allowed"),
            )

    def _validate_and_enforce_issuing_school_scope(self):
        """Enforce optional Issuing School rules using nestedset school hierarchy."""
        user = frappe.session.user
        default_school, tree = _get_school_scope_tree(user)

        # School is optional. When user has a configured default school and no value
        # was chosen, derive it for continuity with school-scoped users.
        if not self.school and default_school:
            self.school = default_school

        if not self.school:
            return

        if _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES):
            if tree and self.school not in tree:
                frappe.throw(
                    _(
                        "You can only issue communications from your school ({default_school}) or its child schools."
                    ).format(default_school=default_school),
                    title=_("Issuing School Not Allowed"),
                )
        else:
            if default_school:
                # Force, ignoring any client-side value
                self.school = default_school
                return

            allowed_schools = _get_allowed_schools_for_user(user)
            if not allowed_schools:
                frappe.throw(
                    _(
                        "You do not have an issuing school scope configured. "
                        "Please set a default school or default organization before selecting Issuing School."
                    ),
                    title=_("No School Scope"),
                )

            if self.school not in set(allowed_schools):
                frappe.throw(
                    _("You can only issue communications from schools within your organization scope."),
                    title=_("Issuing School Not Allowed"),
                )

    def _validate_school_organization_alignment(self):
        """When Issuing School is set, validate it is under selected Organization.

        Organization can be the same as School.organization or any ancestor
        organization in the organization tree.
        """
        if not self.school:
            return

        school_org = frappe.db.get_value("School", self.school, "organization")
        if not school_org:
            return

        if not self.organization:
            self.organization = school_org
            return

        allowed_scope = set(_get_descendant_organizations_uncached(self.organization))
        if school_org not in allowed_scope:
            frappe.throw(
                _(
                    "Organization {org} does not include School {school}. School belongs to organization {school_org}."
                ).format(
                    org=self.organization,
                    school=self.school,
                    school_org=school_org,
                ),
                title=_("Invalid Organization"),
            )

    def _validate_activity_context_links(self):
        """
        Validate optional activity context links for deterministic activity filtering.
        """
        offering = (self.activity_program_offering or "").strip()
        booking = (self.activity_booking or "").strip()
        student_group = (self.activity_student_group or "").strip()

        booking_row = None
        if booking:
            booking_row = frappe.db.get_value(
                "Activity Booking",
                booking,
                ["program_offering", "allocated_student_group"],
                as_dict=True,
            )
            if not booking_row:
                frappe.throw(
                    _("Activity Booking {0} does not exist.").format(booking),
                    title=_("Invalid Activity Context"),
                )
            booking_offering = (booking_row.get("program_offering") or "").strip()
            if offering and booking_offering and offering != booking_offering:
                frappe.throw(
                    _("Activity Program Offering does not match Activity Booking's Program Offering."),
                    title=_("Invalid Activity Context"),
                )
            if not offering and booking_offering:
                self.activity_program_offering = booking_offering

        student_group_row = None
        if student_group:
            student_group_row = frappe.db.get_value(
                "Student Group",
                student_group,
                ["group_based_on", "program_offering"],
                as_dict=True,
            )
            if not student_group_row:
                frappe.throw(
                    _("Activity Student Group {0} does not exist.").format(student_group),
                    title=_("Invalid Activity Context"),
                )
            if (student_group_row.get("group_based_on") or "").strip() != "Activity":
                frappe.throw(
                    _("Activity Student Group must be a Student Group with Group Based On = Activity."),
                    title=_("Invalid Activity Context"),
                )
            sg_offering = (student_group_row.get("program_offering") or "").strip()
            if offering and sg_offering and offering != sg_offering:
                frappe.throw(
                    _("Activity Student Group does not belong to the selected Activity Program Offering."),
                    title=_("Invalid Activity Context"),
                )
            if not offering and sg_offering:
                self.activity_program_offering = sg_offering

        if booking_row and student_group:
            booking_section = (booking_row.get("allocated_student_group") or "").strip()
            if booking_section and booking_section != student_group:
                frappe.throw(
                    _("Activity Booking section does not match Activity Student Group."),
                    title=_("Invalid Activity Context"),
                )

    # ----------------------------------------------------------------
    # Date / window logic
    # ----------------------------------------------------------------

    def _normalize_and_validate_dates(self):
        """Handle brief_start/end normalization and publish_from/to sanity checks."""
        # Brief date range normalisation
        if self.brief_start_date and not self.brief_end_date:
            self.brief_end_date = self.brief_start_date

        if self.brief_start_date and self.brief_end_date:
            if self.brief_end_date < self.brief_start_date:
                frappe.throw(
                    _("Brief End Date cannot be before Brief Start Date."),
                    title=_("Invalid Brief Date Range"),
                )

        # Publish window sanity checks
        if self.publish_from and self.publish_to:
            start = get_datetime(self.publish_from)
            end = get_datetime(self.publish_to)
            if end < start:
                frappe.throw(
                    _("Publish Until cannot be earlier than Publish From."),
                    title=_("Invalid Publish Window"),
                )

    # ----------------------------------------------------------------
    # Audience validation (structure + school alignment)
    # ----------------------------------------------------------------

    def _validate_audiences(self):
        """Validate the audience rows structurally and by school scope.

        - At least one row.
        - Per target_mode, enforce required fields and recipient toggles.
        - For non-admins: School Scope rows must be within allowed scope.
        - For everyone: School Scope rows must be consistent with the parent
          Issuing School nested tree.
        """
        if not self.audiences:
            frappe.throw(
                _("Please add at least one Audience for this communication."),
                title=_("Missing Audience"),
            )

        user = frappe.session.user
        is_privileged = _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES)

        # Non-privileged allowed schools (node + descendants)
        allowed_schools = _get_allowed_schools_for_user(user)

        # Parent school descendants for structural consistency
        parent_descendants = []
        if self.school:
            parent_descendants = get_descendants_of("School", self.school, ignore_permissions=True) or []
            parent_descendants = {self.school, *parent_descendants}

        school_scope_rows = [row for row in (self.audiences or []) if (row.target_mode or "").strip() == "School Scope"]
        school_scope_names = sorted(
            {(row.school or "").strip() for row in school_scope_rows if (row.school or "").strip()}
        )
        school_org_map: dict[str, str] = {}
        if school_scope_names:
            school_meta = frappe.get_all(
                "School",
                filters={"name": ["in", tuple(school_scope_names)]},
                fields=["name", "organization"],
                limit_page_length=0,
            )
            school_org_map = {
                (row.get("name") or "").strip(): (row.get("organization") or "").strip() for row in school_meta
            }

        for row in self.audiences:
            target_mode = (row.target_mode or "").strip()
            if not target_mode:
                frappe.throw(
                    _("Target Mode is required for each Audience row."),
                    title=_("Missing Target Mode"),
                )

            if target_mode not in AUDIENCE_TARGET_MODES:
                frappe.throw(
                    _("Unsupported Target Mode: {mode}").format(mode=target_mode),
                    title=_("Invalid Audience"),
                )

            if target_mode == "School Scope":
                if not row.school:
                    frappe.throw(
                        _("Audience row for School Scope must specify a School."),
                        title=_("Incomplete Audience"),
                    )
            elif target_mode == "Team":
                if not row.team:
                    frappe.throw(
                        _("Audience row for Team must specify a Team."),
                        title=_("Incomplete Audience"),
                    )
            elif target_mode == "Student Group":
                if not row.student_group:
                    frappe.throw(
                        _("Audience row for Student Group must specify a Student Group."),
                        title=_("Incomplete Audience"),
                    )

            enabled_recipients = _get_enabled_recipient_fields(row)
            if not enabled_recipients:
                frappe.throw(
                    _("Audience row must include at least one Recipient toggle."),
                    title=_("Missing Recipients"),
                )

            allowed_roles = TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set())
            invalid_roles = enabled_recipients - allowed_roles
            if invalid_roles:
                allowed_labels = ", ".join(sorted(RECIPIENT_TOGGLE_LABELS.get(role, role) for role in allowed_roles))
                frappe.throw(
                    _("Audience row for {mode} allows only: {roles}.").format(
                        mode=target_mode,
                        roles=allowed_labels,
                    ),
                    title=_("Invalid Audience Recipients"),
                )

            if target_mode == "School Scope":
                if not is_privileged and allowed_schools:
                    if row.school not in allowed_schools:
                        frappe.throw(
                            _(
                                "You cannot target school {school} in this audience row. "
                                "You may only target your school or its child schools."
                            ).format(school=row.school),
                            title=_("Audience School Not Allowed"),
                        )

                if parent_descendants and row.school not in parent_descendants:
                    allow_same_org_explicit_school = (
                        not _as_bool(getattr(row, "include_descendants", 0))
                        and (self.organization or "").strip()
                        and school_org_map.get((row.school or "").strip(), "") == (self.organization or "").strip()
                    )
                    if not allow_same_org_explicit_school:
                        frappe.throw(
                            _(
                                "Audience row school {row_school} is not within the scope of the "
                                "parent communication school {parent_school}."
                            ).format(row_school=row.school, parent_school=self.school),
                            title=_("Audience School Outside Scope"),
                        )

    # ----------------------------------------------------------------
    # Role-based restrictions on audience choices
    # ----------------------------------------------------------------

    def _enforce_role_restrictions_on_audiences(self):
        """Restrict School Scope rows with Staff/Community recipients to privileged roles."""
        user = frappe.session.user
        is_wide_privileged = _user_has_any_role(user, WIDE_AUDIENCE_RECIPIENT_ROLES)

        if not self.audiences:
            return

        for row in self.audiences:
            target_mode = (row.target_mode or "").strip()
            if target_mode != "School Scope":
                continue

            enabled_recipients = _get_enabled_recipient_fields(row)
            if enabled_recipients & {"to_staff", "to_community"} and not is_wide_privileged:
                frappe.throw(
                    _(
                        "You are not allowed to target Staff or Community at School Scope. "
                        "Only Academic Admin, Assistant Admin, HR Manager, Accounts Manager, or System Manager may do this."
                    ),
                    title=_("Audience Not Allowed"),
                )

    # ----------------------------------------------------------------
    # Status / publish window rules
    # ----------------------------------------------------------------

    def _enforce_status_rules(self):
        """Enforce basic rules around status + publish_from/publish_to."""
        user = frappe.session.user
        is_admin = _user_has_any_role(user, ADMIN_ROLES_FULL | WIDE_AUDIENCE_RECIPIENT_ROLES)

        now = now_datetime()

        # Auto-set publish_from when moving to Published without a value
        if self.status == "Published" and not self.publish_from:
            self.publish_from = now

        if self.status == "Scheduled":
            if not self.publish_from:
                frappe.throw(
                    _("Scheduled communications must have a 'Publish From' datetime."),
                    title=_("Missing Publish From"),
                )
            if get_datetime(self.publish_from) <= now:
                frappe.throw(
                    _("Publish From for a Scheduled communication must be in the future."),
                    title=_("Invalid Schedule"),
                )

        # Restrict publishing of wide audiences for non-privileged users
        if self.status == "Published" and not is_admin:
            if any(
                (r.target_mode or "").strip() == "School Scope"
                and _get_enabled_recipient_fields(r) & {"to_staff", "to_community"}
                for r in self.audiences
            ):
                frappe.throw(
                    _("You are not allowed to publish School Scope communications that target Staff or Community."),
                    title=_("Publish Not Allowed"),
                )

    # ----------------------------------------------------------------
    # Portal surface rules
    # ----------------------------------------------------------------

    def _enforce_portal_surface_rules(self):
        """Ensure portal_surface is compatible with brief dates."""
        portal_surface = (self.portal_surface or "").strip()

        if portal_surface in {"Morning Brief", "Everywhere"}:
            if not self.brief_start_date:
                frappe.throw(
                    _("Brief Start Date is required when Portal Surface is Morning Brief or Everywhere."),
                    title=_("Missing Brief Start Date"),
                )

        # No further constraints for Desk / Portal Feed here;
        # the front-end will decide which communications to pull where.

    # ----------------------------------------------------------------
    # Class Announcement pattern
    # ----------------------------------------------------------------

    def _validate_class_announcement_pattern(self):
        """For Class Announcement type, enforce a sane audience pattern.

        - Must target Students (and optionally Guardians/Staff).
        - At least one Student Group audience row with to_students enabled.
        """
        if (self.communication_type or "").strip() != "Class Announcement":
            return

        has_student_group_row = False
        for row in self.audiences:
            if (row.target_mode or "").strip() != "Student Group":
                continue
            if not row.student_group:
                continue
            if _as_bool(getattr(row, "to_students", 0)):
                has_student_group_row = True
                break

        if not has_student_group_row:
            frappe.throw(
                _(
                    "Class Announcement communications must have at least one Audience row "
                    "targeting Students with a Student Group."
                ),
                title=_("Invalid Class Announcement Audience"),
            )

    # ----------------------------------------------------------------
    # Delete behaviour
    # ----------------------------------------------------------------

    def on_trash(self):
        """Only high-privilege roles can delete communications.

        Best practice in schools is to prefer archiving over hard delete.
        """
        user = frappe.session.user
        if not _user_has_any_role(user, ADMIN_ROLES_FULL):
            # Assistant Admin is intentionally excluded here: they can manage content
            # but should not hard-delete the record.
            frappe.throw(
                _("You are not allowed to delete communications. Please archive instead."),
                frappe.PermissionError,
            )


# --------------------------------------------------------------------
# School scope helpers (nestedset-based)
# --------------------------------------------------------------------


def _get_user_default_school(user: str | None = None) -> str | None:
    """Best-effort helper to get a user's default school.

    Try in order:
    - Employee.default_school
    - Employee.school
    """
    if not user or user == "Guest":
        return None

    # Build field list defensively; only include default_school if column exists
    fields = ["name", "school"]
    if frappe.db.has_column("Employee", "default_school"):
        fields.insert(1, "default_school")

    emp = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=True,
    )
    if not emp:
        return None

    return emp.get("default_school") or emp.get("school")


def _get_school_scope_tree(user: str | None = None) -> tuple[str | None, list[str]]:
    """Return (default_school, allowed_schools_tree) for a user.

    default_school: node where the user "sits".
    allowed_schools_tree: default_school + all descendants (nestedset).
    """
    user = user or frappe.session.user
    default_school = _get_user_default_school(user)
    if not default_school:
        return None, []

    descendants = get_descendants_of("School", default_school, ignore_permissions=True) or []
    allowed = list({default_school, *descendants})
    return default_school, allowed


def _get_user_default_from_db(user: str, key: str) -> str | None:
    rows = frappe.get_all(
        "DefaultValue",
        filters={"parent": user, "defkey": key},
        fields=["defvalue"],
        order_by="modified desc, creation desc, name desc",
        limit=1,
    )
    if not rows:
        return None
    value = (rows[0].get("defvalue") or "").strip()
    return value or None


def _get_user_employee_organization(user: str | None = None) -> str | None:
    if not user or user == "Guest":
        return None

    organization = frappe.db.get_value("Employee", {"user_id": user}, "organization")
    return (organization or "").strip() or None


def _resolve_user_base_org(user: str) -> str | None:
    default_org = _get_user_default_from_db(user, "organization")
    if default_org:
        return default_org
    return _get_user_employee_organization(user)


def _get_descendant_organizations_uncached(org: str) -> list[str]:
    org = (org or "").strip()
    if not org:
        return []

    if not frappe.db.exists("Organization", org):
        return []

    descendants = get_descendants_of("Organization", org, ignore_permissions=True) or []
    return [org, *[item for item in descendants if item and item != org]]


def _resolve_user_org_scope(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return []

    scope: set[str] = set()

    base_org = _resolve_user_base_org(user)
    if base_org:
        scope.update(item for item in _get_descendant_organizations_uncached(base_org) if item)

    explicit_orgs = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Organization"},
        pluck="for_value",
    )
    for org in explicit_orgs or []:
        org_name = (org or "").strip()
        if not org_name:
            continue
        scope.update(item for item in _get_descendant_organizations_uncached(org_name) if item)

    return sorted(scope)


def _get_org_scope_schools_for_user(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    org_scope = _resolve_user_org_scope(user)
    if not org_scope:
        return []

    schools = frappe.get_all(
        "School",
        filters={"organization": ["in", org_scope]},
        pluck="name",
        order_by="lft asc, name asc",
    )
    return [school for school in schools if school]


def _get_allowed_schools_for_user(user: str | None = None) -> list[str]:
    """Used in permission_query_conditions / has_permission.

    Admins: return [] to indicate *no SQL restriction*.
    Non-admins:
    - default_school + descendants when a default school is configured
    - otherwise, schools under effective organization scope (organization + descendants
      from user defaults and explicit Organization User Permissions)
    """
    user = user or frappe.session.user

    if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
        # No school restriction for these roles at the query-condition level
        return []

    default_school, allowed = _get_school_scope_tree(user)
    if default_school:
        return allowed

    return _get_org_scope_schools_for_user(user)


def _get_allowed_organizations_for_user(user: str | None = None) -> list[str]:
    """Organizations non-admin users can access for org-level communications."""
    user = user or frappe.session.user

    if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
        # No organization restriction for these roles at query-condition level.
        return []

    org_scope = _resolve_user_org_scope(user)
    if org_scope:
        return org_scope

    default_school = _get_user_default_school(user)
    if not default_school:
        return []

    school_org = frappe.db.get_value("School", default_school, "organization")
    return [school_org] if school_org else []


# --------------------------------------------------------------------
# Client context API (for Desk UX)
# --------------------------------------------------------------------


@frappe.whitelist()
def get_org_communication_context() -> dict:
    """Context for client-side UX:

    - default_school: where the user "sits" in the nestedset
    - allowed_schools:
      * default_school node + descendants when default_school exists
      * org-scope schools when no default_school for non-privileged users
    - is_privileged: can choose Issuing School (Academic Admin, Assistant Admin, System Manager)
    """
    user = frappe.session.user
    default_school, school_tree = _get_school_scope_tree(user)
    is_privileged = _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES)

    base_org = _resolve_user_base_org(user)
    org_scope = _resolve_user_org_scope(user)
    if not base_org and default_school:
        base_org = frappe.db.get_value("School", default_school, "organization")
    if not org_scope and base_org:
        org_scope = _get_descendant_organizations_uncached(base_org)

    # For non-privileged users without a default school, allow selecting from
    # schools inside their effective organization scope.
    if default_school:
        allowed_schools = school_tree
    elif is_privileged:
        allowed_schools = school_tree
    else:
        allowed_schools = _get_org_scope_schools_for_user(user)

    can_select_school = bool(is_privileged or (not default_school and allowed_schools))
    lock_to_default_school = bool(default_school and not is_privileged)

    return {
        "default_school": default_school,
        "default_organization": base_org,
        "allowed_schools": allowed_schools,
        "allowed_organizations": org_scope,
        "is_privileged": is_privileged,
        "can_select_school": can_select_school,
        "lock_to_default_school": lock_to_default_school,
    }


# --------------------------------------------------------------------
# Permission hooks
# --------------------------------------------------------------------


def get_permission_query_conditions(user: str | None = None) -> str | None:
    """Limit Org Communication list by school/org for non-admin users.

    Admins (System Manager, Academic Admin, Assistant Admin) see all.
    Others see communications for their effective school scope:
    - default_school + descendants when available
    - otherwise, schools under their authorized organization scope
    """
    user = user or frappe.session.user

    if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
        return None

    allowed_schools = _get_allowed_schools_for_user(user)
    allowed_orgs = _get_allowed_organizations_for_user(user)
    if not allowed_schools and not allowed_orgs:
        # No scope configured; effectively hide all.
        return "1=0"

    clauses = []
    if allowed_schools:
        escaped_schools = ", ".join(frappe.db.escape(s) for s in allowed_schools)
        clauses.append(f"`tabOrg Communication`.`school` in ({escaped_schools})")

    if allowed_orgs:
        escaped_orgs = ", ".join(frappe.db.escape(o) for o in allowed_orgs)
        clauses.append(
            "("
            "COALESCE(`tabOrg Communication`.`school`, '') = '' "
            f"AND `tabOrg Communication`.`organization` in ({escaped_orgs})"
            ")"
        )

    if not clauses:
        return "1=0"

    if len(clauses) == 1:
        return clauses[0]

    return "(" + " OR ".join(clauses) + ")"


def has_permission(doc: "OrgCommunication", user: str = None, ptype: str = None) -> bool:
    """Fine-tune permissions on top of role-based DocType perms.

    - Read: must be within school/org scope unless admin.
    - Write: admins always; others only for docs in their school/org scope, and
      typically their own docs.
    - Delete: restricted to ADMIN_ROLES_FULL; on_trash enforces as well.
    """
    user = user or frappe.session.user
    ptype = ptype or "read"

    # Admin roles: defer to role-based permissions except for delete, which we tighten.
    if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
        if ptype == "delete":
            # Assistant Admin is not in ADMIN_ROLES_FULL, so only System Manager
            # and Academic Admin get delete = True here.
            return _user_has_any_role(user, ADMIN_ROLES_FULL)
        return True

    allowed_schools = set(_get_allowed_schools_for_user(user))
    allowed_orgs = set(_get_allowed_organizations_for_user(user))

    doc_school = (doc.school or "").strip() if getattr(doc, "school", None) else ""
    doc_org = (doc.organization or "").strip() if getattr(doc, "organization", None) else ""

    if doc_school:
        if not allowed_schools or doc_school not in allowed_schools:
            return False
    else:
        if not doc_org or not allowed_orgs or doc_org not in allowed_orgs:
            return False

    if ptype == "read":
        return True

    if ptype in {"write", "submit", "cancel", "amend"}:
        # Non-admins can only modify their own docs, and only while not Archived.
        if doc.owner == user and doc.status in {"Draft", "Scheduled", "Published"}:
            return True
        return False

    if ptype == "delete":
        return False

    # Default fallback
    return True


def on_doctype_update():
    frappe.db.add_index(
        "Org Communication",
        ["activity_program_offering", "publish_from"],
        index_name="idx_org_comm_activity_offering_publish",
    )
    frappe.db.add_index(
        "Org Communication",
        ["activity_student_group", "publish_from"],
        index_name="idx_org_comm_activity_group_publish",
    )

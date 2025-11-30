# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/org_communication/org_communication.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime
from frappe.utils.nestedset import get_descendants_of


ADMIN_ROLES_FULL = {"System Manager", "Academic Admin", "Admin Assistant"}
ELEVATED_WIDE_AUDIENCE_ROLES = {"System Manager", "Academic Admin", "Admin Assistant"}


def _user_has_any_role(user: str, roles: set[str]) -> bool:
	if not user or user == "Guest":
		return False
	user_roles = set(frappe.get_roles(user))
	return bool(user_roles & roles)


def _get_user_default_school(user: str | None = None) -> str | None:
	"""Best-effort helper to get a user's default school.

	Adjust this if your Employee schema differs.

	Try in order:
	- Employee.default_school
	- Employee.school
	"""
	if not user or user == "Guest":
		return None

	emp = frappe.db.get_value(
		"Employee",
		{"user_id": user},
		["name", "default_school", "school"],
		as_dict=True,
	)
	if not emp:
		return None

	return emp.get("default_school") or emp.get("school")


def _get_allowed_schools_for_user(user: str | None = None) -> list[str]:
	"""Return the list of schools this user is allowed to target/view by default.

	For non-admins: default school + its descendants (nestedset).
	Admins: all schools (returns [] so we don't constrain them in SQL).
	"""
	user = user or frappe.session.user

	if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
		# No school restriction for these roles at the query-condition level
		return []

	default_school = _get_user_default_school(user)
	if not default_school:
		# No school configured: safest is to give them nothing by default
		return []

	descendants = get_descendants_of("School", default_school, ignore_permissions=True) or []
	# get_descendants_of returns children only; include the default_school itself
	return list({default_school, *descendants})


class OrgCommunication(Document):
	def validate(self):
		self._set_organization_from_school()
		self._validate_school_scope_for_creator()
		self._normalize_and_validate_dates()
		self._validate_audiences()
		self._enforce_role_restrictions_on_audiences()
		self._enforce_status_rules()
		self._enforce_portal_surface_rules()
		self._validate_class_announcement_pattern()

	def _set_organization_from_school(self):
		"""If school is set, organization must match the school's organization.
		If blank, auto-fill. If mismatched, throw.
		"""
		if not self.school:
			return

		school_org = frappe.db.get_value("School", self.school, "organization")
		if not school_org:
			return

		if self.organization and self.organization != school_org:
			frappe.throw(
				_(
					"Organization {org} does not match the organization of School {school}."
				).format(org=self.organization, school=self.school),
				title=_("Invalid Organization"),
			)

		self.organization = school_org

	def _validate_school_scope_for_creator(self):
		"""Non-admin users can only use their default school or one of its descendants."""
		user = frappe.session.user

		if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
			return

		if not self.school:
			# schema already makes school reqd, but guard anyway
			frappe.throw(
				_("School is required for Org Communication."),
				title=_("Missing School"),
			)

		allowed_schools = _get_allowed_schools_for_user(user)
		if not allowed_schools:
			frappe.throw(
				_("You do not have any configured school to create communications for."),
				title=_("No School Scope"),
			)

		if self.school not in allowed_schools:
			frappe.throw(
				_(
					"You can only create communications for your school ({school}) "
					"or its child schools."
				).format(school=_get_user_default_school(user)),
				title=_("School Not Allowed"),
			)

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

	def _validate_audiences(self):
		"""Validate the audience rows structurally (field combinations).

		- At least one row.
		- Per target_group, enforce required fields.
		- School alignment: audience.school must be within allowed scope
		  of the parent school for non-admins, or at least consistent with nested set.
		"""
		if not self.audiences:
			frappe.throw(
				_("Please add at least one Audience for this communication."),
				title=_("Missing Audience"),
			)

		user = frappe.session.user
		is_admin = _user_has_any_role(
			user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES
		)

		# Precompute allowed schools for non-admins
		allowed_schools = _get_allowed_schools_for_user(user)

		# Precompute parent school descendants for structural consistency
		parent_descendants = []
		if self.school:
			parent_descendants = get_descendants_of(
				"School", self.school, ignore_permissions=True
			) or []
			parent_descendants = {self.school, *parent_descendants}

		for row in self.audiences:
			# Align row.organization with row.school or parent organization
			if row.school:
				row_org = frappe.db.get_value("School", row.school, "organization")
				if row.organization and row.organization != row_org:
					frappe.throw(
						_(
							"Audience row for School {school} has mismatched Organization {org}."
						).format(school=row.school, org=row.organization),
						title=_("Invalid Audience Organization"),
					)
				row.organization = row_org or self.organization
			else:
				# No school set on row; default to parent school/org if present
				row.school = self.school
				row.organization = row.organization or self.organization

			# For non-admins, row.school must be in allowed_schools
			if not is_admin and allowed_schools:
				if row.school and row.school not in allowed_schools:
					frappe.throw(
						_(
							"You cannot target school {school} in this audience row. "
							"You may only target your school or its child schools."
						).format(school=row.school),
						title=_("Audience School Not Allowed"),
					)

			# Structural consistency with parent school tree
			if parent_descendants and row.school and row.school not in parent_descendants:
				frappe.throw(
					_(
						"Audience row school {row_school} is not within the scope of the "
						"parent communication school {parent_school}."
					).format(row_school=row.school, parent_school=self.school),
					title=_("Audience School Outside Scope"),
				)

			target_group = (row.target_group or "").strip()

			# Per target_group rules
			if target_group in {"Whole Staff", "Academic Staff"}:
				# Staff targeting: must have school or team
				if not (row.school or row.team):
					frappe.throw(
						_(
							"Audience row for {group} must specify at least a School or a Team."
						).format(group=target_group),
						title=_("Incomplete Audience"),
					)

			elif target_group == "Students":
				# Must have at least one of: student_group, program, school
				if not (row.student_group or row.program or row.school):
					frappe.throw(
						_(
							"Audience row for Students must specify at least a Student Group, "
							"Program, or School."
						),
						title=_("Incomplete Audience"),
					)

			elif target_group == "Guardians":
				# Same requirement as Students
				if not (row.student_group or row.program or row.school):
					frappe.throw(
						_(
							"Audience row for Guardians must specify at least a Student Group, "
							"Program, or School."
						),
						title=_("Incomplete Audience"),
					)

			elif target_group == "Whole Community":
				if not row.school:
					frappe.throw(
						_("Audience row for Whole Community must specify a School."),
						title=_("Incomplete Audience"),
					)

			else:
				# If someone adds a new target_group option later and forgets to handle it
				frappe.throw(
					_("Unsupported Target Group: {group}").format(group=target_group),
					title=_("Invalid Audience"),
				)

	def _enforce_role_restrictions_on_audiences(self):
		"""Restrict which target_group values non-privileged users may use."""
		user = frappe.session.user
		is_wide_privileged = _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES)

		if not self.audiences:
			return

		for row in self.audiences:
			target_group = (row.target_group or "").strip()

			if target_group in {"Whole Staff", "Whole Community"} and not is_wide_privileged:
				frappe.throw(
					_(
						"You are not allowed to target '{group}'. "
						"Only Academic Admin, Assistant Admin, or System Manager may do this."
					).format(group=target_group),
					title=_("Audience Not Allowed"),
				)

	def _enforce_status_rules(self):
		"""Enforce basic rules around status + publish_from/publish_to."""
		user = frappe.session.user
		is_admin = _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES)

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
			wide_groups = {"Whole Staff", "Whole Community"}
			if any((r.target_group or "").strip() in wide_groups for r in self.audiences):
				frappe.throw(
					_(
						"You are not allowed to publish communications targeting Whole Staff "
						"or Whole Community."
					),
					title=_("Publish Not Allowed"),
				)

	def _enforce_portal_surface_rules(self):
		"""Ensure portal_surface is compatible with brief dates."""
		portal_surface = (self.portal_surface or "").strip()

		if portal_surface in {"Morning Brief", "Everywhere"}:
			if not self.brief_start_date:
				frappe.throw(
					_(
						"Brief Start Date is required when Portal Surface is Morning Brief "
						"or Everywhere."
					),
					title=_("Missing Brief Start Date"),
				)

		# No further constraints for Desk / Portal Feed here;
		# the front-end will decide which communications to pull where.

	def _validate_class_announcement_pattern(self):
		"""For Class Announcement type, enforce a sane audience pattern.

		- Must target Students (and optionally Guardians).
		- At least one Students audience row with a Student Group.
		"""
		if (self.communication_type or "").strip() != "Class Announcement":
			return

		has_student_group_row = False
		for row in self.audiences:
			if (row.target_group or "").strip() == "Students" and row.student_group:
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
# Permission hooks
# --------------------------------------------------------------------


def get_permission_query_conditions(user: str | None = None) -> str | None:
	"""Limit Org Communication list by school for non-admin users.

	Admins (System Manager, Academic Admin, Assistant Admin) see all.
	Others only see communications for their school + descendants.
	"""
	user = user or frappe.session.user

	if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
		return None

	allowed_schools = _get_allowed_schools_for_user(user)
	if not allowed_schools:
		# No school scope; effectively hide all
		return "1=0"

	# Build a safe IN clause
	escaped = ", ".join(frappe.db.escape(s) for s in allowed_schools)
	return f"`tabOrg Communication`.`school` in ({escaped})"


def has_permission(doc: "OrgCommunication", user: str = None, ptype: str = None) -> bool:
	"""Fine-tune permissions on top of role-based DocType perms.

	- Read: must be within school scope unless admin.
	- Write: admins always; others only for docs in their school scope, and
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

	allowed_schools = _get_allowed_schools_for_user(user)
	if not allowed_schools:
		return False

	if doc.school not in allowed_schools:
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

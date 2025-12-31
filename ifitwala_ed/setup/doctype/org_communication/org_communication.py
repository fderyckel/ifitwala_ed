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

AUDIENCE_TARGET_MODES = {"School Scope", "Team", "Student Group"}
AUDIENCE_RECIPIENT_ROLES = {"Staff", "Students", "Guardians", "Community"}
TARGET_MODE_ALLOWED_RECIPIENTS = {
	"School Scope": AUDIENCE_RECIPIENT_ROLES,
	"Team": {"Staff"},
	"Student Group": {"Staff", "Students", "Guardians"},
}


def _user_has_any_role(user: str, roles: set[str]) -> bool:
	"""Return True if given user has any of the roles in `roles`."""
	if not user or user == "Guest":
		return False
	user_roles = set(frappe.get_roles(user))
	return bool(user_roles & roles)


def _get_recipient_roles(row) -> list[str]:
	roles = []
	for recipient in row.recipients or []:
		role = (recipient.recipient_role or "").strip()
		if role:
			roles.append(role)
	return roles


# --------------------------------------------------------------------
# Main Document controller
# --------------------------------------------------------------------


class OrgCommunication(Document):
	def validate(self):
		"""Main validation pipeline.

		Order matters:
		1. Enforce Issuing School based on user scope (node + descendants).
		2. Derive organization from school.
		3. Handle date logic.
		4. Validate audience rows.
		5. Enforce audience role restrictions.
		6. Enforce status + publish window rules.
		7. Enforce portal_surface rules.
		8. Enforce Class Announcement pattern.
		"""
		self._validate_and_enforce_issuing_school_scope()
		self._set_organization_from_school()
		self._normalize_and_validate_dates()
		self._validate_audiences()
		self._enforce_role_restrictions_on_audiences()
		self._enforce_status_rules()
		self._enforce_portal_surface_rules()
		self._validate_class_announcement_pattern()

	# ----------------------------------------------------------------
	# Issuing School / Organization
	# ----------------------------------------------------------------

	def _validate_and_enforce_issuing_school_scope(self):
		"""Enforce Issuing School rules using nestedset school hierarchy.

		Scope of authority = default_school node + its descendants.

		- Non-privileged users (no elevated roles):
		  * Issuing School is *forced* to their default_school.
		  * They cannot issue for another school.

		- Privileged roles (System Manager, Academic Admin, Assistant Admin):
		  * Can choose Issuing School, but it must be within their node + descendants.
		"""
		user = frappe.session.user
		default_school, tree = _get_school_scope_tree(user)

		if _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES):
			# Privileged: they can choose any school in their nested scope
			if not tree:
				# No configured school – require an explicit Issuing School
				if not self.school:
					frappe.throw(
						_("Issuing School is required for Org Communication."),
						title=_("Missing Issuing School"),
					)
				return

			if not self.school:
				# Default to their own node if nothing set
				self.school = default_school

			if self.school not in tree:
				frappe.throw(
					_(
						"You can only issue communications from your school ({default_school}) "
						"or its child schools."
					).format(default_school=default_school),
					title=_("Issuing School Not Allowed"),
				)
		else:
			# Non-privileged: Issuing School is always their default_school
			if not default_school:
				frappe.throw(
					_("You do not have a default school configured. Please contact your admin."),
					title=_("No Default School"),
				)

			# Force, ignoring any client-side value
			self.school = default_school

	def _set_organization_from_school(self):
		"""Derive organization from Issuing School.

		If school is set, organization must match the school's organization.
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
		- Per target_mode, enforce required fields and recipient roles.
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
		is_privileged = _user_has_any_role(
			user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES
		)

		# Non-privileged allowed schools (node + descendants)
		allowed_schools = _get_allowed_schools_for_user(user)

		# Parent school descendants for structural consistency
		parent_descendants = []
		if self.school:
			parent_descendants = get_descendants_of(
				"School", self.school, ignore_permissions=True
			) or []
			parent_descendants = {self.school, *parent_descendants}

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

			if not row.recipients:
				frappe.throw(
					_("Audience row must include at least one Recipient."),
					title=_("Missing Recipients"),
				)

			seen_roles = set()
			recipients = []
			for recipient in row.recipients:
				role = (recipient.recipient_role or "").strip()
				if not role:
					frappe.throw(
						_("Recipient Role is required for each Audience recipient."),
						title=_("Invalid Audience Recipient"),
					)
				if role not in AUDIENCE_RECIPIENT_ROLES:
					frappe.throw(
						_("Invalid Recipient Role: {role}").format(role=role),
						title=_("Invalid Audience Recipient"),
					)
				if role in seen_roles:
					frappe.throw(
						_("Duplicate Recipient Role: {role}").format(role=role),
						title=_("Duplicate Recipients"),
					)
				seen_roles.add(role)
				recipients.append(role)

			allowed_roles = TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set())
			if any(role not in allowed_roles for role in recipients):
				frappe.throw(
					_(
						"Audience row for {mode} allows only: {roles}."
					).format(mode=target_mode, roles=", ".join(sorted(allowed_roles))),
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
		is_wide_privileged = _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES)

		if not self.audiences:
			return

		for row in self.audiences:
			target_mode = (row.target_mode or "").strip()
			if target_mode != "School Scope":
				continue

			recipient_roles = set(_get_recipient_roles(row))
			if recipient_roles & {"Staff", "Community"} and not is_wide_privileged:
				frappe.throw(
					_(
						"You are not allowed to target Staff or Community at School Scope. "
						"Only Academic Admin, Assistant Admin, or System Manager may do this."
					),
					title=_("Audience Not Allowed"),
				)

	# ----------------------------------------------------------------
	# Status / publish window rules
	# ----------------------------------------------------------------

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
			if any(
				(r.target_mode or "").strip() == "School Scope"
				and set(_get_recipient_roles(r)) & {"Staff", "Community"}
				for r in self.audiences
			):
				frappe.throw(
					_(
						"You are not allowed to publish School Scope communications "
						"that target Staff or Community."
					),
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
					_(
						"Brief Start Date is required when Portal Surface is Morning Brief "
						"or Everywhere."
					),
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
		- At least one Student Group audience row that includes Students.
		"""
		if (self.communication_type or "").strip() != "Class Announcement":
			return

		has_student_group_row = False
		for row in self.audiences:
			if (row.target_mode or "").strip() != "Student Group":
				continue
			if not row.student_group:
				continue
			recipient_roles = set(_get_recipient_roles(row))
			if "Students" in recipient_roles:
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


def _get_allowed_schools_for_user(user: str | None = None) -> list[str]:
	"""Used in permission_query_conditions / has_permission.

	Admins: return [] to indicate *no SQL restriction*.
	Non-admins: default_school + descendants.
	"""
	user = user or frappe.session.user

	if _user_has_any_role(user, ADMIN_ROLES_FULL | ELEVATED_WIDE_AUDIENCE_ROLES):
		# No school restriction for these roles at the query-condition level
		return []

	default_school, allowed = _get_school_scope_tree(user)
	if not default_school:
		return []

	return allowed


# --------------------------------------------------------------------
# Client context API (for Desk UX)
# --------------------------------------------------------------------


@frappe.whitelist()
def get_org_communication_context() -> dict:
	"""Context for client-side UX:

	- default_school: where the user "sits" in the nestedset
	- allowed_schools: node + descendants (even for privileged roles)
	- is_privileged: can choose Issuing School (Academic Admin, Assistant Admin, System Manager)
	"""
	user = frappe.session.user
	default_school, tree = _get_school_scope_tree(user)

	is_privileged = _user_has_any_role(user, ELEVATED_WIDE_AUDIENCE_ROLES)

	return {
		"default_school": default_school,
		"allowed_schools": tree,
		"is_privileged": is_privileged,
	}


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

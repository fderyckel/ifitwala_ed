# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/doctype/instructor/instructor.py

import frappe
from frappe import _
from frappe.model.document import Document
from ifitwala_ed.utilities.school_tree import get_descendant_schools

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
		# Always rebuild the computed child table right before saving
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
			as_dict=True
		)
		if not employee or not employee.user_id:
			frappe.throw(_("Linked Employee must have a User ID."))

		self.linked_user_id = employee.user_id
		self.gender = employee.employee_gender
		self.instructor_name = employee.employee_full_name
		self.instructor_image = employee.employee_image


	def rebuild_instructor_log(self):
		"""Clear and rebuild Instructor Log child table from Student Group Instructor links."""
		self.set("instructor_log", [])

		group_links = frappe.db.get_all(
			"Student Group Instructor",
			filters={"instructor": self.name},
			fields=["parent as student_group", "designation"]
		)
		if not group_links:
			return

		student_group_names = [g["student_group"] for g in group_links]
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
			]
		)
		group_lookup = {g["student_group"]: g for g in groups}

		for link in group_links:
			g = group_lookup.get(link["student_group"])
			if not g:
				continue

			other_details = _format_instructor_log_details(g)
			self.append("instructor_log", {
				"program": g.get("program"),
				"academic_year": g.get("academic_year"),
				"term": g.get("term"),
				"student_group": g.get("student_group"),
				"course": g.get("course"),
				"designation": link.get("designation"),
				"other_details": other_details,
			})


	def _validate_duplicate_employee(self):
		if self.employee and frappe.db.get_value("Instructor", {'employee': self.employee, 'name': ['!=', self.name]}, 'name'):
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


@frappe.whitelist()
def get_instructor_log(instructor: str):
	if not instructor:
		return []
	instructor_doc = frappe.get_doc("Instructor", instructor)
	instructor_doc.rebuild_instructor_log()
	return instructor_doc.get("instructor_log", [])

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

	# is_academic_controller removed - unused & {"Academic Admin", "Academic Assistant"})

	schools = _user_allowed_schools(user)
	user_escaped = frappe.db.escape(user, percent=False)

	if not schools:
		# No default school → still allow their own Instructor doc
		return f"`tabInstructor`.linked_user_id = {user_escaped}"

	escaped_values = ", ".join(frappe.db.escape(s, percent=False) for s in schools)

	# Normal school-based filter OR their own Instructor doc
	return (
		f"`tabInstructor`.school IN ({escaped_values}) "
		f"OR `tabInstructor`.linked_user_id = {user_escaped}"
	)



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


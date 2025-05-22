# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils.nestedset import get_descendants_of

class Program(NestedSet):

	def validate(self):
		self._validate_duplicate_course()

	def _validate_duplicate_course(self):
		seen = set()
		for row in self.courses:
			if row.course in seen:
				frappe.throw(_("Course {0} entered twice").format(row.course))
			seen.add(row.course)



def get_permission_query_conditions(user):
    # Full access for System Manager and Administrator
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"  # No access if no school assigned

    # Get self + descendants
    schools = [user_school] + get_descendants_of("School", user_school)

    schools_escaped = ', '.join([frappe.db.escape(s) for s in schools])
    return f"`tabProgram`.`school` in ({schools_escaped})"

def has_permission(doc, ptype, user):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    schools = [user_school] + get_descendants_of("School", user_school)
    return doc.school in schools
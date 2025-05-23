# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.utils.nestedset import get_descendants_of

class Course(Document):
	def validate(self):
		self.validate_sum_weighting()
		ass_criteria = []
		for d in self.assessment_criteria:
			if d.assessment_criteria in ass_criteria:
				frappe.throw(_("Assessment Criteria {0} appears more than once. Please remove duplicate entries.").format(d.assessment_criteria))
			else:
				ass_criteria.append(d.assessment_criteria)


	def validate_sum_weighting(self):
		if self.assessment_criteria:
			total_weight = 0
			for criteria in self.assessment_criteria:
				total_weight += criteria.criteria_weighting or 0
			if total_weight != 100:
				frappe.throw(_("The sum of the Criteria Weighting should be 100%.  Please adjust and try to save again."))

	def get_learning_units(self):
		lu_data = []
		for unit in self.units:
			unit_doc = frappe.get_doc("Learning Unit", unit.learning_unit)
			if unit_doc.unit_name:
				lu_data.append(unit_doc)
		#lu_data = lu_data.sort(key=lambda x: x.start_date)
		return lu_data


@frappe.whitelist()
def add_course_to_programs(course, programs, mandatory=False):
	programs = json.loads(programs)
	for entry in programs:
		program = frappe.get_doc('Program', entry)
		program.append('courses', {
			'course': course,
			'course_name': course,
			'required': mandatory
		})
		program.flags.ignore_mandatory = True
		program.save()
	frappe.db.commit()
	frappe.msgprint(_('The Course {0} has been added to all the selected programs successfully.').format(frappe.bold(course)),
		title=_('Programs updated'), indicator='green')

@frappe.whitelist()
def get_programs_without_course(course):
	data = []
	for entry in frappe.db.get_all('Program'):
		program = frappe.get_doc('Program', entry.name)
		courses = [c.course for c in program.courses]
		if not courses or course not in courses:
			data.append(program.name)
	return data

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
    return f"`tabCourse`.`school` in ({schools_escaped})"

def has_permission(doc, ptype, user):
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    schools = [user_school] + get_descendants_of("School", user_school)
    return doc.school in schools
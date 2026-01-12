import frappe

@frappe.whitelist()
def get_school_organization(school):
	"""
	Returns School.organization for the given school.
	Throws if missing.
	"""
	if not school:
		return None

	organization = frappe.db.get_value("School", school, "organization")
	if not organization:
		frappe.throw(f"School {school} is not linked to an Organization.")

	return organization

def get_student_organization(student):
	"""
	Reads Student.anchor_school and resolves Organization.
	"""
	anchor_school = frappe.db.get_value("Student", student, "anchor_school")
	if not anchor_school:
		return None # Or throw? Migration might have weak data.

	return get_school_organization(anchor_school)


def validate_account_holder_for_student(student_doc):
	"""
	Enforces org matching between student and account_holder.
	"""
	if not student_doc.account_holder:
		return

	if not student_doc.anchor_school:
		# If no school, strictly speaking we can't validate org, but account_holder implies org.
		# Let's verify student org if possible, but usually student must have school.
		return

	student_org = get_school_organization(student_doc.anchor_school)
	ah_org = frappe.db.get_value("Account Holder", student_doc.account_holder, "organization")

	if student_org and ah_org and student_org != ah_org:
		frappe.throw(f"Account Holder must belong to the same Organization as the Student ({student_org}).")

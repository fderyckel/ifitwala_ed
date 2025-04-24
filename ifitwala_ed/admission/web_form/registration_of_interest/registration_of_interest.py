# admission/web_form/registration_of_interest/registration_of_interest.py
# ---------------------------------------------------------------------
import frappe


def get_context(context):
	"""Inject extra data for Jinja (optional)."""
	today = frappe.utils.today()
	context.future_years = [
		y.name
		for y in frappe.get_all(
			"Academic Year",
			filters={"year_end_date": (">=", today)},
			order_by="year_start_date asc",
		)
	]
	# You can use {{ future_years }} in the .js/.html template if needed.


@frappe.whitelist(allow_guest=True)
def get_valid_academic_years():
	"""STAYS here only if some other code (or future Select field) calls it."""
	today = frappe.utils.today()
	return frappe.get_all(
		"Academic Year",
		filters={"year_end_date": (">=", today)},
		fields=["name"],
		order_by="year_start_date asc",
	)

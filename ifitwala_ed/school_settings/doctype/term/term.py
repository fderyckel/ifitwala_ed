# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, cstr, get_link_to_form
from frappe.model.document import Document
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import ParentRuleViolation
from ifitwala_ed.utilities.school_tree import get_descendant_schools, is_leaf_school


class Term(Document):
	# create automatically the name of the term.
	def autoname(self):
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
		abbr = frappe.db.get_value("School", ay_school, "abbr") or ay_school
		self.name = f"{abbr} {self.term_name} {self.academic_year}"
		self.title = f"{abbr} {self.term_name}"


	def validate(self):
		# first, we'll check that there are no other terms that are the same.
		self.validate_duplicate()
		self._sync_school_with_ay()

		if self.school:
			school_abbr = frappe.db.get_value("School", self.school, "abbr") or self.school
			self.title = f"{self.term_name} ({school_abbr}) - {self.academic_year}"
		else:
			self.title = f"{self.term_name} - {self.academic_year}"

		# start of term cannot be after end of term (or vice versa)
		if self.term_start_date and self.term_end_date and getdate(self.term_start_date) > getdate(self.term_end_date):
			frappe.throw(_("The start of the term has to be before its end. "))

		year = frappe.db.get_value("Academic Year", self.academic_year, ["year_start_date", "year_end_date"], as_dict=True)
		# start of term can not be before start of academic year
		if self.term_start_date and getdate(year.year_start_date) and getdate(self.term_start_date) < getdate(year.year_start_date):
			frappe.throw(_("The start of the term cannot be before the start of the linked academic year. The start of the academic year {0} has been set to {1}.  Please adjust the dates").format(self.academic_year, year.year_start_date))

		# end of term can not be after end of academic year
		if self.term_end_date and getdate(year.year_end_date) and getdate(self.term_end_date) > getdate(year.year_end_date):
			frappe.throw(_("The end of the term cannot be after the end of the linked academic year.  The end of the academic year {0} has been set to {1}. Please adjust the dates.").format(self.academic_year, year.year_end_date))

	def on_update(self):
		if self.term_start_date and self.term_end_date:
			self.create_calendar_events()

	def _sync_school_with_ay(self):
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")

		# 1 ▸ If Term.school is blank → inherit from AY for clarity
		if not self.school:
			self.school = ay_school
			return

		# 2 ▸ If set, it MUST be AY.school itself OR one of its descendants
		ancestors = [self.school] + get_ancestors_of("School", self.school)
		if ay_school not in ancestors:
			frappe.throw(
				_("School {0} is not within the Academic Year’s hierarchy ({1}).")
				.format(self.school, ay_school),
				exc=ParentRuleViolation
			)

	def validate_duplicate(self):
		terms = frappe.qb.DocType("Term")

		# Prevent boolean contamination by explicitly branching
		if self.school:
			# Case: school is defined → match same school
			query = (
				frappe.qb.from_(terms)
				.select(terms.name)
				.where(
					(terms.academic_year == self.academic_year)
					& (terms.term_name == self.term_name)
					& (terms.school == self.school)
					& (terms.name != self.name)
				)
			).run()
		else:
			# Case: school is None → match where school IS NULL
			query = (
				frappe.qb.from_(terms)
				.select(terms.name)
				.where(
					(terms.academic_year == self.academic_year)
					& (terms.term_name == self.term_name)
					& terms.school.isnull()
					& (terms.name != self.name)
				)
			).run()

		if query:
			frappe.throw(
				_("A term with this academic year {0} and this name {1} already exists. Please adjust the name if necessary.").format(
					self.academic_year, self.term_name
				)
			)

	def create_calendar_events(self):
		if self.at_start:
			start_at = frappe.get_doc("School Event", self.at_start)
			if getdate(start_at.starts_on) != getdate(self.term_start_date):
				start_at.db_set("starts_on", self.term_start_date)
				start_at.db_set("ends_on", self.term_start_date)
				frappe.msgprint(_("Date for the start of the term {0} has been updated on the School Event Calendar {1}").format(self.term_start_date, get_link_to_form("School Event", start_at.name)))

		if self.at_end:
			end_at = frappe.get_doc("School Event", self.at_end)
			if getdate(end_at.ends_on) != getdate(self.term_end_date):
				end_at.db_set("starts_on", self.term_end_date)
				end_at.db_set("ends_on", self.term_end_date)
				frappe.msgprint(_("Date for the end of the term {0} has been updated on the School Event Calendar {1}").format(self.term_end_date, get_link_to_form("School Event", end_at.name)))

		if not self.at_start:
			start_term = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"subject": "Start of the " + cstr(self.name) + " Academic Term",
				"starts_on": getdate(self.term_start_date),
				"ends_on": getdate(self.term_start_date),
				"school": self.school if self.school else None,
				"event_category": "Other",
				"event_type": "Public",
				"all_day": "1",
				"color": "#7575ff",
				"reference_type": "Term",
				"reference_name": self.name
			})
			start_term.insert()
			self.db_set("at_start", start_term.name)
			frappe.msgprint(_("Date for the start of the term {0} has been created on the School Event Calendar {1}").format(self.term_start_date, get_link_to_form("School Event", start_term.name)))

		if not self.at_end:
			end_term = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"subject": "End of the " + cstr(self.name) + " Academic Term",
				"starts_on": getdate(self.term_end_date),
				"ends_on": getdate(self.term_end_date),
				"school": self.school if self.school else None,
				"event_category": "Other",
				"event_type": "Public",
				"all_day": "1",
				"color": "#7575ff",
				"reference_type": "Term",
				"reference_name": self.name
			})
			end_term.insert()
			self.db_set("at_end", end_term.name)
			frappe.msgprint(_("Date for the end of the term {0} has been created on the School Event Calendar {1}").format(self.term_end_date, get_link_to_form("School Event", end_term.name)))


def get_schools_per_academic_year_for_terms(user_school):
	"""
	For each academic year, find the first ancestor (including self) that has terms for that AY.
	Return a list of (school, academic_year) tuples.
	"""
	if not user_school:
		return []

	# Get all academic years referenced in the Term table
	academic_years = [row[0] for row in frappe.db.get_values("Term", {}, "academic_year", distinct=True)]
	pairs = set()
	chain = [user_school] + get_ancestors_of("School", user_school)

	for ay in academic_years:
		for sch in chain:
			if frappe.db.exists("Term", {"school": sch, "academic_year": ay}):
				pairs.add((sch, ay))
				break  # Stop at the first ancestor with a term for this AY

	return list(pairs)

def get_current_term(academic_year: str) -> frappe._dict | None:
	"""
	Returns the current active Term for the given academic_year
	(based on today's date falling between term_start_date and term_end_date).
	Returns a frappe._dict with term fields or None if no match.
	"""
	today = getdate(nowdate())

	term = frappe.db.get_value(
		"Term",
		{
			"academic_year": academic_year,
			"term_start_date": ["<=", today],
			"term_end_date": [">=", today],
		},
		["name", "term_start_date", "term_end_date"],
		as_dict=True,
	)

	return term

def get_permission_query_conditions(user):
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return None

	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return "1=0"

	if is_leaf_school(user_school):
		pairs = get_schools_per_academic_year_for_terms(user_school)
		if not pairs:
			return "1=0"
		# Build SQL for pairs
		conditions = [
			"(`tabTerm`.`school` = '{0}' AND `tabTerm`.`academic_year` = '{1}')".format(sch, ay)
			for sch, ay in pairs
		]
		return " OR ".join(conditions)
	else:
		schools = get_descendant_schools(user_school)
		if not schools:
			return "1=0"
		schools_list = "', '".join(schools)
		return f"`tabTerm`.`school` IN ('{schools_list}')"


def has_permission(doc, ptype=None, user=None):
	if not user:
		user = frappe.session.user

	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return False

	if is_leaf_school(user_school):
		pairs = get_schools_per_academic_year_for_terms(user_school)
		return (doc.school, doc.academic_year) in pairs
	else:
		schools = get_descendant_schools(user_school)
		return doc.school in schools

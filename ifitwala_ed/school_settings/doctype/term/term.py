# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/term/term.py

import frappe
from frappe import _
from frappe.utils import getdate, nowdate, cstr, get_link_to_form
from frappe.model.document import Document
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import ParentRuleViolation
from ifitwala_ed.utilities.school_tree import get_descendant_schools, is_leaf_school


class Term(Document):
	# create automatically the name of the term.
	def autoname(self):
		# Do not imply ownership for global terms
		self.name = f"{self.academic_year} {self.term_name}"
		self.title = f"{self.term_name}"

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

		year = frappe.db.get_value(
			"Academic Year",
			self.academic_year,
			["year_start_date", "year_end_date"],
			as_dict=True
		)

		# start of term can not be before start of academic year
		if self.term_start_date and getdate(year.year_start_date) and getdate(self.term_start_date) < getdate(year.year_start_date):
			frappe.throw(
				_("The start of the term cannot be before the start of the linked academic year. "
				  "The start of the academic year {0} has been set to {1}.  Please adjust the dates")
				.format(self.academic_year, year.year_start_date)
			)

		# end of term can not be after end of academic year
		if self.term_end_date and getdate(year.year_end_date) and getdate(self.term_end_date) > getdate(year.year_end_date):
			frappe.throw(
				_("The end of the term cannot be after the end of the linked academic year.  "
				  "The end of the academic year {0} has been set to {1}. Please adjust the dates.")
				.format(self.academic_year, year.year_end_date)
			)

	def on_update(self):
		# Global terms are templates only → no operational side effects
		if not self.school:
			return

		if self.term_start_date and self.term_end_date:
			self.create_calendar_events()

	def _sync_school_with_ay(self):
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")

		# Option B:
		# - Global terms (school is None) remain templates
		# - No auto-inheritance from Academic Year
		if not self.school:
			return

		# If set, it MUST be AY.school itself OR one of its descendants
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
				_("A term with this academic year {0} and this name {1} already exists. "
				  "Please adjust the name if necessary.")
				.format(self.academic_year, self.term_name)
			)

	def create_calendar_events(self):
		# Safety: only school-scoped terms may create events
		if not self.school:
			return

		# Update existing events (dates only)
		if self.at_start:
			start_evt = frappe.get_doc("School Event", self.at_start)
			if getdate(start_evt.starts_on) != getdate(self.term_start_date):
				start_evt.db_set("starts_on", self.term_start_date)
				start_evt.db_set("ends_on", self.term_start_date)
				frappe.msgprint(
					_("Start of term date updated on School Event {0}")
					.format(get_link_to_form("School Event", start_evt.name))
				)

		if self.at_end:
			end_evt = frappe.get_doc("School Event", self.at_end)
			if getdate(end_evt.ends_on) != getdate(self.term_end_date):
				end_evt.db_set("starts_on", self.term_end_date)
				end_evt.db_set("ends_on", self.term_end_date)
				frappe.msgprint(
					_("End of term date updated on School Event {0}")
					.format(get_link_to_form("School Event", end_evt.name))
				)

		# Create missing events (MUST set school + audience)
		if not self.at_start and self.term_start_date:
			start_evt = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"school": self.school,
				"subject": _("Start of {0}").format(self.term_name),
				"starts_on": getdate(self.term_start_date),
				"ends_on": getdate(self.term_start_date),
				"event_category": "Other",
				"all_day": 1,
				"reference_type": "Term",
				"reference_name": self.name,
				"audience": [
					{"audience_type": "Whole School Community"}
				],
			})
			start_evt.flags.ignore_audience_permissions = True
			start_evt.insert(ignore_permissions=True)

			self.db_set("at_start", start_evt.name)
			frappe.msgprint(
				_("Start of term event created: {0}")
				.format(get_link_to_form("School Event", start_evt.name))
			)

		if not self.at_end and self.term_end_date:
			end_evt = frappe.get_doc({
				"doctype": "School Event",
				"owner": frappe.session.user,
				"school": self.school,
				"subject": _("End of {0}").format(self.term_name),
				"starts_on": getdate(self.term_end_date),
				"ends_on": getdate(self.term_end_date),
				"event_category": "Other",
				"all_day": 1,
				"reference_type": "Term",
				"reference_name": self.name,
				"audience": [
					{"audience_type": "Whole School Community"}
				],
			})
			end_evt.flags.ignore_audience_permissions = True
			end_evt.insert(ignore_permissions=True)

			self.db_set("at_end", end_evt.name)
			frappe.msgprint(
				_("End of term event created: {0}")
				.format(get_link_to_form("School Event", end_evt.name))
			)


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

def get_current_term(school: str, academic_year: str) -> frappe._dict | None:
	"""
	Pattern B compliant.

	Return the current active Term for a given (school, academic_year),
	resolved EXCLUSIVELY via the School Calendar.

	- No implicit inheritance
	- No global term activation
	- Calendar is the authority
	"""

	if not school or not academic_year:
		return None

	today = getdate(nowdate())

	# 1 ▸ find the school calendar (must exist explicitly)
	calendar = frappe.db.get_value(
		"School Calendar",
		{
			"school": school,
			"academic_year": academic_year,
			"docstatus": ["<", 2],
		},
		"name",
	)

	if not calendar:
		return None

	# 2 ▸ resolve active term ONLY from calendar terms
	term = frappe.db.get_value(
		"School Calendar Term",
		{
			"parent": calendar,
			"parenttype": "School Calendar",
			"start": ["<=", today],
			"end": [">=", today],
		},
		["term", "start", "end"],
		as_dict=True,
	)

	if not term:
		return None

	return {
		"name": term.term,
		"term_start_date": term.start,
		"term_end_date": term.end,
	}


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

	# superusers
	if user == "Administrator" or "System Manager" in frappe.get_roles(user):
		return True

	# --- ADDED: allow CREATE when user's school is within AY hierarchy ---
	if ptype == "create":
		user_school = frappe.defaults.get_user_default("school", user)
		if not user_school or not doc.academic_year:
			return False

		ay_school = frappe.db.get_value("Academic Year", doc.academic_year, "school")
		if not ay_school:
			return False

		# allow if AY.school is the same as user's school OR one of its ancestors
		ancestors = [user_school] + get_ancestors_of("School", user_school)
		return ay_school in ancestors
	# --- END ADDED ---

	user_school = frappe.defaults.get_user_default("school", user)
	if not user_school:
		return False

	if is_leaf_school(user_school):
		pairs = get_schools_per_academic_year_for_terms(user_school)
		return (doc.school, doc.academic_year) in pairs
	else:
		schools = get_descendant_schools(user_school)
		return doc.school in schools

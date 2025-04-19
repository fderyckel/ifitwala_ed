# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe 
import frappe.defaults
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.cache_manager import clear_defaults_cache
from frappe.contacts.address_and_contact import load_address_and_contact


class School(NestedSet):
	nsm_parent_field = 'parent_school'

	def onload(self):
		load_address_and_contact(self, "school")

	def validate(self):
		self.validate_abbr()
		self.validate_parent_school()

	def on_update(self):
		NestedSet.on_update(self)

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)

	def after_rename(self, olddn, newdn, merge=False):
		frappe.db.set(self, "school_name", newdn)
		clear_defaults_cache()

	def validate_abbr(self):
		if not self.abbr:
			self.abbr = ''.join([c[0] for c in self.school_name.split()]).upper()

		self.abbr = self.abbr.strip()

		if self.get('__islocal') and len(self.abbr) > 5:
			frappe.throw(_("Abbreviation cannot have more than 5 characters"))

		if not self.abbr.strip():
			frappe.throw(_("Abbreviation is mandatory")) 

		### CHANGETO: use frappe.db.exist()
		if frappe.db.sql("""SELECT abbr FROM `tabSchool` WHERE name!=%s AND abbr=%s""", (self.name, self.abbr)):
			frappe.throw(_("Abbreviation {0} is already used for another school.").format(self.abbr))

	def validate_parent_school(self):
		if self.parent_school:
			is_group = frappe.db.get_value('School', self.parent_school, 'is_group')
			if not is_group:
				frappe.throw(_("Parent School must be a group school."))

	## TOTHINK: why would a school need to create a building?  Isn't it what the organization should do?
	## maybe just create an office? 
	def create_default_location(self):
		for loc_detail in [
			{"location_name": self.name, "is_group": 1},
			{"location_name": _("Classroom 1"), "is_group": 0, "location_type": "Classroom"},
			{"location_name": _("Office 1"), "is_group": 0, "location_type": "Office"}]:
			if not frappe.db.exists("Location", "{0} - {1}".format(loc_detail["location_name"], self.abbr)):
				location = frappe.get_doc({
					"doctype": "Location",
					"location_name": loc_detail["location_name"],
					"is_group": loc_detail["is_group"],
					"organization": self.organization,
					"school": self.name,
					"parent_location": "{0} - {1}".format(_("All Locations"), self.abbr) if not loc_detail["is_group"] else "",
					"location_type" : loc_detail["location_type"] if "location_type" in loc_detail else None
				})
			location.flags.ignore_permissions = True
			location.flags.ignore_mandatory = True
			location.insert()

@frappe.whitelist()
def enqueue_replace_abbr(school, old, new):
	kwargs = dict(school=school, old=old, new=new)
	frappe.enqueue('ifitwala_ed.school_settings.doctype.school.school.replace_abbr', **kwargs)


@frappe.whitelist()
def replace_abbr(school, old, new):
	new = new.strip()
	if not new:
		frappe.throw(_("Abbr can not be blank or space"))

	frappe.only_for("System Manager")

	frappe.db.set_value("School", school, "abbr", new)

	def _rename_record(doc):
		parts = doc[0].rsplit(" - ", 1)
		if len(parts) == 1 or parts[1].lower() == old.lower():
			frappe.rename_doc(dt, doc[0], parts[0] + " - " + new)

	def _rename_records(dt):
		# rename is expensive so let's be economical with memory usage
		doc = (d for d in frappe.db.sql("select name from `tab%s` where school=%s" % (dt, '%s'), school))
		for d in doc:
			_rename_record(d)

def get_name_with_abbr(name, school):
	school_abbr = frappe.db.get_value("School", school, "abbr")
	parts = name.split(" - ")
	if parts[-1].lower() != school_abbr.lower():
		parts.append(school_abbr)
	return " - ".join(parts)

@frappe.whitelist()
def get_children(doctype, parent=None, school=None, is_root=False):
	if parent is None or parent == "All Schools":
		parent = ""

	return frappe.db.sql("""
		SELECT
			name as value,
			is_group as expandable
		FROM
			`tab{doctype}` comp
		WHERE
			ifnull(parent_school, "")={parent}
		""".format(
			doctype=doctype,
			parent=frappe.db.escape(parent)
		), as_dict=1)


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args
	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_school == 'All Schools':
		args.parent_school = None

	frappe.get_doc(args).insert()


def get_dashboard_data(doc):
    return {
        "fieldname": "school",
        "transactions": [
            {
                "label": _("Academic"),
                "items": [
                    {
                        "type": "doctype",
                        "name": "Program Enrollment",
                        "filters": {"status": 1}
                    },
                    "Academic Year",
                    "Term",
                    "School Calendar"
                ]
            },
            {
                "label": _("Curriculum"),
                "items": ["Program", "Course"]
            },
            {
                "label": _("Admin"),
                "items": ["Employee"]
            }
        ]
    }

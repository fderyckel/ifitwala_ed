# Copyright (c) 2021, ifitwala and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from six import string_types

import frappe.share

from frappe import _
from frappe.utils import cstr, now_datetime, cint, flt, get_time, get_datetime, get_link_to_form, date_diff, nowdate

from ifitwala_ed.controllers.status_updater import StatusUpdater

class UOMMustBeIntegerError(frappe.ValidationError): pass

class TransactionBase(StatusUpdater):
	def validate_posting_time(self):
		# set Edit Posting Date and Time to 1 while data import
		if frappe.flags.in_import and self.posting_date:
			self.set_posting_time = 1

		if not getattr(self, 'set_posting_time', None):
			now = now_datetime()
			self.posting_date = now.strftime('%Y-%m-%d')
			self.posting_time = now.strftime('%H:%M:%S.%f')
		elif self.posting_time:
			try:
				get_time(self.posting_time)
			except ValueError:
				frappe.throw(_('Invalid Posting Time'))

	def validate_uom_is_integer(self, uom_field, qty_fields):
		validate_uom_is_integer(self, uom_field, qty_fields)

	def validate_with_previous_doc(self, ref):
		self.exclude_fields = ["conversion_factor", "uom"] if self.get('is_return') else []

		for key, val in ref.items():
			is_child = val.get("is_child_table")
			ref_doc = {}
			item_ref_dn = []
			for d in self.get_all_children(self.doctype + " Item"):
				ref_dn = d.get(val["ref_dn_field"])
				if ref_dn:
					if is_child:
						self.compare_values({key: [ref_dn]}, val["compare_fields"], d)
						if ref_dn not in item_ref_dn:
							item_ref_dn.append(ref_dn)
						elif not val.get("allow_duplicate_prev_row_id"):
							frappe.throw(_("Duplicate row {0} with same {1}").format(d.idx, key))
					elif ref_dn:
						ref_doc.setdefault(key, [])
						if ref_dn not in ref_doc[key]:
							ref_doc[key].append(ref_dn)
			if ref_doc:
				self.compare_values(ref_doc, val["compare_fields"])

	def compare_values(self, ref_doc, fields, doc=None):
		for reference_doctype, ref_dn_list in ref_doc.items():
			for reference_name in ref_dn_list:
				prevdoc_values = frappe.db.get_value(reference_doctype, reference_name,
					[d[0] for d in fields], as_dict=1)

				if not prevdoc_values:
					frappe.throw(_("Invalid reference {0} {1}").format(reference_doctype, reference_name))

				for field, condition in fields:
					if prevdoc_values[field] is not None and field not in self.exclude_fields:
						self.validate_value(field, condition, prevdoc_values[field], doc)


	def validate_rate_with_reference_doc(self, ref_details):
		buying_doctypes = ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]

		if self.doctype in buying_doctypes:
			action = frappe.db.get_single_value("Buying Settings", "maintain_same_rate_action")
			settings_doc = "Buying Settings"
		else:
			action = frappe.db.get_single_value("Selling Settings", "maintain_same_rate_action")
			settings_doc = "Selling Settings"

		for ref_dt, ref_dn_field, ref_link_field in ref_details:
			for d in self.get("items"):
				if d.get(ref_link_field):
					ref_rate = frappe.db.get_value(ref_dt + " Item", d.get(ref_link_field), "rate")

					if abs(flt(d.rate - ref_rate, d.precision("rate"))) >= .01:
						if action == "Stop":
							role_allowed_to_override = frappe.db.get_single_value(settings_doc, 'role_to_override_stop_action')

							if role_allowed_to_override not in frappe.get_roles():
								frappe.throw(_("Row #{0}: Rate must be same as {1}: {2} ({3} / {4})").format(
									d.idx, ref_dt, d.get(ref_dn_field), d.rate, ref_rate))
						else:
							frappe.msgprint(_("Row #{0}: Rate must be same as {1}: {2} ({3} / {4})").format(
								d.idx, ref_dt, d.get(ref_dn_field), d.rate, ref_rate), title=_("Warning"), indicator="orange")


	def get_link_filters(self, for_doctype):
		if hasattr(self, "prev_link_mapper") and self.prev_link_mapper.get(for_doctype):
			fieldname = self.prev_link_mapper[for_doctype]["fieldname"]

			values = filter(None, tuple(item.as_dict()[fieldname] for item in self.items))

			if values:
				ret = {
					for_doctype : {
						"filters": [[for_doctype, "name", "in", values]]
					}
				}
			else:
				ret = None
		else:
			ret = None

		return ret



def delete_events(ref_type, ref_name):
	events = frappe.db.sql_list(""" SELECT DISTINCT `tabEvent`.name
        FROM `tabEvent`, `tabEvent Participants`
		WHERE
			`tabEvent`.name = `tabEvent Participants`.parent
			and `tabEvent Participants`.reference_doctype = %s
			and `tabEvent Participants`.reference_docname = %s
		""", (ref_type, ref_name)) or []

	if events:
		frappe.delete_doc("Event", events, for_reload=True)


def validate_uom_is_integer(doc, uom_field, qty_fields, child_dt=None):
	if isinstance(qty_fields, string_types):
		qty_fields = [qty_fields]

	distinct_uoms = list(set(d.get(uom_field) for d in doc.get_all_children()))
	integer_uoms = list(filter(lambda uom: frappe.db.get_value("UOM", uom,
		"must_be_whole_number", cache=True) or None, distinct_uoms))

	if not integer_uoms:
		return

	for d in doc.get_all_children(parenttype=child_dt):
		if d.get(uom_field) in integer_uoms:
			for f in qty_fields:
				qty = d.get(f)
				if qty:
					if abs(cint(qty) - flt(qty)) > 0.0000001:
						frappe.throw(_("Row {1}: Quantity ({0}) cannot be a fraction. To allow this, disable '{2}' in UOM {3}.") \
							.format(qty, d.idx, frappe.bold(_("Must be Whole Number")), frappe.bold(d.get(uom_field))),
								UOMMustBeIntegerError)

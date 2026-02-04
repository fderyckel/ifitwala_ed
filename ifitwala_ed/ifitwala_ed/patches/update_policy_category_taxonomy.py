# ifitwala_ed/patches/update_policy_category_taxonomy.py

import frappe
from frappe import _

from ifitwala_ed.governance.policy_utils import POLICY_CATEGORIES


REMAP_CATEGORIES = {
	"Privacy": "Privacy & Data Protection",
	"Conduct": "Conduct & Behaviour",
	"Handbook": "Handbooks",
}


def execute():
	if not frappe.db.exists("DocType", "Institutional Policy"):
		return

	for old_value, new_value in REMAP_CATEGORIES.items():
		frappe.db.sql(
			"""
			UPDATE `tabInstitutional Policy`
			   SET policy_category = %s
			 WHERE policy_category = %s
			""",
			(new_value, old_value),
		)

	other_rows = frappe.get_all(
		"Institutional Policy",
		filters={"policy_category": "Other"},
		pluck="name",
	)
	if other_rows:
		frappe.throw(
			_(
				"Forbidden policy_category 'Other' found in Institutional Policy records: {0}. "
				"Please recategorize these policies manually before running this migration."
			).format(", ".join(other_rows))
		)

	invalid_rows = frappe.get_all(
		"Institutional Policy",
		filters={"policy_category": ["not in", POLICY_CATEGORIES]},
		fields=["name", "policy_category"],
	)
	if invalid_rows:
		labels = ", ".join(
			f"{row['name']} ({row.get('policy_category') or 'empty'})"
			for row in invalid_rows
		)
		frappe.throw(
			_(
				"Invalid policy_category values found in Institutional Policy records: {0}. "
				"Please recategorize these policies manually before running this migration."
			).format(labels)
		)

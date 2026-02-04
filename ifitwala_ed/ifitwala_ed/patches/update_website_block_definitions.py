# ifitwala_ed/patches/update_website_block_definitions.py

import frappe
from ifitwala_ed.setup.setup import get_website_block_definition_records


def execute():
	records = get_website_block_definition_records()
	fields = [
		"label",
		"template_path",
		"script_path",
		"provider_path",
		"props_schema",
		"seo_role",
		"is_core",
	]

	for record in records:
		block_type = record.get("block_type")
		if not block_type:
			continue

		name = frappe.db.get_value("Website Block Definition", {"block_type": block_type}, "name")
		if name:
			doc = frappe.get_doc("Website Block Definition", name)
			changed = False
			for field in fields:
				if field in record and doc.get(field) != record.get(field):
					doc.set(field, record.get(field))
					changed = True
			if changed:
				doc.save(ignore_permissions=True)
		else:
			doc = frappe.new_doc("Website Block Definition")
			doc.update(record)
			doc.insert(ignore_permissions=True)

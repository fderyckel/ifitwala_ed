# ifitwala_ed/patches/v0_0/remove_legacy_web_pages.py

import frappe

from ifitwala_ed.setup.setup import get_website_block_definition_records


def _seed_block_definitions():
	for record in get_website_block_definition_records():
		block_type = record.get("block_type")
		if not block_type:
			continue
		if frappe.db.exists("Website Block Definition", {"block_type": block_type}):
			continue
		doc = frappe.get_doc(record)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
		frappe.db.commit()


def _delete_all_web_pages():
	names = frappe.get_all("Web Page", pluck="name")
	if not names:
		return

	for idx, name in enumerate(names, start=1):
		frappe.delete_doc("Web Page", name, force=True, ignore_permissions=True)
		if idx % 25 == 0:
			frappe.db.commit()
	frappe.db.commit()


def execute():
	_seed_block_definitions()
	_delete_all_web_pages()

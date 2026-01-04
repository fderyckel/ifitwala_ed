# Copyright (c) 2026
# For license information, please see license.txt

import frappe


def _index_exists(table: str, index_name: str) -> bool:
	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}` WHERE Key_name=%s".format(table),
		(index_name,),
		as_dict=True,
	)
	return bool(rows)


def execute():
	table = "tabLocation Booking"

	# 1) UNIQUE(slot_key)
	# Name it explicitly so we can reliably check presence.
	uniq_name = "uniq_location_booking_slot_key"
	if not _index_exists(table, uniq_name):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{uniq_name}` (`slot_key`)"
		)

	# 2) (location, from_datetime)
	idx_loc_from = "idx_location_booking_location_from"
	if not _index_exists(table, idx_loc_from):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_loc_from}` (`location`, `from_datetime`)"
		)

	# 3) (location, to_datetime)
	idx_loc_to = "idx_location_booking_location_to"
	if not _index_exists(table, idx_loc_to):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_loc_to}` (`location`, `to_datetime`)"
		)

	# 4) (source_doctype, source_name)
	idx_source = "idx_location_booking_source"
	if not _index_exists(table, idx_source):
		frappe.db.sql(
			f"ALTER TABLE `{table}` ADD INDEX `{idx_source}` (`source_doctype`, `source_name`)"
		)

	frappe.db.commit()

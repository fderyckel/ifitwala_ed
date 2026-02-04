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


def _unique_index_exists(table: str, column: str) -> bool:
	rows = frappe.db.sql(
		"SHOW INDEX FROM `{}` WHERE Column_name=%s".format(table),
		(column,),
		as_dict=True,
	)
	for row in rows:
		non_unique = row.get("Non_unique")
		try:
			non_unique = int(non_unique)
		except Exception:
			pass
		if non_unique == 0:
			return True
	return False


def execute():
	table = "tabLocation Booking"

	# 1) UNIQUE(slot_key)
	# Name it explicitly so we can reliably check presence.
	uniq_name = "uniq_location_booking_slot_key"
	if not _unique_index_exists(table, "slot_key"):
		if _index_exists(table, uniq_name):
			frappe.throw(
				"Location Booking slot_key index exists but is not unique. "
				"Migration/installation is broken."
			)
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

	if not _unique_index_exists(table, "slot_key"):
		frappe.throw(
			"Location Booking UNIQUE(slot_key) index missing after migrate. "
			"Migration/installation is broken."
		)

	frappe.db.commit()

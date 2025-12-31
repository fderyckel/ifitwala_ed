# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime


TARGET_GROUP_TO_ROLE = {
	"Whole Staff": "Staff",
	"Academic Staff": "Staff",
	"Support Staff": "Staff",
	"Students": "Students",
	"Guardians": "Guardians",
	"Whole Community": "Community",
}

TARGET_MODES = {"School Scope", "Team", "Student Group"}


def execute():
	logger = frappe.logger("org_comm_audience_migration")

	if not frappe.db.table_exists("Org Communication Audience"):
		logger.info("Org Communication Audience table not found; skipping migration.")
		return

	if not frappe.db.has_column("Org Communication Audience", "target_mode"):
		logger.warning("target_mode column missing; run migrations before this patch.")
		return

	audience_rows = frappe.db.sql(
		"""
		select
			name,
			parent,
			target_group,
			school,
			team,
			student_group,
			target_mode,
			include_descendants
		from `tabOrg Communication Audience`
		""",
		as_dict=True,
	)

	if not audience_rows:
		logger.info("No Org Communication Audience rows found; nothing to migrate.")
		return

	parent_names = {row.parent for row in audience_rows if row.parent}
	parent_school_map = {}
	if parent_names:
		parents = frappe.db.get_all(
			"Org Communication",
			filters={"name": ["in", list(parent_names)]},
			fields=["name", "school"],
		)
		parent_school_map = {p.name: p.school for p in parents}

	audience_names = [row.name for row in audience_rows]
	existing_roles_by_parent = {}
	max_idx_by_parent = {}

	if audience_names and frappe.db.table_exists("Org Communication Audience Recipient"):
		existing = frappe.db.sql(
			"""
			select parent, recipient_role, idx
			from `tabOrg Communication Audience Recipient`
			where parent in %(parents)s
			""",
			{"parents": audience_names},
			as_dict=True,
		)
		for rec in existing:
			parent = rec.parent
			role = (rec.recipient_role or "").strip()
			existing_roles_by_parent.setdefault(parent, set())
			if role:
				existing_roles_by_parent[parent].add(role)
			max_idx_by_parent[parent] = max(max_idx_by_parent.get(parent, 0), rec.idx or 0)

	migrated = 0
	manual = 0
	to_insert = []
	now_ts = now_datetime()
	user = frappe.session.user if frappe.session and frappe.session.user else "Administrator"

	for row in audience_rows:
		row_updated = False
		row_migrated = False
		row_manual = False

		target_mode_original = (row.target_mode or "").strip()
		target_mode = target_mode_original

		if not target_mode:
			if row.team:
				target_mode = "Team"
			elif row.student_group:
				target_mode = "Student Group"
			else:
				target_mode = "School Scope"
			row_updated = True

		if target_mode and target_mode not in TARGET_MODES:
			row_manual = True

		school_value = row.school
		include_descendants_value = row.include_descendants

		if target_mode == "School Scope":
			if not school_value:
				parent_school = parent_school_map.get(row.parent)
				if parent_school:
					school_value = parent_school
					row_updated = True
				else:
					row_manual = True

			if not target_mode_original and include_descendants_value in (None, "", 0):
				include_descendants_value = 1
				row_updated = True

		if row_updated:
			frappe.db.sql(
				"""
				update `tabOrg Communication Audience`
				set target_mode=%s, school=%s, include_descendants=%s
				where name=%s
				""",
				(
					target_mode,
					school_value,
					1 if include_descendants_value in (1, "1", True) else 0,
					row.name,
				),
			)
			row_migrated = True

		mapped_role = TARGET_GROUP_TO_ROLE.get((row.target_group or "").strip())
		existing_roles = existing_roles_by_parent.get(row.name, set())
		if mapped_role:
			if mapped_role not in existing_roles:
				idx = max_idx_by_parent.get(row.name, 0) + 1
				max_idx_by_parent[row.name] = idx
				to_insert.append({
					"name": frappe.generate_hash(length=10),
					"parent": row.name,
					"parenttype": "Org Communication Audience",
					"parentfield": "recipients",
					"idx": idx,
					"recipient_role": mapped_role,
					"docstatus": 0,
					"creation": now_ts,
					"modified": now_ts,
					"owner": user,
					"modified_by": user,
				})
				existing_roles.add(mapped_role)
				existing_roles_by_parent[row.name] = existing_roles
				row_migrated = True
		else:
			if not existing_roles:
				row_manual = True

		if row_migrated:
			migrated += 1
		if row_manual:
			manual += 1

	if to_insert:
		if not frappe.db.table_exists("Org Communication Audience Recipient"):
			logger.warning(
				"Org Communication Audience Recipient table not found; skipping recipient inserts."
			)
		else:
			frappe.db.bulk_insert(
				doctype="Org Communication Audience Recipient",
				fields=list(to_insert[0].keys()),
				values=[list(r.values()) for r in to_insert],
				ignore_duplicates=True,
			)

	logger.info(
		"Org Communication audience migration complete. Migrated rows: {migrated}. "
		"Manual review needed: {manual}."
		.format(migrated=migrated, manual=manual)
	)

# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe


TARGET_GROUP_TO_TOGGLE = {
	"Whole Staff": "to_staff",
	"Academic Staff": "to_staff",
	"Support Staff": "to_staff",
	"Students": "to_students",
	"Guardians": "to_guardians",
	"Whole Community": "to_community",
}

TARGET_MODES = {"School Scope", "Team", "Student Group"}
TOGGLE_FIELDS = ("to_staff", "to_students", "to_guardians", "to_community")


def _as_bool(value) -> bool:
	return value in (1, "1", True)


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
			include_descendants,
			to_staff,
			to_students,
			to_guardians,
			to_community
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

	migrated = 0
	manual = 0

	for row in audience_rows:
		row_updates = {}
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
			row_updates["target_mode"] = target_mode

		if target_mode and target_mode not in TARGET_MODES:
			row_manual = True

		school_value = row.school
		include_descendants_value = row.include_descendants

		if target_mode == "School Scope":
			if not school_value:
				parent_school = parent_school_map.get(row.parent)
				if parent_school:
					school_value = parent_school
					row_updates["school"] = school_value
				else:
					row_manual = True

			if not target_mode_original and include_descendants_value in (None, "", 0):
				row_updates["include_descendants"] = 1

		mapped_toggle = TARGET_GROUP_TO_TOGGLE.get((row.target_group or "").strip())
		current_toggles = {field: _as_bool(row.get(field)) for field in TOGGLE_FIELDS}
		has_any_toggle = any(current_toggles.values())

		if mapped_toggle and not has_any_toggle:
			row_updates[mapped_toggle] = 1
		elif not mapped_toggle and not has_any_toggle:
			row_manual = True

		if row_updates:
			frappe.db.sql(
				"""
				update `tabOrg Communication Audience`
				set
					target_mode=%(target_mode)s,
					school=%(school)s,
					include_descendants=%(include_descendants)s,
					to_staff=%(to_staff)s,
					to_students=%(to_students)s,
					to_guardians=%(to_guardians)s,
					to_community=%(to_community)s
				where name=%(name)s
				""",
				{
					"name": row.name,
					"target_mode": row_updates.get("target_mode", row.target_mode),
					"school": row_updates.get("school", row.school),
					"include_descendants": row_updates.get(
						"include_descendants", row.include_descendants
					),
					"to_staff": row_updates.get("to_staff", row.to_staff),
					"to_students": row_updates.get("to_students", row.to_students),
					"to_guardians": row_updates.get("to_guardians", row.to_guardians),
					"to_community": row_updates.get("to_community", row.to_community),
				},
			)
			row_migrated = True

		if row_migrated:
			migrated += 1
		if row_manual:
			manual += 1

	logger.info(
		"Org Communication audience migration complete. Migrated rows: {migrated}. "
		"Manual review needed: {manual}."
		.format(migrated=migrated, manual=manual)
	)

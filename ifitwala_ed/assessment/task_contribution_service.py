# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def mark_contributions_stale(outcome_id, latest_submission_id=None):
	if not outcome_id:
		return 0

	clauses = ["task_outcome = %(outcome)s", "is_stale = 0"]
	params = {"outcome": outcome_id}
	if latest_submission_id:
		clauses.append("task_submission != %(submission)s")
		params["submission"] = latest_submission_id

	query = f"""
		UPDATE `tabTask Contribution`
		SET is_stale = 1, modified = NOW(), modified_by = %(user)s
		WHERE {' AND '.join(clauses)}
	"""
	params["user"] = frappe.session.user or "Administrator"
	frappe.db.sql(query, params)
	return frappe.db.rowcount


def get_latest_submission_version(outcome_id):
	if not outcome_id:
		frappe.throw(_("Task Outcome is required."))

	version = frappe.db.get_value(
		"Task Submission",
		{"task_outcome": outcome_id},
		"max(version)",
	)
	try:
		return int(version or 0)
	except Exception:
		return 0


def get_submission_version(submission_id):
	if not submission_id:
		return 0
	version = frappe.db.get_value("Task Submission", submission_id, "version")
	try:
		return int(version or 0)
	except Exception:
		return 0

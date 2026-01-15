# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/focus.py

import frappe
from frappe import _

STUDENT_LOG_DOCTYPE = "Student Log"
FOLLOW_UP_DOCTYPE = "Student Log Follow Up"

ACTION_MODE = {
	"student_log.follow_up.act.submit": "assignee",
	"student_log.follow_up.review.decide": "author",
}


def _parse_focus_item_id(focus_item_id: str) -> dict:
	parts = (focus_item_id or "").split("::")
	if len(parts) != 5:
		frappe.throw(_("Invalid focus item id."), frappe.ValidationError)

	workflow, reference_doctype, reference_name, action_type, user = parts
	return {
		"workflow": workflow,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"action_type": action_type,
		"user": user,
	}


def _resolve_mode(action_type: str | None, log_doc) -> str:
	if action_type:
		mode = ACTION_MODE.get(action_type)
		if not mode:
			frappe.throw(_("Unknown Student Log action type."), frappe.ValidationError)
		return mode

	if log_doc.follow_up_person and log_doc.follow_up_person == frappe.session.user:
		return "assignee"

	return "author"


@frappe.whitelist()
def get_context(
	focus_item_id: str | None = None,
	reference_doctype: str | None = None,
	reference_name: str | None = None,
):
	action_type = None
	if focus_item_id:
		parsed = _parse_focus_item_id(focus_item_id)
		reference_doctype = parsed["reference_doctype"]
		reference_name = parsed["reference_name"]
		action_type = parsed["action_type"]

	if not reference_doctype or not reference_name:
		frappe.throw(_("Missing reference info."), frappe.ValidationError)

	if reference_doctype != STUDENT_LOG_DOCTYPE:
		frappe.throw(_("Only Student Log focus items are supported."), frappe.ValidationError)

	log_doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, reference_name)
	if not frappe.has_permission(STUDENT_LOG_DOCTYPE, doc=log_doc, ptype="read"):
		frappe.throw(_("You are not permitted to view this log."), frappe.PermissionError)

	mode = _resolve_mode(action_type, log_doc)

	follow_up_rows = frappe.get_all(
		FOLLOW_UP_DOCTYPE,
		filters={"student_log": reference_name},
		fields=["name", "date", "follow_up_author", "follow_up", "docstatus"],
		order_by="modified desc",
		limit_page_length=20,
	)

	follow_ups = []
	for row in follow_up_rows:
		follow_ups.append(
			{
				"name": row.get("name"),
				"date": str(row.get("date")) if row.get("date") else None,
				"follow_up_author": row.get("follow_up_author"),
				"follow_up_html": row.get("follow_up") or "",
				"docstatus": row.get("docstatus"),
			}
		)

	return {
		"focus_item_id": focus_item_id,
		"reference_doctype": STUDENT_LOG_DOCTYPE,
		"reference_name": reference_name,
		"mode": mode,
		"log": {
			"name": log_doc.name,
			"student_name": log_doc.student_name,
			"log_type": log_doc.log_type,
			"date": str(log_doc.date) if log_doc.date else None,
			"follow_up_status": log_doc.follow_up_status,
			"log_html": log_doc.log or "",
		},
		"follow_ups": follow_ups,
	}

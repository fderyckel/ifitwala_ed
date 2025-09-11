# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from typing import List
import frappe
from frappe.utils import now_datetime

def mark_read(user: str, ref_dt: str, ref_dn: str):
	try:
		frappe.get_doc({
			"doctype": "Portal Read Receipt",
			"user": user,
			"reference_doctype": ref_dt,
			"reference_name": ref_dn,
			"read_at": now_datetime()
		}).insert(ignore_permissions=True)
	except frappe.UniqueValidationError:
		pass

def unread_names_for(user: str, ref_dt: str, names: List[str]) -> List[str]:
	if not names:
		return []
	seen = frappe.db.get_values(
		"Portal Read Receipt",
		{"user": user, "reference_doctype": ref_dt, "reference_name": ["in", names]},
		["reference_name"], as_dict=True
	)
	seen_set = {r["reference_name"] for r in seen}
	return [n for n in names if n not in seen_set]

# ifitwala_ed/students/api/portal_referral.py

import frappe
from frappe import _
from frappe.utils import now_datetime, add_to_date, today

# v15 helper to create Notification Log entries (bell)
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

COUNSELOR_ROLE = "Counselor"
DOC = "Student Referral"


def _linked_student_for(user: str) -> str | None:
	# Match Student by login email → Student.student_email
	return frappe.db.get_value("Student", {"student_email": user}, "name")


def _latest_active_program_enrollment(student: str) -> dict | None:
	# Prefer newest AY, then most recent creation. Avoid heavy joins.
	rows = frappe.db.get_all(
		"Program Enrollment",
		filters={"student": student, "archived": 0},
		fields=["name", "program", "academic_year", "school"],
		order_by="academic_year desc, creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def _settings() -> dict:
	# Single fetch; keep it light
	doc = frappe.get_cached_doc("Referral Settings")  # cached single
	return {
		"default_conf": getattr(doc, "default_confidentiality_for_self_referral", None) or "Restricted",
		"sla_hours_new_to_triaged": int(getattr(doc, "sla_hours_new_to_triaged", 24) or 24),
	}


def _compute_sla_due(hours: int) -> str:
	return add_to_date(now_datetime(), hours=hours)


def _counselor_users() -> list[str]:
	# Get enabled Users who have the Counselor role
	user_ids = frappe.db.get_all(
		"Has Role",
		filters={"role": COUNSELOR_ROLE, "parenttype": "User"},
		pluck="parent",
	)
	if not user_ids:
		return []
	enabled = frappe.db.get_all(
		"User",
		filters={"name": ["in", user_ids], "enabled": 1},
		pluck="name",
	)
	return enabled


def _notify_counselors(docname: str):
	recipients = _counselor_users()
	if not recipients:
		return
	subject = _("New self-referral submitted")
	message = _("A new student self-referral was submitted and needs triage.")
	enqueue_create_notification(
		recipients=recipients,
		subject=subject,
		message=message,
		reference_doctype=DOC,
		reference_name=docname,
	)


@frappe.whitelist(allow_guest=False)
def create_self_referral(**kwargs):
	"""
	Create a Student Referral from the portal wizard.
	Expected kwargs: referral_category, severity, referral_description,
	optional: preferred_contact_method, ok_to_contact_guardians, safe_times_to_contact,
	optional (Phase 1b): reporting_for_other, subject_student
	"""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	if "Student" not in roles:
		frappe.throw(_("Only logged-in students can submit this form."), frappe.PermissionError)

	student = _linked_student_for(user)
	if not student:
		frappe.throw(_("We couldn't find a Student profile linked to your account."))

	# Resolve latest active Program Enrollment (if any)
	pe = _latest_active_program_enrollment(student)

	# Settings
	cfg = _settings()
	sla_due = _compute_sla_due(cfg["sla_hours_new_to_triaged"])

	# Collect & sanitize inputs (keep it simple; wizard already gates length)
	referral_category = (kwargs.get("referral_category") or "").strip()
	severity = (kwargs.get("severity") or "").strip()
	desc = (kwargs.get("referral_description") or "").strip()

	if not (referral_category and severity and len(desc) >= 10):
		frappe.throw(_("Please complete the required fields before submitting."))

	# Optional portal fields
	pref_contact = (kwargs.get("preferred_contact_method") or "").strip() or None
	ok_guardians = 1 if str(kwargs.get("ok_to_contact_guardians", "0")) in ("1", "true", "True") else 0
	safe_times = (kwargs.get("safe_times_to_contact") or "").strip() or None

	# Phase 1b placeholders (ignored if not provided)
	reporting_for_other = 1 if str(kwargs.get("reporting_for_other", "0")) in ("1", "true", "True") else 0
	subject_student = (kwargs.get("subject_student") or "").strip() or None

	# Prepare insert (bypass perms after strong checks above)
	ref = frappe.new_doc(DOC)
	ref.update({
		"student": student,
		"date": today(),
		"referral_source": "Student (Self)",
		"referrer": user,
		"referral_category": referral_category,
		"severity": severity,
		"referral_description": desc,
		"confidentiality_level": cfg["default_conf"],
		"portal_submission_channel": "Portal",
		"sla_due": sla_due,
	})

	# Attach PE-derived context if available
	if pe:
		ref.update({
			"program_enrollment": pe.get("name"),
			"program": pe.get("program"),
			"academic_year": pe.get("academic_year"),
			"school": pe.get("school"),
		})

	# Optional portal fields into doc (fields you added in Step 1)
	if pref_contact:
		ref.preferred_contact_method = pref_contact
	ref.ok_to_contact_guardians = ok_guardians
	if safe_times:
		ref.safe_times_to_contact = safe_times

	# Phase 1b fields (won't break if not present yet)
	if reporting_for_other:
		try:
			ref.reporting_for_other = 1
			if subject_student:
				ref.subject_student = subject_student
		except Exception:
			# Field may not exist yet; ignore silently for MVP
			pass

	# Insert ignoring perms (students may not have Create on this doctype)
	ref.insert(ignore_permissions=True)

	# Notify Counselor role only
	_notify_counselors(ref.name)

	return {"name": ref.name}

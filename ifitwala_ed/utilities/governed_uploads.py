# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/governed_uploads.py

from __future__ import annotations

from typing import Tuple
import json

import frappe
from frappe import _

from ifitwala_ed.utilities import file_dispatcher


def _get_uploaded_file() -> Tuple[str, bytes]:
	if not frappe.request:
		frappe.throw(_("No request context for upload."))

	uploaded = frappe.request.files.get("file")
	if not uploaded:
		frappe.throw(_("No file uploaded."))

	filename = uploaded.filename or uploaded.name
	content = uploaded.stream.read()
	if not content:
		frappe.throw(_("Uploaded file is empty."))

	return filename, content


def _require_doc(doctype: str, name: str):
	if not name:
		frappe.throw(_("Missing document name."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	return doc


def _get_org_from_school(school: str) -> str:
	if not school:
		frappe.throw(_("School is required for this upload."))
	organization = frappe.db.get_value("School", school, "organization")
	if not organization:
		frappe.throw(_("Organization is required for file classification."))
	return organization


def _get_form_arg(key: str):
	value = frappe.form_dict.get(key)
	if value:
		return value

	args = frappe.form_dict.get("args")
	if not args:
		return None

	if isinstance(args, str):
		try:
			args = json.loads(args)
		except Exception:
			return None

	if isinstance(args, dict):
		return args.get(key)

	return None


def _response_payload(file_doc):
	return {
		"file": file_doc.name,
		"file_url": file_doc.file_url,
		"file_name": file_doc.file_name,
		"file_size": file_doc.file_size,
	}


@frappe.whitelist()
def upload_employee_image(employee: str | None = None):
	employee = employee or _get_form_arg("employee")
	doc = _require_doc("Employee", employee)
	if not doc.organization:
		frappe.throw(_("Organization is required for file classification."))

	filename, content = _get_uploaded_file()

	file_doc = file_dispatcher.create_and_classify_file(
		file_kwargs={
			"attached_to_doctype": "Employee",
			"attached_to_name": doc.name,
			"attached_to_field": "employee_image",
			"file_name": filename,
			"content": content,
			"is_private": 0,
		},
		classification={
			"primary_subject_type": "Employee",
			"primary_subject_id": doc.name,
			"data_class": "identity_image",
			"purpose": "employee_profile_display",
			"retention_policy": "employment_duration_plus_grace",
			"slot": "profile_image",
			"organization": doc.organization,
			"school": doc.school,
			"upload_source": "Desk",
		},
	)

	frappe.db.set_value("Employee", doc.name, "employee_image", file_doc.file_url, update_modified=False)
	return _response_payload(file_doc)


@frappe.whitelist()
def upload_student_image(student: str | None = None):
	student = student or _get_form_arg("student")
	doc = _require_doc("Student", student)
	if not doc.anchor_school:
		frappe.throw(_("Anchor School is required before uploading a student image."))

	organization = _get_org_from_school(doc.anchor_school)
	filename, content = _get_uploaded_file()

	file_doc = file_dispatcher.create_and_classify_file(
		file_kwargs={
			"attached_to_doctype": "Student",
			"attached_to_name": doc.name,
			"attached_to_field": "student_image",
			"file_name": filename,
			"content": content,
			"is_private": 0,
		},
		classification={
			"primary_subject_type": "Student",
			"primary_subject_id": doc.name,
			"data_class": "identity_image",
			"purpose": "student_profile_display",
			"retention_policy": "until_school_exit_plus_6m",
			"slot": "profile_image",
			"organization": organization,
			"school": doc.anchor_school,
			"upload_source": "Desk",
		},
	)

	frappe.db.set_value("Student", doc.name, "student_image", file_doc.file_url, update_modified=False)
	doc.student_image = file_doc.file_url
	doc.sync_student_contact_image()
	return _response_payload(file_doc)


@frappe.whitelist()
def upload_applicant_image(student_applicant: str | None = None):
	student_applicant = student_applicant or _get_form_arg("student_applicant")
	doc = _require_doc("Student Applicant", student_applicant)
	if not doc.organization or not doc.school:
		frappe.throw(_("Organization and School are required for file classification."))

	filename, content = _get_uploaded_file()

	file_doc = file_dispatcher.create_and_classify_file(
		file_kwargs={
			"attached_to_doctype": "Student Applicant",
			"attached_to_name": doc.name,
			"attached_to_field": "applicant_image",
			"file_name": filename,
			"content": content,
			"is_private": 1,
		},
		classification={
			"primary_subject_type": "Student Applicant",
			"primary_subject_id": doc.name,
			"data_class": "identity_image",
			"purpose": "applicant_profile_display",
			"retention_policy": "until_school_exit_plus_6m",
			"slot": "profile_image",
			"organization": doc.organization,
			"school": doc.school,
			"upload_source": "Desk",
		},
	)

	frappe.db.set_value("Student Applicant", doc.name, "applicant_image", file_doc.file_url, update_modified=False)
	return _response_payload(file_doc)


@frappe.whitelist()
def upload_task_submission_attachment(task_submission: str | None = None):
	task_submission = task_submission or _get_form_arg("task_submission")
	doc = _require_doc("Task Submission", task_submission)
	if not doc.school or not doc.student:
		frappe.throw(_("Student and School are required for file classification."))

	organization = _get_org_from_school(doc.school)
	filename, content = _get_uploaded_file()

	file_doc = file_dispatcher.create_and_classify_file(
		file_kwargs={
			"attached_to_doctype": "Task Submission",
			"attached_to_name": doc.name,
			"file_name": filename,
			"content": content,
			"is_private": 1,
		},
		classification={
			"primary_subject_type": "Student",
			"primary_subject_id": doc.student,
			"data_class": "academic",
			"purpose": "assessment_submission",
			"retention_policy": "until_program_end_plus_1y",
			"slot": "submission",
			"organization": organization,
			"school": doc.school,
			"upload_source": "Desk",
		},
	)

	doc.append("attachments", {
		"section_break_sbex": file_doc.file_name,
		"file": file_doc.file_url,
		"file_name": file_doc.file_name,
		"file_size": file_doc.file_size,
		"public": 0,
	})
	doc.save(ignore_permissions=True)

	return _response_payload(file_doc)


@frappe.whitelist()
def get_governed_status(doctype: str, name: str, fieldname: str | None = None):
	if not doctype or not name:
		frappe.throw(_("doctype and name are required."))

	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	filters = {
		"attached_to_doctype": doctype,
		"attached_to_name": name,
	}
	if fieldname:
		filters["attached_to_field"] = fieldname

	file_name = frappe.db.get_value("File", filters, "name")
	if not file_name:
		return {"has_file": 0, "governed": 0}

	classification = frappe.db.get_value("File Classification", {"file": file_name}, "name")
	return {
		"has_file": 1,
		"file": file_name,
		"classification": classification,
		"governed": 1 if classification else 0,
	}

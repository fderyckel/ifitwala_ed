# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/file_management.py

from __future__ import annotations

import hashlib
import os
import re
from typing import Dict, Any, Optional, Tuple

import frappe
from frappe import _

# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
	"""Lowercase, replace non-alphanums with '_', strip extra."""
	return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def calculate_hash(file_doc) -> Optional[str]:
	"""
	Return SHA-256 hash for the File's stored content.

	Policy (authoritative):
	- Hashing is best-effort.
	- Public / URL-based or not-yet-materialized files must NOT block saves.
	- Return None when hash cannot be computed yet.
	"""
	if not file_doc:
		frappe.throw(_("File is required for hash computation."))

	file_url = (file_doc.file_url or "").strip()
	if not file_url:
		return None

	# Remote URLs are not hashable here (no disk access)
	if file_url.startswith("http"):
		return None

	rel_path = file_url.lstrip("/")
	abs_path = frappe.utils.get_site_path(rel_path)

	# Disk file may not exist at save-time (Attach Image timing, public files, etc.)
	if not os.path.exists(abs_path):
		frappe.logger().info(
			f"[file_management] File not on disk yet; hash deferred: file={file_doc.name} url={file_url}"
		)
		return None

	digest = hashlib.sha256()
	with open(abs_path, "rb") as handle:
		for chunk in iter(lambda: handle.read(8192), b""):
			digest.update(chunk)

	return digest.hexdigest()


def get_settings():
	"""Fetch File Management Settings (single)."""
	try:
		return frappe.get_single("File Management Settings")
	except Exception:
		# Fail-safe: minimal defaults so dev site still works
		class Dummy:
			admissions_root = "Home/Admissions"
			students_root = "Home/Students"
			meetings_root = "Home/Meetings"
			staff_root = "Home/Staff"
			archive_root = "Home/Archive"
			enable_versioning = 1
		return Dummy()


def ensure_folder(path: str) -> str:
	"""
	Ensure a File folder hierarchy exists under 'Home/...'.
	Returns the final folder path usable in File.folder (e.g. 'Home/Admissions/Applicant/SA-2025-0001').
	"""
	if not path.startswith("Home/"):
		frappe.throw(_("Folder path must start with 'Home/' (got: {0})").format(path))

	# Normalize accidental double-home paths like "Home/Home/..."
	while path.startswith("Home/Home/"):
		path = "Home/" + path[len("Home/Home/"):]

	parts = path.split("/")
	current = "Home"

	# ensure root Home exists
	if not frappe.db.exists("File", {"file_name": "Home", "is_folder": 1, "folder": ""}):
		frappe.get_doc(
			{"doctype": "File", "file_name": "Home", "is_folder": 1, "folder": ""}
		).insert(ignore_permissions=True)

	for part in parts[1:]:
		if part == "Home":
			continue
		next_folder = f"{current}/{part}"
		if not frappe.db.exists("File", {"file_name": part, "is_folder": 1, "folder": current}):
			frappe.get_doc(
				{"doctype": "File", "file_name": part, "is_folder": 1, "folder": current}
			).insert(ignore_permissions=True)
		current = next_folder

	return current  # e.g. 'Home/Admissions/Applicant/SA-2025-0001'


def _get_parent_doc(file_doc) -> Optional[frappe.model.document.Document]:
	"""Fetch the document this File is attached to, if any."""
	if not (file_doc.attached_to_doctype and file_doc.attached_to_name):
		return None
	if not frappe.db.exists(file_doc.attached_to_doctype, file_doc.attached_to_name):
		return None
	return frappe.get_doc(file_doc.attached_to_doctype, file_doc.attached_to_name)


def validate_admissions_attachment(doc, method: Optional[str] = None):
	"""Block direct attachments on Student Applicant except applicant_image."""
	if getattr(doc, "is_folder", 0):
		return
	if not doc.is_new():
		return

	if _is_governed_upload(doc):
		return

	# Hard gate: governed doctypes must use dispatcher uploads.
	if doc.attached_to_doctype in {"Employee", "Student", "Student Applicant", "Task Submission"}:
		action_map = {
			("Employee", "employee_image"): _("Upload Employee Image"),
			("Student", "student_image"): _("Upload Student Image"),
			("Student Applicant", "applicant_image"): _("Upload Applicant Image"),
		}
		action = action_map.get((doc.attached_to_doctype, doc.attached_to_field))
		if doc.attached_to_doctype == "Task Submission":
			action = _("Upload Submission Attachment")
		if not action:
			action = _("the governed upload action")

		frappe.throw(
			_("Governed upload required for {0}. Use {1}.")
			.format(doc.attached_to_doctype, action)
		)

	if doc.attached_to_doctype != "Student Applicant":
		return
	if doc.attached_to_field == "applicant_image":
		return
	frappe.throw(
		_("Admissions files must be attached to Applicant Document (only applicant_image is allowed on Student Applicant).")
	)


def _is_governed_upload(file_doc) -> bool:
	if getattr(file_doc.flags, "governed_upload", False):
		return True

	method = (frappe.form_dict or {}).get("method")
	if method and method.startswith("ifitwala_ed.utilities.governed_uploads."):
		return True

	return False


# ────────────────────────────────────────────────────────────────────────────
# Versioning
# ────────────────────────────────────────────────────────────────────────────

def _compute_slot_key(file_doc, context: Dict[str, Any]) -> Tuple[str, str, str, str]:
	"""
	Compute a logical 'slot' for versioning.
	Slot key = (doctype, name, file_category, logical_key).
	"""
	file_category = context.get("file_category") or "Generic"
	logical_key = context.get("logical_key") or "default"

	return (
		file_doc.attached_to_doctype,
		file_doc.attached_to_name,
		file_category,
		logical_key,
	)


def _get_next_version(slot: Tuple[str, str, str, str]) -> int:
	"""Return next version number for the given slot (using custom_version_no)."""
	doctype, name, file_category, logical_key = slot

	rows = frappe.db.get_all(
		"File",
		fields=["max(custom_version_no) as max_ver"],
		filters={
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"custom_file_category": file_category,
			"custom_logical_key": logical_key,
		},
	)

	max_ver = 0
	if rows and rows[0].get("max_ver") is not None:
		max_ver = int(rows[0]["max_ver"])

	return max_ver + 1




def _mark_other_versions_not_latest(file_doc, slot: Tuple[str, str, str, str]):
	"""Ensure only the newest File is marked custom_is_latest for this slot."""
	doctype, name, file_category, logical_key = slot
	frappe.db.sql(
		"""
		UPDATE `tabFile`
		SET custom_is_latest = 0
		WHERE attached_to_doctype = %s
		  AND attached_to_name = %s
		  AND custom_file_category = %s
		  AND custom_logical_key = %s
		  AND name != %s
		""",
		(
			doctype,
			name,
			file_category,
			logical_key,
			file_doc.name,
		),
	)



# ────────────────────────────────────────────────────────────────────────────
# Context resolution (where to put the file)
# ────────────────────────────────────────────────────────────────────────────

def _context_from_parent_method(parent, file_doc) -> Optional[Dict[str, Any]]:
	"""
	If parent doc has get_file_routing_context(file_doc), use it.
	This is the preferred, doctype-specific way.
	"""
	get_ctx = getattr(parent, "get_file_routing_context", None)
	if callable(get_ctx):
		ctx = get_ctx(file_doc)
		if ctx and isinstance(ctx, dict):
			return ctx
	return None


def _generic_context_from_doctype(parent, file_doc, settings) -> Dict[str, Any]:
	"""
	Fallback mapping by attached_to_doctype when the parent doesn't define
	get_file_routing_context().
	You can extend this mapping over time.
	"""
	dt = file_doc.attached_to_doctype

	# Admissions
	if dt in ("Inquiry", "Student Applicant"):
		root = settings.admissions_root or "Home/Admissions"
		if dt == "Inquiry":
			sub = f"Inquiry/{parent.name}"
			file_category = "Admissions Inquiry"
		else:
			sub = f"Applicant/{parent.name}"
			file_category = "Admissions Applicant"

		return {
			"root_folder": root,
			"subfolder": sub,  # relative to root after 'Home/'
			"file_category": file_category,
			"logical_key": "default",
		}

	# Student-centric doctypes
	if dt in ("Student", "Student Portfolio", "Task Submission"):
		root = settings.students_root or "Home/Students"
		student = getattr(parent, "student", None) or getattr(parent, "name", None)
		if not student:
			frappe.throw(_("Cannot determine student for file routing."))

		if dt == "Student":
			sub = f"{student}/Profile"
			file_category = "Student Profile"
			logical_key = "profile_image"
		elif dt == "Student Portfolio":
			sub = f"{student}/Portfolio"
			file_category = "Student Portfolio"
			logical_key = f"portfolio_{parent.name}"
		else:  # Task Submission
			task_name = getattr(parent, "task", parent.name)
			return build_task_submission_context(
				student=student,
				task_name=task_name,
				settings=settings,
			)

		return {
			"root_folder": root,
			"subfolder": sub,
			"file_category": file_category,
			"logical_key": logical_key,
		}

	# Meetings
	if dt == "Meeting":
		root = settings.meetings_root or "Home/Meetings"
		sub = parent.name
		return {
			"root_folder": root,
			"subfolder": sub,
			"file_category": "Meeting Attachment",
			"logical_key": "default",
		}

	# Generic fallback: Home/<Doctype>/<name>
	root = "Home"
	sub = f"{dt}/{parent.name}"
	return {
		"root_folder": root,
		"subfolder": sub,
		"file_category": dt,
		"logical_key": "default",
	}


def _build_full_folder_path(context: Dict[str, Any]) -> str:
	"""
	Combine root + subfolder into a File.folder string:
	Example:
	  root_folder: 'Home/Admissions'
	  subfolder: 'Applicant/SA-2025-0001'
	→ 'Home/Admissions/Applicant/SA-2025-0001'
	"""
	root = context.get("root_folder") or "Home"
	sub = context.get("subfolder") or ""
	if sub:
		if root.endswith("/"):
			root = root.rstrip("/")
		return f"{root}/{sub}"
	return root


def build_task_submission_context(*, student: str, task_name: str, settings=None) -> Dict[str, Any]:
	"""Build deterministic routing context for Task Submission uploads."""
	if not student:
		frappe.throw(_("Cannot determine student for file routing."))
	settings = settings or get_settings()
	root = settings.students_root or "Home/Students"
	sub = f"{student}/Tasks/Task-{task_name}"
	return {
		"root_folder": root,
		"subfolder": sub,
		"file_category": "Task Submission",
		"logical_key": f"task_{task_name}",
	}


# ────────────────────────────────────────────────────────────────────────────
# Main entrypoint for File hooks
# ────────────────────────────────────────────────────────────────────────────

def route_uploaded_file(doc, method: Optional[str] = None, context_override: Optional[Dict[str, Any]] = None):
	"""
	DocEvent hook for File.after_insert/on_update.
	Decides where the file should live, sets versioning metadata, and renames/moves it.
	"""

	# ── HARD GDPR GATE ──────────────────────────────────────────────
	if not frappe.db.exists(
		"File Classification",
		{"file": doc.name},
	):
		# File exists but has no governance.
		# Do NOT route, version, rename, or finalize.
		return

	# Skip if not attached to any doc
	if not (doc.attached_to_doctype and doc.attached_to_name):
		return

	# Skip URL-only links (Google Drive, etc.)
	if not doc.file_url or doc.file_url.startswith("http"):
		return

	# OPTIONAL: if already under a Home-based folder and has custom_version_no, we can skip
	meta = doc.meta
	if doc.folder and doc.folder.startswith("Home/") and meta.has_field("custom_version_no"):
		if getattr(doc, "custom_version_no", None):
			return

	settings = get_settings()

	if context_override is not None:
		if not isinstance(context_override, dict):
			frappe.throw(_("Invalid routing context override."))
		context = context_override
	else:
		parent = _get_parent_doc(doc)
		if not parent:
			return
		# Get context: first from parent method, then generic mapping
		context = _context_from_parent_method(parent, doc)
		if not context:
			context = _generic_context_from_doctype(parent, doc, settings)

	# Ensure folder exists
	folder_path = _build_full_folder_path(context)
	final_folder = ensure_folder(folder_path)

	# ── Versioning & metadata on custom_* fields ────────────────────────────
	versioning_enabled = getattr(settings, "enable_versioning", 1) and meta.has_field("custom_version_no")

	if versioning_enabled:
		slot = _compute_slot_key(doc, context)
		version_no = _get_next_version(slot)

		if meta.has_field("custom_version_no"):
			doc.custom_version_no = version_no
		if meta.has_field("custom_file_category"):
			doc.custom_file_category = context.get("file_category")
		if meta.has_field("custom_logical_key"):
			doc.custom_logical_key = context.get("logical_key")
		if meta.has_field("custom_is_latest"):
			doc.custom_is_latest = 1

		_mark_other_versions_not_latest(doc, slot)
	else:
		# Even without explicit versioning, we can still set category/logical_key if fields exist
		if meta.has_field("custom_file_category"):
			doc.custom_file_category = context.get("file_category")
		if meta.has_field("custom_logical_key"):
			doc.custom_logical_key = context.get("logical_key")
		if meta.has_field("custom_is_latest") and getattr(doc, "custom_is_latest", None) is None:
			doc.custom_is_latest = 1
		# custom_version_no can stay unset if we’re not versioning

	# ── Compute new filename ───────────────────────────────────────────────
	filename = os.path.basename(doc.file_name or doc.file_url)
	base, ext = os.path.splitext(filename)
	slug_base = slugify(base)

	if versioning_enabled and meta.has_field("custom_version_no") and getattr(doc, "custom_version_no", None):
		new_filename = f"{slug_base}_v{doc.custom_version_no}{ext or ''}"
	else:
		new_filename = f"{slug_base}{ext or ''}"

	# ── Compute new file_url (respect private/public) ──────────────────────
	is_private = bool(doc.is_private)
	if is_private:
		rel_base = "private/files"
	else:
		rel_base = "files"

	# Folder path after 'Home/...'
	# Example final_folder = 'Home/Meetings/MEET-0001'
	relative_folder = "/".join(final_folder.split("/")[1:])  # e.g. Meetings/MEET-0001

	new_rel_path = f"{rel_base}/{relative_folder}/{new_filename}"
	new_abs_path = frappe.utils.get_site_path(new_rel_path)

	# Old path
	old_rel_path = doc.file_url.lstrip("/")
	old_abs_path = frappe.utils.get_site_path(old_rel_path)

	# Ensure destination dir
	os.makedirs(os.path.dirname(new_abs_path), exist_ok=True)

	# Move file if paths differ
	if os.path.abspath(old_abs_path) != os.path.abspath(new_abs_path):
		if os.path.exists(old_abs_path):
			os.rename(old_abs_path, new_abs_path)

	# ── Update File doc fields ─────────────────────────────────────────────
	doc.folder = final_folder
	doc.file_name = new_filename
	doc.file_url = f"/{new_rel_path}"

	values = {
		"folder": doc.folder,
		"file_name": doc.file_name,
		"file_url": doc.file_url,
	}

	# Only set custom_* if the fields actually exist
	if meta.has_field("custom_file_category"):
		values["custom_file_category"] = getattr(doc, "custom_file_category", None)
	if meta.has_field("custom_logical_key"):
		values["custom_logical_key"] = getattr(doc, "custom_logical_key", None)
	if meta.has_field("custom_version_no"):
		values["custom_version_no"] = getattr(doc, "custom_version_no", None)
	if meta.has_field("custom_is_latest"):
		values["custom_is_latest"] = getattr(doc, "custom_is_latest", None)

	# Save without recursion
	doc.db_set(values, update_modified=False)

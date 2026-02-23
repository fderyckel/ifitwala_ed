# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/portal_utils.py

from datetime import datetime
from typing import List

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.exceptions import UniqueValidationError  # optional clarity (see next point)
from frappe.utils import add_to_date, now_datetime, today
from frappe.utils.file_manager import save_file


def mark_read(user: str, ref_dt: str, ref_dn: str):
    try:
        frappe.get_doc(
            {
                "doctype": "Portal Read Receipt",
                "user": user,
                "reference_doctype": ref_dt,
                "reference_name": ref_dn,
                "read_at": now_datetime(),
            }
        ).insert(ignore_permissions=True)
    except UniqueValidationError:
        pass


def unread_names_for(user: str, ref_dt: str, names: List[str]) -> List[str]:
    if not names:
        return []
    seen = frappe.db.get_values(
        "Portal Read Receipt",
        {"user": user, "reference_doctype": ref_dt, "reference_name": ["in", names]},
        ["reference_name"],
        as_dict=True,
    )
    seen_set = {r["reference_name"] for r in seen}
    return [n for n in names if n not in seen_set]


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


def _compute_sla_due(hours: int) -> datetime:
    return add_to_date(now_datetime(), hours=hours)


# --- helpers (replace COUNSELOR_ROLE + _counselor_users) ---


def _intake_role() -> str:
    try:
        return frappe.get_cached_value("Referral Settings", None, "default_intake_owner_role") or "Counselor"
    except Exception:
        return "Counselor"


def _users_with_role(role: str) -> list[str]:
    user_ids = frappe.db.get_all(
        "Has Role",
        filters={"role": role, "parenttype": "User"},
        pluck="parent",
    )
    if not user_ids:
        return []
    return frappe.db.get_all(
        "User",
        filters={"name": ["in", user_ids], "enabled": 1},
        pluck="name",
    )


def _notify_counselors(docname: str):
    recipients = _users_with_role(_intake_role())
    submitter = frappe.session.user
    recipients = [u for u in recipients if u != submitter]
    if not recipients:
        return

    subject = _("New self-referral submitted")
    message = _("A new student self-referral was submitted and needs triage.")

    try:
        # Use POSITIONAL args for broad compatibility across Frappe versions
        # Signature: (recipients, subject, message, reference_doctype, reference_name)
        enqueue_create_notification(recipients, subject, message, DOC, docname)
    except TypeError:
        # Fallback: create Notification Log rows per user
        for u in recipients:
            try:
                frappe.get_doc(
                    {
                        "doctype": "Notification Log",
                        "subject": subject,
                        "email_content": message,
                        "for_user": u,
                        "type": "Alert",
                        "document_type": DOC,
                        "document_name": docname,
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                frappe.log_error(frappe.get_traceback(), "Self Referral: Notification Log fallback failed")


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
    subject_free = (kwargs.get("subject_student") or "").strip() or None  # portal textbox

    # Prepare insert (bypass perms after strong checks above)
    ref = frappe.new_doc(DOC)
    ref.update(
        {
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
        }
    )

    # Attach PE-derived context if available
    if pe:
        ref.update(
            {
                "program_enrollment": pe.get("name"),
                "program": pe.get("program"),
                "academic_year": pe.get("academic_year"),
                "school": pe.get("school"),
            }
        )

    # Optional portal fields into doc (fields you added in Step 1)
    if pref_contact:
        ref.preferred_contact_method = pref_contact
    ref.ok_to_contact_guardians = ok_guardians
    if safe_times:
        ref.safe_times_to_contact = safe_times

    # Always preserve what the student typed (if field exists)
    if reporting_for_other and subject_free:
        try:
            ref.subject_student_text = subject_free
        except Exception:
            pass  # field not deployed yet

    # Optional soft resolve (no failure if not found)
    if reporting_for_other and subject_free:
        target = _resolve_subject_student(subject_free)  # safe helper; may return None
        if target and target != student:
            try:
                ref.subject_student = target
            except Exception:
                pass

    # Insert ignoring perms (students may not have Create on this doctype)
    ref.insert(ignore_permissions=True)

    # Submit so it lands as actionable (docstatus=1)
    try:
        ref.flags.ignore_permissions = True  # allow submit as portal user
        ref.submit()
    except Exception:
        # If submit fails, don't silently leave a Draft around
        frappe.log_error(frappe.get_traceback(), "Self Referral: submit failed")
        frappe.throw(_("We couldn't finalize your referral. Please contact the counselor or try again."))

    # Try to notify, but never block creation
    try:
        _notify_counselors(ref.name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Self Referral: notify failed")

    return {"name": ref.name}


def _resolve_subject_student(candidate: str | None) -> str | None:
    if not candidate:
        return None
    s = candidate.strip()
    if not s:
        return None

    # 1) Exact docname
    if frappe.db.exists("Student", s):
        return s

    # 2) Exact student_id (if your Student has that field)
    try:
        name = frappe.db.get_value("Student", {"student_id": s}, "name")
        if name:
            return name
    except Exception:
        pass  # field may not exist in your schema; ignore

    # 3) Exact full name, but only if unique
    matches = frappe.db.get_all(
        "Student",
        filters={"student_full_name": s},
        pluck="name",
        limit=2,  # we only care if there's exactly one
    )
    if len(matches) == 1:
        return matches[0]

    # Ambiguous or not found → don't auto-link
    return None


ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_MB = 10  # conservative default; can be moved to settings later


def _ext_ok(filename: str) -> bool:
    fn = (filename or "").lower().strip()
    return any(fn.endswith(ext) for ext in ALLOWED_EXTS)


@frappe.whitelist(allow_guest=False)
def upload_self_referral_file(referral_name: str):
    """
    Attach a single file to a Student Referral created via portal.
    Expected multipart/form-data with fields:
    - referral_name: SRF-...
    - file: binary
    """
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    if "Student" not in roles:
        frappe.throw(_("Only logged-in students can upload here."), frappe.PermissionError)

    if not referral_name:
        frappe.throw(_("Missing referral name."))

    try:
        ref = frappe.get_doc("Student Referral", referral_name)
    except Exception:
        frappe.throw(_("Referral not found."))

    # Student can only attach to their own referral
    if ref.owner != user:
        frappe.throw(_("You cannot attach files to this referral."), frappe.PermissionError)

    # Pull file
    file_storage = frappe.request.files.get("file")
    if not file_storage:
        frappe.throw(_("No file uploaded."))

    filename = file_storage.filename or "upload.bin"
    if not _ext_ok(filename):
        frappe.throw(_("Only PNG, JPG, JPEG or PDF files are allowed."))

    # Read bytes once to validate size and pass to save_file
    content = file_storage.stream.read()
    size_mb = len(content) / (1024 * 1024.0)
    if size_mb > MAX_MB:
        frappe.throw(_("File is too large. Max {0} MB.").format(MAX_MB))

    # Save as PRIVATE file
    filedoc = save_file(
        filename=filename, content=content, doctype="Student Referral", name=referral_name, is_private=1, decode=False
    )

    return {"file_url": filedoc.file_url, "file_name": filedoc.file_name, "name": filedoc.name}

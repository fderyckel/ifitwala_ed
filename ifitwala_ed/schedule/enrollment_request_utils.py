# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/enrollment_request_utils.py

import json

import frappe
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist()
def validate_program_enrollment_request(request_name, force=0):
    if not request_name:
        frappe.throw(_("Program Enrollment Request is required."))

    _assert_no_catalog_prereqs()

    doc = frappe.get_doc("Program Enrollment Request", request_name)
    force = int(force or 0)

    # If already Valid and we have a payload, return it (unless forced)
    if not force and (doc.validation_status or "").strip() == "Valid":
        if doc.validation_payload:
            try:
                return json.loads(doc.validation_payload)
            except Exception:
                return {"validation_payload": doc.validation_payload}
        return {}

    # Build requested course list (unique, stable order)
    requested = []
    seen = set()
    for r in doc.courses or []:
        c = (r.course or "").strip()
        if not c or c in seen:
            continue
        seen.add(c)
        requested.append(c)

    if not requested:
        frappe.throw(_("No courses selected to validate."))

    # Single source of truth: enrollment_engine.evaluate_enrollment_request
    from ifitwala_ed.schedule.enrollment_engine import evaluate_enrollment_request

    engine_payload = evaluate_enrollment_request(
        {
            "student": doc.student,
            "program_offering": doc.program_offering,
            "requested_courses": requested,
            "request_id": doc.name,
            # keep default policy unless you later expose it on the doctype
        }
    )

    summary = engine_payload.get("summary") or {}
    results = engine_payload.get("results") or {}
    basket = results.get("basket") or {}

    # Canonical validity rule (Phase 2):
    # all_ok = all(course not blocked) AND basket.status in {"ok", "valid"}
    # requires_override = any course override_required OR basket.override_required
    basket_status = (summary.get("basket_status") or basket.get("status") or "").strip()
    basket_pass = basket_status in {"ok", "valid"}
    basket_override_required = bool(basket.get("override_required") or summary.get("override_required"))

    all_ok = True
    requires_override = False

    # Prefer engine summary.valid when present (single authoritative evaluation path),
    # but keep deterministic fallbacks for older snapshots.
    if "valid" in summary:
        all_ok = bool(summary.get("valid"))
    else:
        # Fallback for older engine payloads
        for r in results.get("courses") or []:
            if r.get("blocked"):
                all_ok = False
            if r.get("override_required"):
                requires_override = True
        if not basket_pass:
            all_ok = False

    # Override requirement: course-level OR basket-level
    requires_override = bool(
        requires_override
        or any(bool(r.get("override_required")) for r in (results.get("courses") or []))
        or basket_override_required
    )

    # Enforce Phase-2 validity invariant even if summary.valid drifts:
    # basket invalid must invalidate request.
    if not basket_pass:
        all_ok = False

    validation_status = "Valid" if all_ok else "Invalid"

    updates = {
        "validation_status": validation_status,
        "validation_payload": json.dumps(engine_payload, sort_keys=True, default=str),
        "validated_on": now_datetime(),
        "validated_by": frappe.session.user,
        "request_kind": (doc.request_kind or "Academic").strip() or "Academic",
        # keep PER flags aligned for workflow UX
        "requires_override": 1 if requires_override else 0,
    }

    doc.db_set(updates, update_modified=True)
    return engine_payload


@frappe.whitelist()
def materialize_program_enrollment_request(request_name):
    if not request_name:
        frappe.throw(_("Program Enrollment Request is required."))

    _assert_no_catalog_prereqs()

    req = frappe.get_doc("Program Enrollment Request", request_name)

    # 1) Hard gates: status + validation snapshot must exist
    if (req.status or "").strip() != "Approved":
        frappe.throw(_("Only Approved requests can be materialized."))

    if (req.validation_status or "").strip() != "Valid":
        frappe.throw(_("Request must be Valid before materializing enrollment."))

    if not req.validation_payload:
        frappe.throw(_("Validation Payload is required before materializing enrollment."))

    if not req.academic_year:
        frappe.throw(_("Academic Year is required to materialize enrollment."))

    # 2) Collect unique courses from request (no duplicates)
    request_courses = []
    seen = set()
    for row in req.courses or []:
        course = (row.course or "").strip()
        if not course or course in seen:
            continue
        seen.add(course)
        request_courses.append(course)

    if not request_courses:
        frappe.throw(_("No courses selected to materialize."))

    # 3) Resolve program + school from request/offering (single fetch)
    offering = (
        frappe.db.get_value(
            "Program Offering",
            req.program_offering,
            ["program", "school"],
            as_dict=True,
        )
        or {}
    )

    program = req.program or offering.get("program")
    if not program:
        frappe.throw(_("Program is required to materialize enrollment."))

    school = req.school or offering.get("school")

    # 4) Find existing enrollment for same (student, offering, ay)
    filters = {
        "student": req.student,
        "program_offering": req.program_offering,
        "academic_year": req.academic_year,
    }
    match = frappe.get_all("Program Enrollment", filters=filters, fields=["name"], limit=1)

    # 5) Create or update enrollment, forcing Request-source lock
    if match:
        enrollment = frappe.get_doc("Program Enrollment", match[0].name)

        # If it already exists but isn't Request-source, this is an admin/migration enrollment.
        # Do NOT mutate it silently; require explicit admin action instead.
        if (enrollment.enrollment_source or "").strip() and (enrollment.enrollment_source or "").strip() != "Request":
            frappe.throw(_("Cannot materialize into an enrollment that was not created from a Request source."))

        # Ensure linkage (idempotent)
        enrollment.enrollment_source = "Request"
        enrollment.program_enrollment_request = req.name

        existing = {r.course: r for r in (enrollment.courses or []) if r.course}
        for course in request_courses:
            if course in existing:
                existing[course].status = "Enrolled"
            else:
                enrollment.append("courses", {"course": course, "status": "Enrolled"})

    else:
        enrollment = frappe.get_doc(
            {
                "doctype": "Program Enrollment",
                "student": req.student,
                "program": program,
                "program_offering": req.program_offering,
                "academic_year": req.academic_year,
                "school": school,
                "enrollment_date": frappe.utils.nowdate(),
                "enrollment_source": "Request",
                "program_enrollment_request": req.name,
                "courses": [{"course": c, "status": "Enrolled"} for c in request_courses],
            }
        )

    # 6) Save using the Request-source guard flag (keeps your Program Enrollment protection)
    frappe.flags.enrollment_from_request = True
    try:
        enrollment.save()
    finally:
        frappe.flags.enrollment_from_request = False

    enrollment.add_comment("Comment", _("Materialized from Program Enrollment Request {0}.").format(req.name))
    return enrollment.name


def _assert_no_catalog_prereqs():
    meta = frappe.get_meta("Course")
    if not meta:
        return
    if meta.has_field("prerequisites"):
        frappe.throw(_("Catalog-level prerequisites are not supported. Use program-scoped prerequisites."))
    assert not meta.has_field("prerequisites")

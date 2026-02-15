# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/activity_booking.py

from __future__ import annotations

import json
import random
from datetime import timedelta
from typing import Any
from urllib.parse import quote_plus

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime, now_datetime, cint, flt

from ifitwala_ed.schedule.doctype.program_offering.program_offering import (
	preview_activity_booking_readiness,
	create_draft_tuition_invoice,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots
from ifitwala_ed.api.org_comm_utils import (
	create_activity_communication,
	get_activity_communication_feed,
	post_activity_communication_interaction,
)


ACTIVE_BOOKING_STATUSES = {"Submitted", "Waitlisted", "Offered", "Confirmed"}
RESERVED_SEAT_STATUSES = {"Offered", "Confirmed"}
ROLE_BOOKING_ADMIN = {"System Manager", "Academic Admin", "Activity Coordinator"}
ROLE_BOOKING_STAFF = ROLE_BOOKING_ADMIN | {"Academic Staff"}

STATUS_LABELS = {
	"Draft": _("Draft"),
	"Submitted": _("Pending Review"),
	"Waitlisted": _("On Waitlist"),
	"Offered": _("Spot Available"),
	"Confirmed": _("Booked"),
	"Cancelled": _("Cancelled"),
	"Rejected": _("Not Allocated"),
	"Expired": _("Offer Expired"),
}

CANCELLATION_MODE_ALLOW_UNTIL_FIRST = "Allow Until First Session Start"
CANCELLATION_MODE_NO_SELF = "No Self Cancellation"
PAID_PORTAL_STATE_CONFIRMED = "Confirmed + Draft Invoice"
PAID_PORTAL_STATE_PENDING = "Pending Payment Label"


def _parse_name_list(value: Any, dict_key: str = "name") -> list[str]:
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return []
		try:
			value = frappe.parse_json(value)
		except Exception:
			return []

	if not isinstance(value, list):
		return []

	out = []
	seen = set()
	for row in value:
		name = ""
		if isinstance(row, dict):
			name = (row.get(dict_key) or row.get("student") or row.get("name") or "").strip()
		else:
			name = (row or "").strip()
		if not name or name in seen:
			continue
		seen.add(name)
		out.append(name)
	return out


def _get_activity_booking_settings() -> dict:
	try:
		doc = frappe.get_cached_doc("Activity Booking Settings")
	except Exception:
		doc = None

	if not doc:
		return {
			"default_waitlist_offer_hours": 24,
			"default_max_choices": 3,
			"default_show_waitlist_position": 1,
			"default_guardian_student_cancellation_mode": CANCELLATION_MODE_ALLOW_UNTIL_FIRST,
			"default_paid_booking_portal_state": PAID_PORTAL_STATE_CONFIRMED,
			"default_offer_banner_hours": 24,
		}

	return {
		"default_waitlist_offer_hours": cint(doc.default_waitlist_offer_hours or 24),
		"default_max_choices": cint(doc.default_max_choices or 3),
		"default_show_waitlist_position": cint(doc.default_show_waitlist_position or 0),
		"default_guardian_student_cancellation_mode": (
			doc.default_guardian_student_cancellation_mode or CANCELLATION_MODE_ALLOW_UNTIL_FIRST
		),
		"default_paid_booking_portal_state": (
			doc.default_paid_booking_portal_state or PAID_PORTAL_STATE_CONFIRMED
		),
		"default_offer_banner_hours": cint(doc.default_offer_banner_hours or 24),
	}


def _should_show_waitlist_position(actor_type: str | None) -> bool:
	if actor_type not in {"Student", "Guardian"}:
		return True
	settings = _get_activity_booking_settings()
	return cint(settings.get("default_show_waitlist_position") or 0) == 1


def _invoice_url(sales_invoice: str | None) -> str | None:
	name = (sales_invoice or "").strip()
	if not name:
		return None
	return f"/app/sales-invoice/{name}"


def _status_label(
	status: str | None,
	*,
	payment_required: int = 0,
	amount: float = 0.0,
	paid_portal_state: str | None = None,
	outstanding_amount: float | None = None,
) -> str:
	raw_status = (status or "Draft").strip() or "Draft"
	if (
		raw_status == "Confirmed"
		and cint(payment_required or 0) == 1
		and flt(amount or 0) > 0
		and (paid_portal_state or "") == PAID_PORTAL_STATE_PENDING
	):
		if outstanding_amount is None or flt(outstanding_amount) > 0:
			return _("Payment Pending")
	return STATUS_LABELS.get(raw_status, raw_status)


def _sales_invoice_outstanding_map(invoice_names: list[str]) -> dict[str, float]:
	names = sorted({(name or "").strip() for name in (invoice_names or []) if (name or "").strip()})
	if not names:
		return {}
	rows = frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", names]},
		fields=["name", "outstanding_amount"],
		limit_page_length=max(50, len(names) + 10),
	)
	return {row.get("name"): flt(row.get("outstanding_amount") or 0) for row in rows}


def _parse_json_list(value: Any) -> list[str]:
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return []
		try:
			value = frappe.parse_json(value)
		except Exception:
			return []

	if not isinstance(value, list):
		return []

	out = []
	seen = set()
	for item in value:
		if isinstance(item, dict):
			name = (item.get("student_group") or item.get("name") or "").strip()
		else:
			name = (item or "").strip()
		if not name or name in seen:
			continue
		seen.add(name)
		out.append(name)
	return out


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
	return not (a_end <= b_start or b_end <= a_start)


def _get_roles() -> set[str]:
	return set(frappe.get_roles(frappe.session.user))


def _require_booking_admin() -> None:
	if not (_get_roles() & ROLE_BOOKING_ADMIN):
		frappe.throw(_("Not permitted to manage activity booking windows."), frappe.PermissionError)


def _activity_sections(program_offering: str) -> list[dict]:
	rows = frappe.get_all(
		"Program Offering Activity Section",
		filters={
			"parent": program_offering,
			"parenttype": "Program Offering",
			"is_active": 1,
		},
		fields=[
			"name",
			"idx",
			"student_group",
			"section_label",
			"capacity_override",
			"priority_tier",
			"allow_waitlist",
		],
		order_by="priority_tier asc, idx asc",
		limit_page_length=2000,
	)
	return rows or []


def _offering_doc(program_offering: str):
	doc = frappe.get_doc("Program Offering", program_offering)
	if cint(doc.activity_booking_enabled or 0) != 1:
		frappe.throw(_("Activity booking is not enabled for this Program Offering."))
	return doc


def _assert_window_is_open(offering) -> None:
	status = (offering.activity_booking_status or "Draft").strip()
	if status != "Open":
		frappe.throw(_("Activity booking window is not open."))

	now_dt = now_datetime()
	open_from = get_datetime(offering.activity_booking_open_from) if offering.activity_booking_open_from else None
	open_to = get_datetime(offering.activity_booking_open_to) if offering.activity_booking_open_to else None

	if open_from and now_dt < open_from:
		frappe.throw(_("Activity booking opens on {0}.").format(open_from))
	if open_to and now_dt > open_to:
		frappe.throw(_("Activity booking closed on {0}.").format(open_to))


def _actor_for_student(student: str) -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to submit activity bookings."), frappe.PermissionError)

	roles = _get_roles()
	if roles & ROLE_BOOKING_STAFF:
		return "Staff"

	student_email = frappe.db.get_value("Student", student, "student_email")
	if "Student" in roles and student_email and student_email == user:
		return "Student"

	guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
	if guardian:
		if frappe.db.exists("Student Guardian", {"parent": student, "guardian": guardian, "parenttype": "Student"}):
			return "Guardian"
		if frappe.db.exists("Guardian Student", {"parent": guardian, "student": student, "parenttype": "Guardian"}):
			return "Guardian"

	frappe.throw(_("You are not permitted to book activities for this student."), frappe.PermissionError)


def _assert_actor_allowed(offering, actor_type: str) -> None:
	if actor_type == "Student" and cint(offering.activity_allow_student_booking or 0) != 1:
		frappe.throw(_("Students cannot self-book this activity."), frappe.PermissionError)
	if actor_type == "Guardian" and cint(offering.activity_allow_guardian_booking or 0) != 1:
		frappe.throw(_("Guardians cannot book this activity."), frappe.PermissionError)
	if actor_type == "Staff" and (_get_roles() & ROLE_BOOKING_ADMIN):
		return
	if actor_type == "Staff" and cint(offering.activity_allow_staff_booking or 0) != 1:
		frappe.throw(_("Staff booking is disabled for this activity."), frappe.PermissionError)


def _validate_student_age(offering, student: str) -> None:
	min_age = offering.activity_min_age_years
	max_age = offering.activity_max_age_years
	if min_age is None and max_age is None:
		return

	dob = frappe.db.get_value("Student", student, "student_date_of_birth")
	if not dob:
		frappe.throw(_("Student date of birth is required for age-restricted activity booking."))

	dob_date = getdate(dob)
	reference_date = getdate(offering.start_date) if offering.start_date else getdate()
	age_years = reference_date.year - dob_date.year - ((reference_date.month, reference_date.day) < (dob_date.month, dob_date.day))

	if min_age is not None and age_years < cint(min_age):
		frappe.throw(_("Student must be at least {0} years old for this activity.").format(min_age))
	if max_age is not None and age_years > cint(max_age):
		frappe.throw(_("Student must be at most {0} years old for this activity.").format(max_age))


def _lock_student_offering(student: str, program_offering: str) -> list[dict]:
	return frappe.db.sql(
		"""
		SELECT name, status
		FROM `tabActivity Booking`
		WHERE student = %s
		  AND program_offering = %s
		  AND status IN ('Submitted', 'Waitlisted', 'Offered', 'Confirmed')
		FOR UPDATE
		""",
		(student, program_offering),
		as_dict=True,
	)


def _lock_reserved_section_rows(program_offering: str, student_group: str) -> list[dict]:
	return frappe.db.sql(
		"""
		SELECT name
		FROM `tabActivity Booking`
		WHERE program_offering = %s
		  AND allocated_student_group = %s
		  AND status IN ('Offered', 'Confirmed')
		FOR UPDATE
		""",
		(program_offering, student_group),
		as_dict=True,
	)


def _waitlist_position(program_offering: str, student_group: str) -> int:
	rows = frappe.db.sql(
		"""
		SELECT COALESCE(MAX(waitlist_position), 0) AS max_pos
		FROM `tabActivity Booking`
		WHERE program_offering = %s
		  AND allocated_student_group = %s
		  AND status IN ('Waitlisted', 'Offered')
		FOR UPDATE
		""",
		(program_offering, student_group),
		as_dict=True,
	)
	return cint((rows[0] or {}).get("max_pos") or 0) + 1


def _section_capacity(section_row: dict, offering_capacity: int) -> int | None:
	override_capacity = cint(section_row.get("capacity_override") or 0)
	if override_capacity > 0:
		return override_capacity

	sg_capacity = cint(frappe.db.get_value("Student Group", section_row.get("student_group"), "maximum_size") or 0)
	if sg_capacity > 0:
		return sg_capacity

	if offering_capacity > 0:
		return offering_capacity
	return None


def _student_overlap_for_section(student: str, target_section: str, window_start, window_end, exclude_booking: str | None = None) -> dict | None:
	"""
	Hard conflict guard: student cannot hold overlapping confirmed/offered activity slots.
	"""
	target_slots = iter_student_group_room_slots(target_section, window_start, window_end)
	if not target_slots:
		return None

	existing_rows = frappe.get_all(
		"Activity Booking",
		filters={
			"student": student,
			"status": ["in", sorted(RESERVED_SEAT_STATUSES)],
			"allocated_student_group": ["is", "set"],
		},
		fields=["name", "allocated_student_group", "program_offering", "status"],
		limit_page_length=2000,
	)

	for row in existing_rows:
		if exclude_booking and row.get("name") == exclude_booking:
			continue
		other_section = (row.get("allocated_student_group") or "").strip()
		if not other_section or other_section == target_section:
			continue
		other_slots = iter_student_group_room_slots(other_section, window_start, window_end)
		if not other_slots:
			continue
		for a in target_slots:
			for b in other_slots:
				if _overlaps(a.get("start"), a.get("end"), b.get("start"), b.get("end")):
					return {
						"other_booking": row.get("name"),
						"other_section": other_section,
						"other_program_offering": row.get("program_offering"),
						"target_section": target_section,
					}
	return None


def _resolve_account_holder(student: str, account_holder: str | None = None) -> str | None:
	if account_holder:
		return account_holder
	return frappe.db.get_value("Student", student, "account_holder")


def _create_invoice_if_required(booking_doc, offering) -> None:
	if cint(booking_doc.payment_required or 0) != 1:
		return
	amount = flt(booking_doc.amount or 0)
	if amount <= 0:
		return

	if not booking_doc.account_holder:
		frappe.throw(_("Account Holder is required for paid activity confirmation."))

	billable_offering = (offering.activity_billable_offering or "").strip()
	if not billable_offering:
		frappe.throw(_("Billable Offering is required for paid activity confirmation."))

	invoice_payload = [
		{
			"billable_offering": billable_offering,
			"qty": 1,
			"rate": amount,
			"student": booking_doc.student,
			"description": _("Activity booking fee for {0}").format(offering.name),
			"charge_source": "Program Offering",
		}
	]
	result = create_draft_tuition_invoice(
		program_offering=offering.name,
		account_holder=booking_doc.account_holder,
		posting_date=str(getdate()),
		items=json.dumps(invoice_payload),
	)
	booking_doc.sales_invoice = (result or {}).get("sales_invoice")


def _emit_booking_communication(booking_doc, event_label: str, message: str) -> str | None:
	offering = booking_doc.program_offering
	section = booking_doc.allocated_student_group
	school = frappe.db.get_value("Program Offering", offering, "school")
	if not school:
		return None

	previous_flag = bool(getattr(frappe.flags, "allow_activity_comm_system_write", False))
	frappe.flags.allow_activity_comm_system_write = True
	try:
		result = create_activity_communication(
			title=_("Activity Booking: {0}").format(event_label),
			message=message,
			school=school,
			activity_program_offering=offering,
			activity_booking=booking_doc.name,
			activity_student_group=section,
			communication_type="Information",
			portal_surface="Portal Feed",
			to_guardians=1,
			to_students=1,
			to_staff=1,
		)
	finally:
		frappe.flags.allow_activity_comm_system_write = previous_flag
	return (result or {}).get("name")


def _booking_payload(
	doc,
	*,
	actor_type: str | None = None,
	paid_portal_state: str | None = None,
	invoice_outstanding: float | None = None,
) -> dict:
	waitlist_position = doc.waitlist_position
	if not _should_show_waitlist_position(actor_type):
		waitlist_position = None

	return {
		"name": doc.name,
		"program_offering": doc.program_offering,
		"student": doc.student,
		"status": doc.status,
		"status_label": _status_label(
			doc.status,
			payment_required=cint(doc.payment_required or 0),
			amount=flt(doc.amount or 0),
			paid_portal_state=paid_portal_state,
			outstanding_amount=invoice_outstanding,
		),
		"allocated_student_group": doc.allocated_student_group,
		"waitlist_position": waitlist_position,
		"offer_expires_on": doc.offer_expires_on,
		"payment_required": cint(doc.payment_required or 0),
		"amount": flt(doc.amount or 0),
		"account_holder": doc.account_holder,
		"sales_invoice": doc.sales_invoice,
		"sales_invoice_url": _invoice_url(doc.sales_invoice),
		"org_communication": doc.org_communication,
		"choices": _parse_json_list(doc.choices_json),
	}


@frappe.whitelist()
def preview_activity_preopen_validation(program_offering: str):
	return preview_activity_booking_readiness(program_offering)


@frappe.whitelist()
def open_activity_booking_window(program_offering: str):
	_require_booking_admin()
	offering = _offering_doc(program_offering)
	report = offering.run_activity_preopen_readiness(raise_on_failure=False)
	if not report.get("ok"):
		return {"ok": False, "report": report}

	offering.activity_booking_status = "Open"
	if not offering.activity_booking_open_from:
		offering.activity_booking_open_from = now_datetime()
	offering.save()
	return {"ok": True, "report": report, "activity_booking_status": offering.activity_booking_status}


@frappe.whitelist()
def close_activity_booking_window(program_offering: str):
	_require_booking_admin()
	offering = _offering_doc(program_offering)
	offering.activity_booking_status = "Closed"
	offering.save()
	return {"ok": True, "activity_booking_status": offering.activity_booking_status}


@frappe.whitelist()
def submit_activity_booking(
	program_offering: str,
	student: str,
	choices=None,
	idempotency_key: str | None = None,
	request_surface: str | None = None,
	account_holder: str | None = None,
):
	offering = _offering_doc(program_offering)
	_assert_window_is_open(offering)
	settings = _get_activity_booking_settings()
	paid_portal_state = settings.get("default_paid_booking_portal_state") or PAID_PORTAL_STATE_CONFIRMED

	actor = _actor_for_student(student)
	_assert_actor_allowed(offering, actor)
	_validate_student_age(offering, student)

	sections = _activity_sections(program_offering)
	if not sections:
		frappe.throw(_("No active activity sections configured for this offering."))

	allowed_section_names = {r.get("student_group") for r in sections if r.get("student_group")}
	requested_choices = _parse_json_list(choices)
	if not requested_choices:
		requested_choices = [r.get("student_group") for r in sections if r.get("student_group")]

	clean_choices = []
	for section in requested_choices:
		if section in allowed_section_names and section not in clean_choices:
			clean_choices.append(section)

	if not clean_choices:
		frappe.throw(_("At least one valid activity section choice is required."))

	max_choices = cint(settings.get("default_max_choices") or 0)
	if max_choices > 0 and len(clean_choices) > max_choices:
		frappe.throw(
			_("You can rank up to {0} activity choices for this booking.").format(max_choices)
		)

	idempotency_key = (idempotency_key or "").strip() or None
	if idempotency_key:
		existing = frappe.db.get_value("Activity Booking", {"idempotency_key": idempotency_key}, "name")
		if existing:
			return _booking_payload(
				frappe.get_doc("Activity Booking", existing),
				actor_type=actor,
				paid_portal_state=paid_portal_state,
			)

	locked_active = _lock_student_offering(student, program_offering)
	if locked_active:
		row = locked_active[0]
		frappe.throw(
			_("Student already has an active booking ({0}) with status {1} for this offering.").format(
				row.get("name"), row.get("status")
			),
			title=_("Duplicate Active Booking"),
		)

	allocation_mode = (offering.activity_allocation_mode or "First Come First Serve").strip()
	window_start, window_end = offering._get_activity_date_window()
	if not window_start or not window_end:
		frappe.throw(_("Program Offering needs a valid date window for booking."))

	selected_section = None
	status = "Submitted"
	waitlist_position = None
	waitlist_state = "None"
	allocation_snapshot = {
		"mode": allocation_mode,
		"choices": clean_choices,
		"evaluated_at": str(now_datetime()),
		"decision": None,
	}

	offering_capacity = cint(offering.capacity or 0)
	section_by_name = {r.get("student_group"): r for r in sections if r.get("student_group")}

	if allocation_mode == "First Come First Serve":
		for section_name in clean_choices:
			section_row = section_by_name.get(section_name)
			if not section_row:
				continue

			conflict = _student_overlap_for_section(student, section_name, window_start, window_end)
			if conflict:
				allocation_snapshot.setdefault("conflicts", []).append(conflict)
				continue

			reserved_rows = _lock_reserved_section_rows(program_offering, section_name)
			reserved_count = len(reserved_rows)
			capacity = _section_capacity(section_row, offering_capacity)
			if capacity is not None and reserved_count >= capacity:
				allocation_snapshot.setdefault("full_sections", []).append(section_name)
				continue

			selected_section = section_name
			status = "Confirmed"
			allocation_snapshot["decision"] = "confirmed"
			break

		if not selected_section:
			if cint(offering.activity_waitlist_enabled or 0) == 1:
				first_choice = clean_choices[0]
				status = "Waitlisted"
				selected_section = first_choice
				waitlist_position = _waitlist_position(program_offering, first_choice)
				waitlist_state = "Active"
				allocation_snapshot["decision"] = "waitlisted"
			else:
				status = "Submitted"
				allocation_snapshot["decision"] = "submitted"

	elif allocation_mode in {"Lottery (Preference)", "Manual"}:
		status = "Submitted"
		allocation_snapshot["decision"] = "submitted"
	else:
		frappe.throw(_("Unsupported allocation mode: {0}").format(allocation_mode))

	booking = frappe.new_doc("Activity Booking")
	booking.program_offering = program_offering
	booking.student = student
	booking.booked_by_user = frappe.session.user
	booking.booking_actor_type = actor
	if request_surface:
		booking.request_surface = request_surface
	elif actor == "Guardian":
		booking.request_surface = "Guardian Portal"
	elif actor == "Student":
		booking.request_surface = "Student Portal"
	else:
		booking.request_surface = "Desk"
	booking.idempotency_key = idempotency_key
	booking.status = status
	booking.allocated_student_group = selected_section
	booking.choices_json = json.dumps(clean_choices)
	booking.allocation_mode = allocation_mode
	booking.allocation_snapshot = json.dumps(allocation_snapshot, default=str)
	booking.waitlist_position = waitlist_position
	booking.waitlist_state = waitlist_state
	booking.payment_required = 1 if cint(offering.activity_payment_required or 0) == 1 else 0
	booking.amount = flt(offering.activity_fee_amount or 0)
	booking.account_holder = _resolve_account_holder(student, account_holder)
	booking.submitted_on = now_datetime()
	booking.submitted_by = frappe.session.user
	if status == "Confirmed":
		booking.confirmed_on = now_datetime()
		booking.confirmed_by = frappe.session.user

	booking.insert(ignore_permissions=True)

	if status == "Confirmed":
		_create_invoice_if_required(booking, offering)
		booking.org_communication = _emit_booking_communication(
			booking,
			event_label="Confirmed",
			message=_("Activity booking {0} has been confirmed for section {1}.").format(
				booking.name,
				booking.allocated_student_group,
			),
		)
		booking.save(ignore_permissions=True)
	elif status == "Waitlisted":
		booking.org_communication = _emit_booking_communication(
			booking,
			event_label="Waitlisted",
			message=_("Activity booking {0} is on waitlist for section {1}.").format(
				booking.name,
				booking.allocated_student_group,
			),
		)
		booking.save(ignore_permissions=True)

	return _booking_payload(
		booking,
		actor_type=actor,
		paid_portal_state=paid_portal_state,
	)


@frappe.whitelist()
def allocate_activity_bookings(program_offering: str, dry_run: int = 0):
	_require_booking_admin()
	offering = _offering_doc(program_offering)
	sections = _activity_sections(program_offering)
	if not sections:
		frappe.throw(_("No active sections found for this offering."))

	mode = (offering.activity_allocation_mode or "").strip()
	if mode != "Lottery (Preference)":
		frappe.throw(_("Auto allocation is available only in Lottery (Preference) mode."))

	window_start, window_end = offering._get_activity_date_window()
	if not window_start or not window_end:
		frappe.throw(_("Program Offering needs a valid date window for allocation."))

	offering_capacity = cint(offering.capacity or 0)
	section_by_name = {r.get("student_group"): r for r in sections if r.get("student_group")}
	reserved_counts = {}
	for section_name, row in section_by_name.items():
		capacity = _section_capacity(row, offering_capacity)
		if capacity is None:
			reserved_counts[section_name] = {"capacity": None, "used": 0}
		else:
			used = frappe.db.count(
				"Activity Booking",
				{
					"program_offering": program_offering,
					"allocated_student_group": section_name,
					"status": ["in", sorted(RESERVED_SEAT_STATUSES)],
				},
			)
			reserved_counts[section_name] = {"capacity": capacity, "used": cint(used)}

	pending = frappe.get_all(
		"Activity Booking",
		filters={
			"program_offering": program_offering,
			"status": ["in", ["Submitted", "Waitlisted"]],
		},
		fields=["name", "student", "choices_json", "status"],
		order_by="creation asc",
		limit_page_length=5000,
	)
	if not pending:
		return {"ok": True, "allocated": 0, "waitlisted": 0, "total": 0}

	seed = int(now_datetime().timestamp())
	rng = random.Random(seed)

	choices_map = {}
	max_choices = 0
	for row in pending:
		choices = [c for c in _parse_json_list(row.get("choices_json")) if c in section_by_name]
		choices_map[row["name"]] = choices
		max_choices = max(max_choices, len(choices))

	assigned = {}
	for rank in range(max_choices):
		bucket = {}
		for row in pending:
			name = row.get("name")
			if name in assigned:
				continue
			choices = choices_map.get(name) or []
			if len(choices) <= rank:
				continue
			section = choices[rank]
			bucket.setdefault(section, []).append(row)

		for section, candidates in bucket.items():
			rng.shuffle(candidates)
			for row in candidates:
				if row.get("name") in assigned:
					continue
				capacity = reserved_counts[section]["capacity"]
				used = reserved_counts[section]["used"]
				if capacity is not None and used >= capacity:
					continue
				conflict = _student_overlap_for_section(
					row.get("student"),
					section,
					window_start,
					window_end,
					exclude_booking=row.get("name"),
				)
				if conflict:
					continue
				assigned[row.get("name")] = section
				if capacity is not None:
					reserved_counts[section]["used"] = used + 1

	waitlisted = 0
	allocated = 0
	for row in pending:
		booking_name = row.get("name")
		section = assigned.get(booking_name)
		if section:
			allocated += 1
			if not cint(dry_run):
				doc = frappe.get_doc("Activity Booking", booking_name)
				previous_status = doc.status
				doc.status = "Confirmed"
				doc.allocated_student_group = section
				doc.waitlist_state = "Promoted" if (previous_status == "Waitlisted") else "None"
				doc.waitlist_position = None
				doc.offer_expires_on = None
				doc.confirmed_on = now_datetime()
				doc.confirmed_by = frappe.session.user
				doc.allocation_snapshot = json.dumps(
					{
						"mode": mode,
						"decision": "confirmed",
						"section": section,
						"seed": seed,
						"allocated_at": str(now_datetime()),
					},
					default=str,
				)
				_create_invoice_if_required(doc, offering)
				doc.save(ignore_permissions=True)
		else:
			waitlisted += 1
			if not cint(dry_run):
				doc = frappe.get_doc("Activity Booking", booking_name)
				if cint(offering.activity_waitlist_enabled or 0) == 1:
					first_choice = (choices_map.get(booking_name) or [None])[0]
					doc.status = "Waitlisted"
					doc.allocated_student_group = first_choice
					doc.waitlist_state = "Active"
					doc.waitlist_position = _waitlist_position(program_offering, first_choice) if first_choice else None
					doc.allocation_snapshot = json.dumps(
						{
							"mode": mode,
							"decision": "waitlisted",
							"seed": seed,
							"evaluated_at": str(now_datetime()),
						},
						default=str,
					)
				else:
					doc.status = "Rejected"
					doc.waitlist_state = "Closed"
					doc.allocation_snapshot = json.dumps(
						{
							"mode": mode,
							"decision": "rejected",
							"seed": seed,
							"evaluated_at": str(now_datetime()),
						},
						default=str,
					)
				doc.save(ignore_permissions=True)

	return {
		"ok": True,
		"dry_run": cint(dry_run),
		"allocated": allocated,
		"waitlisted": waitlisted,
		"total": len(pending),
		"seed": seed,
	}


@frappe.whitelist()
def confirm_activity_booking_offer(activity_booking: str):
	doc = frappe.get_doc("Activity Booking", activity_booking)
	offering = _offering_doc(doc.program_offering)
	settings = _get_activity_booking_settings()

	actor = _actor_for_student(doc.student)
	_assert_actor_allowed(offering, actor)

	if doc.status not in {"Offered", "Waitlisted"}:
		frappe.throw(_("Only offered/waitlisted bookings can be confirmed with this endpoint."))
	if not doc.allocated_student_group:
		frappe.throw(_("Allocated Student Group is required to confirm the booking."))
	if doc.offer_expires_on and now_datetime() > get_datetime(doc.offer_expires_on):
		doc.status = "Expired"
		doc.waitlist_state = "Closed"
		doc.save(ignore_permissions=True)
		frappe.throw(_("This offer has expired."))

	window_start, window_end = offering._get_activity_date_window()
	if not window_start or not window_end:
		frappe.throw(_("Program Offering needs a valid date window for confirmation."))

	conflict = _student_overlap_for_section(
		doc.student,
		doc.allocated_student_group,
		window_start,
		window_end,
		exclude_booking=doc.name,
	)
	if conflict:
		frappe.throw(
			_("Cannot confirm booking due to schedule overlap with booking {0}.").format(conflict.get("other_booking"))
		)

	doc.status = "Confirmed"
	doc.waitlist_state = "Promoted"
	doc.waitlist_position = None
	doc.offer_expires_on = None
	doc.confirmed_on = now_datetime()
	doc.confirmed_by = frappe.session.user
	_create_invoice_if_required(doc, offering)
	doc.org_communication = _emit_booking_communication(
		doc,
		event_label="Offer Accepted",
		message=_("Activity booking {0} has been confirmed.").format(doc.name),
	)
	doc.save(ignore_permissions=True)
	return _booking_payload(
		doc,
		actor_type=actor,
		paid_portal_state=(
			settings.get("default_paid_booking_portal_state") or PAID_PORTAL_STATE_CONFIRMED
		),
	)


def _promote_next_waitlist(program_offering: str, section: str) -> dict | None:
	if not section:
		return None
	offering = _offering_doc(program_offering)
	offer_hours = cint(offering.activity_waitlist_offer_hours or 24)
	if offer_hours <= 0:
		offer_hours = 24

	rows = frappe.get_all(
		"Activity Booking",
		filters={
			"program_offering": program_offering,
			"allocated_student_group": section,
			"status": "Waitlisted",
		},
		fields=["name", "waitlist_position"],
		order_by="waitlist_position asc, creation asc",
		limit=1,
	)
	if not rows:
		return None

	doc = frappe.get_doc("Activity Booking", rows[0].get("name"))
	doc.status = "Offered"
	doc.waitlist_state = "Offered"
	doc.offer_expires_on = now_datetime() + timedelta(hours=offer_hours)
	doc.org_communication = _emit_booking_communication(
		doc,
		event_label="Spot Offered",
		message=_("A spot opened for booking {0}. Offer expires on {1}.").format(
			doc.name,
			doc.offer_expires_on,
		),
	)
	doc.save(ignore_permissions=True)
	return _booking_payload(doc)


def _first_section_slot_start(student_group: str, offering) -> Any | None:
	section = (student_group or "").strip()
	if not section:
		return None
	window_start, window_end = offering._get_activity_date_window()
	if not window_start or not window_end:
		return None

	first_start = None
	for slot in iter_student_group_room_slots(section, window_start, window_end):
		start_dt = slot.get("start")
		if not start_dt:
			continue
		if first_start is None or start_dt < first_start:
			first_start = start_dt
	return first_start


def _assert_self_cancellation_allowed(doc, offering, actor: str) -> None:
	if actor not in {"Student", "Guardian"}:
		return

	settings = _get_activity_booking_settings()
	mode = (
		settings.get("default_guardian_student_cancellation_mode")
		or CANCELLATION_MODE_ALLOW_UNTIL_FIRST
	)
	if mode == CANCELLATION_MODE_NO_SELF:
		frappe.throw(
			_("Self-service cancellation is disabled. Please contact your school office."),
			frappe.PermissionError,
		)

	if mode != CANCELLATION_MODE_ALLOW_UNTIL_FIRST:
		return

	target_section = (doc.allocated_student_group or "").strip()
	if not target_section:
		choices = _parse_json_list(doc.choices_json)
		target_section = choices[0] if choices else ""
	if not target_section:
		return

	first_slot_start = _first_section_slot_start(target_section, offering)
	if first_slot_start and now_datetime() >= get_datetime(first_slot_start):
		frappe.throw(
			_("Self-service cancellation closed when the first session started on {0}.").format(first_slot_start),
			frappe.PermissionError,
		)


@frappe.whitelist()
def cancel_activity_booking(activity_booking: str, reason: str | None = None):
	doc = frappe.get_doc("Activity Booking", activity_booking)
	offering = _offering_doc(doc.program_offering)

	actor = _actor_for_student(doc.student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	_assert_self_cancellation_allowed(doc, offering, actor)

	previous_status = doc.status
	section = doc.allocated_student_group
	doc.status = "Cancelled"
	doc.waitlist_state = "Closed"
	doc.cancellation_reason = (reason or "").strip()
	doc.cancelled_on = now_datetime()
	doc.cancelled_by = frappe.session.user
	doc.save(ignore_permissions=True)

	promoted = None
	if previous_status == "Confirmed" and cint(offering.activity_auto_promote_waitlist or 0) == 1:
		promoted = _promote_next_waitlist(doc.program_offering, section)

	return {
		"ok": True,
		"booking": _booking_payload(
			doc,
			actor_type=actor,
			paid_portal_state=(
				_get_activity_booking_settings().get("default_paid_booking_portal_state")
				or PAID_PORTAL_STATE_CONFIRMED
			),
		),
		"promoted_waitlist": promoted,
	}


@frappe.whitelist()
def get_activity_booking_logistics(student: str, program_offering: str | None = None):
	actor = _actor_for_student(student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	settings = _get_activity_booking_settings()
	paid_portal_state = settings.get("default_paid_booking_portal_state") or PAID_PORTAL_STATE_CONFIRMED
	show_waitlist = _should_show_waitlist_position(actor)

	filters = {
		"student": student,
		"status": ["in", ["Confirmed", "Offered", "Waitlisted"]],
	}
	if program_offering:
		filters["program_offering"] = program_offering

	rows = frappe.get_all(
		"Activity Booking",
		filters=filters,
		fields=[
			"name",
			"program_offering",
			"allocated_student_group",
			"status",
			"offer_expires_on",
			"waitlist_position",
			"payment_required",
			"amount",
			"sales_invoice",
		],
		order_by="modified desc",
		limit_page_length=200,
	)
	invoice_outstanding = _sales_invoice_outstanding_map([row.get("sales_invoice") for row in rows])

	out = []
	for row in rows:
		section = row.get("allocated_student_group")
		next_slot = None
		if section and row.get("status") in {"Confirmed", "Offered"}:
			slots = iter_student_group_room_slots(section, getdate(), getdate() + timedelta(days=30))
			future_slots = [s for s in slots if s.get("start") and s.get("start") >= now_datetime()]
			future_slots.sort(key=lambda x: x.get("start"))
			if future_slots:
				location = future_slots[0].get("location")
				next_slot = {
					"start": future_slots[0].get("start"),
					"end": future_slots[0].get("end"),
					"location": location,
					"map_url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(str(location or ''))}",
				}

		out.append(
				{
					"booking": row.get("name"),
					"program_offering": row.get("program_offering"),
					"section": section,
					"status": row.get("status"),
					"status_label": _status_label(
						row.get("status"),
						payment_required=cint(row.get("payment_required") or 0),
						amount=flt(row.get("amount") or 0),
						paid_portal_state=paid_portal_state,
						outstanding_amount=invoice_outstanding.get((row.get("sales_invoice") or "").strip()),
					),
					"offer_expires_on": row.get("offer_expires_on"),
					"waitlist_position": row.get("waitlist_position") if show_waitlist else None,
					"sales_invoice": row.get("sales_invoice"),
					"sales_invoice_url": _invoice_url(row.get("sales_invoice")),
					"next_slot": next_slot,
				}
			)

	return {"items": out}


@frappe.whitelist()
def get_student_activity_bookings(student: str, program_offering: str | None = None):
	actor = _actor_for_student(student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)
	settings = _get_activity_booking_settings()
	paid_portal_state = settings.get("default_paid_booking_portal_state") or PAID_PORTAL_STATE_CONFIRMED
	show_waitlist = _should_show_waitlist_position(actor)

	filters = {"student": student}
	if program_offering:
		filters["program_offering"] = program_offering

	rows = frappe.get_all(
		"Activity Booking",
		filters=filters,
		fields=[
			"name",
			"program_offering",
			"student",
			"status",
			"allocated_student_group",
			"waitlist_position",
			"offer_expires_on",
			"payment_required",
			"amount",
			"sales_invoice",
			"org_communication",
			"choices_json",
		],
		order_by="modified desc",
		limit_page_length=200,
	)
	invoice_outstanding = _sales_invoice_outstanding_map([row.get("sales_invoice") for row in rows])

	for row in rows:
		row["choices"] = _parse_json_list(row.get("choices_json"))
		row.pop("choices_json", None)
		row["status_label"] = _status_label(
			row.get("status"),
			payment_required=cint(row.get("payment_required") or 0),
			amount=flt(row.get("amount") or 0),
			paid_portal_state=paid_portal_state,
			outstanding_amount=invoice_outstanding.get((row.get("sales_invoice") or "").strip()),
		)
		row["sales_invoice_url"] = _invoice_url(row.get("sales_invoice"))
		if not show_waitlist:
			row["waitlist_position"] = None
	return {"items": rows}


def _guardian_student_names(guardian: str) -> list[str]:
	if not guardian:
		return []
	names = set(
		frappe.get_all(
			"Guardian Student",
			filters={"parent": guardian, "parenttype": "Guardian"},
			pluck="student",
		)
	)
	student_guardian_rows = frappe.get_all(
		"Student Guardian",
		filters={"guardian": guardian, "parenttype": "Student"},
		pluck="parent",
	)
	for row in student_guardian_rows:
		names.add(row)
	return sorted({name for name in names if name})


def _student_rows(student_names: list[str]) -> list[dict]:
	names = sorted({(name or "").strip() for name in (student_names or []) if (name or "").strip()})
	if not names:
		return []
	rows = frappe.get_all(
		"Student",
		filters={"name": ["in", names]},
		fields=[
			"name",
			"student_full_name",
			"student_preferred_name",
			"student_first_name",
			"student_last_name",
			"cohort",
			"student_image",
			"account_holder",
			"anchor_school",
			"enabled",
		],
		limit_page_length=max(100, len(names) + 20),
	)
	row_map = {row.get("name"): row for row in rows if cint(row.get("enabled") or 0) == 1}
	out = []
	for name in names:
		row = row_map.get(name)
		if not row:
			continue
		full_name = (
			(row.get("student_preferred_name") or "").strip()
			or (row.get("student_full_name") or "").strip()
			or " ".join(
				part
				for part in [
					(row.get("student_first_name") or "").strip(),
					(row.get("student_last_name") or "").strip(),
				]
				if part
			).strip()
			or name
		)
		out.append(
			{
				"student": name,
				"full_name": full_name,
				"preferred_name": (row.get("student_preferred_name") or "").strip() or None,
				"cohort": row.get("cohort"),
				"student_image": row.get("student_image"),
				"account_holder": row.get("account_holder"),
				"anchor_school": row.get("anchor_school"),
			}
		)
	return out


def _resolve_portal_students(students=None) -> tuple[str, list[dict]]:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

	requested = _parse_name_list(students, dict_key="student")
	roles = _get_roles()

	if roles & ROLE_BOOKING_STAFF:
		return "Staff", _student_rows(requested)

	student_name = frappe.db.get_value("Student", {"student_email": user}, "name")
	if "Student" in roles and student_name:
		if requested and student_name not in requested:
			frappe.throw(_("You are not permitted to access selected students."), frappe.PermissionError)
		return "Student", _student_rows([student_name])

	guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
	if guardian:
		allowed = _guardian_student_names(guardian)
		if requested:
			allowed_set = set(allowed)
			allowed = [name for name in requested if name in allowed_set]
		return "Guardian", _student_rows(allowed)

	frappe.throw(_("You are not permitted to access activity booking portal data."), frappe.PermissionError)


def _activity_context_maps(program_names: list[str]) -> dict:
	programs = sorted({(name or "").strip() for name in (program_names or []) if (name or "").strip()})
	if not programs:
		return {"by_program_school": {}, "by_program": {}}

	rows = frappe.db.sql(
		"""
		SELECT
			a.name AS activity,
			a.school,
			ap.program,
			a.descriptions,
			a.logistics_location_label,
			a.logistics_pickup_instructions,
			a.logistics_dropoff_instructions,
			a.logistics_map_url,
			a.logistics_notes,
			a.media_cover_image,
			a.media_gallery_link,
			a.media_notes
		FROM `tabActivity` a
		INNER JOIN `tabActivity Program` ap
			ON ap.parent = a.name
			AND ap.parenttype = 'Activity'
			AND ap.parentfield = 'program_allowed'
		WHERE ap.program IN %(programs)s
		  AND a.status = 1
		ORDER BY a.modified DESC
		""",
		{"programs": tuple(programs)},
		as_dict=True,
	)

	by_program_school = {}
	by_program = {}
	for row in rows:
		program = (row.get("program") or "").strip()
		school = (row.get("school") or "").strip()
		payload = {
			"activity": row.get("activity"),
			"descriptions": row.get("descriptions"),
			"logistics_location_label": row.get("logistics_location_label"),
			"logistics_pickup_instructions": row.get("logistics_pickup_instructions"),
			"logistics_dropoff_instructions": row.get("logistics_dropoff_instructions"),
			"logistics_map_url": row.get("logistics_map_url"),
			"logistics_notes": row.get("logistics_notes"),
			"media_cover_image": row.get("media_cover_image"),
			"media_gallery_link": row.get("media_gallery_link"),
			"media_notes": row.get("media_notes"),
		}
		key = (program, school)
		if program and school and key not in by_program_school:
			by_program_school[key] = payload
		if program and program not in by_program:
			by_program[program] = payload
	return {"by_program_school": by_program_school, "by_program": by_program}


def _allocation_fairness_text(mode: str) -> str:
	mode_name = (mode or "").strip()
	if mode_name == "First Come First Serve":
		return _("Seats are allocated by submission order with server-side capacity checks.")
	if mode_name == "Lottery (Preference)":
		return _("Allocation uses ranked preferences and an auditable lottery pass.")
	if mode_name == "Manual":
		return _("Assignments are reviewed manually by the school activity team.")
	return _("Allocation rules are defined by the school.")


def _next_section_slot(section: str, window_start, window_end) -> dict | None:
	if not section:
		return None
	now_dt = now_datetime()
	next_slot = None
	for slot in iter_student_group_room_slots(section, window_start, window_end):
		start_dt = slot.get("start")
		end_dt = slot.get("end")
		if not start_dt or not end_dt:
			continue
		if get_datetime(start_dt) < now_dt:
			continue
		if not next_slot or get_datetime(start_dt) < get_datetime(next_slot.get("start")):
			location = slot.get("location")
			next_slot = {
				"start": start_dt,
				"end": end_dt,
				"location": location,
				"map_url": f"https://www.google.com/maps/search/?api=1&query={quote_plus(str(location or ''))}",
			}
	return next_slot


@frappe.whitelist()
def get_activity_portal_board(students=None, include_inactive: int = 0):
	actor_type, student_rows = _resolve_portal_students(students=students)
	student_names = [row.get("student") for row in student_rows if row.get("student")]
	settings = _get_activity_booking_settings()
	paid_portal_state = settings.get("default_paid_booking_portal_state") or PAID_PORTAL_STATE_CONFIRMED
	show_waitlist = _should_show_waitlist_position(actor_type)
	now_dt = now_datetime()

	booking_rows = []
	if student_names:
		booking_rows = frappe.get_all(
			"Activity Booking",
			filters={"student": ["in", student_names]},
			fields=[
				"name",
				"program_offering",
				"student",
				"status",
				"allocated_student_group",
				"waitlist_position",
				"offer_expires_on",
				"payment_required",
				"amount",
				"sales_invoice",
				"org_communication",
				"choices_json",
			],
			order_by="modified desc",
			limit_page_length=2000,
		)
	invoice_outstanding = _sales_invoice_outstanding_map([row.get("sales_invoice") for row in booking_rows])
	bookings_by_student = {student: [] for student in student_names}
	booked_offerings = set()

	for row in booking_rows:
		booking_payload = {
			"name": row.get("name"),
			"program_offering": row.get("program_offering"),
			"status": row.get("status"),
			"status_label": _status_label(
				row.get("status"),
				payment_required=cint(row.get("payment_required") or 0),
				amount=flt(row.get("amount") or 0),
				paid_portal_state=paid_portal_state,
				outstanding_amount=invoice_outstanding.get((row.get("sales_invoice") or "").strip()),
			),
			"allocated_student_group": row.get("allocated_student_group"),
			"waitlist_position": row.get("waitlist_position") if show_waitlist else None,
			"offer_expires_on": row.get("offer_expires_on"),
			"payment_required": cint(row.get("payment_required") or 0),
			"amount": flt(row.get("amount") or 0),
			"sales_invoice": row.get("sales_invoice"),
			"sales_invoice_url": _invoice_url(row.get("sales_invoice")),
			"org_communication": row.get("org_communication"),
			"choices": _parse_json_list(row.get("choices_json")),
		}
		student_name = row.get("student")
		if student_name in bookings_by_student:
			bookings_by_student[student_name].append(booking_payload)
		if row.get("program_offering"):
			booked_offerings.add(row.get("program_offering"))

	offering_rows = frappe.get_all(
		"Program Offering",
		filters={
			"activity_booking_enabled": 1,
			"status": ["in", ["Planned", "Active"]],
		},
		fields=[
			"name",
			"program",
			"school",
			"offering_title",
			"start_date",
			"end_date",
			"capacity",
			"activity_booking_status",
			"activity_allocation_mode",
			"activity_booking_open_from",
			"activity_booking_open_to",
			"activity_allow_student_booking",
			"activity_allow_guardian_booking",
			"activity_allow_staff_booking",
			"activity_min_age_years",
			"activity_max_age_years",
			"activity_waitlist_enabled",
			"activity_waitlist_offer_hours",
			"activity_payment_required",
			"activity_fee_amount",
			"activity_billable_offering",
		],
		order_by="modified desc",
		limit_page_length=2000,
	)

	program_names = [row.get("program") for row in offering_rows if row.get("program")]
	school_names = [row.get("school") for row in offering_rows if row.get("school")]
	program_rows = frappe.get_all(
		"Program",
		filters={"name": ["in", sorted(set(program_names))]} if program_names else {"name": ["in", [""]]},
		fields=["name", "program_name", "program_abbreviation"],
		limit_page_length=max(100, len(set(program_names)) + 20),
	)
	school_rows = frappe.get_all(
		"School",
		filters={"name": ["in", sorted(set(school_names))]} if school_names else {"name": ["in", [""]]},
		fields=["name", "school_name", "abbr"],
		limit_page_length=max(100, len(set(school_names)) + 20),
	)
	program_map = {row.get("name"): row for row in program_rows}
	school_map = {row.get("name"): row for row in school_rows}
	activity_maps = _activity_context_maps(program_names)

	offerings = []
	for row in offering_rows:
		name = row.get("name")
		booking_status = (row.get("activity_booking_status") or "Draft").strip() or "Draft"
		open_from = get_datetime(row.get("activity_booking_open_from")) if row.get("activity_booking_open_from") else None
		open_to = get_datetime(row.get("activity_booking_open_to")) if row.get("activity_booking_open_to") else None
		in_window = True
		if open_from and now_dt < open_from:
			in_window = False
		if open_to and now_dt > open_to:
			in_window = False
		is_open_now = booking_status == "Open" and in_window
		is_visible = bool(name in booked_offerings or booking_status in {"Open", "Ready"})
		if not cint(include_inactive or 0) and not is_visible:
			continue

		sections = _activity_sections(name)
		section_names = [s.get("student_group") for s in sections if s.get("student_group")]
		sg_rows = frappe.get_all(
			"Student Group",
			filters={"name": ["in", section_names]} if section_names else {"name": ["in", [""]]},
			fields=["name", "student_group_name", "maximum_size"],
			limit_page_length=max(100, len(section_names) + 20),
		)
		sg_map = {sg.get("name"): sg for sg in sg_rows}
		reserved_rows = frappe.db.sql(
			"""
			SELECT allocated_student_group AS section_name, COUNT(*) AS reserved_count
			FROM `tabActivity Booking`
			WHERE program_offering = %(program_offering)s
			  AND status IN ('Offered', 'Confirmed')
			GROUP BY allocated_student_group
			""",
			{"program_offering": name},
			as_dict=True,
		)
		reserved_map = {
			(row.get("section_name") or "").strip(): cint(row.get("reserved_count") or 0)
			for row in reserved_rows
		}
		offering_start = getdate(row.get("start_date")) if row.get("start_date") else getdate()
		offering_end = getdate(row.get("end_date")) if row.get("end_date") else (offering_start + timedelta(days=180))

		section_payload = []
		for section_row in sections:
			section_name = (section_row.get("student_group") or "").strip()
			if not section_name:
				continue
			capacity = _section_capacity(section_row, cint(row.get("capacity") or 0))
			reserved_count = reserved_map.get(section_name, 0)
			remaining = None
			if capacity is not None:
				remaining = max(capacity - reserved_count, 0)
			sg_meta = sg_map.get(section_name) or {}
			section_payload.append(
				{
					"student_group": section_name,
					"label": (
						(section_row.get("section_label") or "").strip()
						or (sg_meta.get("student_group_name") or "").strip()
						or section_name
					),
					"capacity": capacity,
					"reserved": reserved_count,
					"remaining": remaining,
					"allow_waitlist": cint(section_row.get("allow_waitlist") or 0),
					"next_slot": _next_section_slot(section_name, offering_start, offering_end),
				}
			)

		program_name = row.get("program")
		school_name = row.get("school")
		activity_context = (
			activity_maps["by_program_school"].get((program_name, school_name))
			or activity_maps["by_program"].get(program_name)
			or {}
		)
		program_meta = program_map.get(program_name) or {}
		school_meta = school_map.get(school_name) or {}
		offerings.append(
			{
				"program_offering": name,
				"program": program_name,
				"program_label": (program_meta.get("program_name") or "").strip() or program_name,
				"program_abbreviation": program_meta.get("program_abbreviation"),
				"school": school_name,
				"school_label": (school_meta.get("school_name") or "").strip() or school_name,
				"school_abbr": school_meta.get("abbr"),
				"title": (row.get("offering_title") or "").strip()
				or (program_meta.get("program_name") or "").strip()
				or name,
				"start_date": row.get("start_date"),
				"end_date": row.get("end_date"),
				"booking_status": booking_status,
				"booking_window": {
					"open_from": row.get("activity_booking_open_from"),
					"open_to": row.get("activity_booking_open_to"),
					"is_open_now": 1 if is_open_now else 0,
				},
				"allocation_mode": row.get("activity_allocation_mode"),
				"allocation_explanation": _allocation_fairness_text(row.get("activity_allocation_mode") or ""),
				"booking_roles": {
					"allow_student": cint(row.get("activity_allow_student_booking") or 0),
					"allow_guardian": cint(row.get("activity_allow_guardian_booking") or 0),
					"allow_staff": cint(row.get("activity_allow_staff_booking") or 0),
				},
				"age_limits": {
					"min_years": row.get("activity_min_age_years"),
					"max_years": row.get("activity_max_age_years"),
				},
				"waitlist": {
					"enabled": cint(row.get("activity_waitlist_enabled") or 0),
					"offer_hours": cint(row.get("activity_waitlist_offer_hours") or 0),
				},
				"payment": {
					"required": cint(row.get("activity_payment_required") or 0),
					"amount": flt(row.get("activity_fee_amount") or 0),
					"billable_offering": row.get("activity_billable_offering"),
					"portal_state_mode": paid_portal_state,
				},
				"activity_context": activity_context,
				"sections": section_payload,
			}
		)

	students_payload = []
	for student in student_rows:
		name = student.get("student")
		bookings = bookings_by_student.get(name, [])
		counts = {}
		for booking in bookings:
			status = booking.get("status") or "Draft"
			counts[status] = cint(counts.get(status) or 0) + 1
		students_payload.append(
			{
				**student,
				"bookings": bookings,
				"booking_counts": counts,
			}
		)

	return {
		"generated_at": now_dt,
		"viewer": {
			"actor_type": actor_type,
			"user": frappe.session.user,
		},
		"settings": {
			"default_max_choices": cint(settings.get("default_max_choices") or 0),
			"default_show_waitlist_position": 1 if show_waitlist else 0,
			"default_guardian_student_cancellation_mode": settings.get(
				"default_guardian_student_cancellation_mode"
			),
			"default_paid_booking_portal_state": paid_portal_state,
			"default_offer_banner_hours": cint(settings.get("default_offer_banner_hours") or 0),
		},
		"students": students_payload,
		"offerings": offerings,
	}


@frappe.whitelist()
def submit_activity_booking_batch(
	program_offering: str,
	requests=None,
	request_surface: str | None = None,
):
	rows = requests
	if isinstance(rows, str):
		rows = rows.strip()
		rows = frappe.parse_json(rows) if rows else []
	if not isinstance(rows, list):
		frappe.throw(_("Requests must be a JSON list."))
	if not rows:
		frappe.throw(_("At least one booking request is required."))

	results = []
	success = 0
	failed = 0

	for idx, row in enumerate(rows, start=1):
		if not isinstance(row, dict):
			failed += 1
			results.append(
				{
					"ok": False,
					"student": None,
					"error": _("Row {0}: Invalid request payload.").format(idx),
				}
			)
			continue

		student = (row.get("student") or "").strip()
		if not student:
			failed += 1
			results.append(
				{
					"ok": False,
					"student": None,
					"error": _("Row {0}: Student is required.").format(idx),
				}
			)
			continue

		savepoint = f"activity_batch_{idx}"
		frappe.db.savepoint(savepoint)
		try:
			booking = submit_activity_booking(
				program_offering=program_offering,
				student=student,
				choices=row.get("choices"),
				idempotency_key=row.get("idempotency_key"),
				request_surface=request_surface or row.get("request_surface") or "Guardian Portal",
				account_holder=row.get("account_holder"),
			)
			success += 1
			results.append({"ok": True, "student": student, "booking": booking})
		except Exception as exc:
			frappe.db.rollback(save_point=savepoint)
			failed += 1
			results.append({"ok": False, "student": student, "error": str(exc) or _("Booking failed.")})

	return {
		"ok": failed == 0,
		"success_count": success,
		"failed_count": failed,
		"results": results,
	}


@frappe.whitelist()
def get_activity_communications(activity_program_offering: str | None = None, activity_student_group: str | None = None, start: int = 0, page_length: int = 30):
	return get_activity_communication_feed(
		activity_program_offering=activity_program_offering,
		activity_student_group=activity_student_group,
		start=start,
		page_length=page_length,
	)


@frappe.whitelist()
def post_activity_communication_entry(org_communication: str, intent_type: str | None = None, reaction_code: str | None = None, note: str | None = None, surface: str | None = "Portal Feed"):
	return post_activity_communication_interaction(
		org_communication=org_communication,
		intent_type=intent_type,
		reaction_code=reaction_code,
		note=note,
		surface=surface,
	)

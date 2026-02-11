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


def _booking_payload(doc) -> dict:
	return {
		"name": doc.name,
		"program_offering": doc.program_offering,
		"student": doc.student,
		"status": doc.status,
		"allocated_student_group": doc.allocated_student_group,
		"waitlist_position": doc.waitlist_position,
		"offer_expires_on": doc.offer_expires_on,
		"payment_required": cint(doc.payment_required or 0),
		"amount": flt(doc.amount or 0),
		"account_holder": doc.account_holder,
		"sales_invoice": doc.sales_invoice,
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

	idempotency_key = (idempotency_key or "").strip() or None
	if idempotency_key:
		existing = frappe.db.get_value("Activity Booking", {"idempotency_key": idempotency_key}, "name")
		if existing:
			return _booking_payload(frappe.get_doc("Activity Booking", existing))

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

	return _booking_payload(booking)


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
	return _booking_payload(doc)


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


@frappe.whitelist()
def cancel_activity_booking(activity_booking: str, reason: str | None = None):
	doc = frappe.get_doc("Activity Booking", activity_booking)
	offering = _offering_doc(doc.program_offering)

	actor = _actor_for_student(doc.student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)

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
		"booking": _booking_payload(doc),
		"promoted_waitlist": promoted,
	}


@frappe.whitelist()
def get_activity_booking_logistics(student: str, program_offering: str | None = None):
	actor = _actor_for_student(student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)

	filters = {
		"student": student,
		"status": ["in", ["Confirmed", "Offered", "Waitlisted"]],
	}
	if program_offering:
		filters["program_offering"] = program_offering

	rows = frappe.get_all(
		"Activity Booking",
		filters=filters,
		fields=["name", "program_offering", "allocated_student_group", "status", "offer_expires_on", "waitlist_position"],
		order_by="modified desc",
		limit_page_length=200,
	)

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
				"offer_expires_on": row.get("offer_expires_on"),
				"waitlist_position": row.get("waitlist_position"),
				"next_slot": next_slot,
			}
		)

	return {"items": out}


@frappe.whitelist()
def get_student_activity_bookings(student: str, program_offering: str | None = None):
	actor = _actor_for_student(student)
	if actor not in {"Student", "Guardian", "Staff"}:
		frappe.throw(_("Not permitted."), frappe.PermissionError)

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

	for row in rows:
		row["choices"] = _parse_json_list(row.get("choices_json"))
		row.pop("choices_json", None)
	return {"items": rows}


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

# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/referral_case/referral_case.py

import frappe
from frappe import _
from frappe.desk.form.assign_to import add as assign_add
from frappe.model.document import Document
from frappe.utils import cint, now_datetime, strip_html, today

CASE_MANAGER_TAG = "[CASE_MANAGER]"
CASE_TASK_TAG = "[CASE_TASK]"


class ReferralCase(Document):
    def validate(self):
        # Prevent closing when child entries are still active
        if (self.case_status or "").strip() == "Closed":
            active = [row for row in (self.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
            if active:
                frappe.throw(_("Cannot close case with open or in-progress entries."))

        # Case manager must be Counselor or Academic Admin
        if self.case_manager:
            allowed = ("Counselor", "Academic Admin")
            has_allowed = frappe.db.count("Has Role", {"parent": self.case_manager, "role": ["in", allowed]})
            if not has_allowed:
                frappe.throw(_("Case Manager must have either the Counselor or Academic Admin role."))

        # Keep native assignment in sync if manager changed via field
        if self.case_manager and (self.is_new() or self.case_manager != self.get_db_value("case_manager")):
            _assign_case_manager(self.name, self.case_manager, description="Updated via field", priority="Medium")

        # Enforce: assignee must be Academic Staff (when set)
        for r in self.entries or []:
            if r.assignee:
                has_role = frappe.db.count("Has Role", {"parent": r.assignee, "role": ["in", ("Academic Staff",)]})
                if not has_role:
                    frappe.throw(_("Entry assignee must have the Academic Staff role: {0}").format(r.assignee))

    def before_save(self):
        """Enforce triage rules and write mirrored timeline entries on authoritative changes."""
        old: "ReferralCase" | None = self.get_doc_before_save() if not self.is_new() else None
        if not old:
            return

        now_str = now_datetime().strftime("%Y-%m-%d %H:%M")
        actor = _actor()

        # 1) Case Manager change: triage-only (or current manager may reassign)
        if self.case_manager != old.case_manager:
            roles = set(frappe.get_roles(frappe.session.user))
            is_triager = bool({"Counselor", "Academic Admin"} & roles)
            is_current_mgr = bool(old.case_manager and old.case_manager == frappe.session.user)
            if not (is_triager or is_current_mgr):
                frappe.throw(
                    _("Only Counselor, Academic Admin, or the current Case Manager can change the Case Manager.")
                )

        # 2) Severity change: only upwards; triage-only
        old_sev = (old.severity or "Low").strip()
        new_sev = (self.severity or "Low").strip()
        if new_sev != old_sev:
            if not _user_can_triage(self):
                frappe.throw(_("You are not permitted to change severity."))
            if _rank(new_sev) < _rank(old_sev):
                frappe.throw(_("Severity can only be increased (no downgrade)."))

            # Auto-flag escalated status (unless already Closed)
            if (self.case_status or "Open") != "Closed":
                self.case_status = "Escalated"

            # Timeline: Case + mirror on Student Referral
            msg_case = _("Escalated to <b>{sev}</b> by {who} on {when}.").format(sev=new_sev, who=actor, when=now_str)
            _add_timeline("Referral Case", self.name, msg_case)
            if self.get("referral"):
                msg_ref = _("Referral has been escalated to <b>{sev}</b> by {who} on {when}.").format(
                    sev=new_sev, who=actor, when=now_str
                )
                _add_timeline("Student Referral", self.referral, msg_ref)

        # 3) Mandated Reporting toggle: only 0->1; triage-only; bump severity ≥ High
        md = frappe.get_meta(self.doctype)
        mr_field = None
        if md.get_field("mandated_reporting"):
            mr_field = "mandated_reporting"
        elif md.get_field("mandated_reporting_triggered"):
            mr_field = "mandated_reporting_triggered"

        if mr_field:
            old_mr = cint(old.get(mr_field) or 0)
            new_mr = cint(self.get(mr_field) or 0)
            if old_mr != new_mr:
                if new_mr == 0 and old_mr == 1:
                    # Disallow unsetting for audit integrity
                    frappe.throw(_("Mandated reporting cannot be unset once recorded."))
                if new_mr == 1:
                    if not _user_can_triage(self):
                        frappe.throw(
                            _(
                                "Only Counselor, Academic Admin, or the current Case Manager can record mandated reporting."
                            )
                        )

                    # Ensure severity is at least High and escalate status (unless already Closed)
                    if _rank(self.severity) < _rank("High"):
                        self.severity = "High"
                        if (self.case_status or "Open") != "Closed":
                            self.case_status = "Escalated"
                        msg_escal = _(
                            "Escalated to <b>High</b> (due to mandated reporting) by {who} on {when}."
                        ).format(who=actor, when=now_str)
                        _add_timeline("Referral Case", self.name, msg_escal)
                        if self.get("referral"):
                            _add_timeline("Student Referral", self.referral, msg_escal)

                    # MR timeline logs
                    msg_mr_case = _("Mandated reporting <b>recorded</b> by {who} on {when}.").format(
                        who=actor, when=now_str
                    )
                    _add_timeline("Referral Case", self.name, msg_mr_case)
                    if self.get("referral"):
                        msg_mr_ref = _("Mandated reporting was marked by {who} on {when}.").format(
                            who=actor, when=now_str
                        )
                        _add_timeline("Student Referral", self.referral, msg_mr_ref)


# ── Helpers for triage guardrails & logging ──────────────────────────────────
_SEV_ORDER = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}


def _rank(s: str | None) -> int:
    return _SEV_ORDER.get((s or "Low").strip(), 0)


def _actor() -> str:
    fullname = frappe.utils.get_fullname(frappe.session.user)
    return fullname or frappe.session.user


def _add_timeline(doctype: str, name: str, html: str):
    try:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": doctype,
                "reference_name": name,
                "content": html,
            }
        ).insert(ignore_permissions=True)
    except Exception:
        frappe.log_error(f"Failed to add timeline on {doctype} {name}", "Referral Case Timeline")


def _user_can_triage(case_doc: "ReferralCase") -> bool:
    roles = set(frappe.get_roles(frappe.session.user))
    if {"Counselor", "Academic Admin"} & roles:
        return True
    # current case manager can act
    return bool(case_doc.get("case_manager") and case_doc.case_manager == frappe.session.user)


# ─────────────────────────────────────────────────────────────────────────────
# Public APIs used by the client
# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
def quick_update_status(name: str, new_status: str):
    doc = frappe.get_doc("Referral Case", name)
    _ensure_case_action_permitted(doc)
    if new_status not in ("Open", "In Progress", "On Hold", "Escalated", "Closed"):
        frappe.throw(_("Invalid status."))
    if new_status == "Closed":
        active = [row for row in (doc.entries or []) if (row.status or "Open") in ("Open", "In Progress")]
        if active:
            frappe.throw(_("Cannot close case with open or in-progress entries."))
    doc.case_status = new_status
    if new_status == "Closed":
        doc.closed_on = today()
    else:
        # reopening / moving away from Closed clears closed_on
        if doc.closed_on:
            doc.closed_on = None
    doc.save(ignore_permissions=True)
    return {"ok": True}


@frappe.whitelist()
def add_entry(
    name: str,
    entry_type: str,
    summary: str,
    assignee: str | None = None,
    status: str = "Open",
    attachment: str | None = None,
    create_todo: int = 1,
    due_date: str | None = None,
):
    doc = frappe.get_doc("Referral Case", name)
    _ensure_case_action_permitted(doc)

    row = doc.append("entries", {})
    row.entry_type = entry_type
    row.summary = summary
    row.assignee = assignee
    row.status = status or "Open"
    row.author = frappe.session.user
    if attachment:
        row.attachments = attachment
    doc.save(ignore_permissions=True)

    # Optional ToDo for the assignee (task-level), tagged separately from manager ToDo
    if assignee and cint(create_todo):
        clean = strip_html(summary or "")[:120]
        payload = {
            "doctype": "Referral Case",
            "name": name,
            "assign_to": [assignee],
            "priority": "Medium",
            "description": f"{CASE_TASK_TAG} {entry_type}: {clean}",
        }
        if due_date:
            payload["date"] = due_date
        assign_add(payload)
    return {"ok": True}


@frappe.whitelist()
def escalate(name: str, severity: str, note: str = ""):
    doc = frappe.get_doc("Referral Case", name)
    _ensure_case_action_permitted(doc)

    if severity not in ("High", "Critical"):
        frappe.throw(_("Severity must be High or Critical."))

    order = {"Low": 0, "Moderate": 1, "High": 2, "Critical": 3}
    cur = doc.severity or "Low"
    target = severity

    # Early return if no upgrade
    if order.get(target, 0) <= order.get(cur, 0):
        return {"ok": True, "severity": cur}

    doc.severity = target
    if (doc.case_status or "Open") != "Closed":
        doc.case_status = "Escalated"
    doc.save(ignore_permissions=True)

    actor = _actor()
    ts = now_datetime().strftime("%Y-%m-%d %H:%M")
    safe_note = frappe.utils.escape_html(note or "")
    msg_case = _("Escalated to <b>{sev}</b> by {who} on {when}.").format(sev=target, who=actor, when=ts)
    if safe_note:
        msg_case += " " + _("Note") + f": {safe_note}"
    _add_timeline("Referral Case", doc.name, msg_case)

    if doc.get("referral"):
        msg_ref = _("Referral has been escalated to <b>{sev}</b> by {who} on {when}.").format(
            sev=target, who=actor, when=ts
        )
        if safe_note:
            msg_ref += " " + _("Note") + f": {safe_note}"
        _add_timeline("Student Referral", doc.referral, msg_ref)

    manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
    if manager:
        _assign_case_manager(name, manager, description=f"Escalated to {target}. {note or ''}".strip(), priority="High")

    return {"ok": True, "severity": target}


@frappe.whitelist()
def flag_mandated_reporting(name: str, referral: str | None = None, note: str = ""):
    """Authoritative: record mandated reporting on the case and log to both timelines."""
    doc = frappe.get_doc("Referral Case", name)
    _ensure_case_action_permitted(doc)

    # Lightweight entry (optional documentation)
    row = doc.append("entries", {})
    row.entry_type = "Other"
    row.summary = "Mandated reporting completed/triggered."
    row.status = "Done"
    doc.save(ignore_permissions=True)

    # Timeline messages (Case + mirror on Referral)
    actor = _actor()
    ts = now_datetime().strftime("%Y-%m-%d %H:%M")
    safe_note = frappe.utils.escape_html(note or "")
    msg_case = _("Mandated reporting <b>recorded</b> by {who} on {when}.").format(who=actor, when=ts)
    if safe_note:
        msg_case += " " + _("Note") + f": {safe_note}"
    _add_timeline("Referral Case", doc.name, msg_case)

    ref_name = referral or doc.get("referral")
    if ref_name and frappe.db.exists("Student Referral", ref_name):
        msg_ref = _("Mandated reporting was marked by {who} on {when}.").format(who=actor, when=ts)
        if safe_note:
            msg_ref += " " + _("Note") + f": {safe_note}"
        _add_timeline("Student Referral", ref_name, msg_ref)

    manager = doc.case_manager or _pick_manager_from_assignments(name) or _pick_any_counselor()
    if manager:
        _assign_case_manager(name, manager, description="Mandated reporting flagged", priority="High")

    return {"ok": True}


# ── Permissions & assignment helpers ─────────────────────────────────────────


@frappe.whitelist()
def set_manager(name: str, user: str):
    doc = frappe.get_doc("Referral Case", name)
    _ensure_case_action_permitted(doc)

    allowed = ("Counselor", "Academic Admin")
    if not frappe.db.count("Has Role", {"parent": user, "role": ["in", allowed]}):
        frappe.throw(_("Selected user must have either the Counselor or Academic Admin role."))

    _assign_case_manager(name, user, description="Assigned via action", priority="Medium")
    return {"ok": True}


def _ensure_case_action_permitted(doc: "ReferralCase"):
    """Only Counselor / Academic Admin OR the current case_manager may act.
    System Manager intentionally excluded for safeguarding privacy."""
    user = frappe.session.user
    roles = set(frappe.get_roles(user))

    if {"Counselor", "Academic Admin"} & roles:
        return
    if doc.case_manager and doc.case_manager == user:
        return
    frappe.throw(_("You are not permitted to perform this action on the case."))


def _assign_case_manager(case_name: str, user: str, description: str = "Primary owner", priority: str = "Medium"):
    allowed = ("Counselor", "Academic Admin")
    if not frappe.db.count("Has Role", {"parent": user, "role": ["in", allowed]}):
        frappe.throw(_("Case Manager must have either the Counselor or Academic Admin role."))

    _close_manager_todos_only(case_name)
    assign_add(
        {
            "doctype": "Referral Case",
            "name": case_name,
            "assign_to": [user],
            "priority": priority,
            "description": f"{CASE_MANAGER_TAG} {description}",
        }
    )
    frappe.db.set_value("Referral Case", case_name, "case_manager", user, update_modified=False)
    ref = frappe.db.get_value("Referral Case", case_name, "referral")
    if ref:
        frappe.db.set_value("Student Referral", ref, "assigned_case_manager", user, update_modified=False)


def _close_manager_todos_only(case_name: str):
    rows = frappe.get_all(
        "ToDo",
        filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
        fields=["name", "description"],
    )
    for r in rows:
        desc = (r.description or "").strip()
        if desc.startswith(CASE_MANAGER_TAG):
            frappe.db.set_value("ToDo", r.name, "status", "Closed", update_modified=False)


def _pick_manager_from_assignments(case_name: str) -> str | None:
    td = frappe.get_all(
        "ToDo",
        filters={"reference_type": "Referral Case", "reference_name": case_name, "status": "Open"},
        fields=["allocated_to", "description"],
    )
    for r in td:
        if (r.description or "").strip().startswith(CASE_MANAGER_TAG):
            return r.allocated_to
    return None


def _pick_any_counselor() -> str | None:
    cands = frappe.get_all("Has Role", filters={"role": "Counselor"}, fields=["parent"]) or []
    users = [c.parent for c in cands]
    if not users:
        return None
    enabled = frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, pluck="name")
    return enabled[0] if enabled else None


# ── Useful, SSG-agnostic helper kept for later teacher scoping ──────────────
def _get_teachers_of_record(student: str, ay: str) -> list[str]:
    """
    Return distinct, ENABLED user IDs for instructors teaching the student's groups in the given AY.
    """
    if not student or not ay:
        return []
    rows = (
        frappe.db.sql(
            """
        SELECT DISTINCT u.name AS user_id
        FROM `tabStudent Group Student` sgs
        JOIN `tabStudent Group` sg
          ON sg.name = sgs.parent
        JOIN `tabStudent Group Instructor` sgi
          ON sgi.parent = sg.name
        LEFT JOIN `tabInstructor` ins
          ON ins.name = sgi.instructor
        JOIN `tabUser` u
          ON u.name = COALESCE(NULLIF(sgi.user_id, ''), NULLIF(ins.linked_user_id, ''))
         AND u.enabled = 1
        WHERE sgs.student = %(student)s
          AND sg.academic_year = %(ay)s
          AND IFNULL(sg.status, 'Active') = 'Active'
          AND IFNULL(sgs.active, 1) = 1
        """,
            {"student": student, "ay": ay},
        )
        or []
    )
    return [r[0] for r in rows]


# ─────────────────────────────────────────────────────────────────────────────


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def users_with_role(doctype, txt, searchfield, start, page_len, filters):
    params = filters or {}
    roles = params.get("roles") or params.get("role") or ["Counselor"]
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",") if r.strip()] or ["Counselor"]

    return frappe.db.sql(
        """
        SELECT u.name, u.full_name
        FROM `tabUser` u
        WHERE u.enabled = 1
          AND EXISTS (
              SELECT 1 FROM `tabHas Role` hr
              WHERE hr.parent = u.name AND hr.role IN %(roles)s
          )
          AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
        ORDER BY u.full_name, u.name
        LIMIT %(page_len)s OFFSET %(start)s
    """,
        {"roles": tuple(roles), "txt": f"%{txt or ''}%", "page_len": page_len, "start": start},
    )


# A) Teacher-facing list
@frappe.whitelist()
def get_student_support_guidance(student: str) -> list[dict]:
    if not student:
        return []

    # --- permission guard unchanged (keep your current version) ---
    user = frappe.session.user
    user_roles = set(frappe.get_roles(user))
    if not ({"Counselor", "Academic Admin", "System Manager"} & user_roles):
        open_case_ays = frappe.db.sql(
            """
            SELECT DISTINCT IFNULL(rc.academic_year, '')
            FROM `tabReferral Case` rc
            WHERE rc.student = %(student)s
              AND IFNULL(rc.case_status, 'Open') != 'Closed'
            """,
            {"student": student},
        )
        ays = [row[0] for row in (open_case_ays or []) if row and row[0]]
        teachers = {u for ay in ays for u in _get_teachers_of_record(student, ay)}
        if user not in teachers:
            frappe.throw(_("You are not permitted to view support guidance for this student."), frappe.PermissionError)

    # --- include both Open & In Progress ---
    rows = frappe.db.sql(
        """
        SELECT e.name, e.entry_datetime, e.summary, e.assignee, e.status, e.author, rc.name AS case_name
        FROM `tabReferral Case Entry` e
        JOIN `tabReferral Case` rc ON rc.name = e.parent
        WHERE rc.student = %(student)s
          AND e.entry_type = 'Student Support Guidance'
          AND IFNULL(e.is_published, 0) = 1
          AND IFNULL(e.status, 'Open') IN ('Open','In Progress')
          AND IFNULL(rc.case_status, 'Open') != 'Closed'
        ORDER BY e.entry_datetime DESC
        """,
        {"student": student},
        as_dict=True,
    )
    return rows or []


# B) Number card / button gate
@frappe.whitelist()
def card_open_published_guidance(student: str | None = None, silent: int | bool = 0) -> dict:
    user = frappe.session.user
    roles = set(frappe.get_roles(user))
    is_triager = bool({"Counselor", "Academic Admin", "System Manager"} & roles)
    params = {"etype": "Student Support Guidance"}

    def _sql_count(where_extra: str, qparams: dict) -> int:
        row = frappe.db.sql(
            f"""
            SELECT COUNT(1)
            FROM `tabReferral Case Entry` e
            JOIN `tabReferral Case` rc ON rc.name = e.parent
            WHERE e.entry_type = %(etype)s
              AND IFNULL(e.is_published, 0) = 1
              AND IFNULL(e.status, 'Open') IN ('Open','In Progress')
              AND IFNULL(rc.case_status, 'Open') != 'Closed'
              {where_extra}
            """,
            {**params, **qparams},
        )
        return int(row[0][0]) if row else 0

    if student:
        if not is_triager:
            open_case_ays = (
                frappe.db.sql(
                    """
                SELECT DISTINCT IFNULL(rc.academic_year, '')
                FROM `tabReferral Case` rc
                WHERE rc.student = %(student)s
                  AND IFNULL(rc.case_status, 'Open') != 'Closed'
                """,
                    {"student": student},
                )
                or []
            )
            ays = [r[0] for r in open_case_ays if r and r[0]]
            allowed = any(user in set(_get_teachers_of_record(student, ay)) for ay in ays)
            if not allowed:
                # 👇 NEW: silent mode for button-eligibility probe on the Student form
                if cint(silent):
                    return {"value": 0, "fieldtype": "Int"}
                # Default behavior unchanged for dashboards/number cards
                frappe.throw(
                    _("You are not permitted to view support guidance for this student."), frappe.PermissionError
                )

        return {"value": _sql_count("AND rc.student = %(student)s", {"student": student}), "fieldtype": "Int"}

    if is_triager:
        return {"value": _sql_count("", {}), "fieldtype": "Int"}

    # teacher-wide view (unchanged)
    val = frappe.db.sql(
        """
        SELECT COUNT(1)
        FROM `tabReferral Case Entry` e
        JOIN `tabReferral Case` rc ON rc.name = e.parent
        WHERE e.entry_type = %(etype)s
          AND IFNULL(e.is_published, 0) = 1
          AND IFNULL(e.status, 'Open') IN ('Open','In Progress')
          AND IFNULL(rc.case_status, 'Open') != 'Closed'
          AND EXISTS (
              SELECT 1
              FROM `tabStudent Group` sg2
              JOIN `tabStudent Group Student` sgs2 ON sgs2.parent = sg2.name AND IFNULL(sgs2.active, 1) = 1
              JOIN `tabStudent Group Instructor` sgi2 ON sgi2.parent = sg2.name
              LEFT JOIN `tabInstructor` ins2 ON ins2.name = sgi2.instructor
              JOIN `tabUser` u2
                 ON u2.name = COALESCE(NULLIF(sgi2.user_id, ''), NULLIF(ins2.linked_user_id, ''))
                AND u2.enabled = 1
              WHERE u2.name = %(user)s
                AND sg2.academic_year = IFNULL(rc.academic_year, sg2.academic_year)
                AND sgs2.student = rc.student
          )
        """,
        {"etype": "Student Support Guidance", "user": user},
    )
    return {"value": int(val[0][0]) if val else 0, "fieldtype": "Int"}


def on_doctype_update():
    frappe.db.add_index("Referral Case", ["case_manager"])
    frappe.db.add_index("Referral Case", ["student"])
    frappe.db.add_index("Referral Case", ["school"])
    frappe.db.add_index("Referral Case Entry", ["entry_type", "is_published", "status"])

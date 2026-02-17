# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/student_log/student_log.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, get_datetime
from frappe.utils.nestedset import get_descendants_of

# Try native assign/remove; fall back to direct ToDo updates if unavailable
try:
    from frappe.desk.form.assign_to import add as assign_add
    from frappe.desk.form.assign_to import remove as assign_remove
except Exception:
    assign_add = None
    assign_remove = None


class StudentLog(Document):
    # ---------------------------------------------------------------------
    # Status & timeline helpers
    # ---------------------------------------------------------------------

    def _apply_status(self, new_status, reason=None, write_immediately=False):
        """
        Update status and (optionally) log a concise timeline comment.

        No caching: comments are added immediately when the doc exists; skipped on new docs.
        Suppresses comment spam for:
        - 'recomputed on validate'
        - '(re)assignment'
        - 'on submit'
        """
        # Read previous safely (DB for existing, in-memory for new)
        prev = (
            frappe.db.get_value(self.doctype, self.name, "follow_up_status")
            if self.name and not self.is_new()
            else self.follow_up_status
        )

        # No-op if nothing changes
        if prev == new_status:
            # still normalize in-memory for new docs
            if self.is_new():
                self.follow_up_status = new_status
            return

        # Apply the new status
        if self.is_new():
            self.follow_up_status = new_status
        else:
            self.db_set("follow_up_status", new_status)

        # Decide whether to emit a comment
        reason_key = (reason or "").strip().lower()
        if reason_key in {"recomputed on validate", "(re)assignment", "on submit"}:
            return  # quiet update; no timeline comment

        # If the doc doesn't exist yet, skip timeline (no cache)
        if self.is_new():
            return

        # Compose and emit immediately
        msg = f"Follow-up status: {prev or '—'} → {new_status or '—'}"
        if reason:
            msg += f" ({reason})"
        try:
            self.add_comment("Info", _(msg))
        except Exception:
            pass

    def _compute_follow_up_status(self):
        """
        Derive status from current DB state under the new semantics:
        - None            → follow-up not required or no clear state
        - "Open"          → exactly one open ToDo exists and no follow-ups yet
        - "In Progress"   → at least one follow-up exists (draft or submitted)
        - "Completed"     → preserved only if explicitly set (author/admin action)
        Notes:
        - Submitting a follow-up does NOT auto-complete the log anymore.
        """
        # If follow-up isn't required or the doc isn't saved yet, no derived status
        if not frappe.utils.cint(self.requires_follow_up) or not self.name:
            return None

        # Preserve explicit terminal state
        if (self.follow_up_status or "").lower() == "completed":
            return "Completed"

        # Any follow-up (draft or submitted) means work is/was happening → In Progress
        if frappe.db.exists("Student Log Follow Up", {"student_log": self.name}):
            return "In Progress"

        # Otherwise, if exactly one open ToDo exists, we're Open
        open_assignees = frappe.get_all(
            "ToDo", filters={"reference_type": "Student Log", "reference_name": self.name, "status": "Open"}, limit=2
        )
        return "Open" if len(open_assignees) == 1 else None

    # ---------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------
    def validate(self):
        """
        Pre-submit assignment support:
        - If requires_follow_up = 1 and follow_up_person is set before submit,
                ensure exactly one open ToDo exists for that user (single-assignee policy).
        - Enforce role from Next Step → associated_role (if provided).
        - Mirror current open assignee back to follow_up_person.
        - When requires_follow_up = 0 (pre-submit), mark status Completed quietly.
        - Derive status (timeline comments suppressed for auto reasons).
        """
        if cint(self.requires_follow_up):
            if not self.next_step:
                frappe.throw(_("Please select a next step."))

            # Use 'associated_role' (per your Next Step JSON)
            expected_role = None
            if self.next_step:
                expected_role = frappe.get_value("Student Log Next Step", self.next_step, "associated_role")

            # If a person is chosen pre-submit, ensure ToDo reflects that (single open)
            if self.follow_up_person and not self.is_new():
                opens = self._open_assignees()
                if not opens:
                    self._assign_to(self.follow_up_person)
                elif opens != [self.follow_up_person]:
                    self._unassign()
                    self._assign_to(self.follow_up_person)

            # Mirror current open assignee → follow_up_person
            current = self._current_assignee()
            self.follow_up_person = current or self.follow_up_person

            # Role guard if both next_step role and person exist
            if expected_role and self.follow_up_person:
                has_role = frappe.db.exists("Has Role", {"parent": self.follow_up_person, "role": expected_role})
                if not has_role:
                    frappe.throw(
                        _(f"Follow-up person '{self.follow_up_person}' does not have required role '{expected_role}'.")
                    )
            # Derive from current DB state
            derived = self._compute_follow_up_status()

        else:
            # Follow-up not required
            self._unassign()
            self.follow_up_person = None
            self.next_step = None

            # Do NOT force status during draft; let on_submit() finalize to 'Completed'
            if self.docstatus == 0:
                derived = None  # keep unset in draft to avoid illegal transition
            else:
                # For submitted edits (rare), leave status untouched here.
                derived = self.follow_up_status

        # Apply derived status (suppresses timeline via reason)
        self._apply_status(derived, reason="recomputed on validate", write_immediately=False)

        self._ensure_delivery_context()

        # Infer school from program if missing
        if not self.school:
            self.school = self._resolve_school()

        self._assert_followup_transition_and_immutability()

    def on_submit(self):
        """
        Submission invariants for the Student Log itself:
        - If requires_follow_up = 0, force status to 'Completed' and skip follow-up checks.
        - If requires_follow_up = 1, exactly one open assignment must exist.
        - Mirror that assignee into follow_up_person.
        - Recompute status; timeline comment is suppressed via _apply_status() reason.
        """
        if not cint(self.requires_follow_up):
            # Directly mark as Completed on submit (idempotent, quiet)
            if (self.follow_up_status or "").lower() != "completed":
                self.db_set("follow_up_status", "Completed")
            return

        opens = self._open_assignees()

        # Edge case: creator picked follow_up_person pre-submit but no assignment exists yet
        if not opens and self.follow_up_person:
            self._assign_to(self.follow_up_person)
            opens = self._open_assignees()

        if len(opens) != 1:
            frappe.throw(_("Exactly one assignee is required before submit."))

        self.follow_up_person = opens[0]
        self._apply_status(self._compute_follow_up_status(), reason="on submit", write_immediately=False)

    # ---------------------------------------------------------------------
    # Validation helpers
    # ---------------------------------------------------------------------
    def _assert_followup_transition_and_immutability(self):
        """Enforce legal status transitions and lock core fields once Completed."""
        old = self.get_doc_before_save() or frappe._dict()

        old_status = (old.get("follow_up_status") or "").lower()
        new_status = (self.follow_up_status or "").lower()

        # Allowed transitions (Completed is terminal; reopen handled elsewhere)
        allowed = {
            None: {"open", "in progress"},
            "": {"open", "in progress"},
            "open": {"in progress", "completed"},
            "in progress": {"completed"},
            "completed": set(),
        }

        # Normalize key for None/empty
        old_key = old_status if old_status else None
        if new_status != old_status:
            if old_key not in allowed or new_status not in allowed[old_key]:
                frappe.throw(
                    _("Illegal follow-up status change: {0} → {1}").format(old_status or "None", new_status or "None"),
                    title=_("Invalid Transition"),
                )

        # Once Completed, lock core follow-up fields
        if (old_status == "completed") or (new_status == "completed" and old_status != "completed"):
            locked_fields = {
                "requires_follow_up",
                "next_step",
                "follow_up_role",
                "follow_up_person",
                "program",  # optional: protect context
                "academic_year",  # optional: protect context
            }
            for f in locked_fields:
                if old.get(f) != self.get(f):
                    frappe.throw(
                        _("Field {0} cannot be changed after the log is Completed.").format(f),
                        title=_("Locked After Completion"),
                    )

    def _resolve_school(self) -> str | None:
        """Prefer Program Offering.school, else Program Enrollment.school (same AY), else AY.school."""
        # A) Program Offering → school (authoritative)
        if getattr(self, "program_offering", None):
            s = frappe.db.get_value("Program Offering", self.program_offering, "school")
            if s:
                return s  # Program Offering has required School field.  :contentReference[oaicite:0]{index=0}

        # B) Program Enrollment → school (same AY; optionally same offering)
        if self.student and self.academic_year:
            filters = {
                "student": self.student,
                "academic_year": self.academic_year,
                "archived": ["in", (0, None)],
            }
            # if the log points to a specific offering, keep it tight
            if getattr(self, "program_offering", None):
                filters["program_offering"] = self.program_offering

            pe = frappe.get_all(
                "Program Enrollment",
                filters=filters,
                fields=["school"],
                limit=1,
                order_by="modified desc",
            )
            if pe and pe[0].get("school"):
                return pe[0]["school"]  # Program Enrollment carries School.  :contentReference[oaicite:1]{index=1}

        # C) Academic Year → school (last fallback)
        if self.academic_year:
            return frappe.db.get_value("Academic Year", self.academic_year, "school")

        return None

    def _ensure_delivery_context(self):
        """
        Fill Program, Academic Year, Program Offering, and School from the student's
        active Program Enrollment when any is missing. This keeps the log anchored to
        the real delivery context without relying on Program.school (legacy).
        """
        need_program = not getattr(self, "program", None)
        need_ay = not getattr(self, "academic_year", None)
        need_po = not getattr(self, "program_offering", None)
        need_school = not getattr(self, "school", None)

        if not (need_program or need_ay or need_po or need_school):
            return

        if not self.student:
            return

        ctx = get_active_program_enrollment(self.student) or {}
        # ctx may be frappe._dict or dict
        prog = ctx.get("program")
        ay = ctx.get("academic_year")
        po = ctx.get("program_offering")
        school = ctx.get("school")

        updates = {}
        if need_program and prog:
            updates["program"] = prog
        if need_ay and ay:
            updates["academic_year"] = ay
        if need_po and po:
            updates["program_offering"] = po
        if need_school and school:
            updates["school"] = school

        # in-memory updates; let normal save flow persist
        if updates:
            self.update(updates)

    # ---------------------------------------------------------------------
    # Assignment helpers
    # ---------------------------------------------------------------------
    def _assign_to(self, user):
        if not user:
            return

        # Was there already an OPEN assignee before we assign?
        had_open = frappe.db.exists(
            "ToDo",
            {
                "reference_type": self.doctype,
                "reference_name": self.name,
                "status": "Open",
            },
        )

        # due date from School.default_follow_up_due_in_days (fallback 5)
        due_days = 5
        if self.program:
            # due date from School.default_follow_up_due_in_days (fallback 5)
            school = self.school or self._resolve_school()
            due_days = frappe.get_value("School", school, "default_follow_up_due_in_days") or 5
            due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))

        # Create/ensure a single OPEN ToDo for the assignee
        desc = f"Follow up on the Student Log for {self.student_name}"
        if assign_add:
            assign_add(
                {
                    "doctype": self.doctype,
                    "name": self.name,
                    "assign_to": [user],
                    "description": desc,
                    "due_date": due_date,
                }
            )
        else:
            todo = frappe.new_doc("ToDo")
            todo.update(
                {
                    "owner": user,
                    "allocated_to": user,
                    "reference_type": self.doctype,
                    "reference_name": self.name,
                    "description": desc,
                    "date": due_date,
                    "status": "Open",
                    "priority": "Medium",
                }
            )
            todo.insert(ignore_permissions=True)

        # Emit ONE clean "initial assignment" timeline note (not on reassign)
        if not had_open:
            try:
                actor = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
                target = frappe.utils.get_fullname(user) or user
                content = _("{} assigned {}: Follow up on the Student Log for {}").format(
                    actor, target, self.student_name or self.name
                )
                frappe.get_doc(
                    {
                        "doctype": "Comment",
                        "comment_type": "Info",
                        "reference_doctype": self.doctype,
                        "reference_name": self.name,
                        "content": content,
                    }
                ).insert(ignore_permissions=True)
            except Exception:
                pass

    def _unassign(self, user=None):
        assignees = self._open_assignees()
        targets = [user] if user else assignees
        for u in targets:
            if assign_remove:
                assign_remove(self.doctype, self.name, u)
            else:
                frappe.db.set_value(
                    "ToDo",
                    {"reference_type": self.doctype, "reference_name": self.name, "allocated_to": u, "status": "Open"},
                    "status",
                    "Closed",
                )

    def _current_assignee(self):
        users = self._open_assignees()
        return users[0] if users else None

    def _open_assignees(self):
        rows = frappe.get_all(
            "ToDo",
            filters={"reference_type": self.doctype, "reference_name": self.name, "status": "Open"},
            fields=["allocated_to"],
        )
        return [r.allocated_to for r in rows]

    def _fullname(self, user):
        return frappe.utils.get_fullname(user) or user


# ---------- WHITELISTED HELPERS (KEPT) ----------
@frappe.whitelist()
def get_employee_data(employee_name=None):
    """
    If employee_name is given, return that employee's details.
    Otherwise, return the current user's employee details.
    """
    if employee_name:
        employee = frappe.db.get_value(
            "Employee", {"name": employee_name}, ["name", "employee_full_name"], as_dict=True
        )
    else:
        employee = frappe.db.get_value(
            "Employee", {"user_id": frappe.session.user}, ["name", "employee_full_name"], as_dict=True
        )
    return employee or {}


@frappe.whitelist()
def get_active_program_enrollment(student):
    if not student:
        return {}
    today = frappe.utils.today()
    pe = frappe.db.sql(
        """
		SELECT
			pe.name,
			pe.program,
			pe.academic_year,
			pe.program_offering,     -- NEW
			pe.school                -- NEW (authoritative delivery school)
		FROM `tabProgram Enrollment` pe
		JOIN `tabAcademic Year` ay ON pe.academic_year = ay.name
		WHERE pe.student = %s
		  AND %s BETWEEN ay.year_start_date AND ay.year_end_date
		  AND (pe.archived = 0 OR pe.archived IS NULL)
		ORDER BY ay.year_start_date DESC
		LIMIT 1
	""",
        (student, today),
        as_dict=True,
    )
    return pe[0] if pe else {}


@frappe.whitelist()
def get_follow_up_role_from_next_step(next_step):
    """
    Return the role associated with the selected Next Step.
    Used to role-filter the follow_up_person picker (pre-submit assignment).
    """
    return frappe.get_value("Student Log Next Step", next_step, "associated_role")


# ---------- assign/reassign endpoint (owner OR Academic Admin OR current assignee) ----------
@frappe.whitelist()
def assign_follow_up(log_name: str, user: str):
    """
    Efficient (re)assignment:
    - Blocks when log is 'Completed'
    - Branch guard: assignee must be within school subtree
    - Role guard (target): assignee must have follow_up_role (fallback 'Academic Staff')
    - Perms (actor): Academic Admin OR log author OR current assignee OR user with follow_up_role
    - Bulk-closes existing OPEN ToDos; inserts one new ToDo
    - Mirrors follow_up_person; recomputes status via DB (no full doc loads)
    """
    if not (log_name and user):
        frappe.throw(_("Missing parameters."))

    # Minimal parent fetch
    sl = frappe.db.get_value(
        "Student Log",
        log_name,
        ["name", "owner", "school", "student_name", "follow_up_status", "follow_up_role"],
        as_dict=True,
    )
    if not sl:
        frappe.throw(_("Student Log not found: {0}").format(log_name))

    # Completed logs cannot be (re)assigned
    if (sl.follow_up_status or "").lower() == "completed":
        frappe.throw(
            _("This Student Log is already <b>Completed</b> and cannot be (re)assigned."),
            title=_("Follow-Up Completed"),
        )

    # Branch guard: assignee must cover log.school (user default school or Employee.school)
    assignee_anchor = frappe.defaults.get_user_default("school", user) or frappe.db.get_value(
        "Employee", {"user_id": user}, "school"
    )
    if not assignee_anchor:
        frappe.throw(_("Assignee has no School set (User Default or Employee.school)."), title=_("Missing School"))

    ok = frappe.db.sql(
        """
		SELECT 1
		FROM `tabSchool` s1
		JOIN `tabSchool` s2
			ON s2.lft >= s1.lft AND s2.rgt <= s1.rgt
		WHERE s1.name = %s AND s2.name = %s
		LIMIT 1
		""",
        (assignee_anchor, sl.school),
    )
    if not ok:
        frappe.throw(
            _("Assignee's school branch ({0}) does not include the log's school ({1}).").format(
                assignee_anchor, sl.school
            ),
            title=_("Outside School Branch"),
        )

    # Role guard (target): assignee must have required role (fallback 'Academic Staff')
    required_role = sl.follow_up_role or "Academic Staff"
    if required_role and required_role not in set(frappe.get_roles(user)):
        frappe.throw(_("Assignee must have the role: {0}.").format(required_role), title=_("Role Mismatch"))

    # Permission (actor): author OR Academic Admin OR current assignee OR user with the associated role
    roles_current = set(frappe.get_roles())
    is_admin = "Academic Admin" in roles_current
    is_author = frappe.session.user == sl.owner
    current_assignee = frappe.db.get_value(
        "ToDo",
        {"reference_type": "Student Log", "reference_name": sl.name, "status": "Open"},
        "allocated_to",
    )
    is_current_assignee = bool(current_assignee and current_assignee == frappe.session.user)
    has_associated_role = required_role in roles_current

    allowed = is_admin or is_author or is_current_assignee or has_associated_role
    if not allowed:
        frappe.throw(_("Not permitted to (re)assign this Student Log."))

    # Keep previous single open assignee (for timeline message); then bulk-close all opens
    prev_user = current_assignee
    frappe.db.sql(
        """
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = 'Student Log'
		  AND reference_name = %s
		  AND status = 'Open'
		""",
        (sl.name,),
    )

    # Create new OPEN ToDo for assignee (lean insert)
    due_days = frappe.db.get_value("School", sl.school, "default_follow_up_due_in_days") or 5
    due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))
    frappe.get_doc(
        {
            "doctype": "ToDo",
            "allocated_to": user,
            "reference_type": "Student Log",
            "reference_name": sl.name,
            "description": f"Follow up on Student Log for {sl.student_name or sl.name}",
            "date": due_date,
            "status": "Open",
            "priority": "Medium",
        }
    ).insert(ignore_permissions=True)

    # Mirror assignee on the parent
    frappe.db.set_value("Student Log", sl.name, "follow_up_person", user)

    # Recompute status cheaply:
    # any follow-up rows → In Progress; else with open ToDo → Open
    has_followups = bool(frappe.db.exists("Student Log Follow Up", {"student_log": sl.name}))
    new_status = "In Progress" if has_followups else "Open"
    if (sl.follow_up_status or "") != new_status:
        frappe.db.set_value("Student Log", sl.name, "follow_up_status", new_status)

    # Timeline note only for true reassignment Old → New
    if prev_user and prev_user != user:
        try:
            prev_full = frappe.utils.get_fullname(prev_user) or prev_user
            new_full = frappe.utils.get_fullname(user) or user
            frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": "Student Log",
                    "reference_name": sl.name,
                    "content": _("Reassigned: {0} → {1}").format(prev_full, new_full),
                }
            ).insert(ignore_permissions=True)
        except Exception:
            pass

    return {"ok": True, "assigned_to": user, "status": new_status}


# ---------- scheduler: In Progress → Completed ----------
def auto_close_completed_logs():
    """
    Daily job: move 'In Progress' → 'Completed' after N days of inactivity.
    - Only affects logs where follow_up_status = 'In Progress'
    - Does NOT touch 'Open' logs
    - Closes any OPEN ToDos referencing those logs
    - Adds a concise audit comment per log
    Returns: number of logs completed.
    """
    today = frappe.utils.today()

    rows = frappe.get_all(
        "Student Log",
        filters={"follow_up_status": "In Progress", "auto_close_after_days": [">", 0]},
        fields=["name", "modified", "auto_close_after_days"],
    )

    if not rows:
        return 0

    eligible = []
    threshold_by_log = {}
    for r in rows:
        last_updated = get_datetime(r.modified)
        if date_diff(today, last_updated.date()) >= r.auto_close_after_days:
            eligible.append(r.name)
            threshold_by_log[r.name] = r.auto_close_after_days

    if not eligible:
        return 0

    # 1) Close any OPEN ToDos for these logs in a single SQL
    frappe.db.sql(
        f"""
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = 'Student Log'
		  AND status = 'Open'
		  AND reference_name IN ({", ".join(["%s"] * len(eligible))})
		""",
        tuple(eligible),
    )

    # 2) Update status → Completed (use set_value per row to update 'modified' properly)
    for name in eligible:
        frappe.db.set_value("Student Log", name, "follow_up_status", "Completed")

    # 3) Add one concise audit comment per log (idempotent)
    for name in eligible:
        msg = f"Auto-completed after {threshold_by_log.get(name, 0)} days of inactivity."
        already = frappe.db.exists(
            "Comment",
            {
                "reference_doctype": "Student Log",
                "reference_name": name,
                "comment_type": "Info",
                "content": ("like", "Auto-completed after%"),
            },
        )
        if already:
            continue
        try:
            frappe.get_doc(
                {
                    "doctype": "Comment",
                    "comment_type": "Info",
                    "reference_doctype": "Student Log",
                    "reference_name": name,
                    "content": msg,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            pass

    return len(eligible)


@frappe.whitelist()
def complete_follow_up(follow_up_name: str):
    """
    Deprecated: completing a Student Log from a follow-up is no longer supported.
    """
    frappe.throw(
        _(
            "Completing a Student Log from a follow-up is no longer supported. "
            "Please complete the Student Log directly (author/admin)."
        )
    )


@frappe.whitelist()
def complete_log(log_name: str):
    """
    Mark the Student Log as 'Completed'.
    Permissions: log author (owner) OR Academic Admin OR current OPEN ToDo assignee.
    Effects:
    - Set follow_up_status = 'Completed'
    - Close any OPEN ToDos referencing this log
    - Add concise timeline entry
    """
    if not log_name:
        frappe.throw(_("Missing Student Log name."))

    log_row = frappe.db.get_value(
        "Student Log", log_name, ["name", "owner", "student_name", "follow_up_status"], as_dict=True
    )
    if not log_row:
        frappe.throw(_("Student Log not found: {0}").format(log_name))

    roles = set(frappe.get_roles())
    is_admin = "Academic Admin" in roles
    is_author = frappe.session.user == log_row.owner

    current_open_assignee = frappe.db.get_value(
        "ToDo", {"reference_type": "Student Log", "reference_name": log_row.name, "status": "Open"}, "allocated_to"
    )
    is_current_assignee = bool(current_open_assignee and current_open_assignee == frappe.session.user)

    if not (is_admin or is_author or is_current_assignee):
        frappe.throw(_("Only the author, an Academic Admin, or the current assignee can mark this log as Completed."))

    # Idempotent
    if (log_row.follow_up_status or "").lower() == "completed":
        return {"ok": True, "status": "Completed", "log": log_row.name}

    # 1) Update status
    frappe.db.set_value("Student Log", log_row.name, "follow_up_status", "Completed")

    # 2) Close all OPEN ToDos
    frappe.db.sql(
        """
		UPDATE `tabToDo`
		SET status = 'Closed'
		WHERE reference_type = %s AND reference_name = %s AND status = 'Open'
		""",
        ("Student Log", log_row.name),
    )

    # 3) Timeline entry
    try:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Student Log",
                "reference_name": log_row.name,
                "content": _("Log marked <b>Completed</b> by {user}.").format(
                    user=frappe.utils.get_fullname(frappe.session.user)
                ),
            }
        ).insert(ignore_permissions=True)
    except Exception:
        pass

    return {"ok": True, "status": "Completed", "log": log_row.name}


@frappe.whitelist()
def reopen_log(log_name: str):
    """
    Reopen a 'Completed' Student Log → 'In Progress'.
    Permissions: Academic Admin OR log author (owner).
    Effects:
    - Set follow_up_status = 'In Progress'
    - If follow_up_person is set and no OPEN ToDo exists, create one with a sane due date
    - Add concise timeline entry
    - Notify follow_up_person (bell + realtime) if present
    """
    if not log_name:
        frappe.throw(_("Missing Student Log name."))

    # Minimal fetch
    row = frappe.db.get_value(
        "Student Log",
        log_name,
        ["name", "owner", "school", "student_name", "follow_up_status", "follow_up_person"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Log not found: {0}").format(log_name))

    # Only from Completed
    if (row.follow_up_status or "").lower() != "completed":
        frappe.throw(_("Only logs in <b>Completed</b> status can be reopened."))

    # Permission: author or Academic Admin
    roles = set(frappe.get_roles())
    is_admin = "Academic Admin" in roles
    is_author = frappe.session.user == row.owner
    if not (is_admin or is_author):
        frappe.throw(_("Only the log author or an Academic Admin can reopen this log."))

    # 1) Flip status → In Progress (single write)
    frappe.db.set_value("Student Log", row.name, "follow_up_status", "In Progress")

    # 2) Ensure an OPEN ToDo exists for current follow_up_person (if set)
    if row.follow_up_person:
        has_open = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Student Log",
                "reference_name": row.name,
                "allocated_to": row.follow_up_person,
                "status": "Open",
            },
            "name",
        )
        if not has_open:
            due_days = frappe.db.get_value("School", row.school, "default_follow_up_due_in_days") or 5
            due_date = frappe.utils.add_days(frappe.utils.today(), int(due_days))
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "allocated_to": row.follow_up_person,
                    "reference_type": "Student Log",
                    "reference_name": row.name,
                    "description": f"Follow up on Student Log for {row.student_name or row.name}",
                    "date": due_date,
                    "status": "Open",
                    "priority": "Medium",
                }
            ).insert(ignore_permissions=True)

    # 3) Timeline: concise audit note
    try:
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": "Student Log",
                "reference_name": row.name,
                "content": _("Log <b>reopened</b> by {user}.").format(
                    user=frappe.utils.get_fullname(frappe.session.user)
                ),
            }
        ).insert(ignore_permissions=True)
    except Exception:
        pass

    # 4) Notify the follow_up_person (if any)
    if row.follow_up_person and row.follow_up_person != frappe.session.user:
        try:
            # Bell notification
            frappe.get_doc(
                {
                    "doctype": "Notification Log",
                    "subject": _("Log reopened"),
                    "email_content": _("A Student Log you’re assigned to was reopened. Click to review."),
                    "type": "Alert",
                    "for_user": row.follow_up_person,
                    "from_user": frappe.session.user,
                    "document_type": "Student Log",
                    "document_name": row.name,
                }
            ).insert(ignore_permissions=True)
        except Exception:
            # Realtime fallback
            try:
                frappe.publish_realtime(
                    event="inbox_notification",
                    message={
                        "type": "Alert",
                        "subject": _("Log reopened"),
                        "message": _("A Student Log you’re assigned to was reopened. Click to review."),
                        "reference_doctype": "Student Log",
                        "reference_name": row.name,
                    },
                    user=row.follow_up_person,
                )
            except Exception:
                pass

    return {"ok": True, "status": "In Progress", "log": row.name}


def _user_is_pastoral_lead_for_student(user: str, student: str) -> bool:
    """
    True if `user` is an instructor of at least one Pastoral Student Group
    that contains `student`.

    Pastoral scope is explicit: group_based_on == 'Pastoral' only.
    """
    if not user or not student:
        return False

    row = frappe.db.sql(
        """
		SELECT 1
		FROM `tabStudent Group Instructor` sgi
		INNER JOIN `tabStudent Group` sg
			ON sg.name = sgi.parent
		INNER JOIN `tabStudent Group Student` sgs
			ON sgs.parent = sg.name
		WHERE
			sgi.user_id = %(user)s
			AND sg.status = 'Active'
			AND sg.group_based_on = 'Pastoral'
			AND sgs.student = %(student)s
		LIMIT 1
		""",
        {"user": user, "student": student},
        as_dict=False,
    )
    return bool(row)


ADMIN_ROLES = {"System Manager", "Administrator"}
SCHOOL_OVERSIGHT_ROLES = {"Academic Admin", "Counsellor", "Learning Support"}
ACADEMIC_STAFF_ROLE = "Academic Staff"
PASTORAL_LEAD_ROLE = "Pastoral Lead"
CURRICULUM_COORDINATOR_ROLE = "Curriculum Coordinator"
ACCREDITATION_VISITOR_ROLE = "Accreditation Visitor"


def _get_user_employee(user: str) -> frappe._dict:
    if not user or user == "Guest":
        return frappe._dict()

    fields = ["name", "school"]
    if frappe.db.has_column("Employee", "default_school"):
        fields.insert(1, "default_school")

    return frappe.db.get_value("Employee", {"user_id": user}, fields, as_dict=True) or frappe._dict()


def _get_user_school_anchor(user: str) -> str | None:
    if not user or user == "Guest":
        return None
    default_school = frappe.defaults.get_user_default("school", user)
    if default_school:
        return default_school

    emp = _get_user_employee(user)
    return emp.get("default_school") or emp.get("school")


def _get_user_school_tree(user: str) -> list[str]:
    anchor = _get_user_school_anchor(user)
    if not anchor:
        return []
    return [anchor] + (get_descendants_of("School", anchor, ignore_permissions=True) or [])


def _is_accreditation_visitor_only(roles: set[str]) -> bool:
    return ACCREDITATION_VISITOR_ROLE in roles and not (roles - {ACCREDITATION_VISITOR_ROLE})


def _interpolate_sql_params(sql: str, params: dict) -> str:
    """Safely expand params for permission query conditions."""
    out = sql
    for key, val in (params or {}).items():
        placeholder = f"%({key})s"
        if isinstance(val, (list, tuple, set)):
            items = [frappe.db.escape(v) for v in val]
            repl = f"({', '.join(items)})" if items else "(NULL)"
        else:
            repl = frappe.db.escape(val)
        out = out.replace(placeholder, repl)
    return out


def get_student_log_visibility_predicate(
    user: str | None = None,
    table_alias: str = "`tabStudent Log`",
    allow_aggregate_only: bool = False,
) -> tuple[str, dict]:
    """
    Return (SQL, params) for Student Log visibility.

    - allow_aggregate_only: when True, Accreditation Visitor is scoped for aggregates
      (detail views must pass False).
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "0=1", {}

    roles = set(frappe.get_roles(user) or [])
    if roles & ADMIN_ROLES:
        return "1=1", {}

    if _is_accreditation_visitor_only(roles) and not allow_aggregate_only:
        return "0=1", {}

    conditions = []
    params = {"user": user}

    # Authorship / assignment are always visible
    conditions.append(f"{table_alias}.owner = %(user)s")
    conditions.append(f"{table_alias}.follow_up_person = %(user)s")

    # School-tree oversight
    if roles & SCHOOL_OVERSIGHT_ROLES or (_is_accreditation_visitor_only(roles) and allow_aggregate_only):
        allowed_schools = _get_user_school_tree(user)
        if allowed_schools:
            params["oversight_schools"] = tuple(allowed_schools)
            conditions.append(f"{table_alias}.school IN %(oversight_schools)s")

    # Pastoral Lead (group-scoped)
    if PASTORAL_LEAD_ROLE in roles:
        emp = _get_user_employee(user)
        params["employee"] = emp.get("name") or ""
        conditions.append(
            f"""
			EXISTS (
				SELECT 1
				FROM `tabStudent Group Student` sgs
				JOIN `tabStudent Group` sg ON sg.name = sgs.parent
				JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sg.name
				LEFT JOIN `tabInstructor` ins ON ins.name = sgi.instructor
				WHERE sgs.student = {table_alias}.student
				  AND IFNULL(sgs.active, 1) = 1
				  AND IFNULL(sg.status, 'Active') = 'Active'
				  AND sg.group_based_on = 'Pastoral'
				  AND sg.academic_year = {table_alias}.academic_year
				  AND (
					  sgi.user_id = %(user)s
					  OR ins.linked_user_id = %(user)s
					  OR sgi.employee = %(employee)s
				  )
			)
			"""
        )

    # Academic Staff (teaching context)
    if ACADEMIC_STAFF_ROLE in roles:
        emp = _get_user_employee(user)
        params["employee"] = emp.get("name") or params.get("employee") or ""
        conditions.append(
            f"""
			EXISTS (
				SELECT 1
				FROM `tabStudent Group Student` sgs
				JOIN `tabStudent Group` sg ON sg.name = sgs.parent
				JOIN `tabStudent Group Instructor` sgi ON sgi.parent = sg.name
				LEFT JOIN `tabInstructor` ins ON ins.name = sgi.instructor
				WHERE sgs.student = {table_alias}.student
				  AND IFNULL(sgs.active, 1) = 1
				  AND IFNULL(sg.status, 'Active') = 'Active'
				  AND sg.group_based_on != 'Pastoral'
				  AND sg.academic_year = {table_alias}.academic_year
				  AND (
					  sgi.user_id = %(user)s
					  OR ins.linked_user_id = %(user)s
					  OR sgi.employee = %(employee)s
				  )
			)
			"""
        )

    # Curriculum Coordinator (program oversight)
    if CURRICULUM_COORDINATOR_ROLE in roles:
        emp = _get_user_employee(user)
        params["employee"] = emp.get("name") or params.get("employee") or ""
        conditions.append(
            f"""
			EXISTS (
				SELECT 1
				FROM `tabProgram Coordinator` pc
				JOIN `tabProgram Enrollment` pe ON pe.program = pc.parent
				WHERE pc.parenttype = 'Program'
				  AND pc.parentfield = 'program_coordinators'
				  AND pc.coordinator = %(employee)s
				  AND pe.student = {table_alias}.student
				  AND pe.program = {table_alias}.program
				  AND IFNULL(pe.archived, 0) = 0
				  AND pe.academic_year = {table_alias}.academic_year
			)
			"""
        )

    if not conditions:
        return "0=1", {}

    return "(" + " OR ".join(conditions) + ")", params


def get_permission_query_conditions(user: str | None = None) -> str | None:
    sql, params = get_student_log_visibility_predicate(
        user=user, table_alias="`tabStudent Log`", allow_aggregate_only=False
    )
    return _interpolate_sql_params(sql, params)


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False

    roles = set(frappe.get_roles(user) or [])
    if roles & ADMIN_ROLES:
        return True

    if ptype in {"read", "select", "report"}:
        sql, params = get_student_log_visibility_predicate(user=user, table_alias="sl", allow_aggregate_only=False)
        if sql == "1=1":
            return True
        params = {**params, "name": doc.name}
        row = frappe.db.sql(
            f"SELECT 1 FROM `tabStudent Log` sl WHERE sl.name = %(name)s AND {sql} LIMIT 1",
            params,
        )
        return bool(row)

    # Write/submit/amend permissions are tighter than read.
    if roles & SCHOOL_OVERSIGHT_ROLES:
        return doc.school in set(_get_user_school_tree(user))

    return bool(doc.owner == user)


def on_doctype_update():
    frappe.db.add_index("Student Log", ["school"])

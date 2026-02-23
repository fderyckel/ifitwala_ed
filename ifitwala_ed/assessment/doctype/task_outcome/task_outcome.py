# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/task_outcome/task_outcome.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.assessment.task_outcome_service import resolve_grade_symbol


class TaskOutcome(Document):
    def before_validate(self):
        self._require_links()
        self._backfill_denorm_fields()
        self._guard_identity_mutation()
        self._guard_duplicate_outcome()

    def validate(self):
        self._validate_procedural_status()
        self._validate_status_coherence()
        self._enforce_is_complete()
        self._validate_official_grade()
        self._capture_official_changes()

    def on_update(self):
        self._log_official_changes()

    def _doc_meta(self):
        if not hasattr(self, "_outcome_meta"):
            self._outcome_meta = frappe.get_meta(self.doctype)
        return self._outcome_meta

    def _has_field(self, fieldname):
        return bool(self._doc_meta().get_field(fieldname))

    def _require_links(self):
        if not self.task_delivery:
            frappe.throw(_("Task Delivery is required for Task Outcome."))
        if not self.student:
            frappe.throw(_("Student is required for Task Outcome."))

    def _identity_fields(self):
        fields = [
            "task_delivery",
            "student",
            "task",
            "student_group",
            "course",
            "academic_year",
            "school",
        ]
        return [field for field in fields if self._has_field(field)]

    def _optional_denorm_fields(self):
        fields = []
        if self._has_field("grade_scale"):
            fields.append("grade_scale")
        return fields

    def _backfill_denorm_fields(self):
        required = self._identity_fields()
        optional = self._optional_denorm_fields()
        missing_required = [field for field in required if not getattr(self, field, None)]
        missing_optional = [field for field in optional if not getattr(self, field, None)]
        if not missing_required and not missing_optional:
            return

        delivery_fields = list({*required, *optional})
        if not delivery_fields:
            return

        delivery = (
            frappe.db.get_value(
                "Task Delivery",
                self.task_delivery,
                delivery_fields,
                as_dict=True,
            )
            or {}
        )

        for field in missing_required + missing_optional:
            if not getattr(self, field, None) and delivery.get(field):
                setattr(self, field, delivery.get(field))

        still_missing_required = [field for field in required if not getattr(self, field, None)]
        if still_missing_required:
            frappe.log_error(
                message=f"Task Outcome backfill failed for {self.name or '(new)'}: {still_missing_required}",
                title="Task Outcome Backfill Failure",
            )
            frappe.throw(
                _("Task Outcome is missing required context fields: {0}.").format(", ".join(still_missing_required))
            )

    def _guard_identity_mutation(self):
        if self.is_new():
            return

        fields = self._identity_fields() + self._optional_denorm_fields()
        if not fields:
            return

        previous = (
            frappe.db.get_value(
                "Task Outcome",
                self.name,
                fields,
                as_dict=True,
            )
            or {}
        )

        for field in fields:
            if previous.get(field) != getattr(self, field, None):
                frappe.throw(_("Cannot change {0} on an existing Task Outcome.").format(field.replace("_", " ")))

    def _guard_duplicate_outcome(self):
        if self.is_new() and self.task_delivery and self.student:
            existing = frappe.db.get_value(
                "Task Outcome",
                {"task_delivery": self.task_delivery, "student": self.student},
                "name",
            )
            if existing:
                frappe.throw(_("Task Outcome already exists for this student and delivery."))

    def _validate_procedural_status(self):
        status = self.procedural_status
        if not status:
            return

        if status == "Excused":
            if self.submission_status in ("Submitted", "Late", "Resubmitted"):
                frappe.throw(_("Excused outcomes cannot be marked as Submitted."))
            if (
                self.official_score not in (None, "")
                or (self.official_grade or "").strip()
                or (self._has_field("official_grade_value") and self.official_grade_value not in (None, ""))
            ):
                frappe.throw(_("Excused outcomes cannot carry an official score or grade."))
            return

        if status == "Extension Granted":
            if self.submission_status == "Late":
                frappe.throw(_("Extension Granted outcomes should not be marked Late."))
            return

    def _validate_status_coherence(self):
        delivery = self._get_delivery_flags()

        if delivery.get("requires_submission") and self.submission_status == "Not Submitted":
            if self.grading_status in ("Finalized", "Released") and not self.procedural_status:
                frappe.throw(_("Cannot finalize or release without a submission."))

        if self.grading_status == "Released" and delivery.get("require_grading"):
            if not self._has_official_result(delivery.get("grading_mode")):
                frappe.throw(_("Cannot release without an official result."))

    def _enforce_is_complete(self):
        if not self._has_field("is_complete"):
            return

        delivery_mode = self._get_delivery_flags().get("delivery_mode")
        finalized = self.grading_status in ("Finalized", "Released")

        if finalized:
            self.is_complete = 1
            return

        if delivery_mode == "Assign Only":
            self.is_complete = 1 if self.is_complete else 0
            return

        if self.is_complete:
            self.is_complete = 0

    def _validate_official_grade(self):
        if not self._has_field("official_grade"):
            return

        grade_symbol = (self.official_grade or "").strip()
        if not grade_symbol:
            if self._has_field("official_grade_value"):
                self.official_grade_value = None
            return

        if not self.grade_scale:
            frappe.throw(_("Grade Scale is required to set an Official Grade."))

        grade_value = resolve_grade_symbol(self.grade_scale, grade_symbol)

        if self._has_field("official_grade_value"):
            if self.official_grade_value not in (None, ""):
                try:
                    current_value = float(self.official_grade_value)
                except Exception:
                    current_value = None
                if current_value is None or abs(current_value - grade_value) > 1e-9:
                    frappe.throw(_("Official Grade Value is system-managed and must match the Grade Scale."))
            self.official_grade_value = grade_value

    def _has_official_result(self, grading_mode=None):
        if grading_mode in ("Completion", "Binary"):
            return self.is_complete is not None

        if grading_mode == "Criteria":
            rows = self.get("official_criteria") or []
            if rows:
                return True

        if self.official_score not in (None, ""):
            return True
        if (self.official_grade or "").strip():
            return True
        if (self.official_feedback or "").strip():
            return True
        return False

    def _get_delivery_flags(self):
        if not self.task_delivery:
            return {}
        fields = ["requires_submission", "require_grading", "grading_mode", "delivery_mode"]
        values = frappe.db.get_value("Task Delivery", self.task_delivery, fields, as_dict=True) or {}
        return values

    def _capture_official_changes(self):
        if self.flags.get("ignore_official_audit") or self.is_new():
            self._official_changes = []
            return

        fields = ["official_score", "official_grade", "official_feedback"]
        previous = (
            frappe.db.get_value(
                "Task Outcome",
                self.name,
                fields,
                as_dict=True,
            )
            or {}
        )

        def _normalize(field, value):
            if field in ("official_grade", "official_feedback"):
                return (value or "").strip()
            return value

        changes = []
        for field in fields:
            old = _normalize(field, previous.get(field))
            new = _normalize(field, getattr(self, field, None))
            if old != new:
                changes.append((field, previous.get(field), getattr(self, field, None)))

        self._official_changes = changes

    def _log_official_changes(self):
        changes = getattr(self, "_official_changes", [])
        if not changes:
            return

        lines = ["Official outcome edited directly:"]
        for field, old, new in changes:
            lines.append(f"- {field}: {old} -> {new}")

        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Info",
                "reference_doctype": self.doctype,
                "reference_name": self.name,
                "content": "\n".join(lines),
            }
        ).insert(ignore_permissions=True)


def on_doctype_update():
    _ensure_unique_index()


def _ensure_unique_index():
    table = "tabTask Outcome"
    index_name = "uniq_task_outcome_delivery_student"
    columns = ["task_delivery", "student"]

    rows = frappe.db.sql(
        "SHOW INDEX FROM `{}`".format(table),
        as_dict=True,
    )
    if _unique_index_exists(rows, columns):
        return

    existing = [row for row in rows if row.get("Key_name") == index_name]
    if existing:
        non_unique = existing[0].get("Non_unique")
        try:
            non_unique = int(non_unique)
        except Exception:
            non_unique = 1
        if non_unique != 0:
            frappe.throw("Task Outcome index exists but is not unique. Migration/installation is broken.")

    frappe.db.sql(f"ALTER TABLE `{table}` ADD UNIQUE INDEX `{index_name}` (`task_delivery`, `student`)")

    rows = frappe.db.sql(
        "SHOW INDEX FROM `{}`".format(table),
        as_dict=True,
    )
    if not _unique_index_exists(rows, columns):
        frappe.throw(
            "Task Outcome UNIQUE(task_delivery, student) index missing after migrate. Migration/installation is broken."
        )


def _unique_index_exists(rows, columns):
    index_map = {}
    for row in rows:
        key_name = row.get("Key_name")
        if not key_name:
            continue
        non_unique = row.get("Non_unique")
        try:
            non_unique = int(non_unique)
        except Exception:
            non_unique = 1
        if non_unique != 0:
            continue
        index_map.setdefault(key_name, []).append(row)

    for entries in index_map.values():
        ordered = sorted(entries, key=lambda r: int(r.get("Seq_in_index") or 0))
        cols = [row.get("Column_name") for row in ordered]
        if cols == columns:
            return True

    return False

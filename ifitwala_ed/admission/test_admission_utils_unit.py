from __future__ import annotations
import __future__

import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _admission_utils_module():
    assign_to = ModuleType("frappe.desk.form.assign_to")
    assign_to.add = lambda payload: None
    assign_to.remove = lambda **kwargs: None

    frappe_desk = ModuleType("frappe.desk")
    frappe_desk_form = ModuleType("frappe.desk.form")
    frappe_desk.form = frappe_desk_form
    frappe_desk_form.assign_to = assign_to

    nestedset = ModuleType("frappe.utils.nestedset")
    nestedset.get_ancestors_of = lambda *args, **kwargs: []
    nestedset.get_descendants_of = lambda *args, **kwargs: []

    policy_scope_utils = ModuleType("ifitwala_ed.governance.policy_scope_utils")
    policy_scope_utils.get_organization_ancestors_including_self = lambda *args, **kwargs: []
    policy_scope_utils.get_organization_descendants_including_self = lambda *args, **kwargs: []
    policy_scope_utils.get_school_ancestors_including_self = lambda *args, **kwargs: []
    policy_scope_utils.get_school_descendants_including_self = lambda *args, **kwargs: []

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_descendant_schools = lambda *args, **kwargs: []

    with stubbed_frappe(
        extra_modules={
            "frappe.desk": frappe_desk,
            "frappe.desk.form": frappe_desk_form,
            "frappe.desk.form.assign_to": assign_to,
            "frappe.utils.nestedset": nestedset,
            "ifitwala_ed.governance.policy_scope_utils": policy_scope_utils,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe_utils.add_days = lambda base, days: f"{base}+{days}"
        frappe_utils.cint = lambda value=0: int(value or 0)
        frappe_utils.get_datetime = lambda value: value
        frappe_utils.getdate = lambda value=None: value or "2026-04-23"
        frappe_utils.now = lambda: "2026-04-23 09:00:00"
        frappe_utils.now_datetime = lambda: "2026-04-23 09:00:00"
        frappe_utils.nowdate = lambda: "2026-04-23"
        frappe_utils.validate_email_address = lambda value, throw=False: value

        frappe.as_json = lambda value: str(value)
        frappe.logger = lambda *args, **kwargs: SimpleNamespace(
            info=lambda *a, **kw: None,
            exception=lambda *a, **kw: None,
        )
        frappe.validate_and_sanitize_search_inputs = lambda fn: fn
        frappe.utils = SimpleNamespace(
            formatdate=lambda value: value,
            get_link_to_form=lambda doctype, name: f"{doctype}:{name}",
        )

        module = ModuleType("ifitwala_ed.admission.admission_utils")
        module.__file__ = str(Path(__file__).with_name("admission_utils.py"))
        module.__package__ = "ifitwala_ed.admission"

        source = Path(module.__file__).read_text(encoding="utf-8")
        code = compile(
            source,
            module.__file__,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
        )
        exec(code, module.__dict__)

        yield module, frappe


class TestAdmissionUtilsUnit(TestCase):
    def test_assign_inquiry_does_not_backfill_first_contact_due_date_before_save(self):
        doc = SimpleNamespace(
            assigned_to="",
            first_contact_due_on=None,
            followup_due_on=None,
            workflow_state="New",
        )
        doc.mark_assigned = Mock(side_effect=lambda add_comment=False: setattr(doc, "workflow_state", "Assigned"))
        doc.save = Mock()
        doc.add_comment = Mock()

        with _admission_utils_module() as (module, frappe):
            frappe.get_doc = lambda doctype, name: doc
            frappe.get_cached_doc = lambda doctype: SimpleNamespace(
                first_contact_sla_days=7,
                followup_sla_days=2,
                todo_color="blue",
            )

            with (
                patch.object(module, "ensure_admissions_permission"),
                patch.object(module, "_validate_inquiry_assignee_scope"),
                patch.object(module, "_resolve_inquiry_assignment_lane_for_user", return_value="Admission"),
                patch.object(module, "_stamp_inquiry_lane_metrics_on_assignment"),
                patch.object(module, "_create_native_assignment", return_value=None),
                patch.object(module, "notify_user"),
                patch.object(module, "add_days", side_effect=lambda base, days: f"{base}+{days}") as add_days,
            ):
                module.assign_inquiry("Inquiry", "INQ-0001", "owner@example.com")

        self.assertEqual(add_days.call_count, 1)
        self.assertEqual(add_days.call_args.args, ("2026-04-23", 2))

    def test_reassign_inquiry_does_not_backfill_first_contact_due_date_before_save(self):
        doc = SimpleNamespace(
            assigned_to="current@example.com",
            first_contact_due_on=None,
            followup_due_on=None,
            workflow_state="Assigned",
        )
        doc.mark_assigned = Mock(side_effect=lambda add_comment=False: setattr(doc, "workflow_state", "Assigned"))
        doc.save = Mock()
        doc.add_comment = Mock()

        with _admission_utils_module() as (module, frappe):
            frappe.get_doc = lambda doctype, name: doc
            frappe.get_cached_doc = lambda doctype: SimpleNamespace(
                first_contact_sla_days=7,
                followup_sla_days=3,
                todo_color="blue",
            )

            with (
                patch.object(module, "ensure_admissions_permission"),
                patch.object(module, "_validate_inquiry_assignee_scope"),
                patch.object(module, "_resolve_inquiry_assignment_lane_for_user", return_value="Staff"),
                patch.object(module, "_stamp_inquiry_lane_metrics_on_assignment"),
                patch.object(module, "_create_native_assignment", return_value=None),
                patch.object(module, "notify_user"),
                patch.object(module, "remove_assignment"),
                patch.object(module, "add_days", side_effect=lambda base, days: f"{base}+{days}") as add_days,
            ):
                module.reassign_inquiry("Inquiry", "INQ-0002", "next@example.com")

        self.assertEqual(add_days.call_count, 1)
        self.assertEqual(add_days.call_args.args, ("2026-04-23", 3))

    def test_check_sla_breaches_only_updates_status_columns(self):
        sql_calls: list[str] = []

        @contextmanager
        def _lock(*args, **kwargs):
            yield

        with _admission_utils_module() as (module, frappe):
            frappe.db.table_exists = lambda doctype: doctype == "Inquiry"
            frappe.db.has_column = lambda doctype, column: (
                column
                in {
                    "workflow_state",
                    "sla_status",
                    "first_contact_due_on",
                    "followup_due_on",
                    "submitted_at",
                }
            )
            frappe.db.sql = lambda query, params=None, as_dict=False: sql_calls.append(query) or []
            frappe.db.commit = Mock()
            frappe.db.rollback = Mock()
            frappe.cache = lambda: SimpleNamespace(lock=_lock, set_value=lambda *args, **kwargs: None)

            summary = module.check_sla_breaches()

        self.assertEqual(len(sql_calls), 4)
        self.assertTrue(all("SET first_contact_due_on" not in query for query in sql_calls))
        self.assertEqual(
            summary["processed"], [{"doctype": "Inquiry", "first_contact_due_on": True, "followup_due_on": True}]
        )

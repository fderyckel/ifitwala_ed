# ifitwala_ed/hr/test_scheduler_dispatch.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry import (
    dispatch_process_expired_allocation,
    process_expired_allocation_chunk,
)
from ifitwala_ed.hr.utils import (
    _process_leave_encashment_rows,
    dispatch_allocate_earned_leaves,
    dispatch_generate_leave_encashment,
)


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyCache:
    def __init__(self):
        self.store = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def lock(self, key, timeout=15):
        return _DummyLock()


class TestSchedulerDispatch(TestCase):
    def test_dispatch_process_expired_allocation_enqueues_chunks(self):
        cache = _DummyCache()
        expired_rows = [
            frappe._dict({"name": "LAL-0001"}),
            frappe._dict({"name": "LAL-0002"}),
            frappe._dict({"name": "LAL-0003"}),
        ]

        with (
            patch(
                "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry._leave_expiry_scheduler_enabled",
                return_value=True,
            ),
            patch("ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry._get_expired_allocation_rows",
                return_value=expired_rows,
            ),
            patch("ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.frappe.enqueue") as enqueue,
        ):
            summary = dispatch_process_expired_allocation(chunk_size=2)

        self.assertEqual(summary["candidate_count"], 3)
        self.assertEqual(summary["chunk_count"], 2)
        self.assertEqual(enqueue.call_count, 2)
        self.assertEqual(enqueue.call_args_list[0].kwargs["allocation_names"], ["LAL-0001", "LAL-0002"])
        self.assertEqual(enqueue.call_args_list[1].kwargs["allocation_names"], ["LAL-0003"])

    def test_process_expired_allocation_chunk_uses_subset_rows(self):
        cache = _DummyCache()
        expired_rows = [frappe._dict({"name": "LAL-0001"})]

        with (
            patch("ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry._get_expired_allocation_rows",
                return_value=expired_rows,
            ) as get_rows,
            patch(
                "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.create_expiry_ledger_entry"
            ) as create_entries,
        ):
            summary = process_expired_allocation_chunk(["LAL-0001", "LAL-0002"])

        get_rows.assert_called_once_with(["LAL-0001", "LAL-0002"])
        create_entries.assert_called_once_with(expired_rows)
        self.assertEqual(summary["processed_count"], 1)
        self.assertEqual(summary["skipped_count"], 1)

    def test_dispatch_allocate_earned_leaves_enqueues_leave_type_scoped_chunks(self):
        cache = _DummyCache()
        leave_types = [frappe._dict({"name": "LT-Annual"}), frappe._dict({"name": "LT-Monthly"})]

        def _fake_get_leave_allocations(target_date, leave_type, allocation_names=None):
            self.assertIsNone(allocation_names)
            if leave_type == "LT-Annual":
                return [frappe._dict({"name": "LAL-0001"}), frappe._dict({"name": "LAL-0002"})]
            return [frappe._dict({"name": "LAL-0003"})]

        with (
            patch("ifitwala_ed.hr.utils._earned_leave_scheduler_enabled", return_value=True),
            patch("ifitwala_ed.hr.utils._get_today_date", return_value="2026-03-12"),
            patch("ifitwala_ed.hr.utils.frappe.cache", return_value=cache),
            patch("ifitwala_ed.hr.utils.get_earned_leaves", return_value=leave_types),
            patch("ifitwala_ed.hr.utils.get_leave_allocations", side_effect=_fake_get_leave_allocations),
            patch("ifitwala_ed.hr.utils.frappe.enqueue") as enqueue,
        ):
            summary = dispatch_allocate_earned_leaves(chunk_size=2)

        self.assertEqual(summary["candidate_count"], 3)
        self.assertEqual(summary["chunk_count"], 2)
        self.assertEqual(enqueue.call_args_list[0].kwargs["leave_type_name"], "LT-Annual")
        self.assertEqual(enqueue.call_args_list[0].kwargs["allocation_names"], ["LAL-0001", "LAL-0002"])
        self.assertEqual(enqueue.call_args_list[1].kwargs["leave_type_name"], "LT-Monthly")
        self.assertEqual(enqueue.call_args_list[1].kwargs["allocation_names"], ["LAL-0003"])

    def test_dispatch_generate_leave_encashment_enqueues_chunks(self):
        cache = _DummyCache()
        encashments = [
            frappe._dict({"name": "LAL-0001"}),
            frappe._dict({"name": "LAL-0002"}),
            frappe._dict({"name": "LAL-0003"}),
        ]

        with (
            patch("ifitwala_ed.hr.utils._leave_encashment_scheduler_enabled", return_value=True),
            patch("ifitwala_ed.hr.utils.frappe.cache", return_value=cache),
            patch("ifitwala_ed.hr.utils._get_leave_encashment_rows", return_value=encashments),
            patch("ifitwala_ed.hr.utils.frappe.enqueue") as enqueue,
        ):
            summary = dispatch_generate_leave_encashment(chunk_size=2)

        self.assertEqual(summary["candidate_count"], 3)
        self.assertEqual(summary["chunk_count"], 2)
        self.assertEqual(enqueue.call_args_list[0].kwargs["allocation_names"], ["LAL-0001", "LAL-0002"])
        self.assertEqual(enqueue.call_args_list[1].kwargs["allocation_names"], ["LAL-0003"])

    def test_process_leave_encashment_rows_skips_existing_allocations(self):
        cache = _DummyCache()
        leave_allocations = [
            frappe._dict({"name": "LAL-0001", "employee": "EMP-0001", "to_date": "2026-03-11"}),
            frappe._dict({"name": "LAL-0002", "employee": "EMP-0002", "to_date": "2026-03-11"}),
        ]

        def _fake_exists(doctype, filters=None):
            if doctype == "Leave Encashment" and filters.get("leave_allocation") == "LAL-0001":
                return True
            return False

        with (
            patch("ifitwala_ed.hr.utils.frappe.cache", return_value=cache),
            patch("ifitwala_ed.hr.utils.frappe.db.exists", side_effect=_fake_exists),
            patch(
                "ifitwala_ed.hr.doctype.leave_encashment.leave_encashment.get_assigned_salary_structure",
                return_value="SAL-0001",
            ),
            patch(
                "ifitwala_ed.hr.doctype.leave_encashment.leave_encashment.create_leave_encashment"
            ) as create_encashment,
        ):
            result = _process_leave_encashment_rows(leave_allocations)

        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["skipped_count"], 1)
        create_encashment.assert_called_once()
        self.assertEqual(create_encashment.call_args.kwargs["leave_allocation"][0].name, "LAL-0002")

from __future__ import annotations

import copy
import unittest
from contextlib import contextmanager

import frappe

from ifitwala_ed.tests.bootstrap import IfitwalaBootstrapRecords, IfitwalaBootstrapTestData

TEST_SITE = "test_site"


def _ensure_frappe_context(test_site: str = TEST_SITE) -> None:
    site = getattr(frappe.local, "site", None)
    if not site:
        frappe.init(test_site)

    if not getattr(frappe.local, "db", None):
        frappe.connect()


def _rollback_db() -> None:
    if getattr(frappe.local, "db", None):
        frappe.db.value_cache.clear()
        frappe.db.rollback()


def _restore_local_state(flags) -> None:
    frappe.local.flags = copy.deepcopy(flags)
    frappe.local.error_log = []
    frappe.local.message_log = []
    frappe.local.debug_log = []
    frappe.local.response = frappe._dict({"docs": []})
    frappe.local.cache = {}
    frappe.local.lang = "en"
    frappe.local.preload_assets = {"style": [], "script": [], "icons": []}

    if hasattr(frappe.local, "request"):
        delattr(frappe.local, "request")


class IfitwalaEdTestSuite(unittest.TestCase):
    """Deterministic base class for DB-backed Ifitwala_Ed tests."""

    TEST_SITE = TEST_SITE
    bootstrap: IfitwalaBootstrapRecords
    maxDiff = 10_000

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _ensure_frappe_context(cls.TEST_SITE)
        frappe.set_user("Administrator")
        _rollback_db()
        cls.bootstrap = IfitwalaBootstrapTestData.ensure()
        cls._ifitwala_class_flags = copy.deepcopy(frappe.local.flags)
        cls.addClassCleanup(_restore_local_state, cls._ifitwala_class_flags)
        cls.addClassCleanup(_rollback_db)

    def setUp(self):
        super().setUp()
        _ensure_frappe_context(self.TEST_SITE)
        self._ifitwala_test_flags = copy.deepcopy(frappe.local.flags)
        self._reset_volatile_flags()

    def tearDown(self):
        try:
            flags = getattr(
                self,
                "_ifitwala_test_flags",
                getattr(self, "_ifitwala_class_flags", frappe.local.flags),
            )
            _restore_local_state(flags)
            self._reset_volatile_flags()
            _rollback_db()
        finally:
            super().tearDown()

    @contextmanager
    def set_user(self, user: str):
        old_user = frappe.session.user
        try:
            frappe.set_user(user)
            yield
        finally:
            frappe.set_user(old_user)

    @staticmethod
    def _reset_volatile_flags() -> None:
        frappe.flags.enrollment_from_request = False


class IfitwalaFrappeTestCase(IfitwalaEdTestSuite):
    """Compatibility name for existing tests.

    New DB-backed tests should inherit IfitwalaEdTestSuite directly.
    """

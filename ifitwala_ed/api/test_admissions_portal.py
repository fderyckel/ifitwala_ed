# ifitwala_ed/api/test_admissions_portal.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_portal import _portal_status_for, _read_only_for


class TestAdmissionsPortalContracts(FrappeTestCase):
    def test_withdrawn_status_maps_to_portal_withdrawn(self):
        self.assertEqual(_portal_status_for("Withdrawn"), "Withdrawn")

    def test_withdrawn_status_is_read_only_with_reason(self):
        is_read_only, reason = _read_only_for("Withdrawn")
        self.assertTrue(is_read_only)
        self.assertTrue(bool(reason))

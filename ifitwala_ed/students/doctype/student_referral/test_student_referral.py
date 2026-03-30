# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.students.doctype.student_referral.student_referral import (
    get_permission_query_conditions,
    has_permission,
)


class TestStudentReferral(FrappeTestCase):
    def test_privileged_roles_can_read_all_referrals(self):
        doc = frappe._dict(owner="teacher@example.com", referral_source="Staff")

        for role_name in ("Academic Admin", "Counselor", "Pastoral Lead", "System Manager"):
            with patch(
                "ifitwala_ed.students.doctype.student_referral.student_referral.frappe.get_roles",
                return_value=[role_name],
            ):
                self.assertIsNone(get_permission_query_conditions("viewer@example.com"))
                self.assertTrue(has_permission(doc, user="viewer@example.com"))

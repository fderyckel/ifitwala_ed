# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.doctype.communication_interaction_entry import communication_interaction_entry


class TestCommunicationInteractionEntry(FrappeTestCase):
    def test_staff_comment_roles_infer_staff_audience_type(self):
        for role in ("Instructor", "Administrator"):
            doc = frappe._dict(
                user="staff@example.com",
                audience_type=None,
                note="Thanks for the update",
                intent_type="Comment",
                visibility=None,
            )

            with (
                self.subTest(role=role),
                patch(
                    "ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry.frappe.get_roles",
                    return_value=[role],
                ),
            ):
                communication_interaction_entry.CommunicationInteractionEntry._infer_audience_type_if_missing(doc)
                communication_interaction_entry.CommunicationInteractionEntry._apply_staff_comments_constraints(
                    doc,
                    frappe._dict(allow_private_notes=0),
                )

            self.assertEqual(doc.audience_type, "Staff")
            self.assertEqual(doc.visibility, "Public to audience")

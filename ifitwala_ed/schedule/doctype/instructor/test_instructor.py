# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.instructor.instructor import sync_instructor_logs


class TestInstructor(FrappeTestCase):
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.get_doc")
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.exists")
    def test_sync_instructor_logs_rebuilds_each_existing_instructor(self, mock_exists, mock_get_doc):
        doc_one = type("InstructorDoc", (), {"flags": type("Flags", (), {})()})()
        doc_one.rebuild_instructor_log = lambda: None
        doc_one.save = lambda **kwargs: kwargs

        doc_two = type("InstructorDoc", (), {"flags": type("Flags", (), {})()})()
        doc_two.rebuild_instructor_log = lambda: None
        doc_two.save = lambda **kwargs: kwargs

        mock_exists.side_effect = lambda doctype, name=None: {
            ("Instructor", "Cedric Villani"): True,
            ("Instructor", "Andreas Vesalius"): True,
        }.get((doctype, name), False)
        mock_get_doc.side_effect = [doc_two, doc_one]

        with (
            patch.object(doc_one, "rebuild_instructor_log") as rebuild_one,
            patch.object(doc_one, "save") as save_one,
            patch.object(doc_two, "rebuild_instructor_log") as rebuild_two,
            patch.object(doc_two, "save") as save_two,
        ):
            sync_instructor_logs(["Cedric Villani", "Cedric Villani", "", "Andreas Vesalius"])

        self.assertEqual(mock_get_doc.call_count, 2)
        rebuild_one.assert_called_once_with()
        rebuild_two.assert_called_once_with()
        save_one.assert_called_once_with(ignore_permissions=True)
        save_two.assert_called_once_with(ignore_permissions=True)
        self.assertTrue(doc_one.flags.ignore_version)
        self.assertTrue(doc_two.flags.ignore_version)

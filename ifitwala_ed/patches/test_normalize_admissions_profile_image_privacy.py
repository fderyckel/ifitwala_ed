from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _patch_module():
    authority = ModuleType("ifitwala_ed.integrations.drive.authority")
    authority.get_current_drive_file_for_slot = lambda **kwargs: None

    admissions = ModuleType("ifitwala_ed.integrations.drive.admissions")
    admissions._build_guardian_profile_image_slot = lambda guardian_row_name: (
        f"guardian_profile_image__{guardian_row_name.lower()}"
    )

    privacy = ModuleType("ifitwala_ed.patches.normalize_profile_image_privacy")
    privacy._compute_private_file_url = lambda **kwargs: "/private/files/normalized.png"

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.integrations.drive.authority": authority,
            "ifitwala_ed.integrations.drive.admissions": admissions,
            "ifitwala_ed.patches.normalize_profile_image_privacy": privacy,
        }
    ) as frappe:
        frappe.db.table_exists = lambda doctype: doctype in {"Drive File", "File", "Drive Upload Session"}
        frappe.db.exists = lambda doctype, name: True
        frappe.db.get_value = lambda doctype, name, fieldname: f"/private/files/{name}.png"
        frappe.get_all = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.patches.normalize_admissions_profile_image_privacy"), frappe


class TestNormalizeAdmissionsProfileImagePrivacy(TestCase):
    def test_execute_normalizes_admissions_profile_rows_and_syncs_current_fields(self):
        set_calls = []

        def _get_all(doctype, **kwargs):
            if doctype == "Drive File":
                return [
                    {
                        "name": "DF-APP-1",
                        "slot": "profile_image",
                        "file": "FILE-APP-1",
                        "source_upload_session": "DUS-APP-1",
                        "storage_backend": "local",
                        "storage_object_key": "applicant-key",
                    },
                    {
                        "name": "DF-GRD-1",
                        "slot": "guardian_profile_image__grdrow1",
                        "file": "FILE-GRD-1",
                        "source_upload_session": "DUS-GRD-1",
                        "storage_backend": "local",
                        "storage_object_key": "guardian-key",
                    },
                ]
            if doctype == "Student Applicant":
                return [{"name": "APP-0001"}]
            if doctype == "Student Applicant Guardian":
                return [{"name": "GRDROW1", "parent": "APP-0001"}]
            return []

        def _get_current_drive_file_for_slot(**kwargs):
            slot = kwargs.get("slot")
            if slot == "profile_image":
                return {"file": "FILE-APP-CURRENT"}
            if slot == "guardian_profile_image__grdrow1":
                return {"file": "FILE-GRD-CURRENT"}
            return None

        with _patch_module() as (module, frappe):
            module.get_current_drive_file_for_slot = _get_current_drive_file_for_slot
            frappe.get_all = _get_all

            def _set_value(doctype, name, *args, **kwargs):
                set_calls.append((doctype, name, args))

            frappe.db.set_value = _set_value

            module.execute()

        self.assertIn(("Drive File", "DF-APP-1", ("is_private", 1)), set_calls)
        self.assertIn(("Drive File", "DF-GRD-1", ("is_private", 1)), set_calls)
        self.assertIn(("Drive Upload Session", "DUS-APP-1", ("is_private", 1)), set_calls)
        self.assertIn(("Drive Upload Session", "DUS-GRD-1", ("is_private", 1)), set_calls)
        self.assertIn(
            (
                "File",
                "FILE-APP-1",
                ({"is_private": 1, "file_url": "/private/files/normalized.png"},),
            ),
            set_calls,
        )
        self.assertIn(
            (
                "File",
                "FILE-GRD-1",
                ({"is_private": 1, "file_url": "/private/files/normalized.png"},),
            ),
            set_calls,
        )
        self.assertIn(
            (
                "Student Applicant",
                "APP-0001",
                ("applicant_image", "/private/files/FILE-APP-CURRENT.png"),
            ),
            set_calls,
        )
        self.assertIn(
            (
                "Student Applicant Guardian",
                "GRDROW1",
                ("guardian_image", "/private/files/FILE-GRD-CURRENT.png"),
            ),
            set_calls,
        )

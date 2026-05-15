from __future__ import annotations

import re
from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _student_portfolio_module():
    file_access_api = ModuleType("ifitwala_ed.api.file_access")
    file_access_api.resolve_academic_file_open_url = lambda **kwargs: "/open/file"

    student_log_dashboard_api = ModuleType("ifitwala_ed.api.student_log_dashboard")
    student_log_dashboard_api.get_authorized_schools = lambda user: ["SCH-1"]

    drive_authority_api = ModuleType("ifitwala_ed.integrations.drive.authority")
    drive_authority_api.get_drive_file_for_file = lambda *args, **kwargs: None

    school_tree_api = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree_api.get_school_lineage = lambda school: [school]

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.add_days = lambda value, days: value
    frappe_utils.get_datetime = lambda value: value
    frappe_utils.getdate = lambda value: value
    frappe_utils.now_datetime = lambda: "2026-04-07 10:30:00"
    frappe_utils.today = lambda: "2026-04-07"
    frappe_utils.strip_html = lambda value: re.sub(r"<[^>]+>", "", value or "")

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.api.file_access": file_access_api,
            "ifitwala_ed.api.student_log_dashboard": student_log_dashboard_api,
            "ifitwala_ed.integrations.drive.authority": drive_authority_api,
            "ifitwala_ed.utilities.school_tree": school_tree_api,
        }
    ) as frappe:
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.count = lambda *args, **kwargs: 0
        frappe.get_all = lambda *args, **kwargs: []
        frappe.request = None
        yield import_fresh("ifitwala_ed.api.student_portfolio")


class TestStudentPortfolioApi(TestCase):
    def test_add_portfolio_item_rejects_ungoverned_external_artefact(self):
        class _PortfolioDoc:
            name = "PORT-1"
            student = "STU-1"
            academic_year = "2026-2027"
            school = "SCH-1"

            def append(self, fieldname, payload):
                raise AssertionError("invalid artefact must not be appended")

            def save(self, ignore_permissions=True):
                raise AssertionError("invalid artefact must not be saved")

        with _student_portfolio_module() as module:
            module._ensure_can_write_student = lambda student: {"role": "Student", "students": [student]}
            module._get_or_create_portfolio = lambda student, academic_year, school: "PORT-1"
            module.get_drive_file_for_file = lambda *args, **kwargs: None
            module.frappe.get_doc = lambda doctype, name=None: _PortfolioDoc()

            with self.assertRaises(module.frappe.ValidationError):
                module.add_portfolio_item(
                    {
                        "student": "STU-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                        "item_type": "External Artefact",
                        "artefact_file": "FILE-ARTEFACT-1",
                    }
                )

    def test_add_portfolio_item_accepts_governed_external_artefact(self):
        appended = {}

        class _PortfolioDoc:
            name = "PORT-1"
            student = "STU-1"
            academic_year = "2026-2027"
            school = "SCH-1"

            def append(self, fieldname, payload):
                appended["fieldname"] = fieldname
                appended["payload"] = payload
                return SimpleNamespace(name="ITEM-1", moderation_state=payload.get("moderation_state"))

            def save(self, ignore_permissions=True):
                appended["saved"] = True

        with _student_portfolio_module() as module:
            module._ensure_can_write_student = lambda student: {"role": "Student", "students": [student]}
            module._get_or_create_portfolio = lambda student, academic_year, school: "PORT-1"
            module.get_drive_file_for_file = lambda file_name, **kwargs: {
                "file": file_name,
                "primary_subject_type": "Student",
                "primary_subject_id": "STU-1",
                "purpose": "portfolio_evidence",
                "slot": "portfolio_artefact",
                "school": "SCH-1",
            }
            module.frappe.get_doc = lambda doctype, name=None: _PortfolioDoc()

            payload = module.add_portfolio_item(
                {
                    "student": "STU-1",
                    "academic_year": "2026-2027",
                    "school": "SCH-1",
                    "item_type": "External Artefact",
                    "artefact_file": "FILE-ARTEFACT-1",
                }
            )

        self.assertEqual(payload["portfolio"], "PORT-1")
        self.assertEqual(appended["fieldname"], "items")
        self.assertEqual(appended["payload"]["artefact_file"], "FILE-ARTEFACT-1")
        self.assertTrue(appended["saved"])

    def test_resolve_portfolio_share_context_omits_invalid_external_artefact_download(self):
        portfolio_doc = SimpleNamespace(
            name="PORT-1",
            title="Student Portfolio",
            showcase_title="",
            showcase_subtitle="",
            student="STU-1",
            academic_year="2026-2027",
            school="SCH-1",
            items=[
                SimpleNamespace(
                    name="ITEM-1",
                    item_type="External Artefact",
                    caption="Showcase artefact",
                    reflection_summary="",
                    evidence_date="2026-04-07",
                    task_submission="",
                    student_reflection_entry="",
                    artefact_file="FILE-LEGACY-1",
                    is_showcase=1,
                    moderation_state="Approved",
                )
            ],
        )

        with _student_portfolio_module() as module:
            module._token_hash = lambda token: "hashed-token"

            def fake_get_value(doctype, filters=None, fieldname=None, as_dict=False):
                if doctype == "Portfolio Share Link":
                    return {
                        "name": "SHARE-1",
                        "portfolio": "PORT-1",
                        "expires_on": "2026-04-08",
                        "revoked": 0,
                        "allow_download": 1,
                        "allowed_viewer_email": "",
                    }
                if doctype == "Student":
                    return {
                        "name": "STU-1",
                        "student_full_name": "Student One",
                        "student_preferred_name": "Stu",
                    }
                return None

            module.frappe.db.get_value = fake_get_value
            module.frappe.db.set_value = lambda *args, **kwargs: None
            module.frappe.get_doc = lambda doctype, name=None: portfolio_doc
            module.frappe.get_all = lambda doctype, filters=None, fields=None, order_by=None, limit=None: (
                [{"name": "FILE-LEGACY-1", "file_name": "legacy.pdf", "file_size": 128}] if doctype == "File" else []
            )

            payload = module.resolve_portfolio_share_context(token="share-token")

        item = (payload.get("portfolio") or {}).get("items") or [{}]
        self.assertIsNone(item[0].get("artefact_file"))
        self.assertIsNone(item[0].get("artefact_file_url"))
        self.assertIsNone(item[0].get("artefact_file_name"))

    def test_create_reflection_entry_infers_student_for_student_actor(self):
        captured: dict[str, object] = {}

        with _student_portfolio_module() as module:
            module.frappe.session.user = "student@example.com"
            module.frappe.get_roles = lambda user=None: ["Student"]
            module._resolve_student_for_user = lambda user: "STU-1"
            module._ensure_can_write_student = lambda student: {"role": "Student", "students": [student]}
            module._resolve_settings_for_school = lambda school: {"default_visibility_for_reflection": "Teacher"}
            module.frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: {
                ("Student", "STU-1", "anchor_school"): "SCH-1",
                ("School", "SCH-1", "organization"): "ORG-1",
            }.get((doctype, name, fieldname))
            module.frappe.get_all = lambda doctype, filters=None, fields=None, order_by=None, limit=None: (
                [{"academic_year": "2026-2027"}] if doctype == "Program Enrollment" else []
            )

            def fake_get_doc(data):
                captured.update(data)
                return SimpleNamespace(
                    name="REF-1",
                    student=data.get("student"),
                    academic_year=data.get("academic_year"),
                    entry_date=data.get("entry_date"),
                    moderation_state=data.get("moderation_state"),
                    insert=lambda ignore_permissions=True: None,
                )

            module.frappe.get_doc = fake_get_doc

            payload = module.create_reflection_entry(
                {
                    "body": "I can now explain how the microscope evidence supports the claim.",
                    "course": "COURSE-1",
                    "student_group": "GROUP-1",
                    "class_session": "SESSION-1",
                }
            )

        self.assertEqual(payload["name"], "REF-1")
        self.assertEqual(payload["student"], "STU-1")
        self.assertEqual(captured["student"], "STU-1")
        self.assertEqual(captured["school"], "SCH-1")
        self.assertEqual(captured["academic_year"], "2026-2027")
        self.assertEqual(captured["class_session"], "SESSION-1")
        self.assertEqual(captured["visibility"], "Teacher")

    def test_list_reflection_entries_accepts_learning_context_filters(self):
        seen: dict[str, object] = {}

        with _student_portfolio_module() as module:
            module._resolve_actor_scope = lambda requested_students, school_filter=None: {
                "role": "Student",
                "students": ["STU-1"],
                "user": "student@example.com",
            }
            module.frappe.db.count = lambda doctype, filters=None: seen.update({"count_filters": filters}) or 1

            def fake_get_all(
                doctype,
                filters=None,
                fields=None,
                order_by=None,
                start=None,
                page_length=None,
            ):
                seen["filters"] = filters
                seen["fields"] = fields
                seen["page_length"] = page_length
                return [
                    {
                        "name": "REF-1",
                        "student": "STU-1",
                        "academic_year": "2026-2027",
                        "school": "SCH-1",
                        "entry_date": "2026-04-07",
                        "entry_type": "Reflection",
                        "visibility": "Teacher",
                        "moderation_state": "Draft",
                        "body": "<p>Microscope evidence helped me compare the two cells.</p>",
                        "course": "COURSE-1",
                        "student_group": "GROUP-1",
                        "class_session": "SESSION-1",
                        "task_delivery": "TDL-1",
                        "task_submission": "TS-1",
                    }
                ]

            module.frappe.get_all = fake_get_all

            payload = module.list_reflection_entries(
                {
                    "course": "COURSE-1",
                    "student_group": "GROUP-1",
                    "class_session": "SESSION-1",
                    "task_delivery": "TDL-1",
                    "task_submission": "TS-1",
                }
            )

        self.assertEqual(seen["filters"]["course"], "COURSE-1")
        self.assertEqual(seen["filters"]["student_group"], "GROUP-1")
        self.assertEqual(seen["filters"]["class_session"], "SESSION-1")
        self.assertEqual(seen["filters"]["task_delivery"], "TDL-1")
        self.assertEqual(seen["filters"]["task_submission"], "TS-1")
        self.assertIn("course", seen["fields"])
        self.assertEqual(payload["items"][0]["task_delivery"], "TDL-1")
        self.assertEqual(payload["items"][0]["body_preview"], "Microscope evidence helped me compare the two cells.")

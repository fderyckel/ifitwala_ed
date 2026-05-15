from __future__ import annotations

from contextlib import contextmanager
from io import BytesIO
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _materials_module():
    file_access = ModuleType("ifitwala_ed.api.file_access")
    file_access.get_academic_file_thumbnail_ready_map = lambda file_names: {
        file_name: True for file_name in file_names or []
    }
    file_access.resolve_academic_file_open_url = lambda **kwargs: "/open/material"
    file_access.resolve_academic_file_preview_url = lambda **kwargs: "/preview/material"
    file_access.resolve_academic_file_thumbnail_url = lambda **kwargs: "/thumbnail/material"

    materials_domain = ModuleType("ifitwala_ed.curriculum.materials")
    materials_domain.MATERIAL_TYPE_FILE = "File"

    governed_uploads = ModuleType("ifitwala_ed.utilities.governed_uploads")

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.api.file_access": file_access,
            "ifitwala_ed.curriculum.materials": materials_domain,
            "ifitwala_ed.utilities.governed_uploads": governed_uploads,
        }
    ):
        yield import_fresh("ifitwala_ed.api.materials")


class TestTaskMaterialSerialization(TestCase):
    def test_serialize_task_material_returns_governed_attachment_for_file_materials(self):
        with _materials_module() as materials_api:
            payload = materials_api._serialize_task_material(
                {
                    "material": "MAT-1",
                    "course": "COURSE-1",
                    "title": "Microscope guide",
                    "material_type": "File",
                    "description": "Use during the task.",
                    "file": "FILE-1",
                    "file_url": "/private/files/microscope-guide.pdf",
                    "file_name": "microscope-guide.pdf",
                    "placements": [
                        {
                            "placement": "PLACEMENT-1",
                            "origin": "task",
                            "usage_role": "Reference",
                            "placement_note": "Bring to class.",
                            "placement_order": 1,
                        }
                    ],
                }
            )

        self.assertNotIn("thumbnail_url", payload)
        self.assertNotIn("preview_url", payload)
        self.assertNotIn("open_url", payload)
        self.assertNotIn("file", payload)
        self.assertNotIn("attachment_preview", payload)
        self.assertEqual(payload["placement"], "PLACEMENT-1")
        self.assertEqual(payload["attachment"]["id"], "PLACEMENT-1")
        self.assertEqual(payload["attachment"]["surface"], "task.material")
        self.assertEqual(payload["attachment"]["owner_doctype"], "Material Placement")
        self.assertEqual(payload["attachment"]["owner_name"], "PLACEMENT-1")
        self.assertEqual(payload["attachment"]["kind"], "pdf")
        self.assertEqual(payload["attachment"]["thumbnail_url"], "/thumbnail/material")
        self.assertEqual(payload["attachment"]["preview_url"], "/preview/material")
        self.assertEqual(payload["attachment"]["download_url"], "/open/material")

    def test_serialize_task_material_keeps_reference_links_previewless(self):
        with _materials_module() as materials_api:
            payload = materials_api._serialize_task_material(
                {
                    "material": "MAT-2",
                    "course": "COURSE-1",
                    "title": "Reference article",
                    "material_type": "Reference Link",
                    "reference_url": "https://example.com/article",
                    "placements": [{"placement": "PLACEMENT-2"}],
                }
            )

        self.assertNotIn("thumbnail_url", payload)
        self.assertNotIn("preview_url", payload)
        self.assertNotIn("open_url", payload)
        self.assertNotIn("attachment_preview", payload)
        self.assertEqual(payload["attachment"]["surface"], "task.material")
        self.assertEqual(payload["attachment"]["kind"], "link")
        self.assertEqual(payload["attachment"]["preview_mode"], "external_link")
        self.assertEqual(payload["attachment"]["open_url"], "https://example.com/article")

    def test_upload_task_material_file_rejects_non_pdf_and_non_image_uploads(self):
        with _materials_module() as materials_api:
            upload = type(
                "Upload",
                (),
                {
                    "filename": "checkpoint-notes.docx",
                    "mimetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "stream": BytesIO(b"fake-docx"),
                },
            )()
            materials_api.frappe.request = type("Request", (), {"files": {"file": upload}})()

            with (
                patch.object(materials_api, "_require_task_write", return_value=object()),
                self.assertRaises(Exception) as ctx,
            ):
                materials_api.upload_task_material_file(task="TASK-1", title="Checkpoint notes")

        self.assertIn("Task attachments support PDF, JPG, PNG, and WEBP files only.", str(ctx.exception))

    def test_upload_task_material_file_links_returned_governed_file_before_reload(self):
        with _materials_module() as materials_api:
            upload = type(
                "Upload",
                (),
                {
                    "filename": "lab-guide.pdf",
                    "mimetype": "application/pdf",
                    "stream": BytesIO(b"%PDF-1.4"),
                },
            )()
            materials_api.frappe.request = type("Request", (), {"files": {"file": upload}})()
            materials_api.frappe.db.savepoint = lambda name: None
            materials_api.frappe.db.rollback = lambda save_point=None: None
            set_value_calls = []
            materials_api.frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: None
            materials_api.frappe.db.set_value = lambda *args, **kwargs: set_value_calls.append((args, kwargs))

            material = type("Material", (), {"name": "MAT-1"})()
            placement = type("Placement", (), {"name": "PLACEMENT-1"})()
            materials_api.materials_domain.create_file_material_record = lambda **kwargs: material
            materials_api.materials_domain.create_material_placement = lambda **kwargs: placement
            materials_api.materials_domain.list_anchor_materials = lambda doctype, name: [
                {
                    "material": "MAT-1",
                    "course": "COURSE-1",
                    "title": "Lab guide",
                    "material_type": "File",
                    "file": "FILE-1",
                    "file_url": "/private/files/lab-guide.pdf",
                    "file_name": "lab-guide.pdf",
                    "file_size": 8,
                    "placements": [{"placement": "PLACEMENT-1"}],
                }
            ]
            materials_api.governed_uploads.upload_supporting_material_file = lambda material: {
                "file": "FILE-1",
                "file_name": "lab-guide.pdf",
                "file_size": 8,
            }

            with patch.object(materials_api, "_require_task_write", return_value=object()):
                payload = materials_api.upload_task_material_file(task="TASK-1", title="Lab guide")

        self.assertEqual(payload["material"], "MAT-1")
        self.assertEqual(payload["placement"], "PLACEMENT-1")
        self.assertEqual(payload["attachment"]["surface"], "task.material")
        self.assertNotIn("attachment_preview", payload)
        self.assertEqual(set_value_calls[0][0][0:2], ("Supporting Material", "MAT-1"))
        self.assertEqual(set_value_calls[0][0][2]["file"], "FILE-1")
        self.assertFalse(set_value_calls[0][1]["update_modified"])

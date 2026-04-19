from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase

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
    def test_serialize_task_material_includes_preview_url_for_file_materials(self):
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

        self.assertEqual(payload["thumbnail_url"], "/thumbnail/material")
        self.assertEqual(payload["preview_url"], "/preview/material")
        self.assertEqual(payload["open_url"], "/open/material")
        self.assertEqual(payload["placement"], "PLACEMENT-1")

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

        self.assertIsNone(payload["thumbnail_url"])
        self.assertIsNone(payload["preview_url"])
        self.assertEqual(payload["open_url"], "https://example.com/article")

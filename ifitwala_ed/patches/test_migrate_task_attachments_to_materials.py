from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeDoc:
    counters = {"Supporting Material": 0, "Material Placement": 0, "Drive Binding": 0}

    def __init__(self, payload):
        self.flags = SimpleNamespace()
        self.payload = dict(payload)
        for key, value in payload.items():
            setattr(self, key, value)

    def insert(self, ignore_permissions=False):
        prefix = {
            "Supporting Material": "MAT",
            "Material Placement": "MAT-PLC",
            "Drive Binding": "BIND",
        }.get(self.doctype, "DOC")
        self.counters[self.doctype] = self.counters.get(self.doctype, 0) + 1
        self.name = f"{prefix}-{self.counters[self.doctype]}"
        self.ignore_permissions = ignore_permissions
        return self

    def save(self, ignore_permissions=False):
        self.saved = ignore_permissions
        return self


class TestMigrateTaskAttachmentsToMaterials(TestCase):
    def test_execute_migrates_file_and_reference_rows_to_materials(self):
        _FakeDoc.counters = {"Supporting Material": 0, "Material Placement": 0, "Drive Binding": 0}
        created_docs: list[_FakeDoc] = []
        saved_materials: list[_FakeDoc] = []
        deleted_rows: list[str] = []
        updates: list[tuple[str, str, dict, bool]] = []

        attached_rows = [
            {
                "name": "ROW-FILE",
                "parent": "TASK-1",
                "idx": 1,
                "section_break_sbex": "Worksheet",
                "file": "/private/files/worksheet.pdf",
                "external_url": None,
                "description": "Read before class",
                "file_name": "worksheet.pdf",
                "file_size": 1024,
            },
            {
                "name": "ROW-LINK",
                "parent": "TASK-1",
                "idx": 2,
                "section_break_sbex": "Reference",
                "file": None,
                "external_url": "https://example.edu/reference",
                "description": "Optional",
                "file_name": None,
                "file_size": None,
            },
        ]

        def get_all(doctype, **kwargs):
            if doctype == "Attached Document":
                return attached_rows
            if doctype == "Drive File":
                return []
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        def get_value(doctype, name, fieldname=None, as_dict=False):
            if doctype == "Task":
                return {"default_course": "COURSE-1"} if as_dict else "COURSE-1"
            if doctype == "File":
                if isinstance(name, dict):
                    return {
                        "name": "FILE-1",
                        "file_url": "/private/files/worksheet.pdf",
                        "file_name": "worksheet.pdf",
                        "file_size": 1024,
                    }
                return {
                    "name": "FILE-1",
                    "file_url": "/private/files/worksheet.pdf",
                    "file_name": "worksheet.pdf",
                    "file_size": 1024,
                }
            if doctype == "Drive File":
                return {
                    "name": "DRV-1",
                    "file": "FILE-1",
                    "slot": "supporting_material__ROW-FILE",
                    "organization": "ORG-1",
                    "school": "SCH-1",
                    "status": "active",
                }
            if doctype == "Drive Binding":
                return {
                    "name": "BIND-LEGACY",
                    "status": "active",
                    "is_primary": 1,
                }
            if doctype == "Material Placement":
                return None
            return None

        def get_doc(*args):
            if isinstance(args[0], dict):
                doc = _FakeDoc(args[0])
                created_docs.append(doc)
                return doc
            doctype, name = args
            if doctype == "Supporting Material":
                material = next(doc for doc in created_docs if doc.doctype == doctype and doc.name == name)
                saved_materials.append(material)
                return material
            raise AssertionError(f"Unexpected get_doc: {doctype} {name}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: True
            frappe.db.exists = lambda doctype, name=None: doctype == "Task" and name == "TASK-1"
            frappe.get_all = get_all
            frappe.db.get_value = get_value
            frappe.db.sql = lambda *args, **kwargs: []
            frappe.get_doc = get_doc
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            frappe.delete_doc = lambda doctype, name, **kwargs: deleted_rows.append(name)
            module = import_fresh("ifitwala_ed.patches.migrate_task_attachments_to_materials")

            module.execute()

        materials = [doc for doc in created_docs if doc.doctype == "Supporting Material"]
        placements = [doc for doc in created_docs if doc.doctype == "Material Placement"]
        self.assertEqual([doc.title for doc in materials], ["Worksheet", "Reference"])
        self.assertEqual([doc.material_type for doc in materials], ["File", "Reference Link"])
        self.assertEqual([doc.anchor_name for doc in placements], ["TASK-1", "TASK-1"])
        self.assertEqual(deleted_rows, ["ROW-FILE", "ROW-LINK"])
        self.assertEqual(saved_materials[0].file, "FILE-1")
        self.assertIn(
            (
                "File",
                "FILE-1",
                {
                    "attached_to_doctype": "Supporting Material",
                    "attached_to_name": "MAT-1",
                    "attached_to_field": "file",
                },
                False,
            ),
            updates,
        )
        self.assertIn(
            (
                "Drive File",
                "DRV-1",
                {
                    "owner_doctype": "Supporting Material",
                    "owner_name": "MAT-1",
                    "attached_doctype": "Supporting Material",
                    "attached_name": "MAT-1",
                    "slot": "material_file",
                },
                False,
            ),
            updates,
        )
        self.assertIn(
            (
                "Drive Binding",
                "BIND-LEGACY",
                {
                    "binding_doctype": "Supporting Material",
                    "binding_name": "MAT-1",
                    "binding_role": "supporting_material",
                    "slot": "material_file",
                    "status": "active",
                    "is_primary": 1,
                    "primary_key": "DRV-1|Supporting Material|MAT-1|supporting_material|material_file",
                },
                False,
            ),
            updates,
        )

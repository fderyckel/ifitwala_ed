from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillSupportingMaterialBindingRoles(TestCase):
    def test_execute_migrates_legacy_role_and_supersedes_conflicting_primary(self):
        updates: list[tuple[str, str, dict[str, object], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype != "Drive Binding":
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")

            filters = kwargs.get("filters") or {}
            if filters == {
                "binding_doctype": "Supporting Material",
                "binding_role": "supporting_material",
                "slot": "material_file",
                "status": "active",
                "is_primary": 1,
            }:
                return [
                    {
                        "drive_file": "DF-2",
                        "binding_doctype": "Supporting Material",
                        "binding_name": "MAT-2",
                        "slot": "material_file",
                    }
                ]

            if filters == {
                "binding_doctype": "Supporting Material",
                "binding_role": "general_reference",
                "slot": "material_file",
            }:
                return [
                    {
                        "name": "BIND-1",
                        "drive_file": "DF-1",
                        "binding_doctype": "Supporting Material",
                        "binding_name": "MAT-1",
                        "slot": "material_file",
                        "is_primary": 1,
                        "status": "active",
                    },
                    {
                        "name": "BIND-2",
                        "drive_file": "DF-2",
                        "binding_doctype": "Supporting Material",
                        "binding_name": "MAT-2",
                        "slot": "material_file",
                        "is_primary": 1,
                        "status": "active",
                    },
                    {
                        "name": "BIND-3",
                        "drive_file": "DF-3",
                        "binding_doctype": "Supporting Material",
                        "binding_name": "MAT-3",
                        "slot": "material_file",
                        "is_primary": 0,
                        "status": "inactive",
                    },
                ]

            raise AssertionError(f"Unexpected get_all filters: {filters}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Drive Binding"
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_supporting_material_binding_roles")

            module.execute()

        self.assertEqual(
            updates,
            [
                (
                    "Drive Binding",
                    "BIND-1",
                    {
                        "binding_role": "supporting_material",
                        "primary_key": "DF-1|Supporting Material|MAT-1|supporting_material|material_file",
                    },
                    False,
                ),
                (
                    "Drive Binding",
                    "BIND-2",
                    {
                        "binding_role": "supporting_material",
                        "status": "superseded",
                        "is_primary": 0,
                        "primary_key": None,
                    },
                    False,
                ),
                (
                    "Drive Binding",
                    "BIND-3",
                    {
                        "binding_role": "supporting_material",
                        "primary_key": None,
                    },
                    False,
                ),
            ],
        )

    def test_execute_returns_when_drive_binding_table_is_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when Drive Binding is unavailable")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_supporting_material_binding_roles")

            module.execute()
